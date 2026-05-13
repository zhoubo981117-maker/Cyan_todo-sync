import os
import json
import sqlite3
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import server  # noqa: E402


class FeishuTests(unittest.TestCase):
    def setUp(self):
        self.old_db = server.DB
        self.old_ai_key = server.AI_API_KEY
        self.old_feishu_enabled = server.FEISHU_ENABLED
        self.old_feishu_default_email = server.FEISHU_DEFAULT_EMAIL
        self.conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        server.init_db(self.conn)
        server.migrate_db(self.conn)
        salt = b"0" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("me@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )
        server.DB = self.conn
        server.AI_API_KEY = ""
        server.FEISHU_ENABLED = True
        server.FEISHU_DEFAULT_EMAIL = "me@example.com"

    def tearDown(self):
        server.DB = self.old_db
        server.AI_API_KEY = self.old_ai_key
        server.FEISHU_ENABLED = self.old_feishu_enabled
        server.FEISHU_DEFAULT_EMAIL = self.old_feishu_default_email
        self.conn.close()

    def test_http_feishu_event_creates_record_not_todo(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]
        body = {
            "event": {
                "message": {
                    "message_id": "om_http_record",
                    "message_type": "text",
                    "content": json.dumps({"text": "http note"}, ensure_ascii=False),
                }
            }
        }
        try:
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("POST", "/api/feishu/events", body=json.dumps(body), headers={"Content-Type": "application/json"})
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))
            conn.close()
        finally:
            httpd.shutdown()
            thread.join(timeout=2)
            httpd.server_close()

        self.assertEqual(res.status, 200)
        self.assertTrue(data["ok"])
        self.assertTrue(data["handled"])
        self.assertEqual(data["aiStatus"], "failed")
        record_count = self.conn.execute("SELECT COUNT(*) AS c FROM records WHERE source_event_id = 'om_http_record'").fetchone()["c"]
        todo_count = self.conn.execute("SELECT COUNT(*) AS c FROM todos").fetchone()["c"]
        self.assertEqual(record_count, 1)
        self.assertEqual(todo_count, 0)

    def test_parse_feishu_create_todo_command(self):
        self.assertEqual(server.parse_feishu_todo_command("新增任务 买菜"), "买菜")
        self.assertEqual(server.parse_feishu_todo_command("todo 写周报"), "写周报")
        self.assertEqual(server.parse_feishu_todo_command("任务 交电费"), "交电费")
        self.assertIsNone(server.parse_feishu_todo_command("hello"))

    def test_extract_feishu_message_text_from_event(self):
        body = {
            "event": {
                "message": {
                    "message_type": "text",
                    "content": json.dumps({"text": "新增任务 买菜"}, ensure_ascii=False),
                }
            }
        }

        self.assertEqual(server._extract_feishu_message_text(body), "新增任务 买菜")

    def test_extract_feishu_message_metadata(self):
        body = {
            "event": {
                "sender": {"sender_id": {"open_id": "ou_1"}, "sender_type": "user"},
                "message": {
                    "message_id": "om_123",
                    "chat_id": "oc_1",
                    "message_type": "text",
                    "content": json.dumps({"text": "hello"}, ensure_ascii=False),
                },
            }
        }

        self.assertEqual(server._extract_feishu_message_text(body), "hello")
        self.assertEqual(server._extract_feishu_message_id(body), "om_123")
        sender = server._extract_feishu_sender_info(body)
        self.assertEqual(sender["open_id"], "ou_1")
        self.assertEqual(sender["chat_id"], "oc_1")

    def test_feishu_message_creates_record_not_todo(self):
        server.AI_API_KEY = ""
        body = {
            "event": {
                "sender": {"sender_id": {"open_id": "ou_1"}},
                "message": {
                    "message_id": "om_record",
                    "message_type": "text",
                    "content": json.dumps({"text": "customer renewal quote"}, ensure_ascii=False),
                },
            }
        }

        result = server.handle_feishu_inbox_event(self.conn, "me@example.com", body)

        self.assertTrue(result["handled"])
        self.assertEqual(result["aiStatus"], "failed")
        self.assertIn("AI not configured", result["error"])
        self.assertIn("replyText", result)
        record = self.conn.execute("SELECT source, source_event_id, original_input FROM records").fetchone()
        self.assertEqual(record["source"], "feishu")
        self.assertEqual(record["source_event_id"], "om_record")
        self.assertEqual(record["original_input"], "customer renewal quote")
        todo_count = self.conn.execute("SELECT COUNT(*) AS c FROM todos").fetchone()["c"]
        self.assertEqual(todo_count, 0)

    def test_feishu_ai_success_updates_record_without_todo(self):
        server.AI_API_KEY = "test"
        body = {
            "event": {
                "message": {
                    "message_id": "om_ai",
                    "message_type": "text",
                    "content": json.dumps({"text": "quote tomorrow"}, ensure_ascii=False),
                },
            }
        }
        content = json.dumps(
            {
                "record": {
                    "summary": "quote followup",
                    "type": "task",
                    "tags": ["quote"],
                    "dates": ["2026-05-12T10:00:00+08:00"],
                    "sentiment": "neutral",
                },
                "items": [{"title": "prepare quote", "urgency": 2, "dueAt": None, "subtasks": []}],
            }
        )

        with patch.object(server, "call_xiaomi_chat_messages", return_value=content):
            result = server.handle_feishu_inbox_event(self.conn, "me@example.com", body)

        self.assertTrue(result["handled"])
        self.assertEqual(result["aiStatus"], "ready")
        self.assertEqual(result["record"]["summary"], "quote followup")
        self.assertEqual(result["items"][0]["title"], "prepare quote")
        todo_count = self.conn.execute("SELECT COUNT(*) AS c FROM todos").fetchone()["c"]
        self.assertEqual(todo_count, 0)

    def test_feishu_invalid_ai_json_keeps_failed_record(self):
        server.AI_API_KEY = "test"
        body = {
            "event": {
                "message": {
                    "message_id": "om_bad_ai",
                    "message_type": "text",
                    "content": json.dumps({"text": "bad ai"}, ensure_ascii=False),
                },
            }
        }

        with patch.object(server, "call_xiaomi_chat_messages", return_value="not json"):
            result = server.handle_feishu_inbox_event(self.conn, "me@example.com", body)

        self.assertEqual(result["aiStatus"], "failed")
        self.assertIn("invalid JSON", result["error"])
        record = self.conn.execute("SELECT ai_status, ai_error FROM records WHERE source_event_id = 'om_bad_ai'").fetchone()
        self.assertEqual(record["ai_status"], "failed")
        self.assertIn("invalid JSON", record["ai_error"])

    def test_feishu_duplicate_message_id_returns_existing_record(self):
        server.AI_API_KEY = ""
        body = {
            "event": {
                "message": {
                    "message_id": "om_dup",
                    "message_type": "text",
                    "content": json.dumps({"text": "same text"}, ensure_ascii=False),
                },
            }
        }

        first = server.handle_feishu_inbox_event(self.conn, "me@example.com", body)
        second = server.handle_feishu_inbox_event(self.conn, "me@example.com", body)

        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["recordId"], first["recordId"])
        count = self.conn.execute("SELECT COUNT(*) AS c FROM records WHERE source_event_id = 'om_dup'").fetchone()["c"]
        self.assertEqual(count, 1)

    def test_create_feishu_todo_for_default_account(self):
        todo = server.create_feishu_todo(self.conn, "me@example.com", "买菜")

        self.assertEqual(todo["title"], "买菜")
        row = self.conn.execute(
            "SELECT title, urgency, note FROM todos WHERE owner_user_id = ?",
            (todo["ownerUserId"],),
        ).fetchone()
        self.assertEqual(row["title"], "买菜")
        self.assertEqual(row["urgency"], 1)
        self.assertIn("Created from Feishu", row["note"])

    def test_create_feishu_todo_rejects_unknown_default_account(self):
        with self.assertRaisesRegex(ValueError, "default account not found"):
            server.create_feishu_todo(self.conn, "missing@example.com", "买菜")

    def test_create_feishu_ai_todos_creates_subtasks_and_due_time(self):
        content = json.dumps(
            {
                "items": [
                    {
                        "title": "打篮球",
                        "note": "带衣服",
                        "urgency": 1,
                        "dueAt": "2026-05-06T16:00:00+08:00",
                        "subtasks": ["带衣服"],
                    }
                ]
            },
            ensure_ascii=False,
        )

        with patch.object(server, "call_xiaomi_chat_completion", return_value=content):
            todos = server.create_feishu_ai_todos(self.conn, "me@example.com", "明天下午16点打篮球，带衣服")

        self.assertEqual(len(todos), 1)
        self.assertEqual(todos[0]["title"], "打篮球")
        self.assertEqual(todos[0]["subtasks"], ["带衣服"])
        sub_count = self.conn.execute("SELECT COUNT(*) AS c FROM subtasks").fetchone()["c"]
        self.assertEqual(sub_count, 1)


if __name__ == "__main__":
    unittest.main()
