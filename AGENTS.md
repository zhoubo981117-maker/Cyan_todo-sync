<!-- SPECKIT START -->
本项目的文档、规格、计划、任务拆解、变更记录、归档说明和面向用户的说明，
默认使用中文。代码标识符、命令、环境变量、API 路径、错误码和第三方专有
名词可以保留英文。除非用户明确要求英文，否则归档型内容必须写中文。

如需了解当前功能使用的技术、项目结构、Shell 命令和其他关键上下文，
优先读取当前 Spec Kit 计划文件：`specs/004-ops-ux-hardening/plan.md`。

部署相关环境变量（`POSTGRES_URL`、`TODO_SIGNING_SECRET`、版本来源 `TODO_APP_VERSION`/`VERCEL_GIT_COMMIT_SHA`）的中文说明见 `README.md` 的「Vercel / 云部署」一节。

当用户要求推送到 GitHub，而本机 GitHub 网络连接不稳定导致 `git push` / `git fetch`
失败时，不要把后续操作交给用户手动执行。应由 Codex 配置或更新本机定时重试任务，
持续自动推送当前目标分支，直到推送成功或确认远端已经包含目标提交；任务成功后应
自动停用，并在回复中说明任务名称、重试频率、当前提交和验证结果。
<!-- SPECKIT END -->
