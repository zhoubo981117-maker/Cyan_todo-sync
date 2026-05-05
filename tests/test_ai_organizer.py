import json
import os
import sqlite3
import time
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import server  # noqa: E402


class AiOrganizerHelperTests(unittest.TestCase):
    def test_sanitize_ai_todo_items_clamps_and_cleans_values(self):
        raw = {
            "items": [
                {
                    "title": "  完成   方案评审  ",
                    "note": "  明确 风险点  ",
                    "urgency": 9,
                    "dueAt": "2026-05-06T18:30:00+08:00",
                    "subtasks": [" 准备材料 ", "", "同步结论"],
                }
            ]
        }

        items = server.sanitize_ai_todo_items(raw)

        self.assertEqual(items[0]["title"], "完成 方案评审")
        self.assertEqual(items[0]["note"], "明确 风险点")
        self.assertEqual(items[0]["urgency"], 3)
        self.assertEqual(items[0]["dueAt"], "2026-05-06T18:30:00+08:00")
        self.assertEqual(items[0]["subtasks"], ["准备材料", "同步结论"])

    def test_parse_ai_items_from_code_fence(self):
        text = """```json
{"items":[{"title":"买菜","urgency":1,"subtasks":["买鸡蛋"]}]}
```"""

        items = server.parse_ai_items_from_text(text)

        self.assertEqual(items[0]["title"], "买菜")
        self.assertEqual(items[0]["subtasks"], ["买鸡蛋"])

    def test_parse_ai_items_rejects_invalid_json(self):
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            server.parse_ai_items_from_text("not json")

    def test_sanitize_ai_todo_items_limits_items_and_subtasks(self):
        raw = {
            "items": [
                {"title": f"任务{i}", "subtasks": [f"子任务{j}" for j in range(20)]}
                for i in range(20)
            ]
        }

        items = server.sanitize_ai_todo_items(raw)

        self.assertEqual(len(items), 12)
        self.assertEqual(len(items[0]["subtasks"]), 12)


class AiOrganizerEndpointTests(unittest.TestCase):
    def setUp(self):
        self.old_db = server.DB
        self.old_ai_key = server.AI_API_KEY
        self.conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
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

    def request(self, body, token=True):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {self.token}"
        conn.request("POST", "/api/ai/organize", body=json.dumps(body), headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()
        return res.status, data

    def test_ai_organize_requires_authentication(self):
        server.AI_API_KEY = "test"

        status, data = self.request({"text": "新增任务 买菜"}, token=False)

        self.assertEqual(status, 401)
        self.assertFalse(data["ok"])

    def test_ai_organize_rejects_empty_text(self):
        server.AI_API_KEY = "test"

        status, data = self.request({"text": "   "})

        self.assertEqual(status, 400)
        self.assertIn("text required", data["error"])

    def test_ai_organize_requires_ai_configuration(self):
        server.AI_API_KEY = ""

        status, data = self.request({"text": "新增任务 买菜"})

        self.assertEqual(status, 503)
        self.assertIn("AI not configured", data["error"])

    def test_ai_organize_returns_sanitized_drafts(self):
        server.AI_API_KEY = "test"
        content = json.dumps(
            {"items": [{"title": " 买菜 ", "urgency": 2, "subtasks": ["鸡蛋"]}]},
            ensure_ascii=False,
        )

        with patch.object(server, "call_xiaomi_chat_completion", return_value=content):
            status, data = self.request({"text": "明天记得买菜"})

        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["items"][0]["title"], "买菜")
        self.assertEqual(data["items"][0]["subtasks"], ["鸡蛋"])

    def test_ai_organize_handles_invalid_model_json(self):
        server.AI_API_KEY = "test"

        with patch.object(server, "call_xiaomi_chat_completion", return_value="bad"):
            status, data = self.request({"text": "明天记得买菜"})

        self.assertEqual(status, 502)
        self.assertIn("invalid JSON", data["error"])


if __name__ == "__main__":
    unittest.main()
