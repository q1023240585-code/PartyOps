# PartyPlatform（党建智能体）交接文档

> 交接日期：2026-10-27
> 仓库：https://github.com/q1023240585-code/PartyOps （fork 自 linsky-dev/PartyOps，定制改动都在 main 分支）
> 交接人留下的运行包：`PartyPlatform-share.zip`（158MB，见文末）

---

## 一、这是什么

面向中核四〇四有限公司的基层党建协同平台，基于开源项目 PartyOps v1.4.5-rc.6 二次开发，更名 **PartyPlatform / 党建智能体**。本地优先架构：一台主机跑服务（FastAPI + SQLite），浏览器访问，数据不出内网。

**技术上：后端 Python 3.11-3.13（FastAPI + SQLAlchemy 2 + Alembic），前端 Vue 3.5 + Pinia + Arco Design Vue + Vite。**

## 二、十五项功能现状（全部可用）

| # | 功能 | 模块入口 | 来源 |
|---|---|---|---|
| 1 | 党员发展全流程 | 发展党员（时间轴/2026细则计算/一人一档） | 原生 |
| 2 | 党员教育管理 | 党员队伍 → 教育培训 | 二开 |
| 3 | 支部标准化建设 | 考核评议 → 支部标准化对标 | 二开 |
| 4 | 三会一课与主题党日 | 三会一课（8 种会议类型） | 原生 |
| 5 | 组织生活会与民主评议 | 组织生活会 + 考核评议 → 民主评议 | 原生+二开 |
| 6 | 党费收缴使用 | 党费管理（收缴/使用双台账+汇总） | 二开 |
| 7 | 党内统计与党员信息 | 党员队伍 → 党员名册 | 二开 |
| 8 | 党建责任制考核 | 考核评议 → 责任制考核 | 二开 |
| 9 | 党务文书起草审核 | 公文排版（GB/T 9704）+ 在线文档 + AI 草稿 | 原生 |
| 10 | 宣传与思政策划 | AI 草稿线 + 事项跟踪 | 原生（借力） |
| 11 | 舆情监测 | 宣传文化 → 舆情台账（登记/处置闭环） | 二开 |
| 12 | 工会活动策划 | 群团工作 → 工会活动 | 二开 |
| 13 | 团组织换届 | 群团工作 → 团组织换届 | 二开 |
| 14 | 团员管理 | 群团工作 → 团员名册 | 二开 |
| 15 | 文化品牌 | 宣传文化 → 文化品牌 | 二开 |

## 三、怎么跑起来

### 分享包（给使用者）
解压 `PartyPlatform-share.zip` → 装 Python 3.12（勾 Add to PATH）→ 双击 `start-partyplatform.bat`。首跑自动建环境装依赖，自动开浏览器。**管理员：admin / Zhonghe404@2026**（正式启用删 `partyops-data` 文件夹重新初始化）。

### 开发模式（给接手的开发者）
```bat
git clone https://github.com/q1023240585-code/PartyOps.git && cd PartyOps
:: 后端
cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
set PARTYOPS_ENVIRONMENT=development
set PARTYOPS_DATA_DIR=D:\partyops-data
.venv\Scripts\python -m app.main
:: 前端（另开终端；改前端后需重新构建）
cd frontend && pnpm install && pnpm build
```
访问 http://127.0.0.1:18765/ 。后端直接伺服 `frontend/dist/client`（生产形态，同源）。改前端后 `pnpm build` 刷新即生效；改后端后重启进程。注意：**vite dev 模式（pnpm dev）只能看界面，初始化/登录会被 CSRF 同源检查拦截**，联调一律走构建+同源。

## 四、定制改动清单（相对上游 rc.6，19 个 commit）

1. **党建红主题**：`--cinnabar #b42318→#c7000b`、深红 #980008、新增 `--gold #c9a227`；29 个文件旧红字面量清零
2. **品牌更名**：「党建智办→党建智能体」（48 处）；「PartyOps→PartyPlatform」（374 处，大小写敏感——**小写 `partyops_*` cookie/存储键与全大写 `PARTYOPS_` 环境变量前缀是跨层契约，刻意未改，改了会坏登录和数据**）
3. **核城主题视觉**：登录页纪念塔水墨画（真实照片经 qwen-image 风格迁移）+ 嘉峪关/胡杨照片水印层；14 个内页页头画卷 + 四季底部长卷全部换成党建红戈壁意象（经 `data-scene`/`data-season` CSS 变量接入，见 `styles.css`）
4. **党务扩展模块**（二开核心）：
   - `backend/app/models.py` 末尾 12 张表（党员名册/党费/民主评议/考核指标+评分/群团活动/团员/换届/品牌/舆情/标准化自查/培训）
   - `backend/alembic/versions/0027_extension_modules.py` 迁移（启动自动跑）
   - `backend/app/routers/extension.py`：**表驱动通用 CRUD**——加新台账只需在 `RESOURCES` 注册（text/date/float/int 字段组），自动获得列表/创建/更新/删除/summary 五个接口
