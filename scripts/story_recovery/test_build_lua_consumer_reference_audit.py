from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_lua_consumer_reference_audit as audit  # noqa: E402


class LuaConsumerReferenceAuditTests(unittest.TestCase):
    def test_story_playback_literals_are_case_sensitive_and_table_routes_stay_unresolved(self):
        text = """
local EXACT = "cutscene_e1m10_1"
local CASE_MISMATCH = "Cutscene_e0m0_1"
GameAction.PlayCutscene(EXACT, callback)
GameAction.PlayCutsceneAndGetHandle(CASE_MISMATCH, callback)
local row = Tables.skipChapterTable:TryGetValue(configId)
GameAction.StartDialog(row.bindDlgId)
"""
        rows = audit.scan_game_action_calls(
            text,
            rel="fixture.lua",
            story_keys={"cutscene_e1m10_1", "cutscene_e0m0_1", "dlg_e5m0d5_1"},
        )

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["literalResolution"], "module_constant")
        self.assertEqual(rows[0]["registryStatus"], "exact_registry_match")
        self.assertEqual(
            rows[1]["registryStatus"],
            "case_mismatch_registry_match",
        )
        self.assertEqual(rows[1]["canonicalStoryKey"], "cutscene_e0m0_1")
        self.assertEqual(rows[2]["literalResolution"], "unresolved_expression")
        self.assertIn("skipChapterTable", rows[2]["nearbyTables"])

    def test_first_argument_parser_respects_nested_calls_and_strings(self):
        text = 'GameAction.StartDialog(resolve("a,b", value), callback)'
        match = audit.GAME_ACTION_CALL_RE.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(
            audit.first_lua_argument(text, match.end() - 1),
            'resolve("a,b", value)',
        )


if __name__ == "__main__":
    unittest.main()
