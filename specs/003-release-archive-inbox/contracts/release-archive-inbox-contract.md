# 接口契约：发布可靠性、归档中心与收件箱增强

## 版本状态

### `GET /api/version`

用途：返回后端当前运行版本，供页面判断前后端是否一致。

响应示例：

```json
{
  "ok": true,
  "time": "2026-05-20T08:00:00Z",
  "version": {
    "commit": "ff1724affff7705d31cd591cd18d8c0f5d879928",
    "short": "ff1724a",
    "source": "git"
  }
}
```

契约要求：

- 响应不得缓存为旧值。
- 失败时前端必须显示版本检测失败状态，但不阻塞主要页面。
- 页面应把后端短版本与当前前端/Service Worker 版本做一致性判断。

## 归档中心

### `GET /api/todos/archive`

用途：查询当前账号的已完成归档任务。

查询参数：

- `q`：可选，按标题或备注关键字筛选。
- `from`：可选，开始日期或时间。
- `to`：可选，结束日期或时间。
- `urgency`：可选，优先级。
- `limit`：可选，单次返回数量。
- `offset`：可选，分页偏移。

成功响应示例：

```json
{
  "ok": true,
  "todos": [
    {
      "id": 12,
      "clientId": "todo-abc",
      "title": "完成方案评审",
      "note": "补充风险点",
      "urgency": "high",
      "done": true,
      "doneAt": "2026-05-20T03:00:00Z",
      "archivedAt": "2026-05-20T03:00:00Z",
      "sourceRecordId": 8,
      "sourceSummary": "客户续费报价风险点",
      "subtaskSummary": {
        "total": 2,
        "done": 2
      }
    }
  ],
  "stats": {
    "active": 3,
    "archived": 8,
    "total": 11
  }
}
```

契约要求：

- 只返回当前账号数据。
- 默认不返回已删除任务。
- 默认按 `archivedAt` 倒序。
- 无匹配结果时返回空列表，不返回错误。

### `POST /api/todos/{id}/restore`

用途：把当前账号的一条归档任务恢复为活跃任务。

请求体：

```json
{}
```

成功响应示例：

```json
{
  "ok": true,
  "todo": {
    "id": 12,
    "title": "完成方案评审",
    "done": false,
    "doneAt": null,
    "archivedAt": null
  },
  "stats": {
    "active": 4,
    "archived": 7,
    "total": 11
  }
}
```

错误契约：

- 任务不存在、已删除、属于其他账号或不是归档任务时，返回受控错误。
- 恢复失败不得部分修改子任务或来源记录。
- 恢复必须更新任务同步时间，方便现有客户端追赶。

## 收件箱增强

### `GET /api/records`

用途：查询当前账号随记收件箱记录。

新增或明确查询参数：

- `source`：可选，按 `web`、`feishu` 等来源筛选。
- `status`：可选，按 `pending`、`processing`、`ready`、`failed` 等 AI 状态筛选。
- `tag`：可选，按标签筛选。
- `hasTodo`：可选，按是否已生成正式任务筛选。
- `q`：可选，按原始输入或摘要关键字筛选。

契约要求：

- 只返回当前账号记录。
- 组合筛选必须同时生效。
- 过滤结果为空时返回空列表。

### `GET /api/records/{id}`

用途：返回收件箱记录详情。

契约要求：

- 返回原始输入、来源、AI 状态、AI 错误、摘要、标签、日期、任务草稿和关联任务。
- 记录属于其他账号时不得返回详情。

### `POST /api/records/{id}/retry`

用途：对 AI 整理失败或需要重新整理的记录发起重试。

契约要求：

- 重试只更新 record 的 AI 结果和状态。
- 重试不得自动创建正式 todo/subtask。
- AI 不可用或返回无效结果时返回受控失败，并保留原始输入。

### `POST /api/records/bulk`

用途：对多条当前账号记录执行批量处理。

请求示例：

```json
{
  "action": "delete",
  "ids": [1, 2, 3]
}
```

成功响应示例：

```json
{
  "ok": true,
  "result": {
    "succeeded": 2,
    "failed": 0,
    "skipped": 1
  }
}
```

契约要求：

- 支持的动作本轮限定为清理已审查记录或等价软删除动作。
- 不允许跨账号批量处理。
- 部分失败必须返回数量和可排查原因。
