from __future__ import annotations

import unittest

from scripts.story_builder.anime_assets import _subtitle_track_clip_lines


class CutsceneSubtitleTrackTests(unittest.TestCase):
    def test_preserves_display_timing_when_text_id_object_is_missing(self) -> None:
        clips = [{
            "m_Start": 2.5,
            "m_Duration": 1.25,
            "m_DisplayName": "字幕",
            "m_Asset": {"m_PathID": 42},
        }]
        self.assertEqual(
            _subtitle_track_clip_lines(clips, {}),
            [{
                "textId": "",
                "start": 2.5,
                "duration": 1.25,
                "displayName": "字幕",
                "clipIndex": 0,
                "assetPathId": 42,
            }],
        )

    def test_prefers_exact_playable_text_ids_when_available(self) -> None:
        clips = [{
            "m_Start": 1.0,
            "m_Duration": 2.0,
            "m_DisplayName": "字幕",
            "m_Asset": {"m_PathID": 7},
        }]
        rows = _subtitle_track_clip_lines(clips, {7: ["cutscene_test_01"]})
        self.assertEqual(rows[0]["textId"], "cutscene_test_01")


if __name__ == "__main__":
    unittest.main()
