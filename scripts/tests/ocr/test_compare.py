import unittest
from pathlib import Path

from scripts.story_recovery.ocr import compare


class OcrComparisonTests(unittest.TestCase):
    def test_disagreement_reports_key_and_order_differences(self):
        report = compare.build_report(
            {
                "missions": {
                    "e1m1": {
                        "locked": True,
                        "order": ["dlg_a", "dlg_b", "dlg_c"],
                    }
                }
            },
            {
                "missions": {
                    "e1m1": {"order": ["dlg_b", "dlg_a", "dlg_d"]},
                }
            },
            override_path=Path("override.json"),
            ocr_path=Path("ocr.json"),
        )
        row = report["missions"][0]
        self.assertEqual(row["status"], "keys-and-order-disagree")
        self.assertEqual(row["overrideOnlyKeys"], ["dlg_c"])
        self.assertEqual(row["ocrOnlyKeys"], ["dlg_d"])
        self.assertEqual(row["inversionCount"], 1)
        self.assertEqual(report["summary"]["lockedDisagreementMissions"], 1)


if __name__ == "__main__":
    unittest.main()
