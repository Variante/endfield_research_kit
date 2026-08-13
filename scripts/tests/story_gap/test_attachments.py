from ._support import (
    Path,
    SourceGapTestCase,
    copy,
    gap_queue,
    mission_payload,
    partial_mission,
)

class SourceGapAttachmentTests(SourceGapTestCase):
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

    def test_generic_server_placeholder_boundary_uses_typed_shape(self) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payload = gap_queue.load_mission_payload_with_variants(
            mission_dir,
            "c16m4",
        )

        row, failure = gap_queue._classify_server_placeholder_story_boundary(
            "c16m4",
            "c16m4d5_q#11",
            payload,
        )

        self.assertIsNone(failure)
        self.assertEqual(
            row["recoveryStatus"],
            "closed_server_placeholder_context_without_typed_story_consumer",
        )
        self.assertEqual(
            row["diagnosticRelations"],
            ["leveldata_quest_reference", "variant_runtime_attachment"],
        )
        self.assertIn(
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/c16m4d5.json",
            row["sourceHashes"],
        )

    def test_generic_server_placeholder_boundary_fails_closed(self) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payload = gap_queue.load_mission_payload_with_variants(
            mission_dir,
            "c16m4",
        )
        quest = next(
            row
            for row in gap_queue._flow(payload)["quests"]
            if row["id"] == "c16m4d5_q#11"
        )
        quest["storyConnections"][0]["relation"] = "untyped_guess"

        row, failure = gap_queue._classify_server_placeholder_story_boundary(
            "c16m4",
            "c16m4d5_q#11",
            payload,
        )

        self.assertIsNone(row)
        self.assertEqual(
            failure["validator"],
            "genericServerPlaceholderStoryBoundary",
        )
        self.assertEqual(failure["gate"], "context_only_story_relation")
        self.assertEqual(failure["questId"], "c16m4d5_q#11")
        self.assertEqual(
            failure["actual"]["relation"],
            "untyped_guess",
        )

    def test_generic_levelscript_condition_boundary_uses_typed_shape(self) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payload = gap_queue.load_mission_payload_with_variants(
            mission_dir,
            "sm1l1m6",
        )

        row, failure = (
            gap_queue._classify_levelscript_condition_story_boundary(
                "sm1l1m6",
                "sm1l1m6_q#19",
                payload,
                {},
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(
            row["recoveryStatus"],
            "closed_levelscript_condition_scope_without_typed_story_consumer",
        )
        self.assertEqual(row["conditionKey"], "blackscreen_end")
        self.assertEqual(row["diagnosticStoryKeys"], ["dlg_sm1l1m6_5"])

    def test_generic_levelscript_condition_boundary_fails_closed(self) -> None:
        mission_dir = (
            gap_queue.ROOT / "webui" / "data" / "lang" / "CN" / "mission"
        )
        payload = gap_queue.load_mission_payload_with_variants(
            mission_dir,
            "sm1l1m6",
        )
        quest = next(
            row
            for row in gap_queue._flow(payload)["quests"]
            if row["id"] == "sm1l1m6_q#19"
        )
        quest["storyConnections"][0]["scriptId"] = "different"

        row, failure = (
            gap_queue._classify_levelscript_condition_story_boundary(
                "sm1l1m6",
                "sm1l1m6_q#19",
                payload,
                {},
            )
        )

        self.assertIsNone(row)
        self.assertEqual(
            failure["validator"],
            "genericLevelScriptConditionStoryBoundary",
        )
        self.assertEqual(
            failure["gate"],
            "condition_connection_script_agreement",
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
        quest.setdefault("storyConnections", []).append({
            "key": "dlg_typed_fixture",
            "relation": "typed_property_route",
        })

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
        self.assertEqual(
            detail["expected"]["connectionRelations"],
            ["levelscript_condition_scope"],
        )
        self.assertEqual(
            detail["expected"]["connectionStoryKeys"],
            ["dlg_e2m8_1", "radio_e2m8_1d5"],
        )
        self.assertEqual(
            detail["actual"]["connectionRows"][-1],
            {
                "key": "dlg_typed_fixture",
                "relation": "typed_property_route",
            },
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
        failures = []
        self.assertNotIn(
            "dlg_a1m4_2",
            {
                row["sceneKey"]
                for row in gap_queue._closed_exact_runtime_config_isolated_scenes(
                    broken,
                    {"dlg_a1m4_2"},
                    "a1m4",
                    validation_failures=failures,
                )
            },
        )
        self.assertEqual(
            failures[0]["validator"],
            "genericPrimeReachableDialogDependency",
        )
        self.assertEqual(
            failures[0]["gate"],
            "exactNonOwningQuestDependencyEnvelope",
        )
        self.assertEqual(failures[0]["storyKey"], "dlg_a1m4_2")

    def test_uncataloged_prime_reachable_dialog_dependency_is_general(self) -> None:
        payload = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/f1m28.json",
            {},
        )
        failures = []
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            payload["flow"],
            {"dlg_f1m28_5"},
            "f1m28",
            validation_failures=failures,
        )
        closure = next(
            row for row in rows if row["sceneKey"] == "dlg_f1m28_5"
        )
        self.assertEqual(failures, [])
        self.assertEqual(closure["parentStoryKey"], "dlg_f1m28_1")
        self.assertEqual(closure["carrierKinds"], ["dialog"])
        self.assertEqual(closure["dialogIds"], ["dlg_f1m28_5"])
        self.assertEqual(closure["trunkIds"], [])
        self.assertEqual(len(closure["dialogTreePrimeStoryPlaybackCarriers"]), 1)
        self.assertIn(closure["sourceFiles"][0], closure["sourceSha256"])

    def test_registered_dialog_non_owning_contexts_are_general(self) -> None:
        cases = (
            ("sm2l2m1", "dlg_sm2l2m1_13"),
            ("sm2l7m1", "dlg_sm2l7m1_18"),
        )
        for mission_id, story_key in cases:
            with self.subTest(mission_id=mission_id, story_key=story_key):
                payload = gap_queue.read_json(
                    gap_queue.ROOT
                    / f"webui/data/lang/CN/mission/{mission_id}.json",
                    {},
                )
                failures = []
                rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
                    payload["flow"],
                    {story_key},
                    mission_id,
                    validation_failures=failures,
                )
                closure = next(
                    row for row in rows if row["sceneKey"] == story_key
                )
                self.assertEqual(failures, [])
                self.assertEqual(
                    closure["recoveryStatus"],
                    "closed_exact_non_owning_dialog_context_no_relative_order",
                )
                self.assertEqual(closure["graphEffect"], "none")
                self.assertTrue(closure["dialogTreeDefinition"]["lineIds"])
                self.assertEqual(
                    set(closure["sourceFiles"]),
                    set(closure["sourceSha256"]),
                )

    def test_registered_dialog_context_payload_fails_closed(self) -> None:
        payload = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/sm2l7m1.json",
            {},
        )
        broken = copy.deepcopy(payload["flow"])
        connection = next(
            row
            for row in gap_queue._flow_story_connections(broken)
            if row.get("key") == "dlg_sm2l7m1_18"
            and row.get("relation")
            == "npc_proxy_lazy_destroy_dialog_context"
        )
        connection["npcProxyTableRow"]["lazyDestroy"] = False
        failures = []
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            broken,
            {"dlg_sm2l7m1_18"},
            "sm2l7m1",
            validation_failures=failures,
        )
        self.assertNotIn("dlg_sm2l7m1_18", {row["sceneKey"] for row in rows})
        self.assertEqual(
            failures[0]["validator"],
            "genericRegisteredDialogNonOwningContext",
        )
        self.assertEqual(failures[0]["gate"], "exactTypedRelationPayload")
        self.assertEqual(failures[0]["storyKey"], "dlg_sm2l7m1_18")

    def test_npc_proxy_multi_mission_context_preserves_alternatives(self) -> None:
        nominal = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/sm2l3m2.json",
            {},
        )
        adjacent = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/sm2l3m3.json",
            {},
        )
        nominal_row = next(
            row
            for row in gap_queue._flow_story_connections(nominal["flow"])
            if row.get("key") == "dlg_sm2l3m2_7"
            and row.get("relation") == "npc_proxy_ex_mission_context"
        )
        adjacent_row = copy.deepcopy(next(
            row
            for row in gap_queue._flow_story_connections(adjacent["flow"])
            if row.get("key") == "dlg_sm2l3m2_7"
            and row.get("relation") == "npc_proxy_ex_mission_context"
        ))
        adjacent_row["contextMissionBundle"] = "sm2l3m3"
        rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            {"missionStoryConnections": [nominal_row, adjacent_row]},
            {"dlg_sm2l3m2_7"},
            "sm2l3m2",
        )
        closure = next(
            row for row in rows if row["sceneKey"] == "dlg_sm2l3m2_7"
        )
        self.assertEqual(
            closure["recoveryStatus"],
            "closed_exact_multi_mission_runtime_config_no_relative_order",
        )
        self.assertEqual(
            closure["contextMissionIds"],
            ["sm2l3m2", "sm2l3m3"],
        )
        self.assertIn("does not choose", closure["contextBoundary"])
        self.assertEqual(
            set(closure["sourceFiles"]),
            set(closure["sourceSha256"]),
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
