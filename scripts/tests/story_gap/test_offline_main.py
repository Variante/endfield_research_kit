from ._support import (
    Path,
    SourceGapTestCase,
    current_npc_proxy_consumer_contexts,
    gap_queue,
    json,
    mission_payload,
    partial_mission,
    patch,
    tempfile,
)

class SourceGapMainMissionContractTests(SourceGapTestCase):
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

    def test_generic_family_recoveries_fail_closed_on_stronger_routes(self) -> None:
        for evidence_kind in (
            "radio_definition_binary_consumer_surface_exhausted",
            "missionless_npc_proxy_dialog_native_consumer",
            "sns_definition_binary_consumer_surface_exhausted",
        ):
            with self.subTest(evidence_kind=evidence_kind):
                story_key = f"fixture_{evidence_kind}"
                evidence = {
                    "sceneKey": story_key,
                    "missionId": "fixture_mission",
                    "recoveryStatus":
                        "deferred_current_build_offline_surface_exhausted",
                    "evidenceKind": evidence_kind,
                    "graphEffect": "none",
                }
                args = (
                    {"missionStoryConnections": [], "quests": []},
                    {story_key},
                    "fixture_mission",
                    {story_key: evidence},
                )

                rows = gap_queue._deferred_offline_exhausted_isolated_scenes(
                    *args
                )
                self.assertEqual(
                    [row["sceneKey"] for row in rows],
                    [story_key],
                )
                self.assertEqual(
                    gap_queue._deferred_offline_exhausted_isolated_scenes(
                        *args,
                        native_playback_index={
                            story_key: [{"method": "Play"}]
                        },
                    ),
                    [],
                )
                self.assertEqual(
                    gap_queue._deferred_offline_exhausted_isolated_scenes(
                        *args,
                        cross_owner_story_connections=[{"key": story_key}],
                    ),
                    [],
                )

    def test_declared_offline_case_keeps_its_specific_route_contract(self) -> None:
        story_key = "radio_fixture"
        evidence = {
            "sceneKey": story_key,
            "missionId": "fixture_mission",
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": "radio_definition_without_recovered_consumer",
            "graphEffect": "none",
        }

        rows = gap_queue._deferred_offline_exhausted_isolated_scenes(
            {"missionStoryConnections": [], "quests": []},
            {story_key},
            "fixture_mission",
            {story_key: evidence},
            native_playback_index={story_key: [{"method": "fixture"}]},
            cross_owner_story_connections=[{"key": story_key}],
        )

        self.assertEqual([row["sceneKey"] for row in rows], [story_key])

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
                current_npc_proxy_consumer_contexts(story_key)[0]["proxyId"],
                proxy_id,
            )
            self.assertEqual(
                current_npc_proxy_consumer_contexts(story_key)[0]["entryIndex"],
                entry_index,
            )
            self.assertEqual(
                current_npc_proxy_consumer_contexts(story_key)[0]["entry"]["missionId"],
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
            current_npc_proxy_consumer_contexts("dlg_e1m1_6")[0]["proxyId"],
            "chen_map01_e1m1Basement1",
        )
        self.assertEqual(
            current_npc_proxy_consumer_contexts("dlg_e1m1_6")[0]["entry"]["missionId"],
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
            current_npc_proxy_consumer_contexts("dlg_e9m4_14")[0],
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
            current_npc_proxy_consumer_contexts("dlg_e3m2_3")[0]["proxyId"],
            "angelu_map01_e3m201",
        )
        self.assertNotIn(
            "missionId",
            current_npc_proxy_consumer_contexts("dlg_e3m2_3")[0]["entry"],
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
                "radio_gm02m21_4": {
                    "au_radio_gm02m21_4_001",
                    "au_radio_gm02m21_4_002",
                },
                "radio_gm02m21_7": {"au_radio_gm02m21_7_001"},
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
            current_npc_proxy_consumer_contexts("dlg_e8m1_10")[0],
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
            consumer = current_npc_proxy_consumer_contexts(story_key)[0]
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
        audit_report = "reports/mission_order/lua_consumer_reference_audit.json"
        lua_source_path = "scratch/story/lua/PhaseGenderChange.lua"
        lua_sha256 = "a" * 64
        audit_sha256 = "b" * 64
        manifest = {
            "cutscene_e1m10_1": {
                "attachmentStatus": "trigger_known_owner_unresolved",
                "key": "cutscene_e1m10_1",
                "nominalMissionId": "e1m10",
                "routes": [{
                    "causality": "playback_owner_unresolved",
                    "confidence": (
                        "corpus_scanned_shipped_lua_literal_plus_native_entry"
                    ),
                    "direction": "playback",
                    "evidenceTier": "direct",
                    "luaCall": "GameAction.PlayCutscene",
                    "luaFile": lua_file,
                    "luaLine": 104,
                    "luaSourcePath": lua_source_path,
                    "luaSourceSha256": lua_sha256,
                    "luaSymbol": "CUT_SCENE_ID",
                    "auditReport": audit_report,
                    "auditSha256": audit_sha256,
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
                    "sourceFiles": [lua_file, audit_report],
                    "steps": [
                        {
                            "id": lua_file,
                            "kind": "luaController",
                            "phase": "gender_change",
                            "summaries": [
                                "line 104",
                                f"SHA-256 {lua_sha256}",
                            ],
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
        self.assertEqual(rows[0]["luaSourceSha256"], lua_sha256)
        self.assertEqual(rows[0]["auditReport"], audit_report)
        self.assertEqual(rows[0]["graphEffect"], "none")
        failures: list[dict] = []
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
                failures,
            ),
            [],
        )
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["gate"], "route_contract")
        self.assertEqual(failures[0]["storyKey"], "cutscene_e1m10_1")

    def test_story_trigger_manifest_loader_validates_schema_and_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coverage.json"
            payload = {
                "schemaVersion": gap_queue.STORY_BINDING_COVERAGE_SCHEMA_VERSION,
                "language": "CN",
                "storyTriggerManifest": {"cutscene_test_1": {"key": "cutscene_test_1"}},
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            manifest, status = gap_queue.load_story_trigger_manifest_evidence(
                path,
                "CN",
            )
            self.assertEqual(set(manifest), {"cutscene_test_1"})
            self.assertEqual(status["status"], "validated")
            self.assertEqual(status["rowCount"], 1)
            self.assertEqual(status["validationFailures"], [])

            payload["schemaVersion"] -= 1
            path.write_text(json.dumps(payload), encoding="utf-8")
            manifest, status = gap_queue.load_story_trigger_manifest_evidence(
                path,
                "CN",
            )
            self.assertEqual(manifest, {})
            self.assertEqual(status["status"], "validation_failed")
            self.assertEqual(status["validationFailures"][0]["gate"], "schema_version")
            self.assertEqual(
                status["validationFailures"][0]["expected"],
                {"schemaVersion": gap_queue.STORY_BINDING_COVERAGE_SCHEMA_VERSION},
            )

    def test_exact_connected_context_closes_arbitrary_relation_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dialog_source = (
                "export_full/recovered/TextAsset/"
                "dlg_fixture_parent_p0123456789ABCDEF.json"
            )
            level_source = (
                "export_full/structured/LevelScriptData/"
                "map_fixture/4242.json"
            )
            for relative_path in (dialog_source, level_source):
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original game data", encoding="utf-8")

            manifest = {
                "dlg_fixture_multi_quest": {
                    "key": "dlg_fixture_multi_quest",
                    "nominalMissionId": "fixture",
                    "attachmentStatus": "connected",
                    "routes": [{
                        "storyKey": "dlg_fixture_multi_quest",
                        "missionId": "fixture",
                        "relation": "dialog_tree_reachable_story_playback",
                        "questTriggerStatus":
                            "exact_multi_quest_branch_dependency_not_unique_trigger",
                        "confidence":
                            "native_exact_cross_story_quest_state_context",
                    }],
                },
                "dlg_fixture_child": {
                    "key": "dlg_fixture_child",
                    "nominalMissionId": "fixture",
                    "attachmentStatus": "connected",
                    "routes": [{
                        "storyKey": "dlg_fixture_child",
                        "missionId": "fixture",
                        "questId": "fixture_q#3",
                        "scope": "quest",
                        "ownerStatus": "connected",
                        "relation": "dialog_tree_reachable_story_playback",
                        "direction": "context",
                        "phase": "dialog_tree_story_playback",
                        "causality": "dependency",
                        "confidence": "native_exact_parent_quest",
                        "evidenceTier": "native_direct",
                        "certainty": "authored_reachable",
                        "nativeMappingId":
                            "dialog-tree-reachable-story-playback-native-v1",
                        "parentStoryKey": "dlg_fixture_parent",
                        "questTriggerStatus":
                            "exact_parent_quest_context_not_independent_trigger",
                        "serverExchange": False,
                        "clientRequest": False,
                        "expectedClientReply": False,
                        "runtimeReplacementPossible": True,
                        "occurrenceCount": 1,
                        "carrierKinds": ["trunk"],
                        "parentScopeRelations": ["fixture_scope"],
                        "sourcePathIds": ["0123456789ABCDEF"],
                        "sourceFiles": [dialog_source],
                        "steps": [
                            {"kind": "quest", "id": "fixture_q#3",
                             "phase": "dialog_tree_story_playback"},
                            {"kind": "story", "id": "dlg_fixture_child"},
                        ],
                    }],
                },
                "radio_fixture_2": {
                    "key": "radio_fixture_2",
                    "nominalMissionId": "fixture",
                    "attachmentStatus": "connected",
                    "routes": [{
                        "storyKey": "radio_fixture_2",
                        "missionId": "fixture",
                        "questId": "fixture_q#9",
                        "scope": "quest",
                        "ownerStatus": "connected",
                        "relation": "levelscript_quest_state_gate",
                        "direction": "context",
                        "phase": "processing_gate",
                        "causality": "context",
                        "confidence": "native_typed_gate",
                        "nativeMappingId":
                            gap_queue.LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
                        "eventNames": ["ScriptEvent_OnLeaderEnterTriggerVolume"],
                        "levelId": "map_fixture",
                        "scriptIds": ["4242"],
                        "actionNames": ["PlayRadio"],
                        "conditionType": "CheckQuestState",
                        "conditionComparer": "Equal",
                        "conditionQuestState": 2,
                        "headerLocalId": 7,
                        "gateActionLocalId": 8,
                        "actionLocalId": 10,
                        "actionCode": "0x0363",
                        "actionKind": "0x0d",
                        "sourceFiles": [level_source],
                        "steps": [
                            {"kind": "quest", "id": "fixture_q#9",
                             "phase": "processing_gate"},
                            {"kind": "native_event"},
                            {"kind": "levelscript"},
                            {"kind": "native_action"},
                            {"kind": "story", "id": "radio_fixture_2"},
                        ],
                    }],
                },
            }
            failures: list[dict] = []
            with patch.object(gap_queue, "ROOT", root):
                rows = gap_queue._closed_exact_connected_context_isolated_scenes(
                    manifest,
                    {
                        "dlg_fixture_child",
                        "dlg_fixture_multi_quest",
                        "radio_fixture_2",
                    },
                    "fixture",
                    failures,
                )

        self.assertEqual(failures, [])
        self.assertEqual(
            {row["sceneKey"] for row in rows},
            {"dlg_fixture_child", "radio_fixture_2"},
        )
        self.assertTrue(all(row["graphEffect"] == "none" for row in rows))

    def test_exact_connected_context_fails_closed_with_bounded_diagnostic(self) -> None:
        manifest = {
            "radio_fixture_2": {
                "key": "radio_fixture_2",
                "nominalMissionId": "fixture",
                "attachmentStatus": "connected",
                "routes": [{
                    "storyKey": "radio_fixture_2",
                    "missionId": "fixture",
                    "questId": "fixture_q#9",
                    "scope": "quest",
                    "ownerStatus": "connected",
                    "relation": "levelscript_quest_state_gate",
                    "direction": "context",
                    "phase": "processing_gate",
                    "causality": "context",
                    "confidence": "native_typed_gate",
                    "conditionQuestState": 3,
                    "sourceFiles": ["missing/original.json"],
                    "steps": [],
                }],
            },
        }
        failures: list[dict] = []
        rows = gap_queue._closed_exact_connected_context_isolated_scenes(
            manifest,
            {"radio_fixture_2"},
            "fixture",
            failures,
        )

        self.assertEqual(rows, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["validator"], "exact_connected_story_context_v1")
        self.assertEqual(
            failures[0]["gate"],
            "levelscript_quest_state_gate_contract",
        )
        self.assertEqual(failures[0]["storyKey"], "radio_fixture_2")
        self.assertEqual(failures[0]["actual"]["existingSourceFileCount"], 0)

    def test_exact_composed_root_playback_closes_arbitrary_isolated_cutscene(
        self,
    ) -> None:
        story_key = "cutscene_testm2_target"
        root_key = "cutscene_testm2_root"
        mission_source = (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/testm2.json"
        )
        level_source = (
            "export_full/structured/StreamingAssets/Data/Json/"
            "LevelScriptData/test_level/123.json"
        )
        alias_source = "VFS/ABCD/alias.chk"
        audit_report = (
            "reports/story/recovery/"
            "animestudio_story_reverse_pptr_audit.json"
        )
        route = {
            "aliasRelation": "cutscene_root_director_playable_asset",
            "auditReport": audit_report,
            "causality": "playback_alias_owner_connected",
            "confidence": (
                "exact_connected_root_playback_plus_serialized_director_alias"
            ),
            "direction": "context",
            "evidenceTier": "native_serialized_composed_exact",
            "missionId": "testm2",
            "nativeMappingId": "gameassembly-test-cutscene-root-playback-v1",
            "nativePaths": [{
                "sourceFile": mission_source,
                "steps": [{"actionName": "PlayCutsceneAction"}],
            }],
            "ownerStatus": "connected",
            "questId": None,
            "questTriggerStatus": (
                "connected_root_native_playback_composed_with_exact_alias"
            ),
            "relation": "cutscene_root_playback_alias_composed",
            "rootBaseCausality": "context",
            "rootBaseRelation": "mission_event_native_playback_context",
            "rootStoryKey": root_key,
            "scope": "mission",
            "serverExchange": False,
            "sourceFiles": [
                mission_source,
                level_source,
                alias_source,
                audit_report,
            ],
            "steps": [
                {"id": "testm2", "kind": "mission"},
                {"ids": ["event"], "kind": "native_event"},
                {"ids": ["123"], "kind": "levelscript"},
                {"ids": ["PlayCutsceneAction"], "kind": "native_action"},
                {"id": root_key, "kind": "story_root"},
                {
                    "id": "CutsceneRoot._director -> TimelineHandle.Play",
                    "kind": "native_action",
                },
                {"id": story_key, "kind": "story"},
            ],
            "storyKey": story_key,
        }
        alias_route = {
            "auditReport": audit_report,
            "causality": "playback_alias_owner_unresolved",
            "confidence": "exact_serialized_root_director_plus_native_playback",
            "direction": "playback",
            "evidenceTier": "direct",
            "missionId": None,
            "nativeMappingId": route["nativeMappingId"],
            "ownerStatus": "unresolved",
            "questId": None,
            "questTriggerStatus": "no_mission_or_quest_selector_recovered",
            "relation": "cutscene_root_playback_alias",
            "rootStoryKey": root_key,
            "scope": "cutscene_root",
            "serverExchange": False,
            "sourceFiles": [alias_source, audit_report],
            "steps": route["steps"][-3:],
            "storyKey": story_key,
        }
        manifest = {
            story_key: {
                "attachmentStatus": "connected",
                "key": story_key,
                "nominalMissionId": "testm2",
                "routes": [alias_route, route],
            },
        }
        partial = partial_mission(
            "testm2",
            scenes=[story_key],
            isolated=[story_key],
        )

        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            story_trigger_manifest=manifest,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closure = row["closedExactNativeIsolatedScenes"][0]
        self.assertEqual(closure["sceneKey"], story_key)
        self.assertEqual(closure["rootStoryKeys"], [root_key])
        self.assertEqual(closure["sourceFiles"], sorted(
            route["sourceFiles"],
            key=gap_queue.natural_key,
        ))
        self.assertEqual(closure["graphEffect"], "none")

    def test_composed_root_playback_closure_fails_closed_on_route_drift(
        self,
    ) -> None:
        story_key = "cutscene_testm2_target"
        root_key = "cutscene_testm2_root"
        audit_report = "reports/story/recovery/alias_audit.json"
        mission_source = "MissionRuntimeAsset/testm2.json"
        route = {
            "aliasRelation": "cutscene_root_director_playable_asset",
            "auditReport": audit_report,
            "causality": "playback_alias_owner_connected",
            "confidence": (
                "exact_connected_root_playback_plus_serialized_director_alias"
            ),
            "direction": "context",
            "evidenceTier": "native_serialized_composed_exact",
            "missionId": "testm2",
            "nativeMappingId": "native-map-v1",
            "nativePaths": [{
                "sourceFile": mission_source,
                "steps": [{"actionName": "PlayCutsceneAction"}],
            }],
            "ownerStatus": "connected",
            "questId": None,
            "questTriggerStatus": (
                "connected_root_native_playback_composed_with_exact_alias"
            ),
            "relation": "cutscene_root_playback_alias_composed",
            "rootBaseCausality": "context",
            "rootBaseRelation": "mission_event_native_playback_context",
            "rootStoryKey": root_key,
            "scope": "mission",
            "serverExchange": False,
            "sourceFiles": [mission_source, "VFS/alias.chk", audit_report],
            "steps": [
                {"id": "testm2", "kind": "mission"},
                {"ids": ["PlayCutsceneAction"], "kind": "native_action"},
                {"id": root_key, "kind": "story_root"},
                {
                    "id": "CutsceneRoot._director -> TimelineHandle.Play",
                    "kind": "native_action",
                },
                {"id": story_key, "kind": "story"},
            ],
            "storyKey": story_key,
        }
        alias_route = {
            "auditReport": audit_report,
            "causality": "playback_alias_owner_unresolved",
            "confidence": "exact_serialized_root_director_plus_native_playback",
            "direction": "playback",
            "evidenceTier": "direct",
            "missionId": None,
            "nativeMappingId": route["nativeMappingId"],
            "ownerStatus": "unresolved",
            "questId": None,
            "questTriggerStatus": "no_mission_or_quest_selector_recovered",
            "relation": "cutscene_root_playback_alias",
            "rootStoryKey": root_key,
            "scope": "cutscene_root",
            "serverExchange": False,
            "sourceFiles": ["VFS/alias.chk", audit_report],
            "steps": route["steps"][-3:],
            "storyKey": story_key,
        }

        mutations = {
            "wrong mission": {"missionId": "otherm1"},
            "unresolved owner": {"ownerStatus": "unresolved"},
            "weak tier": {"evidenceTier": "direct"},
            "missing audit": {"auditReport": ""},
            "wrong alias action": {
                "steps": [
                    *route["steps"][:-2],
                    {"id": "TimelineHandle.Stop", "kind": "native_action"},
                    route["steps"][-1],
                ],
            },
            "missing native source": {
                "sourceFiles": ["VFS/alias.chk", audit_report],
            },
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                failures: list[dict] = []
                candidate = {**route, **mutation}
                manifest = {
                    story_key: {
                        "attachmentStatus": "connected",
                        "key": story_key,
                        "nominalMissionId": "testm2",
                        "routes": [alias_route, candidate],
                    },
                }
                self.assertEqual(
                    gap_queue
                    ._closed_exact_composed_root_playback_isolated_scenes(
                        manifest,
                        {story_key},
                        "testm2",
                        failures,
                    ),
                    [],
                )
                self.assertEqual(len(failures), 1)
                self.assertEqual(failures[0]["gate"], "route_contract")
                self.assertEqual(failures[0]["storyKey"], story_key)
        missing_alias_failures: list[dict] = []
        self.assertEqual(
            gap_queue._closed_exact_composed_root_playback_isolated_scenes(
                {
                    story_key: {
                        "attachmentStatus": "connected",
                        "key": story_key,
                        "nominalMissionId": "testm2",
                        "routes": [route],
                    },
                },
                {story_key},
                "testm2",
                missing_alias_failures,
            ),
            [],
        )
        self.assertEqual(len(missing_alias_failures), 1)
        self.assertEqual(
            missing_alias_failures[0]["actual"]["aliasRouteCount"],
            0,
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
            consumer = current_npc_proxy_consumer_contexts(story_key)[0]
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
            current_npc_proxy_consumer_contexts("dlg_e1m2_6")[0]["proxyId"],
            "chen_map01_e1m2Factory",
        )
        self.assertEqual(
            current_npc_proxy_consumer_contexts("dlg_e1m2_6")[0]["entry"]["missionId"],
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
            current_npc_proxy_consumer_contexts("dlg_e5m2_2")[0]["entryIndex"],
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
        misc_consumer = current_npc_proxy_consumer_contexts(
            "misc_dlg_e5m2_3d5"
        )[0]
        self.assertEqual(misc_consumer["entryIndex"], 1)
        self.assertNotIn("missionId", misc_consumer["entry"])

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
        consumer = current_npc_proxy_consumer_contexts("dlg_e5m1_3")[0]
        self.assertEqual(consumer["entryIndex"], 1)
        self.assertEqual(
            consumer["proxyId"],
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
            current_npc_proxy_consumer_contexts("dlg_e2m5_6")[0],
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
