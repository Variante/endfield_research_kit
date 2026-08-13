import unittest
from pathlib import Path

from scripts.story_recovery.ocr import proposal


class OcrProposalTests(unittest.TestCase):
    def test_proposal_uses_only_observed_sequence_and_deduplicates(self):
        payload, rows = proposal.build_proposed_story_order(
            video_summaries=[
                {
                    "video": "fixture.mp4",
                    "observedSequences": {
                        "e1m1": [
                            {"key": "dlg_e1m1_1", "actualMission": "e1m1"},
                            {"key": "dlg_e1m1_1", "actualMission": "e1m1"},
                            {"key": "dlg_e1m1_2", "actualMission": "e1m1"},
                        ]
                    },
                }
            ],
            min_sequence_keys=2,
        )
        self.assertEqual(
            payload["missions"]["e1m1"]["order"],
            ["dlg_e1m1_1", "dlg_e1m1_2"],
        )
        self.assertTrue(rows[0]["included"])

    def test_distill_ignores_invalid_and_empty_missions(self):
        distilled = proposal.distill(
            {
                "missions": {
                    "e1m1": {"order": ["dlg_e1m1_1", ""]},
                    "e1m2": {"order": []},
                    "e1m3": "invalid",
                }
            },
            source_path=Path("fixture.json"),
        )
        self.assertEqual(distilled["missions"], {"e1m1": {"order": ["dlg_e1m1_1"]}})


if __name__ == "__main__":
    unittest.main()
