# 实施计划：[FEATURE]

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本计划必须使用中文撰写并归档。

**分支**：`[###-feature-name]` | **日期**：[DATE] | **规格**：[link]  
**输入**：来自 `/specs/[###-feature-name]/spec.md` 的功能规格

**说明**：本模板由 `__SPECKIT_COMMAND_PLAN__` 命令填充。执行流程见 `.specify/templates/plan-template.md`。

## 摘要

[从功能规格提取：核心需求 + 研究后确定的技术方向]

## 技术上下文

<!--
  操作要求：将本节替换为项目真实技术细节。
  当前结构用于引导迭代，不要求保留所有示例。
-->

**语言/版本**：[例如 Python 3.11、Swift 5.9、Rust 1.75，或 NEEDS CLARIFICATION]  
**主要依赖**：[例如 Python 标准库、lark-oapi、Flutter，或 NEEDS CLARIFICATION]  
**存储**：[如适用，例如 SQLite、本地文件，或 N/A]  
**测试**：[例如 unittest、手动浏览器验证，或 NEEDS CLARIFICATION]  
**目标平台**：[例如 Windows 本地、Linux VPS、Android、Web/PWA，或 NEEDS CLARIFICATION]  
**项目类型**：[例如 web-service、PWA、mobile-app、deployment，或 NEEDS CLARIFICATION]  
**性能目标**：[领域相关目标，例如 p95 < 200ms、同步 1000 条任务，或 NEEDS CLARIFICATION]  
**约束**：[领域相关约束，例如离线可用、无前端构建步骤、密钥仅后端，或 NEEDS CLARIFICATION]  
**规模/范围**：[例如个人/小团队自托管、50 个页面、10k 条任务，或 NEEDS CLARIFICATION]

## 宪法检查

*门禁：Phase 0 research 前必须通过。Phase 1 design 后必须重新检查。*

每一项填写 PASS、FAIL 或 N/A。任何 FAIL 都必须先写入“复杂度追踪”，才可以进入 Phase 0 research。

- **个人数据归属**：计划是否保护现有 SQLite/用户数据，并记录任何新的数据导出、删除、迁移或外部传输路径？
- **离线友好的同步**：如果涉及 todos/subtasks/sync，计划是否保护稳定 client ID、tombstone、`updated_at` 和 pull/push 合约兼容性？
- **可审查的 AI**：如果涉及 AI，供应商密钥是否仅保留在后端，输出是否会校验/清洗，默认是否保留用户审查，并在相关场景明确 Asia/Shanghai 日期处理？
- **测试门禁**：涉及 auth、reset、AI、飞书、sync、migrations、recurrence 或共享 API 合约的后端行为，是否列出自动化测试？
- **简洁且可观测的实现**：计划是否避免不必要的新框架/服务/依赖，并在适用时包含确定性错误、日志或 version/health 验证？
- **中文归档**：本计划及后续 specs、tasks、quickstart、research、变更说明是否默认使用中文归档？

## 项目结构

### 本功能文档

```text
specs/[###-feature]/
├── plan.md              # 本文件（__SPECKIT_COMMAND_PLAN__ 输出）
├── research.md          # Phase 0 输出
├── data-model.md        # Phase 1 输出
├── quickstart.md        # Phase 1 输出
├── contracts/           # Phase 1 输出
└── tasks.md             # Phase 2 输出（由 __SPECKIT_COMMAND_TASKS__ 生成）
```

### 源码结构（仓库根目录）

<!--
  操作要求：把下面示例替换成该功能真实涉及的目录结构。
  删除未使用的选项，展开真实路径。最终计划中不应保留“Option”标签。
-->

```text
# [未使用则删除] 选项 1：当前仓库常见结构
server.py
web/
tests/
flutter_app/
deploy/
docs/

# [未使用则删除] 选项 2：后端 + 前端
server.py
tests/
web/

# [未使用则删除] 选项 3：移动端 + API
server.py
tests/
flutter_app/lib/
```

**结构决策**：[说明选择的结构，并引用上方真实目录]

## 复杂度追踪

> **仅在宪法检查存在必须解释的 FAIL 时填写**

| 违反项 | 为什么现在需要 | 为什么拒绝更简单方案 |
|--------|----------------|----------------------|
| [例如新增第 4 个服务] | [当前需要] | [为什么现有结构不足] |
| [例如新增 Repository 层] | [具体问题] | [为什么直接 DB 访问不足] |
