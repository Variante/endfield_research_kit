from __future__ import annotations

import unittest

from scripts.story_builder.radio_continuation import (
    build_radio_continuation_candidates,
)


class RadioContinuationTests(unittest.TestCase):
    def test_combines_authored_flags_with_same_file_serialized_order(self) -> None:
        files_by_level = {
            "level_a": {
                "files": [{
                    "file": "LevelScriptData/level_a/10.json",
                    "stringHits": [
                        {"offset": 10, "text": "dlg_m1_1"},
                        {"offset": 20, "text": "radio_m1_1"},
                        {"offset": 30, "text": "radio_m1_2"},
                    ],
                }],
            },
        }
        radios = {
            "radio_m1_1": {"continueAfterDialog": True},
            "radio_m1_2": {"continueAfterRadio": True},
        }
        available = {"dlg_m1_1", "radio_m1_1", "radio_m1_2"}

        candidates = build_radio_continuation_candidates(
            "m1",
            ["level_a", "level_a"],
            radios,
            lambda value: value if value in available else "",
            load_levelscript=files_by_level.__getitem__,
        )

        self.assertEqual(2, len(candidates))
        self.assertEqual(
            [
                ("dlg_m1_1", "radio_m1_1", "after-dialog"),
                ("radio_m1_1", "radio_m1_2", "after-radio"),
            ],
            [
                (row["predecessor"], row["radio"], row["match"])
                for row in candidates
            ],
        )
        self.assertEqual(10, candidates[0]["predecessorOffset"])
        self.assertEqual(20, candidates[0]["radioOffset"])
        self.assertEqual(
            "authored_radio_continuation_flag_plus_same_file_serialized_order",
            candidates[0]["evidence"],
        )
        self.assertFalse(candidates[0]["missionOwnershipEvidence"])
        self.assertFalse(candidates[0]["branchSelectionEvidence"])

    def test_does_not_carry_predecessors_across_files(self) -> None:
        source = {
            "files": [
                {
                    "file": "LevelScriptData/level_a/1.json",
                    "stringHits": [{"offset": 10, "text": "dlg_m1_1"}],
                },
                {
                    "file": "LevelScriptData/level_a/2.json",
                    "stringHits": [{"offset": 10, "text": "radio_m1_1"}],
                },
            ],
        }

        candidates = build_radio_continuation_candidates(
            "m1",
            ["level_a"],
            {"radio_m1_1": {"continueAfterDialog": True}},
            lambda value: value,
            load_levelscript=lambda _level_id: source,
        )

        self.assertEqual([], candidates)

    def test_requires_resolved_mission_story_nodes_and_authored_flags(self) -> None:
        source = {
            "files": [{
                "file": "LevelScriptData/level_a/1.json",
                "stringHits": [
                    {"offset": 10, "text": "dlg_other_1"},
                    {"offset": 20, "text": "radio_m1_1"},
                    {"offset": 30, "text": "radio_m1_2"},
                ],
            }],
        }
        available = {"radio_m1_1", "radio_m1_2"}

        candidates = build_radio_continuation_candidates(
            "m1",
            ["level_a"],
            {
                "radio_m1_1": {"continueAfterDialog": True},
                "radio_m1_2": {},
            },
            lambda value: value if value in available else "",
            load_levelscript=lambda _level_id: source,
        )

        self.assertEqual([], candidates)


if __name__ == "__main__":
    unittest.main()
