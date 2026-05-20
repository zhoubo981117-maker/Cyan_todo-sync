# 数据模型：发布可靠性、归档中心与收件箱增强

## VersionStatus（版本状态）

版本状态是派生展示实体，不需要独立业务表。

关键属性：

- `frontendVersion`：当前页面或静态资源声明的版本。
- `backendVersion`：后端服务返回的版本。
- `serviceWorkerVersion`：当前激活 Service Worker 对应的缓存版本。
- `checkedAt`：最近一次检测时间。
- `status`：版本一致性状态，取值建议包含 `current`、`update_available`、`checking`、`failed`。
- `message`：面向用户的简短状态说明。

规则：

- 版本检测不得包含账号、任务内容或随记内容。
- 检测失败只能影响版本提示，不得阻塞核心数据加载。
- 更新提示必须由用户确认后触发刷新或缓存更新。

## ArchivedTodo（归档任务）

归档任务复用现有 `todos` 数据，核心判断条件是当前账号下 `archived_at IS NOT NULL` 且 `deleted_at IS NULL`。

关键属性：

- `id`
- `clientId`
- `title`
- `note`
- `urgency`
- `doneAt`
- `archivedAt`
- `createdAt`
- `updatedAt`
- `sourceRecordId`
- `sourceSummary`
- `subtaskSummary`

关系：

- 一个归档任务属于一个账号。
- 一个归档任务可以关联一个来源 record。
- 一个归档任务可以包含多个 subtask。

状态转换：

1. 活跃任务完成：`done = true`，写入 `done_at` 和 `archived_at`。
2. 归档任务恢复：`done = false`，清空 `done_at` 和 `archived_at`，更新 `updated_at`。
3. 归档任务删除：沿用现有删除语义，写入 `deleted_at`，不得通过恢复归档重新出现。

验证规则：

- 查询、搜索和恢复必须带当前账号过滤。
- 恢复不得改变 `client_id`，以保持同步身份稳定。
- 恢复必须更新 `updated_at`，让其他客户端能通过现有同步追赶状态变化。

## ArchiveFilter（归档筛选条件）

归档筛选条件不需要持久化，作为请求或页面状态存在。

关键属性：

- `query`：标题或备注关键字。
- `dateFrom` / `dateTo`：完成或归档时间范围。
- `urgency`：优先级。
- `sort`：排序方式，默认按 `archivedAt` 倒序。

规则：

- 空筛选条件返回默认归档列表。
- 关键字匹配至少覆盖标题和备注。
- 时间范围无效时返回受控错误，不执行跨账号或全库扫描。

## InboxReviewRecord（收件箱审查记录）

收件箱审查记录复用现有 `records` 数据和 AI 结果字段。

关键属性：

- `id`
- `source`
- `originalInput`
- `summary`
- `recordType`
- `tags`
- `dates`
- `aiItems`
- `sentiment`
- `aiStatus`
- `aiError`
- `linkedTodos`
- `createdAt`
- `updatedAt`
- `deletedAt`

补充页面状态：

- `selected`：是否被当前批量操作选中。
- `reviewState`：页面层审查状态，可由 `aiStatus`、`linkedTodos` 和 `deletedAt` 派生。

规则：

- 批量处理不得跨账号。
- AI 重试只能更新当前 record 的 AI 结果，不得创建正式 todo。
- 已有关联 todo 的 record 仍应能被检索和追溯。
