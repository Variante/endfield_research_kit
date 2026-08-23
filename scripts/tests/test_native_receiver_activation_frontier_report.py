from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
from scripts.story_builder import native_receiver_activation_frontier as frontier


class NativeReceiverActivationFrontierTests(unittest.TestCase):
    def test_large_report_writer_streams_and_skips_unchanged_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frontier.json"
            payload = {"rows": [{"storyKey": "radio_test", "value": "中文"}]}
            self.assertTrue(frontier._write_large_report_json(path, payload))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            original_mtime = path.stat().st_mtime_ns
            self.assertFalse(frontier._write_large_report_json(path, payload))
            self.assertEqual(path.stat().st_mtime_ns, original_mtime)

    @staticmethod
    def teleport_runtime_contract_fixture() -> dict:
        return {
            "schema": "teleportFinishRuntimeContract.v1",
            "validation": {"status": "validated", "failures": []},
        }

    @staticmethod
    def activation_runtime_index_fixture(
        *, metadata_sha256: str | None = None,
    ) -> dict:
        contract = frontier.TELEPORT_FINISH_RUNTIME_CONTRACT
        return {
            "runtimeContract": {
                "teleportMissionScriptCarrier": {
                    "type": "Beyond.Gameplay.TeleportParam",
                    "layout": {"actionId": "0x28"},
                    "auditSchema": "nativeValueCarrierAudit.v1",
                    "validation": {"status": "validated", "failures": []},
                    "metadataSignatureMethodCount": 15,
                    "containerPathCount": 10,
                    "focusFieldAccessCount": 23,
                    "storyBindingsAdded": 0,
                },
                "nativeEvidence": [{
                    "symbol": "LevelEvent.OnTeleportFinish.Process",
                    "address": frontier.TELEPORT_FINISH_RUNTIME_CONTRACT[
                        "listenerProcessMethodVa"
                    ],
                    "finding": "exact string comparison",
                }],
                "levelScriptActivationControlAudit": {
                    "source": "reports/story/recovery/protocol_registry_audit.json",
                    "validation": {"status": "validated"},
                    "relatedOriginalFiles": [
                        {
                            "sourceFile": "D:/game/GameAssembly.dll",
                            "sha256": contract["gameAssemblySha256"],
                        },
                        {
                            "sourceFile": "D:/game/global-metadata.dat",
                            "sha256": metadata_sha256
                            or contract["globalMetadataSha256"],
                        },
                    ],
                }
            }
        }

    def test_teleport_runtime_contract_is_hash_bound_and_identity_free(self) -> None:
        contract = frontier.teleport_finish_runtime_contract(
            self.activation_runtime_index_fixture()
        )

        self.assertEqual("validated", contract["validation"]["status"])
        self.assertEqual(
            [],
            contract.get("serializedObjectInputs", []),
        )
        self.assertEqual(
            "Beyond.Gameplay.Actions.LevelEvent.OnTeleportFinish",
            contract["listenerType"],
        )

    def test_compact_receiver_context_keeps_generic_carrier_audit(self) -> None:
        carrier_audit = {
            "schema": "nativeValueCarrierAudit.v1",
            "signatureMethodCount": 15,
            "containerPathCount": 10,
            "directCallsiteCount": 13,
            "validationStatus": "validated",
        }
        compact = frontier._receiver_native_evidence_context({
            "teleportFinishCorrelations": [{
                "schema": "teleportFinishCorrelationCensus.v1",
                "listenerHeaderLocalId": 16,
                "actionIdFilter": "fixture",
                "carrierAudit": carrier_audit,
            }],
        })
        self.assertEqual(
            carrier_audit,
            compact["teleportFinishCorrelations"][0]["carrierAudit"],
        )

    def test_teleport_runtime_contract_reports_hash_drift(self) -> None:
        contract = frontier.teleport_finish_runtime_contract(
            self.activation_runtime_index_fixture(metadata_sha256="bad")
        )

        self.assertEqual(
            "validation_failed", contract["validation"]["status"]
        )
        failure = contract["validation"]["failures"][0]
        self.assertEqual("reviewedGlobalMetadata", failure["gate"])
        self.assertEqual(
            frontier.TELEPORT_FINISH_RUNTIME_CONTRACT["globalMetadataSha256"],
            failure["expected"]["sha256"],
        )
        self.assertEqual(["bad"], failure["actual"]["sha256"])

    def test_teleport_finish_census_is_corpus_driven_and_rejects_self_uid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"61e1bd3e|61e1bd3e")

            def decoder(_data: bytes) -> tuple[dict, None]:
                return ({
                    "status": "exact_complete_action_map",
                    "physicalActionRecordCount": 1,
                    "physicalHeaderRecordCount": 1,
                    "actions": [{
                        "localId": 2,
                        "uid": "unrelated",
                        "texts": [],
                        "recordOffset": 32,
                    }],
                    "eventRoots": [{
                        "localId": 1,
                        "uid": "61e1bd3e",
                        "headerName": "LevelEvent_OnTeleportFinish",
                        "recordOffset": 0,
                        "eventDetail": {"actionIdFilter": "61e1bd3e"},
                    }],
                }, None)

            census = frontier.build_teleport_finish_correlation_census(
                root,
                self.teleport_runtime_contract_fixture(),
                topology_decoder=decoder,
            )

        self.assertEqual("validated", census["validation"]["status"])
        self.assertEqual(1, census["candidateFileCount"])
        self.assertEqual(1, census["listenerCount"])
        self.assertEqual(1, census["distinctFilterCount"])
        self.assertEqual(1, census["selfHeaderUidOccurrenceCount"])
        self.assertEqual(0, census["externalSerializedOccurrenceCount"])
        self.assertEqual(1, census["runtimeOnlyFilterCount"])
        self.assertEqual(
            "runtime_only_no_serialized_levelscript_producer",
            census["filters"][0]["classification"],
        )

    def test_teleport_finish_census_fails_closed_with_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"listener-without-filter")

            def decoder(_data: bytes) -> tuple[dict, None]:
                return ({
                    "status": "exact_complete_action_map",
                    "physicalActionRecordCount": 0,
                    "physicalHeaderRecordCount": 1,
                    "actions": [],
                    "eventRoots": [{
                        "localId": 7,
                        "uid": "header07",
                        "headerName": "LevelEvent_OnTeleportFinish",
                        "recordOffset": 0,
                        "eventDetail": {},
                    }],
                }, None)

            census = frontier.build_teleport_finish_correlation_census(
                root,
                self.teleport_runtime_contract_fixture(),
                topology_decoder=decoder,
            )

        validation = census["validation"]
        self.assertEqual("validation_failed", validation["status"])
        failure = validation["failures"][0]
        self.assertEqual(
            "typedListenerHasExactActionIdFilter", failure["gate"]
        )
        self.assertEqual("map_fixture/1001#7", failure["identity"])
        self.assertRegex(failure["sourceHashes"]["sha256"], r"^[0-9a-f]{64}$")

    def test_teleport_finish_census_surfaces_new_action_candidate_without_edge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "map_fixture" / "2002.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"abcd1234|abcd1234")

            def decoder(_data: bytes) -> tuple[dict, None]:
                return ({
                    "status": "exact_complete_action_map",
                    "physicalActionRecordCount": 1,
                    "physicalHeaderRecordCount": 1,
                    "actions": [{
                        "localId": 8,
                        "uid": "abcd1234",
                        "texts": [],
                        "recordOffset": 9,
                        "actionName": "FutureTeleportProducerCandidate",
                    }],
                    "eventRoots": [{
                        "localId": 7,
                        "uid": "header07",
                        "headerName": "LevelEvent_OnTeleportFinish",
                        "recordOffset": 0,
                        "eventDetail": {"actionIdFilter": "abcd1234"},
                    }],
                }, None)

            census = frontier.build_teleport_finish_correlation_census(
                root,
                self.teleport_runtime_contract_fixture(),
                topology_decoder=decoder,
            )

        row = census["filters"][0]
        self.assertEqual("validated", census["validation"]["status"])
        self.assertEqual("serialized_action_identity_candidate", row["classification"])
        self.assertEqual(1, row["externalSerializedOccurrenceCount"])
        self.assertEqual(1, row["serializedActionCandidateCount"])
        self.assertFalse(row["producerEdge"])
        self.assertFalse(row["orderEvidence"])

    def test_mission_area_leveldata_shell_validator_is_shape_driven(self) -> None:
        pairs = {("map_fixture", "1001")}
        contexts = {
            ("map_fixture", "1001"): {
                "levelId": "map_fixture",
                "scriptId": "1001",
                "status": "unique",
                "hostMissionIds": ["mission_fixture"],
                "hosts": [{
                    "levelId": "map_fixture",
                    "scriptId": "1001",
                    "levelDataFile": (
                        "export_full/structured/StreamingAssets/Data/Json/"
                        "LevelData/map_fixture/fixture.json"
                    ),
                    "hostMissionIds": ["mission_fixture"],
                    "rootScriptIds": ["9001"],
                    "missionAreaReferences": [{
                        "missionId": "mission_fixture",
                        "levelId": "map_fixture",
                        "levelNum": "1",
                        "missionAreaId": "area_fixture",
                        "subDataParentId": "9001",
                        "sourceFile": "source/mission_fixture.json",
                        "missionAreaSourceFile": "source/areas.json",
                        "levelBasicInfoSourceFile": "source/levels.json",
                    }],
                }],
            }
        }
        with mock.patch.object(
            frontier,
            "_source_file_sha256",
            return_value="a" * 64,
        ):
            validation = (
                frontier.validate_mission_area_leveldata_shell_contexts(
                    pairs,
                    contexts,
                    {"mission_fixture"},
                )
            )
            contexts[("map_fixture", "1001")]["status"] = "shared"
            failed = frontier.validate_mission_area_leveldata_shell_contexts(
                pairs,
                contexts,
                {"mission_fixture"},
            )

        self.assertEqual("validated", validation["status"])
        self.assertEqual("validation_failed", failed["status"])
        self.assertEqual(
            "scopeClassification",
            failed["failures"][0]["gate"],
        )
        self.assertEqual(
            "map_fixture/1001",
            failed["failures"][0]["identity"],
        )

    def test_structured_identity_census_accepts_only_reviewed_direct_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rows.json").write_text(json.dumps({
                "rows": [
                    {
                        "bindScriptId": "known_subgame_script",
                        "dungeonMissionId": "mission_fixture",
                    },
                    {"scriptId": "receiver_fixture"},
                    {"missionId": "mission_elsewhere"},
                ]
            }), encoding="utf-8")
            census = frontier.structured_identity_cocarrier_census(
                [{"scriptId": "receiver_fixture"}],
                structured_json_root=root,
            )

        self.assertEqual("validated", census["validation"]["status"])
        self.assertEqual(1, census["directCarrierCount"])
        self.assertEqual(0, census["receiverMatchCount"])
        self.assertEqual(
            {"bindScriptId+dungeonMissionId": 1},
            census["keyPairCounts"],
        )

    def test_structured_identity_census_fails_on_new_direct_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "new_carrier.json"
            source.write_text(json.dumps({
                "scriptId": "receiver_fixture",
                "missionId": "mission_fixture",
            }), encoding="utf-8")
            census = frontier.structured_identity_cocarrier_census(
                [{"scriptId": "receiver_fixture"}],
                structured_json_root=root,
            )

        failure = census["validation"]["failures"][0]
        self.assertEqual("validation_failed", census["validation"]["status"])
        self.assertEqual("allDirectCarrierShapesReviewed", failure["gate"])
        self.assertEqual(frontier.rel_path(source), failure["sourceFile"])
        self.assertEqual(1, census["receiverMatchCount"])
        self.assertEqual(
            "unreviewed_direct_identity_carrier",
            failure["actual"][0]["classification"],
        )

    def test_authored_property_contract_separates_namespaces_and_observers(self) -> None:
        contract = frontier.authored_property_contract(
            [
                {
                    "briefData": {
                        "propertyNames": [
                            "lt:p:task:objective",
                            "@2002_isFinished",
                            "isFinished",
                            "state",
                        ]
                    }
                }
            ],
            [{"propertyKeys": ["isFinished", "missing"]}],
        )

        self.assertEqual(["isFinished", "state"], contract["authoredNames"])
        self.assertEqual(["isFinished"], contract["missionObservedNames"])
        self.assertEqual(
            "authored_property_with_exact_mission_observer",
            contract["classification"],
        )
        self.assertFalse(contract["ownership"])
        self.assertFalse(contract["orderEvidence"])

    def test_module_property_family_census_is_id_agnostic(self) -> None:
        host = {
            "sourceFile": "export_full/structured/LevelData/map_fixture/host.json",
            "briefData": {
                "properties": [
                    {
                        "name": "@987_is_enabled",
                        "valueType": 1,
                        "atomCount": 1,
                        "atoms": [{"valueBit64": 0}],
                    },
                    {
                        "name": "@987_is_completed",
                        "valueType": 1,
                        "atomCount": 1,
                        "atoms": [{"valueBit64": 1}],
                    },
                    {
                        "name": "@987_custom_payload",
                        "valueType": 50,
                        "atomCount": 1,
                        "atoms": [{"valueBit64": 42}],
                    },
                ],
            },
        }
        rows = frontier.module_property_family_contexts(
            [host], receiver_script_id="123"
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("987", rows[0]["moduleId"])
        self.assertFalse(rows[0]["moduleIdMatchesReceiverScript"])
        self.assertEqual(["base_lifecycle_pair", "typed_payload_fields"], rows[0]["pattern"]["features"])
        self.assertEqual(
            "export_full/structured/LevelData/map_fixture/host.json",
            rows[0]["relatedFiles"][0]["sourceFile"],
        )
        self.assertFalse(rows[0]["storyBinding"])
        self.assertFalse(rows[0]["orderEvidence"])

    def test_module_property_family_census_ignores_singletons_and_values(self) -> None:
        rows = frontier.module_property_family_contexts([
            {
                "sourceFile": "host.json",
                "briefData": {
                    "properties": [
                        {
                            "name": "@1_only",
                            "valueType": 50,
                            "atomCount": 1,
                            "atoms": [{"valueBit64": 999}],
                        },
                    ],
                },
            },
        ])
        self.assertEqual([], rows)

    def test_module_property_family_key_ignores_module_id_and_runtime_values(self) -> None:
        def host(module_id: str, value: int) -> dict:
            return {
                "sourceFile": "host.json",
                "briefData": {
                    "properties": [
                        {
                            "name": f"@{module_id}_is_enabled",
                            "valueType": 1,
                            "atomCount": 1,
                            "atoms": [{"valueBit64": value}],
                        },
                        {
                            "name": f"@{module_id}_is_completed",
                            "valueType": 1,
                            "atomCount": 1,
                            "atoms": [{"valueBit64": 0 if value else 1}],
                        },
                    ],
                },
            }
        self.assertEqual(
            frontier.module_property_family_contexts(
                [host("100", 0)]
            )[0]["familyKey"],
            frontier.module_property_family_contexts(
                [host("200", 1)]
            )[0]["familyKey"],
        )

    @staticmethod
    def encounter_host(script_id: str) -> dict:
        prefix = f"@{script_id}_"
        properties = [
            {
                "name": prefix + suffix,
                "valueType": 1,
                "atomCount": 1,
                "atoms": [{"valueBit64": 0, "text": ""}],
            }
            for suffix in frontier.ENCOUNTER_REQUIRED_BOOL_SUFFIXES
        ]
        properties.extend([
            {
                "name": prefix + "enemy_list",
                "valueType": 14,
                "atomCount": 0,
                "atoms": [],
            },
            {
                "name": prefix + "spawner_id",
                "valueType": 50,
                "atomCount": 1,
                "atoms": [{"valueBit64": 1002, "text": ""}],
            },
        ])
        return {
            "sourceFile": "source/leveldata.bin",
            "briefData": {"properties": properties},
        }

    def test_encounter_contract_is_structural_and_attaches_spawner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spawner_root = Path(tmp)
            level_dir = spawner_root / "map_fixture"
            level_dir.mkdir()
            spawner = level_dir / "sc_map_fixture_1002.json"
            spawner.write_bytes(b"fixture")
            rows = frontier.encounter_controller_contexts(
                "map_fixture",
                "1001",
                [self.encounter_host("1001")],
                spawner_root=spawner_root,
            )
        self.assertEqual(1, len(rows))
        self.assertEqual(
            "encounter_controller_property_contract",
            rows[0]["classification"],
        )
        self.assertEqual("1002", rows[0]["spawnerId"])
        self.assertEqual("1001", rows[0]["moduleId"])
        self.assertTrue(rows[0]["moduleIdMatchesReceiverScript"])
        self.assertEqual(2, len(rows[0]["relatedFiles"]))
        self.assertFalse(rows[0]["storyBinding"])
        self.assertFalse(rows[0]["orderEvidence"])

    def test_encounter_contract_uses_lsm_module_not_receiver_id(self) -> None:
        rows = frontier.encounter_controller_contexts(
            "map_fixture",
            "1001",
            [self.encounter_host("2002")],
            spawner_root=Path("missing"),
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("2002", rows[0]["moduleId"])
        self.assertEqual("1001", rows[0]["receiverScriptId"])
        self.assertFalse(rows[0]["moduleIdMatchesReceiverScript"])

    def test_encounter_contract_allows_native_zero_spawner(self) -> None:
        host = self.encounter_host("2002")
        host["briefData"]["properties"][-1]["atoms"][0]["valueBit64"] = 0
        rows = frontier.encounter_controller_contexts(
            "map_fixture",
            "1001",
            [host],
            spawner_root=Path("missing"),
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("0", rows[0]["spawnerId"])
        self.assertEqual(1, len(rows[0]["relatedFiles"]))

    def test_encounter_contract_accepts_populated_entity_reference_list(
        self,
    ) -> None:
        host = self.encounter_host("2002")
        enemy_list = host["briefData"]["properties"][-2]
        enemy_list.update({
            "valueType": frontier.ENCOUNTER_POPULATED_ENEMY_LIST_VALUE_TYPE,
            "atomCount": 3,
            "atoms": [
                {"valueBit64": value, "text": ""}
                for value in (30001, 30002, 30003)
            ],
        })
        rows = frontier.encounter_controller_contexts(
            "map_fixture",
            "1001",
            [host],
            spawner_root=Path("missing"),
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("2002", rows[0]["moduleId"])

    def test_encounter_contract_rejects_malformed_populated_list(self) -> None:
        host = self.encounter_host("2002")
        enemy_list = host["briefData"]["properties"][-2]
        enemy_list.update({
            "valueType": frontier.ENCOUNTER_POPULATED_ENEMY_LIST_VALUE_TYPE,
            "atomCount": 2,
            "atoms": [{"valueBit64": 30001, "text": ""}],
        })
        self.assertEqual(
            [],
            frontier.encounter_controller_contexts(
                "map_fixture",
                "1001",
                [host],
                spawner_root=Path("missing"),
            ),
        )

    def test_encounter_contract_fails_closed_on_wrong_native_shape(self) -> None:
        host = self.encounter_host("1001")
        host["briefData"]["properties"][0]["valueType"] = 2
        self.assertEqual(
            [],
            frontier.encounter_controller_contexts(
                "map_fixture",
                "1001",
                [host],
                spawner_root=Path("missing"),
            ),
        )

    def test_encounter_contract_fails_closed_on_null_spawner_atom(self) -> None:
        host = self.encounter_host("1001")
        host["briefData"]["properties"][-1]["atoms"] = [None]
        self.assertEqual(
            [],
            frontier.encounter_controller_contexts(
                "map_fixture",
                "1001",
                [host],
                spawner_root=Path("missing"),
            ),
        )

    def test_frontend_renders_encounter_context_as_non_owning_files(self) -> None:
        source = (
            ROOT / "webui" / "src" / "features" / "mission_pipeline" / "index.js"
        ).read_text(encoding="utf-8")
        self.assertIn("activation.encounterControllerContexts", source)
        self.assertIn('t("relatedOriginalFile")', source)
        self.assertIn('t("encounterControllerBoundary")', source)

    def test_frontend_renders_generic_module_property_families(self) -> None:
        source = (
            ROOT / "webui" / "src" / "features" / "mission_pipeline" / "index.js"
        ).read_text(encoding="utf-8")
        self.assertIn("activation.modulePropertyFamilies", source)
        self.assertIn('t("modulePropertyFamilyBoundary")', source)

    def test_frontend_renders_objective_consumer_as_observation_only(self) -> None:
        source = (
            ROOT / "webui" / "src" / "features" / "mission_pipeline" / "index.js"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "activation.missionRuntimeScriptConsumers",
            source,
        )
        self.assertIn('class="is-boundary"', source)
        self.assertIn('t("questObserver")', source)
        self.assertIn('t("observationOnly")', source)
        self.assertIn(
            "playback handoff sets the observed property",
            source,
        )

    def test_mission_runtime_consumer_retains_original_and_pipeline_sources(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp_root = Path(tmp)
            original = tmp_root / "original.json"
            original.write_text("{}", encoding="utf-8")
            mission_root = tmp_root / "pipeline"
            mission_root.mkdir()
            pipeline_path = mission_root / "mission_fixture.json"
            pipeline_path.write_text(
                __import__("json").dumps({
                    "mission": {
                        "id": "mission_fixture",
                        "source": frontier.rel_path(original),
                    },
                    "nodes": [{
                        "id": "mission_fixture_q#1",
                        "objectives": [{
                            "index": 1,
                            "levelScriptIds": ["1001"],
                            "conditionTypes": ["CheckLevelScriptPropertyBool"],
                            "condition": {
                                "type": "CombineCondition",
                                "children": [{
                                    "type": "CheckLevelScriptPropertyBool",
                                    "facts": {
                                        "mapId": "map_fixture",
                                        "scriptId": {"scriptId": 1001},
                                        "key": "isFinished",
                                    },
                                }],
                            },
                        }],
                    }],
                }),
                encoding="utf-8",
            )
            rows = frontier.mission_runtime_script_consumers(mission_root)
        consumer = rows[("map_fixture", "1001")][0]
        self.assertEqual(frontier.rel_path(original), consumer["sourceFile"])
        self.assertEqual(
            frontier.rel_path(pipeline_path),
            consumer["pipelineSourceFile"],
        )
        self.assertEqual(["isFinished"], consumer["propertyKeys"])
        self.assertNotIn(("different_map", "1001"), rows)

    def test_mission_runtime_consumer_rejects_flat_script_id_without_level(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            mission_root = Path(tmp)
            (mission_root / "mission_fixture.json").write_text(
                __import__("json").dumps({
                    "mission": {"id": "mission_fixture"},
                    "nodes": [{
                        "id": "mission_fixture_q#1",
                        "objectives": [{
                            "index": 1,
                            "levelScriptIds": ["1001"],
                            "conditionTypes": [
                                "CheckLevelScriptPropertyBool"
                            ],
                        }],
                    }],
                }),
                encoding="utf-8",
            )
            rows = frontier.mission_runtime_script_consumers(mission_root)
        self.assertEqual({}, dict(rows))

    def test_receiver_nodes_collapse_by_exact_levelscript(self) -> None:
        payload = {
            "storyCoverage": {
                "missionlessNativeRuntimeNodes": [
                    {
                        "eventName": "LevelEvent_OnCustomEvent",
                        "selector": {
                            "levelId": "map_fixture",
                            "listenerScriptId": "1001",
                            "listenerHeaderLocalId": 11,
                        },
                        "storyFiles": [
                            {
                                "key": "radio_fixture_1",
                                "kind": "radio",
                                "sourceFiles": ["source/a.json"],
                            }
                        ],
                    },
                    {
                        "eventName": "LevelEvent_OnEntityHpChanged",
                        "selector": {
                            "levelId": "map_fixture",
                            "listenerScriptId": "1001",
                            "listenerHeaderLocalId": 15,
                        },
                        "storyFiles": [
                            {
                                "key": "black_fixture_1",
                                "kind": "black",
                                "sourceFiles": ["source/a.json"],
                            }
                        ],
                    },
                ]
            }
        }
        rows = frontier.receiver_script_rows(payload)
        self.assertEqual(1, len(rows))
        self.assertEqual(2, rows[0]["receiverNodeCount"])
        self.assertEqual(2, rows[0]["receiverToStoryPlacementCount"])
        self.assertEqual(
            ["black_fixture_1", "radio_fixture_1"],
            rows[0]["storyKeys"],
        )
        self.assertEqual([11, 15], rows[0]["listenerHeaderLocalIds"])

    def test_exact_active_phase_receiver_contract_is_corpus_driven(self) -> None:
        original = frontier.decode_levelscript_native_action_topology
        frontier.decode_levelscript_native_action_topology = lambda _data: ({
            "schema": "levelScriptNativeActionTopology.v4",
            "status": "exact_complete_action_map_with_runtime_shadowing",
            "eventRoots": [
                {
                    "localId": 11,
                    "headerName": "LevelEvent_OnCustomEvent",
                    "recordOffset": 100,
                    "triggerActiveDuring": 0,
                    "nextActionLocalId": 12,
                },
                {
                    "localId": 15,
                    "headerName": "ScriptEvent_OnCustomEvent",
                    "recordOffset": 200,
                    "triggerActiveDuring": 0,
                    "nextActionLocalId": 16,
                },
            ],
        }, None)
        try:
            contract = frontier.exact_active_phase_receiver_contract(
                b"original-levelscript",
                {"listenerHeaderLocalIds": [15, 11]},
                {
                    "validation": {"status": "validated"},
                    "activeReceiverFlow": {
                        "triggerActiveDuringValues": {"Active": 0, "Start": 1},
                        "setupRegisterTriggerCallCount": 1,
                        "activePhaseEnableBetweenStateSetters": True,
                    },
                },
            )
        finally:
            frontier.decode_levelscript_native_action_topology = original

        self.assertEqual("validated", contract["status"])
        self.assertEqual(
            "exact_complete_action_map_with_runtime_shadowing",
            contract["topologyStatus"],
        )
        self.assertEqual(2, contract["resolvedHeaderCount"])
        self.assertTrue(contract["allReceiversActivePhase"])
        self.assertEqual(
            [11, 15],
            [row["listenerHeaderLocalId"] for row in contract["receiverHeaders"]],
        )

    def test_exact_active_phase_receiver_contract_fails_closed_on_start_header(
        self,
    ) -> None:
        original = frontier.decode_levelscript_native_action_topology
        frontier.decode_levelscript_native_action_topology = lambda _data: ({
            "schema": "levelScriptNativeActionTopology.v4",
            "status": "exact_complete_action_map",
            "eventRoots": [{
                "localId": 11,
                "headerName": "LevelEvent_OnCustomEvent",
                "recordOffset": 100,
                "triggerActiveDuring": 1,
                "nextActionLocalId": 12,
            }],
        }, None)
        try:
            contract = frontier.exact_active_phase_receiver_contract(
                b"original-levelscript",
                {"listenerHeaderLocalIds": [11]},
                {
                    "validation": {"status": "validated"},
                    "activeReceiverFlow": {
                        "triggerActiveDuringValues": {"Active": 0, "Start": 1},
                        "setupRegisterTriggerCallCount": 1,
                        "activePhaseEnableBetweenStateSetters": True,
                    },
                },
            )
        finally:
            frontier.decode_levelscript_native_action_topology = original

        self.assertEqual("unresolved", contract["status"])
        self.assertFalse(contract["allReceiversActivePhase"])

    @staticmethod
    def activation_selector_fixture() -> dict:
        return {
            "schema": "levelScriptActivationControl.v6",
            "validation": {"status": "validated"},
            "activationSelectorFlow": {
                "levelScriptTypeValues": {
                    "World": 0,
                    "Mission": 1,
                    "SubLevelScript": 4,
                },
                "nonSubLevelRequiresEnabledAndActiveArea": True,
                "subLevelRequiresPublicActive": True,
                "nonSubLevelSendsActiveTrueAfterPreActive": True,
                "subLevelSkipsActiveTrueRequest": True,
            },
            "activeAreaFlow": {
                "emptyActiveListSetsWithinTrue": True,
                "activeShapeHitSetsWithinTrue": True,
                "missingOutsideListPreservesPriorWithin": True,
                "outsideShapeMissPreservesPriorWithin": True,
                "outsideShapeHitClearsWithin": True,
            },
        }

    @staticmethod
    def levelscript_active_shape_fixture() -> dict:
        return {
            "activeShapeList": {
                "schema": "levelScriptActiveShapeList.v1",
                "status": "decoded_unique",
                "candidateCount": 1,
                "count": 1,
                "shapes": [{
                    "type": "SPHERE",
                    "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "radius": 4.0,
                }],
            },
        }

    def test_client_active_request_contract_uses_only_exact_host_type(self) -> None:
        contract = frontier.exact_client_active_request_contract(
            [{"briefData": {"levelScriptType": 1}}],
            self.activation_selector_fixture(),
            self.levelscript_active_shape_fixture(),
        )

        self.assertEqual("validated", contract["status"])
        self.assertEqual("Mission", contract["levelScriptTypeName"])
        self.assertTrue(contract["clientProducesActiveRequest"])
        self.assertEqual("Enabled", contract["entryPublicState"])
        self.assertIn("SendLevelScriptSetActive(true)", contract["runtimePath"])
        self.assertEqual(
            "validated_runtime_position_dependent",
            contract["spatialGateStatus"],
        )
        self.assertEqual(
            "SPHERE", contract["activeShapeList"]["shapes"][0]["type"]
        )

    def test_client_active_request_contract_fails_closed_on_ambiguous_hosts(
        self,
    ) -> None:
        contract = frontier.exact_client_active_request_contract(
            [
                {"briefData": {"levelScriptType": 0}},
                {"briefData": {"levelScriptType": 1}},
            ],
            self.activation_selector_fixture(),
            self.levelscript_active_shape_fixture(),
        )

        self.assertEqual("unresolved", contract["status"])
        self.assertFalse(contract["clientProducesActiveRequest"])
        self.assertEqual([], contract["runtimePath"])

    def test_manual_null_shapes_task_and_parent_is_static_frontier(self) -> None:
        levelscript = {
            "startTypeName": "Manual",
            "startShapeListStatus": "null",
            "startShapeListCount": None,
            "taskMapStatus": "null",
            "taskMapCount": None,
        }
        hosts = [{"briefData": {"parentLevelScriptId": "0"}}]
        self.assertEqual(
            "manual_start_runtime_request_no_static_carrier",
            frontier.activation_class(
                levelscript,
                hosts,
                [],
                activation_control_validated=True,
            ),
        )
        self.assertEqual(
            "manual_start_active_phase_receiver",
            frontier.activation_class(
                levelscript,
                hosts,
                [],
                activation_control_validated=True,
                active_phase_receiver_validated=True,
            ),
        )

    def test_missing_leveldata_host_fails_closed(self) -> None:
        self.assertEqual(
            "manual_start_static_carrier_unresolved",
            frontier.activation_class(
                {
                    "startTypeName": "Manual",
                    "startShapeListStatus": "null",
                    "taskMapStatus": "null",
                },
                [],
                [],
            ),
        )

    def test_literal_cross_script_control_wins_over_manual_frontier(self) -> None:
        self.assertEqual(
            "literal_cross_script_manual_control",
            frontier.activation_class(
                {"startTypeName": "Manual"},
                [],
                [{"selfTarget": False}],
            ),
        )

    def test_header_linked_current_context_self_start_is_static_carrier(self) -> None:
        self.assertEqual(
            "header_linked_current_context_self_manual_start",
            frontier.activation_class(
                {"startTypeName": "Manual"},
                [],
                [
                    {
                        "action": "ManualStartLevelScript",
                        "selfTarget": True,
                        "targetResolution": "current_context_self",
                        "headerLinkedEvent": {"localId": 7},
                    }
                ],
            ),
        )

    def test_subgame_binding_is_an_exact_activation_scope(self) -> None:
        self.assertEqual(
            "subgame_bind_script_activation_scope",
            frontier.activation_class(
                {"startTypeName": "SameWithActive"},
                [],
                [],
                [{"subGameId": "fixture_game"}],
            ),
        )
        self.assertEqual(
            "subgame_interaction_manual_start",
            frontier.activation_class(
                {"startTypeName": "Manual"},
                [],
                [],
                [{"subGameId": "fixture_game"}],
                activation_control_validated=True,
            ),
        )

    def test_same_with_active_uses_generic_validated_binary_policy(self) -> None:
        self.assertEqual(
            "same_with_active_binary_active_gate",
            frontier.activation_class(
                {"startTypeName": "SameWithActive"},
                [],
                [],
                start_policy_validated=True,
            ),
        )
        self.assertEqual(
            "nonmanual_start_static_carrier_unresolved",
            frontier.activation_class(
                {"startTypeName": "SameWithActive"},
                [],
                [],
                start_policy_validated=False,
            ),
        )

    def test_dungeon_scene_context_keeps_sibling_receiver_non_owning(
        self,
    ) -> None:
        contexts = frontier.dungeon_scene_contexts(
            {
                "dataTable": {
                    "dungeon_fixture": {
                        "id": "dungeon_fixture",
                        "bindScriptId": 1002,
                        "dungeonMissionId": "different_mission",
                    }
                }
            },
            {
                "dungeon_fixture": {
                    "dungeonId": "dungeon_fixture",
                    "sceneId": "map_fixture",
                    "levelId": "level_fixture",
                    "dungeonSeriesId": "series_fixture",
                }
            },
            {
                "condition_fixture": {
                    "conditionId": "condition_fixture",
                    "gameMechanicsId": "dungeon_fixture",
                    "conditionType": 19,
                    "parameter": [
                        {"valueStringList": ["mission_fixture"]}
                    ],
                }
            },
            subgame_source="subgame.json",
            dungeon_source="dungeon.json",
            condition_source="condition.json",
        )
        context = contexts["map_fixture"][0]
        self.assertEqual("1002", context["bindScriptId"])
        self.assertFalse(context["ownership"])
        self.assertFalse(context["storyBinding"])
        self.assertEqual(
            "different_mission",
            context["dungeonMissionContext"]["missionId"],
        )
        self.assertFalse(context["dungeonMissionContext"]["ownership"])
        self.assertFalse(context["dungeonMissionContext"]["playback"])
        self.assertEqual(
            "mission_fixture",
            context["associations"][0]["targetId"],
        )
        self.assertFalse(context["associations"][0]["ownership"])

    def test_unknown_subgame_condition_type_fails_closed(self) -> None:
        self.assertEqual(
            {},
            frontier.subgame_availability_associations(
                {
                    "condition_fixture": {
                        "gameMechanicsId": "dungeon_fixture",
                        "conditionType": 9999,
                        "parameter": [
                            {"valueStringList": ["mission_fixture"]}
                        ],
                    }
                }
            ),
        )

    def test_start_shape_requires_complete_exact_mission_area_geometry(self) -> None:
        shape = {
            "offset": "0x10",
            "typeRaw": 2,
            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            "radius": 5.0,
        }
        area = {
            "missionAreaId": "fixture_area",
            "subDataParentId": 10,
            "shape": {
                "type": 2,
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                "radius": 5.0,
            },
        }
        self.assertEqual(
            "fixture_area",
            frontier.exact_start_shape_mission_area_matches(
                [shape],
                [area],
            )[0]["missionAreaId"],
        )
        area["shape"]["position"]["x"] = 1.01
        self.assertEqual(
            [],
            frontier.exact_start_shape_mission_area_matches(
                [shape],
                [area],
            ),
        )

    def test_memorypack_string_scan_requires_exact_length_prefix(self) -> None:
        exact = (7).to_bytes(4, "little", signed=True) + b"mission"
        embedded = (13).to_bytes(4, "little", signed=True) + b"radio_mission"
        self.assertEqual(
            ["mission"],
            frontier.exact_memorypack_string_tokens(
                exact + embedded,
                {"mission", "missing"},
            ),
        )
        self.assertEqual(
            [],
            frontier.exact_memorypack_string_tokens(
                embedded,
                {"mission"},
            ),
        )

    def test_nonmanual_shape_is_kept_separate(self) -> None:
        self.assertEqual(
            "nonmanual_start_with_shapes",
            frontier.activation_class(
                {
                    "startTypeName": "Auto",
                    "startShapeListCount": 1,
                },
                [],
                [],
            ),
        )

    def test_related_original_files_are_recursive_exact_and_deduplicated(
        self,
    ) -> None:
        rows = frontier.collect_related_original_files(
            {
                "sourceFile": (
                    "export_full/structured/LevelScriptData/map_fixture/1001.bin"
                ),
                "nested": [{
                    "sourceFiles": [
                        "export_full/structured/LevelData/map_fixture/data.bin",
                        "export_full/structured/LevelData/map_fixture/data.bin",
                    ],
                    "pipelineSourceFile": "webui/data/mission_pipeline/index.json",
                }],
            },
            {
                "registrySourceFile": (
                    "export_full/structured/SpawnerConfigData/fixture.bin"
                )
            },
        )

        self.assertEqual(3, len(rows))
        self.assertEqual(
            ["leveldata", "levelscript", "spawner_config"],
            sorted(row["kind"] for row in rows),
        )
        self.assertTrue(all(
            row["relationship"] == "exact_typed_activation_frontier_context"
            for row in rows
        ))
        self.assertFalse(any(
            "webui/" in row["sourceFile"] for row in rows
        ))

    def test_pipeline_publication_is_compact_and_non_owning(self) -> None:
        index = {
            "storyCoverage": {
                "missionlessNativeRuntimeNodes": [
                    {
                        "selector": {
                            "levelId": "map_fixture",
                            "listenerScriptId": "1001",
                        }
                    }
                ]
            }
        }
        report = {
            "schemaVersion": frontier.SCHEMA,
            "generated": "fixture",
            "counts": {"receiverScripts": 1},
            "evidencePolicy": {"noPromotion": "fixture"},
            "rows": [
                {
                    "levelId": "map_fixture",
                    "scriptId": "1001",
                    "activationClass": "manual_start_runtime_request_no_static_carrier",
                    "levelScript": {
                        "startTypeName": "Manual",
                        "startShapeListStatus": "null",
                    },
                    "levelDataHosts": [
                        {
                            "fileName": "fixture.json",
                            "dictionaryEntryCount": 1,
                            "hostMissionId": None,
                        }
                    ],
                    "encounterControllerContexts": [
                        {
                            "classification": (
                                "encounter_controller_property_contract"
                            ),
                            "mappingId": "fixture-mapping",
                            "runtimeType": "EncounterBase<T>",
                            "dataType": "EncounterData",
                            "moduleId": "2002",
                            "receiverScriptId": "1001",
                            "moduleIdMatchesReceiverScript": False,
                            "spawnerId": "1002",
                            "relatedFiles": [
                                {
                                    "kind": "encounter_spawner_config",
                                    "sourceFile": "source/spawner.bin",
                                    "relationship": (
                                        "typed_spawner_id_property"
                                    ),
                                }
                            ],
                            "evidenceBoundary": "encounter context only",
                        }
                    ],
                    "subGameBindings": [],
                    "dungeonSceneContexts": [
                        {
                            "subGameId": "dungeon_fixture",
                            "sceneId": "map_fixture",
                            "levelId": "",
                            "dungeonSeriesId": "series_fixture",
                            "bindScriptId": "1002",
                            "receiverIsBoundScript": False,
                            "dungeonMissionContext": {
                                "missionId": "different_mission",
                                "ownership": False,
                                "playback": False,
                                "finding": "mission shell only",
                            },
                            "associations": [
                                {
                                    "relation": (
                                        "subgame_unlock_quest_prerequisite"
                                    ),
                                    "targetType": "quest",
                                    "targetId": "unrelated_quest",
                                    "conditionTypeName": "QuestStateEqual",
                                    "ownership": False,
                                    "finding": "availability only",
                                }
                            ],
                            "ownership": False,
                            "storyBinding": False,
                            "evidenceBoundary": "scene context only",
                        }
                    ],
                    "incomingLiteralManualControls": [],
                    "missionRuntimeScriptConsumers": [
                        {
                            "missionId": "fixture_mission",
                            "questId": "fixture_mission_q#1",
                            "objectiveIndex": 1,
                            "conditionTypes": [
                                "CheckLevelScriptPropertyBool"
                            ],
                            "propertyKeys": ["isFinished"],
                            "sourceFile": "fixture_mission.json",
                        }
                    ],
                    "authoredPropertyContract": {
                        "authoredNames": ["isFinished"],
                        "missionObservedNames": ["isFinished"],
                        "classification": (
                            "authored_property_with_exact_mission_observer"
                        ),
                        "ownership": False,
                        "orderEvidence": False,
                        "evidenceBoundary": "observer only",
                    },
                    "decodedTaskMap": {
                        "taskCount": 1,
                        "tasks": [
                            {
                                "taskKey": "fixture_task",
                                "conditions": [
                                    {
                                        "conditionKey": "fixture_condition",
                                        "condition": {
                                            "type": "TaskReachDestination",
                                            "areaId": {
                                                "kind": "string",
                                                "value": "fixture_area",
                                            },
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                    "taskRuntimeAuthority": {
                        "schema": "levelScriptTaskAuthority.v1",
                        "classification": (
                            "server_selected_scene_script_task_identity"
                        ),
                        "identityFields": ["sceneNumId", "scriptId", "taskId"],
                        "missionQuestIdentityFields": [],
                        "validation": {"status": "validated"},
                    },
                    "startRuntimePolicy": {
                        "schema": "levelScriptStartPolicy.v1",
                        "classification": (
                            "same_with_active_enters_prestart_when_active"
                        ),
                        "finding": "Active unfinished script enters PreStart",
                        "evidenceBoundary": "no mission owner",
                        "validation": {"status": "validated"},
                    },
                    "activePhaseReceiverControl": {
                        "schema": "exactActivePhaseReceiver.v1",
                        "status": "validated",
                        "classification": (
                            "registered_active_phase_story_receivers"
                        ),
                        "receiverHeaders": [{
                            "listenerHeaderLocalId": 11,
                            "triggerActiveDuring": 0,
                        }],
                    },
                    "relatedOriginalFiles": [
                        {
                            "kind": "leveldata",
                            "sourceFile": (
                                "export_full/structured/LevelData/"
                                "map_fixture/data.bin"
                            ),
                            "relationship": (
                                "exact_typed_activation_frontier_context"
                            ),
                            "sha256": "a" * 64,
                        }
                    ],
                }
            ],
        }
        self.assertEqual(
            1,
            frontier.publish_to_pipeline_index(index, report),
        )
        annotation = index["storyCoverage"]["missionlessNativeRuntimeNodes"][0][
            "activationFrontier"
        ]
        self.assertEqual("Manual", annotation["startTypeName"])
        self.assertEqual(
            "validated",
            annotation["activePhaseReceiverControl"]["status"],
        )
        self.assertNotIn("missionOwnerStatus", annotation)
        encounter = annotation["encounterControllerContexts"][0]
        self.assertEqual("1002", encounter["spawnerId"])
        self.assertEqual("2002", encounter["moduleId"])
        self.assertFalse(encounter["moduleIdMatchesReceiverScript"])
        self.assertEqual(
            "source/spawner.bin",
            encounter["relatedFiles"][0]["sourceFile"],
        )
        self.assertFalse(encounter["storyBinding"])
        self.assertFalse(encounter["orderEvidence"])
        self.assertFalse(
            annotation["dungeonSceneContexts"][0]["receiverIsBoundScript"]
        )
        self.assertFalse(
            annotation["dungeonSceneContexts"][0]["storyBinding"]
        )
        self.assertEqual(
            "different_mission",
            annotation["dungeonSceneContexts"][0][
                "dungeonMissionContext"
            ]["missionId"],
        )
        self.assertFalse(
            annotation["dungeonSceneContexts"][0][
                "dungeonMissionContext"
            ]["ownership"],
        )
        self.assertEqual(
            "unrelated_quest",
            annotation["dungeonSceneContexts"][0]["associations"][0][
                "targetId"
            ],
        )
        self.assertEqual(
            "fixture_area",
            annotation["decodedTaskMap"]["tasks"][0]["conditions"][0][
                "condition"
            ]["areaId"]["value"],
        )

        self.assertEqual(
            1,
            annotation["missionRuntimeObjectiveConsumerCount"],
        )
        self.assertEqual(
            "same_with_active_enters_prestart_when_active",
            annotation["startRuntimePolicy"]["classification"],
        )
        consumer = annotation["missionRuntimeScriptConsumers"][0]
        self.assertEqual(
            "mission_runtime_objective_references_level_script",
            consumer["relation"],
        )
        self.assertEqual("fixture_mission", consumer["missionId"])
        self.assertEqual("fixture_mission_q#1", consumer["questId"])
        self.assertEqual(
            ["CheckLevelScriptPropertyBool"],
            consumer["conditionTypes"],
        )
        self.assertEqual(["isFinished"], consumer["propertyKeys"])
        self.assertEqual(
            ["isFinished"],
            annotation["authoredPropertyContract"]["missionObservedNames"],
        )
        self.assertFalse(consumer["ownership"])
        self.assertFalse(consumer["activation"])
        self.assertFalse(consumer["storyPlayback"])
        self.assertEqual("fixture_mission.json", consumer["sourceFile"])
        self.assertEqual("", consumer["pipelineSourceFile"])
        self.assertEqual(
            "export_full/structured/LevelData/map_fixture/data.bin",
            annotation["relatedOriginalFiles"][0]["sourceFile"],
        )
        self.assertEqual(
            "a" * 64,
            annotation["relatedOriginalFiles"][0]["sha256"],
        )
        self.assertEqual(
            "server_selected_scene_script_task_identity",
            annotation["taskRuntimeAuthority"]["classification"],
        )
        self.assertEqual(
            1,
            index["storyCoverage"]["nativeReceiverActivationFrontier"][
                "annotatedReceiverNodes"
            ],
        )

    def test_publish_promotes_exact_direct_trigger_to_spatial_route_without_owner(self) -> None:
        index = {
            "storyCoverage": {
                "storyTriggerManifest": {
                    "dlg_fixture_1": {
                        "key": "dlg_fixture_1",
                        "attachmentStatus": "unlinked_no_trigger_route",
                        "routes": [],
                    }
                },
                "missionlessNativeRuntimeNodes": [],
            }
        }
        report = {
            "storyTriggerZoneCoverage": {
                "rows": [{
                    "storyKey": "dlg_fixture_1",
                    "status": "exact_local_trigger_volume",
                    "uniqueZoneCount": 1,
                    "observations": [{
                        "storyKey": "dlg_fixture_1",
                        "status": "exact_local_trigger_volume",
                        "directPlaybackEnumeration": True,
                        "levelId": "map_fixture",
                        "scriptId": "100",
                        "triggerSlotIdFilter": 80001,
                        "decodedShape": [{"shapeType": "Sphere"}],
                        "playbackControlPathEvidence": {
                            "status": "exact_trigger_rooted_playback",
                            "noSiblingInheritance": True,
                        },
                    }],
                }]
            },
            "rows": [],
        }

        self.assertEqual(0, frontier.publish_to_pipeline_index(index, report))
        coverage = index["storyCoverage"]
        manifest = coverage["storyTriggerManifest"]["dlg_fixture_1"]
        self.assertEqual(
            "spatial_trigger_known_owner_unresolved",
            manifest["attachmentStatus"],
        )
        self.assertEqual(
            "exact_native_local_trigger_playback",
            manifest["spatialPlaybackRoute"]["status"],
        )
        self.assertEqual(
            "unresolved",
            manifest["spatialPlaybackRoute"]["missionOwnerStatus"],
        )
        self.assertFalse(manifest["spatialPlaybackRoute"]["ownership"])
        self.assertFalse(manifest["spatialPlaybackRoute"]["orderEvidence"])
        self.assertEqual(1, coverage["nativeReceiverSpatialPlaybackRouteCount"])

    def test_direct_playback_unique_authoritative_shell_publishes_context_only(
        self,
    ) -> None:
        trigger_coverage = {
            "rows": [{
                "storyKey": "dlg_fixture_1",
                "status": "exact_local_trigger_volume",
                "uniqueZoneCount": 1,
                "observations": [{
                    "storyKey": "dlg_fixture_1",
                    "status": "exact_local_trigger_volume",
                    "directPlaybackEnumeration": True,
                    "levelId": "map_fixture",
                    "scriptId": "100",
                    "triggerSlotIdFilter": 80001,
                    "playbackControlPathEvidence": {
                        "status": "exact_trigger_rooted_playback",
                    },
                }],
            }],
            "counts": {},
        }
        host_index = {
            ("map_fixture", "100"): {
                "status": "unique",
                "hostMissionIds": ["fixture_mission"],
                "hosts": [{
                    "levelDataFile": "source/fixture_mission.json",
                    "dictionaryEntryCount": 3,
                }],
            }
        }
        with mock.patch.object(
            frontier,
            "build_leveldata_authoritative_scope_script_host_index",
            return_value=host_index,
        ) as build_hosts:
            frontier.attach_direct_playback_mission_shell_context(
                trigger_coverage,
                mission_runtime_ids={"fixture_mission"},
            )
        build_hosts.assert_called_once()
        shell = trigger_coverage["rows"][0][
            "authoritativeMissionShellContext"
        ]
        self.assertEqual("fixture_mission", shell["missionId"])
        self.assertFalse(shell["ownership"])
        self.assertFalse(shell["orderEvidence"])

        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            mission_root = Path(tmp)
            mission_path = mission_root / "fixture_mission.json"
            mission_path.write_text(json.dumps({
                "mission": {"id": "fixture_mission"},
                "storyOrder": {"nodes": [], "directEdges": [], "summary": {}},
            }), encoding="utf-8")
            index = {
                "missions": [{"id": "fixture_mission"}],
                "storyCoverage": {
                    "storyTriggerManifest": {
                        "dlg_fixture_1": {
                            "key": "dlg_fixture_1",
                            "attachmentStatus": "unlinked_no_trigger_route",
                            "routes": [],
                        }
                    },
                    "missionlessNativeRuntimeNodes": [],
                },
            }
            report = {
                "storyTriggerZoneCoverage": trigger_coverage,
                "rows": [],
            }
            frontier.publish_to_pipeline_index(
                index, report, mission_root=mission_root,
            )
            mission = json.loads(mission_path.read_text(encoding="utf-8"))

        manifest = index["storyCoverage"]["storyTriggerManifest"][
            "dlg_fixture_1"
        ]
        self.assertEqual("fixture_mission", manifest["routes"][0]["missionId"])
        self.assertFalse(manifest["routes"][0]["ownership"])
        self.assertFalse(manifest["routes"][0]["orderEvidence"])
        contexts = mission["storyOrder"][
            "authoritativeScopeDirectSpatialPlaybackContexts"
        ]
        self.assertEqual(["dlg_fixture_1"], contexts[0]["storyKeys"])
        self.assertEqual("", contexts[0]["questId"])
        self.assertFalse(contexts[0]["ownership"])
        self.assertFalse(contexts[0]["orderEvidence"])
        self.assertEqual([], mission["storyOrder"]["directEdges"])

    def test_pipeline_publishes_generic_story_receiver_context_index(self) -> None:
        index = {
            "storyCoverage": {
                "missionlessNativeRuntimeNodes": [],
            }
        }
        report = {
            "rows": [{
                "levelId": "map_fixture",
                "scriptId": "1001",
                "receiverNodeCount": 2,
                "receiverToStoryPlacementCount": 3,
                "storyKeys": ["black_fixture_1", "dlg_fixture_1"],
                "storyKinds": ["black", "dlg"],
                "eventNames": ["ScriptEvent_OnCustomEvent"],
                "listenerHeaderLocalIds": [11],
                "activationClass": "manual_start_active_phase_receiver",
                "relatedOriginalFiles": [{
                    "kind": "levelscript",
                    "sourceFile": "source/1001.json",
                    "relationship": "exact receiver",
                    "sha256": "a" * 64,
                }],
            }],
        }

        self.assertEqual(0, frontier.publish_to_pipeline_index(index, report))
        context_index = index["storyCoverage"][
            "nativeReceiverStoryContextIndex"
        ]
        self.assertEqual("nativeReceiverStoryContextIndex.v1", context_index["schema"])
        self.assertEqual(2, context_index["counts"]["storyKeys"])
        self.assertEqual(2, context_index["counts"]["contextRows"])
        self.assertEqual(
            {"black_fixture_1", "dlg_fixture_1"},
            {row["storyKey"] for row in context_index["rows"]},
        )
        self.assertTrue(all(
            row["ownership"] is False
            and row["activation"] is False
            and row["orderEvidence"] is False
            for row in context_index["rows"]
        ))
        self.assertEqual(
            "source/1001.json",
            context_index["rows"][0]["relatedOriginalFiles"][0]["sourceFile"],
        )

    def test_publish_attaches_exact_mission_levelscript_context_without_edge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            mission_root = Path(tmp)
            mission_path = mission_root / "fixture_mission.json"
            mission_path.write_text(
                __import__("json").dumps({
                    "mission": {"id": "fixture_mission"},
                    "storyOrder": {
                        "directEdges": [],
                        "summary": {"strongEdgeCount": 0},
                    },
                }),
                encoding="utf-8",
            )
            index = {
                "missions": [{"id": "fixture_mission"}],
                "storyCoverage": {"missionlessNativeRuntimeNodes": []},
            }
            report = {
                "schemaVersion": frontier.SCHEMA,
                "counts": {},
                "rows": [{
                    "levelId": "map_fixture",
                    "scriptId": "1001",
                    "storyKeys": ["cutscene_fixture_1"],
                    "eventNames": ["ScriptEvent_OnCustomEvent"],
                    "listenerHeaderLocalIds": [11],
                    "relatedOriginalFiles": [{
                        "kind": "levelscript",
                        "sourceFile": "source/1001.json",
                        "relationship": "exact context",
                    }],
                    "missionRuntimeScriptConsumers": [{
                        "missionId": "fixture_mission",
                        "questId": "fixture_mission_q#1",
                        "objectiveIndex": 1,
                        "conditionTypes": [
                            "CheckLevelScriptPropertyBool"
                        ],
                        "propertyKeys": ["isFinished"],
                    }],
                }],
            }
            frontier.publish_to_pipeline_index(
                index,
                report,
                mission_root=mission_root,
            )
            mission = __import__("json").loads(
                mission_path.read_text(encoding="utf-8")
            )
        contexts = mission["storyOrder"][
            "missionObservedLevelScriptContexts"
        ]
        self.assertEqual(1, len(contexts))
        self.assertEqual("map_fixture", contexts[0]["levelId"])
        self.assertEqual(["cutscene_fixture_1"], contexts[0]["storyKeys"])
        self.assertFalse(contexts[0]["ownership"])
        self.assertFalse(contexts[0]["orderEvidence"])
        self.assertEqual([], mission["storyOrder"]["directEdges"])
        self.assertEqual(
            1,
            index["missions"][0][
                "storyOrderMissionObservedLevelScriptContextCount"
            ],
        )

    def test_publish_attaches_mission_named_leveldata_receiver_context_without_edge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            mission_root = Path(tmp)
            mission_path = mission_root / "fixture_mission.json"
            mission_path.write_text(
                __import__("json").dumps({
                    "mission": {"id": "fixture_mission"},
                    "storyOrder": {
                        "directEdges": [],
                        "summary": {"strongEdgeCount": 0},
                    },
                }),
                encoding="utf-8",
            )
            index = {
                "missions": [{"id": "fixture_mission"}],
                "storyCoverage": {"missionlessNativeRuntimeNodes": []},
            }
            report = {
                "schemaVersion": frontier.SCHEMA,
                "counts": {},
                "rows": [{
                    "levelId": "map_fixture",
                    "scriptId": "1001",
                    "storyKeys": ["cutscene_fixture_1"],
                    "eventNames": ["ScriptEvent_OnCustomEvent"],
                    "listenerHeaderLocalIds": [11],
                    "activationClass": "manual_start_active_phase_receiver",
                    "levelScript": {"startTypeName": "Manual"},
                    "relatedOriginalFiles": [{
                        "kind": "levelscript",
                        "sourceFile": "source/1001.json",
                        "relationship": "exact context",
                    }],
                    "levelDataHosts": [{
                        "sourceFile": "source/fixture_mission.json",
                        "fileName": "map_fixture_lv_data_sub_fixture_mission.json",
                        "dictionaryEntryCount": 1,
                        "missionNamedHost": True,
                        "hostMissionId": "fixture_mission",
                        "briefData": {
                            "parentLevelScriptId": "0",
                            "propertyNames": ["is_enabled"],
                        },
                    }],
                }],
            }
            frontier.publish_to_pipeline_index(
                index,
                report,
                mission_root=mission_root,
            )
            mission = __import__("json").loads(
                mission_path.read_text(encoding="utf-8")
            )
        contexts = mission["storyOrder"][
            "missionNamedLevelDataReceiverContexts"
        ]
        self.assertEqual(1, len(contexts))
        context = contexts[0]
        self.assertEqual("fixture_mission", context["missionId"])
        self.assertEqual("map_fixture", context["levelId"])
        self.assertEqual(["cutscene_fixture_1"], context["storyKeys"])
        self.assertEqual(
            "leveldata_filename_mission_token_plus_member22_dictionary",
            context["levelDataHost"]["encoding"],
        )
        self.assertFalse(context["ownership"])
        self.assertFalse(context["activation"])
        self.assertFalse(context["storyPlayback"])
        self.assertFalse(context["orderEvidence"])
        self.assertEqual([], mission["storyOrder"]["directEdges"])
        self.assertEqual(
            1,
            mission["storyOrder"][
                "summary"
            ]["missionNamedLevelDataReceiverContextStoryCount"],
        )
        self.assertEqual(
            1,
            index["missions"][0][
                "storyOrderMissionNamedLevelDataReceiverContextCount"
            ],
        )

    def test_publish_attaches_shared_typed_mission_area_shell_to_each_mission(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            mission_root = Path(tmp)
            for mission_id in ("mission_a", "mission_b"):
                (mission_root / f"{mission_id}.json").write_text(
                    json.dumps({
                        "mission": {"id": mission_id},
                        "storyOrder": {
                            "nodes": [],
                            "directEdges": [],
                            "summary": {"strongEdgeCount": 0},
                        },
                    }),
                    encoding="utf-8",
                )
            index = {
                "missions": [{"id": "mission_a"}, {"id": "mission_b"}],
                "storyCoverage": {"missionlessNativeRuntimeNodes": []},
            }
            report = {
                "schemaVersion": frontier.SCHEMA,
                "counts": {},
                "missionAreaLevelDataShellCensus": {
                    "validation": {"status": "validated", "failures": []},
                },
                "rows": [{
                    "levelId": "map_fixture",
                    "scriptId": "1001",
                    "storyKeys": ["radio_fixture_1"],
                    "eventNames": ["ScriptEvent_OnCustomEvent"],
                    "listenerHeaderLocalIds": [11],
                    "activationClass": "nonmanual_start_with_shapes",
                    "levelScript": {"startTypeName": "ByEnterStartShape"},
                    "levelDataHosts": [],
                    "relatedOriginalFiles": [{
                        "kind": "levelscript",
                        "sourceFile": "source/1001.json",
                        "relationship": "exact receiver",
                    }],
                    "missionAreaLevelDataShellContext": {
                        "levelId": "map_fixture",
                        "scriptId": "1001",
                        "status": "shared",
                        "hostMissionIds": ["mission_a", "mission_b"],
                        "hosts": [{
                            "levelId": "map_fixture",
                            "scriptId": "1001",
                            "levelDataFile": "source/fixture_leveldata.json",
                            "hostMissionIds": ["mission_a", "mission_b"],
                            "rootScriptIds": ["9001"],
                            "missionAreaReferences": [
                                {
                                    "missionId": "mission_a",
                                    "missionAreaId": "area_a",
                                    "sourceFile": "source/mission_a.json",
                                },
                                {
                                    "missionId": "mission_b",
                                    "missionAreaId": "area_b",
                                    "sourceFile": "source/mission_b.json",
                                },
                            ],
                        }],
                    },
                }],
            }
            frontier.publish_to_pipeline_index(
                index,
                report,
                mission_root=mission_root,
            )
            missions = {
                mission_id: json.loads(
                    (mission_root / f"{mission_id}.json").read_text(
                        encoding="utf-8"
                    )
                )
                for mission_id in ("mission_a", "mission_b")
            }

        for mission_id, mission in missions.items():
            contexts = mission["storyOrder"][
                "missionAreaLevelDataReceiverContexts"
            ]
            self.assertEqual(1, len(contexts))
            self.assertEqual(mission_id, contexts[0]["missionId"])
            self.assertEqual("shared", contexts[0]["scopeStatus"])
            self.assertEqual(
                ["mission_a", "mission_b"],
                contexts[0]["hostMissionIds"],
            )
            self.assertFalse(contexts[0]["ownership"])
            self.assertFalse(contexts[0]["activation"])
            self.assertFalse(contexts[0]["storyPlayback"])
            self.assertFalse(contexts[0]["orderEvidence"])
            self.assertEqual([], mission["storyOrder"]["directEdges"])
            self.assertEqual(
                1,
                mission["storyOrder"]["summary"][
                    "missionAreaLevelDataReceiverSharedContextCount"
                ],
            )

    def test_publish_projects_exact_receiver_story_intersection_without_ownership(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            mission_root = Path(tmp)
            mission_path = mission_root / "fixture_mission.json"
            mission_path.write_text(
                __import__("json").dumps({
                    "mission": {"id": "fixture_mission"},
                    "storyOrder": {
                        "nodes": [{"key": "story_a"}, {"key": "story_b"}],
                        "directEdges": [],
                        "summary": {"strongEdgeCount": 0},
                    },
                }),
                encoding="utf-8",
            )
            index = {
                "missions": [{"id": "fixture_mission"}],
                "storyCoverage": {"missionlessNativeRuntimeNodes": []},
            }
            base_row = {
                "levelId": "map_fixture",
                "scriptId": "1001",
                "storyKeys": ["story_a", "story_external"],
                "storyKinds": ["cutscene", "radio"],
                "eventNames": ["LevelEvent_OnCustomEvent"],
                "listenerHeaderLocalIds": [11],
                "activationClass": "same_with_active_binary_active_gate",
                "missionOwnerStatus": "unresolved",
                "levelScript": {
                    "scriptIdVerified": True,
                    "serializedMemberCount": 27,
                    "actionMapRecordCount": 5,
                    "startTypeName": "SameWithActive",
                    "activeShapeListStatus": "decoded_unique",
                    "activeShapeListCount": 1,
                    "taskMapStatus": "present",
                    "taskMapCount": 1,
                    "activeShapeList": {
                        "followingFields": {"endTypeName": "Manual"},
                    },
                },
                "activePhaseReceiverControl": {
                    "schema": "exactActivePhaseReceiver.v1",
                    "status": "validated",
                    "classification": "registered_active_phase_story_receivers",
                    "allReceiversActivePhase": True,
                    "listenerHeaderCount": 1,
                    "resolvedHeaderCount": 1,
                    "receiverHeaders": [{
                        "listenerHeaderLocalId": 11,
                        "headerName": "LevelEvent_OnCustomEvent",
                        "triggerActiveDuring": 0,
                        "nextActionLocalId": 12,
                    }],
                    "topologySchema": "levelScriptNativeActionTopology.v4",
                    "topologyStatus": "exact_complete_action_map",
                    "runtimeFlow": {
                        "setupRegisterTriggerCallCount": 1,
                        "activePhaseEnableCallOffsets": [42],
                    },
                    "evidenceBoundary": "binary receiver only",
                },
                "clientActiveRequestControl": {
                    "schema": "exactClientActiveRequest.v1",
                    "status": "validated",
                    "classification": "client_runtime_active_request",
                    "levelScriptType": 0,
                    "levelScriptTypeName": "World",
                    "clientProducesActiveRequest": True,
                    "requiresActiveAreaGate": True,
                    "entryPublicState": "Enabled",
                    "spatialGateStatus": "validated_runtime_position_dependent",
                    "runtimePath": ["Enabled", "SendLevelScriptSetActive(true)"],
                    "evidenceBoundary": "binary request only",
                },
                "startRuntimePolicy": {
                    "schema": "levelScriptStartPolicy.v1",
                    "classification": "same_with_active_enters_prestart_when_active",
                    "validation": {"status": "validated"},
                    "evidenceBoundary": "binary start only",
                },
                "relatedOriginalFiles": [
                    {
                        "kind": "levelscript",
                        "sourceFile": "source/1001.json",
                        "relationship": "exact receiver",
                        "sha256": "a" * 64,
                    },
                    {
                        "kind": "original_game_binary",
                        "sourceFile": "GameAssembly.dll",
                        "relationship": "binary receiver contract",
                        "sha256": "b" * 64,
                    },
                ],
            }
            report = {
                "schemaVersion": frontier.SCHEMA,
                "counts": {},
                "rows": [
                    base_row,
                    {**base_row, "scriptId": "1002"},
                    {**base_row, "scriptId": "1003", "storyKeys": ["elsewhere"]},
                ],
            }
            frontier.publish_to_pipeline_index(
                index,
                report,
                mission_root=mission_root,
            )
            mission = __import__("json").loads(
                mission_path.read_text(encoding="utf-8")
            )

        contexts = mission["storyOrder"]["nativeReceiverStoryContexts"]
        self.assertEqual(2, len(contexts))
        self.assertEqual(["story_a"], contexts[0]["missionStoryKeys"])
        self.assertEqual(
            ["story_external"],
            contexts[0]["externalStoryKeys"],
        )
        self.assertEqual(
            "native_receiver_story_context",
            contexts[0]["relation"],
        )
        self.assertFalse(contexts[0]["ownership"])
        self.assertFalse(contexts[0]["activation"])
        self.assertFalse(contexts[0]["storyPlayback"])
        self.assertFalse(contexts[0]["orderEvidence"])
        self.assertEqual(
            "validated",
            contexts[0]["receiverEvidence"]["activePhaseReceiver"]["status"],
        )
        self.assertEqual(
            {"GameAssembly.dll", "source/1001.json"},
            {
                row["sourceFile"]
                for row in contexts[0]["relatedOriginalFiles"]
            },
        )
        self.assertEqual(
            2,
            mission["storyOrder"]["summary"]["nativeReceiverStoryContextCount"],
        )
        self.assertEqual(
            1,
            mission["storyOrder"]["summary"]["nativeReceiverStoryContextStoryCount"],
        )
        self.assertEqual(
            2,
            index["missions"][0]["storyOrderNativeReceiverStoryContextCount"],
        )
        self.assertEqual([], mission["storyOrder"]["directEdges"])

    def test_task_source_annotations_require_exact_keys(self) -> None:
        task_map = {
            "tasks": [
                {"taskKey": "fixture_task"},
                {"taskKey": "unmatched_task"},
            ]
        }
        extra = frontier.script_task_extra_info_rows(
            {
                "dataTable": {
                    "map_fixture": {
                        "1001": {
                            "fixture_task": {
                                "taskTitle": {"key": "fixture_title"},
                                "objectiveCount": 1,
                                "trackingInfoDict": {
                                    "Objective1": {
                                        "description": {
                                            "key": "fixture_description"
                                        },
                                        "needFormatProgress": True,
                                        "progressDisplayMode": 0,
                                    }
                                },
                            }
                        }
                    }
                }
            },
            source_file="fixture.json",
        )
        frontier.annotate_task_sources(
            task_map,
            level_id="map_fixture",
            script_id="1001",
            subgames=[
                {
                    "subGameId": "fixture_game",
                    "mainTaskIds": ["fixture_task"],
                    "missionOwnerStatus": "unresolved",
                }
            ],
            extra_info=extra,
        )
        task = task_map["tasks"][0]
        self.assertEqual("fixture_title", task["taskExtraInfo"]["taskTitleKey"])
        self.assertEqual(
            "fixture_description",
            task["taskExtraInfo"]["objectives"][0]["descriptionKey"],
        )
        self.assertEqual(
            "fixture_game",
            task["subGameMainTaskBindings"][0]["subGameId"],
        )
        self.assertNotIn("taskExtraInfo", task_map["tasks"][1])

    def test_task_progress_properties_require_complete_exact_pairs(self) -> None:
        task_map = {
            "tasks": [{
                "taskKey": "fixture_task",
                "conditions": [
                    {"conditionKey": "condition_a"},
                    {"conditionKey": "condition_b"},
                ],
            }]
        }
        hosts = [{
            "sourceFile": "fixture_leveldata.json",
            "briefData": {
                "properties": [
                    {
                        "name": f"lt:{prefix}:fixture_task:{condition}",
                        "valueType": 3,
                        "atomCount": 1,
                        "atoms": [{"valueBit64": int(prefix == "mp")}],
                    }
                    for condition in ("condition_a", "condition_b")
                    for prefix in ("p", "mp")
                ]
            },
        }]
        frontier.annotate_task_progress_property_contract(task_map, hosts)
        contract = task_map["tasks"][0]["progressPropertyContract"]
        self.assertEqual(contract["status"], "validated")
        self.assertEqual(contract["expectedPropertyCount"], 4)
        self.assertEqual(contract["matchedPropertyCount"], 4)
        self.assertEqual(contract["missingProperties"], [])

        hosts[0]["briefData"]["properties"].pop()
        frontier.annotate_task_progress_property_contract(task_map, hosts)
        contract = task_map["tasks"][0]["progressPropertyContract"]
        self.assertEqual(contract["status"], "incomplete")
        self.assertEqual(
            contract["missingProperties"],
            ["lt:mp:fixture_task:condition_b"],
        )

    def test_mission_runtime_ids_exclude_story_only_shells(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "authored_mission.json").write_text("{}", encoding="utf-8")
            (root / "story_shell.txt").write_text("", encoding="utf-8")
            self.assertEqual(
                frontier.mission_runtime_ids(root),
                {"authored_mission"},
            )

    def test_mission_runtime_operand_consumers_require_exact_typed_operands(
        self,
    ) -> None:
        indexes = frontier.mission_runtime_operand_consumers_from_payloads(
            [
                (
                    "mission_fixture",
                    {
                        "questId": "quest_fixture",
                        "conditions": [
                            {
                                "$type": "CheckTalkOptionFinish",
                                "_dialogId": {
                                    "constValue": "dialog_fixture"
                                },
                                "_finishId": {"constValue": 2},
                            },
                            {
                                "$type": "CheckLevelScriptTaskFinished",
                                "_sceneId": {"constValue": "map_fixture"},
                                "_scriptId": {
                                    "constValue": {"scriptId": 1001}
                                },
                                "_taskId": {"constValue": "task_fixture"},
                            },
                        ],
                    },
                    "fixture.json",
                )
            ]
        )
        self.assertEqual(
            "mission_fixture",
            indexes["dialog"][("dialog_fixture", 2)][0]["missionId"],
        )
        self.assertNotIn(("dialog_fixture", 1), indexes["dialog"])
        self.assertEqual({}, indexes["area"])
        self.assertEqual(
            "quest_fixture",
            indexes["task"][("map_fixture", "1001", "task_fixture")][0][
                "questId"
            ],
        )

    def test_world_entity_sources_keep_only_unique_script_slots(self) -> None:
        logic_rows, slot_rows = frontier.world_entity_operand_sources(
            {
                "worldEntityBriefInfos": {
                    "9001": {
                        "entityType": 2,
                        "detailId": "enemy_fixture",
                    }
                },
                "m_scriptEntityIdList": [
                    {"scriptIdGlobal": "1001", "slotId": 4},
                    {"scriptIdGlobal": "1001", "slotId": 5},
                    {"scriptIdGlobal": "1001", "slotId": 5},
                ],
                "m_scriptEntityBriefInfo": [
                    {"entityType": 2, "detailId": "slot_fixture"},
                    {"entityType": 2, "detailId": "duplicate_a"},
                    {"entityType": 2, "detailId": "duplicate_b"},
                ],
            }
        )
        self.assertEqual("enemy_fixture", logic_rows["9001"]["detailId"])
        self.assertEqual("slot_fixture", slot_rows[("1001", 4)]["entityDetailId"])
        self.assertNotIn(("1001", 5), slot_rows)

    def test_task_operand_annotations_preserve_non_owning_sources(self) -> None:
        task_map = {
            "tasks": [
                {
                    "taskKey": "fixture_task",
                    "conditions": [
                        {
                            "condition": {
                                "type": "CheckEntityHp",
                                "entity": {
                                    "useSlotId": False,
                                    "logicId": "9001",
                                },
                            }
                        },
                        {
                            "condition": {
                                "type": "TaskReachDestination",
                                "areaId": {"value": "area_fixture"},
                            }
                        },
                    ],
                }
            ]
        }
        consumers = {
            kind: {}
            for kind in (
                "dialog",
                "area",
                "spawner",
                "script",
                "entity",
                "task",
            )
        }
        consumers["entity"][("map_fixture", 9001)] = [
            {
                "missionId": "mission_fixture",
                "questId": "quest_fixture",
                "conditionType": "CheckEntityHp",
                "sourceFile": "mission_fixture.json",
            }
        ]
        consumers["task"][("map_fixture", "1001", "fixture_task")] = [
            {
                "missionId": "task_mission_fixture",
                "questId": "task_quest_fixture",
                "conditionType": "CheckLevelScriptTaskFinished",
                "sourceFile": "task_mission_fixture.json",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_root = Path(temp_dir)
            frontier.annotate_task_condition_operands(
                task_map,
                level_id="map_fixture",
                script_id="1001",
                story_keys=[],
                mission_areas=[
                    {
                        "missionAreaId": "area_fixture",
                        "subDataParentId": 7,
                        "shape": {"type": 2},
                    }
                ],
                logic_entities={
                    "9001": {
                        "entityType": 2,
                        "detailId": "enemy_fixture",
                    }
                },
                slot_entities={},
                mission_consumers=consumers,
                levelscript_root=empty_root,
                spawner_root=empty_root,
            )
        entity_row, area_row = task_map["tasks"][0]["conditions"]
        self.assertEqual(
            "task_mission_fixture",
            task_map["tasks"][0]["missionRuntimeTaskConsumers"][0][
                "missionId"
            ],
        )
        self.assertEqual(
            "world_entity_logic_id",
            entity_row["operandSources"][0]["kind"],
        )
        self.assertEqual(
            "mission_fixture",
            entity_row["missionRuntimeOperandConsumers"][0]["missionId"],
        )
        self.assertEqual(
            "same_level_mission_area",
            area_row["operandSources"][0]["kind"],
        )
        self.assertNotIn("missionRuntimeOperandConsumers", area_row)


    @staticmethod
    def _trigger_fixture_index(story_files: list[dict]) -> dict:
        return {
            "storyCoverage": {
                "missionlessNativeRuntimeNodes": [{
                    "eventName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "selector": {
                        "levelId": "map_fixture",
                        "listenerScriptId": "1001",
                        "listenerHeaderLocalId": 7,
                    },
                    "storyFiles": story_files,
                }]
            }
        }

    @staticmethod
    def _trigger_overlay(source_file: Path, *, shadowed: list[dict] | None = None) -> dict:
        source = source_file.resolve().as_posix()
        return {
            "schema": "levelScriptActiveOverlay.v1",
            "status": "validated_active_overlay",
            "availableRootCount": 1,
            "fileCount": 1,
            "validationFailures": [],
            "files": {
                "map_fixture/1001.json": {
                    "logicalPath": "map_fixture/1001.json",
                    "sourceFile": source,
                    "sourceRoot": source_file.parent.parent.as_posix(),
                    "sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
                    "status": "fallback",
                    "shadowed": shadowed or [],
                }
            },
        }

    @staticmethod
    def _exact_topology(event_name: str, detail: dict) -> tuple[dict, None]:
        return ({
            "status": "exact_complete_action_map",
            "eventRoots": [{
                "localId": 7,
                "headerName": event_name,
                "eventDetail": detail,
            }],
        }, None)

    def test_story_trigger_zone_exact_local_volume_includes_shape_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            volume = {
                "slotId": 80001,
                "triggerVolumeType": "Leader",
                "shapeList": {
                    "status": "present",
                    "parseStatus": "decoded",
                    "shapes": [{"shapeType": "Box", "size": {"x": 3}}],
                },
            }
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "ScriptEvent_OnLeaderEnterTriggerVolume",
                    {
                        "triggerSlotIdFilter": 80001,
                        "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    },
                ),
            ), mock.patch.object(
                frontier,
                "decode_levelscript_binary_summary",
                return_value={
                    "scriptIdVerified": True,
                    "triggerVolumesDetails": {
                        "volumes": [{"slotId": 80001}],
                    },
                },
            ), mock.patch.object(
                frontier,
                "classify_local_trigger_volume_context",
                return_value={
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "triggerVolumes": [volume],
                    "missingSlotIds": [],
                    "ambiguousSlotIds": [],
                },
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([{
                        "key": "radio_fixture_1",
                        "sourceFiles": [source.resolve().as_posix()],
                    }]),
                    overlay_index=self._trigger_overlay(source),
                )
        row = report["rows"][0]
        observation = row["observations"][0]
        self.assertEqual("exact_local_trigger_volume", row["status"])
        self.assertEqual(80001, observation["triggerSlotIdFilter"])
        self.assertEqual("Leader", observation["triggerVolumeType"])
        self.assertEqual(volume["shapeList"]["shapes"], observation["decodedShape"])
        self.assertRegex(observation["sourceSha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(row["ownership"])

    def test_story_trigger_zone_list_selector_keeps_each_exact_slot_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            detail = {
                "type": "ScriptEvent_OnLeaderEnterTriggerVolumeList",
                "scriptEventScope": "owning-level-script",
                "triggerTarget": "SELF",
                "targetScriptPresent": False,
                "validateParam": {"constValue": True},
                "triggerSlotIdFilters": [80001, 80002],
                "triggerSlotIdFilterCount": 2,
                "payloadShape": "constant-trigger-slot-list-selector-prefix",
                "transport": "local-authored-trigger-volume-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "payloadSchemaMappingId": frontier.LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID,
            }
            topology = self._exact_topology(
                "ScriptEvent_OnLeaderEnterTriggerVolumeList", detail,
            )
            topology[0]["eventRoots"][0].update({
                "unionTag": "0x00bf",
                "serializedMemberCount": 17,
            })
            volumes = [{
                "slotId": slot_id,
                "triggerVolumeType": "Leader",
                "shapeList": {"shapes": [{
                    "shapeType": "Sphere",
                    "position": {"x": float(index), "y": 2.0, "z": 3.0},
                }]},
            } for index, slot_id in enumerate((80001, 80002), start=1)]
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=topology,
            ), mock.patch.object(
                frontier,
                "decode_levelscript_binary_summary",
                return_value={
                    "scriptIdVerified": True,
                    "triggerVolumesDetails": {"volumes": volumes},
                },
            ), mock.patch.object(
                frontier,
                "classify_local_trigger_volume_context",
                return_value={
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "triggerVolumes": volumes,
                    "missingSlotIds": [],
                    "ambiguousSlotIds": [],
                },
            ) as classifier:
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([{
                        "key": "radio_trigger_list",
                        "sourceFiles": [source.resolve().as_posix()],
                    }]),
                    overlay_index=self._trigger_overlay(source),
                )

        row = report["rows"][0]
        self.assertEqual("multiple_or_ambiguous_trigger_zones", row["status"])
        self.assertEqual(2, row["observationCount"])
        self.assertEqual(2, row["exactZoneCount"])
        observations = sorted(
            row["observations"], key=lambda item: item["triggerSlotIdFilter"],
        )
        self.assertEqual([80001, 80002], [
            item["triggerSlotIdFilter"] for item in observations
        ])
        self.assertTrue(all(
            item["triggerSlotIdFilters"] == [80001, 80002]
            and item["multiLocationSemantics"]
            == "explicit_independent_trigger_slots"
            for item in observations
        ))
        self.assertEqual(
            [1.0, 2.0],
            [item["decodedShape"][0]["position"]["x"] for item in observations],
        )
        classifier.assert_called_once()
        self.assertEqual([80001, 80002], classifier.call_args.args[1])

    def test_story_trigger_zone_list_selector_duplicate_or_missing_slot_fails_closed(self) -> None:
        for case in ("duplicate_selector", "missing_volume"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"active")
                selector_slots = (
                    [80001, 80001]
                    if case == "duplicate_selector"
                    else [80001, 80002]
                )
                detail = {
                    "type": "ScriptEvent_OnLeaderEnterTriggerVolumeList",
                    "scriptEventScope": "owning-level-script",
                    "triggerTarget": "SELF",
                    "targetScriptPresent": False,
                    "validateParam": {"constValue": True},
                    "triggerSlotIdFilters": selector_slots,
                    "triggerSlotIdFilterCount": 2,
                    "payloadShape": "constant-trigger-slot-list-selector-prefix",
                    "transport": "local-authored-trigger-volume-event",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "payloadSchemaMappingId": frontier.LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID,
                }
                topology = self._exact_topology(
                    "ScriptEvent_OnLeaderEnterTriggerVolumeList", detail,
                )
                topology[0]["eventRoots"][0].update({
                    "unionTag": "0x00bf",
                    "serializedMemberCount": 17,
                })
                with mock.patch.object(
                    frontier,
                    "decode_levelscript_native_action_topology",
                    return_value=topology,
                ), mock.patch.object(
                    frontier,
                    "decode_levelscript_binary_summary",
                    return_value={
                        "scriptIdVerified": True,
                        "triggerVolumesDetails": {
                            "volumes": [{"slotId": 80001}],
                        },
                    },
                ), mock.patch.object(
                    frontier,
                    "classify_local_trigger_volume_context",
                    return_value={
                        "status": "unresolved_local_levelscript_trigger_volume",
                        "triggerVolumes": [],
                        "missingSlotIds": [80002],
                        "ambiguousSlotIds": [],
                        "triggerVolumesStatus": "present",
                        "triggerVolumesParseStatus": "decoded",
                    },
                ) as classifier:
                    report = frontier.build_story_trigger_zone_coverage(
                        self._trigger_fixture_index([{
                            "key": f"radio_trigger_list_{case}",
                            "sourceFiles": [source.resolve().as_posix()],
                        }]),
                        overlay_index=self._trigger_overlay(source),
                    )

            row = report["rows"][0]
            self.assertEqual("trigger_event_known_spatial_unresolved", row["status"])
            self.assertEqual(0, row["exactZoneCount"])
            observation = row["observations"][0]
            if case == "duplicate_selector":
                self.assertEqual(
                    "exactEntityTriggerSelectorContract",
                    observation["diagnostics"][0]["gate"],
                )
                classifier.assert_not_called()
            else:
                self.assertEqual(
                    "uniqueDecodedLocalTriggerVolume",
                    observation["diagnostics"][0]["gate"],
                )
                classifier.assert_called_once()

    def test_story_trigger_zone_shared_zone_is_exact_for_each_story_without_fanout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "ScriptEvent_OnLeaderEnterTriggerVolume",
                    {
                        "triggerSlotIdFilter": 80001,
                        "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    },
                ),
            ), mock.patch.object(
                frontier,
                "decode_levelscript_binary_summary",
                return_value={
                    "scriptIdVerified": True,
                    "triggerVolumesDetails": {
                        "volumes": [{"slotId": 80001}],
                    },
                },
            ), mock.patch.object(
                frontier,
                "classify_local_trigger_volume_context",
                return_value={
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "triggerVolumes": [{
                        "slotId": 80001,
                        "triggerVolumeType": "Leader",
                        "shapeList": {"shapes": [{"shapeType": "Sphere"}]},
                    }],
                },
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([
                        {"key": "radio_fixture_1", "sourceFiles": [source.resolve().as_posix()]},
                        {"key": "radio_fixture_2", "sourceFiles": [source.resolve().as_posix()]},
                    ]),
                    overlay_index=self._trigger_overlay(source),
                )
        self.assertEqual(2, report["counts"]["storyFiles"])
        self.assertEqual(
            ["exact_local_trigger_volume", "exact_local_trigger_volume"],
            [row["status"] for row in report["rows"]],
        )
        self.assertTrue(all(not row["ownership"] for row in report["rows"]))

    def test_story_trigger_zone_exact_non_spatial_event_is_not_a_zone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "ScriptEvent_OnCustomEvent",
                    {
                        "eventKey": "OnFixture",
                        "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    },
                ),
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([
                        {"key": "radio_fixture", "sourceFiles": [source.resolve().as_posix()]}
                    ]),
                    overlay_index=self._trigger_overlay(source),
                )
        observation = report["rows"][0]["observations"][0]
        self.assertEqual("exact_non_spatial_event_trigger", report["rows"][0]["status"])
        self.assertFalse(observation.get("spatiallyApplicable"))
        self.assertEqual(0, report["rows"][0]["exactZoneCount"])

    def test_story_trigger_zone_uses_unique_enriched_playback_owner_detail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            source_file = source.resolve().as_posix()
            fallback_detail = {
                "type": "LevelEvent_OnSpawnerWaveBegin",
                "payloadDecodeStatus": "partial_known_fields",
                "payloadSchemaStatus": "partial_known_fields",
            }
            enriched_detail = {
                "type": "LevelEvent_OnSpawnerWaveBegin",
                "spawnerFilterId": 1002003,
                "payloadDecodeStatus": "exact_complete_subtype",
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
            }
            occurrence = {
                "levelId": "map_fixture",
                "scriptId": "1001",
                "sourceFile": source_file,
                "actionName": "PlayRadio",
                "recordClass": "play_radio",
                "localId": 12,
                "triggerPlaybackBindingEligible": True,
                "playbackExecutionRole": "direct_playback",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerLocalId": 7,
                    "eventDetail": enriched_detail,
                    "path": [{"localId": 9}, {"localId": 12}],
                }],
            }
            with mock.patch.object(
                frontier,
                "build_active_levelscript_action_story_occurrences",
                return_value={"radio_fixture": [occurrence]},
            ), mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "LevelEvent_OnSpawnerWaveBegin", fallback_detail,
                ),
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([{
                        "key": "radio_fixture",
                        "sourceFiles": [source_file],
                    }]),
                    overlay_index=self._trigger_overlay(source),
                )

        observation = report["rows"][0]["observations"][0]
        self.assertEqual(enriched_detail, observation["eventDetail"])
        self.assertEqual(1002003, observation["eventDetail"]["spawnerFilterId"])
        self.assertEqual("exact_non_spatial_event_trigger", observation["status"])

    def test_story_trigger_zone_does_not_use_ambiguous_or_foreign_enriched_detail(self) -> None:
        fallback_detail = {
            "type": "LevelEvent_OnSpawnerWaveBegin",
            "payloadDecodeStatus": "partial_known_fields",
            "payloadSchemaStatus": "partial_known_fields",
        }
        exact_details = [
            {
                "type": "LevelEvent_OnSpawnerWaveBegin",
                "spawnerFilterId": spawner_id,
                "payloadDecodeStatus": "exact_complete_subtype",
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
            }
            for spawner_id in (1002003, 1002004)
        ]
        for case in ("ambiguous", "foreign_source"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"active")
                source_file = source.resolve().as_posix()
                occurrences = []
                for index, detail in enumerate(exact_details):
                    occurrence_source = source_file
                    if case == "foreign_source":
                        occurrence_source = f"{source_file}.foreign"
                    occurrences.append({
                        "levelId": "map_fixture",
                        "scriptId": "1001",
                        "sourceFile": occurrence_source,
                        "actionName": "PlayRadio",
                        "recordClass": "play_radio",
                        "localId": 12 + index,
                        "triggerPlaybackBindingEligible": True,
                        "playbackExecutionRole": "direct_playback",
                        "nativeEventOwners": [{
                            "status": "exact_serialized_control_path",
                            "headerLocalId": 7,
                            "eventDetail": detail,
                            "path": [{"localId": 12 + index}],
                        }],
                    })
                with mock.patch.object(
                    frontier,
                    "build_active_levelscript_action_story_occurrences",
                    return_value={"radio_fixture": occurrences},
                ), mock.patch.object(
                    frontier,
                    "decode_levelscript_native_action_topology",
                    return_value=self._exact_topology(
                        "LevelEvent_OnSpawnerWaveBegin", fallback_detail,
                    ),
                ):
                    report = frontier.build_story_trigger_zone_coverage(
                        self._trigger_fixture_index([{
                            "key": "radio_fixture",
                            "sourceFiles": [source_file],
                        }]),
                        overlay_index=self._trigger_overlay(source),
                    )

            matching = [
                row for row in report["rows"][0]["observations"]
                if row.get("sourceFile") == source_file
            ]
            self.assertEqual(1, len(matching))
            self.assertEqual(fallback_detail, matching[0]["eventDetail"])
            self.assertNotIn("spawnerFilterId", matching[0]["eventDetail"])

    def test_non_spatial_event_with_unvalidated_payload_is_not_labeled_spatial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            with mock.patch.object(
                frontier, "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "ScriptEvent_OnCustomEvent", {"eventKey": "fixture"},
                ),
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([{
                        "key": "radio_fixture", "sourceFiles": [source.resolve().as_posix()]
                    }]),
                    overlay_index=self._trigger_overlay(source),
                )

        row = report["rows"][0]
        self.assertEqual("non_spatial_event_payload_unresolved", row["status"])
        self.assertFalse(row["observations"][0]["spatiallyApplicable"])
        self.assertEqual(
            "exactNonSpatialEventPayload",
            row["observations"][0]["diagnostics"][0]["gate"],
        )

    def test_trigger_rooted_playback_requires_same_action_node_on_typed_header_path(self) -> None:
        common = {
            "levelId": "map_fixture", "scriptId": "1001",
            "sourceFile": "root/1001.json", "actionName": "PlayRadio",
            "recordClass": "play_radio", "localId": 12, "recordOffset": 40,
            "triggerPlaybackBindingEligible": True,
            "playbackExecutionRole": "direct_playback",
        }
        exact = frontier._classify_trigger_rooted_story_playback(
            [{**common, "nativeEventOwners": [{
                "status": "exact_serialized_control_path", "headerLocalId": 7,
                "path": [{"localId": 9}, {"localId": 12}],
            }]}, {**common, "actionName": "PlayCutsceneAction",
                  "recordClass": "preload_cutscene", "localId": 13,
                  "triggerPlaybackBindingEligible": False,
                  "playbackExecutionRole": "preload",
                  "nativeEventOwners": [{
                      "status": "exact_serialized_control_path", "headerLocalId": 7,
                      "path": [{"localId": 13}],
                  }]}],
            story_key="radio_fixture", level_id="map_fixture", script_id="1001",
            source_file="root/1001.json", header_local_id=7,
        )
        sibling = frontier._classify_trigger_rooted_story_playback(
            [{**common, "nativeEventOwners": [{
                "status": "exact_serialized_control_path", "headerLocalId": 8,
                "path": [{"localId": 12}],
            }]}],
            story_key="radio_fixture", level_id="map_fixture", script_id="1001",
            source_file="root/1001.json", header_local_id=7,
        )

        self.assertEqual("exact_trigger_rooted_playback", exact["status"])
        self.assertEqual(12, exact["candidates"][0]["actionLocalId"])
        self.assertEqual(1, exact["excludedReasonCounts"][
            "non_playback_lifecycle_action"
        ])
        self.assertEqual("unresolved_trigger_rooted_playback", sibling["status"])
        self.assertEqual(1, sibling["excludedReasonCounts"][
            "typed_header_does_not_uniquely_reach_playback_action"
        ])

    def test_trigger_rooted_playback_accepts_multiple_exact_paths_from_same_header(self) -> None:
        common = {
            "levelId": "map_fixture", "scriptId": "1001",
            "sourceFile": "root/1001.json", "actionName": "PlayRadioAndWait",
            "recordClass": "play_radio", "localId": 28, "recordOffset": 40,
            "triggerPlaybackBindingEligible": True,
            "playbackExecutionRole": "direct_playback",
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path", "headerLocalId": 8,
                "path": [{"localId": 15}, {"localId": 16}, {"localId": 28}],
            }, {
                "status": "exact_serialized_control_path", "headerLocalId": 8,
                "path": [{"localId": 15}, {"localId": 31}, {"localId": 28}],
            }],
        }
        result = frontier._classify_trigger_rooted_story_playback(
            [common], story_key="radio_fixture", level_id="map_fixture",
            script_id="1001", source_file="root/1001.json", header_local_id=8,
        )
        self.assertEqual("exact_trigger_rooted_playback", result["status"])
        self.assertEqual(1, result["candidateCount"])
        self.assertEqual(2, result["candidates"][0]["exactControlPathCount"])

    def test_story_trigger_zone_missing_shape_is_spatially_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "ScriptEvent_OnLeaderEnterTriggerVolume",
                    {"triggerSlotIdFilter": 80001},
                ),
            ), mock.patch.object(
                frontier,
                "decode_levelscript_binary_summary",
                return_value={"scriptIdVerified": True},
            ), mock.patch.object(
                frontier,
                "classify_local_trigger_volume_context",
                return_value={
                    "status": "unresolved_local_levelscript_trigger_volume",
                    "missingSlotIds": [80001],
                    "ambiguousSlotIds": [],
                    "triggerVolumesStatus": "present",
                    "triggerVolumesParseStatus": "decoded",
                },
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([
                        {"key": "radio_fixture", "sourceFiles": [source.resolve().as_posix()]}
                    ]),
                    overlay_index=self._trigger_overlay(source),
                )
        row = report["rows"][0]
        self.assertEqual("trigger_event_known_spatial_unresolved", row["status"])
        self.assertEqual("uniqueDecodedLocalTriggerVolume", row["observations"][0]["diagnostics"][0]["gate"])

    def test_direct_playback_occurrence_discovers_exact_trigger_without_missionless_node(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            occurrence = {
                "levelId": "map_fixture", "scriptId": "1001",
                "sourceFile": source.resolve().as_posix(),
                "actionName": "PlayRadio", "recordClass": "play_radio",
                "localId": 12, "recordOffset": 40,
                "triggerPlaybackBindingEligible": True,
                "playbackExecutionRole": "direct_playback",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path", "headerLocalId": 7,
                    "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "path": [{"localId": 9}, {"localId": 12}],
                }],
            }
            volume = {
                "slotId": 80001, "triggerVolumeType": "Leader",
                "shapeList": {"shapes": [{"shapeType": "Box"}]},
            }
            with mock.patch.object(
                frontier, "build_active_levelscript_action_story_occurrences",
                return_value={"radio_fixture": [occurrence]},
            ), mock.patch.object(
                frontier, "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "ScriptEvent_OnLeaderEnterTriggerVolume",
                    {"triggerSlotIdFilter": 80001,
                     "payloadSchemaStatus": "exact_current_build_memorypack_fields"},
                ),
            ), mock.patch.object(
                frontier, "decode_levelscript_binary_summary",
                return_value={"scriptIdVerified": True,
                              "triggerVolumesDetails": {"volumes": [{"slotId": 80001}]}},
            ), mock.patch.object(
                frontier, "classify_local_trigger_volume_context",
                return_value={
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "scriptIdVerified": True, "matchedSlotIds": [80001],
                    "missingSlotIds": [], "ambiguousSlotIds": [],
                    "triggerVolumes": [volume],
                },
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    {"storyCoverage": {"missionlessNativeRuntimeNodes": []}},
                    overlay_index=self._trigger_overlay(source),
                )

        self.assertEqual(1, report["counts"]["directPlaybackCandidateCount"])
        self.assertEqual("exact_local_trigger_volume", report["rows"][0]["status"])
        self.assertTrue(report["rows"][0]["observations"][0]["directPlaybackEnumeration"])
        self.assertEqual(
            "exact_trigger_rooted_playback",
            report["rows"][0]["observations"][0]["playbackControlPathEvidence"]["status"],
        )

    def test_story_trigger_zone_changed_shadow_fails_closed_without_stale_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            active = root / "Persistent" / "LevelScriptData" / "map_fixture" / "1001.json"
            active.parent.mkdir(parents=True)
            active.write_bytes(b"active")
            stale = root / "StreamingAssets" / "LevelScriptData" / "map_fixture" / "1001.json"
            stale.parent.mkdir(parents=True)
            stale.write_bytes(b"stale")
            overlay = self._trigger_overlay(active, shadowed=[{
                "sourceFile": stale.resolve().as_posix(),
                "sourceRoot": stale.parent.parent.as_posix(),
                "sha256": "b" * 64,
                "status": "changed_override",
            }])
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
            ) as decoder, mock.patch.object(
                frontier,
                "build_active_levelscript_action_story_occurrences",
                return_value={},
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([
                        {"key": "radio_fixture", "sourceFiles": [stale.resolve().as_posix()]}
                    ]),
                    overlay_index=overlay,
                )
        row = report["rows"][0]
        self.assertEqual("active_overlay_unavailable", row["status"])
        self.assertEqual("activeHeaderPlaybackRemap", row["observations"][0]["diagnostics"][0]["gate"])
        decoder.assert_not_called()

    def test_story_trigger_zone_preload_only_placement_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            index = self._trigger_fixture_index([{
                "key": "cutscene_preload_only",
                "nativeActions": ["PreloadCutsceneAction"],
                "sourceFiles": [source.resolve().as_posix()],
            }])
            with mock.patch.object(frontier, "decode_levelscript_native_action_topology") as decoder:
                report = frontier.build_story_trigger_zone_coverage(
                    index,
                    overlay_index=self._trigger_overlay(source),
                )
        row = report["rows"][0]
        self.assertEqual("preload_only_excluded", row["status"])
        self.assertEqual(0, row["observationCount"])
        self.assertEqual(1, report["counts"]["preloadExcludedPlacementCount"])
        decoder.assert_not_called()

    def test_story_trigger_zone_entity_target_slot_requires_exact_positive_selector(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            index = self._trigger_fixture_index([{
                "key": "radio_entity_slot",
                "sourceFiles": [source.resolve().as_posix()],
            }])
            topology = self._exact_topology(
                "EntityEvent_OnLeaderEnterTrigger",
                {
                    "entityEventScope": "specified-entity",
                    "triggerTarget": "SPECIFY_ENTITY",
                    "targetEntity": {
                        "logicId": 0,
                        "useSlotId": True,
                        "slotId": 80001,
                    },
                    "targetEntityListPresent": False,
                    "targetEntityListOutputPresent": False,
                    "transport": "local-authored-trigger-volume-event",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "payloadSchemaMappingId": frontier.LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID,
                    "validateParam": {"constValue": True},
                },
            )
            volume = {
                "slotId": 80001,
                "triggerVolumeType": "Leader",
                "shapeList": {"shapes": [{"shapeType": "Box"}]},
            }
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=topology,
            ), mock.patch.object(
                frontier,
                "decode_levelscript_binary_summary",
                return_value={
                    "scriptIdVerified": True,
                    "triggerVolumesDetails": {
                        "volumes": [{"slotId": 80001}],
                    },
                },
            ), mock.patch.object(
                frontier,
                "classify_local_trigger_volume_context",
                return_value={
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "triggerVolumes": [volume],
                },
            ) as classifier:
                report = frontier.build_story_trigger_zone_coverage(
                    index,
                    overlay_index=self._trigger_overlay(source),
                )
        self.assertEqual("exact_local_trigger_volume", report["rows"][0]["status"])
        self.assertEqual(
            "eventDetail.targetEntity.slotId",
            report["rows"][0]["observations"][0]["triggerSelectorKind"],
        )
        self.assertEqual([80001], classifier.call_args.args[1])

    def test_story_trigger_zone_entity_target_slot_rejects_non_exact_selector(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"active")
            topology = self._exact_topology(
                "EntityEvent_OnLeaderEnterTrigger",
                {
                    "entityEventScope": "specified-entity",
                    "triggerTarget": "SPECIFY_ENTITY",
                    "targetEntity": {
                        "logicId": 0,
                        "useSlotId": False,
                        "slotId": 80001,
                    },
                    "targetEntityListPresent": False,
                    "targetEntityListOutputPresent": False,
                    "transport": "local-authored-trigger-volume-event",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "payloadSchemaMappingId": frontier.LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID,
                    "validateParam": {"constValue": True},
                },
            )
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=topology,
            ), mock.patch.object(
                frontier,
                "decode_levelscript_binary_summary",
                return_value={
                    "scriptIdVerified": True,
                    "triggerVolumesDetails": {"volumes": [{"slotId": 80001}]},
                },
            ), mock.patch.object(
                frontier,
                "classify_local_trigger_volume_context",
                return_value={
                    "status": "unresolved_local_levelscript_trigger_volume",
                    "missingSlotIds": [],
                    "ambiguousSlotIds": [],
                },
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    self._trigger_fixture_index([{
                        "key": "radio_entity_slot_bad",
                        "sourceFiles": [source.resolve().as_posix()],
                    }]),
                    overlay_index=self._trigger_overlay(source),
                )
        observation = report["rows"][0]["observations"][0]
        self.assertEqual(
            "trigger_event_known_spatial_unresolved",
            report["rows"][0]["status"],
        )
        self.assertIsNone(observation["triggerSlotIdFilter"])

    def test_story_trigger_zone_entity_target_contract_rejects_each_non_exact_field(self) -> None:
        valid = {
            "entityEventScope": "specified-entity",
            "triggerTarget": "SPECIFY_ENTITY",
            "targetEntity": {"logicId": 0, "useSlotId": True, "slotId": 80001},
            "targetEntityListPresent": False,
            "targetEntityListOutputPresent": False,
            "transport": "local-authored-trigger-volume-event",
            "serverExchange": False,
            "serializedMissionOrQuestId": False,
            "payloadSchemaStatus": "exact_current_build_memorypack_fields",
            "payloadSchemaMappingId": frontier.LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID,
            "validateParam": {"constValue": True},
        }
        variants = {
            "logicId": {"targetEntity": {"logicId": 123}},
            "scope": {"entityEventScope": "selected-entity"},
            "target": {"triggerTarget": "OTHER"},
            "transport": {"transport": "local-entity-runtime-event"},
            "server": {"serverExchange": True},
            "mapping": {"payloadSchemaMappingId": "wrong"},
            "list": {"targetEntityListPresent": True},
            "validate": {"validateParam": {"constValue": False}},
        }
        for name, changes in variants.items():
            with self.subTest(field=name), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "LevelScriptData" / "map_fixture" / "1001.json"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"active")
                detail = {
                    **valid,
                    "targetEntity": dict(valid["targetEntity"]),
                    "validateParam": dict(valid["validateParam"]),
                }
                detail.update(changes)
                topology = self._exact_topology("EntityEvent_OnLeaderEnterTrigger", detail)
                with mock.patch.object(
                    frontier,
                    "decode_levelscript_native_action_topology",
                    return_value=topology,
                ), mock.patch.object(
                    frontier,
                    "decode_levelscript_binary_summary",
                    return_value={
                        "scriptIdVerified": True,
                        "triggerVolumesDetails": {"volumes": [{"slotId": 80001}]},
                    },
                ), mock.patch.object(
                    frontier,
                    "classify_local_trigger_volume_context",
                ) as classifier:
                    report = frontier.build_story_trigger_zone_coverage(
                        self._trigger_fixture_index([{
                            "key": f"radio_entity_contract_{name}",
                            "sourceFiles": [source.resolve().as_posix()],
                        }]),
                        overlay_index=self._trigger_overlay(source),
                    )
                observation = report["rows"][0]["observations"][0]
                self.assertEqual(
                    "trigger_event_known_spatial_unresolved",
                    report["rows"][0]["status"],
                )
                self.assertEqual(
                    "exactEntityTriggerSelectorContract",
                    observation["diagnostics"][0]["gate"],
                )
                classifier.assert_not_called()

    def test_story_trigger_zone_changed_shadow_rederives_active_header_and_playback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            active = root / "Persistent" / "LevelScriptData" / "map_fixture" / "1001.json"
            active.parent.mkdir(parents=True)
            active.write_bytes(b"active")
            stale = root / "StreamingAssets" / "LevelScriptData" / "map_fixture" / "1001.json"
            stale.parent.mkdir(parents=True)
            stale.write_bytes(b"stale")
            active_source = active.resolve().as_posix()
            old_source = stale.resolve().as_posix()
            active_hash = hashlib.sha256(active.read_bytes()).hexdigest()
            overlay = self._trigger_overlay(active, shadowed=[{
                "sourceFile": old_source,
                "sourceRoot": stale.parent.parent.as_posix(),
                "sha256": hashlib.sha256(stale.read_bytes()).hexdigest(),
                "status": "changed_override",
            }])
            topology = self._exact_topology(
                "LevelEvent_OnBattleSignal",
                {
                    "signalId": "active_signal",
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                },
            )
            occurrence = {
                "levelId": "map_fixture",
                "scriptId": "1001",
                "sourceFile": active_source,
                "activeOverlaySourceSha256": active_hash,
                "actionName": "PlayRadio",
                "recordClass": "play_radio",
                "playbackExecutionRole": "direct_playback",
                "triggerPlaybackBindingEligible": True,
                "localId": 9,
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "LevelEvent_OnBattleSignal",
                    "headerLocalId": 12,
                    "eventDetail": topology[0]["eventRoots"][0]["eventDetail"],
                    "path": [{"localId": 9}],
                }],
            }
            topology[0]["eventRoots"][0]["localId"] = 12
            topology[0]["actions"] = [{
                "localId": 9,
                "actionName": "PlayRadio",
                "texts": ["radio_active_remap"],
            }]
            index = self._trigger_fixture_index([{
                "key": "radio_active_remap",
                "nativeActions": ["PlayRadio"],
                "sourceFiles": [old_source],
            }])
            with mock.patch.object(
                frontier,
                "build_active_levelscript_action_story_occurrences",
                return_value={"radio_active_remap": [occurrence]},
            ), mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=topology,
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    index,
                    overlay_index=overlay,
                )
        observation = next(
            row for row in report["rows"][0]["observations"]
            if row.get("sourceFile") == active_source
        )
        self.assertEqual("exact_non_spatial_event_trigger", report["rows"][0]["status"])
        self.assertEqual(12, observation["listenerHeaderLocalId"])
        self.assertEqual(active_source, observation["sourceFile"])
        self.assertEqual(active_hash, observation["sourceSha256"])

    def test_story_trigger_zone_cross_script_same_key_is_multiple_not_fanned_out(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            overlay_files = {}
            for script_id in ("1001", "1002"):
                source = root / "LevelScriptData" / "map_fixture" / f"{script_id}.json"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(script_id.encode("ascii"))
                source_text = source.resolve().as_posix()
                sources.append(source_text)
                overlay_files[f"map_fixture/{script_id}.json"] = {
                    "logicalPath": f"map_fixture/{script_id}.json",
                    "sourceFile": source_text,
                    "sourceRoot": source.parent.parent.as_posix(),
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "status": "fallback",
                    "shadowed": [],
                }
            overlay = self._trigger_overlay(Path(sources[0]))
            overlay["files"] = overlay_files
            nodes = []
            for index, script_id in enumerate(("1001", "1002")):
                nodes.append({
                    "eventName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "selector": {
                        "levelId": "map_fixture",
                        "listenerScriptId": script_id,
                        "listenerHeaderLocalId": 7,
                    },
                    "storyFiles": [{
                        "key": "radio_shared_cross_script",
                        "nativeActions": ["PlayRadio"],
                        "sourceFiles": [sources[index]],
                    }],
                })
            index_payload = {
                "storyCoverage": {
                    "missionlessNativeRuntimeNodes": nodes,
                }
            }
            with mock.patch.object(
                frontier,
                "decode_levelscript_native_action_topology",
                return_value=self._exact_topology(
                    "ScriptEvent_OnLeaderEnterTriggerVolume",
                    {"triggerSlotIdFilter": 80001},
                ),
            ), mock.patch.object(
                frontier,
                "decode_levelscript_binary_summary",
                return_value={"scriptIdVerified": True},
            ), mock.patch.object(
                frontier,
                "classify_local_trigger_volume_context",
                side_effect=[
                    {
                        "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                        "triggerVolumes": [{
                            "slotId": 80001,
                            "triggerVolumeType": "Leader",
                            "shapeList": {"shapes": [{"shapeType": "Box"}]},
                        }],
                    },
                    {
                        "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                        "triggerVolumes": [{
                            "slotId": 80001,
                            "triggerVolumeType": "Leader",
                            "shapeList": {"shapes": [{"shapeType": "Sphere"}]},
                        }],
                    },
                ],
            ):
                report = frontier.build_story_trigger_zone_coverage(
                    index_payload,
                    overlay_index=overlay,
                )
        row = report["rows"][0]
        self.assertEqual("multiple_or_ambiguous_trigger_zones", row["status"])
        self.assertEqual(2, row["uniqueZoneCount"])
        self.assertEqual(2, row["observationCount"])

    def test_story_trigger_zone_current_corpus_aggregate_is_active_and_complete(self) -> None:
        pipeline_index = ROOT / "webui" / "data" / "mission_pipeline" / "index.json"
        if not pipeline_index.is_file():
            self.skipTest("generated Mission Pipeline index is unavailable")
        report = frontier.build_story_trigger_zone_coverage(
            json.loads(pipeline_index.read_text(encoding="utf-8"))
        )
        self.assertEqual("validated_active_overlay", report["overlay"]["status"])
        self.assertGreaterEqual(report["counts"]["storyFiles"], 152)
        self.assertGreater(report["counts"]["directPlaybackCandidateCount"], 0)
        self.assertGreaterEqual(report["counts"]["status"]["exact_local_trigger_volume"], 66)
        self.assertGreaterEqual(report["counts"]["status"]["multiple_or_ambiguous_trigger_zones"], 2)
        self.assertGreaterEqual(report["counts"]["status"]["exact_non_spatial_event_trigger"], 84)
        self.assertNotIn("active_overlay_unavailable", report["counts"]["status"])
        self.assertGreater(
            report["counts"]["status"].get("trigger_event_known_spatial_unresolved", 0),
            0,
        )
        remapped = [
            observation
            for row in report["rows"]
            for observation in row["observations"]
            if observation.get("activeHeaderRemapped")
        ]
        self.assertGreater(len(remapped), 0)


if __name__ == "__main__":
    unittest.main()
