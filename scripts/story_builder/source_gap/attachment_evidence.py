"""Quest attachment and generated Story-manifest validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
from .foundation import (
    read_json,
    safe_key,
)
from .contracts import STORY_BINDING_COVERAGE_SCHEMA_VERSION
from ..level_bindings import _load_levelscript_binding_data
from ..levelscript_binary import levelscript_action_map_membership
from ..mission_recovery import natural_key


from .data import (
    QUEST_ATTACHMENT_DIAGNOSTIC_MAPPING_ID,
    QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS,
    QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_HASHES,
    QUEST_ATTACHMENT_DIAGNOSTIC_DECLARATIONS,
)

from .providers import (
    _diagnostic_quest_attachments,
    _flow,
    _repo_source_path,
    _sha256_file,
    _strict_quest_attachments,
    _string_list,
    _timeline,
)

def load_story_trigger_manifest_evidence(
    coverage_path: Path,
    language: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the current trigger manifest or expose the exact rejected gate."""
    source_path = _repo_source_path(coverage_path)
    source_sha256 = _sha256_file(coverage_path)
    base = {
        "validator": "story_trigger_manifest_coverage_v1",
        "sourcePath": source_path,
        "sourceSha256": source_sha256,
        "expectedSchemaVersion": STORY_BINDING_COVERAGE_SCHEMA_VERSION,
        "expectedLanguage": language,
        "graphEffect": "none",
    }
    if not coverage_path.is_file():
        failure = {
            "validator": base["validator"],
            "gate": "coverage_report_exists",
            "sourcePath": source_path,
            "sourceSha256": source_sha256,
            "expected": {"exists": True},
            "actual": {"exists": False},
        }
        return {}, {
            **base,
            "status": "validation_failed",
            "rowCount": 0,
            "validationFailures": [failure],
        }
    report = read_json(coverage_path, {})
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": base["validator"],
            "gate": gate,
            "sourcePath": source_path,
            "sourceSha256": source_sha256,
            "expected": expected,
            "actual": actual,
        })

    if not isinstance(report, dict):
        reject("coverage_report_object", {"type": "object"}, {
            "type": type(report).__name__,
        })
        manifest: dict[str, Any] = {}
    else:
        if report.get("schemaVersion") != STORY_BINDING_COVERAGE_SCHEMA_VERSION:
            reject(
                "schema_version",
                {"schemaVersion": STORY_BINDING_COVERAGE_SCHEMA_VERSION},
                {"schemaVersion": report.get("schemaVersion")},
            )
        if safe_key(report.get("language")) != language:
            reject(
                "language",
                {"language": language},
                {"language": safe_key(report.get("language"))},
            )
        raw_manifest = report.get("storyTriggerManifest")
        if not isinstance(raw_manifest, dict):
            reject(
                "story_trigger_manifest_object",
                {"type": "object"},
                {"type": type(raw_manifest).__name__},
            )
            manifest = {}
        else:
            manifest = raw_manifest
    if failures:
        manifest = {}
    return manifest, {
        **base,
        "status": "validation_failed" if failures else "validated",
        "rowCount": len(manifest),
        "validationFailures": failures,
    }

