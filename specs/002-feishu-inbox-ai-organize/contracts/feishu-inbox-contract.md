# 接口契约：飞书随记入口与 AI 收件箱统一整理

## 飞书事件入口

### `POST /api/feishu/events`

用途：接收飞书事件回调，把有效文本消息写入随记收件箱并触发 AI 整理。

输入要求：

- 请求必须通过现有飞书 token 校验。
- 支持飞书 URL verification。
- 本轮只处理文本消息。
- 文本为空、仅空白或超长时，不创建正常 record。

行为契约：

1. 提取飞书消息事件 ID。
2. 使用默认账号归属 record，并保存飞书发送者信息。
3. 若同一事件 ID 已处理，则返回成功，不创建重复 record。
4. 创建 `source = feishu` 的 record。
5. 立即执行 record AI 整理。
6. 整理成功时更新 record 为 `ready` 并回复飞书成功状态。
7. 整理失败时保留 record，标记 `failed`，写入 `ai_error`，并回复飞书失败状态。
8. 不创建正式 todo/subtask。

成功响应示例：

```json
{
  "ok": true,
  "handled": true,
  "recordId": 123,
  "aiStatus": "ready",
  "duplicate": false
}
```

重复消息响应示例：

```json
{
  "ok": true,
  "handled": true,
  "recordId": 123,
  "duplicate": true
}
```

失败但已保存响应示例：

```json
{
  "ok": true,
  "handled": true,
  "recordId": 123,
  "aiStatus": "failed",
  "error": "AI not configured"
}
```

## 飞书长连接客户端

### `handle_feishu_event_payload(payload)`

用途：长连接客户端收到飞书消息后，调用与 HTTP 事件入口一致的处理逻辑。

行为契约：

- 空文本返回 `handled = false`。
- 有效文本必须创建或复用同一条飞书 record。
- AI 成功和失败都返回可用于回复飞书的状态文案。
- 不再调用直接创建正式任务的旧路径。

返回示例：

```json
{
  "handled": true,
  "record": {
    "id": 123,
    "aiStatus": "ready"
  },
  "replyText": "已保存到随记收件箱，并完成整理。请到 Web/PWA 审查任务草稿。"
}
```

## Web/PWA records API

现有 records API 继续作为审查和确认入口。

相关行为：

- `GET /api/records` 应能展示来源为飞书的记录。
- `GET /api/records/{id}` 应能展示飞书来源、处理状态和关联任务。
- `POST /api/records/{id}/todos` 仍是保存正式任务的唯一入口。
- 本轮不新增飞书内确认任务 API。
