# Todo Sync (Android + Windows)

This is a small self-hosted todo app:

- Android + Windows: open in a browser, can be installed as a PWA.
- Android App + Windows App: Flutter client (offline-first) included.
- Multi-device sync: all devices log into the same server account and see the same list.
- Subtasks: each subtask can be completed independently.
- Urgency + due time: each todo can be marked with an urgency level and a due datetime.

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
```

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

## Notes

- Data is stored in `data/app.db` (SQLite).
- The server generates a local signing key at `data/secret.key`.
- This is intended for personal / small-team use on a trusted network.
