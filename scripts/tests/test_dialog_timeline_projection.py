from __future__ import annotations

import unittest

from scripts.story_builder.dialog_timeline_projection import (
    attach_duplicate_timestamp_warning,
    attach_timeline_action_evidence,
    attach_timeline_timestamp_regression_warning,
    build_duplicate_timestamp_warning,
    build_timeline_timestamp_regression_warning,
)


def _seconds(value: float) -> str:
    return f"{value:.0f}s"


class DialogTimelineProjectionTests(unittest.TestCase):
    def test_duplicate_timestamp_warning_groups_by_timeline_and_display_label(self):
        payload = {
            "lines": [
                {"id": "line_1", "actor": "A", "ts": 1.1, "_debug": {"timelineTiming": {"timeline": "main"}}},
                {"id": "line_2", "aid": "b", "ts": 1.2, "_debug": {"timelineTiming": {"timeline": "main"}}},
                {"id": "line_3", "ts": 1.2, "_debug": {"timelineTiming": {"timeline": "other"}}},
            ],
        }
        warning = build_duplicate_timestamp_warning(payload, _seconds)
        self.assertEqual(warning["code"], "duplicateTimestamps")
        self.assertEqual(warning["lineIds"], ["line_1", "line_2"])
        self.assertEqual(warning["groups"][0]["timeline"], "main")

    def test_timestamp_warning_attachments_replace_only_owned_codes(self):
        payload = {
            "lines": [{"id": "line_1", "ts": 2.0}, {"id": "line_2", "ts": 1.0}],
            "warnings": [
                {"code": "other"},
                {"code": "duplicateTimestamps"},
                {"code": "timelineTimestampRegression"},
            ],
        }
        attach_duplicate_timestamp_warning(payload, _seconds)
        attach_timeline_timestamp_regression_warning(payload, _seconds)
        self.assertEqual(
            [warning["code"] for warning in payload["warnings"]],
            ["other", "timelineTimestampRegression"],
        )
        regression = build_timeline_timestamp_regression_warning(payload, _seconds)
        self.assertEqual(regression["lineIds"], ["line_1", "line_2"])
        self.assertEqual(regression["regressions"][0]["prevTimestamp"], "2s")

    def test_timeline_action_evidence_attaches_payload_and_matching_line_rows(self):
        payload = {"lines": [{"id": "line_1"}, {"id": "line_2"}]}

        def build_debug(key, original, current):
            self.assertEqual((key, original, current), ("dlg_test", ["line_2", "line_1"], ["line_1", "line_2"]))
            return {
                "status": "conflict",
                "lineActions": [{"lineId": "line_1", "actions": [{"kind": "camera"}]}],
            }

        attach_timeline_action_evidence(
            payload,
            "dlg_test",
            ["line_2", "line_1"],
            ["line_1", "line_2"],
            build_debug,
        )
        self.assertEqual(payload["_debug"]["timelineActions"]["status"], "conflict")
        self.assertEqual(
            payload["lines"][0]["_debug"]["timelineActions"]["actions"],
            [{"kind": "camera"}],
        )
        self.assertNotIn("_debug", payload["lines"][1])


if __name__ == "__main__":
    unittest.main()
