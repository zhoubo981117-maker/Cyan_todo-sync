from __future__ import annotations

import base64
import calendar
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib import error as urlerror
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("TODO_DATA_DIR", str(ROOT / "data")))
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
FEISHU_ENABLED = os.environ.get("TODO_FEISHU_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")
FEISHU_VERIFY_TOKEN = os.environ.get("TODO_FEISHU_VERIFY_TOKEN", "").strip()
FEISHU_DEFAULT_EMAIL = os.environ.get("TODO_FEISHU_DEFAULT_EMAIL", "").strip().lower()
AI_PROVIDER = os.environ.get("TODO_AI_PROVIDER", "").strip().lower()
AI_API_KEY = os.environ.get("TODO_AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("TODO_AI_MODEL", "mimo-v2.5").strip()
AI_BASE_URL = os.environ.get("TODO_AI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1").strip().rstrip("/")
AI_MAX_INPUT_CHARS = int(os.environ.get("TODO_AI_MAX_INPUT_CHARS", "6000") or "6000")
CN_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
RESET_TOKEN_TTL_SECONDS = 60 * 30  # 30 minutes
RESET_REQUEST_COOLDOWN_SECONDS = 60
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


def _git_version() -> dict[str, str]:
    env_version = os.environ.get("TODO_APP_VERSION", "").strip()
    if env_version:
        return {"commit": env_version[:40], "short": env_version[:7], "source": "env"}
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except Exception:
        commit = "unknown"
    return {
        "commit": commit,
        "short": commit[:7] if commit != "unknown" else "unknown",
        "source": "git" if commit != "unknown" else "unknown",
    }


APP_VERSION = _git_version()


def _normalize_repeat_rule(value: Any) -> str:
    rule = str(value or "none").strip().lower()
    if rule not in ("none", "daily", "weekly", "monthly"):
        return "none"
    return rule


def _normalize_reminder_minutes(value: Any) -> Optional[int]:
    if value in (None, "", "none"):
        return None
    if value == "at_due":
        return 0
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return None
    return minutes if minutes in (0, 10, 30, 60) else None


def _next_due_at(due_at: Optional[str], rule: str) -> Optional[str]:
    if not due_at or rule == "none":
        return due_at
    try:
        dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
    except ValueError:
        return due_at
    if rule == "daily":
        return (dt + timedelta(days=1)).replace(microsecond=0).isoformat()
    if rule == "weekly":
        return (dt + timedelta(days=7)).replace(microsecond=0).isoformat()
    if rule == "monthly":
        month = dt.month + 1
        year = dt.year
        if month > 12:
            month = 1
            year += 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day, microsecond=0).isoformat()
    return due_at


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


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _send_reset_email(email: str, reset_url: str, code: str) -> bool:
    host = os.environ.get("TODO_SMTP_HOST", "").strip()
    user = os.environ.get("TODO_SMTP_USER", "").strip()
    password = os.environ.get("TODO_SMTP_PASSWORD", "").strip()
    sender = os.environ.get("TODO_SMTP_FROM", user).strip()
    if not host or not user or not password or not sender:
        print(f"[password-reset] SMTP not configured. email={email} code={code} url={reset_url}", flush=True)
        return False

    port = int(os.environ.get("TODO_SMTP_PORT", "465"))
    msg = EmailMessage()
    msg["Subject"] = "Todo Sync 密码重置"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(
        f"你的 Todo Sync 密码重置验证码是：{code}\n\n"
        f"也可以打开这个链接完成重置：\n{reset_url}\n\n"
        "验证码 30 分钟内有效。如果不是你本人操作，可以忽略这封邮件。"
    )
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=10) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
    print(f"[password-reset] SMTP send success. email={email} host={host} port={port} sender={sender}", flush=True)
    return True


def _smtp_configured() -> bool:
    return all(
        os.environ.get(name, "").strip()
        for name in ("TODO_SMTP_HOST", "TODO_SMTP_USER", "TODO_SMTP_PASSWORD")
    ) and bool(os.environ.get("TODO_SMTP_FROM", os.environ.get("TODO_SMTP_USER", "")).strip())


def _smtp_status_for_log() -> str:
    host = os.environ.get("TODO_SMTP_HOST", "").strip()
    port = os.environ.get("TODO_SMTP_PORT", "465").strip()
    user = os.environ.get("TODO_SMTP_USER", "").strip()
    sender = os.environ.get("TODO_SMTP_FROM", user).strip()
    password_set = bool(os.environ.get("TODO_SMTP_PASSWORD", "").strip())
    configured = _smtp_configured()
    return (
        f"configured={configured} host={host or '-'} port={port or '-'} "
        f"user={user or '-'} sender={sender or '-'} passwordSet={password_set}"
    )


