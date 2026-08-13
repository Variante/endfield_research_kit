import unittest

from scripts.story_builder.story_issue_labels import (
    dialog_option_issue_targets,
    dialog_story_issue_codes,
)


def payload_with_layout_groups(group_details):
    return {
        "warnings": [
            {
                "code": "sceneOrderDisorder",
                "problematicAspects": ["optionLayout"],
                "optionLayout": {"status": "inferred"},
            },
            {
                "code": "inferredOptionLayout",
                "groupDetails": group_details,
            },
        ]
    }


class StoryIssueLabelTests(unittest.TestCase):
    def test_option_layout_modes_are_reported_separately(self):
        payload = payload_with_layout_groups(
            [
                {"group": 1, "status": "keyedAfter", "after": "dlg_test_001", "inferredAnchorMode": "lineNumber"},
                {"group": 2, "status": "fallbackAfter", "after": "dlg_test_003", "inferredAnchorMode": "sparseGap"},
                {"group": 3, "status": "fallbackAfter", "after": "dlg_test_009", "inferredAnchorMode": "lastLine"},
                {"group": 4, "status": "unanchored", "after": "", "inferredAnchorMode": ""},
            ]
        )

        self.assertEqual(
            dialog_story_issue_codes(payload),
            [
                "keyedOptionLayout",
                "gapOptionLayout",
                "lastLineOptionLayout",
                "unanchoredOptionLayout",
            ],
        )

    def test_manual_layout_groups_do_not_add_automatic_layout_issue(self):
        payload = payload_with_layout_groups(
            [
                {
                    "group": 1,
                    "status": "fallbackAfter",
                    "after": "dlg_test_003",
                    "inferredAnchorMode": "sparseGap",
                    "manualLayoutOverride": True,
                }
            ]
        )

        self.assertNotIn("gapOptionLayout", dialog_story_issue_codes(payload))

    def test_legacy_payload_keeps_compatibility_issue(self):
        payload = payload_with_layout_groups([])

        self.assertIn("inferredOptionLayout", dialog_story_issue_codes(payload))

    def test_unregistered_layout_is_reported_as_table_only(self):
        payload = payload_with_layout_groups(
            [
                {"group": 1, "status": "keyedAfter", "after": "dlg_test_001", "inferredAnchorMode": "lineNumber"},
                {"group": 2, "status": "fallbackAfter", "after": "dlg_test_003", "inferredAnchorMode": "sparseGap"},
            ]
        )
        payload["_debug"] = {"runtimeRegistry": {"registered": False}}

        self.assertEqual(dialog_story_issue_codes(payload), ["tableOnlyOptionLayout"])
        self.assertEqual(
            dialog_option_issue_targets(payload),
            {"layoutGroupsByCode": {"tableOnlyOptionLayout": ["1", "2"]}},
        )

    def test_option_issue_targets_keep_mixed_modes_separate(self):
        payload = payload_with_layout_groups(
            [
                {"group": 1, "status": "keyedAfter", "after": "dlg_test_001", "inferredAnchorMode": "lineNumber"},
                {"group": 2, "status": "fallbackAfter", "after": "dlg_test_003", "inferredAnchorMode": "sparseGap"},
                {"group": 3, "status": "fallbackAfter", "after": "dlg_test_009", "inferredAnchorMode": "lastLine"},
            ]
        )

        self.assertEqual(
            dialog_option_issue_targets(payload),
            {
                "layoutGroupsByCode": {
                    "keyedOptionLayout": ["1"],
                    "gapOptionLayout": ["2"],
                    "lastLineOptionLayout": ["3"],
                }
            },
        )

    def test_option_response_targets_are_indexed(self):
        payload = {
            "warnings": [
                {
                    "code": "inferredOptionResponse",
                    "optionIds": ["option_test_1", "option_test_2"],
                }
            ]
        }

        self.assertEqual(
            dialog_option_issue_targets(payload),
            {"responseOptionIds": ["option_test_1", "option_test_2"]},
        )


if __name__ == "__main__":
    unittest.main()
