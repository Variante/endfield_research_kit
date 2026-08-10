from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import build_dialog_finish_branch_audit as audit
except ModuleNotFoundError:
    from scripts.story_recovery import build_dialog_finish_branch_audit as audit


def text_asset(nodes: list[dict], connections: list[dict], name: str = "dlg_fixture") -> dict:
    payload = {
        "type": "Beyond.Gameplay.DialogTree",
        "nodes": nodes,
        "connections": connections,
    }
    return {
        "m_Name": name,
        "m_Script": base64.b64encode(
            json.dumps(payload).encode("utf-8")
        ).decode("ascii"),
    }


def option_node(option_ids: list[str]) -> dict:
    return {
        "$id": "option",
        "$type": "Beyond.Gameplay.DialogTreeOptionNode, Gameplay.Beyond",
        "_normalOptions": [
            {"_optionId": value, "index": ordinal}
            for ordinal, value in enumerate(option_ids)
        ],
        "_hasExOption": False,
    }


def finish_node(node_id: str, finish_id: int | None, *, serialized: bool = True) -> dict:
    node = {
        "$id": node_id,
        "$type": "Beyond.Gameplay.DialogTreeFinishNode, Gameplay.Beyond",
    }
    if serialized:
        node["finishId"] = finish_id
    return node


def connection(target: str, source: str = "option") -> dict:
    return {
        "$type": "Beyond.Gameplay.DialogTreeConnection",
        "_sourceNode": {"$ref": source},
        "_targetNode": {"$ref": target},
    }


def leveldata_mp_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(4, "little", signed=True) + encoded


def leveldata_brief_dictionary(
    script_id: int,
    property_names: list[str],
) -> bytes:
    properties = []
    for name in property_names:
        properties.append(
            b"\x02"
            + leveldata_mp_string(name)
            + b"\x02"
            + (3).to_bytes(4, "little", signed=True)
            + (1).to_bytes(4, "little", signed=True)
            + b"\x02"
            + (0).to_bytes(8, "little")
            + leveldata_mp_string("")
        )
    entry = (
        script_id.to_bytes(8, "little")
        + b"\x08"
        + (script_id + 100).to_bytes(8, "little")
        + (0).to_bytes(4, "little", signed=True)
        + (1).to_bytes(4, "little", signed=True)
        + (0).to_bytes(8, "little")
        + len(properties).to_bytes(4, "little", signed=True)
        + b"".join(properties)
        + (0).to_bytes(4, "little", signed=True)
        + (-1).to_bytes(4, "little", signed=True)
        + script_id.to_bytes(8, "little")
    )
    return b"\x2bfixture" + (1).to_bytes(4, "little", signed=True) + entry


