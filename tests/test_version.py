import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["TODO_DATA_DIR"] = str(Path(__file__).resolve().parent / "tmp_data")

import server  # noqa: E402


class GitVersionTests(unittest.TestCase):
    """_git_version() 来源优先级：TODO_APP_VERSION -> VERCEL_GIT_COMMIT_SHA -> git -> unknown。"""

    def setUp(self):
        self._saved = {
            k: os.environ.get(k)
            for k in ("TODO_APP_VERSION", "VERCEL_GIT_COMMIT_SHA")
        }
        for k in self._saved:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_todo_app_version_has_highest_priority(self):
        os.environ["TODO_APP_VERSION"] = "abcdef1234567890"
        os.environ["VERCEL_GIT_COMMIT_SHA"] = "ffffffffffffffff"
        v = server._git_version()
        self.assertEqual(v["source"], "env")
        self.assertEqual(v["short"], "abcdef1")

    def test_vercel_sha_used_when_no_explicit_version(self):
        os.environ["VERCEL_GIT_COMMIT_SHA"] = "1234567deadbeef"
        v = server._git_version()
        self.assertEqual(v["source"], "vercel")
        self.assertEqual(v["short"], "1234567")
        self.assertEqual(v["commit"], "1234567deadbeef")

    def test_falls_back_to_local_git(self):
        with patch.object(server.subprocess, "check_output", return_value="cafebabe1234\n"):
            v = server._git_version()
        self.assertEqual(v["source"], "git")
        self.assertEqual(v["short"], "cafebab")

    def test_unknown_when_nothing_available(self):
        with patch.object(server.subprocess, "check_output", side_effect=OSError("no git")):
            v = server._git_version()
        self.assertEqual(v["source"], "unknown")
        self.assertEqual(v["short"], "unknown")


if __name__ == "__main__":
    unittest.main()
