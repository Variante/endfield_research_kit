from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_presentation_data import graph_freshness_reason
from tools import endfield_source_graph


class SourceGraphAssetMapScopeTests(unittest.TestCase):
    def test_timeline_dialog_context_is_queryable_without_order_edge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mission_root = root / "mission_pipeline"
            mission_root.mkdir(parents=True)
            (mission_root / "index.json").write_text(
                json.dumps({
                    "storyCoverage": {
                        "storyTriggerManifest": {
                            "dlg_testm1_16": {
                                "routes": [{
                                    "storyKey": "dlg_testm1_16",
                                    "missionId": "testm1",
                                    "relation":
                                        "timeline_dialog_contains_"
                                        "foreign_dialog",
                                    "causality": "context",
                                    "ownerStatus": "connected",
                                    "graphEffect": "none",
                                    "parentStoryKey": "dlg_testm1_7",
                                    "timelineIds": [
                                        "dlgtl_testm1_7_sub_1",
                                    ],
                                    "embeddedLineIds": [
                                        "dlg_testm1_16_001",
                                        "dlg_testm1_16_002",
                                    ],
                                    "embeddedOptionIds": [
                                        "option_dlg_testm1_16_1_001",
                                    ],
                                    "beforeParentLineIds": [
                                        "dlg_testm1_7_009",
                                    ],
                                    "afterParentLineIds": [
                                        "dlg_testm1_7_005",
                                    ],
                                    "scriptIds": ["70000000001"],
                                    "eventNames": [
                                        "ScriptEvent_OnLeaderEnterTriggerVolume",
                                    ],
                                    "actionNames": [
                                        "StartDialogAndTeleportAction",
                                    ],
                                    "steps": [
                                        {
                                            "kind": "mission",
                                            "id": "testm1",
                                        },
                                        {
                                            "kind": "parent_story",
                                            "id": "dlg_testm1_7",
                                        },
                                        {
                                            "kind": "dialog_timeline",
                                            "ids": [
                                                "dlgtl_testm1_7_sub_1",
                                            ],
                                        },
                                        {
                                            "kind": "story",
                                            "id": "dlg_testm1_16",
                                        },
                                    ],
                                }],
                            },
                        },
                    },
                }),
                encoding="utf-8",
            )
            builder = endfield_source_graph.SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                include_asset_maps=False,
            )
            builder.open()
            try:
                with patch.object(
                    endfield_source_graph,
                    "MISSION_PIPELINE_ROOT",
                    mission_root,
                ):
                    builder.ingest_mission_pipeline_timeline_dialog_context()

                edges = {
                    (row[0], row[1], row[2]): json.loads(row[3])
                    for row in builder.db.execute(
                        "SELECT src, dst, kind, data FROM edges"
                    ).fetchall()
                }
                context_ids = {
                    row[0]
                    for row in builder.db.execute(
                        """
                        SELECT id FROM nodes
                        WHERE kind = 'mission_story_context'
                        """
                    ).fetchall()
                }
                self.assertEqual(1, len(context_ids))
                context_id = next(iter(context_ids))
                expected = {
                    (
                        "mission:testm1",
                        context_id,
                        "mission_has_timeline_dialog_playback_context",
                    ),
                    (
                        "story:dlg_testm1_7",
                        context_id,
                        "parent_story_supplies_timeline_dialog_context",
                    ),
                    (
                        "timeline:dlgtl_testm1_7_sub_1",
                        context_id,
                        "dialog_timeline_supplies_foreign_story_context",
                    ),
                    (
                        context_id,
                        "story:dlg_testm1_16",
                        "timeline_dialog_playback_context_targets_story",
                    ),
                }
                self.assertTrue(expected <= set(edges))
                for signature in expected:
                    self.assertFalse(edges[signature]["orderEvidence"])
                    self.assertFalse(edges[signature]["missionOwnership"])
                    self.assertEqual(edges[signature]["graphEffect"], "none")
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineTimelineDialogContext.rows"
                    ],
                    1,
                )
            finally:
                builder.close()

    def test_mission_submission_context_preserves_non_ownership_boundaries(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mission_root = root / "mission_pipeline" / "missions"
            mission_root.mkdir(parents=True)
            (mission_root / "testm1.json").write_text(
                json.dumps(
                    {
                        "mission": {"id": "testm1"},
                        "nodes": [
                            {
                                "id": "testm1_q#1",
                                "objectives": [
                                    {
                                        "index": 1,
                                        "submissionChecks": [
                                            {
                                                "submissionId": "submit_fixture",
                                                "conditionId": "submit_condition",
                                                "tableDefined": True,
                                                "requirementGroups": [
                                                    {
                                                        "index": 1,
                                                        "items": [
                                                            {
                                                                "itemId": "item_fixture",
                                                                "count": 1,
                                                            }
                                                        ],
                                                    }
                                                ],
                                            }
                                        ],
                                        "submissionDialogCoGates": [
                                            {
                                                "submissionId": "submit_fixture",
                                                "dialogId": "dlg_fixture_1",
                                                "finishId": -1,
                                                "combineConditionId": "combine_1",
                                                "relation": (
                                                    "same_authored_and_objective"
                                                ),
                                            }
                                        ],
                                        "submissionLevelScriptCoGates": [
                                            {
                                                "submissionId": "submit_fixture",
                                                "levelId": "map_fixture",
                                                "scriptId": "12345",
                                                "conditionId": "script_condition",
                                                "combineConditionId": "combine_2",
                                                "relation": (
                                                    "same_authored_and_objective"
                                                ),
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                        "storyOrder": {
                            "directEdges": [
                                {
                                    "from": "dlg_fixture_1",
                                    "to": "dlg_fixture_2",
                                    "kind": "levelscriptDialogExit",
                                    "tier": "strong",
                                    "sourceScript": "12345",
                                    "headerLocalId": 6,
                                    "targetLocalId": 7,
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            builder = endfield_source_graph.SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                include_asset_maps=False,
            )
            builder.open()
            try:
                builder.add_submit_item_node(
                    "submit_fixture",
                    source="SubmitItem",
                )
                with patch.object(
                    endfield_source_graph,
                    "MISSION_PIPELINE_ROOT",
                    root / "mission_pipeline",
                ):
                    builder.ingest_mission_pipeline_submission_context()

                required_edge = builder.db.execute(
                    """
                    SELECT data FROM edges
                    WHERE kind = 'quest_objective_requires_submit_item'
                    """
                ).fetchone()
                self.assertIsNotNone(required_edge)
                required_data = json.loads(required_edge[0])
                self.assertTrue(required_data["objectiveRequirement"])
                self.assertFalse(required_data["playbackOwnership"])
                self.assertFalse(required_data["openUiOwnership"])
                self.assertFalse(required_data["orderEvidence"])
                edge_kinds = {
                    row[0]
                    for row in builder.db.execute(
                        "SELECT kind FROM edges"
                    ).fetchall()
                }
                self.assertIn(
                    "quest_has_submission_dialog_co_gate",
                    edge_kinds,
                )
                self.assertIn(
                    "submission_dialog_co_gate_tests_dialog_finish",
                    edge_kinds,
                )
                self.assertIn(
                    "quest_has_submission_level_script_co_gate",
                    edge_kinds,
                )
                self.assertIn(
                    "submission_level_script_co_gate_tests_stage_max",
                    edge_kinds,
                )
                self.assertIn(
                    "level_script_exact_dialog_exit_trigger",
                    edge_kinds,
                )
                self.assertIn(
                    "level_script_exact_dialog_playback_target",
                    edge_kinds,
                )
                story_edge = builder.db.execute(
                    """
                    SELECT data FROM edges
                    WHERE kind = 'level_script_exact_dialog_playback_target'
                    """
                ).fetchone()
                self.assertIsNotNone(story_edge)
                story_data = json.loads(story_edge[0])
                self.assertEqual(story_data["headerLocalId"], 6)
                self.assertEqual(story_data["targetLocalId"], 7)
                self.assertFalse(story_data["openUiOwnership"])
                self.assertFalse(story_data["orderEvidence"])
            finally:
                builder.close()

    def test_mission_pipeline_story_scope_stays_non_owning_in_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mission_root = root / "mission_pipeline" / "missions"
            mission_root.mkdir(parents=True)
            (mission_root / "testm1.json").write_text(
                json.dumps(
                    {
                        "mission": {"id": "testm1"},
                        "nodes": [
                            {
                                "id": "testm1_q1",
                                "storyScopeContexts": [
                                    {
                                        "key": "radio_testm1_1",
                                        "relation": "quest_objective_levelscript_scope_context",
                                        "sourceRelation": "levelscript_mission_context",
                                        "confidence": "derived_exact_quest_scope",
                                        "scopeDiscriminator": (
                                            "exact_playback_path_quest_predicate"
                                        ),
                                        "questPredicateEvidence": [
                                            {
                                                "questId": "testm1_q1",
                                                "scriptId": "70000000001",
                                            }
                                        ],
                                        "ownershipStatus": "non_owning_context",
                                        "scriptIds": ["70000000001"],
                                    }
                                ],
                            }
                        ],
                        "flow": {
                            "sceneGraph": {
                                "edges": [{
                                    "from": "radio_testm1_1",
                                    "to": "cutscene_preload_only",
                                    "kind": "levelscriptSceneChain",
                                    "sourceFiles": ["preload-source.json"],
                                    "levelIds": ["level_preload"],
                                }],
                            },
                        },
                        "storyOrder": {
                            "nodes": [{
                                "key": "cutscene_other_owner_1",
                                "kind": "cutscene",
                                "membership":
                                    "exactLevelScriptPlaybackContext",
                                "relationStatus": "weak-only",
                            }],
                            "directEdges": [{
                                "from": "radio_testm1_1",
                                "to": "cutscene_other_owner_1",
                                "kind": "levelscriptSceneChain",
                                "sourceFiles": ["playback-source.json"],
                                "levelIds": ["level_playback"],
                            }],
                            "definitionOnlySourceNodes": [{
                                "key": "cutscene_preload_only",
                                "kind": "cutscene",
                                "incidentEdgeKinds": [
                                    "levelscriptSceneChain",
                                ],
                                "recordClasses": ["preload_cutscene"],
                            }],
                        },
                    }
                ),
                encoding="utf-8",
            )
            builder = endfield_source_graph.SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                include_asset_maps=False,
            )
            builder.open()
            try:
                with patch.object(
                    endfield_source_graph,
                    "MISSION_PIPELINE_ROOT",
                    root / "mission_pipeline",
                ):
                    builder.ingest_mission_pipeline_story_scope()

                row = builder.db.execute(
                    """
                    SELECT data FROM edges
                    WHERE kind = 'story_scoped_to_quest_via_objective_level_script'
                    """
                ).fetchone()
                self.assertIsNotNone(row)
                edge_data = json.loads(row[0])
                self.assertEqual(edge_data["ownershipStatus"], "non_owning_context")
                self.assertFalse(edge_data["playbackOwnership"])
                self.assertFalse(edge_data["orderEvidence"])
                self.assertEqual(
                    edge_data["scopeDiscriminator"],
                    "exact_playback_path_quest_predicate",
                )
                self.assertEqual(
                    edge_data["questPredicateEvidence"][0]["questId"],
                    "testm1_q1",
                )
                self.assertIsNotNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE kind = 'quest_objective_scopes_level_script'
                        """
                    ).fetchone()
                )
                context_row = builder.db.execute(
                    """
                    SELECT data FROM edges
                    WHERE kind =
                        'level_script_playback_context_targets_story'
                    """
                ).fetchone()
                self.assertIsNotNone(context_row)
                context_data = json.loads(context_row[0])
                self.assertEqual(
                    context_data["sourceFiles"],
                    ["playback-source.json"],
                )
                self.assertTrue(context_data["playbackTarget"])
                self.assertFalse(context_data["missionOwnership"])
                self.assertFalse(context_data["orderEvidence"])
                self.assertIsNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE src = 'mission:testm1'
                          AND dst = 'story:cutscene_other_owner_1'
                        """
                    ).fetchone()
                )
                definition_row = builder.db.execute(
                    """
                    SELECT data FROM edges
                    WHERE kind =
                        'mission_has_definition_only_story_reference'
                    """
                ).fetchone()
                self.assertIsNotNone(definition_row)
                definition_data = json.loads(definition_row[0])
                self.assertEqual(
                    definition_data["recordClasses"],
                    ["preload_cutscene"],
                )
                self.assertEqual(
                    definition_data["sourceFiles"],
                    ["preload-source.json"],
                )
                self.assertFalse(definition_data["playbackTarget"])
                self.assertFalse(
                    builder.node_exists(
                        "story",
                        "cutscene_preload_only",
                    )
                )
            finally:
                builder.close()

    def test_atmospheric_envtalk_context_is_queryable_and_non_owning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mission_root = root / "mission_pipeline" / "missions"
            mission_root.mkdir(parents=True)
            (mission_root / "alpha.json").write_text(
                json.dumps(
                    {
                        "mission": {"id": "alpha"},
                        "envTalkContext": [
                            {
                                "relation": "atmosphericSwitcherStateContext",
                                "storyKey": "env_envTalk_a_1",
                                "envTalkId": "envTalk_a_1",
                                "questIds": ["alpha_q#1"],
                                "conditionQuestIds": [
                                    "alpha_q#1",
                                    "missing_q#9",
                                ],
                                "conditionMissionIds": ["beta"],
                                "bindMissionId": "gamma",
                                "clusterId": "cluster_1",
                                "switcherId": "switcher_1",
                                "switcherGroupId": "group_1",
                                "levelId": "level_1",
                                "npcIds": ["npc_2", "npc_1"],
                            },
                            {
                                # Exact identity mismatch must fail closed.
                                "relation": "atmosphericSwitcherStateContext",
                                "storyKey": "env_wrong",
                                "envTalkId": "envTalk_a_2",
                                "clusterId": "cluster_2",
                                "switcherId": "switcher_2",
                                "switcherGroupId": "group_2",
                                "levelId": "level_1",
                                "npcIds": ["npc_3"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            builder = endfield_source_graph.SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                include_asset_maps=False,
            )
            builder.open()
            try:
                with patch.object(
                    endfield_source_graph,
                    "MISSION_PIPELINE_ROOT",
                    root / "mission_pipeline",
                ):
                    builder.ingest_mission_pipeline_env_talk_context()

                context_key = (
                    "switcher_1:group_1:cluster_1:env_envTalk_a_1"
                )
                node_ids = [
                    "mission:alpha",
                    f"atmospheric_env_talk_state_context:{context_key}",
                    "atmospheric_npc_switcher_group:group_1",
                    "atmospheric_npc_cluster:cluster_1",
                    "env_talk:envTalk_a_1",
                    "story:env_envTalk_a_1",
                ]
                edge_kinds = [
                    "mission_has_atmospheric_env_talk_state_context",
                    "atmospheric_env_talk_context_uses_switcher_group",
                    "atmospheric_switcher_group_contains_env_talk_cluster",
                    "atmospheric_cluster_uses_env_talk",
                    "env_talk_has_story_file",
                ]
                for source_id, target_id, edge_kind in zip(
                    node_ids,
                    node_ids[1:],
                    edge_kinds,
                ):
                    row = builder.db.execute(
                        """
                        SELECT data FROM edges
                        WHERE src = ? AND dst = ? AND kind = ?
                        """,
                        (source_id, target_id, edge_kind),
                    ).fetchone()
                    self.assertIsNotNone(row, edge_kind)
                    edge_data = json.loads(row[0])
                    self.assertEqual(edge_data["causality"], "context")
                    self.assertEqual(
                        edge_data["ownershipStatus"],
                        "non_owning_context",
                    )
                    self.assertFalse(edge_data["playbackOwnership"])
                    self.assertFalse(edge_data["orderEvidence"])

                self.assertIsNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE src = 'mission:alpha'
                          AND dst = 'story:env_envTalk_a_1'
                        """
                    ).fetchone()
                )
                self.assertIsNotNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE src = 'quest_task:alpha_q#1'
                          AND dst = 'mission:alpha'
                          AND kind = 'quest_task_in_mission'
                        """
                    ).fetchone()
                )
                self.assertIsNotNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE src = 'quest_task:missing_q#9'
                          AND kind =
                              'quest_state_conditions_atmospheric_env_talk_context'
                        """
                    ).fetchone()
                )
                self.assertIsNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE src = 'quest_task:missing_q#9'
                          AND kind = 'quest_task_in_mission'
                        """
                    ).fetchone()
                )
                self.assertIsNotNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE src = 'mission:beta'
                          AND kind =
                              'mission_state_conditions_atmospheric_env_talk_context'
                        """
                    ).fetchone()
                )
                self.assertIsNotNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE src = 'mission:gamma'
                          AND kind = 'mission_binds_atmospheric_env_talk_context'
                        """
                    ).fetchone()
                )
                source_rows = builder.db.execute(
                    """
                    SELECT kind, data FROM edges
                    WHERE source = 'webui/mission_pipeline/env_talk_context'
                    """
                ).fetchall()
                self.assertTrue(source_rows)
                for edge_kind, edge_json in source_rows:
                    edge_data = json.loads(edge_json)
                    self.assertEqual(
                        edge_data["ownershipStatus"],
                        "non_owning_context",
                        edge_kind,
                    )
                    self.assertFalse(
                        edge_data["playbackOwnership"],
                        edge_kind,
                    )
                    self.assertFalse(edge_data["orderEvidence"], edge_kind)
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineEnvTalkContext.rows"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineEnvTalkContext.uniqueContexts"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineEnvTalkContext.missions"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineEnvTalkContext.storyFiles"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineEnvTalkContext.conditionQuestIds"
                    ],
                    2,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineEnvTalkContext.skippedRows"
                    ],
                    1,
                )
            finally:
                builder.close()

    def test_native_runtime_receiver_is_queryable_without_mission_owner(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mission_root = root / "mission_pipeline"
            mission_root.mkdir(parents=True)
            valid_source = (
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelScriptData/level_1/1001.json"
            )
            duplicate_source = (
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelScriptData/level_2/2002.json"
            )
            (mission_root / "index.json").write_text(
                json.dumps({
                    "schemaVersion": 4,
                    "storyCoverage": {
                        "missionlessNativeRuntimeNodes": [{
                            "relation":
                                "exact_native_runtime_receiver_playback",
                            "confidence":
                                "exact_current_build_memorypack_fields",
                            "missionOwnerStatus": "unresolved",
                            "storyBinding": False,
                            "eventName":
                                "ScriptEvent_OnLeaderEnterTriggerVolume",
                            "eventSummary":
                                "leader enters trigger slot 80001",
                            "payloadSchemaMappingId":
                                "gameassembly-test-memorypack-fields",
                            "selector": {
                                "levelId": "level_1",
                                "listenerScriptId": "1001",
                                "listenerHeaderLocalId": 0,
                                "triggerSlotIdFilter": 80001,
                            },
                            "serverExchange": False,
                            "transport":
                                "local-authored-trigger-volume-event",
                            "storyFiles": [{
                                "key": "radio_a",
                                "kind": "radio",
                                "nativeActions": ["PlayRadio"],
                                "sourceFiles": [valid_source],
                            }],
                        }, {
                            # Exact source identity mismatch must fail closed.
                            "relation":
                                "exact_native_runtime_receiver_playback",
                            "confidence":
                                "exact_current_build_memorypack_fields",
                            "missionOwnerStatus": "unresolved",
                            "storyBinding": False,
                            "eventName": "LevelEvent_OnBattleSignal",
                            "payloadSchemaMappingId":
                                "gameassembly-test-memorypack-fields",
                            "selector": {
                                "levelId": "level_2",
                                "listenerScriptId": "2002",
                                "listenerHeaderLocalId": 3,
                            },
                            "storyFiles": [{
                                "key": "radio_bad",
                                "kind": "radio",
                                "nativeActions": ["PlayRadio"],
                                "sourceFiles": [valid_source],
                            }],
                        }, {
                            # Duplicate receiver identities also fail closed.
                            "relation":
                                "exact_native_runtime_receiver_playback",
                            "confidence":
                                "exact_current_build_memorypack_fields",
                            "missionOwnerStatus": "unresolved",
                            "storyBinding": False,
                            "eventName": "LevelEvent_OnBattleSignal",
                            "payloadSchemaMappingId":
                                "gameassembly-test-memorypack-fields",
                            "selector": {
                                "levelId": "level_2",
                                "listenerScriptId": "2002",
                                "listenerHeaderLocalId": 3,
                            },
                            "storyFiles": [{
                                "key": "radio_duplicate",
                                "kind": "radio",
                                "nativeActions": ["PlayRadio"],
                                "sourceFiles": [duplicate_source],
                            }],
                        }],
                    },
                }),
                encoding="utf-8",
            )
            builder = endfield_source_graph.SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                include_asset_maps=False,
            )
            builder.open()
            try:
                with patch.object(
                    endfield_source_graph,
                    "MISSION_PIPELINE_ROOT",
                    mission_root,
                ):
                    builder.ingest_mission_pipeline_native_runtime_receivers()

                receiver_id = "native_runtime_receiver:level_1:1001:0"
                expected_edges = [
                    (
                        receiver_id,
                        "native_runtime_event:"
                        "ScriptEvent_OnLeaderEnterTriggerVolume",
                        "native_runtime_receiver_uses_event",
                    ),
                    (
                        receiver_id,
                        "level_script:1001",
                        "native_runtime_receiver_uses_level_script",
                    ),
                    (
                        receiver_id,
                        "level:level_1",
                        "native_runtime_receiver_in_level",
                    ),
                    (
                        receiver_id,
                        "story:radio_a",
                        "native_runtime_receiver_reaches_story",
                    ),
                    (
                        "story:radio_a",
                        receiver_id,
                        "story_has_unresolved_native_runtime_receiver",
                    ),
                ]
                for source_id, target_id, edge_kind in expected_edges:
                    row = builder.db.execute(
                        """
                        SELECT data FROM edges
                        WHERE src = ? AND dst = ? AND kind = ?
                        """,
                        (source_id, target_id, edge_kind),
                    ).fetchone()
                    self.assertIsNotNone(row, edge_kind)
                    edge_data = json.loads(row[0])
                    self.assertEqual(
                        edge_data["missionOwnerStatus"],
                        "unresolved",
                    )
                    self.assertFalse(edge_data["missionStoryBinding"])
                    self.assertTrue(edge_data["playbackEvidence"])
                    self.assertFalse(edge_data["playbackOwnership"])
                    self.assertFalse(edge_data["orderEvidence"])

                self.assertIsNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM edges
                        WHERE source =
                            'webui/mission_pipeline/native_runtime_receivers'
                          AND (
                            src LIKE 'mission:%'
                            OR dst LIKE 'mission:%'
                            OR src LIKE 'quest_task:%'
                            OR dst LIKE 'quest_task:%'
                          )
                        """
                    ).fetchone()
                )
                self.assertIsNone(
                    builder.db.execute(
                        """
                        SELECT 1 FROM nodes
                        WHERE id = 'native_runtime_receiver:level_2:2002:3'
                        """
                    ).fetchone()
                )
                source_rows = builder.db.execute(
                    """
                    SELECT kind, data FROM edges
                    WHERE source =
                        'webui/mission_pipeline/native_runtime_receivers'
                    """
                ).fetchall()
                self.assertTrue(source_rows)
                for edge_kind, edge_json in source_rows:
                    edge_data = json.loads(edge_json)
                    self.assertEqual(
                        edge_data["missionOwnerStatus"],
                        "unresolved",
                        edge_kind,
                    )
                    self.assertFalse(
                        edge_data["missionStoryBinding"],
                        edge_kind,
                    )
                    self.assertTrue(
                        edge_data["playbackEvidence"],
                        edge_kind,
                    )
                    self.assertFalse(
                        edge_data["missionOwnershipEvidence"],
                        edge_kind,
                    )
                    self.assertFalse(edge_data["orderEvidence"], edge_kind)
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineNativeRuntimeReceivers.rows"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineNativeRuntimeReceivers.uniqueReceivers"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineNativeRuntimeReceivers.storyFiles"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineNativeRuntimeReceivers.eventFamilies"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineNativeRuntimeReceivers.levels"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineNativeRuntimeReceivers.mappingIds"
                    ],
                    1,
                )
                self.assertEqual(
                    builder.ingest_counts[
                        "missionPipelineNativeRuntimeReceivers.skippedRows"
                    ],
                    2,
                )
            finally:
                builder.close()

    def test_video_bindings_prefer_existing_exact_scene_and_keep_source_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            recovered = root / "recovered"
            recovered.mkdir()
            (recovered / "video_bindings.json").write_text(
                json.dumps(
                    {
                        "bindings": {
                            "cs_video_dlg_e9m2_3": {
                                "fmvId": "cs_video_dlg_e9m2_3",
                                "scene": "cutscene_dlg_e9m2_3",
                                "mission": "e9m2",
                                "fallbackSceneHint": "dlg_e9m2_3",
                                "sources": [{
                                    "kind": "levelscriptFmvAction",
                                    "sourceFile": "export_full/levelscript.json",
                                }],
                            },
                            "cs_video_dlg_e10m1_1": {
                                "fmvId": "cs_video_dlg_e10m1_1",
                                "scene": "e10m1_1",
                                "fallbackSceneHint": "dlg_e10m1_1",
                                "sources": [{
                                    "kind": "timelinePlayable",
                                    "asset": "export_full/playable.json",
                                }],
                            },
                        },
                        "definitions": {
                            "cs_video_e1m3_3": {
                                "fmvId": "cs_video_e1m3_3",
                                "numericIds": [18],
                                "placementEvidence": False,
                                "videos": [
                                    (
                                        "export_full/structured/"
                                        "StreamingAssets/Data/Video/PC/"
                                        "Narrative/Cutscene/"
                                        "cs_video_e1m3_3.mp4"
                                    )
                                ],
                                "sources": [{
                                    "kind": "fmvConfigDefinition",
                                    "asset": (
                                        "export_full/recovered/"
                                        "cs_video_e1m3_3.json"
                                    ),
                                    "pathId": 100,
                                    "defaultPlayablePathId": 200,
                                }],
                                "timelineEvidence": {
                                    "subtitleTextIds": [
                                        "fmv_e1m3_3_01"
                                    ],
                                    "audioEventKeys": [
                                        "au_vo_fmv_e1m3_3"
                                    ],
                                    "placementEvidence": False,
                                },
                            }
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            builder = endfield_source_graph.SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                include_asset_maps=False,
            )
            builder.open()
            try:
                builder.add_node("story", "cutscene_dlg_e9m2_3")
                builder.add_node("story", "dlg_e10m1_1")
                with patch.object(
                    endfield_source_graph,
                    "EXPORT_ROOT",
                    root,
                ):
                    builder.ingest_video_bindings()

                targets = {
                    row[0]: (row[1], row[2])
                    for row in builder.db.execute(
                        """
                        SELECT src, dst, evidence
                        FROM edges
                        WHERE kind = 'fmv_binding_targets_story'
                        """
                    ).fetchall()
                }
                self.assertEqual(
                    targets[
                        "fmv_binding:cs_video_dlg_e9m2_3"
                    ],
                    ("story:cutscene_dlg_e9m2_3", "scene"),
                )
                self.assertEqual(
                    targets[
                        "fmv_binding:cs_video_dlg_e10m1_1"
                    ],
                    ("story:dlg_e10m1_1", "fallbackSceneHint"),
                )
                source_edges = {
                    (row[0], row[1])
                    for row in builder.db.execute(
                        """
                        SELECT dst, evidence
                        FROM edges
                        WHERE kind = 'fmv_binding_source_file'
                        """
                    ).fetchall()
                }
                self.assertIn(
                    (
                        "file:export_full/levelscript.json",
                        "sources[0].sourceFile",
                    ),
                    source_edges,
                )
                definition_data = json.loads(
                    builder.db.execute(
                        """
                        SELECT data
                        FROM nodes
                        WHERE id = 'fmv_definition:cs_video_e1m3_3'
                        """
                    ).fetchone()[0]
                )
                self.assertFalse(
                    definition_data["placementEvidence"]
                )
                self.assertFalse(
                    definition_data["hasAuthoritativeBinding"]
                )
                definition_edges = {
                    (row[0], row[1])
                    for row in builder.db.execute(
                        """
                        SELECT kind, dst
                        FROM edges
                        WHERE src =
                            'fmv_definition:cs_video_e1m3_3'
                        """
                    ).fetchall()
                }
                self.assertIn(
                    (
                        "fmv_definition_resolves_video",
                        (
                            "video:StreamingAssets-structured/"
                            "Data/Video/PC/Narrative/Cutscene/"
                            "cs_video_e1m3_3.mp4"
                        ),
                    ),
                    definition_edges,
                )
                self.assertIn(
                    (
                        "fmv_definition_subtitle_text",
                        "text_key:fmv_e1m3_3_01",
                    ),
                    definition_edges,
                )
                self.assertIn(
                    (
                        "fmv_definition_audio_event",
                        "audio:au_vo_fmv_e1m3_3",
                    ),
                    definition_edges,
                )
                self.assertIn(
                    (
                        "fmv_definition_pathid",
                        "unity_pathid:100",
                    ),
                    definition_edges,
                )
                self.assertNotIn(
                    (
                        "fmv_binding_targets_story",
                        "story:dlg_e1m3_3",
                    ),
                    definition_edges,
                )
                self.assertIn(
                    (
                        "file:export_full/playable.json",
                        "sources[0].asset",
                    ),
                    source_edges,
                )
            finally:
                builder.close()

    def test_relevant_scope_keeps_only_consumed_original_map_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asset_map = root / "AssetMap.json"
            asset_map.write_text(
                json.dumps(
                    {
                        "AssetEntries": [
                            {"PathID": 10, "Name": "used_texture", "Type": "Texture2D"},
                            {"PathID": 20, "Name": "used_fmv", "Type": "VideoClip"},
                            {"PathID": 99, "Name": "unrelated", "Type": "Texture2D"},
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            builder = endfield_source_graph.SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                include_asset_maps=True,
                relevant_asset_maps_only=True,
            )
            builder.open()
            try:
                material = builder.add_node(
                    "material",
                    "mat_test",
                    source="StreamingAssets",
                )
                texture_pathid = builder.add_node("unity_pathid", 10)
                builder.add_edge(material, texture_pathid, "uses_texture_pathid")

                fmv = builder.add_node("video_binding", "fmv_test", source="video_bindings")
                fmv_pathid = builder.add_node("unity_pathid", 20)
                builder.add_edge(
                    fmv,
                    fmv_pathid,
                    "fmv_binding_playable_pathid",
                    data={"sourceRoot": "StreamingAssets"},
                )

                with patch.object(
                    endfield_source_graph,
                    "ASSET_MAPS",
                    {"StreamingAssets": asset_map},
                ):
                    builder.ingest_asset_maps()

                unity_ids = {
                    row[0]
                    for row in builder.db.execute(
                        "SELECT id FROM nodes WHERE kind = 'unity_asset'"
                    ).fetchall()
                }
                self.assertEqual(
                    unity_ids,
                    {
                        "unity_asset:StreamingAssets:10",
                        "unity_asset:StreamingAssets:20",
                    },
                )
                self.assertEqual(builder.ingest_counts["assetMaps.relevantPathIds"], 2)
                self.assertEqual(builder.ingest_counts["assetMaps.matchedPathIds"], 2)
                self.assertEqual(builder.ingest_counts["assetMaps.matchedEntries"], 2)
            finally:
                builder.close()

    def test_presentation_rejects_explicit_no_map_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            graph = Path(temp_dir) / "graph.sqlite"
            connection = sqlite3.connect(graph)
            try:
                connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
                connection.execute("CREATE TABLE nodes (id TEXT, kind TEXT)")
                connection.execute(
                    "INSERT INTO meta(key, value) VALUES ('asset_map_scope', 'none')"
                )
                connection.commit()
            finally:
                connection.close()

            reason = graph_freshness_reason(graph)

            self.assertIn("asset-map scope is none", reason)

    def test_presentation_rejects_legacy_graph_without_unity_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            graph = Path(temp_dir) / "graph.sqlite"
            connection = sqlite3.connect(graph)
            try:
                connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
                connection.execute("CREATE TABLE nodes (id TEXT, kind TEXT)")
                connection.commit()
            finally:
                connection.close()

            reason = graph_freshness_reason(graph)

            self.assertIn("asset-map scope is none", reason)

    def test_presentation_rejects_incomplete_relevant_scope_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            graph = Path(temp_dir) / "graph.sqlite"
            connection = sqlite3.connect(graph)
            try:
                connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
                connection.execute("CREATE TABLE nodes (id TEXT, kind TEXT)")
                connection.execute(
                    "INSERT INTO meta(key, value) VALUES ('asset_map_scope', 'relevant')"
                )
                connection.execute(
                    "INSERT INTO nodes(id, kind) VALUES ('unity_asset:test', 'unity_asset')"
                )
                connection.commit()
            finally:
                connection.close()

            reason = graph_freshness_reason(graph)

            self.assertIn("no completed coverage metadata", reason)


if __name__ == "__main__":
    unittest.main()
