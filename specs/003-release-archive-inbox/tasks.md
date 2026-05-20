# 任务清单：发布可靠性、归档中心与收件箱增强

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本任务清单必须使用中文撰写并归档。

**输入**：来自 `specs/003-release-archive-inbox/` 的设计文档  
**前置条件**：`plan.md`、`spec.md`、`research.md`、`data-model.md`、`contracts/release-archive-inbox-contract.md`、`quickstart.md`  
**状态**：待用户审阅；用户确认前不得进入代码实现。

**测试要求**：本功能涉及部署版本状态、PWA 缓存、归档恢复、账号隔离、records 重试和批量处理，必须包含自动化测试；浏览器缓存和移动端布局用人工浏览器验收补充。

## Phase 1：准备工作（共享基础）

**目的**：确认当前实现边界和本轮文档范围，避免开发偏离。

- [x] T001 阅读 `specs/003-release-archive-inbox/plan.md`、`specs/003-release-archive-inbox/spec.md` 和 `specs/003-release-archive-inbox/contracts/release-archive-inbox-contract.md`
- [x] T002 [P] 检查版本与缓存相关现状：`server.py`、`web/app.js`、`web/sw.js`
- [x] T003 [P] 检查归档相关现状：`server.py`、`tests/test_records.py`
- [x] T004 [P] 检查收件箱相关现状：`server.py`、`web/app.js`、`web/index.html`、`web/styles.css`

## Phase 2：基础设施（阻塞前置）

**目的**：补齐三个用户故事共享的后端契约、前端状态和测试基础。

- [x] T005 在 `tests/test_release.py` 中添加 `/api/version` 不缓存、版本结构稳定的后端契约测试
- [x] T006 在 `tests/test_records.py` 中添加归档查询筛选、恢复和账号隔离的测试骨架
- [x] T007 在 `tests/test_records.py` 中添加 records 来源/状态/标签筛选、重试不自动创建任务、批量处理账号隔离的测试骨架
- [x] T008 在 `web/app.js` 中梳理版本状态、归档中心状态和收件箱筛选状态的数据结构，避免与现有全局状态冲突
- [x] T009 在 `web/index.html` 中确认版本提示、归档中心和收件箱详情所需容器位置

## Phase 3：用户故事 1 - 用户确认当前页面就是最新发布版本（P1，MVP）

**目标**：用户能判断浏览器页面、Service Worker 和后端是否一致，并能安全更新到最新页面。

**独立测试**：模拟旧缓存或旧前端版本后，页面显示更新提示；触发更新后版本一致，核心数据仍可加载。

### 用户故事 1 的测试

- [x] T010 [P] [US1] 在 `tests/test_release.py` 中添加 `/api/version` 响应包含后端版本和时间字段的测试
- [x] T011 [P] [US1] 在 `tests/test_release.py` 中添加静态资源和 `sw.js` 缓存头符合更新策略的测试
- [x] T012 [US1] 使用浏览器手工记录旧缓存到新版本的更新提示验收步骤，结果写入 `specs/003-release-archive-inbox/quickstart.md`

### 用户故事 1 的实现

- [x] T013 [US1] 在 `server.py` 中确认或调整 `/api/version` 与静态资源缓存头，保证版本检测不返回陈旧结果
- [x] T014 [US1] 在 `web/sw.js` 中调整缓存版本、激活和旧缓存清理策略，避免旧资源长期占用
- [x] T015 [US1] 在 `web/app.js` 中实现前端/后端/Service Worker 版本一致性检测和更新提示状态
- [x] T016 [US1] 在 `web/index.html` 中增加版本更新提示区域或顶部状态入口
- [x] T017 [US1] 在 `web/styles.css` 中增加版本状态与更新提示样式，并保证移动端不遮挡核心操作

## Phase 4：用户故事 2 - 用户管理已完成任务归档（P1）

**目标**：用户可以查看、搜索、筛选并恢复当前账号的归档任务。

**独立测试**：完成任务后进入归档中心，搜索定位并恢复任务；另一个账号无法看到或恢复该任务。

### 用户故事 2 的测试

- [x] T018 [P] [US2] 在 `tests/test_records.py` 中添加 `GET /api/todos/archive` 支持关键字、时间和优先级筛选的测试
- [x] T019 [P] [US2] 在 `tests/test_records.py` 中添加 `POST /api/todos/{id}/restore` 恢复归档任务的测试
- [x] T020 [P] [US2] 在 `tests/test_records.py` 中添加归档查询和恢复按账号隔离的测试

### 用户故事 2 的实现

