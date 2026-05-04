import os
import json
import sqlite3
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
