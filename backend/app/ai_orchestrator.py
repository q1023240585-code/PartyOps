"""PartyOps 全系统智能编排器。

本模块把模型输出限制在一组固定的业务工具契约中。模型只负责提出结构化
计划，不能生成任意函数、SQL、Shell、URL 或文件路径；真正的权限、版本、
风险和用户确认检查始终由服务端完成。没有可用的本地规划模型时，使用同
一份工具契约驱动的规则计划，保证智能能力降级不会阻塞业务。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from .enums import ModelPackStatus
from .local_ai import complete_locally, llm_runtime
from .model_packs import active_model_pack, verify_installed_pack
from .models import AIModelPack, AIOrchestrationStep, User, utcnow
from .needle_intent import preview_intent_with_needle
from .problems import ProblemException


@dataclass(frozen=True)
class ToolContract:
    """可被编排器调用的最小工具契约。"""

    name: str
    description: str
    argument_keys: frozenset[str]
    risk: str
    mutates: bool
    sensitive: bool = False
    roles: frozenset[str] = frozenset({"admin", "staff"})


# 工具名称是源码白名单，不接受模型拼接出来的函数名。新增工具必须同时补
# 充参数、权限、风险、幂等和补偿测试，避免把自然语言直接变成副作用。
TOOL_REGISTRY: dict[str, ToolContract] = {
    "work.search": ToolContract(
        "work.search", "查询事项、日历和通知", frozenset({"query"}), "low", False
    ),
    "navigation.find": ToolContract(
        "navigation.find", "定位系统功能入口", frozenset({"target"}), "low", False
    ),
    "business_meeting.create_draft": ToolContract(
        "business_meeting.create_draft",
        "创建党委会或党建业务会议草稿",
        frozenset({"title", "scheduled_at", "topic_count"}),
        "medium",
        True,
    ),
    "business_meeting.prepare_workflow": ToolContract(
        "business_meeting.prepare_workflow",
        "生成会议筹备六步流程草稿",
        frozenset({"meeting_id", "responsible_ids"}),
        "medium",
        True,
    ),
    "ledger.inspect": ToolContract(
        "ledger.inspect", "检查并预览本地台账字段", frozenset({"target_type"}), "low", False
    ),
    "ledger.commit": ToolContract(
        "ledger.commit", "提交已确认的台账导入", frozenset({"import_id"}), "medium", True
    ),
    "party_development.timeline": ToolContract(
        "party_development.timeline",
        "生成发展党员真实进度时间轴草稿",
        frozenset({"case_id"}),
        "medium",
        True,
        sensitive=True,
    ),
    "extension.create_record": ToolContract(
        "extension.create_record",
        "向党务台账登记一条记录（党费/民主评议/考核指标/群团活动/团员/换届/品牌/舆情/标准化自查/教育培训）",
        frozenset({"resource", "values"}),
        "medium",
        True,
    ),
    "party_development.create_profile": ToolContract(
        "party_development.create_profile",
        "按抽取的姓名与申请书日期创建发展党员档案并生成参考计划",
        frozenset({"name", "gender", "party_committee", "party_branch", "application_date", "education"}),
        "medium",
        True,
        sensitive=True,
    ),
    "notifications.recalculate": ToolContract(
        "notifications.recalculate", "按任务日期立即重算提醒", frozenset({"task_id"}), "medium", True
    ),
    "files.explain_open": ToolContract(
        "files.explain_open", "解释文件授权、预览和打开状态", frozenset({"file_id"}), "low", False
    ),
    "official_format.review_diagnostics": ToolContract(
        "official_format.review_diagnostics",
        "根据本机排版引擎的问题码和标准条款生成复核建议",
        frozenset({"diagnostic_codes"}),
        "low",
        False,
    ),
    "fleet.diagnose": ToolContract(
        "fleet.diagnose", "检查主机和协同设备健康状态", frozenset({"device_id"}), "low", False
    ),
    "fleet.rebind": ToolContract(
        "fleet.rebind", "重新绑定协同设备", frozenset({"device_id"}), "high", True, sensitive=True
    ),
    "user.archive": ToolContract(
        "user.archive", "归档用户并预览责任移交影响", frozenset({"user_id", "handover_to"}), "high", True
    ),
    "user.delete": ToolContract(
        "user.delete", "删除用户数据（仅允许进入归档流程）", frozenset({"user_id"}), "high", True
    ),
    "settings.network_change": ToolContract(
        "settings.network_change", "修改协同公布地址", frozenset({"advertise_host", "port"}), "high", True, sensitive=True, roles=frozenset({"admin"})
    ),
}

_WRITE_TOOLS = frozenset(name for name, contract in TOOL_REGISTRY.items() if contract.mutates)
_DANGEROUS_MARKERS = re.compile(
    r"(?:rm\s+-rf|powershell|cmd(?:\.exe)?|/bin/(?:sh|bash)|drop\s+table|\bselect\s+.+\s+from|https?://|file://)",
    re.IGNORECASE,
)
_SAFE_OBJECT_ID = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")


def tool_contracts() -> list[dict[str, Any]]:
    """返回前端可展示的白名单契约，不暴露内部路径或模型提示。"""

    return [
        {
            "name": item.name,
            "description": item.description,
            "arguments": sorted(item.argument_keys),
            "risk": item.risk,
            "mutates": item.mutates,
            "sensitive": item.sensitive,
            "roles": sorted(item.roles),
            "requires_confirmation": item.mutates or item.risk == "high",
        }
        for item in TOOL_REGISTRY.values()
    ]


def _safe_text(value: object, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    text = _DANGEROUS_MARKERS.sub("[已隐藏]", text)
    text = re.sub(r"(?i)(密码|口令|token|密钥|secret)\s*[:=：]\s*\S+", r"\1=[已隐藏]", text)
    text = re.sub(r"(?i)[A-Za-z]:\\[^\s]+|/(?:home|root|Users|opt)/[^\s]+", "[本机路径]", text)
    return text[:limit]


def goal_summary(goal: str) -> str:
    """生成可审计但不保存原始提示的摘要。"""

    return _safe_text(goal, 500)


def input_digest(goal: str) -> str:
    return hashlib.sha256(goal.encode("utf-8")).hexdigest()


def sanitize_scope(scope: Mapping[str, Any] | None) -> dict[str, Any]:
    """只接收业务对象 ID，不接收正文、路径、凭据或任意上下文。"""

    allowed = {"task_ids", "file_ids", "meeting_ids", "case_ids", "archive_ids", "target_type"}
    result: dict[str, Any] = {}
    for key in allowed:
        value = (scope or {}).get(key)
        if key == "target_type":
            if value is not None:
                result[key] = _safe_text(value, 48)
            continue
        if isinstance(value, list):
            result[key] = [
                str(item)
                for item in value[:50]
                if item and _SAFE_OBJECT_ID.fullmatch(str(item))
            ]
    return result


def step_scope_digest(step: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        {
            "tool": step.get("tool") or step.get("tool_name"),
            "arguments": step.get("arguments", {}),
            "risk": step.get("risk") or step.get("risk_level"),
            "requires_confirmation": bool(step.get("requires_confirmation", True)),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


_CJK_NAME = re.compile(r"([\u4e00-\u9fa5]{2,4})(?:同志)?\s*(?:递交了?|提交了?)")
_CJK_NAME_WITH_DATE = re.compile(r"([\u4e00-\u9fa5]{2,4})(?:同志)?\s*于[^。；,]{0,16}?(?:递交了?|提交了?)")
_CJK_NAME_RECEIVED = re.compile(r"收到\s*([\u4e00-\u9fa5]{2,4})(?:同志)?的?\s*入党申请")
_CJK_NAME_TAIL = re.compile(r"入党申请(?:书)?[^。；]{0,10}?([\u4e00-\u9fa5]{2,4})(?=[，。；,]|$)")
_DATE_FULL = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})\s*日?")
_GENDER = re.compile(r"(女|男)(?:同志|\s|$)")
_NAME_STOPWORDS = ("党员", "管理", "支部", "申请", "发展", "纳入", "录入", "系统", "档案", "建立", "登记", "新增")


_NAME_TIME_WORDS = re.compile(r"今天|今日|昨天|昨日|刚刚|刚才|上午|下午|本月|上周|本周")


def _clean_name(candidate: str) -> str:
    name = candidate.replace("同志", "").strip().rstrip("的入")
    name = _NAME_TIME_WORDS.sub("", name).strip()
    name = re.sub(r"^(?:登记|记录|录入|新增|建立|缴纳|帮我|帮忙|记|请|给|把|将|为|替)+", "", name).strip()
    if not 2 <= len(name) <= 4:
        return ""
    if any(word in name for word in _NAME_STOPWORDS):
        return ""
    return name


_VERB_APPLICATION = re.compile(r"(?:递交了?|提交了?)[^。；]{0,10}入党申请")
_NAME_SKIP_UNITS = ("今天", "今日", "昨天", "昨日", "上午", "下午", "刚刚", "刚才", "同志")


def _extract_name_before_verb(goal: str) -> str:
    """从'递交/提交'动词向前回溯收集连续汉字，跳过时间词与'同志'。"""

    match = _VERB_APPLICATION.search(goal)
    if not match:
        return ""
    chars: list[str] = []
    i = match.start() - 1
    while i >= 0 and len(chars) < 4:
        ch = goal[i]
        if ch.isspace():
            i -= 1
            continue
        if not "一" <= ch <= "龥":
            break
        # 跳过时间词与'同志'（整词向前跳）
        skipped = False
        for unit in _NAME_SKIP_UNITS:
            if goal[max(0, i - len(unit) + 1) : i + 1] == unit:
                i -= len(unit)
                skipped = True
                break
        if skipped:
            continue
        if ch in "请纳入录入建立新增登记将把给已由让的地得了与和":
            break
        chars.append(ch)
        i -= 1
    name = _clean_name("".join(reversed(chars)))
    return name


def _extract_name(goal: str) -> str:
    """分层抽取申请人姓名：动词前回溯 > 于+日期间隔 > 收到式 > 句尾兜底。"""

    name = _extract_name_before_verb(goal)
    if name:
        return name
    for pattern in (_CJK_NAME_WITH_DATE, _CJK_NAME_RECEIVED, _CJK_NAME_TAIL):
        match = pattern.search(goal)
        if match:
            name = _clean_name(match.group(1))
            if name:
                return name
    return ""


def _extract_profile_params(goal: str) -> dict[str, Any]:
    """从自然语言目标中抽取发展档案创建参数。

    只抽取白名单字段；抽取不到的值按党建场景给安全默认（性别男、
    申请日期今天），最终以确认门禁页展示给用户核对，不静默写库。
    """

    text = " ".join(str(goal or "").split())
    today = utcnow().astimezone().strftime("%Y-%m-%d")
    name = _extract_name(text)
    application_date = today
    date_match = _DATE_FULL.search(text)
    if date_match:
        application_date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
    gender_match = _GENDER.search(text)
    gender = gender_match.group(1) if gender_match else "男"
    return {
        "name": name,
        "gender": gender,
        "party_committee": "",
        "party_branch": "",
        "application_date": application_date,
        "education": "",
    }


def _rule_steps(goal: str) -> list[dict[str, Any]]:
    text = goal.lower()
    steps: list[dict[str, Any]] = []

    def add(tool: str, arguments: dict[str, Any], reason: str, confidence: float = 0.88) -> None:
        contract = TOOL_REGISTRY[tool]
        safe_arguments = {
            key: (
                {k: _safe_text(v, 160) for k, v in value.items()}
                if isinstance(value, dict)
                else _safe_text(value, 160)
            )
            for key, value in arguments.items()
        }
        steps.append(
            {
                "tool": tool,
                "arguments": safe_arguments,
                "reason": reason,
                "confidence": confidence,
                "evidence": [{"source": "用户目标摘要", "digest": input_digest(goal)}],
                "risk": contract.risk,
                "requires_confirmation": contract.mutates or contract.risk == "high",
            }
        )

    if any(token in text for token in ("党委会", "会议议程", "会议记录", "三会一课", "主题党日")):
        add("business_meeting.create_draft", {"title": goal_summary(goal)}, "识别到会议或党建业务筹备目标")
        add("business_meeting.prepare_workflow", {}, "为会议生成固定筹备流程，等待负责人确认", 0.84)
    if any(token in text for token in ("台账", "表格", "导入", "xlsx", "xls", "csv", "档案")):
        add("ledger.inspect", {"target_type": "重要档案"}, "识别到台账或档案导入目标")
    if any(token in text for token in ("公文排版", "公文格式", "格式诊断", "9704")):
        add(
            "official_format.review_diagnostics",
            {"diagnostic_codes": "由本机公文排版页选择的问题码"},
            "只解释本机确定性引擎已识别的问题，不读取文档正文或直接修改 OOXML",
            0.94,
        )
    if "发展党员" in text or "入党" in text:
        profile_params = _extract_profile_params(goal)
        if profile_params["name"] and any(
            token in text for token in ("纳入", "录入", "建立", "新增", "建档", "登记")
        ):
            steps_text = text
            branch = ""
            branch_match = re.search(r"([\u4e00-\u9fa5]{2,12}党支部)", steps_text)
            if branch_match:
                branch = branch_match.group(1)
            committee_match = re.search(r"([\u4e00-\u9fa5]{2,20}?(?:党委|有限公司党委|公司党委))", steps_text)
            add(
                "party_development.create_profile",
                {
                    "name": profile_params["name"],
                    "gender": profile_params["gender"],
                    "party_committee": committee_match.group(1) if committee_match else "",
                    "party_branch": branch,
                    "application_date": profile_params["application_date"],
                    "education": "",
                },
                "识别到纳入发展党员管理目标，已抽取姓名与申请书日期，待确认后建档",
                0.88,
            )
        else:
            add("party_development.timeline", {}, "识别到发展党员时间轴或节点测算目标", 0.86)
    if any(token in text for token in ("提醒", "通知", "改期", "截止", "日期")):
        add("notifications.recalculate", {}, "识别到日期或提醒联动目标", 0.82)
    if any(token in text for token in ("协同", "主机", "设备", "入网", "重绑", "证书", "端口")):
        add("fleet.diagnose", {}, "识别到主机或协同设备诊断目标")
    if any(token in text for token in ("删除用户", "归档用户", "移交责任")):
        add("user.archive", {}, "涉及用户生命周期，必须先预览责任移交并确认", 0.9)
    if any(token in text for token in ("网络地址", "公布地址", "ip地址", "ip")):
        add("settings.network_change", {}, "涉及协同公布地址变更，必须管理员单独确认", 0.8)
    _add_extension_steps(add, text, goal)
    if not steps:
        if any(token in text for token in ("哪里", "怎么打开", "入口", "进入")):
            add("navigation.find", {"target": goal_summary(goal)}, "定位功能入口")
        else:
            add("work.search", {"query": goal_summary(goal)}, "使用工作台范围内的只读查询")
    return steps


_EXTENSION_RESOURCE_RULES: tuple[tuple[tuple[str, ...], str, dict[str, str]], ...] = (
    (("党费", "缴纳党费", "缴费"), "fees", {"kind": "income", "status": "已缴", "method": "转账"}),
    (("民主评议", "评议党员"), "reviews", {"status": "已完成"}),
    (("考核指标", "责任制考核", "考核项"), "indicators", {}),
    (("工会活动", "团委活动", "团日活动", "文体活动", "联谊", "活动"), "activities", {"status": "已举办"}),
    (("团员", "入团"), "league-members", {"status": "在册"}),
    (("换届", "团支部换届"), "elections", {"approval_status": "待报批"}),
    (("品牌", ), "brands", {"status": "培育中"}),
    (("舆情", ), "opinions", {"status": "登记"}),
    (("标准化", "对标自查", "规范化自查"), "checks", {"compliant": "达标"}),
    (("培训", "读书班", "轮训"), "trainings", {}),
)


def _quoted_title(goal: str) -> str:
    for pattern in ("《([^《》]{2,40})》", "[“”‘’\"']([^“”]{2,40})[“”‘’\"']"):
        match = re.search(pattern, goal)
        if match:
            return match.group(1).strip()
    prefix = re.search(r"([一-龥A-Za-z0-9]{2,20})(?=活动|品牌|读书班|轮训|培训|台账)", goal)
    if prefix:
        return prefix.group(1)
    return ""


def _add_extension_steps(add, text: str, goal: str) -> None:
    """党务扩展台账的语言登记入口：每类资源一条可确认的写入步骤。"""

    for tokens, resource, defaults in _EXTENSION_RESOURCE_RULES:
        if not any(token in text for token in tokens):
            continue
        values: dict[str, Any] = dict(defaults)
        title = _quoted_title(goal)
        if resource in {"activities", "brands", "trainings", "opinions", "indicators"}:
            values["title"] = title or _safe_text(goal, 60)
        if resource == "opinions":
            values.pop("title", None)
            values["title"] = title or _safe_text(goal, 60)
        amount = (re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块钱)", goal)
                  or re.search(r"(\d+(?:\.\d+)?)\s*党费", goal))
        if amount and resource == "fees":
            values["amount"] = amount.group(1)
        month_match = re.search(r"(\d{1,2})\s*月", goal)
        if month_match and resource == "fees":
            values["month"] = month_match.group(1)
            values["year"] = str(utcnow().astimezone().year)
        participants = re.search(r"(\d{1,4})\s*(?:人|名(?:党员|团员|职工))", goal)
        if participants and resource == "trainings":
            values["participants"] = participants.group(1)
        hours = re.search(r"(\d+(?:\.\d+)?)\s*(?:个?学时|课时)", goal)
        if hours and resource == "trainings":
            values["hours"] = hours.group(1)
        if resource in {"fees", "members", "league-members", "reviews"}:
            person = _extract_name_before_verb(goal) or ""
            if not person:
                received = re.search(r"收到(?:团员|党员)?\s*([一-龥]{2,4})(?:同志)?的?", goal)
                if received:
                    person = _clean_name(received.group(1))
            if not person:
                pay = re.search(r"([一-龥]{2,4})(?:同志)?\s*(?:缴纳|交了|缴)", goal)
                if pay:
                    person = _clean_name(pay.group(1))
            if not person:
                monthly = re.search(r"([一-龥]{2,4})的?\s*\d{1,2}\s*月\s*党费", goal)
                if monthly:
                    person = _clean_name(monthly.group(1))
            if not person:
                direct = re.search(r"([一-龥]{2,4})的?党费", goal)
                if direct:
                    person = _clean_name(direct.group(1))
            if not person:
                leading = re.search(r"(?:录入|登记|记录)\s*([一-龥]{2,4})\s*\d", goal)
                if leading:
                    person = _clean_name(leading.group(1))
            if person:
                key = "name" if resource in {"members", "league-members", "reviews"} else "member_name"
                values[key] = person
        add("extension.create_record", {"resource": resource, "values": values},
            f"识别到{resource}登记目标，参数已按模板填充，待确认后写入台账", 0.84)
    return


def _extract_json(text: str) -> dict[str, Any] | None:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE | re.DOTALL)
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        match = re.search(r"\{.*\}", value, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    return parsed if isinstance(parsed, dict) else None


def _validate_model_plan(payload: dict[str, Any], goal: str) -> list[dict[str, Any]] | None:
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps or len(raw_steps) > 20:
        return None
    result: list[dict[str, Any]] = []
    for raw in raw_steps:
        if not isinstance(raw, dict):
            return None
        name = raw.get("tool")
        contract = TOOL_REGISTRY.get(str(name))
        arguments = raw.get("arguments", {})
        if contract is None or not isinstance(arguments, dict):
            return None
        if set(arguments) - contract.argument_keys or _DANGEROUS_MARKERS.search(json.dumps(arguments, ensure_ascii=False)):
            return None
        safe_arguments = {key: _safe_text(value, 160) for key, value in arguments.items() if value is not None}
        try:
            confidence = float(raw.get("confidence", 0.0))
        except (TypeError, ValueError):
            return None
        if not 0 <= confidence <= 1 or confidence < 0.65:
            return None
        result.append(
            {
                "tool": contract.name,
                "arguments": safe_arguments,
                "reason": _safe_text(raw.get("reason", "模型建议的结构化步骤"), 240),
                "confidence": confidence,
                "evidence": [{"source": "用户目标摘要", "digest": input_digest(goal)}],
                "risk": contract.risk,
                "requires_confirmation": contract.mutates or contract.risk == "high",
            }
        )
    return result


def _signed_qwen_fallback(db: Session) -> AIModelPack | None:
    """查找已安装且验签通过的 Qwen3 0.6B 系统回退包。

    该包只会在已启用的主模型明确失败后使用；未签名、损坏、架构不符或
    管理员已卸载的包都不会被自动加载。
    """

    packs = db.scalars(
        select(AIModelPack).where(
            AIModelPack.model_id.in_(("qwen3-0.6b-q8_0", "qwen3-0.6b-gguf", "qwen3-0.6b")),
            AIModelPack.signature_valid.is_(True),
            AIModelPack.status.in_((ModelPackStatus.INSTALLED, ModelPackStatus.ACTIVE)),
        )
    ).all()
    for pack in packs:
        if "llm" in (pack.capabilities or []) and verify_installed_pack(pack):
            return pack
    return None


def build_plan(db: Session, user: User, goal: str, scope: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """优先使用 DeepSeek 规划，失败或不可用时安全回退到规则计划。"""

    route = preview_intent_with_needle(db, goal)
    route_flags = set(route.get("flags") or [])
    if route_flags & {"PROMPT_INJECTION", "NEGATED"}:
        # 安全路由已识别绕过/否定表达时，不再把原目标交给生成模型，也不
        # 产生任何可写步骤。用户可修改为明确、肯定的业务目标后重新规划。
        safe_step = {
            "tool": "work.search",
            "arguments": {"query": "安全路由已拦截当前请求"},
            "reason": str(route.get("clarification") or "请求未通过安全路由")[:240],
            "confidence": 1.0,
            "evidence": [{"source": "Needle 安全路由", "digest": input_digest(goal)}],
            "risk": "low",
            "requires_confirmation": False,
        }
        return {
            "model_id": "rules",
            "engine": "rules",
            "safety_router": str(route.get("engine", "rules")),
            "steps": [safe_step],
            "unresolved": [{"tool": "work.search", "reason": safe_step["reason"]}],
            "sensitive_scope": [],
            "can_execute": False,
        }

    rules = _rule_steps(goal)
    model_id = "rules"
    pack = active_model_pack(db, "llm")
    if pack and str(pack.model_id).lower().startswith(("deepseek-r1", "deepseek", "qwen3-0.6")):
        instruction = (
            "请只输出 JSON，不要 Markdown。你是 PartyOps 计划器，不能执行任何操作。\n"
            "只能从下列固定工具中选择：" + ", ".join(sorted(TOOL_REGISTRY)) + "。\n"
            "输出格式：{\"steps\":[{\"tool\":\"…\",\"arguments\":{},\"reason\":\"…\",\"confidence\":0.0}],\"unresolved\":[]}。\n"
            "所有写入、删除、归档、发送、权限、设备和网络操作必须要求确认；不得把预测当作事实。\n"
            f"用户目标：{goal_summary(goal)}"
        )
        try:
            candidate = _extract_json(complete_locally(db, instruction, []))
            validated = _validate_model_plan(candidate, goal) if candidate else None
            if validated:
                rules = validated
                model_id = str(pack.model_id)
        except Exception:
            # DeepSeek 不可用时，只允许使用已经正式验签并安装的指定低配
            # 回退包；仍失败则落到规则引擎，绝不调用外部模型。
            fallback = _signed_qwen_fallback(db)
            if fallback and fallback.id != pack.id:
                try:
                    candidate = _extract_json(llm_runtime.complete(fallback, instruction, []))
                    validated = _validate_model_plan(candidate, goal) if candidate else None
                    if validated:
                        rules = validated
                        model_id = str(fallback.model_id)
                except Exception:
                    model_id = "rules"
            else:
                model_id = "rules"
    unresolved = []
    for item in rules:
        if item["requires_confirmation"]:
            unresolved.append({"tool": item["tool"], "reason": "执行前需要用户确认并重新校验权限"})
    return {
        "model_id": model_id,
        "engine": (
            "deepseek"
            if model_id.lower().startswith("deepseek")
            else "qwen"
            if model_id.lower().startswith("qwen")
            else "rules"
        ),
        "safety_router": str(route.get("engine", "rules")),
        "steps": rules,
        "unresolved": unresolved,
        "sensitive_scope": [key for key in sanitize_scope(scope) if key in {"file_ids", "case_ids", "archive_ids"}],
        "can_execute": False,
    }


def active_planner_info(db: Session) -> dict[str, Any]:
    pack = active_model_pack(db, "llm")
    if pack and str(pack.model_id).lower().startswith("deepseek"):
        return {"model_id": pack.model_id, "role": "主编排模型", "state": "active"}
    if pack and str(pack.model_id).lower().startswith(("qwen3-0.6", "qwen3_0.6")):
        return {"model_id": pack.model_id, "role": "低配回退模型", "state": "active"}
    return {"model_id": "rules", "role": "规则编排引擎", "state": "fallback"}


def get_owned_step(db: Session, session_id: str, step_id: str, user: User) -> tuple[Any, AIOrchestrationStep]:
    from .models import AIOrchestrationSession

    session = db.get(AIOrchestrationSession, session_id)
    step = db.get(AIOrchestrationStep, step_id)
    if not session or session.user_id != user.id or not step or step.session_id != session.id:
        raise ProblemException(404, "AI_ORCHESTRATION_NOT_FOUND", "编排会话不存在", "请刷新后重试。")
    return session, step


def ensure_session_active(session: Any) -> None:
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        # SQLite DateTime 列不保留时区；本项目内部约定无时区值为 UTC。
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= utcnow():
        session.state = "expired"
        raise ProblemException(410, "AI_ORCHESTRATION_EXPIRED", "编排会话已过期", "请重新描述目标生成计划。")
    if session.state in {"cancelled", "completed", "failed", "expired"}:
        raise ProblemException(409, "AI_ORCHESTRATION_CLOSED", "编排会话已结束", "请重新规划或查看审计记录。")


_BUSINESS_HANDOFFS: dict[str, dict[str, str]] = {
    "business_meeting.create_draft": {"route": "/business-meetings", "label": "打开会议草稿"},
    "business_meeting.prepare_workflow": {"route": "/business-meetings", "label": "打开会议筹备流程"},
    "ledger.commit": {"route": "/archives", "label": "打开台账导入"},
    "party_development.timeline": {"route": "/party-development?tab=cases", "label": "打开发展党员时间轴"},
    "party_development.create_profile": {"route": "/party-development?tab=cases", "label": "打开发展党员时间轴"},
    "notifications.recalculate": {"route": "/notifications", "label": "打开通知重算"},
    "fleet.rebind": {"route": "/fleet/devices", "label": "打开设备重绑"},
    "user.archive": {"route": "/settings/updates?tab=users", "label": "打开用户归档"},
    "user.delete": {"route": "/settings/updates?tab=users", "label": "打开用户生命周期"},
    "settings.network_change": {"route": "/fleet/grants", "label": "打开网络与协同"},
}


def dispatch_step(
    step: AIOrchestrationStep,
    contract: ToolContract,
    db: Session | None = None,
    user: User | None = None,
    request: Any = None,
) -> dict[str, Any]:
    """固定工具的安全执行边界。

    默认策略：写操作不在模型进程中执行，而是生成固定、同源的业务办理
    入口；用户进入对应页面后仍需接受该模块自己的权限、版本、参数与二
    次确认校验。

    例外：标记者（如 party_development.create_profile）在用户已通过编
    排确认门禁后，由服务端既有业务函数完成写入——模型只产出白名单内
    的结构化参数，落库仍走权限、校验与审计，全程留痕。
    """

    if contract.mutates and contract.name == "party_development.create_profile":
        return _execute_create_profile(step, contract, db, user, request)
    if contract.mutates and contract.name == "extension.create_record":
        return _execute_extension_record(step, contract, db, user, request)
    if contract.mutates:
        handoff = _BUSINESS_HANDOFFS[contract.name]
        return {
            "status": "action_required",
            "tool": contract.name,
            "preview_only": True,
            "handoff": handoff,
            "message": "已通过编排器确认门禁；请在对应业务页面核对并完成实际写入。",
        }
    if contract.name == "official_format.review_diagnostics":
        return {
            "status": "completed",
            "tool": contract.name,
            "preview_only": True,
            "message": "已生成排版复核路线；国家标准参数和 OOXML 写入仍由本机确定性引擎裁决。",
            "review_policy": {
                "allowed_context": ["问题码", "候选角色", "置信度", "标准条款"],
                "forbidden_context": ["原文件", "文件路径", "完整正文", "临时副本"],
                "uncertain_action": "保留原段落并要求人工确认",
            },
        }
    return {"status": "completed", "tool": contract.name, "preview_only": False}


def _commit_with_retry(db: Session, attempts: int = 5) -> None:
    """SQLite 写锁竞争（如启动自检窗口）时短暂退避后重试提交。"""

    import time

    from sqlalchemy.exc import OperationalError

    for attempt in range(attempts):
        try:
            db.commit()
            return
        except OperationalError as exc:
            if "database is locked" not in str(exc).lower() or attempt == attempts - 1:
                raise
            time.sleep(0.6 * (attempt + 1))


def _execute_create_profile(
    step: AIOrchestrationStep,
    contract: ToolContract,
    db: Session | None,
    user: User | None,
    request: Any,
) -> dict[str, Any]:
    """确认门禁通过后，调用发展党员模块的既有创建逻辑直接建档。"""

    if db is None or user is None:
        return {
            "status": "action_required",
            "tool": contract.name,
            "preview_only": True,
            "handoff": _BUSINESS_HANDOFFS[contract.name],
            "message": "缺少执行上下文，请进入业务页面手动建档。",
        }
    from datetime import date

    from .party_development import ensure_reference_plan_profile, rule_metadata
    from .routers.party_development import _apply_reference_plan, _as_datetime, beijing_iso
    from .models import PartyDevelopmentCase
    from .audit import write_audit
    from .routers.router_utils import client_ip

    args = step.arguments or {}
    name = str(args.get("name") or "").strip()
    application_date = str(args.get("application_date") or "").strip()
    if not name or not application_date:
        return {
            "status": "failed",
            "tool": contract.name,
            "preview_only": True,
            "message": "参数不完整：需要姓名与申请书日期。",
        }
    # 幂等：同支部同名且申请书日期相同的档案不重复创建。
    existing = db.scalars(
        select(PartyDevelopmentCase).where(
            PartyDevelopmentCase.name == name,
            PartyDevelopmentCase.status == "active",
        )
    ).all()
    for item in existing:
        if item.application_at and item.application_at.strftime("%Y-%m-%d") == application_date:
            return {
                "status": "completed",
                "tool": contract.name,
                "preview_only": False,
                "message": f"已存在同名且同申请日期的发展档案，未重复创建。",
                "case_id": item.id,
                "handoff": _BUSINESS_HANDOFFS[contract.name],
            }
    profile = ensure_reference_plan_profile(db, user)
    snapshot = {
        "system_key": profile.system_key,
        "name": profile.name,
        "version": profile.version,
        "assumptions": dict(profile.assumptions),
        "captured_at": beijing_iso(utcnow()),
    }
    item = PartyDevelopmentCase(
        party_committee=str(args.get("party_committee") or "").strip(),
        party_branch=str(args.get("party_branch") or "").strip(),
        name=name,
        gender=str(args.get("gender") or "男").strip() or "男",
        ethnicity="汉族",
        birth_date=None,
        education=str(args.get("education") or "").strip(),
        application_at=_as_datetime(date.fromisoformat(application_date)),
        activist_at=None,
        training_contacts=[],
        introducers=[],
        development_object_at=None,
        probationary_at=None,
        converted_at=None,
        rule_version=str(rule_metadata()["version"]),
        planning_profile_id=profile.id,
        planning_profile_snapshot=snapshot,
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    _apply_reference_plan(db, item, bump_case_version=False)
    write_audit(
        db,
        user,
        "ai.party_development.create_profile",
        "party_development_case",
        item.id,
        {"name": name, "application_date": application_date, "via": "ai_orchestrator"},
        client_ip(request) if request else "",
    )
    _commit_with_retry(db)
    return {
        "status": "completed",
        "tool": contract.name,
        "preview_only": False,
        "message": f"已创建「{name}」的发展党员档案（申请书 {application_date}），参考计划已生成。",
        "case_id": item.id,
        "handoff": _BUSINESS_HANDOFFS[contract.name],
    }


_EXTENSION_RESOURCE_ALIASES: dict[str, str] = {
    "fees": "fees", "reviews": "reviews", "indicators": "indicators",
    "activities": "activities", "league-members": "league-members",
    "elections": "elections", "brands": "brands", "opinions": "opinions",
    "checks": "checks", "trainings": "trainings", "members": "members",
}


def _execute_extension_record(
    step: AIOrchestrationStep,
    contract: ToolContract,
    db: Session | None,
    user: User | None,
    request: Any,
) -> dict[str, Any]:
    """确认门禁通过后，向党务扩展台账写入一条记录（服务端校验+审计）。"""

    from .routers.extension import RESOURCES, _apply
    from .audit import write_audit
    from .routers.router_utils import client_ip

    if db is None or user is None:
        return {
            "status": "action_required",
            "tool": contract.name,
            "preview_only": True,
            "handoff": {"route": "/party-members", "label": "打开党务台账"},
            "message": "缺少执行上下文，请进入业务页面手动登记。",
        }
    args = step.arguments or {}
    resource = str(args.get("resource") or "").strip()
    values = args.get("values") if isinstance(args.get("values"), dict) else {}
    spec = RESOURCES.get(_EXTENSION_RESOURCE_ALIASES.get(resource, ""))
    if not spec or not values:
        return {
            "status": "failed",
            "tool": contract.name,
            "preview_only": True,
            "message": "参数不完整：资源类型或登记内容缺失。",
        }
    # 数字字段安全转换；文本字段过 _safe_text
    cleaned: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, (int, float)):
            cleaned[key] = value
        elif isinstance(value, str) and value.strip():
            cleaned[key] = _safe_text(value, 200)
    _title_fields = {
        "activities": "title", "brands": "title", "trainings": "title",
        "opinions": "title", "indicators": "title", "fees": "member_name",
        "members": "name", "league-members": "name", "reviews": "member_name",
        "checks": "item", "elections": "branch",
    }
    title_field = _title_fields.get(resource, spec["text_fields"][0])
    if not str(cleaned.get(title_field, "")).strip():
        return {
            "status": "failed",
            "tool": contract.name,
            "preview_only": True,
            "message": "参数不完整：请在指令中写明人员姓名或事项标题。",
        }
    model = spec["model"]
    # NOT NULL 且无默认值的字符串/数值列补安全默认，避免指令未提及时 500。
    from sqlalchemy import Numeric, String, Text as SAText

    for column in model.__table__.columns:
        if column.name in cleaned or column.nullable or column.server_default is not None:
            continue
        if isinstance(column.type, (String, SAText)):
            cleaned[column.name] = ""
        elif isinstance(column.type, Numeric):
            cleaned[column.name] = 0
        elif isinstance(column.type.__class__, type) and "Integer" in column.type.__class__.__name__:
            cleaned[column.name] = 0
    obj = model(created_by=user.id)
    _apply(spec, obj, cleaned, partial=False)
    db.add(obj)
    db.flush()
    write_audit(
        db, user, "ai.extension.create_record", model.__tablename__, obj.id,
        {"resource": resource, "via": "ai_orchestrator"}, client_ip(request) if request else "",
    )
    _commit_with_retry(db)
    first_text = str(cleaned.get(spec["text_fields"][0], ""))[:30]
    return {
        "status": "completed",
        "tool": contract.name,
        "preview_only": False,
        "message": f"已在「{resource}」台账登记一条记录：{first_text}",
        "record_id": obj.id,
        "handoff": {"route": "/party-members", "label": "打开党务台账"},
    }


__all__ = [
    "TOOL_REGISTRY",
    "ToolContract",
    "active_planner_info",
    "build_plan",
    "dispatch_step",
    "ensure_session_active",
    "get_owned_step",
    "goal_summary",
    "input_digest",
    "sanitize_scope",
    "step_scope_digest",
    "tool_contracts",
]
