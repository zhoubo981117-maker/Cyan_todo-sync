# 实施计划：随记收件箱 + AI 整理

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本计划必须使用中文撰写并归档。

**分支**：`001-suiji-inbox-ai-organize` | **日期**：2026-05-10 | **规格**：[spec.md](./spec.md)  
**输入**：来自 `specs/001-suiji-inbox-ai-organize/spec.md` 的功能规格

## 摘要

在现有 Python 标准库服务端、SQLite、原生 Web/PWA 架构内实现随记收件箱。新增 `records` 服务端持久化能力，AI 整理生成一条主 `record` 和可审查的 `todo/subtask` 草稿；正式任务仍沿用现有 `todos/subtasks` 与同步体系，`records` 不进入离线同步协议。

## 技术上下文

**语言/版本**：Python 3.11+、原生 JavaScript/CSS/HTML  
**主要依赖**：Python 标准库、SQLite、现有小米 AI 调用封装  
**存储**：`TODO_DATA_DIR` 下的 SQLite 数据库  
**测试**：`unittest`、`python -m py_compile server.py`、必要的浏览器人工验证  
**目标平台**：Windows 本地、Linux VPS、Web/PWA  
**项目类型**：自托管 Web 服务 + PWA  
**性能目标**：随记提交 3 秒内返回 record 创建结果或受控错误  
**约束**：不引入前端构建流程；AI 密钥只在后端；`records` 不进入 `/api/sync/pull` 和 `/api/sync/push`  
**规模/范围**：个人/小团队自托管，第一版聚焦 Web/PWA

## 宪法检查

- **个人数据归属**：PASS。新增数据仍保存在本地 SQLite；AI 输入继续只发送到已配置的后端 AI 服务。
- **离线友好的同步**：PASS。正式 `todos/subtasks` 继续保护现有同步合约，`records` 不进入离线同步协议。
- **可审查的 AI**：PASS。AI 输出只生成 record 字段和待办草稿，正式任务必须由用户确认。
- **测试门禁**：PASS。新增后端行为覆盖自动化测试，AI 网络调用使用 mock。
- **简洁且可观测的实现**：PASS。不新增框架、服务或依赖；错误返回保持确定性。
- **中文归档**：PASS。本计划和后续文档使用中文。

## 项目结构

```text
server.py
web/
tests/
specs/001-suiji-inbox-ai-organize/
```

**结构决策**：沿用单文件 Python 服务端、原生 Web/PWA 和 `tests/` 测试目录。第一版不新增包结构或前端构建目录。

## 关键实现

- 后端新增 `records` 表，保存用户、原始输入、摘要、类型、标签 JSON、日期 JSON、情绪、AI 状态、错误、软删除时间、创建/更新时间；为 `todos` 增加可空 `source_record_id`。
- 新增随记 API：`POST /api/records/organize`、`GET /api/records`、`GET/PATCH/DELETE /api/records/{id}`、`POST /api/records/{id}/retry`、`POST /api/records/{id}/todos`、`POST /api/records/{id}/sync-dates`。
- 保留 `/api/ai/organize` 兼容现有行为；新随记 UI 使用 `/api/records/organize`。
- AI 解析扩展为 `record + items` 结构，record 字段经过长度、枚举、数量和日期格式清洗；items 继续复用现有待办草稿清洗逻辑。
- Web/PWA 在现有 AI 整理面板内升级为“随记收件箱”，支持提交、列表、筛选、详情、编辑、草稿保存、失败重试和来源展示。

## 接口与数据约束

- `record` 响应字段：`id, originalInput, summary, type, tags, dates, sentiment, aiStatus, aiError, linkedTodos, deletedAt, createdAt, updatedAt`。
- 标签最多 8 个，单个 24 字；日期保存 ISO8601 字符串数组；类型限制为 `task/note/idea/reminder/event/question/other`，前端显示中文。
- `records` 不出现在 `/api/sync/pull` 和 `/api/sync/push`。
- 删除 record 只软删除 record，不级联删除正式任务。

## 测试计划

- 后端单元测试：record 字段清洗、AI 成功解析、AI 无配置保存失败 record、AI 无效 JSON 保存失败 record、重试成功更新 record。
- 后端接口测试：认证要求、空输入拒绝且不建 record、创建 record + 草稿、保存草稿为正式 todo/subtask 并关联来源、删除 record 不删除任务、record 日期手动同步任务截止时间。
- 回归测试：现有 `/api/ai/organize` 行为、`/api/todos`、`/api/sync/pull`、`/api/sync/push` 不破坏。
- 验证命令：`python -m py_compile server.py`；`python -m unittest tests/test_ai_organizer.py tests/test_records.py`。

## 复杂度追踪

无。
