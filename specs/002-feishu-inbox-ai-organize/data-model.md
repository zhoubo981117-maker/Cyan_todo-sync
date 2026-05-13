# 数据模型：飞书随记入口与 AI 收件箱统一整理

## Record（随记记录）

现有 `records` 表继续作为核心实体。本轮需要让 record 能表达飞书来源和去重信息。

字段补充：

- `source`：记录来源。取值至少包含 `web`、`feishu`，默认 `web`。
- `source_event_id`：来源事件 ID。飞书记录保存飞书消息事件 ID，用于重复送达去重。
- `source_sender_json`：来源发送者信息 JSON。飞书记录保存发送者 ID、open_id、union_id、chat_id 等可获得信息。
- `ai_status`：继续使用现有状态，并面向飞书记录表达 `pending`、`processing`、`ready`、`failed`。
- `ai_error`：AI 整理失败原因，供 Web/PWA 和飞书失败回复使用。

关系：

- 一个飞书消息最多创建一条正常 record。
- 一个 record 可以生成多个任务草稿。
- 用户确认后，一个 record 可以关联多个正式 todo。
- record 被软删除时，不级联删除已创建的正式 todo。

验证规则：

- `source = feishu` 时，`source_event_id` 必须非空。
- 同一用户下 `source = feishu` 且 `source_event_id` 相同的正常记录不得重复创建。
- `source_sender_json` 必须是对象 JSON；无法获得发送者详情时保存空对象。
- 飞书 record 的 `original_input` 使用与 Web/PWA 输入一致的长度和空值校验。

## FeishuMessage（飞书消息）

飞书消息不是独立业务表的首选方案；它作为 record 的来源元数据保存。

关键属性：

- `message_id`：飞书消息事件 ID，用于幂等。
- `message_type`：本轮只处理文本消息。
- `text`：提取后的纯文本。
- `sender`：飞书发送者信息。
- `received_at`：服务器接收时间。

生命周期：

1. 收到消息。
2. 校验 token、消息类型和文本有效性。
3. 使用 `message_id` 查询是否已处理。
4. 未处理则创建来源为 `feishu` 的 record。
5. 立即执行 AI 整理并更新 record。
6. 回复飞书成功或失败状态。

## TodoDraft（任务草稿）

任务草稿仍然是 AI 整理结果中的临时结构，不作为正式任务持久化。

关键属性：

- `title`
- `note`
- `urgency`
- `dueAt`
- `subtasks`
- `sourceRecordId`

规则：

- 草稿只在 AI 整理响应和 record 详情审查流程中出现。
- 草稿在用户确认前不得写入正式任务列表。
- 用户可以选择部分草稿保存为正式任务。

## Todo / Subtask（正式任务与子任务）

继续沿用现有任务体系。

本轮相关字段：

- `todos.source_record_id`：保存来源 record。

规则：

- 只有 Web/PWA 确认动作能把草稿写入正式 todo/subtask。
- 飞书成功回复不得创建正式任务。
- 现有同步协议不包含 record，但正式 todo/subtask 继续同步。