class DialogTreeRouteTests(unittest.TestCase):
    def test_recovers_serialized_connection_index_finish_routes(self) -> None:
        outer = text_asset(
            [
                option_node(["option_fixture_1_001", "option_fixture_1_002"]),
                finish_node("finish1", 1),
                finish_node("finish2", 2),
            ],
            [connection("finish1"), connection("finish2")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(rejected, [])
        self.assertEqual(
            [(row["optionId"], row["finishId"]) for row in rows],
            [("option_fixture_1_001", 1), ("option_fixture_1_002", 2)],
        )

    def test_missing_finish_id_fails_closed_without_runtime_contract(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", None, serialized=False)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["gate"], "serializedFinishId")
        self.assertEqual(
            rejected[0]["actual"], "missing_without_validated_default"
        )

    def test_missing_finish_id_uses_validated_managed_int_default(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", None, serialized=False)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            runtime_defaults={
                "status": "validated",
                "managedValueTypeDefaults": {"System.Int32": 0},
            },
        )
        self.assertEqual(rejected, [])
        self.assertEqual(rows[0]["finishId"], 0)
        self.assertEqual(rows[0]["finishIdSource"], "runtime_default")

    def test_explicit_finish_id_wins_over_runtime_default(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", 7)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            runtime_defaults={
                "status": "validated",
                "managedValueTypeDefaults": {"System.Int32": 0},
            },
        )
        self.assertEqual(rejected, [])
        self.assertEqual(rows[0]["finishId"], 7)
        self.assertEqual(rows[0]["finishIdSource"], "serialized_explicit")

    def test_invalid_explicit_finish_id_is_not_replaced_by_default(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", True)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            runtime_defaults={
                "status": "validated",
                "managedValueTypeDefaults": {"System.Int32": 0},
            },
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["actual"], "invalid_serialized_value")

    def test_out_of_bounds_route_fails_closed_without_discarding_valid_route(self) -> None:
        outer = text_asset(
            [
                option_node(["option_fixture_1_001", "option_fixture_1_002"]),
                finish_node("finish", 1),
            ],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(
            [(row["optionId"], row["finishId"]) for row in rows],
            [("option_fixture_1_001", 1)],
        )
        self.assertEqual(rejected[0]["gate"], "normalOptionConnectionIndexBounds")
        self.assertEqual(rejected[0]["expected"]["maximumExclusive"], 1)
        self.assertEqual(rejected[0]["actual"], 1)

    def test_extra_option_edge_does_not_break_physical_index_mapping(self) -> None:
        option = option_node(["option_fixture_1_001", "option_fixture_1_002"])
        option["_normalOptions"][1]["index"] = 2
        option["_hasExOption"] = True
        extra = {
            "$id": "extra",
            "$type": "Beyond.Gameplay.DialogTreeExOptionNode, Gameplay.Beyond",
        }
        outer = text_asset(
            [option, finish_node("finish1", 1), extra, finish_node("finish2", 2)],
            [connection("finish1"), connection("extra"), connection("finish2")],
        )
        coverage: dict = {}
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            route_coverage=coverage,
        )
        self.assertEqual(rejected, [])
        self.assertEqual(
            [(row["optionId"], row["finishId"]) for row in rows],
            [("option_fixture_1_001", 1), ("option_fixture_1_002", 2)],
        )
        self.assertEqual(coverage["counts"]["extraOptionNodes"], 1)
        self.assertEqual(coverage["counts"]["connectionCountMismatchNodes"], 1)

    def test_non_object_option_row_fails_closed(self) -> None:
        node = option_node(["option_fixture_1_001"])
        node["_normalOptions"].append("invalid")
        outer = text_asset(
            [node, finish_node("finish", 1)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["gate"], "uniqueOptionIds")


class DialogTreeFinishEndpointTests(unittest.TestCase):
    def test_recovers_exact_prime_reachable_endpoint_with_source_binding(self) -> None:
        prime = {
            "$id": "prime",
            "$type": "Beyond.Gameplay.DialogTreeTrunkNode, Gameplay.Beyond",
        }
        outer = text_asset(
            [prime, finish_node("finish", 3)],
            [connection("finish", "prime")],
        )
        rows, rejected, coverage = audit.decode_dialog_tree_finish_endpoints(
            outer,
            source_file="fixture.json",
        )
        self.assertEqual(rejected, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["finishId"], 3)
        self.assertEqual(rows[0]["nodePath"], ["prime", "finish"])
        self.assertEqual(rows[0]["predecessorNodeTypes"], ["DialogTreeTrunkNode"])
        self.assertEqual(
            rows[0]["sourceFiles"][0]["relationship"],
            "exact_prime_reachable_finish_endpoint",
        )
        self.assertEqual(coverage["counts"]["validatedFinishEndpoints"], 1)

    def test_detached_finish_definition_is_not_published(self) -> None:
        prime = {
            "$id": "prime",
            "$type": "Beyond.Gameplay.DialogTreeTrunkNode, Gameplay.Beyond",
        }
        outer = text_asset([prime, finish_node("finish", 3)], [])
        rows, rejected, coverage = audit.decode_dialog_tree_finish_endpoints(
            outer,
            source_file="fixture.json",
        )
        self.assertEqual(rows, [])
        self.assertEqual(
            rejected[0]["failureClass"],
            "finish_node_not_reachable_from_prime",
        )
        self.assertEqual(coverage["counts"]["rejectedFinishEndpoints"], 1)


class TimelineRouteTests(unittest.TestCase):
    def test_duplicate_clips_agree_and_are_collapsed(self) -> None:
        option = {
            "id": "option_fixture_1_001",
            "changeFinishNum": 1,
            "targetFinishNum": 3,
            "assetTrack": "asset.json",
        }
        rows, rejected = audit.decode_timeline_finish_routes(
            {
                "dlg_fixture": {
                    "dialogKey": "dlg_fixture",
                    "timeline": "dlgtl_fixture",
                    "sourceRoots": ["root.json"],
                    "options": [option, dict(option)],
                }
            }
        )
        self.assertEqual(rejected, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["finishId"], 3)
        self.assertEqual(rows[0]["serializedOccurrenceCount"], 2)

    def test_conflicting_duplicate_clips_are_rejected(self) -> None:
        rows, rejected = audit.decode_timeline_finish_routes(
            {
                "dlg_fixture": {
                    "dialogKey": "dlg_fixture",
                    "options": [
                        {
                            "id": "option_fixture_1_001",
                            "changeFinishNum": 1,
                            "targetFinishNum": 1,
                        },
                        {
                            "id": "option_fixture_1_001",
                            "changeFinishNum": 1,
                            "targetFinishNum": 2,
                        },
                    ],
                }
            }
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["gate"], "timelineOptionScopeAgreement")
        self.assertEqual(rejected[0]["finishIds"], [1, 2])


class ProducerScopeTests(unittest.TestCase):
    def test_reused_option_id_in_distinct_nodes_is_not_a_conflict(self) -> None:
        rows = [
            {
                "dialogId": "dlg_fixture",
                "optionId": "option_shared",
                "finishId": finish_id,
                "finishIdSource": "serialized_explicit",
                "producerFamily": "dialog_tree_finish_node",
                "producerScope": {
                    "kind": "dialog_tree_option_node",
                    "key": f"node:{node_id}:option:0",
                },
                "sourceFiles": [],
            }
            for node_id, finish_id in (("6", 0), ("15", 3))
        ]
        accepted, conflicts = audit._normalize_producers(rows)
        self.assertEqual(len(accepted), 2)
        self.assertEqual(conflicts, [])
        reused = audit._collect_reused_option_scopes(accepted)
        self.assertEqual(len(reused), 1)
        self.assertEqual(reused[0]["finishIds"], [0, 3])

    def test_conflicting_finish_within_one_runtime_scope_fails_closed(self) -> None:
        rows = [
            {
                "dialogId": "dlg_fixture",
                "optionId": "option_shared",
                "finishId": finish_id,
                "finishIdSource": "serialized_explicit",
                "producerFamily": "dialog_tree_finish_node",
                "producerScope": {
                    "kind": "dialog_tree_option_node",
                    "key": "node:6:option:0",
                },
                "sourceFiles": [],
            }
            for finish_id in (0, 3)
        ]
        accepted, conflicts = audit._normalize_producers(rows)
        self.assertEqual(accepted, [])
        self.assertEqual(conflicts[0]["gate"], "producerScopeAgreement")


class PipelinePublicationTests(unittest.TestCase):
    def test_publishes_option_and_endpoint_dependencies_as_separate_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = {
                "missions": [{"id": "mission_fixture", "file": "mission.json"}],
                "counts": {},
            }
            payload = {
                "nodes": [
                    {
                        "id": "quest_fixture",
                        "objectives": [
                            {
                                "index": 0,
                                "conditionId": "condition_fixture",
                            }
                        ],
                    }
                ]
            }
            common = {
                "missionId": "mission_fixture",
                "questId": "quest_fixture",
                "objectiveIndex": 0,
                "conditionId": "condition_fixture",
            }
            report = {
                "schemaVersion": "dialogFinishMissionBranchAudit.v5",
                "status": "validated",
                "evidencePolicy": "fixture",
                "counts": {},
                "producerFamilyCounts": {},
                "nativeContract": {},
                "dependencies": [{**common, "dialogId": "dlg_option", "finishId": 1}],
                "endpointDependencies": [
                    {**common, "dialogId": "dlg_endpoint", "finishId": 0}
                ],
            }
            published = audit.publish_to_pipeline_index(
                index,
                report,
                {"mission_fixture": payload},
                root,
            )
            self.assertEqual(published, 2)
            objective = payload["nodes"][0]["objectives"][0]
            self.assertEqual(
                objective["dialogFinishBranchDependencies"][0]["dialogId"],
                "dlg_option",
            )
            self.assertEqual(
                objective["dialogFinishEndpointDependencies"][0]["dialogId"],
                "dlg_endpoint",
            )
            self.assertEqual(index["counts"]["dialogFinishBranchDependencies"], 1)
            self.assertEqual(index["counts"]["dialogFinishEndpointDependencies"], 1)
            self.assertEqual(index["counts"]["dialogFinishExactConsumerCoverage"], 2)

    def test_publishes_shared_task_consumer_and_exact_subgame_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = {
                "missions": [{"id": "mission_fixture", "file": "mission.json"}],
                "counts": {},
            }
            payload = {
                "mission": {
                    "nativeRuntimeBindings": [
                        {
                            "subGameId": "subgame_fixture",
                            "bindScriptId": "4242",
                        }
                    ]
                },
                "nodes": [
                    {
                        "id": "quest_fixture",
                        "objectives": [
                            {"index": 0, "conditionId": "mission_condition"}
                        ],
                    }
                ],
            }
            shared = {
                "missionId": "mission_fixture",
                "questId": "quest_fixture",
                "objectiveIndex": 0,
                "missionConditionId": "mission_condition",
                "dialogId": "dlg_fixture",
                "finishId": 2,
                "scriptId": "4242",
                "taskConditionId": "task_condition",
                "missionShellRelationship": "same_mission_shell",
                "missionShellOwner": {
                    "missionId": "mission_fixture",
                    "subGameId": "subgame_fixture",
                    "scriptId": "4242",
                    "taskId": "deadbeef",
                },
            }
            report = {
                "schemaVersion": "dialogFinishMissionBranchAudit.v6",
                "status": "validated",
                "evidencePolicy": "fixture",
                "counts": {},
                "producerFamilyCounts": {},
                "nativeContract": {},
                "dependencies": [],
                "endpointDependencies": [],
                "levelScriptTaskSharedConsumerDependencies": [shared],
            }

            published = audit.publish_to_pipeline_index(
                index,
                report,
                {"mission_fixture": payload},
                root,
            )

            self.assertEqual(1, published)
            objective = payload["nodes"][0]["objectives"][0]
            self.assertEqual(
                "task_condition",
                objective["dialogFinishLevelScriptTaskDependencies"][0][
                    "taskConditionId"
                ],
            )
            binding = payload["mission"]["nativeRuntimeBindings"][0]
            self.assertEqual(
                "dlg_fixture",
                binding["dialogFinishTaskDependencies"][0]["dialogId"],
            )
            self.assertEqual(
                1,
                index["counts"]["dialogFinishOwnedLevelScriptTaskDependencies"],
            )

    def test_publishes_context_tiers_without_claiming_task_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = {
                "missions": [{"id": "mission_fixture", "file": "mission.json"}],
                "counts": {},
            }
            payload = {
                "nodes": [{
                    "id": "quest_fixture",
                    "objectives": [{
                        "index": 0,
                        "conditionId": "mission_condition",
                    }],
                }],
            }
            context = {
                "missionId": "mission_fixture",
                "questId": "quest_fixture",
                "objectiveIndex": 0,
                "missionConditionId": "mission_condition",
                "dialogId": "dlg_fixture",
                "finishId": 2,
                "levelId": "level_fixture",
                "scriptId": "4242",
                "taskConditionId": "task_condition",
                "missionOwnershipStatus": "unresolved",
            }
            global_dependency = {
                "dialogId": "dlg_fixture",
                "finishId": 2,
                "levelId": "level_fixture",
                "scriptId": "4242",
                "taskConditionId": "task_condition",
                "missionOwnershipStatus": "unresolved",
            }
            report = {
                "schemaVersion": "dialogFinishMissionBranchAudit.v7",
                "status": "validated",
                "evidencePolicy": "fixture",
                "counts": {},
                "producerFamilyCounts": {},
                "nativeContract": {},
                "dependencies": [],
                "endpointDependencies": [],
                "levelScriptTaskSharedConsumerDependencies": [],
                "levelScriptTaskAuthoredFinishDependencies": [global_dependency],
                "levelScriptTaskAnyFinishMissionContexts": [context],
                "levelScriptTaskMissionScriptContexts": [
                    {**context, "missionOwnershipStatus": "script_context_only"}
                ],
                "levelScriptTaskWithoutExactMissionFinishMatch": [
                    global_dependency
                ],
            }

            published = audit.publish_to_pipeline_index(
                index,
                report,
                {"mission_fixture": payload},
                root,
            )

            self.assertEqual(2, published)
            objective = payload["nodes"][0]["objectives"][0]
            self.assertEqual(
                "unresolved",
                objective["dialogFinishLevelScriptTaskAnyFinishContexts"][0][
                    "missionOwnershipStatus"
                ],
            )
            self.assertEqual(
                "script_context_only",
                objective[
                    "dialogFinishLevelScriptTaskMissionScriptContexts"
                ][0]["missionOwnershipStatus"],
            )
            self.assertEqual(
                [global_dependency],
                index["dialogFinishBranchRecovery"][
                    "missionRuntimeUnmatchedLevelScriptTaskFinishDependencies"
                ],
            )

    def test_publishes_leveldata_task_shell_dependency_on_mission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = {
                "missions": [{"id": "mission_fixture", "file": "mission.json"}],
                "counts": {},
            }
            payload = {"mission": {}, "nodes": []}
            dependency = {
                "dialogId": "dlg_fixture",
                "finishId": 2,
                "levelId": "map_fixture",
                "scriptId": "4242",
                "taskId": "deadbeef",
                "taskConditionId": "condition",
                "missionShellOwner": {
                    "ownerKind": "leveldata_task_progress_mission_shell",
                    "missionId": "mission_fixture",
                    "sourceFile": "fixture/LevelData/carrier.json",
                },
            }
            report = {
                "schemaVersion": "dialogFinishMissionBranchAudit.v9",
                "status": "validated",
                "evidencePolicy": "fixture",
                "counts": {},
                "producerFamilyCounts": {},
                "nativeContract": {},
                "dependencies": [],
                "endpointDependencies": [],
                "levelScriptTaskSharedConsumerDependencies": [],
                "levelScriptTaskAuthoredFinishDependencies": [dependency],
            }

            published = audit.publish_to_pipeline_index(
                index,
                report,
                {"mission_fixture": payload},
                root,
            )

            self.assertEqual(1, published)
            self.assertEqual(
                [dependency],
                payload["dialogFinishAuthoredTaskShellDependencies"],
            )
            self.assertEqual(
                1,
                payload["dialogFinishBranchRecovery"][
                    "authoredTaskMissionShellDependencyCount"
                ],
            )
            self.assertEqual(
                1,
                index["counts"]["dialogFinishAuthoredTaskShellDependencies"],
            )
            self.assertEqual(
                1,
                index["counts"][
                    "dialogFinishLevelScriptTaskAuthoredFinishDependencies"
                ],
            )


class MissionContextCollectionTests(unittest.TestCase):
    def test_separates_exact_and_any_finish_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission_file = root / "mission.json"
            mission_file.write_text(
                json.dumps({
                    "nodes": [{
                        "id": "quest_fixture",
                        "objectives": [{
                            "index": 0,
                            "conditionId": "condition_fixture",
                            "dialogFinishes": [
                                {"dialogId": "dlg_fixture", "finishId": 2},
                                {"dialogId": "dlg_fixture", "finishId": -1},
                            ],
                        }],
                    }],
                }),
                encoding="utf-8",
            )
            exact, any_finish, _payloads = audit._collect_mission_consumers(
                {
                    "missions": [{
                        "id": "mission_fixture",
                        "file": "mission.json",
                    }]
                },
                root,
            )
        self.assertEqual([2], [row["finishId"] for row in exact])
        self.assertEqual([-1], [row["finishId"] for row in any_finish])

    def test_levelscript_context_requires_hash_bound_active_overlay(self) -> None:
        payloads = {
            "mission_fixture": {
                "mission": {"source": "MissionRuntimeDataTable.json"},
                "nodes": [{
                    "id": "quest_fixture",
                    "objectives": [{
                        "index": 0,
                        "conditionId": "condition_fixture",
                        "levelScriptSources": [{
                            "conditionType": "CheckLevelScriptStage",
                            "levelId": "level_fixture",
                            "scriptId": "4242",
                            "levelScriptOverlay": {
                                "activeSourceFile": "Persistent/4242.json",
                                "activeSha256": "a" * 64,
                            },
                        }],
                    }],
                }],
            }
        }
        rows = audit._collect_mission_levelscript_contexts(payloads)
        self.assertEqual(1, len(rows))
        self.assertEqual("4242", rows[0]["scriptId"])
        self.assertEqual("a" * 64, rows[0]["activeLevelScriptSha256"])

        del payloads["mission_fixture"]["nodes"][0]["objectives"][0][
            "levelScriptSources"
        ][0]["levelScriptOverlay"]
        with self.assertRaisesRegex(
            audit.AuditValidationError,
            "gate=activeLevelScriptOverlay",
        ):
            audit._collect_mission_levelscript_contexts(payloads)


class LevelScriptTaskConsumerTests(unittest.TestCase):
    @staticmethod
    def _condition_row(finish_id: int = 2) -> dict:
        constant = lambda value: {
            "value": value,
            "idRef": -1,
            "paramSource": 0,
            "path": None,
        }
        return {
            "conditionKey": "cafefeed",
            "condition": {
                "type": "CheckTalkOptionFinish",
                "conditionOffset": 42,
                "conditionOffsetHex": "0x2a",
                "conditionUnionTag": "0x009f",
                "nativeMappingId": "fixture",
                "dialogId": constant("dlg_fixture"),
                "finishId": constant(finish_id),
            },
        }

    def test_overlay_is_data_driven_and_persistent_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            streaming = root / "StreamingAssets" / "LevelScriptData"
            persistent = root / "Persistent" / "LevelScriptData"
            for source, body in ((streaming, b"streaming"), (persistent, b"persistent")):
                target = source / "level_fixture" / "4242.json"
                target.parent.mkdir(parents=True)
                target.write_bytes(body)
            decoded = [{
                "tasks": [{
                    "taskKey": "deadbeef",
                    "taskType": 0,
                    "canBeTracked": False,
                    "needManualCheck": False,
                    "conditions": [self._condition_row()],
                }]
            }]
            with (
                patch.object(
                    audit,
                    "decode_levelscript_task_conditions",
                    side_effect=lambda data, _script: decoded if data == b"persistent" else [],
                ),
                patch.object(
                    audit,
                    "scan_levelscript_task_condition_fragments",
                    return_value=[],
                ),
            ):
                rows, census = audit._collect_levelscript_task_finish_consumers(
                    (streaming, persistent)
                )
            self.assertEqual(1, len(rows))
            self.assertIn("Persistent", rows[0]["sourceFile"])
            self.assertEqual("deadbeef", rows[0]["taskId"])
            self.assertEqual(
                {
                    "taskType": 0,
                    "canBeTracked": False,
                    "needManualCheck": False,
                    "conditionCount": 1,
                    "mainObjectiveConditionCount": 0,
                    "objectiveEnums": [],
                    "conditionTypeCounts": {"CheckTalkOptionFinish": 1},
                },
                rows[0]["taskDefinition"],
            )
            self.assertEqual(1, census["resolvedTaskCount"])
            self.assertEqual({"0": 1}, census["resolvedTaskTypeCounts"])
            self.assertEqual(1, census["shadowedPathCount"])
            self.assertEqual(1, census["changedOverrideCount"])

    def test_indirect_finish_param_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            streaming = Path(tmp) / "StreamingAssets" / "LevelScriptData"
            persistent = Path(tmp) / "Persistent" / "LevelScriptData"
            target = streaming / "level_fixture" / "4242.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"fixture")
            persistent.mkdir(parents=True)
            row = self._condition_row()
            row["condition"]["finishId"]["paramSource"] = 1000
            decoded = [{"tasks": [{"taskKey": "deadbeef", "conditions": [row]}]}]
            with (
                patch.object(audit, "decode_levelscript_task_conditions", return_value=decoded),
                patch.object(audit, "scan_levelscript_task_condition_fragments", return_value=[]),
            ):
                rows, census = audit._collect_levelscript_task_finish_consumers(
                    (streaming, persistent)
                )
            self.assertEqual([], rows)
            self.assertEqual(1, census["rejectedIndirectOrMalformedParamCount"])

    def test_subgame_owner_requires_unique_exact_script_task_carrier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / "SubGameInstanceDataTable.json"
            rows = {}
            for suffix in ("a", "b"):
                subgame_id = f"subgame_{suffix}"
                rows[subgame_id] = {
                    "id": subgame_id,
                    "$type": "Fixture.DungeonSubGameData, Fixture",
                    "dungeonMissionId": f"mission_{suffix}",
                    "bindScriptId": 4242,
                    "mainTasks": [{"taskId": "deadbeef"}],
                    "extraTasks": [],
                    "failTasks": [],
                }
            table.write_text(json.dumps({"dataTable": rows}), encoding="utf-8")

            owners, census = audit._load_subgame_task_owners(table)

            self.assertNotIn(("4242", "deadbeef"), owners)
            self.assertEqual(1, len(census["ambiguousTaskOwners"]))

    def test_task_carrier_census_discovers_minimal_typed_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            streaming = root / "StreamingAssets" / "GameplayConfig"
            persistent = root / "Persistent" / "GameplayConfig"
            mission_streaming = root / "StreamingAssets" / "MissionRuntimeAsset"
            mission_persistent = root / "Persistent" / "MissionRuntimeAsset"
            for directory in (
                streaming,
                persistent,
                mission_streaming,
                mission_persistent,
            ):
                directory.mkdir(parents=True)
            payload = {
                "dataTable": {
                    "fixture": {
                        "$type": "Fixture.DungeonSubGameData, Fixture",
                        "dungeonMissionId": "mission_fixture",
                        "bindScriptId": 4242,
                        "mainTasks": [{"taskId": "deadbeef"}],
                    },
                    "unrelated_script": {"bindScriptId": 9999},
                    "unrelated_task": {"taskId": "deadbeef"},
                }
            }
            for directory in (streaming, persistent):
                (directory / "FixtureTable.json").write_text(
                    json.dumps(payload), encoding="utf-8"
                )
            consumers = [{"scriptId": "4242", "taskId": "deadbeef"}]

            census = audit._scan_exact_task_identity_carriers(
                consumers,
                (
                    streaming,
                    mission_streaming,
                    persistent,
                    mission_persistent,
                ),
            )

            self.assertEqual(1, census["carrierCount"])
            self.assertEqual(1, census["missionCarrierCount"])
            self.assertEqual(1, census["shadowedFileCount"])
            self.assertEqual(
                ["GameplayConfig"],
                census["scope"],
            )
            carrier = census["carriers"][0]
            self.assertEqual("$/dataTable/fixture", carrier["jsonPath"])
            self.assertEqual(["mission_fixture"], carrier["missionIds"])
            self.assertIn("Persistent", carrier["sourceFile"])

    def test_task_carrier_census_excludes_non_json_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "GameplayConfig"
            root.mkdir(parents=True)
            (root / "broken.json").write_bytes(b"deadbeef\x00\xff")

            census = audit._scan_exact_task_identity_carriers(
                [{"scriptId": "4242", "taskId": "deadbeef"}],
                (root,),
            )

            self.assertEqual(0, census["carrierCount"])
            self.assertEqual(0, census["rejectedCandidateFileCount"])
            self.assertEqual(0, census["typedJsonFileCount"])
            self.assertEqual(1, census["nonJsonFileCount"])

    def test_task_carrier_census_scans_all_typed_json_families(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            roots = []
            payload = {
                "rows": [{
                    "$type": "Fixture.Owner, Fixture",
                    "missionId": "mission_fixture",
                    "scriptId": 4242,
                    "taskId": "deadbeef",
                }],
            }
            for layer in ("StreamingAssets", "Persistent"):
                json_root = root / layer / "Data" / "Json"
                roots.append(json_root)
                carrier_root = json_root / "GameplayConfig"
                carrier_root.mkdir(parents=True)
                (carrier_root / "carrier.json").write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )
            level_data = roots[1] / "LevelData"
            level_data.mkdir()
            (level_data / "serialized.json").write_bytes(
                b"deadbeef\x00\xff"
            )
            definition_root = roots[1] / "LevelScriptData"
            definition_root.mkdir()
            (definition_root / "definition.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            census = audit._scan_exact_task_identity_carriers(
                [{"scriptId": "4242", "taskId": "deadbeef"}],
                roots,
            )

            self.assertEqual("exactTaskIdentityCarrierCensus.v2", census["schema"])
            self.assertEqual(["GameplayConfig", "LevelData"], census["scope"])
            self.assertEqual(3, census["physicalFileCount"])
            self.assertEqual(2, census["activeLogicalFileCount"])
            self.assertEqual(1, census["shadowedFileCount"])
            self.assertEqual(1, census["carrierCount"])
            self.assertEqual(1, census["typedJsonFileCount"])
            self.assertEqual(1, census["nonJsonFileCount"])
            self.assertEqual(
                "GameplayConfig/carrier.json",
                census["carriers"][0]["relativePath"],
            )

    def test_leveldata_progress_carrier_requires_exact_paired_properties(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            streaming = root / "Streaming" / "LevelData"
            persistent = root / "Persistent" / "LevelData"
            levelscript = root / "LevelScriptData"
            for directory in (streaming, persistent, levelscript):
                (directory / "map_fixture").mkdir(parents=True)
            (levelscript / "map_fixture" / "4242.json").write_bytes(b"script")
            progress = "lt:p:deadbeef:condition"
            max_progress = "lt:mp:deadbeef:condition"
            (streaming / "map_fixture" / "carrier.json").write_bytes(
                leveldata_brief_dictionary(4242, [progress])
            )
            (persistent / "map_fixture" / "carrier.json").write_bytes(
                leveldata_brief_dictionary(4242, [progress, max_progress])
            )
            shell_index = {
                ("map_fixture", "4242"): {
                    "hosts": [{
                        "levelDataFile": (
                            "fixture/LevelData/map_fixture/carrier.json"
                        ),
                        "dictionaryScriptIds": ["4242"],
                        "targetBriefData": {"dataPathHash": "4342"},
                        "hostMissionIds": ["mission_fixture"],
                        "authoritativeReferences": [{
                            "missionId": "mission_fixture",
                            "scopeKind": "typed_fixture_reference",
                        }],
                    }],
                },
            }
            census = audit._scan_leveldata_task_progress_carriers(
                [{
                    "levelId": "map_fixture",
                    "scriptId": "4242",
                    "taskId": "deadbeef",
                    "conditionId": "condition",
                }],
                (streaming, persistent),
                (levelscript,),
                (),
                authoritative_shell_index=shell_index,
            )

            self.assertEqual("levelDataTaskProgressCarrierCensus.v1", census["schema"])
            self.assertEqual(1, census["shadowedFileCount"])
            self.assertEqual(1, census["rawCandidateFileCount"])
            self.assertEqual(1, census["carrierCount"])
            self.assertEqual(1, census["uniqueMissionShellTaskIdentityCount"])
            self.assertEqual(0, census["rejectedShellClassificationCount"])
            carrier = census["carriers"][0]
            self.assertIn("Persistent", carrier["sourceFile"])
            self.assertEqual(["mission_fixture"], carrier["missionIds"])
            self.assertEqual(
                [progress, max_progress],
                carrier["progressProperties"],
            )

    def test_leveldata_progress_carrier_rejects_unpaired_raw_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leveldata = root / "LevelData"
            levelscript = root / "LevelScriptData"
            for directory in (leveldata, levelscript):
                (directory / "map_fixture").mkdir(parents=True)
            (levelscript / "map_fixture" / "4242.json").write_bytes(b"script")
            (leveldata / "map_fixture" / "carrier.json").write_bytes(
                leveldata_brief_dictionary(
                    4242,
                    ["lt:p:deadbeef:condition"],
                )
            )

            census = audit._scan_leveldata_task_progress_carriers(
                [{
                    "levelId": "map_fixture",
                    "scriptId": "4242",
                    "taskId": "deadbeef",
                    "conditionId": "condition",
                }],
                (leveldata,),
                (levelscript,),
                (),
                authoritative_shell_index={},
            )

            self.assertEqual(1, census["rawCandidateFileCount"])
            self.assertEqual(1, census["validatedDictionaryCandidateFileCount"])
            self.assertEqual(0, census["carrierCount"])
            self.assertEqual(1, census["un_carriedTaskConditionIdentityCount"])

    def test_leveldata_progress_carrier_rejects_stale_overlay_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leveldata = root / "LevelData"
            levelscript = root / "LevelScriptData"
            for directory in (leveldata, levelscript):
                (directory / "map_fixture").mkdir(parents=True)
            (levelscript / "map_fixture" / "4242.json").write_bytes(b"script")
            progress = "lt:p:deadbeef:condition"
            max_progress = "lt:mp:deadbeef:condition"
            (leveldata / "map_fixture" / "carrier.json").write_bytes(
                leveldata_brief_dictionary(4242, [progress, max_progress])
            )
            stale_shell_index = {
                ("map_fixture", "4242"): {
                    "hosts": [{
                        "levelDataFile": (
                            "fixture/LevelData/map_fixture/carrier.json"
                        ),
                        "dictionaryScriptIds": ["4242", "9999"],
                        "targetBriefData": {"dataPathHash": "stale"},
                        "hostMissionIds": ["mission_fixture"],
                        "authoritativeReferences": [{
                            "missionId": "mission_fixture",
                            "scopeKind": "typed_fixture_reference",
                        }],
                    }],
                },
            }

            census = audit._scan_leveldata_task_progress_carriers(
                [{
                    "levelId": "map_fixture",
                    "scriptId": "4242",
                    "taskId": "deadbeef",
                    "conditionId": "condition",
                }],
                (leveldata,),
                (levelscript,),
                (),
                authoritative_shell_index=stale_shell_index,
            )

            self.assertEqual(1, census["carrierCount"])
            self.assertEqual([], census["carriers"][0]["missionIds"])
            self.assertEqual(1, census["rejectedShellClassificationCount"])
            diagnostic = census["rejectedShellClassifications"][0]
            self.assertEqual("activeOverlayAgreement", diagnostic["gate"])
            self.assertEqual(
                ["4242"],
                diagnostic["expected"]["dictionaryScriptIds"],
            )
            self.assertEqual(
                ["4242", "9999"],
                diagnostic["actual"]["dictionaryScriptIds"],
            )

    def test_leveldata_progress_census_forwards_all_typed_script_references(self) -> None:
        references = {
            ("map_fixture", "4242"): [{
                "missionId": "mission_fixture",
                "questId": "quest_fixture",
                "conditionType": "CheckScriptMonsterKilled",
                "scopeKind": "exact_mission_runtime_levelscript_condition",
                "sourceFile": "MissionRuntimeAsset/mission_fixture.json",
            }],
        }
        with patch.object(
            audit,
            "build_leveldata_authoritative_scope_script_host_index",
            return_value={},
        ) as build_shell_index:
            audit._scan_leveldata_task_progress_carriers(
                [{
                    "levelId": "map_fixture",
                    "scriptId": "4242",
                    "taskId": "deadbeef",
                    "conditionId": "condition",
                }],
                (),
                (),
                (),
                script_scope_references=references,
            )

        self.assertEqual(references, build_shell_index.call_args.args[2])


class NativeContractTests(unittest.TestCase):
    class FakePe:
        def __init__(self, _path: Path, body: bytes) -> None:
            self.body = body

        def bytes_at_va(self, _va: int, size: int) -> bytes:
            return self.body[:size]

    def test_native_validator_accepts_hash_locked_sources_and_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            game.write_bytes(b"game")
            metadata.write_bytes(b"metadata")
            body = b"native-body"
            methods = {
                "Fixture.Method": {
                    "token": "0x1",
                    "va": 0x1000,
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "contract": "fixture",
                }
            }
            mapper = type(
                "Mapper",
                (),
                {
                    "PeImage": lambda _path: self.FakePe(_path, body),
                    "load_catalog_module": lambda: type(
                        "Catalog", (), {"Metadata": lambda _path: type("Metadata", (), {"types": []})()}
                    ),
                    "metadata_registration_summary": lambda _pe, _address: {
                        "fieldOffsets": "0x1"
                    },
                },
            )
            with (
                patch.object(audit, "EXPECTED_GAME_ASSEMBLY_SHA256", hashlib.sha256(b"game").hexdigest()),
                patch.object(audit, "EXPECTED_METADATA_SHA256", hashlib.sha256(b"metadata").hexdigest()),
                patch.object(audit, "NATIVE_METHODS", methods),
                patch.object(audit, "EXPECTED_RUNTIME_FIELD_OFFSETS", {}),
                patch.object(audit, "_load_mapper", return_value=mapper),
            ):
                result = audit.validate_native_contract(game, metadata)
            self.assertEqual(result["status"], "validated")
            self.assertEqual(result["methods"][0]["symbol"], "Fixture.Method")

    def test_native_validator_reports_bounded_hash_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            game.write_bytes(b"drifted")
            metadata.write_bytes(b"metadata")
            with self.assertRaisesRegex(
                audit.AuditValidationError,
                r"validator=dialog_finish_native_contract gate=sourceSha256 .*expected=.* actual=.*",
            ):
                audit.validate_native_contract(game, metadata)


if __name__ == "__main__":
    unittest.main()
