import json
import os
import sqlite3
import time
import unittest
from datetime import datetime, timedelta, timezone
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

    def test_ai_prompt_contains_current_beijing_date(self):
        now = datetime(2026, 5, 5, 13, 40, tzinfo=timezone(timedelta(hours=8)))

        prompt = server._ai_prompt(now)

        self.assertIn("2026-05-05", prompt)
        self.assertIn("明天是 2026-05-06", prompt)
        self.assertIn("+08:00", prompt)

    def test_relative_due_fallback_repairs_stale_model_date(self):
        now = datetime(2026, 5, 5, 13, 40, tzinfo=timezone(timedelta(hours=8)))
        items = [{"title": "打篮球", "note": "", "urgency": 1, "dueAt": "2023-10-02T16:00:00+08:00", "subtasks": []}]

        fixed = server._apply_relative_due_fallback(items, "明天下午16点打篮球", now)

        self.assertEqual(fixed[0]["dueAt"], "2026-05-06T16:00:00+08:00")

    def test_parse_daily_plan_from_text(self):
        text = """```json
{"date":"2026-05-05","summary":"先做紧急事项","items":[{"time":"09:00","text":"完成方案评审","todoIds":[1,"2","bad"]}]}
```"""

        plan = server.parse_daily_plan_from_text(text)

        self.assertEqual(plan["date"], "2026-05-05")
        self.assertEqual(plan["items"][0]["todoIds"], [1, 2])


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

    def request(self, body, token=True, path="/api/ai/organize"):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {self.token}"
        conn.request("POST", path, body=json.dumps(body), headers=headers)
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

    def test_daily_plan_returns_mocked_plan(self):
        server.AI_API_KEY = "test"
        self.conn.execute(
            """
            INSERT INTO todos(owner_user_id, client_id, title, note, urgency, repeat_rule, reminder_minutes, due_at, done, done_at, deleted_at, created_at, updated_at)
            VALUES (1, 'todo-1', '完成方案评审', '', 2, 'none', NULL, NULL, 0, NULL, NULL, ?, ?)
            """,
            (server._utc_now_iso(), server._utc_now_iso()),
        )
        plan = {"date": "2026-05-05", "summary": "先做评审", "items": [{"time": "09:00", "text": "完成方案评审", "todoIds": [1]}]}
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}

        with patch.object(server, "call_xiaomi_daily_plan", return_value=plan):
            conn.request("POST", "/api/ai/daily-plan", body="{}", headers=headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))
        conn.close()

        self.assertEqual(res.status, 200)
        self.assertEqual(data["plan"]["summary"], "先做评审")
        self.assertEqual(data["todoCount"], 1)

    def test_short_feishu_url_verification_path(self):
        status, data = self.request(
            {"type": "url_verification", "challenge": "abc", "token": ""},
            token=False,
            path="/feishu",
        )

        self.assertEqual(status, 200)
        self.assertEqual(data["challenge"], "abc")

    def test_feishu_url_verification_ignores_token_mismatch(self):
        old_token = server.FEISHU_VERIFY_TOKEN
        server.FEISHU_VERIFY_TOKEN = "server-token"
        try:
            status, data = self.request(
                {"type": "url_verification", "challenge": "abc", "token": "console-token"},
                token=False,
                path="/api/feishu/events",
            )
        finally:
            server.FEISHU_VERIFY_TOKEN = old_token

        self.assertEqual(status, 200)
        self.assertEqual(data["challenge"], "abc")

    def test_password_reset_request_is_rate_limited(self):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        body = json.dumps({"email": "me@example.com"})

        with patch.object(server, "_send_reset_email", return_value=False):
            conn.request("POST", "/api/password/forgot", body=body, headers=headers)
            first = conn.getresponse()
            first_data = json.loads(first.read().decode("utf-8"))
            conn.request("POST", "/api/password/forgot", body=body, headers=headers)
            second = conn.getresponse()
            second_data = json.loads(second.read().decode("utf-8"))
        conn.close()

        self.assertEqual(first.status, 200)
        self.assertTrue(first_data["ok"])
        self.assertEqual(second.status, 429)
        self.assertIn("retryAfter", second_data)


if __name__ == "__main__":
    unittest.main()
