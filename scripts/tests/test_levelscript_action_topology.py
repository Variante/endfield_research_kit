from __future__ import annotations

import unittest
from contextlib import ExitStack
from unittest.mock import patch

from scripts.story_builder import level_bindings


class LevelScriptActionTopologyTests(unittest.TestCase):
    def records(self) -> list[dict]:
        return [
            {
                "start": 10,
                "localId": 1,
                "code": 0x12BA,
                "kind": 0,
                "unionTag": 0x00BA,
                "serializedMemberCount": 0x12,
                "nextId": 0,
                "strings": [],
                "plainStrings": [],
            },
            {
                "start": 100,
                "localId": 10,
                "code": 0x002D,
                "kind": 0x09,
                "unionTag": 0x002D,
                "serializedMemberCount": 0x09,
                "nextId": -1,
                "strings": [],
                "plainStrings": [],
            },
            {
                "start": 200,
                "localId": 20,
                "code": 0x0303,
                "kind": 0x09,
                "unionTag": 0x0303,
                "serializedMemberCount": 0x09,
                "nextId": -1,
                "strings": [{"text": "guide_example_a"}],
                "plainStrings": [],
            },
            {
                "start": 300,
                "localId": 30,
                "code": 0x048D,
                "kind": 0x0A,
                "unionTag": 0x048D,
                "serializedMemberCount": 0x0A,
                "nextId": -1,
                "strings": [{"text": "toast_example"}],
                "plainStrings": [],
            },
        ]

    def run_topology(
        self,
        *,
        branch_targets: list[int],
    ) -> tuple[dict, dict | None]:
        records = self.records()
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 root",
            300: "actionList#3 root",
        }
        decoded = {
            10: {
                "actionHeader": {"nextId": 10},
                "nativeEventDetail": {
                    "type": "ScriptEvent_OnCustomEvent",
                    "eventKey": "#example",
                },
            },
            100: {"branchSequenceActionLocalIds": branch_targets},
            200: {"guideId": "guide_example_a"},
            300: {},
        }
        context = {
            "ordered": records,
            "actionBuckets": {
                10: [records[1]],
                20: [records[2]],
                30: [records[3]],
            },
            "actionByLocal": {
                10: records[1],
                20: records[2],
                30: records[3],
            },
            "getterByLocal": {},
            "equivalentRecordOffsets": {},
            "decodedByStart": decoded,
            "nextStarts": {10: 100, 100: 200, 200: 300, 300: 400},
        }
        action_map = {
            "status": "present",
            "listCounts": {"actionList": 3, "getterList": 0, "headerList": 1},
        }
        with ExitStack() as stack:
            stack.enter_context(patch.object(
                level_bindings,
                "_extract_levelscript_tagged_ascii_strings",
                return_value=[],
            ))
            stack.enter_context(patch.object(
                level_bindings,
                "_extract_levelscript_plain_ascii_strings",
                return_value=[],
            ))
            stack.enter_context(patch.object(
                level_bindings,
                "extract_levelscript_uid_records",
                return_value=records,
            ))
            stack.enter_context(patch.object(
                level_bindings,
                "levelscript_action_map_membership",
                return_value=(action_map, membership),
            ))
            stack.enter_context(patch.object(
                level_bindings,
                "_prepare_levelscript_native_control_context",
                return_value=context,
            ))
            stack.enter_context(patch.object(
                level_bindings,
                "levelscript_native_header_name",
                return_value="ScriptEvent_OnCustomEvent",
            ))
            return level_bindings.decode_levelscript_native_action_topology(
                b"fixture"
            )

    def test_recovers_typed_fanout_without_record_adjacency(self) -> None:
        topology, diagnostic = self.run_topology(branch_targets=[20, 30])

        self.assertIsNone(diagnostic)
        self.assertEqual(topology["status"], "exact_complete_action_map")
        self.assertEqual(topology["eventRootCount"], 1)
        self.assertEqual(topology["actionNodeCount"], 3)
        self.assertEqual(topology["edgeCount"], 3)
        self.assertEqual(topology["typedBranchNodeCount"], 1)
        self.assertEqual(topology["cycleCount"], 0)
        self.assertEqual(topology["orphanRootActionCount"], 0)
        self.assertEqual(topology["unmappedActionTypeCounts"], {})
        self.assertEqual(
            [row["actionName"] for row in topology["actions"]],
            ["Branch", "ManuallyAcceptClientGuideGroup", "ShowUIToast"],
        )
        self.assertFalse(topology["storyOrderEvidence"])

    def test_fails_closed_with_bounded_missing_target_diagnostic(self) -> None:
        topology, diagnostic = self.run_topology(branch_targets=[20, 99])

        self.assertEqual(topology["status"], "unavailable_fail_closed")
        self.assertEqual(
            diagnostic["validator"],
            "levelScriptNativeActionTopology",
        )
        self.assertEqual(
            diagnostic["gate"],
            "completeSerializedActionEventGraph",
        )
        failure = next(
            row
            for row in diagnostic["actual"]["failures"]
            if row["check"] == "allSerializedControlTargetsResolve"
        )
        self.assertEqual(failure["failureCount"], 1)
        self.assertEqual(
            failure["actual"][0]["targetActionLocalId"],
            99,
        )

    def test_accepts_exact_empty_action_map(self) -> None:
        action_map = {
            "status": "present",
            "listCounts": {
                "actionList": 0,
                "getterList": None,
                "headerList": None,
            },
        }
        with patch.object(
            level_bindings,
            "_extract_levelscript_tagged_ascii_strings",
            return_value=[],
        ), patch.object(
            level_bindings,
            "_extract_levelscript_plain_ascii_strings",
            return_value=[],
        ), patch.object(
            level_bindings,
            "extract_levelscript_uid_records",
            return_value=[],
        ), patch.object(
            level_bindings,
            "levelscript_action_map_membership",
            return_value=(action_map, {}),
        ):
            topology, diagnostic = (
                level_bindings.decode_levelscript_native_action_topology(
                    b"empty-map-fixture"
                )
            )

        self.assertIsNone(diagnostic)
        self.assertEqual(topology["status"], "exact_empty_action_map")
        self.assertEqual(topology["actionNodeCount"], 0)
        self.assertTrue(topology["actionControlFlowEvidence"])


if __name__ == "__main__":
    unittest.main()
