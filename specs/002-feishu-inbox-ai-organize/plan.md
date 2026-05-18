# 实施计划：飞书随记入口与 AI 收件箱统一整理

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本计划必须使用中文撰写并归档。
**分支**：`002-feishu-inbox-ai-organize` | **日期**：2026-05-12 | **规格**：[spec.md](./spec.md)  
**输入**：来自 `specs/002-feishu-inbox-ai-organize/spec.md` 的功能规格

## 摘要

本轮把飞书消息入口接入上一轮已完成的随记收件箱能力：有效飞书文本先保存为 `record`，记录来源、飞书发送者和飞书消息事件 ID；随后立即执行与 Web/PWA 一致的 AI 整理，产出可审查的 record 字段和任务草稿；成功与失败都会在飞书中回复状态。正式任务仍只能由用户在 Web/PWA 审查确认后创建，本轮不支持飞书内直接确认任务。

2026-05-17 下一轮迭代聚焦首页信息架构和完成归档：取消番茄钟，取消“任务栏”大面板表达，把账号、版本和任务完成情况上移到顶部状态区；活跃待办列表和新增代办入口必须进入首屏核心区域；任务完成后按账号归档，从活跃列表移除但不删除。

## 技术上下文

**语言/版本**：Python 3.11+、原生 JavaScript/CSS/HTML  
**主要依赖**：Python 标准库、SQLite、现有 Xiaomi MiMo AI 调用封装、可选 `lark-oapi` 长连接客户端  
**存储**：`TODO_DATA_DIR` 下的 SQLite 数据库  
**测试**：`unittest`、`python -m py_compile server.py feishu_client.py`、必要的 Web/PWA 人工验收与浏览器截图检查  
**目标平台**：Windows 本地开发、Linux VPS、Web/PWA、飞书机器人长连接/事件入口  
**项目类型**：自托管 Web 服务 + PWA + 飞书机器人接入  
**性能目标**：飞书收到有效文本后 5 秒内保存 record 并返回飞书状态；AI 慢或失败时不得阻塞原始输入保存  
**约束**：不引入前端构建流程；不新增数据库服务；AI 密钥只在后端；records 继续不进入 `/api/sync/pull` 和 `/api/sync/push`；飞书内不确认创建正式任务；完成归档不得等同于删除，必须按账号隔离  
**规模/范围**：个人/小团队自托管；单默认账号飞书归属，保留发送者信息为后续绑定迁移做准备

## 宪法检查

*门禁：Phase 0 research 前通过；Phase 1 design 后重新检查。*

- **个人数据归属**：PASS。新增飞书来源、发送者和事件 ID 只写入本项目 SQLite；不会导出用户数据；飞书消息原文会发送给已配置的后端 AI 服务，与现有 AI 整理路径一致。
- **离线友好的同步**：PASS。正式 `todos/subtasks` 仍沿用现有创建和同步语义；`records` 继续不进入离线同步协议；新增字段不改变 `/api/sync/pull` 和 `/api/sync/push` 合约。
- **可审查的 AI**：PASS。AI 只生成 record 字段和任务草稿；正式任务必须在 Web/PWA 人工确认；AI 输出继续经过解析、校验、长度限制和清洗。
- **测试门禁**：PASS。计划覆盖飞书消息入库、事件 ID 去重、AI 成功/失败、飞书回复、正式任务不自动创建、Web/PWA 审查确认的自动化测试。
- **简洁且可观测的实现**：PASS。复用现有 `server.py`、`feishu_client.py`、records 服务和测试结构；不新增后台服务；保留确定性 JSON 错误和服务日志。
- **中文归档**：PASS。本计划及本轮 `research.md`、`data-model.md`、`quickstart.md`、contracts 文档均使用中文归档。

### 2026-05-17 迭代补充检查

- **个人数据归属**：PASS。归档查询必须按 `owner_user_id` 过滤，不能跨账号泄露已完成任务。
- **离线友好的同步**：PASS。归档通过 `todos.archived_at` 在服务端表达，活跃列表过滤归档任务；同步接口保留现有字段语义，不把归档当删除。
- **可审查的 AI**：PASS。本轮不改变 AI 生成任务草稿和人工确认边界。
- **测试门禁**：PASS。新增归档迁移、完成归档、账号隔离和顶部统计的后端测试；前端通过浏览器首屏检查验收布局。
- **简洁且可观测的实现**：PASS。沿用原生 HTML/CSS/JS 与单文件 Python 服务，不引入构建流程或新服务。
- **中文归档**：PASS。本轮规格、计划和任务补充继续用中文。

## 项目结构

### 本功能文档

```text
specs/002-feishu-inbox-ai-organize/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── feishu-inbox-contract.md
└── tasks.md
```

### 源码结构（仓库根目录）

```text
server.py                 # 飞书事件入口、records 持久化、AI 整理、Web/PWA API
feishu_client.py          # 飞书长连接客户端、消息回复、事件处理桥接
web/                      # 复用现有随记收件箱 UI，必要时补充来源/状态展示
tests/
├── test_feishu.py        # 飞书入口行为测试
├── test_feishu_client.py # 长连接客户端和回复行为测试
├── test_records.py       # records 与任务确认回归测试
└── test_ai_organizer.py  # AI 整理回归测试
deploy/                   # systemd 服务和部署脚本，必要时仅更新说明
```

**结构决策**：沿用当前单文件 Python 服务端、原生 Web/PWA 和 `tests/` 结构。飞书入口是现有后端能力的调用方，不新增服务层或前端构建目录。

### 2026-05-17 结构补充

```text
server.py                 # 增加 todos.archived_at 迁移、完成归档和当前账号归档查询
web/index.html            # 首页重排：顶部状态区、活跃待办、右侧新增代办优先
web/app.js                # 移除番茄钟逻辑，刷新时读取任务统计与归档数量
web/styles.css            # 重做首屏密度、顶部状态和两栏排序
tests/test_records.py     # 增加完成归档与账号隔离回归测试
```

**结构决策补充**：完成任务使用 `archived_at` 明确归档状态，避免复用 `deleted_at` 造成“完成”和“删除”语义混淆。`GET /api/todos` 默认只返回活跃未归档任务；新增归档查询和统计能力供 Web/PWA 顶部状态区使用。

## Phase 0：研究结论

见 [research.md](./research.md)。所有技术未知项已收敛为本地实现决策，无需额外用户澄清。

## Phase 1：设计产物

- 数据模型：[data-model.md](./data-model.md)
- 接口契约：[contracts/feishu-inbox-contract.md](./contracts/feishu-inbox-contract.md)
- 快速验证：[quickstart.md](./quickstart.md)
- Agent 上下文：已更新 [AGENTS.md](../../AGENTS.md)，指向本计划文件。

## Phase 1 后宪法复查

- **个人数据归属**：PASS。数据新增字段和事件处理路径已在数据模型与契约中记录。
- **离线友好的同步**：PASS。设计明确不改变同步 API，正式任务仍走现有任务体系。
- **可审查的 AI**：PASS。契约明确飞书只捕获和反馈，任务确认仍在 Web/PWA。
- **测试门禁**：PASS。quickstart 列出自动化验证命令和重点测试场景。
- **简洁且可观测的实现**：PASS。设计复用现有函数边界，飞书回复和事件处理结果可通过测试与日志观测。
- **中文归档**：PASS。所有计划产物为中文。

## 复杂度追踪

无宪法违背项，无需复杂度豁免。
