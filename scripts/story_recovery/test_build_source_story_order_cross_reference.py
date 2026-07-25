from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_source_story_order_cross_reference as cross_reference  # noqa: E402


class SourceStoryOrderCrossReferenceTests(unittest.TestCase):
    def test_cross_references_never_add_non_strict_edges(self) -> None:
        partial = {
            "_schema": "fixture",
            "missions": [{
                "mission": "m1",
                "directEdges": [
                    {"from": "a", "to": "b", "kind": "questPrev", "tier": "strong"},
                    {"from": "b", "to": "c", "kind": "questSequence", "tier": "supported"},
                ],
            }],
        }
        override = {"missions": {"m1": {"order": ["a", "b", "c"]}}}
        ocr = {"missions": {"m1": {"order": ["b", "a", "c"]}}}

        report = cross_reference.build_report(partial, override, ocr)

        self.assertEqual(report["summary"]["strictEdges"], 1)
        self.assertEqual(report["summary"]["override_agrees"], 1)
        self.assertEqual(report["summary"]["ocr_disagrees"], 1)
        self.assertEqual(report["summary"]["crossReferenceConflicts"], 1)
        self.assertEqual(len(report["missions"][0]["edges"]), 1)

    def test_missing_keys_are_uncovered_not_disagreements(self) -> None:
        partial = {
            "missions": [{
                "mission": "m1",
                "directEdges": [
                    {"from": "a", "to": "b", "kind": "questPrev", "tier": "strong"},
                ],
            }],
        }

        report = cross_reference.build_report(
            partial,
            {"missions": {"m1": {"order": ["a"]}}},
            {"missions": {}},
        )

        edge = report["missions"][0]["edges"][0]
        self.assertEqual(edge["override"]["status"], "uncovered")
        self.assertEqual(edge["override"]["missing"], ["b"])
        self.assertEqual(edge["ocr"]["status"], "uncovered")


if __name__ == "__main__":
    unittest.main()
