import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery.ocr import extract


class OcrExtractCacheTests(unittest.TestCase):
    def test_cache_fingerprint_requires_path_size_and_mtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            video = Path(temporary) / "fixture.mp4"
            video.write_bytes(b"fixture")
            fingerprint = extract.video_fingerprint(video)
            self.assertTrue(extract.same_fingerprint(fingerprint, dict(fingerprint)))
            for key, value in (
                ("path", "different.mp4"),
                ("size", fingerprint["size"] + 1),
                ("mtimeNs", fingerprint["mtimeNs"] + 1),
            ):
                with self.subTest(key=key):
                    changed = dict(fingerprint)
                    changed[key] = value
                    self.assertFalse(extract.same_fingerprint(fingerprint, changed))

    def test_incomplete_report_is_never_reused(self):
        params = {"frameStep": 10, "limitFrames": None}
        self.assertFalse(extract.reusable_complete_report({"status": "running"}, params))
        self.assertTrue(
            extract.reusable_complete_report(
                {"status": "complete", "parameters": dict(params)},
                params,
            )
        )


if __name__ == "__main__":
    unittest.main()
