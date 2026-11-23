import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from core.hub import group_gguf  # noqa: E402


def f(path, size):
    return {"path": path, "size": size, "sha256": None}


class GroupTest(unittest.TestCase):
    FILES = [
        f("imatrix_unsloth.gguf", 12_000_000),
        f("Qwen3.8-27B-UD-IQ1_S.gguf", 5_800_000_000),
        f("Qwen3.8-27B-Q4_K_M.gguf", 16_000_000_000),
        f("mmproj-F16.gguf", 900_000_000),
        f("README.md", 9_000),
    ]

    def test_imatrix_is_not_a_model_row(self):
        gguf, _ = group_gguf(self.FILES)
        self.assertNotIn("imatrix_unsloth.gguf", [g["name"] for g in gguf])

    def test_imatrix_is_still_downloadable_as_another_file(self):
        _, others = group_gguf(self.FILES)
        self.assertIn("imatrix_unsloth.gguf", [o["path"] for o in others])

    def test_smallest_model_is_a_real_model(self):
        gguf, _ = group_gguf(self.FILES)
        models = [g for g in gguf if not g["mmproj"]]
        self.assertEqual(min(models, key=lambda g: g["size"])["name"], "Qwen3.8-27B-UD-IQ1_S.gguf")

    def test_imatrix_does_not_shorten_labels(self):
        gguf, _ = group_gguf(self.FILES)
        labels = {g["label"] for g in gguf if not g["mmproj"]}
        self.assertEqual(labels, {"UD-IQ1_S", "Q4_K_M"})

    def test_named_imatrix_variants(self):
        gguf, others = group_gguf([f("model.imatrix.gguf", 1), f("model-Q4_K_M.gguf", 10)])
        self.assertEqual([g["name"] for g in gguf], ["model-Q4_K_M.gguf"])
        self.assertEqual([o["path"] for o in others], ["model.imatrix.gguf"])


if __name__ == "__main__":
    unittest.main()