5. **AI 执行能力**（见下节）
6. **提示词案例库**：`frontend/src/promptLibrary.ts`（31 条现成提示词）+ AI 助手页案例库区块（填入/复制），27 条执行线提示词逐条实测通过
7. 登录页布局修复（长副标题换行/窄屏单列/中文断词 keep-all/影像分区防重影）

## 五、AI 助手执行能力（重要设计）

**三层受控架构**：DeepSeek 只做规划（出计划不执行）→ Needle 2 做安全路由（提示注入/越权检测）→ BGE 做中文检索（只喂授权最小片段）。**模型不能直接访问数据库、文件系统或网络。**

执行链：用户输入 → `build_plan`（规则引擎 `_rule_steps` 关键词路由 + 参数抽取）→ 用户逐项确认（approve 带 scope_sha256 防调包）→ `execute` 时 `dispatch_step` 真正落库（写操作走服务函数 + 审计 + 幂等防重）。

**当前可落库工具**（`ai_orchestrator.py` TOOL_REGISTRY）：
- `party_development.create_profile`：从自然语言抽姓名/性别/申请书日期建档（动词前向回溯抽取算法）
- `extension.create_record`：通用 10 类台账登记（党费/评议/指标/活动/团员/换届/品牌/舆情/对标/培训）

**如何加新的可执行工具**：① TOOL_REGISTRY 注册契约 → ② `_rule_steps` 加触发词与参数抽取 → ③ `dispatch_step` 加真实写入分支（复用对应 router 的服务函数，写 `write_audit`）。其余写工具默认行为是"生成业务页面跳转链接"（handoff），不落库——这是原厂安全边界，改造时保留。

AI provider 配置走 `PATCH /api/v1/ai/settings`（需管理员 + If-Match 版本头），当前配 DeepSeek（deepseek-v4-flash，key 加密存库）。

## 六、已知坑（接手必读）

1. **Arco 表格列必须包在 `<template #columns>`**，直接子组件写法不报错但 0 行
2. **验收数据必须查 DOM**（`document.querySelectorAll('.arco-table-td').length`），视觉/截图会被统计条误导
3. 全局 `html/body/#app min-width:1180px` 是桌面锁，登录页有 `:has(.login-screen)` 例外，别扩大
4. 同层 multiply 影像**绝不叠印**（重影），多图分区 + mask 羽化
5. Windows bat 必须**纯 ASCII + CRLF**（UTF-8 BOM 会乱码）；Python 字符串写 Windows 路径用 r-string
6. SQLite 写锁：执行器已带 commit 重试；步骤失败会 rollback 并传播 failed（别吞）
7. 后端启动头几秒有写锁窗口，脚本化 E2E 每场景间隔 ≥1.5s
8. `rename_files.txt`/`server.log` 等杂物别提交进仓库
9. **上游同步策略**：上游极活跃（月更多个 RC），建议锁 rc.6 基线只挑安全修复 cherry-pick，不要追 merge
10. **许可**：GPL-3.0——内网自用无义务；对外分发须整体开源

## 七、遗留事项（按优先级）

1. **司徽/logo**：登录页与侧栏仍用文字品牌，待官方 VI 素材替换（AI 已出过渡水墨版）
2. **舆情"监测"**：现在是登记处置台账，真正的自动监测需接外部舆情 SaaS 或自建爬虫（需求方未拍板）
3. **一键启动**：分享包已有 bat；如需注册成 Windows 服务开机自启，用 NSSM 包一层即可
4. **民主评议得分统计图表**、**党费年度汇总报表导出**：台账已就绪，报表是下一步增值项
5. **前端测试**：新增模块未写 Vitest 用例（原厂 182 个测试文件是范本）；`pnpm build` 已含 vue-tsc 类型检查兜底
6. **正式启用前**：删演示数据（删 `partyops-data` 重新初始化）、改默认管理员密码、AI key 换成单位自己的、检查 GPL 分发义务

## 八、关键文件索引

| 路径 | 内容 |
|---|---|
| `backend/app/routers/extension.py` | 扩展台账通用 CRUD（RESOURCES 注册表） |
| `backend/app/ai_orchestrator.py` | AI 编排器（工具契约/参数抽取/执行边界） |
| `frontend/src/components/ExtensionLedger.vue` | 通用台账组件（表格+弹窗+统计） |
| `frontend/src/promptLibrary.ts` | 提示词案例库数据（31 条） |
| `frontend/src/navigation.ts` | 侧栏导航（党务域 9 项） |
| `frontend/src/styles.css` | 主题变量 + 场景画卷接入（:root 顶部） |
| `backend/alembic/versions/0027_*` | 扩展表迁移 |
| `start-partyplatform.bat` | 一键启动（分享包内；开发机用 uvicorn 直启） |

## 九、日常运维速查

- 启动：双击 `start-partyplatform.bat`（或 backend 下 `python -m app.main`，带 `PARTYOPS_DATA_DIR`）
- 日志：`server.log`（bat 启动时重定向）
- 备份：管理域 → 备份恢复（系统内置）；或直接停服务拷 `partyops-data`
- 重置演示：停服务 → 删 `partyops-data` → 重启 → 走初始化向导
- 改 AI 供应商：管理域 → AI 与权限（或 `PATCH /api/v1/ai/settings`）
