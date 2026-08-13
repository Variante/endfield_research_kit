from ._support import *

class SourceGapDefinitionTests(SourceGapTestCase):
    def test_exact_typed_selector_closes_isolated_alternatives(self) -> None:
        partial = partial_mission(
            "m1", scenes=["dlg_a", "dlg_b"], isolated=["dlg_a", "dlg_b"]
        )
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(connections=[
                self.typed_selector_connection("dlg_a"),
                self.typed_selector_connection("dlg_b"),
            ]),
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        self.assertEqual(
            row["metrics"]["closedExactSystemSelectorIsolatedScenes"], 2
        )
        self.assertEqual(row["exactSystemSelectorValidationFailures"], [])

    def test_partial_typed_selector_fails_closed_with_diagnostics(self) -> None:
        connection = self.typed_selector_connection("dlg_a")
        connection["selectorAlternatives"] = [
            {"role": "first", "key": "dlg_a"}
        ]
        row = gap_queue.build_gap_row(
            partial_mission("m1", scenes=["dlg_a"], isolated=["dlg_a"]),
            mission_payload(connections=[connection]),
            mission_bundle_exists=True,
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 1)
        failure = row["exactSystemSelectorValidationFailures"][0]
        self.assertEqual(failure["validator"], "exact_typed_story_selector")
        self.assertIn("distinctKeys", failure["failedChecks"])
        self.assertEqual(failure["expected"]["minimumDistinctAlternatives"], 2)

    def test_present_literal_keys_preserves_overlapping_prefixes(self) -> None:
        payload = b"before radio_fixture_10 after"
        present = gap_queue._present_literal_keys(
            payload,
            {
                "short": "radio_fixture_1",
                "long": "radio_fixture_10",
                "absent": "radio_fixture_11",
            },
            "utf-8",
        )

        self.assertEqual(present, {"short", "long"})

    def test_generic_radio_definition_validator_recovers_shape(self) -> None:
        story_key = "radio_fixture"
        line = {
            field: ""
            for field in gap_queue.OFFLINE_EXHAUSTION_RADIO_LINE_FIELDS
        }
        line.update({
            "id": f"{story_key}_1",
            "index": 1,
            "audioOverride": "au_radio_fixture_001",
        })
        row = {
            "continueAfterDialog": False,
            "continueAfterRadio": False,
            "priority": 3,
            "radioSingleDataList": [line],
            "radioType": 0,
        }

        facts, failure = gap_queue._generic_radio_definition_facts(
            story_key,
            row,
            {"au_radio_fixture_001_variant"},
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["lineIds"], ["radio_fixture_1"])
        self.assertEqual(facts["lineIndices"], [1])
        self.assertEqual(
            facts["audioMembershipStatus"],
            "all_current_audio_dialog_ids_present",
        )

    def test_generic_radio_definition_validator_reports_line_shape(self) -> None:
        story_key = "radio_fixture"
        line = {
            field: ""
            for field in gap_queue.OFFLINE_EXHAUSTION_RADIO_LINE_FIELDS
        }
        line.update({
            "id": "wrong_owner_1",
            "index": 0,
            "audioOverride": "",
        })
        row = {
            "continueAfterDialog": False,
            "continueAfterRadio": False,
            "priority": 3,
            "radioSingleDataList": [line],
            "radioType": 0,
        }

        facts, failure = gap_queue._generic_radio_definition_facts(
            story_key,
            row,
            set(),
        )

        self.assertIsNone(facts)
        self.assertEqual(failure["validator"], "genericRadioNegativeConsumer")
        self.assertEqual(failure["gate"], "exactRadioLineShape")
        self.assertEqual(failure["storyKey"], story_key)
        self.assertEqual(failure["actual"]["lineId"], "wrong_owner_1")

    def test_generic_reading_popup_validator_recovers_definition(self) -> None:
        story_key = "text_fixture_1"
        facts, failure = gap_queue._generic_reading_popup_definition_facts(
            story_key,
            {
                "rp_text_fixture_1": {
                    "bgType": 2,
                    "contentId": story_key,
                    "iconType": 0,
                    "id": "rp_text_fixture_1",
                    "overrideRadioId": "",
                    "title": {"id": 0, "text": ""},
                },
            },
            {
                "contentList": [
                    {"content": {"id": 42, "text": ""}},
                    {"content": {"id": -7, "text": ""}},
                ],
                "title": {"id": 11, "text": ""},
            },
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["readingPopupRowIds"], ["rp_text_fixture_1"])
        self.assertEqual(facts["richContentTitleId"], 11)
        self.assertEqual(facts["contentTextIds"], [42, -7])

    def test_generic_reading_popup_validator_reports_rich_shape(self) -> None:
        story_key = "text_fixture_1"
        facts, failure = gap_queue._generic_reading_popup_definition_facts(
            story_key,
            {
                story_key: {
                    "bgType": 0,
                    "contentId": story_key,
                    "iconType": 0,
                    "id": story_key,
                    "overrideRadioId": "",
                    "title": {"id": 0, "text": ""},
                },
            },
            {
                "contentList": [{"content": {"id": True, "text": ""}}],
                "title": {"id": 11, "text": ""},
            },
        )

        self.assertIsNone(facts)
        self.assertEqual(
            failure["validator"],
            "genericReadingPopupNegativeConsumer",
        )
        self.assertEqual(failure["gate"], "exactRichContentDefinitionShape")
        self.assertEqual(failure["storyKey"], story_key)

    def test_generic_unregistered_dialog_uses_exact_root_boundary(self) -> None:
        story_key = "dlg_fixture_1"
        line = {
            field: ""
            for field in gap_queue.OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
        }
        line["audioOverride"] = "au_dlg_fixture_1_001"
        other_line = dict(line, audioOverride="au_dlg_fixture_10_001")
        facts, failure = (
            gap_queue._generic_unregistered_dialog_definition_facts(
                story_key,
                {
                    "dlg_fixture_1_001": line,
                    "dlg_fixture_10_001": other_line,
                },
                {
                    "option_dlg_fixture_1_2_001": {
                        "iconType": "Default",
                        "optionText": {"id": 42, "text": ""},
                    },
                    "option_dlg_fixture_10_1_001": {
                        "iconType": "Default",
                        "optionText": {"id": 99, "text": ""},
                    },
                },
                {"au_dlg_fixture_1_001"},
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["lineIds"], ["dlg_fixture_1_001"])
        self.assertEqual(
            facts["optionIds"],
            ["option_dlg_fixture_1_2_001"],
        )
        self.assertEqual(facts["optionsByGroup"], {"2": [
            "option_dlg_fixture_1_2_001",
        ]})

    def test_generic_unregistered_dialog_accepts_authored_suffix_widths(
        self,
    ) -> None:
        story_key = "dlg_fixture_short"
        line = {
            field: ""
            for field in gap_queue.OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
        }
        line["audioOverride"] = "0"
        facts, failure = (
            gap_queue._generic_unregistered_dialog_definition_facts(
                story_key,
                {
                    "dlg_fixture_short_01": line,
                    "dlg_fixture_short_002": line,
                    "dlg_fixture_short_nested_01": line,
                },
                {
                    "option_dlg_fixture_short_a_01": {
                        "iconType": "Default",
                        "optionText": {"id": 42, "text": ""},
                    },
                },
                set(),
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["lineIds"], [
            "dlg_fixture_short_01",
            "dlg_fixture_short_002",
        ])
        self.assertEqual(facts["optionIds"], [
            "option_dlg_fixture_short_a_01",
        ])

    def test_generic_unregistered_dialog_resolves_misc_alias_generically(self) -> None:
        story_key = "misc_dlg_fixture_0d5"
        definition_root = "dlg_fixture_0d5"
        line = {
            field: ""
            for field in gap_queue.OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
        }
        line["audioOverride"] = "au_dlg_fixture_0d5_001"
        facts, failure = (
            gap_queue._generic_unregistered_dialog_definition_facts(
                story_key,
                {"dlg_fixture_0d5_001": line},
                {
                    "option_dlg_fixture_0d5_0d5_001": {
                        "iconType": "Default",
                        "optionText": {"id": 42, "text": ""},
                    },
                },
                {"au_dlg_fixture_0d5_001"},
                definition_root_key=definition_root,
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(definition_root, facts["definitionRootKey"])
        self.assertEqual(
            ["option_dlg_fixture_0d5_0d5_001"],
            facts["optionIds"],
        )
        self.assertEqual(
            {"0d5": ["option_dlg_fixture_0d5_0d5_001"]},
            facts["optionsByGroup"],
        )

    def test_generic_registered_table_dialog_resolves_mechanical_alias(self) -> None:
        story_key = "misc_dlg_fixture_1d5"
        definition_root = "dlg_fixture_1d5"
        line = {
            field: ""
            for field in gap_queue.OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
        }
        line["audioOverride"] = "au_dlg_fixture_1d5_001"
        facts, failure = (
            gap_queue._generic_registered_table_dialog_definition_facts(
                story_key,
                definition_root,
                {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                },
                {"dlg_fixture_1d5_001": line},
                {},
                {"au_dlg_fixture_1d5_001"},
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["emittedStoryKey"], story_key)
        self.assertEqual(facts["definitionRootKey"], definition_root)
        self.assertEqual(facts["lineIds"], ["dlg_fixture_1d5_001"])

    def test_generic_registered_table_dialog_fails_closed_on_alias_drift(self) -> None:
        facts, failure = (
            gap_queue._generic_registered_table_dialog_definition_facts(
                "misc_dlg_fixture_1d5",
                "dlg_wrong_root",
                {},
                {},
                {},
                set(),
            )
        )

        self.assertIsNone(facts)
        self.assertEqual(
            failure["validator"],
            "genericRegisteredTableDialogNegativeConsumer",
        )
        self.assertEqual(
            failure["gate"],
            "mechanicalEmittedToAuthoredDialogAlias",
        )

    def test_generic_text_table_only_cutscene_validates_exact_root(self) -> None:
        story_key = "cutscene_fixture_1"
        facts, failure = (
            gap_queue._generic_text_table_only_cutscene_definition_facts(
                story_key,
                {
                    "cutscene_fixture_1_02": {"id": 12, "text": "two"},
                    "cutscene_fixture_1_03": {"id": 13, "text": "three"},
                    "cutscene_fixture_10_01": {"id": 99, "text": "other"},
                },
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(
            facts["definitionRowKeys"],
            ["cutscene_fixture_1_02", "cutscene_fixture_1_03"],
        )
        self.assertEqual(facts["localizedTextIds"], [12, 13])

    def test_generic_text_table_only_cutscene_reports_invalid_row(self) -> None:
        facts, failure = (
            gap_queue._generic_text_table_only_cutscene_definition_facts(
                "cutscene_fixture_1",
                {"cutscene_fixture_1_01": {"id": True, "text": "bad"}},
            )
        )

        self.assertIsNone(facts)
        self.assertEqual(
            failure["validator"],
            "genericTextTableOnlyCutsceneNegativeConsumer",
        )
        self.assertEqual(failure["gate"], "exactLocalizedTextRowShape")

    def test_generic_missionless_native_playback_validates_exact_path(
        self,
    ) -> None:
        story_key = "radio_fixture_1"
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            source_file = source_root / "LevelScriptData/lv1/1001.json"
            source_file.parent.mkdir(parents=True)
            source_file.write_text("{}", encoding="utf-8")
            occurrences = [{
                "levelId": "lv1",
                "scriptId": "1001",
                "sourceFile": "LevelScriptData/lv1/1001.json",
                "actionMapRole": "actionList#1 linked",
                "allStoryKeysInRecord": [story_key],
                "localId": 6,
                "actionName": "PlayRadio",
                "recordClass": "play_radio",
                "nativeMappingId": "gameassembly-fixture-actionbase-v1",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "headerLocalId": 4,
                    "eventDetail": {
                        "type": "ScriptEvent_OnLeaderEnterTriggerVolume",
                        "serializedMissionOrQuestId": False,
                        "serverExchange": False,
                        "summary": "leader enters trigger slot 80001",
                    },
                    "path": [{
                        "localId": 6,
                        "actionName": "PlayRadio",
                        "recordClass": "play_radio",
                    }],
                }],
            }]

            facts, failure, exclusion = (
                gap_queue._generic_missionless_native_playback_facts(
                    story_key,
                    occurrences,
                    source_root=source_root,
                )
            )

        self.assertIsNone(failure)
        self.assertIsNone(exclusion)
        self.assertEqual(facts["nativeEventPaths"][0]["actionLocalId"], 6)
        self.assertTrue(facts["sourceSha256"][occurrences[0]["sourceFile"]])

    def test_generic_missionless_native_playback_fails_closed_on_terminal(
        self,
    ) -> None:
        story_key = "dlg_fixture_1"
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            source_file = source_root / "LevelScriptData/lv1/1001.json"
            source_file.parent.mkdir(parents=True)
            source_file.write_text("{}", encoding="utf-8")
            facts, failure, exclusion = (
                gap_queue._generic_missionless_native_playback_facts(
                    story_key,
                    [{
                        "sourceFile": "LevelScriptData/lv1/1001.json",
                        "actionMapRole": "actionList#2 root",
                        "allStoryKeysInRecord": [story_key],
                        "localId": 2,
                        "actionName": "StartDialogAction",
                        "recordClass": "play_dialog",
                        "nativeMappingId": "gameassembly-fixture-actionbase-v1",
                        "nativeEventOwners": [{
                            "status": "exact_serialized_control_path",
                            "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                            "headerLocalId": 0,
                            "eventDetail": {
                                "serializedMissionOrQuestId": False,
                                "serverExchange": False,
                            },
                            "path": [{
                                "localId": 3,
                                "actionName": "StartDialogAction",
                                "recordClass": "play_dialog",
                            }],
                        }],
                    }],
                    source_root=source_root,
                )
            )

        self.assertIsNone(facts)
        self.assertIsNone(exclusion)
        self.assertEqual(
            failure["validator"],
            "genericMissionlessNativePlayback",
        )
        self.assertEqual(
            failure["gate"],
            "exactMissionlessNativeControlPath",
        )
        self.assertEqual(failure["expected"]["terminalLocalId"], 2)
        self.assertEqual(failure["actual"]["terminal"]["localId"], 3)

    def test_generic_unregistered_dialog_reports_option_shape(self) -> None:
        story_key = "dlg_fixture_1"
        line = {
            field: ""
            for field in gap_queue.OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
        }
        line["audioOverride"] = "au_dlg_fixture_1_001"
        facts, failure = (
            gap_queue._generic_unregistered_dialog_definition_facts(
                story_key,
                {"dlg_fixture_1_001": line},
                {
                    "option_dlg_fixture_1_1_001": {
                        "iconType": "",
                        "optionText": {"id": True, "text": ""},
                    },
                },
                set(),
            )
        )

        self.assertIsNone(facts)
        self.assertEqual(
            failure["validator"],
            "genericUnregisteredDialogNegativeConsumer",
        )
        self.assertEqual(failure["gate"], "exactDialogOptionShape")
        self.assertEqual(failure["storyKey"], story_key)

    def test_generic_registered_dialog_tree_validates_exact_definition(self) -> None:
        story_key = "dlg_c27m4_15"
        definition = recover_dialog_tree_definition_evidence(story_key)
        facts, failure = (
            gap_queue._generic_registered_dialog_tree_definition_facts(
                story_key,
                {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                },
                definition,
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["sceneKey"], story_key)
        self.assertEqual(facts["assetType"], "Beyond.Gameplay.DialogTree")
        self.assertEqual(facts["nodeCount"], 2)
        self.assertTrue(facts["sourceSha256"])
        self.assertEqual(
            facts["optionRouteRecovery"]["schemaVersion"],
            "dialogTreeNormalOptionRoutes.v1",
        )
        self.assertEqual(
            facts["optionRouteRecoveryStatus"],
            "exact_validated_routes",
        )

    def test_generic_registered_dialog_tree_reports_source_hash_failure(self) -> None:
        story_key = "dlg_c27m4_15"
        definition = recover_dialog_tree_definition_evidence(story_key)
        invalid = {**definition, "sourceSha256": "0" * 64}
        facts, failure = (
            gap_queue._generic_registered_dialog_tree_definition_facts(
                story_key,
                {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                },
                invalid,
            )
        )

        self.assertIsNone(facts)
        self.assertEqual(
            failure["validator"],
            "genericRegisteredDialogTreeNegativeConsumer",
        )
        self.assertEqual(failure["gate"], "exactCurrentDialogTreeDefinition")
        self.assertFalse(failure["actual"]["sourceHashMatches"])

    def test_generic_registered_dialog_tree_reports_route_schema_failure(
        self,
    ) -> None:
        story_key = "dlg_c27m4_15"
        definition = recover_dialog_tree_definition_evidence(story_key)
        invalid = copy.deepcopy(definition)
        invalid["optionRouteRecovery"]["schemaVersion"] = "unknown"
        facts, failure = (
            gap_queue._generic_registered_dialog_tree_definition_facts(
                story_key,
                {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                },
                invalid,
            )
        )

        self.assertIsNone(facts)
        self.assertEqual(failure["gate"], "exactCurrentDialogTreeDefinition")
        self.assertTrue(failure["expected"]["validatedOptionRouteRecovery"])
        self.assertEqual(
            failure["actual"]["optionRouteRecovery"]["schemaVersion"],
            "unknown",
        )

    def test_plain_dialog_definitions_do_not_require_per_object_declarations(
        self,
    ) -> None:
        definitions = {
            "dlg_arbitrary_future_1": {
                "missionId": "future_mission",
                "filename": "must_not_drive_discovery.json",
                "sha256": "must_not_drive_discovery",
                "lineIds": ("must_not_drive_discovery_001",),
                "optionIds": (),
            },
            "dlg_external_context": {
                "missionId": "mission_context",
                "filename": "context.json",
                "sha256": "context-hash",
                "lineIds": ("dlg_external_context_001",),
                "optionIds": (),
                "npcProxyConsumer": {"proxyId": "proxy_fixture"},
            },
            "dlg_task_context": {
                "missionId": "mission_task",
                "filename": "task.json",
                "sha256": "task-hash",
                "lineIds": ("dlg_task_context_001",),
                "optionIds": (),
            },
            "dlg_leveldata_context": {
                "missionId": "mission_leveldata",
                "filename": "leveldata.json",
                "sha256": "leveldata-hash",
                "lineIds": ("dlg_leveldata_context_001",),
                "optionIds": (),
            },
        }
        with (
            patch.object(
                gap_queue,
                "OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS",
                definitions,
            ),
            patch.object(
                gap_queue,
                "OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS",
                {"dlg_task_context": {}},
            ),
            patch.object(
                gap_queue,
                "OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS",
                {
                    "mission_leveldata": {
                        "propertyDialogs": {
                            "result_dialog": "dlg_leveldata_context",
                        },
                    },
                },
            ),
        ):
            contextual = gap_queue._declared_dialog_context_definitions()

        self.assertEqual(
            set(contextual),
            {
                "dlg_task_context",
                "dlg_leveldata_context",
            },
        )
        self.assertNotIn("dlg_arbitrary_future_1", contextual)
        self.assertNotIn("dlg_external_context", contextual)

    def test_carrier_audit_source_diagnostics_name_missing_index(self) -> None:
        report = {
            "sources": [
                {
                    "source": source,
                    "stageSignatureSha256": f"{source}-signature",
                }
                for source in ("StreamingAssets", "Persistent")
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persistent = (
                root
                / "export_full/recovered/AnimeStudio-cli/Persistent/"
                  "object_index"
            )
            persistent.mkdir(parents=True)
            (persistent / "summary.json").write_text(
                json.dumps({
                    "complete": True,
                    "stageSignature": {
                        "sha256": "Persistent-signature",
                    },
                }),
                encoding="utf-8",
            )
            with patch.object(gap_queue, "ROOT", root):
                failures = gap_queue._audit_source_index_diagnostics(report)

        self.assertEqual(len(failures), 1)
        failure = failures[0]
        self.assertEqual(failure["validator"], "offlineAnimeStudioCarrierAudit")
        self.assertEqual(failure["gate"], "exactCurrentPublishedObjectIndex")
        self.assertEqual(failure["source"], "StreamingAssets")
        self.assertFalse(failure["actual"]["exists"])
        self.assertTrue(failure["expected"]["exists"])

    def test_generic_dialog_timeline_is_internal_definition_only(self) -> None:
        timeline_rows = gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/timeline_line_orders.json",
            {},
        )
        facts, failure = gap_queue._generic_dialog_timeline_definition_facts(
            "dlg_c6m1_27",
            timeline_rows["dlg_c6m1_27"],
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["timeline"], "dlgtl_c6m1_27_sub_1")
        self.assertFalse(facts["activationEvidence"])
        self.assertFalse(facts["crossFileOrderEvidence"])
        self.assertTrue(facts["sourceRoots"])

    def test_generic_dialog_timeline_reports_missing_source_root(self) -> None:
        timeline_rows = gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/timeline_line_orders.json",
            {},
        )
        invalid = {
            **timeline_rows["dlg_c6m1_27"],
            "sourceRoots": ["export_full/recovered/missing-dialog-timeline.json"],
        }
        facts, failure = gap_queue._generic_dialog_timeline_definition_facts(
            "dlg_c6m1_27",
            invalid,
        )

        self.assertIsNone(facts)
        self.assertEqual(failure["gate"], "exactInternalDialogTimelineDefinition")
        self.assertEqual(failure["actual"]["existingSourceRoots"], 0)

    def test_generic_missionless_npc_proxy_consumer_recovers_identity(self) -> None:
        story_key = "dlg_fixture_1"
        row = {
            "addDialogExOption": False,
            "dialogExOptionData": [],
            "dialogId": story_key,
            "envTalkData": {"envTalkOverrideNpc": True},
            "missionId": "",
        }
        facts, failure = (
            gap_queue._generic_missionless_npc_proxy_dialog_facts(
                story_key,
                {
                    "data": {"proxy_fixture": [row]},
                    "proxyInfoData": {"proxy_fixture": {
                        "npcProxyType": 0,
                        "npcId": "npc_fixture",
                        "npcNameId": "npc_name_fixture",
                        "mapId": "map_fixture",
                    }},
                },
                {"dataTable": {"proxy_fixture": {
                    "proxyId": "proxy_fixture",
                    "levelId": "level_fixture",
                    "subDataParentId": 42,
                }}},
                {story_key: {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                }},
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["consumerCount"], 1)
        self.assertEqual(
            facts["npcProxyConsumers"][0]["npcProxyId"],
            "proxy_fixture",
        )
        self.assertEqual(
            facts["dialogIdRegistrationStatus"],
            "memorypack_root_registered",
        )
        self.assertEqual(facts["definitionRootKey"], story_key)

    def test_generic_missionless_npc_proxy_consumer_resolves_alias_and_all_rows(
        self,
    ) -> None:
        story_key = "misc_dlg_fixture_future_3d5"
        definition_root = "dlg_fixture_future_3d5"
        missionless_row = {
            "addDialogExOption": False,
            "dialogExOptionData": [],
            "dialogId": definition_root,
            "envTalkData": {"envTalkOverrideNpc": True},
            "missionId": "",
        }
        mission_row = {**missionless_row, "missionId": "fixture_mission"}
        proxy_ids = ("proxy_future_a", "proxy_future_b")
        facts, failure = (
            gap_queue._generic_missionless_npc_proxy_dialog_facts(
                story_key,
                {
                    "data": {
                        proxy_ids[0]: [mission_row, missionless_row],
                        proxy_ids[1]: [missionless_row],
                    },
                    "proxyInfoData": {
                        proxy_id: {
                            "npcProxyType": 0,
                            "npcId": f"npc_{proxy_id}",
                            "npcNameId": f"name_{proxy_id}",
                            "mapId": "map_fixture",
                        }
                        for proxy_id in proxy_ids
                    },
                },
                {"dataTable": {
                    proxy_id: {
                        "proxyId": proxy_id,
                        "levelId": "level_fixture",
                        "subDataParentId": None,
                    }
                    for proxy_id in proxy_ids
                }},
                {definition_root: {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                }},
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(facts["emittedStoryKey"], story_key)
        self.assertEqual(facts["definitionRootKey"], definition_root)
        self.assertEqual(
            [
                (row["npcProxyId"], row["activeRowIndex"])
                for row in facts["npcProxyConsumers"]
            ],
            [(proxy_ids[0], 1), (proxy_ids[1], 0)],
        )

    def test_generic_missionless_npc_proxy_consumer_reports_identity_gap(
        self,
    ) -> None:
        story_key = "dlg_fixture_future_9"
        row = {
            "addDialogExOption": False,
            "dialogExOptionData": [],
            "dialogId": story_key,
            "envTalkData": {"envTalkOverrideNpc": True},
            "missionId": "",
        }
        facts, failure = (
            gap_queue._generic_missionless_npc_proxy_dialog_facts(
                story_key,
                {
                    "data": {"proxy_future": [row]},
                    "proxyInfoData": {},
                },
                {"dataTable": {}},
                {story_key: {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                }},
            )
        )

        self.assertIsNone(facts)
        self.assertEqual(failure["gate"], "exactNpcProxyConsumerIdentity")
        self.assertEqual(failure["storyKey"], story_key)
        self.assertEqual(failure["npcProxyId"], "proxy_future")
        self.assertIn("expected", failure)
        self.assertIn("actual", failure)

    def test_dialog_context_declarations_do_not_copy_npc_proxy_rows(self) -> None:
        for story_key, definition in (
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.items()
        ):
            with self.subTest(story_key=story_key):
                self.assertNotIn("npcProxyConsumer", definition)
                self.assertNotIn("npcProxyConsumers", definition)

    def test_current_dialog_npc_proxy_consumers_follow_the_general_pattern(
        self,
    ) -> None:
        npc_proxy_ex = gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/structured/Persistent/Data/Json/GameplayConfig/"
            "NpcProxyExDataTable.json",
            {},
        )
        npc_proxy = gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Data/Json/GameplayConfig/"
            "NpcProxyTable.json",
            {},
        )
        dialog_id_index = gap_queue.read_json(
            gap_queue.ROOT / "export_full/recovered/dialog_id_table_index.json",
            {},
        )
        ex_data = npc_proxy_ex.get("data") or {}
        qualified = 0
        alias_qualified = 0
        multiple_consumer_qualified = 0
        for story_key in gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS:
            definition_root = story_key.removeprefix("misc_")
            expected_rows = [
                (proxy_id, row_index)
                for proxy_id, rows in ex_data.items()
                if isinstance(rows, list)
                for row_index, row in enumerate(rows)
                if (
                    isinstance(row, dict)
                    and row.get("dialogId") == definition_root
                    and not row.get("missionId")
                )
            ]
            facts, failure = (
                gap_queue._generic_missionless_npc_proxy_dialog_facts(
                    story_key,
                    npc_proxy_ex,
                    npc_proxy,
                    dialog_id_index,
                )
            )
            if not expected_rows:
                self.assertIsNone(facts)
                self.assertIsNone(failure)
                continue
            self.assertNotEqual((facts is None), (failure is None))
            if failure is not None:
                self.assertIn("expected", failure)
                self.assertIn("actual", failure)
                continue
            actual_rows = [
                (row["npcProxyId"], row["activeRowIndex"])
                for row in facts["npcProxyConsumers"]
            ]
            self.assertEqual(actual_rows, expected_rows)
            tree = recover_dialog_tree_definition_evidence(definition_root)
            tree_facts, tree_failure = (
                gap_queue._generic_registered_dialog_tree_definition_facts(
                    definition_root,
                    dialog_id_index.get(definition_root),
                    tree,
                )
            )
            self.assertIsNone(tree_failure)
            self.assertTrue(tree_facts["sourceFile"])
            self.assertIsInstance(tree_facts["lineIds"], list)
            self.assertGreater(tree_facts["nodeCount"], 0)
            qualified += 1
            alias_qualified += story_key.startswith("misc_dlg_")
            multiple_consumer_qualified += len(actual_rows) > 1

        self.assertGreater(qualified, 0)
        self.assertGreater(alias_qualified, 0)
        self.assertGreater(multiple_consumer_qualified, 0)

    def test_registered_dialog_tree_and_npc_proxy_evidence_compose_generically(
        self,
    ) -> None:
        story_key = "misc_dlg_fixture_future_3d5"
        definition_root = "dlg_fixture_future_3d5"
        tree = {
            "sceneKey": story_key,
            "missionId": "fixture_mission",
            "definitionRootKey": definition_root,
            "evidenceKind": (
                "registered_dialog_tree_definition_binary_consumer_surface_exhausted"
            ),
            "definitionSourceFiles": ["DialogTree.json"],
            "sourceFiles": ["dialog_id_table_index.json"],
            "originalBinaryFiles": ["global-metadata.dat"],
            "searchedConsumerKinds": ["DialogId registry"],
            "nativeMappingId": "definition-negative-consumer-v1",
            "dialogTreeBranchGroups": [{"optionGroup": 1}],
        }
        consumer = {
            "sceneKey": story_key,
            "missionId": "fixture_mission",
            "definitionRootKey": definition_root,
            "evidenceKind": "missionless_npc_proxy_dialog_native_consumer",
            "definitionSourceFiles": ["NpcProxyExDataTable.json"],
            "sourceFiles": ["carrier_audit.json"],
            "originalBinaryFiles": ["GameAssembly.dll"],
            "searchedConsumerKinds": ["NpcProxyEx selector"],
            "nativeMappingId": "npc-proxy-selector-v1",
            "npcProxyConsumers": [{
                "npcProxyId": "proxy_future",
                "activeRowIndex": 0,
            }],
        }

        composed, failure = (
            gap_queue._compose_registered_dialog_tree_npc_proxy_evidence(
                tree,
                consumer,
            )
        )

        self.assertIsNone(failure)
        self.assertEqual(composed["dialogTreeBranchGroups"], [{"optionGroup": 1}])
        self.assertEqual(
            composed["definitionSourceFiles"],
            ["DialogTree.json", "NpcProxyExDataTable.json"],
        )
        self.assertEqual(
            composed["originalBinaryFiles"],
            ["global-metadata.dat", "GameAssembly.dll"],
        )
        self.assertEqual(composed["nativeMappingId"], "npc-proxy-selector-v1")

        consumer["definitionRootKey"] = "dlg_different_root"
        composed, failure = (
            gap_queue._compose_registered_dialog_tree_npc_proxy_evidence(
                tree,
                consumer,
            )
        )
        self.assertIsNone(composed)
        self.assertEqual(failure["gate"], "exactDefinitionConsumerIdentity")

    def test_generic_missionless_npc_proxy_consumer_reports_row_shape(self) -> None:
        story_key = "dlg_fixture_1"
        facts, failure = (
            gap_queue._generic_missionless_npc_proxy_dialog_facts(
                story_key,
                {
                    "data": {"proxy_fixture": [{
                        "dialogId": story_key,
                        "missionId": "",
                    }]},
                    "proxyInfoData": {"proxy_fixture": {
                        "npcProxyType": 0,
                        "npcId": "npc_fixture",
                        "npcNameId": "npc_name_fixture",
                        "mapId": "map_fixture",
                    }},
                },
                {"dataTable": {"proxy_fixture": {
                    "proxyId": "proxy_fixture",
                    "levelId": "level_fixture",
                }}},
                {story_key: {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "hasRootKey": True,
                }},
            )
        )

        self.assertIsNone(facts)
        self.assertEqual(
            failure["validator"],
            "genericMissionlessNpcProxyDialogConsumer",
        )
        self.assertEqual(failure["gate"], "exactNpcProxyExConsumerRow")
        self.assertEqual(failure["npcProxyId"], "proxy_fixture")

    def test_generic_unlinked_sns_definition_recovers_internal_graph(self) -> None:
        story_key = "sns_fixture_1"
        content_fields = {
            "content": {"id": 1, "text": ""},
            "contentParam": [],
            "contentParams": "",
            "contentType": 1,
            "dialogOptionIds": [],
            "isEnd": False,
            "linkMissionId": "",
            "linkRewardId": "",
            "optionType": 0,
            "speaker": "speaker_fixture",
        }
        row = {
            "chatId": "chat_fixture",
            "dialogContentData": {
                "1": {
                    **content_fields,
                    "contentId": 1,
                    "preContentId": 0,
                    "nextContentId": -1,
                },
                "-1": {
                    **content_fields,
                    "content": {"id": 0, "text": ""},
                    "contentId": -1,
                    "preContentId": 1,
                    "nextContentId": 0,
                    "isEnd": True,
                },
            },
            "dialogId": story_key,
            "dialogType": 2,
            "noticeType": 0,
            "relatedMissionId": "",
            "skipToFirstOption": False,
            "topicId": "",
        }
        chat = {
            field: 0
            for field in gap_queue.SNS_CHAT_ROW_FIELDS
        }
        chat.update({
            "chatId": "chat_fixture",
            "name": {"id": 1, "text": ""},
        })

        facts, failure, exclusion = (
            gap_queue._generic_unlinked_sns_definition_facts(
                story_key,
                row,
                {},
                {"chat_fixture": chat},
            )
        )

        self.assertIsNone(failure)
        self.assertIsNone(exclusion)
        self.assertEqual(facts["contentIds"], [-1, 1])
        self.assertEqual(facts["authoredMissionLinkStatus"], "absent")

        # Candidate selection follows the exact authored row identity, so a
        # shipped fixture or future family does not need an sns_* filename.
        nonstandard_key = "fixture_visual_dialog"
        nonstandard_row = copy.deepcopy(row)
        nonstandard_row["dialogId"] = nonstandard_key
        self.assertTrue(
            gap_queue._is_authored_sns_definition_candidate(
                nonstandard_key,
                {nonstandard_key: nonstandard_row},
            )
        )
        self.assertFalse(
            gap_queue._is_authored_sns_definition_candidate(
                nonstandard_key,
                {nonstandard_key: row},
            )
        )

        linked = copy.deepcopy(row)
        linked["relatedMissionId"] = "mission_fixture"
        linked["dialogContentData"]["1"].update({
            "contentParam": ["mission_fixture"],
            "contentType": 12,
            "linkMissionId": "mission_fixture",
        })
        facts, failure, exclusion = (
            gap_queue._generic_unlinked_sns_definition_facts(
                story_key,
                linked,
                {},
                {"chat_fixture": chat},
            )
        )
        self.assertIsNone(failure)
        self.assertEqual(exclusion, "authoredMissionLink")
        self.assertEqual(facts["relatedMissionId"], "mission_fixture")
        self.assertEqual(facts["snsContentIds"], ["1"])
        self.assertEqual(
            facts["linkMissionIdsByContentId"],
            {"1": "mission_fixture"},
        )

        inconsistent = copy.deepcopy(row)
        inconsistent["relatedMissionId"] = "mission_fixture"
        facts, failure, exclusion = (
            gap_queue._generic_unlinked_sns_definition_facts(
                story_key,
                inconsistent,
                {},
                {"chat_fixture": chat},
            )
        )
        self.assertIsNone(facts)
        self.assertIsNone(exclusion)
        self.assertEqual(failure["gate"], "coherentAuthoredMissionLink")

    def test_generic_unlinked_sns_definition_reports_dangling_content(self) -> None:
        story_key = "sns_fixture_1"
        row = {
            field: ""
            for field in gap_queue.SNS_DIALOG_ROW_FIELDS
        }
        row.update({
            "chatId": "chat_fixture",
            "dialogId": story_key,
            "dialogType": 2,
            "noticeType": 0,
            "skipToFirstOption": False,
            "dialogContentData": {"-1": {
                "content": {"id": 0, "text": ""},
                "contentId": -1,
                "contentParam": [],
                "contentParams": "",
                "contentType": 1,
                "dialogOptionIds": [],
                "isEnd": True,
                "linkMissionId": "",
                "linkRewardId": "",
                "nextContentId": 0,
                "optionType": 0,
                "preContentId": 99,
                "speaker": "",
            }},
        })
        chat = {field: 0 for field in gap_queue.SNS_CHAT_ROW_FIELDS}
        chat.update({
            "chatId": "chat_fixture",
            "name": {"id": 1, "text": ""},
        })

        facts, failure, exclusion = (
            gap_queue._generic_unlinked_sns_definition_facts(
                story_key,
                row,
                {},
                {"chat_fixture": chat},
            )
        )

        self.assertIsNone(facts)
        self.assertIsNone(exclusion)
        self.assertEqual(failure["validator"], "genericSnsNegativeConsumer")
        self.assertEqual(failure["gate"], "closedContentGraphAndOptions")
        self.assertEqual(failure["actual"]["invalidContentReferences"], [99])

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
