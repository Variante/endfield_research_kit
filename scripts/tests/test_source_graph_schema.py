from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.endfield_source_graph import (
    SourceGraphBuilder,
    classify_story_audio_reference,
    story_line_audio_candidates,
)


class SourceGraphSchemaTests(unittest.TestCase):
    def test_pathless_story_audio_classification_keeps_evidence_separate(self) -> None:
        self.assertEqual(
            classify_story_audio_reference(
                "au_radio_fixture_001",
                "dialog_line",
                {"radio_line"},
                False,
            ),
            {
                "family": "radio",
                "evidenceClass": "owner_table_without_path",
                "ownerKinds": ["radio_line"],
            },
        )
        self.assertEqual(
            classify_story_audio_reference(
                "au_sfx_fixture",
                "dialog_line",
                set(),
                True,
            )["evidenceClass"],
            "wwise_event_media_candidate",
        )
        self.assertEqual(
            classify_story_audio_reference("#N/A", "dialog_line", {"env_talk"}, False)[
                "evidenceClass"
            ],
            "placeholder",
        )

    def test_unique_indexes_cover_source_and_alias_lookups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = SourceGraphBuilder(db_path=Path(temp_dir) / "graph.sqlite")
            builder.open()
            try:
                edge_indexes = {
                    row[1] for row in builder.db.execute("PRAGMA index_list(edges)")
                }
                alias_indexes = {
                    row[1] for row in builder.db.execute("PRAGMA index_list(aliases)")
                }
                self.assertNotIn("idx_edges_src", edge_indexes)
                self.assertNotIn("idx_aliases_alias", alias_indexes)
                self.assertIn("sqlite_autoindex_edges_1", edge_indexes)
                self.assertIn("sqlite_autoindex_aliases_1", alias_indexes)

                source = builder.add_node("test", "source")
                destination = builder.add_node("test", "destination")
                builder.add_edge(source, destination, "test_edge")
                builder.add_alias("source_alias", source, kind="test")

                edge_plan = " ".join(
                    str(value)
                    for row in builder.db.execute(
                        "EXPLAIN QUERY PLAN SELECT dst FROM edges WHERE src = ?",
                        (source,),
                    )
                    for value in row
                )
                alias_plan = " ".join(
                    str(value)
                    for row in builder.db.execute(
                        "EXPLAIN QUERY PLAN SELECT node_id FROM aliases WHERE alias = ?",
                        ("source_alias",),
                    )
                    for value in row
                )
                self.assertIn("sqlite_autoindex_edges_1", edge_plan)
                self.assertIn("sqlite_autoindex_aliases_1", alias_plan)
                self.assertEqual(builder.alias_node_ids("source_alias"), [source])
            finally:
                builder.close()

    def test_audio_dialog_backfills_story_created_audio_node(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = SourceGraphBuilder(db_path=Path(temp_dir) / "graph.sqlite")
            builder.open()
            try:
                line_node = builder.add_node(
                    "line",
                    "dlg_fixture_001",
                    source="webui/story",
                    data={"audio": "au_fixture"},
                )
                audio_node = builder.add_node(
                    "audio",
                    "au_fixture",
                    source="dialog_line",
                )
                builder.add_edge(
                    line_node,
                    audio_node,
                    "uses_audio",
                    source="webui/story",
                )
                row_node = builder.add_node(
                    "table_row",
                    "AudioDialog:fixture",
                    source="AudioDialog",
                )
                builder.add_structured_row_edges(
                    "AudioDialog",
                    "fixture",
                    {
                        "path": "v1d0/Narrating/SubChar/fixture/au_fixture.wem",
                        "speakerChannel": "fixture_actor",
                        "wavDuration": 1.25,
                        "voType": 4,
                        "codec": "vorbis",
                    },
                    row_node,
                )

                path, source, raw_data = builder.db.execute(
                    "SELECT path, source, data FROM nodes WHERE id = ?",
                    (audio_node,),
                ).fetchone()
                self.assertEqual(path, "v1d0/Narrating/SubChar/fixture/au_fixture.wem")
                self.assertEqual(source, "AudioDialog")
                self.assertEqual(
                    json.loads(raw_data),
                    {
                        "id": "fixture",
                        "speaker": "fixture_actor",
                        "duration": 1.25,
                        "path": "v1d0/Narrating/SubChar/fixture/au_fixture.wem",
                        "voType": 4,
                        "codec": "vorbis",
                    },
                )
                linked_path = builder.db.execute(
                    """
                    SELECT audio.path
                    FROM edges AS edge
                    JOIN nodes AS audio ON audio.id = edge.dst
                    WHERE edge.src = ? AND edge.kind = 'uses_audio'
                    """,
                    (line_node,),
                ).fetchone()[0]
                self.assertEqual(
                    linked_path,
                    "v1d0/Narrating/SubChar/fixture/au_fixture.wem",
                )
            finally:
                builder.close()

    def test_audio_table_payload_merges_persistent_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            export_root = Path(temp_dir) / "export"
            for layer in ("StreamingAssets", "Persistent"):
                (export_root / "structured" / layer / "Table").mkdir(parents=True)
            (export_root / "structured" / "StreamingAssets" / "Table" / "AudioDialog.json").write_text(
                json.dumps(
                    {
                        "stream_only": {"path": "stream/stream_only.wem"},
                        "shared": {"path": "stream/shared.wem"},
                    }
                ),
                encoding="utf-8",
            )
            (export_root / "structured" / "Persistent" / "Table" / "AudioDialog.json").write_text(
                json.dumps(
                    {
                        "shared": {"path": "persistent/shared.wem"},
                        "persistent_only": {"path": "persistent/persistent_only.wem"},
                    }
                ),
                encoding="utf-8",
            )
            builder = SourceGraphBuilder(
                db_path=Path(temp_dir) / "graph.sqlite",
                export_root=export_root,
            )
            payload, sources = builder.structured_table_payload(
                "AudioDialog.json",
                include_persistent=True,
            )
            self.assertEqual(payload["shared"]["path"], "persistent/shared.wem")
            self.assertEqual(sorted(payload), ["persistent_only", "shared", "stream_only"])
            self.assertEqual([layer for layer, _path in sources], ["StreamingAssets", "Persistent"])
            self.assertEqual(
                builder.audio_dialog_rows()["persistent_only"]["path"],
                "persistent/persistent_only.wem",
            )

    def test_story_line_keeps_remote_event_and_voice_id_as_separate_candidates(self) -> None:
        line = {
            "id": "remotecomm_fixture_001",
            "actor": "Fixture",
            "aid": "fixture_actor",
            "audio": "au_sfx_remotecomm_fixture",
            "_debug": {
                "source": {
                    "audioOverride": "au_sfx_remotecomm_fixture",
                    "voiceId": "au_remotecomm_fixture_001",
                }
            },
        }
        self.assertEqual(
            story_line_audio_candidates(line),
            [
                ("au_sfx_remotecomm_fixture", "line.audio"),
                ("au_remotecomm_fixture_001", "line._debug.source.voiceId"),
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = SourceGraphBuilder(db_path=Path(temp_dir) / "graph.sqlite")
            builder.open()
            try:
                story_node = builder.add_story_node("remotecomm_fixture", {"lines": [line]})
                builder.add_lines_and_options(
                    {"key": "remotecomm_fixture", "lines": [line]},
                    story_node,
                )
                voice_row_node = builder.add_node(
                    "table_row",
                    "AudioDialog:remotecomm_fixture",
                    source="AudioDialog",
                )
                builder.add_structured_row_edges(
                    "AudioDialog",
                    "remotecomm_fixture",
                    {"path": "v1d0/Narrating/Fixture/au_remotecomm_fixture_001.wem"},
                    voice_row_node,
                )
                line_node = builder.node_id("line", "remotecomm_fixture_001")
                rows = builder.db.execute(
                    """
                    SELECT audio.name, audio.path, edge.evidence
                    FROM edges AS edge
                    JOIN nodes AS audio ON audio.id = edge.dst
                    WHERE edge.src = ? AND edge.kind = 'uses_audio'
                    ORDER BY audio.name
                    """,
                    (line_node,),
                ).fetchall()
                self.assertEqual(
                    [(row[0], row[1], row[2]) for row in rows],
                    [
                        ("au_remotecomm_fixture_001", "v1d0/Narrating/Fixture/au_remotecomm_fixture_001.wem", "line._debug.source.voiceId"),
                        ("au_sfx_remotecomm_fixture", None, "line.audio"),
                    ],
                )
            finally:
                builder.close()

    def test_audio_trigger_contexts_add_static_context_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_path = root / "webui" / "data" / "lang" / "CN" / "audio" / "trigger_contexts.json"
            context_path.parent.mkdir(parents=True)
            context_path.write_text(
                json.dumps(
                    {
                        "schema": 4,
                        "language": "CN",
                        "counts": {"total": 1},
                        "contexts": [
                            {
                                "triggerId": "radio:fixture",
                                "semanticKind": "radio",
                                "triggerRole": "play",
                                "situation": {
                                    "radioId": "radio_fixture",
                                    "lineId": "radio_fixture_001",
                                    "levelScriptId": "level_fixture",
                                },
                                "meaning": {
                                    "id": "radio_fixture_001",
                                    "audio": "au_fixture",
                                    "eventId": "au_sfx_fixture",
                                },
                                "action": {"levelScriptId": "level_fixture"},
                                "selection": {"mediaSelectionStatus": "playable"},
                                "mediaRefs": [{"id": "au_fixture"}],
                                "runtimeActivationStatus": "unobserved",
                                "sourceRefs": ["fixture.json"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                for kind, key in (
                    ("audio", "au_fixture"),
                    ("wwise_event", "au_sfx_fixture"),
                    ("radio", "radio_fixture"),
                    ("line", "radio_fixture_001"),
                    ("level_script", "level_fixture"),
                ):
                    builder.add_node(kind, key, source="fixture")
                builder.ingest_audio_trigger_contexts()
                context_node = builder.node_id("audio_trigger_context", "radio:fixture")
                self.assertTrue(builder.node_exists("audio_trigger_context", "radio:fixture"))
                edges = {
                    row[0]
                    for row in builder.db.execute(
                        "SELECT kind FROM edges WHERE src = ?",
                        (context_node,),
                    )
                }
                self.assertIn("audio_trigger_context_uses_audio", edges)
                self.assertIn("audio_trigger_context_targets_wwise_event", edges)
                self.assertIn("audio_trigger_context_for_radio", edges)
                self.assertIn("audio_trigger_context_for_line", edges)
                self.assertIn("audio_trigger_context_for_level_script", edges)
                boundary = json.loads(
                    builder.db.execute(
                        "SELECT data FROM nodes WHERE id = ?",
                        (context_node,),
                    ).fetchone()[0]
                )["evidenceBoundary"]
                self.assertIn("not runtime ownership", boundary)
            finally:
                builder.close()

    def test_external_audio_media_identity_does_not_infer_playback_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            media_path = root / "webui" / "data" / "lang" / "CN" / "audio" / "media.json"
            media_path.parent.mkdir(parents=True)
            media_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 49,
                        "language": "CN",
                        "media": [
                            {
                                "id": "955778167792087661",
                                "rel": "wwise/unknown/955778167792087661.flac",
                                "storageRoot": "CN",
                                "format": "flac",
                                "externalMediaIdentityStatus": "recoveredAuthoredPathHash",
                                "externalAuthoredAudioId": "au_voice_c35m3_3_001",
                                "externalAuthoredPath": "v1d4/Narrating/HS_Part04/c35m3/au_voice_c35m3_3_001.wem",
                                "externalIdentityEvidence": "boundedD4MissionVoiceNamespaceUniqueFNV1a64Preimage",
                                "identityOnlyPlaybackPlacementStatus": "identityOnlyNoCurrentAudioDialogOrTrigger",
                                "playbackLocationStatus": "unknown",
                                "purposeKnowledgeStatus": "unknownUse",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export_full",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                builder.ingest_external_audio_media_identities()
                audio_node = builder.node_id("audio", "au_voice_c35m3_3_001")
                self.assertTrue(builder.node_exists("audio", "au_voice_c35m3_3_001"))
                self.assertTrue(builder.node_exists("wwise_media", "955778167792087661"))
                node = builder.db.execute(
                    "SELECT path, data FROM nodes WHERE id = ?",
                    (audio_node,),
                ).fetchone()
                self.assertEqual(
                    node[0],
                    "v1d4/Narrating/HS_Part04/c35m3/au_voice_c35m3_3_001.wem",
                )
                self.assertEqual(json.loads(node[1])["playbackLocationStatus"], "unknown")
                edges = {
                    row[0]
                    for row in builder.db.execute(
                        "SELECT kind FROM edges WHERE src = ? OR dst = ?",
                        (audio_node, audio_node),
                    )
                }
                self.assertIn("has_external_audio_media_identity", edges)
                self.assertIn("audio_identity_matches_wwise_media", edges)
                self.assertIn("audio_identity_decoded_file", edges)
                self.assertFalse(
                    any(
                        marker in edge
                        for edge in edges
                        for marker in ("trigger", "story", "line", "speaker")
                    )
                )
                self.assertEqual(
                    builder.alias_node_ids("955778167792087661"),
                    [audio_node, builder.node_id("wwise_media", "955778167792087661")],
                )
            finally:
                builder.close()

    def test_audio_event_library_relation_does_not_create_trigger_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            events_path = root / "webui" / "data" / "lang" / "CN" / "audio" / "events.json"
            events_path.parent.mkdir(parents=True)
            events_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 47,
                        "language": "CN",
                        "events": [
                            {
                                "id": "hashed-event:0x12345678",
                                "audioLibraryPlaybackTargetStatus": "exactSharedPlayTargetSetWithAuthoredEvent",
                                "audioLibraryEquivalentEventIds": ["au_ui_known"],
                                "audioLibraryEquivalentCategories": ["ui"],
                                "audioLibrarySharedPlayTargetSets": [
                                    {"bank": "default_banks.pck", "targetIds": [100, 200]}
                                ],
                                "audioLibraryPurposeHintStatus": "libraryOutputEquivalentOnlyExternalTriggerUnknown",
                                "audioLibraryMediaLeafStatus": "exactCompleteWwiseMediaIdSetWithAuthoredEvent",
                                "audioLibraryMediaEquivalentEventIds": ["au_ui_media_known"],
                                "audioLibraryMediaEquivalentCategories": ["ui"],
                                "audioLibrarySharedMediaIds": [300],
                                "audioLibrarySharedMediaPackages": ["default_banks.pck"],
                                "audioLibraryMediaPurposeHintStatus": "completeMediaLeafSetEquivalentOnlyContainersAndExternalTriggerUnknown",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export_full",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                builder.ingest_audio_event_library_relations()
                event_node = builder.node_id("wwise_event", "hashed-event:0x12345678")
                equivalent_node = builder.node_id("wwise_event", "au_ui_known")
                edges = builder.db.execute(
                    "SELECT kind, dst FROM edges WHERE src = ? ORDER BY kind, dst",
                    (event_node,),
                ).fetchall()
                self.assertIn(
                    ("wwise_event_shares_exact_play_target_set", equivalent_node),
                    edges,
                )
                self.assertIn(
                    (
                        "wwise_event_shares_exact_media_leaf_set",
                        builder.node_id("wwise_event", "au_ui_media_known"),
                    ),
                    edges,
                )
                self.assertFalse(
                    any(
                        marker in kind
                        for kind, _dst in edges
                        for marker in ("trigger", "story", "line", "speaker")
                    )
                )
            finally:
                builder.close()

    def test_audio_trigger_contexts_link_anonymous_event_to_audio_node(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_path = root / "webui/data/lang/CN/audio/trigger_contexts.json"
            context_path.parent.mkdir(parents=True)
            context_path.write_text(json.dumps({
                "schemaVersion": 6,
                "language": "CN",
                "counts": {"total": 1},
                "contexts": [{
                    "triggerId": "mono:fixture",
                    "semanticKind": "monoBehaviourAudioIdField",
                    "situation": {"eventId": "hashed-event:0x12345678"},
                    "meaning": {"eventId": "hashed-event:0x12345678", "foundInWwise": True},
                    "owner": {
                        "serializedFile": "CAB-fixture",
                        "pathId": 7,
                        "managedReferenceClass": "PlayLineSound",
                        "managedReferenceAssembly": "Gameplay.Beyond",
                        "managedReferencePayloadLength": 24,
                        "managedReferenceDecodeStatus": "strictStructuredDecoder",
                    },
                    "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
                    "sourceRefs": ["fixture.json"],
                }],
            }), encoding="utf-8")
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                builder.ingest_audio_trigger_contexts()
                context_node = builder.node_id("audio_trigger_context", "mono:fixture")
                audio_node = builder.node_id("audio", "hashed-event:0x12345678")
                edges = {
                    (row[0], row[1])
                    for row in builder.db.execute(
                        "SELECT kind, dst FROM edges WHERE src = ?",
                        (context_node,),
                    )
                }
                self.assertIn(
                    ("audio_trigger_context_targets_audio_event", audio_node),
                    edges,
                )
                data = json.loads(builder.db.execute(
                    "SELECT data FROM nodes WHERE id = ?", (context_node,),
                ).fetchone()[0])
                self.assertEqual(data["owner"]["managedReferenceClass"], "PlayLineSound")
                self.assertEqual(data["owner"]["managedReferenceAssembly"], "Gameplay.Beyond")
                self.assertEqual(data["owner"]["managedReferencePayloadLength"], 24)
                self.assertEqual(
                    data["owner"]["managedReferenceDecodeStatus"],
                    "strictStructuredDecoder",
                )
                forbidden = {
                    kind for kind, _dst in edges
                    if any(token in kind for token in ("story", "line", "actor", "execut"))
                }
                self.assertEqual(forbidden, set())
            finally:
                builder.close()

    def test_audio_global_context_keeps_lifecycle_state_without_execution_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_path = root / "webui/data/lang/CN/audio/trigger_contexts.json"
            context_path.parent.mkdir(parents=True)
            context_path.write_text(json.dumps({
                "schemaVersion": 7,
                "language": "CN",
                "counts": {"total": 1},
                "contexts": [{
                    "triggerId": "global:fixture",
                    "semanticKind": "audioGlobalConfigEventHash",
                    "triggerRole": "audioStateTransitionEvent",
                    "situation": {
                        "eventId": "hashed-event:0x12345678",
                        "serializedFieldPath": "audioStatesIn._valueData[0]._ids[0]",
                        "stateDirection": "enter",
                        "audioStateMask": 512,
                    },
                    "meaning": {
                        "eventId": "hashed-event:0x12345678",
                        "foundInWwise": True,
                        "playbackRole": "mixedPlaybackAndControl",
                    },
                    "runtimeActivationStatus": "runtimeLifecycleConditionRequired",
                }],
            }), encoding="utf-8")
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                builder.ingest_audio_trigger_contexts()
                context_node = builder.node_id("audio_trigger_context", "global:fixture")
                data = json.loads(builder.db.execute(
                    "SELECT data FROM nodes WHERE id = ?", (context_node,),
                ).fetchone()[0])
                self.assertEqual(data["situation"]["stateDirection"], "enter")
                self.assertEqual(data["situation"]["audioStateMask"], 512)
                self.assertEqual(data["meaning"]["playbackRole"], "mixedPlaybackAndControl")
                edges = builder.db.execute(
                    "SELECT kind FROM edges WHERE src = ?", (context_node,),
                ).fetchall()
                self.assertFalse(any("execut" in kind for (kind,) in edges))
            finally:
                builder.close()

    def test_audio_event_library_roles_keep_control_and_empty_events_noncontextual(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            events_path = root / "webui" / "data" / "lang" / "CN" / "audio" / "events.json"
            events_path.parent.mkdir(parents=True)
            events_path.write_text(
                json.dumps({
                    "schemaVersion": 50,
                    "language": "CN",
                    "events": [
                        {
                            "id": "hashed-event:0x12345678",
                            "playbackRole": "controlOnly",
                            "wwiseActionOperationTypes": [0x0200],
                            "wwiseActionOperationTypesHex": ["0x0200"],
                            "wwiseActionOperations": ["pause"],
                            "wwiseActionOperationRows": [{
                                "operationType": 0x0200,
                                "operationTypeHex": "0x0200",
                                "operationLabels": ["pause"],
                            }],
                            "purposeKnowledgeStatus": "audioLibraryControlKnown",
                            "purposeInvestigationPriority": "secondary",
                            "playbackLocationStatus": "libraryControlOnlyExternalCallerUnknown",
                        },
                        {
                            "id": "hashed-event:0x87654321",
                            "playbackRole": "emptyEventDefinition",
                            "wwiseActionOperationTypes": [],
                            "wwiseActionOperationTypesHex": [],
                            "wwiseActionOperations": [],
                            "wwiseActionOperationRows": [],
                            "purposeKnowledgeStatus": "audioLibraryEmptyEventKnown",
                            "purposeInvestigationPriority": "secondary",
                            "playbackLocationStatus": "libraryEmptyEventExternalCallerUnknown",
                        },
                    ],
                }),
                encoding="utf-8",
            )
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export_full",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                builder.ingest_audio_event_library_roles()
                control_node = builder.node_id("wwise_event", "hashed-event:0x12345678")
                empty_node = builder.node_id("wwise_event", "hashed-event:0x87654321")
                operation_node = builder.node_id("wwise_action_operation", "0x0200")
                edges = builder.db.execute(
                    "SELECT src, kind, dst FROM edges ORDER BY src, kind, dst"
                ).fetchall()
                self.assertIn(
                    (control_node, "wwise_event_has_nonplayback_action_operation", operation_node),
                    edges,
                )
                self.assertTrue(any(
                    kind == "has_audio_event_library_role" and dst == empty_node
                    for _src, kind, dst in edges
                ))
                self.assertFalse(any(
                    marker in kind
                    for _src, kind, _dst in edges
                    for marker in ("trigger", "story", "line", "speaker")
                ))
            finally:
                builder.close()

    def test_audio_trigger_contexts_link_remote_common_auto_play_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_path = root / "webui" / "data" / "lang" / "CN" / "audio" / "trigger_contexts.json"
            context_path.parent.mkdir(parents=True)
            context_path.write_text(
                json.dumps({
                    "schema": 4,
                    "language": "CN",
                    "counts": {"total": 1},
                    "contexts": [{
                        "triggerId": "remoteCommonAudio:fixture:fixture_001:au_sfx_fixture",
                        "semanticKind": "remoteCommonAudio",
                        "triggerRole": "RemoteCommonTableAutoPlay",
                        "situation": {
                            "remoteCommonId": "remote_common_fixture",
                            "singleId": "remote_common_fixture_001",
                            "eventId": "au_sfx_fixture",
                            "autoPlay": True,
                        },
                        "meaning": {
                            "id": "remote_common_fixture_001",
                            "audio": "au_sfx_fixture",
                            "eventId": "au_sfx_fixture",
                        },
                        "mediaRefs": [{"id": "au_sfx_fixture"}],
                        "sourceRefs": ["structured/Persistent/Table/RemoteCommonTable.json"],
                    }],
                }),
                encoding="utf-8",
            )
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                for kind, key in (
                    ("audio", "au_sfx_fixture"),
                    ("wwise_event", "au_sfx_fixture"),
                    ("remote_common", "remote_common_fixture"),
                    ("remote_common_line", "remote_common_fixture_001"),
                ):
                    builder.add_node(kind, key, source="fixture")
                builder.ingest_audio_trigger_contexts()
                context_node = builder.node_id(
                    "audio_trigger_context",
                    "remoteCommonAudio:fixture:fixture_001:au_sfx_fixture",
                )
                edges = {
                    row[0]
                    for row in builder.db.execute(
                        "SELECT kind FROM edges WHERE src = ?",
                        (context_node,),
                    )
                }
                self.assertIn("audio_trigger_context_for_remote_common", edges)
                self.assertIn("audio_trigger_context_for_remote_common_line", edges)
            finally:
                builder.close()

    def test_audio_trigger_contexts_preserve_timeline_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_path = root / "webui" / "data" / "lang" / "CN" / "audio" / "trigger_contexts.json"
            context_path.parent.mkdir(parents=True)
            context_path.write_text(json.dumps({
                "schema": 4,
                "language": "CN",
                "counts": {"total": 1},
                "contexts": [{
                    "triggerId": "timeline:fixture",
                    "semanticKind": "timelineAudio",
                    "triggerRole": "TimelineAssetPlayback",
                    "situation": {"eventId": "au_music_fixture", "contextKind": "levelSequenceAudio"},
                    "meaning": {"eventId": "au_music_fixture", "audio": "au_music_fixture"},
                    "owner": {
                        "timelineAssetName": "levelseq_fixture_Audio",
                        "audioPlayableType": "AudioMusicPlayable",
                        "audioPlayableRuntimeContractId": "timelineMusicEventKey.audioMusic",
                        "audioPlayableKeyStatus": "exactAudioEventPlayableScalar",
                        "authoredEventName": "au_music_fixture",
                        "authoredEventNameEvidence": "exactTimelineDisplayNameHashEqualsSerializedAudioId",
                        "audioPlayableStopOnDisable": 1,
                        "audioMusicActionType": 1,
                        "audioMusicActionTypeLabel": "NORMAL_MUSIC",
                        "audioMusicTriggerOnSkip": 0,
                        "audioMusicTriggerOnSkipLabel": "notTriggeredOnSkip",
                        "runtimeCarrierStatus": "serializedPlayableCarrier",
                    },
                    "selection": {
                        "triggerBindingStatus": "timelineParentNotLevelSequence",
                        "audioSelectionStatus": "exactTimelineAudioEventKey",
                        "runtimeSelectionStatus": "unobserved",
                    },
                    "sourceRefs": ["fixture.json"],
                }],
            }), encoding="utf-8")
            builder = SourceGraphBuilder(
                db_path=root / "graph.sqlite",
                root=root,
                export_root=root / "export",
                include_asset_maps=False,
                include_reference_rows=False,
            )
            builder.open()
            try:
                builder.ingest_audio_trigger_contexts()
                context_node = builder.node_id("audio_trigger_context", "timeline:fixture")
                data = json.loads(
                    builder.db.execute(
                        "SELECT data FROM nodes WHERE id = ?",
                        (context_node,),
                    ).fetchone()[0]
                )
                self.assertEqual(data["owner"]["audioPlayableType"], "AudioMusicPlayable")
                self.assertEqual(
                    data["owner"]["audioPlayableRuntimeContractId"],
                    "timelineMusicEventKey.audioMusic",
                )
                self.assertEqual(data["owner"]["authoredEventName"], "au_music_fixture")
                self.assertEqual(
                    data["owner"]["authoredEventNameEvidence"],
                    "exactTimelineDisplayNameHashEqualsSerializedAudioId",
                )
                self.assertEqual(data["owner"]["audioPlayableStopOnDisable"], 1)
                self.assertEqual(data["owner"]["audioMusicActionType"], 1)
                self.assertEqual(data["owner"]["audioMusicActionTypeLabel"], "NORMAL_MUSIC")
                self.assertEqual(data["owner"]["audioMusicTriggerOnSkip"], 0)
                self.assertEqual(data["owner"]["audioMusicTriggerOnSkipLabel"], "notTriggeredOnSkip")
                self.assertEqual(data["owner"]["runtimeCarrierStatus"], "serializedPlayableCarrier")
                self.assertEqual(data["selection"]["audioSelectionStatus"], "exactTimelineAudioEventKey")
            finally:
                builder.close()


if __name__ == "__main__":
    unittest.main()
