# 任务清单：随记收件箱 + AI 整理

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本任务清单必须使用中文撰写并归档。

**输入**：来自 `specs/001-suiji-inbox-ai-organize/` 的设计文档  
**前置条件**：plan.md、spec.md

## Phase 1：准备工作

- [x] T001 确认 `specs/001-suiji-inbox-ai-organize/spec.md` 与实施计划中的 API、数据模型、测试范围一致
- [x] T002 [P] 在 `tests/test_records.py` 中建立随记接口测试文件和共享 HTTP 测试夹具
- [x] T003 [P] 在 `web/index.html` 中确认 AI 整理面板和侧栏区域作为随记收件箱 UI 插入点

## Phase 2：基础设施

- [x] T004 在 `server.py` 的 `init_db()` 中新增 `records` 表结构
- [x] T005 在 `server.py` 的 `migrate_db()` 中为 `records` 建索引，并为 `todos` 增加可空 `source_record_id`
- [x] T006 在 `server.py` 中实现 record 字段清洗工具，包括摘要、类型、标签、日期、情绪、AI 状态和错误文本
- [x] T007 在 `server.py` 中实现 record 行到 API 响应对象的序列化函数
- [x] T008 在 `server.py` 中实现 `record + optional todos/subtasks` AI 提示词、解析和校验函数，复用现有待办草稿清洗逻辑
- [x] T009 在 `tests/test_records.py` 中添加 schema/migration 测试，确认 records 建表、todos 来源字段、既有数据迁移不破坏

## Phase 3：用户故事 1 - 随手记录原始输入（P1）

- [x] T010 [US1] 在 `tests/test_records.py` 中添加 `POST /api/records/organize` 成功保存原始输入的接口测试
- [x] T011 [US1] 在 `tests/test_records.py` 中添加空输入、超长输入、未登录访问的失败测试
- [x] T012 [US1] 在 `server.py` 中实现创建 record 的数据库写入函数，默认保存原始输入和初始 AI 状态
- [x] T013 [US1] 在 `server.py` 中新增 `POST /api/records/organize` 路由，完成鉴权、输入校验和 record 创建
- [x] T014 [US1] 在 `server.py` 中新增 `GET /api/records` 基础列表路由，按当前用户返回未删除 records
- [x] T015 [US1] 在 `web/app.js` 中新增 records API 客户端方法和收件箱状态变量
- [x] T016 [US1] 在 `web/index.html` 中把现有 AI 整理面板文案调整为随记收件箱入口，并增加历史 record 列表容器
- [x] T017 [US1] 在 `web/app.js` 中实现提交随记、渲染 record 列表、登录刷新后加载 records

## Phase 4：用户故事 2 - AI 自动整理 records 与待办草稿（P1）

- [x] T018 [US2] 在 `tests/test_records.py` 中添加 AI 成功返回 record 字段和待办草稿的测试
- [x] T019 [US2] 在 `tests/test_records.py` 中添加 AI 无配置、无效 JSON、字段缺失时保存失败状态 record 的测试
- [x] T020 [US2] 在 `tests/test_records.py` 中添加保存草稿为正式 todo/subtask 并写入 `source_record_id` 的测试
- [x] T021 [US2] 在 `server.py` 中把 `POST /api/records/organize` 接入 AI 整理，成功时更新 record 结构化字段并返回草稿
- [x] T022 [US2] 在 `server.py` 中实现 AI 失败路径：保存原始输入、标记 `ai_status=failed`、记录受控错误、返回可重试状态
- [x] T023 [US2] 在 `server.py` 中新增 `POST /api/records/{id}/todos`，将选中的草稿保存为正式 todo/subtask 并关联来源 record
- [x] T024 [US2] 在 `server.py` 中保持 `/api/ai/organize` 原有响应兼容，不引入 record 副作用
- [x] T025 [US2] 在 `web/app.js` 中把草稿保存流程改为通过 record 来源保存，并刷新任务列表和 record 详情
- [x] T026 [US2] 在 `web/index.html` 与 `web/styles.css` 中展示 record 摘要、类型、标签、日期、情绪、AI 状态和草稿区域

## Phase 5：用户故事 3 - 浏览、筛选和追溯随记记录（P2）

- [x] T027 [US3] 在 `tests/test_records.py` 中添加 records 筛选参数测试，覆盖类型、标签、情绪、是否有关联任务
- [x] T028 [US3] 在 `tests/test_records.py` 中添加 `GET /api/records/{id}` 返回关联 todo/subtask 状态的测试
- [x] T029 [US3] 在 `server.py` 中扩展 `GET /api/records` 支持筛选和排序
- [x] T030 [US3] 在 `server.py` 中新增 `GET /api/records/{id}` 详情路由，返回 record 和关联任务摘要
- [x] T031 [US3] 在 `server.py` 的 `/api/todos` 响应中增加来源 record 摘要或来源已删除状态，不改变 sync API
- [x] T032 [US3] 在 `web/app.js`、`web/index.html`、`web/styles.css` 中实现筛选控件、record 详情视图和任务来源展示

## Phase 6：用户故事 4 - 修正 AI 整理结果（P3）

- [x] T033 [US4] 在 `tests/test_records.py` 中添加 `PATCH /api/records/{id}` 修正摘要、类型、标签、日期、情绪的测试
- [x] T034 [US4] 在 `tests/test_records.py` 中添加手动同步 record 日期到关联 todo 截止时间的测试
- [x] T035 [US4] 在 `server.py` 中实现 `PATCH /api/records/{id}`，复用 record 字段清洗规则
- [x] T036 [US4] 在 `server.py` 中新增 `POST /api/records/{id}/sync-dates`，仅在用户触发时更新关联 todo 的 `due_at`
- [x] T037 [US4] 在 `web/app.js`、`web/index.html`、`web/styles.css` 中实现 record 编辑表单和手动同步日期操作

## Phase 7：打磨与横切关注点

- [x] T038 在 `tests/test_records.py` 中添加删除 record 不删除正式 todo/subtask 的测试
- [x] T039 在 `server.py` 中实现 `DELETE /api/records/{id}` 软删除，并确保关联任务继续存在
- [x] T040 在 `tests/test_ai_organizer.py` 中补充或调整兼容性测试，确认旧 `/api/ai/organize` 仍只返回 `items`
- [x] T041 [P] 在 `web/styles.css` 中完善移动端 record 列表、详情、草稿和筛选控件布局
- [x] T042 [P] 在 `specs/001-suiji-inbox-ai-organize/quickstart.md` 中记录中文手工验收流程
- [x] T043 运行 `python -m py_compile server.py` 和 `python -m unittest tests/test_ai_organizer.py tests/test_records.py`

## 依赖与执行顺序

- Phase 1 -> Phase 2 -> US1 -> US2 -> US3 -> US4 -> 打磨。
- US1 完成后即可演示 MVP；US2 依赖 US1 的 record 创建和列表能力。
- US3 依赖 US2 的来源关联；US4 依赖 US3 的详情能力。
- 前端样式任务 T041 可与后端收尾测试 T038-T040 并行。

## 验证要求

- 所有后端行为先写测试，再实现。
- 不允许真实第三方 AI 网络调用，测试必须 mock `call_xiaomi_chat_completion`。
- `records` 不得加入 `/api/sync/pull` 或 `/api/sync/push`。
- 完成前必须通过 `python -m py_compile server.py` 和相关 unittest。
