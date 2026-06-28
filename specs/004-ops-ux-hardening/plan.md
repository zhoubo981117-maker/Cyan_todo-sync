# 实施计划：运维与体验加固

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本计划必须使用中文撰写并归档。

**分支**：`004-ops-ux-hardening` | **日期**：2026-06-28 | **规格**：[spec.md](./spec.md)  
**输入**：来自 `/specs/004-ops-ux-hardening/spec.md` 的功能规格

## 摘要

四项加固，按用户故事交付：①（P1）移动端窄屏响应式修复——纯 `web/styles.css` 媒体查询调整，必要时微调 `web/index.html`，无 JS 改动；②（P1）版本号修复——`server.py` 的 `_git_version()` 在缺少 `TODO_APP_VERSION` 时回退读取 `VERCEL_GIT_COMMIT_SHA`，**一处修复同时打通"应用内更新提示"与"Service Worker 缓存刷新"两段链路**；③（P2）签名密钥固化——`load_or_create_secret()` 已实现 `TODO_SIGNING_SECRET` 优先，补一条优先级单元测试 + 部署文档；④（P3）CI——新增 GitHub Actions，在 PR / push main 时跑 `pytest` 与 `python -c "import server"`（SQLite 模式）+ `python -m py_compile server.py`。

研究阶段关键结论：版本恒为 `unknown` 是更新链路失灵的**唯一根因**。`server.py` 已在服务 `sw.js` 时把 `__APP_VERSION__` 替换为 `APP_VERSION["short"]`，且 `app.js` 通过比较 `/api/version` 的 `short` 变化触发"发现新版本"。只要 `short` 变成真实 commit，两段链路自动恢复，无需改动 `app.js` / `sw.js`。详见 [research.md](./research.md)。

## 技术上下文

**语言/版本**：Python 3.12（后端 `server.py`，标准库 `http.server`）；原生 Web（HTML/CSS/JS，无构建步骤）  
**主要依赖**：Python 标准库；`psycopg[binary]`（Postgres 适配，仅生产）；`lark-oapi`（飞书，可选）；前端无框架  
**存储**：本地 SQLite（`TODO_DATA_DIR`）/ 生产 Postgres（`pg_compat.py` 适配 Vercel-Neon）。本特性**不改动任何表结构与数据**  
**测试**：`pytest`（`tests/`）+ `python -m py_compile server.py` + SQLite 模式导入冒烟；移动端用无头浏览器（Edge headless）人工视觉验证  
**目标平台**：Web/PWA（Android 浏览器为主用场景）+ Windows 本地开发 + Vercel 生产  
**项目类型**：自托管 Web 服务 + PWA（单文件后端 + 静态前端）  
**性能目标**：不引入额外冷启动开销；版本解析为常量级  
**约束**：不改业务逻辑与 API 契约（FR-010）；无前端构建步骤；密钥仅后端；文档中文  
**规模/范围**：个人/小团队自托管；本特性为运维与体验加固，改动面小且集中

## 宪法检查

*门禁：Phase 0 research 前必须通过。Phase 1 design 后必须重新检查。*

- **个人数据归属**：**PASS**。不删除/导出/迁移任何用户数据；签名密钥固化通过环境变量提供稳定值，DB 中 `app_kv` 回退保持不变，既有数据受保护（FR-006/007/011）。
- **离线友好的同步**：**N/A**。不触及 todos/subtasks/sync 逻辑、client ID、tombstone、`updated_at` 或 `/api/sync/*` 合约（FR-010）。
- **可审查的 AI**：**N/A**。不涉及 AI 功能与供应商密钥。
- **测试门禁**：**PASS**。版本回退、签名密钥优先级属后端行为，纳入自动化单元测试；CI 统一跑 `pytest` + `py_compile` + 导入冒烟。移动端为窄范围 UI 调整，按宪法采用人工浏览器验证，并在 quickstart 记录验证方法与原因。
- **简洁且可观测的实现**：**PASS**。不新增框架/服务/运行时依赖（GitHub Actions 为外部 CI 配置，非应用依赖）；本特性正是强化 version 可观测性与更新可达性。
- **中文归档**：**PASS**。spec/plan/research/quickstart/tasks 与变更说明均中文。

> 结论：无 FAIL，无需填写「复杂度追踪」。Phase 1 设计后复检维持上述结论（设计未引入新违反项）。

## 项目结构

### 本功能文档

```text
specs/004-ops-ux-hardening/
├── plan.md              # 本文件
├── research.md          # Phase 0 输出：根因与技术决策
├── data-model.md        # Phase 1 输出：版本标识 / 签名密钥（无新表）
├── quickstart.md        # Phase 1 输出：四项验证步骤
├── contracts/           # Phase 1 输出：/api/version 契约（保持不变，仅登记）
└── tasks.md             # Phase 2 输出（由 /speckit.tasks 生成）
```

### 源码结构（仓库根目录，本特性真实涉及）

```text
server.py                     # ② _git_version 回退 VERCEL_GIT_COMMIT_SHA；④ 导入冒烟目标
web/styles.css                # ① 移动端媒体查询修复
web/index.html                # ①（必要时）窄屏结构微调
tests/test_version.py         # ② 新增：版本来源优先级测试
tests/test_secret.py          # ③ 新增：签名密钥优先级测试
.github/workflows/ci.yml      # ④ 新增：CI 工作流
README.md / AGENTS.md         # ③ 部署文档补充（TODO_SIGNING_SECRET / 版本来源）
```

**结构决策**：沿用现有"单文件后端 + 静态前端"结构，不新增目录层级。改动按用户故事分散到独立文件，避免互相写冲突（CSS / server.py / tests / workflow / docs 各自独立），可并行实现。

## 复杂度追踪

> 无宪法 FAIL，无需填写。
