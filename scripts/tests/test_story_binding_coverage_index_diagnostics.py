from __future__ import annotations

import unittest

from scripts.build_mission_pipeline_data import (
    normalize_story_binding_coverage_index_row,
)


class StoryBindingCoverageIndexDiagnosticsTests(unittest.TestCase):
    def test_preserves_playback_diagnostic_without_connection_claim(self) -> None:
        row = normalize_story_binding_coverage_index_row({
            "k": "cutscene_fixture",
            "d": "cutscene",
            "m": "fixture",
            "p": "preview",
            "playbackUse": {
                "status": "playback_observed",
                "automaticUnused": False,
            },
            "automaticUnused": False,
        })
        self.assertEqual("playback_observed", row["playbackUse"]["status"])
        self.assertFalse(row["automaticUnused"])
        self.assertNotIn("connected", row)
        self.assertNotIn("missionBinding", row)

    def test_omits_absent_diagnostic_for_legacy_inputs(self) -> None:
        row = normalize_story_binding_coverage_index_row({
            "k": "dlg_fixture", "d": "dlg", "m": "fixture",
        })
        self.assertNotIn("playbackUse", row)
        self.assertNotIn("automaticUnused", row)


if __name__ == "__main__":
    unittest.main()
