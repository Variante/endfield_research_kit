from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.timeline_action_evidence import (
    action_evidence_availability,
    iter_mono_dirs,
)


class TimelineActionEvidencePathTests(unittest.TestCase):
    def test_exact_monobehaviour_root_does_not_recurse_again(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "MonoBehaviour"
            nested = root / "nested" / "MonoBehaviour"
            nested.mkdir(parents=True)

            self.assertEqual([root], iter_mono_dirs([root]))

    def test_availability_reports_first_missing_gate(self) -> None:
        self.assertEqual(
            {
                "status": "unavailable",
                "reason": "timeline_action_carriers_missing",
            },
            action_evidence_availability(
                {
                    "monoDirCount": 2,
                    "candidateMonoFileCount": 0,
                    "managedReferenceCount": 0,
                    "mainFlowCount": 0,
                }
            ),
        )

    def test_availability_accepts_decoded_flows(self) -> None:
        self.assertEqual(
            {"status": "available", "reason": "decoded_dialog_main_flows"},
            action_evidence_availability(
                {
                    "monoDirCount": 2,
                    "candidateMonoFileCount": 3,
                    "managedReferenceCount": 12,
                    "mainFlowCount": 4,
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
