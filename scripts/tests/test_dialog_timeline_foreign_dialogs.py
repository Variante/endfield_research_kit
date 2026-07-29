from __future__ import annotations

import unittest

from scripts.story_builder.dialog_tree import (
    recover_foreign_dialog_timeline_containments,
)


class DialogTimelineForeignDialogTests(unittest.TestCase):
    def test_recovers_complete_contiguous_foreign_block(self) -> None:
        registry = {
            "dlg_test_1": {
                "usedDialogTimelineIds": ["dlgtl_test_1_sub_1"],
            },
        }
        entries = {
            "dlg_test_1": [{
                "sourceKey": "dlgtl_test_1_sub_1",
                "timeline": "dlgtl_test_1_sub_1",
                "file": "CAB-test",
                "lineIds": [
                    "dlg_test_1_001",
                    "dlg_test_2_001",
                    "dlg_test_2_002",
                    "dlg_test_1_002",
                ],
                "optionIds": [
                    "option_dlg_test_2_1_001",
                    "option_dlg_test_2_1_002",
                ],
            }],
        }

        rows = recover_foreign_dialog_timeline_containments(
            registry,
            {"dlg_test_1", "dlg_test_2"},
            {
                "dlg_test_1_001",
                "dlg_test_1_002",
                "dlg_test_2_001",
                "dlg_test_2_002",
            },
            timeline_loader=lambda key: entries.get(key, []),
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("dlg_test_2", rows[0]["key"])
        self.assertEqual("dlg_test_1", rows[0]["dialogKey"])
        self.assertEqual(
            ["dlg_test_2_001", "dlg_test_2_002"],
            rows[0]["lineIds"],
        )
        self.assertEqual("dlg_test_1_001", rows[0]["beforeParentLineId"])
        self.assertEqual("dlg_test_1_002", rows[0]["afterParentLineId"])
        self.assertEqual(
            [
                "option_dlg_test_2_1_001",
                "option_dlg_test_2_1_002",
            ],
            rows[0]["optionIds"],
        )

    def test_rejects_partial_noncontiguous_and_ambiguous_owners(self) -> None:
        available = {"dlg_test_1", "dlg_test_2"}
        line_ids = {
            "dlg_test_1_001",
            "dlg_test_1_002",
            "dlg_test_2_001",
            "dlg_test_2_002",
        }
        partial = [{
            "timeline": "dlgtl_test_1_sub_1",
            "lineIds": [
                "dlg_test_1_001",
                "dlg_test_2_001",
                "dlg_test_1_002",
            ],
        }]
        self.assertEqual(
            [],
            recover_foreign_dialog_timeline_containments(
                {
                    "dlg_test_1": {
                        "usedDialogTimelineIds": [
                            "dlgtl_test_1_sub_1",
                        ],
                    },
                },
                available,
                line_ids,
                timeline_loader=lambda _key: partial,
            ),
        )

        ambiguous_registry = {
            key: {
                "usedDialogTimelineIds": ["dlgtl_test_1_sub_1"],
            }
            for key in ("dlg_test_1", "dlg_test_3")
        }
        self.assertEqual(
            [],
            recover_foreign_dialog_timeline_containments(
                ambiguous_registry,
                available,
                line_ids,
                timeline_loader=lambda _key: partial,
            ),
        )


if __name__ == "__main__":
    unittest.main()
