from ._support import (
    Path,
    base64,
    copy,
    gap_queue,
    json,
    mission_payload,
    partial_mission,
    patch,
    tempfile,
    unittest,
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

    def test_project_authored_story_provenance_is_generic_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "scripts" / "producer.py"
            source.parent.mkdir(parents=True)
            source.write_text("# fixture\n", encoding="utf-8")
            conv_dir = root / "conv"
            conv_dir.mkdir()
            provenance = {
                "scope": "project_authored",
                "purpose": "fixture_notice",
                "producer": "fixture.producer",
                "sourceFile": "scripts/producer.py",
                "gameDataEvidence": False,
            }
            entry = {
                "k": "opaque_notice",
                "m": "ui_shell",
                "d": "black",
                "provenance": provenance,
            }
            (conv_dir / "opaque_notice.json").write_text(
                json.dumps({
                    "key": "opaque_notice",
                    "mission": "ui_shell",
                    "provenance": provenance,
                }),
                encoding="utf-8",
            )

            found, status = gap_queue.project_authored_story_content_keys(
                {"entries": [entry]},
                conv_dir,
                source_root=root,
            )
            self.assertEqual(status["status"], "validated")
            self.assertIn("opaque_notice", found)
            self.assertFalse(found["opaque_notice"].get("gameDataEvidence", False))

            broken = copy.deepcopy(entry)
            broken["provenance"]["sourceFile"] = "../outside.py"
            found, status = gap_queue.project_authored_story_content_keys(
                {"entries": [broken]},
                conv_dir,
                source_root=root,
            )
            self.assertEqual(found, {})
            self.assertEqual(status["status"], "validation_failed")
            self.assertEqual(
                status["validationFailures"][0]["gate"],
                "matchingGeneratedEntryAndExistingSource",
            )

    def test_project_authored_story_is_excluded_without_graph_evidence(self) -> None:
        story_key = "opaque_notice"
        partial = partial_mission(
            "ui_shell",
            scenes=[story_key],
            isolated=[story_key],
        )
        partial["nodes"][0]["kind"] = "black"
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            non_mission_content={story_key: {
                "evidenceKind": "project_authored_story_content",
                "content": "fixture_notice",
                "storyKind": "black",
                "sourceScope": "project_authored",
                "producer": "fixture.producer",
                "sourceFiles": ["scripts/producer.py"],
                "sourceSha256": {"scripts/producer.py": "abc"},
            }},
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closed = row["closedNonMissionContentIsolatedScenes"][0]
        self.assertEqual(
            closed["recoveryStatus"],
            "excluded_project_authored_story_content",
        )
        self.assertFalse(closed["gameDataEvidence"])
        self.assertEqual(closed["graphEffect"], "none")

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

    def test_exact_spaceship_runtime_content_is_closed_without_order(self) -> None:
        story_key = "misc_sim_work_aglina"
        partial = partial_mission(
            "work",
            scenes=[story_key],
            isolated=[story_key],
        )
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            non_mission_content={
                story_key: {
                    "evidenceKind": "spaceship_dialog_tree",
                    "content": "operator_spaceship_dialog_tree",
                    "lineIds": ["sim_work_aglina_01"],
                    "dialogTreeRoots": [
                        "dlg_npc_0013_aglina_spaceshippresent",
                    ],
                    "consumerClasses": [
                        "Beyond.Gameplay.SpaceshipOptionWorkData",
                    ],
                    "sourceFiles": ["tree.json", "DialogTextTable.json"],
                    "nativeMappingId": "spaceship-mapping-v1",
                    "orderBoundary": "no mission or Story order edge",
                    "evidenceReport": "report.json",
                },
            },
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closed = row["closedNonMissionContentIsolatedScenes"][0]
        self.assertEqual(
            closed["recoveryStatus"],
            "closed_exact_spaceship_runtime_non_mission_content",
        )
        self.assertEqual(
            closed["dialogTreeRoots"],
            ["dlg_npc_0013_aglina_spaceshippresent"],
        )
        self.assertEqual(closed["sourceFiles"], [
            "tree.json",
            "DialogTextTable.json",
        ])

    def test_spaceship_definition_gap_is_deferred_without_table_fallback(self) -> None:
        story_key = "misc_sim_gift_fixture_recvbye"
        partial = partial_mission(
            "gift",
            scenes=[story_key],
            isolated=[story_key],
        )
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            non_mission_content={
                story_key: {
                    "evidenceKind": (
                        "spaceship_dialog_definition_without_tree_carrier"
                    ),
                    "content": "operator_spaceship_dialog_definition",
                    "lineIds": ["sim_gift_fixture_recvbye_01"],
                    "dialogTreeRoots": [
                        "dlg_npc_9999_fixture_spaceshipgift",
                    ],
                    "consumerClasses": [
                        "Beyond.Gameplay.SpaceshipOptionGiftData",
                    ],
                    "dialogFamily": "gift",
                    "actorId": "fixture",
                    "carrierStatus": (
                        "absent_from_all_related_typed_dialog_trees"
                    ),
                    "consumerBoundary": "typed related tree carries no target",
                    "sourceFiles": ["tree.json", "DialogTextTable.json"],
                    "nativeMappingId": "spaceship-mapping-v1",
                    "orderBoundary": "no playback or Story order edge",
                    "evidenceReport": "report.json",
                },
            },
        )

        self.assertEqual(row["metrics"]["actionableCoreIsolatedScenes"], 0)
        closed = row["closedNonMissionContentIsolatedScenes"][0]
        self.assertEqual(
            closed["recoveryStatus"],
            (
                "deferred_current_build_spaceship_dialog_definition_"
                "without_tree_carrier"
            ),
        )
        self.assertEqual(
            closed["carrierStatus"],
            "absent_from_all_related_typed_dialog_trees",
        )

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

    def test_cross_owner_levelscript_quest_playback_is_identity_agnostic(
        self,
    ) -> None:
        connection = {
            "key": "opaque_story_key",
            "relation": "levelscript_quest_completed_action",
            "direction": "quest_to_story",
            "phase": "succeed",
            "confidence": "native_typed_direct",
            "event": "LevelEvent_OnQuestStateChanged",
            "questState": 3,
            "questStateName": "Completed",
            "levelId": "opaque_level",
            "scriptId": "42",
            "sourceFile": (
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelScriptData/opaque_level/42.json"
            ),
            "headerLocalId": 7,
            "actionLocalId": 11,
            "actionPathLocalIds": [8, 11, 12],
            "actionName": "OpaqueTypedPlaybackAction",
            "nativeMappingId": "gameassembly-current-actionbase",
        }
        with patch.object(Path, "is_file", return_value=True):
            valid, failure = (
                gap_queue._exact_cross_owner_levelscript_quest_playback(
                    connection,
                    "owner_alpha",
                    "runtime_beta",
                    "runtime_beta_q#opaque",
                )
            )
        self.assertTrue(valid)
        self.assertIsNone(failure)

        broken = {**connection, "questState": 2}
        with patch.object(Path, "is_file", return_value=False):
            valid, failure = (
                gap_queue._exact_cross_owner_levelscript_quest_playback(
                    broken,
                    "owner_alpha",
                    "runtime_beta",
                    "runtime_beta_q#opaque",
                )
            )
        self.assertFalse(valid)
        self.assertEqual(failure["validator"], (
            "crossOwnerLevelScriptQuestPlayback"
        ))
        self.assertEqual(failure["gate"], "exactTypedQuestStatePlaybackPath")
        self.assertEqual(failure["actual"]["questState"], 2)

    def test_registered_dialog_tree_trunk_group_is_identity_agnostic(
        self,
    ) -> None:
        story_key = "misc_opaque_group"
        table = {
            "opaque_group_001": {},
            "opaque_group_002": {},
            "opaque_group_003": {},
        }
        definitions = {
            "parent_alpha": {
                "sceneKey": "parent_alpha",
                "lineIds": ["opaque_group_001", "opaque_group_002"],
                "lineConnections": [{
                    "fromLineId": "opaque_group_001",
                    "toLineId": "opaque_group_002",
                }],
                "sourceFile": "alpha.json",
                "sourceSha256": "A",
                "branchingOptionGroupCount": 0,
            },
            "parent_beta": {
                "sceneKey": "parent_beta",
                "lineIds": ["opaque_group_003"],
                "lineConnections": [],
                "sourceFile": "beta.json",
                "sourceSha256": "B",
                "branchingOptionGroupCount": 1,
            },
        }
        registry = {
            "parent_alpha": {"registered": True},
            "parent_beta": {"registered": True},
        }

        def validate(parent_key, _registry_row, definition):
            return {**definition, "sceneKey": parent_key}, None

        with patch.object(
            gap_queue,
            "_generic_registered_dialog_tree_definition_facts",
            side_effect=validate,
        ):
            facts, failure, exclusion = (
                gap_queue._generic_registered_dialog_tree_trunk_group_facts(
                    story_key,
                    table,
                    registry,
                    definitions,
                )
            )

        self.assertIsNone(failure)
        self.assertIsNone(exclusion)
        self.assertEqual(facts["parentDialogTreeCount"], 2)
        self.assertEqual(facts["branchingParentDialogTreeCount"], 1)
        self.assertEqual(facts["exactLinePartition"], {
            "opaque_group_001": "parent_alpha",
            "opaque_group_002": "parent_alpha",
            "opaque_group_003": "parent_beta",
        })

        malformed = {**table, "opaque_group_004": []}
        facts, failure, exclusion = (
            gap_queue._generic_registered_dialog_tree_trunk_group_facts(
                story_key,
                malformed,
                registry,
                definitions,
            )
        )
        self.assertIsNone(facts)
        self.assertIsNone(exclusion)
        self.assertEqual(
            failure["validator"],
            "genericRegisteredDialogTreeTrunkGroup",
        )
        self.assertEqual(failure["gate"], "exactDialogTextRows")

    def test_registered_dialog_tree_trunk_group_uses_namespace_tiebreak(
        self,
    ) -> None:
        story_key = "misc_timeline_opaque_group"
        table = {
            "timeline_opaque_group_001": {},
            "timeline_opaque_group_002": {},
        }
        definitions = {
            "dlg_opaque_group_1": {
                "lineIds": list(table),
                "sourceFile": "owner.json",
                "sourceSha256": "A",
            },
            "dlg_quest_reuse_1": {
                "lineIds": list(table),
                "sourceFile": "reuse.json",
                "sourceSha256": "B",
            },
        }
        registry = {key: {"registered": True} for key in definitions}

        def validate(parent_key, _registry_row, definition):
            return {**definition, "sceneKey": parent_key}, None

        with patch.object(
            gap_queue,
            "_generic_registered_dialog_tree_definition_facts",
            side_effect=validate,
        ):
            facts, failure, exclusion = (
                gap_queue._generic_registered_dialog_tree_trunk_group_facts(
                    story_key,
                    table,
                    registry,
                    definitions,
                )
            )

        self.assertIsNone(failure)
        self.assertIsNone(exclusion)
        self.assertEqual(facts["parentDialogTreeCount"], 1)
        self.assertEqual(
            facts["parentSelectionMethod"],
            "exact_registered_line_partition_namespace_tiebreak",
        )
        self.assertEqual(set(facts["exactLinePartition"].values()), {
            "dlg_opaque_group_1"
        })

    def test_registered_dialog_tree_trunk_group_direct_scene_is_exact_numbered(
        self,
    ) -> None:
        story_key = "dlg_opaque_pipe_1"
        table = {
            "dlg_opaque_pipe_1_01": {},
            "dlg_opaque_pipe_1_02": {},
            "dlg_opaque_pipe_1_2_01": {},
            "dlg_opaque_pipe_1_suffix": {},
        }
        definitions = {
            "dlg_gpl_opaque_pipe_1_1": {
                "lineIds": [
                    "dlg_opaque_pipe_1_01",
                    "dlg_opaque_pipe_1_02",
                ],
                "sourceFile": "direct.json",
                "sourceSha256": "A",
            },
            "dlg_gpl_opaque_pipe_1_2": {
                "lineIds": ["dlg_opaque_pipe_1_2_01"],
                "sourceFile": "nested.json",
                "sourceSha256": "B",
            },
        }
        registry = {key: {"registered": True} for key in definitions}

        def validate(parent_key, _registry_row, definition):
            return {**definition, "sceneKey": parent_key}, None

        with patch.object(
            gap_queue,
            "_generic_registered_dialog_tree_definition_facts",
            side_effect=validate,
        ):
            facts, failure, exclusion = (
                gap_queue._generic_registered_dialog_tree_trunk_group_facts(
                    story_key,
                    table,
                    registry,
                    definitions,
                )
            )

        self.assertIsNone(failure)
        self.assertIsNone(exclusion)
        self.assertEqual(facts["emittedGroupKind"], (
            "direct_numbered_dialog_scene"
        ))
        self.assertEqual(facts["lineSelectionMethod"], (
            "exact_numbered_scene_rows"
        ))
        self.assertEqual(facts["lineIds"], [
            "dlg_opaque_pipe_1_01",
            "dlg_opaque_pipe_1_02",
        ])
        self.assertEqual(facts["parentDialogTreeCount"], 1)
        self.assertEqual(set(facts["exactLinePartition"].values()), {
            "dlg_gpl_opaque_pipe_1_1"
        })

    def test_registered_dialog_tree_trunk_group_direct_scene_retains_partial_partition(
        self,
    ) -> None:
        story_key = "dlg_opaque_mix_3"
        table = {
            "dlg_opaque_mix_3_01": {},
            "dlg_opaque_mix_3_02": {},
            "dlg_opaque_mix_3_03": {},
        }
        definitions = {
            "dlg_opaque_mix_3_1": {
                "lineIds": [
                    "dlg_opaque_mix_3_01",
                    "dlg_opaque_mix_3_02",
                ],
                "sourceFile": "incomplete.json",
                "sourceSha256": "A",
            },
        }
        registry = {"dlg_opaque_mix_3_1": {"registered": True}}

        def validate(parent_key, _registry_row, definition):
            return {**definition, "sceneKey": parent_key}, None

        with patch.object(
            gap_queue,
            "_generic_registered_dialog_tree_definition_facts",
            side_effect=validate,
        ):
            facts, failure, exclusion = (
                gap_queue._generic_registered_dialog_tree_trunk_group_facts(
                    story_key,
                    table,
                    registry,
                    definitions,
                )
            )

        self.assertIsNone(failure)
        self.assertEqual(facts["partitionStatus"], "partial")
        self.assertEqual(facts["coveredLineIds"], [
            "dlg_opaque_mix_3_01",
            "dlg_opaque_mix_3_02",
        ])
        self.assertEqual(facts["missingLineIds"], [
            "dlg_opaque_mix_3_03",
        ])
        self.assertEqual(facts["coveredLineCount"], 2)
        self.assertEqual(facts["missingLineCount"], 1)
        self.assertEqual(
            exclusion,
            "incompleteParentTreePartition",
        )

    def test_partial_dialog_rows_close_only_after_complete_consumer_absence(
        self,
    ) -> None:
        missing_id = "dlg_opaque_mix_3_03"
        facts = {
            "partitionStatus": "partial",
            "missingLineIds": [missing_id],
            "parentDialogTrees": [{"sceneKey": "dlg_opaque_mix_3_1"}],
            "parentLevelContexts": [{
                "levelId": "opaque_mix_3",
                "parentDialogTreeIds": ["dlg_opaque_mix_3_1"],
                "subGameRuntime": {
                    "runtimeType": (
                        "Beyond.Gameplay.Core.BlackBoxSubGameData, "
                        "Gameplay.Beyond"
                    ),
                    "bindScriptId": 42,
                    "taskTopology": {"status": "exact_complete_task_map"},
                    "parentDialogPlayback": [{
                        "parentDialogTreeId": "dlg_opaque_mix_3_1",
                    }],
                    "definitionOnlyParentDialogTreeIds": [],
                },
            }],
        }
        empty_level_census = {
            "literalIds": [missing_id, "dlg_other_batch_01"],
            "matchesByLiteral": {},
            "sourceFileCount": 1,
            "sourceSetSha256": "A",
        }
        empty_binary_census = {
            "literalIds": [missing_id, "dlg_other_batch_01"],
            "matchesByLiteral": {},
            "sourceFileCount": 2,
            "sourceSetSha256": "B",
        }
        closure, failure, exclusion = (
            gap_queue._generic_partial_dialog_row_consumer_exhaustion_facts(
                "dlg_opaque_mix_3",
                facts,
                {"dlg_opaque_mix_3_1": {
                    "lineIds": ["dlg_opaque_mix_3_01"],
                }},
                empty_level_census,
                empty_binary_census,
            )
        )
        self.assertIsNone(failure)
        self.assertIsNone(exclusion)
        self.assertEqual(
            closure["unmatchedRowStatus"],
            "definition_rows_without_current_consumer",
        )
        self.assertIn("not appended", closure["orderBoundary"])

        invalid_facts = copy.deepcopy(facts)
        invalid_facts["parentLevelContexts"][0]["subGameRuntime"][
            "taskTopology"
        ]["status"] = "partial"
        closure, failure, exclusion = (
            gap_queue._generic_partial_dialog_row_consumer_exhaustion_facts(
                "dlg_opaque_mix_3",
                invalid_facts,
                {},
                empty_level_census,
                empty_binary_census,
            )
        )
        self.assertIsNone(closure)
        self.assertIsNone(exclusion)
        self.assertEqual(
            failure["gate"],
            "exactTypedParentRuntimeCoverage",
        )

        incomplete_binary_census = {
            **empty_binary_census,
            "sourceFileCount": 1,
        }
        closure, failure, exclusion = (
            gap_queue._generic_partial_dialog_row_consumer_exhaustion_facts(
                "dlg_opaque_mix_3",
                facts,
                {"dlg_opaque_mix_3_1": {
                    "lineIds": ["dlg_opaque_mix_3_01"],
                }},
                empty_level_census,
                incomplete_binary_census,
            )
        )
        self.assertIsNone(closure)
        self.assertIsNone(exclusion)
        self.assertEqual(failure["gate"], "completeConsumerCorpusCensus")
        self.assertEqual(failure["actual"]["binarySourceFileCount"], 1)

    def test_partial_dialog_row_consumer_census_rejects_any_literal_hit(
        self,
    ) -> None:
        missing_id = "dlg_opaque_mix_3_03"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            absent = root / "absent.bin"
            present = root / "present.bin"
            absent.write_bytes(b"unrelated")
            present.write_bytes(b"prefix" + missing_id.encode("utf-8") + b"suffix")
            census = gap_queue._literal_absence_census(
                [missing_id],
                [absent, present],
            )
        self.assertEqual(census["sourceFileCount"], 2)
        self.assertEqual(
            list(census["matchesByLiteral"]),
            [missing_id],
        )
        self.assertTrue(census["sourceSetSha256"])

    def test_registered_parent_playback_alias_requires_exact_bound_source(
        self,
    ) -> None:
        scene_key = "dlg_opaque_mix_3"
        parent_key = "dlg_opaque_mix_3_1"
        source_file = "LevelScriptData/opaque_mix_3/42.json"
        evidence = {
            "evidenceKind": (
                "partial_registered_dialog_tree_rows_without_current_consumer"
            ),
            "parentLevelContexts": [{
                "subGameRuntime": {
                    "parentDialogPlayback": [{
                        "parentDialogTreeId": parent_key,
                        "sourceFile": source_file,
                    }],
                },
            }],
        }
        route = {
            "key": scene_key,
            "relation": "native_story_playback_unscoped",
            "confidence": "native_typed_direct_unscoped",
            "storyOwnerMission": "opaque_mix",
            "questTriggerStatus": "unresolved",
            "occurrences": [{
                "authoredStoryKey": parent_key,
                "sourceFile": source_file,
                "actionName": "StartDialogAction",
                "recordClass": "play_dialog",
            }],
        }
        self.assertTrue(
            gap_queue._registered_parent_playback_routes_match(
                scene_key,
                "opaque_mix",
                evidence,
                [route],
            )
        )
        wrong_source = copy.deepcopy(route)
        wrong_source["occurrences"][0]["sourceFile"] = "other.json"
        self.assertFalse(
            gap_queue._registered_parent_playback_routes_match(
                scene_key,
                "opaque_mix",
                evidence,
                [wrong_source],
            )
        )

    def test_parent_dialog_level_context_is_generic_and_binary_validated(
        self,
    ) -> None:
        level_id = "opaque_factory_7"
        encoded_level_id = level_id.encode("utf-8")
        framed_level_id = (
            len(encoded_level_id).to_bytes(4, "little", signed=True)
            + encoded_level_id
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "LevelConfig"
            level_data_root = root / "LevelData"
            text_asset_root = root / "TextAsset"
            config_root.mkdir()
            (level_data_root / level_id).mkdir(parents=True)
            text_asset_root.mkdir()
            (config_root / f"{level_id}.json").write_bytes(
                b"config" + framed_level_id
            )
            (level_data_root / level_id / f"{level_id}_lv_data.json").write_bytes(
                b"\x2bdata" + framed_level_id
            )
            map_payload = {
                "mapIdStr": level_id,
                "levelStrIds": [level_id],
                "artScenePaths": [f"Assets/Scenes/{level_id}.unity"],
            }
            (text_asset_root / f"{level_id}_pABC.json").write_text(
                json.dumps({
                    "m_Name": level_id,
                    "Name": level_id,
                    "m_Script": base64.b64encode(
                        json.dumps(map_payload).encode("utf-8")
                    ).decode("ascii"),
                }),
                encoding="utf-8",
            )
            contexts, failure = (
                gap_queue._generic_parent_dialog_level_context_facts(
                    [{"sceneKey": f"dlg_gpl_{level_id}_intro"}],
                    {level_id: {
                        "id": level_id,
                        "configPath": f"Data/Json/LevelConfig/{level_id}.json",
                        "domainName": "opaque_domain",
                    }},
                    {f"dung_{level_id}": {
                        "sceneId": level_id,
                        "domainId": "opaque_domain",
                        "sortId": 17,
                    }},
                    level_config_root=config_root,
                    level_data_root=level_data_root,
                    text_asset_root=text_asset_root,
                )
            )

            self.assertIsNone(failure)
            self.assertEqual(len(contexts), 1)
            self.assertEqual(contexts[0]["levelId"], level_id)
            self.assertEqual(contexts[0]["dungeonId"], f"dung_{level_id}")
            self.assertEqual(
                contexts[0]["relation"],
                "exact_parent_dialog_level_asset_shell",
            )
            self.assertFalse(contexts[0]["orderEvidence"])
            self.assertEqual(
                contexts[0]["mapTextAssets"][0]["sourcePathId"],
                "ABC",
            )

            (level_data_root / level_id / f"{level_id}_lv_data.json").write_bytes(
                b"\x2a" + framed_level_id
            )
            contexts, failure = (
                gap_queue._generic_parent_dialog_level_context_facts(
                    [{"sceneKey": f"dlg_{level_id}_intro"}],
                    {level_id: {
                        "id": level_id,
                        "configPath": f"Data/Json/LevelConfig/{level_id}.json",
                    }},
                    {f"dung_{level_id}": {"sceneId": level_id}},
                    level_config_root=config_root,
                    level_data_root=level_data_root,
                    text_asset_root=text_asset_root,
                )
            )

            self.assertEqual(contexts, [])
            self.assertEqual(failure["gate"], "exactParentDialogLevelContext")
            self.assertEqual(failure["actual"]["levelDataMemberCount"], 42)
            self.assertEqual(failure["expected"]["levelDataMemberCount"], 43)

    def test_dialog_text_partition_fragments_are_cross_reference_only(
        self,
    ) -> None:
        facts = gap_queue._dialog_text_partition_fragment_facts(
            [
                "opaque_01",
                "opaque_02",
                "opaque_03",
                "opaque_04",
                "opaque_05",
            ],
            ["opaque_02", "opaque_04"],
            ["opaque_01", "opaque_03", "opaque_05"],
        )

        self.assertEqual(
            [row["numericPosition"] for row in facts],
            [
                "before_covered_numeric_range",
                "inside_covered_numeric_range",
                "after_covered_numeric_range",
            ],
        )
        self.assertTrue(all(row["graphEffect"] == "none" for row in facts))
        self.assertTrue(all(row["orderEvidence"] is False for row in facts))
        self.assertEqual(facts[1]["nearestLowerCoveredLineId"], "opaque_02")
        self.assertEqual(facts[1]["nearestUpperCoveredLineId"], "opaque_04")

    def test_parent_level_context_resolves_generic_blackbox_subgame_runtime(
        self,
    ) -> None:
        level_id = "opaque_factory_8"
        dungeon_id = f"dung_{level_id}"
        parent_key = f"dlg_{level_id}_intro"
        bind_script_id = 81000000001
        framed_level_id = (
            len(level_id.encode("utf-8")).to_bytes(4, "little", signed=True)
            + level_id.encode("utf-8")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "LevelConfig"
            level_data_root = root / "LevelData"
            text_asset_root = root / "TextAsset"
            level_script_root = root / "LevelScriptData"
            config_root.mkdir()
            (level_data_root / level_id).mkdir(parents=True)
            text_asset_root.mkdir()
            (level_script_root / level_id).mkdir(parents=True)
            (config_root / f"{level_id}.json").write_bytes(
                b"config" + framed_level_id
            )
            (level_data_root / level_id / f"{level_id}_lv_data.json").write_bytes(
                b"\x2bdata" + framed_level_id
            )
            script_path = (
                level_script_root / level_id / f"{bind_script_id}.json"
            )
            script_path.write_bytes(b"exact current LevelScript payload")
            subgame_path = root / "SubGameInstanceDataTable.json"
            subgame_row = {
                "$type": (
                    "Beyond.Gameplay.Core.BlackBoxSubGameData, Gameplay.Beyond"
                ),
                "id": dungeon_id,
                "modeId": "blackbox",
                "subDataParentId": bind_script_id - 1,
                "bindScriptId": bind_script_id,
                "mainTasks": [{"taskId": "main_a"}],
                "extraTasks": [{"taskId": "extra_b"}],
                "failTasks": [{"taskId": "fail_c", "failInfo": "failed"}],
            }
            subgame_path.write_text(
                json.dumps({"dataTable": {dungeon_id: subgame_row}}),
                encoding="utf-8",
            )
            native_index = {parent_key: [{
                "levelId": level_id,
                "scriptId": bind_script_id,
                "actionName": "StartDialogAction",
                "localId": 7,
                "recordOffset": 123,
                "sourceFile": gap_queue._repo_source_path(script_path),
                "nativeMappingId": "gameassembly-current-test-mapping",
                "nativeEventOwnerStatus": "exact_serialized_control_path",
                "nativeEventOwners": [{
                    "headerName": "ScriptEvent_OnCustomEvent",
                    "status": "exact_serialized_control_path",
                }],
            }]}
            common = {
                "level_config_root": config_root,
                "level_data_root": level_data_root,
                "text_asset_root": text_asset_root,
                "subgame_table": {"dataTable": {dungeon_id: subgame_row}},
                "subgame_table_path": subgame_path,
                "level_script_root": level_script_root,
                "native_playback_index": native_index,
            }
            contexts, failure = gap_queue._generic_parent_dialog_level_context_facts(
                [{"sceneKey": parent_key}],
                {level_id: {
                    "id": level_id,
                    "configPath": f"Data/Json/LevelConfig/{level_id}.json",
                }},
                {dungeon_id: {"sceneId": level_id}},
                **common,
            )

            self.assertIsNone(failure)
            runtime = contexts[0]["subGameRuntime"]
            self.assertEqual(runtime["bindScriptId"], bind_script_id)
            self.assertEqual(runtime["mainTasks"], [{"taskId": "main_a"}])
            self.assertEqual(runtime["extraTasks"], [{"taskId": "extra_b"}])
            self.assertEqual(runtime["failTasks"][0]["taskId"], "fail_c")
            self.assertEqual(
                runtime["parentDialogPlayback"][0]["parentDialogTreeId"],
                parent_key,
            )
            self.assertFalse(runtime["orderEvidence"])

            drifted_index = {parent_key: [dict(
                native_index[parent_key][0],
                scriptId=bind_script_id + 1,
            )]}
            contexts, failure = gap_queue._generic_parent_dialog_level_context_facts(
                [{"sceneKey": parent_key}],
                {level_id: {
                    "id": level_id,
                    "configPath": f"Data/Json/LevelConfig/{level_id}.json",
                }},
                {dungeon_id: {"sceneId": level_id}},
                **dict(common, native_playback_index=drifted_index),
            )
            self.assertEqual(contexts, [])
            self.assertEqual(
                failure["gate"],
                "exactBlackBoxSubGameParentPlayback",
            )
            self.assertEqual(
                failure["actual"]["mismatchedParentOccurrences"]
                [parent_key][0]["scriptId"],
                bind_script_id + 1,
            )

    def test_cross_owner_dialog_tree_narrative_retains_exact_parent_scope(
        self,
    ) -> None:
        story_key = "opaque_nested_story"
        parent_key = "opaque_parent_dialog"
        parent_context = {
            "key": parent_key,
            "relation": "leveldata_levelscript_mission_context",
            "storyOwnerMission": "parent_owner",
        }
        connection = {
            "key": story_key,
            "storyOwnerMission": "owner_alpha",
            "parentStoryKey": parent_key,
            "relation": "dialog_tree_narrative_action",
            "direction": "context",
            "confidence": "native_derived_exact_parent_shell",
            "evidenceTier": "derived_exact_shell",
            "contextMissionId": "runtime_beta",
            "nativeMappingId": (
                gap_queue.DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
            ),
            "graphEffect": "none",
            "occurrenceCount": 1,
            "parentScopeRelations": [
                "leveldata_levelscript_mission_context"
            ],
            "parentScopeContexts": [parent_context],
            "dialogTreeNarrativeActions": [{
                "dialogKey": parent_key,
                "textId": f"{story_key}_001",
                "actionType": (
                    "Beyond.Gameplay.DialogNarrativeMaskActionData"
                ),
                "nativeMappingId": (
                    gap_queue.DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                ),
                "sourceFile": "opaque_tree.json",
                "sourcePathId": "opaque_path_id",
            }],
        }
        with patch.object(
            gap_queue,
            "_exact_leveldata_story_context",
            return_value=True,
        ) as parent_validator:
            valid, failure = (
                gap_queue._exact_cross_owner_dialog_tree_narrative_context(
                    connection,
                    "owner_alpha",
                    "runtime_beta",
                )
            )
            self.assertTrue(valid)
            self.assertIsNone(failure)
        parent_validator.assert_called_once_with(
            parent_context,
            "parent_owner",
            "runtime_beta",
        )
        broken = {**connection, "graphEffect": "strong"}
        with patch.object(
            gap_queue,
            "_exact_leveldata_story_context",
            return_value=True,
        ):
            valid, failure = (
                gap_queue._exact_cross_owner_dialog_tree_narrative_context(
                    broken,
                    "owner_alpha",
                    "runtime_beta",
                )
            )
        self.assertFalse(valid)
        self.assertEqual(
            failure["validator"],
            "crossOwnerDialogTreeNarrativeContext",
        )
        self.assertEqual(
            failure["gate"],
            "typedNarrativeActionWithExactParentPlaybackShell",
        )
        self.assertEqual(failure["actual"]["graphEffect"], "strong")
