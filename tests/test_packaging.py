"""1.5.0: what the installed (frozen) build relies on."""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import api as api_mod  # noqa: E402
from core import downloads, fonts  # noqa: E402


class WorkerCmdTest(unittest.TestCase):
    def test_source_runs_the_module(self):
        with mock.patch.object(sys, "frozen", False, create=True):
            self.assertEqual(downloads.worker_cmd("{}")[1:], ["-m", "core.worker", "{}"])

    def test_frozen_starts_itself_with_worker_flag(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            self.assertEqual(downloads.worker_cmd("{}"), [sys.executable, "--worker", "{}"])


class FontsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.new, self.old = os.path.join(self.tmp, "new"), os.path.join(self.tmp, "old")
        os.makedirs(self.old)
        self.p = [mock.patch.object(fonts, "FONTS_DIR", self.new), mock.patch.object(fonts, "_OLD_DIR", self.old)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        shutil.rmtree(self.tmp)

    def test_old_files_are_copied_to_the_data_folder(self):
        with open(os.path.join(self.old, "Satoshi-400.woff2"), "wb") as f:
            f.write(b"wOF2" + b"\0" * 2000)
        self.assertEqual(fonts.missing(), [500, 700])
        self.assertEqual(fonts.present(), [400])
        self.assertTrue(fonts.data()["400"].startswith("d09GMg"))   # base64 of "wOF2"

    def test_tiny_files_dont_count(self):
        os.makedirs(self.new)
        with open(fonts.path(500), "wb") as f:
            f.write(b"x")
        self.assertEqual(fonts.present(), [])


class HfLoginTest(unittest.TestCase):
    def test_rejects_non_tokens_without_a_network_call(self):
        a = api_mod.Api.__new__(api_mod.Api)
        with mock.patch("huggingface_hub.whoami") as who:
            r = a.hf_login("not-a-token")
        self.assertIn("hf_", r["error"])
        who.assert_not_called()


if __name__ == "__main__":
    unittest.main()
