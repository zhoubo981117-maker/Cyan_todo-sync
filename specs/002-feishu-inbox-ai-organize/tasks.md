# 任务清单：飞书随记入口与 AI 收件箱统一整理

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本任务清单必须使用中文撰写并归档。

**输入**：来自 `specs/002-feishu-inbox-ai-organize/` 的设计文档  
**前置条件**：`plan.md`、`spec.md`、`research.md`、`data-model.md`、`contracts/feishu-inbox-contract.md`、`quickstart.md`

**测试要求**：本功能涉及飞书接入、AI 整理、数据迁移和共享后端行为，必须包含自动化测试。  
**组织方式**：任务按用户故事分组，确保每个故事可以独立实现、独立测试和独立演示。

## Phase 1：准备工作（共享基础）

**目的**：确认当前分支、规格和现有飞书/records 边界，避免实现偏离计划。

- [x] T001 确认当前分支为 `002-feishu-inbox-ai-organize`，并阅读 `specs/002-feishu-inbox-ai-organize/plan.md`
- [x] T002 [P] 阅读现有飞书入口实现并记录影响点：`server.py`、`feishu_client.py`
- [x] T003 [P] 阅读现有 records 与 AI 测试边界：`tests/test_records.py`、`tests/test_feishu.py`、`tests/test_feishu_client.py`

## Phase 2：基础设施（阻塞前置）

**目的**：完成所有用户故事共享的数据模型、幂等字段和通用处理函数。

- [x] T004 在 `tests/test_records.py` 中添加 records 迁移测试，覆盖 `source`、`source_event_id`、`source_sender_json` 字段
- [x] T005 在 `server.py` 的 records schema 和 migration 中添加 `source`、`source_event_id`、`source_sender_json` 字段及飞书事件去重索引
- [x] T006 在 `server.py` 中扩展 `serialize_record_row`，输出 `source`、`sourceEventId`、`sourceSender` 字段
- [x] T007 在 `server.py` 中扩展 `create_record`，支持传入来源、来源事件 ID、来源发送者信息并保持 Web/PWA 默认来源为 `web`
- [x] T008 在 `server.py` 中新增飞书消息元数据提取工具函数，覆盖 message ID、sender、chat ID 和文本类型判断
- [x] T009 [P] 在 `tests/test_feishu.py` 中添加飞书消息 ID 和发送者信息提取测试

## Phase 3：用户故事 1 - 飞书消息进入随记收件箱（P1，MVP）

**目标**：飞书有效文本先创建来源为飞书的 record，不再直接创建正式任务。

- [x] T010 [P] [US1] 在 `tests/test_feishu.py` 中添加 HTTP 飞书事件创建 record 且不创建 todo 的测试
- [x] T011 [P] [US1] 在 `tests/test_feishu_client.py` 中添加长连接 handler 创建 record 且不调用直接建任务旧路径的测试
- [x] T012 [P] [US1] 在 `tests/test_records.py` 中添加 `GET /api/records` 返回飞书来源字段的测试
- [x] T013 [US1] 在 `server.py` 中新增 `create_feishu_record` 或等价函数，按默认账号创建来源为 `feishu` 的 record
- [x] T014 [US1] 在 `server.py` 的 `/api/feishu/events` 路径中改为调用飞书 record 创建逻辑，不再直接调用 `create_feishu_todo` 或 `create_feishu_ai_todos`
- [x] T015 [US1] 在 `feishu_client.py` 中改造 `handle_feishu_event_payload`，复用与 HTTP 飞书入口一致的 record 创建逻辑
- [x] T016 [US1] 在 `server.py` 中确保飞书空文本、非文本和超长文本不创建正常 record，并返回可排查状态
- [x] T017 [US1] 在 `web/app.js` 和 `web/index.html` 中确认或补充随记列表展示来源为飞书的标识
- [x] T018 [US1] 在 `web/styles.css` 中补充来源标识样式，保持现有界面密度和可读性

## Phase 4：用户故事 2 - 飞书随记自动整理为可审查结果（P1）

