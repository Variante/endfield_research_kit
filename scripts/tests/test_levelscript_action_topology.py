from __future__ import annotations

import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.story_builder import level_bindings


class LevelScriptActionTopologyTests(unittest.TestCase):
    def records(self) -> list[dict]:
        return [
            {
                "start": 10,
                "localId": 1,
                "uid": "header01",
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
                "uid": "action10",
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
                "uid": "action20",
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
                "uid": "action30",
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
        serialized_action_count: int = 3,
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
                "actionHeader": {
                    "nextId": 10,
                    "priority": -2,
                    "triggerActiveDuring": 0,
                    "filterMode": 1,
                    "filterMask": 3,
                    "filterLevel": 2,
                },
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
            "headerByLocal": {1: records[0]},
            "equivalentRecordOffsets": {},
            "runtimeShadowedRecordOffsets": {},
            "runtimeDuplicateSignatureStatus": {},
            "runtimeShadowedHeaderRecordOffsets": {},
            "runtimeShadowedGetterRecordOffsets": {},
            "decodedByStart": decoded,
            "nextStarts": {10: 100, 100: 200, 200: 300, 300: 400},
        }
        action_map = {
            "status": "present",
            "listCounts": {
                "actionList": serialized_action_count,
                "getterList": 0,
                "headerList": 1,
            },
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

    def test_recovers_ordered_branch_sequence_without_record_adjacency(self) -> None:
        topology, diagnostic = self.run_topology(branch_targets=[20, 30])

        self.assertIsNone(diagnostic)
        self.assertEqual(topology["status"], "exact_complete_action_map")
        self.assertEqual(topology["eventRootCount"], 1)
        self.assertEqual(topology["actionNodeCount"], 3)
        self.assertEqual(topology["edgeCount"], 3)
        self.assertEqual(topology["schema"], "levelScriptNativeActionTopology.v4")
        self.assertEqual(topology["typedBranchNodeCount"], 0)
        self.assertEqual(topology["orderedSequenceNodeCount"], 1)
        self.assertEqual(topology["parallelFanoutNodeCount"], 0)
        self.assertEqual(topology["cycleCount"], 0)
        self.assertEqual(topology["orphanRootActionCount"], 0)
        self.assertEqual(topology["unmappedActionTypeCounts"], {})
        self.assertEqual(
            [row["actionName"] for row in topology["actions"]],
            ["Branch", "ManuallyAcceptClientGuideGroup", "ShowUIToast"],
        )
        self.assertFalse(topology["storyOrderEvidence"])
        self.assertEqual(
            topology["eventRootRuntimeMode"],
            "independently_invoked_indexed_event_slots",
        )
        self.assertEqual(topology["eventPriorityCounts"], {"-2": 1})
        self.assertEqual(topology["eventRoots"][0]["priority"], -2)
        self.assertEqual(topology["eventRoots"][0]["filterMask"], 3)
        self.assertEqual(topology["eventRoots"][0]["uid"], "header01")
        self.assertEqual(
            [row["uid"] for row in topology["actions"]],
            ["action10", "action20", "action30"],
        )

    def test_zero_branch_arm_is_an_exact_terminal_not_a_missing_target(self) -> None:
        topology, diagnostic = self.run_topology(branch_targets=[20, 0])

        self.assertIsNone(diagnostic)
        self.assertEqual(topology["status"], "exact_complete_action_map")
        self.assertEqual(topology["orderedSequenceNodeCount"], 1)
        self.assertEqual(topology["orphanRootActionCount"], 1)

    def test_split_is_classified_as_parallel_fanout(self) -> None:
        record = {
            "nextId": -1,
            "unionTag": 0x0495,
            "serializedMemberCount": 0x09,
        }
        successors = level_bindings._levelscript_native_action_successors(
            record,
            {"splitActionLocalIds": [20, 30]},
        )

        self.assertEqual(
            successors,
            [("Split.actions[0]", 20), ("Split.actions[1]", 30)],
        )
        self.assertEqual(
            level_bindings.LEVELSCRIPT_NATIVE_CONTROL_RUNTIME_MAPPINGS[
                (0x0495, 0x09)
            ]["kind"],
            "parallel_fanout",
        )

    def test_switch_int_larger_uses_shared_integer_switch_successors(self) -> None:
        record = {
            "nextId": -1,
            "unionTag": 0x04BE,
            "serializedMemberCount": 0x0C,
        }
        successors = level_bindings._levelscript_native_action_successors(
            record,
            {
                "switchIntLargerCaseActionLocalIds": [20, -1],
                "switchIntLargerCaseValues": [2, 9],
                "switchIntLargerDefaultActionLocalId": 30,
            },
        )

        self.assertEqual(
            successors,
            [
                ("SwitchIntLarger.case[0]=2", 20),
                ("SwitchIntLarger.default", 30),
            ],
        )
        self.assertEqual(
            level_bindings.LEVELSCRIPT_NATIVE_CONTROL_RUNTIME_MAPPINGS[
                (0x04BE, 0x0C)
            ]["kind"],
            "conditional_choice",
        )

    def test_missing_positive_target_is_an_exact_runtime_terminal(self) -> None:
        topology, diagnostic = self.run_topology(branch_targets=[20, 99])

        self.assertIsNone(diagnostic)
        self.assertEqual(topology["status"], "exact_complete_action_map")
        self.assertEqual(topology["runtimeTerminalTargetCount"], 1)
        self.assertEqual(
            topology["runtimeTerminalTargets"][0]["targetActionLocalId"],
            99,
        )
        self.assertEqual(
            topology["runtimeTerminalTargets"][0]["nativeMappingId"],
            level_bindings.LEVELSCRIPT_NATIVE_MISSING_ACTION_TERMINAL_MAPPING_ID,
        )

    def test_fails_closed_with_bounded_physical_count_diagnostic(self) -> None:
        topology, diagnostic = self.run_topology(
            branch_targets=[20, 30],
            serialized_action_count=4,
        )

        self.assertEqual(topology["status"], "unavailable_fail_closed")
        self.assertEqual(diagnostic["validator"], "levelScriptNativeActionTopology")
        self.assertEqual(diagnostic["gate"], "completeSerializedActionEventGraph")
        failure = next(
            row
            for row in diagnostic["actual"]["failures"]
            if row["check"] == "physicalActionRecordCount"
        )
        self.assertEqual(failure["expected"], 4)
        self.assertEqual(failure["actual"], 3)

    def test_runtime_action_slot_uses_final_serialized_duplicate(self) -> None:
        first = {
            "start": 100,
            "localId": 14,
            "unionTag": 0x00FF,
            "serializedMemberCount": 0x0B,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        final = {**first, "start": 200}
        membership = {100: "actionList#1", 200: "actionList#2"}

        def decode(_data, record, **_kwargs):
            return {
                "trueActionLocalId": 4 if record["start"] == 200 else 0,
                "falseActionLocalId": 0 if record["start"] == 200 else 15,
            }

        with patch.object(
            level_bindings,
            "decode_levelscript_record_payload",
            side_effect=decode,
        ):
            context = level_bindings._prepare_levelscript_native_control_context(
                b"fixture",
                [final, first],
                membership,
            )

        self.assertIs(context["actionByLocal"][14], final)
        self.assertEqual(context["runtimeShadowedRecordOffsets"][14], [100])
        self.assertEqual(
            context["runtimeDuplicateSignatureStatus"][14],
            "different_payload",
        )
        self.assertEqual(
            context["runtimeActionSlotMappingId"],
            level_bindings.LEVELSCRIPT_NATIVE_ACTION_SLOT_MAPPING_ID,
        )

    def test_runtime_action_slot_selection_tracks_serialized_order(self) -> None:
        records = [
            {
                "start": start,
                "localId": 7,
                "unionTag": tag,
                "serializedMemberCount": 0x09,
                "nextId": -1,
                "strings": [],
                "plainStrings": [],
            }
            for start, tag in ((300, 0x0303), (100, 0x048D))
        ]
        membership = {100: "actionList#1", 300: "actionList#2"}
        with patch.object(
            level_bindings,
            "decode_levelscript_record_payload",
            return_value={},
        ):
            context = level_bindings._prepare_levelscript_native_control_context(
                b"fixture",
                records,
                membership,
            )

        self.assertEqual(context["actionByLocal"][7]["start"], 300)
        self.assertEqual(context["runtimeShadowedRecordOffsets"][7], [100])

    def test_runtime_header_and_getter_slots_share_last_serialized_rule(self) -> None:
        records = [
            {
                "start": start,
                "localId": local_id,
                "unionTag": tag,
                "serializedMemberCount": 0,
                "nextId": -1,
                "strings": [],
                "plainStrings": [],
            }
            for start, local_id, tag in (
                (10, 4, 0x12BA),
                (20, 4, 0x12BA),
                (30, 8, 0x0001),
                (40, 8, 0x0002),
            )
        ]
        membership = {
            10: "headerList#1",
            20: "headerList#2",
            30: "getterList#1",
            40: "getterList#2",
        }
        with patch.object(
            level_bindings,
            "decode_levelscript_record_payload",
            return_value={},
        ):
            context = level_bindings._prepare_levelscript_native_control_context(
                b"fixture",
                records,
                membership,
            )

        self.assertEqual(context["headerByLocal"][4]["start"], 20)
        self.assertEqual(context["getterByLocal"][8]["start"], 40)
        self.assertEqual(context["runtimeShadowedHeaderRecordOffsets"][4], [10])
        self.assertEqual(context["runtimeShadowedGetterRecordOffsets"][8], [30])
        self.assertEqual(
            context["runtimeHeaderSlotMappingId"],
            level_bindings.LEVELSCRIPT_NATIVE_INDEXED_SLOT_MAPPING_ID,
        )
        self.assertEqual(
            context["runtimeGetterSlotMappingId"],
            level_bindings.LEVELSCRIPT_NATIVE_INDEXED_SLOT_MAPPING_ID,
        )

    def test_header_action_index_exposes_active_slot_and_reachable_graph(self) -> None:
        topology = {
            "status": "exact_complete_action_map_with_runtime_shadowing",
            "eventRoots": [{
                "localId": 4,
                "recordOffsetHex": "0x20",
                "opcode": "0x12ba/0x00",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "nextActionLocalId": 7,
                "eventDetail": {
                    "type": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "triggerSlotIdFilter": 80007,
                },
                "runtimeShadowedRecordOffsets": [16],
            }],
            "actions": [
                {"localId": 7, "recordOffsetHex": "0x30", "actionName": "Branch"},
                {
                    "localId": 8,
                    "recordOffsetHex": "0x40",
                    "actionName": "StartDialogAction",
                    "recordClass": "play_dialog",
                    "texts": ["dlg_general"],
                },
            ],
            "edges": [
                {
                    "sourceKind": "event",
                    "sourceLocalId": 4,
                    "targetActionLocalId": 7,
                    "relation": "ActionHeader.nextId",
                },
                {
                    "sourceKind": "action",
                    "sourceLocalId": 7,
                    "targetActionLocalId": 8,
                    "relation": "Branch.actions[0]",
                },
            ],
        }
        trigger_context = {
            "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
            "selectorSlotIds": [80007],
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "level_general" / "70001.json"
            source.parent.mkdir()
            source.write_bytes(b"fixture")
            with (
                patch.object(
                    level_bindings,
                    "decode_levelscript_native_action_topology",
                    return_value=(topology, None),
                ),
                patch.object(
                    level_bindings,
                    "decode_levelscript_binary_summary",
                    return_value={"status": "decoded"},
                ),
                patch.object(
                    level_bindings,
                    "classify_local_trigger_volume_context",
                    return_value=trigger_context,
                ),
            ):
                index = level_bindings.build_levelscript_header_action_index(
                    ["level_general"],
                    level_script_root=root,
                )

        self.assertEqual("validated", index["validation"]["status"])
        self.assertEqual(
            level_bindings.LEVELSCRIPT_NATIVE_HEADER_SLOT_MAPPING_ID,
            index["runtimeSlotMappingId"],
        )
        row = index["rows"][0]
        self.assertEqual("active-final-serialized-slot", row["runtimeSlotStatus"])
        self.assertEqual(index["runtimeSlotMappingId"], row["runtimeSlotMappingId"])
        self.assertEqual("action-list", row["targetStatus"])
        self.assertEqual([7, 8], [item["localId"] for item in row["reachableActions"]])
        self.assertEqual("Branch.actions[0]", row["reachableActionEdges"][0]["relation"])
        self.assertEqual(trigger_context, row["localTriggerVolumeContext"])

    def test_header_action_index_fails_closed_on_incomplete_topology(self) -> None:
        diagnostic = {
            "validator": "levelScriptNativeActionTopology",
            "gate": "completeSerializedActionEventGraph",
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "level_general" / "1.json"
            source.parent.mkdir()
            source.write_bytes(b"fixture")
            with patch.object(
                level_bindings,
                "decode_levelscript_native_action_topology",
                return_value=(
                    {"status": "unavailable_fail_closed"},
                    diagnostic,
                ),
            ):
                index = level_bindings.build_levelscript_header_action_index(
                    ["level_general"],
                    level_script_root=root,
                )

        self.assertEqual("failed", index["validation"]["status"])
        self.assertEqual([], index["rows"])
        failure = index["validation"]["failures"][0]
        self.assertEqual("completeSerializedActionEventGraph", failure["gate"])
        self.assertEqual(diagnostic, failure["diagnostic"])

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

    def test_accepts_file_with_no_serialized_action_map(self) -> None:
        action_map = {"status": "absent", "listCounts": {}}
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
                    b"no-map-fixture"
                )
            )

        self.assertIsNone(diagnostic)
        self.assertEqual(topology["status"], "exact_no_action_map")
        self.assertTrue(topology["actionControlFlowEvidence"])


if __name__ == "__main__":
    unittest.main()
