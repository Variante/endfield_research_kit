from __future__ import annotations

import base64
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_source_story_gap_queue as gap_queue  # noqa: E402


def partial_mission(
    mission: str,
    *,
    scenes: list[str],
    isolated: list[str] | None = None,
    weak_only: list[str] | None = None,
    cycles: list[list[str]] | None = None,
    edges: list[dict] | None = None,
    no_route_groups: int = 0,
    excluded_groups: int = 0,
) -> dict:
    cycle_rows = [
        {"id": f"p{index}", "sceneKeys": values, "cyclic": True}
        for index, values in enumerate(cycles or [], start=1)
    ]
    return {
        "mission": mission,
        "summary": {
            "sceneCount": len(scenes),
            "strongEdgeCount": sum(edge.get("tier") == "strong" for edge in edges or []),
            "reducedComponentEdgeCount": 0,
            "comparableScenePairs": 0,
            "totalScenePairs": len(scenes) * (len(scenes) - 1) // 2,
            "isolatedSceneCount": len(isolated or []),
            "weakOnlySceneCount": len(weak_only or []),
            "cycleCount": len(cycle_rows),
            "questForkCount": 0,
            "questMergeCount": 0,
            "dialogLineOptionGroupCount": 0,
            "noExplicitRouteGroupCount": no_route_groups,
            "excludedDialogLineOptionGroupCount": excluded_groups,
        },
        "nodes": [
            {
                "key": key,
                "kind": "dlg",
                "relationStatus": "isolated" if key in (isolated or []) else "source-ordered",
            }
            for key in scenes
        ],
        "directEdges": edges or [],
        "cycles": cycle_rows,
        "isolatedSceneKeys": isolated or [],
        "weakOnlySceneKeys": weak_only or [],
        "unresolvedSourceNodes": [],
    }


def mission_payload(
    *,
    quest_ids: list[str] | None = None,
    contexts: list[dict] | None = None,
    sequences: list[dict] | None = None,
    connections: list[dict] | None = None,
    placements: dict | None = None,
) -> dict:
    return {
        "flow": {
            "missionStoryConnections": connections or [],
        },
        "timelineRecovery": {
            "quests": [{"questId": quest_id} for quest_id in quest_ids or []],
            "sourceBackedStoryCallContexts": contexts or [],
            "sourceBackedSceneSequences": sequences or [],
            "scenePlacement": placements or {},
            "unresolved": [],
        }
    }