**目标**：飞书 record 创建后立即执行 AI 整理，成功和失败都保留在同一条 record 上，并向飞书回复状态。

- [x] T019 [P] [US2] 在 `tests/test_feishu.py` 中添加 AI 成功时飞书 record 更新为 `ready` 且不创建 todo 的测试
- [x] T020 [P] [US2] 在 `tests/test_feishu.py` 中添加 AI 未配置或无效 JSON 时 record 标记 `failed` 的测试
- [x] T021 [P] [US2] 在 `tests/test_feishu_client.py` 中添加成功和失败都生成飞书回复文案的测试
- [x] T022 [US2] 在 `server.py` 中抽取 Web/PWA 和飞书共用的 record AI 整理函数，复用 `call_xiaomi_record_organizer` 与 `update_record_ai_result`
- [x] T023 [US2] 在 `server.py` 中让飞书事件处理在创建 record 后立即调用共用 AI 整理函数，并返回 `aiStatus`、`recordId` 和错误信息
- [x] T024 [US2] 在 `feishu_client.py` 中根据处理结果回复飞书成功或失败状态，不再只回复“收到”
- [x] T025 [US2] 在 `server.py` 中记录飞书处理日志，包含 record ID、AI 状态和 duplicate 状态，且不得输出密钥
- [x] T026 [US2] 在 `web/app.js` 中确认飞书 record 详情沿用现有任务草稿审查，不自动保存正式任务

## Phase 5：用户故事 3 - 从飞书记录确认生成正式任务（P2）

**目标**：用户在 Web/PWA 中从飞书 record 的任务草稿确认创建正式任务，并保留来源追溯。

- [x] T027 [P] [US3] 在 `tests/test_records.py` 中添加飞书来源 record 保存任务草稿后保留 `source_record_id` 的测试
- [x] T028 [P] [US3] 在 `tests/test_records.py` 中添加来源 record 软删除后已创建 todo 仍存在并显示 deleted 来源状态的回归测试
- [x] T029 [US3] 在 `server.py` 中确认 `POST /api/records/{id}/todos` 对 `source = feishu` 的 record 走现有确认创建路径
- [x] T030 [US3] 在 `web/app.js` 中确认飞书来源 record 的任务草稿选择、部分保存和关联任务展示与 Web 来源一致
- [x] T031 [US3] 在 `web/index.html` 和 `web/styles.css` 中补充来源记录追溯展示所需的最小 UI 文案或样式

## Phase 6：用户故事 4 - 重复消息与处理状态（P3）

**目标**：同一飞书消息事件 ID 重复送达时不创建重复 record，并能表达处理状态。

- [x] T032 [P] [US4] 在 `tests/test_feishu.py` 中添加相同飞书消息事件 ID 重复送达只创建一条 record 的测试
- [x] T033 [P] [US4] 在 `tests/test_feishu_client.py` 中添加 duplicate 结果不会重复回复误导性成功文案的测试
- [x] T034 [US4] 在 `server.py` 中实现按 `source = feishu` 和 `source_event_id` 查询已有 record 的幂等逻辑
- [x] T035 [US4] 在 `server.py` 中让重复飞书事件返回 `duplicate = true` 和既有 `recordId`
- [x] T036 [US4] 在 `feishu_client.py` 中处理 duplicate 结果的飞书回复文案
- [x] T037 [US4] 在 `web/app.js` 中确认收件箱列表和详情能展示 `pending`、`processing`、`ready`、`failed` 状态

## Phase 7：打磨与横切关注点

**目的**：补齐文档、部署说明和全量验证。

- [x] T038 [P] 更新 `README.md` 的飞书机器人说明，说明飞书消息进入随记收件箱且不直接创建正式任务
- [x] T039 [P] 更新 `docs/xiaomi-mimo-orbit-submission.md` 中与 AI/飞书入口相关的说明，保持中文归档
- [x] T040 检查 `deploy/todo-sync-feishu.service` 是否仍满足本轮环境变量要求，必要时更新注释或 README 引导
- [x] T041 运行 `python -m py_compile server.py feishu_client.py`
- [x] T042 运行 `python -m unittest tests/test_feishu.py tests/test_feishu_client.py tests/test_records.py tests/test_ai_organizer.py`
- [ ] T043 按 `specs/002-feishu-inbox-ai-organize/quickstart.md` 执行手工验收，记录线上或本地验证结果

