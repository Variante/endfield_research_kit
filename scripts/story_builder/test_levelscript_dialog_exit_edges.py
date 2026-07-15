from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.story_builder.level_bindings import (
    _build_levelscript_dialog_exit_scene_pairs,
)


def resolver_for(*keys: str):
    known = set(keys)
    return lambda value: value if value in known else ""


class LevelScriptDialogExitEdgeTests(unittest.TestCase):
    def build(self, row: dict, *keys: str) -> list[dict]:
        with patch(
            "scripts.story_builder.level_bindings._build_levelscript_dialog_exit_text_pairs",
            return_value=[row],
        ):
            return _build_levelscript_dialog_exit_scene_pairs(
                "map02_lv002", resolver_for(*keys), "sm2l2m7"
            )

    def test_emits_ordered_scene_chain_after_dialog_exit(self) -> None:
        rows = self.build(
            {
                "file": "LevelScriptData/map02_lv002/1.json",
                "sourceScript": "1",
                "headerLocalId": 4,
                "targetLocalId": 5,
                "sourceTexts": ["dlg_sm2l2m7_8"],
                "targetTextGroups": [
                    {"localId": 5, "texts": ["black_sm2l2m7_1_001"]},
                    {"localId": 6, "texts": ["dlg_sm2l2m7_9"]},
                ],
            },
            "dlg_sm2l2m7_8",
            "black_sm2l2m7_1",
            "dlg_sm2l2m7_9",
        )
        self.assertEqual(
            [(row["src"], row["dst"], row["position"]) for row in rows],
            [
                ("dlg_sm2l2m7_8", "black_sm2l2m7_1", 0),
                ("black_sm2l2m7_1", "dlg_sm2l2m7_9", 1),
            ],
        )
        self.assertEqual(rows[0]["event"], "LevelEvent_OnDialogExit")
        self.assertEqual(rows[1]["targetLocalId"], 6)

    def test_rejects_two_story_targets_in_one_action_record(self) -> None:
        rows = self.build(
            {
                "sourceTexts": ["dlg_sm2l2m7_8"],
                "targetTextGroups": [
                    {
                        "localId": 5,
                        "texts": ["radio_sm2l2m7_1", "dlg_sm2l2m7_9"],
                    }
                ],
            },
            "dlg_sm2l2m7_8",
            "radio_sm2l2m7_1",
            "dlg_sm2l2m7_9",
        )
        self.assertEqual(rows, [])

    def test_rejects_ambiguous_source_header(self) -> None:
        rows = self.build(
            {
                "sourceTexts": ["dlg_sm2l2m7_8", "dlg_sm2l2m7_7"],
                "targetTextGroups": [
                    {"localId": 5, "texts": ["dlg_sm2l2m7_9"]}
                ],
            },
            "dlg_sm2l2m7_7",
            "dlg_sm2l2m7_8",
            "dlg_sm2l2m7_9",
        )
        self.assertEqual(rows, [])

    def test_drops_self_reference_only_chain(self) -> None:
        rows = self.build(
            {
                "sourceTexts": ["dlg_sm2l2m7_8"],
                "targetTextGroups": [
                    {"localId": 5, "texts": ["dlg_sm2l2m7_8"]}
                ],
            },
            "dlg_sm2l2m7_8",
        )
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
