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
                "exact counted LevelData interactive list -> next-record-"
                "bounded 25-member LevelInteractiveData -> "
                "componentProperties[94].type_id; the final unbounded list "
                "item is excluded"
            ),
            "storyOwnerMission": "e1m1",
            "storyBinding": True,
            "ownership": False,
            "nativeMappingId":
                "leveldata-interactive-narrative-config-v1",
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
            "entityLogicId": 10002,
            "entityDetailIds": ["int_narrative_scene_book"],
            "entityTemplateIds": ["int_narrative_scene"],
            "narrativeComponentKey": 94,
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

        payload["flow"]["missionStoryConnections"][0][
            "interactiveRecordIndex"
        ] = 2
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