class SourceStoryGapQueueTests(unittest.TestCase):
    def test_radio_definition_validator_reports_exact_audio_failure(self) -> None:
        row = {
            "continueAfterDialog": False,
            "continueAfterRadio": False,
            "priority": 3,
            "radioSingleDataList": [{
                "audioOverride": "au_radio_fixture_001",
            }],
            "radioType": 0,
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS,
            {"radio_fixture": frozenset()},
            clear=True,
        ):
            failure = gap_queue._offline_radio_definition_validation_failure(
                "radio_fixture",
                row,
                set(),
            )

        self.assertEqual(failure["validator"], "offlineRadioDefinition")
        self.assertEqual(failure["gate"], "exactAudioDialogMembership")
        self.assertEqual(failure["storyKey"], "radio_fixture")
        self.assertEqual(
            failure["actual"]["baseAbsentAudioIds"],
            ["au_radio_fixture_001"],
        )

    def test_a1m8d3_dialog_declares_exact_missing_audio_surface(self) -> None:
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_a1m8d3_2"
        ]
        self.assertEqual(
            definition["missingAudioIds"],
            tuple(
                f"au_dlg_a1m8d3_2_{number:03d}"
                for number in range(2, 20)
            ),
        )

    def test_option_frontier_scores_only_multi_choice_and_actionable_exclusions(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["dlg_a"],
            no_route_groups=5,
            excluded_groups=4,
        )
        partial["summary"].update({
            "branchingNoExplicitRouteGroupCount": 2,
            "singleOptionNoExplicitRouteGroupCount": 3,
            "actionableExcludedDialogLineOptionGroupCount": 1,
            "closedExcludedDialogLineOptionGroupCount": 3,
        })

        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["noExplicitOptionRouteGroups"], 5)
        self.assertEqual(
            row["metrics"]["actionableNoExplicitOptionRouteGroups"],
            2,
        )
        self.assertEqual(
            row["metrics"]["singleOptionNoExplicitRouteGroups"],
            3,
        )
        self.assertEqual(row["metrics"]["excludedOptionEvidenceGroups"], 4)
        self.assertEqual(
            row["metrics"]["actionableExcludedOptionEvidenceGroups"],
            1,
        )
        self.assertEqual(
            row["metrics"]["closedExcludedOptionEvidenceGroups"],
            3,
        )
        self.assertEqual(
            row["scoreContributions"][
                "actionableNoExplicitOptionRouteGroups"
            ],
            4,
        )
        self.assertEqual(
            row["scoreContributions"][
                "actionableExcludedOptionEvidenceGroups"
            ],
            2,
        )
        self.assertEqual(
            row["frontierContributions"]["dialog-option-runtime"],
            6,
        )

    def test_main_story_sorts_before_higher_scoring_event(self) -> None:
        main = partial_mission("e1m1", scenes=["a"], isolated=["a"])
        event = partial_mission("a1m1", scenes=["a", "b", "c"], isolated=["a", "b", "c"])
        report = gap_queue.build_gap_report(
            {"_schema": "partial", "language": "CN", "missions": [event, main]},
            {"e1m1": mission_payload(), "a1m1": mission_payload()},
            {"e1m1", "a1m1"},
        )

        self.assertEqual([row["mission"] for row in report["missions"]], ["e1m1", "a1m1"])
        self.assertEqual(report["missions"][0]["bucket"], "main")

    def test_untyped_multiscene_context_is_ranked(self) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a", "dlg_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "LevelScriptData/a.json",
                "levelId": "lv1",
                "sceneKeys": ["dlg_a", "dlg_b"],
            }],
        )

        row = gap_queue.build_gap_row(partial, payload, mission_bundle_exists=True)

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 1)
        self.assertEqual(row["scoreContributions"]["untypedMultiSceneLevelscriptContexts"], 10)
        self.assertIn("levelscript-control-flow", row["activeFrontiers"])

    def test_fully_typed_context_is_not_a_gap(self) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a", "dlg_b"])
        payload = mission_payload(
            contexts=[{"sourceFile": "a.json", "sceneKeys": ["dlg_a", "dlg_b"]}],
            sequences=[{"sourceFile": "a.json", "sceneKeys": ["dlg_a", "dlg_b"]}],
            connections=[
                {
                    "key": key,
                    "levelScriptOccurrences": [{
                        "sourceFile": "a.json",
                        "actionMapRole": f"actionList#{index} linked",
                        "actionName": "StartDialogAction",
                        "recordClass": "play_dialog",
                    }],
                }
                for index, key in enumerate(("dlg_a", "dlg_b"), start=1)
            ],
        )

        row = gap_queue.build_gap_row(partial, payload, mission_bundle_exists=True)

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 0)

    def test_exact_native_weak_only_scene_is_closed_not_actionable(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["radio_a"],
            weak_only=["radio_a"],
        )
        payload = mission_payload(connections=[{
            "key": "radio_a",
            "levelScriptOccurrences": [{
                "levelId": "lv1",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "actionMapRole": "actionList#1 linked",
                "actionName": "PlayRadio",
                "recordClass": "play_radio",
                "localId": 6,
                "allStoryKeysInRecord": ["radio_a"],
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "headerLocalId": 4,
                    "eventDetail": {
                        "summary": "leader enters trigger slot 80001",
                    },
                    "path": [
                        {"localId": 5},
                        {"localId": 6},
                    ],
                }],
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["weakOnlyScenes"], 1)
        self.assertEqual(row["metrics"]["actionableWeakOnlyScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactNativeWeakOnlyScenes"],
            1,
        )
        self.assertEqual(row["scoreContributions"]["actionableWeakOnlyScenes"], 0)
        self.assertEqual(
            row["closedExactNativeWeakOnlyScenes"][0]["recoveryStatus"],
            "closed_exact_native_event_path_no_relative_order",
        )

    def test_equivalent_duplicate_native_path_is_closed_not_actionable(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["radio_a"],
            weak_only=["radio_a"],
        )
        payload = mission_payload(connections=[{
            "key": "radio_a",
            "levelScriptOccurrences": [{
                "levelId": "lv1",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "actionMapRole": "actionList#3 linked",
                "actionName": "Play3DRadio",
                "recordClass": "play_radio",
                "localId": 8,
                "allStoryKeysInRecord": ["radio_a"],
                "nativeEventOwners": [{
                    "status":
                        "exact_serialized_control_path_equivalent_duplicates",
                    "headerName": "ScriptEvent_OnScriptStageChanged",
                    "headerLocalId": 4,
                    "eventDetail": {
                        "summary": "local LevelScript stage changes to 2",
                    },
                    "path": [
                        {
                            "localId": 7,
                            "equivalentRecordOffsets": [100, 200],
                        },
                        {"localId": 8},
                    ],
                }],
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableWeakOnlyScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactNativeWeakOnlyScenes"],
            1,
        )
        self.assertEqual(
            row["closedExactNativeWeakOnlyScenes"][0]["nativeEventPaths"][0][
                "controlPathStatus"
            ],
            "exact_serialized_control_path_equivalent_duplicates",
        )

    def test_incomplete_native_weak_only_scene_remains_actionable(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["radio_a"],
            weak_only=["radio_a"],
        )
        payload = mission_payload(connections=[{
            "key": "radio_a",
            "levelScriptOccurrences": [{
                "levelId": "lv1",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "actionMapRole": "actionList#1 linked",
                "actionName": "PlayRadio",
                "recordClass": "play_radio",
                "localId": 6,
                "allStoryKeysInRecord": ["radio_a"],
                "nativeEventOwners": [{
                    "status": "unresolved_native_event_owner",
                    "headerLocalId": 4,
                    "path": [{"localId": 6}],
                }],
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableWeakOnlyScenes"], 1)
        self.assertEqual(
            row["metrics"]["closedExactNativeWeakOnlyScenes"],
            0,
        )
        self.assertEqual(
            row["scoreContributions"]["actionableWeakOnlyScenes"],
            4,
        )

    def test_weak_topology_without_action_record_is_not_control_flow_gap(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["dlg_a", "dlg_b"],
            weak_only=["dlg_a"],
            edges=[{
                "from": "dlg_a",
                "to": "dlg_b",
                "kind": "levelscriptFileOrder",
                "tier": "weak",
                "sourceFiles": ["LevelScriptData/lv1/1001.json"],
            }],
        )

        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableWeakOnlyScenes"], 0)
        self.assertEqual(row["metrics"]["nonActionableWeakOnlyScenes"], 1)
        self.assertEqual(
            row["nonActionableWeakOnlySceneKeys"],
            ["dlg_a"],
        )

    def test_weak_only_stop_radio_is_not_a_playback_decoder_gap(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["radio_a", "cutscene_b"],
            weak_only=["radio_a"],
            edges=[{
                "from": "radio_a",
                "to": "cutscene_b",
                "kind": "levelscriptFileOrder",
                "tier": "weak",
                "sourceFiles": ["LevelScriptData/lv1/1001.json"],
            }],
        )
        action_story_occurrences = {
            "radio_a": [{
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "actionMapRole": "actionList#2 root",
                "actionCode": "0x04b5",
                "actionKind": "0x09",
                "localId": 10,
            }],
        }

        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            action_story_occurrences=action_story_occurrences,
        )

        self.assertEqual(row["metrics"]["actionableWeakOnlyScenes"], 0)
        self.assertEqual(row["metrics"]["nonActionableWeakOnlyScenes"], 1)
        self.assertEqual(row["nonActionableWeakOnlySceneKeys"], ["radio_a"])

    def test_native_index_closes_exact_stub_weak_scene(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["cutscene_a", "dlg_b"],
            weak_only=["cutscene_a"],
            edges=[{
                "from": "cutscene_a",
                "to": "dlg_b",
                "kind": "levelscriptFileOrder",
                "tier": "weak",
                "sourceFiles": ["LevelScriptData/lv1/1001.json"],
            }],
        )
        owner = {
            "status": "exact_serialized_control_path",
            "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
            "headerLocalId": 4,
            "path": [{"localId": 5}],
        }
        payload = mission_payload(connections=[{
            "key": "cutscene_a",
            "levelScriptOccurrences": [{
                "levelId": "lv1",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "nativeEventOwners": [owner],
            }],
        }])
        native_playback_index = {
            "cutscene_a": [{
                "levelId": "lv1",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "actionMapRole": "actionList#1 root",
                "actionName": "PlayCutsceneAction",
                "recordClass": "play_cutscene",
                "localId": 5,
                "allStoryKeysInRecord": ["cutscene_a"],
                "nativeEventOwners": [owner],
            }],
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            native_playback_index=native_playback_index,
        )

        self.assertEqual(row["metrics"]["actionableWeakOnlyScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactNativeWeakOnlyScenes"],
            1,
        )

    def test_unlinked_exact_native_playback_still_counts_as_typed(self) -> None:
        partial = partial_mission("e1m1", scenes=["radio_a", "radio_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "LevelScriptData/a.json",
                "sceneKeys": ["radio_a", "radio_b"],
            }],
        )
        payload["flow"]["unlinkedNativePlayback"] = [
            {
                "key": key,
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "occurrences": [{
                    "sourceFile": "LevelScriptData/a.json",
                    "actionMapRole": f"actionList#{index} linked",
                    "actionName": "Play3DRadio",
                    "recordClass": "play_radio",
                }],
            }
            for index, key in enumerate(("radio_a", "radio_b"), start=1)
        ]

        row = gap_queue.build_gap_row(partial, payload, mission_bundle_exists=True)

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 0)

    def test_binary_playback_index_closes_omitted_redundant_native_rows(
        self,
    ) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a", "radio_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "LevelScriptData/a.json",
                "sceneKeys": ["dlg_a", "radio_b"],
            }],
            connections=[
                {
                    "key": key,
                    "relation": "levelscript_condition_scope",
                    "confidence": "scoped_script",
                }
                for key in ("dlg_a", "radio_b")
            ],
        )
        native_playback_index = {
            key: [{
                "sourceFile": "LevelScriptData/a.json",
                "actionMapRole": f"actionList#{index} linked",
                "actionName": action,
                "recordClass": record_class,
                "allStoryKeysInRecord": [key],
                "nativeMappingId": "gameassembly-test-actionbase",
            }]
            for index, (key, action, record_class) in enumerate((
                ("dlg_a", "StartDialogAction", "play_dialog"),
                ("radio_b", "PlayRadio", "play_radio"),
            ), start=1)
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            native_playback_index=native_playback_index,
        )

        self.assertEqual(
            row["metrics"]["untypedMultiSceneLevelscriptContexts"],
            0,
        )

    def test_binary_playback_index_fails_closed_without_exact_identity(
        self,
    ) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a", "radio_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "LevelScriptData/a.json",
                "sceneKeys": ["dlg_a", "radio_b"],
            }],
        )
        native_playback_index = {
            "dlg_a": [{
                "sourceFile": "LevelScriptData/a.json",
                "actionMapRole": "actionList#1 linked",
                "actionName": "StartDialogAction",
                "recordClass": "play_dialog",
                "allStoryKeysInRecord": ["different_key"],
                "nativeMappingId": "gameassembly-test-actionbase",
            }],
            "radio_b": [{
                "sourceFile": "LevelScriptData/a.json",
                "actionMapRole": "actionList#2 linked",
                "actionName": "PlayRadio",
                "recordClass": "play_radio",
                "allStoryKeysInRecord": ["radio_b"],
                "nativeMappingId": "manual-test-mapping",
            }],
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            native_playback_index=native_playback_index,
        )

        self.assertEqual(
            row["metrics"]["untypedMultiSceneLevelscriptContexts"],
            1,
        )

    def test_generic_scene_sequence_and_preload_do_not_count_as_typed_playback(self) -> None:
        partial = partial_mission("e1m1", scenes=["cutscene_a", "dlg_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "a.json",
                "sceneKeys": ["cutscene_a", "dlg_b"],
            }],
            sequences=[{
                "sourceFile": "a.json",
                "sceneKeys": ["cutscene_a", "dlg_b"],
            }],
            connections=[{
                "key": "cutscene_a",
                "levelScriptOccurrences": [{
                    "sourceFile": "a.json",
                    "actionMapRole": "actionList#1 root",
                    "actionName": "PreloadCutsceneAction",
                    "recordClass": "preload_cutscene",
                }],
            }],
        )

        row = gap_queue.build_gap_row(partial, payload, mission_bundle_exists=True)

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 1)
        self.assertEqual(
            row["untypedMultiSceneLevelscriptContexts"][0]["unresolvedSceneKeys"],
            ["cutscene_a", "dlg_b"],
        )

    def test_exact_non_playback_and_non_action_references_are_closed_negatives(
        self,
    ) -> None:
        partial = partial_mission("e1m1", scenes=["cutscene_a", "dlg_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "a.json",
                "sceneKeys": ["cutscene_a", "dlg_b"],
            }],
            connections=[{
                "key": "cutscene_a",
                "levelScriptOccurrences": [{
                    "sourceFile": "a.json",
                    "actionMapRole": "actionList#1 root",
                    "actionName": "PreloadCutsceneAction",
                    "recordClass": "preload_cutscene",
                }],
            }],
        )
        action_story_occurrences = {
            "cutscene_a": [{
                "sourceFile": "a.json",
                "actionMapRole": "actionList#1 root",
                "actionCode": "0x0376",
                "actionKind": "0x0c",
                "actionName": "PreloadCutsceneAction",
                "recordClass": "preload_cutscene",
                "nativeMappingId": "gameassembly-test-actionbase",
            }],
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            action_story_occurrences=action_story_occurrences,
        )

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 0)
        self.assertEqual(row["metrics"]["closedNonPlaybackLevelscriptContexts"], 1)
        classifications = row["closedNonPlaybackLevelscriptContexts"][0][
            "unresolvedBinaryClassifications"
        ]
        self.assertEqual(
            [item["status"] for item in classifications],
            [
                "known_non_playback_action_only",
                "non_action_story_reference",
            ],
        )

    def test_formatter_mapped_override_is_not_an_actionable_playback_gap(
        self,
    ) -> None:
        partial = partial_mission("a1m1", scenes=["dlg_a", "radio_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "a.json",
                "sceneKeys": ["dlg_a", "radio_b"],
            }],
            connections=[{
                "key": "radio_b",
                "levelScriptOccurrences": [{
                    "sourceFile": "a.json",
                    "actionMapRole": "actionList#2 root",
                    "actionName": "PlayRadio",
                    "recordClass": "play_radio",
                }],
            }],
        )
        action_story_occurrences = {
            "dlg_a": [{
                "sourceFile": "a.json",
                "actionMapRole": "actionList#1 root",
                "actionCode": "0x0344",
                "actionKind": "0x0a",
                "localId": 4,
            }],
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            action_story_occurrences=action_story_occurrences,
        )

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 0)
        evidence = row["closedNonPlaybackLevelscriptContexts"][0][
            "unresolvedBinaryClassifications"
        ][0]["actionOccurrences"][0]
        self.assertEqual(evidence["actionName"], "OverrideNPCDialog")
        self.assertEqual(evidence["recordClass"], "override_dialog")
        self.assertTrue(evidence["nativeMappingId"].startswith("gameassembly-"))

    def test_unmapped_action_record_remains_actionable(self) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a", "radio_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "a.json",
                "sceneKeys": ["dlg_a", "radio_b"],
            }],
            connections=[{
                "key": "radio_b",
                "levelScriptOccurrences": [{
                    "sourceFile": "a.json",
                    "actionMapRole": "actionList#2 root",
                    "actionName": "PlayRadio",
                    "recordClass": "play_radio",
                }],
            }],
        )
        action_story_occurrences = {
            "dlg_a": [{
                "sourceFile": "a.json",
                "actionMapRole": "actionList#1 root",
                "actionCode": "0x0123",
                "actionKind": "0x09",
            }],
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            action_story_occurrences=action_story_occurrences,
        )

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 1)
        classification = row["untypedMultiSceneLevelscriptContexts"][0][
            "unresolvedBinaryClassifications"
        ][0]
        self.assertEqual(classification["status"], "unmapped_action_record")

    def test_exact_connection_level_native_path_counts_as_typed_playback(self) -> None:
        partial = partial_mission("e1m1", scenes=["cutscene_a", "radio_b"])
        payload = mission_payload(
            contexts=[{
                "sourceFile": "LevelScriptData/a.json",
                "sceneKeys": ["cutscene_a", "radio_b"],
            }],
            connections=[
                {
                    "key": key,
                    "sourceFiles": [
                        "LevelScriptData/a.json",
                        "MissionRuntimeAsset/e1m1.json",
                    ],
                    "nativeActions": [action],
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "path": [{
                            "actionName": action,
                            "recordClass": record_class,
                        }],
                    }],
                }
                for key, action, record_class in (
                    ("cutscene_a", "PlayCutsceneAction", "play_cutscene"),
                    ("radio_b", "PlayRadio", "play_radio"),
                )
            ],
        )

        row = gap_queue.build_gap_row(partial, payload, mission_bundle_exists=True)

        self.assertEqual(row["metrics"]["untypedMultiSceneLevelscriptContexts"], 0)

    def test_quest_attachment_requires_strong_story_edge(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["dlg_a", "dlg_b"],
            edges=[
                {"from": "dlg_a", "to": "dlg_b", "tier": "strong", "questIds": ["e1m1_q#1"]},
                {"from": "dlg_b", "to": "dlg_a", "tier": "weak", "questIds": ["e1m1_q#2"]},
            ],
        )
        payload = mission_payload(
            quest_ids=["e1m1_q#1", "e1m1_q#2"],
            placements={
                "dlg_b": {
                    "sceneKey": "dlg_b",
                    "questIds": ["e1m1_q#2"],
                    "questAttachSources": [{"source": "scriptCondition"}],
                }
            },
        )

        row = gap_queue.build_gap_row(partial, payload, mission_bundle_exists=True)

        self.assertEqual(row["metrics"]["strictQuestIdsWithStoryAttachment"], 1)
        self.assertEqual(row["questIdsWithoutStrictStoryAttachment"], ["e1m1_q#2"])

    def test_validated_non_owning_quest_diagnostic_is_not_actionable(self) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a"])
        payload = mission_payload(
            quest_ids=["e1m1_q#2"],
            placements={
                "dlg_a": {
                    "sceneKey": "dlg_a",
                    "questIds": ["e1m1_q#2"],
                    "questAttachSources": [{
                        "questId": "e1m1_q#2",
                        "source": "variantMissionRuntime",
                    }],
                },
            },
        )
        closure = {
            "questId": "e1m1_q#2",
            "missionId": "e1m1",
            "recoveryStatus": "closed_fixture_non_owning_diagnostic",
            "graphEffect": "none",
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            quest_attachment_diagnostic_index={"e1m1_q#2": closure},
        )

        self.assertEqual(row["questIdsWithoutStrictStoryAttachment"], [])
        self.assertEqual(row["closedQuestAttachmentDiagnostics"], [closure])
        self.assertEqual(row["metrics"]["closedQuestAttachmentDiagnostics"], 1)
        self.assertEqual(
            row["scoreContributions"]["questIdsWithoutStrictStoryAttachment"],
            0,
        )

    def test_npc_proxy_dialog_context_is_not_actionable_quest_attachment(
        self,
    ) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a"])
        payload = mission_payload(
            quest_ids=["e1m1_q#2"],
            placements={
                "dlg_a": {
                    "sceneKey": "dlg_a",
                    "questIds": ["e1m1_q#2"],
                    "questAttachSources": [{
                        "questId": "e1m1_q#2",
                        "source": "npcProxyDialog",
                        "npcProxyId": "npc_e1m1_wait",
                        "dialogId": "dlg_a",
                    }],
                },
            },
        )

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(
            row["questIdsWithoutStrictStoryAttachment"],
            [],
        )
        self.assertEqual(
            row["questIdsWithoutAnyStoryEvidence"],
            ["e1m1_q#2"],
        )
        self.assertEqual(row["diagnosticQuestAttachmentSources"], {})

    def test_unique_objective_script_owner_is_strict_quest_attachment(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["cutscene_a"],
            isolated=["cutscene_a"],
        )
        payload = mission_payload(
            quest_ids=["e1m1_q#1"],
            placements={
                "cutscene_a": {
                    "sceneKey": "cutscene_a",
                    "questIds": ["e1m1_q#1"],
                    "questAttachSources": [{"source": "scriptCondition"}],
                },
            },
            connections=[{
                "key": "cutscene_a",
                "relation": "levelscript_mission_context",
                "confidence": "scoped_script",
                "hasUnscopedOrOtherMissionOccurrences": False,
                "scopeEvidenceKinds": ["mission_condition_checks_script"],
                "levelScriptOccurrences": [{
                    "scopeEvidenceKinds": [
                        "mission_condition_checks_script",
                    ],
                    "missionConditions": [{
                        "missionId": "e1m1",
                        "questId": "e1m1_q#1",
                    }],
                }],
            }],
        )

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["strictQuestIdsWithStoryAttachment"], 1)
        self.assertEqual(row["questIdsWithoutStrictStoryAttachment"], [])

    def test_exact_dialog_finish_dependency_is_strict_quest_attachment(
        self,
    ) -> None:
        partial = partial_mission("e7m4", scenes=["dlg_e7m4_4"])
        payload = mission_payload(quest_ids=["e7m4_q#2"])
        payload["flow"]["quests"] = [{
            "id": "e7m4_q#2",
            "storyConnections": [{
                "key": "dlg_e7m4_4",
                "kind": "dialog",
                "relation": "objective_condition",
                "direction": "story_to_quest",
                "phase": "progress",
                "confidence": "direct",
                "source": (
                    "MissionRuntimeAsset.questDic[*].objectiveList[0]"
                    ".condition._dialogId"
                ),
                "objectiveIndex": 1,
                "conditionType": "CheckTalkOptionFinish",
                "finishId": 1,
            }],
        }]
        payload["timelineRecovery"]["scenePlacement"] = {
            "dlg_e7m4_4": {
                "sceneKey": "dlg_e7m4_4",
                "questIds": ["e7m4_q#2"],
                "questAttachSources": [{"source": "missionStoryRef"}],
            },
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["strictQuestIdsWithStoryAttachment"], 1)
        self.assertEqual(row["questIdsWithoutStrictStoryAttachment"], [])

        payload["flow"]["quests"][0]["storyConnections"][0][
            "source"
        ] = "derived dialog completion"
        invalid = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(
            invalid["questIdsWithoutStrictStoryAttachment"],
            ["e7m4_q#2"],
        )

    def test_exact_sns_tracking_reference_is_strict_attachment_only(
        self,
    ) -> None:
        partial = partial_mission("e2m1", scenes=["sns_e2m1_1"])
        payload = mission_payload(
            quest_ids=["e2m1_q#1"],
            placements={
                "sns_e2m1_1": {
                    "sceneKey": "sns_e2m1_1",
                    "questIds": ["e2m1_q#1"],
                    "questAttachSources": [{
                        "questId": "e2m1_q#1",
                        "source": "missionStoryRef",
                    }],
                },
            },
        )
        payload["flow"]["quests"] = [{
            "id": "e2m1_q#1",
            "storyConnections": [{
                "key": "sns_e2m1_1",
                "kind": "sns",
                "relation": "objective_tracking_story_reference",
                "direction": "context",
                "phase": "tracking",
                "confidence": "native_typed_context",
                "source": (
                    "MissionRuntimeAsset.questDic[*].objectiveList[0]"
                    ".trackingInfoList[0].snsDialogId"
                ),
                "objectiveIndex": 1,
                "trackingIndex": 0,
                "trackingType": "SnsTrackingInfo",
                "playback": False,
            }],
        }]

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["strictQuestIdsWithStoryAttachment"], 1)
        self.assertEqual(row["questIdsWithoutStrictStoryAttachment"], [])

        payload["flow"]["quests"][0]["storyConnections"][0]["playback"] = True
        invalid = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(
            invalid["questIdsWithoutStrictStoryAttachment"],
            ["e2m1_q#1"],
        )

    def test_missing_bundle_is_explicit_high_priority_gap(self) -> None:
        partial = partial_mission("e1m1", scenes=["dlg_a"])

        row = gap_queue.build_gap_row(partial, None, mission_bundle_exists=False)

        self.assertEqual(row["metrics"]["missingMissionBundle"], 1)
        self.assertEqual(row["scoreContributions"]["missingMissionBundle"], 100)
        self.assertEqual(row["primaryFrontier"], "missing-mission-runtime-bundle")

    def test_ambient_and_video_isolation_do_not_inflate_core_score(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["dlg_a", "env_a", "video_a"],
            isolated=["dlg_a", "env_a", "video_a"],
        )
        for node in partial["nodes"]:
            node["kind"] = {
                "dlg_a": "dlg",
                "env_a": "env",
                "video_a": "video",
            }[node["key"]]

        row = gap_queue.build_gap_row(partial, mission_payload(), mission_bundle_exists=True)

        self.assertEqual(row["metrics"]["isolatedScenes"], 3)
        self.assertEqual(row["metrics"]["coreIsolatedScenes"], 1)
        self.assertEqual(
            row["scoreContributions"]["actionableCoreIsolatedScenes"],
            5,
        )

    def test_exact_native_isolated_scene_is_closed_not_source_link_gap(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["radio_a"],
            isolated=["radio_a"],
        )
        payload = mission_payload(connections=[{
            "key": "radio_a",
            "levelScriptOccurrences": [{
                "levelId": "lv1",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "actionMapRole": "actionList#1 root",
                "actionName": "PlayRadio",
                "recordClass": "play_radio",
                "localId": 6,
                "allStoryKeysInRecord": ["radio_a"],
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "LevelEvent_OnEncounterActivated",
                    "headerLocalId": 4,
                    "path": [{"localId": 5}, {"localId": 6}],
                }],
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["coreIsolatedScenes"], 1)
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactNativeIsolatedScenes"],
            1,
        )
        self.assertEqual(
            row["scoreContributions"]["actionableCoreIsolatedScenes"],
            0,
        )

    def test_compact_top_level_native_path_closes_exact_isolated_scene(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["dlg_a"],
            isolated=["dlg_a"],
        )
        payload = mission_payload(connections=[{
            "key": "dlg_a",
            "levelIds": ["lv1"],
            "scriptIds": ["1001"],
            "sourceFiles": [
                "MissionRuntimeAsset/e1m1.json",
                "LevelScriptData/lv1/1001.json",
            ],
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "headerLocalId": 4,
                "path": [{
                    "localId": 5,
                    "actionName": "StartDialogAndTeleportAction",
                    "recordClass": "play_dialog",
                    "texts": ["teleport_id", "dlg_a"],
                }],
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(row["metrics"]["closedExactNativeIsolatedScenes"], 1)
        self.assertEqual(
            row["closedExactNativeIsolatedScenes"][0]["nativeEventPaths"][0][
                "actionName"
            ],
            "StartDialogAndTeleportAction",
        )

    def test_timeline_embedded_black_with_exact_parent_path_is_closed(
        self,
    ) -> None:
        partial = partial_mission(
            "e10m4",
            scenes=["black_e10m4_1"],
            isolated=["black_e10m4_1"],
        )
        payload = mission_payload(connections=[{
            "key": "black_e10m4_1",
            "relation": "timeline_dialog_contains_black",
            "confidence": "native_exact_host",
            "storyOwnerMission": "e10m4",
            "parentStoryKey": "dlg_e10m4_5",
            "occurrenceCount": 1,
            "textIds": ["black_e10m4_1_001"],
            "timelines": ["dlgtl_e10m4_5_sub_1"],
            "sourceFiles": ["CAB-story"],
            "timelineAttachments": [{
                "key": "black_e10m4_1",
                "textId": "black_e10m4_1_001",
                "dialogKey": "dlg_e10m4_5",
                "timeline": "dlgtl_e10m4_5_sub_1",
                "sourceFile": "CAB-story",
                "dialogJoin": "dialog_id_table_used_timeline",
                "assetPath": "center_text.json",
                "trackPath": "trunk_track.json",
                "rootPath": "timeline_root.json",
            }],
            "parentDialogNativeOccurrences": [{
                "levelId": "dungeon",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/dungeon/1001.json",
                "actionName": "StartDialogAndTeleportAction",
                "recordClass": "play_dialog",
                "localId": 8,
                "allStoryKeysInRecord": ["dlg_e10m4_5"],
                "levelDataHosts": [{
                    "missionId": "e10m4d5",
                    "levelDataFile": "LevelData/dungeon/e10m4d5.json",
                }],
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "headerLocalId": 6,
                    "path": [{"localId": 7}, {"localId": 8}],
                }],
            }],
        }])
        payload["flow"]["_sourceVariantMissionIds"] = ["e10m4d5"]

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(row["metrics"]["closedExactNativeIsolatedScenes"], 1)
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_native_timeline_embedded_playback_context_"
            "no_file_order",
        )
        self.assertEqual(closure["graphEffect"], "none")

    def test_timeline_foreign_dialog_with_exact_parent_path_is_closed(
        self,
    ) -> None:
        partial = partial_mission(
            "e11m3",
            scenes=["dlg_e11m3_16"],
            isolated=["dlg_e11m3_16"],
        )
        payload = mission_payload(connections=[{
            "key": "dlg_e11m3_16",
            "relation": "timeline_dialog_contains_foreign_dialog",
            "confidence": "native_exact_host",
            "storyOwnerMission": "e11m3",
            "parentStoryKey": "dlg_e11m3_7",
            "occurrenceCount": 1,
            "textIds": [
                "dlg_e11m3_16_001",
                "dlg_e11m3_16_002",
            ],
            "optionIds": [
                "option_dlg_e11m3_16_1_001",
                "option_dlg_e11m3_16_1_002",
            ],
            "timelines": ["dlgtl_e11m3_7_sub_1"],
            "sourceFiles": ["CAB-story"],
            "graphEffect": "none",
            "timelineDialogContainments": [{
                "key": "dlg_e11m3_16",
                "rawDialogKey": "dlg_e11m3_16",
                "dialogKey": "dlg_e11m3_7",
                "timeline": "dlgtl_e11m3_7_sub_1",
                "sourceFile": "CAB-story",
                "lineIds": [
                    "dlg_e11m3_16_001",
                    "dlg_e11m3_16_002",
                ],
                "optionIds": [
                    "option_dlg_e11m3_16_1_001",
                    "option_dlg_e11m3_16_1_002",
                ],
                "beforeParentLineId": "dlg_e11m3_7_009",
                "afterParentLineId": "dlg_e11m3_7_005",
                "dialogJoin": "dialog_id_table_used_timeline",
                "placementStatus":
                    "exact_contiguous_foreign_dialog_lines_"
                    "with_parent_on_both_sides",
                "graphEffect": "none",
            }],
            "parentDialogNativeOccurrences": [{
                "levelId": "map02_lv008",
                "scriptId": "23100080005",
                "sourceFile":
                    "LevelScriptData/map02_lv008/23100080005.json",
                "actionName": "StartDialogAndTeleportAction",
                "recordClass": "play_dialog",
                "localId": 5,
                "allStoryKeysInRecord": ["dlg_e11m3_7"],
                "levelDataHosts": [{
                    "missionId": "e11m3",
                    "levelDataFile": "LevelData/e11m3.json",
                }],
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName":
                        "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "headerLocalId": 4,
                    "path": [{"localId": 5}],
                }],
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(row["metrics"]["closedExactNativeIsolatedScenes"], 1)
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_native_timeline_foreign_dialog_playback_"
            "context_no_file_order",
        )
        self.assertEqual(
            closure["beforeParentLineIds"],
            ["dlg_e11m3_7_009"],
        )
        self.assertEqual(closure["graphEffect"], "none")

    def test_exact_npc_proxy_runtime_config_is_closed_without_order(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["dlg_a"],
            isolated=["dlg_a"],
        )
        payload = mission_payload(connections=[{
            "key": "dlg_a",
            "relation": "npc_proxy_ex_mission_context",
            "confidence": "direct_mission_scope",
            "source": "NpcProxyExDataTable.data[*].missionId + dialogId",
            "npcProxyId": "npc_proxy_a",
            "npcProxyMissionId": "e1m1",
            "storyOwnerMission": "e1m1",
            "selectionOrderStatus": (
                "one_based_active_row_selection_only_no_cross_row_chronology"
            ),
            "nativeMappingId": "npc-proxy-dialog-selection-native-v1",
            "gameAssemblySha256": (
                "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2"
                "B983FB9D45677D80FFCE"
            ),
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["coreIsolatedScenes"], 1)
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            1,
        )
        self.assertEqual(
            row["closedExactRuntimeConfigIsolatedScenes"][0][
                "recoveryStatus"
            ],
            "closed_exact_runtime_config_no_relative_order",
        )
        self.assertEqual(
            row["scoreContributions"]["actionableCoreIsolatedScenes"],
            0,
        )

    def test_unique_mission_tracked_proxy_bundle_closes_without_order(
        self,
    ) -> None:
        declaration = gap_queue.UNIQUE_MISSION_TRACKED_PROXY_CONTEXTS[
            "gm01m14"
        ]
        story_key = "dlg_gm01m14_2"
        connection = {
            "key": story_key,
            "relation":
                "unique_mission_tracked_npc_proxy_dialog_context",
            "direction": "context",
            "phase": "server_selected_proxy_state",
            "confidence": "native_exact_mission_context",
            "evidenceTier": "derived_exact_mission",
            "storyOwnerMission": "gm01m14",
            "npcProxyId": declaration["npcProxyId"],
            "levelIds": [declaration["levelId"]],
            "candidateQuestIds": list(declaration["questIds"]),
            "activeRowIndex": 2,
            "configuredDialogIds": list(declaration["dialogIds"]),
            "questTriggerStatus": (
                "shared_tracked_proxy_state_context_not_quest_selection_"
                "or_playback"
            ),
            "selectionOrderStatus": (
                "one_based_active_row_selection_only_no_cross_row_chronology"
            ),
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "serverExchange": True,
            "clientRequest": False,
            "expectedClientReply": False,
            "sourceFiles": list(declaration["sourceHashes"]),
            "npcProxyTableRow": {
                "proxyId": declaration["npcProxyId"],
                "levelId": declaration["levelId"],
                "subDataParentId": declaration["subDataParentId"],
            },
            "npcProxyExRows": [
                {"missionId": "", "dialogId": dialog_id}
                for dialog_id in declaration["exDialogIds"]
            ],
            "nativeMappingId": "npc-proxy-dialog-selection-native-v1",
            "gameAssemblySha256": (
                "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2"
                "B983FB9D45677D80FFCE"
            ),
        }
        partial = partial_mission(
            "gm01m14",
            scenes=[story_key],
            isolated=[story_key],
        )

        row = gap_queue.build_gap_row(
            partial,
            mission_payload(connections=[connection]),
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            closure["relation"],
            "unique_mission_tracked_npc_proxy_dialog_context",
        )
        self.assertEqual(closure["candidateQuestIds"], list(
            declaration["questIds"]
        ))
        self.assertIn("do not order", closure["orderBoundary"])

        invalid = dict(connection)
        invalid["activeRowIndex"] = 3
        reopened = gap_queue.build_gap_row(
            partial,
            mission_payload(connections=[invalid]),
            mission_bundle_exists=True,
        )
        self.assertEqual(
            reopened["metrics"]["actionableCoreIsolatedScenes"],
            1,
        )

    def test_gm01m14_unconsumed_definitions_are_exact(self) -> None:
        dialog = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_gm01m14_7"
        ]
        self.assertEqual(dialog["dialogIdRegistrationStatus"], "absent")
        self.assertEqual(len(dialog["lineIds"]), 11)
        self.assertEqual(len(dialog["missingAudioIds"]), 11)
        self.assertEqual(len(dialog["optionRows"]), 5)

        text_4 = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            "text_gm01m14_4"
        ]
        text_5 = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            "text_gm01m14_5"
        ]
        self.assertEqual(text_4["readingPopupRowId"], "text_gm01m14_4")
        self.assertEqual(text_4["contentTextIds"], (7825423282124136370,))
        self.assertEqual(text_5["readingPopupRowId"], "text_gm01m14_5")
        self.assertEqual(len(text_5["contentTextIds"]), 7)

    def test_gm01m27_retired_definitions_and_related_prts_bundle_are_exact(
        self,
    ) -> None:
        dialogs = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            {
                key: (
                    len(dialogs[key]["lineIds"]),
                    len(dialogs[key]["optionRows"]),
                )
                for key in (
                    "dlg_gm01m27_1",
                    "dlg_gm01m27_2",
                    "dlg_gm01m27_3",
                )
            },
            {
                "dlg_gm01m27_1": (6, 3),
                "dlg_gm01m27_2": (3, 2),
                "dlg_gm01m27_3": (3, 2),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIOS_BY_MISSION["gm01m27"],
            {
                "radio_gm01m27_1",
                "radio_gm01m27_2",
                "radio_gm01m27_3",
            },
        )

        table_root = (
            gap_queue.ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Table"
        )
        declaration = (
            gap_queue.OFFLINE_EXHAUSTION_MISSION_RELATED_ORIGINAL_DATA[
                "gm01m27"
            ]
        )
        prts = gap_queue.read_json(table_root / "PrtsReading.json", {})
        num_to_str = gap_queue.read_json(
            table_root / "NumIdStrTable.json", {}
        )
        str_to_num = gap_queue.read_json(
            table_root / "StrIdNumTable.json", {}
        )
        text_table = gap_queue.read_json(table_root / "TextTable.json", {})

        related, failure = (
            gap_queue._mission_related_original_data_validation(
                "gm01m27",
                declaration,
                prts,
                num_to_str,
                str_to_num,
                text_table,
            )
        )
        self.assertIsNone(failure)
        self.assertEqual(related["groupId"], "term_map01_lv001_gm01m27")
        self.assertEqual(
            [row["order"] for row in related["entries"]],
            [1, 2],
        )
        self.assertEqual(
            related["storyRelationStatus"],
            "same_nominal_mission_only_no_scene_or_quest_join",
        )

        broken_prts = copy.deepcopy(prts)
        broken_prts["term_map01_lv001_gm01m27"]["list"]["1"][
            "order"
        ] = 9
        related, failure = (
            gap_queue._mission_related_original_data_validation(
                "gm01m27",
                declaration,
                broken_prts,
                num_to_str,
                str_to_num,
                text_table,
            )
        )
        self.assertIsNone(related)
        self.assertEqual(
            failure["validator"],
            "offlineMissionRelatedOriginalData",
        )
        self.assertEqual(
            failure["gate"],
            "exactPrtsTerminalBundleAndMissionTextRows",
        )
        self.assertEqual(failure["expected"]["entries"][0]["order"], 1)
        self.assertEqual(failure["actual"]["entries"][0]["order"], 9)

    def test_exact_levelscript_interactive_config_is_closed_without_order(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["text_e1m1_1"],
            isolated=["text_e1m1_1"],
        )
        payload = mission_payload(connections=[{
            "key": "text_e1m1_1",
            "relation": "levelscript_interactive_narrative_config",
            "confidence": "native_exact_serialized_config",
            "source": (
                "exact counted LevelScriptData interactive map -> 25-member "
                "LevelInteractiveData -> componentProperties[94].type_id; "
                "ReadingPopUpTable is joined only when TYPE_ID names a popup row"
            ),
            "storyOwnerMission": "e1m1",
            "storyBinding": True,
            "ownership": False,
            "nativeMappingId":
                "levelscript-interactive-narrative-config-v1",
            "orderBoundary": (
                "interactive-map order, local interactive id, object position, "
                "and Story suffix do not establish relative Story chronology"
            ),
            "levelIds": ["map_test"],
            "scriptIds": ["1001"],
            "localInteractiveId": 40001,
            "entityDetailIds": ["int_narrative_scene_book"],
            "entityTemplateIds": ["int_narrative_scene"],
            "narrativeComponentKey": 94,
            "interactiveMapCount": 1,
            "rawTypeId": "rp_text_e1m1_1",
            "storyKeyResolution": "reading_popup_content_id",
            "questContextIds": ["e1m1_q#2"],
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelScriptData/map_test/1001.json",
            ],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            1,
        )
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            "levelscript_interactive_narrative_config",
            closure["relation"],
        )
        self.assertEqual([40001], closure["localInteractiveIds"])
        self.assertEqual(["e1m1_q#2"], closure["questContextIds"])

    def test_exact_leveldata_interactive_config_is_closed_without_order(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["text_e1m1_2"],
            isolated=["text_e1m1_2"],
        )
        payload = mission_payload(connections=[{
            "key": "text_e1m1_2",
            "relation": "leveldata_interactive_narrative_config",
            "confidence": "native_exact_serialized_config",
            "source": (
                "exact counted LevelData interactive list -> 25-member "
                "LevelInteractiveData bounded by the next record or validated "
                "member-21 suffix (nonempty BriefData dictionary or complete "
                "empty-script suffix), including an exact null or "
                "decoded mission/quest-state progress lock -> "
                "componentProperties[94].type_id"
            ),
            "storyOwnerMission": "e1m1",
            "storyBinding": True,
            "ownership": False,
            "nativeMappingId":
                "leveldata-interactive-narrative-config-v5",
            "orderBoundary": (
                "interactive-list order, record index, entity logic id, "
                "object position, and Story suffix do not establish relative "
                "Story chronology"
            ),
            "levelIds": ["map_test"],
            "levelDataAssets": ["map_test_lv_data_sub_e1m1"],
            "interactiveRecordIndex": 1,
            "interactiveListCount": 3,
            "interactiveRecordOffset": 100,
            "interactiveRecordEndOffset": 200,
            "interactiveRecordBoundarySource": "next_record",
            "entityLogicId": 10002,
            "entityDetailIds": ["int_narrative_scene_book"],
            "entityTemplateIds": ["int_narrative_scene"],
            "narrativeComponentKey": 94,
            "progressLockConditionStatus": "null",
            "rawTypeId": "rp_text_e1m1_2",
            "storyKeyResolution": "reading_popup_content_id",
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelData/map_test/map_test_lv_data_sub_e1m1.json",
            ],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            1,
        )
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            "leveldata_interactive_narrative_config",
            closure["relation"],
        )
        self.assertEqual([1], closure["interactiveRecordIndexes"])
        self.assertEqual([10002], closure["entityLogicIds"])

        connection = payload["flow"]["missionStoryConnections"][0]
        connection.update({
            "progressLockConditionStatus": "decoded",
            "progressLockConditionUnionTag": 16,
            "progressLockConditionSerializedMemberCount": 3,
            "progressLockConditionType":
                "SimpleConditionCheckQuestState",
            "progressLockConditionTree": {
                "unionTag": 16,
                "serializedMemberCount": 3,
                "conditionType": "SimpleConditionCheckQuestState",
                "ownerKind": "quest",
                "ownerId": "e1m1_q#2",
                "compareOperator": 0,
                "compareTarget": 3,
            },
            "progressLockConditions": [{
                "unionTag": 16,
                "serializedMemberCount": 3,
                "conditionType": "SimpleConditionCheckQuestState",
                "ownerKind": "quest",
                "ownerId": "e1m1_q#2",
                "compareOperator": 0,
                "compareTarget": 3,
            }],
        })
        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            1,
        )
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            closure["progressLocks"][0]["conditionType"],
            "SimpleConditionCheckQuestState",
        )
        self.assertEqual(
            closure["progressLocks"][0]["conditions"][0]["ownerId"],
            "e1m1_q#2",
        )

        connection["progressLockConditionStatus"] = "null"
        connection["progressLockConditions"] = []
        connection.pop("progressLockConditionUnionTag")
        connection.pop("progressLockConditionSerializedMemberCount")
        connection.pop("progressLockConditionType")
        connection.pop("progressLockConditionTree")
        connection[
            "interactiveRecordIndex"
        ] = 2
        connection[
            "interactiveRecordBoundarySource"
        ] = "leveldata_member21_start"
        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            0,
        )

        connection["levelDataMember21Offset"] = 200
        connection["levelScriptBriefDictionaryCountOffset"] = 204
        connection["levelScriptBriefDictionaryCount"] = 1
        connection["levelIdNum"] = 10
        connection["levelDataFinalBoundaryValidation"] = (
            "nonempty_levelscript_brief_dictionary"
        )
        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            1,
        )

        connection["levelScriptBriefDictionaryCount"] = 0
        connection["levelScriptDataPathDictionaryCountOffset"] = 208
        connection["levelScriptDataPathDictionaryCount"] = 0
        connection["levelDataSafeZoneOffset"] = 260
        connection["levelDataSceneId"] = "map_test"
        connection["levelDataSpecificDataOffset"] = 280
        connection["levelDataEmptySuffixEndOffset"] = 320
        connection["levelDataFinalBoundaryValidation"] = (
            "complete_empty_script_suffix_to_eof"
        )
        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            1,
        )

    def test_exact_leveldata_horn_dialog_config_is_closed_without_order(
        self,
    ) -> None:
        partial = partial_mission(
            "sm1l1m9",
            scenes=["dlg_sm1l1m9_11"],
            isolated=["dlg_sm1l1m9_11"],
        )
        payload = mission_payload(connections=[{
            "key": "dlg_sm1l1m9_11",
            "relation": "leveldata_interactive_narrative_config",
            "confidence": "native_exact_serialized_config",
            "source": (
                "exact counted LevelData interactive list -> 25-member "
                "LevelInteractiveData bounded by the next record or validated "
                "member-21 suffix (nonempty BriefData dictionary or complete "
                "empty-script suffix), including an exact null or decoded "
                "mission/quest-state progress lock -> "
                "int_horn.properties.dialog_id; the byte-identical authored "
                "Horn template and current native Horn flow validate the "
                "dialog consumer"
            ),
            "storyOwnerMission": "sm1l1m9",
            "storyBinding": True,
            "ownership": False,
            "nativeMappingId":
                "leveldata-interactive-horn-dialog-config-v1",
            "narrativeConsumerKind": "horn_dialog_property",
            "interactiveHornNativeMappingId":
                "gameassembly-2026-07-29-interactive-horn-dialog-v1",
            "interactiveHornTemplateSha256": (
                "1200acb7208de5e4b9e861dc511cc3a3d4f1f5c56dd4b59f1"
                "dcb0ef7ab2ea33e"
            ),
            "orderBoundary": (
                "interactive-list order, record index, entity logic id, "
                "object position, and Story suffix do not establish relative "
                "Story chronology"
            ),
            "levelIds": ["map01_lv001"],
            "levelDataAssets": ["map01_lv001_lv_data_sub_sm1l1m9"],
            "interactiveRecordIndex": 2,
            "interactiveListCount": 3,
            "interactiveRecordOffset": 2155,
            "interactiveRecordEndOffset": 3099,
            "interactiveRecordBoundarySource":
                "leveldata_member21_start",
            "levelDataMember21Offset": 3099,
            "levelScriptBriefDictionaryCountOffset": 3103,
            "levelScriptBriefDictionaryCount": 7,
            "levelIdNum": 1,
            "levelDataFinalBoundaryValidation":
                "nonempty_levelscript_brief_dictionary",
            "entityLogicId": 2100280047,
            "entityDetailIds": ["int_horn"],
            "entityTemplateIds": ["int_horn"],
            "dialogIdEntryOffset": 2800,
            "progressLockConditionStatus": "decoded",
            "progressLockConditionUnionTag": 16,
            "progressLockConditionSerializedMemberCount": 3,
            "progressLockConditionType":
                "SimpleConditionCheckQuestState",
            "progressLockConditionTree": {
                "unionTag": 16,
                "serializedMemberCount": 3,
                "conditionType": "SimpleConditionCheckQuestState",
                "ownerKind": "quest",
                "ownerId": "sm1l1m9_q#16",
                "compareOperator": 0,
                "compareTarget": 3,
            },
            "progressLockConditions": [{
                "unionTag": 16,
                "serializedMemberCount": 3,
                "conditionType": "SimpleConditionCheckQuestState",
                "ownerKind": "quest",
                "ownerId": "sm1l1m9_q#16",
                "compareOperator": 0,
                "compareTarget": 3,
            }],
            "rawTypeId": "dlg_sm1l1m9_11",
            "storyKeyResolution": "direct_story_key",
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelData/map01_lv001/"
                "map01_lv001_lv_data_sub_sm1l1m9.json",
            ],
            "nativeConsumer": (
                "data_int_horn dialog_id -> authored dialog flow -> "
                "OnDialogExit -> ReqInteractHorn(finishId)"
            ),
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            1,
        )
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            ["horn_dialog_property"],
            closure["narrativeConsumerKinds"],
        )
        self.assertEqual([2], closure["interactiveRecordIndexes"])
        self.assertEqual(
            ["leveldata-interactive-horn-dialog-config-v1"],
            closure["nativeMappingIds"],
        )

    def test_exact_embedded_dialog_tree_line_context_closes_without_file_edge(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["black_a"],
            isolated=["black_a"],
        )
        occurrence = {
            "textId": "black_a_001",
            "actionType": "Beyond.Gameplay.DialogNarrativeMaskActionData",
            "actionKind": "narrative",
            "actionPath": (
                "nodes[3]._transitionData._actionGroups[0].actions[0]"
            ),
            "nodeId": "3",
            "dialogKey": "dlg_parent",
            "sourceFile": "TextAsset/dlg_parent.json",
            "sourcePathId": "123",
            "dialogTreeConnectionPlacementStatus":
                "exact_unique_adjacent_parent_trunks",
            "reachableFromPrimeNode": True,
            "primeToActionNodePath": ["0", "1", "2", "3"],
            "embeddedAfterLineIds": ["dlg_parent_006"],
            "embeddedBeforeLineIds": ["dlg_parent_007"],
            "nativeMappingId":
                "dialog-tree-narrative-mask-connection-native-v1",
        }
        payload = mission_payload(connections=[{
            "key": "black_a",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKey": "dlg_parent",
            "storyOwnerMission": "e1m1",
            "confidence": "native_derived_exact_parent_shell",
            "evidenceTier": "derived_exact_shell",
            "scopeCompleteness": "complete",
            "allParentStoryKeys": ["dlg_parent"],
            "embeddedLinePlacementStatus":
                "exact_complete_connection_neighbors",
            "embeddedAfterLineIds": ["dlg_parent_006"],
            "embeddedBeforeLineIds": ["dlg_parent_007"],
            "nativeMappingId":
                "dialog-tree-narrative-mask-connection-native-v1",
            "occurrenceCount": 1,
            "sourceFiles": ["TextAsset/dlg_parent.json"],
            "sourcePathIds": ["123"],
            "dialogTreeNarrativeActions": [occurrence],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactNativeIsolatedScenes"],
            1,
        )
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(
            "closed_exact_native_embedded_line_context_no_file_order",
            closure["recoveryStatus"],
        )
        self.assertEqual(["dlg_parent_006"], closure["embeddedAfterLineIds"])
        self.assertEqual(["dlg_parent_007"], closure["embeddedBeforeLineIds"])

    def test_partial_embedded_dialog_tree_scope_stays_actionable(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["black_a"],
            isolated=["black_a"],
        )
        payload = mission_payload(connections=[{
            "key": "black_a",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKey": "dlg_parent",
            "storyOwnerMission": "e1m1",
            "confidence": "native_derived_exact_parent_shell",
            "evidenceTier": "derived_exact_shell",
            "scopeCompleteness": "partial",
            "allParentStoryKeys": ["dlg_parent", "dlg_unscoped"],
            "unscopedParentStoryKeys": ["dlg_unscoped"],
            "embeddedLinePlacementStatus":
                "exact_complete_connection_neighbors",
            "embeddedAfterLineIds": ["dlg_parent_006"],
            "embeddedBeforeLineIds": ["dlg_parent_007"],
            "nativeMappingId":
                "dialog-tree-narrative-mask-connection-native-v1",
            "occurrenceCount": 1,
            "dialogTreeNarrativeActions": [{
                "textId": "black_a_001",
                "actionPath": "nodes[3]._transitionData.actions[0]",
                "nodeId": "3",
                "dialogKey": "dlg_parent",
                "sourceFile": "TextAsset/dlg_parent.json",
                "dialogTreeConnectionPlacementStatus":
                    "exact_unique_adjacent_parent_trunks",
                "reachableFromPrimeNode": True,
                "primeToActionNodePath": ["0", "1", "2", "3"],
                "embeddedAfterLineIds": ["dlg_parent_006"],
                "embeddedBeforeLineIds": ["dlg_parent_007"],
                "nativeMappingId":
                    "dialog-tree-narrative-mask-connection-native-v1",
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["closedExactNativeIsolatedScenes"], 0)
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)

    def test_exact_embedded_playback_context_closes_with_line_position_unknown(
        self,
    ) -> None:
        partial = partial_mission(
            "e7m3",
            scenes=["black_e7m3_1"],
            isolated=["black_e7m3_1"],
        )
        payload = mission_payload(connections=[{
            "key": "black_e7m3_1",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKey": "dlg_e7m3_14",
            "storyOwnerMission": "e7m3",
            "confidence": "native_exact_parent_quest",
            "evidenceTier": "native_direct",
            "scopeCompleteness": "complete",
            "allParentStoryKeys": ["dlg_e7m3_14"],
            "embeddedLinePlacementStatus":
                "not_exact_complete_connection_neighbors",
            "nativeMappingId":
                "dialog-tree-narrative-mask-connection-native-v1",
            "occurrenceCount": 1,
            "sourceFiles": ["TextAsset/dlg_e7m3_14.json"],
            "sourcePathIds": ["CCD54B0D31965DE2"],
            "dialogTreeNarrativeActions": [{
                "textId": "black_e7m3_1_003",
                "actionType":
                    "Beyond.Gameplay.DialogNarrativeMaskActionData",
                "actionKind": "narrative",
                "actionPath": (
                    "nodes[11]._transitionData._actionGroups[0].actions[0]"
                ),
                "nodeId": "11",
                "dialogKey": "dlg_e7m3_14",
                "sourceFile": "TextAsset/dlg_e7m3_14.json",
                "sourcePathId": "CCD54B0D31965DE2",
                "dialogTreeConnectionPlacementStatus":
                    "no_exact_unique_adjacent_parent_trunks",
                "reachableFromPrimeNode": True,
                "primeToActionNodePath": [
                    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                    "11",
                ],
                "incomingNodeIds": ["9"],
                "outgoingNodeIds": ["12"],
                "immediatelyPrecedingTrunkIds": [],
                "immediatelyFollowingTrunkIds": ["dlg_e7m3_14_007"],
                "nativeMappingId":
                    "dialog-tree-narrative-mask-connection-native-v1",
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactNativeIsolatedScenes"],
            1,
        )
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(
            (
                "closed_exact_native_embedded_playback_context_"
                "line_position_unresolved_no_file_order"
            ),
            closure["recoveryStatus"],
        )
        self.assertEqual(
            "exact_parent_playback_line_position_unresolved",
            closure["linePlacementStatus"],
        )
        self.assertEqual(
            ["dlg_e7m3_14_007"],
            closure["unresolvedLinePlacements"][0][
                "immediatelyFollowingTrunkIds"
            ],
        )

    def test_embedded_context_without_exact_prime_path_stays_actionable(
        self,
    ) -> None:
        partial = partial_mission(
            "e7m3",
            scenes=["black_e7m3_1"],
            isolated=["black_e7m3_1"],
        )
        payload = mission_payload(connections=[{
            "key": "black_e7m3_1",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKey": "dlg_e7m3_14",
            "storyOwnerMission": "e7m3",
            "confidence": "native_exact_parent_quest",
            "evidenceTier": "native_direct",
            "scopeCompleteness": "complete",
            "allParentStoryKeys": ["dlg_e7m3_14"],
            "embeddedLinePlacementStatus":
                "not_exact_complete_connection_neighbors",
            "nativeMappingId":
                "dialog-tree-narrative-mask-connection-native-v1",
            "occurrenceCount": 1,
            "sourceFiles": ["TextAsset/dlg_e7m3_14.json"],
            "sourcePathIds": ["CCD54B0D31965DE2"],
            "dialogTreeNarrativeActions": [{
                "textId": "black_e7m3_1_003",
                "actionType":
                    "Beyond.Gameplay.DialogNarrativeMaskActionData",
                "actionKind": "narrative",
                "actionPath": "nodes[11]._transitionData.actions[0]",
                "nodeId": "11",
                "dialogKey": "dlg_e7m3_14",
                "sourceFile": "TextAsset/dlg_e7m3_14.json",
                "sourcePathId": "CCD54B0D31965DE2",
                "dialogTreeConnectionPlacementStatus":
                    "no_exact_unique_adjacent_parent_trunks",
                "reachableFromPrimeNode": False,
                "primeToActionNodePath": [],
                "nativeMappingId":
                    "dialog-tree-narrative-mask-connection-native-v1",
            }],
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["closedExactNativeIsolatedScenes"], 0)
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)

    def test_npc_proxy_runtime_config_for_other_mission_stays_actionable(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["dlg_a"],
            isolated=["dlg_a"],
        )
        payload = mission_payload(connections=[{
            "key": "dlg_a",
            "relation": "npc_proxy_ex_mission_context",
            "confidence": "direct_mission_scope",
            "source": "NpcProxyExDataTable.data[*].missionId + dialogId",
            "npcProxyId": "npc_proxy_a",
            "npcProxyMissionId": "e2m1",
            "storyOwnerMission": "e2m1",
            "selectionOrderStatus": (
                "one_based_active_row_selection_only_no_cross_row_chronology"
            ),
            "nativeMappingId": "npc-proxy-dialog-selection-native-v1",
            "gameAssemblySha256": (
                "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2"
                "B983FB9D45677D80FFCE"
            ),
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            0,
        )
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)

    def test_npc_proxy_cross_mission_context_closes_nominal_story_gap(
        self,
    ) -> None:
        partial = partial_mission(
            "e11m1",
            scenes=["dlg_e11m1_30"],
            isolated=["dlg_e11m1_30"],
        )
        payload = mission_payload(connections=[{
            "key": "dlg_e11m1_30",
            "relation": "npc_proxy_ex_mission_context",
            "confidence": "direct_mission_scope",
            "source": "NpcProxyExDataTable.data[*].missionId + dialogId",
            "npcProxyId": "shenjiaoe_map02_v1d40_002",
            "npcProxyMissionId": "e11m2",
            "storyOwnerMission": "e11m1",
            "contextMissionBundle": "e11m2",
            "selectionOrderStatus": (
                "one_based_active_row_selection_only_no_cross_row_chronology"
            ),
            "nativeMappingId": "npc-proxy-dialog-selection-native-v1",
            "gameAssemblySha256": (
                "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2"
                "B983FB9D45677D80FFCE"
            ),
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_cross_mission_runtime_config_no_relative_order",
        )
        self.assertEqual(closure["missionId"], "e11m2")
        self.assertEqual(closure["nominalStoryMissionId"], "e11m1")
        self.assertTrue(closure["contextMissionMismatch"])
        self.assertEqual(closure["contextMissionBundles"], ["e11m2"])

    def test_exact_cross_mission_dialog_finish_dependency_closes_story_gap(
        self,
    ) -> None:
        partial = partial_mission(
            "e9m2",
            scenes=["dlg_e9m2_14"],
            isolated=["dlg_e9m2_14"],
        )
        dependent = mission_payload()
        dependent["flow"]["quests"] = [{
            "id": "e9m9_q#1",
            "storyConnections": [{
                "key": "dlg_e9m2_14",
                "kind": "dialog",
                "relation": "objective_condition",
                "direction": "story_to_quest",
                "phase": "progress",
                "confidence": "direct",
                "source": (
                    "MissionRuntimeAsset.questDic[*].objectiveList[0]"
                    ".condition._dialogId"
                ),
                "objectiveIndex": 1,
                "conditionType": "CheckTalkOptionFinish",
                "finishId": -1,
            }],
        }]
        report = gap_queue.build_gap_report(
            {
                "_schema": "partial",
                "language": "CN",
                "missions": [partial],
            },
            {
                "e9m2": mission_payload(),
                "e9m9": dependent,
            },
            {"e9m2", "e9m9"},
        )

        row = report["missions"][0]
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            closure["recoveryStatus"],
            (
                "closed_exact_mission_dialog_finish_dependency_"
                "no_relative_order"
            ),
        )
        self.assertEqual(closure["dependentMissionIds"], ["e9m9"])
        self.assertEqual(closure["dependentQuestIds"], ["e9m9_q#1"])
        self.assertEqual(closure["finishIds"], [-1])

    def test_exact_cross_mission_runtime_configs_close_story_gaps(
        self,
    ) -> None:
        partial = partial_mission(
            "e6m1",
            scenes=["radio_e6m1_20", "radio_e6m1_21"],
            isolated=["radio_e6m1_20", "radio_e6m1_21"],
        )
        for node in partial["nodes"]:
            node["kind"] = "radio"
        dependent = mission_payload(connections=[
            {
                "key": "radio_e6m1_20",
                "relation":
                    "airwall_mission_state_radio_playback_context",
                "direction": "context",
                "phase": "airwall_mission_state_gate",
                "confidence": "native_exact_serialized_co_carrier",
                "evidenceTier": "direct",
                "storyOwnerMission": "e6m1",
                "missionStateId": "e6m1d5",
                "storyBinding": True,
                "ownership": False,
                "dependencyOnly": False,
                "questActivation": False,
                "questPlayback": False,
                "questCompletion": False,
                "nativeMappingId":
                    "leveldata-airwall-mission-radio-memorypack-v1d4",
                "nativeConsumer":
                    "AirWall pushback -> GameAction.PlayRadio",
                "levelIds": ["indie_dg005"],
                "sourceFiles": ["indie_dg005_lv_data_sub_e6m1.json"],
                "sourcePath": "LevelData/indie_dg005/e6m1.json",
                "recordOffset": 5,
                "recordEndOffset": 242,
                "serializedMemberCount": 8,
                "airWallGroupId": "25600010001",
                "airWallSlotId": 0,
                "airWallDefaultOn": False,
                "targetMissionStateChecks": [{
                    "transition": "rise",
                    "id": "e6m1d5",
                    "isQuest": False,
                    "targetMissionId": "e6m1d5",
                    "detailState": 2,
                    "comparison": "equal",
                }],
            },
            {
                "key": "radio_e6m1_21",
                "relation": "focus_mode_interact_locked_radio",
                "direction": "context",
                "phase": "interact_locked",
                "confidence": "direct_mission_scope",
                "storyOwnerMission": "e6m1",
                "focusModeId": "e6m1_ZhuangfyBanGongShi",
                "focusModeMissionId": "e6m1d5",
                "focusModeField": "radioIdInteractLocked",
                "subDataParentId": 25600010000,
            },
        ])
        report = gap_queue.build_gap_report(
            {
                "_schema": "partial",
                "language": "CN",
                "missions": [partial],
            },
            {
                "e6m1": mission_payload(),
                "e6m1d5": dependent,
            },
            {"e6m1", "e6m1d5"},
        )

        row = report["missions"][0]
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            {
                closure["relation"]
                for closure in row[
                    "closedExactRuntimeConfigIsolatedScenes"
                ]
            },
            {
                "airwall_mission_state_radio_playback_context",
                "focus_mode_interact_locked_radio",
            },
        )

    def test_exact_cross_mission_leveldata_playback_closes_story_gap(
        self,
    ) -> None:
        story_key = "radio_e2m7_11"
        occurrence = {
            "levelId": "dung02_dg003",
            "scriptId": "29800030004",
            "sourceFile": "LevelScriptData/dung02_dg003/29800030004.json",
            "actionMapRole": "actionList#45 linked",
            "actionCode": "0x0363",
            "actionKind": "0x0d",
            "localId": 60,
            "actionName": "PlayRadio",
            "recordClass": "play_radio",
            "nativeMappingId": "gameassembly-test-actionbase",
            "allStoryKeysInRecord": [story_key],
            "nativeEventOwnerStatus": "exact_serialized_control_path",
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "LevelEvent_OnBattleSignal",
                "headerLocalId": 57,
                "eventDetail": {
                    "summary": "battle signal radio_0079_07_boss_4",
                },
                "path": [
                    {"localId": 58},
                    {
                        "localId": 60,
                        "actionName": "PlayRadio",
                        "recordClass": "play_radio",
                    },
                ],
            }],
            "levelDataHosts": [{
                "missionId": "e9m3",
                "levelId": "dung02_dg003",
                "scriptId": "29800030004",
                "levelDataFile": "LevelData/dung02_dg003/e9m3.json",
                "encoding": "leveldata_member22_levelscriptbriefdata",
                "nativeSchema": (
                    "LevelData/43.member22:"
                    "Dictionary<u64,LevelScriptBriefData/8>"
                ),
                "briefData": [{"scriptId": "29800030004"}],
            }],
            "scopeEvidenceKinds": [
                "mission_leveldata_member22_contains_validated_"
                "levelscript_brief",
            ],
        }
        connection = {
            "key": story_key,
            "kind": "radio",
            "relation": "leveldata_levelscript_mission_context",
            "direction": "context",
            "phase": "context",
            "confidence": "native_exact_host",
            "storyOwnerMission": "e2m7",
            "levelDataHostMissionId": "e9m3",
            "questTriggerStatus": "unresolved",
            "occurrenceCount": 1,
            "allOccurrenceCount": 1,
            "hasUnscopedOrOtherMissionOccurrences": False,
            "nativeActions": ["PlayRadio"],
            "opcodes": ["0x0363/0x0d"],
            "levelIds": ["dung02_dg003"],
            "scriptIds": ["29800030004"],
            "sourceFiles": [
                "LevelScriptData/dung02_dg003/29800030004.json",
            ],
            "levelDataFiles": ["LevelData/dung02_dg003/e9m3.json"],
            "levelScriptOccurrences": [occurrence],
        }
        partial = partial_mission(
            "e2m7",
            scenes=[story_key],
            isolated=[story_key],
        )
        report = gap_queue.build_gap_report(
            {
                "_schema": "partial",
                "language": "CN",
                "missions": [partial],
            },
            {
                "e2m7": mission_payload(),
                "e9m3": mission_payload(connections=[connection]),
            },
            {"e2m7", "e9m3"},
        )

        row = report["missions"][0]
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(closure["sceneKey"], story_key)
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_native_event_path_no_relative_order",
        )
        self.assertEqual(
            closure["nativeEventPaths"][0]["headerName"],
            "LevelEvent_OnBattleSignal",
        )

        invalid = dict(connection)
        invalid["confidence"] = "derived"
        self.assertFalse(
            gap_queue._exact_cross_owner_leveldata_story_context(
                invalid,
                "e2m7",
                "e9m3",
            )
        )

    def test_exact_cross_mission_condition_playback_closes_story_gap(
        self,
    ) -> None:
        story_key = "dlg_e8m3_1"
        source_file = "LevelScriptData/map02_lv004/23400020010.json"
        occurrence = {
            "levelId": "map02_lv004",
            "scriptId": "23400020010",
            "sourceFile": source_file,
            "actionMapRole": "actionList#8 linked",
            "localId": 12,
            "actionName": "StartDialogAndTeleportAction",
            "recordClass": "play_dialog",
            "nativeMappingId": "gameassembly-test-actionbase",
            "allStoryKeysInRecord": [story_key],
            "nativeEventOwnerStatus": "exact_serialized_control_path",
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "headerLocalId": 6,
                "eventDetail": {
                    "summary": "leader enters trigger slot 80001",
                },
                "path": [
                    {"localId": 7},
                    {
                        "localId": 12,
                        "actionName": "StartDialogAndTeleportAction",
                        "recordClass": "play_dialog",
                    },
                ],
            }],
            "missionConditions": [{
                "missionId": "e8m2",
                "questId": "e8m2_q#14d5",
                "conditionType": "CheckLevelScriptPropertyBool",
                "sourceFile": "MissionRuntimeAsset/e8m2.json",
            }],
            "scopeEvidenceKinds": ["mission_condition_checks_script"],
        }
        connection = {
            "key": story_key,
            "kind": "dialog",
            "relation": "levelscript_mission_context",
            "direction": "context",
            "phase": "context",
            "confidence": "scoped_script",
            "storyOwnerMission": "e8m3",
            "levelScriptMissionId": "e8m2",
            "occurrenceCount": 1,
            "allOccurrenceCount": 1,
            "hasUnscopedOrOtherMissionOccurrences": False,
            "scopeEvidenceKinds": ["mission_condition_checks_script"],
            "levelScriptOccurrences": [occurrence],
        }
        partial = partial_mission(
            "e8m3",
            scenes=[story_key],
            isolated=[story_key],
        )
        report = gap_queue.build_gap_report(
            {
                "_schema": "partial",
                "language": "CN",
                "missions": [partial],
            },
            {
                "e8m2": mission_payload(connections=[connection]),
                "e8m3": mission_payload(),
            },
            {"e8m2", "e8m3"},
        )

        row = report["missions"][0]
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(closure["sceneKey"], story_key)
        self.assertEqual(
            closure["nativeEventPaths"][0]["headerName"],
            "ScriptEvent_OnLeaderEnterTriggerVolume",
        )

        invalid = dict(connection)
        invalid["scopeEvidenceKinds"] = ["script_contains_mission_or_quest_ref"]
        self.assertFalse(
            gap_queue._exact_cross_owner_mission_condition_story_context(
                invalid,
                "e8m3",
                "e8m2",
            )
        )

    def test_dialog_finish_dependency_requires_exact_typed_source(self) -> None:
        partial = partial_mission(
            "e9m2",
            scenes=["dlg_e9m2_14"],
            isolated=["dlg_e9m2_14"],
        )
        payload = mission_payload(connections=[{
            "key": "dlg_e9m2_14",
            "relation": "objective_condition",
            "direction": "story_to_quest",
            "phase": "progress",
            "confidence": "direct",
            "source": "derived dialog completion",
            "objectiveIndex": 1,
            "conditionType": "CheckTalkOptionFinish",
            "finishId": -1,
            "contextMissionBundle": "e9m9",
            "contextQuestId": "e9m9_q#1",
        }])

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            0,
        )

    def test_exact_mission_client_action_closes_and_attaches_quest(
        self,
    ) -> None:
        story_key = "radio_e6m3_10d3"
        partial = partial_mission(
            "e6m3",
            scenes=[story_key],
            isolated=[story_key],
        )
        partial["nodes"][0]["kind"] = "radio"
        payload = mission_payload(quest_ids=["e6m3_q#16"])
        payload["flow"]["quests"] = [{
            "id": "e6m3_q#16",
            "storyConnections": [{
                "key": story_key,
                "kind": "radio",
                "relation": "client_action_succeed",
                "direction": "quest_to_story",
                "phase": "succeed",
                "confidence": "native_typed_direct",
                "source": (
                    "MissionRuntimeAsset.clientActionMapKey[0] -> "
                    "actionMapRaw.actionList[7]._radioId"
                ),
                "actionSlot": 2,
                "actionId": 7,
                "actionType": "PlayRadio",
            }],
        }]

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(row["metrics"]["strictQuestIdsWithStoryAttachment"], 1)
        self.assertEqual(row["metrics"]["questIdsWithoutStrictStoryAttachment"], 0)
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_mission_quest_client_action_no_relative_order",
        )
        self.assertEqual(closure["questIds"], ["e6m3_q#16"])
        self.assertEqual(closure["actionTypes"], ["PlayRadio"])

    def test_exact_cross_mission_client_action_closes_story_gap(
        self,
    ) -> None:
        story_key = "radio_e2m2_1"
        partial = partial_mission(
            "e2m2",
            scenes=[story_key],
            isolated=[story_key],
        )
        partial["nodes"][0]["kind"] = "radio"
        dependent = mission_payload()
        dependent["flow"]["quests"] = [{
            "id": "e2m1_q#3",
            "storyConnections": [{
                "key": story_key,
                "kind": "radio",
                "relation": "client_action_succeed",
                "direction": "quest_to_story",
                "phase": "succeed",
                "confidence": "native_typed_direct",
                "source": (
                    "MissionRuntimeAsset.clientActionMapKey[1] -> "
                    "actionMapRaw.actionList[16]._radioId"
                ),
                "actionSlot": 2,
                "actionId": 16,
                "actionType": "PlayRadio",
            }],
        }]
        report = gap_queue.build_gap_report(
            {
                "_schema": "partial",
                "language": "CN",
                "missions": [partial],
            },
            {
                "e2m1": dependent,
                "e2m2": mission_payload(),
            },
            {"e2m1", "e2m2"},
        )

        row = report["missions"][0]
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactRuntimeConfigIsolatedScenes"][0]
        self.assertEqual(closure["sceneKey"], story_key)
        self.assertEqual(closure["contextMissionIds"], ["e2m1"])
        self.assertTrue(closure["contextMissionMismatch"])
        self.assertEqual(closure["questIds"], ["e2m1_q#3"])
        self.assertEqual(
            closure["sourceFiles"],
            [
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/e2m1.json"
            ],
        )

    def test_cross_mission_client_action_requires_exact_native_shape(
        self,
    ) -> None:
        story_key = "radio_e2m2_1"
        partial = partial_mission(
            "e2m2",
            scenes=[story_key],
            isolated=[story_key],
        )
        dependent = mission_payload()
        dependent["flow"]["quests"] = [{
            "id": "e2m1_q#3",
            "storyConnections": [{
                "key": story_key,
                "relation": "client_action_succeed",
                "direction": "quest_to_story",
                "phase": "succeed",
                "confidence": "native_typed_direct",
                "source": "derived client action",
                "actionSlot": 1,
                "actionId": 16,
                "actionType": "PlayRadio",
            }],
        }]
        report = gap_queue.build_gap_report(
            {
                "_schema": "partial",
                "language": "CN",
                "missions": [partial],
            },
            {
                "e2m1": dependent,
                "e2m2": mission_payload(),
            },
            {"e2m1", "e2m2"},
        )

        row = report["missions"][0]
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)
        self.assertEqual(
            row["metrics"]["closedExactRuntimeConfigIsolatedScenes"],
            0,
        )

    def test_mission_client_action_requires_exact_slot_and_source(self) -> None:
        story_key = "radio_e6m3_10d3"
        partial = partial_mission(
            "e6m3",
            scenes=[story_key],
            isolated=[story_key],
        )
        payload = mission_payload(quest_ids=["e6m3_q#16"])
        payload["flow"]["quests"] = [{
            "id": "e6m3_q#16",
            "storyConnections": [{
                "key": story_key,
                "relation": "client_action_succeed",
                "direction": "quest_to_story",
                "phase": "succeed",
                "confidence": "native_typed_direct",
                "source": "derived client action",
                "actionSlot": 1,
                "actionId": 7,
                "actionType": "PlayRadio",
            }],
        }]

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)
        self.assertEqual(row["metrics"]["strictQuestIdsWithStoryAttachment"], 0)
        self.assertEqual(row["metrics"]["questIdsWithoutAnyStoryEvidence"], 1)

    def test_exact_definition_only_isolated_scene_is_closed(self) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["black_a"],
            isolated=["black_a"],
        )
        payload = mission_payload()
        payload["flow"]["unlinkedDefinitionOnly"] = [{
            "key": "black_a",
            "relation": "original_text_definition_without_consumer",
            "phase": "definition_only",
            "confidence": "current_build_no_consumer",
            "source": "original definition; complete consumer search",
            "consumerSearchStatus":
                "no_current_original_game_consumer_recovered",
            "searchedConsumerKinds": [
                "LevelScript playback",
                "DialogTree narrative mask",
                "Timeline text playable",
            ],
            "bindingStatus": "definition_only_unlinked",
            "serverEvidenceStatus":
                "no_runtime_consumer_or_network_edge_recovered",
        }]
        partial["nodes"][0]["kind"] = "black"

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["coreIsolatedScenes"], 1)
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedDefinitionOnlyIsolatedScenes"],
            1,
        )
        self.assertEqual(
            row["closedDefinitionOnlyIsolatedScenes"][0][
                "recoveryStatus"
            ],
            "closed_current_build_definition_without_consumer",
        )

    def test_declared_cutscene_definitions_cover_every_host_gate(self) -> None:
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS),
            set(gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS),
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS),
            set(gap_queue.OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e11m6_rift_camera_state1to2"
            ]["timelineRegistryId"],
            483,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e11m6_zhuangcomein"
            ]["timelineRegistryId"],
            547,
        )

    def test_declared_e11m2_alias_chain_is_composition_only(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES,
            {
                "cutscene_e11m2_liexi_xs_m_01_last_02": (
                    "cutscene_e11m2_liexi_xs_m_01_last_01",
                    "cutscene_e11m2_liexi_xs_m_01_last_02",
                ),
                "cutscene_e11m2_liexi_xs_m_01_last_03": (
                    "cutscene_e11m2_liexi_xs_m_01_last_02",
                    "cutscene_e11m2_liexi_xs_m_01_last_03",
                ),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS[
                "cutscene_e11m2_liexi_xs_m_01_last_03"
            ],
            0,
        )

    def test_declared_e11m2_radio_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E11M2_RADIOS,
            {
                "radio_e11m2_22",
                "radio_e11m2_25",
                "radio_e11m2_27",
                "radio_e11m2_30",
                "radio_e11m2_33",
                "radio_e11m2_34",
                "radio_e11m2_35",
                "radio_e11m2_36",
                "radio_e11m2_37",
            },
        )

    def test_declared_e2m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION["e2m1"],
            {"cutscene_e2m1_1"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES[
                "cutscene_e2m1_1"
            ],
            {
                "missionId": "e2m1",
                "definitionRowKeys": (
                    "cutscene_e2m1_1_01",
                    "cutscene_e2m1_1_02",
                ),
            },
        )

    def test_declared_remaining_main_story_isolated_frontier_is_exact(
        self,
    ) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E1M5_RADIOS,
            {"radio_e1m5_3d5"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_CONTEXTS[
                "radio_e1m5_3d5"
            ]["byteStringCounts"],
            {"radio_e1m5_3d5": 5, "e1m5_q#8": 1},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E1M6_RADIOS,
            {"radio_e1m6_2"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E4M1D5_RADIOS,
            {"radio_e4m1d5_3"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E5M3_RADIOS,
            {"radio_e5m3_14"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_TABLE_ONLY_STORIES[
                "black_e7m1_3"
            ]["definitionRowKeys"],
            ("black_e7m1_3_001",),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                "sns_e1m9_1"
            ],
            {
                "missionId": "e1m9",
                "chatId": "sns_chr_0006_wolfgd",
                "contentIds": (-1, 1, 2),
                "optionIdsByContentId": {},
                "optionNextContentIds": {},
                "optionDescriptionIds": {},
            },
        )
        text = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            "text_e8m4_1"
        ]
        self.assertEqual(text["readingPopupRowId"], "rp_text_e8m4_1")
        self.assertEqual(
            text["prtsDefinition"]["rowId"],
            "nar_collection_map02_12136_1",
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e5m0d5_1"
        ]
        self.assertEqual(len(dialog["lineIds"]), 14)
        self.assertEqual(dialog["optionIds"], ())
        self.assertEqual(
            dialog["ownedTimeline"]["timeline"],
            "dlgtl_e5m0d5_1_sub_1",
        )
        self.assertEqual(
            dialog["ownedTimeline"]["trackPathId"],
            3386777180023897082,
        )

    def test_offline_radio_leveldata_context_fails_closed_on_route_change(
        self,
    ) -> None:
        source_file = (
            "export_full/structured/StreamingAssets/Data/Json/LevelData/"
            "map01_lv002/map01_lv002_lv_data.json"
        )
        route = {
            "key": "radio_e1m5_3d5",
            "relation": "leveldata_quest_reference",
            "direction": "context",
            "phase": "context",
            "confidence": "direct",
            "levelId": "map01_lv002",
            "file": source_file,
        }
        evidence = {
            "sceneKey": "radio_e1m5_3d5",
            "missionId": "e1m5",
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "graphEffect": "none",
            "nonOwningContext": {
                "questId": "e1m5_q#8",
                "distance": 65,
            },
            "allowedNonOwningRoute": {
                key: value for key, value in route.items() if key != "key"
            },
        }
        flow = {
            "quests": [{
                "id": "e1m5_q#8",
                "storyConnections": [route],
                "levelDataStoryRefs": [{
                    "storyRef": "radio_e1m5_3d5",
                    "file": source_file,
                    "distance": 65,
                }],
            }],
        }
        rows = gap_queue._deferred_offline_exhausted_isolated_scenes(
            flow,
            {"radio_e1m5_3d5"},
            "e1m5",
            {"radio_e1m5_3d5": evidence},
        )
        self.assertEqual([row["sceneKey"] for row in rows], ["radio_e1m5_3d5"])
        flow["quests"][0]["storyConnections"][0]["confidence"] = "weak"
        self.assertEqual(
            gap_queue._deferred_offline_exhausted_isolated_scenes(
                flow,
                {"radio_e1m5_3d5"},
                "e1m5",
                {"radio_e1m5_3d5": evidence},
            ),
            [],
        )

    def test_dialog_tree_branch_context_defer_fails_closed(self) -> None:
        story_key = "dlg_a1m5_5"
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            story_key
        ]
        context = definition["nonOwningContext"]
        route = {
            "key": story_key,
            **definition["allowedNonOwningRoute"],
            "sourceFiles": [context["sourceFile"]],
            "carrierQuestStateContext": {
                "candidateQuestIds": list(context["candidateQuestIds"]),
                "questStateBranchContexts": [{
                    "questIds": list(context["candidateQuestIds"]),
                    "conditionEvalString": context["conditionEvalString"],
                    "noBypass": True,
                    "conditions": [
                        {
                            "questId": quest_id,
                            "targetQuestState": context[
                                "targetQuestState"
                            ],
                        }
                        for quest_id in context["candidateQuestIds"]
                    ],
                }],
            },
        }
        evidence = {
            "sceneKey": story_key,
            "missionId": "a1m5",
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "graphEffect": "none",
            "nonOwningContext": context,
            "allowedNonOwningRoute": definition["allowedNonOwningRoute"],
        }
        flow = {"missionStoryConnections": [route], "quests": []}

        rows = gap_queue._deferred_offline_exhausted_isolated_scenes(
            flow,
            {story_key},
            "a1m5",
            {story_key: evidence},
        )
        self.assertEqual([row["sceneKey"] for row in rows], [story_key])

        route["carrierQuestStateContext"]["questStateBranchContexts"][0][
            "noBypass"
        ] = False
        self.assertEqual(
            gap_queue._deferred_offline_exhausted_isolated_scenes(
                flow,
                {story_key},
                "a1m5",
                {story_key: evidence},
            ),
            [],
        )

    def test_declared_e2m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E2M2_RADIOS,
            {"radio_e2m2_7"},
        )
        expected_dialogs = {
            "dlg_e2m2_7": (
                "dlg_e2m2_7",
                "tata_map01_i002",
                1,
                12,
                3,
            ),
            "misc_dlg_e2m2_1d5": (
                "dlg_e2m2_1d5",
                "fabian_map01_lv005",
                0,
                11,
                1,
            ),
            "misc_dlg_e2m2_4d5": (
                "dlg_e2m2_4d5",
                "ailaizha_map01_lv005",
                0,
                7,
                2,
            ),
        }
        for story_key, (
            registry_key,
            proxy_id,
            entry_index,
            line_count,
            option_count,
        ) in expected_dialogs.items():
            definition = (
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]
            )
            self.assertEqual(
                definition.get("registryKey", story_key),
                registry_key,
            )
            self.assertEqual(
                definition["npcProxyConsumer"]["proxyId"],
                proxy_id,
            )
            self.assertEqual(
                definition["npcProxyConsumer"]["entryIndex"],
                entry_index,
            )
            self.assertEqual(
                definition["npcProxyConsumer"]["entry"]["missionId"],
                "",
            )
            self.assertEqual(len(definition["lineIds"]), line_count)
            self.assertEqual(len(definition["optionIds"]), option_count)

    def test_declared_e1m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION["e1m1"],
            {
                "cutscene_e1m1_3_1_test",
                "cutscene_e1m1_4",
                "cutscene_e1m1_6",
            },
        )
        roots = {
            "cutscene_e1m1_3_1_test": (70, 1, 1, 1),
            "cutscene_e1m1_4": (190, 2, 2, 2),
        }
        for story_key, (
            registry_id,
            file_count,
            gameobject_count,
            host_count,
        ) in roots.items():
            definition = (
                gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[story_key]
            )
            self.assertEqual(
                definition["timelineRegistryId"],
                registry_id,
            )
            self.assertEqual(len(definition["files"]), file_count)
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS[story_key],
                gameobject_count,
            )
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS[story_key],
                host_count,
            )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES[
                "cutscene_e1m1_6"
            ]["definitionRowKeys"],
            tuple(
                f"cutscene_e1m1_6_{number:02d}"
                for number in range(1, 6)
            ),
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e1m1_6"
        ]
        self.assertEqual(len(dialog["lineIds"]), 5)
        self.assertEqual(dialog["optionIds"], ())
        self.assertEqual(
            dialog["npcProxyConsumer"]["proxyId"],
            "chen_map01_e1m1Basement1",
        )
        self.assertEqual(
            dialog["npcProxyConsumer"]["entry"]["missionId"],
            "",
        )

    def test_declared_e9m2_offline_frontier_is_exact(self) -> None:
        cutscenes = {
            "cutscene_dung02_dg002_e9m2_lightthewall": 327,
            "cutscene_dung02_dg002_e9m2_zipline01": 325,
            "cutscene_dung02_dg002_e9m2_zipline02": 334,
            "cutscene_dung02_dg002_e9m2_zipline03": 333,
            "cutscene_dung02_dg002_e9m2_zipline06": 326,
        }
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION["e9m2"],
            set(cutscenes),
        )
        for story_key, registry_id in cutscenes.items():
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                    story_key
                ]["timelineRegistryId"],
                registry_id,
            )
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS[story_key],
                1,
            )
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS[story_key],
                1,
            )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E9M2_RADIOS,
            {
                "radio_e9m2_12",
                "radio_e9m2_33",
                "radio_e9m2_34",
                "radio_e9m2_41",
                "radio_e9m2_44",
                "radio_e9m2_49",
                "radio_e9m2_50",
                "radio_e9m2_51",
            },
        )

    def test_declared_e9m3_radio_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E9M3_RADIOS,
            {
                "radio_e9m3_3",
                "radio_e9m3_7",
                "radio_e9m3_8",
                "radio_e9m3_9",
                "radio_e9m3_13",
                "radio_e9m3_20",
                "radio_e9m3_22",
            },
        )

    def test_declared_e8m2_radio_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E8M2_RADIOS,
            {
                "radio_e8m2_1",
                "radio_e8m2_9",
                "radio_e8m2_15",
                "radio_e8m2_16",
            },
        )

    def test_declared_e3m4_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E3M4_RADIOS,
            {"radio_e3m4_1", "radio_e3m4_2"},
        )
        cutscene = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES[
            "cutscene_e3m4_1"
        ]
        self.assertEqual(
            cutscene["definitionRowKeys"],
            tuple(
                f"cutscene_e3m4_1_{number:02d}"
                for number in range(1, 12)
            ),
        )
        self.assertIn("cs_video_e3m5_4", cutscene["consumerBoundary"])
        self.assertIn("cutscene_e3m5_4", cutscene["consumerBoundary"])
        dialog = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_e3m4_9"
        ]
        self.assertEqual(dialog["lineIds"], ("dlg_e3m4_9_001",))
        self.assertEqual(
            dialog["missingAudioIds"],
            ("au_dlg_e3m4_9_001",),
        )

    def test_declared_e1m10_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E1M10_RADIOS,
            {"radio_e1m10_0d2"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "misc_dlg_e1m10_2d7"
        ]
        self.assertEqual(dialog["registryKey"], "dlg_e1m10_2d7")
        self.assertEqual(len(dialog["lineIds"]), 6)
        self.assertEqual(dialog["optionIds"], ())

    def test_declared_e9m4_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E9M4_RADIOS,
            {"radio_e9m4_1", "radio_e9m4_4d5"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e9m4_14"
        ]
        self.assertEqual(
            dialog["lineIds"],
            (
                "dlg_e9m4_14_001",
                "dlg_e9m4_14_002",
                "dlg_e9m4_14_003",
                "dlg_e9m4_14_004",
                "dlg_e9m4_14_005",
                "dlg_e9m4_14_006",
                "dlg_e9m4_14_009",
            ),
        )
        self.assertEqual(dialog["optionIds"], ())
        self.assertEqual(
            dialog["npcProxyConsumer"],
            {
                "proxyId": "lizhui_map02_e9m4",
                "entryIndex": 0,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_e9m4_14",
                },
            },
        )

    def test_declared_e4m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E4M1_RADIOS,
            {"radio_e4m1_106", "radio_e4m1_107"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES[
                "cutscene_e4m1_1"
            ],
            {
                "missionId": "e4m1",
                "definitionRowKeys": (
                    "cutscene_e4m1_1_01",
                    "cutscene_e4m1_1_02",
                ),
            },
        )

    def test_declared_e1m4_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E1M4_RADIOS,
            {
                "radio_e1m4_0d5",
                "radio_e1m4_1d5",
                "radio_e1m4_2d5",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS[
                "radio_e1m4_0d5"
            ],
            {
                "au_radio_e1m4_0d5_001": (
                    "au_radio_e1m4_0d5_001_f",
                    "au_radio_e1m4_0d5_001_m",
                ),
            },
        )

    def test_declared_e2m3_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E2M3_RADIOS,
            {"radio_e2m3_4", "radio_e2m3_6", "radio_e2m3_15"},
        )

    def test_declared_e3m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E3M2_RADIOS,
            {"radio_e3m2_0d5", "radio_e3m2_4d5"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e3m2_3"
        ]
        self.assertEqual(
            dialog["lineIds"],
            ("dlg_e3m2_3_001", "dlg_e3m2_3_002"),
        )
        self.assertEqual(dialog["optionIds"], ())
        self.assertEqual(
            dialog["missingAudioIds"],
            ("au_dlg_e3m2_3_001", "au_dlg_e3m2_3_002"),
        )
        self.assertEqual(
            dialog["npcProxyConsumer"]["proxyId"],
            "angelu_map01_e3m201",
        )
        self.assertNotIn(
            "missionId",
            dialog["npcProxyConsumer"]["entry"],
        )

    def test_declared_e5m4_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E5M4_RADIOS,
            {"radio_e5m4_1", "radio_e5m4_1d5", "radio_e5m4_2"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS,
            {
                "radio_a1m6d1_2": {"au_radio_a1m6d1_2_001"},
                "radio_a1m6d2_1": {"au_radio_a1m6d2_1_001"},
                "radio_a1m6d3_1": {"au_radio_a1m6d3_1_001"},
                "radio_a1m8d3_1": {"au_radio_a1m8d3_1_001"},
                "radio_gm02m2_1": {
                    "au_radio_gm02m2_1_001",
                    "au_radio_gm02m2_1_002",
                },
                "radio_gm02m2_2": {
                    "au_radio_gm02m2_2_001",
                    "au_radio_gm02m2_2_002",
                },
                "radio_gm02m2_2d5": {
                    "au_radio_gm02m2_2d5_001",
                    "au_radio_gm02m2_2d5_002",
                    "au_radio_gm02m2_2d5_003",
                },
                "radio_gm02m2_3": {
                    "au_radio_gm02m2_3_001",
                    "au_radio_gm02m2_3_002",
                },
                "radio_gm02m2_4": {"au_radio_gm02m2_4_001"},
                "radio_gm02m2_5": {"au_radio_gm02m2_5_001"},
                "radio_gm02m2_6": {"au_radio_gm02m2_6_001"},
                "radio_gm02m2_7": {"au_radio_gm02m2_7_001"},
                "radio_gm02m2_10": {
                    "au_radio_gm02m2_10_001",
                    "au_radio_gm02m2_10_002",
                },
                "radio_gm02m3_1": {"au_radio_gm02m3_1_001"},
                "radio_gm02m3_2": {"au_radio_gm02m3_2_002"},
                "radio_gm02m3_3": {"au_radio_gm02m3_3_003"},
                "radio_gm02m3_4": {"au_radio_gm02m3_4_004"},
                "radio_gm02m3_5": {"au_radio_gm02m3_5_001"},
                "radio_gm02m13_3": {"au_radio_gm02m13_3_001"},
                "radio_gm02m13_4": {"au_radio_gm02m13_4_001"},
                "radio_gm02m13_5": {"au_radio_gm02m13_5_001"},
                "radio_gm02m14_1": {"au_radio_gm02m14_1_001"},
                "radio_gm02m14_12": {"au_radio_gm02m14_12_001"},
                "radio_gm02m15_9": {
                    f"au_radio_gm02m15_9_{number:03d}"
                    for number in range(1, 5)
                },
                "radio_gm02m15_12": {
                    "au_radio_gm02m15_12_001",
                    "au_radio_gm02m15_12_002",
                },
                "radio_gm02m17_2": {"au_radio_gm02m17_2_001"},
                "radio_gm02m17_4": {"au_radio_gm02m17_4_001"},
                "radio_gm01m6_0d5": {
                    "au_radio_gm01m6_0d5_001",
                    "au_radio_gm01m6_0d5_002",
                },
                "radio_gm01m6_4d5": {"au_radio_gm01m6_4d5_001"},
                "radio_gm01m6_6": {"au_radio_gm01m6_6_001"},
                "radio_gm01m7_9": {
                    f"au_radio_gm01m7_9_{number:03d}"
                    for number in range(1, 13)
                },
                "radio_gm01m16_8": {"au_radio_gm01m16_8_001"},
                "radio_gm01m16_13": {
                    f"au_radio_gm01m16_13_{number:03d}"
                    for number in range(1, 4)
                },
                "radio_gm01m16_14": {"au_radio_gm01m16_14_001"},
                "radio_gm01m17_4": {"au_radio_gm01m17_4_001"},
                "radio_gm01m17_5": {"au_radio_gm01m17_5_001"},
                "radio_gm01m17_9": {"au_radio_gm01m17_9_001"},
                "radio_gm01m3_3d8": {"au_radio_gm01m3_3d8_001"},
                "radio_gm01m4_1": {"au_radio_gm01m4_1_001"},
                "radio_gm01m20_1": {"au_radio_gm01m20_1_001"},
                "radio_gm01m20_2": {"au_radio_gm01m20_2_001"},
                "radio_gm01m20_3": {"au_radio_gm01m20_3_001"},
                "radio_gm01m20_4": {"au_radio_gm01m20_4_001"},
                "radio_gm01m22_1d2": {"au_radio_gm01m22_1d2_001"},
                "radio_gm01m22_1d3": {"au_radio_gm01m22_1d3_001"},
                "radio_gm01m24_1d5": {"au_radio_gm01m24_1d5_001"},
                "radio_gm01m24_2": {"au_radio_gm01m24_2_002"},
                "radio_gm01m24_3": {"au_radio_gm01m24_3_003"},
                "radio_gm01m24_4": {"au_radio_gm01m24_4_004"},
                "radio_gm01m25_1d5": {"au_radio_gm01m25_1d5_001"},
                "radio_gm01m25_2": {"au_radio_gm01m25_2_002"},
                "radio_gm01m25_3": {"au_radio_gm01m25_3_003"},
                "radio_gm01m25_4": {"au_radio_gm01m25_4_004"},
                "radio_gm01m26_1d5": {"au_radio_gm01m26_1d5_001"},
                "radio_gm01m26_2": {"au_radio_gm01m26_2_002"},
                "radio_gm01m26_3": {"au_radio_gm01m26_3_003"},
                "radio_gm01m26_4": {"au_radio_gm01m26_4_004"},
                "radio_gm01m27_1": {
                    "au_radio_gm01m27_1_001",
                    "au_radio_gm01m27_1_002",
                },
                "radio_gm01m27_2": {"au_radio_gm01m27_2_001"},
                "radio_gm01m27_3": {"au_radio_gm01m27_3_001"},
                "radio_gm01m5_1": {
                    "au_radio_gm01m5_1_001",
                    "au_radio_gm01m5_1_002",
                },
                "radio_gm01m5_2": {"au_radio_gm01m5_2_001"},
                "radio_gm01m5_3": {"au_radio_gm01m5_3_001"},
                "radio_gm01m5_4": {"au_radio_gm01m5_4_001"},
                "radio_gm02m1_1": {
                    "au_radio_gm02m1_1_001",
                    "au_radio_gm02m1_1_002",
                },
                "radio_gm02m1_2": {"au_radio_gm02m1_2_001"},
                "radio_gm02m1_6": {
                    "au_radio_gm02m1_6_001",
                    "au_radio_gm02m1_6_002",
                },
                "radio_gm02m1_7": {
                    "au_radio_gm02m1_7_001",
                    "au_radio_gm02m1_7_002",
                },
                "radio_gm02m1_8": {"au_radio_gm02m1_8_001"},
                "radio_gm02m20_7": {"au_radio_gm02m20_7_001"},
                "radio_gm02m20_8": {
                    "au_radio_gm02m20_8_001",
                    "au_radio_gm02m20_8_002",
                },
                "radio_gm02m20_10": {
                    "au_radio_gm02m20_10_001",
                    "au_radio_gm02m20_10_002",
                },
                "radio_gm02m20_11": {"au_radio_gm02m20_11_001"},
                "radio_gm02m20_13": {
                    "au_radio_gm02m20_13_001",
                    "au_radio_gm02m20_13_002",
                },
                "radio_gm02m23_2": {"au_radio_gm02m23_2_001"},
                "radio_e5m4_1": {
                    f"au_radio_e5m4_1_{number:03d}"
                    for number in range(1, 5)
                },
                "radio_e5m4_1d5": {
                    f"au_radio_e5m4_1d5_{number:03d}"
                    for number in range(1, 4)
                },
                "radio_e5m4_2": {
                    f"au_radio_e5m4_2_{number:03d}"
                    for number in range(1, 4)
                },
                "radio_e5m5_1": {
                    "au_radio_e5m5_1_001",
                    "au_radio_e5m5_1_002",
                },
                "radio_e5m5_2": {"au_radio_e5m5_2_001"},
            },
        )

    def test_declared_e0m2_offline_frontier_is_exact(self) -> None:
        cutscenes = {
            "cutscene_e0m2_3_3": (
                262,
                "cutscene_e0m2_3_3_p8B24FED0A23FB54B.json",
                "cutscene_e0m2_3_3",
            ),
            "cutscene_e0m2_99": (
                237,
                "m_cutscene_e0m2_99_pEA3DAF65D39D43C5.json",
                "m_cutscene_e0m2_99",
            ),
        }
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION["e0m2"],
            set(cutscenes),
        )
        for story_key, (
            registry_id,
            filename,
            definition_name,
        ) in cutscenes.items():
            definition = (
                gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[story_key]
            )
            self.assertEqual(
                definition["timelineRegistryId"],
                registry_id,
            )
            self.assertEqual(len(definition["files"]), 1)
            self.assertEqual(definition["files"][0][0], filename)
            self.assertEqual(definition["files"][0][2], definition_name)
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS[story_key],
                1,
            )
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS[story_key],
                1,
            )

    def test_declared_e8m3_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E8M3_RADIOS,
            {"radio_e8m3_27"},
        )

    def test_declared_e8m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E8M1_RADIOS,
            {"radio_e8m1_9"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e8m1_10"
        ]
        self.assertEqual(len(dialog["lineIds"]), 13)
        self.assertEqual(len(dialog["optionIds"]), 5)
        self.assertEqual(
            dialog["npcProxyConsumer"],
            {
                "proxyId": "ximo_map02_default",
                "entryIndex": 0,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_e8m1_10",
                    "missionId": "",
                },
            },
        )

    def test_declared_e10m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E10M2_RADIOS,
            {"radio_e10m2_1"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e10m2_8"
        ]
        self.assertEqual(dialog["lineIds"], ("dlg_e10m2_8_001",))
        self.assertEqual(dialog["optionIds"], ())
        self.assertNotIn("npcProxyConsumer", dialog)

    def test_declared_e8m5_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E8M5_RADIOS,
            {"radio_e8m5_4"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e8m5_6"
        ]
        self.assertEqual(
            dialog["lineIds"],
            ("dlg_e8m5_6_001", "dlg_e8m5_6_002"),
        )
        self.assertEqual(dialog["optionIds"], ())
        self.assertEqual(
            dialog["ownedTimeline"],
            {
                "timeline": "dlgtl_e8m5_6_sub_1",
                "sourceFile": "CAB-42aad6a7bfd8d23c4e3f6c1e0d515744",
                "trackPathId": -7243836360867709977,
                "fullLineIds": (
                    "dlg_e8m5_6_001",
                    "dlg_e8m5_6_002",
                ),
            },
        )

    def test_declared_e3m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E3M1_RADIOS,
            {"radio_e3m1_3"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION["e3m1"],
            {"cutscene_e3m1_1"},
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
            "cutscene_e3m1_1"
        ]
        self.assertEqual(definition["timelineRegistryId"], 191)
        self.assertEqual(len(definition["files"]), 2)
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS[
                "cutscene_e3m1_1"
            ],
            2,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS[
                "cutscene_e3m1_1"
            ],
            2,
        )

    def test_declared_e2m5d5_offline_frontier_is_exact(self) -> None:
        expected = {
            "misc_dlg_e2m5d5_1d5": {
                "registryKey": "dlg_e2m5d5_1d5",
                "lineCount": 3,
                "proxyId": "pelica_map01_e2m5d5",
                "missionIdPresent": False,
            },
            "misc_dlg_e2m5d5_1d7": {
                "registryKey": "dlg_e2m5d5_1d7",
                "lineCount": 5,
                "proxyId": "chen_map01_e2m5d5",
                "missionIdPresent": True,
            },
        }
        for story_key, facts in expected.items():
            definition = (
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]
            )
            self.assertEqual(definition["missionId"], "e2m5d5")
            self.assertEqual(
                definition["registryKey"],
                facts["registryKey"],
            )
            self.assertEqual(len(definition["lineIds"]), facts["lineCount"])
            self.assertEqual(definition["optionIds"], ())
            consumer = definition["npcProxyConsumer"]
            self.assertEqual(consumer["proxyId"], facts["proxyId"])
            self.assertEqual(consumer["entryIndex"], 0)
            self.assertEqual(
                "missionId" in consumer["entry"],
                facts["missionIdPresent"],
            )
            self.assertFalse(consumer["entry"].get("missionId"))

    def test_exact_lua_controller_playback_closes_isolated_cutscene(
        self,
    ) -> None:
        lua_file = (
            "Lua/Data/LuaScripts/Phase/GenderChange/"
            "PhaseGenderChange.lua"
        )
        manifest = {
            "cutscene_e1m10_1": {
                "attachmentStatus": "trigger_known_owner_unresolved",
                "key": "cutscene_e1m10_1",
                "nominalMissionId": "e1m10",
                "routes": [{
                    "causality": "playback_owner_unresolved",
                    "confidence": "shipped_lua_literal_plus_native_entry",
                    "direction": "playback",
                    "evidenceTier": "direct",
                    "luaCall": "GameAction.PlayCutscene",
                    "luaFile": lua_file,
                    "luaSymbol": "CUT_SCENE_ID",
                    "missionId": None,
                    "nativeEntry":
                        "Beyond.Gameplay.Actions.GameAction::PlayCutscene",
                    "ownerStatus": "unresolved",
                    "phase": "gender_change",
                    "questId": None,
                    "questTriggerStatus":
                        "no_mission_or_quest_identity_serialized",
                    "relation": "lua_controller_playback",
                    "scope": "phase",
                    "serverExchange": False,
                    "sourceFiles": [lua_file],
                    "steps": [
                        {
                            "id": lua_file,
                            "kind": "luaController",
                            "phase": "gender_change",
                        },
                        {
                            "id":
                                "Beyond.Gameplay.Actions.GameAction::"
                                "PlayCutscene",
                            "kind": "nativePlayback",
                        },
                    ],
                    "storyKey": "cutscene_e1m10_1",
                }],
            },
        }
        rows = (
            gap_queue
            ._closed_exact_lua_controller_playback_isolated_scenes(
                manifest,
                {"cutscene_e1m10_1"},
                "e1m10",
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sceneKey"], "cutscene_e1m10_1")
        self.assertEqual(rows[0]["relation"], "lua_controller_playback")
        self.assertEqual(rows[0]["graphEffect"], "none")
        self.assertEqual(
            gap_queue
            ._closed_exact_lua_controller_playback_isolated_scenes(
                {
                    "cutscene_e1m10_1": {
                        **manifest["cutscene_e1m10_1"],
                        "routes": [{
                            **manifest["cutscene_e1m10_1"]["routes"][0],
                            "missionId": "e1m10",
                        }],
                    },
                },
                {"cutscene_e1m10_1"},
                "e1m10",
            ),
            [],
        )

    def test_declared_e6m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M2_RADIOS,
            {"radio_e6m2_3", "radio_e6m2_7"},
        )
        expected_dialogs = {
            "dlg_e6m2_1": (
                "zhuangfy_indie_dg005_e6m1Final",
                0,
                17,
                5,
                True,
            ),
            "dlg_e6m2_2": (
                "mifu_indie_dg005_e6m1DianTiKou",
                2,
                6,
                2,
                False,
            ),
        }
        for story_key, (
            proxy_id,
            entry_index,
            line_count,
            option_count,
            has_mission_id,
        ) in expected_dialogs.items():
            definition = (
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]
            )
            consumer = definition["npcProxyConsumer"]
            self.assertEqual(consumer["proxyId"], proxy_id)
            self.assertEqual(consumer["entryIndex"], entry_index)
            self.assertEqual(
                "missionId" in consumer["entry"],
                has_mission_id,
            )
            self.assertEqual(len(definition["lineIds"]), line_count)
            self.assertEqual(len(definition["optionIds"]), option_count)

    def test_declared_dialog_definitions_preserve_shared_timeline_boundary(
        self,
    ) -> None:
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS),
            {
                "dlg_a1m2_4",
                "dlg_a1m8d3_2",
                "dlg_e5m0d5_1",
                "dlg_e1m1_6",
                "dlg_e1m2_6",
                "misc_dlg_e1m3_5d5",
                "misc_dlg_e1m10_2d7",
                "dlg_e2m2_7",
                "misc_dlg_e2m2_1d5",
                "misc_dlg_e2m2_4d5",
                "dlg_e2m4_10",
                "dlg_e2m5_6",
                "misc_dlg_e2m5d5_1d5",
                "misc_dlg_e2m5d5_1d7",
                "dlg_e2m6_12",
                "dlg_e2m8d5_2",
                "dlg_e2m8d5_3",
                "dlg_e3m2_3",
                "dlg_e3m3_12",
                "dlg_e3m3_13",
                "dlg_e5m1_3",
                "dlg_e5m2_2",
                "dlg_e5m2_8",
                "misc_dlg_e5m2_3d5",
                "dlg_e6m1_14",
                "dlg_e6m1_15",
                "dlg_e6m2_1",
                "dlg_e6m2_2",
                "dlg_e6m3_6",
                "dlg_e6m3_12",
                "misc_dlg_e6m3_3d5",
                "dlg_e9m4_14",
                "dlg_e7m2_11",
                "dlg_e7m2_13",
                "dlg_e7m3_13",
                "dlg_e7m3_15",
                "dlg_e7m3_16",
                "dlg_e7m4_7",
                "dlg_e8m1_10",
                "dlg_e8m5_6",
                "dlg_e10m1_7",
                "dlg_e10m2_8",
                "dlg_e10m3_3",
                "dlg_e10m3_9",
                "dlg_e10m4_21",
                "dlg_e11m2_17",
                "dlg_e11m2_18",
                "dlg_e11m5_9",
                "dlg_e11m5_10",
                "dlg_e11m5_11",
                "dlg_e11m5_12",
                "dlg_e11m5_13",
                "dlg_e11m5_18",
                "dlg_e11m5_19",
                "dlg_e11m6_9",
                "dlg_e11m8_9",
                "dlg_e11m8d5_1",
                "misc_dlg_gm01m3_1d5",
                "dlg_gm01m4_7",
                "misc_dlg_gm01m4_3d5",
                "dlg_gm01m13_2",
                "dlg_gm01m13_3",
                "dlg_gm01m2_1",
                "dlg_gm01m2_2",
                "dlg_gm01m2_3",
                "dlg_gm01m6_6",
                "dlg_gm01m6_7",
                "misc_dlg_gm01m6_1d5",
                "misc_dlg_gm01m6_3d7",
                "misc_dlg_gm01m6_4d5",
                "misc_dlg_gm01m6_4d7",
                "dlg_gm01m7_1",
                "dlg_gm01m7_2",
                "dlg_gm01m7_3",
                "dlg_gm01m7_5",
                "dlg_gm01m7_7",
                "dlg_gm01m22_6",
                "dlg_gm01m22_7",
                "dlg_gm01m22_8",
                "misc_dlg_gm01m22_2d5",
                "misc_dlg_gm01m22_3d2",
                "misc_dlg_gm01m22_3d8",
                "misc_dlg_gm01m22_4d0",
                "dlg_gm01m12_1",
                "dlg_gm01m12_3",
                "dlg_gm01m12_6",
                "dlg_gm01m20_1",
                "dlg_gm01m20_5",
                "dlg_gm01m20_6",
                "dlg_gm01m20_7",
                "dlg_gm01m24_1",
                "dlg_gm01m24_2",
                "dlg_gm01m24_3",
                "dlg_gm01m25_1",
                "dlg_gm01m25_2",
                "dlg_gm01m25_3",
                "dlg_gm01m26_1",
                "dlg_gm01m26_2",
                "dlg_gm01m26_3",
                "dlg_gm01m26_5",
                "dlg_gm02m23_3",
                "dlg_gm02m23_10",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_POSITIVE_DIALOG_KEYS,
            {
                "dlg_e10m3_9",
                "dlg_e11m5_9",
                "dlg_e11m8_9",
            },
        )
        shared = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e11m6_9"
        ]["sharedTimeline"]
        self.assertEqual(shared["ownerDialogKey"], "dlg_e11m5_9")
        self.assertEqual(shared["trackPathId"], 5795311945645305682)
        self.assertEqual(
            shared["embeddedLineIds"],
            (
                "dlg_e11m6_9_005",
                "dlg_e11m6_9_006",
                "dlg_e11m6_9_007",
                "dlg_e11m6_9_003",
                "dlg_e11m6_9_008",
                "dlg_e11m6_9_004",
            ),
        )

    def test_declared_e1m3_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E1M3_RADIOS,
            {
                "radio_e1m3_3",
                "radio_e1m3_4",
                "radio_e1m3_7",
                "radio_e1m3_18",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e1m3_1"
            ]["timelineRegistryId"],
            89,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS[
                "cutscene_e1m3_1"
            ],
            1,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "misc_dlg_e1m3_5d5"
            ]["registryKey"],
            "dlg_e1m3_5d5",
        )

    def test_declared_e1m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E1M2_RADIOS,
            {
                "radio_e1m2_2d5",
                "radio_e1m2_3d5",
                "radio_e1m2_5",
                "radio_e1m2_7d7",
            },
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e1m2_6"
        ]
        self.assertEqual(len(dialog["lineIds"]), 4)
        self.assertEqual(
            dialog["optionIds"],
            ("option_dlg_e1m2_6_1_001",),
        )
        self.assertEqual(
            dialog["npcProxyConsumer"]["proxyId"],
            "chen_map01_e1m2Factory",
        )
        self.assertEqual(
            dialog["npcProxyConsumer"]["entry"]["missionId"],
            "",
        )
        self.assertEqual(
            dialog["extraConfigSha256"],
            "89B14D65387F1567990671228000339E8AEC0EE76D7529324C3AD2204F490D48",
        )

    def test_declared_e10m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E10M1_RADIOS,
            {
                "radio_e10m1_6",
                "radio_e10m1_9",
            },
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e10m1_7"
        ]
        self.assertEqual(dialog["lineIds"], ("dlg_e10m1_7_001",))
        self.assertEqual(dialog["optionIds"], ())
        self.assertEqual(
            dialog["missingAudioIds"],
            ("au_dlg_e10m1_7_001",),
        )
        self.assertEqual(
            dialog["extraConfigSha256"],
            "95BB5B09DEA22F63EFBB5506FBF1900AFC43D7DC3C6411F8281E33216DA7E5FA",
        )

    def test_declared_e5m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E5M2_RADIOS,
            {"radio_e5m2_3"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e5m2_2"
        ]
        self.assertEqual(len(dialog["lineIds"]), 29)
        self.assertEqual(
            dialog["ownedTimeline"]["timeline"],
            "dlgtl_e5m2_2_sub_1",
        )
        self.assertEqual(
            dialog["ownedTimeline"]["trackPathId"],
            -6721394561739517947,
        )
        self.assertEqual(
            len(dialog["ownedTimeline"]["fullLineIds"]),
            29,
        )
        self.assertEqual(
            dialog["missingAudioIds"],
            ("au_dlg_e5m2_2_003",),
        )
        self.assertEqual(
            dialog["npcProxyConsumer"]["entryIndex"],
            1,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e5m2_8"
            ]["optionIds"],
            (
                "option_dlg_e5m2_8_1_001",
                "option_dlg_e5m2_8_1_002",
            ),
        )
        misc = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "misc_dlg_e5m2_3d5"
        ]
        self.assertEqual(misc["registryKey"], "dlg_e5m2_3d5")
        self.assertEqual(misc["npcProxyConsumer"]["entryIndex"], 1)
        self.assertNotIn("missionId", misc["npcProxyConsumer"]["entry"])

    def test_declared_e5m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E5M1_RADIOS,
            {
                "radio_e5m1_7",
                "radio_e5m1_10d8",
                "radio_e5m1_12",
                "radio_e5m1_15",
            },
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e5m1_3"
        ]
        self.assertEqual(
            dialog["lineIds"],
            ("dlg_e5m1_3_001", "dlg_e5m1_3_002"),
        )
        self.assertEqual(
            dialog["optionIds"],
            (
                "option_dlg_e5m1_3_1_001",
                "option_dlg_e5m1_3_1_002",
            ),
        )
        self.assertEqual(dialog["npcProxyConsumer"]["entryIndex"], 1)
        self.assertEqual(
            dialog["npcProxyConsumer"]["proxyId"],
            "pelica_base01_lv001_e5m1back",
        )

    def test_declared_e2m4_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E2M4_RADIOS,
            {
                "radio_e2m4_4",
                "radio_e2m4_5d5",
                "radio_e2m4_11",
                "radio_e2m4_14",
                "radio_e2m4_15",
                "radio_e2m4_19",
                "radio_e2m4_22",
            },
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e2m4_10"
        ]
        self.assertEqual(len(dialog["lineIds"]), 5)
        self.assertEqual(
            dialog["optionIds"],
            (
                "option_dlg_e2m4_10_1_001",
                "option_dlg_e2m4_10_1_002",
            ),
        )

    def test_declared_e2m6_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E2M6_RADIOS,
            {"radio_e2m6_2", "radio_e2m6_7d2", "radio_e2m6_7d4"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e2m6_12"
        ]
        self.assertEqual(len(dialog["lineIds"]), 24)
        self.assertEqual(len(dialog["optionIds"]), 4)
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION["e2m6"],
            {"cutscene_e2m6_designer_AngelSurrounding"},
        )
        self.assertNotIn(
            "cutscene_e2m6_designer_anchorperish_001",
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS,
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
                    "dlg_e2m6_18"
                ]["lineIds"]
            ),
            7,
        )

    def test_declared_e2m7_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E2M7_RADIOS,
            {
                "radio_e2m7_9",
                "radio_e2m7_10",
                "radio_e2m7_16",
            },
        )

    def test_declared_e2m5_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E2M5_RADIOS,
            {
                "radio_e2m5_5",
                "radio_e2m5_27",
                "radio_e2m5_29",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION["e2m5"],
            {
                "cutscene_e2m5_2",
                "cutscene_e2m5_3",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES[
                "cutscene_e2m5_2"
            ]["definitionRowKeys"],
            (
                "cutscene_e2m5_2_01",
                "cutscene_e2m5_2_11",
            ),
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e2m5_6"
        ]
        self.assertEqual(len(dialog["lineIds"]), 6)
        self.assertEqual(len(dialog["optionIds"]), 2)
        self.assertEqual(
            dialog["extraConfigSha256"],
            "ECB4AAE557503DD87DD1D3C02088A41277EE32D977BAE4998BB23D457A1239EF",
        )
        self.assertEqual(
            dialog["npcProxyConsumer"],
            {
                "proxyId": "tata_map01_i008",
                "entryIndex": 0,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_e2m5_6",
                    "missionId": "",
                },
            },
        )

    def test_exact_native_context_isolated_scenes_are_fail_closed(
        self,
    ) -> None:
        trigger_zone = {
            "key": "radio_e1m3_13",
            "relation":
                "radio_trigger_zone_mission_state_playback_context",
            "direction": "context",
            "phase": "mission_state_trigger_zone",
            "confidence": "native_exact_serialized_co_carrier",
            "evidenceTier": "direct",
            "storyOwnerMission": "e1m3",
            "storyBinding": True,
            "ownership": False,
            "missionStateId": "e1m3",
            "missionStateGateRoles": [
                "hideBeforeMissionId",
                "hideCompleteMissionId",
            ],
            "missionStateRolesById": {
                "e1m3": [
                    "hideBeforeMissionId",
                    "hideCompleteMissionId",
                ],
            },
            "nativeMappingId": "radio-zone-test",
            "nativeConsumer": "OnEnter -> GameAction.PlayRadio",
            "unionTag": 9,
            "serializedMemberCount": 7,
            "specificDataListCount": 1,
            "levelIds": ["map01_lv001"],
            "sourceFiles": ["level-data.json"],
            "recordOffset": 10,
            "recordEndOffset": 20,
        }
        patrol_radio = {
            "key": "radio_e1m3_33",
            "relation": "npc_patrol_action_radio_playback_context",
            "direction": "context",
            "phase": "npc_patrol_action",
            "confidence": "native_exact_serialized_patrol_action",
            "evidenceTier": "direct",
            "storyOwnerMission": "e1m3",
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "patrolId": 20001,
            "patrolPointIndex": None,
            "patrolEnvelopeStatus":
                "exact_typed_neighbor_boundaries_partial_point_decode",
            "patrolActionType": 9,
            "serializedMemberCount": 26,
            "patrolSubActionDataStatus": "null",
            "nativeMappingId": "patrol-action-test",
            "nativeConsumer": "_PlayRadioSubAction",
            "levelIds": ["map01_lv001"],
            "sourceFiles": ["level-data.json"],
            "patrolRecordOffset": 100,
            "radioActionRecordOffset": 200,
            "radioActionRecordEndOffset": 300,
            "nextPatrolRecordOffset": 400,
        }
        tracked_world_entity = {
            "key": "radio_e1m3_32",
            "relation":
                "mission_tracked_world_entity_levelscript_context",
            "direction": "context",
            "phase": "local_leader_trigger_world_entity_context",
            "confidence": "native_exact_mission_navigation_context",
            "evidenceTier": "derived_exact_foreign_key",
            "storyOwnerMission": "e1m3",
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "candidateQuestIds": ["e1m3_q#44"],
            "trackingRows": [{
                "missionId": "e1m3",
                "questId": "e1m3_q#44",
            }],
            "worldEntityIds": ["2100130040"],
            "levelIds": ["map01_lv001"],
            "scriptIds": ["2100130014"],
            "sourceFiles": ["level-script.json"],
            "worldEntityLevelScriptEvidence": [{
                "nativeAction": "PlayRadio",
                "playbackRecordOffset": 711,
                "listener": {
                    "status": "exact_serialized_control_path",
                    "path": [{
                        "actionName": "PlayRadio",
                        "recordClass": "play_radio",
                        "texts": ["radio_e1m3_32"],
                    }],
                },
            }],
        }
        rows = gap_queue._closed_exact_native_context_isolated_scenes(
            {
                "missionStoryConnections": [
                    trigger_zone,
                    patrol_radio,
                    tracked_world_entity,
                ],
            },
            {"radio_e1m3_13", "radio_e1m3_32", "radio_e1m3_33"},
            "e1m3",
        )
        self.assertEqual(
            [row["sceneKey"] for row in rows],
            ["radio_e1m3_13", "radio_e1m3_32", "radio_e1m3_33"],
        )
        invalid_tracked = dict(tracked_world_entity)
        invalid_tracked["questPlayback"] = True
        self.assertEqual(
            [
                row["sceneKey"]
                for row in (
                    gap_queue
                    ._closed_exact_native_context_isolated_scenes(
                        {
                            "missionStoryConnections": [
                                trigger_zone,
                                patrol_radio,
                                invalid_tracked,
                            ],
                        },
                        {
                            "radio_e1m3_13",
                            "radio_e1m3_32",
                            "radio_e1m3_33",
                        },
                        "e1m3",
                    )
                )
            ],
            ["radio_e1m3_13", "radio_e1m3_33"],
        )
        gm_trigger = dict(trigger_zone)
        gm_trigger.update({
            "key": "radio_gm01m16_1",
            "storyOwnerMission": "gm01m16",
            "missionStateId": "gm01m16",
            "missionStateGateRoles": ["hideAfterMissionId"],
            "missionStateRolesById": {
                "e2m5": ["hideBeforeMissionId"],
                "gm01m16": ["hideAfterMissionId"],
            },
        })
        self.assertEqual(
            [
                row["sceneKey"]
                for row in gap_queue._closed_exact_native_context_isolated_scenes(
                    {"missionStoryConnections": [gm_trigger]},
                    {"radio_gm01m16_1"},
                    "gm01m16",
                )
            ],
            ["radio_gm01m16_1"],
        )
        invalid_patrol = dict(patrol_radio)
        invalid_patrol["patrolActionType"] = 8
        self.assertEqual(
            gap_queue._closed_exact_native_context_isolated_scenes(
                {"missionStoryConnections": [invalid_patrol]},
                {"radio_e1m3_33"},
                "e1m3",
            ),
            [],
        )

    def test_declared_e7m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E7M2_RADIOS,
            {
                "radio_e7m2_2",
                "radio_e7m2_9",
                "radio_e7m2_12",
                "radio_e7m2_18",
            },
        )
        cutscene = gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
            "cutscene_e7m2_designer_QingBoZhai"
        ]
        self.assertEqual(cutscene["timelineRegistryId"], 406)
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS[
                "cutscene_e7m2_designer_QingBoZhai"
            ],
            1,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e7m2_13"
            ]["missingAudioIds"],
            (
                "au_dlg_e7m2_13_001",
                "au_dlg_e7m2_13_002",
            ),
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS)
            & {"text_e7m2_2", "text_e7m2_3"},
            {"text_e7m2_2"},
        )

    def test_declared_e3m3_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E3M3_RADIOS,
            {
                "radio_e3m3_1d5",
                "radio_e3m3_1d7",
                "radio_e3m3_2",
                "radio_e3m3_2d5",
                "radio_e3m3_3",
                "radio_e3m3_4d5",
                "radio_e3m3_5",
                "radio_e3m3_6",
            },
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e3m3_12"
        ]
        self.assertEqual(len(dialog["lineIds"]), 18)
        self.assertEqual(
            dialog["optionIds"],
            (
                "option_dlg_e3m3_12_1_001",
                "option_dlg_e3m3_12_1_002",
                "option_dlg_e3m3_12_1_003",
                "option_dlg_e3m3_12_1_004",
            ),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e3m3_13"
            ]["lineIds"],
            (
                "dlg_e3m3_13_001",
                "dlg_e3m3_13_002",
                "dlg_e3m3_13_003",
                "dlg_e3m3_13_004",
            ),
        )

    def test_declared_e0m0_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E0M0_RADIOS,
            {"radio_e0m0_9d5", "radio_e0m0_10", "radio_e0m0_21"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS[
                "radio_e0m0_10"
            ],
            {
                f"au_radio_e0m0_10_{number:03d}": (
                    f"au_radio_e0m0_10_{number:03d}_f",
                    f"au_radio_e0m0_10_{number:03d}_m",
                )
                for number in range(1, 4)
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e0m0_11111"
            ],
            {"timelineRegistryId": None, "files": ()},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e0m0_1"
            ]["timelineRegistryId"],
            158,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_e0m0_1"
            ]["contentTextIds"],
            (
                2511221695470576053,
                5177474080784617714,
                8007409330529367903,
            ),
        )

    def test_declared_e10m3_partial_frontier_is_exact(self) -> None:
        self.assertNotIn(
            "e10m3",
            gap_queue.OFFLINE_EXHAUSTION_RADIOS_BY_MISSION,
        )
        owned = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e10m3_9"
        ]["ownedTimeline"]
        self.assertEqual(
            owned["trackPathIds"],
            (-3513721562143553181, 4679925721215633763),
        )
        self.assertEqual(len(owned["fullLineIds"]), 19)
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS)
            & {"text_e10m3_4", "text_e10m3_6", "text_e10m3_8"},
            {"text_e10m3_4", "text_e10m3_6", "text_e10m3_8"},
        )
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            {
                "missionStoryConnections": [{
                    "key": "radio_e10m3_10",
                    "relation": "focus_mode_interact_locked_radio",
                    "direction": "context",
                    "phase": "interact_locked",
                    "confidence": "direct_mission_scope",
                    "storyOwnerMission": "e10m3",
                    "focusModeField": "radioIdInteractLocked",
                    "focusModeId": "Zfy_e10m3",
                    "focusModeMissionId": "e10m3d5",
                    "subDataParentId": 22800780000,
                }],
            },
            {"radio_e10m3_10"},
            "e10m3",
        )
        self.assertEqual(
            [(row["sceneKey"], row["relation"]) for row in rows],
            [(
                "radio_e10m3_10",
                "focus_mode_interact_locked_radio",
            )],
        )
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            set(text_only),
            {
                "dlg_a1m11_3",
                "dlg_a1m7_2",
                "dlg_a1m7_12",
                "dlg_a1m5_5",
                "dlg_e3m4_9",
                "dlg_e10m4_16",
                "dlg_e10m4_17",
                "dlg_e10m3_10",
                "dlg_e10m3_11",
                "dlg_e10m3_12",
                "dlg_e2m6_18",
                "dlg_e11m8_13",
                "dlg_e11m8_14",
                "dlg_e11m8d5_2",
                "dlg_gm02m2_1",
                "dlg_gm02m2_2",
                "dlg_gm02m2_3",
                "dlg_gm02m2_4",
                "dlg_gm02m3_1",
                "dlg_gm02m3_2",
                "dlg_gm02m3_3",
                "dlg_gm02m3_4",
                "dlg_gm02m3_5",
                "dlg_gm02m8_2",
                "dlg_gm02m8_3",
                "dlg_gm02m8_4",
                "dlg_gm01m12_8",
                "dlg_gm01m15_7",
                "dlg_gm02m1_1",
                "dlg_gm02m1_2",
                "misc_dlg_gm02m1_1d5",
                "dlg_gm01m5_1",
                "dlg_gm01m5_2",
                "dlg_gm01m5_3",
                "dlg_gm01m5_4",
                "dlg_gm01m2_5",
                "dlg_gm01m13_5",
                "dlg_gm01m24_5",
                "dlg_gm01m25_5",
                "dlg_gm01m14_7",
                "dlg_gm01m27_1",
                "dlg_gm01m27_2",
                "dlg_gm01m27_3",
            },
        )
        self.assertEqual(len(text_only["dlg_e10m3_10"]["lineIds"]), 8)
        self.assertEqual(len(text_only["dlg_e10m3_11"]["lineIds"]), 4)
        self.assertEqual(len(text_only["dlg_e10m3_12"]["lineIds"]), 16)

    def test_declared_gm02m8_text_only_progress_dialogs_are_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        for number in (2, 3, 4):
            story_key = f"dlg_gm02m8_{number}"
            self.assertEqual(
                text_only[story_key],
                {
                    "missionId": "gm02m8",
                    "dialogIdRegistrationStatus": "absent",
                    "lineIds": (
                        f"{story_key}_001",
                        f"{story_key}_002",
                    ),
                    "missingAudioIds": (
                        f"au_{story_key}_001",
                        f"au_{story_key}_002",
                    ),
                },
            )
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS[story_key],
                story_key,
            )
        topology = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m8"
        ]
        self.assertEqual(
            topology["mainPathQuestIds"],
            ("gm02m8_q#1", "gm02m8_q#2", "gm02m8_q#3"),
        )
        self.assertEqual(
            topology["prevQuestIdsByQuest"],
            {
                "gm02m8_q#1": (),
                "gm02m8_q#2": ("gm02m8_q#1",),
                "gm02m8_q#3": ("gm02m8_q#2",),
            },
        )

    def test_declared_a1m7_text_only_branch_frontier_is_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            text_only["dlg_a1m7_2"]["lineIds"],
            ("dlg_a1m7_2_001", "dlg_a1m7_2_002"),
        )
        self.assertEqual(
            set(text_only["dlg_a1m7_2"]["optionRows"]),
            {
                "option_dlg_a1m7_2_1_001",
                "option_dlg_a1m7_2_2_001",
                "option_dlg_a1m7_2_2_002",
            },
        )
        self.assertEqual(text_only["dlg_a1m7_12"]["optionRows"], {})
        popup = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            "text_a1m6d5_1"
        ]
        self.assertEqual(popup["readingPopupRowId"], "rp_text_a1m6d5_1")
        self.assertEqual(popup["iconType"], 3)
        self.assertEqual(len(popup["contentTextIds"]), 14)

    def test_a1m7_option_definition_validator_reports_exact_failure(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports"
            / "mission_order"
            / "source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        self.assertEqual(
            index["dlg_a1m7_2"]["optionRouteStatus"],
            "definitions_present_route_unresolved",
        )

        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_a1m7_2"
        ]
        broken_rows = {
            key: dict(value)
            for key, value in definition["optionRows"].items()
        }
        broken_rows["option_dlg_a1m7_2_1_001"] = {
            **broken_rows["option_dlg_a1m7_2_1_001"],
            "iconType": "Changed",
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_a1m7_2": {**definition, "optionRows": broken_rows}},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        self.assertEqual(
            failed_status["status"],
            "inactive_text_only_dialog_definition_validation_failed",
        )
        failure = next(
            row for row in failed_status["validationFailures"]
            if row["storyKey"] == "dlg_a1m7_2"
        )
        self.assertEqual(failure["validator"], "offlineTextOnlyDialogDefinition")
        self.assertEqual(failure["gate"], "exactDialogOptionDefinitions")
        self.assertIn("dialogOptionTable", failure["sourceSha256"])
        self.assertEqual(
            failure["actual"]["option_dlg_a1m7_2_1_001"]["iconType"],
            "Default",
        )

    def test_declared_gm02m2_table_only_branch_frontier_is_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            {
                key: (
                    len(text_only[key]["lineIds"]),
                    len(text_only[key]["optionRows"]),
                    text_only[key]["dialogIdRegistrationStatus"],
                )
                for key in (
                    "dlg_gm02m2_1",
                    "dlg_gm02m2_2",
                    "dlg_gm02m2_3",
                    "dlg_gm02m2_4",
                )
            },
            {
                "dlg_gm02m2_1": (7, 3, "present_table_only"),
                "dlg_gm02m2_2": (1, 2, "present_table_only"),
                "dlg_gm02m2_3": (5, 3, "present_table_only"),
                "dlg_gm02m2_4": (3, 1, "present_table_only"),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M2_RADIOS,
            {
                "radio_gm02m2_1",
                "radio_gm02m2_2",
                "radio_gm02m2_2d5",
                "radio_gm02m2_3",
                "radio_gm02m2_4",
                "radio_gm02m2_5",
                "radio_gm02m2_6",
                "radio_gm02m2_7",
                "radio_gm02m2_10",
            },
        )

    def test_declared_gm02m3_table_only_branch_frontier_is_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            {
                key: (
                    len(text_only[key]["lineIds"]),
                    len(text_only[key]["optionRows"]),
                    text_only[key].get(
                        "dialogIdRegistrationStatus",
                        "absent",
                    ),
                )
                for key in (
                    "dlg_gm02m3_1",
                    "dlg_gm02m3_2",
                    "dlg_gm02m3_3",
                    "dlg_gm02m3_4",
                    "dlg_gm02m3_5",
                )
            },
            {
                "dlg_gm02m3_1": (12, 3, "present_table_only"),
                "dlg_gm02m3_2": (4, 2, "present_table_only"),
                "dlg_gm02m3_3": (3, 2, "present_table_only"),
                "dlg_gm02m3_4": (4, 0, "absent"),
                "dlg_gm02m3_5": (7, 3, "absent"),
            },
        )
        self.assertEqual(
            {
                key: text_only[key].get("printableOnlyDialogTokens", ())
                for key in (
                    "dlg_gm02m3_1",
                    "dlg_gm02m3_2",
                    "dlg_gm02m3_3",
                )
            },
            {
                "dlg_gm02m3_1": ("dlg_gm02m3_1X", "dlg_gm02m3_1Y"),
                "dlg_gm02m3_2": ("dlg_gm02m3_2Y", "dlg_gm02m3_2Z"),
                "dlg_gm02m3_3": ("dlg_gm02m3_3Z", "dlg_gm02m3_3d"),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M3_RADIOS,
            {f"radio_gm02m3_{number}" for number in range(1, 6)},
        )
        self.assertEqual(
            {
                key for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m3" in key
            },
            {
                "dlg_gm02m3_1", "dlg_gm02m3_2", "dlg_gm02m3_3",
                "dlg_gm02m3_4", "dlg_gm02m3_5",
                "radio_gm02m3_1", "radio_gm02m3_2", "radio_gm02m3_3",
                "radio_gm02m3_4", "radio_gm02m3_5",
                "dlg_gm02m3_1X", "dlg_gm02m3_1Y",
                "dlg_gm02m3_2Y", "dlg_gm02m3_2Z",
                "dlg_gm02m3_3Z", "dlg_gm02m3_3d",
            },
        )

    def test_gm02m13_radio_frontier_and_dialog_guard_topology_are_exact(
        self,
    ) -> None:
        story_keys = {
            "radio_gm02m13_3",
            "radio_gm02m13_4",
            "radio_gm02m13_5",
        }
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M13_RADIOS,
            story_keys,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m13" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        for number in (3, 4, 5):
            story_key = f"radio_gm02m13_{number}"
            self.assertEqual(
                index[story_key]["missingAudioIds"],
                [f"au_radio_gm02m13_{number}_001"],
            )
        topology = index["radio_gm02m13_3"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm02m13_q#5", "gm02m13_q#6",
                "gm02m13_q#7", "gm02m13_q#15",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual(4, len(topology["forks"]))
        self.assertEqual(1, len(topology["merges"]))
        self.assertEqual(
            {
                "gm02m13_q#6": {"dlg_gm02m13_3", "dlg_gm02m13_4"},
                "gm02m13_q#8": {"dlg_gm02m13_2", "dlg_gm02m13_4"},
                "gm02m13_q#9": {"dlg_gm02m13_2", "dlg_gm02m13_3"},
            },
            {
                row["questId"]: {
                    finish["dialogId"]
                    for finish in row["dialogFinishes"]
                }
                for row in topology["failedDialogGuards"]
            },
        )
        self.assertTrue(all(
            not row["storyOrderEvidence"]
            for row in topology["failedDialogGuards"]
        ))
        self.assertEqual([], topology["failedQuestStateGuards"])
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm02m14_radio_frontier_and_mission_topology_are_exact(
        self,
    ) -> None:
        story_keys = {"radio_gm02m14_1", "radio_gm02m14_12"}
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M14_RADIOS,
            story_keys,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m14" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        self.assertEqual(
            index["radio_gm02m14_1"]["missingAudioIds"],
            ["au_radio_gm02m14_1_001"],
        )
        self.assertEqual(
            index["radio_gm02m14_12"]["missingAudioIds"],
            ["au_radio_gm02m14_12_001"],
        )
        topology = index["radio_gm02m14_1"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm02m14_q#1", "gm02m14_q#2", "gm02m14_q#3",
                "gm02m14_q#5", "gm02m14_q#6", "gm02m14_q#4",
                "gm02m14_q#7", "gm02m14_q#8", "gm02m14_q#9",
                "gm02m14_q#10", "gm02m14_q#11", "gm02m14_q#12",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm02m15_radio_frontier_and_objective_conjunction_are_exact(
        self,
    ) -> None:
        story_keys = {"radio_gm02m15_9", "radio_gm02m15_12"}
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M15_RADIOS,
            story_keys,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m15" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        self.assertEqual(
            [
                "au_radio_gm02m15_9_001",
                "au_radio_gm02m15_9_002",
                "au_radio_gm02m15_9_003",
                "au_radio_gm02m15_9_004",
            ],
            index["radio_gm02m15_9"]["missingAudioIds"],
        )
        self.assertEqual(
            [
                "au_radio_gm02m15_12_001",
                "au_radio_gm02m15_12_002",
            ],
            index["radio_gm02m15_12"]["missingAudioIds"],
        )
        topology = index["radio_gm02m15_9"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [f"gm02m15_q#{number}" for number in range(1, 9)],
            topology["mainPathQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual(1, len(topology["objectiveConjunctions"]))
        conjunction = topology["objectiveConjunctions"][0]
        self.assertEqual("gm02m15_q#5", conjunction["questId"])
        self.assertEqual(
            ["jianbei1", "jianbei2", "jianbei3"],
            [row["key"] for row in conjunction["subConditions"]],
        )
        self.assertEqual(
            "all_serialized_conditions_required",
            conjunction["completionSemantics"],
        )
        self.assertEqual("not_serialized", conjunction["executionOrderStatus"])
        self.assertFalse(conjunction["storyOrderEvidence"])
        self.assertIn(
            "export_full/structured/StreamingAssets/Data/Json/"
            "LevelScriptData/map02_lv006/25000120003.json",
            conjunction["relatedSourceFiles"],
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm02m15_objective_conjunction_validator_fails_closed(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m15"
        ]
        broken_conjunctions = copy.deepcopy(
            declaration["objectiveConjunctionsByQuest"]
        )
        broken_conjunctions["gm02m15_q#5"][0]["subConditions"][1][
            "key"
        ] = "jianbei_missing"
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm02m15": {
                **declaration,
                "objectiveConjunctionsByQuest": broken_conjunctions,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual("offlineMissionTopologyContext", failure["validator"])
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm02m15", failure["mission"])
        expected = failure["expected"]["objectiveConjunctionsByQuest"]
        actual = failure["actual"]["objectiveConjunctionsByQuest"]
        self.assertEqual(
            "jianbei_missing",
            expected["gm02m15_q#5"][0]["subConditions"][1]["key"],
        )
        self.assertEqual(
            "jianbei2",
            actual["gm02m15_q#5"][0]["subConditions"][1]["key"],
        )
        self.assertIn("sourceSha256", failure)

    def test_gm01m4_dialog_radio_frontier_and_linear_topology_are_exact(
        self,
    ) -> None:
        story_keys = {
            "dlg_gm01m4_7",
            "misc_dlg_gm01m4_3d5",
            "radio_gm01m4_1",
        }
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M4_RADIOS,
            {"radio_gm01m4_1"},
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m4" in key
            },
        )

        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))

        linear = index["dlg_gm01m4_7"]
        self.assertEqual(
            linear["missingAudioIds"],
            ["au_dlg_gm01m4_7_001", "au_dlg_gm01m4_7_002"],
        )
        self.assertEqual([], linear["dialogTreeBranchGroups"])
        self.assertEqual(
            linear["npcProxyConsumers"],
            [{
                "proxyId": "luoke_map01_v1d0d0_gm01m4man",
                "entryIndex": 3,
                "dialogId": "dlg_gm01m4_7",
                "missionId": "",
                "relation": "npc_proxy_ex_dialog_consumer_without_mission_id",
                "missionOwnership": False,
                "orderEvidence": False,
                "graphEffect": "none",
            }],
        )
        self.assertEqual(
            linear["missionNpcProxyTracking"]["questIds"],
            ["gm01m4_q#2"],
        )

        branched = index["misc_dlg_gm01m4_3d5"]
        self.assertEqual(
            branched["missingAudioIds"],
            [
                f"au_dlg_gm01m4_3d5_{number:03d}"
                for number in range(1, 7)
            ],
        )
        self.assertEqual(
            branched["npcProxyConsumers"][0]["entryIndex"],
            1,
        )
        self.assertEqual(
            branched["dialogTreeBranchGroups"],
            [{
                "optionGroup": 1,
                "optionIds": [
                    "option_dlg_gm01m4_3d5_1_001",
                    "option_dlg_gm01m4_3d5_1_002",
                ],
                "targetLineIds": [
                    "dlg_gm01m4_3d5_002",
                    "dlg_gm01m4_3d5_004",
                ],
                "routeKind": "authored_split",
            }],
        )
        self.assertEqual(
            index["radio_gm01m4_1"]["missingAudioIds"],
            ["au_radio_gm01m4_1_001"],
        )

        topology = linear["missionQuestTopologyContext"]
        self.assertEqual(
            ["gm01m4_q#1", "gm01m4_q#2"],
            topology["mainPathQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])
        for story_key in story_keys:
            self.assertEqual(
                index[story_key]["recoveryStatus"],
                "deferred_current_build_offline_surface_exhausted",
            )
            self.assertEqual(index[story_key]["graphEffect"], "none")

    def test_declared_gm01m22_binary_bounded_frontier_is_exact(self) -> None:
        self.assertEqual(
            {
                key for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m22" in key
            },
            {
                "dlg_gm01m22_6",
                "dlg_gm01m22_7",
                "dlg_gm01m22_8",
                "misc_dlg_gm01m22_2d5",
                "misc_dlg_gm01m22_3d2",
                "misc_dlg_gm01m22_3d8",
                "misc_dlg_gm01m22_4d0",
                "radio_gm01m22_1d2",
                "radio_gm01m22_1d3",
                "sns_gm01m22_2",
                "text_gm01m22_5",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M22_RADIOS,
            {"radio_gm01m22_1d2", "radio_gm01m22_1d3"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                "sns_gm01m22_2"
            ]["dialogType"],
            2,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_gm01m22_5"
            ]["contentTextIds"],
            (
                9056785448930934737,
                -3599045778776472798,
                -8943409554594408505,
                -5685369311502986662,
            ),
        )

    def test_declared_gm01m6_npc_proxy_frontier_is_exact(self) -> None:
        story_keys = {
            "dlg_gm01m6_6",
            "dlg_gm01m6_7",
            "misc_dlg_gm01m6_1d5",
            "misc_dlg_gm01m6_3d7",
            "misc_dlg_gm01m6_4d5",
            "misc_dlg_gm01m6_4d7",
            "radio_gm01m6_0d5",
            "radio_gm01m6_4d5",
            "radio_gm01m6_6",
        }
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m6" in key
            },
            story_keys,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M6_RADIOS,
            {
                "radio_gm01m6_0d5",
                "radio_gm01m6_4d5",
                "radio_gm01m6_6",
            },
        )
        expected_consumers = {
            "dlg_gm01m6_6": ("heerman_map01_default", 1),
            "dlg_gm01m6_7": ("sikete_map01_default", 0),
            "misc_dlg_gm01m6_3d7": ("heerman_map01_001", 3),
            "misc_dlg_gm01m6_4d5": ("heerman_map01_002", 0),
            "misc_dlg_gm01m6_4d7": ("sikete_map01_002", 0),
        }
        for story_key, (proxy_id, entry_index) in expected_consumers.items():
            consumer = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                story_key
            ]["npcProxyConsumer"]
            self.assertEqual(consumer["proxyId"], proxy_id)
            self.assertEqual(consumer["entryIndex"], entry_index)
            self.assertEqual(consumer["entry"]["missionId"], "")
        self.assertNotIn(
            "npcProxyConsumer",
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "misc_dlg_gm01m6_1d5"
            ],
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "misc_dlg_gm01m6_3d7"
            ]["missionNpcProxyTracking"]["rows"],
            (
                {
                    "questId": "gm01m6_q#3",
                    "objectiveIndex": 0,
                    "trackingIndex": 0,
                },
                {
                    "questId": "gm01m6_q#10",
                    "objectiveIndex": 0,
                    "trackingIndex": 0,
                },
            ),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_gm01m6_6"
            ]["missionNpcProxyTracking"]["rows"][0]["questId"],
            "gm01m6_q#12",
        )

    def test_gm01m6_mission_npc_tracking_is_visible_and_fails_closed(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        tracking = index["misc_dlg_gm01m6_3d7"][
            "missionNpcProxyTracking"
        ]
        self.assertEqual(tracking["proxyId"], "heerman_map01_001")
        self.assertEqual(tracking["levelId"], "map01_lv006")
        self.assertEqual(
            tracking["questIds"],
            ["gm01m6_q#3", "gm01m6_q#10"],
        )
        self.assertFalse(tracking["missionOwnership"])
        self.assertFalse(tracking["questPlaybackOwnership"])
        self.assertFalse(tracking["orderEvidence"])

        story_key = "misc_dlg_gm01m6_3d7"
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            story_key
        ]
        broken_tracking = {
            **definition["missionNpcProxyTracking"],
            "rows": ({
                "questId": "gm01m6_q#missing",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            },),
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS,
            {story_key: {
                **definition,
                "missionNpcProxyTracking": broken_tracking,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row
            for row in failed_status["validatorDiagnostics"]
            if row.get("storyKey") == story_key
        )
        self.assertEqual(failure["validator"], "offlineDialogDefinition")
        self.assertEqual(
            failure["gate"],
            "exactMissionNpcProxyTrackingContext",
        )
        self.assertEqual(failure["mission"], "gm01m6")
        self.assertIn("sourceSha256", failure)

    def test_gm01m13_proxy_context_and_definition_frontier_is_exact(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m13" in key
            },
            {
                "dlg_gm01m13_2",
                "dlg_gm01m13_3",
                "dlg_gm01m13_5",
                "text_gm01m13_1",
            },
        )
        for story_key, entry_index in (
            ("dlg_gm01m13_2", 1),
            ("dlg_gm01m13_3", 2),
        ):
            evidence = index[story_key]
            self.assertEqual(
                evidence["evidenceKind"],
                "mission_tracked_npc_proxy_dialog_context_without_playback_owner",
            )
            self.assertEqual(
                evidence["npcProxyConsumer"]["proxyId"],
                "sesidun02_map01_001",
            )
            self.assertEqual(
                evidence["npcProxyConsumer"]["entryIndex"],
                entry_index,
            )
            self.assertEqual(
                evidence["missionNpcProxyTracking"]["questIds"],
                [
                    "gm01m13_q#1",
                    "gm01m13_q#2",
                    "gm01m13_q#3",
                    "gm01m13_q#4",
                    "gm01m13_q#7",
                    "gm01m13_q#8",
                    "gm01m13_q#9",
                    "gm01m13_q#11",
                    "gm01m13_q#12",
                ],
            )
            self.assertFalse(
                evidence["missionNpcProxyTracking"]["questPlaybackOwnership"]
            )
            self.assertEqual(
                evidence["dialogTreeBranchGroups"][0]["routeKind"],
                "authored_convergence",
            )
            topology = evidence["missionQuestTopologyContext"]
            self.assertEqual(
                topology["mainPathQuestIds"],
                [
                    "gm01m13_q#1",
                    "gm01m13_q#2",
                    "gm01m13_q#3",
                    "gm01m13_q#4",
                    "gm01m13_q#8",
                    "gm01m13_q#9",
                    "gm01m13_q#5",
                    "gm01m13_q#7",
                    "gm01m13_q#11",
                ],
            )
            self.assertEqual(
                topology["forks"],
                [{
                    "questId": "gm01m13_q#2",
                    "successorQuestIds": [
                        "gm01m13_q#3",
                        "gm01m13_q#12",
                    ],
                }],
            )
            self.assertEqual(
                topology["merges"],
                [{
                    "predecessorQuestIds": [
                        "gm01m13_q#3",
                        "gm01m13_q#12",
                    ],
                    "questId": "gm01m13_q#4",
                }],
            )
        self.assertEqual(
            index["dlg_gm01m13_5"]["dialogIdRegistrationStatus"],
            "absent",
        )
        self.assertEqual(
            len(index["dlg_gm01m13_5"]["optionRows"]),
            4,
        )
        self.assertEqual(
            index["text_gm01m13_1"]["readingPopupRowId"],
            "text_gm01m13_1",
        )

        declaration = (
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
                "gm01m13"
            ]
        )
        broken_predecessors = {
            **declaration["prevQuestIdsByQuest"],
            "gm01m13_q#4": ("gm01m13_q#3",),
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm01m13": {
                **declaration,
                "prevQuestIdsByQuest": broken_predecessors,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row
            for row in failed_status["validatorDiagnostics"]
            if row.get("mission") == "gm01m13"
        )
        self.assertEqual(failure["validator"], "offlineMissionTopologyContext")
        self.assertEqual(
            failure["gate"],
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
        )
        self.assertEqual(failure["mission"], "gm01m13")
        self.assertIn("sourceSha256", failure)

    def test_gm01m15_definition_frontier_and_topology_are_exact(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m15" in key
            },
            {"dlg_gm01m15_7", "text_gm01m15_1", "text_gm01m15_8"},
        )

        dialog = index["dlg_gm01m15_7"]
        self.assertEqual(
            dialog["evidenceKind"],
            "dialog_text_table_only_without_registry_asset_or_consumer",
        )
        self.assertEqual(len(dialog["lineIds"]), 11)
        self.assertEqual(len(dialog["missingAudioIds"]), 11)
        self.assertEqual(len(dialog["optionIds"]), 5)
        self.assertEqual(
            dialog["optionRouteStatus"],
            "definitions_present_route_unresolved",
        )
        self.assertEqual(
            dialog["summaryDefinition"],
            {
                "summaryId": "summary_gm01m15_7_001",
                "textId": "1386392558646000191",
                "relation": "dialog_summary_map_targets_dialog",
                "missionOwnership": False,
                "orderEvidence": False,
            },
        )
        self.assertNotIn("dialogTreeBranchGroups", dialog)

        text_one = index["text_gm01m15_1"]
        self.assertEqual(
            text_one["contentTextIds"],
            [
                8242330289792353294,
                -2455707730206541547,
                -2339893156956209480,
                119766408319964938,
                -8714781499976003721,
            ],
        )
        self.assertEqual(
            text_one["prtsDefinition"],
            {
                "rowId": "nar_digital_map01_research1_16_1",
                "firstLvId": "digital_map01_research1_16",
                "type": "text",
                "order": 1,
                "relation": "prts_archive_entry_targets_story",
                "missionOwnership": False,
                "orderEvidence": False,
            },
        )
        self.assertEqual(
            index["text_gm01m15_8"]["contentTextIds"],
            [6649389232287698087],
        )
        self.assertIsNone(index["text_gm01m15_8"]["prtsDefinition"])

        topology = dialog["missionQuestTopologyContext"]
        self.assertEqual(
            topology["mainPathQuestIds"],
            [
                "gm01m15_q#2", "gm01m15_q#3", "gm01m15_q#4",
                "gm01m15_q#6", "gm01m15_q#7", "gm01m15_q#8",
                "gm01m15_q#14", "gm01m15_q#5", "gm01m15_q#10",
                "gm01m15_q#11", "gm01m15_q#12",
            ],
        )
        self.assertEqual(
            topology["forks"],
            [{
                "questId": "gm01m15_q#3",
                "successorQuestIds": ["gm01m15_q#4", "gm01m15_q#13"],
            }],
        )
        self.assertEqual(
            topology["merges"],
            [{
                "predecessorQuestIds": ["gm01m15_q#4", "gm01m15_q#13"],
                "questId": "gm01m15_q#6",
            }],
        )
        self.assertEqual(
            topology["parallelRendezvous"],
            [{
                "forkQuestId": "gm01m15_q#3",
                "parallelQuestIds": ["gm01m15_q#4", "gm01m15_q#13"],
                "mergeQuestId": "gm01m15_q#6",
                "joinSemantics": "all_predecessor_quests_required",
                "playerChoice": False,
            }],
        )
        self.assertEqual(topology["storyAssignments"], [])
        self.assertFalse(topology["orderEvidence"])
        for story_key in ("dlg_gm01m15_7", "text_gm01m15_1", "text_gm01m15_8"):
            self.assertEqual(index[story_key]["graphEffect"], "none")

        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_gm01m15_7"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_gm01m15_7": {
                **definition,
                "summaryDefinition": {
                    **definition["summaryDefinition"],
                    "summaryId": "summary_gm01m15_7_changed",
                },
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row.get("storyKey") == "dlg_gm01m15_7"
            and row.get("gate") == "exactDialogSummaryDefinition"
        )
        self.assertEqual(failure["validator"], "offlineTextOnlyDialogDefinition")
        self.assertIn("dialogSummaryMapTable", failure["sourceSha256"])
        self.assertIn("dialogSummaryTable", failure["sourceSha256"])

    def test_declared_gm01m7_branch_frontier_is_exact(self) -> None:
        story_keys = {
            "dlg_gm01m7_1",
            "dlg_gm01m7_2",
            "dlg_gm01m7_3",
            "dlg_gm01m7_5",
            "dlg_gm01m7_7",
            "radio_gm01m7_9",
            "sns_gm01m7_1",
            "sns_gm01m7_2",
            "text_gm01m7_1",
        }
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m7" in key
            },
            story_keys,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M7_RADIOS,
            {"radio_gm01m7_9"},
        )
        branch = gap_queue.OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS[
            "gm01m7"
        ]
        self.assertEqual(
            branch["fork"],
            {
                "questId": "gm01m7_q#1",
                "successorQuestIds": (
                    "gm01m7_q#8",
                    "gm01m7_q#14",
                ),
            },
        )
        self.assertEqual(
            branch["merge"],
            {
                "predecessorQuestIds": (
                    "gm01m7_q#14",
                    "gm01m7_q#8",
                ),
                "questId": "gm01m7_q#9",
            },
        )
        self.assertEqual(
            branch["sharedTracking"]["proxyId"],
            "sesidun_map01_001",
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                    "dlg_gm01m7_1"
                ]["treeBranchGroups"]
            ),
            2,
        )
        for story_key in (
            "dlg_gm01m7_1",
            "dlg_gm01m7_2",
            "dlg_gm01m7_3",
            "dlg_gm01m7_5",
            "dlg_gm01m7_7",
        ):
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                    story_key
                ]["missionNpcProxyTracking"]["runtimeMissionId"],
                "gm01m12",
            )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                    "dlg_gm01m7_2"
                ]["npcProxyConsumers"]
            ),
            2,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                "sns_gm01m7_1"
            ]["runtimeTracking"]["questId"],
            "gm01m12_q#16",
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                    "text_gm01m7_1"
                ]["contentTextIds"]
            ),
            13,
        )

    def test_gm01m7_branch_and_cross_mission_sns_context_are_visible(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        context = index["dlg_gm01m7_1"]["missionQuestBranchContext"]
        self.assertEqual(
            context["fork"]["successorQuestIds"],
            ["gm01m7_q#8", "gm01m7_q#14"],
        )
        self.assertEqual(
            context["merge"]["predecessorQuestIds"],
            ["gm01m7_q#14", "gm01m7_q#8"],
        )
        self.assertEqual(context["storyArmAssignments"], [])
        self.assertEqual(
            context["storyArmAssignmentStatus"],
            "unresolved",
        )
        self.assertFalse(context["orderEvidence"])
        dialog_tracking = index["dlg_gm01m7_1"][
            "missionNpcProxyTracking"
        ]
        self.assertTrue(dialog_tracking["crossMission"])
        self.assertEqual(dialog_tracking["missionId"], "gm01m12")
        self.assertEqual(dialog_tracking["nominalMissionId"], "gm01m7")
        self.assertEqual(dialog_tracking["questIds"], ["gm01m12_q#14"])
        shared_dialog_tracking = index["dlg_gm01m7_7"][
            "missionNpcProxyTracking"
        ]
        self.assertEqual(
            shared_dialog_tracking["questIds"],
            [
                "gm01m12_q#2",
                "gm01m12_q#3",
                "gm01m12_q#4",
                "gm01m12_q#6",
                "gm01m12_q#12",
            ],
        )
        tracking = index["sns_gm01m7_1"]["runtimeTrackingContext"]
        self.assertEqual(tracking["runtimeMissionId"], "gm01m12")
        self.assertEqual(tracking["questId"], "gm01m12_q#16")
        self.assertFalse(tracking["playback"])
        self.assertFalse(tracking["nominalMissionOwnership"])

    def test_gm01m7_branch_context_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS[
            "gm01m7"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS,
            {"gm01m7": {
                **declaration,
                "fork": {
                    **declaration["fork"],
                    "successorQuestIds": ("gm01m7_q#missing",),
                },
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(failure["validator"], "offlineMissionBranchContext")
        self.assertEqual(
            failure["gate"],
            "exactForkMergeAndSharedNpcTracking",
        )
        self.assertEqual(failure["mission"], "gm01m7")
        self.assertIn("sourceSha256", failure)

    def test_declared_gm01m12_linear_frontier_is_exact(self) -> None:
        story_keys = {
            "dlg_gm01m12_1",
            "dlg_gm01m12_3",
            "dlg_gm01m12_6",
            "dlg_gm01m12_8",
            "text_gm01m12_1",
            "text_gm01m12_3",
            "text_gm01m12_5",
            "text_gm01m12_6",
            "text_gm01m12_7",
        }
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m12" in key
            },
            story_keys,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS[
                "gm01m12"
            ]["questSequence"],
            tuple(
                f"gm01m12_q#{number}"
                for number in (15, 16, 13, 14, 1, 2, 3, 4, 12, 5, 6)
            ),
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS),
            {"dlg_gm01m12_1", "dlg_gm01m12_3"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS[
                "dlg_gm01m12_1"
            ]["postDialogAction"]["actionName"],
            "BlackScreenFadeInAndOut",
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_gm01m12_5"
            ]["richContentStatus"],
            "absent",
        )

    def test_gm01m12_linear_and_task_context_are_visible(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        row = index["dlg_gm01m12_1"]
        sequence = row["missionQuestSequenceContext"]
        self.assertEqual(len(sequence["questSequence"]), 11)
        self.assertEqual(sequence["forkQuestIds"], [])
        self.assertEqual(sequence["mergeQuestIds"], [])
        self.assertEqual(sequence["storyAssignments"], [])
        self.assertFalse(sequence["orderEvidence"])
        consumer = row["levelScriptTaskConsumer"]
        self.assertEqual(consumer["conditionType"], "CheckTalkOptionFinish")
        self.assertEqual(consumer["finishId"], -1)
        self.assertFalse(consumer["playback"])
        self.assertFalse(consumer["missionOwnership"])
        self.assertEqual(
            consumer["postDialogAction"]["actionName"],
            "BlackScreenFadeInAndOut",
        )
        self.assertEqual(
            index["text_gm01m12_3"]["prtsReadingDefinition"]["rowId"],
            "term_001_gm01m7",
        )

    def test_gm01m12_linear_context_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS[
            "gm01m12"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS,
            {"gm01m12": {
                **declaration,
                "questSequence": (*declaration["questSequence"][:-1], "gm01m12_q#missing"),
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(failure["validator"], "offlineMissionLinearContext")
        self.assertEqual(
            failure["gate"],
            "exactSinglePredecessorQuestSequence",
        )
        self.assertEqual(failure["mission"], "gm01m12")
        self.assertIn("sourceSha256", failure)

    def test_gm01m12_levelscript_task_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS[
            "dlg_gm01m12_1"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS,
            {"dlg_gm01m12_1": {
                **declaration,
                "conditionKey": "changed",
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(
            failure["validator"],
            "offlineLevelScriptTaskConsumer",
        )
        self.assertEqual(
            failure["gate"],
            "exactLevelScriptTalkCompletionConsumer",
        )
        self.assertEqual(failure["storyKey"], "dlg_gm01m12_1")
        self.assertIn("sourceSha256", failure)

    def test_gm02m20_retired_radios_and_auxiliary_topology_are_exact(
        self,
    ) -> None:
        story_keys = {
            "radio_gm02m20_7",
            "radio_gm02m20_8",
            "radio_gm02m20_10",
            "radio_gm02m20_11",
            "radio_gm02m20_13",
        }
        self.assertEqual(
            story_keys,
            gap_queue.OFFLINE_EXHAUSTION_GM02M20_RADIOS,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m20" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        topology = index["radio_gm02m20_7"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm02m20_q#1", "gm02m20_q#2", "gm02m20_q#10",
                "gm02m20_q#11", "gm02m20_q#3", "gm02m20_q#6",
                "gm02m20_q#4", "gm02m20_q#7", "gm02m20_q#5",
                "gm02m20_q#8",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual(
            ["gm02m20_q#1", "gm02m20_q#9"],
            topology["entryQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual(
            [{
                "questId": "gm02m20_q#9",
                "objectiveIndex": 1,
                "targetQuestId": "gm02m20_q#1",
                "comparer": 0,
                "targetQuestState": 3,
                "scopeMask": 1,
                "useGraphScope": True,
            }],
            topology["questStateDependencies"],
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm01m3_original_context_and_definition_frontier_is_exact(
        self,
    ) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M3_RADIOS,
            {"radio_gm01m3_3d8"},
        )
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m3" in key
            },
            {
                "misc_dlg_gm01m3_1d5",
                "radio_gm01m3_3d2",
                "radio_gm01m3_3d8",
                "sns_gm01m3_1",
            },
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "misc_dlg_gm01m3_1d5"
        ]
        self.assertEqual(
            dialog["lineIds"],
            ("dlg_gm01m3_1d5_001", "dlg_gm01m3_1d5_002"),
        )
        self.assertEqual(dialog["optionIds"], ())

        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        offline_index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertEqual(
            offline_index["sns_gm01m3_1"]["relatedMissionId"],
            "gm01m3",
        )
        self.assertEqual(
            offline_index["sns_gm01m3_1"][
                "linkMissionIdsByContentId"
            ],
            {"4": "gm01m3"},
        )

        gm01m3 = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/gm01m3.json",
            {},
        )
        sns_rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            gm01m3["flow"],
            {"sns_gm01m3_1"},
            "gm01m3",
            offline_index,
        )
        self.assertEqual(
            [row["recoveryStatus"] for row in sns_rows],
            ["closed_exact_authored_sns_mission_link_no_relative_order"],
        )
        self.assertEqual(
            gap_queue._closed_exact_runtime_config_isolated_scenes(
                gm01m3["flow"],
                {"sns_gm01m3_1"},
                "gm01m3",
                {},
            ),
            [],
        )

        gm01m4 = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/gm01m4.json",
            {},
        )
        connection = next(
            row
            for row in gm01m4["flow"]["missionStoryConnections"]
            if row.get("key") == "radio_gm01m3_3d2"
        )
        native_rows = gap_queue._closed_exact_native_context_isolated_scenes(
            {"missionStoryConnections": [connection]},
            {"radio_gm01m3_3d2"},
            "gm01m3",
        )
        self.assertEqual(
            native_rows[0]["recoveryStatus"],
            "closed_exact_cross_mission_leveldata_shell_playback_context_no_relative_order",
        )
        self.assertEqual(native_rows[0]["contextMissionId"], "gm01m4")
        invalid = copy.deepcopy(connection)
        invalid["levelScriptOccurrences"][0][
            "authoritativeScopeLevelDataHosts"
        ][0]["dictionaryEntryCount"] = 13
        self.assertEqual(
            gap_queue._closed_exact_native_context_isolated_scenes(
                {"missionStoryConnections": [invalid]},
                {"radio_gm01m3_3d2"},
                "gm01m3",
            ),
            [],
        )

    def test_gm01m17_retired_definitions_and_nested_topology_are_exact(
        self,
    ) -> None:
        radio_keys = {
            "radio_gm01m17_4",
            "radio_gm01m17_5",
            "radio_gm01m17_9",
        }
        self.assertEqual(
            radio_keys,
            gap_queue.OFFLINE_EXHAUSTION_GM01M17_RADIOS,
        )
        self.assertEqual(
            radio_keys | {"text_gm01m17_1"},
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m17" in key
            },
        )
        self.assertEqual(
            {
                "missionId": "gm01m17",
                "readingPopupRowId": "text_gm01m17_1",
                "bgType": 2,
                "iconType": 0,
                "titleId": -5216252211990160921,
                "contentTextIds": (
                    2833540280945742009,
                    -8531949106363903611,
                ),
            },
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_gm01m17_1"
            ],
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(radio_keys | {"text_gm01m17_1"} <= set(index))
        topology = index["radio_gm01m17_4"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm01m17_q#1", "gm01m17_q#2", "gm01m17_q#13",
                "gm01m17_q#14", "gm01m17_q#16", "gm01m17_q#18",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual(8, len(topology["entryQuestIds"]))
        self.assertEqual(3, len(topology["forks"]))
        self.assertEqual([], topology["merges"])
        self.assertEqual(12, len(topology["terminalQuestIds"]))
        self.assertEqual(4, len(topology["questStateDependencies"]))
        self.assertEqual(
            {(0, 1), (1, 1), (2, 1)},
            {
                tuple(row["conditionIndexPath"])
                for row in topology["questStateDependencies"]
                if row["questId"] == "gm01m17_q#3"
            },
        )
        self.assertEqual(
            [{
                "questId": "gm01m17_q#13",
                "conditionType": "CheckQuestState",
                "targetQuestId": "gm01m17_q#3",
                "comparer": 0,
                "targetQuestState": 3,
                "relation": "authored_quest_failure_guard",
                "branchExclusivityStatus": (
                    "not_proven_by_one_way_failure_guard"
                ),
                "storyOrderEvidence": False,
            }],
            topology["failedQuestStateGuards"],
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm01m17_nested_topology_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm01m17"
        ]
        broken_dependencies = copy.deepcopy(
            declaration["questStateDependenciesByQuest"]
        )
        broken_dependencies["gm01m17_q#3"][1][
            "targetQuestId"
        ] = "gm01m17_q#missing"
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm01m17": {
                **declaration,
                "questStateDependenciesByQuest": broken_dependencies,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual("offlineMissionTopologyContext", failure["validator"])
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm01m17", failure["mission"])
        expected = failure["expected"]["questStateDependenciesByQuest"]
        actual = failure["actual"]["questStateDependenciesByQuest"]
        self.assertEqual(
            "gm01m17_q#missing",
            expected["gm01m17_q#3"][1]["targetQuestId"],
        )
        self.assertEqual(
            "gm01m17_q#13",
            actual["gm01m17_q#3"][1]["targetQuestId"],
        )
        self.assertEqual(
            (1, 1),
            actual["gm01m17_q#3"][1]["conditionIndexPath"],
        )

    def test_gm02m20_auxiliary_topology_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m20"
        ]
        broken_dependencies = copy.deepcopy(
            declaration["questStateDependenciesByQuest"]
        )
        broken_dependencies["gm02m20_q#9"][0][
            "targetQuestId"
        ] = "gm02m20_q#missing"
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm02m20": {
                **declaration,
                "questStateDependenciesByQuest": broken_dependencies,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(
            "offlineMissionTopologyContext",
            failure["validator"],
        )
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm02m20", failure["mission"])
        self.assertEqual(
            "gm02m20_q#missing",
            failure["expected"]["questStateDependenciesByQuest"]
            ["gm02m20_q#9"][0]["targetQuestId"],
        )
        self.assertEqual(
            "gm02m20_q#1",
            failure["actual"]["questStateDependenciesByQuest"]
            ["gm02m20_q#9"][0]["targetQuestId"],
        )

    def test_gm01m16_exact_topology_is_visible_without_story_assignment(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        index, status = gap_queue.build_offline_exhaustion_index(partial, table_root)
        self.assertEqual("active", status["status"])
        topology = index["radio_gm01m16_8"]["missionQuestTopologyContext"]
        self.assertEqual(26, len(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
                "gm01m16"
            ]["prevQuestIdsByQuest"]
        ))
        self.assertEqual(2, len(topology["entryQuestIds"]))
        self.assertEqual(5, len(topology["forks"]))
        self.assertEqual(4, len(topology["merges"]))
        self.assertEqual(8, len(topology["terminalQuestIds"]))
        self.assertEqual(12, len(topology["mainPathQuestIds"]))
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])
        self.assertEqual("not_evidence", topology["flowIndexExclusivityStatus"])

    def test_gm01m16_topology_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm01m16"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm01m16": {
                **declaration,
                "mainPathQuestIds": (*declaration["mainPathQuestIds"][:-1], "gm01m16_q#missing"),
            }},
        ):
            failed_index, failed_status = gap_queue.build_offline_exhaustion_index(
                partial,
                table_root,
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual("offlineMissionTopologyContext", failure["validator"])
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm01m16", failure["mission"])
        self.assertIn("sourceSha256", failure)

    def test_gm01m20_exact_fork_and_main_path_are_visible(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        topology = index["radio_gm01m20_1"]["missionQuestTopologyContext"]
        self.assertEqual(["gm01m20_q#7"], topology["entryQuestIds"])
        self.assertEqual([
            "gm01m20_q#7", "gm01m20_q#1", "gm01m20_q#6",
            "gm01m20_q#3", "gm01m20_q#4", "gm01m20_q#2",
        ], topology["mainPathQuestIds"])
        self.assertEqual([{
            "questId": "gm01m20_q#4",
            "successorQuestIds": ["gm01m20_q#2", "gm01m20_q#10"],
        }], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual(
            {"gm01m20_q#2", "gm01m20_q#10"},
            set(topology["terminalQuestIds"]),
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertEqual(
            "not_serialized_in_client_asset",
            topology["serverSuccessorSelectionStatus"],
        )

    def test_gm01m7_cross_mission_sns_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        story_key = "sns_gm01m7_1"
        definition = gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[story_key]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS,
            {story_key: {
                **definition,
                "runtimeTracking": {
                    **definition["runtimeTracking"],
                    "questId": "gm01m12_q#missing",
                },
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row
            for row in failed_status["validatorDiagnostics"]
            if row.get("storyKey") == story_key
        )
        self.assertEqual(failure["validator"], "offline_sns_definition")
        self.assertEqual(
            failure["gate"],
            "exactCrossMissionSnsTrackingContext",
        )
        self.assertEqual(failure["mission"], "gm01m12")
        self.assertIn("sourceSha256", failure)

    def test_gm01m22_dialog_tree_branches_are_exact_and_fail_closed(self) -> None:
        definition_root = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
        )
        expected = {
            "dlg_gm01m22_6": [{
                "optionGroup": 3,
                "optionIds": [
                    "option_dlg_gm01m22_6_3_001",
                    "option_dlg_gm01m22_6_3_002",
                    "option_dlg_gm01m22_6_3_003",
                ],
                "targetLineIds": [
                    "dlg_gm01m22_6_007",
                    "dlg_gm01m22_6_009",
                    "dlg_gm01m22_6_012",
                ],
                "routeKind": "authored_split",
            }],
            "dlg_gm01m22_8": [{
                "optionGroup": 6,
                "optionIds": [
                    "option_dlg_gm01m22_8_6_001",
                    "option_dlg_gm01m22_8_6_002",
                ],
                "targetLineIds": [
                    "dlg_gm01m22_8_019",
                    "dlg_gm01m22_8_019",
                ],
                "routeKind": "authored_convergence",
            }, {
                "optionGroup": 9,
                "optionIds": [
                    "option_dlg_gm01m22_8_9_001",
                    "option_dlg_gm01m22_8_9_002",
                    "option_dlg_gm01m22_8_9_003",
                ],
                "targetLineIds": [
                    "dlg_gm01m22_8_026",
                    "dlg_gm01m22_8_028",
                    "dlg_gm01m22_8_031",
                ],
                "routeKind": "authored_split",
            }],
        }
        for story_key, groups in expected.items():
            definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                story_key
            ]
            asset = gap_queue.read_json(
                definition_root / definition["filename"],
                {},
            )
            self.assertEqual(
                gap_queue._dialog_tree_branch_groups(asset),
                groups,
            )

        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_gm01m22_6"
        ]
        broken_groups = list(definition["treeBranchGroups"])
        broken_groups[0] = {
            **broken_groups[0],
            "targetLineIds": ("dlg_gm01m22_6_007",) * 3,
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS,
            {"dlg_gm01m22_6": {
                **definition,
                "treeBranchGroups": broken_groups,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row["storyKey"] == "dlg_gm01m22_6"
        )
        self.assertEqual(failure["validator"], "offlineDialogDefinition")
        self.assertEqual(failure["gate"], "exactRegisteredDialogDefinition")
        self.assertNotEqual(
            failure["expected"]["treeBranchGroups"],
            failure["actual"]["treeBranchGroups"],
        )

    def test_gm01m2_result_and_internal_dialog_branches_are_exact(self) -> None:
        root = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
        )
        definitions = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS
        assets = {
            key: gap_queue.read_json(root / definitions[key]["filename"], {})
            for key in ("dlg_gm01m2_1", "dlg_gm01m2_2", "dlg_gm01m2_3")
        }
        self.assertEqual(
            gap_queue._dialog_tree_branch_groups(assets["dlg_gm01m2_1"]),
            [{
                "optionGroup": 1,
                "optionIds": [
                    f"option_dlg_gm01m2_1_1_{number:03d}"
                    for number in range(1, 5)
                ],
                "targetLineIds": [
                    "dlg_gm01m2_1_003", "dlg_gm01m2_1_004",
                    "dlg_gm01m2_1_005", "dlg_gm01m2_1_009",
                ],
                "routeKind": "authored_split",
            }],
        )
        success_routes = gap_queue._dialog_tree_terminal_option_routes(
            assets["dlg_gm01m2_2"]
        )
        failure_routes = gap_queue._dialog_tree_terminal_option_routes(
            assets["dlg_gm01m2_3"]
        )
        self.assertEqual(
            [row["finishId"] for row in success_routes[0]["routes"]],
            [1, None],
        )
        self.assertEqual(
            failure_routes[0]["routes"][1]["optionId"],
            "option_dlg_gm01m2_2_1_002",
        )
        declaration = (
            gap_queue.OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS[
                "gm01m2"
            ]
        )
        self.assertEqual(declaration["propertyCount"], 38)
        self.assertEqual(
            tuple(
                (row["value"], row["propertyPath"])
                for row in declaration["resultSwitch"]["cases"]
            ),
            ((8, "succeed_dialog"), (9, "failed_dialog")),
        )

    def test_dialog_tree_idless_non_actor_node_fails_closed(self) -> None:
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_gm01m2_1"
        ]
        path = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
            / definition["filename"]
        )
        asset = gap_queue.read_json(path, {})
        payload = json.loads(
            base64.b64decode(asset["m_Script"]).decode("utf-8-sig")
        )
        payload["nodes"][0].pop("$id")
        broken = {
            **asset,
            "m_Script": base64.b64encode(
                json.dumps(payload).encode("utf-8")
            ).decode("ascii"),
        }
        self.assertIsNone(gap_queue._dialog_tree_branch_groups(broken))
        self.assertIsNone(
            gap_queue._dialog_tree_terminal_option_routes(broken)
        )

    def test_gm01m2_leveldata_property_count_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        contexts = (
            gap_queue.OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS
        )
        declaration = contexts["gm01m2"]
        with patch.dict(
            contexts,
            {"gm01m2": {**declaration, "propertyCount": 37}},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row.get("mission") == "gm01m2"
        )
        self.assertEqual(
            failure["validator"],
            "offlineLevelDataDialogBranchContext",
        )
        self.assertEqual(failure["actual"]["propertyCount"], 38)

    def test_gm02m23_dialog_tree_convergence_and_terminal_routes_are_exact(self) -> None:
        definition_root = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_gm02m23_3"
        ]
        asset = gap_queue.read_json(
            definition_root / definition["filename"],
            {},
        )

        self.assertEqual(
            gap_queue._dialog_tree_branch_groups(asset),
            [{
                "optionGroup": 4,
                "optionIds": [
                    "option_dlg_gm02m23_3_4_001",
                    "option_dlg_gm02m23_3_4_002",
                ],
                "targetLineIds": [
                    "dlg_gm02m23_3_023",
                    "dlg_gm02m23_3_023",
                ],
                "routeKind": "authored_convergence",
            }, {
                "optionGroup": 5,
                "optionIds": [
                    "option_dlg_gm02m23_3_5_001",
                    "option_dlg_gm02m23_3_5_002",
                ],
                "targetLineIds": [
                    "dlg_gm02m23_3_024",
                    "dlg_gm02m23_3_024",
                ],
                "routeKind": "authored_convergence",
            }],
        )
        self.assertEqual(
            gap_queue._dialog_tree_terminal_option_routes(asset),
            [{
                "optionGroup": 6,
                "routes": [{
                    "optionId": "option_dlg_gm02m23_3_6_001",
                    "targetKind": "finish",
                    "finishId": None,
                    "finishIdSerialized": False,
                }, {
                    "optionId": "option_dlg_gm02m23_3_6_002",
                    "targetKind": "finish",
                    "finishId": 1,
                    "finishIdSerialized": True,
                }],
            }],
        )

    def test_gm02m2_table_only_registration_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_gm02m2_2"
        ]
        incomplete_options = dict(definition["optionRows"])
        incomplete_options.pop("option_dlg_gm02m2_2_1_002")
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_gm02m2_2": {
                **definition,
                "optionRows": incomplete_options,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row["storyKey"] == "dlg_gm02m2_2"
            and row["gate"] == "exactTableOnlyDialogIdRegistration"
        )
        self.assertEqual(failure["validator"], "offlineTextOnlyDialogDefinition")
        self.assertEqual(failure["missionId"], "gm02m2")
        self.assertEqual(failure["expected"]["optionCount"], 1)
        self.assertEqual(failure["actual"]["optionCount"], 2)
        self.assertIn("dialogIdSource", failure["sourceSha256"])
        self.assertIn("dialogIdIndex", failure["sourceSha256"])

    def test_gm02m3_printable_only_tokens_fail_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_gm02m3_1"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_gm02m3_1": {
                **definition,
                "printableOnlyDialogTokens": (
                    "dlg_gm02m3_1X",
                    "dlg_gm02m3_not_an_original_token",
                ),
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row["storyKey"] == "dlg_gm02m3_1"
            and row["gate"] == "exactPrintableOnlyDialogTokens"
        )
        self.assertEqual(failure["missionId"], "gm02m3")
        self.assertIsNone(
            failure["actual"]["dlg_gm02m3_not_an_original_token"]
        )
        self.assertIn("dialogIdSource", failure["sourceSha256"])
        self.assertIn("dialogIdIndex", failure["sourceSha256"])

    def test_offline_table_only_options_leave_routes_visible_but_deferred(self) -> None:
        partial = partial_mission(
            "gm02m2",
            scenes=["dlg_gm02m2_2"],
            isolated=["dlg_gm02m2_2"],
            no_route_groups=1,
        )
        partial["summary"].update({
            "branchingNoExplicitRouteGroupCount": 1,
            "singleOptionNoExplicitRouteGroupCount": 0,
        })
        partial["branches"] = {
            "branchingNoExplicitRouteGroups": [{
                "storyKey": "dlg_gm02m2_2",
                "group": 1,
                "options": [
                    {"optionId": "option_dlg_gm02m2_2_1_001"},
                    {"optionId": "option_dlg_gm02m2_2_1_002"},
                ],
            }],
        }
        recovery = {
            "sceneKey": "dlg_gm02m2_2",
            "missionId": "gm02m2",
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "optionRouteStatus": "definitions_present_route_unresolved",
            "optionIds": [
                "option_dlg_gm02m2_2_1_001",
                "option_dlg_gm02m2_2_1_002",
            ],
            "evidenceKind":
                "registered_dialog_table_rows_without_tree_asset_or_consumer",
            "consumerBoundary": "fixture exact-build boundary",
            "graphEffect": "none",
        }
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            offline_exhaustion_index={"dlg_gm02m2_2": recovery},
        )
        self.assertEqual(
            row["metrics"]["actionableNoExplicitOptionRouteGroups"],
            0,
        )
        self.assertEqual(
            row["metrics"]["deferredOfflineExhaustedOptionRouteGroups"],
            1,
        )
        self.assertEqual(
            row["deferredOfflineExhaustedOptionRouteGroups"][0]["optionIds"],
            recovery["optionIds"],
        )
        self.assertEqual(
            row["deferredOfflineExhaustedOptionRouteGroups"][0]["graphEffect"],
            "none",
        )

    def test_a1m8d1_sns_branch_validator_reports_exact_failure(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
            "sns_a1m8d1_1"
        ]
        self.assertEqual(
            definition["optionNextContentIds"][
                "option_sns_a1m8d1_1_2_002"
            ],
            10,
        )
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS,
            {
                "sns_a1m8d1_1": {
                    **definition,
                    "chatId": "changed_native_chat_id",
                },
            },
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        self.assertEqual(
            failed_status["status"],
            "inactive_sns_definition_validation_failed",
        )
        failure = failed_status["validationFailures"][0]
        self.assertEqual(failure["validator"], "offline_sns_definition")
        self.assertEqual(failure["storyKey"], "sns_a1m8d1_1")
        self.assertEqual(
            failure["gate"],
            "dialog_shape_and_exact_key_sets",
        )
        self.assertEqual(
            failure["actual"]["chatId"],
            "sns_npc_zuoguyan_a1m8d3",
        )

    def test_declared_a1m5_definition_frontier_is_exact(self) -> None:
        dialog = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_a1m5_5"
        ]
        self.assertEqual(dialog["missionId"], "a1m5")
        self.assertEqual(
            dialog["lineIds"],
            ("dlg_a1m5_5_001", "dlg_a1m5_5_002"),
        )
        self.assertEqual(
            dialog["missingAudioIds"],
            ("au_dlg_a1m5_5_001", "au_dlg_a1m5_5_002"),
        )
        self.assertEqual(
            dialog["allowedNonOwningRoute"]["relation"],
            "dialog_tree_reachable_story_playback",
        )
        self.assertEqual(
            dialog["nonOwningContext"]["candidateQuestIds"],
            (
                "a1m5_q#4",
                "a1m5_q#5",
                "a1m5_q#8",
                "a1m5_q#10",
                "a1m5_q#12",
                "a1m5_q#14",
                "a1m5_q#16",
            ),
        )
        expected_content_ids = {
            "text_a1m5_1": (
                7065289209916235881,
                -3793799197369702242,
            ),
            "text_a1m5_2": (145014796983259450,),
            "text_a1m5_3": (
                -4841045965292223135,
                -89499260089272388,
            ),
            "text_a1m5_4": (-4489297013210307938,),
            "text_a1m5_5": (
                -5413898867121804929,
                -1357598897532823788,
            ),
            "text_a1m5_6": (1303745015045365078,),
            "text_a1m5_7": (-7046570968636013796,),
        }
        self.assertEqual(
            {
                key: gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                    key
                ]["contentTextIds"]
                for key in expected_content_ids
            },
            expected_content_ids,
        )
        self.assertEqual(
            {
                key: gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[key][
                    "titleId"
                ]
                for key in expected_content_ids
            },
            {
                "text_a1m5_1": -8904306416814611456,
                "text_a1m5_2": -2647826485076773960,
                "text_a1m5_3": -676517154678141545,
                "text_a1m5_4": 2405623048071579055,
                "text_a1m5_5": 1365793654747611898,
                "text_a1m5_6": 5740509153553995198,
                "text_a1m5_7": 2638866450720374170,
            },
        )

    def test_offline_text_definition_validator_reports_exact_failure(
        self,
    ) -> None:
        story_key = "text_a1m5_1"
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            story_key
        ]
        popup = {
            "bgType": definition["bgType"],
            "contentId": story_key,
            "iconType": definition["iconType"],
            "id": definition["readingPopupRowId"],
            "overrideRadioId": "",
            "title": {"id": 0, "text": ""},
        }
        rich = {
            "contentList": [
                {"content": {"id": text_id, "text": ""}}
                for text_id in definition["contentTextIds"]
            ],
            "title": {"id": definition["titleId"], "text": ""},
        }

        self.assertIsNone(
            gap_queue._offline_text_definition_validation_failure(
                story_key,
                definition,
                popup,
                rich,
                {},
                {},
            )
        )

        rich["title"]["id"] = 0
        failure = gap_queue._offline_text_definition_validation_failure(
            story_key,
            definition,
            popup,
            rich,
            {},
            {},
        )
        self.assertEqual(failure["validator"], "offlineTextDefinition")
        self.assertEqual(
            failure["gate"],
            "exactReadingPopupAndRichContentRows",
        )
        self.assertEqual(failure["storyKey"], story_key)
        self.assertEqual(
            failure["expected"]["richTitle"]["id"],
            -8904306416814611456,
        )
        self.assertEqual(failure["actual"]["richTitle"]["id"], 0)

    def test_declared_a1m9_definition_frontier_is_exact(self) -> None:
        expected = {
            "text_a1m9_1": (
                "rp_text_a1m9_1", 6133950036636760715,
                (4360361720766943813, -5286642356287476400),
            ),
            "text_a1m9_2": (
                "rp_text_a1m9_2", -9061878788721069148,
                (-8710457857620610713, 195657822153420954),
            ),
            "text_a1m9_3": (
                "rp_text_a1m9_3", -4216673929559825878,
                (5233675183060561957, 4427207018166369215),
            ),
            "text_a1m9_4": (
                "rp_text_a1m9_4", 1447286566198348849,
                (1656717363105155858, -8370465523951817989),
            ),
            "text_a1m9_5": (
                "rp_text_a1m9_5", -7333612545186178263,
                (-5168759132077193528, 7120988803212617269),
            ),
            "text_a1m9_6": (
                "rp_text_a1m9_6", 93296881304760627,
                (-5058010235124771975, -8995527205053721848),
            ),
            "text_a1m9_7": (
                "rp_text_a1m9_7", -8532814195849073983,
                (1466176077223606619, 4212985633755235735),
            ),
        }
        actual = {}
        for story_key in expected:
            definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                story_key
            ]
            self.assertEqual(definition["missionId"], "a1m9")
            self.assertEqual(definition["bgType"], 0)
            self.assertEqual(definition["iconType"], 0)
            actual[story_key] = (
                definition["readingPopupRowId"],
                definition["titleId"],
                definition["contentTextIds"],
            )
        self.assertEqual(actual, expected)

        story_key = "text_a1m9_1"
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[story_key]
        popup = {
            "bgType": 0,
            "contentId": story_key,
            "iconType": 0,
            "id": definition["readingPopupRowId"],
            "overrideRadioId": "",
            "title": {"id": 0, "text": ""},
        }
        rich = {
            "contentList": [
                {"content": {"id": text_id, "text": ""}}
                for text_id in definition["contentTextIds"]
            ],
            "title": {"id": definition["titleId"], "text": ""},
        }
        self.assertIsNone(
            gap_queue._offline_text_definition_validation_failure(
                story_key, definition, popup, rich, {}, {},
            )
        )
        popup["id"] = story_key
        failure = gap_queue._offline_text_definition_validation_failure(
            story_key, definition, popup, rich, {}, {},
        )
        self.assertEqual(failure["validator"], "offlineTextDefinition")
        self.assertEqual(failure["gate"], "exactReadingPopupAndRichContentRows")
        self.assertEqual(
            failure["expected"]["popup"]["id"],
            "rp_text_a1m9_1",
        )
        self.assertEqual(failure["actual"]["popup"]["id"], story_key)

    def test_declared_e6m3_definition_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M3_RADIOS,
            {
                "radio_e6m3_10d6",
                "radio_e6m3_21",
                "radio_e6m3_22",
                "radio_e6m3_23",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES[
                "cutscene_e6m3_2"
            ]["definitionRowKeys"],
            tuple(
                f"cutscene_e6m3_2_{number:02d}"
                for number in range(1, 15)
            ),
        )
        misc = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "misc_dlg_e6m3_3d5"
        ]
        self.assertEqual(misc["registryKey"], "dlg_e6m3_3d5")
        self.assertEqual(misc["definitionName"], "dlg_e6m3_3d5")
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS),
            {
                "text_gm01m7_1",
                "text_a1m6d5_1",
                "text_a1m5_1",
                "text_a1m5_2",
                "text_a1m5_3",
                "text_a1m5_4",
                "text_a1m5_5",
                "text_a1m5_6",
                "text_a1m5_7",
                "text_a1m9_1",
                "text_a1m9_2",
                "text_a1m9_3",
                "text_a1m9_4",
                "text_a1m9_5",
                "text_a1m9_6",
                "text_a1m9_7",
                "text_e0m0_1",
                "text_e6m3_1",
                "text_e6m3_4",
                "text_e6m5_1",
                "text_e7m2_2",
                "text_e7m3_1",
                "text_e7m4_1",
                "text_e8m4_1",
                "text_e10m3_4",
                "text_e10m3_6",
                "text_e10m3_8",
                "text_e10m4_1",
                "text_gm01m22_5",
                "text_gm01m12_1",
                "text_gm01m13_1",
                "text_gm01m15_1",
                "text_gm01m15_8",
                "text_gm01m12_3",
                "text_gm01m12_5",
                "text_gm01m12_6",
                "text_gm01m12_7",
                "text_gm01m14_4",
                "text_gm01m14_5",
                "text_gm01m17_1",
            },
        )

    def test_declared_e6m5_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M5_RADIOS,
            {"radio_e6m5_4"},
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            "text_e6m5_1"
        ]
        self.assertEqual(
            definition["contentTextIds"],
            (2915169207318156019, -3317420327824307745),
        )
        self.assertEqual(
            definition["prtsDefinition"],
            {
                "rowId": "nar_collection_map02_69_1",
                "row": {
                    "contentId": "text_e6m5_1",
                    "desc": {"id": 0, "text": ""},
                    "firstLvId": "collection_map02_69",
                    "id": "nar_collection_map02_69_1",
                    "name": {"id": 6370990046482612204, "text": ""},
                    "order": 1,
                    "overrideRadioId": "",
                    "type": "text",
                },
            },
        )

    def test_declared_e2m8d5_offline_frontier_is_exact(self) -> None:
        expected = {
            "dlg_e2m8d5_2": {
                "lines": (
                    "dlg_e2m8d5_2_001",
                    "dlg_e2m8d5_2_002",
                    "dlg_e2m8d5_2_004",
                    "dlg_e2m8d5_2_006",
                    "dlg_e2m8d5_2_007",
                ),
                "options": (
                    "option_dlg_e2m8d5_2_1_001",
                    "option_dlg_e2m8d5_2_1_002",
                ),
                "proxyId": "pelica_map01_e2m8d5",
                "entryIndex": 2,
                "missionIdPresent": False,
            },
            "dlg_e2m8d5_3": {
                "lines": tuple(
                    f"dlg_e2m8d5_3_{number:03d}"
                    for number in range(1, 6)
                ),
                "options": ("option_dlg_e2m8d5_3_1_001",),
                "proxyId": "chen_map01_e2m8d5",
                "entryIndex": 0,
                "missionIdPresent": True,
            },
        }
        for story_key, facts in expected.items():
            definition = (
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]
            )
            self.assertEqual(definition["missionId"], "e2m8d5")
            self.assertEqual(definition["lineIds"], facts["lines"])
            self.assertEqual(definition["optionIds"], facts["options"])
            consumer = definition["npcProxyConsumer"]
            self.assertEqual(consumer["proxyId"], facts["proxyId"])
            self.assertEqual(consumer["entryIndex"], facts["entryIndex"])
            self.assertEqual(
                "missionId" in consumer["entry"],
                facts["missionIdPresent"],
            )
            self.assertFalse(consumer["entry"].get("missionId"))

    def test_declared_e11m8d5_offline_frontier_is_exact(self) -> None:
        registered = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e11m8d5_1"
        ]
        self.assertEqual(len(registered["lineIds"]), 10)
        self.assertEqual(len(registered["optionIds"]), 2)
        self.assertEqual(len(registered["missingAudioIds"]), 10)
        consumer = registered["npcProxyConsumer"]
        self.assertEqual(consumer["proxyId"], "lizy_map02_v1d4d0_world")
        self.assertEqual(consumer["entryIndex"], 0)
        self.assertEqual(consumer["entry"]["missionId"], "")
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_e11m8d5_2"
        ]
        self.assertEqual(
            text_only["lineIds"],
            ("dlg_e11m8d5_2_001", "dlg_e11m8d5_2_002"),
        )
        self.assertEqual(
            text_only["missingAudioIds"],
            ("au_dlg_e11m8d5_2_001", "au_dlg_e11m8d5_2_002"),
        )

    def test_declared_e5m5_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E5M5_RADIOS,
            {"radio_e5m5_1", "radio_e5m5_2"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS[
                "radio_e5m5_1"
            ],
            {"au_radio_e5m5_1_001", "au_radio_e5m5_1_002"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS[
                "radio_e5m5_2"
            ],
            {"au_radio_e5m5_2_001"},
        )

    def test_declared_e6m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M1_RADIOS,
            {"radio_e6m1_19"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e6m1_14"
        ]
        self.assertEqual(len(dialog["lineIds"]), 4)
        self.assertEqual(
            dialog["npcProxyConsumer"]["proxyId"],
            "lugang_map02_e6m1ZhenLie",
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e6m1_15"
        ]
        self.assertEqual(len(dialog["lineIds"]), 3)
        self.assertEqual(len(dialog["optionIds"]), 2)
        self.assertEqual(
            {
                row["proxyId"]
                for row in dialog["npcProxyConsumers"]
            },
            {
                "puyuan_map02_default",
                "puyuan_map02_e6m1ZhenLie",
            },
        )

    def test_declared_e10m4_definition_frontier_is_exact(self) -> None:
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS)
            & {"dlg_e10m4_16", "dlg_e10m4_17", "dlg_e10m4_21"},
            {"dlg_e10m4_21"},
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS)
            & {"dlg_e10m4_16", "dlg_e10m4_17", "dlg_e10m4_21"},
            {"dlg_e10m4_16", "dlg_e10m4_17"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e10m4_21"
            ]["missingAudioIds"],
            (
                "au_dlg_e10m4_21_001",
                "au_dlg_e10m4_21_002",
                "au_dlg_e10m4_21_003",
            ),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e10m4_21"
            ]["extraConfigSha256"],
            "BBA7D588A2B3D0B9A44D8D4D9D58A14246096C41E85ABA330357BAFC32140B94",
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
                "dlg_e10m4_16"
            ]["audioVariants"],
            {
                "au_dlg_e10m4_16_001": (
                    "au_dlg_e10m4_16_001_f",
                    "au_dlg_e10m4_16_001_m",
                ),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
                "dlg_e10m4_17"
            ]["missingAudioIds"],
            (
                "au_dlg_e10m4_17_001",
                "au_dlg_e10m4_17_002",
            ),
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS),
            {
                "sns_a1m8d1_1",
                "sns_e1m9_1",
                "sns_e7m4_1",
                "sns_e10m4_1",
                "sns_gm01m3_1",
                "sns_gm01m22_2",
                "sns_gm01m7_1",
                "sns_gm01m7_2",
            },
        )
        self.assertEqual(
            set(
                gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                    "sns_e10m4_1"
                ]["optionNextContentIds"]
            ),
            {
                "option_sns_e10m4_1_1_001",
                "option_sns_e10m4_1_2_001",
                "option_sns_e10m4_1_3_001",
                "option_sns_e10m4_1_5_001",
            },
        )
        self.assertIn(
            "text_e10m4_1",
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS,
        )

    def test_current_quest_attachment_diagnostics_are_exact(self) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payloads = {
            mission: gap_queue.load_mission_payload_with_variants(
                mission_dir,
                mission,
            )
            for mission in ("e2m8", "e5m2", "e10m3", "e10m4")
        }

        index, status = gap_queue.build_quest_attachment_diagnostic_index(
            payloads
        )

        self.assertEqual(status["status"], "active")
        self.assertEqual(status["sourceHashMismatches"], [])
        self.assertEqual(
            set(index),
            {
                "e2m8_q#5",
                "e5m2_q#33",
                "e5m2d5_q#12",
                "e10m3d5_q#7",
                "e10m4d5_q#31",
                "e10m4d5_q#34",
                "e10m4d5_q#35",
            },
        )
        self.assertEqual(
            index["e10m4d5_q#31"]["propertyKey"],
            "enemyStart1",
        )
        self.assertEqual(
            index["e10m4d5_q#35"]["propertyKey"],
            "enemyStart2",
        )
        self.assertEqual(
            index["e10m4d5_q#34"]["conditionType"],
            "GameConditionServerPlaceHolder",
        )
        self.assertEqual(index["e5m2_q#33"]["propertyKey"], "bridge")
        self.assertEqual(
            index["e2m8_q#5"]["propertyRecord"]["membership"],
            "getterList#2",
        )
        self.assertEqual(
            index["e10m3d5_q#7"]["npcProxyId"],
            "cuidaifu_map02_e10m3d5",
        )
        self.assertEqual(
            index["e5m2d5_q#12"]["recoveryStatus"],
            "closed_weak_leveldata_reference_without_typed_story_bridge",
        )
        self.assertEqual(
            index["e5m2d5_q#12"]["diagnosticStoryKeys"],
            ["radio_e5m2_7d5", "radio_e5m2_18"],
        )

    def test_quest_attachment_diagnostics_fail_closed_on_shape_change(
        self,
    ) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payloads = {
            mission: gap_queue.load_mission_payload_with_variants(
                mission_dir,
                mission,
            )
            for mission in ("e2m8", "e5m2", "e10m3", "e10m4")
        }
        flow = gap_queue._flow(payloads["e5m2"])
        quest = next(
            row
            for row in flow["quests"]
            if row["id"] == "e5m2d5_q#12"
        )
        quest["storyConnections"][0]["relation"] = "new_typed_route"

        index, status = gap_queue.build_quest_attachment_diagnostic_index(
            payloads
        )

        self.assertEqual(index, {})
        self.assertEqual(
            status["status"],
            "inactive_generated_shape_validation_failed",
        )
        self.assertEqual(
            status["validationFailures"],
            ["e5m2d5_q#12"],
        )
        self.assertEqual(
            status["validationFailureDetails"][0]["gate"],
            "weak_leveldata_context",
        )
        self.assertEqual(
            status["validationFailureDetails"][0]["questId"],
            "e5m2d5_q#12",
        )
        self.assertEqual(
            status["validationFailureDetails"][0]["actual"][
                "connectionRelations"
            ],
            ["new_typed_route", "variant_runtime_attachment"],
        )

    def test_property_getter_diagnostic_fails_closed_on_route_change(
        self,
    ) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payloads = {
            mission: gap_queue.load_mission_payload_with_variants(
                mission_dir,
                mission,
            )
            for mission in ("e2m8", "e5m2", "e10m3", "e10m4")
        }
        flow = gap_queue._flow(payloads["e2m8"])
        quest = next(
            row for row in flow["quests"] if row["id"] == "e2m8_q#5"
        )
        quest["storyConnections"][0]["relation"] = "typed_property_route"

        index, status = gap_queue.build_quest_attachment_diagnostic_index(
            payloads
        )

        self.assertEqual(index, {})
        self.assertEqual(
            status["validationFailures"],
            ["e2m8_q#5"],
        )
        detail = status["validationFailureDetails"][0]
        self.assertEqual(detail["validator"], "questAttachmentDiagnostic")
        self.assertEqual(
            detail["gate"],
            "property_getter_without_story_chain",
        )
        self.assertEqual(detail["questId"], "e2m8_q#5")
        self.assertEqual(
            detail["sourcePath"],
            gap_queue.QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "missionRuntime:e2m8"
            ],
        )
        self.assertEqual(
            detail["actual"]["connectionRelations"],
            ["levelscript_condition_scope", "typed_property_route"],
        )

    def test_mission_bound_proxy_diagnostic_fails_closed_on_proxy_change(
        self,
    ) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payloads = {
            mission: gap_queue.load_mission_payload_with_variants(
                mission_dir,
                mission,
            )
            for mission in ("e2m8", "e5m2", "e10m3", "e10m4")
        }
        flow = gap_queue._flow(payloads["e10m3"])
        quest = next(
            row for row in flow["quests"] if row["id"] == "e10m3d5_q#7"
        )
        quest["proxyDialogs"][0]["dialogId"] = "dlg_unrelated"

        index, status = gap_queue.build_quest_attachment_diagnostic_index(
            payloads
        )

        self.assertEqual(index, {})
        self.assertEqual(status["validationFailures"], ["e10m3d5_q#7"])
        detail = status["validationFailureDetails"][0]
        self.assertEqual(detail["validator"], "questAttachmentDiagnostic")
        self.assertEqual(detail["gate"], "mission_bound_npc_proxy_context")
        self.assertEqual(detail["questId"], "e10m3d5_q#7")
        self.assertEqual(
            detail["sourcePath"],
            gap_queue.QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "missionRuntime:e10m3d5"
            ],
        )

    def test_quest_attachment_diagnostics_fail_closed_on_hash_change(
        self,
    ) -> None:
        index, status = gap_queue.build_quest_attachment_diagnostic_index(
            {},
            source_path_overrides={
                "missionRuntime:e5m2": Path(__file__),
            },
        )

        self.assertEqual(index, {})
        self.assertEqual(
            status["status"],
            "inactive_source_validation_failed",
        )
        self.assertEqual(
            status["sourceHashMismatches"],
            ["missionRuntime:e5m2"],
        )

    def test_declared_e6m4_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M4_RADIOS,
            {
                "radio_e6m4_5",
                "radio_e6m4_9",
                "radio_e6m4_15",
                "radio_e6m4_25",
                "radio_e6m4_35",
                "radio_e6m4_36",
                "radio_e6m4_37",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e6m4_1"
            ]["timelineRegistryId"],
            400,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e6m4_hydrantStart"
            ]["timelineRegistryId"],
            324,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS[
                "cutscene_e6m4_hydrantStart"
            ],
            1,
        )

    def test_declared_e7m3_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E7M3_RADIOS,
            {"radio_e7m3_16", "radio_e7m3_26"},
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                    "dlg_e7m3_13"
                ]["optionIds"]
            ),
            3,
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                    "dlg_e7m3_15"
                ]["optionIds"]
            ),
            6,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e7m3_16"
            ]["optionIds"],
            ("option_dlg_e7m3_16_1_001",),
        )

    def test_declared_e7m4_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E7M4_RADIOS,
            {"radio_e7m4_3"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e7m4_7"
        ]
        self.assertEqual(len(dialog["lineIds"]), 3)
        self.assertEqual(
            dialog["missingAudioIds"],
            (
                "au_dlg_e7m4_7_001",
                "au_dlg_e7m4_7_002",
                "au_dlg_e7m4_7_003",
            ),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                "sns_e7m4_1"
            ]["contentIds"],
            (-1, 1, 2, 3, 4, 5, 6, 7),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                "sns_e7m4_1"
            ]["contentParamsByContentId"],
            {4: ("sns_image_e7m4_1",)},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_e7m4_1"
            ]["contentTextIds"],
            (
                -11413322245013826,
                -7389517897749196338,
            ),
        )

    def test_declared_e11m8_partial_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E11M8_RADIOS,
            {"radio_e11m8_5"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e11m8_9"
        ]
        self.assertEqual(len(dialog["lineIds"]), 30)
        self.assertEqual(len(dialog["ownedTimeline"]["fullLineIds"]), 30)
        self.assertEqual(
            dialog["optionIds"],
            (
                "option_dlg_e11m8_9_1_001",
                "option_dlg_e11m8_9_1_002",
            ),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
                "dlg_e11m8_13"
            ]["missingAudioIds"],
            (),
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_TEXT_TABLE_ONLY_STORIES),
            {
                "black_e7m1_3",
                "black_e11m8_12",
                "black_e11m8_39",
            },
        )

    def test_npc_proxy_segment_native_path_closes_context_without_order(self) -> None:
        connection = {
            "key": "black_a1m8d3_2",
            "relation": "npc_proxy_segment_levelscript_mission_context",
            "direction": "context",
            "confidence": "native_exact_npc_proxy_segment_shell",
            "evidenceTier": "derived_exact_shell",
            "storyOwnerMission": "a1m8d3",
            "questTriggerStatus":
                "same_authored_npc_proxy_segment_not_quest_playback",
            "executionSide": "client",
            "serverExchange": False,
            "npcProxyIds": ["liaowuhen_map02_v1d2d0_005"],
            "segmentIdsGlobal": ["10100620005"],
            "candidateQuestIds": ["a1m8d3_q#2"],
            "sourceFiles": ["LevelScriptData/map02_lv001/10100620005.json"],
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "path": [{
                    "actionName": "NarrativeBlackScreenAction",
                    "recordClass": "play_black",
                    "texts": ["black_a1m8d3_2_001"],
                }],
            }],
        }
        flow = {"missionStoryConnections": [connection]}

        rows = gap_queue._closed_exact_native_context_isolated_scenes(
            flow,
            {"black_a1m8d3_2"},
            "a1m8d3",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["recoveryStatus"],
            "closed_exact_npc_proxy_segment_playback_context_no_relative_order",
        )
        self.assertEqual(rows[0]["candidateQuestIds"], ["a1m8d3_q#2"])

        broken = {**connection, "nativeEventOwners": [{
            **connection["nativeEventOwners"][0],
            "status": "partial",
        }]}
        self.assertEqual(
            gap_queue._closed_exact_native_context_isolated_scenes(
                {"missionStoryConnections": [broken]},
                {"black_a1m8d3_2"},
                "a1m8d3",
            ),
            [],
        )

    def test_cross_owner_npc_proxy_segment_radio_fails_closed(self) -> None:
        connection = {
            "key": "radio_a1m6d1_1",
            "relation": "npc_proxy_segment_levelscript_mission_context",
            "direction": "context",
            "phase": "runtime_playback",
            "confidence": "native_exact_npc_proxy_segment_shell",
            "evidenceTier": "derived_exact_shell",
            "storyOwnerMission": "a1m6d1",
            "questTriggerStatus":
                "same_authored_npc_proxy_segment_not_quest_playback",
            "executionSide": "client",
            "serverExchange": False,
            "npcProxyIds": ["yuxiuli2_map02_v1d1d0_002"],
            "segmentIdsGlobal": ["22800970016"],
            "candidateQuestIds": ["a1m6d4_q#2", "a1m6d4_q#3"],
            "scriptIds": ["22800970016"],
            "sourceFiles": ["MissionRuntimeAsset/a1m6d4.json"],
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "path": [{
                    "actionName": "PlayRadio",
                    "recordClass": "play_radio",
                    "texts": ["radio_a1m6d1_1"],
                }],
            }],
            "npcProxyTrackingRows": [{
                "missionId": "a1m6d4",
                "questId": "a1m6d4_q#2",
                "sourceFile": "MissionRuntimeAsset/a1m6d4.json",
            }],
            "npcProxyRegistryRows": [{
                "dictionaryKey": "22800970016",
                "proxyId": "yuxiuli2_map02_v1d1d0_002",
                "segmentIdGlobal": "22800970016",
                "sourceFile": "WorldEntityRegistry.json",
            }],
            "npcProxyExRows": [{
                "proxyId": "yuxiuli2_map02_v1d1d0_002",
                "missionId": "a1m6d4",
                "rowIndex": 0,
                "sourceFile": "NpcProxyExDataTable.json",
            }],
        }
        self.assertTrue(
            gap_queue._exact_cross_owner_npc_proxy_segment_story_context(
                connection,
                "a1m6d1",
                "a1m6d4",
            )
        )
        rows = gap_queue._closed_exact_native_context_isolated_scenes(
            {"missionStoryConnections": [{
                **connection,
                "contextMissionBundle": "a1m6d4",
            }]},
            {"radio_a1m6d1_1"},
            "a1m6d1",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["contextMissionId"], "a1m6d4")
        self.assertTrue(rows[0]["contextMissionMismatch"])
        self.assertFalse(
            gap_queue._exact_cross_owner_npc_proxy_segment_story_context(
                {
                    **connection,
                    "npcProxyExRows": [{
                        **connection["npcProxyExRows"][0],
                        "missionId": "a1m6d1",
                    }],
                },
                "a1m6d1",
                "a1m6d4",
            )
        )

    def test_tracked_interactive_context_closes_without_playback_or_order(self) -> None:
        connection = {
            "key": "dlg_a1m6d5_8",
            "relation": "entity_tracking_interactive_story_target",
            "direction": "context",
            "phase": "tracking",
            "confidence": "native_exact_tracked_interactive_property",
            "evidenceTier": "native_exact_context",
            "storyOwnerMission": "a1m6d5",
            "trackingMissionId": "a1m6d5",
            "candidateQuestIds": ["a1m6d5_q#4"],
            "questTriggerStatus":
                "navigation_target_configured_story_not_playback",
            "executionSide": "client",
            "networkRole": "local_navigation_context",
            "clientNavigationOnly": True,
            "serverExchange": False,
            "levelIds": ["map02_lv002"],
            "scriptIds": ["22800970028"],
            "localScriptIds": ["970028"],
            "entitySlotIds": ["40017"],
            "entityDetailIds": ["int_narrative_empty"],
            "entityTemplateIds": ["int_narrative_mission"],
            "entityTemplatePaths": ["data_int_narrative_mission.json"],
            "registrySourceFiles": ["WorldEntityRegistry.json"],
            "interactiveTableSourceFiles": ["InteractiveTable.json"],
            "sourceFiles": ["MissionRuntimeAsset/a1m6d5.json"],
            "trackingObjectiveIndex": 1,
            "trackingIndex": 0,
            "interactivePropertyKey": "type_id",
            "interactiveEntryOffset": 15999,
            "interactivePropertyOffset": 16297,
            "interactiveStoryOffset": 16331,
        }
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            {"missionStoryConnections": [connection]},
            {"dlg_a1m6d5_8"},
            "a1m6d5",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["recoveryStatus"],
            "closed_exact_tracked_interactive_context_no_relative_order",
        )
        broken = {**connection, "clientNavigationOnly": False}
        self.assertEqual(
            gap_queue._closed_exact_runtime_config_isolated_scenes(
                {"missionStoryConnections": [broken]},
                {"dlg_a1m6d5_8"},
                "a1m6d5",
            ),
            [],
        )

    def test_sns_tracking_context_closes_without_playback_or_order(self) -> None:
        payload = gap_queue.read_json(
            gap_queue.ROOT
            / "webui/data/lang/CN/mission/a1m13.json",
            {},
        )
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            payload["flow"],
            {"sns_a1m13_1"},
            "a1m13",
        )
        closure = next(
            row for row in rows if row["sceneKey"] == "sns_a1m13_1"
        )
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_mission_tracking_context_no_relative_order",
        )
        self.assertEqual(closure["questId"], "a1m13_q#1")

        broken = copy.deepcopy(payload["flow"])
        broken["quests"][1]["storyConnections"][0]["playback"] = True
        self.assertNotIn(
            "sns_a1m13_1",
            {
                row["sceneKey"]
                for row in gap_queue._closed_exact_runtime_config_isolated_scenes(
                    broken,
                    {"sns_a1m13_1"},
                    "a1m13",
                )
            },
        )

    def test_mission_accept_dialog_closes_with_lifecycle_only(self) -> None:
        connection = {
            "key": "dlg_gm01m22_1",
            "kind": "dialog",
            "relation": "mission_accept_dialog",
            "direction": "story_to_mission",
            "phase": "accept",
            "confidence": "native_typed_direct",
            "source": (
                "MissionRuntimeAsset/gm01m22_meta.json."
                "acceptMode.modeInfo.dialogId"
            ),
            "acceptMode": 3,
            "acceptModeType": "MissionAcceptMode+NPCInfo",
            "npcProxyId": "jite_map01_005",
            "levelId": "map01_lv005",
            "finishId": -1,
        }
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            {"missionStoryConnections": [connection]},
            {"dlg_gm01m22_1"},
            "gm01m22",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["recoveryStatus"],
            "closed_exact_mission_accept_dialog_no_relative_order",
        )
        self.assertEqual(rows[0]["phase"], "accept")
        self.assertIn("does not create a relative edge", rows[0]["orderBoundary"])

        for field, bad_value in (
            ("relation", "mission_finish_dialog"),
            ("source", "MissionRuntimeAsset/gm01m22.json.dialogId"),
            ("acceptModeType", "MissionAcceptMode"),
        ):
            broken = {**connection, field: bad_value}
            self.assertEqual(
                gap_queue._closed_exact_runtime_config_isolated_scenes(
                    {"missionStoryConnections": [broken]},
                    {"dlg_gm01m22_1"},
                    "gm01m22",
                ),
                [],
            )

    def test_prime_reachable_dialog_dependency_is_hash_locked(self) -> None:
        payload = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/a1m4.json",
            {},
        )
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            payload["flow"],
            {"dlg_a1m4_2"},
            "a1m4",
        )
        closure = next(
            row for row in rows if row["sceneKey"] == "dlg_a1m4_2"
        )
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_parent_dialog_dependency_no_relative_order",
        )
        self.assertEqual(
            closure["trunkIds"],
            ["dlg_a1m4_2_001", "dlg_a1m4_2_002"],
        )

        broken = copy.deepcopy(payload["flow"])
        broken["quests"][0]["storyConnections"][1][
            "questPlayback"
        ] = True
        self.assertNotIn(
            "dlg_a1m4_2",
            {
                row["sceneKey"]
                for row in gap_queue._closed_exact_runtime_config_isolated_scenes(
                    broken,
                    {"dlg_a1m4_2"},
                    "a1m4",
                )
            },
        )

    def test_gm01m22_nested_dialog_dependencies_are_hash_locked(self) -> None:
        payload = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/gm01m22.json",
            {},
        )
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            payload["flow"],
            {"dlg_gm01m22_6", "dlg_gm01m22_8"},
            "gm01m22",
        )
        by_key = {row["sceneKey"]: row for row in rows}
        self.assertEqual(set(by_key), {"dlg_gm01m22_6", "dlg_gm01m22_8"})
        for story_key in by_key:
            self.assertEqual(
                by_key[story_key]["parentStoryKey"],
                "dlg_gm01m22_hapo",
            )
            self.assertEqual(by_key[story_key]["dialogIds"], [story_key])
            self.assertEqual(
                by_key[story_key]["recoveryStatus"],
                "closed_exact_parent_dialog_dependency_no_relative_order",
            )

        broken = copy.deepcopy(payload["flow"])
        dependency = next(
            row
            for quest in broken["quests"]
            for row in quest.get("storyConnections") or []
            if row.get("key") == "dlg_gm01m22_6"
        )
        dependency["dialogTreePrimeStoryPlaybackCarriers"][0][
            "sourcePathId"
        ] = "changed"
        self.assertNotIn(
            "dlg_gm01m22_6",
            {
                row["sceneKey"]
                for row in gap_queue._closed_exact_runtime_config_isolated_scenes(
                    broken,
                    {"dlg_gm01m22_6", "dlg_gm01m22_8"},
                    "gm01m22",
                )
            },
        )

    def test_disconnected_dialog_tree_context_fails_closed(self) -> None:
        disconnected = {
            "key": "black_e11m8_27",
            "relation": "dialog_tree_narrative_action",
            "storyOwnerMission": "e11m8",
            "parentStoryKey": "dlg_e11m8_3",
            "confidence": "native_exact_parent_quest",
            "evidenceTier": "native_direct",
            "scopeCompleteness": "complete",
            "allParentStoryKeys": ["dlg_e11m8_3"],
            "nativeMappingId":
                gap_queue.DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "sourceFiles": ["dlg_e11m8_3.json"],
            "sourcePathIds": ["90FF60230D4F7FDA"],
            "occurrenceCount": 1,
            "dialogTreeNarrativeActions": [{
                "dialogKey": "dlg_e11m8_3",
                "actionType":
                    "Beyond.Gameplay.DialogNarrativeMaskActionData",
                "nativeMappingId":
                    gap_queue.DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
                "reachableFromPrimeNode": False,
                "primeToActionNodePath": [],
                "primeToActionConnectionPath": [],
                "incomingNodeIds": ["12"],
                "outgoingNodeIds": ["14"],
                "textId": "black_e11m8_27_001",
                "actionPath": "nodes[13].actions[0]",
                "nodeId": "13",
                "sourceFile": "dlg_e11m8_3.json",
                "sourcePathId": "90FF60230D4F7FDA",
            }],
        }
        rows = (
            gap_queue
            ._closed_exact_disconnected_dialog_tree_context_isolated_scenes(
                {"missionStoryConnections": [disconnected]},
                {"black_e11m8_27"},
                "e11m8",
            )
        )
        self.assertEqual(
            [row["sceneKey"] for row in rows],
            ["black_e11m8_27"],
        )
        disconnected["dialogTreeNarrativeActions"][0][
            "incomingNodeIds"
        ] = []
        self.assertEqual(
            [
                row["sceneKey"]
                for row in (
                    gap_queue
                    ._closed_exact_disconnected_dialog_tree_context_isolated_scenes(
                        {"missionStoryConnections": [disconnected]},
                        {"black_e11m8_27"},
                        "e11m8",
                    )
                )
            ],
            ["black_e11m8_27"],
        )
        disconnected["dialogTreeNarrativeActions"][0][
            "outgoingNodeIds"
        ] = []
        self.assertEqual(
            gap_queue
            ._closed_exact_disconnected_dialog_tree_context_isolated_scenes(
                {"missionStoryConnections": [disconnected]},
                {"black_e11m8_27"},
                "e11m8",
            ),
            [],
        )
        disconnected["dialogTreeNarrativeActions"][0][
            "incomingNodeIds"
        ] = ["12"]
        disconnected["dialogTreeNarrativeActions"][0][
            "outgoingNodeIds"
        ] = ["14"]
        disconnected["dialogTreeNarrativeActions"][0][
            "reachableFromPrimeNode"
        ] = True
        self.assertEqual(
            gap_queue
            ._closed_exact_disconnected_dialog_tree_context_isolated_scenes(
                {"missionStoryConnections": [disconnected]},
                {"black_e11m8_27"},
                "e11m8",
            ),
            [],
        )

    def test_declared_e11m3_radio_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E11M3_RADIOS,
            {
                "radio_e11m3_3",
                "radio_e11m3_15",
                "radio_e11m3_18",
                "radio_e11m3_22",
                "radio_e11m3_23",
            },
        )

    def test_declared_e11m5_frontier_preserves_owned_mixed_timeline(
        self,
    ) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E11M5_RADIOS,
            {
                "radio_e11m5_12",
                "radio_e11m5_19",
                "radio_e11m5_20",
                "radio_e11m5_21",
                "radio_e11m5_22",
                "radio_e11m5_23",
                "radio_e11m5_24",
            },
        )
        owned = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e11m5_9"
        ]["ownedTimeline"]
        self.assertEqual(owned["timeline"], "dlgtl_e11m5_9_sub_1")
        self.assertEqual(owned["trackPathId"], 5795311945645305682)
        self.assertEqual(
            owned["fullLineIds"][9:15],
            (
                "dlg_e11m6_9_005",
                "dlg_e11m6_9_006",
                "dlg_e11m6_9_007",
                "dlg_e11m6_9_003",
                "dlg_e11m6_9_008",
                "dlg_e11m6_9_004",
            ),
        )

    def test_declared_e11m6_radio_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E11M6_RADIOS,
            {
                "radio_e11m6_10",
                "radio_e11m6_13",
                *{
                    f"radio_e11m6_{number}"
                    for number in range(19, 39)
                },
            },
        )

    def test_exact_build_offline_exhausted_scene_is_deferred_only(self) -> None:
        story_key = "radio_e11m4_29"
        partial = partial_mission(
            "e11m4",
            scenes=[story_key],
            isolated=[story_key],
        )
        partial["nodes"][0]["kind"] = "radio"
        payload = mission_payload()
        payload["flow"]["unlinked"] = [story_key]
        evidence = {
            story_key: {
                "sceneKey": story_key,
                "missionId": "e11m4",
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    "radio_definition_without_recovered_consumer",
                "graphEffect": "none",
            },
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            offline_exhaustion_index=evidence,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["deferredOfflineExhaustedIsolatedScenes"],
            1,
        )
        self.assertEqual(
            row["deferredOfflineExhaustedIsolatedScenes"][0][
                "evidenceKind"
            ],
            "radio_definition_without_recovered_consumer",
        )
        self.assertEqual(row["score"], 0)

    def test_exact_owned_timeline_dialog_can_defer_without_unlinked_flag(
        self,
    ) -> None:
        story_key = "dlg_e11m5_9"
        partial = partial_mission(
            "e11m5",
            scenes=[story_key],
            isolated=[story_key],
        )
        evidence = {
            story_key: {
                "sceneKey": story_key,
                "missionId": "e11m5",
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    "registered_dialog_definition_without_recovered_activator",
                "sharedTimelineContext": {
                    "relation":
                        "owned_dialog_timeline_exact_mixed_story_context",
                    "graphEffect": "none",
                },
                "graphEffect": "none",
            },
        }

        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            offline_exhaustion_index=evidence,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["deferredOfflineExhaustedIsolatedScenes"],
            1,
        )
        self.assertEqual(row["score"], 0)

    def test_offline_exhausted_scene_with_runtime_route_reopens(self) -> None:
        story_key = "radio_e11m4_29"
        partial = partial_mission(
            "e11m4",
            scenes=[story_key],
            isolated=[story_key],
        )
        partial["nodes"][0]["kind"] = "radio"
        payload = mission_payload()
        payload["flow"]["unlinked"] = [story_key]
        payload["flow"]["unlinkedNativePlayback"] = [{
            "key": story_key,
            "relation": "native_story_playback_unscoped",
        }]
        evidence = {
            story_key: {
                "sceneKey": story_key,
                "missionId": "e11m4",
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "graphEffect": "none",
            },
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
            offline_exhaustion_index=evidence,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)
        self.assertEqual(
            row["metrics"]["deferredOfflineExhaustedIsolatedScenes"],
            0,
        )


