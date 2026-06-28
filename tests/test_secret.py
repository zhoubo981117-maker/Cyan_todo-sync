import os
import unittest
from pathlib import Path

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import server  # noqa: E402


class SigningSecretTests(unittest.TestCase):
    """load_or_create_secret() 优先级：TODO_SIGNING_SECRET(env) > DB(app_kv) > 本地文件。"""

    def setUp(self):
        self._saved_env = os.environ.get("TODO_SIGNING_SECRET")
        os.environ.pop("TODO_SIGNING_SECRET", None)
        server.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("TODO_SIGNING_SECRET", None)
        else:
            os.environ["TODO_SIGNING_SECRET"] = self._saved_env

    def test_env_secret_takes_priority_over_file(self):
        # 即使本地已有 secret.key，env 也必须优先。
        server.SECRET_PATH.write_bytes(b"file-based-secret-bytes")
        os.environ["TODO_SIGNING_SECRET"] = "pinned-secret-value"
        self.assertEqual(server.load_or_create_secret(), b"pinned-secret-value")

    def test_no_env_uses_file_and_is_stable(self):
        # 未配置 env 时维持文件持久化行为，且多次调用稳定一致。
        if server.SECRET_PATH.exists():
            server.SECRET_PATH.unlink()
        first = server.load_or_create_secret()
        second = server.load_or_create_secret()
        self.assertIsInstance(first, (bytes, bytearray))
        self.assertEqual(len(first), 32)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
