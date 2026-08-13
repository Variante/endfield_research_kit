from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import scene_order_gap_shared


class SceneOrderGapReportTests(unittest.TestCase):
    def test_writer_publishes_owned_json_and_markdown(self) -> None:
        row = {
            "key": "dlg_testm1_1",
            "mission": "testm1",
            "path": "conv/dlg_testm1_1.json",
            "lineCount": 2,
            "optionGroupCount": 1,
            "lineOrderStatus": "missing",
            "lineOrderReasonCode": "missingBlock",
            "lineOrderPatternCode": "missingBlockNoSafeFallback",
            "lineOrderPattern": {},
            "inferredOptionLayout": True,
            "optionLayoutReason": "fallback",
            "optionPositionPatternCode": "unanchoredAllGroups",
            "optionPositionPattern": {},
            "inferredOptionResponse": False,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            result = scene_order_gap_shared.write_scene_order_gap_reports(
                reports_dir,
                reports_dir,
                "CN",
                reports_dir / "conv",
                rows=[row],
            )

            payload = json.loads(result["json"].read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["totalFlaggedScenes"], 1)
            self.assertEqual(payload["scenes"], [row])
            self.assertIn("dlg_testm1_1", result["markdown"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