## Phase 8：2026-05-17 首页体验与完成归档迭代

**目的**：解决首页核心操作位置过低、番茄钟伪需求占位、完成任务堆积的问题；任务完成后按账号归档，并把账户、版本和任务完成情况上移到顶部。

### 用户故事 5 的测试

- [x] T044 [P] [US5] 在 `tests/test_records.py` 中添加 `todos.archived_at` 迁移测试，确认归档字段随数据库初始化和迁移存在
- [x] T045 [P] [US5] 在 `tests/test_records.py` 中添加完成任务后从 `GET /api/todos` 移除、进入 `GET /api/todos/archive` 的测试
- [x] T046 [P] [US5] 在 `tests/test_records.py` 中添加归档按账号隔离的测试，确认另一个账号无法看到当前账号归档任务

### 用户故事 5 的实现

- [x] T047 [US5] 在 `server.py` 中为 `todos` 增加 `archived_at` 字段迁移，并在任务序列化中保留归档时间
- [x] T048 [US5] 在 `server.py` 中实现完成任务自动写入 `archived_at`，取消完成时清空 `archived_at`
- [x] T049 [US5] 在 `server.py` 中让 `GET /api/todos` 只返回未归档活跃任务，并新增 `GET /api/todos/archive` 和顶部统计数据
- [x] T050 [US5] 在 `web/index.html` 中移除番茄钟 DOM，取消“任务栏”面板表达，增加顶部账号、版本和完成情况状态区
- [x] T051 [US5] 在 `web/index.html` 中把新增代办移动到右侧首个工作面板，把随记收件箱和今日计划后移
- [x] T052 [US5] 在 `web/app.js` 中移除番茄钟状态和事件绑定，刷新时读取归档统计并更新顶部状态
- [x] T053 [US5] 在 `web/styles.css` 中重排首屏布局，提高待办列表和新增代办的首屏优先级，并保证移动端不重叠
- [x] T054 运行 `python -m py_compile server.py feishu_client.py`
- [x] T055 运行 `python -m unittest tests/test_records.py tests/test_feishu.py tests/test_feishu_client.py tests/test_ai_organizer.py`
- [x] T056 使用浏览器打开本地页面，检查桌面首屏不再出现番茄钟，活跃待办与新增代办位于首屏核心区域

## 依赖与执行顺序

- Phase 1 无依赖，可立即开始。
- Phase 2 依赖 Phase 1，阻塞所有用户故事。
- Phase 3 依赖 Phase 2，是 MVP。
- Phase 4 依赖 Phase 3 的飞书 record 创建能力。
- Phase 5 依赖 Phase 3，可与 Phase 4 后半段部分并行。
- Phase 6 依赖 Phase 2 的来源字段，可在 Phase 3 后并行推进。
- Phase 7 依赖本轮目标故事完成。
- Phase 8 依赖现有 Web/PWA 和 todos API，可独立于飞书入口继续迭代。

## 并行机会

- T002 和 T003 可并行阅读不同文件。
- 同一用户故事中的测试任务通常可并行，涉及 `server.py` 的实现任务需要串行整合。
- Web/PWA 展示任务可在服务端字段稳定后并行。
- 文档任务可与最终验证准备并行。

## 实施策略

1. MVP：先完成 Phase 1 到 Phase 3，让飞书消息进入随记收件箱且不创建正式任务。
2. 增量交付：继续完成 AI 整理、任务确认、事件去重和状态展示。
3. 首页体验迭代：完成 Phase 8，取消番茄钟、上移核心操作，并实现完成归档。
4. 完成定义：自动化测试通过，`py_compile` 通过，关键 Web/PWA 首屏验收通过。
