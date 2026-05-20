import json
import json
import os
import sqlite3
import time
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from unittest.mock import patch

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import server  # noqa: E402


class RecordsEndpointTests(unittest.TestCase):
    def setUp(self):
        self.old_db = server.DB
        self.old_ai_key = server.AI_API_KEY
        self.conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        server.init_db(self.conn)
        server.migrate_db(self.conn)
        salt = b"2" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("me@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )
        server.DB = self.conn
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = __import__("threading").Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.token = server.sign_token(
            {"uid": 1, "email": "me@example.com", "exp": int(time.time()) + 3600}
        )

    def tearDown(self):
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        self.httpd.server_close()
        self.conn.close()
        server.DB = self.old_db
        server.AI_API_KEY = self.old_ai_key

    def request(self, method, path, body=None, token=True):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = None if body is None else json.dumps(body)
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        conn.close()
        return res.status, data

    def test_records_schema_is_created_by_migration(self):
        record_columns = {r["name"] for r in self.conn.execute("PRAGMA table_info(records)").fetchall()}
        todo_columns = {r["name"] for r in self.conn.execute("PRAGMA table_info(todos)").fetchall()}

        self.assertIn("original_input", record_columns)
        self.assertIn("ai_status", record_columns)
        self.assertIn("source", record_columns)
        self.assertIn("source_event_id", record_columns)
        self.assertIn("source_sender_json", record_columns)
        self.assertIn("source_record_id", todo_columns)
        self.assertIn("archived_at", todo_columns)

    def test_done_todo_moves_from_active_list_to_archive(self):
        now = server._utc_now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, archived_at, created_at, updated_at)
            VALUES (1, 'todo-archive', '完成归档', '', 1, 'none', NULL, NULL, 0, NULL, NULL, NULL, ?, ?)
            """,
            (now, now),
        )
        todo_id = int(cur.lastrowid)

        status, patched = self.request("PATCH", f"/api/todos/{todo_id}", {"done": True})
        self.assertEqual(status, 200)
        self.assertTrue(patched["ok"])

        row = self.conn.execute("SELECT done, done_at, archived_at FROM todos WHERE id = ?", (todo_id,)).fetchone()
        self.assertEqual(row["done"], 1)
        self.assertIsNotNone(row["done_at"])
        self.assertIsNotNone(row["archived_at"])

        status, active = self.request("GET", "/api/todos")
        self.assertEqual(status, 200)
        self.assertEqual(active["todos"], [])
        self.assertEqual(active["stats"]["active"], 0)
        self.assertEqual(active["stats"]["archived"], 1)

        status, archive = self.request("GET", "/api/todos/archive")
        self.assertEqual(status, 200)
        self.assertEqual([t["title"] for t in archive["todos"]], ["完成归档"])
        self.assertIsNotNone(archive["todos"][0]["archivedAt"])

    def test_archive_is_scoped_to_current_account(self):
        salt = b"3" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("other@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )
        now = server._utc_now_iso()
        self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, archived_at, created_at, updated_at)
            VALUES (1, 'mine-archived', '我的归档', '', 1, 'none', NULL, NULL, 1, ?, NULL, ?, ?, ?)
            """,
            (now, now, now, now),
        )
        self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, archived_at, created_at, updated_at)
            VALUES (2, 'other-archived', '他人归档', '', 1, 'none', NULL, NULL, 1, ?, NULL, ?, ?, ?)
            """,
            (now, now, now, now),
        )

        status, archive = self.request("GET", "/api/todos/archive")

        self.assertEqual(status, 200)
        self.assertEqual([t["title"] for t in archive["todos"]], ["我的归档"])
        self.assertEqual(archive["stats"]["archived"], 1)

    def test_archive_filters_and_restore_todo(self):
        now = server._utc_now_iso()
        old = "2026-05-01T00:00:00Z"
        keep = self._insert_todo(
            "客户方案评审",
            note="包含风险点",
            urgency=2,
            done=True,
            done_at=now,
            archived_at=now,
        )
        self._insert_todo(
            "普通资料整理",
            note="内部归档",
            urgency=1,
            done=True,
            done_at=old,
            archived_at=old,
        )

        status, archive = self.request("GET", f"/api/todos/archive?q={quote('风险')}&urgency=2&from=2026-05-20")
        self.assertEqual(status, 200)
        self.assertEqual([t["id"] for t in archive["todos"]], [keep])
        self.assertEqual(archive["todos"][0]["subtaskSummary"]["total"], 0)

        status, restored = self.request("POST", f"/api/todos/{keep}/restore", {})
        self.assertEqual(status, 200)
        self.assertFalse(restored["todo"]["done"])
        self.assertIsNone(restored["todo"]["doneAt"])
        self.assertIsNone(restored["todo"]["archivedAt"])
        self.assertEqual(restored["stats"]["active"], 1)

        status, active = self.request("GET", "/api/todos")
        self.assertEqual(status, 200)
        self.assertEqual([t["id"] for t in active["todos"]], [keep])

    def test_restore_archive_is_scoped_to_current_account(self):
        salt = b"4" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("other2@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )
        now = server._utc_now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, archived_at, created_at, updated_at)
            VALUES (2, 'other-restore', '他人归档任务', '', 1, 'none', NULL, NULL, 1, ?, NULL, ?, ?, ?)
            """,
            (now, now, now, now),
        )

        status, data = self.request("POST", f"/api/todos/{int(cur.lastrowid)}/restore", {})

        self.assertEqual(status, 404)
        self.assertIn("not found", data["error"])

    def test_create_record_saves_original_input_and_lists_it(self):
        server.AI_API_KEY = ""

        status, data = self.request("POST", "/api/records/organize", {"text": "今天客户说要补报价"})

        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["record"]["originalInput"], "今天客户说要补报价")
        self.assertEqual(data["record"]["aiStatus"], "failed")
        self.assertIn("AI not configured", data["record"]["aiError"])

        status, listed = self.request("GET", "/api/records")
        self.assertEqual(status, 200)
        self.assertEqual(len(listed["records"]), 1)
        self.assertEqual(listed["records"][0]["originalInput"], "今天客户说要补报价")

    def test_list_records_returns_feishu_source_fields(self):
        record = server.create_record(
            self.conn,
            1,
            "feishu note",
            "failed",
            source="feishu",
            source_event_id="om_123",
            source_sender={"open_id": "ou_1", "chat_id": "oc_1"},
        )

        status, listed = self.request("GET", "/api/records")

        self.assertEqual(status, 200)
        self.assertEqual(listed["records"][0]["id"], record["id"])
        self.assertEqual(listed["records"][0]["source"], "feishu")
        self.assertEqual(listed["records"][0]["sourceEventId"], "om_123")
        self.assertEqual(listed["records"][0]["sourceSender"]["open_id"], "ou_1")

    def test_record_organize_rejects_invalid_inputs(self):
        server.AI_API_KEY = "test"

        status, data = self.request("POST", "/api/records/organize", {"text": "   "})
        self.assertEqual(status, 400)
        self.assertIn("text required", data["error"])

        status, data = self.request("POST", "/api/records/organize", {"text": "买菜"}, token=False)
        self.assertEqual(status, 401)

    def test_ai_success_returns_record_fields_and_drafts(self):
        server.AI_API_KEY = "test"
        content = json.dumps(
            {
                "record": {
                    "summary": "客户续费沟通",
                    "type": "task",
                    "tags": ["客户", "续费"],
                    "dates": ["2026-05-11T10:00:00+08:00"],
                    "sentiment": "neutral",
                },
                "items": [{"title": "整理报价", "urgency": 2, "dueAt": "2026-05-11T10:00:00+08:00", "subtasks": ["补风险点"]}],
            },
            ensure_ascii=False,
        )

        with patch.object(server, "call_xiaomi_chat_messages", return_value=content):
            status, data = self.request("POST", "/api/records/organize", {"text": "客户续费，明天10点整理报价"})

        self.assertEqual(status, 200)
        self.assertEqual(data["record"]["summary"], "客户续费沟通")
        self.assertEqual(data["record"]["type"], "task")
        self.assertEqual(data["record"]["tags"], ["客户", "续费"])
        self.assertEqual(data["record"]["dates"], ["2026-05-11T10:00:00+08:00"])
        self.assertEqual(data["record"]["sentiment"], "neutral")
        self.assertEqual(data["record"]["aiStatus"], "ready")
        self.assertEqual(data["record"]["aiItems"][0]["title"], data["items"][0]["title"])
        self.assertEqual(data["items"][0]["title"], "整理报价")

    def test_invalid_ai_json_keeps_failed_record(self):
        server.AI_API_KEY = "test"

        with patch.object(server, "call_xiaomi_chat_messages", return_value="bad"):
            status, data = self.request("POST", "/api/records/organize", {"text": "明天买菜"})

        self.assertEqual(status, 200)
        self.assertEqual(data["record"]["aiStatus"], "failed")
        self.assertIn("invalid JSON", data["record"]["aiError"])
        self.assertEqual(data["items"], [])

    def test_save_drafts_creates_todo_subtasks_and_source_link(self):
        server.AI_API_KEY = ""
        status, data = self.request("POST", "/api/records/organize", {"text": "客户续费"})
        record_id = data["record"]["id"]

        status, saved = self.request(
            "POST",
            f"/api/records/{record_id}/todos",
            {"items": [{"title": "整理报价", "urgency": 2, "dueAt": "2026-05-11T10:00:00+08:00", "subtasks": ["补风险点"]}]},
        )

        self.assertEqual(status, 200)
        self.assertEqual(saved["todos"][0]["title"], "整理报价")
        todo = self.conn.execute("SELECT source_record_id FROM todos WHERE title = ?", ("整理报价",)).fetchone()
        self.assertEqual(int(todo["source_record_id"]), record_id)
        subtasks = self.conn.execute("SELECT title FROM subtasks").fetchall()
        self.assertEqual([r["title"] for r in subtasks], ["补风险点"])

    def test_sync_record_creates_todos_from_persisted_ai_items(self):
        server.AI_API_KEY = "test"
        content = json.dumps(
            {
                "record": {
                    "summary": "basketball plan",
                    "type": "event",
                    "tags": ["sport"],
                    "dates": ["2026-05-14T17:00:00+08:00"],
                    "sentiment": "neutral",
                },
                "items": [
                    {
                        "title": "play basketball",
                        "note": "bring shoes",
                        "urgency": 1,
                        "dueAt": "2026-05-14T17:00:00+08:00",
                        "subtasks": ["pack shoes"],
                    }
                ],
            },
            ensure_ascii=False,
        )
        with patch.object(server, "call_xiaomi_chat_messages", return_value=content):
            status, data = self.request("POST", "/api/records/organize", {"text": "basketball tomorrow 5pm"})
        record_id = data["record"]["id"]

        status, synced = self.request("POST", f"/api/records/{record_id}/sync-dates", {})

        self.assertEqual(status, 200)
        self.assertEqual(synced["created"], 1)
        self.assertEqual(synced["updated"], 1)
        todo = self.conn.execute("SELECT title, note, due_at, source_record_id FROM todos").fetchone()
        self.assertEqual(todo["title"], "play basketball")
        self.assertEqual(todo["note"], "bring shoes")
        self.assertEqual(todo["due_at"], "2026-05-14T17:00:00+08:00")
        self.assertEqual(int(todo["source_record_id"]), record_id)
        subtask = self.conn.execute("SELECT title FROM subtasks").fetchone()
        self.assertEqual(subtask["title"], "pack shoes")

    def test_filters_details_and_todo_source(self):
        r1 = self._insert_record("任务记录", "task", ["客户"], "neutral")
        self._insert_record("灵感记录", "idea", ["产品"], "positive")
        self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, source_record_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
            VALUES (1, 'todo-source', ?, '整理报价', '', 1, 'none', NULL, NULL, 0, NULL, NULL, ?, ?)
            """,
            (r1, server._utc_now_iso(), server._utc_now_iso()),
        )

        status, data = self.request("GET", f"/api/records?type=task&tag={quote('客户')}&sentiment=neutral&linked=1")
        self.assertEqual(status, 200)
        self.assertEqual([r["id"] for r in data["records"]], [r1])

        status, detail = self.request("GET", f"/api/records/{r1}")
        self.assertEqual(status, 200)
        self.assertEqual(detail["record"]["linkedTodos"][0]["title"], "整理报价")

        status, todos = self.request("GET", "/api/todos")
        self.assertEqual(status, 200)
        self.assertEqual(todos["todos"][0]["sourceRecord"]["id"], r1)
        self.assertEqual(todos["todos"][0]["sourceRecord"]["summary"], "任务记录")

    def test_records_support_source_status_has_todo_and_keyword_filters(self):
        r1 = self._insert_record("客户续费摘要", "task", ["客户"], "neutral", source="feishu", ai_status="ready")
        self._insert_record("个人灵感", "idea", ["产品"], "positive", source="web", ai_status="failed")
        self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, source_record_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
            VALUES (1, 'todo-filter-source', ?, '跟进续费', '', 1, 'none', NULL, NULL, 0, NULL, NULL, ?, ?)
            """,
            (r1, server._utc_now_iso(), server._utc_now_iso()),
        )

        status, data = self.request(
            "GET",
            f"/api/records?source=feishu&status=ready&hasTodo=1&q={quote('续费')}&tag={quote('客户')}",
        )

        self.assertEqual(status, 200)
        self.assertEqual([r["id"] for r in data["records"]], [r1])

    def test_bulk_delete_records_is_scoped_and_reports_counts(self):
        mine = self._insert_record("我的记录", "note", [], "neutral")
        salt = b"5" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("bulk-other@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )
        self.conn.execute(
            """
            INSERT INTO records(owner_user_id, original_input, summary, record_type, tags_json, dates_json, sentiment, ai_status, ai_error, deleted_at, created_at, updated_at)
            VALUES (2, '他人记录', '他人记录', 'note', '[]', '[]', 'neutral', 'ready', '', NULL, ?, ?)
            """,
            (server._utc_now_iso(), server._utc_now_iso()),
        )
        other = int(self.conn.execute("SELECT id FROM records WHERE owner_user_id = 2").fetchone()["id"])

        status, data = self.request("POST", "/api/records/bulk", {"action": "delete", "ids": [mine, other, 9999]})

        self.assertEqual(status, 200)
        self.assertEqual(data["result"], {"succeeded": 1, "failed": 0, "skipped": 2})
        mine_row = self.conn.execute("SELECT deleted_at FROM records WHERE id = ?", (mine,)).fetchone()
        other_row = self.conn.execute("SELECT deleted_at FROM records WHERE id = ?", (other,)).fetchone()
        self.assertIsNotNone(mine_row["deleted_at"])
        self.assertIsNone(other_row["deleted_at"])

    def test_retry_record_does_not_create_todo(self):
        server.AI_API_KEY = "test"
        record_id = self._insert_record("失败记录", "other", [], "neutral", ai_status="failed")
        content = json.dumps(
            {
                "record": {"summary": "重试摘要", "type": "task", "tags": ["客户"], "dates": [], "sentiment": "neutral"},
                "items": [{"title": "只生成草稿", "urgency": 1}],
            },
            ensure_ascii=False,
        )

        with patch.object(server, "call_xiaomi_chat_messages", return_value=content):
            status, data = self.request("POST", f"/api/records/{record_id}/retry", {})

        self.assertEqual(status, 200)
        self.assertEqual(data["record"]["aiStatus"], "ready")
        self.assertEqual(data["items"][0]["title"], "只生成草稿")
        todo_count = self.conn.execute("SELECT COUNT(*) AS c FROM todos").fetchone()["c"]
        self.assertEqual(int(todo_count), 0)

    def test_patch_record_and_manual_sync_dates(self):
        r1 = self._insert_record("旧摘要", "note", [], "neutral")
        self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, source_record_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
            VALUES (1, 'todo-sync', ?, '整理报价', '', 1, 'none', NULL, NULL, 0, NULL, NULL, ?, ?)
            """,
            (r1, server._utc_now_iso(), server._utc_now_iso()),
        )

        status, patched = self.request(
            "PATCH",
            f"/api/records/{r1}",
            {"summary": "新摘要", "type": "task", "tags": ["客户"], "dates": ["2026-05-12T09:00:00+08:00"], "sentiment": "positive"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(patched["record"]["summary"], "新摘要")

        todo_before = self.conn.execute("SELECT due_at FROM todos WHERE client_id = 'todo-sync'").fetchone()
        self.assertIsNone(todo_before["due_at"])

        status, synced = self.request("POST", f"/api/records/{r1}/sync-dates", {})
        self.assertEqual(status, 200)
        self.assertEqual(synced["updated"], 1)
        todo_after = self.conn.execute("SELECT due_at FROM todos WHERE client_id = 'todo-sync'").fetchone()
        self.assertEqual(todo_after["due_at"], "2026-05-12T09:00:00+08:00")

    def test_delete_record_does_not_delete_linked_todo(self):
        r1 = self._insert_record("任务记录", "task", [], "neutral")
        self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, source_record_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
            VALUES (1, 'todo-delete', ?, '保留任务', '', 1, 'none', NULL, NULL, 0, NULL, NULL, ?, ?)
            """,
            (r1, server._utc_now_iso(), server._utc_now_iso()),
        )

        status, data = self.request("DELETE", f"/api/records/{r1}")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])

        todo = self.conn.execute("SELECT deleted_at FROM todos WHERE client_id = 'todo-delete'").fetchone()
        self.assertIsNone(todo["deleted_at"])
        status, todos = self.request("GET", "/api/todos")
        self.assertEqual(todos["todos"][0]["sourceRecord"]["deleted"], True)

    def _insert_record(self, summary, record_type, tags, sentiment, source="web", ai_status="ready"):
        now = server._utc_now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO records(owner_user_id, original_input, source, source_event_id, source_sender_json, summary, record_type, tags_json, dates_json, sentiment, ai_status, ai_error, deleted_at, created_at, updated_at)
            VALUES (1, ?, ?, '', '{}', ?, ?, ?, ?, ?, ?, '', NULL, ?, ?)
            """,
            (summary, source, summary, record_type, json.dumps(tags, ensure_ascii=False), "[]", sentiment, ai_status, now, now),
        )
        return int(cur.lastrowid)

    def _insert_todo(self, title, note="", urgency=1, done=False, done_at=None, archived_at=None):
        now = server._utc_now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, archived_at, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, 'none', NULL, NULL, ?, ?, NULL, ?, ?, ?)
            """,
            (f"todo-{title}", title, note, urgency, 1 if done else 0, done_at, archived_at, now, now),
        )
        return int(cur.lastrowid)


if __name__ == "__main__":
    unittest.main()
