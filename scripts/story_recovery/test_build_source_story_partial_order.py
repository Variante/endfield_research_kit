from __future__ import annotations

import copy
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_source_story_partial_order as partial_order  # noqa: E402


def mp_string(value: str | None) -> bytes:
    if value is None:
        return struct.pack("<I", 0xFFFFFFFF)
    encoded = value.encode("utf-8")
    return struct.pack("<I", len(encoded)) + encoded


def spawner_wave_fixture() -> bytes:
    def group_entry(
        map_key: int,
        group_key: int,
        group_id: int,
        mode: int,
        target: str | None = None,
    ) -> bytes:
        return (
            struct.pack("<i", map_key)
            + b"\x0c"
            + struct.pack("<I", 0)
            + struct.pack("<fii", 0.0, 0, group_id)
            + mp_string(str(group_key))
            + struct.pack("<iii", 0, mode, 0)
            + mp_string(target)
            + b"\x00\x00"
            + struct.pack("<f", 1.0)
        )

    def entry(
        map_key: int,
        wave_id: int,
        mode: int,
        target: str | None,
        groups: list[bytes],
    ) -> bytes:
        return (
            struct.pack("<i", map_key)
            + b"\x0b"
            + struct.pack("<fI", 0.0, len(groups))
            + b"".join(groups)
            + b"\x00\x00\x00"
            + struct.pack("<f", 0.0)
            + struct.pack("<i", wave_id)
            + mp_string(str(map_key))
            + struct.pack("<ii", mode, 5)
            + mp_string(target)
        )

    return (
        b"\x05"
        + mp_string("sc_map_test_1004")
        + b"opaque-prefix"
        + struct.pack("<I", 2)
        + entry(4, 186, 2, "2", [group_entry(1, 401, 1, 0)])
        + entry(5, 193, 2, "4", [group_entry(1, 501, 2, 0)])
    )


def mission_payload(
    edges: list[dict] | None = None,
    *,
    branch_points: list[dict] | None = None,
    quest_edges: list[dict] | None = None,
    node_orders: dict[str, int] | None = None,
) -> dict:
    keys = {
        str(edge.get("from") or "")
        for edge in edges or []
    } | {
        str(edge.get("to") or "")
        for edge in edges or []
    }
    return {
        "flow": {
            "sceneGraph": {
                "nodes": [
                    {
                        "key": key,
                        "kind": "dlg",
                        "order": (node_orders or {}).get(key, 999),
                    }
                    for key in sorted(keys)
                    if key
                ],
                "edges": edges or [],
            }
        },
        "timelineRecovery": {
            "branchPoints": branch_points or [],
            "questEdges": quest_edges or [],
            # Deliberately contradictory: this field must never affect output.
            "sceneOrderInfo": {
                key: {"questOrder": 1000 - index, "orderSource": "numericFallback"}
                for index, key in enumerate(sorted(keys))
                if key
            },
        },
    }


