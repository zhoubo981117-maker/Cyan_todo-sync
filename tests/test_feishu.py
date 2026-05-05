import os
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import server  # noqa: E402


class FeishuTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:", isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        server.init_db(self.conn)
        server.migrate_db(self.conn)
        salt = b"0" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("me@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )

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
