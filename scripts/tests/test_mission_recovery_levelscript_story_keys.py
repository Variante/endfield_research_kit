from __future__ import annotations

import unittest

from scripts.story_builder.mission_recovery import build_levelscript_story_keys_map


class MissionRecoveryLevelScriptStoryKeyTests(unittest.TestCase):
    def test_rejects_weak_cross_file_order_as_script_scope(self) -> None:
        rows = build_levelscript_story_keys_map([{
            "from": "radio_example_1",
            "to": "dlg_example_2",
            "kind": "levelscriptCrossFileOrder",
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/level_a/1001.json",
                "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/level_a/1002.json",
            ],
        }])

        self.assertEqual(rows, {})

    def test_accepts_strong_single_file_edge(self) -> None:
        rows = build_levelscript_story_keys_map([{
            "from": "dlg_example_1",
            "to": "dlg_example_2",
            "kind": "levelscriptSceneChain",
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/level_a/1001.json",
            ],
        }])

        self.assertEqual(
            rows,
            {("level_a", "1001"): {"dlg_example_1", "dlg_example_2"}},
        )

    def test_rejects_even_strong_edge_when_source_file_is_ambiguous(self) -> None:
        rows = build_levelscript_story_keys_map([{
            "from": "dlg_example_1",
            "to": "dlg_example_2",
            "kind": "levelscriptSceneChain",
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/level_a/1001.json",
                "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/level_a/1002.json",
            ],
        }])

        self.assertEqual(rows, {})


if __name__ == "__main__":
    unittest.main()
