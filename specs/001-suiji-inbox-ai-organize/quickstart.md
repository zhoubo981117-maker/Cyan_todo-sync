# 快速验证：随记收件箱 + AI 整理

> 文档语言：除代码标识符、命令、环境变量、API 路径、错误码和第三方专有名词外，本说明使用中文归档。

## 自动验证

在仓库根目录执行：

```powershell
python -m py_compile server.py
python -m unittest tests/test_ai_organizer.py tests/test_records.py
node --check web/app.js
```

期望结果：

- `server.py` 编译无输出。
- `test_ai_organizer.py` 和 `test_records.py` 全部通过。
- `web/app.js` 语法检查无输出。

## 手工验证

1. 启动服务并登录 Web/PWA。
2. 在“随记收件箱”输入一段自然语言，例如“今天和客户聊了续费，明天 10 点整理报价，让小王补风险点”。
3. 点击“保存并整理”，确认页面出现一条 record，包含摘要、类型、标签、日期、情绪和原始输入。
4. 如 AI 识别出待办草稿，勾选后点击“保存选中”，确认任务栏出现正式任务，并显示来源随记。
5. 使用类型、标签或“有关联任务”筛选 records，确认列表按条件变化。
6. 打开某条 record，编辑摘要或标签，刷新后确认修改保留。
7. 删除 record，确认关联任务仍保留，任务来源显示“随记已删除”。
8. 对有日期和关联任务的 record 点击“同步日期到任务”，确认关联任务截止时间被更新。

## 约束确认

- `records` 不进入 `/api/sync/pull` 或 `/api/sync/push`。
- AI 失败时仍保存原始输入，并显示可重试状态。
- AI 密钥不暴露给浏览器或 PWA。