def _recent_password_reset_request(user_id: int, now: datetime) -> Optional[int]:
    row = DB.execute(
        """
        SELECT created_at
        FROM password_reset_tokens
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if not row:
        return None
    try:
        created = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
    except ValueError:
        return None
    elapsed = int((now - created).total_seconds())
    remaining = RESET_REQUEST_COOLDOWN_SECONDS - elapsed
    return remaining if remaining > 0 else None


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
          repeat_rule TEXT NOT NULL DEFAULT 'none',
          reminder_minutes INTEGER NULL,
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

        CREATE TABLE IF NOT EXISTS records (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_user_id INTEGER NOT NULL,
          original_input TEXT NOT NULL,
          source TEXT NOT NULL DEFAULT 'web',
          source_event_id TEXT NOT NULL DEFAULT '',
          source_sender_json TEXT NOT NULL DEFAULT '{}',
          summary TEXT NOT NULL DEFAULT '',
          record_type TEXT NOT NULL DEFAULT 'other',
          tags_json TEXT NOT NULL DEFAULT '[]',
          dates_json TEXT NOT NULL DEFAULT '[]',
          sentiment TEXT NOT NULL DEFAULT 'neutral',
          ai_status TEXT NOT NULL DEFAULT 'pending',
          ai_error TEXT NOT NULL DEFAULT '',
          deleted_at TEXT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          token_hash TEXT NOT NULL UNIQUE,
          code TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          used_at TEXT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_todos_owner_updated ON todos(owner_user_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_subtasks_todo ON subtasks(todo_id);
        CREATE INDEX IF NOT EXISTS idx_records_owner_updated ON records(owner_user_id, updated_at DESC);
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
    if not _column_exists(conn, "todos", "repeat_rule"):
        conn.execute("ALTER TABLE todos ADD COLUMN repeat_rule TEXT NOT NULL DEFAULT 'none'")
    if not _column_exists(conn, "todos", "reminder_minutes"):
        conn.execute("ALTER TABLE todos ADD COLUMN reminder_minutes INTEGER NULL")
    if not _column_exists(conn, "todos", "source_record_id"):
        conn.execute("ALTER TABLE todos ADD COLUMN source_record_id INTEGER NULL")
    if not _column_exists(conn, "records", "source"):
        conn.execute("ALTER TABLE records ADD COLUMN source TEXT NOT NULL DEFAULT 'web'")
    if not _column_exists(conn, "records", "source_event_id"):
        conn.execute("ALTER TABLE records ADD COLUMN source_event_id TEXT NOT NULL DEFAULT ''")
    if not _column_exists(conn, "records", "source_sender_json"):
        conn.execute("ALTER TABLE records ADD COLUMN source_sender_json TEXT NOT NULL DEFAULT '{}'")

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_todos_owner_client_id ON todos(owner_user_id, client_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_subtasks_owner_client_id ON subtasks(owner_user_id, client_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_todos_owner_updated2 ON todos(owner_user_id, updated_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_records_owner_updated2 ON records(owner_user_id, updated_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_todos_source_record ON todos(owner_user_id, source_record_id)"
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_records_feishu_event
        ON records(owner_user_id, source, source_event_id)
        WHERE source = 'feishu' AND source_event_id IS NOT NULL AND source_event_id <> ''
        """
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


def _clean_ai_string(value: Any, max_len: int) -> str:
    return " ".join(str(value or "").strip().split())[:max_len]


def _normalize_ai_due_at(value: Any) -> Optional[str]:
    if value in (None, "", "null"):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(microsecond=0).isoformat()


def sanitize_ai_todo_items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        raw_items = raw.get("items")
    else:
        raw_items = raw
    if not isinstance(raw_items, list):
        raise ValueError("AI returned invalid item list")
    items: list[dict[str, Any]] = []
    for raw_item in raw_items[:12]:
        if not isinstance(raw_item, dict):
            continue
        title = _clean_ai_string(raw_item.get("title"), 120)
        if not title:
            continue
        note = _clean_ai_string(raw_item.get("note"), 500)
        try:
            urgency = int(raw_item.get("urgency", 1) or 1)
        except (TypeError, ValueError):
            urgency = 1
        urgency = max(0, min(3, urgency))
        subtasks_raw = raw_item.get("subtasks")
        subtasks: list[str] = []
        if isinstance(subtasks_raw, list):
            for subtask in subtasks_raw[:12]:
                sub_title = _clean_ai_string(subtask, 120)
                if sub_title:
                    subtasks.append(sub_title)
        items.append(
            {
                "title": title,
                "note": note,
                "urgency": urgency,
                "dueAt": _normalize_ai_due_at(raw_item.get("dueAt")),
                "subtasks": subtasks,
            }
        )
    return items


RECORD_TYPES = {"task", "note", "idea", "reminder", "event", "question", "other"}
RECORD_SENTIMENTS = {"positive", "neutral", "negative"}
RECORD_STATUSES = {"pending", "processing", "ready", "failed"}


def _normalize_record_type(value: Any) -> str:
    raw = str(value or "other").strip().lower()
    aliases = {
        "任务": "task",
        "待办": "task",
        "笔记": "note",
        "灵感": "idea",
        "提醒": "reminder",
        "事件": "event",
        "问题": "question",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in RECORD_TYPES else "other"


def _normalize_record_sentiment(value: Any) -> str:
    raw = str(value or "neutral").strip().lower()
    aliases = {"积极": "positive", "正面": "positive", "中性": "neutral", "消极": "negative", "负面": "negative"}
    raw = aliases.get(raw, raw)
    return raw if raw in RECORD_SENTIMENTS else "neutral"


def _normalize_record_tags(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else []
    tags: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        tag = _clean_ai_string(item, 24)
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
        if len(tags) >= 8:
            break
    return tags


def _normalize_record_dates(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else []
    dates: list[str] = []
    seen: set[str] = set()
    for item in raw_items[:8]:
        normalized = _normalize_ai_due_at(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            dates.append(normalized)
    return dates


def sanitize_record_fields(raw: Any, source_text: str = "") -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    summary = _clean_ai_string(data.get("summary") or source_text, 240)
    return {
        "summary": summary,
        "type": _normalize_record_type(data.get("type")),
        "tags": _normalize_record_tags(data.get("tags")),
        "dates": _normalize_record_dates(data.get("dates")),
        "sentiment": _normalize_record_sentiment(data.get("sentiment")),
    }


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return value if isinstance(value, list) else []


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return value if isinstance(value, dict) else {}


def _linked_todos_for_record(conn: sqlite3.Connection, user_id: int, record_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, title, done, due_at, deleted_at
        FROM todos
        WHERE owner_user_id = ? AND source_record_id = ? AND deleted_at IS NULL
        ORDER BY updated_at DESC
        """,
        (user_id, record_id),
    ).fetchall()
    return [
        {
            "id": int(r["id"]),
            "title": r["title"],
            "done": bool(r["done"]),
            "dueAt": r["due_at"],
            "deleted": bool(r["deleted_at"]),
        }
        for r in rows
    ]


def serialize_record_row(conn: sqlite3.Connection, row: sqlite3.Row, include_links: bool = True) -> dict[str, Any]:
    record_id = int(row["id"])
    user_id = int(row["owner_user_id"])
    record = {
        "id": record_id,
        "originalInput": row["original_input"],
        "source": row["source"],
        "sourceEventId": row["source_event_id"],
        "sourceSender": _json_object(row["source_sender_json"]),
        "summary": row["summary"],
        "type": row["record_type"],
        "tags": _json_list(row["tags_json"]),
        "dates": _json_list(row["dates_json"]),
        "sentiment": row["sentiment"],
        "aiStatus": row["ai_status"],
        "aiError": row["ai_error"],
        "linkedTodos": [],
        "deletedAt": row["deleted_at"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }
    if include_links:
        record["linkedTodos"] = _linked_todos_for_record(conn, user_id, record_id)
    return record


def create_record(
    conn: sqlite3.Connection,
    user_id: int,
    text: str,
    ai_status: str = "pending",
    source: str = "web",
    source_event_id: str = "",
    source_sender: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    now = _utc_now_iso()
    summary = _clean_ai_string(text, 240)
    clean_source = _clean_ai_string(source or "web", 32) or "web"
    clean_event_id = _clean_ai_string(source_event_id, 160)
    sender_json = json.dumps(source_sender if isinstance(source_sender, dict) else {}, ensure_ascii=False)
    cur = conn.execute(
        """
        INSERT INTO records(owner_user_id, original_input, source, source_event_id, source_sender_json, summary, record_type, tags_json, dates_json, sentiment, ai_status, ai_error, deleted_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'other', '[]', '[]', 'neutral', ?, '', NULL, ?, ?)
        """,
        (
            user_id,
            text,
            clean_source,
            clean_event_id,
            sender_json,
            summary,
            ai_status if ai_status in RECORD_STATUSES else "pending",
            now,
            now,
        ),
    )
    row = conn.execute("SELECT * FROM records WHERE id = ?", (int(cur.lastrowid),)).fetchone()
    return serialize_record_row(conn, row)


def update_record_ai_result(conn: sqlite3.Connection, user_id: int, record_id: int, fields: dict[str, Any], status: str, error: str = "") -> dict[str, Any]:
    now = _utc_now_iso()
    conn.execute(
        """
        UPDATE records
        SET summary = ?, record_type = ?, tags_json = ?, dates_json = ?, sentiment = ?,
            ai_status = ?, ai_error = ?, updated_at = ?
        WHERE id = ? AND owner_user_id = ?
        """,
        (
            fields["summary"],
            fields["type"],
            json.dumps(fields["tags"], ensure_ascii=False),
            json.dumps(fields["dates"], ensure_ascii=False),
            fields["sentiment"],
            status,
            _clean_ai_string(error, 300),
            now,
            record_id,
            user_id,
        ),
    )
    row = conn.execute("SELECT * FROM records WHERE id = ? AND owner_user_id = ?", (record_id, user_id)).fetchone()
    return serialize_record_row(conn, row)


def organize_record_ai(conn: sqlite3.Connection, user_id: int, record_id: int, text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not AI_API_KEY:
        failed = update_record_ai_result(
            conn,
            user_id,
            record_id,
            sanitize_record_fields({}, text),
            "failed",
            "AI not configured",
        )
        return failed, []
    try:
        fields, items = call_xiaomi_record_organizer(text)
    except ValueError:
        failed = update_record_ai_result(
            conn,
            user_id,
            record_id,
            sanitize_record_fields({}, text),
            "failed",
            "AI returned invalid JSON",
        )
        return failed, []
    except RuntimeError as exc:
        failed = update_record_ai_result(
            conn,
            user_id,
            record_id,
            sanitize_record_fields({}, text),
            "failed",
            str(exc),
        )
        return failed, []
    ready = update_record_ai_result(conn, user_id, record_id, fields, "ready", "")
    return ready, items


def _strip_json_code_fence(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def parse_ai_items_from_text(text: str) -> list[dict[str, Any]]:
    cleaned = _strip_json_code_fence(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("AI returned invalid JSON") from exc
    return sanitize_ai_todo_items(parsed)


def _record_ai_prompt(now: Optional[datetime] = None) -> str:
    current = _cn_now(now)
    tomorrow = current + timedelta(days=1)
    return (
        "你是随记收件箱整理助手。把用户输入整理为一条主 record 和可选待办草稿。"
        f"当前日期时间是北京时间/Asia/Shanghai：{current.strftime('%Y-%m-%d %H:%M')}。"
        f"今天是 {current.strftime('%Y-%m-%d')}，明天是 {tomorrow.strftime('%Y-%m-%d')}。"
        "只输出严格 JSON，不要 Markdown，不要解释。JSON 格式："
        '{"record":{"summary":"一句话摘要","type":"task|note|idea|reminder|event|question|other",'
        '"tags":["标签"],"dates":["ISO8601时间"],"sentiment":"positive|neutral|negative"},'
        '"items":[{"title":"任务标题","note":"补充说明","urgency":1,"dueAt":"ISO8601时间或null","subtasks":["子任务"]}]}。'
        "第一版只能生成一条主 record。无法判断的字段使用 other、neutral、空数组或 null。"
    )


def parse_record_ai_result_from_text(text: str, source_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cleaned = _strip_json_code_fence(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("AI returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("AI returned invalid JSON")
    record = sanitize_record_fields(parsed.get("record"), source_text)
    items = sanitize_ai_todo_items(parsed.get("items", []))
    return record, items


def call_xiaomi_record_organizer(text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    content = call_xiaomi_chat_messages(_record_ai_prompt(), text, temperature=0.2)
    fields, items = parse_record_ai_result_from_text(content, text)
    return fields, _apply_relative_due_fallback(items, text)


def _cn_now(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(CN_TZ).replace(microsecond=0)
    if now.tzinfo is None:
        return now.replace(tzinfo=CN_TZ, microsecond=0)
    return now.astimezone(CN_TZ).replace(microsecond=0)


def _extract_simple_relative_due(text: str, now: Optional[datetime] = None) -> Optional[str]:
    raw = str(text or "")
    offset = None
    if "今天" in raw:
        offset = 0
    if "明天" in raw:
        offset = 1
    if "后天" in raw:
        offset = 2
    if offset is None:
        return None
    match = re.search(r"(上午|早上|中午|下午|晚上)?\s*(\d{1,2})(?:[:：点时](\d{1,2})?)?", raw)
    if not match:
        return None
    period = match.group(1) or ""
    hour = int(match.group(2))
    minute = int(match.group(3) or 0)
    if hour > 23 or minute > 59:
        return None
    if period in ("下午", "晚上") and hour < 12:
        hour += 12
    if period == "中午" and hour < 11:
        hour += 12
    due = _cn_now(now) + timedelta(days=offset)
    due = due.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return due.isoformat()


def _apply_relative_due_fallback(items: list[dict[str, Any]], source_text: str, now: Optional[datetime] = None) -> list[dict[str, Any]]:
    fallback = _extract_simple_relative_due(source_text, now)
    if not fallback:
        return items
    current = _cn_now(now)
    for item in items:
        due_at = item.get("dueAt")
        use_fallback = not due_at
        if due_at:
            try:
                parsed = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
                use_fallback = parsed < current - timedelta(days=1)
            except ValueError:
                use_fallback = True
        if use_fallback:
            item["dueAt"] = fallback
    return items


def _ai_prompt(now: Optional[datetime] = None) -> str:
    current = _cn_now(now)
    tomorrow = current + timedelta(days=1)
    return (
        "你是代办事项整理助手。把用户输入的中文文本整理为待确认的代办草稿。"
        f"当前日期时间是北京时间/Asia/Shanghai：{current.strftime('%Y-%m-%d %H:%M')}。"
        f"今天是 {current.strftime('%Y-%m-%d')}，明天是 {tomorrow.strftime('%Y-%m-%d')}。"
        "所有相对日期（今天、明天、后天、本周、下周）必须基于这个当前日期计算。"
        "只输出严格 JSON，不要 Markdown，不要解释。JSON 格式："
        '{"items":[{"title":"简短任务标题","note":"补充说明","urgency":1,'
        '"dueAt":"ISO8601时间或null","subtasks":["子任务"]}]}。'
        "dueAt 必须带 +08:00 时区，例如 2026-05-06T16:00:00+08:00。"
        "urgency 取值 0 到 3，0最低，3最高。无法判断时间时 dueAt 为 null。"
    )


def call_xiaomi_chat_messages(system_prompt: str, user_text: str, temperature: float = 0.2) -> str:
    if AI_PROVIDER and AI_PROVIDER != "xiaomi":
        raise RuntimeError("unsupported AI provider")
    if not AI_API_KEY:
        raise RuntimeError("AI not configured")
    payload = {
        "model": AI_MODEL or "mimo-v2.5",
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }
    body = _json_bytes(payload)
    req = Request(
        f"{AI_BASE_URL}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"AI request failed: HTTP {exc.code} {detail}") from exc
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("AI request failed") from exc
    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices or not isinstance(choices, list):
        raise RuntimeError("AI returned invalid response")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI returned empty response")
    return content


def call_xiaomi_chat_completion(text: str) -> str:
    return call_xiaomi_chat_messages(_ai_prompt(), text, temperature=0.2)


def create_todo_item_for_email(conn: sqlite3.Connection, default_email: str, item: dict[str, Any], source_note: str = "") -> dict[str, Any]:
    email = normalize_email(default_email)
    if not email:
        raise ValueError("default account not configured")
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        raise ValueError("default account not found")
    sanitized = sanitize_ai_todo_items({"items": [item]})
    if not sanitized:
        raise ValueError("title required")
    todo = sanitized[0]
    user_id = int(row["id"])
    now = _utc_now_iso()
    client_id = secrets.token_urlsafe(18)
    note = todo["note"]
    if source_note:
        note = f"{note}\n{source_note}".strip()
    cur = conn.execute(
        """
        INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'none', NULL, ?, 0, NULL, NULL, ?, ?)
        """,
        (user_id, client_id, todo["title"], note, int(todo["urgency"]), todo["dueAt"], now, now),
    )
    todo_id = int(cur.lastrowid)
    subtask_titles = []
    for subtask_title in todo["subtasks"]:
        sub_client_id = secrets.token_urlsafe(18)
        conn.execute(
            """
            INSERT INTO subtasks(owner_user_id, client_id, todo_id, title, done, done_at, deleted_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, NULL, NULL, ?, ?)
            """,
            (user_id, sub_client_id, todo_id, subtask_title, now, now),
        )
        subtask_titles.append(subtask_title)
    return {
        "id": todo_id,
        "ownerUserId": user_id,
        "clientId": client_id,
        "title": todo["title"],
        "note": note,
        "urgency": todo["urgency"],
        "dueAt": todo["dueAt"],
        "subtasks": subtask_titles,
        "updatedAt": now,
    }


def parse_feishu_todo_command(text: str) -> Optional[str]:
    normalized = " ".join(str(text or "").strip().split())
    if not normalized:
        return None
    for prefix in ("新增任务", "todo", "任务"):
        if normalized == prefix:
            return None
        marker = f"{prefix} "
        if normalized.lower().startswith(marker.lower()):
            title = normalized[len(marker):].strip()
            return title or None
    return None


def create_feishu_todo(conn: sqlite3.Connection, default_email: str, title: str) -> dict[str, Any]:
    clean_title = str(title or "").strip()
    if not clean_title:
        raise ValueError("title required")
    return create_todo_item_for_email(
        conn,
        default_email,
        {"title": clean_title, "note": "Created from Feishu", "urgency": 1, "dueAt": None, "subtasks": []},
    )


def create_feishu_ai_todos(conn: sqlite3.Connection, default_email: str, text: str) -> list[dict[str, Any]]:
    content = call_xiaomi_chat_completion(text)
    items = _apply_relative_due_fallback(parse_ai_items_from_text(content), text)
    return [create_todo_item_for_email(conn, default_email, item, "Created from Feishu AI") for item in items]


def _extract_feishu_message(body: dict[str, Any]) -> dict[str, Any]:
    event = body.get("event")
    if not isinstance(event, dict):
        return {}
    message = event.get("message")
    if not isinstance(message, dict):
        return {}
    return message


def _extract_feishu_message_text(body: dict[str, Any]) -> str:
    message = _extract_feishu_message(body)
    if message.get("message_type") not in ("", None, "text"):
        return ""
    content = message.get("content")
    if not isinstance(content, str):
        return ""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return ""
    text = parsed.get("text")
    return str(text or "")


def _extract_feishu_message_id(body: dict[str, Any]) -> str:
    message = _extract_feishu_message(body)
    return _clean_ai_string(message.get("message_id"), 160)


def _extract_feishu_sender_info(body: dict[str, Any]) -> dict[str, Any]:
    event = body.get("event")
    if not isinstance(event, dict):
        return {}
    message = event.get("message")
    sender = event.get("sender")
    result: dict[str, Any] = {}
    if isinstance(sender, dict):
        sender_id = sender.get("sender_id")
        if isinstance(sender_id, dict):
            for key in ("open_id", "union_id", "user_id"):
                value = _clean_ai_string(sender_id.get(key), 120)
                if value:
                    result[key] = value
        sender_type = _clean_ai_string(sender.get("sender_type"), 40)
        if sender_type:
            result["sender_type"] = sender_type
    if isinstance(message, dict):
        chat_id = _clean_ai_string(message.get("chat_id"), 120)
        if chat_id:
            result["chat_id"] = chat_id
    return result


def _feishu_reply_text(result: dict[str, Any]) -> str:
    if result.get("duplicate"):
        return "已收到，这条飞书消息已在随记收件箱中，无需重复保存。"
    status = result.get("aiStatus")
    if status == "ready":
        return "已保存到随记收件箱，并完成整理。请到 Web/PWA 审查任务草稿。"
    if status == "failed":
        return "已保存到随记收件箱，但 AI 整理失败。请到 Web/PWA 查看或重试。"
    if result.get("handled"):
        return "已保存到随记收件箱。"
    return "未处理：请输入有效文本消息。"


def handle_feishu_inbox_event(conn: sqlite3.Connection, default_email: str, body: dict[str, Any]) -> dict[str, Any]:
    text = _extract_feishu_message_text(body).strip()
    if not text:
        result = {"handled": False, "reason": "empty message"}
        result["replyText"] = _feishu_reply_text(result)
        return result
    if len(text) > AI_MAX_INPUT_CHARS:
        result = {"handled": False, "reason": f"text too long, max {AI_MAX_INPUT_CHARS} chars"}
        result["replyText"] = _feishu_reply_text(result)
        return result
    email = normalize_email(default_email)
    if not email:
        raise ValueError("default account not configured")
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        raise ValueError("default account not found")
    user_id = int(row["id"])
    message_id = _extract_feishu_message_id(body)
    if not message_id:
        raise ValueError("feishu message id required")
    existing = conn.execute(
        """
        SELECT *
        FROM records
        WHERE owner_user_id = ? AND source = 'feishu' AND source_event_id = ? AND deleted_at IS NULL
        """,
        (user_id, message_id),
    ).fetchone()
    if existing:
        record = serialize_record_row(conn, existing)
        result = {
            "handled": True,
            "duplicate": True,
            "recordId": record["id"],
            "aiStatus": record["aiStatus"],
            "record": record,
            "items": [],
        }
        result["replyText"] = _feishu_reply_text(result)
        return result
    record = create_record(
        conn,
        user_id,
        text,
        "processing",
        source="feishu",
        source_event_id=message_id,
        source_sender=_extract_feishu_sender_info(body),
    )
    record_id = int(record["id"])
    record, items = organize_record_ai(conn, user_id, record_id, text)
    result = {
        "handled": True,
        "duplicate": False,
        "recordId": record_id,
        "aiStatus": record["aiStatus"],
        "record": record,
        "items": items,
    }
    if record["aiError"]:
        result["error"] = record["aiError"]
    result["replyText"] = _feishu_reply_text(result)
    return result


def _daily_plan_prompt(now: Optional[datetime] = None) -> str:
    current = _cn_now(now)
    return (
        "你是今日计划助手。根据用户已有代办，生成今天的执行建议，不要创建新任务。"
        f"当前北京时间是 {current.strftime('%Y-%m-%d %H:%M')}，今天是 {current.strftime('%Y-%m-%d')}。"
        "只输出严格 JSON，不要 Markdown，不要解释。格式："
        '{"date":"YYYY-MM-DD","summary":"一句话总结","items":[{"time":"建议时间或空字符串","text":"行动建议","todoIds":[1]}]}。'
        "items 最多 8 条。优先安排今天到期、已逾期、高优先级任务。"
    )


def _strip_json_object(text: str) -> str:
    cleaned = _strip_json_code_fence(text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end >= start:
        return cleaned[start : end + 1]
    return cleaned


def sanitize_daily_plan(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("AI returned invalid daily plan")
    date = _clean_ai_string(raw.get("date"), 20)
    summary = _clean_ai_string(raw.get("summary"), 200)
    raw_items = raw.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("AI returned invalid daily plan items")
    items = []
    for raw_item in raw_items[:8]:
        if not isinstance(raw_item, dict):
            continue
        text = _clean_ai_string(raw_item.get("text"), 200)
        if not text:
            continue
        ids_raw = raw_item.get("todoIds")
        todo_ids = []
        if isinstance(ids_raw, list):
            for value in ids_raw[:6]:
                try:
                    todo_ids.append(int(value))
                except (TypeError, ValueError):
                    continue
        items.append({"time": _clean_ai_string(raw_item.get("time"), 20), "text": text, "todoIds": todo_ids})
    return {"date": date, "summary": summary, "items": items}


def parse_daily_plan_from_text(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(_strip_json_object(text))
    except json.JSONDecodeError as exc:
        raise ValueError("AI returned invalid JSON") from exc
    return sanitize_daily_plan(parsed)


def _todos_for_daily_plan(user_id: int) -> list[dict[str, Any]]:
    rows = DB.execute(
        """
        SELECT id, title, note, urgency, repeat_rule, reminder_minutes, due_at, updated_at
        FROM todos
        WHERE owner_user_id = ?
          AND done = 0
          AND deleted_at IS NULL
        ORDER BY
          CASE WHEN due_at IS NULL THEN 1 ELSE 0 END ASC,
          due_at ASC,
          urgency DESC,
          updated_at DESC
        LIMIT 40
        """,
        (user_id,),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "title": row["title"],
            "note": row["note"],
            "urgency": int(row["urgency"]),
            "repeatRule": row["repeat_rule"],
            "reminderMinutes": row["reminder_minutes"],
            "dueAt": row["due_at"],
        }
        for row in rows
    ]


def call_xiaomi_daily_plan(todos: list[dict[str, Any]]) -> dict[str, Any]:
    user_text = json.dumps({"todos": todos}, ensure_ascii=False, separators=(",", ":"))
    content = call_xiaomi_chat_messages(_daily_plan_prompt(), user_text, temperature=0.3)
    return parse_daily_plan_from_text(content)


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

    def _send_service_worker(self, path: Path) -> None:
        if not path.is_file():
            self._send_text(404, "Not found")
            return
        body = path.read_text(encoding="utf-8").replace("__APP_VERSION__", APP_VERSION["short"])
        raw = body.encode("utf-8")
        self.send_response(200)
        self._set_cors()
        self._set_security_headers()
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
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
        if parsed.path == "/feishu":
            self._send_text(200, "ok")
            return
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
        if parsed.path == "/feishu":
            self._send_json(200, {"ok": True, "endpoint": "feishu"})
            return
        if parsed.path.startswith("/api/"):
            self._handle_api("GET", parsed.path, parse_qs(parsed.query))
            return
        self._handle_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/feishu":
            self._handle_api("POST", "/api/feishu/events", parse_qs(parsed.query))
            return
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
        if candidate.name == "sw.js":
            self._send_service_worker(candidate)
            return
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
                code, obj = json_ok({"time": _utc_now_iso(), "version": APP_VERSION})
                self._send_json(code, obj)
                return

            if method == "GET" and path == "/api/version":
                code, obj = json_ok({"time": _utc_now_iso(), "version": APP_VERSION})
                self._send_json(code, obj)
                return

            if method == "POST" and path == "/api/feishu/events":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                header = body.get("header") if isinstance(body.get("header"), dict) else {}
                token = str(body.get("token") or header.get("token") or "").strip()
                if body.get("type") == "url_verification":
                    # Feishu validates the URL before event delivery. Return the challenge
                    # immediately so a token mismatch cannot make the console reject the URL.
                    # Real event pushes below still verify TODO_FEISHU_VERIFY_TOKEN.
                    challenge = str(body.get("challenge", ""))
                    self._send_json(200, {"challenge": challenge})
                    return
                if not FEISHU_ENABLED:
                    self._send_json(*json_error(404, "not found"))
                    return
                if FEISHU_VERIFY_TOKEN and not hmac.compare_digest(token, FEISHU_VERIFY_TOKEN):
                    self._send_json(*json_error(401, "invalid feishu token"))
                    return
                try:
                    result = handle_feishu_inbox_event(DB, FEISHU_DEFAULT_EMAIL, body)
                except ValueError as exc:
                    self._send_json(*json_error(400, str(exc)))
                    return
                except RuntimeError as exc:
                    self._send_json(*json_error(502, str(exc)))
                    return
                self._send_json(*json_ok(result))
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

            if method == "POST" and path == "/api/password/forgot":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                email = normalize_email(str(body.get("email", "")))
                row = DB.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                print(
                    f"[password-reset] request received. email={email or '-'} "
                    f"accountFound={bool(row)} smtp={_smtp_status_for_log()}",
                    flush=True,
                )
                if row:
                    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
                    cooldown = _recent_password_reset_request(int(row["id"]), now_dt)
                    if cooldown:
                        print(f"[password-reset] rate limited. email={email} retryAfter={cooldown}", flush=True)
                        self._send_json(429, {"ok": False, "error": f"please wait {cooldown}s", "retryAfter": cooldown})
                        return
                    token = secrets.token_urlsafe(32)
                    code = f"{secrets.randbelow(1_000_000):06d}"
                    now = now_dt.isoformat()
                    expires_at = (now_dt + timedelta(seconds=RESET_TOKEN_TTL_SECONDS)).isoformat()
                    DB.execute(
                        """
                        INSERT INTO password_reset_tokens(user_id, token_hash, code, expires_at, used_at, created_at)
                        VALUES (?, ?, ?, ?, NULL, ?)
                        """,
                        (int(row["id"]), _hash_reset_token(token), code, expires_at, now),
                    )
                    proto = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
                    host = self.headers.get("Host", "")
                    reset_url = f"{proto}://{host}/?resetToken={token}&email={email}" if host else token
                    try:
                        sent = _send_reset_email(email, reset_url, code)
                    except Exception as exc:
                        print(f"[password-reset] SMTP send failed. email={email} error={exc}", flush=True)
                        sent = False
                    message = "如果邮箱存在，重置邮件会在几分钟内发送。"
                    if not _smtp_configured():
                        message = "服务器未配置 SMTP，验证码已写入服务器日志。"
                    print(f"[password-reset] response. email={email} sent={sent} smtpConfigured={_smtp_configured()}", flush=True)
                    self._send_json(*json_ok({"sent": sent, "smtpConfigured": _smtp_configured(), "message": message}))
                    return
                # Do not reveal whether the account exists.
                print(f"[password-reset] ignored unknown account. email={email or '-'}", flush=True)
                self._send_json(*json_ok({"sent": False, "smtpConfigured": _smtp_configured(), "message": "如果邮箱存在，重置邮件会在几分钟内发送。"}))
                return

            if method == "POST" and path == "/api/password/forgot/confirm":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                email = normalize_email(str(body.get("email", "")))
                token = str(body.get("token", "")).strip()
                code = str(body.get("code", "")).strip()
                new_password = str(body.get("newPassword", ""))
                pw_err = validate_password(new_password)
                if pw_err:
                    self._send_json(*json_error(400, pw_err))
                    return
                user_row = DB.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                if not user_row:
                    self._send_json(*json_error(400, "invalid or expired reset token"))
                    return
                token_hash = _hash_reset_token(token) if token else ""
                row = DB.execute(
                    """
                    SELECT id, user_id, expires_at
                    FROM password_reset_tokens
                    WHERE user_id = ?
                      AND used_at IS NULL
                      AND (token_hash = ? OR code = ?)
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (int(user_row["id"]), token_hash, code),
                ).fetchone()
                if not row:
                    self._send_json(*json_error(400, "invalid or expired reset token"))
                    return
                try:
                    expires = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
                except ValueError:
                    self._send_json(*json_error(400, "invalid or expired reset token"))
                    return
                if datetime.now(timezone.utc) > expires:
                    self._send_json(*json_error(400, "invalid or expired reset token"))
                    return
                update_user_password(int(row["user_id"]), new_password)
                now = _utc_now_iso()
                DB.execute("UPDATE password_reset_tokens SET used_at = ? WHERE id = ?", (now, int(row["id"])))
                self._send_json(*json_ok({}))
                return

            user = require_user(self)
            if not user:
                self._send_json(*json_error(401, "unauthorized"))
                return

            if method == "GET" and path == "/api/me":
                self._send_json(*json_ok({"user": {"id": user.id, "email": user.email}}))
                return

            if method == "POST" and path == "/api/records/organize":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                text = str(body.get("text", "")).strip()
                if not text:
                    self._send_json(*json_error(400, "text required"))
                    return
                if len(text) > AI_MAX_INPUT_CHARS:
                    self._send_json(*json_error(400, f"text too long, max {AI_MAX_INPUT_CHARS} chars"))
                    return
                record = create_record(DB, user.id, text, "pending")
                record_id = int(record["id"])
                organized, items = organize_record_ai(DB, user.id, record_id, text)
                self._send_json(*json_ok({"record": organized, "items": items}))
                return

            if method == "GET" and path == "/api/records":
                filters = ["owner_user_id = ?", "deleted_at IS NULL"]
                params: list[Any] = [user.id]
                record_type = (query.get("type") or [""])[0]
                if record_type:
                    filters.append("record_type = ?")
                    params.append(_normalize_record_type(record_type))
                sentiment = (query.get("sentiment") or [""])[0]
                if sentiment:
                    filters.append("sentiment = ?")
                    params.append(_normalize_record_sentiment(sentiment))
                tag = _clean_ai_string((query.get("tag") or [""])[0], 24)
                if tag:
                    filters.append("tags_json LIKE ?")
                    params.append(f'%"{tag}"%')
                linked = (query.get("linked") or [""])[0]
                if linked in ("1", "true", "yes"):
                    filters.append(
                        "EXISTS (SELECT 1 FROM todos t WHERE t.owner_user_id = records.owner_user_id AND t.source_record_id = records.id AND t.deleted_at IS NULL)"
                    )
                rows = DB.execute(
                    f"""
                    SELECT *
                    FROM records
                    WHERE {' AND '.join(filters)}
                    ORDER BY updated_at DESC
                    LIMIT 200
                    """,
                    tuple(params),
                ).fetchall()
                self._send_json(*json_ok({"records": [serialize_record_row(DB, r) for r in rows]}))
                return

            if path.startswith("/api/records/"):
                parts = path.strip("/").split("/")
                if len(parts) >= 3:
                    record_id_str = parts[2]
                    if not record_id_str.isdigit():
                        self._send_json(*json_error(404, "not found"))
                        return
                    record_id = int(record_id_str)
                    record_row = DB.execute(
                        "SELECT * FROM records WHERE id = ? AND owner_user_id = ?",
                        (record_id, user.id),
                    ).fetchone()
                    if not record_row:
                        self._send_json(*json_error(404, "not found"))
                        return

                    if len(parts) == 3:
                        if method == "GET":
                            self._send_json(*json_ok({"record": serialize_record_row(DB, record_row)}))
                            return
                        if method == "PATCH":
                            body, err = parse_json_body(self)
                            if err:
                                self._send_json(*json_error(400, err))
                                return
                            current = {
                                "summary": record_row["summary"],
                                "type": record_row["record_type"],
                                "tags": _json_list(record_row["tags_json"]),
                                "dates": _json_list(record_row["dates_json"]),
                                "sentiment": record_row["sentiment"],
                            }
                            merged = {
                                "summary": body.get("summary", current["summary"]),
                                "type": body.get("type", current["type"]),
                                "tags": body.get("tags", current["tags"]),
                                "dates": body.get("dates", current["dates"]),
                                "sentiment": body.get("sentiment", current["sentiment"]),
                            }
                            fields = sanitize_record_fields(merged, record_row["original_input"])
                            patched = update_record_ai_result(DB, user.id, record_id, fields, record_row["ai_status"], record_row["ai_error"])
                            self._send_json(*json_ok({"record": patched}))
                            return
                        if method == "DELETE":
                            now = _utc_now_iso()
                            DB.execute(
                                "UPDATE records SET deleted_at = ?, updated_at = ? WHERE id = ? AND owner_user_id = ?",
                                (now, now, record_id, user.id),
                            )
                            self._send_json(*json_ok({"deletedAt": now}))
                            return

                    if len(parts) == 4 and parts[3] == "retry" and method == "POST":
                        text = record_row["original_input"]
                        organized, items = organize_record_ai(DB, user.id, record_id, text)
                        self._send_json(*json_ok({"record": organized, "items": items}))
                        return

                    if len(parts) == 4 and parts[3] == "todos" and method == "POST":
                        body, err = parse_json_body(self)
                        if err:
                            self._send_json(*json_error(400, err))
                            return
                        try:
                            items = sanitize_ai_todo_items(body)
                        except ValueError as exc:
                            self._send_json(*json_error(400, str(exc)))
                            return
                        now = _utc_now_iso()
                        saved: list[dict[str, Any]] = []
                        for item in items:
                            client_id = secrets.token_urlsafe(18)
                            cur = DB.execute(
                                """
                                INSERT INTO todos(owner_user_id, client_id, source_record_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, 'none', NULL, ?, 0, NULL, NULL, ?, ?)
                                """,
                                (user.id, client_id, record_id, item["title"], item["note"], int(item["urgency"]), item["dueAt"], now, now),
                            )
                            todo_id = int(cur.lastrowid)
                            subs = []
                            for subtask_title in item["subtasks"]:
                                sub_client_id = secrets.token_urlsafe(18)
                                sub_cur = DB.execute(
                                    """
                                    INSERT INTO subtasks(owner_user_id, client_id, todo_id, title, done, done_at, deleted_at, created_at, updated_at)
                                    VALUES (?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                                    """,
                                    (user.id, sub_client_id, todo_id, subtask_title, now, now),
                                )
                                subs.append({"id": int(sub_cur.lastrowid), "title": subtask_title})
                            saved.append({"id": todo_id, "clientId": client_id, "title": item["title"], "subtasks": subs})
                        self._send_json(*json_ok({"todos": saved}))
                        return

                    if len(parts) == 4 and parts[3] == "sync-dates" and method == "POST":
                        dates = _json_list(record_row["dates_json"])
                        due_at = str(dates[0]) if dates else None
                        if not due_at:
                            self._send_json(*json_ok({"updated": 0}))
                            return
                        now = _utc_now_iso()
                        cur = DB.execute(
                            """
                            UPDATE todos
                            SET due_at = ?, updated_at = ?
                            WHERE owner_user_id = ? AND source_record_id = ? AND deleted_at IS NULL
                            """,
                            (due_at, now, user.id, record_id),
                        )
                        self._send_json(*json_ok({"updated": cur.rowcount}))
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

            if method == "POST" and path == "/api/ai/organize":
                body, err = parse_json_body(self)
                if err:
                    self._send_json(*json_error(400, err))
                    return
                text = str(body.get("text", "")).strip()
                if not text:
                    self._send_json(*json_error(400, "text required"))
                    return
                if len(text) > AI_MAX_INPUT_CHARS:
                    self._send_json(*json_error(400, f"text too long, max {AI_MAX_INPUT_CHARS} chars"))
                    return
                if not AI_API_KEY:
                    self._send_json(*json_error(503, "AI not configured"))
                    return
                try:
                    content = call_xiaomi_chat_completion(text)
                    items = parse_ai_items_from_text(content)
                    items = _apply_relative_due_fallback(items, text)
                except ValueError:
                    self._send_json(*json_error(502, "AI returned invalid JSON"))
                    return
                except RuntimeError as exc:
                    self._send_json(*json_error(502, str(exc)))
                    return
                self._send_json(*json_ok({"items": items}))
                return

            if method == "POST" and path == "/api/ai/daily-plan":
                if not AI_API_KEY:
                    self._send_json(*json_error(503, "AI not configured"))
                    return
                todos = _todos_for_daily_plan(user.id)
                try:
                    plan = call_xiaomi_daily_plan(todos)
                except ValueError:
                    self._send_json(*json_error(502, "AI returned invalid JSON"))
                    return
                except RuntimeError as exc:
                    self._send_json(*json_error(502, str(exc)))
                    return
                self._send_json(*json_ok({"plan": plan, "todoCount": len(todos)}))
                return

            if method == "GET" and path == "/api/todos":
                rows = DB.execute(
                    """
                    SELECT t.id, t.client_id, t.title, t.note, t.urgency, t.repeat_rule, t.reminder_minutes,
                           t.due_at, t.done, t.done_at, t.created_at, t.updated_at, t.source_record_id,
                           r.summary AS source_record_summary,
                           r.deleted_at AS source_record_deleted_at
                    FROM todos t
                    LEFT JOIN records r
                      ON r.id = t.source_record_id AND r.owner_user_id = t.owner_user_id
                    WHERE t.owner_user_id = ?
                      AND t.deleted_at IS NULL
                    ORDER BY
                      t.done ASC,
                      CASE WHEN t.due_at IS NULL THEN 1 ELSE 0 END ASC,
                      t.due_at ASC,
                      t.urgency DESC,
                      t.updated_at DESC
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
                            "repeatRule": r["repeat_rule"],
                            "reminderMinutes": r["reminder_minutes"],
                            "dueAt": r["due_at"],
                            "done": bool(r["done"]),
                            "doneAt": r["done_at"],
                            "createdAt": r["created_at"],
                            "updatedAt": r["updated_at"],
                            "sourceRecord": (
                                {
                                    "id": int(r["source_record_id"]),
                                    "summary": r["source_record_summary"] or "",
                                    "deleted": bool(r["source_record_deleted_at"]),
                                }
                                if r["source_record_id"] is not None
                                else None
                            ),
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
                repeat_rule = _normalize_repeat_rule(body.get("repeatRule"))
                reminder_minutes = _normalize_reminder_minutes(body.get("reminderMinutes"))
                due_at = body.get("dueAt")
                if due_at is not None:
                    due_at = str(due_at).strip() or None
                client_id = _normalize_client_id(body.get("clientId")) or secrets.token_urlsafe(18)
                now = _utc_now_iso()
                try:
                    cur = DB.execute(
                    """
                    INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                    """,
                    (user.id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, now, now),
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
                    existing_todo = DB.execute(
                        "SELECT done FROM todos WHERE id = ? AND owner_user_id = ? AND deleted_at IS NULL",
                        (todo_id, user.id),
                    ).fetchone()
                    if not existing_todo:
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
                            if "repeatRule" in body:
                                fields.append("repeat_rule = ?")
                                values.append(_normalize_repeat_rule(body.get("repeatRule")))
                            if "reminderMinutes" in body:
                                fields.append("reminder_minutes = ?")
                                values.append(_normalize_reminder_minutes(body.get("reminderMinutes")))
                            if "dueAt" in body:
                                due_at = body.get("dueAt")
                                if due_at is not None:
                                    due_at = str(due_at).strip() or None
                                fields.append("due_at = ?")
                                values.append(due_at)
                            done_changed = "done" in body
                            done = False
                            if done_changed:
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
                            if done_changed and done and not bool(existing_todo["done"]):
                                self._create_next_repeat_todo(user.id, todo_id)
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
                    SELECT id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at
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
                            "repeatRule": r["repeat_rule"],
                            "reminderMinutes": r["reminder_minutes"],
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
                    repeat_rule = _normalize_repeat_rule(item.get("repeatRule"))
                    reminder_minutes = _normalize_reminder_minutes(item.get("reminderMinutes"))
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
                            SET title = ?, note = ?, urgency = ?, repeat_rule = ?, reminder_minutes = ?, due_at = ?, done = ?, done_at = ?, deleted_at = NULL, updated_at = ?
                            WHERE owner_user_id = ? AND client_id = ?
                            """,
                            (title, note, urgency, repeat_rule, reminder_minutes, due_at, 1 if done else 0, done_at, now, user.id, cid),
                        )
                    else:
                        try:
                            DB.execute(
                                """
                                INSERT INTO todos(
                                  owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at,
                                  done, done_at, deleted_at, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                                """,
                                (user.id, cid, title, note, urgency, repeat_rule, reminder_minutes, due_at, 1 if done else 0, done_at, now, now),
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

    def _create_next_repeat_todo(self, user_id: int, todo_id: int) -> None:
        row = DB.execute(
            """
            SELECT title, note, urgency, repeat_rule, reminder_minutes, due_at
            FROM todos
            WHERE id = ? AND owner_user_id = ? AND deleted_at IS NULL
            """,
            (todo_id, user_id),
        ).fetchone()
        if not row:
            return
        repeat_rule = _normalize_repeat_rule(row["repeat_rule"])
        if repeat_rule == "none":
            return
        next_due = _next_due_at(row["due_at"], repeat_rule)
        now = _utc_now_iso()
        cur = DB.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?)
            """,
            (
                user_id,
                secrets.token_urlsafe(18),
                row["title"],
                row["note"],
                int(row["urgency"]),
                repeat_rule,
                row["reminder_minutes"],
                next_due,
                now,
                now,
            ),
        )
        new_todo_id = int(cur.lastrowid)
        subtasks = DB.execute(
            """
            SELECT title
            FROM subtasks
            WHERE owner_user_id = ? AND todo_id = ? AND deleted_at IS NULL
            ORDER BY id ASC
            """,
            (user_id, todo_id),
        ).fetchall()
        for subtask in subtasks:
            DB.execute(
                """
                INSERT INTO subtasks(owner_user_id, client_id, todo_id, title, done, done_at, deleted_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (user_id, secrets.token_urlsafe(18), new_todo_id, subtask["title"], now, now),
            )

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
