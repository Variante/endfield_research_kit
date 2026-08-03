import base64
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


from scripts import build_mission_pipeline_data as pipeline
from scripts.story_builder import level_bindings, mission_flow, source_links


def condition(kind, **values):
    return {"$type": f"Beyond.Gameplay.{kind}, Gameplay.Beyond", "uniqueId": f"id_{kind}", **values}


class MissionPipelineBuilderTests(unittest.TestCase):
    def test_offline_story_recovery_schema_tracks_source_queue(self):
        self.assertEqual(
            pipeline.SOURCE_STORY_GAP_QUEUE_SCHEMA,
            "sourceStoryGapQueue.v130",
        )

    def test_trigger_route_preserves_exact_connected_context_evidence(self):
        route = pipeline.build_story_trigger_route(
            {
                "key": "radio_arbitrary_2",
                "relation": "levelscript_quest_state_gate",
                "direction": "context",
                "phase": "processing_gate",
                "confidence": "native_typed_gate",
                "event": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "levelId": "map_fixture",
                "scriptId": "4242",
                "sourceFile": "LevelScriptData/map_fixture/4242.json",
                "nativeMappingId": "mapping-v1",
                "headerLocalId": 7,
                "gateActionLocalId": 8,
                "conditionType": "CheckQuestState",
                "conditionComparer": "Equal",
                "conditionQuestState": 2,
                "actionLocalId": 10,
                "actionCode": "0x0363",
                "actionKind": "0x0d",
                "actionName": "PlayRadio",
            },
            mission_id="arbitrary",
            quest_id="arbitrary_q#9",
            scope="quest",
        )

        self.assertEqual(
            route["sourceFiles"],
            ["LevelScriptData/map_fixture/4242.json"],
        )
        self.assertEqual(
            route["eventNames"],
            ["ScriptEvent_OnLeaderEnterTriggerVolume"],
        )
        self.assertEqual(route["nativeMappingId"], "mapping-v1")
        self.assertEqual(route["conditionQuestState"], 2)
        self.assertEqual(
            [step["kind"] for step in route["steps"]],
            ["quest", "native_event", "levelscript", "native_action", "story"],
        )

    def test_gap_queue_refresh_validates_current_generated_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue_path = Path(temporary) / "source_story_gap_queue_CN.json"
            queue_path.write_text(
                json.dumps({
                    "_schema": pipeline.SOURCE_STORY_GAP_QUEUE_SCHEMA,
                    "language": "CN",
                    "offlineExhaustionEvidence": {
                        "status": "active",
                        "validationFailures": [],
                        "sourceHashMismatches": [],
                    },
                    "crossOwnerValidation": {
                        "status": "validated",
                        "validationFailures": [],
                    },
                }),
                encoding="utf-8",
            )
            with patch.object(
                pipeline.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0),
            ) as run:
                report = pipeline.refresh_source_story_gap_queue(
                    "CN",
                    queue_path,
                )

        self.assertEqual(
            report["_schema"],
            pipeline.SOURCE_STORY_GAP_QUEUE_SCHEMA,
        )
        self.assertIn("--language", run.call_args.args[0])

    def test_gap_queue_refresh_fails_with_bounded_validator_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue_path = Path(temporary) / "source_story_gap_queue_CN.json"
            queue_path.write_text(
                json.dumps({
                    "_schema": pipeline.SOURCE_STORY_GAP_QUEUE_SCHEMA,
                    "language": "CN",
                    "crossOwnerValidation": {
                        "status": "validation_failed",
                        "validationFailures": [{
                            "gate": "fixtureGate",
                            "storyKey": "opaque_story",
                            "expected": {"schemaVersion": 16},
                            "actual": {"schemaVersion": 15},
                            "sourceFile": "reports/fixture.json",
                        }],
                    },
                }),
                encoding="utf-8",
            )
            with patch.object(
                pipeline.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0),
            ):
                with self.assertRaises(RuntimeError) as raised:
                    pipeline.refresh_source_story_gap_queue(
                        "CN",
                        queue_path,
                    )

        message = str(raised.exception)
        self.assertIn("validator=report.crossOwnerValidation", message)
        self.assertIn("story=opaque_story", message)
        self.assertIn("expected={'schemaVersion': 16}", message)
        self.assertIn("actual={'schemaVersion': 15}", message)
        self.assertIn("source=reports/fixture.json", message)

    def test_offline_story_recovery_annotates_without_creating_graph_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue_path = Path(temporary) / "gap_queue.json"
            queue_path.write_text(
                json.dumps({
                    "_schema": pipeline.SOURCE_STORY_GAP_QUEUE_SCHEMA,
                    "offlineExhaustionEvidence": {
                        "status": "active",
                        "mappingId": "fixture-offline-v1",
                        "graphEffect": "none",
                        "sourceHashMismatches": [],
                    },
                    "missions": [{
                        "mission": "testm1",
                        "closedExactRuntimeConfigIsolatedScenes": [{
                            "sceneKey": "sns_testm1_1",
                            "missionId": "testm1",
                            "questId": "testm1_q#1",
                            "relation":
                                "objective_tracking_story_reference",
                            "recoveryStatus":
                                "closed_exact_mission_tracking_context_no_relative_order",
                            "activationBoundary": "tracking is not playback",
                            "orderBoundary": "tracking does not order files",
                        }, {
                            "sceneKey": "dlg_testm1_accept",
                            "missionId": "testm1",
                            "relation": "mission_accept_dialog",
                            "recoveryStatus":
                                "closed_exact_mission_accept_dialog_no_relative_order",
                            "activationBoundary": "mission accept lifecycle",
                            "orderBoundary": "accept does not order files",
                        }, {
                            "sceneKey": "sns_testm1_link",
                            "missionId": "testm1",
                            "relation": "sns_authored_mission_link",
                            "recoveryStatus":
                                "closed_exact_authored_sns_mission_link_no_relative_order",
                            "activationBoundary": "authored mission link",
                            "orderBoundary": "link does not order files",
                        }, {
                            "sceneKey": "radio_testm1_airwall",
                            "missionId": "testm1",
                            "relation":
                                "airwall_mission_state_radio_playback_context",
                            "recoveryStatus":
                                "closed_exact_native_playback_context_no_relative_order",
                            "sourceFiles": ["LevelData/testm1.json"],
                            "activationBoundary": "exact wall-state playback context",
                            "orderBoundary": "wall state does not order files",
                        }, {
                            "sceneKey": "dlg_testm1_tracking",
                            "missionId": "testm1",
                            "questIds": ["testm1_q#2"],
                            "relation":
                                "npc_proxy_tracking_dialog_navigation_context",
                            "recoveryStatus":
                                "closed_exact_non_owning_dialog_context_no_relative_order",
                            "sourceFiles": ["NpcProxyTable.json"],
                            "activationBoundary": "navigation is not playback",
                            "orderBoundary": "tracking does not order files",
                        }, {
                            "sceneKey": "dlg_testm1_lazy",
                            "missionId": "testm1",
                            "relation": "npc_proxy_lazy_destroy_dialog_context",
                            "recoveryStatus":
                                "closed_exact_non_owning_dialog_context_no_relative_order",
                            "sourceFiles": ["GameAssembly.dll"],
                            "activationBoundary": "deactivation context only",
                            "orderBoundary": "deactivation does not order files",
                        }, {
                            "sceneKey": "dlg_testm1_multi",
                            "missionId": "testm1",
                            "contextMissionIds": ["testm1", "testm2"],
                            "relation": "npc_proxy_ex_mission_context",
                            "recoveryStatus":
                                "closed_exact_multi_mission_runtime_config_no_relative_order",
                            "sourceFiles": ["NpcProxyExDataTable.json"],
                            "contextBoundary": "authored alternatives, not chronology",
                            "orderBoundary": "selection does not order files",
                        }],
                        "closedExactNativeIsolatedScenes": [{
                            "sceneKey": "dlg_testm1_reachable",
                            "missionId": "testm1",
                            "questId": "testm1_q#3",
                            "parentStoryKey": "dlg_testm1_parent",
                            "relation": "dialog_tree_reachable_story_playback",
                            "recoveryStatus":
                                "closed_exact_connected_dialog_tree_playback_context_no_relative_order",
                            "sourceFiles": ["TextAsset/parent.json"],
                            "orderBoundary": "context does not order files",
                        }, {
                            "sceneKey": "radio_testm1_gate",
                            "missionId": "testm1",
                            "questId": "testm1_q#4",
                            "relation": "levelscript_quest_state_gate",
                            "recoveryStatus":
                                "closed_exact_quest_state_gated_playback_context_no_relative_order",
                            "conditionType": "CheckQuestState",
                            "conditionComparer": "Equal",
                            "conditionQuestState": 2,
                            "eventNames": ["ScriptEvent_OnLeaderEnterTriggerVolume"],
                            "actionNames": ["PlayRadio"],
                            "sourceFiles": ["LevelScriptData/gate.json"],
                            "orderBoundary": "gate does not order files",
                        }, {
                            "sceneKey": "misc_dlg_testm1_local_shell",
                            "nominalStoryMissionId": "testm1",
                            "contextMissionId": "testm1",
                            "relation": "leveldata_levelscript_mission_context",
                            "recoveryStatus":
                                "closed_exact_same_mission_leveldata_playback_context_no_relative_order",
                            "sourceFiles": [
                                "LevelScriptData/local.json",
                                "LevelData/testm1.json",
                            ],
                            "activationBoundary": "exact local shell playback",
                            "orderBoundary": "local playback does not order files",
                        }, {
                            "sceneKey": "radio_testm1_shell",
                            "nominalStoryMissionId": "testm1",
                            "contextMissionId": "testm2",
                            "relation":
                                "authoritative_scope_leveldata_mission_context",
                            "recoveryStatus":
                                "closed_exact_cross_mission_leveldata_shell_playback_context_no_relative_order",
                            "activationBoundary": "exact playback in sibling shell",
                            "orderBoundary": "shell does not order files",
                        }, {
                            "sceneKey": "cutscene_testm1_alias",
                            "missionId": "testm1",
                            "rootStoryKeys": ["cutscene_testm1_root"],
                            "relation":
                                "cutscene_root_playback_alias_composed",
                            "recoveryStatus":
                                "closed_exact_composed_root_playback_context_no_relative_order",
                            "playbackBoundary": "exact composed playback",
                            "orderBoundary": "alias does not order files",
                        }, {
                            "sceneKey": "cutscene_testm1_lua",
                            "missionId": "testm1",
                            "relation": "lua_controller_playback",
                            "recoveryStatus":
                                "closed_exact_lua_controller_playback_no_mission_owner_or_relative_order",
                            "luaFile": "Lua/Phase/Test.lua",
                            "luaCall": "GameAction.PlayCutscene",
                            "sourceFiles": [
                                "Lua/Phase/Test.lua",
                                "reports/mission_order/lua_consumer_reference_audit.json",
                            ],
                            "playbackBoundary": "exact shipped Lua playback",
                            "graphEffect": "none",
                        }, {
                            "sceneKey": "black_testm1_timeline",
                            "nominalStoryMissionId": "testm1",
                            "relation": "timeline_dialog_contains_black",
                            "recoveryStatus":
                                "closed_exact_timeline_black_carrier_context_owner_or_order_unresolved",
                            "sourceFiles": ["CAB-fixture", "track.json"],
                            "activationBoundary": "exact carrier only",
                            "orderBoundary": "carrier does not order files",
                        }, {
                            "sceneKey": "black_testm1_tree",
                            "nominalStoryMissionId": "testm1",
                            "relation": "dialog_tree_narrative_action",
                            "recoveryStatus":
                                "closed_exact_dialog_tree_black_carrier_context_no_file_order",
                            "sourceFiles": ["dialog-tree.json"],
                            "activationBoundary": "exact parent only",
                            "orderBoundary": "tree adjacency does not order files",
                        }, {
                            "sceneKey": "dlg_testm1_foreign_shell",
                            "nominalStoryMissionId": "testm1",
                            "contextMissionId": "testm2",
                            "relation": "leveldata_levelscript_mission_context",
                            "recoveryStatus":
                                "closed_exact_cross_mission_leveldata_playback_context_no_relative_order",
                            "sourceFiles": [
                                "LevelScriptData/test.json",
                                "LevelData/testm2.json",
                            ],
                            "activationBoundary": "exact foreign shell playback",
                            "orderBoundary": "shell does not transfer ownership",
                        }, {
                            "sceneKey": "radio_testm1_quest_shell",
                            "nominalStoryMissionId": "testm1",
                            "contextMissionId": "testm2",
                            "contextQuestId": "testm2_q#1",
                            "relation":
                                "cross_owner_levelscript_quest_playback_context",
                            "recoveryStatus":
                                "closed_exact_cross_mission_quest_playback_context_no_relative_order",
                            "sourceFiles": [
                                "LevelScriptData/test.json",
                                "MissionRuntimeAsset/testm2.json",
                            ],
                            "orderBoundary": "quest playback does not transfer ownership",
                        }],
                        "deferredOfflineExhaustedIsolatedScenes": [{
                            "sceneKey": "dlg_testm1_1",
                            "missionId": "testm1",
                            "recoveryStatus":
                                "deferred_current_build_offline_surface_exhausted",
                            "evidenceKind":
                                "registered_dialog_definition_without_recovered_activator",
                            "consumerBoundary": "no exact activator",
                            "orderBoundary": "definition order is not chronology",
                        "reopenWhen": "source changes",
                        "graphEffect": "none",
                        "gameAssemblySha256": "fixture",
                    }, {
                        "sceneKey": "text_testm1_1",
                        "missionId": "testm1",
                        "recoveryStatus":
                            "deferred_current_build_offline_surface_exhausted",
                        "evidenceKind":
                            "reading_popup_definition_without_recovered_activator",
                        "consumerBoundary": "no exact activator",
                        "orderBoundary": "definition order is not chronology",
                        "reopenWhen": "source changes",
                        "graphEffect": "none",
                        "gameAssemblySha256": "fixture",
                    }, {
                        "sceneKey": "radio_testm1_1",
                        "missionId": "testm1",
                        "recoveryStatus":
                            "deferred_current_build_offline_surface_exhausted",
                        "evidenceKind":
                            "radio_definition_without_recovered_consumer",
                        "consumerBoundary": "no exact activator",
                        "orderBoundary": "definition order is not chronology",
                        "reopenWhen": "source changes",
                        "graphEffect": "none",
                        "gameAssemblySha256": "fixture",
                        }],
                        "partialRegisteredDialogTreeCarriers": [{
                            "sceneKey": "dlg_testm1_partial",
                            "missionId": "testm1",
                            "recoveryStatus":
                                "actionable_partial_registered_dialog_tree_partition",
                            "evidenceKind":
                                "partial_registered_dialog_tree_trunk_group_line_partition",
                            "coveredLineIds": ["dlg_testm1_partial_01"],
                            "coveredLineCount": 1,
                            "missingLineIds": ["dlg_testm1_partial_02"],
                            "missingLineCount": 1,
                            "parentDialogTrees": [{
                                "sceneKey": "dlg_testm1_partial_1",
                                "sourceFile": "TextAsset/partial.json",
                            }],
                            "consumerBoundary": "one authored row unmatched",
                            "orderBoundary": "partial carrier is not chronology",
                            "graphEffect": "none",
                            "gameAssemblySha256": "fixture",
                        }],
                    }],
                }),
                encoding="utf-8",
            )
            manifest = {
                "dlg_testm1_1": {
                    "attachmentStatus": "definition_only_no_consumer",
                    "routes": [],
                },
                "dlg_testm1_partial": {
                    "attachmentStatus": "unlinked_no_trigger_route",
                    "routes": [],
                },
                "sns_testm1_1": {
                    "attachmentStatus": "connected",
                    "routes": [{"relation": "objective_tracking_story_reference"}],
                },
                "dlg_testm1_accept": {
                    "attachmentStatus": "connected",
                    "routes": [{"relation": "mission_accept_dialog"}],
                },
                "sns_testm1_link": {
                    "attachmentStatus": "connected",
                    "routes": [{"relation": "sns_authored_mission_link"}],
                },
                "radio_testm1_shell": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation":
                            "authoritative_scope_leveldata_mission_context",
                    }],
                },
                "misc_dlg_testm1_local_shell": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation": "leveldata_levelscript_mission_context",
                    }],
                },
                "cutscene_testm1_alias": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation":
                            "cutscene_root_playback_alias_composed",
                    }],
                },
                "cutscene_testm1_lua": {
                    "attachmentStatus": "trigger_known_owner_unresolved",
                    "nominalMissionId": "testm1",
                    "routes": [{"relation": "lua_controller_playback"}],
                },
                "black_testm1_timeline": {
                    "attachmentStatus": "unlinked_no_trigger_route",
                    "routes": [],
                },
                "black_testm1_tree": {
                    "attachmentStatus": "connected",
                    "routes": [{"causality": "context_owner_unresolved"}],
                },
                "dlg_testm1_foreign_shell": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation": "leveldata_levelscript_mission_context",
                    }],
                },
                "radio_testm1_quest_shell": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation":
                            "cross_owner_levelscript_quest_playback_context",
                    }],
                },
                "dlg_testm1_reachable": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation": "dialog_tree_reachable_story_playback",
                    }],
                },
                "radio_testm1_gate": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation": "levelscript_quest_state_gate",
                    }],
                },
                "dlg_testm1_tracking": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation":
                            "npc_proxy_tracking_dialog_navigation_context",
                    }],
                },
                "dlg_testm1_lazy": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation": "npc_proxy_lazy_destroy_dialog_context",
                    }],
                },
                "dlg_testm1_multi": {
                    "attachmentStatus": "connected",
                    "routes": [{
                        "relation": "npc_proxy_ex_mission_context",
                    }],
                },
            }

            result = pipeline.publish_offline_story_recovery(
                manifest,
                queue_path,
            )

        self.assertEqual(result["status"], "active")
        self.assertEqual(result["publishedStoryKeys"], 1)
        self.assertEqual(result["publishedPartialStoryKeys"], 1)
        self.assertEqual(result["publishedRuntimeContextStoryKeys"], 17)
        self.assertEqual(result["outsidePipelineCoverageStoryKeys"], 3)
        self.assertEqual(
            manifest["dlg_testm1_1"]["attachmentStatus"],
            "definition_only_no_consumer",
        )
        self.assertEqual(manifest["dlg_testm1_1"]["routes"], [])
        recovery = manifest["dlg_testm1_1"]["offlineRecovery"]
        self.assertEqual(recovery["graphEffect"], "none")
        self.assertNotIn("gameAssemblySha256", recovery)
        partial = manifest["dlg_testm1_partial"]["partialRecovery"]
        self.assertEqual(partial["missingLineIds"], [
            "dlg_testm1_partial_02",
        ])
        self.assertNotIn("gameAssemblySha256", partial)
        self.assertNotIn("offlineRecovery", manifest["dlg_testm1_partial"])
        runtime_recovery = manifest["sns_testm1_1"][
            "runtimeContextRecovery"
        ]
        self.assertEqual(runtime_recovery["graphEffect"], "none")
        self.assertEqual(
            runtime_recovery["questId"],
            "testm1_q#1",
        )
        self.assertEqual(
            manifest["dlg_testm1_accept"]["runtimeContextRecovery"][
                "recoveryStatus"
            ],
            "closed_exact_mission_accept_dialog_no_relative_order",
        )
        self.assertEqual(
            manifest["sns_testm1_link"]["runtimeContextRecovery"][
                "recoveryStatus"
            ],
            "closed_exact_authored_sns_mission_link_no_relative_order",
        )
        self.assertEqual(
            result["storyTriggerManifestOverlay"]["radio_testm1_airwall"][
                "runtimeContextRecovery"
            ][
                "sourceFiles"
            ],
            ["LevelData/testm1.json"],
        )
        self.assertEqual(
            manifest["radio_testm1_airwall"]["runtimeContextRecovery"][
                "relation"
            ],
            "airwall_mission_state_radio_playback_context",
        )
        self.assertEqual(
            manifest["misc_dlg_testm1_local_shell"][
                "runtimeContextRecovery"
            ]["contextMissionId"],
            "testm1",
        )
        self.assertEqual(
            manifest["radio_testm1_shell"]["runtimeContextRecovery"][
                "contextMissionId"
            ],
            "testm2",
        )
        self.assertEqual(
            manifest["cutscene_testm1_alias"]["runtimeContextRecovery"][
                "rootStoryKeys"
            ],
            ["cutscene_testm1_root"],
        )
        self.assertEqual(
            manifest["black_testm1_timeline"]["runtimeContextRecovery"][
                "sourceFiles"
            ],
            ["CAB-fixture", "track.json"],
        )
        self.assertEqual(
            manifest["black_testm1_tree"]["runtimeContextRecovery"][
                "relation"
            ],
            "dialog_tree_narrative_action",
        )
        self.assertEqual(
            manifest["dlg_testm1_foreign_shell"]["runtimeContextRecovery"][
                "contextMissionId"
            ],
            "testm2",
        )
        self.assertEqual(
            manifest["radio_testm1_quest_shell"]["runtimeContextRecovery"][
                "contextQuestId"
            ],
            "testm2_q#1",
        )
        self.assertEqual(
            manifest["dlg_testm1_reachable"]["runtimeContextRecovery"][
                "parentStoryKey"
            ],
            "dlg_testm1_parent",
        )
        self.assertEqual(
            manifest["radio_testm1_gate"]["runtimeContextRecovery"][
                "conditionQuestState"
            ],
            2,
        )
        self.assertEqual(
            manifest["dlg_testm1_tracking"]["runtimeContextRecovery"][
                "questIds"
            ],
            ["testm1_q#2"],
        )
        self.assertEqual(
            manifest["dlg_testm1_lazy"]["runtimeContextRecovery"][
                "relation"
            ],
            "npc_proxy_lazy_destroy_dialog_context",
        )
        self.assertEqual(
            manifest["cutscene_testm1_lua"]["runtimeContextRecovery"][
                "luaCall"
            ],
            "GameAction.PlayCutscene",
        )
        self.assertEqual(
            manifest["dlg_testm1_multi"]["runtimeContextRecovery"][
                "contextMissionIds"
            ],
            ["testm1", "testm2"],
        )
        overlay = result["storyTriggerManifestOverlay"]["text_testm1_1"]
        self.assertEqual(overlay["routes"], [])
        self.assertEqual(
            overlay["attachmentStatus"],
            "offline_exhausted_outside_pipeline_coverage_denominator",
        )
        radio_overlay = result["storyTriggerManifestOverlay"][
            "radio_testm1_1"
        ]
        self.assertEqual(radio_overlay["kind"], "radio")
        self.assertEqual(radio_overlay["routes"], [])

    def test_offline_story_recovery_publishes_non_owning_quest_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue_path = Path(temporary) / "gap_queue.json"
            queue_path.write_text(
                json.dumps({
                    "_schema": pipeline.SOURCE_STORY_GAP_QUEUE_SCHEMA,
                    "offlineExhaustionEvidence": {
                        "status": "active",
                        "mappingId": "fixture-offline-v1",
                        "graphEffect": "none",
                        "sourceHashMismatches": [],
                    },
                    "questAttachmentDiagnosticEvidence": {
                        "status": "active",
                        "mappingId": "fixture-quest-negative-v1",
                        "graphEffect": "none",
                        "sourceHashMismatches": [],
                        "validationFailures": [],
                    },
                    "missions": [{
                        "mission": "testm1",
                        "closedQuestAttachmentDiagnostics": [{
                            "questId": "testm1_q#1",
                            "missionId": "testm1",
                            "recoveryStatus":
                                "closed_server_placeholder_without_client_story_semantics",
                            "attachmentBoundary": "no client Story field",
                            "orderBoundary": "no order edge",
                            "reopenWhen": "source changes",
                            "graphEffect": "none",
                        }],
                        "deferredOfflineExhaustedIsolatedScenes": [],
                    }],
                }),
                encoding="utf-8",
            )

            result = pipeline.publish_offline_story_recovery(
                {},
                queue_path,
            )

        self.assertEqual(result["questAttachmentDiagnosticStatus"], "active")
        self.assertEqual(
            result["questAttachmentDiagnosticMappingId"],
            "fixture-quest-negative-v1",
        )
        diagnostic = result["questAttachmentDiagnostics"]["testm1_q#1"]
        self.assertEqual(diagnostic["graphEffect"], "none")
        self.assertEqual(diagnostic["attachmentBoundary"], "no client Story field")

    def test_offline_story_recovery_fails_closed_on_schema_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue_path = Path(temporary) / "gap_queue.json"
            queue_path.write_text(
                json.dumps({
                    "_schema": "sourceStoryGapQueue.v999",
                    "offlineExhaustionEvidence": {
                        "status": "active",
                        "mappingId": "fixture-offline-v999",
                        "graphEffect": "none",
                        "sourceHashMismatches": [],
                    },
                    "missions": [],
                }),
                encoding="utf-8",
            )
            manifest = {
                "dlg_testm1_1": {
                    "attachmentStatus": "definition_only_no_consumer",
                    "routes": [],
                }
            }

            result = pipeline.publish_offline_story_recovery(
                manifest,
                queue_path,
            )

        self.assertEqual(result["status"], "rejected_stale_or_incompatible")
        self.assertNotIn("offlineRecovery", manifest["dlg_testm1_1"])

    def test_project_authored_story_provenance_is_visible_but_graph_neutral(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue_path = Path(temporary) / "gap_queue.json"
            queue_path.write_text(
                json.dumps({
                    "_schema": pipeline.SOURCE_STORY_GAP_QUEUE_SCHEMA,
                    "offlineExhaustionEvidence": {
                        "status": "active",
                        "mappingId": "fixture-offline-v1",
                        "graphEffect": "none",
                        "sourceHashMismatches": [],
                    },
                    "projectAuthoredStoryEvidence": {
                        "status": "validated",
                        "graphEffect": "none",
                        "validationFailures": [],
                    },
                    "missions": [{
                        "mission": "ui_shell",
                        "closedNonMissionContentIsolatedScenes": [{
                            "sceneKey": "opaque_notice",
                            "recoveryStatus":
                                "excluded_project_authored_story_content",
                            "evidenceKind":
                                "project_authored_story_content",
                            "storyKind": "black",
                            "sourceFiles": ["scripts/producer.py"],
                            "gameDataEvidence": False,
                            "consumerBoundary": "not original game data",
                            "orderBoundary": "no graph evidence",
                            "graphEffect": "none",
                        }],
                    }],
                }),
                encoding="utf-8",
            )
            manifest = {
                "opaque_notice": {
                    "key": "opaque_notice",
                    "attachmentStatus": "unlinked",
                    "routes": [],
                }
            }

            result = pipeline.publish_offline_story_recovery(
                manifest,
                queue_path,
            )

        provenance = manifest["opaque_notice"]["contentProvenance"]
        self.assertEqual(provenance["sourceFiles"], ["scripts/producer.py"])
        self.assertFalse(provenance["gameDataEvidence"])
        self.assertEqual(provenance["graphEffect"], "none")
        self.assertEqual(result["publishedProjectAuthoredStoryKeys"], 1)
        self.assertEqual(manifest["opaque_notice"]["routes"], [])

    def test_offline_recovery_publishes_graph_neutral_missing_mission_shell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue_path = root / "gap_queue.json"
            queue_path.write_text(
                json.dumps({
                    "missions": [{
                        "mission": "gm_fixture",
                        "metrics": {
                            "sceneCount": 2,
                            "strongEdgeCount": 0,
                            "sourceCycles": 0,
                        },
                        "deferredOfflineExhaustedIsolatedScenes": [],
                    }],
                }),
                encoding="utf-8",
            )
            index = {
                "counts": {"missions": 1},
                "missions": [{"id": "existing", "file": "missions/existing.json"}],
            }
            offline = {
                "status": "active",
                "storyTriggerManifestOverlay": {
                    "dlg_gm_fixture_1": {
                        "nominalMissionId": "gm_fixture",
                        "offlineRecovery": {
                            "missionId": "gm_fixture",
                            "graphEffect": "none",
                        },
                    },
                    "radio_gm_fixture_1": {
                        "nominalMissionId": "gm_fixture",
                        "offlineRecovery": {
                            "missionId": "gm_fixture",
                            "graphEffect": "none",
                        },
                    },
                },
            }
            published = pipeline.publish_offline_recovery_mission_shells(
                index,
                root,
                offline,
                queue_path,
            )
            shell = json.loads(
                (root / "missions/gm_fixture.json").read_text(encoding="utf-8")
            )

        self.assertEqual(published, ["gm_fixture"])
        self.assertEqual(index["counts"]["missions"], 2)
        self.assertEqual(index["counts"]["offlineRecoveryMissionShells"], 1)
        summary = next(row for row in index["missions"] if row["id"] == "gm_fixture")
        self.assertTrue(summary["offlineRecoveryShell"])
        self.assertEqual(summary["offlineRecoveryStoryCount"], 2)
        self.assertEqual(shell["nodes"], [])
        self.assertEqual(shell["edges"], [])
        self.assertTrue(shell["mission"]["offlineRecoveryShell"])
        self.assertEqual(shell["storyOrder"]["mission"], "gm_fixture")

    def test_dynamic_scene_cross_references_remain_non_owning(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit_path = Path(temporary) / "dynamic_scene.json"
            audit_path.write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "nativeIdentityBoundary": {
                        "classification":
                            "exact_cross_reference_not_runtime_owner",
                        "directBridgeFound": False,
                        "missionGraphAction": "none",
                        "promotionRequirement": "typed runtime bridge required",
                    },
                    "storyIdentityCandidates": [{
                        "scene": "map01",
                        "logicId": "2100060003",
                        "sourceFile": "DynamicStreaming/map01/fb_main.bytes",
                        "missionControls": [{
                            "compareType": 0,
                            "toBeTrue": True,
                            "conditions": [{
                                "identifier": "e1m2_q#5",
                                "isQuest": True,
                                "state": 3,
                                "isSame": True,
                            }],
                        }],
                        "storyOccurrences": [{
                            "storyKey": "cutscene_e1m3_1",
                            "levelId": "map01_lv001",
                            "scriptId": "2100060003",
                            "recordOffset": 368,
                            "actionName": "PlayFmvAction",
                            "sourceFile":
                                "LevelScriptData/map01_lv001/2100060003.json",
                            "nativeEventOwnerStatus":
                                "exact_serialized_control_path",
                        }],
                    }],
                }),
                encoding="utf-8",
            )

            published = pipeline.load_dynamic_scene_identity_cross_references(
                audit_path
            )

        self.assertIsNotNone(published)
        self.assertEqual(published["missionGraphAction"], "none")
        self.assertFalse(published["directBridgeFound"])
        self.assertEqual(published["counts"]["candidateRoots"], 1)
        row = published["rows"][0]
        self.assertEqual(row["logicId"], row["scriptId"])
        self.assertEqual(row["missionOwnerStatus"], "unresolved")
        self.assertFalse(row["storyBinding"])
        self.assertFalse(row["orderEvidence"])

    def test_dynamic_scene_cross_references_fail_closed_on_positive_bridge(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit_path = Path(temporary) / "dynamic_scene.json"
            audit_path.write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "nativeIdentityBoundary": {
                        "classification":
                            "exact_cross_reference_not_runtime_owner",
                        "directBridgeFound": True,
                        "missionGraphAction": "none",
                    },
                    "storyIdentityCandidates": [],
                }),
                encoding="utf-8",
            )

            published = pipeline.load_dynamic_scene_identity_cross_references(
                audit_path
            )

        self.assertIsNone(published)

    def test_dynamic_scene_typed_target_bridge_stays_local_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            audit_path = root / "dynamic_scene.json"
            bridge_path = root / "dynamic_scene_bridge.json"
            audit = {
                "schemaVersion": 1,
                "nativeIdentityBoundary": {
                    "classification":
                        "exact_cross_reference_not_runtime_owner",
                    "directBridgeFound": False,
                    "missionActivationBridgeFound": False,
                    "missionGraphAction": "none",
                    "promotionRequirement":
                        "mission condition activation edge required",
                },
                "storyIdentityCandidates": [{
                    "scene": "map02",
                    "logicId": "10100282001",
                    "sourceFile": "DynamicStreaming/map02/fb_main.bytes",
                    "missionControls": [{
                        "conditions": [{
                            "identifier": "c27m3_q#3",
                            "isQuest": True,
                            "state": 3,
                            "isSame": True,
                        }],
                    }],
                    "storyOccurrences": [{
                        "storyKey": "dlg_c27m3_6",
                        "levelId": "map02_lv001",
                        "scriptId": "10100282001",
                        "recordOffset": 7,
                        "actionName": "StartDialogAndTeleportAction",
                    }],
                }],
            }
            audit_path.write_text(json.dumps(audit), encoding="utf-8")
            bridge_path.write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "sources": {
                        "identityAudit": {
                            "sha256": hashlib.sha256(
                                audit_path.read_bytes()
                            ).hexdigest(),
                        },
                    },
                    "boundary": {
                        "classification":
                            "exact_local_context_without_mission_activation_edge",
                        "missionActivationBridgeFound": False,
                        "missionGraphAction": "none",
                        "levelScriptTriggerVolumeBoundary": {
                            "classification":
                                "exact_local_trigger_geometry_without_dynamic_scene_or_mission_foreign_key",
                            "foreignKeyBridgeFound": False,
                            "schemaMappingId":
                                "current-global-metadata-levelscript-trigger-volume-data-fields",
                            "leaderDeclaredFieldCount": 0,
                        },
                    },
                    "bridgeRows": [{
                        "logicId": "10100282001",
                        "missionOwnerStatus": "unresolved",
                        "storyBinding": False,
                        "orderEvidence": False,
                        "missionGraphAction": "none",
                        "classification":
                            "exact_dynamic_scene_target_and_shared_levelscript_control_path",
                        "exactTargetActions": [{
                            "actionName": "ShowSceneDecorationNew",
                            "unionTag": "0x0485",
                            "serializedMemberCount": 10,
                            "recordOffset": 284,
                            "localId": 6,
                            "targetDynamicEntityLogicId": "10100282001",
                            "visible": False,
                            "payloadFullyConsumed": True,
                            "targetParam": {
                                "idRef": -1,
                                "paramSource": 0,
                                "path": None,
                            },
                            "visibleParam": {
                                "idRef": -1,
                                "paramSource": 0,
                                "path": None,
                            },
                            "localTriggerVolumeContext": {
                                "status":
                                    "exact_local_levelscript_trigger_volume_without_foreign_identity",
                                "selectorSlotIds": [80001],
                                "matchedSlotIds": [80001],
                                "missingSlotIds": [],
                                "scriptIdVerified": True,
                                "triggerVolumesStatus": "present",
                                "triggerVolumesParseStatus": "decoded",
                                "dynamicSceneIdentityFieldPresent": False,
                                "missionOrQuestIdentityFieldPresent": False,
                                "foreignKeyBridgeFound": False,
                                "missionGraphAction": "none",
                                "schema": {
                                    "baseDeclaredFieldCount": 8,
                                    "leaderDeclaredFieldCount": 0,
                                    "serializedMemberCount": 8,
                                    "mappingId":
                                        "current-global-metadata-levelscript-trigger-volume-data-fields",
                                },
                                "triggerVolumes": [{
                                    "keySlotId": 80001,
                                    "slotId": 80001,
                                    "triggerVolumeType": "Leader",
                                    "memberCount": 8,
                                    "triggerCountLimit": 1,
                                    "enterCheckOnGround": False,
                                    "isImportant": False,
                                    "triggerOnPole": False,
                                    "waitSrvRes": False,
                                    "shapeList": {
                                        "parseStatus": "decoded",
                                        "shapes": [{
                                            "shapeType": "Sphere",
                                            "position": {
                                                "x": -757.75,
                                                "y": 234.828,
                                                "z": -1185.85,
                                            },
                                            "radius": 59.0,
                                        }],
                                    },
                                }],
                            },
                            "storyControlPathLinks": [{
                                "storyKey": "dlg_c27m3_6",
                                "storyRecordOffset": 7,
                                "storyActionName":
                                    "StartDialogAndTeleportAction",
                                "sharedControlPaths": [{
                                    "status":
                                        "exact_serialized_shared_control_path",
                                    "relation":
                                        "decoration_follows_story_on_same_path",
                                    "headerName":
                                        "ScriptEvent_OnLeaderEnterTriggerVolume",
                                    "headerLocalId": 4,
                                    "eventDetail": {
                                        "summary":
                                            "leader enters trigger slot 80001",
                                        "triggerSlotIdFilter": 80001,
                                    },
                                    "storyPathLocalIds": [5],
                                    "decorationPathLocalIds": [5, 6],
                                }],
                            }],
                        }],
                    }],
                }),
                encoding="utf-8",
            )

            published = pipeline.load_dynamic_scene_identity_cross_references(
                audit_path,
                bridge_path,
            )

        self.assertIsNotNone(published)
        self.assertEqual(published["counts"]["exactTargetBridgeRoots"], 1)
        self.assertEqual(
            published["counts"]["sharedControlPathStoryOccurrences"],
            1,
        )
        row = published["rows"][0]
        bridge = row["localContextBridge"]
        self.assertFalse(bridge["storyBinding"])
        self.assertFalse(bridge["orderEvidence"])
        self.assertEqual(bridge["missionGraphAction"], "none")
        path = bridge["exactTargetActions"][0][
            "storyControlPathLinks"
        ][0]["sharedControlPaths"][0]
        self.assertEqual(path["triggerSlotId"], 80001)
        self.assertEqual(path["decorationPathLocalIds"], [5, 6])
        context = bridge["exactTargetActions"][0][
            "localTriggerVolumeContext"
        ]
        self.assertFalse(context["foreignKeyBridgeFound"])
        self.assertEqual(
            context["triggerVolumes"][0]["shapes"][0]["shapeType"],
            "Sphere",
        )
        self.assertEqual(
            published["counts"]["exactLocalTriggerVolumeContexts"],
            1,
        )

    def test_trigger_route_reads_exact_levelscript_occurrence_paths(self):
        row = {
            "key": "radio_testm1_1",
            "relation": "levelscript_mission_context",
            "direction": "context",
            "levelScriptOccurrences": [{
                "levelId": "map_test",
                "scriptId": "70000000001",
                "sourceFile": "LevelScriptData/map_test/70000000001.json",
                "actionName": "PlayRadioAction",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "LevelEvent_OnBattleSignal",
                    "headerLocalId": 4,
                    "eventDetail": {"summary": "literal battle signal"},
                    "path": [{
                        "edge": "nextId",
                        "localId": 5,
                        "actionName": "PlayRadioAction",
                        "recordClass": "play_radio",
                    }],
                }],
            }],
        }

        route = pipeline.build_story_trigger_route(row, mission_id="testm1")

        self.assertEqual(route["eventNames"], ["LevelEvent_OnBattleSignal"])
        self.assertEqual(route["actionNames"], ["PlayRadioAction"])
        self.assertEqual(route["scriptIds"], ["70000000001"])
        self.assertEqual(route["controlPathCount"], 1)
        self.assertEqual(route["nativePaths"][0]["headerLocalId"], 4)

    def test_unresolved_timeline_route_stays_context_and_attaches_files(self):
        row = {
            "key": "black_testm1_1",
            "relation": "timeline_dialog_contains_black",
            "direction": "context",
            "phase": "timeline_contained",
            "parentStoryKey": "dlg_parent",
            "sourceFiles": ["CAB-story"],
            "assetPaths": ["TextPlayable.json"],
            "trackPaths": ["Track.json"],
            "rootPaths": ["TimelineRoot.json"],
        }

        route = pipeline.build_story_trigger_route(
            row,
            mission_id="testm1",
            owner_status="unresolved",
        )

        self.assertEqual(route["causality"], "context_owner_unresolved")
        self.assertEqual(
            route["sourceFiles"],
            [
                "CAB-story",
                "TextPlayable.json",
                "Track.json",
                "TimelineRoot.json",
            ],
        )
        direct = {"causality": "playback", "questId": "testm1_q#1"}
        self.assertLess(
            pipeline.story_trigger_route_sort_key(direct),
            pipeline.story_trigger_route_sort_key(route),
        )

    def test_trigger_route_reads_world_entity_listener_evidence(self):
        row = {
            "key": "radio_testm1_1",
            "relation": "mission_tracked_world_entity_levelscript_context",
            "direction": "context",
            "worldEntityLevelScriptEvidence": [{
                "levelId": "map_test",
                "scriptId": "70000000001",
                "sourceFile": "LevelScriptData/map_test/70000000001.json",
                "nativeAction": "PlayRadio",
                "listener": {
                    "status": "exact_serialized_control_path",
                    "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "headerLocalId": 6,
                    "eventDetail": {
                        "summary": "leader enters trigger slot 80001",
                    },
                    "path": [{
                        "edge": "Split.actions[0]",
                        "localId": 8,
                        "actionName": "PlayRadio",
                        "recordClass": "play_radio",
                    }],
                },
            }],
        }

        route = pipeline.build_story_trigger_route(row, mission_id="testm1")

        self.assertEqual(
            route["eventNames"],
            ["ScriptEvent_OnLeaderEnterTriggerVolume"],
        )
        self.assertEqual(route["actionNames"], ["PlayRadio"])
        self.assertEqual(route["controlPathCount"], 1)
        self.assertEqual(route["nativePaths"][0]["headerLocalId"], 6)

    def test_trigger_route_preserves_foreign_dialog_timeline_chain(self):
        row = {
            "key": "dlg_testm1_16",
            "relation": "timeline_dialog_contains_foreign_dialog",
            "direction": "context",
            "phase": "timeline_contained",
            "confidence": "native_exact_host",
            "parentStoryKey": "dlg_testm1_7",
            "timelines": ["dlgtl_testm1_7_sub_1"],
            "textIds": [
                "dlg_testm1_16_001",
                "dlg_testm1_16_002",
            ],
            "optionIds": [
                "option_dlg_testm1_16_1_001",
                "option_dlg_testm1_16_1_002",
            ],
            "placementBoundary": "parent content on both sides",
            "graphEffect": "none",
            "timelineDialogContainments": [{
                "timeline": "dlgtl_testm1_7_sub_1",
                "lineIds": [
                    "dlg_testm1_16_001",
                    "dlg_testm1_16_002",
                ],
                "optionIds": [
                    "option_dlg_testm1_16_1_001",
                    "option_dlg_testm1_16_1_002",
                ],
                "beforeParentLineId": "dlg_testm1_7_009",
                "afterParentLineId": "dlg_testm1_7_005",
            }],
            "parentDialogNativeOccurrences": [{
                "levelId": "map_test",
                "scriptId": "70000000001",
                "sourceFile":
                    "LevelScriptData/map_test/70000000001.json",
                "actionName": "StartDialogAndTeleportAction",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName":
                        "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "headerLocalId": 4,
                    "eventDetail": {
                        "summary": "leader enters trigger slot 80001",
                    },
                    "path": [{
                        "edge": "nextId",
                        "localId": 5,
                        "actionName":
                            "StartDialogAndTeleportAction",
                        "recordClass": "play_dialog",
                    }],
                }],
            }],
        }

        route = pipeline.build_story_trigger_route(
            row,
            mission_id="testm1",
        )

        self.assertEqual(route["causality"], "context")
        self.assertEqual(
            [step["kind"] for step in route["steps"]],
            [
                "mission",
                "native_event",
                "levelscript",
                "native_action",
                "parent_story",
                "dialog_timeline",
                "story",
            ],
        )
        self.assertEqual(route["parentStoryKey"], "dlg_testm1_7")
        self.assertEqual(
            route["timelineIds"],
            ["dlgtl_testm1_7_sub_1"],
        )
        self.assertEqual(
            route["beforeParentLineIds"],
            ["dlg_testm1_7_009"],
        )
        self.assertEqual(
            route["afterParentLineIds"],
            ["dlg_testm1_7_005"],
        )
        self.assertEqual(route["graphEffect"], "none")

    def test_trigger_route_preserves_exact_narrative_interactive(self):
        row = {
            "key": "text_testm1_1",
            "relation": "levelscript_interactive_narrative_config",
            "direction": "context",
            "scriptIds": ["70000000001"],
            "localInteractiveId": 40001,
            "rawTypeId": "rp_text_testm1_1",
            "entityDetailIds": ["int_narrative_book"],
            "entityTemplateIds": ["int_narrative_mission"],
        }

        route = pipeline.build_story_trigger_route(row, mission_id="testm1")

        self.assertEqual(
            [step["kind"] for step in route["steps"]],
            ["mission", "levelscript", "narrative_interactive", "story"],
        )
        self.assertEqual(route["steps"][2]["id"], "40001")
        self.assertEqual(
            route["steps"][2]["summaries"],
            ["rp_text_testm1_1", "int_narrative_mission"],
        )
        self.assertEqual(route["localInteractiveId"], 40001)
        self.assertEqual(route["entityDetailIds"], ["int_narrative_book"])

    def test_trigger_route_preserves_exact_leveldata_narrative_interactive(
        self,
    ):
        row = {
            "key": "text_testm1_2",
            "relation": "leveldata_interactive_narrative_config",
            "direction": "context",
            "levelDataAssets": ["map_test_lv_data_sub_testm1"],
            "entityLogicId": 10002,
            "interactiveRecordIndex": 1,
            "rawTypeId": "rp_text_testm1_2",
            "entityDetailIds": ["int_narrative_book"],
            "entityTemplateIds": ["int_narrative_scene"],
            "progressLockConditionStatus": "decoded",
            "progressLockConditionUnionTag": 0,
            "progressLockConditionSerializedMemberCount": 3,
            "progressLockConditionType": "CombinedConditionRuntime",
            "progressLockConditionOperator": 1,
            "progressLockSerializedRuntimeFlag": False,
            "progressLockConditionTree": {
                "unionTag": 0,
                "serializedMemberCount": 3,
                "conditionType": "CombinedConditionRuntime",
                "conditionOperator": 1,
                "serializedRuntimeFlag": False,
                "conditions": [{
                    "unionTag": 12,
                    "serializedMemberCount": 3,
                    "conditionType": "SimpleConditionCheckMissionState",
                    "ownerKind": "mission",
                    "ownerId": "testm0",
                    "compareOperator": 0,
                    "compareTarget": 3,
                }],
            },
            "progressLockConditions": [{
                "unionTag": 12,
                "serializedMemberCount": 3,
                "conditionType": "SimpleConditionCheckMissionState",
                "ownerKind": "mission",
                "ownerId": "testm0",
                "compareOperator": 0,
                "compareTarget": 3,
            }],
        }

        route = pipeline.build_story_trigger_route(row, mission_id="testm1")

        self.assertEqual(
            [step["kind"] for step in route["steps"]],
            [
                "mission",
                "leveldata",
                "availability_condition",
                "narrative_interactive",
                "story",
            ],
        )
        self.assertEqual(
            route["steps"][1]["ids"],
            ["map_test_lv_data_sub_testm1"],
        )
        self.assertEqual(
            route["steps"][2]["id"],
            "CombinedConditionRuntime",
        )
        self.assertIn(
            "mission testm0 state 3",
            route["steps"][2]["summaries"][1],
        )
        self.assertEqual(route["steps"][3]["id"], "10002")
        self.assertEqual(route["entityLogicId"], 10002)
        self.assertEqual(route["interactiveRecordIndex"], 1)
        self.assertEqual(
            route["progressLockConditions"][0]["ownerId"],
            "testm0",
        )
        self.assertEqual(
            route["progressLockConditionTree"]["conditionOperator"],
            1,
        )

    def test_trigger_route_preserves_shared_proxy_selection_boundary(self):
        row = {
            "key": "dlg_testm1_2",
            "relation":
                "unique_mission_tracked_npc_proxy_dialog_context",
            "direction": "context",
            "phase": "server_selected_proxy_state",
            "confidence": "native_exact_mission_context",
            "evidenceTier": "derived_exact_mission",
            "ownership": False,
            "npcProxyId": "proxy_a",
            "candidateQuestIds": ["testm1_q#4", "testm1_q#12"],
            "activeRowIndex": 2,
            "configuredDialogIds": ["dlg_testm1_2", "dlg_testm1_1"],
            "selectionOrderStatus": (
                "one_based_active_row_selection_only_no_cross_row_chronology"
            ),
            "serverExchange": True,
            "clientRequest": False,
            "expectedClientReply": False,
            "serverFields": ["proxyNumId", "activeCondIndex"],
            "upstreamServerStateSources": ["SC_NPC_ACTIVE_CHANGE_NTF"],
        }

        route = pipeline.build_story_trigger_route(row, mission_id="testm1")

        self.assertEqual(route["causality"], "dependency")
        self.assertEqual(route["npcProxyId"], "proxy_a")
        self.assertEqual(route["activeRowIndex"], 2)
        self.assertEqual(
            route["candidateQuestIds"],
            ["testm1_q#4", "testm1_q#12"],
        )
        self.assertEqual(
            route["configuredDialogIds"],
            ["dlg_testm1_2", "dlg_testm1_1"],
        )
        self.assertEqual(
            route["upstreamServerStateSources"],
            ["SC_NPC_ACTIVE_CHANGE_NTF"],
        )
        self.assertIs(route["clientRequest"], False)

    def test_trigger_route_preserves_definition_only_horn_context(self):
        row = {
            "key": "dlg_testm1_11",
            "relation": "leveldata_interactive_narrative_config",
            "direction": "context",
            "levelDataAssets": ["map_test_lv_data_sub_testm1"],
            "entityLogicId": 10003,
            "interactiveRecordIndex": 2,
            "narrativeConsumerKind": "horn_dialog_property",
            "dialogDefinitionOnly": True,
            "dialogDefinitionBinding": True,
            "dialogDefinitionConsumerMission": "testm1",
            "dialogDefinitionConsumerQuestId": "testm1_q#3",
            "dialogIdEntryOffset": 2800,
            "interactiveHornNativeMappingId":
                "gameassembly-test-interactive-horn-dialog-v1",
            "progressLockConditionStatus": "decoded",
            "progressLockConditionType":
                "SimpleConditionCheckQuestState",
            "progressLockConditions": [{
                "conditionType": "SimpleConditionCheckQuestState",
                "ownerKind": "quest",
                "ownerId": "testm1_q#2",
                "compareOperator": 0,
                "compareTarget": 3,
            }],
            "rawTypeId": "dlg_testm1_11",
            "entityDetailIds": ["int_horn"],
            "entityTemplateIds": ["int_horn"],
        }

        route = pipeline.build_story_trigger_route(
            row,
            mission_id="testm1",
            quest_id="testm1_q#3",
            scope="quest",
        )

        self.assertEqual(
            [step["kind"] for step in route["steps"]],
            [
                "quest",
                "leveldata",
                "availability_condition",
                "narrative_interactive",
                "dialog_definition",
            ],
        )
        self.assertTrue(route["dialogDefinitionOnly"])
        self.assertEqual(
            "testm1_q#3",
            route["dialogDefinitionConsumerQuestId"],
        )
        self.assertEqual(
            "testm1_q#2",
            route["progressLockConditions"][0]["ownerId"],
        )

    def test_publish_source_story_partial_order_embeds_lazy_mission_graph(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "mission_pipeline"
            mission_root = output_root / "missions"
            story_root = root / "lang"
            mission_root.mkdir(parents=True)
            (story_root / "CN").mkdir(parents=True)
            (story_root / "CN" / "index.json").write_text("{}", encoding="utf-8")
            pipeline.write_json(mission_root / "testm1.json", {"mission": {"id": "testm1"}})
            index = {
                "missions": [{"id": "testm1", "file": "missions/testm1.json"}],
            }
            order_row = {
                "mission": "testm1",
                "summary": {
                    "sceneCount": 2,
                    "strongEdgeCount": 1,
                    "cycleCount": 0,
                    "questForkCount": 1,
                    "questMergeCount": 1,
                },
                "nodes": [{"key": "dlg_testm1_1"}, {"key": "dlg_testm1_2"}],
                "reducedComponentEdges": [{"from": "p1", "to": "p2"}],
            }
            report = {
                "_schema": "sourceStoryPartialOrder.v5",
                "language": "CN",
                "summary": {"strongEdges": 1, "questForks": 1, "questMerges": 1},
                "evidencePolicy": {"rejects": ["numeric filename suffixes"]},
                "missions": [order_row],
            }
            report_root = root / "reports"
            with patch.object(
                pipeline,
                "build_source_story_partial_order_report",
                return_value=report,
            ), patch.object(
                pipeline,
                "render_source_story_partial_order_markdown",
                return_value="# fixture\n",
            ):
                result = pipeline.publish_source_story_partial_order(
                    index,
                    output_root,
                    story_root,
                    "CN",
                    report_root,
                )

            self.assertIs(result, report)
            mission_payload = json.loads((mission_root / "testm1.json").read_text(encoding="utf-8"))
            self.assertEqual(mission_payload["storyOrder"], order_row)
            self.assertEqual(index["missions"][0]["storyOrderStrongEdgeCount"], 1)
            self.assertEqual(index["storyOrder"]["schema"], "sourceStoryPartialOrder.v5")

    def test_publish_quest_objective_story_scope_is_exact_non_owning_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "mission_pipeline"
            mission_root = output_root / "missions"
            flow_root = root / "lang" / "CN" / "mission"
            report_root = root / "reports"
            mission_root.mkdir(parents=True)
            flow_root.mkdir(parents=True)
            pipeline.write_json(
                mission_root / "testm1.json",
                {
                    "mission": {"id": "testm1"},
                    "nodes": [
                        {
                            "id": "testm1_q1",
                            "objectives": [{"levelScriptIds": ["70000000001"]}],
                        },
                        {"id": "testm1_q2", "objectives": []},
                    ],
                },
            )
            pipeline.write_json(
                flow_root / "testm1.json",
                {
                    "flow": {
                        "quests": [
                            {"id": "testm1_q1", "storyConnections": []},
                            {"id": "testm1_q2", "storyConnections": []},
                        ],
                        "missionStoryConnections": [
                            {
                                "key": "radio_testm1_1",
                                "kind": "radio",
                                "relation": "levelscript_mission_context",
                                "scriptIds": ["70000000001"],
                                "questTriggerStatus": "mission_shell_only",
                            }
                        ],
                    }
                },
            )
            coverage_path = root / "coverage.json"
            pipeline.write_json(coverage_path, {"unlinked": []})
            index = {
                "missions": [{"id": "testm1", "file": "missions/testm1.json"}],
            }

            report = pipeline.publish_quest_objective_story_scope(
                index,
                output_root,
                root / "lang",
                "CN",
                coverage_path,
                report_root,
            )

            self.assertIsNotNone(report)
            payload = json.loads(
                (mission_root / "testm1.json").read_text(encoding="utf-8")
            )
            context = payload["nodes"][0]["storyScopeContexts"][0]
            self.assertEqual(context["key"], "radio_testm1_1")
            self.assertEqual(
                context["relation"],
                "quest_objective_levelscript_scope_context",
            )
            self.assertEqual(context["ownershipStatus"], "non_owning_context")
            self.assertFalse(context["playbackOwnership"])
            self.assertFalse(context["orderEvidence"])
            self.assertEqual(
                context["scopeDiscriminator"],
                "globally_unique_objective_script_owner",
            )
            self.assertNotIn("storyScopeContexts", payload["nodes"][1])
            self.assertEqual(
                index["nodeAttachmentCoverage"]["published"],
                {
                    "missions": 1,
                    "quests": 1,
                    "rows": 1,
                    "uniqueStoryKeys": 1,
                },
            )
            self.assertTrue((report_root / "node_attachment_coverage.json").is_file())

    def test_publish_runtime_trace_attaches_observation_without_promoting_ownership(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "mission_pipeline"
            mission_root = output_root / "missions"
            mission_root.mkdir(parents=True)
            pipeline.write_json(mission_root / "e11m1.json", {
                "mission": {"id": "e11m1"},
                "nodes": [{"id": "e11m1_q1"}, {"id": "e11m1_q2"}],
                "edges": [],
            })
            index = {
                "missions": [{"id": "e11m1", "file": "missions/e11m1.json"}],
            }
            observation = {
                "sessionId": "capture-1",
                "seq": 5,
                "monotonicMs": 50,
                "storyKey": "radio_e11m1_1",
                "playbackType": "radio",
                "chainId": "chain-1",
                "triggerStatus": "exact_event_action_chain",
                "ownershipStatus": "observed_active_quest_context",
                "activeMissions": [{"missionId": "e11m1", "state": "Processing"}],
                "activeQuests": [{
                    "missionId": "e11m1", "questId": "e11m1_q1", "state": "Processing",
                }],
                "route": [{"kind": "action_enter", "actionType": "PlayRadio"}],
            }
            bundle_path = root / "trace.json"
            pipeline.write_json(bundle_path, {
                "_schema": "missionRuntimeTrace.v1",
                "summary": {"storyPlaybacks": 1},
                "evidencePolicy": {"ownership": "observed context only"},
                "sessions": [{"id": "capture-1"}],
                "storyObservations": {"radio_e11m1_1": [observation]},
                "observedEdges": [],
                "observedForks": [],
                "observedMerges": [],
            })

            pipeline.publish_mission_runtime_trace(index, output_root, bundle_path)

            payload = json.loads((mission_root / "e11m1.json").read_text(encoding="utf-8"))
            attached = payload["nodes"][0]["runtimeStoryObservations"]
            self.assertEqual(attached[0]["storyKey"], "radio_e11m1_1")
            self.assertNotIn("runtimeStoryObservations", payload["nodes"][1])
            self.assertFalse(payload["runtimeTrace"]["ownershipPromotion"])
            self.assertFalse(payload["runtimeTrace"]["orderPromotion"])
            self.assertEqual(payload["edges"], [])
            self.assertEqual(index["runtimeTrace"]["published"]["questObservationPlacements"], 1)

    def test_definition_only_consumer_classification_is_negative_and_audio_aware(self):
        with tempfile.TemporaryDirectory() as temporary:
            text_vo_table = Path(temporary) / "TextVoIdTable.json"
            text_vo_table.write_text(json.dumps({
                "black_audio_1_001": "au_black_audio_1_001",
                "black_audio_1_002": "",
                "black_empty_1_001": "",
            }), encoding="utf-8")

            result = pipeline.classify_definition_only_current_build_consumers(
                ["black_audio_1", "black_empty_1", "black_missing_1"],
                text_vo_table,
            )

            self.assertEqual(result["source"]["status"], "loaded")
            self.assertEqual(result["source"]["tableRows"], 3)
            self.assertEqual(result["counts"], {
                "explicit_empty_audio_metadata_likely_legacy_definition": 1,
                "no_audio_metadata_or_playback_consumer_recovered": 1,
                "original_audio_metadata_without_playback_consumer": 1,
            })
            records = {row["key"]: row for row in result["records"]}
            self.assertEqual(
                records["black_audio_1"]["voiceIds"],
                ["au_black_audio_1_001"],
            )
            self.assertFalse(records["black_audio_1"]["likelyLegacy"])
            self.assertTrue(records["black_empty_1"]["likelyLegacy"])
            self.assertIsNone(records["black_missing_1"]["likelyLegacy"])
            self.assertTrue(all(not row["storyBinding"] for row in records.values()))
            self.assertTrue(all(not row["missionOwnershipEvidence"] for row in records.values()))

    def test_main_publishes_exact_runtime_receiver_nodes_to_webui_index(self):
        args = type("Args", (), {
            "output_root": pipeline.ROOT / "tmp" / "mission_pipeline_fixture",
            "mission_root": pipeline.ROOT / "fixture_missions",
            "subgame_table": pipeline.ROOT / "fixture_subgames.json",
            "story_data_root": pipeline.ROOT / "fixture_story",
            "story_language": "CN",
            "report_root": pipeline.ROOT / "reports" / "story" / "build",
            "activity_stage_table": pipeline.ROOT / "fixture_activity.json",
            "game_mechanic_condition_table": pipeline.ROOT / "fixture_conditions.json",
            "dungeon_table": pipeline.ROOT / "fixture_dungeons.json",
        })()
        index = {"counts": {"missions": 1, "quests": 1}}
        receiver = {
            "eventName": "LevelEvent_OnBattleSignal",
            "selector": {"listenerScriptId": "70000000001", "signalId": "fixture"},
            "storyFiles": [{"key": "radio_testm1_1"}],
        }
        coverage = {
            "language": "CN",
            "policy": "original data only",
            "counts": {"connectedUniqueStoryFiles": 1, "unlinkedUniqueStoryFiles": 0},
            "nativePlaybackEventFamilies": {"LevelEvent_OnBattleSignal": 1},
            "storyTriggerManifest": {"radio_testm1_1": {"routes": []}},
            "missionlessSubGamePlaybackNodes": [],
            "missionlessNativeRuntimeNodes": [receiver],
        }
        writes = []
        with patch.object(pipeline, "parse_args", return_value=args), \
             patch.object(pipeline, "build_all", return_value=index), \
             patch.object(pipeline, "build_story_binding_coverage", return_value=coverage), \
             patch.object(pipeline, "write_json", side_effect=lambda path, data: writes.append((path, data))):
            self.assertEqual(pipeline.main(), 0)
        self.assertEqual(writes[-1][1]["storyCoverage"]["missionlessNativeRuntimeNodes"], [receiver])
        self.assertIn("radio_testm1_1", writes[-1][1]["storyCoverage"]["storyTriggerManifest"])

    def test_exact_native_runtime_selector_keeps_filterless_receiver_identity(self):
        selector = pipeline.exact_native_runtime_selector(
            "LevelEvent_OnSquadInFightChanged",
            {
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "serverExchange": False,
            },
            level_id="map_fixture",
            script_id="70000000001",
            header_local_id=36,
        )
        self.assertEqual(selector, {
            "levelId": "map_fixture",
            "listenerScriptId": "70000000001",
            "listenerHeaderLocalId": 36,
        })

    def test_native_receiver_gate_formats_exact_generic_predicate(self):
        validation = {
            "status": "exact_current_build_memorypack_fields",
            "headerLocalId": 101,
            "headerNextLocalId": 102,
            "getterLocalId": 100,
            "predicateType": "booleanCompare",
            "predicate": {
                "comparerName": "Equal",
                "valueA": {
                    "value": False,
                    "idRef": -1,
                    "paramSource": 300,
                    "path": "radio_fixturePlayed",
                },
                "valueB": {
                    "value": False,
                    "idRef": -1,
                    "paramSource": 0,
                    "path": None,
                },
            },
        }
        with patch.object(
            pipeline,
            "decode_levelscript_action_header_validation",
            return_value=validation,
        ):
            gate = pipeline.exact_native_receiver_playback_gate(
                b"fixture",
                101,
                source_file="fixture/levelscript.json",
            )
        self.assertEqual("radio_fixturePlayed == false", gate["summary"])
        self.assertEqual(
            "receiver_playback_allowed_when_true",
            gate["effect"],
        )
        self.assertTrue(gate["branchEvidence"])
        self.assertFalse(gate["crossStoryOrderEvidence"])
        self.assertFalse(gate["serverWriteEvidence"])

    def test_native_receiver_gate_rejects_unproven_getter_family(self):
        with patch.object(
            pipeline,
            "decode_levelscript_action_header_validation",
            return_value={},
        ):
            self.assertEqual(
                {},
                pipeline.exact_native_receiver_playback_gate(
                    b"fixture",
                    9,
                    source_file="fixture/levelscript.json",
                ),
            )

    def test_native_receiver_post_playback_control_is_identity_agnostic(self):
        owner = {
            "status": "exact_serialized_control_path",
            "downstreamControlStatus": "exact_serialized_typed_reachability",
            "downstreamControlPaths": [
                [{
                    "edge": "ActionBase.nextId",
                    "localId": 5,
                    "actionName": "Split",
                }],
                [
                    {
                        "edge": "ActionBase.nextId",
                        "localId": 5,
                        "actionName": "Split",
                    },
                    {
                        "edge": "Split.actions[0]",
                        "localId": 6,
                        "actionName": "CallServer",
                        "recordClass": "server_handoff",
                        "texts": ["#callback_a", "event_args"],
                    },
                ],
                [
                    {
                        "edge": "ActionBase.nextId",
                        "localId": 5,
                        "actionName": "Split",
                    },
                    {
                        "edge": "Split.actions[1]",
                        "localId": 7,
                        "actionName": "WaitForSeconds",
                    },
                ],
            ],
        }
        control = pipeline.exact_native_receiver_post_playback_control(
            owner,
            story_key="story_fixture",
            playback_local_id=4,
            source_file="fixture/levelscript.json",
        )
        self.assertEqual("exactNativePostPlaybackControl.v1", control["schema"])
        self.assertEqual([5], control["branchPointLocalIds"])
        self.assertEqual(2, len(control["maximalReachablePaths"]))
        self.assertEqual(
            ["#callback_a"],
            control["serverHandoffs"][0]["callbackCorrelationLabels"],
        )
        self.assertFalse(control["missionOwnershipEvidence"])
        self.assertFalse(control["serverHandlerIdentityEvidence"])

    def test_native_receiver_post_playback_control_fails_closed(self):
        self.assertEqual(
            {},
            pipeline.exact_native_receiver_post_playback_control(
                {"status": "text_scan_only", "downstreamControlPaths": []},
                story_key="story_fixture",
                playback_local_id=4,
                source_file="fixture/levelscript.json",
            ),
        )

    def test_level_sequence_action_name_comes_from_binary_formatter_mapping(self):
        self.assertEqual(
            "LoadLevelSequenceAction",
            level_bindings.LEVELSCRIPT_NATIVE_ACTION_NAMES[(0x02FA, 0x09)],
        )

    def test_actionbase_formatter_loader_recovers_every_tag_and_fails_closed(self):
        rows = [
            {
                "tag": tag,
                "tagHex": f"0x{tag:04x}",
                "actionName": f"GenericAction{tag}",
            }
            for tag in range(1313)
        ]
        payload = {
            "metadata": {
                "gameAssemblySha256":
                    level_bindings.ACTIONBASE_FORMATTER_GAMEASSEMBLY_SHA256,
                "metadataSha256":
                    level_bindings.ACTIONBASE_FORMATTER_METADATA_SHA256,
                "codeRegistration": "0x18b9217d0",
            },
            "targetMethod": {
                "typeToken": "0x02000c1c",
                "methodToken": "0x0600488f",
                "methodPointerVa": "0x183998700",
            },
            "summary": {
                "tagCount": 1313,
                "minTag": 0,
                "maxTag": 1312,
                "duplicateTagCount": 0,
                "missingTagCountInsideRange": 0,
                "unknownInstructionCount": 0,
            },
            "actionNames": [row["actionName"] for row in rows],
        }
        with tempfile.TemporaryDirectory() as temporary:
            valid_path = Path(temporary) / "valid.json"
            valid_path.write_text(json.dumps(payload), encoding="utf-8")
            names, audit = level_bindings.load_actionbase_formatter_names(
                valid_path
            )
            payload["actionNames"][42] = ""
            invalid_path = Path(temporary) / "invalid.json"
            invalid_path.write_text(json.dumps(payload), encoding="utf-8")
            invalid_names, invalid_audit = (
                level_bindings.load_actionbase_formatter_names(invalid_path)
            )

        self.assertEqual(1313, len(names))
        self.assertEqual("GenericAction42", names[42])
        self.assertEqual("validated", audit["status"])
        self.assertEqual({}, invalid_names)
        self.assertEqual("validation_failed", invalid_audit["status"])
        self.assertEqual(
            "nonempty_action_name",
            invalid_audit["validationFailures"][0]["gate"],
        )

    def test_post_playback_action_name_audit_keeps_outside_union_raw(self):
        nodes = [{
            "postPlaybackControls": [{
                "sourceFile": "fixture.bin",
                "storyKey": "story_fixture",
                "actions": [{
                    "localId": 1,
                    "opcode": "0x0a10/0x00",
                    "unionTag": "0x0010",
                    "serializedMemberCount": 10,
                    "actionName": "GenericAction",
                }, {
                    "localId": 2,
                    "opcode": "0x1000/0x00",
                    "unionTag": "",
                    "serializedMemberCount": 0,
                    "actionName": "",
                }],
            }],
        }]
        audit = pipeline.build_post_playback_action_name_audit(
            nodes,
            formatter_names={0x0010: "GenericAction"},
            formatter_audit={
                "status": "validated",
                "validationFailures": [],
            },
        )

        self.assertEqual(
            "validated_actionbase_complete_outside_families_retained",
            audit["status"],
        )
        self.assertEqual(1, audit["summary"]["formatterNamedActionPlacements"])
        self.assertEqual(
            1,
            audit["summary"]["unresolvedOutsideActionBasePlacements"],
        )
        self.assertEqual(
            [{"opcode": "0x1000/0x00", "count": 1}],
            audit["unresolvedActionShapes"],
        )
        self.assertFalse(audit["missionOwnershipEvidence"])

    def test_level_sequence_textasset_index_requires_three_way_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_payload = {
                "cutsceneName": "levelseq_fixture_valid",
                "path": "fixture/path",
                "version": 3,
                "targetFrameRate": 30,
            }
            (root / "levelseq_fixture_valid_pABCD.json").write_text(
                json.dumps({
                    "m_Name": "levelseq_fixture_valid",
                    "Name": "levelseq_fixture_valid",
                    "m_Script": base64.b64encode(
                        json.dumps(valid_payload).encode("utf-8")
                    ).decode("ascii"),
                }),
                encoding="utf-8",
            )
            invalid_payload = {"cutsceneName": "levelseq_other"}
            (root / "levelseq_fixture_invalid_p1234.json").write_text(
                json.dumps({
                    "m_Name": "levelseq_fixture_invalid",
                    "Name": "levelseq_fixture_invalid",
                    "m_Script": base64.b64encode(
                        json.dumps(invalid_payload).encode("utf-8")
                    ).decode("ascii"),
                }),
                encoding="utf-8",
            )

            index = pipeline.build_level_sequence_textasset_index(root)

        self.assertEqual("degraded_fail_closed", index["status"])
        self.assertEqual(
            ["levelseq_fixture_valid"],
            list(index["assetsById"]),
        )
        self.assertEqual(
            "exact_m_name_name_cutscene_name_match",
            index["assetsById"]["levelseq_fixture_valid"]["identityStatus"],
        )
        self.assertEqual(1, index["summary"]["validationFailures"])
        self.assertEqual(
            "m_Name_equals_Name_equals_decoded_cutsceneName",
            index["validationFailures"][0]["gate"],
        )

    def test_level_sequence_asset_join_is_type_and_identity_driven(self):
        nodes = [{
            "postPlaybackControls": [{
                "actions": [{
                    "localId": 5,
                    "actionName": "LoadLevelSequenceAction",
                    "texts": ["levelseq_fixture"],
                }, {
                    "localId": 6,
                    "actionName": "SetString",
                    "texts": ["levelseq_fixture"],
                }, {
                    "localId": 7,
                    "actionName": "StopLevelSequenceAction",
                    "texts": ["levelseq_missing"],
                }],
            }],
        }]
        index = {
            "schema": "exactLevelSequenceTextAssetIndex.v1",
            "root": "fixture",
            "status": "exact_complete",
            "summary": {},
            "validationFailures": [],
            "ambiguousLevelSequenceIds": [],
            "assetsById": {
                "levelseq_fixture": {
                    "levelSequenceId": "levelseq_fixture",
                    "sourceFile": "export/fixture.json",
                    "identityStatus": "exact_m_name_name_cutscene_name_match",
                },
            },
        }

        audit = pipeline.attach_exact_level_sequence_assets(nodes, index)

        actions = nodes[0]["postPlaybackControls"][0]["actions"]
        self.assertEqual(
            "export/fixture.json",
            actions[0]["levelSequenceReferences"][0]["sourceFile"],
        )
        self.assertNotIn("levelSequenceReferences", actions[1])
        self.assertEqual(
            "no_exact_validated_textasset",
            actions[2]["levelSequenceReferences"][0]["identityStatus"],
        )
        self.assertEqual(2, audit["summary"]["typedActionPlacements"])
        self.assertEqual(1, audit["summary"]["exactResolvedLevelSequenceIds"])
        self.assertEqual(["levelseq_missing"], audit["unresolvedLevelSequenceIds"])
        self.assertFalse(audit["missionOwnershipEvidence"])
        self.assertFalse(audit["crossStoryOrderEvidence"])

    def test_post_playback_variable_bridge_is_generic_and_non_promoting(self):
        exact_owner = {
            "status": "exact_serialized_control_path",
            "headerName": "ScriptEvent_OnPropertyChanged",
            "headerLocalId": 2,
            "eventDetail": {
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "propertyKeyFilter": "other_key",
            },
            "downstreamControlStatus": "exact_serialized_typed_reachability",
            "downstreamControlPaths": [[{
                "edge": "ActionBase.nextId",
                "localId": 5,
                "actionName": "SetBool",
                "texts": ["shared_key"],
            }]],
        }
        listener_owner = {
            "status": "exact_serialized_control_path",
            "headerName": "ScriptEvent_OnBlackboardValueChanged",
            "headerLocalId": 7,
            "eventDetail": {
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "blackboardKeyFilter": "shared_key",
            },
        }
        native_index = {
            "story_setter": [{
                "levelId": "map_fixture",
                "scriptId": "1001",
                "sourceFile": "export_full/LevelScriptData/map_fixture/1001.bin",
                "localId": 4,
                "nativeEventOwners": [exact_owner],
            }],
            "story_listener": [{
                "levelId": "map_fixture",
                "scriptId": "1001",
                "sourceFile": "export_full/LevelScriptData/map_fixture/1001.bin",
                "localId": 8,
                "nativeEventOwners": [listener_owner],
            }],
        }

        audit = pipeline.build_post_playback_variable_bridge_audit(native_index)

        self.assertEqual(
            "context_only_execute_notification_family_unproven",
            audit["status"],
        )
        self.assertEqual(1, audit["summary"]["postPlaybackVariableSetters"])
        self.assertEqual(1, audit["summary"]["exactSetterListenerMatches"])
        self.assertEqual(1, audit["summary"]["crossStorySetterListenerMatches"])
        self.assertEqual(
            "story_listener",
            audit["setters"][0]["exactListenerMatches"][0]["storyKey"],
        )
        self.assertFalse(audit["setters"][0]["orderEvidence"])
        self.assertFalse(audit["setters"][0]["missionOwnershipEvidence"])
        self.assertFalse(audit["usesOcrOrManualOrder"])

    def test_post_playback_variable_bridge_closes_zero_overlap(self):
        audit = pipeline.build_post_playback_variable_bridge_audit({})

        self.assertEqual("closed_no_exact_same_script_key_match", audit["status"])
        self.assertEqual(0, audit["summary"]["exactSetterListenerMatches"])

    def test_native_receiver_gate_formats_recursive_boolean_tree(self):
        leaf = {
            "predicateType": "getterBool",
            "predicate": {
                "value": {
                    "value": False,
                    "idRef": -1,
                    "paramSource": 300,
                    "path": "isFinished",
                },
            },
            "children": [],
        }
        validation = {
            "status": "exact_current_build_memorypack_fields",
            "headerLocalId": 2,
            "headerNextLocalId": 3,
            "getterLocalId": 1,
            "predicateType": "boolGetterInvert",
            "predicate": {
                "operation": "Not",
                "value": {
                    "operandKind": "localGetterRef",
                    "getterLocalId": 0,
                },
            },
            "predicateTree": {
                "predicateType": "boolGetterInvert",
                "predicate": {
                    "operation": "Not",
                    "value": {
                        "operandKind": "localGetterRef",
                        "getterLocalId": 0,
                    },
                },
                "children": [{
                    "path": "value.getterLocalId",
                    "getterLocalId": 0,
                    "predicate": leaf,
                }],
            },
        }
        with patch.object(
            pipeline,
            "decode_levelscript_action_header_validation",
            return_value=validation,
        ):
            gate = pipeline.exact_native_receiver_playback_gate(
                b"fixture",
                2,
                source_file="fixture/levelscript.json",
            )
        self.assertEqual("NOT (isFinished)", gate["summary"])
        self.assertEqual(2, gate["predicateNodeCount"])
        self.assertEqual(2, gate["predicateDepth"])

    def test_battle_signal_producer_route_revalidates_every_binary_identity(self):
        route = {
            "relation": "ability_battle_signal_local_causality",
            "storyKey": "radio_testm1_1",
            "actionType": "Core_SendBattleSignalToLevel_Data",
            "actionUnionTag": "0x0134",
            "serializedMemberCount": 6,
            "producerMappingId": pipeline.BATTLE_SIGNAL_PRODUCER_MAPPING_ID,
            "producerDomain": "SkillData",
            "producerAssetId": "skill_fixture",
            "producerSourceFile": "fixture/skill_fixture.json",
            "actionOffset": "0x20",
            "prefix": {"isEnable": True},
            "signalId": {
                "memberCount": 3,
                "useBlackboardKey": False,
                "value": "fixture_signal",
            },
            "doubleValue": {
                "memberCount": 3,
                "useBlackboardKey": False,
                "value": 1.0,
            },
            "receiverSignalId": "fixture_signal",
            "listenerLevelId": "map_test",
            "listenerScriptId": "70000000001",
            "listenerHeaderLocalId": 9,
            "listenerSourceFile": "fixture/70000000001.json",
            "receiverMappingId": pipeline.BATTLE_SIGNAL_RECEIVER_MAPPING_ID,
            "receiverPayloadMappingId": pipeline.BATTLE_SIGNAL_PAYLOAD_MAPPING_ID,
            "executionSide": "client",
            "transport": "local-level-runtime-event",
            "serverExchange": False,
            "clientRequest": False,
            "expectedServerReturn": False,
            "missionOwnerStatus": "unresolved",
            "storyBinding": False,
        }
        kwargs = {
            "story_key": "radio_testm1_1",
            "signal_id": "fixture_signal",
            "level_id": "map_test",
            "script_id": "70000000001",
            "header_local_id": 9,
            "source_file": "fixture/70000000001.json",
        }
        self.assertTrue(
            pipeline.is_exact_battle_signal_producer_route(route, **kwargs)
        )
        for field, invalid in (
            ("actionUnionTag", "0x011f"),
            ("serializedMemberCount", 5),
            ("producerMappingId", "stale"),
            ("listenerScriptId", "70000000002"),
            ("receiverPayloadMappingId", "stale"),
            ("serverExchange", True),
            ("storyBinding", True),
        ):
            rejected = {**route, field: invalid}
            self.assertFalse(
                pipeline.is_exact_battle_signal_producer_route(
                    rejected,
                    **kwargs,
                ),
                field,
            )
        dynamic_signal = {
            **route,
            "signalId": {
                **route["signalId"],
                "useBlackboardKey": True,
            },
        }
        self.assertFalse(
            pipeline.is_exact_battle_signal_producer_route(
                dynamic_signal,
                **kwargs,
            )
        )

    def test_guide_completion_condition_retains_authored_group_and_mode(self):
        row = pipeline.condition_tree(condition(
            "CheckGuideGroupComplete",
            _guideGroupId={"constValue": "guide_group_team"},
            _completeType=2,
        ))
        self.assertEqual("CheckGuideGroupComplete", row["type"])
        self.assertEqual("guide_group_team", row["facts"]["guideGroupId"])
        self.assertEqual(2, row["facts"]["completeType"])

    def test_interactive_int_condition_retains_generic_entity_comparison(self):
        row = pipeline.condition_tree(condition(
            "InteractiveCheckInt",
            _levelId={"constValue": "map_fixture"},
            _entityId={"constValue": {"logicId": 10100360003}},
            _key={"constValue": "state"},
            _compareValue={"constValue": 1},
            _comparer={"constValue": 0},
        ))
        self.assertEqual(row, {
            "type": "InteractiveCheckInt",
            "facts": {
                "levelId": "map_fixture",
                "entityId": {"logicId": 10100360003},
                "key": "state",
                "compareValue": 1,
                "comparer": 0,
            },
        })

    def test_objective_retains_tracking_filter_without_creating_condition_edge(self):
        row = pipeline.objective_row({
            "description": {"key": "objective_tracking"},
            "condition": condition("GameConditionServerPlaceHolder"),
            "trackingInfoList": [{
                "$type": (
                    "Beyond.Gameplay.PosTrackingInfo, Gameplay.Beyond"
                ),
                "sceneId": "map_fixture",
                "useFilterCondition": True,
                "filterCondition": {
                    "$type": (
                        "Beyond.Gameplay.SimpleConditionCheckMissionVariableInt, "
                        "Gameplay.Beyond"
                    ),
                    "missionId": "testm1",
                    "missionVarName": "track_1",
                    "compareOperator": 0,
                    "compareTarget": 1,
                },
                "trackingPos": {"x": 1, "y": 2, "z": 3},
            }],
        }, 1)
        self.assertEqual(row["tracking"], [{
            "index": 0,
            "type": "PosTrackingInfo",
            "sceneId": "map_fixture",
            "useFilterCondition": True,
            "trackingPos": {"x": 1.0, "y": 2.0, "z": 3.0},
            "filterCondition": {
                "type": "SimpleConditionCheckMissionVariableInt",
                "facts": {
                    "compareTarget": 1,
                    "missionId": "testm1",
                    "missionVarName": "track_1",
                    "compareOperator": 0,
                },
            },
        }])
        self.assertEqual(row["questStateRefs"], [])

    def test_build_mission_retains_property_defaults_without_writer_claim(self):
        fixture = self.fixture()
        fixture["properties"] = [{
            "key": "track_1",
            "value": {
                "type": 3,
                "valueArray": [{
                    "valueBit64": 1,
                    "valueString": "",
                }],
            },
        }]
        payload, _ = pipeline.build_mission(
            fixture,
            pipeline.ROOT / "fixture" / "testm1.json",
        )
        self.assertEqual(payload["mission"]["properties"], [{
            "key": "track_1",
            "type": 3,
            "values": [{
                "valueBit64": 1,
                "valueString": "",
            }],
        }])

    def fixture(self):
        return {
            "missionId": "testm1",
            "missionName": {"key": "testm1_name"},
            "missionDescription": {"key": "testm1_desc"},
            "levelId": "map_test",
            "mainPathQuests": ["testm1_q#1", "testm1_q#2"],
            "questDic": {
                "testm1_q#1": {
                    "questId": "testm1_q#1",
                    "flowIndex": 0,
                    "showMode": 1,
                    "prevQuestIdList": [],
                    "objectiveList": [{
                        "description": {"key": "objective_1"},
                        "condition": condition("ReachDestination", _areaId={"constValue": "area"}),
                    }],
                },
                "testm1_q#2": {
                    "questId": "testm1_q#2",
                    "flowIndex": 1,
                    "showMode": 1000,
                    "prevQuestIdList": ["testm1_q#1"],
                    "objectiveList": [{
                        "description": {"key": "objective_2"},
                        "condition": condition(
                            "CheckTalkOptionFinish",
                            _dialogId={"constValue": "dlg_test"},
                            _finishId={"constValue": 0},
                        ),
                    }],
                },
                "testm1_q#3": {
                    "questId": "testm1_q#3",
                    "flowIndex": 0,
                    "showMode": 1,
                    "prevQuestIdList": ["testm1_q#1"],
                    "objectiveList": [{
                        "description": {"key": "objective_3"},
                        "condition": condition(
                            "CombineCondition",
                            conditionEvalString="{0}and{1}",
                            subConditions=[
                                condition("CheckQuestState", _questId={"constValue": "testm1_q#1"}, _targetQuestState={"constValue": 3}),
                                condition("CheckQuestState", _questId={"constValue": "testm1_q#2"}, _targetQuestState={"constValue": 3}),
                            ],
                        ),
                    }],
                },
            },
            "actionMapRaw": {
                "dataMap": {
                    "actionList": [{
                        "$type": "Beyond.Gameplay.Actions.PlayRadio, Gameplay.Beyond",
                        "_ID": 7,
                        "_radioId": {"constValue": "radio_test"},
                        "_nextID": 8,
                    }, {
                        "$type": "Beyond.Gameplay.Actions.ShowLimitedGuide, Gameplay.Beyond",
                        "_ID": 8,
                        "_nextID": -1,
                    }],
                },
            },
            "clientActionMapKey": [{"questId": "testm1_q#2", "action": 2}],
            "clientActionMapValue": [7],
        }

    def test_build_mission_preserves_finish_zero_and_condition_dependencies(self):
        payload, summary = pipeline.build_mission(self.fixture(), pipeline.ROOT / "fixture" / "testm1.json")
        nodes = {row["id"]: row for row in payload["nodes"]}
        finish = nodes["testm1_q#2"]["objectives"][0]["dialogFinishes"][0]
        self.assertEqual(finish, {"dialogId": "dlg_test", "finishId": 0})
        self.assertEqual(nodes["testm1_q#1"]["network"]["outbound"], "objective_progress")
        self.assertEqual(nodes["testm1_q#2"]["network"]["outbound"], "dialog_finish")
        self.assertEqual(nodes["testm1_q#2"]["clientActions"][0]["triggerName"], "OnSucceedClientAction")
        self.assertEqual([row["chainIndex"] for row in nodes["testm1_q#2"]["clientActions"]], [0, 1])
        self.assertEqual(nodes["testm1_q#2"]["clientActions"][1]["type"], "ShowLimitedGuide")
        dependencies = [edge for edge in payload["edges"] if edge["type"] == "condition_dependency"]
        self.assertEqual({(edge["source"], edge["target"], edge["targetState"]) for edge in dependencies}, {
            ("testm1_q#1", "testm1_q#3", 3),
            ("testm1_q#2", "testm1_q#3", 3),
        })
        self.assertEqual(summary["activeJoinCount"], 1)
        self.assertEqual(summary["exactFinishCount"], 1)

    def test_objective_recovers_submit_item_requirement_and_co_gates(self):
        submit_condition = condition(
            "CheckQuestSubmitItem",
            _submissionId={"constValue": "submit_fixture"},
        )
        submit_condition["uniqueId"] = "submit_condition"
        dialog_condition = condition(
            "CheckTalkOptionFinish",
            _dialogId={"constValue": "dlg_fixture"},
            _finishId={"constValue": 1},
        )
        level_script_condition = condition(
            "CheckLevelScriptStageReachMax",
            levelId={"constValue": "map_fixture"},
            scriptId={"constValue": {"scriptId": 12345}},
        )
        level_script_condition["uniqueId"] = "script_condition"
        combined = condition(
            "CombineCondition",
            conditionEvalString="{0} and {1} and {2}",
            subConditions=[
                submit_condition,
                dialog_condition,
                level_script_condition,
            ],
        )
        previous_cache = pipeline._SUBMIT_ITEM_ROWS_CACHE
        pipeline._SUBMIT_ITEM_ROWS_CACHE = {
            "submit_fixture": {
                "submitId": "submit_fixture",
                "paramData": [{
                    "type": 1,
                    "paramList": [
                        {"valueStringList": ["item_fixture"]},
                        {"valueIntList": [2]},
                    ],
                }],
            },
        }
        try:
            row = pipeline.objective_row(
                {"description": {"key": "fixture"}, "condition": combined},
                1,
            )
        finally:
            pipeline._SUBMIT_ITEM_ROWS_CACHE = previous_cache

        self.assertEqual(row["condition"]["children"][0]["facts"]["submissionId"], "submit_fixture")
        self.assertEqual(row["submissionChecks"], [{
            "submissionId": "submit_fixture",
            "tableDefined": True,
            "requirementGroups": [{
                "index": 1,
                "type": 1,
                "items": [{"itemId": "item_fixture", "count": 2}],
            }],
            "conditionId": "submit_condition",
        }])
        self.assertEqual(row["submissionDialogCoGates"], [{
            "submissionId": "submit_fixture",
            "dialogId": "dlg_fixture",
            "finishId": 1,
            "combineConditionId": "id_CombineCondition",
            "relation": "same_authored_and_objective",
        }])
        self.assertEqual(row["submissionLevelScriptCoGates"], [{
            "submissionId": "submit_fixture",
            "levelId": "map_fixture",
            "scriptId": "12345",
            "conditionId": "script_condition",
            "combineConditionId": "id_CombineCondition",
            "relation": "same_authored_and_objective",
        }])

    def test_build_all_writes_lazy_index_and_mission_payload(self):
        self.maxDiff = None
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mission_root = root / "input"
            output_root = root / "output"
            mission_root.mkdir()
            (mission_root / "testm1.json").write_text(json.dumps(self.fixture()), encoding="utf-8")
            (mission_root / "testm1_meta.json").write_text("{}", encoding="utf-8")
            index = pipeline.build_all(mission_root, output_root)
            self.assertEqual(index["counts"], {
                "missions": 1,
                "quests": 3,
                "caseStudies": 0,
                "serverPlaceholderConditions": 0,
                "serverPlaceholderQuests": 0,
                "serverPlaceholderMissions": 0,
                "serverPlaceholderDistinctConditionIds": 0,
                "serverPlaceholderReusedConditionIds": 0,
                "serverPlaceholderRowsWithReusedConditionId": 0,
                "serverPlaceholderMaxConditionIdReuse": 0,
                "submitItemConditions": 0,
                "submitItemQuests": 0,
                "submitItemMissions": 0,
                "submitItemDialogCoGates": 0,
                "submitItemLevelScriptCoGates": 0,
                "nativeRuntimeBindings": 0,
                "nativeRuntimeBoundMissions": 0,
                "nativeRuntimeDistinctScriptIds": 0,
                "activityQuestLevelRows": 0,
                "activityQuestLevelQuests": 0,
                "activityQuestLevelMissions": 0,
                "trackingInfoRows": 0,
                "trackingObjectives": 0,
                "missionPropertyRows": 0,
                "missionsWithProperties": 0,
                # The fixture has one mission with no cross-mission state
                # condition and no envTalk consumer table, so both new lanes
                # are legitimately empty rather than absent.
                "missionGraphEdges": 0,
                "missionGraphPrecedenceEdges": 0,
                "missionGraphMissions": 0,
                "missionGraphInterleavings": 0,
                "envTalkQuestContextFiles": 0,
                "envTalkQuestContextMissions": 0,
                "envTalkStateContextFiles": 0,
                "envTalkStateContextMissions": 0,
            })
            self.assertTrue((output_root / "index.json").is_file())
            self.assertTrue((output_root / "missions" / "testm1.json").is_file())
            self.assertEqual(
                index["missionRuntimeSource"],
                {
                    "selectedRoot": mission_root.as_posix(),
                    "selection": "explicit_mission_root",
                },
            )
            self.assertEqual(index["runtimeContract"]["outbound"][1]["message"], "CS_UPDATE_QUEST_OBJECTIVE")
            payload = json.loads((output_root / "missions" / "testm1.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["missionGraph"], {"upstream": {}, "downstream": {}})
            self.assertEqual(payload["envTalkContext"], [])

    def test_activity_stage_tables_add_typed_quest_level_hosts_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mission_root = root / "input"
            output_root = root / "output"
            dungeon_table = root / "ActivityDungeonFightingStageTable.json"
            snapshot_table = root / "ActivitySnapShotStageTable.json"
            mission_root.mkdir()
            (mission_root / "testm1.json").write_text(
                json.dumps(self.fixture()),
                encoding="utf-8",
            )
            dungeon_table.write_text(json.dumps({
                "fight_stage": {
                    "questId": "testm1_q#1",
                    "levelId": "dung_fixture",
                },
            }), encoding="utf-8")
            snapshot_table.write_text(json.dumps({
                "snapshot_stage": {
                    "questId": "testm1_q#2",
                    "levelId": "map_fixture_lv001",
                },
            }), encoding="utf-8")

            index = pipeline.build_all(
                mission_root,
                output_root,
                None,
                dungeon_table,
                snapshot_table,
            )
            payload = json.loads(
                (output_root / "missions" / "testm1.json").read_text(
                    encoding="utf-8"
                )
            )
            nodes = {row["id"]: row for row in payload["nodes"]}
            self.assertEqual(
                nodes["testm1_q#1"]["activityStageHosts"][0]["levelId"],
                "dung_fixture",
            )
            self.assertEqual(
                nodes["testm1_q#2"]["activityStageHosts"][0]["levelId"],
                "map_fixture_lv001",
            )
            self.assertFalse(
                nodes["testm1_q#1"]["activityStageHosts"][0]["storyBinding"]
            )
            self.assertEqual(index["counts"]["activityQuestLevelRows"], 2)
            self.assertEqual(index["counts"]["activityQuestLevelQuests"], 2)
            self.assertEqual(index["counts"]["activityQuestLevelMissions"], 1)
            self.assertEqual(
                index["activityQuestLevelRegistry"]["storyBindingsAdded"],
                0,
            )

    def test_subgame_registry_adds_mission_shell_runtime_binding_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mission_root = root / "input"
            output_root = root / "output"
            table_path = root / "SubGameInstanceDataTable.json"
            mission_root.mkdir()
            (mission_root / "testm1.json").write_text(json.dumps(self.fixture()), encoding="utf-8")
            table_path.write_text(json.dumps({"dataTable": {
                "dung_test": {
                    "$type": "Beyond.Gameplay.Core.DungeonSubGameData, Gameplay.Beyond",
                    "id": "dung_test",
                    "subDataParentId": 12345000000,
                    "bindScriptId": 12345000001,
                    "dungeonMissionId": "testm1",
                    "modeId": "dungeon_test",
                    "modeType": 2,
                    "gameMechanicsType": 4,
                },
                "world_without_mission": {
                    "$type": "Beyond.Gameplay.Core.WorldChallengeSubGameData, Gameplay.Beyond",
                    "id": "world_without_mission",
                    "bindScriptId": 9000000001,
                },
            }}), encoding="utf-8")

            index = pipeline.build_all(mission_root, output_root, table_path)
            payload = json.loads((output_root / "missions" / "testm1.json").read_text(encoding="utf-8"))
            binding = payload["mission"]["nativeRuntimeBindings"][0]
            self.assertEqual(binding["subGameId"], "dung_test")
            self.assertEqual(binding["bindScriptId"], "12345000001")
            self.assertEqual(binding["dungeonMissionId"], "testm1")
            self.assertEqual(binding["relation"], "subgame_bind_script_runtime")
            self.assertFalse(binding["storyBinding"])
            self.assertEqual(binding["networkIdentity"]["authoredKeyField"], "gameId")
            self.assertEqual(binding["networkIdentity"]["authoredKeyValue"], "dung_test")
            self.assertEqual(binding["networkIdentity"]["startRequest"], "CS_GAME_MECHANICS_REQ_START")
            self.assertEqual(
                binding["networkIdentity"]["challengeCompletePush"],
                "SC_GAME_MECHANICS_SYNC_CHALLENGE_COMPLETE",
            )
            self.assertEqual(binding["networkIdentity"]["leavePush"], "SC_GAME_MECHANICS_SYNC_LEAVE_GAME_INST")
            self.assertEqual(index["counts"]["nativeRuntimeBindings"], 1)
            self.assertEqual(index["nativeRuntimeRegistry"]["rowCount"], 2)
            self.assertEqual(index["nativeRuntimeRegistry"]["rowsWithBindScriptId"], 2)
            self.assertEqual(index["nativeRuntimeRegistry"]["rowsWithDungeonMissionId"], 1)
            self.assertEqual(index["nativeRuntimeRegistry"]["storyBindingsAdded"], 0)
            self.assertEqual(
                index["nativeRuntimeRegistry"]["bindScriptNativeEvidence"]["serializedFieldOffset"],
                "0x50",
            )
            self.assertFalse(
                index["nativeRuntimeRegistry"]["bindScriptNativeEvidence"]["auditedOnStartConsumerFound"]
            )
            self.assertIn(
                "SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST.gameId",
                index["runtimeContract"]["subGameMissionRegistry"]["runtimeBoundary"],
            )

    def test_server_placeholder_counts_conditions_and_keeps_composite_identity(self):
        fixture = self.fixture()
        placeholders = []
        for index in range(3):
            row = condition(
                "GameConditionServerPlaceHolder",
                _comparer={"constValue": 0},
                _progressToCompare={"constValue": index + 1},
            )
            row["uniqueId"] = f"server_gate_{index + 1}"
            placeholders.append({"description": {"key": f"gate_{index + 1}"}, "condition": row})
        fixture["questDic"]["testm1_q#1"]["objectiveList"] = placeholders

        payload, summary = pipeline.build_mission(
            fixture,
            pipeline.ROOT / "fixture" / "testm1.json",
        )
        node = next(row for row in payload["nodes"] if row["id"] == "testm1_q#1")
        self.assertEqual(summary["serverPlaceholderCount"], 3)
        self.assertEqual(summary["serverPlaceholderQuestCount"], 1)
        self.assertEqual(node["network"]["outbound"], "server_owned")
        self.assertEqual(node["serverPlaceholderKeys"], [
            {"questId": "testm1_q#1", "conditionId": "server_gate_1"},
            {"questId": "testm1_q#1", "conditionId": "server_gate_2"},
            {"questId": "testm1_q#1", "conditionId": "server_gate_3"},
        ])
        self.assertEqual(
            [objective["serverPlaceholderConditionIds"] for objective in node["objectives"]],
            [["server_gate_1"], ["server_gate_2"], ["server_gate_3"]],
        )

    def test_server_placeholder_contract_excludes_client_progress_callback(self):
        contract = pipeline.RUNTIME_CONTRACT["serverPlaceholder"]
        self.assertEqual(contract["conditionTypeFallback"], 2147483647)
        self.assertEqual(contract["clientOnlyConditionType"], 9999)
        self.assertEqual(contract["identityFields"], ["questId", "conditionId"])
        self.assertIsNone(contract["outboundMessage"])
        self.assertIn("extraDetails", " ".join(contract["inboundFields"]))
        self.assertIn("does not send CS_UPDATE_QUEST_OBJECTIVE", contract["finding"])
        self.assertEqual(contract["installedPatch"]["signatureTargetCount"], 30)
        self.assertEqual(contract["installedPatch"]["matchedRelevantPatchIds"], [])
        self.assertEqual(contract["installedPatch"]["taskCompletionTargetMatches"], 0)
        self.assertEqual(contract["installedPatch"]["taskCompletionExplicitReferenceMatches"], 0)
        self.assertEqual(contract["installedPatch"]["receiverOwnershipTargetMatches"], 0)
        self.assertEqual(contract["installedPatch"]["receiverOwnershipExplicitReferenceMatches"], 0)
        self.assertEqual(contract["installedPatch"]["missionHudTargets"], 2)
        self.assertEqual(contract["installedPatch"]["dialogCinematicTargets"], 7)
        self.assertEqual(
            contract["installedPatch"]["sha256"],
            "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21",
        )

        objective_update = next(
            row for row in pipeline.RUNTIME_CONTRACT["inbound"]
            if row["id"] == "quest-objectives"
        )
        self.assertEqual(objective_update["messageId"], 116)
        self.assertIn("questObjectives[].extraDetails", objective_update["fields"])

        outbound = {
            row["id"]: row for row in pipeline.RUNTIME_CONTRACT["outbound"]
        }
        self.assertEqual(315, outbound["accept-mission"]["messageId"])
        self.assertIsNone(outbound["accept-mission"]["responseMessage"])
        self.assertEqual(
            "SC_MISSION_STATE_UPDATE (112)",
            outbound["accept-mission"]["expectedServerPush"],
        )
        self.assertEqual(
            [
                "SC_QUEST_OBJECTIVES_UPDATE (116)",
                "SC_QUEST_STATE_UPDATE (111)",
            ],
            outbound["objective-progress"]["expectedServerPushes"],
        )
        self.assertIsNone(outbound["dialog-finish"]["correlationId"])
        self.assertEqual(3, len(pipeline.RUNTIME_CONTRACT["protocolOnly"]))
        protocol_confidence = {
            row["id"]: row["confidence"]
            for row in pipeline.RUNTIME_CONTRACT["protocolOnly"]
        }
        self.assertEqual(
            "protocol_schema_only_sender_unconfirmed",
            protocol_confidence["fail-mission-capability"],
        )
        self.assertEqual(
            "native_fallback_sender_and_handler_absent",
            protocol_confidence["mission-event-capability"],
        )
        self.assertEqual(
            "native_fallback_sender_absent",
            protocol_confidence["mission-client-trigger-done-capability"],
        )
        native_rows = {
            row["id"]: row
            for direction in ("outbound", "inbound")
            for row in pipeline.RUNTIME_CONTRACT[direction]
        }
        self.assertEqual(
            ["sceneNumId", "scriptId", "taskId", "taskState"],
            native_rows["level-script-task-state"]["fields"],
        )
        self.assertIn(
            "no missionid or questid",
            native_rows["level-script-task-state"]["effect"].lower(),
        )
        self.assertEqual(
            "0x186fb0f9c -> 0x1873825c8 -> 0x183f54e20",
            native_rows["level-script-task-progress"]["address"],
        )
        self.assertEqual(
            "0x1842ba410 -> 0x1842b9140 -> 0x1842bad00",
            native_rows["level-script-task-progress-update"]["address"],
        )
        self.assertIn(
            "completion boolean",
            native_rows["level-script-task-progress-update"]["effect"],
        )
        self.assertEqual(
            "native_proven",
            native_rows["level-script-set-done"]["confidence"],
        )
        mission_event = native_rows["mission-client-event"]
        self.assertEqual(125, mission_event["messageId"])
        self.assertEqual(["missionId", "eventName"], mission_event["fields"])
        self.assertEqual(
            "0x1873bdf58 -> 0x184a428a0 -> 0x187bdfd38",
            mission_event["address"],
        )
        self.assertEqual(
            "no_current_aot_typed_subscriber",
            mission_event["typedConsumerStatus"],
        )
        self.assertIn(
            "does not target the serialized",
            mission_event["effect"],
        )
        self.assertIn(
            "complete current-build AOT table",
            mission_event["effect"],
        )
        trigger_done = next(
            row for row in pipeline.RUNTIME_CONTRACT["protocolOnly"]
            if row["id"] == "mission-client-trigger-done-capability"
        )
        self.assertIsNone(trigger_done["possibleServerPush"])
        self.assertIn("separate native inbound handler", trigger_done["effect"])

    def test_teleport_param_contract_rejects_unused_mission_script_carrier(self):
        contract = pipeline.RUNTIME_CONTRACT["teleportMissionScriptCarrier"]
        self.assertEqual(contract["type"], "Beyond.Gameplay.TeleportParam")
        self.assertEqual(contract["size"], "0x38")
        self.assertEqual(contract["layout"]["missionId"], "0x18")
        self.assertEqual(contract["layout"]["levelScriptId"], "0x20")
        self.assertEqual(contract["directCallerCensus"]["GameLevelLoader.OpenLevel"], 2)
        self.assertEqual(
            contract["directCallerCensus"]["GameLevelLoader.LoadAtPosInCurrentMap"],
            2,
        )
        self.assertIn("no audited producer co-populates", contract["producerFinding"])
        self.assertIn("No audited current consumer reads missionId", contract["consumerFinding"])
        self.assertEqual(contract["storyBindingsAdded"], 0)
        self.assertEqual(contract["confidence"], "native_proven_bounded")
        native = next(
            row
            for row in pipeline.RUNTIME_CONTRACT["nativeEvidence"]
            if row["symbol"] == "TeleportParam -> LoadingPipeline.LoadFinishStep"
        )
        self.assertIn("zero ownership or order edges", native["finding"])

    def test_level_script_ctx_token_is_bounded_round_trip_not_mission_carrier(self):
        audit = pipeline.RUNTIME_CONTRACT["levelScriptCtxTokenAudit"]
        self.assertEqual(audit["paramBlackboardKeySlot"], "0x18e2eef08")
        self.assertEqual(audit["directKeySlotReferences"], 4)
        self.assertEqual(len(audit["referencingMethods"]), 2)
        self.assertEqual(
            audit["reader"]["symbol"],
            "Beyond.Gameplay.Actions.CallServer.Execute",
        )
        self.assertIn("TryGetValue(netToken)", audit["reader"]["operation"])
        self.assertEqual(
            audit["outboundPath"][-1],
            "Proto.CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.set_CtxToken",
        )
        self.assertIn("round-trip/correlation lane", audit["finding"])
        self.assertEqual(audit["storyBindingsAdded"], 0)
        self.assertEqual(audit["confidence"], "native_proven_bounded")

        native = next(
            row
            for row in pipeline.RUNTIME_CONTRACT["nativeEvidence"]
            if row["symbol"]
            == "GameplayNetwork._Handle_SceneTriggerClientLevelScriptEvent"
        )
        self.assertIn("CallServer.Execute", native["finding"])
        self.assertIn("set_CtxToken", native["finding"])
        self.assertIn("round-trip/correlation context", native["finding"])

    def test_recursive_protobuf_census_closes_role_scene_snapshots(self):
        audit = pipeline.RUNTIME_CONTRACT["protobufIdentityCarrierAudit"]
        self.assertEqual(audit["coverage"]["protoTypeDefinitions"], 3743)
        self.assertEqual(audit["coverage"]["registryMessageTypes"], 983)
        self.assertEqual(audit["coverage"]["fieldBearingRegistryMessageTypes"], 936)
        self.assertEqual(audit["coverage"]["missionOrQuestMessageTypes"], 33)
        self.assertEqual(audit["coverage"]["levelScriptMessageTypes"], 29)
        self.assertEqual(audit["exactMissionScriptOrStoryCandidateCount"], 0)
        self.assertEqual(audit["weakMissionSceneCandidateCount"], 3)
        self.assertEqual(
            [row["classification"] for row in audit["weakCandidates"]],
            [
                "inactive_current_fallback_sender",
                "role_snapshot_position_correction",
                "role_snapshot_position_correction",
            ],
        )
        consumer = audit["roleSnapshotConsumer"]
        self.assertEqual(consumer["token"], "0x0600527b")
        self.assertEqual(consumer["fallbackPatchId"], "0x5ea7")
        self.assertIn("position", consumer["finding"])
        self.assertEqual(audit["installedPatch"]["matchedMethods"], 0)
        self.assertEqual(audit["storyBindingsAdded"], 0)
        self.assertEqual(audit["confidence"], "native_proven_bounded")

        inbound = {
            row["id"]: row for row in pipeline.RUNTIME_CONTRACT["inbound"]
        }
        self.assertIn(
            "CharacterPositionCorrection",
            inbound["mission-state"]["effect"],
        )
        self.assertIn(
            "adds no quest-to-scene or Story edge",
            inbound["quest-start"]["effect"],
        )
        native = next(
            row
            for row in pipeline.RUNTIME_CONTRACT["nativeEvidence"]
            if "CharacterPositionCorrection" in row["symbol"]
        )
        self.assertIn("zero mission/quest + LevelScript/Story", native["finding"])

    def test_mission_option_carrier_is_alternate_action_not_dialog_bridge(self):
        audit = pipeline.RUNTIME_CONTRACT["missionOptionCarrierAudit"]
        fields = {
            row["name"]: row
            for row in audit["managedCarrier"]["fields"]
        }
        self.assertEqual(fields["missionId"]["offset"], "0x68")
        self.assertEqual(fields["callDialogId"]["offset"], "0x70")
        self.assertEqual(
            audit["managedCarrier"]["handlerType"]["name"],
            "Mission",
        )
        consumer = audit["nativeConsumer"]
        self.assertEqual(consumer["token"], "0x0600fa1a")
        self.assertIn("then jump to end", consumer["callDialogBranch"])
        self.assertIn(
            "only when callDialogId is empty",
            consumer["missionBranch"],
        )
        search = audit["authoredInstanceSearch"]
        self.assertEqual(search["monoBehaviourRows"], 1325026)
        self.assertEqual(search["textAssets"], 8195)
        self.assertEqual(search["structuredJsonFiles"], 179925)
        self.assertEqual(search["installedLuaFiles"], 1291)
        self.assertEqual(search["matches"], 0)
        self.assertEqual(audit["installedPatch"]["matchedMethods"], 0)
        self.assertIn("mutually exclusive", audit["finding"])
        self.assertEqual(audit["storyBindingsAdded"], 0)
        self.assertEqual(
            audit["classification"],
            "schema_only_current_export_absent",
        )

    def test_mission_property_script_pointer_is_runtime_subscription_context(self):
        audit = pipeline.RUNTIME_CONTRACT["missionPropertyScriptPtrAudit"]
        layout = audit["managedLayout"]
        self.assertEqual(
            layout["MissionRuntimeAsset"]["properties"]["offset"],
            "0xe0",
        )
        self.assertEqual(
            layout["MissionRuntimeAsset"]["propertyDic"]["offset"],
            "0xf8",
        )
        self.assertEqual(
            layout["MissionSystem+MissionData"]["propertyDict"]["offset"],
            "0x20",
        )
        self.assertEqual(
            layout["ParamVariable"]["m_scriptPtr"]["offset"],
            "0x70",
        )
        authored = audit["authoredMissionProperties"]
        self.assertEqual(authored["missionFiles"], 490)
        self.assertEqual(authored["missionsWithProperties"], 71)
        self.assertEqual(authored["propertyRows"], 217)
        self.assertEqual(authored["levelScriptPointerFieldRows"], 0)
        tracking = audit["trackingPropertyFilterRuntime"]
        self.assertEqual(tracking["authoredRows"], 204)
        self.assertEqual(tracking["authoredMissions"], 46)
        self.assertEqual(tracking["authoredVariables"], 110)
        self.assertEqual(
            tracking["evaluator"]["token"],
            "0x06004b72",
        )
        self.assertEqual(
            tracking["serverUpdate"]["message"],
            "SC_UPDATE_MISSION_PROPERTY (124)",
        )
        self.assertEqual(tracking["storyBindingsAdded"], 0)
        self.assertEqual(tracking["missionOrderEdgesAdded"], 0)
        self.assertEqual(len(audit["missionPropertyWriters"]), 3)
        self.assertEqual(
            audit["directCallCensus"]["missionSystemScriptPointerSetterCalls"],
            0,
        )
        self.assertEqual(audit["installedPatch"]["matchedMethods"], 0)
        self.assertIn("not a mission-to-LevelScript", audit["finding"])
        self.assertEqual(audit["storyBindingsAdded"], 0)
        self.assertEqual(
            audit["classification"],
            "runtime_context_only_no_mission_levelscript_edge",
        )

    def test_current_mission_param_source_has_no_levelscript_story_use(self):
        audit = pipeline.RUNTIME_CONTRACT["paramSourceMissionContextAudit"]
        managed = audit["managedContract"]
        self.assertEqual(managed["currentMissionId"], 1004)
        self.assertEqual(managed["paramSourceFieldToken"], "0x04006c3d")
        self.assertEqual(managed["currentMissionGetterToken"], "0x060091d6")
        mission = audit["authoredMissionRuntime"]
        self.assertEqual(mission["missionFiles"], 490)
        self.assertEqual(mission["currentMissionIdOccurrences"], 18)
        self.assertEqual(mission["missions"], 6)
        self.assertEqual(mission["storyPlaybackOperands"], 0)
        self.assertEqual(
            mission["actionTypes"]["CheckMissionIntProperty"],
            17,
        )
        levelscript = audit["authoredLevelScripts"]
        self.assertEqual(levelscript["levelScriptFiles"], 4512)
        self.assertEqual(levelscript["uidRecords"], 74839)
        self.assertEqual(levelscript["rawCurrentMissionIdValues"], 0)
        self.assertEqual(levelscript["validatedParamTails"], 0)
        self.assertEqual(
            levelscript["embeddedJsonCurrentMissionIdValues"],
            0,
        )
        self.assertEqual(audit["installedPatch"]["matchedMethods"], 0)
        self.assertEqual(audit["storyBindingsAdded"], 0)
        self.assertEqual(audit["missionOrderEdgesAdded"], 0)
        self.assertEqual(
            audit["classification"],
            "implicit_context_only_missionruntime_no_levelscript_story_edge",
        )

    def test_direct_managed_identity_carrier_census_has_no_open_candidate(self):
        audit = pipeline.RUNTIME_CONTRACT["managedIdentityCarrierCensus"]
        metadata = audit["metadata"]
        self.assertEqual(metadata["managedTypeCount"], 63987)
        self.assertEqual(metadata["directCandidateTypes"], 10)
        self.assertEqual(metadata["runtimeObjectCandidates"], 8)
        self.assertEqual(metadata["unreviewedCandidates"], 0)
        authored = audit["authored"]
        self.assertEqual(authored["focusModeMissionRadioRows"], 13)
        self.assertEqual(authored["focusModeUniqueRadios"], 10)
        self.assertEqual(authored["npcProxyExMissionDialogRows"], 453)
        self.assertEqual(authored["subGameMissionScriptRows"], 20)
        tracking = audit["trackingClosure"]
        self.assertEqual(
            tracking["classification"],
            "closed_tracking_ui_context",
        )
        self.assertEqual(
            tracking["commonTrackingFields"]["missionId"]["offset"],
            "0x20",
        )
        self.assertEqual(
            tracking["commonTrackingFields"]["sceneId"]["offset"],
            "0x30",
        )
        self.assertEqual(len(tracking["nativeConsumers"]), 3)
        self.assertEqual(audit["storyBindingsAdded"], 0)
        self.assertEqual(audit["missionOrderEdgesAdded"], 0)
        self.assertEqual(
            audit["classification"],
            "all_direct_managed_identity_carriers_reviewed",
        )

    def test_nested_managed_identity_carrier_census_has_no_open_candidate(self):
        audit = pipeline.RUNTIME_CONTRACT["nestedManagedIdentityCarrierCensus"]
        metadata = audit["metadata"]
        self.assertEqual(metadata["managedTypeRecords"], 63987)
        self.assertEqual(metadata["runtimeTypeEntries"], 272743)
        self.assertEqual(metadata["maxCustomTypeDepth"], 3)
        self.assertEqual(metadata["candidateTypes"], 25)
        self.assertEqual(metadata["directExactCandidateTypes"], 11)
        self.assertEqual(metadata["nestedDependentCandidateTypes"], 14)
        self.assertEqual(metadata["reviewedCandidateTypes"], 25)
        self.assertEqual(metadata["unreviewedCandidateTypes"], 0)
        submitter = audit["pendingItemSubmitterClosure"]
        self.assertEqual(
            submitter["classification"],
            "active_shipped_xlua_producer_with_exact_submission_context_without_ui_join",
        )
        self.assertEqual(
            submitter["fields"]["DialogManager.m_pendingItemSubmitter"]["offset"],
            "0x200",
        )
        self.assertEqual(
            submitter["fields"]["InventoryItemSubmitter.questId"]["offset"],
            "0x20",
        )
        caller_counts = {
            row["symbol"]: row["nativeDirectCallerCount"]
            for row in submitter["methods"]
        }
        self.assertEqual(caller_counts["InventoryItemSubmitter..ctor"], 0)
        self.assertEqual(
            caller_counts["InventoryItemSubmitter.TryGetSubmitMsg"],
            1,
        )
        self.assertEqual(
            caller_counts["DialogManager.RegisterPendingSubmission"],
            0,
        )
        self.assertEqual(
            submitter["nativeOpenUiBridge"]["callee"][
                "nativeDirectCallerCount"
            ],
            2,
        )
        self.assertEqual(
            submitter["shippedLuaProducer"][
                "constructorAndRegistrationCalls"
            ],
            1,
        )
        authored = submitter["authoredOpenUiActions"]
        self.assertEqual(authored["typedTerminalActions"], 95)
        self.assertEqual(authored["submitItemPanelType"], 9)
        self.assertEqual(authored["submitItemActions"], 13)
        self.assertEqual(authored["placeholderSubmitItemActions"], 3)
        self.assertEqual(authored["emptyParamSubmitItemActions"], 10)
        self.assertEqual(authored["concreteQuestIdActions"], 0)
        objectives = submitter["authoredMissionObjectives"]
        self.assertEqual(objectives["conditionCount"], 3)
        self.assertEqual(objectives["questCount"], 3)
        self.assertEqual(objectives["missionCount"], 3)
        self.assertEqual(objectives["tableDefinedCount"], 3)
        self.assertEqual(objectives["dialogCoGateCount"], 2)
        self.assertEqual(objectives["dialogCoGateOpenUiOverlap"], 0)
        self.assertIn(
            "no quest lookup",
            submitter["fallbackParamFlow"]["finding"],
        )
        self.assertEqual(submitter["installedPatchMatches"], 0)
        self.assertEqual(audit["storyBindingsAdded"], 0)
        self.assertEqual(audit["missionOrderEdgesAdded"], 0)
        self.assertEqual(
            audit["classification"],
            "all_nested_managed_identity_carriers_reviewed",
        )

    def test_airwall_contract_is_state_gated_context_not_transition_owner(self):
        audit = pipeline.RUNTIME_CONTRACT["airWallMissionRadioContext"]
        self.assertEqual(audit["memoryPackSchema"]["levelDataMemberCount"], 43)
        self.assertEqual(audit["memoryPackSchema"]["airWallsMemberIndex"], 0)
        self.assertEqual(
            audit["memoryPackSchema"]["airWallGroupMemberCount"],
            8,
        )
        corpus = audit["corpus"]
        self.assertEqual(corpus["levelDataFiles"], 958)
        self.assertEqual(corpus["airWallGroups"], 822)
        self.assertEqual(corpus["missionCheckedRadioGroups"], 60)
        self.assertEqual(corpus["acceptedStoryContexts"], 58)
        self.assertEqual(corpus["missionAttachmentEdges"], 61)
        self.assertEqual(corpus["parseFailures"], 0)
        self.assertEqual(audit["installedPatch"]["matchedAirWallMethods"], 0)
        self.assertIn("not a mission-transition", audit["finding"])
        native = next(
            row
            for row in pipeline.RUNTIME_CONTRACT["nativeEvidence"]
            if row["symbol"].startswith("AirWallManager mission/quest")
        )
        self.assertIn("58 resolve completely", native["finding"])
        self.assertIn("non-owning", native["finding"])

    def test_missionless_subgame_reference_audit_rejects_non_owning_joins(self):
        audit = pipeline.RUNTIME_CONTRACT["subGameMissionRegistry"]["missionlessPlaybackAudit"]
        self.assertEqual(audit["subGameRows"], 10)
        self.assertEqual(audit["uniqueStoryFiles"], 9)
        self.assertEqual(audit["storyPlacements"], 14)
        self.assertEqual(audit["primaryTaskIds"], 10)
        self.assertEqual(audit["secondaryTaskIds"], 3)
        self.assertEqual(audit["exactMissionAssociations"], 1)
        self.assertEqual(audit["questUnlockPrerequisites"], 1)
        self.assertEqual(audit["previousSubGamePrerequisites"], 5)
        self.assertEqual(audit["missionRuntimeTaskConsumers"], 0)
        self.assertIn("explicitly non-owning", audit["finding"])
        self.assertEqual(audit["storyBindingsAdded"], 0)

    def test_runtime_contract_exposes_global_var_and_spawner_async_boundaries(self):
        rows = {
            row["id"]: row
            for direction in ("outbound", "inbound")
            for row in pipeline.RUNTIME_CONTRACT[direction]
        }
        expected = {
            "client-global-var-update": (
                "client_to_server",
                "global_var",
                "request_after_local_event",
                ["key", "value"],
            ),
            "global-var-update": (
                "server_to_client",
                "global_var",
                "server_update_or_confirmation",
                ["key", "value", "type"],
            ),
            "guide-group-complete-request": (
                "client_to_server",
                "guide_completion",
                "request",
                ["GuideGroupId", "IsClose"],
            ),
            "guide-group-complete-response": (
                "server_to_client",
                "guide_completion",
                "response",
                ["GuideGroupId", "IsClosed"],
            ),
            "level-script-event": (
                "client_to_server",
                "level_script_event",
                "request",
                ["sceneNumId", "scriptId", "eventName", "properties", "ctxToken"],
            ),
            "level-script-event-ack": (
                "server_to_client",
                "level_script_event",
                "response",
                [],
            ),
            "level-script-client-event": (
                "server_to_client",
                "level_script_event",
                "server_push",
                ["sceneNumId", "scriptId", "eventName", "ctxToken"],
            ),
            "level-script-stage-change": (
                "server_to_client",
                "level_script_stage",
                "server_push",
                ["sceneNumId", "scriptId", "stage"],
            ),
            "spawner-begin-wave": (
                "client_to_server",
                "spawner_wave",
                "request",
                ["sceneNumId", "spawnerId", "waveId", "clientTimestamp"],
            ),
            "spawner-begin-wave-response": (
                "server_to_client",
                "spawner_wave",
                "response",
                ["sceneNumId", "spawnerId", "waveId"],
            ),
            "spawner-wave-confirm-complete": (
                "client_to_server",
                "spawner_wave",
                "completion_acknowledgement",
                ["sceneNumId", "spawnerId", "waveId"],
            ),
            "spawner-complete": (
                "server_to_client",
                "spawner_completion",
                "server_push",
                ["sceneNumId", "spawnerId"],
            ),
            "touch-trigger-volume-request": (
                "client_to_server",
                "trigger_volume_touch",
                "request",
                ["sceneNumId", "scriptId", "scriptLocalId", "isLeaveAction"],
            ),
            "touch-trigger-volume-response": (
                "server_to_client",
                "trigger_volume_touch",
                "response",
                ["sceneNumId", "scriptId", "scriptLocalId", "isLeaveAction"],
            ),
            "trigger-volume-state-sync": (
                "server_to_client",
                "trigger_volume_state",
                "server_push",
                [
                    "sceneNumId",
                    "scriptId",
                    "triggerVolumeInfos[].scriptLocalId",
                    "triggerVolumeInfos[].isHidden",
                    "triggerVolumeInfos[].triggerCount",
                ],
            ),
            "subgame-start-request": (
                "client_to_server",
                "subgame_lifecycle",
                "request",
                ["gameId", "interactiveObjId", "npcProxyId", "npcObjId"],
            ),
            "subgame-enter": (
                "server_to_client",
                "subgame_lifecycle",
                "server_push",
                ["gameId", "isHunterMode", "gameInstId", "gameUniqueId", "isReenter"],
            ),
            "subgame-challenge-start": (
                "server_to_client",
                "subgame_lifecycle",
                "server_push",
                ["gameId", "challengeStartTs", "challengeExpireTs", "prepareChallengeSeconds"],
            ),
            "subgame-challenge-complete": (
                "server_to_client",
                "subgame_lifecycle",
                "server_push",
                ["gameId", "isPass", "forceLeaveTs", "passTime"],
            ),
            "subgame-completion-reward": (
                "server_to_client",
                "subgame_lifecycle",
                "server_push",
                [
                    "gameId",
                    "isPass",
                    "forceLeaveTs",
                    "rewardMultiplier",
                    "withoutStaminaReward",
                    "useStaminaReduce",
                ],
            ),
            "subgame-stop-request": (
                "client_to_server",
                "subgame_lifecycle",
                "request",
                ["curGameId"],
            ),
            "subgame-leave": (
                "server_to_client",
                "subgame_lifecycle",
                "server_push",
                ["gameId", "gameInstId", "gameUniqueId"],
            ),
            "scene-teleport-request": (
                "client_to_server",
                "scene_teleport",
                "request",
                [
                    "sceneNumId",
                    "position",
                    "rotation",
                    "teleportReason",
                    "passThroughData",
                    "tpPosId",
                    "tpReasonDetail(oneof)",
                ],
            ),
            "scene-teleport": (
                "server_to_client",
                "scene_teleport",
                "server_push",
                [
                    "objIdList[]",
                    "sceneNumId",
                    "position",
                    "rotation",
                    "serverTime",
                    "teleportReason",
                    "tpUuid",
                    "passThroughData",
                ],
            ),
            "scene-teleport-finish": (
                "client_to_server",
                "scene_teleport",
                "completion_acknowledgement",
                ["tpUuid"],
            ),
        }
        for row_id, (direction, family, role, fields) in expected.items():
            with self.subTest(row_id=row_id):
                row = rows[row_id]
                self.assertEqual(row["direction"], direction)
                self.assertEqual(row["exchangeFamily"], family)
                self.assertEqual(row["exchangeRole"], role)
                self.assertEqual(row["fields"], fields)
                self.assertTrue(row["asynchronous"])
                self.assertFalse(row["questScoped"])
                self.assertEqual(row["confidence"], "native_proven")

        self.assertIn("type:int32", rows["global-var-update"]["message"])
        self.assertIn("type discriminator remains raw", rows["global-var-update"]["effect"])
        self.assertIn("does not carry the LevelEvent_OnTeleportFinish actionId", rows["scene-teleport-finish"]["effect"])
        self.assertFalse(any("SPAWNER_GROUP_BEGIN" in row["message"] for row in rows.values()))
        guide = pipeline.RUNTIME_CONTRACT["guideCompletion"]
        self.assertEqual(11, guide["conditionType"])
        self.assertEqual("All", guide["completeTypeNames"]["0"])
        self.assertIn("skips CS_COMPLETE_GUIDE_GROUP", guide["clientOnlyFinding"])
        battle_signal = next(
            row for row in pipeline.RUNTIME_CONTRACT["localOnly"]
            if row["id"] == "battle-signal"
        )
        self.assertFalse(battle_signal["serverExchange"])
        self.assertEqual(battle_signal["fields"], ["signalId", "doubleValue"])
        self.assertIn("no sender, entity, spawner", battle_signal["effect"])
        local_rows = {
            row["id"]: row for row in pipeline.RUNTIME_CONTRACT["localOnly"]
        }
        self.assertFalse(local_rows["spawner-group-begin"]["serverExchange"])
        self.assertEqual(
            "spawner_begin_wave",
            local_rows["spawner-group-begin"]["upstreamExchangeFamily"],
        )
        self.assertFalse(local_rows["entity-hp-changed"]["serverExchange"])
        self.assertFalse(local_rows["npc-patrol-checkpoint"]["serverExchange"])

        npc_selector = pipeline.RUNTIME_CONTRACT["npcProxyDialogSelection"]
        self.assertFalse(npc_selector["clientRequest"])
        self.assertFalse(npc_selector["expectedClientReply"])
        self.assertIn("reads dialogId but not", npc_selector["bindingBoundary"])
        self.assertIn("proxy-deactivation guard", npc_selector["bindingBoundary"])
        for row_id in (
            "npc-proxy-enter-map-resync",
            "npc-proxy-active-change",
        ):
            row = rows[row_id]
            self.assertEqual("server_to_client", row["direction"])
            self.assertIn("SCD_NPC_PROXY_INFO.activeCondIndex", row["fields"])
            self.assertNotIn("missionId", row["fields"])
            self.assertNotIn("questId", row["fields"])
            self.assertNotIn("dialogId", row["fields"])

    def test_runtime_contract_exposes_original_system_story_carrier_boundaries(self):
        contract = pipeline.RUNTIME_CONTRACT
        carriers = contract["systemStoryCarriers"]
        rows = {
            row["id"]: row
            for direction in ("outbound", "inbound")
            for row in contract[direction]
        }

        domain = carriers["domainDepotDeliveryDialog"]
        self.assertEqual("f1m25", domain["missionId"])
        self.assertIsNone(domain["questId"])
        self.assertEqual(4, len(domain["exchangeIds"]))
        self.assertIn("do not serialize an individual quest", domain["bindingBoundary"])
        receive_request = rows["domain-depot-recv-package-request"]
        receive_response = rows["domain-depot-recv-package-response"]
        self.assertEqual(["deliverInstId"], receive_request["fields"])
        self.assertEqual(receive_request["expectedResponse"], receive_response["message"])
        self.assertIn("_AddDialogInDelivering", receive_response["effect"])
        send_request = rows["domain-depot-send-package-request"]
        send_response = rows["domain-depot-send-package-response"]
        self.assertEqual(["deliverInstId"], send_request["fields"])
        self.assertEqual(send_request["expectedResponse"], send_response["message"])
        self.assertEqual(
            ["deliverInstId", "rewardValue", "extraCreditCount"],
            send_response["fields"],
        )
        self.assertIn("remove the delivery dialog override", send_response["effect"])

        skip = carriers["skipChapterDialog"]
        self.assertEqual("e5m1", skip["missionId"])
        self.assertIsNone(skip["questId"])
        skip_request = rows["skip-chapter-request"]
        skip_response = rows["skip-chapter-response"]
        self.assertEqual(["skipChapterConfigId"], skip_request["fields"])
        self.assertEqual(skip_request["expectedResponse"], skip_response["message"])
        self.assertIn("no additional resolved non-wrapper side effect", skip_response["effect"])

        factory = carriers["factoryBuildingPanelLockRadio"]
        self.assertEqual(["e1m1_q#01", "e1m4_q#5"], factory["questIds"])
        self.assertIsNone(factory["missionId"])
        self.assertFalse(factory["serverExchange"])
        self.assertEqual([], factory["exchangeIds"])
        factory_local = next(
            row for row in contract["localOnly"]
            if row["id"] == "factory-building-panel-lock-radio"
        )
        self.assertFalse(factory_local["serverExchange"])
        self.assertFalse(factory_local["storyOwnership"])
        self.assertIn("expects no server response", factory_local["effect"])
        self.assertNotIn("e1m2", " ".join(factory["questIds"]))

        dialog_tree = carriers["dialogTreeQuestStateBranch"]
        self.assertEqual(
            "Beyond.Gameplay.CheckQuestState",
            dialog_tree["conditionType"],
        )
        self.assertFalse(dialog_tree["serverExchange"])
        self.assertEqual([], dialog_tree["exchangeIds"])
        self.assertIn("non-owning dependency", dialog_tree["bindingBoundary"])
        dialog_tree_local = next(
            row for row in contract["localOnly"]
            if row["id"] == "dialog-tree-quest-state-branch"
        )
        self.assertFalse(dialog_tree_local["serverExchange"])
        self.assertFalse(dialog_tree_local["storyOwnership"])
        self.assertEqual(
            ["SC_SYNC_ALL_MISSION", "SC_QUEST_STATE_UPDATE"],
            dialog_tree_local["upstreamStateSources"],
        )
        self.assertEqual(
            ["_questId", "_comparer", "_targetQuestState", "connections"],
            dialog_tree_local["fields"],
        )
        self.assertEqual(
            "0x18400f840 / 0x1873418f0; 0x1872a5280 or 0x1872a1d0c",
            dialog_tree_local["address"],
        )
        self.assertNotIn("->", dialog_tree_local["handler"])
        self.assertIn("expects no server response", dialog_tree_local["effect"])

    def test_story_binding_coverage_separates_unique_files_and_cross_mission_placements(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story_root = root / "lang"
            language_root = story_root / "CN"
            mission_root = language_root / "mission"
            report_root = root / "reports"
            subgame_table = root / "SubGameInstanceDataTable.json"
            activity_stage_table = root / "ActivityConditionalMultiStageTable.json"
            game_mechanic_condition_table = root / "GameMechanicConditionTable.json"
            dungeon_table = root / "DungeonTable.json"
            text_vo_id_table = root / "TextVoIdTable.json"
            mission_root.mkdir(parents=True)
            battle_signal_route = {
                "relation": "ability_battle_signal_local_causality",
                "storyKey": "radio_testm1_1",
                "actionType": "Core_SendBattleSignalToLevel_Data",
                "actionUnionTag": "0x0134",
                "serializedMemberCount": 6,
                "producerMappingId": pipeline.BATTLE_SIGNAL_PRODUCER_MAPPING_ID,
                "producerDomain": "SkillData",
                "producerAssetId": "skill_fixture",
                "producerSourceFile": "fixture/skill_fixture.json",
                "actionOffset": "0x20",
                "prefix": {"isEnable": True},
                "signalId": {
                    "memberCount": 3,
                    "useBlackboardKey": False,
                    "value": "fixture_signal",
                },
                "doubleValue": {
                    "memberCount": 3,
                    "useBlackboardKey": False,
                    "value": 0.0,
                },
                "receiverSignalId": "fixture_signal",
                "listenerLevelId": "map_test",
                "listenerScriptId": "70000000001",
                "listenerHeaderLocalId": 9,
                "listenerSourceFile": "fixture/70000000001.json",
                "receiverMappingId": pipeline.BATTLE_SIGNAL_RECEIVER_MAPPING_ID,
                "receiverPayloadMappingId": pipeline.BATTLE_SIGNAL_PAYLOAD_MAPPING_ID,
                "executionSide": "client",
                "transport": "local-level-runtime-event",
                "serverExchange": False,
                "clientRequest": False,
                "expectedServerReturn": False,
                "missionOwnerStatus": "unresolved",
                "storyBinding": False,
            }
            wrong_header_battle_signal_route = {
                **battle_signal_route,
                "producerAssetId": "skill_wrong_header",
                "producerSourceFile": "fixture/skill_wrong_header.json",
                "actionOffset": "0x40",
                "listenerHeaderLocalId": 8,
            }
            (language_root / "index.json").write_text(json.dumps({"entries": [
                {"k": "dlg_testm1_1", "d": "dlg", "m": "testm1", "p": "one"},
                {"k": "radio_testm1_1", "d": "radio", "m": "testm1", "p": "two"},
                {"k": "sns_testm2_1", "d": "sns", "m": "testm2", "p": "three"},
                {"k": "cutscene_map_test_1", "d": "cutscene", "m": "map_test", "p": "cross owner"},
                {"k": "black_map_external_1", "d": "black", "m": "map_external", "p": "dependency only"},
                {"k": "text_testm1_1", "d": "text", "m": "testm1", "p": "reading"},
                {"k": "env_testm1_1", "d": "env", "m": "testm1", "p": "excluded"},
            ]}), encoding="utf-8")
            (mission_root / "testm1.json").write_text(json.dumps({"flow": {
                "quests": [{"id": "testm1_q#1", "storyConnections": [{
                    "key": "dlg_testm1_1", "relation": "client_action_start",
                    "direction": "quest_to_story", "phase": "start",
                    "actionType": "StartDialogAction",
                    "evidenceTier": "native_direct",
                }, {
                    "key": "cutscene_map_test_1",
                    "relation": "leveldata_world_entity_quest_playback_context",
                    "evidenceTier": "derived_exact_foreign_key",
                }]}],
                "missionStoryConnections": [{
                    "key": "sns_testm2_1", "relation": "sns_authored_mission_link",
                }, {
                    "key": "text_testm1_1",
                    "relation": "levelscript_interactive_narrative_config",
                    "scriptIds": ["70000000002"],
                    "localInteractiveId": 40001,
                    "rawTypeId": "rp_text_testm1_1",
                    "entityTemplateIds": ["int_narrative_mission"],
                }],
                "unlinkedNativePlayback": [{
                    "key": "radio_testm1_1",
                    "nativeEventNames": ["LevelEvent_OnBattleSignal"],
                    "nativeActions": ["PlayRadioAction", "DifferentOccurrenceAction"],
                    "nativeEventProducerRoutes": [
                        battle_signal_route,
                        wrong_header_battle_signal_route,
                    ],
                    "occurrences": [{
                        "scriptId": "70000000001",
                        "levelId": "map_test",
                        "sourceFile": "fixture/70000000001.json",
                        "actionName": "PlayRadioAction",
                        "nativeEventOwners": [{
                            "status": "exact_serialized_control_path",
                            "headerName": "LevelEvent_OnBattleSignal",
                            "headerUnionTag": "0x004c",
                            "headerSerializedMemberCount": 16,
                            "headerLocalId": 9,
                            "nativeHeaderMappingId": (
                                pipeline.BATTLE_SIGNAL_RECEIVER_MAPPING_ID
                            ),
                            "eventDetail": {
                                "type": "LevelEvent_OnBattleSignal",
                                "signalId": "fixture_signal",
                                "transport": "local-level-runtime-event",
                                "serverExchange": False,
                                "serializedMissionOrQuestId": False,
                                "summary": "battle signal fixture_signal",
                                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                                "payloadSchemaMappingId": (
                                    pipeline.BATTLE_SIGNAL_PAYLOAD_MAPPING_ID
                                ),
                            },
                            "runtimeTarget": {
                                "status": "exact_top_level_encounter_module_target",
                                "moduleType": "EncounterData",
                                "levelScriptVariablePtr": "70000000003",
                                "ownershipBoundary": "fixture missing mission / quest foreign key",
                            },
                        }],
                    }],
                }],
                "unresolvedDialogTreeNarrativeActions": [
                    {"key": "dlg_testm1_1", "partiallyScoped": True},
                    {"key": "radio_testm1_1"},
                ],
                "unlinkedDialogTreeNarrativeActions": [{"key": "radio_testm1_1"}],
                "unresolvedDialogTreeStoryPlaybackCarriers": [
                    {"key": "radio_testm1_1"},
                ],
                "unlinkedDefinitionOnly": [{"key": "radio_testm1_1"}],
                "missionStateStoryDependencies": [{
                    "key": "radio_testm1_1",
                    "relation": "mission_state_getter_native_dependency",
                    "storyBinding": False,
                    "ownership": False,
                }, {
                    "key": "black_map_external_1",
                    "relation": "levelscript_task_mission_state_dependency",
                    "storyBinding": False,
                    "ownership": False,
                }],
            }}), encoding="utf-8")
            (mission_root / "testm2.json").write_text(json.dumps({"flow": {
                "quests": [{"id": "testm2_q#1", "storyConnections": [{
                    "key": "sns_testm2_1", "relation": "runtime_reference",
                }]}],
            }}), encoding="utf-8")
            subgame_table.write_text(json.dumps({"dataTable": {
                "missionless_test": {
                    "$type": "Beyond.Gameplay.Core.WorldChallengeSubGameData, Gameplay.Beyond",
                    "bindScriptId": 70000000001,
                    "modeId": "fixture_mode",
                    "mainTasks": [{"taskId": "fixture_task"}],
                },
                "mission_owned_test": {
                    "$type": "Beyond.Gameplay.Core.DungeonSubGameData, Gameplay.Beyond",
                    "bindScriptId": 70000000001,
                    "dungeonMissionId": "testm1",
                },
            }}), encoding="utf-8")
            activity_stage_table.write_text(json.dumps({
                "fixture_activity": {"stageList": {"fixture_stage": {
                    "stageId": "fixture_stage",
                    "missionId": "testm1",
                    "rankRelatedId": "missionless_test",
                }}},
            }), encoding="utf-8")
            game_mechanic_condition_table.write_text(json.dumps({
                "fixture_condition": {
                    "conditionId": "fixture_condition",
                    "gameMechanicsId": "missionless_test",
                    "conditionType": 18,
                    "parameter": [{"valueStringList": ["testm1_q#2", "0"]}],
                },
                "fixture_mission_condition": {
                    "conditionId": "fixture_mission_condition",
                    "gameMechanicsId": "missionless_test",
                    "conditionType": 19,
                    "parameter": [{"valueStringList": ["testm1", "0"]}],
                },
            }), encoding="utf-8")
            dungeon_table.write_text(json.dumps({
                "missionless_test": {
                    "dungeonId": "missionless_test",
                    "sceneId": "dung_fixture",
                    "levelId": "map_test",
                    "dungeonSeriesId": "fixture_series",
                },
            }), encoding="utf-8")
            text_vo_id_table.write_text(json.dumps({
                "radio_testm1_1_001": "au_radio_testm1_1_001",
            }), encoding="utf-8")
            pipeline_index = {"missions": [{"id": "testm1"}, {"id": "testm2"}]}
            report = pipeline.build_story_binding_coverage(
                pipeline_index,
                root / "pipeline" / "index.json",
                story_root,
                "CN",
                report_root,
                subgame_table,
                activity_stage_table,
                game_mechanic_condition_table,
                dungeon_table,
                text_vo_id_table,
                native_story_playback_index={},
            )
            self.assertIsNotNone(report)
            self.assertEqual(report["counts"]["uniqueStoryFiles"], 4)
            self.assertEqual(report["counts"]["connectedUniqueStoryFiles"], 3)
            self.assertEqual(report["counts"]["connectedCrossOwnerStoryFiles"], 1)
            self.assertEqual(
                report["connectedCrossOwnerStoryKeys"],
                ["cutscene_map_test_1"],
            )
            self.assertEqual(report["counts"]["connectedMissionPlacements"], 4)
            self.assertEqual(report["counts"]["unlinkedUniqueStoryFiles"], 1)
            self.assertEqual(report["counts"]["storyFilesWithTriggerRoutes"], 4)
            self.assertEqual(report["counts"]["unlinkedStoryFilesWithTriggerRoutes"], 1)
            self.assertGreaterEqual(report["counts"]["storyTriggerRoutes"], 7)
            self.assertEqual(
                report["counts"]["contextOnlyTriggerRouteFiles"],
                1,
            )
            self.assertEqual(report["counts"]["contextOnlyTriggerRoutes"], 1)
            trigger_manifest = report["storyTriggerManifest"]
            text_route = trigger_manifest["text_testm1_1"]
            self.assertEqual(
                text_route["attachmentStatus"],
                "context_only_outside_pipeline_coverage_denominator",
            )
            self.assertEqual(
                [step["kind"] for step in text_route["routes"][0]["steps"]],
                ["mission", "levelscript", "narrative_interactive", "story"],
            )
            connected_route = trigger_manifest["dlg_testm1_1"]["routes"][0]
            self.assertEqual(connected_route["questId"], "testm1_q#1")
            self.assertEqual(connected_route["causality"], "playback")
            self.assertEqual(
                [step["kind"] for step in connected_route["steps"]],
                ["quest", "native_action", "story"],
            )
            self.assertEqual(
                connected_route["nativeCinematicProducerRoutes"][0]["producerMethod"],
                "StartDialog",
            )
            self.assertIn(
                "reports/story/recovery/cinematic_queue_runtime_audit.json",
                connected_route["sourceFiles"],
            )
            self.assertEqual(
                report["counts"]["nativeCinematicProducerStoryFiles"],
                1,
            )
            self.assertEqual(
                report["counts"]["nativeCinematicProducerRouteAttachments"],
                1,
            )
            unresolved_routes = trigger_manifest["radio_testm1_1"]["routes"]
            unresolved_route = next(
                row for row in unresolved_routes
                if row["causality"] == "playback_owner_unresolved"
            )
            self.assertEqual(unresolved_route["eventNames"], ["LevelEvent_OnBattleSignal"])
            self.assertEqual(unresolved_route["scriptIds"], ["70000000001"])
            self.assertEqual(unresolved_route["nativePaths"][0]["selector"]["signalId"], "fixture_signal")
            self.assertEqual(unresolved_route["steps"][0]["kind"], "ownership_gap")
            self.assertEqual(
                report["counts"]["missionStateDependencyStoryFiles"],
                2,
            )
            self.assertEqual(
                report["counts"]["missionStateDependencyCrossOwnerStoryFiles"],
                1,
            )
            self.assertEqual(
                report["counts"]["missionStateDependencyPlacements"],
                2,
            )
            self.assertEqual(
                report["missionStateDependencyCrossOwnerStoryKeys"],
                ["black_map_external_1"],
            )
            self.assertTrue(
                all(
                    not row["storyBinding"]
                    for row in report["missionStateStoryDependencies"]
                )
            )
            self.assertEqual(report["counts"]["unlinkedNativePlaybackFiles"], 1)
            self.assertEqual(report["counts"]["unlinkedNativePlaybackWithoutNamedEvent"], 0)
            self.assertEqual(report["counts"]["missionlessSubGameRows"], 1)
            self.assertEqual(report["counts"]["missionlessSubGameStoryFiles"], 1)
            self.assertEqual(report["counts"]["missionlessSubGameStoryPlacements"], 1)
            runtime_node = report["missionlessSubGamePlaybackNodes"][0]
            self.assertEqual(runtime_node["subGameId"], "missionless_test")
            self.assertEqual(runtime_node["bindScriptId"], "70000000001")
            self.assertEqual(runtime_node["mainTaskIds"], ["fixture_task"])
            self.assertEqual(runtime_node["storyFiles"][0]["key"], "radio_testm1_1")
            self.assertEqual(runtime_node["storyFiles"][0]["nativeActions"], ["PlayRadioAction"])
            self.assertFalse(runtime_node["storyBinding"])
            self.assertEqual(
                [row["relation"] for row in runtime_node["associations"]],
                [
                    "activity_stage_mission_association",
                    "subgame_unlock_quest_prerequisite",
                    "subgame_unlock_mission_prerequisite",
                ],
            )
            mission_prerequisite = runtime_node["associations"][2]
            self.assertEqual(mission_prerequisite["targetType"], "mission")
            self.assertEqual(mission_prerequisite["targetId"], "testm1")
            self.assertEqual(
                mission_prerequisite["conditionTypeName"],
                "MissionStateEqual",
            )
            self.assertTrue(all(not row["ownership"] for row in runtime_node["associations"]))
            self.assertEqual(runtime_node["sceneHosts"][0]["sceneId"], "dung_fixture")
            self.assertEqual(report["counts"]["missionlessNativeRuntimeRows"], 1)
            self.assertEqual(report["counts"]["missionlessNativeRuntimeStoryFiles"], 1)
            native_node = report["missionlessNativeRuntimeNodes"][0]
            self.assertEqual(native_node["eventName"], "LevelEvent_OnBattleSignal")
            self.assertEqual(native_node["selector"]["signalId"], "fixture_signal")
            self.assertEqual(native_node["selector"]["listenerScriptId"], "70000000001")
            self.assertEqual(native_node["selector"]["listenerHeaderLocalId"], 9)
            self.assertEqual(native_node["storyFiles"][0]["key"], "radio_testm1_1")
            self.assertFalse(native_node["storyBinding"])
            self.assertEqual(
                native_node["localProducerRoutes"][0]["producerAssetId"],
                "skill_fixture",
            )
            self.assertEqual(
                native_node["producerReceiverBoundary"],
                "OnBattleSignal selects only signalId; it has no serialized sender, entity, spawner, mission, or quest selector",
            )
            self.assertFalse(native_node["serverExchange"])
            self.assertFalse(native_node["clientRequest"])
            self.assertFalse(native_node["expectedServerReturn"])
            self.assertEqual(
                native_node["runtimeTarget"]["levelScriptVariablePtr"],
                "70000000003",
            )
            self.assertEqual(
                native_node["ownershipBoundary"],
                "fixture missing mission / quest foreign key",
            )
            self.assertEqual(
                report["counts"]["missionlessNativeRuntimeProducerRoutes"],
                1,
            )
            self.assertIn("Original exported game data", report["policy"])
            self.assertIn("do not promote", report["policy"])
            self.assertEqual(
                report["nativePlaybackEventFamilies"],
                {"LevelEvent_OnBattleSignal": 1},
            )
            self.assertEqual(
                report["nativePlaybackEventFamilyKeys"],
                {"LevelEvent_OnBattleSignal": ["radio_testm1_1"]},
            )
            self.assertEqual(report["counts"]["unresolvedDialogTreeNarrativeFiles"], 2)
            self.assertEqual(report["counts"]["unlinkedDialogTreeNarrativeFiles"], 1)
            self.assertEqual(
                report["counts"]["unresolvedDialogTreeStoryPlaybackFiles"],
                1,
            )
            self.assertEqual(
                report["unresolvedDialogTreeStoryPlaybackKeys"],
                ["radio_testm1_1"],
            )
            self.assertEqual(report["counts"]["unlinkedDefinitionOnlyFiles"], 1)
            self.assertEqual(
                report["counts"]["unlinkedDefinitionOnlyAudioMetadataFiles"],
                1,
            )
            self.assertEqual(
                report["counts"]["unlinkedDefinitionOnlyEmptyAudioLikelyLegacyFiles"],
                0,
            )
            definition_classification = report["definitionOnlyNegativeConsumerClassification"]
            self.assertIn("never promotes", definition_classification["policy"])
            self.assertEqual(definition_classification["source"]["tableRows"], 1)
            self.assertEqual(
                definition_classification["records"][0]["classification"],
                "original_audio_metadata_without_playback_consumer",
            )
            self.assertFalse(definition_classification["records"][0]["storyBinding"])
            self.assertEqual(
                report["unlinkedDefinitionOnlyKeys"],
                ["radio_testm1_1"],
            )
            self.assertEqual(
                report["counts"]["partiallyConnectedDialogTreeNarrativeFiles"],
                1,
            )
            self.assertEqual(
                report["evidenceTierRows"],
                {"derived_exact_foreign_key": 1, "native_direct": 1},
            )
            self.assertEqual(
                report["evidenceTierUniqueStoryFiles"],
                {"derived_exact_foreign_key": 1, "native_direct": 1},
            )
            self.assertEqual(report["unlinked"][0]["key"], "radio_testm1_1")
            self.assertTrue((report_root / "mission_pipeline_story_binding_coverage_CN.json").is_file())

    def test_story_connection_direction_uses_condition_and_native_action_semantics(self):
        condition_rows = mission_flow._runtime_story_connections(
            condition(
                "CheckTalkOptionFinish",
                _dialogId={"constValue": "dlg_test"},
                _finishId={"constValue": 2},
            ),
            relation="objective_condition",
            phase="progress",
            source="fixture.condition",
            objective_index=1,
        )
        self.assertEqual(condition_rows[0]["direction"], "story_to_quest")
        self.assertEqual(condition_rows[0]["finishId"], 2)

        action_rows = mission_flow._client_action_story_connections(self.fixture())
        connection = action_rows["testm1_q#2"][0]
        self.assertEqual(connection["direction"], "quest_to_story")
        self.assertEqual(connection["relation"], "client_action_succeed")
        self.assertEqual(connection["actionType"], "PlayRadio")

    def test_objective_area_embedded_story_id_is_context_not_playback(self):
        rows = mission_flow._objective_area_story_connections([{
            "index": 2,
            "missionAreaIds": ["e1m1_radio_e1m1_3d2"],
            "areaStoryRefs": ["radio_e1m1_3d2"],
            "conditionTypes": ["ReachDestination"],
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "radio_e1m1_3d2")
        self.assertEqual(rows[0]["relation"], "mission_area_story_reference")
        self.assertEqual(rows[0]["direction"], "context")
        self.assertEqual(rows[0]["confidence"], "direct_embedded")

    def test_npc_proxy_attachment_requires_explicit_mission_and_keeps_all_dialogs(self):
        quests = [{"id": "e11m6_q#4", "proxies": ["proxy_a"]}]
        proxy_rows = {
            "data": {
                "proxy_a": [
                    {"missionId": "", "dialogId": "dlg_default"},
                    {"missionId": "other", "dialogId": "dlg_other"},
                    {"missionId": "e11m6", "dialogId": "dlg_e11m6_6"},
                    {"missionId": "e11m6", "dialogId": "dlg_e11m6_7"},
                ],
            },
        }
        with patch.object(mission_flow, "_load_npc_proxy_ex", return_value=proxy_rows):
            mission_flow._attach_unique_proxy_dialog_refs("e11m6", quests)
        connections = quests[0]["storyConnections"]
        self.assertEqual([row["key"] for row in connections], ["dlg_e11m6_6", "dlg_e11m6_7"])
        self.assertTrue(all(row["relation"] == "npc_proxy_ex_attachment" for row in connections))

    def test_mission_accept_dialog_requires_native_npc_accept_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = {
                "acceptMode": {
                    "mode": 3,
                    "modeInfo": {
                        "$type": "Beyond.Gameplay.MissionAcceptMode+NPCInfo, Gameplay.Beyond",
                        "npcProxyId": "npc_accept",
                        "dialogId": "dlg_test_accept",
                        "finishId": -1,
                        "levelId": "map_test",
                    },
                },
            }
            (root / "testm1_meta.json").write_text(json.dumps(valid), encoding="utf-8")
            with patch.object(mission_flow, "MRA_DIR", root):
                rows = mission_flow._mission_accept_story_connections("testm1")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["relation"], "mission_accept_dialog")
            self.assertEqual(rows[0]["direction"], "story_to_mission")

            valid["acceptMode"]["mode"] = 5
            (root / "testm1_meta.json").write_text(json.dumps(valid), encoding="utf-8")
            with patch.object(mission_flow, "MRA_DIR", root):
                self.assertEqual(mission_flow._mission_accept_story_connections("testm1"), [])

    def test_source_link_ignores_default_path_when_runtime_const_value_differs(self):
        owner = {
            "path": "radio_m1m8_1",
            "constValue": "radio_m1m41_1",
        }
        self.assertTrue(source_links.is_shadowed_serialized_path(
            ("_radioId", "path"),
            (("_radioId", owner),),
            "radio_m1m8_1",
        ))
        owner["constValue"] = "radio_m1m8_1"
        self.assertFalse(source_links.is_shadowed_serialized_path(
            ("_radioId", "path"),
            (("_radioId", owner),),
            "radio_m1m8_1",
        ))


class LuaStoryPlaybackCallSiteTests(unittest.TestCase):
    """The shipped-Lua playback lane is corpus-derived, so guard its gates."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = pipeline.load_lua_story_playback_evidence()

    def test_every_admitted_call_site_has_full_provenance(self) -> None:
        for row in self.evidence["acceptedExactPlaybackCalls"]:
            for field in (
                "storyKey", "luaFile", "luaSymbol", "luaCall", "nativeEntry",
                "phase", "note", "luaSourceSha256", "luaLine", "auditReport",
            ):
                self.assertTrue(
                    str(row.get(field) or "").strip(),
                    f"{row.get('storyKey')} missing {field}",
                )
            self.assertTrue(row["luaFile"].endswith(".lua"))

    def test_handle_calls_are_one_binary_proven_runtime_family(self) -> None:
        self.assertEqual(7, self.evidence["runtimeHandleDispatcherCallCount"])
        self.assertEqual(1, self.evidence["runtimeHandleDispatcherFamilyCount"])
        self.assertEqual(0, self.evidence["unresolvedPlaybackCalls"])
        contract_methods = set(
            self.evidence["runtimeHandleContract"]["dispatcherMethods"]
        )
        self.assertTrue({
            row["method"]
            for row in self.evidence["runtimeHandleDispatcherCalls"]
        }.issubset(contract_methods))

    def test_case_sensitive_gender_select_cutscene_is_not_admitted(self) -> None:
        # The current native resolver preserves "Cutscene_e0m0_1" into
        # case-sensitive StringPathHash resource lookup, so it cannot prove
        # playback of lowercase "cutscene_e0m0_1".
        keys = {
            row["storyKey"]
            for row in self.evidence["acceptedExactPlaybackCalls"]
        }
        self.assertNotIn("cutscene_e0m0_1", keys)
        self.assertNotIn("Cutscene_e0m0_1", keys)

    def test_every_rejected_candidate_has_auditable_provenance(self) -> None:
        admitted = {
            row["storyKey"]
            for row in self.evidence["acceptedExactPlaybackCalls"]
        }
        for row in self.evidence["rejectedCaseMismatchCalls"]:
            for field in (
                "storyKey", "luaLiteral", "luaFile", "luaSymbol", "luaCall",
                "nativeEntry", "reason", "confidence", "auditReport", "note",
            ):
                self.assertTrue(
                    str(row.get(field) or "").strip(),
                    f"{row.get('storyKey')} missing {field}",
                )
            self.assertNotIn(row["storyKey"], admitted)
            self.assertNotEqual(row["luaLiteral"], row["storyKey"])
            self.assertEqual(
                row["reason"],
                "case_sensitive_native_resource_lookup",
            )
            self.assertTrue(row["auditReport"].endswith(".json"))

    def test_corpus_rule_admits_an_arbitrary_exact_story_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            audit_path = Path(temporary) / "lua_audit.json"
            audit_path.write_text(json.dumps({
                "schemaVersion": pipeline.LUA_CONSUMER_REFERENCE_SCHEMA,
                "summary": {"readErrorCount": 0},
                "gameActionAudit": {"storyPlaybackCalls": [{
                    "module": "Phase/Fixture/Fixture.lua",
                    "sourcePath": "not-present/original-fixture.lua",
                    "sourceSha256": "a" * 64,
                    "line": 7,
                    "method": "PlayCutscene",
                    "playbackKind": "cutscene",
                    "argumentSemantics": "story_id",
                    "firstArgument": "STORY_ID",
                    "resolvedLiteral": "cutscene_fixture_general_9",
                    "registryStatus": "exact_registry_match",
                    "canonicalStoryKey": "cutscene_fixture_general_9",
                }]},
            }), encoding="utf-8")

            evidence = pipeline.load_lua_story_playback_evidence(
                audit_path,
                (),
            )

        self.assertEqual(
            [row["storyKey"] for row in evidence["acceptedExactPlaybackCalls"]],
            ["cutscene_fixture_general_9"],
        )
        self.assertEqual(
            evidence["acceptedExactPlaybackCalls"][0]["phase"],
            "fixture",
        )

    def test_corpus_rule_admits_a_general_same_row_mission_carrier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            audit_path = Path(temporary) / "lua_audit.json"
            audit_path.write_text(json.dumps({
                "schemaVersion": pipeline.LUA_CONSUMER_REFERENCE_SCHEMA,
                "summary": {"readErrorCount": 0},
                "gameActionAudit": {"storyPlaybackCalls": [{
                    "module": "UI/Panels/Fixture/FixtureCtrl.lua",
                    "sourcePath": "not-present/original-fixture.lua",
                    "sourceSha256": "a" * 64,
                    "line": 17,
                    "method": "StartDialog",
                    "playbackKind": "dialog",
                    "argumentSemantics": "story_id",
                    "firstArgument": "storyId",
                    "literalResolution": "table_field_singleton",
                    "resolvedLiteral": "dlg_fixture_general_9",
                    "registryStatus": "exact_registry_match",
                    "canonicalStoryKey": "dlg_fixture_general_9",
                    "tableFieldResolution": {
                        "table": "FixtureCarrierTable",
                        "tableSourcePath": "not-present/FixtureCarrierTable.json",
                        "tableSourceSha256": "b" * 64,
                        "field": "storyId",
                        "lookupKeyExpression": "configId",
                        "exactSingleton": True,
                        "candidateRows": [{
                            "tableKey": "fixture_carrier",
                            "rawValue": "dlg_fixture_general_9",
                            "canonicalStoryKey": "dlg_fixture_general_9",
                            "registryStatus": "exact_registry_match",
                            "rowFields": {
                                "storyId": "dlg_fixture_general_9",
                                "missionId": "fixture_mission",
                            },
                        }],
                    },
                }]},
            }), encoding="utf-8")

            evidence = pipeline.load_lua_story_playback_evidence(
                audit_path,
                (),
            )

        row = evidence["acceptedExactPlaybackCalls"][0]
        self.assertEqual("dlg_fixture_general_9", row["storyKey"])
        self.assertEqual("fixture_mission", row["missionId"])
        self.assertEqual("FixtureCarrierTable", row["table"])
        self.assertEqual(1, evidence["acceptedTableCarrierCalls"])

    def test_corpus_rule_fails_closed_with_bounded_hash_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            audit_path = Path(temporary) / "lua_audit.json"
            audit_path.write_text(json.dumps({
                "schemaVersion": pipeline.LUA_CONSUMER_REFERENCE_SCHEMA,
                "summary": {"readErrorCount": 0},
                "gameActionAudit": {"storyPlaybackCalls": [{
                    "module": "fixture.lua",
                    "sourcePath": "not-present/fixture.lua",
                    "sourceSha256": "bad",
                    "line": 1,
                    "method": "PlayCutscene",
                    "argumentSemantics": "story_id",
                    "registryStatus": "exact_registry_match",
                }]},
            }), encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError,
                r"validator.*gate=row_provenance.*sourceSha256:sha256",
            ):
                pipeline.load_lua_story_playback_evidence(audit_path, ())

    def test_rejected_candidate_is_published_without_a_trigger_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story_root = root / "lang"
            language_root = story_root / "CN"
            mission_root = language_root / "mission"
            report_root = root / "reports"
            mission_root.mkdir(parents=True)
            (language_root / "index.json").write_text(json.dumps({
                "entries": [{
                    "k": "cutscene_e0m0_1",
                    "d": "cutscene",
                    "m": "e0m0",
                    "p": "fixture",
                }],
            }), encoding="utf-8")
            (mission_root / "e0m0.json").write_text(json.dumps({
                "flow": {},
            }), encoding="utf-8")
            table_paths = [
                root / "SubGameInstanceDataTable.json",
                root / "ActivityConditionalMultiStageTable.json",
                root / "GameMechanicConditionTable.json",
                root / "DungeonTable.json",
                root / "TextVoIdTable.json",
            ]
            for path in table_paths:
                path.write_text("{}", encoding="utf-8")

            report = pipeline.build_story_binding_coverage(
                {"missions": [{"id": "e0m0"}]},
                root / "pipeline" / "index.json",
                story_root,
                "CN",
                report_root,
                *table_paths,
                native_story_playback_index={},
            )

        row = report["storyTriggerManifest"]["cutscene_e0m0_1"]
        self.assertEqual(row["attachmentStatus"], "unlinked_no_trigger_route")
        self.assertEqual(row["routes"], [])
        self.assertEqual(
            row["rejectedPlaybackCandidates"],
            self.evidence["rejectedCaseMismatchCalls"],
        )
        self.assertEqual(
            report["counts"]["rejectedStoryPlaybackCandidates"],
            1,
        )

    def test_root_playback_alias_is_non_owning_trigger_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story_root = root / "lang"
            language_root = story_root / "CN"
            mission_root = language_root / "mission"
            report_root = root / "reports"
            mission_root.mkdir(parents=True)
            (language_root / "index.json").write_text(json.dumps({
                "entries": [{
                    "k": "cutscene_fixture_asset",
                    "d": "cutscene",
                    "m": "fixture",
                    "p": "fixture",
                }],
            }), encoding="utf-8")
            (mission_root / "fixture.json").write_text(
                json.dumps({"flow": {}}),
                encoding="utf-8",
            )
            table_paths = [
                root / "SubGameInstanceDataTable.json",
                root / "ActivityConditionalMultiStageTable.json",
                root / "GameMechanicConditionTable.json",
                root / "DungeonTable.json",
                root / "TextVoIdTable.json",
            ]
            for path in table_paths:
                path.write_text("{}", encoding="utf-8")
            alias = {
                "rootStoryKey": "cutscene_fixture_root",
                "playableAssetStoryKey": "cutscene_fixture_asset",
                "relation": "cutscene_root_director_playable_asset",
                "edgeStatus": (
                    "exact_root_playback_alias_no_chronology_or_mission_owner"
                ),
                "cutsceneRootGameObjectPathId": 7,
                "cutsceneRootComponentPathId": 8,
                "directorObject": {
                    "serializedFile": "CAB-host",
                    "pathId": 9,
                    "source": "VFS/hash/chunk.chk",
                },
                "nativeMappingId": (
                    "gameassembly-2026-07-28-"
                    "cutscene-root-director-playback-v1"
                ),
                "evidenceReport": (
                    "reports/story/recovery/"
                    "animestudio_story_reverse_pptr_audit.json"
                ),
                "ownership": False,
                "chronology": False,
            }
            with patch.object(
                pipeline,
                "story_root_playback_aliases",
                return_value=[alias],
            ):
                report = pipeline.build_story_binding_coverage(
                    {"missions": [{"id": "fixture"}]},
                    root / "pipeline" / "index.json",
                    story_root,
                    "CN",
                    report_root,
                    *table_paths,
                    native_story_playback_index={},
                )

        manifest = report["storyTriggerManifest"][
            "cutscene_fixture_asset"
        ]
        self.assertEqual(
            manifest["attachmentStatus"],
            "trigger_known_owner_unresolved",
        )
        self.assertEqual(len(manifest["routes"]), 1)
        route = manifest["routes"][0]
        self.assertEqual(
            route["causality"],
            "playback_alias_owner_unresolved",
        )
        self.assertEqual(
            [step["kind"] for step in route["steps"]],
            ["story_root", "native_action", "story"],
        )
        self.assertEqual(report["counts"]["connectedUniqueStoryFiles"], 0)
        self.assertEqual(report["counts"]["rootPlaybackAliasRows"], 1)
        self.assertEqual(report["counts"]["rootPlaybackAliasFiles"], 1)
        self.assertEqual(report["rootPlaybackAliases"], [alias])

    def test_owned_root_playback_route_composes_alias_owner_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story_root = root / "lang"
            language_root = story_root / "CN"
            mission_root = language_root / "mission"
            report_root = root / "reports"
            mission_root.mkdir(parents=True)
            (language_root / "index.json").write_text(json.dumps({
                "entries": [
                    {
                        "k": "cutscene_fixture_root",
                        "d": "cutscene",
                        "m": "fixture",
                        "p": "fixture",
                    },
                    {
                        "k": "cutscene_fixture_asset",
                        "d": "cutscene",
                        "m": "fixture",
                        "p": "fixture",
                    },
                ],
            }), encoding="utf-8")
            (mission_root / "fixture.json").write_text(json.dumps({
                "flow": {
                    "missionStoryConnections": [{
                        "key": "cutscene_fixture_root",
                        "relation":
                            "mission_global_var_native_playback_context",
                        "direction": "context",
                        "nativeActions": ["PlayCutsceneAction"],
                        "confidence":
                            "native_exact_unique_mission_global_var_context",
                        "evidenceTier": "native_exact_context",
                        "sourceFiles": ["fixture_levelscript.json"],
                    }],
                },
            }), encoding="utf-8")
            table_paths = [
                root / "SubGameInstanceDataTable.json",
                root / "ActivityConditionalMultiStageTable.json",
                root / "GameMechanicConditionTable.json",
                root / "DungeonTable.json",
                root / "TextVoIdTable.json",
            ]
            for path in table_paths:
                path.write_text("{}", encoding="utf-8")
            alias = {
                "rootStoryKey": "cutscene_fixture_root",
                "playableAssetStoryKey": "cutscene_fixture_asset",
                "relation": "cutscene_root_director_playable_asset",
                "edgeStatus": (
                    "exact_root_playback_alias_no_chronology_or_mission_owner"
                ),
                "cutsceneRootGameObjectPathId": 7,
                "cutsceneRootComponentPathId": 8,
                "directorObject": {
                    "serializedFile": "CAB-host",
                    "pathId": 9,
                    "source": "VFS/hash/chunk.chk",
                },
                "nativeMappingId": (
                    "gameassembly-2026-07-28-"
                    "cutscene-root-director-playback-v1"
                ),
                "evidenceReport": (
                    "reports/story/recovery/"
                    "animestudio_story_reverse_pptr_audit.json"
                ),
                "ownership": False,
                "chronology": False,
            }
            with patch.object(
                pipeline,
                "story_root_playback_aliases",
                return_value=[alias],
            ):
                report = pipeline.build_story_binding_coverage(
                    {"missions": [{"id": "fixture"}]},
                    root / "pipeline" / "index.json",
                    story_root,
                    "CN",
                    report_root,
                    *table_paths,
                    native_story_playback_index={},
                )

        manifest = report["storyTriggerManifest"][
            "cutscene_fixture_asset"
        ]
        self.assertEqual(manifest["attachmentStatus"], "connected")
        composed = next(
            route
            for route in manifest["routes"]
            if route["causality"] == "playback_alias_owner_connected"
        )
        self.assertEqual(composed["missionId"], "fixture")
        self.assertEqual(
            [step["kind"] for step in composed["steps"]],
            [
                "mission",
                "native_action",
                "story_root",
                "native_action",
                "story",
            ],
        )
        self.assertEqual(report["counts"]["connectedUniqueStoryFiles"], 2)
        self.assertEqual(report["counts"]["unlinkedUniqueStoryFiles"], 0)
        self.assertEqual(
            report["counts"]["composedRootPlaybackAliasRows"],
            1,
        )
        self.assertEqual(
            report["counts"]["composedRootPlaybackAliasFiles"],
            1,
        )
        self.assertEqual(
            report["composedRootPlaybackAliases"][0]["missionId"],
            "fixture",
        )

    def test_admitted_story_keys_are_lowercase_exact(self) -> None:
        for row in self.evidence["acceptedExactPlaybackCalls"]:
            self.assertEqual(row["storyKey"], row["storyKey"].lower())


class NonMissionContentTableTests(unittest.TestCase):
    def test_exact_runtime_non_mission_families_are_pipeline_visible(self) -> None:
        self.assertEqual(
            pipeline.PIPELINE_VISIBLE_NON_MISSION_EVIDENCE_KINDS,
            {
                "guide_runtime_asset",
                "spaceship_dialog_tree",
                "character_profile_voice",
                "spaceship_dialog_definition_without_tree_carrier",
            },
        )

    def test_tables_are_keyed_outside_the_mission_lane(self) -> None:
        from scripts.common import NON_MISSION_CONTENT_TABLES

        keyed_by = {spec["keyedBy"] for spec in NON_MISSION_CONTENT_TABLES}
        # A mission/quest/scene/script key would make the rows ownable and this
        # whole classification invalid.
        self.assertTrue(keyed_by.isdisjoint(
            {"missionId", "questId", "sceneNumId", "scriptId"}
        ))
        self.assertEqual(keyed_by, {"speaker", "topicId"})


class EnvTalkContextRegroupTests(unittest.TestCase):
    """``env_talk_contexts_by_mission`` must never widen a scope into a mission."""

    def report(self, entries):
        return {"entries": entries}

    def test_quest_contexts_are_grouped_by_mission(self):
        grouped = pipeline.env_talk_contexts_by_mission(self.report([
            {
                "storyKey": "env_envTalk_a_1",
                "envTalkId": "envTalk_a_1",
                "relation": "questTrackedNpcProxy",
                "questContexts": [
                    {"missionId": "alpha", "questId": "alpha_q#1", "npcProxyId": "p1", "levelId": "L"},
                ],
            },
        ]))
        self.assertEqual(list(grouped), ["alpha"])
        self.assertEqual(grouped["alpha"][0]["storyKey"], "env_envTalk_a_1")
        self.assertEqual(grouped["alpha"][0]["questId"], "alpha_q#1")

    def test_level_scoped_entries_never_reach_a_mission(self):
        # A level-scoped row has no quest context; inferring a mission from its
        # levelId would be exactly the promotion the evidence policy forbids.
        grouped = pipeline.env_talk_contexts_by_mission(self.report([
            {
                "storyKey": "env_envTalk_a_2",
                "envTalkId": "envTalk_a_2",
                "relation": "levelScopedConsumer",
                "questContexts": [],
            },
        ]))
        self.assertEqual(grouped, {})

    def test_blank_mission_id_is_dropped(self):
        grouped = pipeline.env_talk_contexts_by_mission(self.report([
            {
                "storyKey": "env_envTalk_a_3",
                "envTalkId": "envTalk_a_3",
                "relation": "questTrackedNpcProxy",
                "questContexts": [{"missionId": "", "questId": "q", "npcProxyId": "p", "levelId": ""}],
            },
        ]))
        self.assertEqual(grouped, {})

    def test_atmospheric_state_context_is_grouped_only_by_exact_mission_ids(self):
        grouped = pipeline.env_talk_contexts_by_mission(self.report([
            {
                "storyKey": "env_envTalk_a_4",
                "envTalkId": "envTalk_a_4",
                "relation": "levelScopedConsumer",
                "questContexts": [],
                "stateContexts": [{
                    "missionIds": ["alpha", "beta"],
                    "conditionMissionIds": ["beta"],
                    "questIds": ["alpha_q#1"],
                    "questOwners": {"alpha_q#1": "alpha"},
                    "bindMissionId": "",
                    "clusterId": "cluster_1",
                    "switcherId": "switcher_1",
                    "switcherGroupId": "group_1",
                    "levelId": "L",
                    "npcIds": ["npc_1", "npc_2"],
                }],
            },
        ]))
        self.assertEqual(sorted(grouped), ["alpha", "beta"])
        self.assertEqual(grouped["alpha"][0]["questIds"], ["alpha_q#1"])
        self.assertEqual(grouped["beta"][0]["questIds"], [])
        self.assertEqual(
            grouped["alpha"][0]["relation"],
            "atmosphericSwitcherStateContext",
        )
        self.assertEqual(grouped["alpha"][0]["switcherGroupId"], "group_1")

    def test_atmospheric_context_without_resolved_mission_is_not_widened(self):
        grouped = pipeline.env_talk_contexts_by_mission(self.report([
            {
                "storyKey": "env_envTalk_a_5",
                "envTalkId": "envTalk_a_5",
                "relation": "levelScopedConsumer",
                "questContexts": [],
                "stateContexts": [{
                    "missionIds": [],
                    "questIds": ["unknown_q#1"],
                    "questOwners": {},
                    "clusterId": "cluster_2",
                    "switcherGroupId": "group_2",
                    "levelId": "L",
                }],
            },
        ]))
        self.assertEqual(grouped, {})

    def test_trigger_manifest_keeps_atmospheric_route_context_only(self):
        manifest = pipeline.env_talk_trigger_manifest(self.report([
            {
                "storyKey": "env_envTalk_a_6",
                "envTalkId": "envTalk_a_6",
                "relation": "levelScopedConsumer",
                "levelIds": ["L"],
                "consumerCount": 1,
                "questContexts": [],
                "stateContexts": [{
                    "missionIds": ["alpha"],
                    "conditionMissionIds": [],
                    "questIds": ["alpha_q#1"],
                    "questOwners": {"alpha_q#1": "alpha"},
                    "clusterId": "cluster_3",
                    "switcherId": "switcher_1",
                    "switcherGroupId": "group_3",
                    "levelId": "L",
                }],
            },
        ]))
        route = manifest["env_envTalk_a_6"]["routes"][0]
        self.assertEqual(route["causality"], "context")
        self.assertEqual(
            route["relation"],
            "env_talk_atmospheric_switcher_state_context",
        )
        self.assertNotIn("playback", route)


class MissionGraphPayloadTests(unittest.TestCase):
    """The per-mission payload must carry the graph entry verbatim."""

    def test_payload_carries_supplied_graph_entry(self):
        base = MissionPipelineBuilderTests()
        mission = base.fixture()
        entry = {"upstream": {"requiresCompleted": ["beta"]}, "downstream": {}}
        payload, _ = pipeline.build_mission(
            mission,
            Path("testm1.json"),
            None,
            None,
            entry,
            [{"storyKey": "env_envTalk_x", "questId": "testm1_q#1"}],
        )
        self.assertEqual(payload["missionGraph"], entry)
        self.assertEqual(payload["envTalkContext"][0]["storyKey"], "env_envTalk_x")

    def test_payload_defaults_are_empty_not_missing(self):
        base = MissionPipelineBuilderTests()
        payload, _ = pipeline.build_mission(base.fixture(), Path("testm1.json"))
        self.assertEqual(payload["missionGraph"], {"upstream": {}, "downstream": {}})
        self.assertEqual(payload["envTalkContext"], [])


class MissionDialogTreeDefinitionPublisherTests(unittest.TestCase):
    def fixture(self, root: Path, source_sha256: str) -> tuple[dict, Path, Path]:
        output_root = root / "webui" / "data" / "mission_pipeline"
        mission_root = output_root / "missions"
        mission_root.mkdir(parents=True)
        story_root = root / "webui" / "data" / "lang"
        sidecar_root = story_root / "CN" / "mission"
        sidecar_root.mkdir(parents=True)
        (mission_root / "testm1.json").write_text(
            json.dumps({
                "nodes": [{
                    "id": "testm1_q#1",
                    "objectives": [{
                        "index": 1,
                        "condition": {
                            "type": "CheckTalkOptionFinish",
                            "facts": {
                                "dialogId": "dlg_testm1_1",
                                "finishId": -1,
                            },
                        },
                        "dialogFinishes": [{
                            "dialogId": "dlg_testm1_1",
                            "finishId": -1,
                        }],
                    }],
                }],
            }),
            encoding="utf-8",
        )
        (sidecar_root / "testm1.json").write_text(
            json.dumps({
                "timelineRecovery": {
                    "sceneDialogTreeEvidence": {
                        "dlg_testm1_1": {
                            "sceneKey": "dlg_testm1_1",
                            "assetType": "Beyond.Gameplay.DialogTree",
                            "evidenceKind": "exact_dialog_tree_definition",
                            "sourceFile": "assets/dlg_testm1_1.json",
                            "sourceSha256": source_sha256,
                            "lineIds": ["dlg_testm1_1_001"],
                            "nodeCount": 2,
                            "connectionCount": 1,
                            "branchingOptionGroupCount": 0,
                        },
                    },
                },
            }),
            encoding="utf-8",
        )
        index = {
            "missions": [{
                "id": "testm1",
                "file": "missions/testm1.json",
            }],
        }
        return index, output_root, story_root

    def test_publishes_hash_verified_definition_on_exact_quest_observer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "assets" / "dlg_testm1_1.json"
            source.parent.mkdir()
            source.write_bytes(b"dialog-tree-fixture")
            digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
            index, output_root, story_root = self.fixture(root, digest)

            with patch.object(pipeline, "ROOT", root):
                result = pipeline.publish_quest_dialog_tree_definitions(
                    index,
                    output_root,
                    story_root,
                    "CN",
                )

            mission = json.loads(
                (output_root / "missions" / "testm1.json").read_text(
                    encoding="utf-8"
                )
            )
            evidence = mission["nodes"][0]["dialogTreeDefinitions"][0]
            self.assertEqual("dlg_testm1_1", evidence["sceneKey"])
            self.assertEqual([{
                "relation": "objective_condition",
                "conditionType": "CheckTalkOptionFinish",
                "objectiveIndex": 1,
                "finishId": -1,
            }], evidence["missionObservers"])
            self.assertEqual(1, result["published"]["placements"])
            self.assertEqual(1, result["published"]["quests"])

    def test_publishes_repeatable_and_failed_condition_observers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "assets" / "dlg_testm1_1.json"
            source.parent.mkdir()
            source.write_bytes(b"dialog-tree-fixture")
            digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
            index, output_root, story_root = self.fixture(root, digest)
            mission_path = output_root / "missions" / "testm1.json"
            mission = json.loads(mission_path.read_text(encoding="utf-8"))
            node = mission["nodes"][0]
            node["objectives"][0]["condition"] = {
                "type": "CombineCondition",
                "children": [{
                    "type": "CheckRepeatableTalkFinish",
                    "facts": {"dialogId": "dlg_testm1_1", "finishId": -1},
                }],
            }
            node["failedCondition"] = {
                "type": "CheckTalkOptionFinish",
                "facts": {"dialogId": "dlg_testm1_1", "finishId": 2},
            }
            mission_path.write_text(json.dumps(mission), encoding="utf-8")

            with patch.object(pipeline, "ROOT", root):
                pipeline.publish_quest_dialog_tree_definitions(
                    index, output_root, story_root, "CN"
                )

            published = json.loads(mission_path.read_text(encoding="utf-8"))
            observers = published["nodes"][0]["dialogTreeDefinitions"][0][
                "missionObservers"
            ]
            self.assertEqual(
                ["objective_condition", "failed_condition"],
                [row["relation"] for row in observers],
            )
            self.assertEqual(
                ["CheckRepeatableTalkFinish", "CheckTalkOptionFinish"],
                [row["conditionType"] for row in observers],
            )

    def test_rejects_unplaced_definition_with_expected_actual_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "assets" / "dlg_testm1_1.json"
            source.parent.mkdir()
            source.write_bytes(b"dialog-tree-fixture")
            digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
            index, output_root, story_root = self.fixture(root, digest)
            mission_path = output_root / "missions" / "testm1.json"
            mission = json.loads(mission_path.read_text(encoding="utf-8"))
            mission["nodes"][0]["objectives"] = []
            mission_path.write_text(json.dumps(mission), encoding="utf-8")

            with patch.object(pipeline, "ROOT", root):
                with self.assertRaisesRegex(
                    ValueError,
                    r"mission=testm1.*expected=\['dlg_testm1_1'\].*actual=\[\]",
                ):
                    pipeline.publish_quest_dialog_tree_definitions(
                        index, output_root, story_root, "CN"
                    )

    def test_rejects_definition_source_hash_mismatch_with_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "assets" / "dlg_testm1_1.json"
            source.parent.mkdir()
            source.write_bytes(b"dialog-tree-fixture")
            expected = "0" * 64
            actual = hashlib.sha256(source.read_bytes()).hexdigest().upper()
            index, output_root, story_root = self.fixture(root, expected)

            with patch.object(pipeline, "ROOT", root):
                with self.assertRaisesRegex(
                    ValueError,
                    f"expected={expected} actual={actual}",
                ):
                    pipeline.publish_quest_dialog_tree_definitions(
                        index,
                        output_root,
                        story_root,
                        "CN",
                    )


if __name__ == "__main__":
    unittest.main()
