# 随记代办同步（Android + Windows）

这是一个小型自托管代办应用，适合个人或小团队在自己的服务器上使用：

- Android + Windows：直接用浏览器打开，也可以安装为 PWA。
- Android App + Windows App：仓库内包含 Flutter 客户端骨架，支持离线优先。
- 多设备同步：所有设备登录同一个服务端账号后，会看到同一份清单。
- 子任务：每个子任务都可以独立完成。
- 优先级与完成时间：每条代办都可以设置紧急程度和完成时间。

## 项目提交材料

- 小米 MiMo Orbit 提交材料：[`docs/xiaomi-mimo-orbit-submission.md`](docs/xiaomi-mimo-orbit-submission.md)

## 本地运行

推荐使用 Codex 自带的 Python 运行时：

```powershell
& 'C:\Users\huawei\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\server.py
```

启动后打开：

- Windows：`http://127.0.0.1:8787/`
- Android：`http://<your-windows-lan-ip>:8787/`，需要和 Windows 在同一个 Wi-Fi 下

## 公网部署（HTTPS）

推荐部署到 Linux VPS，并使用 Docker + Caddy 自动申请 Let's Encrypt 证书。

1. 购买域名，并把 `todo.example.com` 的 DNS A 记录指向 VPS 公网 IP。
2. 在 VPS 安全组或防火墙中开放 `80` 和 `443` 端口。
3. 在 VPS 安装 Docker 和 Docker Compose。
4. 把本项目复制到 VPS，编辑 `Caddyfile`，把 `todo.example.com` 替换成你的域名。
5. 启动服务：

```bash
docker compose up -d --build
```

然后在 Windows 和 Android 上打开 `https://todo.example.com/`。

## 服务端自动更新

在服务器上启用 systemd timer 后，服务会每分钟检查 GitHub；当 `origin/main` 更新时自动合并并重启应用：

```bash
cd /opt/Cyan_todo-sync
git pull
chmod +x deploy/update-from-github.sh
cp deploy/todo-sync-update.service /etc/systemd/system/todo-sync-update.service
cp deploy/todo-sync-update.timer /etc/systemd/system/todo-sync-update.timer
systemctl daemon-reload
systemctl enable --now todo-sync-update.timer
```

常用检查命令：

```bash
systemctl list-timers todo-sync-update.timer
journalctl -u todo-sync-update.service -n 100 --no-pager
curl http://127.0.0.1:8787/api/version
```

`/api/version` 会返回服务器当前运行的 Git 提交。网页任务栏也会显示短提交号，方便确认服务器是否已经部署到 GitHub 最新版本。

## 密码重置邮件

忘记密码的重置链接在 API 层可以直接使用。若要真正发送邮件，需要为 `todo-sync` 服务配置 SMTP 环境变量：

```bash
TODO_SMTP_HOST=smtp.example.com
TODO_SMTP_PORT=465
TODO_SMTP_USER=todo@example.com
TODO_SMTP_PASSWORD=your-smtp-password
TODO_SMTP_FROM=todo@example.com
```

如果没有配置 SMTP，重置验证码和链接会写入服务日志，便于个人测试：

```bash
journalctl -u todo-sync -n 80 --no-pager
```

QQ 邮箱需要使用 SMTP 授权码，不要使用普通邮箱密码：

```bash
TODO_SMTP_HOST=smtp.qq.com
TODO_SMTP_PORT=465
TODO_SMTP_USER=your@qq.com
TODO_SMTP_PASSWORD=your-qq-mail-smtp-authorization-code
TODO_SMTP_FROM=your@qq.com
```

## AI 代办整理

网页端可以调用小米 MiMo，把粘贴的自然语言内容整理成可编辑的代办草稿。AI 密钥只需要配置在服务端：

```bash
TODO_AI_PROVIDER=xiaomi
TODO_AI_API_KEY=your-xiaomi-mimo-api-key
TODO_AI_MODEL=mimo-v2.5
TODO_AI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
```

重启服务后，打开应用并使用“随记收件箱”。AI 只会先生成浏览器里的草稿，必须由你审查并点击“保存选中”后，才会写入正式代办。

## 公网部署（无域名，仅 IP 测试）

如果暂时没有域名，可以先用 `http://<server-ip>:8787/` 暴露服务：

```bash
docker compose -f compose.ip.yaml up -d --build
```

注意：

- 这是 **HTTP**，不是 HTTPS，只建议初期测试使用。
- 有域名后，切换到 `compose.yaml` + `Caddyfile` 使用 HTTPS。

