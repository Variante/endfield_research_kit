from ._support import *

class SourceGapModelTests(SourceGapTestCase):
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

    def test_runtime_shadowed_native_path_is_closed_not_actionable(self) -> None:
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
                    "status": "exact_serialized_control_path_runtime_shadowing",
                    "headerName": "ScriptEvent_OnScriptStageChanged",
                    "headerLocalId": 4,
                    "eventDetail": {
                        "summary": "local LevelScript stage changes to 2",
                    },
                    "path": [
                        {
                            "localId": 7,
                            "runtimeShadowedRecordOffsets": [100],
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
            "exact_serialized_control_path_runtime_shadowing",
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

    def test_repeatable_dialog_finish_is_a_typed_strict_attachment(self) -> None:
        partial = partial_mission("c1m1", scenes=["dlg_c1m1_1"])
        payload = mission_payload(quest_ids=["c1m1_q#1"])
        payload["flow"]["quests"] = [{
            "id": "c1m1_q#1",
            "storyConnections": [{
                "key": "dlg_c1m1_1",
                "relation": "objective_condition",
                "direction": "story_to_quest",
                "phase": "progress",
                "confidence": "direct",
                "source": (
                    "MissionRuntimeAsset.questDic[*].objectiveList[0]"
                    ".condition._dialogId"
                ),
                "objectiveIndex": 1,
                "conditionType": "CheckRepeatableTalkFinish",
            }],
        }]
        payload["timelineRecovery"]["scenePlacement"] = {
            "dlg_c1m1_1": {
                "sceneKey": "dlg_c1m1_1",
                "questIds": ["c1m1_q#1"],
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

    def test_exact_property_story_consumer_is_a_strict_attachment(self) -> None:
        story_key = "radio_c1m1_1"
        quest_id = "c1m1_q#1"
        partial = partial_mission("c1m1", scenes=[story_key])
        payload = mission_payload(quest_ids=[quest_id])
        owner = {
            "status": "exact_serialized_control_path",
            "headerName": "ScriptEvent_OnPropertyChanged",
            "downstreamControlStatus": "exact_serialized_typed_reachability",
            "eventDetail": {
                "propertyKeyFilter": "allTalkFinished",
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "transport": "local-level-script-variable-event",
                "validateParam": {"constValue": True},
            },
            "path": [{"localId": 9, "recordClass": "play_radio"}],
        }
        connection = {
            "key": story_key,
            "relation": "levelscript_property_story_consumer",
            "direction": "shared_trigger",
            "phase": "progress_and_runtime_playback",
            "confidence": "native_typed_direct",
            "evidenceTier": "native_direct",
            "conditionType": "CheckLevelScriptPropertyBool",
            "conditionKey": "allTalkFinished",
            "conditionValue": True,
            "mapId": "level_a",
            "scriptId": "1001",
            "nativeEventOwner": owner,
            "levelScriptOccurrence": {
                "levelId": "level_a",
                "scriptId": "1001",
                "sourceFile": (
                    "export_full/structured/StreamingAssets/Data/Json/"
                    "LevelScriptData/level_a/1001.json"
                ),
                "recordClass": "play_radio",
                "localId": 9,
            },
            "sourceFiles": [
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/c1m1.json",
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelScriptData/level_a/1001.json",
            ],
        }
        payload["flow"]["quests"] = [{
            "id": quest_id,
            "storyConnections": [connection],
        }]
        payload["timelineRecovery"]["scenePlacement"] = {
            story_key: {
                "sceneKey": story_key,
                "questIds": [quest_id],
                "questAttachSources": [{"source": "scriptCondition"}],
            },
        }

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(row["questIdsWithoutStrictStoryAttachment"], [])

        connection["nativeEventOwner"]["eventDetail"][
            "propertyKeyFilter"
        ] = "different"
        invalid = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(
            invalid["questIdsWithoutStrictStoryAttachment"],
            [quest_id],
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
        story_key = "dlg_gm01m14_2"
        mission = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/gm01m14.json",
            {},
        )
        connection = next(
            row
            for row in (
                mission.get("flow", {}).get("missionStoryConnections") or []
            )
            if row.get("key") == story_key
            and row.get("relation")
            == "unique_mission_tracked_npc_proxy_dialog_context"
        )
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
        self.assertEqual(
            closure["candidateQuestIds"],
            connection["candidateQuestIds"],
        )
        self.assertEqual(
            closure["recoveryMethod"],
            "complete_mission_runtime_proxy_census",
        )
        self.assertTrue(closure["sourceSha256"])
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

    def test_partial_dialog_tree_scope_closes_when_all_exact_carriers_exist(
        self,
    ) -> None:
        partial = partial_mission(
            "e1m1",
            scenes=["black_a"],
            isolated=["black_a"],
        )

        def occurrence(parent: str, source_path_id: str) -> dict:
            return {
                "textId": "black_a_001",
                "actionType":
                    "Beyond.Gameplay.DialogNarrativeMaskActionData",
                "actionKind": "narrative",
                "actionPath": "nodes[3]._transitionData.actions[0]",
                "nodeId": "3",
                "dialogKey": parent,
                "sourceFile": f"TextAsset/{parent}.json",
                "sourcePathId": source_path_id,
                "dialogTreeConnectionPlacementStatus":
                    "no_exact_unique_adjacent_parent_trunks",
                "reachableFromPrimeNode": False,
                "primeToActionNodePath": [],
                "incomingNodeIds": ["2"],
                "outgoingNodeIds": ["4"],
                "nativeMappingId":
                    gap_queue.DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            }

        scoped = {
            "key": "black_a",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKey": "dlg_parent_a",
            "storyOwnerMission": "e1m1",
            "confidence": "native_derived_exact_parent_shell",
            "evidenceTier": "derived_exact_shell",
            "scopeCompleteness": "partial",
            "allParentStoryKeys": ["dlg_parent_a", "dlg_parent_b"],
            "unscopedParentStoryKeys": ["dlg_parent_b"],
            "nativeMappingId":
                gap_queue.DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "occurrenceCount": 1,
            "dialogTreeNarrativeActions": [
                occurrence("dlg_parent_a", "AAA")
            ],
        }
        unresolved = {
            "key": "black_a",
            "relation": "dialog_tree_narrative_action_unscoped",
            "parentStoryKey": "dlg_parent_b",
            "storyOwnerMission": "e1m1",
            "confidence": "native_exact_containment_unscoped",
            "allParentStoryKeys": ["dlg_parent_a", "dlg_parent_b"],
            "nativeMappingId":
                gap_queue.DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "occurrenceCount": 1,
            "dialogTreeNarrativeActions": [
                occurrence("dlg_parent_b", "BBB")
            ],
        }
        payload = mission_payload(connections=[scoped])
        payload["flow"]["unresolvedDialogTreeNarrativeActions"] = [
            unresolved
        ]

        row = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_dialog_tree_black_carrier_context_no_file_order",
        )
        self.assertEqual(
            closure["parentStoryKeys"],
            ["dlg_parent_a", "dlg_parent_b"],
        )
        self.assertEqual(row["exactBlackCarrierValidationFailures"], [])

        payload["flow"].pop("unresolvedDialogTreeNarrativeActions")
        failed = gap_queue.build_gap_row(
            partial,
            payload,
            mission_bundle_exists=True,
        )
        self.assertEqual(
            failed["actionableCoreIsolatedSceneKeys"],
            ["black_a"],
        )
        self.assertEqual(
            failed["exactBlackCarrierValidationFailures"][0]["gate"],
            "dialog_tree_exact_carrier_coverage",
        )

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
                "targetMissionStateChecks": [
                    {
                        "transition": "rise",
                        "id": "e6m1d5",
                        "isQuest": False,
                        "targetMissionId": "e6m1d5",
                        "detailState": 2,
                        "comparison": "equal",
                    },
                    {
                        "transition": "down",
                        "id": "e6m1d5",
                        "isQuest": False,
                        "targetMissionId": "e6m1d5",
                        "detailState": 2,
                        "comparison": "not_equal",
                    },
                ],
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
        self.assertEqual(
            report["exactRuntimeConfigValidation"]["status"],
            "validated",
        )

    def test_airwall_predicate_validator_reports_unknown_comparison(self) -> None:
        facts, failure = gap_queue._exact_typed_mission_state_transition_checks(
            "radio_fixture_1",
            "fixture_m1",
            [
                {
                    "transition": "rise",
                    "id": "fixture_m1",
                    "isQuest": False,
                    "targetMissionId": "fixture_m1",
                    "detailState": 2,
                    "comparison": "greater",
                },
                {
                    "transition": "down",
                    "id": "fixture_m1",
                    "isQuest": False,
                    "targetMissionId": "fixture_m1",
                    "detailState": 2,
                    "comparison": "equal",
                },
            ],
        )

        self.assertIsNone(facts)
        self.assertEqual(failure["validator"], "exactAirWallMissionStateRadioContext")
        self.assertEqual(
            failure["gate"],
            "typedMissionStateTransitionPredicates",
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
            (
                "closed_exact_cross_mission_leveldata_playback_context_"
                "no_relative_order"
            ),
        )
        self.assertEqual(
            closure["levelScriptOccurrences"][0]["nativeEventOwners"][0][
                "headerName"
            ],
            "LevelEvent_OnBattleSignal",
        )
        self.assertEqual(closure["contextMissionId"], "e9m3")
        self.assertIn("LevelData/dung02_dg003/e9m3.json", closure["sourceFiles"])

        invalid = dict(connection)
        invalid["confidence"] = "derived"
        self.assertFalse(
            gap_queue._exact_leveldata_story_context(
                invalid,
                "e2m7",
                "e9m3",
            )
        )

    def test_exact_same_mission_leveldata_alias_playback_closes_gap(
        self,
    ) -> None:
        story_key = "misc_dlg_testm1_1d5"
        authored_key = "dlg_testm1_1d5"
        source_file = "LevelScriptData/level_a/1001.json"
        level_data_file = "LevelData/level_a/testm1.json"
        occurrence = {
            "levelId": "level_a",
            "scriptId": "1001",
            "sourceFile": source_file,
            "actionMapRole": "actionList#1 root",
            "actionCode": "0x049e",
            "actionKind": "0x0f",
            "localId": 5,
            "actionName": "StartDialogAction",
            "recordClass": "play_dialog",
            "nativeMappingId": "gameassembly-test-actionbase",
            "allStoryKeysInRecord": [authored_key],
            "authoredStoryKey": authored_key,
            "nativeEventOwnerStatus": "exact_serialized_control_path",
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "headerLocalId": 4,
                "eventDetail": {
                    "summary": "leader enters trigger slot 80001",
                },
                "path": [{
                    "localId": 5,
                    "actionName": "StartDialogAction",
                    "recordClass": "play_dialog",
                    "texts": [authored_key],
                }],
            }],
            "levelDataHosts": [{
                "missionId": "testm1",
                "levelId": "level_a",
                "scriptId": "1001",
                "levelDataFile": level_data_file,
                "encoding": "leveldata_member22_levelscriptbriefdata",
                "nativeSchema": (
                    "LevelData/43.member22:"
                    "Dictionary<u64,LevelScriptBriefData/8>"
                ),
                "briefData": [{"scriptId": "1001"}],
            }],
            "scopeEvidenceKinds": [
                "mission_leveldata_member22_contains_validated_"
                "levelscript_brief",
            ],
        }
        connection = {
            "key": story_key,
            "relation": "leveldata_levelscript_mission_context",
            "direction": "context",
            "phase": "context",
            "confidence": "native_exact_host",
            "storyOwnerMission": "testm1",
            "levelDataHostMissionId": "testm1",
            "questTriggerStatus": "unresolved",
            "occurrenceCount": 1,
            "allOccurrenceCount": 1,
            "hasUnscopedOrOtherMissionOccurrences": False,
            "nativeActions": ["StartDialogAction"],
            "opcodes": ["0x049e/0x0f"],
            "levelIds": ["level_a"],
            "scriptIds": ["1001"],
            "sourceFiles": [source_file],
            "levelDataFiles": [level_data_file],
            "levelScriptOccurrences": [occurrence],
        }

        closures = gap_queue._closed_exact_native_context_isolated_scenes(
            {"missionStoryConnections": [connection]},
            {story_key},
            "testm1",
        )

        self.assertEqual(len(closures), 1)
        self.assertEqual(
            closures[0]["recoveryStatus"],
            (
                "closed_exact_same_mission_leveldata_playback_context_"
                "no_relative_order"
            ),
        )
        self.assertIs(closures[0]["contextMissionMismatch"], False)
        self.assertEqual(
            closures[0]["sourceFiles"],
            [level_data_file, source_file],
        )

        occurrence["authoredStoryKey"] = "dlg_different_1"
        self.assertEqual(
            gap_queue._closed_exact_native_context_isolated_scenes(
                {"missionStoryConnections": [connection]},
                {story_key},
                "testm1",
            ),
            [],
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
