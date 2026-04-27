from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
DB_PATH = DATA_DIR / "app.db"
SECRET_PATH = DATA_DIR / "secret.key"

HOST = os.environ.get("TODO_HOST", "0.0.0.0")
PORT = int(os.environ.get("TODO_PORT", "8787"))
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("TODO_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
PBKDF2_ITERS = 200_000


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_or_create_secret() -> bytes:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_PATH.exists():
        return SECRET_PATH.read_bytes()
    secret = secrets.token_bytes(32)
    SECRET_PATH.write_bytes(secret)
    return secret


SIGNING_SECRET = load_or_create_secret()


def sign_token(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(_json_bytes(header))
    payload_b64 = _b64url_encode(_json_bytes(payload))
    msg = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(SIGNING_SECRET, msg, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[dict[str, Any]]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        return None
    msg = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(SIGNING_SECRET, msg, hashlib.sha256).digest()
    try:
        got = _b64url_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected, got):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None
    if int(time.time()) > exp:
        return None
    return payload


def password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS)


def validate_password(password: str) -> Optional[str]:
    if len(password) < 6:
        return "password too short (>= 6)"
    return None


def update_user_password(user_id: int, new_password: str) -> None:
    salt = secrets.token_bytes(16)
    pw_hash = password_hash(new_password, salt)
    DB.execute(
        "UPDATE users SET pw_salt = ?, pw_hash = ? WHERE id = ?",
        (salt, pw_hash, user_id),
    )


def open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT NOT NULL UNIQUE,
          pw_salt BLOB NOT NULL,
          pw_hash BLOB NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS todos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_user_id INTEGER NOT NULL,
          title TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          urgency INTEGER NOT NULL DEFAULT 1,
          due_at TEXT NULL,
          done INTEGER NOT NULL DEFAULT 0,
          done_at TEXT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subtasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_user_id INTEGER NOT NULL,
          todo_id INTEGER NOT NULL,
          title TEXT NOT NULL,
          done INTEGER NOT NULL DEFAULT 0,
          done_at TEXT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_todos_owner_updated ON todos(owner_user_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_subtasks_todo ON subtasks(todo_id);
        """
    )


DB = open_db()
init_db(DB)


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def migrate_db(conn: sqlite3.Connection) -> None:
    # Add columns needed for offline sync (stable client IDs + tombstones).
    for table in ("todos", "subtasks"):
        if not _column_exists(conn, table, "client_id"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN client_id TEXT NULL")
        if not _column_exists(conn, table, "deleted_at"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TEXT NULL")

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_todos_owner_client_id ON todos(owner_user_id, client_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_subtasks_owner_client_id ON subtasks(owner_user_id, client_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_todos_owner_updated2 ON todos(owner_user_id, updated_at DESC)"
    )

    # Backfill missing client_id for existing rows.
    rows = conn.execute("SELECT id FROM todos WHERE client_id IS NULL OR client_id = ''").fetchall()
    for r in rows:
        cid = secrets.token_urlsafe(18)
        conn.execute("UPDATE todos SET client_id = ?, updated_at = ? WHERE id = ?", (cid, _utc_now_iso(), int(r["id"])))

    rows = conn.execute("SELECT id FROM subtasks WHERE client_id IS NULL OR client_id = ''").fetchall()
    for r in rows:
        cid = secrets.token_urlsafe(18)
        conn.execute(
            "UPDATE subtasks SET client_id = ?, updated_at = ? WHERE id = ?",
            (cid, _utc_now_iso(), int(r["id"])),
        )


migrate_db(DB)


def json_error(code: int, message: str) -> tuple[int, dict[str, Any]]:
    return code, {"ok": False, "error": message}


def json_ok(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return 200, {"ok": True, **data}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def parse_json_body(handler: BaseHTTPRequestHandler) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        return None, "invalid Content-Length"
    if length <= 0:
        return None, "missing JSON body"
    raw = handler.rfile.read(length)
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, "invalid JSON"
    if not isinstance(obj, dict):
        return None, "JSON must be an object"
    return obj, None


def get_bearer_token(handler: BaseHTTPRequestHandler) -> Optional[str]:
    auth = handler.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[len("Bearer ") :].strip()


@dataclass(frozen=True)
class User:
    id: int
    email: str


def require_user(handler: BaseHTTPRequestHandler) -> Optional[User]:
    token = get_bearer_token(handler)
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    uid = payload.get("uid")
    email = payload.get("email")
    if not isinstance(uid, int) or not isinstance(email, str):
        return None
    return User(id=uid, email=email)


def _normalize_client_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Avoid unbounded IDs; keep storage/abuse in check.
    if len(s) > 128:
        return None
    return s


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in ("1", "true", "yes", "y", "on")


def _parse_since(query: dict[str, list[str]]) -> Optional[str]:
    since = (query.get("since") or [None])[0]
    if not since:
        return None
    since = str(since).strip()
    if len(since) > 64:
        return None
    return since


MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # No inline scripts; keeps XSS blast radius down.
    "Content-Security-Policy": "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
    "style-src 'self'; script-src 'self'; manifest-src 'self'; base-uri 'none'; frame-ancestors 'none'",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "TodoSync/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep console noise low; comment out if you want request logs.
        return

    def _set_cors(self) -> None:
        origin = self.headers.get("Origin")
        if not origin:
            return
        # Default: no cross-origin access for public deployment.
        if ALLOWED_ORIGINS and origin not in ALLOWED_ORIGINS:
            return
        # If allowlist not set, allow same-origin only (Origin must match scheme+host).
        if not ALLOWED_ORIGINS:
            host = self.headers.get("Host", "")
            if not host:
                return
            if not (origin == f"http://{host}" or origin == f"https://{host}"):
                return
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")

    def _set_security_headers(self) -> None:
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)

    def _send_json(self, code: int, obj: dict[str, Any]) -> None:
        body = _json_bytes(obj)
        self.send_response(code)
        self._set_cors()
        self._set_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
        raw = body.encode("utf-8")
        self.send_response(code)
        self._set_cors()
        self._set_security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_text(404, "Not found")
            return
        ext = path.suffix.lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")
        raw = path.read_bytes()
        self.send_response(200)
        self._set_cors()
        self._set_security_headers()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw)))
        if ext in (".html", ".css", ".js", ".webmanifest", ".svg"):
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._set_cors()
        self._set_security_headers()
        self.end_headers()

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            if parsed.path == "/api/health":
                body = _json_bytes({"ok": True, "time": _utc_now_iso()})
                self.send_response(200)
                self._set_cors()
                self._set_security_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return
            self._send_text(405, "Method Not Allowed")
            return
        self._handle_static_head(parsed.path)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("GET", parsed.path, parse_qs(parsed.query))
            return
        self._handle_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("POST", parsed.path, parse_qs(parsed.query))
            return
        self._send_text(404, "Not found")

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("PATCH", parsed.path, parse_qs(parsed.query))
            return
        self._send_text(404, "Not found")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("DELETE", parsed.path, parse_qs(parsed.query))
            return
        self._send_text(404, "Not found")

    def _handle_static(self, path: str) -> None:
        if path == "/" or path == "":
            self._send_file(WEB_DIR / "index.html")
            return
        safe = unquote(path).lstrip("/")
        # Prevent directory traversal
        candidate = (WEB_DIR / safe).resolve()
        if not str(candidate).startswith(str(WEB_DIR.resolve())):
            self._send_text(403, "Forbidden")
            return
        if candidate.is_dir():
            candidate = candidate / "index.html"
        self._send_file(candidate)

    def _handle_static_head(self, path: str) -> None:
        if path == "/" or path == "":
            self._send_file_head(WEB_DIR / "index.html")
            return
        safe = unquote(path).lstrip("/")
        candidate = (WEB_DIR / safe).resolve()
        if not str(candidate).startswith(str(WEB_DIR.resolve())):
            self._send_text(403, "Forbidden")
            return
        if candidate.is_dir():
            candidate = candidate / "index.html"
        self._send_file_head(candidate)

    def _handle_api(self, method: str, path: str, query: dict[str, list[str]]) -> None:
        try:
            if method == "GET" and path == "/api/health":
                code, obj = json_ok({"time": _utc_now_iso()})
                self._send_json(code, obj)
                return

            if method == "POST" and path == "/api/register":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                email = normalize_email(str(body.get("email", "")))
                password = str(body.get("password", ""))
                if "@" not in email or len(email) < 3:
                    self._send_json(*json_error(400, "invalid email"))
                    return
                pw_err = validate_password(password)
                if pw_err:
                    self._send_json(*json_error(400, pw_err))
                    return
                salt = secrets.token_bytes(16)
                pw_hash = password_hash(password, salt)
                try:
                    cur = DB.execute(
                        "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
                        (email, salt, pw_hash, _utc_now_iso()),
                    )
                except sqlite3.IntegrityError:
                    self._send_json(*json_error(409, "email already registered"))
                    return
                user_id = int(cur.lastrowid)
                token = sign_token(
                    {
                        "uid": user_id,
                        "email": email,
                        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
                    }
                )
                self._send_json(*json_ok({"token": token, "user": {"id": user_id, "email": email}}))
                return

            if method == "POST" and path == "/api/login":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                email = normalize_email(str(body.get("email", "")))
                password = str(body.get("password", ""))
                row = DB.execute("SELECT id, email, pw_salt, pw_hash FROM users WHERE email = ?", (email,)).fetchone()
                if not row:
                    self._send_json(*json_error(401, "invalid credentials"))
                    return
                salt = bytes(row["pw_salt"])
                expected = bytes(row["pw_hash"])
                got = password_hash(password, salt)
                if not hmac.compare_digest(expected, got):
                    self._send_json(*json_error(401, "invalid credentials"))
                    return
                user_id = int(row["id"])
                token = sign_token(
                    {
                        "uid": user_id,
                        "email": email,
                        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
                    }
                )
                self._send_json(*json_ok({"token": token, "user": {"id": user_id, "email": email}}))
                return

            user = require_user(self)
            if not user:
                self._send_json(*json_error(401, "unauthorized"))
                return

            if method == "GET" and path == "/api/me":
                self._send_json(*json_ok({"user": {"id": user.id, "email": user.email}}))
                return

            if method == "POST" and path == "/api/password/change":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                current_password = str(body.get("currentPassword", ""))
                new_password = str(body.get("newPassword", ""))
                pw_err = validate_password(new_password)
                if pw_err:
                    self._send_json(*json_error(400, pw_err))
                    return
                row = DB.execute(
                    "SELECT pw_salt, pw_hash FROM users WHERE id = ?",
                    (user.id,),
                ).fetchone()
                if not row:
                    self._send_json(*json_error(404, "user not found"))
                    return
                expected = bytes(row["pw_hash"])
                current_hash = password_hash(current_password, bytes(row["pw_salt"]))
                if not hmac.compare_digest(expected, current_hash):
                    self._send_json(*json_error(401, "current password incorrect"))
                    return
                update_user_password(user.id, new_password)
                self._send_json(*json_ok({"message": "password changed"}))
                return

            if method == "POST" and path == "/api/password/reset":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                new_password = str(body.get("newPassword", ""))
                pw_err = validate_password(new_password)
                if pw_err:
                    self._send_json(*json_error(400, pw_err))
                    return
                update_user_password(user.id, new_password)
                self._send_json(*json_ok({"message": "password reset"}))
                return

            if method == "GET" and path == "/api/todos":
                rows = DB.execute(
                    """
                    SELECT id, client_id, title, note, urgency, due_at, done, done_at, created_at, updated_at
                    FROM todos
                    WHERE owner_user_id = ?
                      AND deleted_at IS NULL
                    ORDER BY
                      done ASC,
                      CASE WHEN due_at IS NULL THEN 1 ELSE 0 END ASC,
                      due_at ASC,
                      urgency DESC,
                      updated_at DESC
                    """,
                    (user.id,),
                ).fetchall()
                todo_ids = [int(r["id"]) for r in rows]
                subtasks_by_todo: dict[int, list[dict[str, Any]]] = {tid: [] for tid in todo_ids}
                if todo_ids:
                    qmarks = ",".join("?" for _ in todo_ids)
                    srows = DB.execute(
                        f"""
                        SELECT id, client_id, todo_id, title, done, done_at, created_at, updated_at
                        FROM subtasks
                        WHERE owner_user_id = ? AND todo_id IN ({qmarks})
                          AND deleted_at IS NULL
                        ORDER BY done ASC, updated_at DESC
                        """,
                        (user.id, *todo_ids),
                    ).fetchall()
                    for s in srows:
                        tid = int(s["todo_id"])
                        subtasks_by_todo.setdefault(tid, []).append(
                            {
                                "id": int(s["id"]),
                                "clientId": s["client_id"],
                                "todoId": tid,
                                "title": s["title"],
                                "done": bool(s["done"]),
                                "doneAt": s["done_at"],
                                "createdAt": s["created_at"],
                                "updatedAt": s["updated_at"],
                            }
                        )
                todos = []
                for r in rows:
                    tid = int(r["id"])
                    todos.append(
                        {
                            "id": tid,
                            "clientId": r["client_id"],
                            "title": r["title"],
                            "note": r["note"],
                            "urgency": int(r["urgency"]),
                            "dueAt": r["due_at"],
                            "done": bool(r["done"]),
                            "doneAt": r["done_at"],
                            "createdAt": r["created_at"],
                            "updatedAt": r["updated_at"],
                            "subtasks": subtasks_by_todo.get(tid, []),
                        }
                    )
                self._send_json(*json_ok({"todos": todos}))
                return

            if method == "POST" and path == "/api/todos":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                title = str(body.get("title", "")).strip()
                if not title:
                    self._send_json(*json_error(400, "title required"))
                    return
                note = str(body.get("note", "")).strip()
                urgency = int(body.get("urgency", 1) or 1)
                urgency = max(0, min(3, urgency))
                due_at = body.get("dueAt")
                if due_at is not None:
                    due_at = str(due_at).strip() or None
                client_id = _normalize_client_id(body.get("clientId")) or secrets.token_urlsafe(18)
                now = _utc_now_iso()
                try:
                    cur = DB.execute(
                    """
                    INSERT INTO todos(owner_user_id, client_id, title, note, urgency, due_at, done, done_at, deleted_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                    """,
                    (user.id, client_id, title, note, urgency, due_at, now, now),
                    )
                except sqlite3.IntegrityError:
                    self._send_json(*json_error(409, "clientId already exists"))
                    return
                todo_id = int(cur.lastrowid)
                self._send_json(*json_ok({"id": todo_id, "clientId": client_id, "updatedAt": now}))
                return

            if path.startswith("/api/todos/"):
                parts = path.strip("/").split("/")
                # /api/todos/{id}
                # /api/todos/{id}/subtasks
                if len(parts) >= 3:
                    todo_id_str = parts[2]
                    if not todo_id_str.isdigit():
                        self._send_json(*json_error(404, "not found"))
                        return
                    todo_id = int(todo_id_str)
                    exists = DB.execute(
                        "SELECT 1 FROM todos WHERE id = ? AND owner_user_id = ? AND deleted_at IS NULL",
                        (todo_id, user.id),
                    ).fetchone()
                    if not exists:
                        self._send_json(*json_error(404, "not found"))
                        return

                    if len(parts) == 3:
                        if method == "PATCH":
                            body, err = parse_json_body(self)
                            if err:
                                self._send_json(*json_error(400, err))
                                return
                            fields = []
                            values: list[Any] = []
                            if "title" in body:
                                title = str(body.get("title", "")).strip()
                                if not title:
                                    self._send_json(*json_error(400, "title required"))
                                    return
                                fields.append("title = ?")
                                values.append(title)
                            if "note" in body:
                                fields.append("note = ?")
                                values.append(str(body.get("note", "")).strip())
                            if "urgency" in body:
                                urgency = int(body.get("urgency", 1) or 1)
                                urgency = max(0, min(3, urgency))
                                fields.append("urgency = ?")
                                values.append(urgency)
                            if "dueAt" in body:
                                due_at = body.get("dueAt")
                                if due_at is not None:
                                    due_at = str(due_at).strip() or None
                                fields.append("due_at = ?")
                                values.append(due_at)
                            if "done" in body:
                                done = bool(body.get("done"))
                                fields.append("done = ?")
                                values.append(1 if done else 0)
                                fields.append("done_at = ?")
                                values.append(_utc_now_iso() if done else None)
                            if not fields:
                                self._send_json(*json_error(400, "no fields to update"))
                                return
                            fields.append("updated_at = ?")
                            values.append(_utc_now_iso())
                            values.extend([todo_id, user.id])
                            DB.execute(
                                f"UPDATE todos SET {', '.join(fields)} WHERE id = ? AND owner_user_id = ?",
                                tuple(values),
                            )
                            self._send_json(*json_ok({}))
                            return

                        if method == "DELETE":
                            now = _utc_now_iso()
                            DB.execute(
                                "UPDATE todos SET deleted_at = ?, updated_at = ? WHERE id = ? AND owner_user_id = ?",
                                (now, now, todo_id, user.id),
                            )
                            self._send_json(*json_ok({"updatedAt": now}))
                            return

                    if len(parts) == 4 and parts[3] == "subtasks" and method == "POST":
                        body, err = parse_json_body(self)
                        if err:
                            self._send_json(*json_error(400, err))
                            return
                        title = str(body.get("title", "")).strip()
                        if not title:
                            self._send_json(*json_error(400, "title required"))
                            return
                        client_id = _normalize_client_id(body.get("clientId")) or secrets.token_urlsafe(18)
                        now = _utc_now_iso()
                        try:
                            cur = DB.execute(
                            """
                            INSERT INTO subtasks(owner_user_id, client_id, todo_id, title, done, done_at, deleted_at, created_at, updated_at)
                            VALUES (?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                            """,
                            (user.id, client_id, todo_id, title, now, now),
                            )
                        except sqlite3.IntegrityError:
                            self._send_json(*json_error(409, "clientId already exists"))
                            return
                        sub_id = int(cur.lastrowid)
                        DB.execute("UPDATE todos SET updated_at = ? WHERE id = ? AND owner_user_id = ?", (now, todo_id, user.id))
                        self._send_json(*json_ok({"id": sub_id, "clientId": client_id, "updatedAt": now}))
                        return

            if path.startswith("/api/subtasks/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3:
                    sub_id_str = parts[2]
                    if not sub_id_str.isdigit():
                        self._send_json(*json_error(404, "not found"))
                        return
                    sub_id = int(sub_id_str)
                    row = DB.execute(
                        "SELECT todo_id FROM subtasks WHERE id = ? AND owner_user_id = ? AND deleted_at IS NULL",
                        (sub_id, user.id),
                    ).fetchone()
                    if not row:
                        self._send_json(*json_error(404, "not found"))
                        return
                    todo_id = int(row["todo_id"])

                    if method == "PATCH":
                        body, err = parse_json_body(self)
                        if err:
                            self._send_json(*json_error(400, err))
                            return
                        fields = []
                        values: list[Any] = []
                        if "title" in body:
                            title = str(body.get("title", "")).strip()
                            if not title:
                                self._send_json(*json_error(400, "title required"))
                                return
                            fields.append("title = ?")
                            values.append(title)
                        if "done" in body:
                            done = bool(body.get("done"))
                            fields.append("done = ?")
                            values.append(1 if done else 0)
                            fields.append("done_at = ?")
                            values.append(_utc_now_iso() if done else None)
                        if not fields:
                            self._send_json(*json_error(400, "no fields to update"))
                            return
                        fields.append("updated_at = ?")
                        now = _utc_now_iso()
                        values.append(now)
                        values.extend([sub_id, user.id])
                        DB.execute(
                            f"UPDATE subtasks SET {', '.join(fields)} WHERE id = ? AND owner_user_id = ?",
                            tuple(values),
                        )
                        DB.execute("UPDATE todos SET updated_at = ? WHERE id = ? AND owner_user_id = ?", (now, todo_id, user.id))
                        self._send_json(*json_ok({}))
                        return

                    if method == "DELETE":
                        now = _utc_now_iso()
                        DB.execute(
                            "UPDATE subtasks SET deleted_at = ?, updated_at = ? WHERE id = ? AND owner_user_id = ?",
                            (now, now, sub_id, user.id),
                        )
                        DB.execute("UPDATE todos SET updated_at = ? WHERE id = ? AND owner_user_id = ?", (now, todo_id, user.id))
                        self._send_json(*json_ok({"updatedAt": now}))
                        return

            if method == "GET" and path == "/api/sync/pull":
                since = _parse_since(query)
                rows = DB.execute(
                    """
                    SELECT id, client_id, title, note, urgency, due_at, done, done_at, deleted_at, created_at, updated_at
                    FROM todos
                    WHERE owner_user_id = ?
                      AND (? IS NULL OR updated_at > ?)
                    ORDER BY updated_at ASC
                    """,
                    (user.id, since, since),
                ).fetchall()
                todo_int_by_client: dict[str, int] = {}
                todos = []
                for r in rows:
                    cid = r["client_id"] or ""
                    todo_int_by_client[cid] = int(r["id"])
                    todos.append(
                        {
                            "clientId": cid,
                            "title": r["title"],
                            "note": r["note"],
                            "urgency": int(r["urgency"]),
                            "dueAt": r["due_at"],
                            "done": bool(r["done"]),
                            "doneAt": r["done_at"],
                            "deletedAt": r["deleted_at"],
                            "createdAt": r["created_at"],
                            "updatedAt": r["updated_at"],
                        }
                    )

                srows = DB.execute(
                    """
                    SELECT s.client_id AS client_id,
                           t.client_id AS todo_client_id,
                           s.title AS title,
                           s.done AS done,
                           s.done_at AS done_at,
                           s.deleted_at AS deleted_at,
                           s.created_at AS created_at,
                           s.updated_at AS updated_at
                    FROM subtasks s
                    JOIN todos t ON t.id = s.todo_id
                    WHERE s.owner_user_id = ?
                      AND (? IS NULL OR s.updated_at > ?)
                    ORDER BY s.updated_at ASC
                    """,
                    (user.id, since, since),
                ).fetchall()
                subtasks = []
                for s in srows:
                    subtasks.append(
                        {
                            "clientId": s["client_id"] or "",
                            "todoClientId": s["todo_client_id"] or "",
                            "title": s["title"],
                            "done": bool(s["done"]),
                            "doneAt": s["done_at"],
                            "deletedAt": s["deleted_at"],
                            "createdAt": s["created_at"],
                            "updatedAt": s["updated_at"],
                        }
                    )
                self._send_json(*json_ok({"serverTime": _utc_now_iso(), "todos": todos, "subtasks": subtasks}))
                return

            if method == "POST" and path == "/api/sync/push":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                now = _utc_now_iso()

                todos_in = body.get("todos")
                subs_in = body.get("subtasks")
                if todos_in is None:
                    todos_in = []
                if subs_in is None:
                    subs_in = []
                if not isinstance(todos_in, list) or not isinstance(subs_in, list):
                    self._send_json(*json_error(400, "todos/subtasks must be arrays"))
                    return

                # Apply todos first (so subtasks can resolve todoClientId).
                for item in todos_in:
                    if not isinstance(item, dict):
                        continue
                    cid = _normalize_client_id(item.get("clientId"))
                    if not cid:
                        continue
                    deleted = _parse_bool(item.get("deleted")) or (item.get("deletedAt") is not None)
                    if deleted:
                        DB.execute(
                            """
                            UPDATE todos
                            SET deleted_at = ?, updated_at = ?
                            WHERE owner_user_id = ? AND client_id = ?
                            """,
                            (now, now, user.id, cid),
                        )
                        continue

                    title = str(item.get("title", "")).strip()
                    if not title:
                        continue
                    note = str(item.get("note", "")).strip()
                    urgency = int(item.get("urgency", 1) or 1)
                    urgency = max(0, min(3, urgency))
                    due_at = item.get("dueAt")
                    if due_at is not None:
                        due_at = str(due_at).strip() or None
                    done = _parse_bool(item.get("done"))
                    done_at = now if done else None

                    row = DB.execute(
                        "SELECT id FROM todos WHERE owner_user_id = ? AND client_id = ?",
                        (user.id, cid),
                    ).fetchone()
                    if row:
                        DB.execute(
                            """
                            UPDATE todos
                            SET title = ?, note = ?, urgency = ?, due_at = ?, done = ?, done_at = ?, deleted_at = NULL, updated_at = ?
                            WHERE owner_user_id = ? AND client_id = ?
                            """,
                            (title, note, urgency, due_at, 1 if done else 0, done_at, now, user.id, cid),
                        )
                    else:
                        try:
                            DB.execute(
                                """
                                INSERT INTO todos(
                                  owner_user_id, client_id, title, note, urgency, due_at,
                                  done, done_at, deleted_at, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                                """,
                                (user.id, cid, title, note, urgency, due_at, 1 if done else 0, done_at, now, now),
                            )
                        except sqlite3.IntegrityError:
                            # Client IDs are per user; ignore duplicates in race.
                            pass

                # Resolve todo_client_id -> todo_id int for subtasks.
                todo_map_rows = DB.execute(
                    "SELECT id, client_id FROM todos WHERE owner_user_id = ?",
                    (user.id,),
                ).fetchall()
                todo_id_by_client = {str(r["client_id"] or ""): int(r["id"]) for r in todo_map_rows}

                for item in subs_in:
                    if not isinstance(item, dict):
                        continue
                    cid = _normalize_client_id(item.get("clientId"))
                    todo_cid = _normalize_client_id(item.get("todoClientId"))
                    if not cid or not todo_cid:
                        continue
                    todo_id = todo_id_by_client.get(todo_cid)
                    if not todo_id:
                        continue

                    deleted = _parse_bool(item.get("deleted")) or (item.get("deletedAt") is not None)
                    if deleted:
                        DB.execute(
                            """
                            UPDATE subtasks
                            SET deleted_at = ?, updated_at = ?
                            WHERE owner_user_id = ? AND client_id = ?
                            """,
                            (now, now, user.id, cid),
                        )
                        DB.execute(
                            "UPDATE todos SET updated_at = ? WHERE id = ? AND owner_user_id = ?",
                            (now, todo_id, user.id),
                        )
                        continue

                    title = str(item.get("title", "")).strip()
                    if not title:
                        continue
                    done = _parse_bool(item.get("done"))
                    done_at = now if done else None

                    row = DB.execute(
                        "SELECT id FROM subtasks WHERE owner_user_id = ? AND client_id = ?",
                        (user.id, cid),
                    ).fetchone()
                    if row:
                        DB.execute(
                            """
                            UPDATE subtasks
                            SET todo_id = ?, title = ?, done = ?, done_at = ?, deleted_at = NULL, updated_at = ?
                            WHERE owner_user_id = ? AND client_id = ?
                            """,
                            (todo_id, title, 1 if done else 0, done_at, now, user.id, cid),
                        )
                    else:
                        try:
                            DB.execute(
                                """
                                INSERT INTO subtasks(
                                  owner_user_id, client_id, todo_id, title,
                                  done, done_at, deleted_at, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                                """,
                                (user.id, cid, todo_id, title, 1 if done else 0, done_at, now, now),
                            )
                        except sqlite3.IntegrityError:
                            pass
                    DB.execute(
                        "UPDATE todos SET updated_at = ? WHERE id = ? AND owner_user_id = ?",
                        (now, todo_id, user.id),
                    )

                self._send_json(*json_ok({"serverTime": now}))
                return

            self._send_json(*json_error(404, "not found"))
        except Exception:
            # Avoid leaking details to clients; keep it deterministic.
            self._send_json(*json_error(500, "internal error"))

    def _send_file_head(self, path: Path) -> None:
        if not path.is_file():
            self._send_text(404, "Not found")
            return
        ext = path.suffix.lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")
        size = path.stat().st_size
        self.send_response(200)
        self._set_cors()
        self._set_security_headers()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(size))
        if ext in (".html", ".css", ".js", ".webmanifest", ".svg"):
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()


def main() -> None:
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"TodoSync server listening on http://{HOST}:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
