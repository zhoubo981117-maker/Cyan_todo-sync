# Quickstart：运维与体验加固验证

四项的验证步骤。所有命令在仓库根目录执行。

## 前置

```bash
# 本地以 SQLite 模式运行（不设 POSTGRES_URL）
export TODO_DATA_DIR=/tmp/cyan-verify
python server.py   # 监听 http://localhost:8787
```

## US1 移动端窄屏（人工浏览器验证）

用无头浏览器在 390px 与 320px 两档对登录页与仪表盘截图，逐屏核查：

```bash
# 以 Edge headless 为例（Windows）
msedge --headless=new --window-size=390,844 --screenshot=login_390.png http://localhost:8787/
msedge --headless=new --window-size=320,720 --screenshot=login_320.png http://localhost:8787/
```

判定（对应 SC-001）：无横向滚动、无元素重叠；日历保持 7 列不撑破；筛选器换行可点；可完成"登录→新增→勾选完成"闭环。仪表盘需登录后截图（或临时本地造数据）。

## US2 版本与更新提示

```bash
# 本地：应返回真实 git short（非 unknown），source=git
curl -s http://localhost:8787/api/version

# 模拟 Vercel 注入
TODO_DATA_DIR=/tmp/cyan-verify VERCEL_GIT_COMMIT_SHA=abc1234deadbeef python server.py &
curl -s http://localhost:8787/api/version    # short=abc1234, source=vercel
curl -s http://localhost:8787/sw.js | head -2 # CACHE 名含 abc1234，而非 __APP_VERSION__/unknown
```

判定（SC-002/003）：`short` 为真实值；`sw.js` 缓存名随之变化。线上部署新版后，旧页面应出现"发现新版本"。

## US3 签名密钥固化

```bash
python -m pytest tests/test_secret.py -q
```

判定（SC-004）：`TODO_SIGNING_SECRET` 设置时，签名密钥等于该值且优先于 DB/文件；未设置时维持原行为。

## US4 CI 与质量门禁

```bash
# 本地等价于 CI 的核心步骤
python -m py_compile server.py pg_compat.py
TODO_DATA_DIR=/tmp/cyan-verify python -c "import server; print('import ok')"
python -m pytest -q
```

判定（SC-005）：以上全绿即代表 CI 应通过；故意改坏一个测试应让 `pytest` 失败。CI 在 PR 与 push main 时自动运行同样步骤。

## 总验收

对照 [spec.md](./spec.md) 成功标准 SC-001..SC-005 逐条确认，并确保未改动任何用户数据与 API 契约（FR-010/011）。