- [x] T021 [US2] 在 `server.py` 中扩展 `GET /api/todos/archive`，支持 `q`、`from`、`to`、`urgency`、`limit`、`offset` 筛选
- [x] T022 [US2] 在 `server.py` 中新增 `POST /api/todos/{id}/restore`，恢复归档任务并更新 `updated_at`
- [x] T023 [US2] 在 `server.py` 中为归档结果补充来源摘要和子任务摘要，且保持当前账号过滤
- [x] T024 [US2] 在 `web/index.html` 中增加归档中心入口、筛选控件、列表和恢复操作容器
- [x] T025 [US2] 在 `web/app.js` 中实现归档中心加载、搜索、筛选、恢复和统计刷新逻辑
- [x] T026 [US2] 在 `web/styles.css` 中实现归档中心桌面和移动端布局

## Phase 5：用户故事 3 - 用户高效审查随记收件箱（P2）

**目标**：用户能按来源、状态、标签和是否已生成任务筛选记录，查看详情，重试失败记录，并批量清理已审查记录。

**独立测试**：创建多条不同状态记录后，组合筛选结果正确；失败记录可重试；批量处理不跨账号。

### 用户故事 3 的测试

- [x] T027 [P] [US3] 在 `tests/test_records.py` 中添加 `GET /api/records` 来源、状态、标签、是否已生成任务和关键字组合筛选测试
- [x] T028 [P] [US3] 在 `tests/test_records.py` 中添加 `GET /api/records/{id}` 详情包含 AI 结果、任务草稿和关联任务的测试
- [x] T029 [P] [US3] 在 `tests/test_records.py` 中添加 `POST /api/records/{id}/retry` 不自动创建正式任务的回归测试
- [x] T030 [P] [US3] 在 `tests/test_records.py` 中添加 `POST /api/records/bulk` 批量处理与账号隔离测试

### 用户故事 3 的实现

- [x] T031 [US3] 在 `server.py` 中扩展 `GET /api/records` 筛选参数并保持当前账号隔离
- [x] T032 [US3] 在 `server.py` 中确认或补齐 `GET /api/records/{id}` 详情输出，包含 AI 结果、草稿和关联任务
- [x] T033 [US3] 在 `server.py` 中确认或调整 `POST /api/records/{id}/retry`，保证重试不创建正式任务
- [x] T034 [US3] 在 `server.py` 中新增 `POST /api/records/bulk`，支持本轮限定的批量清理动作和部分失败结果
- [x] T035 [US3] 在 `web/index.html` 中重排收件箱筛选、详情和批量操作区域
- [x] T036 [US3] 在 `web/app.js` 中实现收件箱组合筛选、详情抽屉或详情区、重试和批量处理交互
- [x] T037 [US3] 在 `web/styles.css` 中打磨收件箱列表、详情和批量操作的视觉层级

## Phase 6：打磨与横切关注点

**目的**：补齐文档、部署说明和全量验证。

- [x] T038 [P] 更新 `README.md`，说明版本状态、缓存刷新、归档中心和收件箱增强的使用方式
- [x] T039 [P] 更新 `specs/003-release-archive-inbox/quickstart.md`，记录本地和线上浏览器验收结果
- [x] T040 检查 `deploy/update-from-github.sh` 和现有服务器更新说明，记录 dirty worktree 阻塞更新时的处理策略
- [x] T041 运行 `python -m py_compile server.py feishu_client.py`
- [x] T042 运行 `python -m unittest tests/test_records.py tests/test_feishu.py tests/test_feishu_client.py tests/test_ai_organizer.py tests/test_release.py`
- [x] T043 运行 `node --check web\app.js`
- [x] T044 使用浏览器验收桌面和移动端：版本提示、归档中心、收件箱筛选详情均不遮挡、不重叠
- [ ] T045 若用户确认发布，推送 GitHub 并同步服务器；如网络不稳定，按项目约定配置自动重试任务直到成功或远端已包含目标提交

## 依赖与执行顺序

- Phase 1 无依赖，可以立即开始。
- Phase 2 依赖 Phase 1，完成前不得实现任何用户故事。
- 用户故事 1 是 MVP，优先解决发布可验证性。
- 用户故事 2 可在 Phase 2 后与用户故事 1 后半段并行，但涉及 `server.py` 时需要串行整合。
- 用户故事 3 依赖 records 现有行为，可在 Phase 2 后推进；与归档中心共享 Web 布局文件时需要避免同文件冲突。
- Phase 6 依赖计划范围内用户故事完成。

## 并行机会

- T002、T003、T004 可并行阅读不同边界。
- T010、T011 可并行编写版本相关测试。
- T018、T019、T020 可并行编写归档测试。
- T027、T028、T029、T030 可并行编写 records 测试。
- README、quickstart 和部署说明可与最后验证准备并行。

## 实施策略

1. MVP：先完成发布可靠性，确保用户能判断线上页面是否最新。
2. 增量交付：完成归档中心，补齐已完成任务可见、可查、可恢复。
3. 收件箱增强：在不改变 AI 人工确认原则的前提下补齐筛选、详情、重试和批量处理。
4. 完成定义：自动化测试通过，浏览器验收通过，文档更新完成，用户确认后再推送和部署。