## Flutter 客户端（离线优先）

仓库的 `flutter_app/` 目录包含 Flutter 客户端代码骨架。

开发机器需要先安装 Flutter SDK。

### 创建平台工程（一次性）

进入 `flutter_app` 目录后运行：

```bash
flutter create .
```

这会生成 Android + Windows runner 工程，同时保留现有 `lib/` 代码。

### 运行

在客户端里设置服务端 URL，例如 `https://todo.example.com`，然后注册或登录。

如果用 IP + HTTP 测试，例如 `http://1.2.3.4:8787`：

- Windows 构建通常可以直接使用。
- Android 默认可能会拦截明文 HTTP。优先使用带域名的 HTTPS；如果必须测试 HTTP，在执行 `flutter create .` 后，编辑 `android/app/src/main/AndroidManifest.xml`，在 `<application>` 标签上设置 `android:usesCleartextTraffic="true"`，或添加网络安全配置。

### 构建

- Android：`flutter build apk`
- Windows：`flutter build windows`

## 同步 API

- 拉取：`GET /api/sync/pull?since=<utc-iso>`，返回指定时间后更新的 todos/subtasks，包括删除标记。
- 推送：`POST /api/sync/push`，请求体为 `{ "todos": [...], "subtasks": [...] }`。

## 飞书收件箱

可以让飞书自建应用机器人把消息事件发送到本服务，从而自动收集随手记录。

有效的飞书文本消息会先保存为随记收件箱里的 record。如果已配置 AI，服务端会立即整理摘要、类型、标签、日期、情绪和可选代办草稿。

飞书消息**不会**直接创建正式 todo。需要打开 Web/PWA 的随记收件箱，审查 record 后，再把选中的草稿保存为正式代办。

应用服务需要配置：

```bash
TODO_FEISHU_ENABLED=1
TODO_FEISHU_VERIFY_TOKEN=your-feishu-event-verification-token
TODO_FEISHU_DEFAULT_EMAIL=you@example.com
```

在飞书开放平台启用机器人消息事件，并把事件请求地址设置为：

```text
https://todo.example.com/feishu
```

第一版不要配置 Encrypt Key。服务端会校验飞书 Verification Token，但不会解密加密事件载荷。

所有飞书创建的 record 都会保存到 `TODO_FEISHU_DEFAULT_EMAIL` 配置的 Todo 账号下。record 也会保存飞书发送者元数据和飞书消息 ID，用于避免重复投递。

机器人会在处理后回复。成功表示消息已经保存并整理成可审查草稿；失败表示原始输入已保留，但需要在 Web/PWA 中重新触发 AI 整理。

### 飞书长连接

如果飞书无法保存公网回调 URL，可以改用飞书长连接模式。该模式需要单独运行一个 worker 进程：

```bash
cd /opt/Cyan_todo-sync
python3 -m pip install -r requirements.txt
cp deploy/todo-sync-feishu.service /etc/systemd/system/todo-sync-feishu.service
```

把飞书和 AI 变量放入 `/etc/todo-sync.env`，让两个服务读取同一份配置：

```bash
TODO_FEISHU_ENABLED=1
TODO_FEISHU_APP_ID=cli_xxx
TODO_FEISHU_APP_SECRET=your-feishu-app-secret
TODO_FEISHU_DEFAULT_EMAIL=you@example.com
TODO_AI_PROVIDER=xiaomi
TODO_AI_API_KEY=your-xiaomi-mimo-api-key
TODO_AI_MODEL=mimo-v2.5
TODO_AI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
```

然后启动 worker：

```bash
systemctl daemon-reload
systemctl enable --now todo-sync-feishu
systemctl status todo-sync-feishu --no-pager
journalctl -u todo-sync-feishu -n 100 --no-pager
```

worker 运行后，回到飞书开放平台重新检查长连接状态。新的机器人消息会保存到 `TODO_FEISHU_DEFAULT_EMAIL` 对应账号的随记收件箱，并在配置 AI 后整理为可审查草稿。

## 今日计划

网页端包含“今日计划”面板。点击“生成今日计划”后，AI 会根据当前未完成任务给出当天执行建议。第一版只展示建议，不会自动创建或修改代办。

## 说明

- 数据保存在 `data/app.db`（SQLite）。
- 服务端会在 `data/secret.key` 生成本地签名密钥。
- 本项目面向个人或小团队自托管场景，适合部署在可信网络中。
