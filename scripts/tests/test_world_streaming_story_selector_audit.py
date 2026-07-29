from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT
    / "scripts"
    / "story_recovery"
    / "build_world_streaming_story_selector_audit.py"
)
SPEC = importlib.util.spec_from_file_location(
    "build_world_streaming_story_selector_audit",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WorldStreamingStorySelectorAuditTests(unittest.TestCase):
    def test_patterns_cover_names_paths_and_both_hash_orders(self) -> None:
        rows = [{
            "target": "cutscene_test",
            "path": "Assets/cutscene_test.prefab",
            "hashUnsigned": 0x0102030405060708,
            "hashHex": "0x0102030405060708",
        }]
        patterns = MODULE.build_patterns(rows)

        self.assertEqual(len(patterns), 6)
        self.assertIn(b"cutscene_test", patterns)
        self.assertIn("cutscene_test".encode("utf-16le"), patterns)
        self.assertIn(bytes.fromhex("0807060504030201"), patterns)
        self.assertIn(bytes.fromhex("0102030405060708"), patterns)

    def test_ordered_system_type_match_is_exactly_typed(self) -> None:
        row = {
            "script": {"fullName": "Beyond.Gameplay.BossBattlerData"},
            "type": "MonoBehaviour",
            "scalars": [],
            "pptrs": [],
        }
        matches = MODULE.ordered_system_matches(row)

        self.assertEqual(matches[0]["kind"], "scriptFullName")
        self.assertEqual(matches[0]["terms"], ["bossbattlerdata"])

    def test_distinctive_nested_field_is_matched_by_leaf(self) -> None:
        row = {
            "script": {"fullName": "Beyond.Gameplay.SomeHost"},
            "type": "MonoBehaviour",
            "scalars": [
                ["$.config.introPart.operaSegments[0].operaType", "i", 2],
            ],
            "pptrs": [],
        }
        matches = MODULE.ordered_system_matches(row)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["leaf"], "operatype")


if __name__ == "__main__":
    unittest.main()
