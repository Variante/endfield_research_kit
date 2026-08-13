import unittest

from scripts.story_builder.video_bindings import (
    compact_narrative_video_ref,
    narrative_video_index_summary,
    narrative_video_search_text,
    narrative_video_sort_key,
)


class NarrativeVideoProjectionTests(unittest.TestCase):
    def test_compact_ref_keeps_authoritative_debug_evidence(self):
        ref = {
            "name": "clip.mp4",
            "rel": "video/clip.mp4",
            "source": "StreamingAssets-structured",
            "format": "mp4",
            "size": 42,
            "baseStem": "clip",
            "kind": "fmv",
            "gender": "f",
            "binding": {"fmvId": "clip"},
            "authoritativeKeys": ["cutscene_test"],
        }

        compact = compact_narrative_video_ref(ref)

        self.assertEqual(compact["binding"], {"fmvId": "clip"})
        self.assertEqual(compact["gender"], "f")
        self.assertEqual(
            compact["_debug"]["source"]["authoritativeKeys"],
            ["cutscene_test"],
        )

    def test_sort_key_prefers_structured_mp4_and_default_gender(self):
        refs = [
            {"baseStem": "clip", "source": "raw_vfs", "format": "usm", "gender": "f", "rel": "c"},
            {"baseStem": "clip", "source": "StreamingAssets-structured", "format": "mp4", "rel": "a"},
        ]

        self.assertEqual(sorted(refs, key=narrative_video_sort_key)[0]["rel"], "a")

    def test_search_and_summary_preserve_identity_and_file_order(self):
        refs = [
            {"name": "b.mp4", "source": "raw_vfs", "format": "mp4", "kind": "fmv"},
            {"name": "a.usm", "source": "raw_vfs", "format": "usm", "kind": "fmv"},
            {"name": "b.mp4", "source": "Persistent-structured", "format": "mp4"},
        ]

        self.assertIn("b.mp4 raw_vfs", narrative_video_search_text(refs))
        self.assertEqual(
            narrative_video_index_summary(refs),
            {
                "n": 3,
                "sources": {"Persistent-structured": 1, "raw_vfs": 2},
                "formats": {"mp4": 2, "usm": 1},
                "files": ["b.mp4", "a.usm"],
            },
        )


if __name__ == "__main__":
    unittest.main()
