# 实施计划：发布可靠性、归档中心与收件箱增强

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本计划必须使用中文撰写并归档。

**分支**：`003-release-archive-inbox` | **日期**：2026-05-20 | **规格**：[spec.md](./spec.md)  
**输入**：来自 `specs/003-release-archive-inbox/spec.md` 的功能规格

## 摘要

本轮聚焦三个可独立验收的能力：第一，解决发布后浏览器仍展示旧版本的问题，让用户能看到前端、Service Worker 和后端版本是否一致，并提供明确更新入口；第二，把上一轮已完成的任务归档语义补成可用归档中心，支持查看、搜索和恢复当前账号的已完成任务；第三，增强随记收件箱审查效率，补充详情、筛选、失败重试和批量处理能力，同时保持 AI 草稿必须人工确认的边界。

## 技术上下文

**语言/版本**：Python 3.11+、原生 JavaScript/CSS/HTML  
**主要依赖**：Python 标准库、SQLite、现有 Xiaomi MiMo AI 调用封装、现有 PWA Service Worker  
**存储**：`TODO_DATA_DIR` 下的 SQLite 数据库；归档复用 `todos.archived_at`，收件箱复用 `records`  
**测试**：`unittest`、`python -m py_compile server.py feishu_client.py`、`node --check web/app.js`、浏览器桌面/移动验收  
**目标平台**：Windows 本地开发、Linux VPS、Web/PWA、现有 Caddy/systemd 部署  
**项目类型**：自托管 Web 服务 + PWA + 部署可观测性改进  
**性能目标**：版本检测 10 秒内给出状态；归档搜索在个人使用规模下 5 秒内返回可用结果；收件箱筛选不明显阻塞页面交互  
**约束**：不引入前端构建流程；不新增数据库服务；不改变 AI 人工确认原则；不改变 `/api/sync/pull` 和 `/api/sync/push` 现有合约；不得跨账号泄露归档或收件箱记录  
**规模/范围**：个人/小团队自托管；单 SQLite；现有 Web/PWA 首屏和右侧工作区内完成

## 宪法检查

*门禁：Phase 0 research 前通过。Phase 1 design 后重新检查。*

- **个人数据归属**：PASS。新增能力只使用现有 SQLite 和浏览器缓存状态；不导出用户数据，不引入新的外部数据服务。
- **离线友好的同步**：PASS。归档恢复会影响正式 todo 状态，但必须保持 `client_id`、`updated_at`、tombstone 和 sync 合约兼容；records 继续不进入同步协议。
- **可审查的 AI**：PASS。本轮不新增 AI 自动创建任务路径；收件箱重试继续使用后端 AI 封装，输出仍停留在可审查记录和草稿层。
- **测试门禁**：PASS。归档恢复、账号隔离、收件箱重试/批量、版本状态接口需要自动化测试；缓存更新体验需要浏览器验收。
- **简洁且可观测的实现**：PASS。复用现有 `server.py`、`web/`、`deploy/`，以版本接口、受控 JSON 错误和 UI 状态表达为主，不新增服务。
- **中文归档**：PASS。本计划和后续文档均使用中文归档。

## 项目结构

### 本功能文档

```text
specs/003-release-archive-inbox/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── release-archive-inbox-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### 源码结构（仓库根目录）

```text
server.py                 # 版本状态、归档查询/恢复、records 筛选/重试/批量处理 API
web/index.html            # 顶部版本状态、归档中心入口、收件箱详情/批量操作结构
web/app.js                # 版本检测与更新提示、归档中心交互、收件箱筛选/详情/批量逻辑
web/styles.css            # 更新提示、归档中心、收件箱详情和移动端布局样式
web/sw.js                 # PWA 缓存版本、激活与旧缓存清理策略
tests/test_records.py     # 归档恢复、账号隔离、records 筛选/重试/批量行为测试
tests/test_release.py     # 版本状态和缓存相关后端契约测试
deploy/                   # 必要时补充部署更新说明，不新增常驻服务
README.md                 # 更新线上发布、缓存刷新和归档中心使用说明
```

**结构决策**：沿用当前单文件 Python 后端、原生 Web/PWA 和 `tests/` 结构。版本可靠性不新建发布平台，优先用现有 `/api/version`、静态资源头和 Service Worker 更新流程补齐用户可见状态。归档中心和收件箱增强复用当前 `todos`、`records` 数据，不新增独立数据存储。

## Phase 0：研究结论

见 [research.md](./research.md)。本轮未发现必须由用户进一步澄清的技术未知项。

## Phase 1：设计产物

- 数据模型：[data-model.md](./data-model.md)
- 接口契约：[contracts/release-archive-inbox-contract.md](./contracts/release-archive-inbox-contract.md)
- 快速验证：[quickstart.md](./quickstart.md)

## Phase 1 后宪法复查

- **个人数据归属**：PASS。归档与收件箱继续按 `owner_user_id` 隔离；版本状态不包含用户敏感数据。
- **离线友好的同步**：PASS。恢复归档任务必须更新 todo 状态和 `updated_at`，但不改变 sync 请求/响应字段要求。
- **可审查的 AI**：PASS。收件箱重试只更新 record 的 AI 结果和草稿，正式任务仍由 `POST /api/records/{id}/todos` 人工确认。
- **测试门禁**：PASS。任务清单将包含后端自动化测试和浏览器缓存验收。
- **简洁且可观测的实现**：PASS。计划不新增服务和大型依赖；发布可靠性通过现有页面状态、JSON 接口和 Service Worker 生命周期表达。
- **中文归档**：PASS。所有新增文档均为中文。

## 复杂度追踪

无宪法违反项，无需复杂度豁免。