class NonMissionContentClosureTests(unittest.TestCase):
    """Table-proven non-mission content must leave the narrative queue.

    Only authored table contents may admit a key. Filename shape must not,
    because filename inference is not original-data proof.
    """

    def _table_root(self, **tables) -> Path:
        import json
        import tempfile

        root = Path(tempfile.mkdtemp())
        for name, payload in tables.items():
            (root / f"{name}.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
        return root

    def test_speaker_keyed_radio_continuation_is_closed(self) -> None:
        root = self._table_root(AudioRadioContinueTable={
            "aglina": {
                "speaker": "aglina",
                "selfContinue": ["radio_continue_self_aglina_01"],
                "otherContinue": [],
            },
        })
        keys = gap_queue.non_mission_content_keys(root)
        self.assertIn("radio_continue_self_aglina_01", keys)
        self.assertEqual(
            keys["radio_continue_self_aglina_01"]["table"],
            "AudioRadioContinueTable",
        )

        partial = partial_mission(
            "e1m1",
            scenes=["radio_continue_self_aglina_01"],
            isolated=["radio_continue_self_aglina_01"],
        )
        partial["nodes"][0]["kind"] = "radio"
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            non_mission_content=keys,
        )

        self.assertEqual(row["metrics"]["coreIsolatedScenes"], 1)
        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedNonMissionContentIsolatedScenes"], 1
        )
        closed = row["closedNonMissionContentIsolatedScenes"][0]
        self.assertEqual(
            closed["recoveryStatus"], "closed_table_backed_non_mission_content"
        )
        self.assertEqual(closed["tableKeyedBy"], "speaker")

    def test_sns_topic_dialog_is_closed(self) -> None:
        root = self._table_root(SNSDialogTopicTable={
            "topic_chr_0004_pelica_1": {
                "topicId": "topic_chr_0004_pelica_1",
                "includeDialogIds": ["sns_topic_chr_0004_pelica_1"],
                "sortId": 3,
            },
        })
        keys = gap_queue.non_mission_content_keys(root)
        self.assertEqual(
            keys["sns_topic_chr_0004_pelica_1"]["field"], "includeDialogIds"
        )

    def test_exact_guide_runtime_radio_is_closed_without_order(self) -> None:
        story_key = "radio_blackbox_common_1"
        partial = partial_mission(
            "blackbox_common",
            scenes=[story_key],
            isolated=[story_key],
        )
        partial["nodes"][0]["kind"] = "radio"
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            non_mission_content={
                story_key: {
                    "evidenceKind": "guide_runtime_asset",
                    "content": "factory_interaction_lock_guide_radio",
                    "assetType":
                        "Beyond.Gameplay.Actions.GuideRuntimeAsset",
                    "consumerClass":
                        "Beyond.Gameplay.Actions."
                        "FacSetInteractLockedState",
                    "assetCount": 10,
                    "actionCount": 13,
                    "assetNames": ["guide_blackbox_test"],
                    "guideLevelIds": ["blackbox_test"],
                    "nativeMappingId": "mapping-v1",
                    "nativeMethod": {"token": "0x06008a6d"},
                    "orderBoundary": "no mission or Story order edge",
                    "evidenceReport": "report.json",
                },
            },
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedNonMissionContentIsolatedScenes"], 1
        )
        closed = row["closedNonMissionContentIsolatedScenes"][0]
        self.assertEqual(
            closed["recoveryStatus"],
            "closed_exact_guide_runtime_non_mission_content",
        )
        self.assertEqual(closed["actionCount"], 13)

    def test_lookalike_key_not_in_any_table_stays_actionable(self) -> None:
        # Same filename shape, absent from the tables: must NOT be closed.
        root = self._table_root(AudioRadioContinueTable={})
        keys = gap_queue.non_mission_content_keys(root)
        partial = partial_mission(
            "e1m1",
            scenes=["radio_continue_self_ghost_99"],
            isolated=["radio_continue_self_ghost_99"],
        )
        partial["nodes"][0]["kind"] = "radio"
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            non_mission_content=keys,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)
        self.assertEqual(
            row["metrics"]["closedNonMissionContentIsolatedScenes"], 0
        )

    def test_missing_table_directory_yields_no_keys(self) -> None:
        keys = gap_queue.non_mission_content_keys(Path("does/not/exist"))
        self.assertEqual(keys, {})


if __name__ == "__main__":
    unittest.main()
