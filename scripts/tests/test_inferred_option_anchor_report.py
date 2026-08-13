from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import option_anchor_reports


class InferredOptionAnchorReportTests(unittest.TestCase):
    def fixture(self) -> dict:
        return {
            "key": "dlg_testm1_1",
            "kind": "dlg",
            "mission": "testm1",
            "scene": 1,
            "lines": [{"id": "line_1"}, {"id": "line_2"}],
            "optionGroups": [{"g": "group_1"}],
            "warnings": [{
                "code": "inferredOptionLayout",
                "reason": "fixture fallback",
                "groupDetails": [{
                    "group": "group_1",
                    "status": "fallbackAfter",
                    "after": "line_1",
                    "inferredAnchorMode": "lineNumberGap",
                    "optionIds": ["option_1", "option_2"],
                }, {
                    "group": "group_2",
                    "status": "known",
                }],
            }],
        }

    def test_in_memory_rows_match_legacy_directory_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            conv_dir = root / "conv"
            legacy_reports = root / "legacy"
            memory_reports = root / "memory"
            conv_dir.mkdir()
            payload = self.fixture()
            (conv_dir / "dlg_testm1_1.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            (conv_dir / "radio_testm1_1.json").write_text(
                json.dumps({"kind": "radio"}),
                encoding="utf-8",
            )

            legacy = option_anchor_reports.write_inferred_option_anchors_report(
                legacy_reports,
                "CN",
                conv_dir,
            )
            row = option_anchor_reports.inferred_option_anchor_row(payload, "fallback")
            self.assertIsNotNone(row)
            with patch.object(
                option_anchor_reports,
                "read_json",
                side_effect=AssertionError("in-memory report must not reread conversations"),
            ):
                memory = option_anchor_reports.write_inferred_option_anchors_report(
                    memory_reports,
                    "CN",
                    conv_dir,
                    rows=[row],
                )

            self.assertEqual(legacy["summary"], memory["summary"])
            self.assertEqual(
                legacy["json"].read_text(encoding="utf-8"),
                memory["json"].read_text(encoding="utf-8"),
            )
            self.assertEqual(
                legacy["markdown"].read_text(encoding="utf-8"),
                memory["markdown"].read_text(encoding="utf-8"),
            )

    def test_non_inferred_rewrite_removes_current_row(self) -> None:
        payload = self.fixture()
        self.assertIsNotNone(
            option_anchor_reports.inferred_option_anchor_row(payload, "dlg_testm1_1")
        )
        payload["warnings"] = []
        self.assertIsNone(
            option_anchor_reports.inferred_option_anchor_row(payload, "dlg_testm1_1")
        )


if __name__ == "__main__":
    unittest.main()
