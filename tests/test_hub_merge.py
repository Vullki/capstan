import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from core.hub import merge_results  # noqa: E402


def row(i, downloads=0, likes=0, updated=None, trending=0):
    return {"id": i, "downloads": downloads, "likes": likes, "updated": updated, "trending": trending}


class MergeTest(unittest.TestCase):
    def test_duplicate_kept_once(self):
        out = merge_results([[row("a/x", 5)], [row("a/x", 5), row("b/y", 1)]], "downloads")
        self.assertEqual([r["id"] for r in out], ["a/x", "b/y"])

    def test_sorted_by_downloads_desc(self):
        out = merge_results([[row("a", 1), row("b", 9)], [row("c", 5)]], "downloads")
        self.assertEqual([r["id"] for r in out], ["b", "c", "a"])

    def test_sorted_by_updated_handles_missing(self):
        out = merge_results([[row("a", updated=None), row("b", updated="2026-11-20T00:00:00")]], "updated")
        self.assertEqual([r["id"] for r in out], ["b", "a"])

    def test_sorted_by_trending(self):
        out = merge_results([[row("a", trending=3), row("b", trending=7)]], "trending")
        self.assertEqual([r["id"] for r in out], ["b", "a"])


if __name__ == "__main__":
    unittest.main()
