# Phase 0 研究：运维与体验加固

本文件汇总四项的技术决策与关键根因调查。格式：决策 / 理由 / 备选方案。

## R1：更新链路失灵的根因（US2 核心）

**调查结论**：版本恒为 `unknown` 是**唯一根因**，同时拖垮两段更新链路。

- 应用内提示：[web/app.js](../../web/app.js) `loadVersionInfo()` 调 `/api/version` 取 `version.short`，与 `localStorage.todo_app_version` 比较，**值变化**才弹"发现新版本"。`short` 恒为 `unknown` → 永不变化 → 永不提示。
- Service Worker 缓存：[web/sw.js](../../web/sw.js) `CACHE = todo-sync-${APP_VERSION}`；[server.py](../../server.py) 在服务 `/sw.js` 时**已**将 `__APP_VERSION__` 替换为 `APP_VERSION["short"]`。但 `short=unknown` → 缓存名 `todo-sync-unknown` 恒定 → 旧资源永久命中 → 用户被卡在旧界面（需手动 Ctrl+F5）。

**决策**：只修 `server.py` 的 `_git_version()`，让其在缺 `TODO_APP_VERSION` 时回退 `VERCEL_GIT_COMMIT_SHA`，使 `short` 变成真实 commit 前 7 位。两段链路随之自动恢复，**不改 `app.js` / `sw.js`**。

**理由**：根因单一、改动面最小、风险最低，符合宪法"简洁实现"。`app.js`/`sw.js` 现有机制本身正确。

**备选方案**：① 在 `app.js` 内改用其它更新探测（无意义，机制本就正确）；② 引入前端构建步骤在打包时注入版本（违反"无前端构建"约束，被拒）；③ 用部署时脚本替换 `sw.js` 占位符（`server.py` 已在运行时替换，重复且更复杂，被拒）。

## R2：版本来源与回退顺序（US2）

**决策**：`_git_version()` 解析顺序为 `TODO_APP_VERSION` → `VERCEL_GIT_COMMIT_SHA` → 本地 `git rev-parse HEAD` → `unknown`。`short` 取前 7 位，`source` 标注来源（`env` / `vercel` / `git` / `unknown`）。

**理由**：`TODO_APP_VERSION` 保留显式覆盖；`VERCEL_GIT_COMMIT_SHA` 是 Vercel 默认在构建与运行时注入的系统环境变量（开启"自动暴露系统环境变量"，默认开），无需用户手动配置；本地开发仍走 `git`；最终 `unknown` 兜底不报错。

**备选方案**：要求用户手动在 Vercel 配 `TODO_APP_VERSION=$VERCEL_GIT_COMMIT_SHA`（多一步人工运维，且 Vercel 环境变量值不支持引用其它变量，被拒）。

## R3：移动端响应式（US1）

**现状**：[web/styles.css](../../web/styles.css) 已有 `@media (max-width:1080px)`（双栏折叠单列）与 `@media (max-width:720px)`（topbar 单列、padding 收紧、`.grid2`/登录行单列）。

**决策**：在 390px 与 320px 两档实测，重点核查并修复：①日历 `.calendar-grid` 7 列在窄屏的最小宽度与横向溢出；②各类筛选器 `.archive-filters` / `.record-filters` 的换行与可点击；③ `.dialog-card` 在窄屏宽度（已 `min(560px,92vw)`，需复核内部 `.grid2`）；④ topbar `.stats-pill` 过长换行；⑤触控目标尺寸（按钮/复选框 ≥ 可点）。采用无头浏览器（Edge headless，`--window-size`）逐屏截图验证。

**理由**：窄范围纯样式修复，宪法允许人工浏览器验证；无需引入测试框架。

**备选方案**：引入响应式可视化回归测试工具（超出本特性范围与技术栈简洁约束，被拒）。

## R4：签名密钥固化（US3）

**现状**：[server.py](../../server.py) `load_or_create_secret()` 已实现优先级：`TODO_SIGNING_SECRET`（env）→ Postgres 模式存入/读取 `app_kv` 表 → 本地文件。env 值优先级最高。

**决策**：保持现有优先级不变；新增单元测试锁定"env 存在时优先于其它来源"；在 `README.md` / `AGENTS.md` 补充：生产建议配置 `TODO_SIGNING_SECRET`（任意高熵随机串），以保证清库/换库后不掉登录。

**理由**：实现已就绪，本故事核心是"用测试锁定优先级 + 文档化运维动作"，零行为变更。

**备选方案**：把密钥管理做成应用内界面（违反"密钥仅经环境变量/被忽略的本地文件配置"，被拒）。

## R5：CI 设计（US4）

**决策**：新增 `.github/workflows/ci.yml`，触发于 `pull_request` 与 `push: main`。步骤：检出 → 安装 Python 3.12 → `pip install -r requirements.txt` → `python -m py_compile server.py pg_compat.py` → `python -c "import server"`（设 `TODO_DATA_DIR` 为临时目录，SQLite 模式导入冒烟）→ `pytest -q`。

**理由**：复用既有 `tests/`；`py_compile` 与导入冒烟是宪法对共享后端改动的最低要求；GitHub Actions 是仓库托管平台自带、零额外应用依赖。

**风险与处理**：①`tests/` 中涉及 AI/SMTP/飞书的用例须用 mock（宪法已要求），CI 不放真实密钥，相关用例应自洽通过或自行跳过（FR-009）；②`psycopg[binary]` 安装为预编译 wheel，CI 安装无需系统库；③导入冒烟不连 Postgres（不设 `POSTGRES_URL`），走 SQLite 分支。

**备选方案**：用其它 CI（无意义，仓库在 GitHub）；在 CI 内起 Postgres 服务做集成测试（超范围，本特性不改数据层，被拒）。
