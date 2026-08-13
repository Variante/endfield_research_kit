from __future__ import annotations

import unittest


from scripts.story_builder import source_story_order_cross_reference as cross_reference


class SourceStoryOrderCrossReferenceTests(unittest.TestCase):
    def test_module_is_a_small_library_not_a_second_command_surface(self) -> None:
        self.assertFalse(hasattr(cross_reference, "main"))
        self.assertEqual(
            cross_reference.__all__,
            ["SCHEMA", "build_report", "render_markdown"],
        )

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
