import json
import os
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import feishu_client  # noqa: E402
import server  # noqa: E402


class FeishuClientTests(unittest.TestCase):
    def setUp(self):
        self.old_db = server.DB
        self.old_default_email = server.FEISHU_DEFAULT_EMAIL
        self.old_ai_key = server.AI_API_KEY
        self.conn = sqlite3.connect(":memory:", isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        server.init_db(self.conn)
        server.migrate_db(self.conn)
        salt = b"1" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("me@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )
        server.DB = self.conn
        server.FEISHU_DEFAULT_EMAIL = "me@example.com"

    def tearDown(self):
        server.DB = self.old_db
        server.FEISHU_DEFAULT_EMAIL = self.old_default_email
        server.AI_API_KEY = self.old_ai_key
        self.conn.close()

    def test_handle_event_creates_todo_from_basic_command(self):
        server.AI_API_KEY = ""
        payload = {
            "event": {
                "message": {
                    "message_type": "text",
                    "content": json.dumps({"text": "todo buy milk"}),
                }
            }
        }

        result = feishu_client.handle_feishu_event_payload(payload)

        self.assertTrue(result["handled"])
        self.assertEqual(result["todo"]["title"], "buy milk")

    def test_handle_event_uses_ai_when_configured(self):
        server.AI_API_KEY = "test-key"
        payload = {
            "event": {
                "message": {
                    "message_type": "text",
                    "content": json.dumps({"text": "basketball tomorrow 16:00"}),
                }
            }
        }
        content = json.dumps(
            {
                "items": [
                    {
                        "title": "play basketball",
                        "note": "bring clothes",
                        "urgency": 1,
                        "dueAt": "2026-05-06T16:00:00+08:00",
                        "subtasks": ["bring clothes"],
                    }
                ]
            }
        )

        with patch.object(server, "call_xiaomi_chat_completion", return_value=content):
            result = feishu_client.handle_feishu_event_payload(payload)

        self.assertTrue(result["handled"])
        self.assertEqual(result["todos"][0]["title"], "play basketball")
        self.assertEqual(result["todos"][0]["subtasks"], ["bring clothes"])

    def test_extract_message_id(self):
        payload = {"event": {"message": {"message_id": "om_123"}}}

        self.assertEqual(feishu_client.extract_message_id(payload), "om_123")


if __name__ == "__main__":
    unittest.main()
