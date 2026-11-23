import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from core.modeltype import BUCKET_PIPELINES, classify  # noqa: E402


class ClassifyTest(unittest.TestCase):
    def test_untagged_chat_model_with_mmproj_is_text_and_vision(self):
        r = classify(None, ["gguf", "conversational"], ["Qwen3.8-27B-Q4_K_M.gguf", "mmproj-F16.gguf"])
        self.assertEqual(r["types"], ["text", "vision"])
        self.assertTrue({"text", "vision"} <= set(r["buckets"]))
        self.assertTrue(r["vision_projector"])

    def test_music_tag(self):
        r = classify(None, ["gguf", "music-generation", "text-to-music"], ["yue2.gguf"])
        self.assertEqual(r["types"], ["music"])
        self.assertEqual(r["buckets"], ["audio"])

    def test_audio_mmproj_is_not_vision(self):
        r = classify(None, ["gguf", "audio", "speech", "conversational"], ["LFM2.5-Audio.gguf", "mmproj-audio.gguf"])
        self.assertNotIn("vision", r["types"])
        self.assertNotIn("vision", r["buckets"])
        self.assertFalse(r["vision_projector"])

    def test_vision_label_without_projector(self):
        r = classify("image-text-to-text", ["gguf"], ["model-Q4_K_M.gguf"])
        self.assertIn("vision_no_proj", r["types"])
        self.assertNotIn("vision", r["types"])
        self.assertIn("vision", r["buckets"])

    def test_nothing_known_is_unlabeled(self):
        r = classify(None, ["gguf"], [])
        self.assertEqual(r["types"], ["unlabeled"])
        self.assertEqual(r["buckets"], [])

    def test_embeddings(self):
        r = classify(None, ["gguf", "feature-extraction"], [])
        self.assertEqual(r["types"], ["embeddings"])
        self.assertEqual(r["buckets"], ["embeddings"])

    def test_video_generation(self):
        r = classify("image-text-to-video", ["gguf"], [])
        self.assertEqual(r["types"], ["video_gen"])
        self.assertEqual(r["buckets"], ["video"])

    def test_multimodal_tag_on_a_generator_is_not_vision(self):
        r = classify("image-text-to-video", ["multimodal", "video-generation"], ["minimax-h3-Q4_K_M.gguf"])
        self.assertEqual(r["types"], ["video_gen"])
        self.assertEqual(r["buckets"], ["video"])

    def test_any_to_any_is_omni(self):
        r = classify("any-to-any", ["gguf"], [])
        self.assertIn("omni", r["types"])
        self.assertTrue({"text", "vision"} <= set(r["buckets"]))

    def test_official_text_label(self):
        r = classify("text-generation", ["gguf", "conversational"], ["m.gguf"])
        self.assertEqual(r["types"], ["text"])
        self.assertEqual(r["buckets"], ["text"])

    def test_speech_both_ways(self):
        r = classify("text-to-speech", ["automatic-speech-recognition"], [])
        self.assertEqual(r["types"], ["stt", "tts"])
        self.assertEqual(r["buckets"], ["audio"])

    def test_bucket_pipelines_cover_every_filter(self):
        for b in ("text", "vision", "audio", "image", "video", "embeddings"):
            self.assertTrue(BUCKET_PIPELINES[b], b)


if __name__ == "__main__":
    unittest.main()