class SourceStoryPartialOrderTests(unittest.TestCase):
    def test_exact_quest_succeed_lifecycle_orders_same_quest_story_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "MissionRuntimeAsset" / "m1.json"
            source.parent.mkdir(parents=True)
            source.write_text('{"missionId":"m1"}', encoding="utf-8")
            payload = mission_payload()
            payload["timelineRecovery"]["metadata"] = {
                "source": {"file": "MissionRuntimeAsset/m1.json"},
            }
            payload["flow"]["quests"] = [{
                "id": "m1_q#1",
                "storyConnections": [
                    {
                        "key": "dlg_m1_1",
                        "relation": "objective_condition",
                        "direction": "story_to_quest",
                        "phase": "progress",
                        "confidence": "direct",
                        "conditionType": "CheckTalkOptionFinish",
                    },
                    {
                        "key": "radio_m1_1",
                        "relation": "client_action_succeed",
                        "direction": "quest_to_story",
                        "phase": "succeed",
                        "confidence": "native_typed_direct",
                        "actionType": "PlayRadio",
                    },
                ],
            }]
            contract = {
                "schema": "questSucceedClientAction.v1",
                "validation": {"status": "validated", "failures": []},
                "succeedActionCalls": [{"questActionValue": 2}],
                "relatedOriginalFiles": [{
                    "kind": "original_game_binary",
                    "sourceFile": "GameAssembly.dll",
                    "sha256": "A" * 64,
                }],
            }
            with patch.object(partial_order, "ROOT", root):
                result = partial_order.build_mission_partial_order(
                    "m1",
                    {"dlg_m1_1": "dlg", "radio_m1_1": "radio"},
                    payload,
                    quest_succeed_lifecycle_contract=contract,
                )

        edge = result["directEdges"][0]
        self.assertEqual(
            (edge["from"], edge["to"], edge["kind"], edge["tier"]),
            ("dlg_m1_1", "radio_m1_1", "questSucceedLifecycle", "strong"),
        )
        self.assertEqual(edge["questIds"], ["m1_q#1"])
        self.assertEqual(len(edge["relatedOriginalFiles"]), 2)
        self.assertEqual(result["summary"]["questSucceedLifecycleEdgeCount"], 1)

    def test_quest_succeed_lifecycle_rejects_reverse_strong_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "m1.json"
            source.write_text("{}", encoding="utf-8")
            payload = mission_payload([{
                "from": "radio_m1_1",
                "to": "dlg_m1_1",
                "kind": "questPrev",
            }])
            payload["timelineRecovery"]["metadata"] = {
                "source": {"file": "m1.json"},
            }
            payload["flow"]["quests"] = [{
                "id": "m1_q#1",
                "storyConnections": [
                    {"key": "dlg_m1_1", "relation": "objective_condition",
                     "direction": "story_to_quest", "phase": "progress"},
                    {"key": "radio_m1_1", "relation": "client_action_succeed",
                     "direction": "quest_to_story", "phase": "succeed",
                     "confidence": "native_typed_direct"},
                ],
            }]
            with patch.object(partial_order, "ROOT", root):
                result = partial_order.build_mission_partial_order(
                    "m1",
                    {"dlg_m1_1": "dlg", "radio_m1_1": "radio"},
                    payload,
                    quest_succeed_lifecycle_contract={
                        "validation": {"status": "validated", "failures": []},
                    },
                )

        self.assertEqual(result["summary"]["questSucceedLifecycleEdgeCount"], 0)
        self.assertEqual(result["warnings"][0]["check"], "noReverseStrongOrderConflict")

    def test_quest_succeed_lifecycle_skips_non_applicable_mission_cleanly(self) -> None:
        payload = mission_payload()
        payload["flow"]["quests"] = [{
            "id": "m1_q#1",
            "storyConnections": [{
                "key": "dlg_m1_1",
                "relation": "objective_condition",
                "direction": "story_to_quest",
                "phase": "progress",
            }],
        }]

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_1": "dlg"},
            payload,
            quest_succeed_lifecycle_contract={
                "validation": {"status": "validation_failed", "failures": []},
            },
        )

        self.assertEqual(result["summary"]["questSucceedLifecycleEdgeCount"], 0)
        self.assertFalse(any(
            warning.get("validator") == "questSucceedLifecycle"
            for warning in result["warnings"]
            if isinstance(warning, dict)
        ))

    def test_typed_selector_alternatives_are_visible_without_order_edges(self) -> None:
        alternatives = [
            {"role": "first", "key": "dlg_a"},
            {"role": "repeat", "key": "dlg_b"},
        ]
        payload = mission_payload()
        payload["flow"]["missionStoryConnections"] = [
            {
                "missionId": "m1",
                "key": key,
                "selectorKind": "typed_table_story_selector",
                "selectorGroupId": "target_opaque",
                "selectorRole": role,
                "selectorAlternatives": alternatives,
                "graphEffect": "none",
                "sourceFiles": ["TypedTable.json"],
                "nativeMappingId": "mapping-v1",
                "orderBoundary": "no relative order",
            }
            for role, key in (("first", "dlg_a"), ("repeat", "dlg_b"))
        ]

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_a": "dlg", "dlg_b": "dlg"}, payload
        )

        self.assertEqual(result["directEdges"], [])
        self.assertEqual(result["summary"]["typedStorySelectorGroupCount"], 1)
        self.assertEqual(
            result["branches"]["typedStorySelectorGroups"][0]["alternatives"],
            alternatives,
        )

    @staticmethod
    def narrative_containment_flow(*, placement_status: str) -> dict:
        return {
            "sceneGraph": {"nodes": [], "edges": []},
            "unresolvedDialogTreeNarrativeActions": [{
                "key": "black_m1_1",
                "parentStoryKey": "dlg_m1_1",
                "relation": "dialog_tree_narrative_action_unscoped",
                "confidence": "native_exact_containment_unscoped",
                "dialogTreeNarrativeActions": [{
                    "textId": "black_m1_1_001",
                    "dialogKey": "dlg_m1_1",
                    "nativeMappingId":
                        "dialog-tree-narrative-mask-connection-native-v1",
                    "dialogTreeConnectionPlacementStatus": placement_status,
                    "reachableFromPrimeNode": True,
                    "embeddedAfterLineIds": ["dlg_m1_1_009"],
                    "embeddedBeforeLineIds": ["dlg_m1_1_010"],
                    "sourceFile": "TextAsset/dlg_m1_1.json",
                }],
            }],
        }

    def test_exact_dialog_tree_narrative_containment_is_visible_not_ordered(self) -> None:
        result = partial_order.build_mission_partial_order(
            "m1",
            {"black_m1_1": "black", "dlg_m1_1": "dlg"},
            {"flow": self.narrative_containment_flow(
                placement_status="exact_unique_adjacent_parent_trunks",
            )},
        )

        self.assertEqual(result["directEdges"], [])
        self.assertEqual(result["isolatedSceneKeys"], ["dlg_m1_1"])
        self.assertEqual(result["unknownSceneKeys"], ["dlg_m1_1"])
        self.assertEqual(result["containments"][0]["child"], "black_m1_1")
        self.assertEqual(
            result["containments"][0]["embeddedAfterLineIds"],
            ["dlg_m1_1_009"],
        )
        child = next(row for row in result["nodes"] if row["key"] == "black_m1_1")
        self.assertEqual(child["relationStatus"], "embedded")
        self.assertEqual(result["warnings"], [])

    def test_dialog_tree_narrative_containment_fails_closed_with_diagnostic(self) -> None:
        result = partial_order.build_mission_partial_order(
            "m1",
            {"black_m1_1": "black", "dlg_m1_1": "dlg"},
            {"flow": self.narrative_containment_flow(
                placement_status="not_exact_unique_adjacent_trunks",
            )},
        )

        self.assertEqual(result["containments"], [])
        self.assertEqual(
            result["isolatedSceneKeys"],
            ["black_m1_1", "dlg_m1_1"],
        )
        diagnostic = result["warnings"][0]
        self.assertEqual(diagnostic["validator"], "dialogTreeNarrativeContainment")
        self.assertEqual(diagnostic["storyKey"], "black_m1_1")
        self.assertEqual(diagnostic["sourcePaths"], ["TextAsset/dlg_m1_1.json"])
        self.assertEqual(diagnostic["actual"]["validOccurrenceCount"], 0)

    @staticmethod
    def open_ui_occurrence(*, placement_status: str) -> dict:
        return {
            "dialogKey": "dlg_m1_1",
            "nodeId": "7",
            "readingPopupId": "rp_text_m1_1",
            "paramData": {"id": "rp_text_m1_1"},
            "panelType": 17,
            "actionEnum": 57,
            "nativeMappingId":
                "dialog-tree-open-ui-reading-popup-connection-native-v1",
            "dialogTreeConnectionPlacementStatus": placement_status,
            "reachableFromPrimeNode": True,
            "embeddedAfterLineIds": ["dlg_m1_1_009"],
            "embeddedBeforeLineIds": ["dlg_m1_1_010"],
            "sourceFile": "TextAsset/dlg_m1_1.json",
            "sourceSha256": "A" * 64,
        }

    def test_exact_dialog_tree_open_ui_popup_containment_is_visible(self) -> None:
        result = partial_order.build_mission_partial_order(
            "m1",
            {"text_m1_1": "text", "dlg_m1_1": "dlg"},
            {"flow": {"sceneGraph": {"nodes": [], "edges": []}}},
            dialog_tree_open_ui_occurrences=[self.open_ui_occurrence(
                placement_status="exact_between_adjacent_parent_trunks",
            )],
            reading_popup_rows={"rp_text_m1_1": {
                "bgType": 1,
                "contentId": "text_m1_1",
                "iconType": 3,
                "id": "rp_text_m1_1",
                "overrideRadioId": "",
                "title": {"id": 0, "text": ""},
            }},
            reading_popup_source="Table/ReadingPopUpTable.json",
            reading_popup_sha256="B" * 64,
        )

        self.assertEqual(result["directEdges"], [])
        self.assertEqual(result["isolatedSceneKeys"], ["dlg_m1_1"])
        self.assertEqual(result["containments"][0]["child"], "text_m1_1")
        self.assertEqual(
            result["containments"][0]["readingPopupId"],
            "rp_text_m1_1",
        )
        child = next(row for row in result["nodes"] if row["key"] == "text_m1_1")
        self.assertEqual(child["relationStatus"], "embedded")
        self.assertEqual(result["warnings"], [])

    def test_dialog_tree_open_ui_popup_containment_fails_closed(self) -> None:
        occurrence = self.open_ui_occurrence(
            placement_status="not_exact_story_boundary",
        )
        result = partial_order.build_mission_partial_order(
            "m1",
            {"text_m1_1": "text", "dlg_m1_1": "dlg"},
            {"flow": {"sceneGraph": {"nodes": [], "edges": []}}},
            dialog_tree_open_ui_occurrences=[occurrence],
            reading_popup_rows={"rp_text_m1_1": {
                "bgType": 1,
                "contentId": "text_m1_1",
                "iconType": 3,
                "id": "rp_text_m1_1",
                "overrideRadioId": "",
                "title": {"id": 0, "text": ""},
            }},
            reading_popup_source="Table/ReadingPopUpTable.json",
            reading_popup_sha256="B" * 64,
        )

        self.assertEqual(result["containments"], [])
        diagnostic = result["warnings"][0]
        self.assertEqual(diagnostic["validator"], "dialogTreeOpenUIContainment")
        self.assertEqual(diagnostic["storyKey"], "text_m1_1")
        self.assertEqual(
            diagnostic["actual"]["placementStatus"],
            "not_exact_story_boundary",
        )

    def test_declared_variant_mission_evidence_is_merged_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir = Path(tmp)
            base_payload = {
                "mission": "e10m4",
                "flow": {
                    "sceneGraph": {"nodes": [{"key": "dlg_base"}], "edges": []},
                    "sceneGraphVariantMissions": ["e10m4d5", "wrong"],
                    "missionStoryConnections": [{"key": "dlg_base"}],
                    "quests": [{"id": "e10m4_q#1"}],
                },
                "timelineRecovery": {
                    "questEdges": [{"from": "base_a", "to": "base_b"}],
                    "scenePlacement": {"dlg_base": {"sceneKey": "dlg_base"}},
                },
            }
            variant_payload = {
                "mission": "e10m4d5",
                "flow": {
                    "missionStoryConnections": [{"key": "radio_variant"}],
                    "quests": [{"id": "e10m4d5_q#1"}],
                },
                "timelineRecovery": {
                    "questEdges": [{"from": "variant_a", "to": "variant_b"}],
                    "scenePlacement": {
                        "radio_variant": {"sceneKey": "radio_variant"},
                    },
                },
            }
            wrong_payload = {
                "mission": "another_mission",
                "flow": {
                    "missionStoryConnections": [{"key": "must_not_merge"}],
                },
            }
            (mission_dir / "e10m4.json").write_text(
                json.dumps(base_payload),
                encoding="utf-8",
            )
            (mission_dir / "e10m4d5.json").write_text(
                json.dumps(variant_payload),
                encoding="utf-8",
            )
            (mission_dir / "wrong.json").write_text(
                json.dumps(wrong_payload),
                encoding="utf-8",
            )

            merged = partial_order.load_mission_payload_with_variants(
                mission_dir,
                "e10m4",
            )

        self.assertEqual(
            [
                row["key"]
                for row in merged["flow"]["missionStoryConnections"]
            ],
            ["dlg_base", "radio_variant"],
        )
        self.assertEqual(
            [row["id"] for row in merged["flow"]["quests"]],
            ["e10m4_q#1", "e10m4d5_q#1"],
        )
        self.assertEqual(
            merged["flow"]["_sourceVariantMissionIds"],
            ["e10m4d5"],
        )
        self.assertEqual(
            set(merged["timelineRecovery"]["scenePlacement"]),
            {"dlg_base", "radio_variant"},
        )
        self.assertEqual(
            merged["flow"]["sceneGraph"],
            base_payload["flow"]["sceneGraph"],
        )

    def test_complete_cross_story_dialog_trunk_continuation_is_strong(
        self,
    ) -> None:
        payload = mission_payload([])
        payload["flow"]["missionStoryConnections"] = [{
            "key": "dlg_m1_2",
            "parentStoryKey": "dlg_m1_1",
            "relation": "dialog_tree_reachable_story_playback",
            "confidence": "native_derived_exact_parent_shell",
            "certainty": "authored_reachable",
            "nativeMappingId": "dialog-tree-reachable-story-playback-native-v1",
            "trunkIds": ["dlg_m1_2_001", "dlg_m1_2_002"],
            "sourceFiles": ["dialog_tree.json"],
            "dialogTreeStoryPlaybackCarriers": [{
                "storyKey": "dlg_m1_2",
                "carrierKind": "trunk",
                "carrierValue": "dlg_m1_2_001",
                "nodeId": "22",
                "parentTrunkId": "dlg_m1_1_002",
                "currentParentTrunkIds": [
                    "dlg_m1_1_001",
                    "dlg_m1_1_002",
                ],
                "reachableFromCurrentParentTrunk": True,
                "entryProof":
                    "exact_registered_dialog_tree_current_parent_anchor",
                "nodePath": ["21", "22"],
                "connectionPath": [{"sourceNodeId": "21", "targetNodeId": "22"}],
            }, {
                "storyKey": "dlg_m1_2",
                "carrierKind": "trunk",
                "carrierValue": "dlg_m1_2_002",
                "nodeId": "23",
                "parentTrunkId": "dlg_m1_1_002",
                "currentParentTrunkIds": [
                    "dlg_m1_1_001",
                    "dlg_m1_1_002",
                ],
                "reachableFromCurrentParentTrunk": True,
                "entryProof":
                    "exact_registered_dialog_tree_current_parent_anchor",
                "nodePath": ["21", "22", "23"],
                "connectionPath": [
                    {"sourceNodeId": "21", "targetNodeId": "22"},
                    {"sourceNodeId": "22", "targetNodeId": "23"},
                ],
            }],
        }]
        conversations = [
            ("conv/dlg_m1_1.json", {
                "key": "dlg_m1_1",
                "lines": [{"id": "dlg_m1_1_001"}, {"id": "dlg_m1_1_002"}],
            }),
            ("conv/dlg_m1_2.json", {
                "key": "dlg_m1_2",
                "lines": [{"id": "dlg_m1_2_001"}, {"id": "dlg_m1_2_002"}],
            }),
        ]

        row = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_1": "dlg", "dlg_m1_2": "dlg"},
            payload,
            conversations,
        )

        edge = next(
            edge
            for edge in row["directEdges"]
            if edge["kind"] == "dialogTreeCrossStoryTrunkContinuation"
        )
        self.assertEqual((edge["from"], edge["to"]), ("dlg_m1_1", "dlg_m1_2"))
        self.assertEqual(edge["tier"], "strong")

        incomplete = copy.deepcopy(payload)
        incomplete["flow"]["missionStoryConnections"][0][
            "dialogTreeStoryPlaybackCarriers"
        ][0]["currentParentTrunkIds"] = ["dlg_m1_1_002"]
        incomplete["flow"]["missionStoryConnections"][0][
            "dialogTreeStoryPlaybackCarriers"
        ][1]["currentParentTrunkIds"] = ["dlg_m1_1_002"]
        rejected = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_1": "dlg", "dlg_m1_2": "dlg"},
            incomplete,
            conversations,
        )
        self.assertFalse(any(
            edge["kind"] == "dialogTreeCrossStoryTrunkContinuation"
            for edge in rejected["directEdges"]
        ))

    def test_gm02m14_conditional_cross_story_branch_is_fail_closed(
        self,
    ) -> None:
        mission_payload_path = (
            partial_order.ROOT
            / "webui" / "data" / "lang" / "CN" / "mission"
            / "gm02m14.json"
        )
        conv_root = (
            partial_order.ROOT
            / "webui" / "data" / "lang" / "CN" / "conv"
        )
        payload = json.loads(mission_payload_path.read_text(encoding="utf-8"))
        conversations = [
            (
                f"conv/{story_key}.json",
                json.loads(
                    (conv_root / f"{story_key}.json").read_text(
                        encoding="utf-8"
                    )
                ),
            )
            for story_key in ("dlg_gm02m14_1", "dlg_gm02m14_3")
        ]
        candidates = {
            "dlg_gm02m14_1": "dlg",
            "dlg_gm02m14_3": "dlg",
        }

        row = partial_order.build_mission_partial_order(
            "gm02m14", candidates, payload, conversations
        )
        edge = next(
            edge for edge in row["directEdges"]
            if edge["kind"] == "dialogTreeCrossStoryConditionalBranch"
        )
        self.assertEqual(
            (edge["from"], edge["to"]),
            ("dlg_gm02m14_1", "dlg_gm02m14_3"),
        )
        self.assertEqual(edge["conditionTrueConnectionIndex"], 1)
        self.assertEqual(edge["conditionFalseConnectionIndex"], 0)
        self.assertEqual(edge["condition"]["key"], "canskip")
        self.assertTrue(edge["condition"]["value"])

        corrupted = copy.deepcopy(payload)
        connection = next(
            row for row in corrupted["flow"]["missionStoryConnections"]
            if row.get("key") == "dlg_gm02m14_3"
        )
        connection["dialogTreeStoryPlaybackCarriers"][0][
            "connectionPath"
        ][1]["index"] = 99
        rejected = partial_order.build_mission_partial_order(
            "gm02m14", candidates, corrupted, conversations
        )
        self.assertFalse(any(
            edge["kind"] == "dialogTreeCrossStoryConditionalBranch"
            for edge in rejected["directEdges"]
        ))
        diagnostic = next(
            warning for warning in rejected["warnings"]
            if isinstance(warning, dict)
            and warning.get("validator")
            == "dialogTreeCrossStoryConditionalBranch"
        )
        self.assertEqual(
            diagnostic["gate"],
            "exactSerializedBranchCarrierAndNativePolarity",
        )
        self.assertEqual(diagnostic["mission"], "gm02m14")
        self.assertEqual(
            diagnostic["actual"]["carrierConnectionIndexes"]
            ["dlg_gm02m14_3_001"],
            (10, 99),
        )

    def test_spawner_part_killed_target_recovers_wave_begin_order(self) -> None:
        candidates = {
            "radio_m1_wave4": "radio",
            "radio_m1_wave5": "radio",
        }
        flow = mission_payload([])["flow"]

        def connection(story_key: str, wave_key: str, local_id: int) -> dict:
            return {
                "key": story_key,
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "occurrences": [{
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "localId": local_id,
                    "actionName": "Play3DRadio",
                    "recordClass": "play_radio",
                    "allStoryKeysInRecord": [story_key],
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "LevelEvent_OnSpawnerWaveBegin",
                        "headerLocalId": local_id - 1,
                        "eventDetail": {
                            "type": "LevelEvent_OnSpawnerWaveBegin",
                            "spawnerFilterId": 1004,
                            "waveKeyFilter": wave_key,
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-wave-event",
                        },
                    }],
                }],
            }

        flow["unlinkedNativePlayback"] = [
            connection("radio_m1_wave4", "4", 40),
            connection("radio_m1_wave5", "5", 50),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / "map_test"
            config_dir.mkdir()
            (config_dir / "sc_map_test_1004.json").write_bytes(
                spawner_wave_fixture()
            )
            edges = partial_order._spawner_wave_part_killed_story_edges(
                flow,
                set(candidates),
                spawner_roots=[root],
            )

        self.assertEqual(len(edges), 1)
        self.assertEqual(
            (edges[0]["from"], edges[0]["to"]),
            ("radio_m1_wave4", "radio_m1_wave5"),
        )
        self.assertEqual(edges[0]["kind"], "spawnerWavePartKilled")
        self.assertEqual(edges[0]["tier"], "strong")
        self.assertEqual(edges[0]["targetWaveKey"], "4")
        self.assertEqual(edges[0]["waveKey"], "5")

    def test_spawner_group_and_wave_callbacks_cross_part_killed_gate(self) -> None:
        candidates = {
            "radio_m1_wave4",
            "radio_m1_group401",
            "radio_m1_wave5",
            "radio_m1_group501",
        }
        flow = mission_payload([])["flow"]

        def connection(
            story_key: str,
            selector_key: str,
            event_type: str,
            local_id: int,
        ) -> dict:
            selector_field = (
                "waveKeyFilter"
                if event_type == "LevelEvent_OnSpawnerWaveBegin"
                else "groupKeyFilter"
            )
            return {
                "key": story_key,
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "occurrences": [{
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "localId": local_id,
                    "actionName": "Play3DRadio",
                    "recordClass": "play_radio",
                    "allStoryKeysInRecord": [story_key],
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": event_type,
                        "headerLocalId": local_id - 1,
                        "eventDetail": {
                            "type": event_type,
                            "spawnerFilterId": 1004,
                            selector_field: selector_key,
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-event",
                        },
                    }],
                }],
            }

        flow["unlinkedNativePlayback"] = [
            connection(
                "radio_m1_wave4",
                "4",
                "LevelEvent_OnSpawnerWaveBegin",
                40,
            ),
            connection(
                "radio_m1_group401",
                "401",
                "LevelEvent_OnSpawnerGroupBegin",
                41,
            ),
            connection(
                "radio_m1_wave5",
                "5",
                "LevelEvent_OnSpawnerWaveBegin",
                50,
            ),
            connection(
                "radio_m1_group501",
                "501",
                "LevelEvent_OnSpawnerGroupBegin",
                51,
            ),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / "map_test"
            config_dir.mkdir()
            (config_dir / "sc_map_test_1004.json").write_bytes(
                spawner_wave_fixture()
            )
            edges = (
                partial_order._spawner_wave_group_part_killed_story_edges(
                    flow,
                    candidates,
                    spawner_roots=[root],
                )
            )

        self.assertEqual(
            {(edge["from"], edge["to"]) for edge in edges},
            {
                ("radio_m1_wave4", "radio_m1_group501"),
                ("radio_m1_group401", "radio_m1_wave5"),
                ("radio_m1_group401", "radio_m1_group501"),
            },
        )
        self.assertTrue(
            all(edge["kind"] == "spawnerWaveGroupPartKilled" for edge in edges)
        )
        self.assertTrue(all(edge["tier"] == "strong" for edge in edges))

    def test_spawner_group_callback_follows_exact_local_custom_event_relay(
        self,
    ) -> None:
        candidates = {"radio_m1_group401", "cutscene_m1_group501"}
        flow = mission_payload([])["flow"]
        flow["unlinkedNativePlayback"] = [
            {
                "key": "radio_m1_group401",
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "occurrences": [{
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "localId": 41,
                    "actionName": "Play3DRadio",
                    "recordClass": "play_radio",
                    "allStoryKeysInRecord": ["radio_m1_group401"],
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "LevelEvent_OnSpawnerGroupBegin",
                        "headerLocalId": 40,
                        "eventDetail": {
                            "type": "LevelEvent_OnSpawnerGroupBegin",
                            "spawnerFilterId": 1004,
                            "groupKeyFilter": "401",
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-event",
                        },
                    }],
                }],
            },
            {
                "key": "cutscene_m1_group501",
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "nativeEventProducerRoutes": [{
                    "status": "exact_serialized_local_producer",
                    "storyKey": "cutscene_m1_group501",
                    "levelId": "map_test",
                    "raisedEventKey": "TigerStart",
                    "producerAction": "RaiseCustomScriptEvent",
                    "producerActionLocalId": 51,
                    "producerScriptId": "1001",
                    "producerSourceFile":
                        "LevelScriptData/map_test/1001.json",
                    "receiverMode": "current_script",
                    "targetScriptId": "1001",
                    "listenerScriptIds": ["1001"],
                    "listenerSourceFiles": [
                        "LevelScriptData/map_test/1001.json",
                    ],
                    "listenerRoutes": [{
                        "listenerScriptId": "1001",
                        "listenerSourceFile":
                            "LevelScriptData/map_test/1001.json",
                        "listenerEventOwner": {
                            "status": "exact_serialized_control_path",
                            "headerName": "ScriptEvent_OnCustomEvent",
                            "headerLocalId": 60,
                            "eventDetail": {
                                "type": "ScriptEvent_OnCustomEvent",
                                "eventKey": "TigerStart",
                            },
                        },
                    }],
                    "producerControlPaths": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "LevelEvent_OnSpawnerGroupBegin",
                        "headerLocalId": 50,
                        "eventDetail": {
                            "type": "LevelEvent_OnSpawnerGroupBegin",
                            "spawnerFilterId": 1004,
                            "groupKeyFilter": "501",
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-event",
                        },
                    }],
                    "nativeMappingId": "gameassembly-test-actionbase",
                    "serverExchange": False,
                }],
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / "map_test"
            config_dir.mkdir()
            (config_dir / "sc_map_test_1004.json").write_bytes(
                spawner_wave_fixture()
            )
            edges = (
                partial_order._spawner_wave_group_part_killed_story_edges(
                    flow,
                    candidates,
                    spawner_roots=[root],
                )
            )

        self.assertEqual(len(edges), 1)
        self.assertEqual(
            (edges[0]["from"], edges[0]["to"]),
            ("radio_m1_group401", "cutscene_m1_group501"),
        )
        child_event = edges[0]["events"][0]["childEvents"][0]
        self.assertEqual(
            child_event["routeMode"],
            "sameScriptCustomEventRelay",
        )
        self.assertEqual(child_event["raisedEventKey"], "TigerStart")

        rejected_mutations = {
            "cross-script listener route": lambda route: route.update(
                listenerScriptId="1002"
            ),
            "mismatched listener event key": lambda route: route[
                "listenerEventOwner"
            ]["eventDetail"].update(eventKey="OtherEvent"),
            "non-current receiver": lambda route: route.update(
                receiverMode="specified_script"
            ),
            "non-binary producer mapping": lambda route: route.update(
                nativeMappingId="manual-test-mapping"
            ),
            "missing producer mapping": lambda route: route.pop(
                "nativeMappingId"
            ),
        }
        for label, mutate in rejected_mutations.items():
            with self.subTest(label=label):
                rejected_flow = copy.deepcopy(flow)
                producer = rejected_flow["unlinkedNativePlayback"][1][
                    "nativeEventProducerRoutes"
                ][0]
                if label in {
                    "cross-script listener route",
                    "mismatched listener event key",
                }:
                    mutate(producer["listenerRoutes"][0])
                else:
                    mutate(producer)
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    config_dir = root / "map_test"
                    config_dir.mkdir()
                    (config_dir / "sc_map_test_1004.json").write_bytes(
                        spawner_wave_fixture()
                    )
                    rejected_edges = (
                        partial_order
                        ._spawner_wave_group_part_killed_story_edges(
                            rejected_flow,
                            candidates,
                            spawner_roots=[root],
                        )
                    )
                self.assertEqual(rejected_edges, [])

    def test_quest_state_typed_action_path_recovers_strict_story_order(self) -> None:
        candidates = {
            "cutscene_m1_1": "cutscene",
            "radio_m1_1": "radio",
            "radio_m1_2": "radio",
        }
        payload = mission_payload([])
        action_path = [9, 10, 11, 12]
        payload["flow"]["quests"] = [{
            "id": "m1_q#2",
            "storyConnections": [
                {
                    "key": key,
                    "relation": "levelscript_quest_completed_action",
                    "confidence": "native_typed_direct",
                    "event": "LevelEvent_OnQuestStateChanged",
                    "questState": 3,
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "headerLocalId": 8,
                    "actionLocalId": local_id,
                    "actionPathIndex": index,
                    "actionPathLocalIds": action_path,
                    "nativeMappingId": "gameassembly-test-actionbase",
                }
                for key, local_id, index in (
                    ("cutscene_m1_1", 9, 0),
                    ("radio_m1_1", 11, 2),
                    ("radio_m1_2", 12, 3),
                )
            ],
        }]

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        edges = [
            edge for edge in result["directEdges"]
            if edge["kind"] == "levelscriptQuestStateActionPath"
        ]
        self.assertEqual(
            {(edge["from"], edge["to"]) for edge in edges},
            {
                ("cutscene_m1_1", "radio_m1_1"),
                ("radio_m1_1", "radio_m1_2"),
            },
        )
        self.assertTrue(all(edge["tier"] == "strong" for edge in edges))
        self.assertEqual(result["summary"]["comparableScenePairs"], 3)

    def test_native_control_path_prefix_recovers_strict_story_order(self) -> None:
        candidates = {"cutscene_m1_1": "cutscene", "dlg_m1_1": "dlg", "radio_m1_1": "radio"}
        payload = mission_payload([])
        owner = lambda path: {  # noqa: E731 - compact fixture helper
            "status": "exact_serialized_control_path",
            "headerName": "ScriptEvent_OnCustomEvent",
            "headerLocalId": 4,
            "path": [{"localId": local_id} for local_id in path],
        }
        payload["flow"]["missionStoryConnections"] = [
            {
                "key": "cutscene_m1_1",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5])],
                }],
            },
            {
                "key": "dlg_m1_1",
                "nativeOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5, 6])],
                }],
            },
            {
                "key": "radio_m1_1",
                "nativeOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5, 6, 7])],
                }],
            },
        ]

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        native_edges = [
            edge for edge in result["directEdges"]
            if edge["kind"] == "levelscriptNativeControlPath"
        ]
        self.assertEqual(
            {(edge["from"], edge["to"]) for edge in native_edges},
            {
                ("cutscene_m1_1", "dlg_m1_1"),
                ("cutscene_m1_1", "radio_m1_1"),
                ("dlg_m1_1", "radio_m1_1"),
            },
        )
        self.assertTrue(all(edge["tier"] == "strong" for edge in native_edges))
        self.assertTrue(
            all(edge["transitionKinds"] == ["linear"] for edge in native_edges)
        )
        self.assertEqual(
            native_edges[0]["events"][0]["transitionSteps"][0][
                "transitionKind"
            ],
            "linear",
        )
        self.assertEqual(
            result["summary"]["nativeControlPathTransitionEdgeCount"],
            3,
        )
        self.assertEqual(
            result["summary"][
                "nativeControlPathBranchingTransitionEdgeCount"
            ],
            0,
        )
        self.assertEqual(result["summary"]["comparableScenePairs"], 3)

    def test_native_story_transition_suffix_preserves_typed_branch(self) -> None:
        predicate = json.dumps({
            "status": "exact_unique_getter",
            "getterLocalId": 20,
            "getterName": "BooleanCompare",
        }, sort_keys=True, separators=(",", ":"))
        source_path = (
            (5, "ActionHeader.nextId", "PlayRadio", "play_radio", "{}"),
        )
        target_path = (
            *source_path,
            (6, "ActionBase.nextId", "IfElseAction", "branch", predicate),
            (
                7,
                "IfElseAction.trueAction",
                "StartDialogAction",
                "play_dialog",
                "{}",
            ),
        )

        steps = partial_order._native_story_transition_steps(
            source_path,
            target_path,
        )

        self.assertEqual(
            [step["transitionKind"] for step in steps],
            ["linear", "conditionalBranch"],
        )
        self.assertEqual(
            steps[1]["predicate"]["getterName"],
            "BooleanCompare",
        )
        self.assertEqual(steps[1]["sourceLocalId"], 6)
        self.assertEqual(steps[1]["targetLocalId"], 7)
        self.assertEqual(
            partial_order._native_story_transition_steps(
                target_path,
                source_path,
            ),
            [],
        )

    def test_native_control_edge_reports_branching_transition(self) -> None:
        candidates = {"radio_m1_1": "radio", "dlg_m1_1": "dlg"}
        predicate = {
            "status": "exact_unique_getter",
            "getterLocalId": 20,
            "getterName": "BooleanCompare",
        }

        def connection(key: str, path: list[dict]) -> dict:
            return {
                "key": key,
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "LevelScriptData/map_test/70000000001.json",
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "ScriptEvent_OnCustomEvent",
                        "headerLocalId": 4,
                        "path": path,
                    }],
                }],
            }

        source_step = {
            "localId": 5,
            "edge": "ActionHeader.nextId",
            "actionName": "PlayRadio",
            "recordClass": "play_radio",
        }
        payload = mission_payload([])
        payload["flow"]["missionStoryConnections"] = [
            connection("radio_m1_1", [source_step]),
            connection("dlg_m1_1", [
                source_step,
                {
                    "localId": 6,
                    "edge": "ActionBase.nextId",
                    "actionName": "IfElseAction",
                    "recordClass": "branch",
                    "branchPredicate": predicate,
                },
                {
                    "localId": 7,
                    "edge": "IfElseAction.trueAction",
                    "actionName": "StartDialogAction",
                    "recordClass": "play_dialog",
                },
            ]),
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        edge = next(
            edge
            for edge in result["directEdges"]
            if edge["kind"] == "levelscriptNativeControlPath"
        )
        self.assertTrue(edge["branchingTransition"])
        self.assertEqual(
            edge["transitionKinds"],
            ["conditionalBranch", "linear"],
        )
        self.assertEqual(
            edge["events"][0]["transitionSteps"][1]["predicate"],
            predicate,
        )
        self.assertEqual(
            result["summary"][
                "nativeControlPathBranchingTransitionEdgeCount"
            ],
            1,
        )

    def test_while_action_path_is_reachability_not_global_story_order(self) -> None:
        candidates = {"radio_m1_1": "radio", "radio_m1_2": "radio"}
        payload = mission_payload([])

        def owner(path: list[tuple[int, str]]) -> dict:
            return {
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "headerLocalId": 4,
                "path": [
                    {"localId": local_id, "edge": edge}
                    for local_id, edge in path
                ],
            }

        payload["flow"]["missionStoryConnections"] = [
            {
                "key": "radio_m1_1",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([
                        (5, "ActionHeader.nextId"),
                        (6, "WhileAction.doAction"),
                    ])],
                }],
            },
            {
                "key": "radio_m1_2",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([
                        (5, "ActionHeader.nextId"),
                        (6, "WhileAction.doAction"),
                        (7, "ActionBase.nextId"),
                    ])],
                }],
            },
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(
            [],
            [
                edge
                for edge in result["directEdges"]
                if edge["kind"] == "levelscriptNativeControlPath"
            ],
        )

    def test_exact_native_path_admits_cross_owner_scene_context(self) -> None:
        candidates = {"radio_m1_1": "radio"}
        payload = mission_payload([])

        def owner(path: list[int], header_local_id: int = 4) -> dict:
            return {
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "headerLocalId": header_local_id,
                "path": [{"localId": local_id} for local_id in path],
            }

        payload["flow"]["missionStoryConnections"] = [
            {
                "key": "dlg_other_9",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5])],
                }],
            },
            {
                "key": "radio_m1_1",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5, 6])],
                }],
            },
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(
            result["nativeControlPathContextSceneKeys"],
            ["dlg_other_9"],
        )
        self.assertEqual(
            result["summary"]["nativeControlPathContextSceneCount"],
            1,
        )
        self.assertEqual(
            {
                (edge["from"], edge["to"])
                for edge in result["directEdges"]
                if edge["kind"] == "levelscriptNativeControlPath"
            },
            {("dlg_other_9", "radio_m1_1")},
        )
        membership = {
            node["key"]: node["membership"]
            for node in result["nodes"]
        }
        self.assertEqual(membership["radio_m1_1"], "index")
        self.assertEqual(
            membership["dlg_other_9"],
            "exactNativeControlPathContext",
        )

    def test_cross_owner_context_rejects_non_prefix_native_and_graph_clues(
        self,
    ) -> None:
        candidates = {"radio_m1_1": "radio"}
        payload = mission_payload([{
            "from": "dlg_other_graph",
            "to": "radio_m1_1",
            "kind": "levelscriptChain",
        }])

        def connection(
            key: str,
            path: list[int],
            header_local_id: int = 4,
        ) -> dict:
            return {
                "key": key,
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                        "headerLocalId": header_local_id,
                        "path": [
                            {"localId": local_id}
                            for local_id in path
                        ],
                    }],
                }],
            }

        payload["flow"]["missionStoryConnections"] = [
            connection("radio_m1_1", [5, 6]),
            connection("dlg_other_equal", [5, 6]),
            connection("dlg_other_divergent", [5, 7]),
            connection("dlg_other_event", [5], header_local_id=40),
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(result["nativeControlPathContextSceneKeys"], [])
        self.assertEqual(
            {node["key"] for node in result["nodes"]},
            {"radio_m1_1"},
        )
        self.assertEqual(result["directEdges"], [])

    def test_native_control_paths_preserve_branch_arms_and_merge(self) -> None:
        candidates = {"radio_m1_true": "radio", "radio_m1_false": "radio"}
        payload = mission_payload([])

        def owner(path: list[tuple[int, str]]) -> dict:
            return {
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnCustomEvent",
                "headerLocalId": 4,
                "eventDetail": {
                    "type": "ScriptEvent_OnCustomEvent",
                    "eventKey": "branch_test",
                    "summary": "custom event branch_test",
                },
                "path": [
                    {"localId": local_id, "edge": edge}
                    for local_id, edge in path
                ],
            }

        def connection(key: str, path: list[tuple[int, str]]) -> dict:
            return {
                "key": key,
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner(path)],
                }],
            }

        payload["flow"]["missionStoryConnections"] = [
            connection("radio_m1_true", [
                (5, "ActionHeader.nextId"),
                (6, "IfElseAction.trueAction"),
                (9, "ActionBase.nextId"),
                (12, "ActionBase.nextId"),
            ]),
            connection("radio_m1_false", [
                (5, "ActionHeader.nextId"),
                (7, "IfElseAction.falseAction"),
                (9, "ActionBase.nextId"),
                (13, "ActionBase.nextId"),
            ]),
        ]
        predicate = {
            "status": "exact_unique_getter",
            "getterLocalId": 20,
            "getterName": "BooleanCompare",
            "getterUnionTag": "0x0004",
            "detailKind": "booleanCompare",
            "detail": {
                "comparerName": "Equal",
                "valueA": {"path": "enabled", "value": False},
                "valueB": {"value": True},
            },
        }
        for connection_row in payload["flow"]["missionStoryConnections"]:
            connection_row["levelScriptOccurrences"][0]["nativeEventOwners"][0]["path"][0][
                "branchPredicate"
            ] = predicate

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        branch = result["branches"]["nativeControlBranches"][0]
        self.assertEqual(branch["kind"], "ifElse")
        self.assertEqual(branch["branchLocalId"], 5)
        self.assertEqual(branch["predicate"]["getterName"], "BooleanCompare")
        self.assertEqual(branch["eventDetail"]["eventKey"], "branch_test")
        self.assertEqual(
            {arm["edge"] for arm in branch["arms"]},
            {"IfElseAction.trueAction", "IfElseAction.falseAction"},
        )
        merge = result["branches"]["nativeControlMerges"][0]
        self.assertEqual(merge["mergeLocalId"], 9)
        self.assertEqual(result["summary"]["nativeControlBranchCount"], 1)
        self.assertEqual(result["summary"]["nativeControlMergeCount"], 1)
        self.assertEqual(result["summary"]["nativeNamedPredicateCount"], 1)
        self.assertEqual(result["summary"]["nativeSemanticPredicateCount"], 1)
        self.assertEqual(result["summary"]["nativeClassOnlyPredicateCount"], 0)

    def test_native_branch_sequence_creates_exact_story_order(self) -> None:
        candidates = {
            "radio_m1_first": "radio",
            "cutscene_m1_second": "cutscene",
            "radio_m1_after": "radio",
        }
        payload = mission_payload([])

        def connection(key: str, edge: str, entry_id: int) -> dict:
            return {
                "key": key,
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "LevelScriptData/map_test/70000000001.json",
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "ScriptEvent_OnCustomEvent",
                        "headerLocalId": 4,
                        "path": [
                            {
                                "localId": 5,
                                "edge": "ActionHeader.nextId",
                                "actionName": "Branch",
                            },
                            {"localId": entry_id, "edge": edge},
                        ],
                    }],
                }],
            }

        payload["flow"]["missionStoryConnections"] = [
            connection("radio_m1_first", "Branch.sequence[0]", 10),
            connection("cutscene_m1_second", "Branch.sequence[1]", 20),
            connection("radio_m1_after", "ActionBase.nextId", 30),
        ]

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["summary"]["nativeOrderedSequenceCount"], 1)
        self.assertEqual(result["summary"]["nativeOrderedSequenceEdgeCount"], 3)
        self.assertEqual(
            {
                (edge["from"], edge["to"])
                for edge in result["directEdges"]
                if edge["kind"] == "levelscriptNativeOrderedSequence"
            },
            {
                ("radio_m1_first", "cutscene_m1_second"),
                ("radio_m1_first", "radio_m1_after"),
                ("cutscene_m1_second", "radio_m1_after"),
            },
        )
        sequence = result["branches"]["nativeOrderedSequences"][0]
        self.assertEqual(sequence["branchLocalId"], 5)
        self.assertEqual(
            [arm["edge"] for arm in sequence["arms"]],
            [
                "Branch.sequence[0]",
                "Branch.sequence[1]",
                "ActionBase.nextId (after sequence)",
            ],
        )
        self.assertEqual(
            sequence["runtimeMappingId"],
            "gameassembly-2026-08-02-branch-execute-0x18764d990",
        )

    def test_related_action_topology_requires_exact_story_path_file(self) -> None:
        payload = mission_payload([])
        payload["flow"]["missionStoryConnections"] = [{
            "key": "radio_m1_1",
            "levelScriptOccurrences": [{
                "levelId": "map_test",
                "scriptId": "70000000001",
                "sourceFile": "LevelScriptData/map_test/70000000001.json",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "ScriptEvent_OnCustomEvent",
                    "headerLocalId": 4,
                    "path": [{
                        "localId": 5,
                        "edge": "ActionHeader.nextId",
                    }],
                }],
            }],
        }]
        topology = {
            "schema": "levelScriptNativeActionTopology.v4",
            "status": "exact_complete_action_map",
            "actionNodeCount": 3,
            "eventRootCount": 1,
            "physicalHeaderRecordCount": 2,
            "runtimeShadowedHeaderRecordCount": 1,
            "runtimeShadowedHeaderLocalIdCount": 1,
            "runtimeShadowedGetterRecordCount": 2,
            "runtimeShadowedGetterLocalIdCount": 1,
            "edgeCount": 3,
            "orderedSequenceNodeCount": 1,
            "eventRootRuntimeMode": "independently_invoked_indexed_event_slots",
            "runtimeHeaderSlotMappingId": "indexed-slots",
            "runtimeGetterSlotMappingId": "indexed-slots",
            "eventRoots": [{
                "localId": 4,
                "headerName": "ScriptEvent_OnCustomEvent",
                "nextActionLocalId": 5,
                "priority": -1000,
                "triggerActiveDuring": True,
                "filterMode": 2,
                "runtimeHeaderSlotMappingId": "indexed-slots",
            }],
            "actions": [{
                "localId": 5,
                "actionName": "Branch",
                "controlKind": "ordered_sequence",
                "controlRuntimeMappingId": (
                    "gameassembly-2026-08-02-branch-execute-0x18764d990"
                ),
            }],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = (
                Path(temp_dir) / "LevelScriptData" / "map_test"
                / "70000000001.json"
            )
            source_path.parent.mkdir(parents=True)
            source_path.write_bytes(b"fixture")
            partial_order._NATIVE_ACTION_TOPOLOGY_CACHE.clear()
            with patch.object(partial_order, "ROOT", Path(temp_dir)), patch.object(
                partial_order,
                "decode_levelscript_native_action_topology",
                return_value=(topology, None),
            ):
                result = partial_order.build_mission_partial_order(
                    "m1", {"radio_m1_1": "radio"}, payload
                )

        self.assertEqual(result["summary"]["nativeRelatedActionTopologyCount"], 1)
        related = result["branches"]["nativeRelatedActionTopologies"][0]
        self.assertEqual(related["relatedStoryKeys"], ["radio_m1_1"])
        self.assertEqual(related["orderedSequenceNodeCount"], 1)
        self.assertEqual(related["controlActions"][0]["actionName"], "Branch")
        self.assertEqual(related["physicalHeaderRecordCount"], 2)
        self.assertEqual(related["runtimeShadowedHeaderRecordCount"], 1)
        self.assertEqual(related["runtimeShadowedGetterRecordCount"], 2)
        self.assertEqual(related["runtimeHeaderSlotMappingId"], "indexed-slots")
        self.assertEqual(related["runtimeGetterSlotMappingId"], "indexed-slots")
        self.assertEqual(
            related["eventRootRuntimeMode"],
            "independently_invoked_indexed_event_slots",
        )
        self.assertEqual(related["selectedEventRoots"][0]["localId"], 4)
        self.assertEqual(
            related["selectedEventRoots"][0]["headerName"],
            "ScriptEvent_OnCustomEvent",
        )
        self.assertEqual(related["selectedEventRoots"][0]["priority"], -1000)

    def test_runtime_shadowed_native_paths_preserve_exact_split(self) -> None:
        candidates = {"radio_m1_1": "radio", "cutscene_m1_1": "cutscene"}
        payload = mission_payload([])

        def connection(
            key: str,
            arm_edge: str,
            entry_id: int,
            downstream_ids: list[int],
        ) -> dict:
            return {
                "key": key,
                "levelIds": ["map_test"],
                "scriptIds": ["70000000001"],
                "sourceFiles": [
                    "MissionRuntimeAsset/m1.json",
                    "LevelScriptData/map_test/70000000001.json",
                ],
                "nativeEventOwners": [{
                        "status": "exact_serialized_control_path_runtime_shadowing",
                        "headerName": "MissionEvent_OnClientGlobalVarChanged",
                        "headerLocalId": 28,
                        "path": [
                            {
                                "localId": 7,
                                "edge": "ActionHeader.nextId",
                                "runtimeShadowedRecordOffsets": [7],
                                "runtimeDuplicateSignatureStatus":
                                    "different_payload",
                            },
                            {"localId": entry_id, "edge": arm_edge},
                        ],
                        "downstreamControlStatus":
                            "exact_serialized_typed_reachability",
                        "downstreamControlPaths": [
                            [
                                {
                                    "localId": local_id,
                                    "edge": "ActionBase.nextId",
                                }
                                for local_id in downstream_ids[:index]
                            ]
                            for index in range(1, len(downstream_ids) + 1)
                        ],
                    }],
            }

        payload["flow"]["missionStoryConnections"] = [
            connection(
                "radio_m1_1",
                "Split.actions[0]",
                17,
                [18, 11],
            ),
            connection(
                "cutscene_m1_1",
                "Split.actions[1]",
                8,
                [9, 10, 11],
            ),
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(result["summary"]["nativeControlBranchCount"], 1)
        branch = result["branches"]["nativeControlBranches"][0]
        self.assertEqual(branch["kind"], "splitFanout")
        self.assertEqual(branch["branchLocalId"], 7)
        self.assertEqual(
            [arm["edge"] for arm in branch["arms"]],
            ["Split.actions[0]", "Split.actions[1]"],
        )
        self.assertEqual(branch["sourceFiles"], [
            "LevelScriptData/map_test/70000000001.json",
            "MissionRuntimeAsset/m1.json",
        ])
        merge = result["branches"]["nativeControlMerges"][0]
        self.assertEqual(merge["mergeLocalId"], 11)
        self.assertEqual(
            merge["convergenceStatus"],
            "exact_serialized_downstream_control_convergence",
        )
        self.assertEqual(merge["mergePaths"], [[18, 11], [9, 10, 11]])

    def test_unvalidated_duplicate_native_path_status_stays_excluded(self) -> None:
        candidates = {"radio_m1_1": "radio", "cutscene_m1_1": "cutscene"}
        payload = mission_payload([])
        payload["flow"]["missionStoryConnections"] = [
            {
                "key": key,
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [{
                        "status": "duplicate_local_id_conflict",
                        "headerName": "ScriptEvent_OnCustomEvent",
                        "headerLocalId": 4,
                        "path": [
                            {"localId": 5, "edge": "ActionHeader.nextId"},
                            {"localId": entry, "edge": edge},
                        ],
                    }],
                }],
            }
            for key, entry, edge in (
                ("radio_m1_1", 6, "Split.actions[0]"),
                ("cutscene_m1_1", 7, "Split.actions[1]"),
            )
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(result["summary"]["nativeControlBranchCount"], 0)
        self.assertEqual(result["directEdges"], [])

    def test_chain_is_transitively_reduced(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "questPrev"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questPrev"},
            {"from": "dlg_a", "to": "dlg_c", "kind": "questPrev"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        component_by_scene = {row["key"]: row["component"] for row in result["nodes"]}
        reduced = {(row["from"], row["to"]) for row in result["reducedComponentEdges"]}
        self.assertEqual(reduced, {
            (component_by_scene["dlg_a"], component_by_scene["dlg_b"]),
            (component_by_scene["dlg_b"], component_by_scene["dlg_c"]),
        })
        self.assertEqual(result["summary"]["comparableScenePairs"], 3)
        self.assertEqual(result["summary"]["unorderedScenePairs"], 0)

    def test_option_fork_remains_partial(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {
                "from": "dlg_a",
                "to": "dlg_b",
                "kind": "authoredDirect",
                "optionIds": ["option_a_1"],
                "sourceKeys": ["tree_a"],
            },
            {
                "from": "dlg_a",
                "to": "dlg_c",
                "kind": "authoredMenu",
                "optionIds": ["option_a_2"],
                "sourceKeys": ["tree_a"],
            },
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["summary"]["comparableScenePairs"], 1)
        self.assertEqual(result["summary"]["unorderedScenePairs"], 2)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 1)
        option_group = result["branches"]["sceneGraphOptions"][0]
        self.assertTrue(option_group["isFork"])
        self.assertEqual(
            {arm["optionId"] for arm in option_group["arms"]},
            {"option_a_1", "option_a_2"},
        )

    def test_cycle_is_collapsed_without_internal_order(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "authoredDirect"},
            {"from": "dlg_b", "to": "dlg_a", "kind": "authoredDirect"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questPrev"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(len(result["cycles"]), 1)
        self.assertEqual(set(result["cycles"][0]["sceneKeys"]), {"dlg_a", "dlg_b"})
        self.assertEqual(result["summary"]["cyclicInternalPairs"], 1)
        self.assertEqual(result["summary"]["comparableScenePairs"], 2)
        self.assertEqual(
            {node["relationStatus"] for node in result["nodes"] if node["key"] in {"dlg_a", "dlg_b"}},
            {"cycle"},
        )

    def test_source_topology_without_playback_contract_does_not_create_order(self) -> None:
        candidates = {
            "dlg_a": "dlg",
            "dlg_b": "dlg",
            "dlg_c": "dlg",
            "dlg_d": "dlg",
            "dlg_e": "dlg",
        }
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "questSequence"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questFailGuard"},
            {"from": "dlg_c", "to": "dlg_d", "kind": "authoredMenu"},
            {"from": "dlg_d", "to": "dlg_e", "kind": "levelscriptSceneChain"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["summary"]["strongEdgeCount"], 0)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 4)
        self.assertEqual(result["summary"]["comparableScenePairs"], 0)
        self.assertEqual(result["cycles"], [])
        self.assertEqual(set(result["weakOnlySceneKeys"]), set(candidates))

    def test_reciprocal_quest_file_projection_is_supported_not_chronology(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg"}
        payload = mission_payload([
            {
                "from": "dlg_a",
                "to": "dlg_b",
                "kind": "questPrev",
                "questIds": ["m1_q#1", "m1_q#2"],
            },
            {
                "from": "dlg_b",
                "to": "dlg_a",
                "kind": "questPrev",
                "questIds": ["m1_q#3", "m1_q#4"],
            },
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["summary"]["strongEdgeCount"], 0)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 2)
        self.assertEqual(result["summary"]["comparableScenePairs"], 0)
        self.assertEqual(result["cycles"], [])
        self.assertTrue(all(
            edge.get("demotionReason") == "reciprocalQuestProjection"
            for edge in result["directEdges"]
        ))

    def test_weak_and_supported_edges_do_not_create_order(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "levelscriptFileOrder"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "radioContinuation"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["reducedComponentEdges"], [])
        self.assertEqual(result["summary"]["comparableScenePairs"], 0)
        self.assertEqual(result["summary"]["weakEdgeCount"], 1)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 1)
        self.assertEqual(set(result["weakOnlySceneKeys"]), set(candidates))

    def test_candidates_ignore_rank_order_and_non_index_scene(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg"}
        payload = mission_payload(
            [{"from": "dlg_a", "to": "dlg_override_only", "kind": "questSequence"}],
            node_orders={"dlg_a": 50, "dlg_b": 1, "dlg_override_only": 0},
        )

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual({node["key"] for node in result["nodes"]}, set(candidates))
        self.assertEqual(result["directEdges"], [])
        self.assertEqual(result["isolatedSceneKeys"], ["dlg_a", "dlg_b"])
        self.assertEqual(
            [row["key"] for row in result["unresolvedSourceNodes"]],
            ["dlg_override_only"],
        )

    def test_preload_only_source_node_is_definition_not_unresolved(
        self,
    ) -> None:
        candidates = {"radio_m1_1": "radio"}
        payload = mission_payload([{
            "from": "radio_m1_1",
            "to": "cutscene_test_preload",
            "kind": "levelscriptSceneChain",
            "fromActionClasses": ["play_radio"],
            "toActionClasses": ["preload_cutscene"],
            "sourceFiles": ["preload-source.json"],
            "levelIds": ["level_preload"],
        }])
        next(
            node
            for node in payload["flow"]["sceneGraph"]["nodes"]
            if node["key"] == "cutscene_test_preload"
        )["kind"] = "cutscene"

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(result["unresolvedSourceNodes"], [])
        self.assertEqual(
            result["definitionOnlySourceNodes"],
            [{
                "key": "cutscene_test_preload",
                "kind": "cutscene",
                "incidentEdgeKinds": ["levelscriptSceneChain"],
                "recordClasses": ["preload_cutscene"],
                "sourceFiles": ["preload-source.json"],
                "levelIds": ["level_preload"],
            }],
        )
        self.assertEqual(
            result["summary"]["definitionOnlySourceNodeCount"],
            1,
        )

    def test_final_playback_source_node_remains_unresolved(self) -> None:
        candidates = {"radio_m1_1": "radio"}
        payload = mission_payload([{
            "from": "radio_m1_1",
            "to": "cutscene_missing_playback",
            "kind": "levelscriptSceneChain",
            "fromActionClasses": ["play_radio"],
            "toActionClasses": ["play_cutscene"],
        }])
        next(
            node
            for node in payload["flow"]["sceneGraph"]["nodes"]
            if node["key"] == "cutscene_missing_playback"
        )["kind"] = "cutscene"

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(
            [row["key"] for row in result["unresolvedSourceNodes"]],
            ["cutscene_missing_playback"],
        )
        self.assertEqual(result["definitionOnlySourceNodes"], [])

    def test_global_final_playback_overrides_preload_only_incident_edge(
        self,
    ) -> None:
        candidates = {"radio_m1_1": "radio"}
        payload = mission_payload([{
            "from": "radio_m1_1",
            "to": "cutscene_played_elsewhere",
            "kind": "levelscriptSceneChain",
            "fromActionClasses": ["play_radio"],
            "toActionClasses": ["preload_cutscene"],
        }])
        next(
            node
            for node in payload["flow"]["sceneGraph"]["nodes"]
            if node["key"] == "cutscene_played_elsewhere"
        )["kind"] = "cutscene"

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
            exact_playback_source_keys={"cutscene_played_elsewhere"},
        )

        self.assertEqual(
            [row["key"] for row in result["unresolvedSourceNodes"]],
            ["cutscene_played_elsewhere"],
        )
        self.assertEqual(result["definitionOnlySourceNodes"], [])

    def test_exact_playback_source_file_adds_cross_owner_context(
        self,
    ) -> None:
        payload = mission_payload([{
            "from": "radio_m1_1",
            "to": "cutscene_other_owner_1",
            "kind": "levelscriptSceneChain",
            "sourceFiles": ["source.json"],
        }])
        candidates, context_keys = (
            partial_order._expand_levelscript_playback_context_candidates(
                {"radio_m1_1": "radio"},
                payload,
                {"cutscene_other_owner_1": "cutscene"},
                {"cutscene_other_owner_1": {"source.json"}},
            )
        )

        self.assertEqual(
            candidates["cutscene_other_owner_1"],
            "cutscene",
        )
        self.assertEqual(
            context_keys,
            {"cutscene_other_owner_1"},
        )
        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
            exact_levelscript_playback_context_keys=context_keys,
        )
        context_node = next(
            node
            for node in result["nodes"]
            if node["key"] == "cutscene_other_owner_1"
        )
        self.assertEqual(
            context_node["membership"],
            "exactLevelScriptPlaybackContext",
        )

    def test_playback_context_requires_same_source_file(self) -> None:
        payload = mission_payload([{
            "from": "radio_m1_1",
            "to": "cutscene_other_owner_1",
            "kind": "levelscriptSceneChain",
            "sourceFiles": ["mission-source.json"],
        }])

        candidates, context_keys = (
            partial_order._expand_levelscript_playback_context_candidates(
                {"radio_m1_1": "radio"},
                payload,
                {"cutscene_other_owner_1": "cutscene"},
                {"cutscene_other_owner_1": {"other-source.json"}},
            )
        )

        self.assertEqual(candidates, {"radio_m1_1": "radio"})
        self.assertEqual(context_keys, set())

    def test_quest_forks_and_merges_are_preserved(self) -> None:
        candidates = {"dlg_a": "dlg"}
        payload = mission_payload(
            [],
            branch_points=[{
                "questId": "m1_q#1",
                "successorQuestIds": ["m1_q#2", "m1_q#3"],
                "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
            }],
            quest_edges=[
                {"from": "m1_q#2", "to": "m1_q#4", "kind": "questPrev", "source": {"field": "a"}},
                {"from": "m1_q#3", "to": "m1_q#4", "kind": "questPrev", "source": {"field": "b"}},
            ],
        )

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["branches"]["questForks"][0]["questId"], "m1_q#1")
        self.assertEqual(result["summary"]["questForkCount"], 1)
        self.assertEqual(result["summary"]["questMergeCount"], 1)
        self.assertEqual(
            result["branches"]["questMerges"][0]["predecessorQuestIds"],
            ["m1_q#2", "m1_q#3"],
        )

    def test_direct_dialog_tree_branch_lines_are_source_backed(self) -> None:
        conv = {
            "key": "dlg_m1_1",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_1_001",
                "options": [
                    {"id": "option_1", "i": 1, "branchLines": ["dlg_m1_1_002"]},
                    {"id": "option_2", "i": 2, "branchLines": ["dlg_m1_1_003"]},
                ],
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_1",
                "file": "export_full/source/DialogTree/dlg_m1_1.json",
                "after": "dlg_m1_1_001",
                "options": [
                    {"optionId": "option_1", "firstLineId": "dlg_m1_1_002", "pathLineIds": ["dlg_m1_1_002"]},
                    {"optionId": "option_2", "firstLineId": "dlg_m1_1_003", "pathLineIds": ["dlg_m1_1_003"]},
                ],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_1": "dlg"}, mission_payload([]), [("conv/dlg_m1_1.json", conv)]
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["provenance"]["kind"], "DialogTreeBranchLines")
        self.assertEqual(
            [option["branchLineIds"] for option in groups[0]["options"]],
            [["dlg_m1_1_002"], ["dlg_m1_1_003"]],
        )

    def test_exact_runtime_jump_signature_is_source_backed(self) -> None:
        conv = {
            "key": "dlg_m1_2",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_2_001",
                "options": [
                    {"id": "option_1", "branchLines": ["dlg_m1_2_002"]},
                    {"id": "option_2", "branchLines": ["dlg_m1_2_003"]},
                ],
                "optionBranchRisk": {
                    "code": "timelineRouteBranches",
                    "reason": "runtimeJumpTrack",
                    "source": "dialogTimeline",
                    "branchLineIdsByOption": {
                        "option_1": ["dlg_m1_2_002"],
                        "option_2": ["dlg_m1_2_003"],
                    },
                    "skippedLineIdsByOption": {
                        "option_1": ["dlg_m1_2_003"],
                        "option_2": ["dlg_m1_2_002"],
                    },
                    "assetTracks": ["Runtime Jump Track.json"],
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_2": "dlg"}, mission_payload([]), [("conv/dlg_m1_2.json", conv)]
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["provenance"]["kind"], "DialogTimelineRuntimeJump")
        self.assertEqual(result["summary"]["dialogLineOptionRouteCount"], 2)

    def test_exact_timeline_clip_option_indices_are_source_backed(self) -> None:
        conv = {
            "key": "dlg_m1_clip_indices",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_clip_indices_001",
                "options": [
                    {
                        "id": "option_1",
                        "branchLines": [
                            "dlg_m1_clip_indices_002",
                            "dlg_m1_clip_indices_003",
                        ],
                    },
                    {
                        "id": "option_2",
                        "branchLines": ["dlg_m1_clip_indices_004"],
                    },
                ],
                "optionBranchRisk": {
                    "code": "timelineClipOptionIndexBranches",
                    "reason": "runtimeClipOptionIndex",
                    "source": "dialogTimeline",
                    "candidateMapping": "trunkClipOptionIndex",
                    "optionIndex": [1, 2],
                    "branchLineIdsByOption": {
                        "option_1": [
                            "dlg_m1_clip_indices_002",
                            "dlg_m1_clip_indices_003",
                        ],
                        "option_2": ["dlg_m1_clip_indices_004"],
                    },
                    "commonContinuationLineId":
                        "dlg_m1_clip_indices_005",
                    "assetTracks": ["Dialog Option Track.json"],
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_clip_indices": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_clip_indices.json", conv)],
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(
            groups[0]["provenance"]["kind"],
            "DialogTimelineClipOptionIndex",
        )
        self.assertEqual(
            [option["branchLineIds"] for option in groups[0]["options"]],
            [
                [
                    "dlg_m1_clip_indices_002",
                    "dlg_m1_clip_indices_003",
                ],
                ["dlg_m1_clip_indices_004"],
            ],
        )
        self.assertEqual(result["summary"]["dialogLineOptionRouteCount"], 2)

    def test_pre_dialog_runtime_jump_signature_is_source_backed(self) -> None:
        conv = {
            "key": "dlg_m1_pre",
            "optionGroups": [{
                "g": 1,
                "position": "pre",
                "options": [
                    {"id": "option_1", "branchLines": ["dlg_m1_pre_001"]},
                    {"id": "option_2", "branchLines": ["dlg_m1_pre_004"]},
                ],
                "optionBranchRisk": {
                    "code": "timelineRouteBranches",
                    "reason": "runtimeJumpTrack",
                    "source": "dialogTimeline",
                    "branchLineIdsByOption": {
                        "option_1": [
                            "dlg_m1_pre_001",
                            "dlg_m1_pre_002",
                            "dlg_m1_pre_003",
                        ],
                        "option_2": [
                            "dlg_m1_pre_004",
                            "dlg_m1_pre_005",
                            "dlg_m1_pre_006",
                        ],
                    },
                    "assetTracks": ["Runtime Jump Track.json"],
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_pre": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_pre.json", conv)],
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["after"], "")
        self.assertEqual(groups[0]["provenance"]["kind"], "DialogTimelineRuntimeJump")
        self.assertEqual(result["summary"]["dialogLineOptionRouteCount"], 2)

    def test_direct_dialog_tree_branch_debug_is_source_provenance(self) -> None:
        conv = {
            "key": "dlg_m1_direct",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_direct_001",
                "options": [{
                    "id": "option_1",
                    "branchLines": ["dlg_m1_direct_002"],
                    "_debug": {
                        "branchLineSources": [{
                            "kind": "DialogTree",
                            "sourceKey": "dlg_m1_direct",
                            "file": "export_full/source/DialogTree/dlg_m1_direct.json",
                        }],
                    },
                }, {
                    "id": "option_2",
                    "branchLines": ["dlg_m1_direct_003"],
                    "_debug": {
                        "branchLineSources": [{
                            "kind": "DialogTree",
                            "sourceKey": "dlg_m1_direct",
                            "file": "export_full/source/DialogTree/dlg_m1_direct.json",
                        }],
                    },
                }],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_direct": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_direct.json", conv)],
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["provenance"]["kind"], "DialogTreeBranchLines")
        self.assertEqual(
            groups[0]["provenance"]["sourceFiles"],
            ["export_full/source/DialogTree/dlg_m1_direct.json"],
        )

    def test_runtime_jump_direct_continuation_is_a_complete_route(self) -> None:
        conv = {
            "key": "dlg_m1_direct_continue",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_direct_continue_001",
                "options": [
                    {
                        "id": "option_1",
                        "branchLines": ["dlg_m1_direct_continue_002"],
                    },
                    {"id": "option_2"},
                ],
                "optionBranchRisk": {
                    "code": "timelineRouteBranches",
                    "reason": "runtimeJumpTrack",
                    "source": "dialogTimeline",
                    "branchLineIdsByOption": {
                        "option_1": ["dlg_m1_direct_continue_002"],
                        "option_2": [],
                    },
                    "directContinuationOptionIds": ["option_2"],
                    "commonContinuationLineId":
                        "dlg_m1_direct_continue_003",
                    "assetTracks": ["Runtime Jump Track.json"],
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_direct_continue": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_direct_continue.json", conv)],
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(result["summary"]["dialogLineOptionRouteCount"], 2)
        self.assertEqual(
            groups[0]["directContinuationOptionIds"],
            ["option_2"],
        )
        self.assertEqual(
            groups[0]["options"][1]["continuationLineId"],
            "dlg_m1_direct_continue_003",
        )
        self.assertTrue(groups[0]["options"][1]["directContinuation"])

    def test_inferred_option_routes_are_excluded(self) -> None:
        conv = {
            "key": "dlg_m1_3",
            "optionGroups": [{
                "g": 4,
                "after": "dlg_m1_3_001",
                "options": [{"id": "option_1"}, {"id": "option_2"}],
                "optionBranchRisk": {
                    "code": "inferredFollowingLines",
                    "reason": "optionTargetsMissing",
                    "source": "dialogTimeline",
                    "candidateLineIds": ["dlg_m1_3_002", "dlg_m1_3_003"],
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_3": "dlg"}, mission_payload([]), [("conv/dlg_m1_3.json", conv)]
        )

        self.assertEqual(result["branches"]["dialogLineOptions"], [])
        self.assertEqual(
            result["branches"]["excludedDialogLineOptions"][0]["exclusionReason"],
            "inferredOrUnsupportedRisk",
        )
        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            1,
        )
        self.assertEqual(
            result["summary"]["closedExcludedDialogLineOptionGroupCount"],
            0,
        )

    def test_option_group_without_explicit_route_stays_unknown(self) -> None:
        conv = {
            "key": "dlg_m1_4",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_4_001",
                "options": [{"id": "option_1"}, {"id": "option_2"}],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_4": "dlg"}, mission_payload([]), [("conv/dlg_m1_4.json", conv)]
        )

        self.assertEqual(result["branches"]["dialogLineOptions"], [])
        self.assertEqual(
            result["branches"]["noExplicitRouteGroups"][0]["reason"],
            "noExplicitSourceRoute",
        )
        self.assertEqual(
            result["summary"]["branchingNoExplicitRouteGroupCount"],
            1,
        )
        self.assertEqual(
            result["summary"]["singleOptionNoExplicitRouteGroupCount"],
            0,
        )

    def test_complete_authored_terminal_outcomes_are_closed_not_missing(self) -> None:
        conv = {
            "key": "dlg_m1_terminal",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_terminal_001",
                "options": [{"id": "option_1"}, {"id": "option_2"}],
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_terminal",
                "file": "export_full/source/DialogTree/dlg_m1_terminal.json",
                "after": "dlg_m1_terminal_001",
                "options": [{
                    "optionId": "option_1",
                    "terminal": "openUi",
                    "outcomeKind": "terminalOnly",
                }, {
                    "optionId": "option_2",
                    "terminal": "finish",
                    "outcomeKind": "terminalOnly",
                }],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_terminal": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_terminal.json", conv)],
        )

        self.assertEqual(result["branches"]["noExplicitRouteGroups"], [])
        self.assertEqual(
            result["summary"]["closedExcludedDialogLineOptionGroupCount"],
            1,
        )
        row = result["branches"]["closedExcludedDialogLineOptions"][0]
        self.assertEqual(
            row["exclusionReason"],
            "authoredNonLineOptionOutcomes",
        )
        self.assertEqual(
            row["outcomesByOption"]["option_1"][0]["terminal"],
            "openUi",
        )

    def test_partial_authored_terminal_outcomes_remain_actionable(self) -> None:
        conv = {
            "key": "dlg_m1_partial_terminal",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_partial_terminal_001",
                "options": [{"id": "option_1"}, {"id": "option_2"}],
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_partial_terminal",
                "file":
                    "export_full/source/DialogTree/dlg_m1_partial_terminal.json",
                "after": "dlg_m1_partial_terminal_001",
                "options": [{
                    "optionId": "option_1",
                    "terminal": "finish",
                    "outcomeKind": "terminalOnly",
                }],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_partial_terminal": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_partial_terminal.json", conv)],
        )

        self.assertEqual(result["branches"]["noExplicitRouteGroups"], [])
        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            1,
        )
        row = result["branches"]["actionableExcludedDialogLineOptions"][0]
        self.assertEqual(
            row["exclusionReason"],
            "incompleteAuthoredNonLineOptionOutcomes",
        )

    def test_partial_authored_outcome_closes_proven_definition_only_rows(
        self,
    ) -> None:
        conv = {
            "key": "dlg_m1_partial_definition",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_partial_definition_001",
                "options": [{"id": "option_1"}, {"id": "option_2"}],
                "_debug": {
                    "partialAuthoredOptionCoverage": {
                        "authoredOptionIds": ["option_1"],
                        "definitionOnlyOptionIds": ["option_2"],
                    },
                },
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_partial_definition",
                "file":
                    "export_full/source/DialogTree/"
                    "dlg_m1_partial_definition.json",
                "after": "dlg_m1_partial_definition_001",
                "options": [{
                    "optionId": "option_1",
                    "terminal": "finish",
                    "outcomeKind": "terminalOnly",
                }],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_partial_definition": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_partial_definition.json", conv)],
        )

        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            0,
        )
        row = result["branches"]["closedExcludedDialogLineOptions"][0]
        self.assertEqual(
            row["exclusionReason"],
            "authoredOutcomesWithDefinitionOnlyRows",
        )
        self.assertEqual(row["definitionOnlyOptionIds"], ["option_2"])
        self.assertEqual(row["coveredOptionIds"], ["option_1"])

    def test_unregistered_scene_without_authored_consumer_is_closed(
        self,
    ) -> None:
        conv = {
            "key": "dlg_m1_unregistered",
            "_debug": {
                "runtimeRegistry": {
                    "registered": False,
                    "sceneKey": "dlg_m1_unregistered",
                    "reason": "sceneKey is not present in DialogIdTable",
                },
            },
            "optionGroups": [{
                "g": 1,
                "options": [{"id": "option_1"}, {"id": "option_2"}],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_unregistered": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_unregistered.json", conv)],
        )

        self.assertEqual(result["branches"]["noExplicitRouteGroups"], [])
        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            0,
        )
        row = result["branches"]["closedExcludedDialogLineOptions"][0]
        self.assertEqual(
            row["exclusionReason"],
            "unregisteredSceneWithoutAuthoredOptionConsumer",
        )
        self.assertFalse(row["runtimeRegistry"]["registered"])

    def test_unregistered_sibling_template_risk_is_closed(self) -> None:
        conv = {
            "key": "dlg_m1_unregistered_risk",
            "_debug": {
                "runtimeRegistry": {
                    "registered": False,
                    "sceneKey": "dlg_m1_unregistered_risk",
                },
            },
            "optionGroups": [{
                "g": 1,
                "options": [{"id": "option_1"}, {"id": "option_2"}],
                "optionBranchRisk": {
                    "code": "siblingSceneTextBranches",
                    "reason": "siblingSceneTemplate",
                    "source": "siblingSceneGraphText",
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_unregistered_risk": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_unregistered_risk.json", conv)],
        )

        row = result["branches"]["closedExcludedDialogLineOptions"][0]
        self.assertEqual(
            row["exclusionReason"],
            "unregisteredSceneWithoutAuthoredOptionConsumer",
        )
        self.assertEqual(
            row["retainedRiskEvidence"]["code"],
            "siblingSceneTextBranches",
        )

    def test_definition_only_branch_lines_do_not_create_actionable_gap(
        self,
    ) -> None:
        conv = {
            "key": "dlg_m1_partial_branch",
            "optionGroups": [{
                "g": 1,
                "options": [{
                    "id": "option_1",
                    "branchLines": ["dlg_m1_partial_branch_001"],
                }, {
                    "id": "option_2",
                    "branchLines": ["dlg_m1_partial_branch_002"],
                }],
                "_debug": {
                    "partialAuthoredOptionCoverage": {
                        "authoredOptionIds": ["option_1"],
                        "definitionOnlyOptionIds": ["option_2"],
                    },
                },
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_partial_branch",
                "file": "export_full/source/DialogTree/partial.json",
                "after": "",
                "options": [{
                    "optionId": "option_1",
                    "firstLineId": "dlg_m1_partial_branch_001",
                    "pathLineIds": ["dlg_m1_partial_branch_001"],
                }],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_partial_branch": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_partial_branch.json", conv)],
        )

        self.assertEqual(
            len(result["branches"]["dialogLineOptions"]),
            1,
        )
        self.assertEqual(
            result["branches"]["closedExcludedDialogLineOptions"][0][
                "exclusionReason"
            ],
            "branchLinesForDefinitionOnlyRows",
        )
        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            0,
        )

    def test_exact_dialog_tree_option_node_layout_negatives_are_closed(
        self,
    ) -> None:
        for code, reason in (
            (
                "separateDialogTreeOptionNodes",
                "distinctAuthoredOptionNodes",
            ),
            (
                "orphanDialogTreeOptionDefinitions",
                "optionNodeHasNoOutgoingConnection",
            ),
        ):
            with self.subTest(code=code):
                conv = {
                    "key": f"dlg_m1_{code}",
                    "optionGroups": [{
                        "g": 1,
                        "options": [
                            {"id": "option_1"},
                            {"id": "option_2"},
                        ],
                        "optionBranchRisk": {
                            "code": code,
                            "reason": reason,
                            "source": "dialogTree",
                        },
                    }],
                }
                result = partial_order.build_mission_partial_order(
                    "m1",
                    {conv["key"]: "dlg"},
                    mission_payload([]),
                    [(f"conv/{conv['key']}.json", conv)],
                )

                row = result["branches"][
                    "closedExcludedDialogLineOptions"
                ][0]
                self.assertEqual(
                    row["exclusionReason"],
                    "closedDialogTreeOptionLayout",
                )
                self.assertEqual(
                    result["summary"][
                        "actionableExcludedDialogLineOptionGroupCount"
                    ],
                    0,
                )

    def test_single_option_without_route_is_not_a_missing_choice_branch(self) -> None:
        conv = {
            "key": "dlg_m1_ack",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_ack_001",
                "options": [{"id": "option_ack"}],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_ack": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_ack.json", conv)],
        )

        self.assertEqual(
            result["summary"]["singleOptionNoExplicitRouteGroupCount"],
            1,
        )
        self.assertEqual(
            result["summary"]["branchingNoExplicitRouteGroupCount"],
            0,
        )
        self.assertEqual(
            result["branches"]["singleOptionNoExplicitRouteGroups"][0][
                "storyKey"
            ],
            "dlg_m1_ack",
        )

    def test_shared_and_cosmetic_exclusions_are_closed_option_evidence(self) -> None:
        conversations = [
            ("conv/dlg_m1_shared.json", {
                "key": "dlg_m1_shared",
                "optionGroups": [{
                    "g": 1,
                    "after": "dlg_m1_shared_001",
                    "options": [{"id": "option_1"}, {"id": "option_2"}],
                    "optionBranchRisk": {
                        "code": "sharedTimelineContinuation",
                        "reason": "defaultTrunkClipContinuation",
                    },
                }],
            }),
            ("conv/dlg_m1_cosmetic.json", {
                "key": "dlg_m1_cosmetic",
                "optionGroups": [{
                    "g": 1,
                    "after": "dlg_m1_cosmetic_001",
                    "options": [{"id": "option_1"}, {"id": "option_2"}],
                    "optionBranchRisk": {
                        "code": "cosmeticChoice",
                        "reason": "treeSourcedConvergence",
                    },
                }],
            }),
            ("conv/dlg_m1_sequential.json", {
                "key": "dlg_m1_sequential",
                "optionGroups": [{
                    "g": 1,
                    "after": "dlg_m1_sequential_001",
                    "options": [{"id": "option_1"}, {"id": "option_2"}],
                    "optionBranchRisk": {
                        "code": "sequentialTimelineOptionPrompts",
                        "reason": "distinctZeroIndexTimelineSlots",
                    },
                }],
            }),
            ("conv/dlg_m1_terminal_slot.json", {
                "key": "dlg_m1_terminal_slot",
                "optionGroups": [{
                    "g": 1,
                    "after": "dlg_m1_terminal_slot_001",
                    "options": [{"id": "option_1"}, {"id": "option_2"}],
                    "optionBranchRisk": {
                        "code": "terminalTimelineOptionSlot",
                        "reason": "afterLastLocalTimelineLine",
                    },
                }],
            }),
            ("conv/dlg_m1_foreign_options.json", {
                "key": "dlg_m1_foreign_options",
                "optionGroups": [{
                    "g": 1,
                    "after": "dlg_m1_foreign_options_001",
                    "options": [{"id": "option_1"}, {"id": "option_2"}],
                    "optionBranchRisk": {
                        "code": "foreignTimelineOptionDefinitions",
                        "reason": "cinematicConsumesForeignOptionIds",
                    },
                }],
            }),
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            {
                "dlg_m1_shared": "dlg",
                "dlg_m1_cosmetic": "dlg",
                "dlg_m1_sequential": "dlg",
                "dlg_m1_terminal_slot": "dlg",
                "dlg_m1_foreign_options": "dlg",
            },
            mission_payload([]),
            conversations,
        )

        self.assertEqual(
            result["summary"]["closedExcludedDialogLineOptionGroupCount"],
            5,
        )
        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            0,
        )
        self.assertEqual(
            len(result["branches"]["closedExcludedDialogLineOptions"]),
            5,
        )

    def test_manual_option_evidence_is_never_promoted(self) -> None:
        conv = {
            "key": "dlg_m1_5",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_5_001",
                "manualOverride": {"source": "webui/overrides/options.json"},
                "options": [{"id": "option_1", "branchLines": ["dlg_m1_5_002"]}],
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_5",
                "file": "export_full/source/DialogTree/dlg_m1_5.json",
                "after": "dlg_m1_5_001",
                "options": [{"optionId": "option_1", "pathLineIds": ["dlg_m1_5_002"]}],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_5": "dlg"}, mission_payload([]), [("conv/dlg_m1_5.json", conv)]
        )

        self.assertEqual(result["branches"]["dialogLineOptions"], [])
        self.assertEqual(
            result["branches"]["excludedDialogLineOptions"][0]["exclusionReason"],
            "manualOptionEvidence",
        )


if __name__ == "__main__":
    unittest.main()
