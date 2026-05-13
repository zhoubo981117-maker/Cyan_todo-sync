# 快速验证：飞书随记入口与 AI 收件箱统一整理

## 前置条件

- 已存在默认用户账号。
- 已配置 `TODO_FEISHU_DEFAULT_EMAIL` 指向该账号。
- 飞书长连接或事件回调已按现有部署方式启用。
- 如需验证 AI 成功路径，配置 `TODO_AI_PROVIDER`、`TODO_AI_API_KEY`、`TODO_AI_MODEL` 和 `TODO_AI_BASE_URL`。

## 本地自动化验证

```powershell
python -m py_compile server.py feishu_client.py
python -m unittest tests/test_feishu.py tests/test_feishu_client.py tests/test_records.py tests/test_ai_organizer.py
```

## 手工验收路径

1. 启动服务并登录 Web/PWA。
2. 向飞书机器人发送：“明天 10 点前整理客户续费报价，让小王补风险点”。
3. 确认飞书收到成功或失败回复。
4. 打开随记收件箱，确认出现来源为飞书的 record。
5. 查看 record 详情，确认能看到原始输入、AI 整理结果、处理状态和任务草稿。
6. 确认正式任务列表没有自动新增任务。
7. 在 Web/PWA 中选择任务草稿并保存为正式任务。
8. 刷新页面，确认正式任务存在，并能追溯来源 record。

## 失败路径验证

1. 临时移除 AI 配置。
2. 发送一条有效飞书文本消息。
3. 确认系统仍保存 record。
4. 确认飞书收到失败反馈。
5. 在 Web/PWA 中打开该 record，确认显示失败状态并可重试。

## 重复消息验证

1. 使用测试或模拟方式发送两次相同飞书消息事件 ID。
2. 确认随记收件箱只出现一条正常 record。
3. 确认第二次处理返回重复状态，不创建正式任务。
