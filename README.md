# Todo Sync (Android + Windows)

This is a small self-hosted todo app:

- Android + Windows: open in a browser, can be installed as a PWA.
- Android App + Windows App: Flutter client (offline-first) included.
- Multi-device sync: all devices log into the same server account and see the same list.
- Subtasks: each subtask can be completed independently.
- Urgency + due time: each todo can be marked with an urgency level and a due datetime.

## Project Submission

- Xiaomi MiMo Orbit submission material: [`docs/xiaomi-mimo-orbit-submission.md`](docs/xiaomi-mimo-orbit-submission.md)

## Run

Use the bundled Python runtime path from Codex (recommended).

```powershell
& 'C:\Users\huawei\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\server.py
```

Then open:

- `http://127.0.0.1:8787/` on Windows
- `http://<your-windows-lan-ip>:8787/` on Android (same Wi-Fi)

## Public Internet (HTTPS)

Recommended: deploy on a Linux VPS with Docker + Caddy (automatic Let's Encrypt).

1. Buy a domain and point `todo.example.com` to your VPS public IP (DNS A record).
2. Open ports `80` and `443` on the VPS security group / firewall.
3. On the VPS, install Docker + Docker Compose.
4. Copy this project to the VPS, edit `Caddyfile` and replace `todo.example.com` with your domain.
5. Start:

```bash
docker compose up -d --build
```

Then open `https://todo.example.com/` on Windows and Android.

## Server Auto Update

On the server, enable a systemd timer that checks GitHub every minute and restarts the app when `origin/main` changes:

```bash
cd /opt/Cyan_todo-sync
git pull
chmod +x deploy/update-from-github.sh
cp deploy/todo-sync-update.service /etc/systemd/system/todo-sync-update.service
cp deploy/todo-sync-update.timer /etc/systemd/system/todo-sync-update.timer
systemctl daemon-reload
systemctl enable --now todo-sync-update.timer
```

Useful checks:

```bash
systemctl list-timers todo-sync-update.timer
journalctl -u todo-sync-update.service -n 100 --no-pager
curl http://127.0.0.1:8787/api/version
```

`/api/version` returns the Git commit currently running on the server. The web page also shows the short commit in the task header, which makes it easier to verify whether the server has deployed the latest GitHub version.

## Password Reset Email

Forgot-password reset links work out of the box at the API level. For real email delivery, configure SMTP environment variables for the `todo-sync` service:

```bash
TODO_SMTP_HOST=smtp.example.com
TODO_SMTP_PORT=465
TODO_SMTP_USER=todo@example.com
TODO_SMTP_PASSWORD=your-smtp-password
TODO_SMTP_FROM=todo@example.com
```

If SMTP is not configured, the reset code and link are written to the server journal for personal testing:

```bash
journalctl -u todo-sync -n 80 --no-pager
```

For QQ Mail, use an SMTP authorization code instead of the normal mailbox password:

```bash
TODO_SMTP_HOST=smtp.qq.com
TODO_SMTP_PORT=465
TODO_SMTP_USER=your@qq.com
TODO_SMTP_PASSWORD=your-qq-mail-smtp-authorization-code
TODO_SMTP_FROM=your@qq.com
```

## AI Todo Organizer

The web app can use Xiaomi MiMo to turn pasted text into editable todo drafts. Configure the AI key on the server only:

```bash
TODO_AI_PROVIDER=xiaomi
TODO_AI_API_KEY=your-xiaomi-mimo-api-key
TODO_AI_MODEL=mimo-v2.5
TODO_AI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
```

After restarting the server, open the app and use the "AI 整理" panel. The AI only creates local drafts in the browser; tasks are saved only after you review and click "保存选中".

## Public Internet (No Domain, IP Testing)

If you don't have a domain yet, you can temporarily expose the app on `http://<server-ip>:8787/`:

```bash
docker compose -f compose.ip.yaml up -d --build
```

Notes:

- This is **HTTP** (not HTTPS). Use it for initial testing only.
- Once you have a domain, switch to `compose.yaml` + `Caddyfile` for HTTPS.

## Flutter App (Offline-First)

This repo includes a Flutter client code skeleton in `flutter_app/`.

You need Flutter SDK installed on your dev machine.

### Create platform projects (one-time)

In the `flutter_app` folder, run:

```bash
flutter create .
```

This generates the Android + Windows runner projects while keeping the existing `lib/` code.

### Run

Set server URL in the app (e.g. `https://todo.example.com`), then register/login.

If you are testing with IP + HTTP (e.g. `http://1.2.3.4:8787`):

- Windows build usually works fine.
- Android may block cleartext HTTP by default. Prefer HTTPS with a domain. If you must test HTTP, enable cleartext traffic in the generated Android project (after `flutter create .`):
  1. Edit `android/app/src/main/AndroidManifest.xml` and set `android:usesCleartextTraffic="true"` in the `<application>` tag (or add a network security config).

### Build

- Android: `flutter build apk`
- Windows: `flutter build windows`

## Sync API

- Pull: `GET /api/sync/pull?since=<utc-iso>` (returns todos/subtasks updated since, including tombstones)
- Push: `POST /api/sync/push` with `{ "todos": [...], "subtasks": [...] }`

## Feishu Inbox

You can let a Feishu custom app bot capture notes by sending message events to this server.
Valid Feishu text messages are saved into the 随记收件箱 as records first. If AI is configured, the server immediately organizes the record into summary, type, tags, dates, sentiment, and optional todo drafts.

Feishu messages do **not** create formal todos directly. Open the Web/PWA inbox, review the record, then save selected drafts as formal todos.

Configure the app service with:

```bash
TODO_FEISHU_ENABLED=1
TODO_FEISHU_VERIFY_TOKEN=your-feishu-event-verification-token
TODO_FEISHU_DEFAULT_EMAIL=you@example.com
```

In Feishu Open Platform, enable bot message events and set the event request URL to:

```text
https://todo.example.com/feishu
```

Do not configure an Encrypt Key for this first version. The server verifies the Feishu Verification Token, but it does not decrypt encrypted event payloads.

All Feishu-created records are saved to the Todo account configured by `TODO_FEISHU_DEFAULT_EMAIL`. The record also stores Feishu sender metadata and the Feishu message ID for duplicate delivery protection.

The bot replies after processing. Success means the message was saved and organized into reviewable drafts; failure means the original input was preserved but AI organization needs to be retried from Web/PWA.

### Feishu Long Connection

If Feishu refuses to save the public callback URL, use Feishu's long connection mode instead. This requires a separate worker process:

```bash
cd /opt/Cyan_todo-sync
python3 -m pip install -r requirements.txt
cp deploy/todo-sync-feishu.service /etc/systemd/system/todo-sync-feishu.service
```

Put the Feishu and AI variables in `/etc/todo-sync.env` so both services can read the same configuration:

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

Then start the worker:

```bash
systemctl daemon-reload
systemctl enable --now todo-sync-feishu
systemctl status todo-sync-feishu --no-pager
journalctl -u todo-sync-feishu -n 100 --no-pager
```

After the worker is running, return to Feishu Open Platform and re-check the long connection status. New bot messages are saved into 随记收件箱 for `TODO_FEISHU_DEFAULT_EMAIL`, then organized into reviewable drafts when AI is configured.

## Daily Plan

The web app includes a "今日计划" panel. Click "生成今日计划" to ask AI for a suggested plan based on current unfinished todos. The first version only displays suggestions and does not create or modify todos automatically.

## Notes

- Data is stored in `data/app.db` (SQLite).
- The server generates a local signing key at `data/secret.key`.
- This is intended for personal / small-team use on a trusted network.