def build_quest_attachment_diagnostic_index(
    mission_payloads: dict[str, dict[str, Any]],
    *,
    mission_runtime_path: Path | None = None,
    levelscript_path: Path | None = None,
    source_path_overrides: dict[str, Path] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Validate exact current-build quest/Story negative boundaries.

    These rows retire broad diagnostic co-membership from the actionable queue.
    They do not attach a quest to a Story file and do not assert chronology.
    Hash changes, generated-shape changes, or a newly recovered strict route
    reopen the quest automatically.
    """
    source_paths = {
        name: ROOT / relative_path
        for name, relative_path
        in QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS.items()
    }
    if mission_runtime_path is not None:
        source_paths["missionRuntime:e10m4d5"] = mission_runtime_path
    if levelscript_path is not None:
        source_paths[
            "levelScript:dung02_rdg002/24400000018"
        ] = levelscript_path
    source_paths.update(source_path_overrides or {})
    actual_hashes = {
        name: _sha256_file(path)
        for name, path in source_paths.items()
    }
    mismatches = sorted(
        name
        for name, expected
        in QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_HASHES.items()
        if actual_hashes.get(name) != expected
    )
    status: dict[str, Any] = {
        "mappingId": QUEST_ATTACHMENT_DIAGNOSTIC_MAPPING_ID,
        "status":
            "inactive_source_validation_failed" if mismatches else "validating",
        "sourceHashes": actual_hashes,
        "expectedSourceHashes": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_HASHES,
        "sourcePaths": {
            name: _repo_source_path(path)
            for name, path in source_paths.items()
        },
        "sourceHashMismatches": mismatches,
        "graphEffect": "none",
        "queueEffect":
            "close broad diagnostic quest co-membership only while every "
            "current-build source and generated condition shape matches",
    }
    if mismatches:
        return {}, status

    source_bytes = {
        name: path.read_bytes()
        for name, path in source_paths.items()
    }
    npc_proxy_payload = read_json(
        source_paths["gameplayConfig:NpcProxyExDataTable"]
    )
    npc_proxy_table_payload = read_json(
        source_paths["gameplayConfig:NpcProxyTable"]
    )
    world_entity_registry_payload = read_json(
        source_paths["gameplayConfig:WorldEntityRegistry"]
    )

    def exact_rows(actual: Any, expected: Any) -> bool:
        if (
            not isinstance(actual, list)
            or not isinstance(expected, (list, tuple))
            or len(actual) != len(expected)
            or not all(isinstance(row, dict) for row in actual)
            or not all(isinstance(row, dict) for row in expected)
        ):
            return False
        return sorted(
            json.dumps(row, sort_keys=True, separators=(",", ":"))
            for row in actual
        ) == sorted(
            json.dumps(row, sort_keys=True, separators=(",", ":"))
            for row in expected
        )

    index: dict[str, dict[str, Any]] = {}
    validation_failures: list[str] = []
    validation_failure_details: list[dict[str, Any]] = []
    for quest_id, declaration in (
        QUEST_ATTACHMENT_DIAGNOSTIC_DECLARATIONS.items()
    ):
        payload = mission_payloads.get(declaration["mission"])
        timeline = _timeline(payload)
        flow = _flow(payload)
        timeline_quests = {
            safe_key(row.get("questId")): row
            for row in timeline.get("quests") or []
            if isinstance(row, dict) and safe_key(row.get("questId"))
        }
        flow_quests = {
            safe_key(row.get("id")): row
            for row in flow.get("quests") or []
            if isinstance(row, dict) and safe_key(row.get("id"))
        }
        quest = timeline_quests.get(quest_id)
        flow_quest = flow_quests.get(quest_id)
        objectives = quest.get("objectives") if isinstance(quest, dict) else None
        objective = (
            objectives[0]
            if isinstance(objectives, list)
            and len(objectives) == 1
            and isinstance(objectives[0], dict)
            else {}
        )
        leaves = objective.get("conditionLeaves")
        leaf = (
            leaves[0]
            if isinstance(leaves, list)
            and len(leaves) == 1
            and isinstance(leaves[0], dict)
            else {}
        )
        connections = (
            flow_quest.get("storyConnections")
            if isinstance(flow_quest, dict)
            else None
        )
        expected_source_file = declaration.get(
            "sourceFile",
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "missionRuntime:e10m4d5"
            ],
        )
        valid = (
            isinstance(quest, dict)
            and isinstance(flow_quest, dict)
            and safe_key((quest.get("source") or {}).get("file"))
            == expected_source_file
            and tuple(_string_list(quest.get("prevQuestIds")))
            == declaration["prevQuestIds"]
            and objective.get("index") == 1
            and safe_key(leaf.get("type")) == declaration["conditionType"]
            and set(_string_list(objective.get("conditionTypes")))
            == {declaration["conditionType"]}
        )
        validation_kind = declaration.get(
            "validationKind",
            "variant_runtime_shell",
        )
        if valid and validation_kind == "variant_runtime_shell":
            diagnostic_connections = (
                connections
                if isinstance(connections, list)
                and connections
                and all(
                    isinstance(row, dict)
                    and safe_key(row.get("relation"))
                    == "variant_runtime_attachment"
                    and safe_key(row.get("direction")) == "context"
                    and safe_key(row.get("phase")) == "context"
                    and safe_key(row.get("confidence")) == "scoped_variant"
                    and safe_key(row.get("source"))
                    == "variant MissionRuntime quest attachment"
                    and safe_key(row.get("variantMission"))
                    == declaration["variantMission"]
                    and safe_key(row.get("attachmentKind"))
                    in {"questPrev", "questSequence"}
                    for row in connections
                )
                else []
            )
            valid = (
                bool(diagnostic_connections)
                and {
                    safe_key(row.get("key"))
                    for row in diagnostic_connections
                }
                == set(declaration["diagnosticStoryKeys"])
            )
        elif valid and validation_kind == (
            "property_getter_without_story_chain"
        ):
            # The producer publishes exact context-only condition-scope rows;
            # they identify stories in the referenced script but do not form
            # a typed ownership or control route. Any drift or newly typed
            # route reopens the diagnostic fail-closed.
            valid = exact_rows(
                connections,
                declaration.get("connectionRows") or (),
            )
        elif valid and validation_kind == (
            "shared_levelscript_condition_scope"
        ):
            # This boundary has no property-scoped generated connection. A
            # newly recovered row must be reviewed rather than accepted as a
            # route implicitly.
            valid = not connections
        elif valid:
            valid = exact_rows(
                connections,
                declaration.get("connectionRows") or (),
            )

        if valid and declaration["conditionType"] == (
            "CheckLevelScriptPropertyBool"
        ):
            property_values = [
                safe_key(row.get("value"))
                for row in leaf.get("propertyKeys") or []
                if isinstance(row, dict)
            ]
            script_values = [
                safe_key((row.get("value") or {}).get("scriptId"))
                for row in leaf.get("scriptIds") or []
                if isinstance(row, dict)
                and isinstance(row.get("value"), dict)
            ]
            valid = (
                property_values == [declaration["propertyKey"]]
                and script_values == [declaration["scriptId"]]
            )
        elif valid:
            comparers = [
                row.get("value")
                for row in leaf.get("comparers") or []
                if isinstance(row, dict)
            ]
            progress_values = [
                row.get("value")
                for row in leaf.get("compareValues") or []
                if isinstance(row, dict)
            ]
            valid = (
                comparers == (
                    [declaration["comparer"]]
                    if "comparer" in declaration
                    else []
                )
                and progress_values == [declaration["progressToCompare"]]
            )

        if valid and validation_kind == "property_getter_without_story_chain":
            levelscript_data = source_bytes.get(
                declaration["levelScriptSourceKey"],
                b"",
            )
            byte_counts = declaration["levelScriptByteStringCounts"]
            try:
                decoded_level = _load_levelscript_binding_data(
                    declaration["levelId"]
                )
            except Exception:
                decoded_level = None
            expected_suffix = f"/{declaration['scriptId']}.json"
            file_entries = [
                row
                for row in (
                    decoded_level.get("files") or []
                    if isinstance(decoded_level, dict)
                    else []
                )
                if str(row.get("file") or "").replace("\\", "/").endswith(
                    expected_suffix
                )
            ]
            file_entry = file_entries[0] if len(file_entries) == 1 else {}
            records = file_entry.get("records") or []
            try:
                action_map, membership_by_start = (
                    levelscript_action_map_membership(
                        levelscript_data,
                        records,
                    )
                )
            except Exception:
                action_map, membership_by_start = {}, {}

            def record_texts(record: dict[str, Any]) -> tuple[str, ...]:
                return tuple(
                    safe_key(hit.get("text"))
                    for field in ("strings", "plainStrings")
                    for hit in record.get(field) or []
                    if isinstance(hit, dict) and safe_key(hit.get("text"))
                )

            getter_records = [
                row
                for row in records
                if declaration["propertyKey"] in record_texts(row)
            ]
            expected_getter = declaration["getterRecord"]
            actual_getter = (
                {
                    "start": getter_records[0].get("start"),
                    "localId": getter_records[0].get("localId"),
                    "nextId": getter_records[0].get("nextId"),
                    "code": getter_records[0].get("code"),
                    "kind": getter_records[0].get("kind"),
                    "uid": safe_key(getter_records[0].get("uid")),
                    "membership": membership_by_start.get(
                        getter_records[0].get("start")
                    ),
                    "texts": record_texts(getter_records[0]),
                }
                if len(getter_records) == 1
                else {}
            )
            story_records_are_separate_actions = all(
                any(
                    story_key in record_texts(record)
                    and safe_key(
                        membership_by_start.get(record.get("start"))
                    ).startswith("actionList#")
                    for record in records
                )
                for story_key in declaration["diagnosticStoryKeys"]
            )
            valid = (
                all(
                    levelscript_data.count(value.encode("utf-8")) == count
                    for value, count in byte_counts.items()
                )
                and actual_getter == expected_getter
                and action_map.get("listCounts") == {
                    "actionList": 18,
                    "getterList": 5,
                    "headerList": 3,
                }
                and story_records_are_separate_actions
            )
        elif valid and validation_kind == "shared_levelscript_condition_scope":
            levelscript_data = source_bytes.get(
                declaration["levelScriptSourceKey"],
                b"",
            )
            byte_counts = declaration["levelScriptByteStringCounts"]
            exact_property_string = (
                b"\x04"
                + len(declaration["propertyKey"]).to_bytes(4, "little")
                + declaration["propertyKey"].encode("utf-8")
            )
            valid = (
                all(
                    levelscript_data.count(value.encode("utf-8")) == count
                    for value, count in byte_counts.items()
                )
                and exact_property_string not in levelscript_data
            )
        elif valid and validation_kind == "mission_bound_npc_proxy_context":
            tracking = objective.get("tracking")
            tracking_row = (
                tracking[0]
                if isinstance(tracking, list)
                and len(tracking) == 1
                and isinstance(tracking[0], dict)
                else {}
            )
            proxy_id = declaration["npcProxyId"]
            proxy_rows = (
                (npc_proxy_payload.get("data") or {}).get(proxy_id)
                if isinstance(npc_proxy_payload, dict)
                else None
            )
            proxy_dialog_rows = (
                tuple(
                    (
                        safe_key(row.get("missionId")),
                        safe_key(row.get("dialogId")),
                    )
                    for row in proxy_rows
                    if isinstance(row, dict)
                )
                if isinstance(proxy_rows, list)
                else ()
            )
            proxy_definition = (
                (npc_proxy_table_payload.get("dataTable") or {}).get(
                    proxy_id
                )
                if isinstance(npc_proxy_table_payload, dict)
                else None
            )
            world_entity = (
                (
                    world_entity_registry_payload.get(
                        "npcProxyBriefInfos"
                    )
                    or {}
                ).get(declaration["worldEntitySegmentId"])
                if isinstance(world_entity_registry_payload, dict)
                else None
            )
            leveldata_data = source_bytes.get(
                declaration["levelDataSourceKey"],
                b"",
            )
            valid = (
                safe_key(tracking_row.get("type"))
                == "NpcProxyTrackingInfo"
                and safe_key(tracking_row.get("npcProxyId")) == proxy_id
                and safe_key(tracking_row.get("scene")) == "map02_lv002"
                and exact_rows(
                    flow_quest.get("levelDataStoryRefs"),
                    declaration["levelDataStoryRefs"],
                )
                and exact_rows(
                    flow_quest.get("proxyDialogs"),
                    ({
                        "dialogId": "dlg_e10m3_2",
                        "npcProxyId": proxy_id,
                        "missionId": declaration["npcProxyMissionId"],
                        "source": (
                            "NpcProxyExDataTable.data[*].dialogId"
                        ),
                    },),
                )
                and proxy_dialog_rows
                == declaration["npcProxyDialogRows"]
                and isinstance(proxy_definition, dict)
                and proxy_definition.get("subDataParentId") == 22800780000
                and safe_key(proxy_definition.get("proxyId")) == proxy_id
                and safe_key(proxy_definition.get("levelId"))
                == "map02_lv002"
                and proxy_definition.get("position")
                == declaration["npcProxyPosition"]
                and proxy_definition.get("envTalkIds")
                == ["envTalk_e10m3_1"]
                and isinstance(world_entity, dict)
                and safe_key(world_entity.get("proxyId")) == proxy_id
                and world_entity.get("position")
                == declaration["npcProxyPosition"]
                and all(
                    leveldata_data.count(value.encode("utf-8")) == count
                    for value, count
                    in declaration["levelDataByteStringCounts"].items()
                )
            )
        elif valid and validation_kind == "weak_leveldata_context":
            tracking = objective.get("tracking")
            tracking_row = (
                tracking[0]
                if isinstance(tracking, list)
                and len(tracking) == 1
                and isinstance(tracking[0], dict)
                else {}
            )
            leveldata_data = source_bytes.get(
                declaration["levelDataSourceKey"],
                b"",
            )
            byte_counts = declaration["levelDataByteStringCounts"]
            proxy_rows = (
                (npc_proxy_payload.get("data") or {}).get(
                    declaration["npcProxyId"]
                )
                if isinstance(npc_proxy_payload, dict)
                else None
            )
            proxy_dialog_rows = (
                tuple(
                    (
                        safe_key(row.get("missionId")),
                        safe_key(row.get("dialogId")),
                    )
                    for row in proxy_rows
                    if isinstance(row, dict)
                )
                if isinstance(proxy_rows, list)
                else ()
            )
            valid = (
                safe_key(tracking_row.get("type"))
                == "NpcProxyTrackingInfo"
                and safe_key(tracking_row.get("npcProxyId"))
                == declaration["npcProxyId"]
                and exact_rows(
                    flow_quest.get("levelDataStoryRefs"),
                    declaration["levelDataStoryRefs"],
                )
                and not flow_quest.get("proxyDialogs")
                and proxy_dialog_rows
                == declaration["npcProxyDialogRows"]
                and all(
                    leveldata_data.count(value.encode("utf-8")) == count
                    for value, count in byte_counts.items()
                )
            )
        if not valid:
            validation_failures.append(quest_id)
            validation_failure_details.append({
                "validator": "questAttachmentDiagnostic",
                "gate": validation_kind,
                "questId": quest_id,
                "missionId": declaration["mission"],
                "sourcePath": expected_source_file,
                "sourceSha256": actual_hashes.get(
                    declaration.get("sourceKey", "missionRuntime:e10m4d5"),
                    "",
                ),
                "expected": {
                    "conditionType": declaration["conditionType"],
                    "prevQuestIds": list(declaration["prevQuestIds"]),
                    "diagnosticStoryKeys": list(
                        declaration["diagnosticStoryKeys"]
                    ),
                    "validationKind": validation_kind,
                    "connectionStoryKeys": (
                        []
                        if validation_kind
                        == "shared_levelscript_condition_scope"
                        else sorted({
                            safe_key(row.get("key"))
                            for row in declaration.get("connectionRows") or []
                            if isinstance(row, dict) and safe_key(row.get("key"))
                        }, key=natural_key)
                    ),
                    "connectionRelations": (
                        []
                        if validation_kind
                        == "shared_levelscript_condition_scope"
                        else sorted({
                            safe_key(row.get("relation"))
                            for row in declaration.get("connectionRows") or []
                            if isinstance(row, dict) and safe_key(row.get("relation"))
                        })
                    ),
                },
                "actual": {
                    "conditionType": safe_key(leaf.get("type")),
                    "prevQuestIds": _string_list(
                        quest.get("prevQuestIds")
                        if isinstance(quest, dict)
                        else []
                    ),
                    "connectionStoryKeys": sorted({
                        safe_key(row.get("key"))
                        for row in connections or []
                        if isinstance(row, dict) and safe_key(row.get("key"))
                    }, key=natural_key),
                    "connectionRelations": sorted({
                        safe_key(row.get("relation"))
                        for row in connections or []
                        if isinstance(row, dict)
                        and safe_key(row.get("relation"))
                    }),
                    "connectionRows": [
                        {
                            key: row.get(key)
                            for key in (
                                "key",
                                "kind",
                                "relation",
                                "direction",
                                "phase",
                                "confidence",
                                "mapId",
                                "scriptId",
                                "conditionKey",
                            )
                            if key in row
                        }
                        for row in (connections or [])[:8]
                        if isinstance(row, dict)
                    ],
                },
            })
            continue

        shared_boundary = declaration["conditionType"] == (
            "CheckLevelScriptPropertyBool"
        )
        index[quest_id] = {
            "questId": quest_id,
            "missionId": declaration["mission"],
            "variantMissionId": declaration["variantMission"],
            "recoveryStatus": declaration["recoveryStatus"],
            "evidenceKind": declaration.get(
                "evidenceKind",
                (
                    "exact property checker plus hash-locked LevelScript "
                    "negative"
                    if shared_boundary
                    else "exact server-owned placeholder with no client "
                    "Story field"
                ),
            ),
            "conditionType": declaration["conditionType"],
            "scriptId": declaration.get("scriptId", ""),
            "propertyKey": declaration.get("propertyKey", ""),
            "diagnosticStoryKeys": list(
                declaration["diagnosticStoryKeys"]
            ),
            "sourceFile": expected_source_file,
            "levelScriptFile": declaration.get(
                "levelScriptFile",
                (
                    QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                        "levelScript:dung02_rdg002/24400000018"
                    ]
                    if shared_boundary
                    else ""
                ),
            ),
            "levelDataFile": declaration.get("levelDataFile", ""),
            "relatedSourceFiles": list(
                declaration.get("relatedSourceFiles") or ()
            ),
            "propertyRecord": declaration.get("getterRecord") or {},
            "npcProxyId": declaration.get("npcProxyId", ""),
            "nativeMappingId": QUEST_ATTACHMENT_DIAGNOSTIC_MAPPING_ID,
            "graphEffect": "none",
            "attachmentBoundary": declaration.get(
                "attachmentBoundary",
                (
                    "the quest checks a named property in a script that "
                    "contains multiple Story calls, but the exact "
                    "current-build script has no matching quest id, property "
                    "key, or property-scoped Story bridge"
                    if shared_boundary
                    else "the objective is server-owned and exposes no "
                    "client-readable Story id or playback field"
                ),
            ),
            "orderBoundary": declaration.get(
                "orderBoundary",
                (
                    "shared LevelScript membership and generated "
                    "quest-sequence context do not identify which Story call, "
                    "if any, belongs to this quest"
                    if shared_boundary
                    else
                    "the generated predecessor-shell Story context is "
                    "diagnostic only and does not establish playback or order"
                ),
            ),
            "reopenWhen": declaration.get(
                "reopenWhen",
                "either source hash or generated condition shape changes, "
                "or a property/quest-scoped native playback route is "
                "recovered",
            ),
        }

    status["validationFailures"] = validation_failures
    status["validationFailureDetails"] = validation_failure_details
    status["validatedQuestIds"] = sorted(index, key=natural_key)
    status["status"] = (
        "active"
        if len(index) == len(QUEST_ATTACHMENT_DIAGNOSTIC_DECLARATIONS)
        and not validation_failures
        else "inactive_generated_shape_validation_failed"
    )
    if status["status"] != "active":
        return {}, status
    return index, status

SERVER_PLACEHOLDER_CONTEXT_RELATIONS = {
    "leveldata_quest_reference": ("context", "context", "direct"),
    "levelscript_condition_scope": ("context", "context", "scoped_script"),
    "npc_proxy_ex_attachment": ("context", "context", "scoped_unique"),
    "variant_runtime_attachment": ("context", "context", "scoped_variant"),
}

def _classify_server_placeholder_story_boundary(
    mission: str,
    quest_id: str,
    mission_payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Classify one opaque server objective with context-only Story evidence."""
    timeline_quest = next((
        row
        for row in _timeline(mission_payload).get("quests") or []
        if isinstance(row, dict) and safe_key(row.get("questId")) == quest_id
    ), None)
    flow_quest = next((
        row
        for row in _flow(mission_payload).get("quests") or []
        if isinstance(row, dict) and safe_key(row.get("id")) == quest_id
    ), None)
    if not isinstance(timeline_quest, dict) or not isinstance(flow_quest, dict):
        return None, None
    objectives = timeline_quest.get("objectives") or []
    leaves = [
        leaf
        for objective in objectives
        if isinstance(objective, dict)
        for leaf in objective.get("conditionLeaves") or []
        if isinstance(leaf, dict)
    ]
    if (
        len(objectives) != 1
        or len(leaves) != 1
        or safe_key(leaves[0].get("type"))
        != "GameConditionServerPlaceHolder"
    ):
        return None, None
    connections = [
        row
        for row in flow_quest.get("storyConnections") or []
        if isinstance(row, dict)
    ]
    if not connections:
        return None, None

    source_file = safe_key((timeline_quest.get("source") or {}).get("file"))
    source_paths = {source_file} if source_file else set()
    failures: list[dict[str, Any]] = []
    quest_mission = quest_id.split("_q#", 1)[0]
    expected_source_suffix = f"/MissionRuntimeAsset/{quest_mission}.json"
    if (
        not source_file
        or not source_file.replace("\\", "/").endswith(expected_source_suffix)
        or not (ROOT / source_file).is_file()
    ):
        failures.append({
            "gate": "mission_runtime_source",
            "expected": expected_source_suffix,
            "actual": source_file,
        })

    for connection in connections:
        relation = safe_key(connection.get("relation"))
        expected_shape = SERVER_PLACEHOLDER_CONTEXT_RELATIONS.get(relation)
        actual_shape = (
            safe_key(connection.get("direction")),
            safe_key(connection.get("phase")),
            safe_key(connection.get("confidence")),
        )
        if not expected_shape or actual_shape != expected_shape:
            failures.append({
                "gate": "context_only_story_relation",
                "expected": {
                    key: list(value)
                    for key, value in SERVER_PLACEHOLDER_CONTEXT_RELATIONS.items()
                },
                "actual": {"relation": relation, "shape": list(actual_shape)},
            })
            continue
        if relation == "leveldata_quest_reference":
            path = safe_key(connection.get("file"))
            if (
                not path
                or not (ROOT / path).is_file()
                or not safe_key(connection.get("key"))
            ):
                failures.append({
                    "gate": "leveldata_context_source",
                    "expected": "existing LevelData file plus exact Story key",
                    "actual": {"file": path, "key": connection.get("key")},
                })
            elif path:
                source_paths.add(path)
        elif relation == "levelscript_condition_scope":
            level_id = safe_key(connection.get("mapId"))
            script_id = safe_key(connection.get("scriptId"))
            path = (
                "export_full/structured/StreamingAssets/Data/Json/"
                f"LevelScriptData/{level_id}/{script_id}.json"
            )
            if not level_id or not script_id or not (ROOT / path).is_file():
                failures.append({
                    "gate": "levelscript_context_source",
                    "expected": "existing typed level/script source",
                    "actual": {"levelId": level_id, "scriptId": script_id},
                })
            else:
                source_paths.add(path)
        elif relation == "npc_proxy_ex_attachment":
            proxy_id = safe_key(connection.get("npcProxyId"))
            proxy_mission = safe_key(connection.get("npcProxyMissionId"))
            proxy_rows = [
                row
                for row in flow_quest.get("proxyDialogs") or []
                if isinstance(row, dict)
                and safe_key(row.get("npcProxyId")) == proxy_id
                and safe_key(row.get("missionId")) == proxy_mission
                and safe_key(row.get("dialogId"))
                == safe_key(connection.get("key"))
            ]
            if not proxy_id or proxy_mission != quest_mission or len(proxy_rows) != 1:
                failures.append({
                    "gate": "npc_proxy_exact_context",
                    "expected": {
                        "missionId": quest_mission,
                        "matchingProxyDialogRows": 1,
                    },
                    "actual": {
                        "missionId": proxy_mission,
                        "matchingProxyDialogRows": len(proxy_rows),
                    },
                })
            proxy_path = QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "gameplayConfig:NpcProxyExDataTable"
            ]
            if (ROOT / proxy_path).is_file():
                source_paths.add(proxy_path)
        elif relation == "variant_runtime_attachment":
            if (
                safe_key(connection.get("variantMission")) != quest_mission
                or not safe_key(connection.get("attachmentKind"))
            ):
                failures.append({
                    "gate": "variant_runtime_scope",
                    "expected": {
                        "variantMission": quest_mission,
                        "attachmentKind": "non-empty",
                    },
                    "actual": {
                        "variantMission": connection.get("variantMission"),
                        "attachmentKind": connection.get("attachmentKind"),
                    },
                })

    if failures:
        first = failures[0]
        return None, {
            "validator": "genericServerPlaceholderStoryBoundary",
            "gate": first["gate"],
            "missionId": mission,
            "questId": quest_id,
            "sourcePath": source_file,
            "expected": first["expected"],
            "actual": first["actual"],
            "independentFailures": failures,
        }

    source_files = sorted(source_paths, key=natural_key)
    return {
        "questId": quest_id,
        "missionId": mission,
        "conditionType": "GameConditionServerPlaceHolder",
        "diagnosticStoryKeys": sorted({
            safe_key(row.get("key"))
            for row in connections
            if safe_key(row.get("key"))
        }, key=natural_key),
        "diagnosticRelations": sorted({
            safe_key(row.get("relation")) for row in connections
        }),
        "recoveryStatus": (
            "closed_server_placeholder_context_without_typed_story_consumer"
        ),
        "sourceFile": source_file,
        "relatedSourceFiles": source_files,
        "sourceHashes": {
            path: _sha256_file(ROOT / path)
            for path in source_files
        },
        "nativeMappingId": "generic-server-placeholder-story-boundary-v1",
        "graphEffect": "none",
        "attachmentBoundary": (
            "the typed objective is a server-owned placeholder and every Story "
            "reference is exact authored context; no client-readable Story id, "
            "playback field, or completion consumer is serialized on the quest"
        ),
        "orderBoundary": (
            "shared LevelData, LevelScript, proxy, or variant context cannot "
            "select playback or relative Story order"
        ),
        "reopenWhen": (
            "the generic shape gains a typed Story lifecycle field or an exact "
            "property/quest-scoped native playback consumer"
        ),
    }, None

