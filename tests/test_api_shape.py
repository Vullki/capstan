import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import api as api_mod  # noqa: E402
from core import gguf, store  # noqa: E402

EMPTY = {"architecture": "", "layers": 0, "layer_kind": [], "kv_heads": [], "context_max": 0}
GOOD = {"architecture": "qwen35", "layers": 64, "layer_kind": ["full"] * 64, "kv_heads": [4] * 64, "context_max": 262144}


class ShapeTest(unittest.TestCase):
    def setUp(self):
        self.api = api_mod.Api.__new__(api_mod.Api)   # no window or queue needed for shape()

    def test_empty_header_is_not_trusted_or_cached(self):
        with mock.patch.object(store, "cached_shape", return_value=None), \
             mock.patch.object(store, "cache_shape") as cache, \
             mock.patch.object(gguf, "read_metadata", return_value={}), \
             mock.patch.object(gguf, "model_shape", return_value=EMPTY):
            r = self.api.shape("o/r", "x.gguf")
        self.assertIsNone(r["shape"])
        cache.assert_not_called()

    def test_empty_cached_shape_is_ignored(self):
        with mock.patch.object(store, "cached_shape", return_value=EMPTY), \
             mock.patch.object(store, "cache_shape"), \
             mock.patch.object(gguf, "read_metadata", return_value={}), \
             mock.patch.object(gguf, "model_shape", return_value=GOOD):
            r = self.api.shape("o/r", "x.gguf")
        self.assertEqual(r["shape"]["layers"], 64)

    def test_good_header_is_cached(self):
        with mock.patch.object(store, "cached_shape", return_value=None), \
             mock.patch.object(store, "cache_shape") as cache, \
             mock.patch.object(gguf, "read_metadata", return_value={}), \
             mock.patch.object(gguf, "model_shape", return_value=GOOD):
            r = self.api.shape("o/r", "x.gguf")
        self.assertEqual(r["shape"]["layers"], 64)
        cache.assert_called_once()


if __name__ == "__main__":
    unittest.main()
