# 任务：运维与体验加固

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本任务清单使用中文。

**分支**：`004-ops-ux-hardening` | **规格**：[spec.md](./spec.md) | **计划**：[plan.md](./plan.md)

**说明**：任务按用户故事分阶段，便于独立实现与验证。四个故事改动文件互不重叠，可并行交付。`[P]` 表示可与同阶段其它 `[P]` 任务并行（不同文件、无未完成依赖）。

---

## Phase 1：Setup（基线）

- [x] T001 在仓库根目录以 SQLite 模式跑通基线：`export TODO_DATA_DIR=/tmp/cyan-verify && python server.py`，确认 `GET /` 与 `GET /api/version` 返回 200，作为后续对照（不改任何文件）

## Phase 2：Foundational（阻塞性前置）

无。四个故事相互独立，无需共享前置改动。

---

## Phase 3：用户故事 US1 — 移动端窄屏可用（优先级 P1）

**目标**：登录页与仪表盘在 320–420px 正确排版、可完成核心闭环。
**独立测试**：在 390px 与 320px 无头截图，逐屏核查无横向滚动/重叠且可操作（SC-001）。

- [x] T002 [US1] 基线取证：用 Edge headless 在 390px 与 320px 截图登录页（仪表盘需登录后或临时造数据），记录溢出/重叠/不可点问题清单
- [x] T003 [US1] 修复 [web/styles.css](../../web/styles.css) 窄屏样式：复核并补强 `@media (max-width:720px)` 与新增更窄断点，重点处理 ①`.calendar-grid` 7 列最小宽度与横向溢出（必要时容器内 `overflow-x:auto` 或缩小格子内边距）②`.archive-filters`/`.record-filters` 换行与控件可点 ③`.dialog-card` 内 `.grid2` 单列 ④topbar `.stats-pill` 过长换行 ⑤触控目标尺寸
- [x] T004 [US1] 如结构性溢出无法纯 CSS 解决，最小化微调 [web/index.html](../../web/index.html)（仅布局容器，保留所有 id/结构，不动 app.js 钩子）
- [x] T005 [US1] 复测：在 390px 与 320px 重新截图，确认无横向滚动/重叠，并完成"登录→新增待办→勾选完成"闭环（对照 SC-001）

**检查点**：US1 可独立交付——窄屏体验达标。

---

## Phase 4：用户故事 US2 — 版本可见且能收到更新提示（优先级 P1）

**目标**：线上版本徽标显示真实 commit，恢复应用内更新提示与 SW 缓存刷新。
**独立测试**：`/api/version` 的 `short` 非 `unknown`；`/sw.js` 缓存名随版本变化（SC-002/003）。

- [x] T006 [P] [US2] 新增 [tests/test_version.py](../../tests/test_version.py)：覆盖 `_git_version()` 来源优先级 `TODO_APP_VERSION` → `VERCEL_GIT_COMMIT_SHA` → 本地 git → `unknown`，断言 `short` 取前 7 位、`source` 标注正确（先写测试，预期失败）
- [x] T007 [US2] 修改 [server.py](../../server.py) `_git_version()`：无 `TODO_APP_VERSION` 时回退读取 `VERCEL_GIT_COMMIT_SHA`，`source` 记为 `vercel`；保留本地 git 与 `unknown` 兜底，缺失来源静默不报错
- [x] T008 [US2] 验证：`pytest tests/test_version.py -q` 通过；本地 `curl /api/version` 返回真实 git short；`VERCEL_GIT_COMMIT_SHA=abc1234... python server.py` 后 `curl /sw.js | head -2` 缓存名含 `abc1234`（非 `__APP_VERSION__`/`unknown`）

**检查点**：US2 可独立交付——更新链路恢复。

---

## Phase 5：用户故事 US3 — 清库/换库后不掉登录（优先级 P2）

**目标**：用测试锁定签名密钥优先级（env > DB > 文件），并文档化运维动作。
**独立测试**：`TODO_SIGNING_SECRET` 设置时密钥等于该值且优先（SC-004）。

