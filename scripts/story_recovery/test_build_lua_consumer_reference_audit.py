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

    def test_binary_discovered_handle_method_is_runtime_dispatch_not_authored_reference(self):
        text = """
local queueItemType = handle.data.queueItemType
if queueItemType == Const.CinematicQueueItemTypeEnum.Dialog then
    GameAction.DoPlayDialogByHandle(handle)
end
"""
        rows = audit.scan_game_action_calls(
            text,
            rel="LuaSystem/CinematicSystem.lua",
            story_keys=set(),
            cinematic_handle_dispatchers={"DoPlayDialogByHandle"},
        )

        self.assertEqual("runtime_queue_dispatcher", rows[0]["playbackRole"])
        self.assertEqual("runtime_handle_payload", rows[0]["literalResolution"])
        self.assertEqual(
            "runtime_payload_not_static_story_id",
            rows[0]["registryStatus"],
        )

    def test_singleton_original_table_field_is_resolved_without_table_name_rules(self):
        text = """
local ok, carrierRow = Tables.fixtureCarrierTable:TryGetValue(configId)
local storyId = carrierRow.storyField
GameAction.StartDialog(storyId)
"""
        rows = audit.scan_game_action_calls(
            text,
            rel="fixture.lua",
            story_keys={"dlg_fixture_general_1"},
            table_payloads={
                "fixturecarriertable": {
                    "table": "FixtureCarrierTable",
                    "sourcePath": "fixture/FixtureCarrierTable.json",
                    "sourceSha256": "a" * 64,
                    "rows": {
                        "carrier_1": {
                            "storyField": "dlg_fixture_general_1",
                            "missionId": "fixture_mission",
                        },
                    },
                },
            },
        )

        self.assertEqual("table_field_singleton", rows[0]["literalResolution"])
        self.assertEqual("exact_registry_match", rows[0]["registryStatus"])
        self.assertEqual("dlg_fixture_general_1", rows[0]["canonicalStoryKey"])
        resolution = rows[0]["tableFieldResolution"]
        self.assertEqual("FixtureCarrierTable", resolution["table"])
        self.assertEqual("storyField", resolution["field"])
        self.assertEqual(
            "fixture_mission",
            resolution["candidateRows"][0]["rowFields"]["missionId"],
        )

    def test_multirow_table_field_remains_candidates_without_lookup_key_proof(self):
        text = """
local carrierRow = Tables.fixtureCarrierTable:GetValue(configId)
GameAction.StartDialog(carrierRow.storyField)
"""
        rows = audit.scan_game_action_calls(
            text,
            rel="fixture.lua",
            story_keys={"dlg_fixture_1", "dlg_fixture_2"},
            table_payloads={
                "fixturecarriertable": {
                    "table": "FixtureCarrierTable",
                    "sourcePath": "fixture/FixtureCarrierTable.json",
                    "sourceSha256": "b" * 64,
                    "rows": {
                        "one": {"storyField": "dlg_fixture_1"},
                        "two": {"storyField": "dlg_fixture_2"},
                    },
                },
            },
        )

        self.assertEqual("table_field_candidates", rows[0]["literalResolution"])
        self.assertEqual("not_story_shaped", rows[0]["registryStatus"])
        self.assertIsNone(rows[0]["canonicalStoryKey"])
        self.assertEqual(
            ["dlg_fixture_1", "dlg_fixture_2"],
            [
                row["canonicalStoryKey"]
                for row in rows[0]["tableFieldResolution"]["candidateRows"]
            ],
        )


if __name__ == "__main__":
    unittest.main()
