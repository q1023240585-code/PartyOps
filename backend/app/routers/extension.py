"""党务扩展模块：党员队伍、党费、考核评议、群团、品牌舆情、标准化对标、教育培训。

通用台账接口：每资源提供列表（可过滤）、创建、更新、删除与少量统计，
遵循既有审计字段与乐观版本约定。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Type

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_session
from ..models import (
    AssessmentIndicator,
    AssessmentScore,
    BrandProject,
    DemocraticReview,
    LeagueElection,
    LeagueMember,
    MassActivity,
    PartyFeeRecord,
    PartyMember,
    PublicOpinionItem,
    StandardCheckItem,
    TrainingRecord,
    User,
    utcnow,
)
from ..problems import ProblemException
from ..security import get_current_user
from .router_utils import client_ip, parse_if_match

router = APIRouter(tags=["extension"])

RESOURCES: dict[str, dict[str, Any]] = {
    "members": {
        "model": PartyMember,
        "audit": "extension.member",
        "text_fields": ("name", "gender", "branch", "party_post", "education", "phone", "member_kind", "status", "notes"),
        "date_fields": ("birth_date", "joined_party_at"),
    },
    "fees": {
        "model": PartyFeeRecord,
        "audit": "extension.fee",
        "text_fields": ("kind", "member_name", "branch", "status", "method", "purpose", "approver", "notes"),
        "date_fields": ("paid_at",),
        "float_fields": ("base_amount", "ratio", "amount"),
        "int_fields": ("year", "month"),
    },
    "reviews": {
        "model": DemocraticReview,
        "audit": "extension.review",
        "text_fields": ("member_name", "branch", "self_rating", "peer_rating", "final_rating", "issues_found", "rectification", "status", "notes"),
        "int_fields": ("year",),
    },
    "indicators": {
        "model": AssessmentIndicator,
        "audit": "extension.indicator",
        "text_fields": ("category", "title", "owner_role", "description"),
        "float_fields": ("score",),
        "int_fields": ("year",),
    },
    "scores": {
        "model": AssessmentScore,
        "audit": "extension.score",
        "text_fields": ("branch", "evidence", "assessor", "notes"),
        "float_fields": ("score_obtained",),
        "int_fields": ("year",),
        "fk_fields": {"indicator_ref": AssessmentIndicator},
    },
    "activities": {
        "model": MassActivity,
        "audit": "extension.activity",
        "text_fields": ("kind", "title", "location", "organizer", "summary", "status", "notes"),
        "date_fields": ("held_at",),
        "float_fields": ("budget",),
        "int_fields": ("participants",),
    },
    "league-members": {
        "model": LeagueMember,
        "audit": "extension.league-member",
        "text_fields": ("name", "gender", "branch", "league_post", "education", "status", "notes"),
        "date_fields": ("birth_date", "league_joined_at"),
    },
    "elections": {
        "model": LeagueElection,
        "audit": "extension.election",
        "text_fields": ("branch", "term", "new_secretary", "committee", "approval_status", "notes"),
        "date_fields": ("election_date",),
    },
    "brands": {
        "model": BrandProject,
        "audit": "extension.brand",
        "text_fields": ("title", "category", "slogan", "description", "status", "highlights", "owner", "notes"),
        "date_fields": ("started_at",),
    },
    "opinions": {
        "model": PublicOpinionItem,
        "audit": "extension.opinion",
        "text_fields": ("title", "source", "severity", "summary", "disposition", "status", "responder", "notes"),
        "date_fields": ("occurred_at",),
    },
    "checks": {
        "model": StandardCheckItem,
        "audit": "extension.check",
        "text_fields": ("branch", "category", "item", "requirement", "compliant", "evidence", "notes"),
        "date_fields": ("checked_at",),
    },
    "trainings": {
        "model": TrainingRecord,
        "audit": "extension.training",
        "text_fields": ("title", "category", "branch", "summary", "notes"),
        "date_fields": ("start_date", "end_date"),
        "float_fields": ("hours",),
        "int_fields": ("participants",),
    },
}


class ExtensionPayload(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


def _resource(name: str) -> dict[str, Any]:
    spec = RESOURCES.get(name)
    if not spec:
        raise ProblemException(404, "EXTENSION_RESOURCE_UNKNOWN", "未知的扩展资源", "请检查接口地址。")
    return spec


def _apply(spec: dict[str, Any], obj: Any, values: dict[str, Any], *, partial: bool) -> None:
    for field in spec["text_fields"]:
        if field in values and isinstance(values[field], str):
            setattr(obj, field, values[field])
    for field in spec.get("date_fields", ()):
        value = values.get(field)
        if value is None:
            if not partial:
                setattr(obj, field, None)
            continue
        if isinstance(value, str) and value:
            setattr(obj, field, datetime.fromisoformat(value.replace("Z", "+00:00")))
    for field in spec.get("float_fields", ()):
        if field in values and values[field] not in (None, ""):
            setattr(obj, field, float(values[field]))
    for field in spec.get("int_fields", ()):
        if field in values and values[field] not in (None, ""):
            setattr(obj, field, int(values[field]))
    for field, model in spec.get("fk_fields", {}).items():
        if field in values and values[field]:
            setattr(obj, field, str(values[field]))


def _out(obj: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"id": obj.id, "version": obj.version}
    for key in dir(obj):
        if key.startswith("_") or key in data:
            continue
        try:
            value = getattr(obj, key)
        except AttributeError:
            continue
        if callable(value):
            continue
        if isinstance(value, datetime):
            data[key] = value.isoformat() if value else None
        elif value is None or isinstance(value, (str, int, float, bool)):
            data[key] = value
    return data


@router.get("/extension/{name}")
def list_items(
    name: str,
    q: str = Query(default=""),
    branch: str = Query(default=""),
    year: int = Query(default=0),
    kind: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    spec = _resource(name)
    stmt = select(spec["model"]).order_by(spec["model"].created_at.desc()).limit(limit)
    model = spec["model"]
    text_fields = spec["text_fields"]
    if q:
        first = text_fields[0]
        if hasattr(model, first):
            stmt = stmt.where(getattr(model, first).contains(q))
    if branch and hasattr(model, "branch"):
        stmt = stmt.where(model.branch == branch)
    if year and hasattr(model, "year"):
        stmt = stmt.where(model.year == year)
    if kind and hasattr(model, "kind"):
        stmt = stmt.where(model.kind == kind)
    if status and hasattr(model, "status"):
        stmt = stmt.where(model.status == status)
    rows = db.scalars(stmt).all()
    return [_out(row) for row in rows]


@router.post("/extension/{name}", status_code=201)
def create_item(
    name: str,
    payload: ExtensionPayload,
    request: Request,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    spec = _resource(name)
    obj = spec["model"](created_by=user.id)
    _apply(spec, obj, payload.values, partial=False)
    db.add(obj)
    db.flush()
    write_audit(db, user, spec["audit"] + ".create", spec["model"].__tablename__, obj.id,
                {"title": getattr(obj, spec["text_fields"][0], "")}, client_ip(request))
    db.commit()
    db.refresh(obj)
    return _out(obj)


@router.patch("/extension/{name}/{item_id}")
def update_item(
    name: str,
    item_id: str,
    payload: ExtensionPayload,
    request: Request,
    if_match: str = Depends(parse_if_match),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    spec = _resource(name)
    obj = db.get(spec["model"], item_id)
    if not obj:
        raise ProblemException(404, "EXTENSION_ITEM_NOT_FOUND", "记录不存在", "请刷新后重试。")
    if if_match is not None and int(if_match) != obj.version:
        raise ProblemException(409, "VERSION_CONFLICT", "记录已被他人更新", "请刷新后核对最新内容。")
    _apply(spec, obj, payload.values, partial=True)
    obj.version = obj.version + 1
    db.flush()
    write_audit(db, user, spec["audit"] + ".update", spec["model"].__tablename__, obj.id,
                {"version": obj.version}, client_ip(request))
    db.commit()
    db.refresh(obj)
    return _out(obj)


@router.delete("/extension/{name}/{item_id}", status_code=204)
def delete_item(
    name: str,
    item_id: str,
    request: Request,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    spec = _resource(name)
    obj = db.get(spec["model"], item_id)
    if not obj:
        raise ProblemException(404, "EXTENSION_ITEM_NOT_FOUND", "记录不存在", "请刷新后重试。")
    write_audit(db, user, spec["audit"] + ".delete", spec["model"].__tablename__, obj.id, None, client_ip(request))
    db.delete(obj)
    db.commit()


@router.get("/extension/{name}/summary")
def summary(
    name: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    spec = _resource(name)
    model = spec["model"]
    total = db.scalar(select(func.count()).select_from(model)) or 0
    result: dict[str, Any] = {"total": total}
    if hasattr(model, "status"):
        rows = db.execute(select(model.status, func.count()).group_by(model.status)).all()
        result["by_status"] = {row[0]: row[1] for row in rows}
        for key, count in result["by_status"].items():
            result[str(key)] = count
    if hasattr(model, "branch"):
        rows = db.execute(select(model.branch, func.count()).group_by(model.branch)).all()
        result["by_branch"] = {row[0]: row[1] for row in rows}
    if hasattr(model, "kind") and hasattr(model, "status"):
        pass
    if name == "members":
        kinds = db.execute(select(PartyMember.member_kind, func.count()).group_by(PartyMember.member_kind)).all()
        for row in kinds:
            result[str(row[0])] = row[1]
    if name == "fees":
        income = db.scalar(
            select(func.coalesce(func.sum(PartyFeeRecord.amount), 0)).where(PartyFeeRecord.kind == "income")
        ) or 0
        expense = db.scalar(
            select(func.coalesce(func.sum(PartyFeeRecord.amount), 0)).where(PartyFeeRecord.kind == "expense")
        ) or 0
        unpaid = db.scalar(
            select(func.count()).select_from(PartyFeeRecord).where(PartyFeeRecord.kind == "income", PartyFeeRecord.status != "已缴")
        ) or 0
        result.update({"income_total": float(income), "expense_total": float(expense), "unpaid": unpaid})
    if name == "members":
        kinds = db.execute(select(PartyMember.member_kind, func.count()).group_by(PartyMember.member_kind)).all()
        result["by_kind"] = {row[0]: row[1] for row in kinds}
        for row in kinds:
            result[str(row[0])] = row[1]
    if name == "trainings":
        hours = db.scalar(select(func.coalesce(func.sum(TrainingRecord.hours), 0))) or 0
        people = db.scalar(select(func.coalesce(func.sum(TrainingRecord.participants), 0))) or 0
        result.update({"hours_total": float(hours), "participants_total": int(people)})
    return result
