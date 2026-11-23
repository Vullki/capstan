import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from core.fit import GB, estimate  # noqa: E402


class NonChatFitTest(unittest.TestCase):
    def test_non_chat_model_has_no_kv_cache(self):
        r = estimate(4 * GB, None, 131072, 12 * GB, 16 * GB, text=False)
        self.assertEqual(r["kv"], 0)

    def test_non_chat_estimate_ignores_context(self):
        a = estimate(4 * GB, None, 2048, 12 * GB, 16 * GB, text=False)
        b = estimate(4 * GB, None, 262144, 12 * GB, 16 * GB, text=False)
        self.assertEqual(a["need"], b["need"])

    def test_chat_model_still_counts_kv(self):
        r = estimate(4 * GB, None, 8192, 12 * GB, 16 * GB)
        self.assertGreater(r["kv"], 0)


if __name__ == "__main__":
    unittest.main()
