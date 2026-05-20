import json
import os
import sqlite3
import time
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import server  # noqa: E402


class ReleaseEndpointTests(unittest.TestCase):
    def setUp(self):
        self.old_db = server.DB
        self.conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        server.init_db(self.conn)
        server.migrate_db(self.conn)
        salt = b"7" * 16
        self.conn.execute(
            "INSERT INTO users(email, pw_salt, pw_hash, created_at) VALUES (?, ?, ?, ?)",
            ("release@example.com", salt, server.password_hash("password", salt), server._utc_now_iso()),
        )
        server.DB = self.conn
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = __import__("threading").Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.token = server.sign_token(
            {"uid": 1, "email": "release@example.com", "exp": int(time.time()) + 3600}
        )

    def tearDown(self):
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        self.httpd.server_close()
        self.conn.close()
        server.DB = self.old_db

    def request(self, method, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, headers={"Authorization": f"Bearer {self.token}"})
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        headers = {k.lower(): v for k, v in res.getheaders()}
        data = {}
        if raw and headers.get("content-type", "").startswith("application/json"):
            data = json.loads(raw)
        status = res.status
        conn.close()
        return status, headers, data

    def test_version_response_is_not_cacheable_and_has_stable_shape(self):
        status, headers, data = self.request("GET", "/api/version")

        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-cache, no-store, must-revalidate")
        self.assertTrue(data["ok"])
        self.assertIn("time", data)
        self.assertIn("version", data)
        self.assertIn("short", data["version"])
        self.assertIn("source", data["version"])

    def test_static_assets_use_update_friendly_cache_headers(self):
        status, headers, _ = self.request("GET", "/sw.js")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-cache, no-store, must-revalidate")

        status, headers, _ = self.request("GET", "/app.js")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-cache, no-store, must-revalidate")