def _classify_levelscript_condition_story_boundary(
    mission: str,
    quest_id: str,
    mission_payload: dict[str, Any],
    native_playback_index: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Close exact script co-scope when no typed condition consumer exists."""
    timeline_quest = next((
        row
        for row in _timeline(mission_payload).get("quests") or []
        if isinstance(row, dict) and safe_key(row.get("questId")) == quest_id
    ), None)
    flow_quest = next((
        row
        for row in _flow(mission_payload).get("quests") or []
        if isinstance(row, dict) and safe_key(row.get("id")) == quest_id
    ), None)
    if not isinstance(timeline_quest, dict) or not isinstance(flow_quest, dict):
        return None, None
    objectives = timeline_quest.get("objectives") or []
    leaves = [
        leaf
        for objective in objectives
        if isinstance(objective, dict)
        for leaf in objective.get("conditionLeaves") or []
        if isinstance(leaf, dict)
    ]
    if len(objectives) != 1 or len(leaves) != 1:
        return None, None
    leaf = leaves[0]
    condition_type = safe_key(leaf.get("type"))
    if condition_type not in {
        "CheckLevelScriptPropertyBool",
        "CheckLevelScriptPropertyInt",
        "CheckScriptMonsterKilled",
    }:
        return None, None
    connections = [
        row
        for row in flow_quest.get("storyConnections") or []
        if isinstance(row, dict)
    ]
    if not connections or any(
        safe_key(row.get("relation")) != "levelscript_condition_scope"
        or safe_key(row.get("direction")) != "context"
        or safe_key(row.get("confidence")) != "scoped_script"
        for row in connections
    ):
        return None, None

    script_rows = [
        row.get("value") or {}
        for row in leaf.get("scriptIds") or []
        if isinstance(row, dict) and isinstance(row.get("value"), dict)
    ]
    script_ids = {
        safe_key(row.get("scriptId"))
        for row in script_rows
        if safe_key(row.get("scriptId"))
    }
    connection_pairs = {
        (safe_key(row.get("mapId")), safe_key(row.get("scriptId")))
        for row in connections
    }
    if len(connection_pairs) != 1 or len(script_ids) != 1:
        return None, {
            "validator": "genericLevelScriptConditionStoryBoundary",
            "gate": "unique_condition_script",
            "missionId": mission,
            "questId": quest_id,
            "sourcePath": safe_key((timeline_quest.get("source") or {}).get("file")),
            "expected": {"scriptCount": 1, "connectionPairCount": 1},
            "actual": {
                "scriptIds": sorted(script_ids),
                "connectionPairs": sorted(connection_pairs),
            },
        }
    level_id, script_id = next(iter(connection_pairs))
    if script_id not in script_ids or not level_id:
        return None, {
            "validator": "genericLevelScriptConditionStoryBoundary",
            "gate": "condition_connection_script_agreement",
            "missionId": mission,
            "questId": quest_id,
            "sourcePath": safe_key((timeline_quest.get("source") or {}).get("file")),
            "expected": {"scriptId": next(iter(script_ids))},
            "actual": {"levelId": level_id, "scriptId": script_id},
        }
    levelscript_file = (
        "export_full/structured/StreamingAssets/Data/Json/"
        f"LevelScriptData/{level_id}/{script_id}.json"
    )
    levelscript_path = ROOT / levelscript_file
    mission_runtime_file = safe_key(
        (timeline_quest.get("source") or {}).get("file")
    )
    if not levelscript_path.is_file() or not (ROOT / mission_runtime_file).is_file():
        return None, {
            "validator": "genericLevelScriptConditionStoryBoundary",
            "gate": "typed_source_files",
            "missionId": mission,
            "questId": quest_id,
            "sourcePath": levelscript_file,
            "expected": "existing MissionRuntime and LevelScript sources",
            "actual": {
                "missionRuntimeExists": (ROOT / mission_runtime_file).is_file(),
                "levelScriptExists": levelscript_path.is_file(),
            },
        }
    levelscript_data = levelscript_path.read_bytes()
    property_keys = [
        safe_key(row.get("value"))
        for row in leaf.get("propertyKeys") or []
        if isinstance(row, dict) and safe_key(row.get("value"))
    ]
    if condition_type.startswith("CheckLevelScriptProperty"):
        if len(property_keys) != 1 or property_keys[0].encode("utf-8") in levelscript_data:
            return None, None
    elif property_keys:
        return None, None

    native_event_names: set[str] = set()
    if condition_type == "CheckScriptMonsterKilled":
        for connection in connections:
            story_key = safe_key(connection.get("key"))
            occurrences = [
                row
                for row in native_playback_index.get(story_key) or []
                if safe_key(row.get("levelId")) == level_id
                and safe_key(row.get("scriptId")) == script_id
            ]
            if not occurrences:
                return None, None
            owners = [
                owner
                for occurrence in occurrences
                for owner in occurrence.get("nativeEventOwners") or []
                if isinstance(owner, dict)
            ]
            if not owners or any(
                safe_key(owner.get("status"))
                != "exact_serialized_control_path"
                or safe_key(owner.get("headerName"))
                != "ScriptEvent_OnLeaderEnterTriggerVolume"
                for owner in owners
            ):
                return None, None
            native_event_names.update(
                safe_key(owner.get("headerName")) for owner in owners
            )

    story_keys = sorted({
        safe_key(row.get("key"))
        for row in connections
        if safe_key(row.get("key"))
    }, key=natural_key)
    return {
        "questId": quest_id,
        "missionId": mission,
        "conditionType": condition_type,
        "conditionKey": property_keys[0] if property_keys else "",
        "diagnosticStoryKeys": story_keys,
        "diagnosticRelations": ["levelscript_condition_scope"],
        "recoveryStatus": (
            "closed_levelscript_condition_scope_without_typed_story_consumer"
        ),
        "sourceFile": mission_runtime_file,
        "levelScriptFile": levelscript_file,
        "relatedSourceFiles": [mission_runtime_file, levelscript_file],
        "sourceHashes": {
            mission_runtime_file: _sha256_file(ROOT / mission_runtime_file),
            levelscript_file: _sha256_file(levelscript_path),
        },
        "nativeEventNames": sorted(native_event_names),
        "nativeMappingId": "generic-levelscript-condition-story-boundary-v1",
        "graphEffect": "none",
        "attachmentBoundary": (
            "the typed quest condition names this LevelScript, but the original "
            "serialized Story actions expose no matching property/condition "
            "consumer path"
        ),
        "orderBoundary": (
            "same-script membership does not identify which independent Story "
            "action, if any, belongs to the quest or establish relative order"
        ),
        "reopenWhen": (
            "an exact condition-key/value consumer reaches Story playback, or "
            "the original MissionRuntime/LevelScript shape changes"
        ),
    }, None

def build_general_quest_attachment_boundary_index(
    partial_report: dict[str, Any],
    mission_payloads: dict[str, dict[str, Any]],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Discover graph-neutral quest boundaries from reusable typed patterns."""
    index: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    candidates: list[str] = []
    native_playback_index = native_playback_index or {}
    for partial_row in partial_report.get("missions") or []:
        if not isinstance(partial_row, dict):
            continue
        mission = safe_key(partial_row.get("mission"))
        payload = mission_payloads.get(mission)
        if not isinstance(payload, dict):
            continue
        timeline = _timeline(payload)
        flow = _flow(payload)
        candidate_scene_keys = {
            safe_key(node.get("key"))
            for node in partial_row.get("nodes") or []
            if isinstance(node, dict) and safe_key(node.get("key"))
        }
        quest_ids = {
            safe_key(row.get("questId"))
            for row in timeline.get("quests") or []
            if isinstance(row, dict) and safe_key(row.get("questId"))
        }
        strict_ids, _strict_scenes = _strict_quest_attachments(partial_row, flow)
        diagnostic_ids, _diagnostic_scenes, _counts = (
            _diagnostic_quest_attachments(timeline, candidate_scene_keys)
        )
        for quest_id in sorted(
            (quest_ids & diagnostic_ids) - strict_ids,
            key=natural_key,
        ):
            candidates.append(quest_id)
            row, failure = _classify_server_placeholder_story_boundary(
                mission,
                quest_id,
                payload,
            )
            if row is None and failure is None:
                row, failure = _classify_levelscript_condition_story_boundary(
                    mission,
                    quest_id,
                    payload,
                    native_playback_index,
                )
            if row:
                index[quest_id] = row
            if failure:
                failures.append(failure)
    return index, {
        "mappingId": "generic-quest-story-attachment-boundaries-v1",
        "status": "validation_failed" if failures else "active",
        "graphEffect": "none",
        "candidateQuestIds": sorted(set(candidates), key=natural_key),
        "validatedQuestIds": sorted(index, key=natural_key),
        "validationFailures": failures,
    }
