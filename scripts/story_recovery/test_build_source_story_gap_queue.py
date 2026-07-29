from __future__ import annotations

import sys
import unittest
from pathlib import Path


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

    def test_declared_dialog_deferrals_preserve_shared_timeline_boundary(
        self,
    ) -> None:
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS),
            {
                "dlg_e1m2_6",
                "misc_dlg_e1m3_5d5",
                "dlg_e2m4_10",
                "dlg_e2m5_6",
                "dlg_e2m6_12",
                "dlg_e3m3_12",
                "dlg_e3m3_13",
                "dlg_e5m1_3",
                "dlg_e5m2_2",
                "dlg_e5m2_8",
                "misc_dlg_e5m2_3d5",
                "dlg_e6m1_14",
                "dlg_e6m1_15",
                "dlg_e6m3_6",
                "dlg_e6m3_12",
                "misc_dlg_e6m3_3d5",
                "dlg_e7m2_11",
                "dlg_e7m2_13",
                "dlg_e7m3_13",
                "dlg_e7m3_15",
                "dlg_e7m3_16",
                "dlg_e7m4_7",
                "dlg_e10m1_7",
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
                "radio_e1m3_13",
                "radio_e1m3_13d5",
                "radio_e1m3_13d7",
                "radio_e1m3_18",
                "radio_e1m3_32",
                "radio_e1m3_34",
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
            gap_queue.OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[
                "cutscene_e2m6_designer_anchorperish_001"
            ]["timelineRegistryId"],
            265,
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
                    "dlg_e2m6_18"
                ]["lineIds"]
            ),
            7,
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
                    tracked_world_entity,
                ],
            },
            {"radio_e1m3_13", "radio_e1m3_32"},
            "e1m3",
        )
        self.assertEqual(
            [row["sceneKey"] for row in rows],
            ["radio_e1m3_13", "radio_e1m3_32"],
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
                                invalid_tracked,
                            ],
                        },
                        {"radio_e1m3_13", "radio_e1m3_32"},
                        "e1m3",
                    )
                )
            ],
            ["radio_e1m3_13"],
        )

    def test_declared_e7m2_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E7M2_RADIOS,
            {
                "radio_e7m2_2",
                "radio_e7m2_9",
                "radio_e7m2_12",
                "radio_e7m2_14",
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
            {"text_e7m2_2", "text_e7m2_3"},
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
            gap_queue.OFFLINE_EXHAUSTION_MISSING_AUDIO_IDS[
                "radio_e0m0_10"
            ],
            {
                "au_radio_e0m0_10_001",
                "au_radio_e0m0_10_002",
                "au_radio_e0m0_10_003",
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
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E10M3_RADIOS,
            {"radio_e10m3_10"},
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
                "dlg_e10m4_16",
                "dlg_e10m4_17",
                "dlg_e10m3_10",
                "dlg_e10m3_11",
                "dlg_e10m3_12",
                "dlg_e2m6_18",
                "dlg_e11m8_13",
                "dlg_e11m8_14",
            },
        )
        self.assertEqual(len(text_only["dlg_e10m3_10"]["lineIds"]), 8)
        self.assertEqual(len(text_only["dlg_e10m3_11"]["lineIds"]), 4)
        self.assertEqual(len(text_only["dlg_e10m3_12"]["lineIds"]), 16)

    def test_declared_e6m3_definition_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M3_RADIOS,
            {
                "radio_e6m3_1",
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
                "text_e0m0_1",
                "text_e6m3_1",
                "text_e6m3_4",
                "text_e7m2_2",
                "text_e7m2_3",
                "text_e7m3_1",
                "text_e7m3_2",
                "text_e7m4_1",
                "text_e10m3_4",
                "text_e10m3_6",
                "text_e10m3_8",
                "text_e10m4_1",
            },
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
            {"sns_e7m4_1", "sns_e10m4_1"},
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
            {"black_e11m8_12", "black_e11m8_39"},
        )
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
