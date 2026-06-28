# 接口契约：运维与体验加固

本特性遵守 FR-010：**不改变任何现有 API 的行为或契约**。此处仅登记受影响但**保持不变**的契约，供实现与验证对照。

## `GET /api/version`（保持不变）

- 现有响应结构不变；仅 `version` 内各字段的**取值来源**扩展（新增 `VERCEL_GIT_COMMIT_SHA` 回退），字段名与形态不变。
- 响应示例：

```json
{
  "ok": true,
  "time": "2026-06-28T10:00:00+00:00",
  "version": { "commit": "<sha>", "short": "<sha7>", "source": "vercel" }
}
```

- 验收：生产环境 `version.short` 不再为 `unknown`；`source` 反映真实来源。

## `GET /sw.js`（保持不变）

- 服务端继续把文件中的 `__APP_VERSION__` 占位符替换为 `APP_VERSION["short"]`（既有行为）。
- 本特性不改替换逻辑，仅因 `short` 变为真实值而使缓存名随部署变化。

## 其它 API

- 认证、待办、子任务、归档、日历、随记/AI、同步（`/api/sync/*`）、飞书等所有接口**契约与行为不变**。
- 签名密钥固化只改变密钥**取值来源优先级**，不改变 `/api/login`、`/api/register` 等的请求/响应契约。