- [x] T009 [P] [US3] 新增 [tests/test_secret.py](../../tests/test_secret.py)：断言设置 `TODO_SIGNING_SECRET` 时 `load_or_create_secret()` 返回该值（优先于 DB/文件）；未设置时维持本地文件持久化行为，无回归
- [x] T010 [US3] 核对 [server.py](../../server.py) `load_or_create_secret()` 现有优先级与测试一致（如不一致则最小修正，确保 env 始终最高，DB 中 `app_kv` 回退不变）
- [x] T011 [P] [US3] 在 [README.md](../../README.md) 与 [AGENTS.md](../../AGENTS.md) 补充中文部署说明：生产建议配置 `TODO_SIGNING_SECRET`（高熵随机串）以清库/换库不掉登录；并说明版本来源（`TODO_APP_VERSION`/`VERCEL_GIT_COMMIT_SHA`）

**检查点**：US3 可独立交付——会话稳定性有保障且文档化。

---

## Phase 6：用户故事 US4 — 提交即受自动化质量门禁保护（优先级 P3）

**目标**：PR 与 push main 自动跑测试 + 后端导入冒烟。
**独立测试**：坏改动让检查失败，正常改动通过（SC-005）。

- [x] T012 [P] [US4] 新增 [.github/workflows/ci.yml](../../.github/workflows/ci.yml)：触发 `pull_request` 与 `push: main`；步骤 = 检出 → setup Python 3.12 → `pip install -r requirements.txt` → `python -m py_compile server.py pg_compat.py` → `TODO_DATA_DIR=$(mktemp -d) python -c "import server"`（SQLite 导入冒烟，不设 `POSTGRES_URL`）→ `pytest -q`
- [x] T013 [US4] 本地预演 CI 等价命令全绿：`python -m py_compile server.py pg_compat.py` + SQLite 导入冒烟 + `pytest -q`；确认涉及 AI/SMTP/飞书的用例已 mock、无真实网络依赖（FR-009）

**检查点**：US4 可独立交付——质量门禁生效。

---

## Phase 7：Polish & 收尾

- [x] T014 按 [quickstart.md](./quickstart.md) 逐条复核 SC-001..SC-005 全部达标
- [x] T015 合并前确认未改动任何用户数据与现有 API 契约（FR-010/011）：`git diff` 仅触及 styles.css/index.html/server.py(_git_version)/tests/docs/workflow，且 server.py 仅 `_git_version` 区域变更
- [x] T016 全量 `pytest -q` 与 `python -m py_compile server.py` 最终绿，准备提交

---

## 依赖与执行顺序

- **Setup（T001）** 先行（仅基线，不阻塞）。
- **Phase 2** 为空。
- **四个用户故事（US1–US4）相互独立、可并行**：US1 改 `web/`、US2 改 `server.py`+`tests/test_version.py`、US3 改 `tests/test_secret.py`+docs、US4 改 `.github/`。文件无重叠。
- 故事内顺序：US2/US3 先写测试（T006/T009）再实现（T007/T010）。
- **Polish（T014–T016）** 在各故事完成后统一收尾。

## 并行执行示例

- 可同时启动：T006 `[P]`（test_version）、T009 `[P]`（test_secret）、T011 `[P]`（docs）、T012 `[P]`（ci.yml）——分属不同文件。
- US1 的 T002→T003→T004→T005 顺序执行（同改 `web/`）。

## MVP 与增量交付

- **MVP 建议**：US2（版本/更新链路）——根因单一、直接解决"用户看不到新界面"的痛点，改动最小、价值最高。
- 随后并行补 US1（移动端）、US3（密钥+文档）、US4（CI）。
- 每个故事独立成可验证增量，可分别提交/合并。

---

**任务统计**：共 16 个任务。US1=4、US2=3、US3=3、US4=2、Setup=1、Polish=3。
**并行机会**：T006/T009/T011/T012 四项可并行；四个用户故事整体可并行。
**测试任务**：T006（版本优先级）、T009（密钥优先级）——满足宪法测试门禁。
