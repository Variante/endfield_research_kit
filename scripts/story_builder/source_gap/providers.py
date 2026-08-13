"""Shared source-gap evidence providers and exact validation primitives."""
from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
from .foundation import (
    read_json,
    resolve_installed_native_inputs,
    safe_key,
    sha256_file,
)
from ..mission_recovery import natural_key
from ..mission_assets import (
    mission_runtime_source_summary,
    select_complete_mission_runtime_root,
)


from .data import (
    NON_OWNING_DIAGNOSTIC_QUEST_ATTACH_SOURCES,
    NPC_PROXY_TRACKING_INFO_TYPE,
    NPC_PROXY_TRACKING_INFO_FIELDS,
)


def _generic_registered_dialog_tree_definition_facts(
    story_key: str,
    dialog_id_row: Any,
    definition: Any,
    *,
    require_control_flow: bool = True,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate one registered DialogTree without assuming an activator.

    Registration proves that the current client can resolve the root and the
    TextAsset proves its internal graph. Neither fact identifies which mission
    action starts the dialog, so consumer exhaustion is checked separately.
    """
    if (
        not isinstance(dialog_id_row, dict)
        or dialog_id_row.get("registered") is not True
        or dialog_id_row.get("memoryPackRecordKey") is not True
        or dialog_id_row.get("hasRootKey") is not True
    ):
        return None, {
            "validator": "genericRegisteredDialogTreeNegativeConsumer",
            "gate": "exactCurrentDialogIdRegistration",
            "storyKey": story_key,
            "expected": {
                "registered": True,
                "memoryPackRecordKey": True,
                "hasRootKey": True,
            },
            "actual": dialog_id_row,
        }
    required_definition = {
        "sceneKey": story_key,
        "assetName": story_key,
        "assetType": "Beyond.Gameplay.DialogTree",
        "evidenceKind": "exact_dialog_tree_definition",
        "sourceType": "AnimeStudio TextAsset/DialogTree",
    }
    actual_definition = {
        key: definition.get(key)
        for key in required_definition
    } if isinstance(definition, dict) else {
        "type": type(definition).__name__,
    }
    source_file = (
        safe_key(definition.get("sourceFile"))
        if isinstance(definition, dict) else ""
    )
    source_path = ROOT / source_file if source_file else None
    source_sha256 = (
        safe_key(definition.get("sourceSha256")).upper()
        if isinstance(definition, dict) else ""
    )
    source_valid = (
        isinstance(source_path, Path)
        and source_path.is_file()
        and source_path.parent.name == "TextAsset"
        and source_path.name.startswith(f"{story_key}_p")
        and _sha256_file(source_path).upper() == source_sha256
    )
    count_fields = (
        "nodeCount",
        "connectionCount",
        "optionGroupCount",
        "branchingOptionGroupCount",
    )
    option_route_recovery = (
        definition.get("optionRouteRecovery")
        if isinstance(definition, dict) else None
    )
    option_route_nodes = (
        option_route_recovery.get("nodes")
        if isinstance(option_route_recovery, dict) else None
    )
    option_routes = [
        route
        for node in option_route_nodes or []
        if isinstance(node, dict)
        for route in node.get("routes") or []
        if isinstance(route, dict)
    ]
    option_routes_valid = (
        isinstance(option_route_recovery, dict)
        and option_route_recovery.get("schemaVersion")
        == "dialogTreeNormalOptionRoutes.v1"
        and isinstance(option_route_recovery.get("issues"), list)
        and isinstance(option_route_recovery.get("counts"), dict)
        and isinstance(option_route_nodes, list)
        and all(
            isinstance(node, dict)
            and isinstance(node.get("routes"), list)
            and node.get("normalOptionCount") == len(node["routes"])
            and node.get("issues") == []
            for node in option_route_nodes
        )
        and all(
            route.get("status") == "validated"
            and safe_key(route.get("optionId"))
            in set(definition.get("optionIds") or [])
            and isinstance(route.get("connectionIndex"), int)
            and not isinstance(route.get("connectionIndex"), bool)
            and route["connectionIndex"] >= 0
            and safe_key(route.get("targetNodeId"))
            and safe_key(route.get("targetNodeType"))
            for route in option_routes
        )
        and option_route_recovery["counts"].get(
            "validatedNormalOptionRoutes", 0
        ) == len(option_routes)
    )
    finish_endpoint_recovery = (
        definition.get("finishEndpointRecovery")
        if isinstance(definition, dict) else None
    )
    finish_endpoints = (
        finish_endpoint_recovery.get("endpoints")
        if isinstance(finish_endpoint_recovery, dict) else None
    )
    finish_endpoints_valid = (
        isinstance(finish_endpoint_recovery, dict)
        and finish_endpoint_recovery.get("schemaVersion")
        == "dialogTreeFinishEndpoints.v1"
        and isinstance(finish_endpoint_recovery.get("issues"), list)
        and isinstance(finish_endpoint_recovery.get("counts"), dict)
        and isinstance(finish_endpoints, list)
        and all(
            isinstance(endpoint, dict)
            and endpoint.get("status") == "validated"
            and endpoint.get("reachableFromPrimeNode") is True
            and isinstance(endpoint.get("finishId"), int)
            and not isinstance(endpoint.get("finishId"), bool)
            and safe_key(endpoint.get("nodeId"))
            and isinstance(endpoint.get("nodePath"), list)
            and isinstance(endpoint.get("connectionPath"), list)
            for endpoint in finish_endpoints
        )
        and finish_endpoint_recovery["counts"].get(
            "validatedFinishEndpoints"
        ) == len(finish_endpoints)
    )
    control_flow_payload_valid = (
        isinstance(option_route_recovery, dict)
        and option_route_recovery.get("schemaVersion")
        == "dialogTreeNormalOptionRoutes.v1"
        and isinstance(option_route_recovery.get("issues"), list)
        and isinstance(finish_endpoint_recovery, dict)
        and finish_endpoint_recovery.get("schemaVersion")
        == "dialogTreeFinishEndpoints.v1"
        and isinstance(finish_endpoint_recovery.get("issues"), list)
    )
    structure_valid = (
        isinstance(definition, dict)
        and all(definition.get(key) == value for key, value in required_definition.items())
        and all(
            isinstance(definition.get(key), int) and definition[key] >= 0
            for key in count_fields
        )
        and definition["nodeCount"] > 0
        and isinstance(definition.get("nodeTypeCounts"), dict)
        and sum(definition["nodeTypeCounts"].values()) == definition["nodeCount"]
        and isinstance(definition.get("lineIds"), list)
        and isinstance(definition.get("lineConnections"), list)
        and isinstance(definition.get("entryLineIds"), list)
        and isinstance(definition.get("terminalLineIds"), list)
        and isinstance(definition.get("nonLineConnectionCount"), int)
        and definition["nonLineConnectionCount"] >= 0
        and (
            len(definition["lineConnections"])
            + definition["nonLineConnectionCount"]
            == definition["connectionCount"]
        )
        and isinstance(definition.get("optionIds"), list)
        and (
            control_flow_payload_valid
            and (
                not require_control_flow
                or (option_routes_valid and finish_endpoints_valid)
            )
        )
        and bool(safe_key(definition.get("sourcePathId")))
        and source_valid
    )
    if not structure_valid:
        return None, {
            "validator": "genericRegisteredDialogTreeNegativeConsumer",
            "gate": "exactCurrentDialogTreeDefinition",
            "storyKey": story_key,
            "expected": {
                **required_definition,
                "positiveNodeCount": True,
                "nonnegativeStructureCounts": list(count_fields),
                "validatedOptionRouteRecovery": require_control_flow,
                "validatedFinishEndpointRecovery": require_control_flow,
                "exactSourceHash": True,
            },
            "actual": {
                **actual_definition,
                "sourceFile": source_file,
                "sourceSha256": source_sha256,
                "sourceHashMatches": source_valid,
                "optionRouteRecovery": option_route_recovery,
                "finishEndpointRecovery": finish_endpoint_recovery,
                **({
                    key: definition.get(key)
                    for key in (*count_fields, "nodeTypeCounts")
                } if isinstance(definition, dict) else {}),
            },
        }
    return {
        **{
            key: definition[key]
            for key in (
            "sceneKey",
            "assetName",
            "assetType",
            "lineIds",
            "lineConnections",
            "entryLineIds",
            "terminalLineIds",
            "nonLineConnectionCount",
            "optionIds",
            "nodeCount",
            "nodeTypeCounts",
            "connectionCount",
            "optionGroupCount",
            "branchingOptionGroupCount",
            "optionRouteRecovery",
            "finishEndpointRecovery",
            "sourceFile",
            "sourcePathId",
            "sourceSha256",
            "sourceType",
            )
        },
        "optionRouteRecoveryStatus": (
            "partial_validated_routes_with_fail_closed_issues"
            if option_route_recovery["issues"] else "exact_validated_routes"
        ),
        "finishEndpointRecoveryStatus": (
            "partial_validated_endpoints_with_fail_closed_issues"
            if finish_endpoint_recovery["issues"]
            else "exact_validated_endpoints"
        ),
        "controlFlowValidationRequired": require_control_flow,
        "controlFlowValidationStatus": (
            "exact_validated"
            if option_routes_valid and finish_endpoints_valid
            else "partial_not_required_for_non_owning_context"
        ),
    }, None

def _repo_source_path(path: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(ROOT):
        return resolved.relative_to(ROOT).as_posix()
    return resolved.as_posix()

def _build_mission_npc_proxy_tracking_index(
    streaming_root: Path,
    persistent_root: Path,
) -> dict[str, Any]:
    """Index typed NPC tracking rows from one complete active mission corpus."""
    selected_root = select_complete_mission_runtime_root(
        streaming_root,
        persistent_root,
    )
    source_summary = mission_runtime_source_summary(
        streaming_root,
        persistent_root,
    )
    rows_by_proxy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scan_failures: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    source_files = sorted(
        (
            path for path in selected_root.glob("*.json")
            if not path.stem.endswith("_meta")
        ),
        key=lambda path: natural_key(path.name),
    )
    if not source_files:
        scan_failures.append({
            "validator": "missionNpcProxyTrackingCorpus",
            "gate": "nonEmptySelectedMissionRuntimeCorpus",
            "sourcePath": _repo_source_path(selected_root),
            "expected": {"jsonFileCount": "> 0"},
            "actual": {"jsonFileCount": 0},
        })
    for source_path in source_files:
        source_file = _repo_source_path(source_path)
        source_sha256 = _sha256_file(source_path)
        source_hashes[source_file] = source_sha256
        payload = read_json(source_path, None)
        mission_id = safe_key(payload.get("missionId")) if isinstance(payload, dict) else ""
        quest_dic = payload.get("questDic") if isinstance(payload, dict) else None
        if (
            not isinstance(payload, dict)
            or mission_id != source_path.stem
            or not isinstance(quest_dic, dict)
        ):
            scan_failures.append({
                "validator": "missionNpcProxyTrackingCorpus",
                "gate": "exactMissionRuntimeFileIdentity",
                "mission": source_path.stem,
                "sourcePath": source_file,
                "sourceSha256": source_sha256,
                "expected": {
                    "missionId": source_path.stem,
                    "questDicType": "dict",
                },
                "actual": {
                    "payloadType": type(payload).__name__,
                    "missionId": mission_id,
                    "questDicType": type(quest_dic).__name__,
                },
            })
            continue
        for quest_id, quest in sorted(quest_dic.items(), key=lambda item: natural_key(item[0])):
            objectives = quest.get("objectiveList") if isinstance(quest, dict) else None
            if not isinstance(objectives, list):
                scan_failures.append({
                    "validator": "missionNpcProxyTrackingCorpus",
                    "gate": "missionQuestObjectiveListShape",
                    "mission": mission_id,
                    "questId": safe_key(quest_id),
                    "sourcePath": source_file,
                    "sourceSha256": source_sha256,
                    "expected": {"objectiveListType": "list"},
                    "actual": {"objectiveListType": type(objectives).__name__},
                })
                continue
            for objective_index, objective in enumerate(objectives):
                tracking_rows = (
                    objective.get("trackingInfoList")
                    if isinstance(objective, dict) else None
                )
                if tracking_rows is None:
                    continue
                if not isinstance(tracking_rows, list):
                    scan_failures.append({
                        "validator": "missionNpcProxyTrackingCorpus",
                        "gate": "missionObjectiveTrackingListShape",
                        "mission": mission_id,
                        "questId": safe_key(quest_id),
                        "objectiveIndex": objective_index,
                        "sourcePath": source_file,
                        "sourceSha256": source_sha256,
                        "expected": {"trackingInfoListType": "list"},
                        "actual": {
                            "trackingInfoListType": type(tracking_rows).__name__,
                        },
                    })
                    continue
                for tracking_index, tracking in enumerate(tracking_rows):
                    if (
                        not isinstance(tracking, dict)
                        or safe_key(tracking.get("$type"))
                        != NPC_PROXY_TRACKING_INFO_TYPE
                    ):
                        continue
                    proxy_id = safe_key(tracking.get("npcProxyId"))
                    row = {
                        "missionId": mission_id,
                        "questId": safe_key(quest_id),
                        "objectiveIndex": objective_index,
                        "trackingIndex": tracking_index,
                        "npcProxyId": proxy_id,
                        "sceneId": safe_key(tracking.get("sceneId")),
                        "tracking": tracking,
                        "sourceFile": source_file,
                        "sourceSha256": source_sha256,
                        "qualified": (
                            set(tracking) == NPC_PROXY_TRACKING_INFO_FIELDS
                            and tracking.get("useFilterCondition") is False
                            and isinstance(
                                tracking.get("guidingArea"), (int, float)
                            )
                            and not isinstance(
                                tracking.get("guidingArea"), bool
                            )
                            and bool(proxy_id)
                            and bool(safe_key(tracking.get("sceneId")))
                        ),
                    }
                    if proxy_id:
                        rows_by_proxy[proxy_id].append(row)
                    else:
                        scan_failures.append({
                            "validator": "missionNpcProxyTrackingCorpus",
                            "gate": "typedTrackingRowHasProxyIdentity",
                            "mission": mission_id,
                            "questId": safe_key(quest_id),
                            "objectiveIndex": objective_index,
                            "trackingIndex": tracking_index,
                            "sourcePath": source_file,
                            "sourceSha256": source_sha256,
                            "expected": {"nonEmptyNpcProxyId": True},
                            "actual": tracking,
                        })
    for rows in rows_by_proxy.values():
        rows.sort(key=lambda row: (
            natural_key(row["missionId"]),
            natural_key(row["questId"]),
            row["objectiveIndex"],
            row["trackingIndex"],
        ))
    source_set_digest = hashlib.sha256()
    for source_file, source_sha256 in source_hashes.items():
        source_set_digest.update(source_file.encode("utf-8"))
        source_set_digest.update(b"\0")
        source_set_digest.update(source_sha256.encode("ascii"))
        source_set_digest.update(b"\n")
    return {
        **source_summary,
        "selectedRoot": _repo_source_path(selected_root),
        "status": "inactive_source_validation_failed" if scan_failures else "active",
        "sourceFiles": list(source_hashes),
        "sourceSha256": source_hashes,
        "sourceSetSha256": source_set_digest.hexdigest().upper(),
        "scannedMissionFileCount": len(source_files),
        "rowsByProxy": dict(rows_by_proxy),
        "typedRowCount": sum(len(rows) for rows in rows_by_proxy.values()),
        "qualifiedRowCount": sum(
            row["qualified"] for rows in rows_by_proxy.values() for row in rows
        ),
        "proxyCount": len(rows_by_proxy),
        "scanFailureCount": len(scan_failures),
        "scanFailures": scan_failures[:100],
    }

def _generic_mission_npc_proxy_tracking_contexts(
    story_key: str,
    nominal_mission_id: str,
    npc_proxy_facts: Any,
    tracking_corpus: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Join exact dialog consumers to unfiltered typed mission tracking rows."""
    if (
        not isinstance(npc_proxy_facts, dict)
        or not isinstance(tracking_corpus, dict)
        or tracking_corpus.get("status") != "active"
    ):
        return [], []
    consumers = [
        row for row in (npc_proxy_facts.get("npcProxyConsumers") or [])
        if isinstance(row, dict) and safe_key(row.get("npcProxyId"))
    ]
    rows_by_proxy = tracking_corpus.get("rowsByProxy") or {}
    contexts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for proxy_id in sorted({
        safe_key(row.get("npcProxyId")) for row in consumers
    }, key=natural_key):
        rows = list(rows_by_proxy.get(proxy_id) or [])
        if not rows:
            continue
        proxy_consumers = [
            row for row in consumers
            if safe_key(row.get("npcProxyId")) == proxy_id
        ]
        source_files = list(dict.fromkeys(
            safe_key(row.get("sourceFile")) for row in rows
            if safe_key(row.get("sourceFile"))
        ))
        source_sha256 = {
            source_file: next(
                safe_key(row.get("sourceSha256"))
                for row in rows
                if safe_key(row.get("sourceFile")) == source_file
            )
            for source_file in source_files
        }
        row_identities = [(
            safe_key(row.get("missionId")),
            safe_key(row.get("questId")),
            row.get("objectiveIndex"),
            row.get("trackingIndex"),
        ) for row in rows]
        mission_ids = {
            safe_key(row.get("missionId")) for row in rows
            if safe_key(row.get("missionId"))
        }
        scene_ids = {
            safe_key(row.get("sceneId")) for row in rows
            if safe_key(row.get("sceneId"))
        }
        consumer_levels = {
            safe_key(row.get("levelId")) for row in proxy_consumers
            if safe_key(row.get("levelId"))
        }
        valid = (
            all(row.get("qualified") is True for row in rows)
            and len(row_identities) == len(set(row_identities))
            and len(mission_ids) == 1
            and len(scene_ids) == 1
            and len(consumer_levels) == 1
            and consumer_levels == scene_ids
        )
        if not valid:
            failures.append({
                "validator": "genericMissionNpcProxyTrackingContext",
                "gate": "exactUnfilteredSingleMissionProxyTracking",
                "storyKey": story_key,
                "npcProxyId": proxy_id,
                "sourcePaths": source_files,
                "sourceSha256": source_sha256,
                "expected": {
                    "trackingFields": sorted(NPC_PROXY_TRACKING_INFO_FIELDS),
                    "useFilterCondition": False,
                    "guidingArea": "number",
                    "uniqueRowIdentities": True,
                    "singleMission": True,
                    "singleTrackingLevel": True,
                    "consumerLevelMatchesTrackingLevel": True,
                },
                "actual": {
                    "rowCount": len(rows),
                    "missionIds": sorted(mission_ids, key=natural_key),
                    "sceneIds": sorted(scene_ids, key=natural_key),
                    "consumerLevels": sorted(consumer_levels, key=natural_key),
                    "duplicateRowIdentityCount": (
                        len(row_identities) - len(set(row_identities))
                    ),
                    "unsupportedRows": [
                        {
                            key: row.get(key)
                            for key in (
                                "missionId", "questId", "objectiveIndex",
                                "trackingIndex", "sourceFile", "sourceSha256",
                                "tracking",
                            )
                        }
                        for row in rows if row.get("qualified") is not True
                    ][:10],
                },
            })
            continue
        runtime_mission_id = next(iter(mission_ids))
        level_id = next(iter(scene_ids))
        contexts.append({
            "proxyId": proxy_id,
            "levelId": level_id,
            "missionId": runtime_mission_id,
            "nominalMissionId": nominal_mission_id,
            "crossMission": runtime_mission_id != nominal_mission_id,
            "questIds": sorted({
                safe_key(row.get("questId")) for row in rows
                if safe_key(row.get("questId"))
            }, key=natural_key),
            "rows": [{
                key: row.get(key)
                for key in (
                    "missionId", "questId", "objectiveIndex",
                    "trackingIndex", "npcProxyId", "sceneId",
                    "tracking", "sourceFile", "sourceSha256",
                )
            } for row in rows],
            "sourceFile": source_files[0] if len(source_files) == 1 else None,
            "sourceFiles": source_files,
            "sourceSha256": source_sha256,
            "relation": "mission_quest_npc_proxy_tracking_context",
            "recoveryMethod": "complete_active_mission_runtime_census",
            "missionContextOnly": True,
            "missionOwnership": False,
            "questPlaybackOwnership": False,
            "orderEvidence": False,
            "graphEffect": "none",
        })
    return contexts, failures

def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = safe_key(value)
        if text and text not in out:
            out.append(text)
    return out

def _sha256_file(path: Path) -> str:
    return sha256_file(path).upper()

def _configured_game_assembly_path() -> Path | None:
    return resolve_installed_native_inputs()[0]

def _merge_exact_interaction_trigger_with_native_playback(
    prior: dict[str, Any] | None,
    native: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Preserve an exact activator when generic native playback also exists."""
    if (
        not isinstance(prior, dict)
        or prior.get("evidenceKind")
        != "reading_popup_world_entity_interaction_trigger"
        or len(prior.get("worldEntityInteractionTriggers") or []) != 1
    ):
        return dict(native), False
    merged = dict(native)
    for field in (
        "levelId",
        "readingPopupRowId",
        "readingPopupRowIds",
        "unhostedReadingPopupReceivers",
        "worldEntityInteractionTriggers",
        "richContentStatus",
        "contentTextIds",
        "prtsDefinition",
        "prtsReadingDefinition",
        "consumerBoundary",
    ):
        if field in prior:
            merged[field] = prior[field]
    merged.update({
        "recoveryStatus":
            "exact_current_build_interaction_trigger_recovered",
        "evidenceKind":
            "reading_popup_world_entity_interaction_trigger",
        "activationStatus":
            "exact_world_entity_interaction_trigger",
        "missionBridgeStatus": "unresolved",
        "activationBoundary": (
            "the exact WorldEntityRegistry script/slot and complete map "
            "interaction raise the custom event consumed by the exact local "
            "ShowUIReadingPopPanel path; neither source carries a mission or "
            "quest owner"
        ),
        "graphEffect": "none",
    })
    return merged, True

def _timeline(mission_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mission_payload, dict):
        return {}
    value = mission_payload.get("timelineRecovery")
    return value if isinstance(value, dict) else {}

def _flow(mission_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mission_payload, dict):
        return {}
    value = mission_payload.get("flow")
    return value if isinstance(value, dict) else {}

DIRECT_OBJECTIVE_STORY_CONDITION_FIELDS = {
    "CheckCutsceneFinish": "_cutsceneId",
    "CheckRemoteCommFinish": "_remoteCommId",
    "CheckRepeatableTalkFinish": "_dialogId",
    "CheckSNSDialogComplete": "_dialogId",
    "CheckTalkOptionFinish": "_dialogId",
}

def _exact_levelscript_property_story_consumer(
    row: dict[str, Any],
    quest_id: str,
) -> bool:
    """Validate a typed property check joined to its native Story consumer."""
    key = safe_key(row.get("conditionKey"))
    level_id = safe_key(row.get("mapId"))
    script_id = safe_key(row.get("scriptId"))
    owner = row.get("nativeEventOwner")
    occurrence = row.get("levelScriptOccurrence")
    source_files = set(_string_list(row.get("sourceFiles")))
    quest_mission = quest_id.split("_q#", 1)[0]
    expected_mission_suffix = f"/MissionRuntimeAsset/{quest_mission}.json"
    expected_script_suffix = (
        f"/LevelScriptData/{level_id}/{script_id}.json"
    )
    if (
        safe_key(row.get("relation"))
        != "levelscript_property_story_consumer"
        or safe_key(row.get("direction")) != "shared_trigger"
        or safe_key(row.get("phase")) != "progress_and_runtime_playback"
        or safe_key(row.get("confidence")) != "native_typed_direct"
        or safe_key(row.get("evidenceTier")) != "native_direct"
        or safe_key(row.get("conditionType"))
        != "CheckLevelScriptPropertyBool"
        or not isinstance(row.get("conditionValue"), bool)
        or not key
        or not level_id
        or not script_id
        or not isinstance(owner, dict)
        or not isinstance(occurrence, dict)
        or not any(path.replace("\\", "/").endswith(expected_mission_suffix)
                   for path in source_files)
        or not any(path.replace("\\", "/").endswith(expected_script_suffix)
                   for path in source_files)
        or safe_key(occurrence.get("levelId")) != level_id
        or safe_key(occurrence.get("scriptId")) != script_id
        or safe_key(occurrence.get("sourceFile")) not in source_files
        or not safe_key(occurrence.get("recordClass")).startswith("play_")
        or safe_key(owner.get("status")) != "exact_serialized_control_path"
        or safe_key(owner.get("headerName"))
        != "ScriptEvent_OnPropertyChanged"
        or safe_key(owner.get("downstreamControlStatus"))
        != "exact_serialized_typed_reachability"
    ):
        return False
    detail = owner.get("eventDetail")
    if (
        not isinstance(detail, dict)
        or safe_key(detail.get("propertyKeyFilter")) != key
        or safe_key(detail.get("payloadSchemaStatus"))
        != "exact_current_build_memorypack_fields"
        or safe_key(detail.get("transport"))
        != "local-level-script-variable-event"
        or (detail.get("validateParam") or {}).get("constValue")
        is not row.get("conditionValue")
    ):
        return False
    local_id = occurrence.get("localId")
    return sum(
        1
        for step in owner.get("path") or []
        if isinstance(step, dict)
        and step.get("localId") == local_id
        and safe_key(step.get("recordClass")).startswith("play_")
    ) == 1

def _strict_quest_attachments(
    partial_row: dict[str, Any],
    flow: dict[str, Any] | None = None,
) -> tuple[set[str], set[str]]:
    quest_ids: set[str] = set()
    scene_keys: set[str] = set()
    for edge in partial_row.get("directEdges") or []:
        if not isinstance(edge, dict) or safe_key(edge.get("tier")) != "strong":
            continue
        edge_quest_ids = _string_list(edge.get("questIds"))
        if not edge_quest_ids:
            continue
        quest_ids.update(edge_quest_ids)
        for field in ("from", "to"):
            scene_key = safe_key(edge.get(field))
            if scene_key:
                scene_keys.add(scene_key)
    for row in _flow_story_connections(flow or {}):
        scene_key = safe_key(row.get("key"))
        occurrences = [
            occurrence
            for occurrence in row.get("levelScriptOccurrences") or []
            if isinstance(occurrence, dict)
        ]
        if (
            not scene_key
            or safe_key(row.get("relation")) != "levelscript_mission_context"
            or safe_key(row.get("confidence")) != "scoped_script"
            or row.get("hasUnscopedOrOtherMissionOccurrences") is not False
            or not occurrences
            or "mission_condition_checks_script"
            not in _string_list(row.get("scopeEvidenceKinds"))
        ):
            continue
        occurrence_quest_ids: set[str] = set()
        complete = True
        for occurrence in occurrences:
            conditions = [
                condition
                for condition in occurrence.get("missionConditions") or []
                if isinstance(condition, dict)
            ]
            if (
                not conditions
                or "mission_condition_checks_script"
                not in _string_list(occurrence.get("scopeEvidenceKinds"))
            ):
                complete = False
                break
            occurrence_quest_ids.update(
                safe_key(condition.get("questId"))
                for condition in conditions
                if safe_key(condition.get("questId"))
            )
        if complete and len(occurrence_quest_ids) == 1:
            quest_ids.update(occurrence_quest_ids)
            scene_keys.add(scene_key)
    direct_quest_story_relations = {
        "client_action_start": (1, "start"),
        "client_action_succeed": (2, "succeed"),
        "client_action_failed": (4, "failed"),
    }
    for quest in (flow or {}).get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        if not quest_id:
            continue
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            scene_key = safe_key(row.get("key"))
            relation = safe_key(row.get("relation"))
            objective_index = row.get("objectiveIndex")
            finish_id = row.get("finishId")
            if scene_key and _exact_levelscript_property_story_consumer(
                row,
                quest_id,
            ):
                quest_ids.add(quest_id)
                scene_keys.add(scene_key)
                continue
            if (
                scene_key
                and relation == "objective_tracking_story_reference"
                and safe_key(row.get("direction")) == "context"
                and safe_key(row.get("phase")) == "tracking"
                and safe_key(row.get("confidence")) == "native_typed_context"
                and safe_key(row.get("trackingType")) == "SnsTrackingInfo"
                and row.get("playback") is False
                and re.fullmatch(
                    r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                    r"\[\d+\]\.trackingInfoList\[\d+\]\.snsDialogId",
                    safe_key(row.get("source")),
                )
                and isinstance(objective_index, int)
                and not isinstance(objective_index, bool)
                and objective_index > 0
                and isinstance(row.get("trackingIndex"), int)
                and not isinstance(row.get("trackingIndex"), bool)
                and int(row["trackingIndex"]) >= 0
            ):
                quest_ids.add(quest_id)
                scene_keys.add(scene_key)
                continue
            condition_type = safe_key(row.get("conditionType"))
            condition_field = DIRECT_OBJECTIVE_STORY_CONDITION_FIELDS.get(
                condition_type
            )
            if (
                scene_key
                and relation == "objective_condition"
                and safe_key(row.get("direction")) == "story_to_quest"
                and safe_key(row.get("phase")) == "progress"
                and safe_key(row.get("confidence")) == "direct"
                and bool(condition_field)
                and re.fullmatch(
                    r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                    rf"\[\d+\]\.condition\.{condition_field}",
                    safe_key(row.get("source")),
                )
                and isinstance(objective_index, int)
                and not isinstance(objective_index, bool)
                and objective_index > 0
                and (
                    condition_type != "CheckTalkOptionFinish"
                    or (
                        isinstance(finish_id, int)
                        and not isinstance(finish_id, bool)
                    )
                )
            ):
                quest_ids.add(quest_id)
                scene_keys.add(scene_key)
                continue
            expected = direct_quest_story_relations.get(relation)
            if (
                not scene_key
                or not expected
                or safe_key(row.get("direction")) != "quest_to_story"
                or safe_key(row.get("phase")) != expected[1]
                or safe_key(row.get("confidence")) != "native_typed_direct"
                or row.get("actionSlot") != expected[0]
                or not isinstance(row.get("actionId"), int)
                or isinstance(row.get("actionId"), bool)
                or int(row["actionId"]) < 0
                or not safe_key(row.get("actionType"))
                or not re.fullmatch(
                    r"MissionRuntimeAsset\.clientActionMapKey\[\d+\] -> "
                    r"actionMapRaw\.actionList\[\d+\]\._[A-Za-z]+Id",
                    safe_key(row.get("source")),
                )
            ):
                continue
            quest_ids.add(quest_id)
            scene_keys.add(scene_key)
    return quest_ids, scene_keys

def _diagnostic_quest_attachments(
    timeline: dict[str, Any],
    candidate_scene_keys: set[str],
) -> tuple[set[str], set[str], Counter[str]]:
    quest_ids: set[str] = set()
    scene_keys: set[str] = set()
    source_counts: Counter[str] = Counter()
    placements = timeline.get("scenePlacement")
    if not isinstance(placements, dict):
        return quest_ids, scene_keys, source_counts
    for placement in placements.values():
        if not isinstance(placement, dict):
            continue
        scene_key = safe_key(placement.get("sceneKey"))
        if scene_key not in candidate_scene_keys:
            continue
        attach_sources = [
            source
            for source in placement.get("questAttachSources") or []
            if isinstance(source, dict)
        ]
        non_owning_ids = {
            safe_key(source.get("questId"))
            for source in attach_sources
            if (
                safe_key(source.get("source"))
                in NON_OWNING_DIAGNOSTIC_QUEST_ATTACH_SOURCES
                and safe_key(source.get("questId"))
            )
        }
        owning_or_unclassified_ids = {
            safe_key(source.get("questId"))
            for source in attach_sources
            if (
                safe_key(source.get("source"))
                not in NON_OWNING_DIAGNOSTIC_QUEST_ATTACH_SOURCES
                and safe_key(source.get("questId"))
            )
        }
        attached_ids = [
            quest_id
            for quest_id in _string_list(placement.get("questIds"))
            if (
                quest_id not in non_owning_ids
                or quest_id in owning_or_unclassified_ids
            )
        ]
        if not attached_ids:
            continue
        quest_ids.update(attached_ids)
        scene_keys.add(scene_key)
        for source in attach_sources:
            if safe_key(source.get("questId")) not in attached_ids:
                continue
            source_counts[safe_key(source.get("source")) or "unknown"] += 1
    return quest_ids, scene_keys, source_counts

def _flow_story_connections(flow: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in flow.get("missionStoryConnections") or []
        if isinstance(row, dict)
    ]
    rows.extend(
        row
        for quest in flow.get("quests") or []
        if isinstance(quest, dict)
        for row in quest.get("storyConnections") or []
        if isinstance(row, dict)
    )
    for field in (
        "unlinkedNativePlayback",
        "unlinkedDefinitionOnly",
        "unlinkedTimelineContainment",
        "unresolvedDialogTreeNarrativeActions",
        "unlinkedDialogTreeNarrativeActions",
        "unresolvedDialogTreeLeftSubtitleActions",
        "unlinkedDialogTreeLeftSubtitleActions",
        "unresolvedDialogTreeStoryPlaybackCarriers",
    ):
        rows.extend(
            row
            for row in flow.get(field) or []
            if isinstance(row, dict)
        )
    return rows
