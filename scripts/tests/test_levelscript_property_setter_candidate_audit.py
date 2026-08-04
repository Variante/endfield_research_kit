from __future__ import annotations

import unittest

from scripts.story_recovery.build_levelscript_property_setter_candidate_audit import (
    aggregate_candidates,
    score_candidate,
)


class LevelScriptPropertySetterCandidateAuditTests(unittest.TestCase):
    def test_serialized_tail_story_cooccurrence_is_not_an_action_candidate(self) -> None:
        score, reasons, kind = score_candidate(
            record={
                "actionMap": "outside",
                "texts": ["isFinished"],
                "storyRefs": ["dlg_example_1"],
            },
            key="isFinished",
            relation="same-record-as-story",
            expected=[True],
        )

        self.assertEqual(kind, "serialized-tail-cooccurrence")
        self.assertIn(
            "serialized tail co-occurrence is not executable action evidence",
            reasons,
        )
        self.assertLess(score, 10)

    def test_serialized_tail_observation_is_excluded_from_opcode_candidates(self) -> None:
        rows = [{
            "mapId": "level_a",
            "scriptId": "1001",
            "key": "isFinished",
            "checkerMissions": ["mission_a"],
            "candidates": [{
                "score": 7,
                "candidateKind": "serialized-tail-cooccurrence",
                "relationToStory": "same-record-as-story",
                "record": {
                    "opcode": "0x0000/0x00",
                    "actionMap": "outside",
                },
            }],
        }]

        self.assertEqual(aggregate_candidates(rows), [])


if __name__ == "__main__":
    unittest.main()
