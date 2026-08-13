#!/usr/bin/env python3
"""Audit the static activation frontier of unresolved native Story receivers.

Mission Pipeline already preserves exact native event receivers that lead to
Story playback while refusing to invent a mission owner.  This audit asks the
next narrower question for each hosting LevelScript:

* how the LevelScript says it starts;
* which validated LevelData member-22 dictionary contains it;
* whether that container names a MissionRuntime id;
* whether any decoded ManualStartLevelScript row literally targets it.

The result is a typed Mission Pipeline context surface.  A generic LevelData
container, activation request, Manual start type, or incoming manual-control
edge does not by itself identify a mission, quest, playback order, or
server-side state selector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for search_path in (ROOT / "scripts",):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from common import (  # noqa: E402
    STORY_RECOVERY_REPORTS_DIR,
    md_escape,
    read_bytes_cached,
    read_json,
    rel_path,
    write_json,
    write_report_json,
    write_text_if_changed,
)
from story_builder.context import (  # noqa: E402
    GAMEPLAY_CONFIG_DIR,
    LEVELDATA_DIR,
    LEVELSCRIPT_DIR,
    MRA_DIR,
    SPAWNER_CONFIG_DIR,
)
from story_builder.level_bindings import (  # noqa: E402
    _native_vector_close,
    _parse_leveldata_mission_host_name,
    build_leveldata_mission_area_script_host_index,
    decode_levelscript_native_action_topology,
    parse_leveldata_levelscript_brief_dictionary,
)
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_task_conditions,
    decode_levelscript_binary_file,
)
from story_builder.levelscript_manual_control import (  # noqa: E402
    build_manual_control_index,
)
from story_builder.mission_recovery import (  # noqa: E402
    decode_mission_script_conditions,
    decode_mission_world_entity_condition_refs,
)


SCHEMA = "nativeReceiverActivationFrontier.v28"

TELEPORT_FINISH_CORRELATION_MAPPING_ID = (
    "gameassembly-2026-08-02-teleport-finish-action-id-correlation-v1"
)
TELEPORT_FINISH_EVENT_TYPE = "LevelEvent_OnTeleportFinish"
TELEPORT_FINISH_FILTER_RE = re.compile(r"[0-9a-f]{8}")
TELEPORT_FINISH_FILTER_BYTES_RE = re.compile(
    rb"(?<![0-9a-f])([0-9a-f]{8})(?![0-9a-f])"
)
TELEPORT_FINISH_RUNTIME_CONTRACT = {
    "mappingId": TELEPORT_FINISH_CORRELATION_MAPPING_ID,
    "listenerType": "Beyond.Gameplay.Actions.LevelEvent.OnTeleportFinish",
    "listenerActionIdFieldToken": "0x04006dec",
    "listenerProcessMethodToken": "0x060095f5",
    "listenerProcessMethodVa": "0x186abe000",
    "teleportParamType": "Beyond.Gameplay.TeleportParam",
    "teleportParamActionIdFieldToken": "0x04004c72",
    "teleportFinishPublisherMethod": (
        "Beyond.Gameplay.TeleportProcessor._OnTeleportFinish"
    ),
    "teleportFinishPublisherMethodVa": "0x184970510",
    "gameAssemblySha256": (
        "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
    ),
    "globalMetadataSha256": (
        "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
    ),
}

# This is the binary-validated namespace rule shared by every LevelScript
# module property.  LevelData writes the module's save-state fields as
# ``@<LsmPtr id>_<save key>``; the id is a runtime namespace, not an object or
# mission identifier.  Keep this evidence separate from the semantic
# Encounter adapter below so new typed module families can be surfaced without
# adding one function per object.
LEVELSCRIPT_MODULE_PROPERTY_MAPPING_ID = (
    "gameassembly-2026-08-02-levelscriptmodule-save-prefix-v1"
)
LEVELSCRIPT_MODULE_PROPERTY_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
LEVELSCRIPT_MODULE_PROPERTY_METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
LEVELSCRIPT_MODULE_PROPERTY_NAME_RE = re.compile(r"@(?P<module_id>\d+)_(?P<suffix>.+)")

# The installed 2026-08-02 binary identifies this serialized property family
# as the reusable Encounter controller contract.  The names below are suffixes
# because LevelData namespaces every property with its owning LsmPtr module id.
# GameAssembly's LevelScriptModule.GetSaveKeyPrefixed reads the module id at
# this+0x18 before formatting the supplied save key; it is not necessarily the
# hosting LevelScript id.  This
# is deliberately a structural classifier: host filenames and Story-key names
# never participate.
ENCOUNTER_CONTROLLER_MAPPING_ID = (
    "gameassembly-2026-08-02-levelscriptmodule-save-prefix-encounter-contract"
)
ENCOUNTER_REQUIRED_BOOL_SUFFIXES = (
    "is_enabled",
    "is_completed",
    "is_activated",
    "is_failed",
    "battle_completed",
    "pass_first_intro",
)
ENCOUNTER_REQUIRED_DATA_SUFFIXES = (
    "enemy_list",
    "spawner_id",
)
# The installed ParamRealType enum and current LevelData payloads expose two
# valid enemy-list encodings: an empty entity-reference value and a populated
# ScriptEntityPtrList.  Keep this shape rule independent of any level, script,
# module, or enemy id.
ENCOUNTER_EMPTY_ENEMY_VALUE_TYPE = 14
ENCOUNTER_POPULATED_ENEMY_LIST_VALUE_TYPE = 61
ENCOUNTER_RUNTIME_TYPE = "Beyond.Gameplay.Core.EncounterBase<T>"
ENCOUNTER_DATA_TYPE = "Beyond.Gameplay.EncounterData"
ENCOUNTER_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
ENCOUNTER_METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
DEFAULT_PIPELINE_INDEX = ROOT / "webui" / "data" / "mission_pipeline" / "index.json"
DEFAULT_PIPELINE_MISSION_ROOT = (
    ROOT / "webui" / "data" / "mission_pipeline" / "missions"
)
DEFAULT_JSON = STORY_RECOVERY_REPORTS_DIR / "native_receiver_activation_frontier.json"
DEFAULT_MARKDOWN = STORY_RECOVERY_REPORTS_DIR / "native_receiver_activation_frontier.md"
DEFAULT_MISSION_AREA_TABLE = GAMEPLAY_CONFIG_DIR / "MissionAreaTable.json"
DEFAULT_LEVEL_BASIC_INFO_TABLE = GAMEPLAY_CONFIG_DIR / "LevelBasicInfoTable.json"
DEFAULT_SCRIPT_TASK_EXTRA_INFO_TABLE = (
    GAMEPLAY_CONFIG_DIR / "ScriptTaskExtraInfoTable.json"
)
DEFAULT_WORLD_ENTITY_REGISTRY = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
DEFAULT_SUBGAME_TABLE = GAMEPLAY_CONFIG_DIR / "SubGameInstanceDataTable.json"
DEFAULT_GAME_MECHANIC_CONDITION_TABLE = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Table"
    / "GameMechanicConditionTable.json"
)
DEFAULT_DUNGEON_TABLE = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Table"
    / "DungeonTable.json"
)
DEFAULT_STRUCTURED_JSON_ROOT = MRA_DIR.parent
STRUCTURED_SCRIPT_IDENTITY_KEYS = frozenset({
    "scriptId",
    "scriptIdGlobal",
    "bindScriptId",
    "_scriptId",
    "levelScriptId",
    "targetScriptId",
})
STRUCTURED_MISSION_IDENTITY_KEYS = frozenset({
    "missionId",
    "questId",
    "_missionId",
    "_questId",
    "dungeonMissionId",
})


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _story_order_keys(story_order: dict[str, Any]) -> set[str]:
    """Read only exact Story node keys from a published order row."""
    return {
        safe_text(node if isinstance(node, str) else node.get("key"))
        for node in story_order.get("nodes") or []
        if (isinstance(node, str) and safe_text(node))
        or (isinstance(node, dict) and safe_text(node.get("key")))
    }


def _receiver_related_files(row: dict[str, Any]) -> list[dict[str, str]]:
    """Keep the exact original-file evidence attached to a compact context row."""
    related: dict[tuple[str, str], dict[str, str]] = {}
    for item in row.get("relatedOriginalFiles") or []:
        if not isinstance(item, dict):
            continue
        source_file = safe_text(item.get("sourceFile"))
        if not source_file:
            continue
        normalized = source_file.replace("\\", "/")
        related[(normalized, safe_text(item.get("relationship")))] = {
            "kind": safe_text(item.get("kind")),
            "sourceFile": normalized,
            "relationship": safe_text(item.get("relationship")),
            "sha256": safe_text(item.get("sha256")),
        }
    return [
        related[key]
        for key in sorted(related)
    ]


def _receiver_native_evidence_context(row: dict[str, Any]) -> dict[str, Any]:
    """Compact the binary-validated receiver contract for mission-card display."""
    levelscript = row.get("levelScript") or {}
    active = row.get("activePhaseReceiverControl") or {}
    request = row.get("clientActiveRequestControl") or {}
    start_policy = row.get("startRuntimePolicy") or {}
    teleport_rows = [
        {
            "schema": safe_text(item.get("schema")),
            "mappingId": safe_text(item.get("mappingId")),
            "listenerHeaderLocalId": item.get("listenerHeaderLocalId"),
            "actionIdFilter": safe_text(item.get("actionIdFilter")),
            "classification": safe_text(item.get("classification")),
            "rawCorpusOccurrenceCount": item.get("rawCorpusOccurrenceCount"),
            "externalSerializedOccurrenceCount": item.get(
                "externalSerializedOccurrenceCount"
            ),
            "serializedActionCandidateCount": item.get(
                "serializedActionCandidateCount"
            ),
            "corpusFileCount": item.get("corpusFileCount"),
            "corpusListenerCount": item.get("corpusListenerCount"),
            "corpusDistinctFilterCount": item.get("corpusDistinctFilterCount"),
            "carrierAudit": item.get("carrierAudit") or {},
            "producerEdge": False,
            "orderEvidence": False,
            "evidenceBoundary": safe_text(item.get("evidenceBoundary")),
        }
        for item in row.get("teleportFinishCorrelations") or []
        if isinstance(item, dict)
    ]
    active_shape = levelscript.get("activeShapeList") or {}
    headers = [
        {
            "listenerHeaderLocalId": header.get("listenerHeaderLocalId"),
            "headerName": safe_text(header.get("headerName")),
            "triggerActiveDuring": header.get("triggerActiveDuring"),
            "nextActionLocalId": header.get("nextActionLocalId"),
        }
        for header in active.get("receiverHeaders") or []
        if isinstance(header, dict)
    ]
    return {
        "levelScript": {
            "scriptIdVerified": bool(levelscript.get("scriptIdVerified")),
            "serializedMemberCount": levelscript.get("serializedMemberCount"),
            "actionMapRecordCount": levelscript.get("actionMapRecordCount"),
            "startTypeName": safe_text(levelscript.get("startTypeName")),
            "endTypeName": safe_text(
                (active_shape.get("followingFields") or {}).get("endTypeName")
            ),
            "activeShapeListStatus": safe_text(
                levelscript.get("activeShapeListStatus")
            ),
            "activeShapeListCount": levelscript.get("activeShapeListCount"),
            "taskMapStatus": safe_text(levelscript.get("taskMapStatus")),
            "taskMapCount": levelscript.get("taskMapCount"),
        },
        "activePhaseReceiver": {
            "schema": safe_text(active.get("schema")),
            "status": safe_text(active.get("status")),
            "classification": safe_text(active.get("classification")),
            "allReceiversActivePhase": bool(
                active.get("allReceiversActivePhase")
            ),
            "listenerHeaderCount": active.get("listenerHeaderCount"),
            "resolvedHeaderCount": active.get("resolvedHeaderCount"),
            "receiverHeaders": headers,
            "topologySchema": safe_text(active.get("topologySchema")),
            "topologyStatus": safe_text(active.get("topologyStatus")),
            "runtimeFlow": {
                key: active.get("runtimeFlow", {}).get(key)
                for key in (
                    "setupRegisterTriggerCallCount",
                    "setupRegisterTriggerCallOffsets",
                    "activePhaseEnableCallOffsets",
                    "activeBeginStateValue",
                    "activeBeginSetterOffsets",
                    "activePhaseEnableBetweenStateSetters",
                )
                if active.get("runtimeFlow", {}).get(key) not in (None, [], {})
            },
        },
        "clientActiveRequest": {
            "schema": safe_text(request.get("schema")),
            "status": safe_text(request.get("status")),
            "classification": safe_text(request.get("classification")),
            "levelScriptType": request.get("levelScriptType"),
            "levelScriptTypeName": safe_text(request.get("levelScriptTypeName")),
            "clientProducesActiveRequest": bool(
                request.get("clientProducesActiveRequest")
            ),
            "requiresActiveAreaGate": bool(request.get("requiresActiveAreaGate")),
            "entryPublicState": request.get("entryPublicState"),
            "spatialGateStatus": safe_text(request.get("spatialGateStatus")),
            "runtimePath": [
                safe_text(value)
                for value in request.get("runtimePath") or []
                if safe_text(value)
            ],
        },
        "startRuntimePolicy": {
            "schema": safe_text(start_policy.get("schema")),
            "classification": safe_text(start_policy.get("classification")),
            "validation": (start_policy.get("validation") or {}).get("status"),
        },
        "teleportFinishCorrelations": teleport_rows,
        "binaryBoundary": safe_text(
            active.get("evidenceBoundary")
            or request.get("evidenceBoundary")
            or start_policy.get("evidenceBoundary")
        ),
    }


def _receiver_story_context(
    row: dict[str, Any],
    mission_id: str,
    mission_story_keys: set[str],
) -> dict[str, Any] | None:
    """Project one exact receiver/Story intersection without promoting ownership."""
    story_keys = {
        safe_text(key) for key in row.get("storyKeys") or [] if safe_text(key)
    }
    matched = story_keys & mission_story_keys
    if not matched:
        return None
    level_id = safe_text(row.get("levelId"))
    script_id = safe_text(row.get("scriptId"))
    if not level_id or not script_id:
        return None
    return {
        "relation": "native_receiver_story_context",
        "missionId": mission_id,
        "levelId": level_id,
        "scriptId": script_id,
        "storyKeys": sorted(story_keys),
        "missionStoryKeys": sorted(matched),
        "externalStoryKeys": sorted(story_keys - mission_story_keys),
        "storyKinds": sorted({
            safe_text(kind)
            for kind in row.get("storyKinds") or []
            if safe_text(kind)
        }),
        "eventNames": sorted({
            safe_text(name)
            for name in row.get("eventNames") or []
            if safe_text(name)
        }),
        "listenerHeaderLocalIds": sorted({
            value
            for value in row.get("listenerHeaderLocalIds") or []
            if isinstance(value, int)
        }),
        "activationClass": safe_text(row.get("activationClass")),
        "missionOwnerStatus": safe_text(row.get("missionOwnerStatus")),
        "receiverEvidence": _receiver_native_evidence_context(row),
        "ownership": False,
        "activation": False,
        "storyPlayback": False,
        "orderEvidence": False,
        "relatedOriginalFiles": _receiver_related_files(row),
        "evidenceBoundary": (
            "The original LevelScript receiver row has an exact native path to "
            "the listed Story keys, and those keys intersect this mission's "
            "published Story nodes. The attached binary-backed receiver contract "
            "proves availability/control shape only; it does not prove the mission "
            "selected activation, event firing, ownership, branch choice, or "
            "inter-Story order."
        ),
    }


def _receiver_story_context_index(
    report: dict[str, Any],
) -> dict[str, Any]:
    """Build a compact Story-key index for every exact receiver placement.

    This is a presentation join only.  It is keyed by the serialized
    ``(levelId, scriptId, storyKey)`` shape recovered from native receiver
    rows, never by a hand-maintained Story/object list.  The index keeps the
    exact source files and binary boundary beside unassigned Story cards while
    explicitly retaining the unresolved ownership/order status.
    """
    contexts: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in report.get("rows") or []:
        if not isinstance(row, dict):
            continue
        level_id = safe_text(row.get("levelId"))
        script_id = safe_text(row.get("scriptId"))
        if not level_id or not script_id:
            continue
        story_keys = sorted({
            safe_text(key)
            for key in row.get("storyKeys") or []
            if safe_text(key)
        })
        if not story_keys:
            continue
        related_files = _receiver_related_files(row)
        context_boundary = (
            "The exact serialized native receiver path and activation-frontier "
            "files are attached for this Story key. They prove receiver "
            "availability/control shape only; they do not prove mission or "
            "quest ownership, event firing, branch selection, or Story order."
        )
        for story_key in story_keys:
            key = (story_key, level_id, script_id)
            context = contexts.setdefault(
                key,
                {
                    "relation": "native_receiver_story_context",
                    "storyKey": story_key,
                    "levelId": level_id,
                    "scriptId": script_id,
                    "storyKinds": [],
                    "eventNames": [],
                    "listenerHeaderLocalIds": [],
                    "receiverNodeCount": 0,
                    "receiverToStoryPlacementCount": 0,
                    "activationClass": safe_text(row.get("activationClass")),
                    "missionOwnerStatus": safe_text(
                        row.get("missionOwnerStatus")
                    ) or "unresolved",
                    "relatedOriginalFiles": related_files,
                    "ownership": False,
                    "activation": False,
                    "storyPlayback": False,
                    "orderEvidence": False,
                    "evidenceBoundary": context_boundary,
                },
            )
            context["storyKinds"] = sorted({
                *context.get("storyKinds", []),
                *(
                    safe_text(kind)
                    for kind in row.get("storyKinds") or []
                    if safe_text(kind)
                ),
            })
            context["eventNames"] = sorted({
                *context.get("eventNames", []),
                *(
                    safe_text(name)
                    for name in row.get("eventNames") or []
                    if safe_text(name)
                ),
            })
            context["listenerHeaderLocalIds"] = sorted({
                *context.get("listenerHeaderLocalIds", []),
                *(
                    value
                    for value in row.get("listenerHeaderLocalIds") or []
                    if isinstance(value, int)
                ),
            })
            context["receiverNodeCount"] += int(
                row.get("receiverNodeCount") or 0
            )
            context["receiverToStoryPlacementCount"] += int(
                row.get("receiverToStoryPlacementCount") or 0
            )
            file_map = {
                (
                    safe_text(item.get("sourceFile")),
                    safe_text(item.get("sha256")),
                ): item
                for item in context.get("relatedOriginalFiles") or []
                if isinstance(item, dict) and safe_text(item.get("sourceFile"))
            }
            file_map.update({
                (
                    safe_text(item.get("sourceFile")),
                    safe_text(item.get("sha256")),
                ): item
                for item in related_files
                if isinstance(item, dict) and safe_text(item.get("sourceFile"))
            })
            context["relatedOriginalFiles"] = [
                file_map[file_key]
                for file_key in sorted(file_map)
            ]

    rows = [contexts[key] for key in sorted(contexts)]
    return {
        "schema": "nativeReceiverStoryContextIndex.v1",
        "rows": rows,
        "counts": {
            "storyKeys": len({row["storyKey"] for row in rows}),
            "contextRows": len(rows),
            "relatedOriginalFiles": len({
                (
                    safe_text(item.get("sourceFile")),
                    safe_text(item.get("sha256")),
                )
                for row in rows
                for item in row.get("relatedOriginalFiles") or []
                if isinstance(item, dict) and safe_text(item.get("sourceFile"))
            }),
        },
        "evidenceBoundary": (
            "This index joins exact serialized native receiver placements to "
            "their Story keys for inspection. It is non-owning context: no row "
            "adds mission ownership, activation, branch, completion, or Story "
            "order evidence."
        ),
        "usesOcrOrManualOrder": False,
    }


def _original_file_kind(source_file: str) -> str:
    normalized = source_file.replace("\\", "/")
    for marker, kind in (
        ("/LevelScriptData/", "levelscript"),
        ("/LevelData/", "leveldata"),
        ("/MissionRuntimeAsset/", "mission_runtime"),
        ("/SpawnerConfigData/", "spawner_config"),
        ("/SpawnerConfig/", "spawner_config"),
        ("/GameplayConfig/", "gameplay_config"),
        ("/Table/", "table"),
    ):
        if marker in normalized:
            return kind
    return "original_game_data"


_SOURCE_FILE_HASH_CACHE: dict[Path, str] = {}


def _source_file_sha256(source_file: str) -> str:
    """Hash an exported original-data path when it is present.

    Receiver reports are also used with reduced fixture corpora, so a missing
    fixture path remains a context row with an empty hash rather than making
    publication fail.  The root and export boundary are explicit; arbitrary
    WebUI or scratch paths are never treated as original bytes.
    """
    normalized = safe_text(source_file).replace("\\", "/")
    if not normalized.startswith("export_full/"):
        return ""
    path = (ROOT / Path(normalized)).resolve()
    export_root = (ROOT / "export_full").resolve()
    if not path.is_file() or not path.is_relative_to(export_root):
        return ""
    cached = _SOURCE_FILE_HASH_CACHE.get(path)
    if cached:
        return cached
    digest = hashlib.sha256(read_bytes_cached(path)).hexdigest()
    _SOURCE_FILE_HASH_CACHE[path] = digest
    return digest


def collect_related_original_files(*values: Any) -> list[dict[str, str]]:
    """Collect exact original-data sources from nested evidence structures."""
    paths: set[str] = set()

    def walk(value: Any, field: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, safe_text(key))
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                walk(item, field)
            return
        if not isinstance(value, str):
            return
        path = safe_text(value).replace("\\", "/")
        if (
            path.startswith("export_full/")
            and field.lower() in {
                "source",
                "sourcefile",
                "sourcefiles",
                "registrysourcefile",
            }
        ):
            paths.add(path)

    for value in values:
        walk(value)
    return [
        {
            "kind": _original_file_kind(path),
            "sourceFile": path,
            "relationship": "exact_typed_activation_frontier_context",
            **(
                {"sha256": digest}
                if (digest := _source_file_sha256(path))
                else {}
            ),
        }
        for path in sorted(paths)
    ]


def teleport_finish_runtime_contract(
    index_payload: dict[str, Any],
) -> dict[str, Any]:
    """Bind the generic listener correlation rule to reviewed original binaries."""
    runtime_contracts = index_payload.get("runtimeContract") or {}
    activation = (
        runtime_contracts.get(
            "levelScriptActivationControlAudit"
        )
        or {}
    )
    teleport_param = runtime_contracts.get("teleportMissionScriptCarrier") or {}
    native_rows = [
        row
        for row in runtime_contracts.get("nativeEvidence") or []
        if isinstance(row, dict)
        and safe_text(row.get("symbol"))
        == "LevelEvent.OnTeleportFinish.Process"
    ]
    carrier_related = [
        item for item in teleport_param.get("relatedOriginalFiles") or []
        if isinstance(item, dict)
        and safe_text(item.get("sourceFile"))
        and safe_text(item.get("sha256"))
    ]
    related = [
        {
            **item,
            "relationship": "native_teleport_finish_correlation_authority",
        }
        for item in (
            carrier_related or activation.get("relatedOriginalFiles") or []
        )
        if isinstance(item, dict)
        and safe_text(item.get("sourceFile"))
        and safe_text(item.get("sha256"))
    ]
    game_rows = [
        row for row in related
        if safe_text(row.get("sourceFile")).lower().endswith("gameassembly.dll")
    ]
    metadata_rows = [
        row for row in related
        if safe_text(row.get("sourceFile")).lower().endswith(
            "global-metadata.dat"
        )
    ]
    failures: list[dict[str, Any]] = []
    checks = (
        (
            "reviewedGameAssembly",
            game_rows,
            TELEPORT_FINISH_RUNTIME_CONTRACT["gameAssemblySha256"],
        ),
        (
            "reviewedGlobalMetadata",
            metadata_rows,
            TELEPORT_FINISH_RUNTIME_CONTRACT["globalMetadataSha256"],
        ),
    )
    for gate, rows, expected_hash in checks:
        hashes = sorted({safe_text(row.get("sha256")).lower() for row in rows})
        if len(rows) != 1 or hashes != [expected_hash]:
            failures.append({
                "validator": "teleport_finish_runtime_contract",
                "gate": gate,
                "sourceFile": safe_text((rows or [{}])[0].get("sourceFile")),
                "expected": {
                    "sourceCount": 1,
                    "sha256": expected_hash,
                },
                "actual": {
                    "sourceCount": len(rows),
                    "sha256": hashes,
                },
                "sourceHashes": hashes,
            })
    if (activation.get("validation") or {}).get("status") != "validated":
        failures.append({
            "validator": "teleport_finish_runtime_contract",
            "gate": "sourceRuntimeAuditValidated",
            "sourceFile": safe_text(activation.get("source")),
            "expected": "validated",
            "actual": (activation.get("validation") or {}).get("status"),
            "sourceHashes": sorted({
                safe_text(row.get("sha256")).lower() for row in related
            }),
        })
    teleport_shape = {
        "type": teleport_param.get("type"),
        "actionIdOffset": (teleport_param.get("layout") or {}).get("actionId"),
        "auditSchema": teleport_param.get("auditSchema"),
        "auditValidation": (teleport_param.get("validation") or {}).get("status"),
        "metadataSignatureMethodCount": teleport_param.get(
            "metadataSignatureMethodCount"
        ),
        "containerPathCount": teleport_param.get("containerPathCount"),
        "focusFieldAccessCount": teleport_param.get("focusFieldAccessCount"),
        "storyBindingsAdded": teleport_param.get("storyBindingsAdded"),
    }
    expected_teleport_shape = {
        "type": "Beyond.Gameplay.TeleportParam",
        "actionIdOffset": "0x28",
        "auditSchema": "nativeValueCarrierAudit.v1",
        "auditValidation": "validated",
        "metadataSignatureMethodCount": 15,
        "containerPathCount": 10,
        "focusFieldAccessCount": 23,
        "storyBindingsAdded": 0,
    }
    if teleport_shape != expected_teleport_shape:
        failures.append({
            "validator": "teleport_finish_runtime_contract",
            "gate": "typedTeleportParamActionIdCarrier",
            "sourceFile": safe_text(activation.get("source")),
            "expected": expected_teleport_shape,
            "actual": teleport_shape,
            "sourceHashes": sorted({
                safe_text(row.get("sha256")).lower() for row in related
            }),
        })
    expected_native_row = {
        "symbol": "LevelEvent.OnTeleportFinish.Process",
        "address": TELEPORT_FINISH_RUNTIME_CONTRACT[
            "listenerProcessMethodVa"
        ],
    }
    actual_native_rows = [
        {
            "symbol": safe_text(row.get("symbol")),
            "address": safe_text(row.get("address")),
        }
        for row in native_rows
    ]
    if actual_native_rows != [expected_native_row]:
        failures.append({
            "validator": "teleport_finish_runtime_contract",
            "gate": "typedListenerRuntimeComparison",
            "sourceFile": safe_text(activation.get("source")),
            "expected": [expected_native_row],
            "actual": actual_native_rows,
            "sourceHashes": sorted({
                safe_text(row.get("sha256")).lower() for row in related
            }),
        })
    return {
        "schema": "teleportFinishRuntimeContract.v1",
        **TELEPORT_FINISH_RUNTIME_CONTRACT,
        "classification": "runtime_action_id_correlation",
        "teleportParamCarrier": teleport_param,
        "listenerNativeEvidence": native_rows[0] if len(native_rows) == 1 else {},
        "relatedOriginalFiles": related,
        "validation": {
            "status": "validation_failed" if failures else "validated",
            "failures": failures,
        },
        "evidenceBoundary": (
            "The reviewed client binary proves that OnTeleportFinish compares "
            "its serialized actionId filter with the TeleportParam actionId "
            "published at runtime. The generic carrier audit finds no nonzero direct "
            "AOT originator for that field. It does not prove that an indirect, "
            "reflected, XLua, or live-server path supplied the value, that the event "
            "fired, mission ownership, or order."
        ),
    }


def build_teleport_finish_correlation_census(
    levelscript_root: Path,
    runtime_contract: dict[str, Any],
    *,
    topology_decoder: Any = decode_levelscript_native_action_topology,
) -> dict[str, Any]:
    """Correlate every typed teleport-finish filter across the complete corpus.

    Discovery uses only typed event records and exact serialized bytes.  Known
    Story keys, missions, scripts, filters, filenames, OCR, and overrides are
    not inputs.  Exact action UID/text matches are surfaced as candidates but
    never promoted to producer or order edges without a typed runtime relation.
    """
    files = sorted(levelscript_root.glob("*/*.json"))
    raw_hex_counts: Counter[str] = Counter()
    listeners: list[dict[str, Any]] = []
    action_candidates: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = (
        defaultdict(dict)
    )
    failures: list[dict[str, Any]] = []
    decoded_files = 0
    physical_record_count = 0

    if not files:
        failures.append({
            "validator": "teleport_finish_levelscript_corpus",
            "gate": "nonemptyOriginalLevelScriptCorpus",
            "sourceFile": rel_path(levelscript_root),
            "expected": {"candidateFileCountGreaterThan": 0},
            "actual": {"candidateFileCount": 0},
            "sourceHashes": {},
        })

    for path in files:
        source_file = rel_path(path)
        try:
            data = read_bytes_cached(path)
        except OSError as exc:
            failures.append({
                "validator": "teleport_finish_levelscript_corpus",
                "gate": "readOriginalLevelScript",
                "sourceFile": source_file,
                "expected": "readable original LevelScript bytes",
                "actual": type(exc).__name__,
                "sourceHashes": {},
            })
            continue
        raw_hex_counts.update(
            match.group(1).decode("ascii")
            for match in TELEPORT_FINISH_FILTER_BYTES_RE.finditer(data)
        )
        topology, diagnostic = topology_decoder(data)
        status = safe_text((topology or {}).get("status"))
        if diagnostic or not status.startswith("exact_"):
            failures.append({
                "validator": "teleport_finish_levelscript_corpus",
                "gate": "completeTypedActionTopology",
                "sourceFile": source_file,
                "expected": "exact_* topology status with no diagnostic",
                "actual": {
                    "status": status,
                    "diagnostic": diagnostic,
                },
                "sourceHashes": {"sha256": hashlib.sha256(data).hexdigest()},
            })
            continue
        decoded_files += 1
        physical_record_count += int(
            (topology or {}).get("physicalActionRecordCount") or 0
        ) + int((topology or {}).get("physicalHeaderRecordCount") or 0)

        for action in (topology or {}).get("actions") or []:
            if not isinstance(action, dict):
                continue
            identities = [("uid", safe_text(action.get("uid")))]
            identities.extend(
                ("literal", safe_text(value))
                for value in action.get("texts") or []
            )
            for field, value in identities:
                if not TELEPORT_FINISH_FILTER_RE.fullmatch(value):
                    continue
                candidate = {
                    "sourceFile": source_file,
                    "recordOffset": action.get("recordOffset"),
                    "localId": action.get("localId"),
                    "actionName": safe_text(action.get("actionName")),
                    "matchField": field,
                    "value": value,
                }
                key = (
                    source_file,
                    action.get("recordOffset"),
                    field,
                    value,
                )
                action_candidates[value][key] = candidate

        level_id = path.parent.name
        script_id = path.stem
        for event in (topology or {}).get("eventRoots") or []:
            if (
                not isinstance(event, dict)
                or safe_text(event.get("headerName"))
                != TELEPORT_FINISH_EVENT_TYPE
            ):
                continue
            event_detail = event.get("eventDetail") or {}
            action_id_filter = safe_text(event_detail.get("actionIdFilter"))
            if not TELEPORT_FINISH_FILTER_RE.fullmatch(action_id_filter):
                failures.append({
                    "validator": "teleport_finish_levelscript_corpus",
                    "gate": "typedListenerHasExactActionIdFilter",
                    "identity": f"{level_id}/{script_id}#{event.get('localId')}",
                    "sourceFile": source_file,
                    "expected": "one lowercase eight-hex actionId filter",
                    "actual": action_id_filter,
                    "sourceHashes": {
                        "sha256": hashlib.sha256(data).hexdigest()
                    },
                })
                continue
            listeners.append({
                "levelId": level_id,
                "scriptId": script_id,
                "listenerHeaderLocalId": event.get("localId"),
                "recordOffset": event.get("recordOffset"),
                "headerUid": safe_text(event.get("uid")),
                "actionIdFilter": action_id_filter,
                "sourceFile": source_file,
                "sha256": hashlib.sha256(data).hexdigest(),
            })

    listeners_by_filter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in listeners:
        listeners_by_filter[row["actionIdFilter"]].append(row)

    filter_rows: list[dict[str, Any]] = []
    for value in sorted(listeners_by_filter):
        filter_listeners = listeners_by_filter[value]
        self_header_uid_count = sum(
            row.get("headerUid") == value for row in filter_listeners
        )
        raw_count = raw_hex_counts[value]
        expected_listener_owned = len(filter_listeners) + self_header_uid_count
        external_count = raw_count - expected_listener_owned
        candidates = list(action_candidates.get(value, {}).values())
        if external_count < 0:
            failures.append({
                "validator": "teleport_finish_levelscript_corpus",
                "gate": "listenerOwnedRawOccurrenceAccounting",
                "identity": value,
                "sourceFile": filter_listeners[0]["sourceFile"],
                "expected": {
                    "rawOccurrenceCountAtLeast": expected_listener_owned,
                },
                "actual": {"rawOccurrenceCount": raw_count},
                "sourceHashes": {
                    row["sourceFile"]: row["sha256"]
                    for row in filter_listeners
                },
            })
        if len(candidates) > max(0, external_count):
            failures.append({
                "validator": "teleport_finish_levelscript_corpus",
                "gate": "actionCandidateRawOccurrenceAccounting",
                "identity": value,
                "sourceFile": candidates[0]["sourceFile"],
                "expected": {
                    "serializedActionCandidateCountAtMost": max(
                        0, external_count
                    ),
                },
                "actual": {
                    "serializedActionCandidateCount": len(candidates),
                },
                "sourceHashes": {
                    row["sourceFile"]: row["sha256"]
                    for row in filter_listeners
                },
            })
        if candidates:
            classification = "serialized_action_identity_candidate"
        elif external_count > 0:
            classification = "serialized_non_action_occurrence_unclassified"
        else:
            classification = "runtime_only_no_serialized_levelscript_producer"
        filter_rows.append({
            "actionIdFilter": value,
            "classification": classification,
            "listenerCount": len(filter_listeners),
            "selfHeaderUidOccurrenceCount": self_header_uid_count,
            "rawCorpusOccurrenceCount": raw_count,
            "externalSerializedOccurrenceCount": max(0, external_count),
            "serializedActionCandidateCount": len(candidates),
            "serializedActionCandidates": candidates,
            "listeners": filter_listeners,
            "producerEdge": False,
            "orderEvidence": False,
            "evidenceBoundary": (
                "An exact serialized action UID/text match is only a candidate; "
                "without a typed producer-to-TeleportParam relation it creates no "
                "event, mission, branch, or order edge."
                if candidates or external_count > 0
                else "The filter occurs only in its typed listener field (plus "
                "an explicitly accounted same-header UID where present). The "
                "complete current LevelScript corpus contains no serialized "
                "producer, so the runtime actionId carrier remains unresolved."
            ),
        })

    runtime_validation = runtime_contract.get("validation") or {}
    failures.extend(runtime_validation.get("failures") or [])
    return {
        "schema": "teleportFinishCorrelationCensus.v1",
        "mappingId": TELEPORT_FINISH_CORRELATION_MAPPING_ID,
        "runtimeContract": runtime_contract,
        "candidateFileCount": len(files),
        "decodedFileCount": decoded_files,
        "physicalActionAndHeaderRecordCount": physical_record_count,
        "listenerCount": len(listeners),
        "distinctFilterCount": len(filter_rows),
        "filtersWithSerializedActionCandidate": sum(
            bool(row["serializedActionCandidateCount"]) for row in filter_rows
        ),
        "serializedActionCandidateCount": sum(
            row["serializedActionCandidateCount"] for row in filter_rows
        ),
        "externalSerializedOccurrenceCount": sum(
            row["externalSerializedOccurrenceCount"] for row in filter_rows
        ),
        "runtimeOnlyFilterCount": sum(
            row["classification"]
            == "runtime_only_no_serialized_levelscript_producer"
            for row in filter_rows
        ),
        "selfHeaderUidOccurrenceCount": sum(
            row["selfHeaderUidOccurrenceCount"] for row in filter_rows
        ),
        "filters": filter_rows,
        "validation": {
            "status": "validation_failed" if failures else "validated",
            "failures": failures,
            "checkedFileCount": len(files),
            "decodedFileCount": decoded_files,
        },
        "discoveryPattern": {
            "eventType": TELEPORT_FINISH_EVENT_TYPE,
            "filterField": "eventDetail.actionIdFilter",
            "correlationFields": ["action.uid", "action.texts", "exact raw bytes"],
            "serializedObjectInputs": [],
            "storyMissionOrObjectAllowlists": [],
        },
        "evidenceBoundary": (
            "This corpus census can close serialized LevelScript producers for "
            "an exact runtime correlation key. It never converts name proximity, "
            "raw occurrence, action identity, OCR, or overrides into playback, "
            "branch, mission ownership, or Story-order evidence."
        ),
    }


def teleport_finish_receiver_contexts(
    census: dict[str, Any],
) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Index corpus results by the exact typed listener identity."""
    contexts: dict[tuple[str, str, int], dict[str, Any]] = {}
    carrier = (census.get("runtimeContract") or {}).get(
        "teleportParamCarrier"
    ) or {}
    action_field = (carrier.get("focusFieldSummary") or {}).get("actionId") or {}
    for filter_row in census.get("filters") or []:
        if not isinstance(filter_row, dict):
            continue
        for listener in filter_row.get("listeners") or []:
            if not isinstance(listener, dict):
                continue
            header_id = listener.get("listenerHeaderLocalId")
            if not isinstance(header_id, int):
                continue
            key = (
                safe_text(listener.get("levelId")),
                safe_text(listener.get("scriptId")),
                header_id,
            )
            contexts[key] = {
                "schema": safe_text(census.get("schema")),
                "mappingId": safe_text(census.get("mappingId")),
                "actionIdFilter": safe_text(filter_row.get("actionIdFilter")),
                "classification": safe_text(filter_row.get("classification")),
                "rawCorpusOccurrenceCount": filter_row.get(
                    "rawCorpusOccurrenceCount"
                ),
                "externalSerializedOccurrenceCount": filter_row.get(
                    "externalSerializedOccurrenceCount"
                ),
                "serializedActionCandidateCount": filter_row.get(
                    "serializedActionCandidateCount"
                ),
                "corpusFileCount": census.get("candidateFileCount"),
                "corpusListenerCount": census.get("listenerCount"),
                "corpusDistinctFilterCount": census.get("distinctFilterCount"),
                "carrierAudit": {
                    "schema": safe_text(carrier.get("auditSchema")),
                    "reportJson": safe_text(carrier.get("auditReport")),
                    "signatureMethodCount": carrier.get(
                        "metadataSignatureMethodCount"
                    ),
                    "containerPathCount": carrier.get("containerPathCount"),
                    "focusFieldAccessCount": carrier.get(
                        "focusFieldAccessCount"
                    ),
                    "directCallsiteCount": sum(
                        int(value or 0)
                        for value in (carrier.get("directCallerCensus") or {}).values()
                    ),
                    "actionIdZeroWriteAccesses": action_field.get(
                        "zeroWriteAccesses"
                    ),
                    "actionIdUnknownCopyAccesses": action_field.get(
                        "unknownWriteAccesses"
                    ),
                    "actionIdInitializerStates": action_field.get(
                        "directCallInitializerStates"
                    ) or {},
                    "producerFinding": safe_text(carrier.get("producerFinding")),
                    "consumerFinding": safe_text(carrier.get("consumerFinding")),
                    "validationStatus": safe_text(
                        (carrier.get("validation") or {}).get("status")
                    ),
                },
                "producerEdge": False,
                "orderEvidence": False,
                "evidenceBoundary": safe_text(
                    filter_row.get("evidenceBoundary")
                ),
            }
    return contexts


def validate_mission_area_leveldata_shell_contexts(
    receiver_pairs: set[tuple[str, str]],
    contexts: dict[tuple[str, str], dict[str, Any]],
    authored_mission_ids: set[str],
) -> dict[str, Any]:
    """Fail closed on malformed typed MissionArea/LevelData shell joins.

    The shared level-binding helper discovers candidates by field shape.  This
    validator independently checks every emitted identity, complete mission
    union, source row, and unique/shared classification before the contexts
    can be published beside Mission Pipeline Story rows.
    """
    validator = "native_receiver_mission_area_leveldata_shell"
    failures: list[dict[str, Any]] = []

    def fail(
        gate: str,
        identity: str,
        expected: Any,
        actual: Any,
        source_file: str = "",
        source_hashes: dict[str, str] | None = None,
    ) -> None:
        failures.append({
            "validator": validator,
            "gate": gate,
            "identity": identity,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
            "sourceHashes": source_hashes or {},
        })

    for pair, context in sorted(contexts.items()):
        level_id, script_id = pair
        identity = f"{level_id}/{script_id}"
        if pair not in receiver_pairs:
            fail(
                "receiverIdentity",
                identity,
                "exact unresolved native receiver pair",
                pair,
            )
        if (
            safe_text(context.get("levelId")) != level_id
            or safe_text(context.get("scriptId")) != script_id
        ):
            fail(
                "contextIdentity",
                identity,
                {"levelId": level_id, "scriptId": script_id},
                {
                    "levelId": context.get("levelId"),
                    "scriptId": context.get("scriptId"),
                },
            )

        mission_ids = sorted({
            safe_text(value)
            for value in context.get("hostMissionIds") or []
            if safe_text(value)
        })
        unknown_missions = sorted(set(mission_ids) - authored_mission_ids)
        if not mission_ids or unknown_missions:
            fail(
                "authoredMissionSet",
                identity,
                "one or more current MissionRuntime ids",
                {
                    "hostMissionIds": mission_ids,
                    "unknownMissionIds": unknown_missions,
                },
            )
        expected_status = "unique" if len(mission_ids) == 1 else "shared"
        if safe_text(context.get("status")) != expected_status:
            fail(
                "scopeClassification",
                identity,
                expected_status,
                context.get("status"),
            )

        hosts = [
            host for host in context.get("hosts") or []
            if isinstance(host, dict)
        ]
        if not hosts:
            fail("hostRows", identity, "at least one exact LevelData host", 0)
            continue
        host_mission_union: set[str] = set()
        for host_index, host in enumerate(hosts):
            source_file = safe_text(host.get("levelDataFile"))
            host_identity = f"{identity}#host[{host_index}]"
            source_hash = _source_file_sha256(source_file)
            if not source_file or not source_hash:
                fail(
                    "levelDataSourceHash",
                    host_identity,
                    "existing exported original LevelData with SHA-256",
                    source_file or "[missing]",
                    source_file,
                )
            if (
                safe_text(host.get("levelId")) != level_id
                or safe_text(host.get("scriptId")) != script_id
            ):
                fail(
                    "hostIdentity",
                    host_identity,
                    {"levelId": level_id, "scriptId": script_id},
                    {
                        "levelId": host.get("levelId"),
                        "scriptId": host.get("scriptId"),
                    },
                    source_file,
                    {source_file: source_hash} if source_hash else {},
                )
            host_missions = {
                safe_text(value)
                for value in host.get("hostMissionIds") or []
                if safe_text(value)
            }
            host_mission_union.update(host_missions)
            references = [
                reference
                for reference in host.get("missionAreaReferences") or []
                if isinstance(reference, dict)
            ]
            roots = [
                safe_text(value)
                for value in host.get("rootScriptIds") or []
                if safe_text(value)
            ]
            if not references or not roots:
                fail(
                    "typedMissionAreaRootEvidence",
                    host_identity,
                    "nonempty MissionRuntime references and subDataParent roots",
                    {
                        "missionAreaReferenceCount": len(references),
                        "rootScriptIds": roots,
                    },
                    source_file,
                    {source_file: source_hash} if source_hash else {},
                )
            reference_roots = {
                safe_text(reference.get("subDataParentId"))
                for reference in references
                if safe_text(reference.get("subDataParentId"))
            }
            if reference_roots != set(roots):
                fail(
                    "levelDataRootAgreement",
                    host_identity,
                    sorted(reference_roots),
                    roots,
                    source_file,
                    {source_file: source_hash} if source_hash else {},
                )
            reference_levels = {
                safe_text(reference.get("levelId"))
                for reference in references
                if safe_text(reference.get("levelId"))
            }
            reference_level_nums = {
                safe_text(reference.get("levelNum"))
                for reference in references
                if safe_text(reference.get("levelNum"))
            }
            if reference_levels != {level_id} or not reference_level_nums:
                fail(
                    "levelScopedMissionAreaSelection",
                    host_identity,
                    {
                        "levelIds": [level_id],
                        "levelNumCount": "at least one",
                    },
                    {
                        "levelIds": sorted(reference_levels),
                        "levelNums": sorted(reference_level_nums),
                    },
                    source_file,
                    {source_file: source_hash} if source_hash else {},
                )
            reference_source_files = sorted({
                safe_text(reference.get(field_name))
                for reference in references
                for field_name in (
                    "sourceFile",
                    "missionAreaSourceFile",
                    "levelBasicInfoSourceFile",
                )
                if safe_text(reference.get(field_name))
            })
            reference_source_hashes = {
                path: _source_file_sha256(path)
                for path in reference_source_files
            }
            missing_reference_hashes = sorted(
                path
                for path, digest in reference_source_hashes.items()
                if not digest
            )
            if (
                len(reference_source_files) < 3
                or missing_reference_hashes
            ):
                fail(
                    "typedSourceHashes",
                    host_identity,
                    "MissionRuntime, MissionAreaTable, and LevelBasicInfoTable hashes",
                    {
                        "sourceFiles": reference_source_files,
                        "missingHashes": missing_reference_hashes,
                    },
                    source_file,
                    reference_source_hashes,
                )
            reference_missions = {
                safe_text(reference.get("missionId"))
                for reference in references
                if safe_text(reference.get("missionId"))
            }
            if reference_missions != host_missions:
                fail(
                    "hostMissionUnion",
                    host_identity,
                    sorted(reference_missions),
                    sorted(host_missions),
                    source_file,
                    {source_file: source_hash} if source_hash else {},
                )
        if host_mission_union != set(mission_ids):
            fail(
                "completeMissionUnion",
                identity,
                sorted(host_mission_union),
                mission_ids,
            )

    return {
        "status": "validation_failed" if failures else "validated",
        "validator": validator,
        "checkedReceiverPairCount": len(receiver_pairs),
        "checkedContextCount": len(contexts),
        "failures": failures,
    }


def structured_identity_cocarrier_census(
    receiver_rows: list[dict[str, Any]],
    *,
    structured_json_root: Path = DEFAULT_STRUCTURED_JSON_ROOT,
) -> dict[str, Any]:
    """Census direct authored LevelScript + mission/quest identity records.

    The scan is schema-key driven and covers every JSON file under the selected
    original structured-data root.  It admits no filename-derived identities
    and fails closed when a new direct key-pair shape appears.
    """
    receiver_ids = {
        safe_text(row.get("scriptId"))
        for row in receiver_rows
        if safe_text(row.get("scriptId"))
    }
    candidate_files = 0
    parsed_files = 0
    visited_records = 0
    parse_failures: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    key_pairs: Counter[str] = Counter()
    key_tokens = [
        f'"{key}"'.encode("utf-8")
        for key in sorted(STRUCTURED_SCRIPT_IDENTITY_KEYS)
    ]

    def scalar_values(value: Any) -> list[str]:
        if isinstance(value, bool):
            return []
        if isinstance(value, (str, int)):
            return [safe_text(value)] if safe_text(value) else []
        if isinstance(value, list):
            return sorted({
                safe_text(item)
                for item in value
                if not isinstance(item, bool)
                and isinstance(item, (str, int))
                and safe_text(item)
            })
        return []

    def walk(value: Any, path: str, source_file: str) -> None:
        nonlocal visited_records
        if isinstance(value, dict):
            visited_records += 1
            script_fields = {
                key: scalar_values(item)
                for key, item in value.items()
                if key in STRUCTURED_SCRIPT_IDENTITY_KEYS
                and scalar_values(item)
            }
            mission_fields = {
                key: scalar_values(item)
                for key, item in value.items()
                if key in STRUCTURED_MISSION_IDENTITY_KEYS
                and scalar_values(item)
            }
            if script_fields and mission_fields:
                for script_key in script_fields:
                    for mission_key in mission_fields:
                        key_pairs[f"{script_key}+{mission_key}"] += 1
                matched_receivers = sorted({
                    script_id
                    for values in script_fields.values()
                    for script_id in values
                    if script_id in receiver_ids
                })
                key_pair_set = {
                    (script_key, mission_key)
                    for script_key in script_fields
                    for mission_key in mission_fields
                }
                classification = (
                    "subgame_dungeon_mission_binding"
                    if key_pair_set == {("bindScriptId", "dungeonMissionId")}
                    else "unreviewed_direct_identity_carrier"
                )
                rows.append({
                    "sourceFile": source_file,
                    "recordPath": path,
                    "scriptFields": script_fields,
                    "missionFields": mission_fields,
                    "receiverScriptIds": matched_receivers,
                    "classification": classification,
                    "ownershipAction": (
                        "existing_subgame_binding_contract"
                        if classification == "subgame_dungeon_mission_binding"
                        else "review_required"
                    ),
                })
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else safe_text(key), source_file)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]", source_file)

    if structured_json_root.is_dir():
        for path in sorted(structured_json_root.rglob("*.json")):
            try:
                data = read_bytes_cached(path)
            except OSError as exc:
                parse_failures.append({
                    "sourceFile": rel_path(path),
                    "error": f"read failed: {exc}",
                })
                continue
            if not any(token in data for token in key_tokens):
                continue
            candidate_files += 1
            try:
                payload = json.loads(data.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                parse_failures.append({
                    "sourceFile": rel_path(path),
                    "error": f"JSON parse failed: {exc}",
                })
                continue
            parsed_files += 1
            walk(payload, "", rel_path(path))

    unreviewed = [
        row for row in rows
        if row["classification"] == "unreviewed_direct_identity_carrier"
    ]
    receiver_matches = [row for row in rows if row["receiverScriptIds"]]
    failures: list[dict[str, Any]] = []
    if not structured_json_root.is_dir():
        failures.append({
            "validator": "structured_identity_cocarrier_census",
            "gate": "structuredJsonRoot",
            "expected": "directory",
            "actual": "missing",
            "sourceFile": rel_path(structured_json_root),
        })
    if candidate_files == 0 or parsed_files == 0:
        failures.append({
            "validator": "structured_identity_cocarrier_census",
            "gate": "candidateDiscovery",
            "expected": ">=1 parsed script-identity JSON file",
            "actual": {
                "candidateFiles": candidate_files,
                "parsedFiles": parsed_files,
            },
            "sourceFile": rel_path(structured_json_root),
        })
    if parse_failures:
        failures.append({
            "validator": "structured_identity_cocarrier_census",
            "gate": "completeJsonParse",
            "expected": [],
            "actual": parse_failures,
            "sourceFile": rel_path(structured_json_root),
        })
    if unreviewed:
        failures.append({
            "validator": "structured_identity_cocarrier_census",
            "gate": "allDirectCarrierShapesReviewed",
            "expected": [],
            "actual": unreviewed,
            "sourceFile": unreviewed[0]["sourceFile"],
        })
    validation = {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }
    return {
        "schema": "structuredLevelScriptMissionIdentityCensus.v1",
        "sourceRoot": rel_path(structured_json_root),
        "scriptIdentityKeys": sorted(STRUCTURED_SCRIPT_IDENTITY_KEYS),
        "missionIdentityKeys": sorted(STRUCTURED_MISSION_IDENTITY_KEYS),
        "candidateFileCount": candidate_files,
        "parsedFileCount": parsed_files,
        "visitedRecordCount": visited_records,
        "directCarrierCount": len(rows),
        "keyPairCounts": dict(sorted(key_pairs.items())),
        "receiverMatchCount": len(receiver_matches),
        "receiverScriptIds": sorted({
            script_id
            for row in receiver_matches
            for script_id in row["receiverScriptIds"]
        }),
        "rows": rows,
        "finding": (
            "The complete selected structured-data corpus exposes direct "
            "LevelScript plus mission/quest identities only through reviewed "
            "SubGame bindScriptId+dungeonMissionId records; none currently names "
            "an unresolved native Story receiver script."
        ),
        "boundary": (
            "This covers exact keys co-carried in one authored JSON record. "
            "Ancestor-container proximity, filenames, numeric adjacency, OCR, and "
            "manual overrides are not identity evidence. A future new key-pair "
            "shape fails validation instead of being promoted automatically."
        ),
        "validation": validation,
    }


def receiver_script_rows(index_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Collapse exact receiver nodes to one row per hosting LevelScript."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    nodes = (
        (index_payload.get("storyCoverage") or {}).get(
            "missionlessNativeRuntimeNodes"
        )
        or []
    )
    for node in nodes:
        if not isinstance(node, dict):
            continue
        selector = node.get("selector") or {}
        level_id = safe_text(selector.get("levelId"))
        script_id = safe_text(selector.get("listenerScriptId"))
        if not level_id or not script_id.isdigit():
            continue
        key = (level_id, script_id)
        slot = grouped.setdefault(
            key,
            {
                "levelId": level_id,
                "scriptId": script_id,
                "receiverNodeCount": 0,
                "receiverToStoryPlacementCount": 0,
                "eventNames": set(),
                "storyKeys": set(),
                "storyKinds": set(),
                "sourceFiles": set(),
                "listenerHeaderLocalIds": set(),
            },
        )
        slot["receiverNodeCount"] += 1
        event_name = safe_text(node.get("eventName"))
        if event_name:
            slot["eventNames"].add(event_name)
        header_local_id = selector.get("listenerHeaderLocalId")
        if isinstance(header_local_id, int):
            slot["listenerHeaderLocalIds"].add(header_local_id)
        for story_file in node.get("storyFiles") or []:
            if not isinstance(story_file, dict):
                continue
            slot["receiverToStoryPlacementCount"] += 1
            story_key = safe_text(story_file.get("key"))
            story_kind = safe_text(story_file.get("kind"))
            if story_key:
                slot["storyKeys"].add(story_key)
            if story_kind:
                slot["storyKinds"].add(story_kind)
            for source_file in story_file.get("sourceFiles") or []:
                if safe_text(source_file):
                    slot["sourceFiles"].add(safe_text(source_file))

    rows: list[dict[str, Any]] = []
    for slot in grouped.values():
        rows.append(
            {
                **slot,
                "eventNames": sorted(slot["eventNames"]),
                "storyKeys": sorted(slot["storyKeys"]),
                "storyKinds": sorted(slot["storyKinds"]),
                "sourceFiles": sorted(slot["sourceFiles"]),
                "listenerHeaderLocalIds": sorted(
                    slot["listenerHeaderLocalIds"]
                ),
            }
        )
    rows.sort(key=lambda row: (row["levelId"], int(row["scriptId"])))
    return rows


def subgame_script_bindings(
    index_payload: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Index exact SubGame bindScriptId rows already preserved by the pipeline."""
    bindings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows = (
        (index_payload.get("storyCoverage") or {}).get(
            "missionlessSubGamePlaybackNodes"
        )
        or []
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        script_id = safe_text(row.get("bindScriptId"))
        if not script_id:
            continue
        bindings[script_id].append(
            {
                "subGameId": safe_text(row.get("subGameId")),
                "modeId": safe_text(row.get("modeId")),
                "runtimeType": safe_text(row.get("runtimeType")),
                "mainTaskIds": sorted(
                    safe_text(value)
                    for value in row.get("mainTaskIds") or []
                    if safe_text(value)
                ),
                "subDataParentId": safe_text(row.get("subDataParentId")),
                "sourceFile": safe_text(row.get("source")),
                "missionOwnerStatus": safe_text(
                    row.get("missionOwnerStatus")
                ),
                "associations": row.get("associations") or [],
            }
        )
    return bindings


def subgame_availability_associations(
    condition_payload: dict[str, Any],
    *,
    source_file: str = "",
) -> dict[str, list[dict[str, Any]]]:
    """Index only understood typed SubGame availability prerequisites."""
    associations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    condition_specs = {
        18: (
            "subgame_unlock_quest_prerequisite",
            "quest",
            "QuestStateEqual",
            "The quest state gates SubGame availability; it does not own "
            "runtime playback.",
        ),
        19: (
            "subgame_unlock_mission_prerequisite",
            "mission",
            "MissionStateEqual",
            "The mission state gates SubGame availability; it does not own "
            "or trigger runtime playback.",
        ),
        5031: (
            "subgame_unlock_previous_game_mechanic",
            "subgame",
            "CheckPassGameMechanicsId",
            "The prior challenge gates this SubGame; it supplies no mission "
            "owner.",
        ),
    }
    for raw in condition_payload.values():
        if not isinstance(raw, dict):
            continue
        condition_type = raw.get("conditionType")
        spec = condition_specs.get(condition_type)
        subgame_id = safe_text(raw.get("gameMechanicsId"))
        if spec is None or not subgame_id:
            continue
        params = [
            safe_text(value)
            for parameter in raw.get("parameter") or []
            if isinstance(parameter, dict)
            for value in parameter.get("valueStringList") or []
            if safe_text(value)
        ]
        if not params:
            continue
        relation, target_type, type_name, finding = spec
        associations[subgame_id].append(
            {
                "relation": relation,
                "targetType": target_type,
                "targetId": params[0],
                "conditionType": condition_type,
                "conditionTypeName": type_name,
                "sourceId": safe_text(raw.get("conditionId")),
                "ownership": False,
                "finding": finding,
                "source": source_file,
                "confidence": (
                    "typed_original_data_and_native_enum_non_owning"
                ),
            }
        )
    return associations


def dungeon_scene_contexts(
    subgame_payload: dict[str, Any],
    dungeon_payload: dict[str, Any],
    condition_payload: dict[str, Any],
    *,
    subgame_source: str = "",
    dungeon_source: str = "",
    condition_source: str = "",
) -> dict[str, list[dict[str, Any]]]:
    """Join exact Dungeon scene hosts to typed SubGames without adding owners."""
    subgames = subgame_payload.get("dataTable") or {}
    if not isinstance(subgames, dict):
        return {}
    availability = subgame_availability_associations(
        condition_payload,
        source_file=condition_source,
    )
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in dungeon_payload.values():
        if not isinstance(raw, dict):
            continue
        dungeon_id = safe_text(raw.get("dungeonId"))
        scene_id = safe_text(raw.get("sceneId"))
        subgame = subgames.get(dungeon_id)
        if not dungeon_id or not scene_id or not isinstance(subgame, dict):
            continue
        bind_script_id = safe_text(subgame.get("bindScriptId"))
        if not bind_script_id.isdigit():
            continue
        dungeon_mission_id = safe_text(subgame.get("dungeonMissionId"))
        contexts[scene_id].append(
            {
                "subGameId": dungeon_id,
                "dungeonId": dungeon_id,
                "sceneId": scene_id,
                "levelId": safe_text(raw.get("levelId")),
                "dungeonSeriesId": safe_text(raw.get("dungeonSeriesId")),
                "bindScriptId": bind_script_id,
                "dungeonMissionContext": (
                    {
                        "missionId": dungeon_mission_id,
                        "ownership": False,
                        "playback": False,
                        "finding": (
                            "DungeonSubGameData co-carries dungeonMissionId "
                            "with the bound script. A different receiver in "
                            "the same scene has mission-shell runtime context "
                            "only; it does not inherit Story ownership."
                        ),
                        "source": subgame_source,
                        "confidence": "typed_original_data_non_owning",
                    }
                    if dungeon_mission_id
                    else None
                ),
                "associations": availability.get(dungeon_id, []),
                "ownership": False,
                "storyBinding": False,
                "sources": {
                    "subGame": subgame_source,
                    "dungeon": dungeon_source,
                },
                "confidence": "typed_original_data_scene_context",
                "evidenceBoundary": (
                    "Dungeon.sceneId proves that this SubGame loads the same "
                    "authored scene as the receiver. A sibling LevelScript in "
                    "that scene is not the SubGame bindScriptId, and any "
                    "availability prerequisite is not a Story owner or trigger."
                ),
            }
        )
    for scene_rows in contexts.values():
        scene_rows.sort(
            key=lambda row: (
                row["dungeonSeriesId"],
                row["subGameId"],
                int(row["bindScriptId"]),
            )
        )
    return dict(contexts)


def script_task_extra_info_rows(
    payload: dict[str, Any],
    *,
    source_file: str = "",
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Index exact level/script/task display metadata without inferring owners."""
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    data_table = payload.get("dataTable") or {}
    if not isinstance(data_table, dict):
        return indexed
    for level_id_raw, scripts in data_table.items():
        level_id = safe_text(level_id_raw)
        if not level_id or not isinstance(scripts, dict):
            continue
        for script_id_raw, tasks in scripts.items():
            script_id = safe_text(script_id_raw)
            if not script_id.isdigit() or not isinstance(tasks, dict):
                continue
            for task_id_raw, info in tasks.items():
                task_id = safe_text(task_id_raw)
                if not task_id or not isinstance(info, dict):
                    continue
                tracking_info = info.get("trackingInfoDict")
                if not isinstance(tracking_info, dict):
                    tracking_info = {}
                objectives = []
                for objective_id_raw, objective in tracking_info.items():
                    if not isinstance(objective, dict):
                        continue
                    description = objective.get("description")
                    if not isinstance(description, dict):
                        description = {}
                    objectives.append({
                        "objectiveId": safe_text(objective_id_raw),
                        "descriptionKey": safe_text(
                            description.get("key")
                        ),
                        "needFormatProgress": objective.get(
                            "needFormatProgress"
                        ),
                        "progressDisplayMode": objective.get(
                            "progressDisplayMode"
                        ),
                    })
                task_title = info.get("taskTitle")
                if not isinstance(task_title, dict):
                    task_title = {}
                indexed[(level_id, script_id, task_id)] = {
                    "taskTitleKey": safe_text(task_title.get("key")),
                    "objectiveCount": info.get("objectiveCount"),
                    "singleDescriptionFormatProgress": info.get(
                        "singleDescriptionFormatProgress"
                    ),
                    "objectives": objectives,
                    "sourceFile": source_file,
                    "evidenceBoundary": (
                        "Exact task display/tracking metadata only; it carries "
                        "no mission or quest owner."
                    ),
                }
    return indexed


def annotate_task_sources(
    decoded_task_map: dict[str, Any] | None,
    *,
    level_id: str,
    script_id: str,
    subgames: list[dict[str, Any]],
    extra_info: dict[tuple[str, str, str], dict[str, Any]],
) -> None:
    """Attach exact task-table/SubGame cross-references in place."""
    for task in (decoded_task_map or {}).get("tasks") or []:
        task_id = safe_text(task.get("taskKey"))
        if not task_id:
            continue
        detail = extra_info.get((level_id, script_id, task_id))
        if detail:
            task["taskExtraInfo"] = detail
        bindings = []
        for subgame in subgames:
            if task_id not in set(subgame.get("mainTaskIds") or []):
                continue
            bindings.append({
                "subGameId": safe_text(subgame.get("subGameId")),
                "modeId": safe_text(subgame.get("modeId")),
                "runtimeType": safe_text(subgame.get("runtimeType")),
                "missionOwnerStatus": safe_text(
                    subgame.get("missionOwnerStatus")
                ),
                "sourceFile": safe_text(subgame.get("sourceFile")),
            })
        if bindings:
            task["subGameMainTaskBindings"] = bindings


def _unwrap_const(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def _short_type_name(value: Any) -> str:
    return safe_text(value).split(",", 1)[0].rsplit(".", 1)[-1]


def _typed_nodes(
    value: Any,
    quest_id: str = "",
) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        next_quest_id = safe_text(value.get("questId")) or quest_id
        if safe_text(value.get("$type")):
            rows.append((next_quest_id, value))
        for child in value.values():
            rows.extend(_typed_nodes(child, next_quest_id))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_typed_nodes(child, quest_id))
    return rows


def mission_runtime_operand_consumers_from_payloads(
    payloads: list[tuple[str, dict[str, Any], str]],
) -> dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]:
    """Index typed MissionRuntime condition operands by exact authored key."""
    indexes: dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]] = {
        kind: defaultdict(list)
        for kind in ("dialog", "area", "spawner", "script", "entity", "task")
    }
    for mission_id, raw, source_file in payloads:
        for row in decode_mission_script_conditions(raw):
            level_id = safe_text(row.get("mapId"))
            script_id = safe_text(row.get("scriptId"))
            if level_id and script_id:
                indexes["script"][(level_id, script_id)].append({
                    "missionId": mission_id,
                    "questId": safe_text(row.get("questId")),
                    "conditionType": _short_type_name(row.get("type")),
                    "sourceFile": source_file,
                })
        for row in decode_mission_world_entity_condition_refs(raw):
            level_id = safe_text(row.get("mapId"))
            logic_id = row.get("logicId")
            if (
                level_id
                and isinstance(logic_id, int)
                and not isinstance(logic_id, bool)
                and logic_id > 0
            ):
                indexes["entity"][(level_id, logic_id)].append({
                    "missionId": mission_id,
                    "questId": safe_text(row.get("questId")),
                    "conditionType": safe_text(row.get("conditionType")),
                    "conditionPath": safe_text(row.get("conditionPath")),
                    "sourceFile": source_file,
                })
        for quest_id, node in _typed_nodes(raw):
            condition_type = _short_type_name(node.get("$type"))
            if condition_type == "CheckTalkOptionFinish":
                dialog_id = _unwrap_const(
                    node.get("_dialogId", node.get("dialogId"))
                )
                finish_id = _unwrap_const(
                    node.get("_finishId", node.get("finishId"))
                )
                if isinstance(dialog_id, str) and isinstance(finish_id, int):
                    indexes["dialog"][(dialog_id, finish_id)].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
            elif condition_type in {"ReachDestination", "TaskReachDestination"}:
                area_id = _unwrap_const(node.get("_areaId", node.get("areaId")))
                level_id = _unwrap_const(
                    node.get(
                        "_mapId",
                        node.get(
                            "mapId",
                            node.get("_levelId", node.get("levelId")),
                        ),
                    )
                )
                if isinstance(area_id, str) and isinstance(level_id, str):
                    indexes["area"][(level_id, area_id)].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
            elif condition_type == "CheckMonsterSpawnerComplete":
                spawner_id = _unwrap_const(
                    node.get("_spawnerId", node.get("spawnerId"))
                )
                level_id = _unwrap_const(
                    node.get(
                        "_levelId",
                        node.get(
                            "levelId",
                            node.get("_mapId", node.get("mapId")),
                        ),
                    )
                )
                if (
                    isinstance(spawner_id, int)
                    and not isinstance(spawner_id, bool)
                    and isinstance(level_id, str)
                ):
                    indexes["spawner"][(level_id, str(spawner_id))].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
            elif condition_type == "CheckLevelScriptTaskFinished":
                level_id = _unwrap_const(
                    node.get(
                        "_sceneId",
                        node.get(
                            "sceneId",
                            node.get("_levelId", node.get("levelId")),
                        ),
                    )
                )
                script_value = _unwrap_const(
                    node.get("_scriptId", node.get("scriptId"))
                )
                if isinstance(script_value, dict):
                    script_value = script_value.get("scriptId")
                task_id = _unwrap_const(
                    node.get("_taskId", node.get("taskId"))
                )
                level_text = safe_text(level_id)
                script_text = safe_text(script_value)
                task_text = safe_text(task_id)
                if level_text and script_text and task_text:
                    indexes["task"][
                        (level_text, script_text, task_text)
                    ].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
    return {kind: dict(rows) for kind, rows in indexes.items()}


def mission_runtime_operand_consumers(
    mission_runtime_root: Path = MRA_DIR,
) -> dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]:
    payloads = []
    if mission_runtime_root.is_dir():
        for path in sorted(mission_runtime_root.glob("*.json")):
            if path.stem.endswith("_meta"):
                continue
            raw = read_json(path) or {}
            mission_id = safe_text(raw.get("missionId")) or path.stem
            payloads.append((mission_id, raw, rel_path(path)))
    return mission_runtime_operand_consumers_from_payloads(payloads)


def world_entity_operand_sources(
    payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    """Build exact logic-id and current-script/slot WorldEntity indexes."""
    raw_logic_rows = payload.get("worldEntityBriefInfos") or {}
    if not isinstance(raw_logic_rows, dict):
        raw_logic_rows = {}
    logic_rows = {
        safe_text(logic_id): dict(brief)
        for logic_id, brief in raw_logic_rows.items()
        if safe_text(logic_id) and isinstance(brief, dict)
    }
    id_rows = payload.get("m_scriptEntityIdList") or []
    brief_rows = payload.get("m_scriptEntityBriefInfo") or []
    slot_rows: dict[tuple[str, int], dict[str, Any]] = {}
    if (
        isinstance(id_rows, list)
        and isinstance(brief_rows, list)
        and len(id_rows) == len(brief_rows)
    ):
        candidates: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        for index, (identity, brief) in enumerate(zip(id_rows, brief_rows)):
            if not isinstance(identity, dict) or not isinstance(brief, dict):
                continue
            script_id = safe_text(identity.get("scriptIdGlobal"))
            slot_id = identity.get("slotId")
            if (
                not script_id.isdigit()
                or not isinstance(slot_id, int)
                or isinstance(slot_id, bool)
            ):
                continue
            candidates[(script_id, slot_id)].append({
                "registryIndex": index,
                "scriptIdGlobal": script_id,
                "slotId": slot_id,
                "entityType": brief.get("entityType"),
                "entityDetailId": safe_text(brief.get("detailId")),
                "position": brief.get("position"),
            })
        slot_rows = {
            key: rows[0]
            for key, rows in candidates.items()
            if len(rows) == 1
        }
    return logic_rows, slot_rows


def annotate_task_condition_operands(
    decoded_task_map: dict[str, Any] | None,
    *,
    level_id: str,
    script_id: str,
    story_keys: list[str],
    mission_areas: list[dict[str, Any]],
    logic_entities: dict[str, dict[str, Any]],
    slot_entities: dict[tuple[str, int], dict[str, Any]],
    mission_consumers: dict[
        str,
        dict[tuple[Any, ...], list[dict[str, Any]]],
    ],
    levelscript_root: Path,
    spawner_root: Path,
) -> None:
    """Resolve exact condition operands while preserving non-owning status."""
    area_by_id = {
        safe_text(area.get("missionAreaId")): area
        for area in mission_areas
        if isinstance(area, dict) and safe_text(area.get("missionAreaId"))
    }
    story_key_set = set(story_keys)
    for task in (decoded_task_map or {}).get("tasks") or []:
        task_consumers = mission_consumers["task"].get(
            (level_id, script_id, safe_text(task.get("taskKey"))),
            [],
        )
        if task_consumers:
            task["missionRuntimeTaskConsumers"] = task_consumers
        for condition_row in task.get("conditions") or []:
            condition = condition_row.get("condition") or {}
            sources = []
            consumers = []

            dialog_id = (condition.get("dialogId") or {}).get("value")
            finish_id = (condition.get("finishId") or {}).get("value")
            if isinstance(dialog_id, str):
                if dialog_id in story_key_set:
                    sources.append({
                        "kind": "same_receiver_story",
                        "storyKey": dialog_id,
                    })
                if isinstance(finish_id, int):
                    consumers.extend(
                        mission_consumers["dialog"].get(
                            (dialog_id, finish_id),
                            [],
                        )
                    )

            area_id = (condition.get("areaId") or {}).get("value")
            if isinstance(area_id, str) and area_id in area_by_id:
                area = area_by_id[area_id]
                sources.append({
                    "kind": "same_level_mission_area",
                    "missionAreaId": area_id,
                    "subDataParentId": area.get("subDataParentId"),
                    "shape": area.get("shape"),
                })
                consumers.extend(
                    mission_consumers["area"].get((level_id, area_id), [])
                )

            spawner_id = (condition.get("spawnerId") or {}).get("value")
            if isinstance(spawner_id, str):
                spawner_path = (
                    spawner_root
                    / level_id
                    / f"sc_{level_id}_{spawner_id}.json"
                )
                if spawner_path.is_file():
                    sources.append({
                        "kind": "same_level_spawner_config",
                        "spawnerId": spawner_id,
                        "sourceFile": rel_path(spawner_path),
                    })
                consumers.extend(
                    mission_consumers["spawner"].get(
                        (level_id, spawner_id),
                        [],
                    )
                )

            script_ptr = condition.get("scriptId") or {}
            target_script = (
                script_id
                if script_ptr.get("mode") == "current_script"
                else safe_text(script_ptr.get("scriptId"))
            )
            if target_script:
                target_path = (
                    levelscript_root / level_id / f"{target_script}.json"
                )
                if target_path.is_file():
                    sources.append({
                        "kind": "same_level_levelscript",
                        "scriptId": target_script,
                        "sourceFile": rel_path(target_path),
                    })
                consumers.extend(
                    mission_consumers["script"].get(
                        (level_id, target_script),
                        [],
                    )
                )

            pointers = []
            for field in ("entity", "entityId"):
                if isinstance(condition.get(field), dict):
                    pointers.append((field, condition[field]))
            for index, pointer in enumerate(
                (condition.get("enemyIds") or {}).get("values") or []
            ):
                if isinstance(pointer, dict):
                    pointers.append((f"enemyIds[{index}]", pointer))
            for field, pointer in pointers:
                if pointer.get("useSlotId") is True:
                    slot_id = pointer.get("slotId")
                    if isinstance(slot_id, int):
                        source = slot_entities.get((script_id, slot_id))
                        if source:
                            sources.append({
                                "kind": "current_script_slot_entity",
                                "field": field,
                                **source,
                            })
                elif pointer.get("useSlotId") is False:
                    logic_text = safe_text(pointer.get("logicId"))
                    if logic_text.isdigit() and int(logic_text) > 0:
                        logic_id = int(logic_text)
                        source = logic_entities.get(logic_text)
                        if source:
                            sources.append({
                                "kind": "world_entity_logic_id",
                                "field": field,
                                "logicId": logic_text,
                                "entityType": source.get("entityType"),
                                "entityDetailId": safe_text(
                                    source.get("detailId")
                                ),
                                "position": source.get("position"),
                            })
                        consumers.extend(
                            mission_consumers["entity"].get(
                                (level_id, logic_id),
                                [],
                            )
                        )
            if sources:
                condition_row["operandSources"] = sources
            if consumers:
                unique_consumers = {
                    (
                        safe_text(row.get("missionId")),
                        safe_text(row.get("questId")),
                        safe_text(row.get("conditionType")),
                        safe_text(row.get("sourceFile")),
                    ): row
                    for row in consumers
                }
                condition_row["missionRuntimeOperandConsumers"] = list(
                    unique_consumers.values()
                )


def _typed_levelscript_condition_operands(
    value: Any,
) -> list[dict[str, str]]:
    """Recover exact ``(levelId, scriptId)`` operands from condition trees.

    Mission objective summaries also expose a flat ``levelScriptIds`` list,
    but script ids are not globally unique.  Only the original typed condition
    operand carries the level needed for a fail-closed corpus join.
    """
    operands: list[dict[str, str]] = []
    if isinstance(value, list):
        for item in value:
            operands.extend(_typed_levelscript_condition_operands(item))
        return operands
    if not isinstance(value, dict):
        return operands
    facts = value.get("facts")
    if isinstance(facts, dict):
        level_id = safe_text(facts.get("mapId") or facts.get("levelId"))
        script_value = facts.get("scriptId")
        if isinstance(script_value, dict):
            script_value = script_value.get("scriptId")
        script_id = safe_text(script_value)
        condition_type = safe_text(value.get("type"))
        if level_id and script_id and condition_type:
            operands.append({
                "levelId": level_id,
                "scriptId": script_id,
                "conditionType": condition_type,
                "propertyKey": safe_text(facts.get("key")),
            })
    for nested in value.values():
        if isinstance(nested, (dict, list)):
            operands.extend(_typed_levelscript_condition_operands(nested))
    return operands


def mission_runtime_script_consumers(
    mission_root: Path,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Index exact typed objective operands by level and LevelScript id."""
    consumers: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    if not mission_root.is_dir():
        return consumers
    for path in sorted(mission_root.glob("*.json")):
        payload = read_json(path) or {}
        mission = payload.get("mission") or {}
        mission_id = safe_text(mission.get("id")) or path.stem
        original_source = safe_text(mission.get("source"))
        if not original_source or not (ROOT / original_source).is_file():
            original_source = ""
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            quest_id = safe_text(node.get("id"))
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                operands = _typed_levelscript_condition_operands(
                    objective.get("condition")
                )
                grouped: dict[tuple[str, str], list[dict[str, str]]] = (
                    defaultdict(list)
                )
                for operand in operands:
                    grouped[(operand["levelId"], operand["scriptId"])].append(
                        operand
                    )
                for (level_id, script_id), exact_operands in grouped.items():
                    condition_types = sorted({
                        operand["conditionType"] for operand in exact_operands
                    })
                    property_keys = sorted({
                        operand["propertyKey"] for operand in exact_operands
                        if operand["propertyKey"]
                    })
                    consumers[(level_id, script_id)].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "objectiveIndex": objective.get("index"),
                        "levelId": level_id,
                        "scriptId": script_id,
                        "conditionTypes": condition_types,
                        "propertyKeys": property_keys,
                        "sourceFile": original_source,
                        "pipelineSourceFile": rel_path(path),
                    })
    return consumers


def authored_property_contract(
    hosts: list[dict[str, Any]],
    consumers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Classify LevelData properties without treating names as ownership.

    ``lt:`` keys are generated task/lifecycle slots and ``@<id>_`` keys are
    typed module namespaces. Remaining names are authored contracts, but only
    an exact MissionRuntime property operand is an observed mission-side read.
    Neither category proves who writes the property or orders Story playback.
    """
    names = sorted({
        safe_text(name)
        for host in hosts
        for name in (host.get("briefData") or {}).get("propertyNames") or []
        if safe_text(name)
    })
    generated_names = [name for name in names if name.startswith("lt:")]
    module_names = [name for name in names if re.fullmatch(r"@\d+_.+", name)]
    authored_names = [
        name for name in names
        if name not in generated_names and name not in module_names
    ]
    observed_names = sorted({
        safe_text(key)
        for consumer in consumers
        for key in consumer.get("propertyKeys") or []
        if safe_text(key) in authored_names
    })
    return {
        "authoredNames": authored_names,
        "generatedLifecycleNames": generated_names,
        "typedModuleNames": module_names,
        "missionObservedNames": observed_names,
        "classification": (
            "authored_property_with_exact_mission_observer"
            if observed_names
            else "authored_property_unobserved_by_mission"
            if authored_names
            else "generated_or_typed_module_properties_only"
            if names
            else "no_leveldata_properties"
        ),
        "ownership": False,
        "orderEvidence": False,
        "evidenceBoundary": (
            "An authored LevelData property name is a script-local contract. "
            "An exact MissionRuntime property operand proves a mission-side "
            "read only; neither identifies the writer, playback owner, or order."
        ),
    }


def mission_areas_by_level(
    mission_area_path: Path = DEFAULT_MISSION_AREA_TABLE,
    level_basic_info_path: Path = DEFAULT_LEVEL_BASIC_INFO_TABLE,
) -> dict[str, list[dict[str, Any]]]:
    """Resolve authored MissionArea rows to their exact LevelBasicInfo level."""
    mission_area_payload = read_json(mission_area_path) or {}
    level_rows = read_json(level_basic_info_path) or {}
    area_groups = (
        mission_area_payload.get("m_areas")
        if isinstance(mission_area_payload, dict)
        else None
    )
    if not isinstance(area_groups, dict) or not isinstance(level_rows, dict):
        return {}

    out: dict[str, list[dict[str, Any]]] = {}
    for level_id, level_row in level_rows.items():
        if not isinstance(level_row, dict):
            continue
        level_num = safe_text(level_row.get("idNum"))
        group = area_groups.get(level_num)
        if not isinstance(group, dict):
            continue
        out[safe_text(level_id)] = [
            {
                "missionAreaId": safe_text(area_id),
                **area,
            }
            for area_id, area in sorted(group.items())
            if isinstance(area, dict)
        ]
    return out


def exact_start_shape_mission_area_matches(
    shapes: list[dict[str, Any]],
    mission_areas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Match complete authored shapes; proximity and names are never enough."""
    matches: list[dict[str, Any]] = []
    for shape_index, shape in enumerate(shapes):
        if not isinstance(shape, dict):
            continue
        try:
            shape_type = int(shape.get("typeRaw"))
        except (TypeError, ValueError):
            continue
        for area in mission_areas:
            area_shape = area.get("shape") if isinstance(area, dict) else None
            if not isinstance(area_shape, dict):
                continue
            try:
                area_type = int(area_shape.get("type"))
            except (TypeError, ValueError):
                continue
            if shape_type != area_type or not _native_vector_close(
                shape.get("position"),
                area_shape.get("position"),
            ):
                continue
            if shape_type == 1 and (
                not _native_vector_close(shape.get("size"), area_shape.get("size"))
                or not _native_vector_close(
                    shape.get("eulerAngles"),
                    area_shape.get("eulerAngles"),
                    angular=True,
                )
            ):
                continue
            if shape_type == 2:
                try:
                    radius_delta = abs(
                        float(shape.get("radius") or 0.0)
                        - float(area_shape.get("radius") or 0.0)
                    )
                except (TypeError, ValueError):
                    continue
                if radius_delta > 0.001:
                    continue
            matches.append(
                {
                    "startShapeIndex": shape_index,
                    "startShapeOffset": safe_text(shape.get("offset")),
                    "missionAreaId": safe_text(area.get("missionAreaId")),
                    "subDataParentId": area.get("subDataParentId"),
                    "shape": area_shape,
                    "status": "exact_complete_authored_shape_match",
                }
            )
    return matches


def exact_memorypack_string_tokens(
    data: bytes,
    values: set[str],
) -> list[str]:
    """Return exact positive-length MemoryPack string constants in one blob."""
    hits: list[str] = []
    for value in sorted(values):
        encoded = value.encode("utf-8")
        if not encoded:
            continue
        token = len(encoded).to_bytes(4, "little", signed=True) + encoded
        if token in data:
            hits.append(value)
    return hits


def mission_runtime_ids(root: Path) -> set[str]:
    """Return only ids backed by original MissionRuntimeAsset files."""
    return {
        path.stem
        for path in root.glob("*.json")
        if path.is_file() and path.stem
    }


def annotate_task_progress_property_contract(
    decoded_task_map: dict[str, Any] | None,
    hosts: list[dict[str, Any]],
) -> None:
    """Match task/condition ids to their exact LevelData progress properties.

    The current LevelData payload persists one ``lt:p`` and one ``lt:mp`` key
    for every serialized task condition. This is a structural task-runtime
    identity contract; it is not a mission owner or activation selector.
    """
    if not decoded_task_map:
        return
    properties: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for host in hosts:
        source_file = safe_text(host.get("sourceFile"))
        for row in (host.get("briefData") or {}).get("properties") or []:
            if not isinstance(row, dict):
                continue
            name = safe_text(row.get("name"))
            if name:
                properties[name].append({
                    "sourceFile": source_file,
                    "valueType": row.get("valueType"),
                    "atomCount": row.get("atomCount"),
                    "atoms": row.get("atoms") or [],
                })
    for task in decoded_task_map.get("tasks") or []:
        task_key = safe_text(task.get("taskKey"))
        condition_keys = [
            safe_text(row.get("conditionKey"))
            for row in task.get("conditions") or []
            if isinstance(row, dict) and safe_text(row.get("conditionKey"))
        ]
        expected = sorted({
            f"lt:{prefix}:{task_key}:{condition_key}"
            for condition_key in condition_keys
            for prefix in ("p", "mp")
        }) if task_key else []
        matched = [
            {
                "name": name,
                "placements": properties.get(name) or [],
            }
            for name in expected
            if properties.get(name)
        ]
        missing = [name for name in expected if not properties.get(name)]
        task["progressPropertyContract"] = {
            "schema": "levelScriptTaskProgressProperties.v1",
            "status": "validated" if expected and not missing else "incomplete",
            "expectedPropertyCount": len(expected),
            "matchedPropertyCount": len(matched),
            "conditionCount": len(condition_keys),
            "properties": matched,
            "missingProperties": missing,
            "missionOwnerStatus": "unresolved",
            "evidenceBoundary": (
                "The exact lt:p/lt:mp property pair persists progress for this "
                "serialized task condition inside its LevelData host. It carries "
                "no missionId, questId, Story identity, or playback order."
            ),
        }


def compact_leveldata_property(property_row: dict[str, Any]) -> dict[str, Any]:
    """Preserve the typed value needed by structural contract classifiers."""
    value = property_row.get("value")
    if not isinstance(value, dict):
        return {
            "name": safe_text(property_row.get("name")),
            "valueType": None,
            "atomCount": 0,
            "atoms": [],
        }
    return {
        "name": safe_text(property_row.get("name")),
        "valueType": value.get("valueType"),
        "atomCount": value.get("atomCount"),
        "atoms": [
            {
                "valueBit64": atom.get("valueBit64"),
                "text": safe_text(atom.get("text")),
            }
            for atom in value.get("atoms") or []
            if isinstance(atom, dict)
        ],
    }


def single_native_atom_value(
    property_row: dict[str, Any],
    *,
    value_type: int,
) -> Any | None:
    """Return one strictly shaped ParamValue atom, otherwise fail closed."""
    atoms = property_row.get("atoms") or []
    if (
        property_row.get("valueType") != value_type
        or property_row.get("atomCount") != 1
        or len(atoms) != 1
        or not isinstance(atoms[0], dict)
    ):
        return None
    return atoms[0].get("valueBit64")


def _module_property_signature(property_row: dict[str, Any]) -> dict[str, Any]:
    """Return a value-free signature for one serialized module property.

    Values such as spawner ids and entity references vary by instance.  The
    serialized value type, atom count, and atom representation are the stable
    shape evidence that can be compared across hosts without naming a level,
    receiver, or mission.
    """
    name = safe_text(property_row.get("name"))
    match = LEVELSCRIPT_MODULE_PROPERTY_NAME_RE.fullmatch(name)
    value_type = property_row.get("valueType")
    atom_count = property_row.get("atomCount")
    atoms = property_row.get("atoms") or []
    atom_shapes: list[str] = []
    for atom in atoms:
        if not isinstance(atom, dict):
            atom_shapes.append("invalid")
        elif isinstance(atom.get("valueBit64"), bool):
            atom_shapes.append("bool")
        elif isinstance(atom.get("valueBit64"), int):
            atom_shapes.append("int")
        elif atom.get("valueBit64") is None:
            atom_shapes.append("null")
        else:
            atom_shapes.append(type(atom.get("valueBit64")).__name__)
    return {
        "name": name,
        "moduleId": match.group("module_id") if match else "",
        "suffix": match.group("suffix") if match else "",
        "valueType": value_type,
        "atomCount": atom_count,
        "atomShapes": atom_shapes,
    }


def _module_property_family_key(signatures: list[dict[str, Any]]) -> str:
    """Build a deterministic value-independent family key."""
    shape = [
        (
            safe_text(signature.get("suffix")),
            signature.get("valueType"),
            signature.get("atomCount"),
            tuple(signature.get("atomShapes") or []),
        )
        for signature in signatures
    ]
    return hashlib.sha256(
        json.dumps(shape, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _module_property_family_pattern(
    signatures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Classify only reusable field-shape features, never an object id.

    The feature flags intentionally describe what is serialized.  They are
    not ownership claims.  A semantic adapter can add stronger binary meaning
    (for example the Encounter contract) only after this generic census has
    validated the complete family shape.
    """
    by_suffix = {
        safe_text(signature.get("suffix")): signature
        for signature in signatures
        if safe_text(signature.get("suffix"))
    }
    lifecycle = {
        suffix
        for suffix in ("is_enabled", "is_completed")
        if suffix in by_suffix
        and by_suffix[suffix].get("valueType") == 1
        and by_suffix[suffix].get("atomCount") == 1
        and by_suffix[suffix].get("atomShapes") == ["int"]
    }
    typed_payload = {
        suffix
        for suffix in by_suffix
        if suffix not in {"is_enabled", "is_completed"}
        and by_suffix[suffix].get("valueType") not in (None, 0)
    }
    features: list[str] = []
    if len(lifecycle) == 2:
        features.append("base_lifecycle_pair")
    if typed_payload:
        features.append("typed_payload_fields")
    if any(
        suffix in by_suffix
        for suffix in ("spawner_id", "enemy_list")
    ):
        features.append("encounter_candidate_fields")
    if not features:
        features.append("serialized_module_fields")
    return {
        "features": features,
        "propertyCount": len(signatures),
        "suffixes": [
            safe_text(signature.get("suffix"))
            for signature in signatures
            if safe_text(signature.get("suffix"))
        ],
    }


def module_property_family_contexts(
    hosts: list[dict[str, Any]],
    *,
    receiver_script_id: str = "",
) -> list[dict[str, Any]]:
    """Census every serialized ``@module_suffix`` family in every host.

    This is the reusable recovery surface.  It groups by the serialized
    namespace pattern and preserves exact field/value shapes, so future
    controllers can be recognized from corpus repetition and binary metadata
    without adding a host- or object-specific allowlist.
    """
    contexts: list[dict[str, Any]] = []
    for host in hosts:
        brief = host.get("briefData") or {}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for property_row in brief.get("properties") or []:
            if not isinstance(property_row, dict):
                continue
            signature = _module_property_signature(property_row)
            module_id = safe_text(signature.get("moduleId"))
            suffix = safe_text(signature.get("suffix"))
            if not module_id or not suffix:
                continue
            grouped[module_id].append(signature)
        for module_id, signatures in sorted(grouped.items(), key=lambda item: int(item[0])):
            signatures = sorted(
                signatures,
                key=lambda signature: (
                    safe_text(signature.get("suffix")),
                    str(signature.get("valueType")),
                    str(signature.get("atomCount")),
                ),
            )
            if len(signatures) < 2:
                continue
            pattern = _module_property_family_pattern(signatures)
            source_file = safe_text(host.get("sourceFile"))
            contexts.append({
                "classification": "levelscript_module_property_family",
                "mappingId": LEVELSCRIPT_MODULE_PROPERTY_MAPPING_ID,
                "runtimeType": "Beyond.Gameplay.Core.LevelScriptModule",
                "moduleId": module_id,
                "receiverScriptId": safe_text(receiver_script_id),
                "moduleIdMatchesReceiverScript": (
                    bool(receiver_script_id) and module_id == receiver_script_id
                ),
                "familyKey": _module_property_family_key(signatures),
                "pattern": pattern,
                "propertySignatures": signatures,
                "relatedFiles": ([{
                    "kind": "leveldata_module_property_host",
                    "sourceFile": source_file,
                    "relationship": "serialized_module_property_family",
                }] if source_file else []),
                "missionOwnerStatus": "unresolved",
                "storyBinding": False,
                "orderEvidence": False,
                "binaryEvidence": {
                    "gameAssemblySha256": (
                        LEVELSCRIPT_MODULE_PROPERTY_GAMEASSEMBLY_SHA256
                    ),
                    "globalMetadataSha256": (
                        LEVELSCRIPT_MODULE_PROPERTY_METADATA_SHA256
                    ),
                    "namespaceMethod": "LevelScriptModule.GetSaveKeyPrefixed",
                    "moduleIdFieldOffset": "this+0x18",
                },
                "evidenceBoundary": (
                    "The original LevelData property names and native value "
                    "shapes prove a reusable module namespace family only. "
                    "The module id is not a mission, quest, Story owner, "
                    "activation selector, branch, or playback order."
                ),
            })
    return contexts


def encounter_controller_contexts(
    level_id: str,
    receiver_script_id: str,
    hosts: list[dict[str, Any]],
    *,
    spawner_root: Path,
) -> list[dict[str, Any]]:
    """Recognize the binary-proven Encounter contract without name guesses.

    EncounterBase<T> owns the six lifecycle properties and EncounterData owns
    the enemy/spawner inputs. All eight exact module-prefixed properties must
    have their current native value shapes. The native prefix is the LsmPtr
    module id, which can differ from the hosting LevelScript id. This proves
    controller type and related source files only; it cannot identify a
    MissionRuntime owner.
    """
    contexts: list[dict[str, Any]] = []
    for host in hosts:
        brief = host.get("briefData") or {}
        properties = {
            safe_text(row.get("name")): row
            for row in brief.get("properties") or []
            if isinstance(row, dict) and safe_text(row.get("name"))
        }
        module_ids = sorted({
            match.group(1)
            for name in properties
            for match in [re.fullmatch(r"@(\d+)_.+", name)]
            if match
        }, key=int)
        for module_id in module_ids:
            prefix = f"@{module_id}_"
            required_names = [
                prefix + suffix
                for suffix in (
                    *ENCOUNTER_REQUIRED_BOOL_SUFFIXES,
                    *ENCOUNTER_REQUIRED_DATA_SUFFIXES,
                )
            ]
            if any(name not in properties for name in required_names):
                continue
            bool_rows = [
                properties[prefix + suffix]
                for suffix in ENCOUNTER_REQUIRED_BOOL_SUFFIXES
            ]
            if any(
                single_native_atom_value(row, value_type=1) not in (0, 1)
                for row in bool_rows
            ):
                continue
            enemy_row = properties[prefix + "enemy_list"]
            spawner_row = properties[prefix + "spawner_id"]
            enemy_atoms = enemy_row.get("atoms") or []
            enemy_atom_count = enemy_row.get("atomCount")
            empty_enemy_list = (
                enemy_row.get("valueType")
                == ENCOUNTER_EMPTY_ENEMY_VALUE_TYPE
                and enemy_atom_count == 0
                and not enemy_atoms
            )
            populated_enemy_list = (
                enemy_row.get("valueType")
                == ENCOUNTER_POPULATED_ENEMY_LIST_VALUE_TYPE
                and isinstance(enemy_atom_count, int)
                and not isinstance(enemy_atom_count, bool)
                and enemy_atom_count > 0
                and len(enemy_atoms) == enemy_atom_count
                and all(
                    isinstance(atom.get("valueBit64"), int)
                    and not isinstance(atom.get("valueBit64"), bool)
                    and atom["valueBit64"] > 0
                    for atom in enemy_atoms
                    if isinstance(atom, dict)
                )
                and all(isinstance(atom, dict) for atom in enemy_atoms)
            )
            spawner_value = single_native_atom_value(
                spawner_row,
                value_type=50,
            )
            if not (empty_enemy_list or populated_enemy_list):
                continue
            if (
                not isinstance(spawner_value, int)
                or isinstance(spawner_value, bool)
                or spawner_value < 0
            ):
                continue
            spawner_id = str(spawner_value)
            spawner_path = (
                spawner_root / level_id / f"sc_{level_id}_{spawner_id}.json"
            )
            related_files = [
                {
                    "kind": "leveldata_encounter_host",
                    "sourceFile": safe_text(host.get("sourceFile")),
                    "relationship": "serialized_controller_contract",
                }
            ]
            if int(spawner_id) > 0 and spawner_path.is_file():
                related_files.append({
                    "kind": "encounter_spawner_config",
                    "sourceFile": rel_path(spawner_path),
                    "relationship": "typed_spawner_id_property",
                })
            contexts.append({
                "classification": "encounter_controller_property_contract",
                "mappingId": ENCOUNTER_CONTROLLER_MAPPING_ID,
                "runtimeType": ENCOUNTER_RUNTIME_TYPE,
                "dataType": ENCOUNTER_DATA_TYPE,
                "moduleId": module_id,
                "receiverScriptId": receiver_script_id,
                "moduleIdMatchesReceiverScript": (
                    module_id == receiver_script_id
                ),
                "spawnerId": spawner_id,
                "matchedPropertyNames": required_names,
                "relatedFiles": related_files,
                "binaryEvidence": {
                    "gameAssemblySha256": ENCOUNTER_GAMEASSEMBLY_SHA256,
                    "globalMetadataSha256": ENCOUNTER_METADATA_SHA256,
                    "modulePrefixMethod": (
                        "LevelScriptModule.GetSaveKeyPrefixed"
                    ),
                    "modulePrefixMethodVa": "0x183be6a50",
                    "moduleIdFieldOffset": "this+0x18",
                    "lifecycleMethods": [
                        "ManuallyActivate",
                        "_TriggerActivate",
                        "OnBattleCompleted",
                        "OnCompleted",
                    ],
                },
                "missionOwnerStatus": "unresolved",
                "storyBinding": False,
                "orderEvidence": False,
                "evidenceBoundary": (
                    "The exact original-data property family identifies a "
                    "native Encounter module namespace and its typed spawner "
                    "dependency. The LsmPtr module id is not necessarily the "
                    "hosting LevelScript id and identifies no MissionRuntime "
                    "owner, Story activation edge, branch, or playback order."
                ),
            })
    return contexts


def validated_leveldata_hosts(
    level_id: str,
    target_script_id: str,
    mission_ids: set[str],
    *,
    leveldata_root: Path,
    levelscript_root: Path,
) -> list[dict[str, Any]]:
    """Return containers whose complete member-22 dictionary validates."""
    leveldata_dir = leveldata_root / level_id
    levelscript_dir = levelscript_root / level_id
    if not leveldata_dir.is_dir() or not levelscript_dir.is_dir():
        return []
    candidate_script_ids = {
        int(path.stem)
        for path in levelscript_dir.glob("*.json")
        if path.stem.isdigit()
    }
    numeric_target = int(target_script_id)
    if numeric_target not in candidate_script_ids:
        return []

    hosts: list[dict[str, Any]] = []
    for path in sorted(leveldata_dir.glob("*.json")):
        try:
            data = read_bytes_cached(path)
        except OSError:
            continue
        dictionary = parse_leveldata_levelscript_brief_dictionary(
            data,
            candidate_script_ids,
        )
        brief = dictionary.get(numeric_target)
        if not brief:
            continue
        mission_id = _parse_leveldata_mission_host_name(
            path.name,
            level_id,
            mission_ids,
        )
        hosts.append(
            {
                "sourceFile": rel_path(path),
                "fileName": path.name,
                "dictionaryEntryCount": len(dictionary),
                "missionNamedHost": bool(mission_id),
                "hostMissionId": mission_id or None,
                "briefData": {
                    "dataPathHash": safe_text(brief.get("dataPathHash")),
                    "levelScriptType": brief.get("levelScriptType"),
                    "maxStage": brief.get("maxStage"),
                    "parentLevelScriptId": safe_text(
                        brief.get("parentLevelScriptId")
                    ),
                    "propertyCount": brief.get("propertyCount"),
                    "propertyNames": [
                        safe_text(item.get("name"))
                        for item in brief.get("properties") or []
                        if isinstance(item, dict) and safe_text(item.get("name"))
                    ],
                    "properties": [
                        compact_leveldata_property(item)
                        for item in brief.get("properties") or []
                        if isinstance(item, dict)
                    ],
                    "refWorldEntityCount": brief.get("refWorldEntityCount"),
                    "refWorldEntityIds": brief.get("refWorldEntityIds") or [],
                },
            }
        )
    return hosts


def nominal_story_mission_candidates(
    index_payload: dict[str, Any],
    story_keys: list[str],
) -> list[dict[str, str]]:
    """Read filename-derived mission candidates already labeled by the index."""
    manifest = (
        (index_payload.get("storyCoverage") or {}).get(
            "storyTriggerManifest"
        )
        or {}
    )
    rows: list[dict[str, str]] = []
    for story_key in story_keys:
        entry = manifest.get(story_key)
        if not isinstance(entry, dict):
            continue
        mission_id = safe_text(entry.get("nominalMissionId"))
        if not mission_id:
            continue
        rows.append({
            "storyKey": story_key,
            "storyKind": safe_text(entry.get("kind")),
            "nominalMissionId": mission_id,
        })
    return rows


def nominal_mission_host_comparison(
    level_id: str,
    target_script_id: str,
    story_candidates: list[dict[str, str]],
    *,
    leveldata_root: Path,
    levelscript_root: Path,
) -> dict[str, Any]:
    """Test whether same-level nominal-mission hosts contain the receiver.

    The nominal mission id remains a filename/index candidate only. The exact
    result is limited to LevelData container membership or exclusion.
    """
    mission_ids = {
        safe_text(row.get("nominalMissionId"))
        for row in story_candidates
        if safe_text(row.get("nominalMissionId"))
    }
    leveldata_dir = leveldata_root / level_id
    levelscript_dir = levelscript_root / level_id
    comparisons: list[dict[str, Any]] = []
    if leveldata_dir.is_dir() and levelscript_dir.is_dir() and mission_ids:
        candidate_script_ids = {
            int(path.stem)
            for path in levelscript_dir.glob("*.json")
            if path.stem.isdigit()
        }
        numeric_target = int(target_script_id)
        for path in sorted(leveldata_dir.glob("*.json")):
            mission_id = _parse_leveldata_mission_host_name(
                path.name,
                level_id,
                mission_ids,
            )
            if not mission_id:
                continue
            try:
                data = read_bytes_cached(path)
            except OSError:
                continue
            dictionary = parse_leveldata_levelscript_brief_dictionary(
                data,
                candidate_script_ids,
            )
            comparisons.append({
                "missionId": mission_id,
                "sourceFile": rel_path(path),
                "fileName": path.name,
                "dictionaryValidated": bool(dictionary),
                "dictionaryEntryCount": len(dictionary),
                "receiverScriptPresent": numeric_target in dictionary,
            })

    classification = classify_nominal_mission_host_comparisons(comparisons)
    return {
        "classification": classification,
        "storyCandidates": story_candidates,
        "sameLevelMissionNamedHosts": comparisons,
        "missionOwnerStatus": "unresolved",
        "storyBinding": False,
        "orderEvidence": False,
        "missionGraphAction": "none",
        "evidenceBoundary": (
            "The nominal mission id is a Story filename/index candidate, not "
            "ownership evidence. A validated same-level mission-named "
            "LevelData dictionary can prove only whether it contains or "
            "excludes this receiver script."
        ),
    }


def classify_nominal_mission_host_comparisons(
    comparisons: list[dict[str, Any]],
) -> str:
    """Classify only validated dictionary membership or exclusion."""
    validated = [
        row for row in comparisons if row.get("dictionaryValidated")
    ]
    if any(row.get("receiverScriptPresent") for row in validated):
        return "nominal_mission_host_contains_receiver_script"
    if validated:
        return (
            "validated_nominal_mission_hosts_exclude_receiver_script"
        )
    if comparisons:
        return "nominal_mission_host_dictionary_unresolved"
    return "no_same_level_nominal_mission_host"


def activation_class(
    levelscript: dict[str, Any],
    hosts: list[dict[str, Any]],
    incoming_manual_controls: list[dict[str, Any]],
    subgame_bindings: list[dict[str, Any]] | None = None,
    *,
    start_policy_validated: bool = False,
    activation_control_validated: bool = False,
    active_phase_receiver_validated: bool = False,
) -> str:
    """Classify only the static carriers that the audit actually decodes."""
    if subgame_bindings:
        if activation_control_validated:
            return "subgame_interaction_manual_start"
        return "subgame_bind_script_activation_scope"
    if not levelscript:
        return "levelscript_missing_or_undecoded"
    start_type = safe_text(levelscript.get("startTypeName"))
    if not start_type:
        return "start_type_unresolved"
    cross_targets = [
        row for row in incoming_manual_controls if not row.get("selfTarget")
    ]
    if cross_targets:
        return "literal_cross_script_manual_control"
    current_context_self_starts = [
        row
        for row in incoming_manual_controls
        if row.get("selfTarget")
        and safe_text(row.get("action")) == "ManualStartLevelScript"
        and safe_text(row.get("targetResolution"))
        == "current_context_self"
        and bool(row.get("headerLinkedEvent"))
    ]
    if current_context_self_starts:
        return "header_linked_current_context_self_manual_start"
    if start_type == "SameWithActive" and start_policy_validated:
        return "same_with_active_binary_active_gate"
    if start_type != "Manual":
        if (levelscript.get("startShapeListCount") or 0) > 0:
            return "nonmanual_start_with_shapes"
        return "nonmanual_start_static_carrier_unresolved"

    parent_ids = {
        safe_text((host.get("briefData") or {}).get("parentLevelScriptId"))
        for host in hosts
    }
    parent_ids.discard("")
    no_parent = bool(hosts) and parent_ids == {"0"}
    no_shapes = (
        safe_text(levelscript.get("startShapeListStatus")) == "null"
        and (levelscript.get("startShapeListCount") or 0) == 0
    )
    no_task_map = (
        safe_text(levelscript.get("taskMapStatus")) == "null"
        and (levelscript.get("taskMapCount") or 0) == 0
    )
    if no_parent and no_shapes and no_task_map:
        if active_phase_receiver_validated:
            return "manual_start_active_phase_receiver"
        if activation_control_validated:
            return "manual_start_runtime_request_no_static_carrier"
        return "manual_start_no_static_activation_carrier"
    return "manual_start_static_carrier_unresolved"


def exact_active_phase_receiver_contract(
    script_data: bytes,
    receiver: dict[str, Any],
    activation_control: dict[str, Any],
) -> dict[str, Any]:
    """Join exact receiver header ids to their original serialized phase."""
    header_ids = sorted({
        value
        for value in receiver.get("listenerHeaderLocalIds") or []
        if isinstance(value, int)
    })
    topology, diagnostic = decode_levelscript_native_action_topology(script_data)
    roots_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    if isinstance(topology, dict):
        for root in topology.get("eventRoots") or []:
            if isinstance(root, dict) and isinstance(root.get("localId"), int):
                roots_by_id[root["localId"]].append(root)
    rows: list[dict[str, Any]] = []
    missing: list[int] = []
    ambiguous: list[int] = []
    for header_id in header_ids:
        candidates = roots_by_id.get(header_id) or []
        if not candidates:
            missing.append(header_id)
            continue
        if len(candidates) != 1:
            ambiguous.append(header_id)
            continue
        root = candidates[0]
        rows.append({
            "listenerHeaderLocalId": header_id,
            "headerName": safe_text(root.get("headerName")),
            "recordOffset": root.get("recordOffset"),
            "triggerActiveDuring": root.get("triggerActiveDuring"),
            "nextActionLocalId": root.get("nextActionLocalId"),
        })
    flow = activation_control.get("activeReceiverFlow") or {}
    active_value = (flow.get("triggerActiveDuringValues") or {}).get("Active")
    binary_validated = (
        (activation_control.get("validation") or {}).get("status") == "validated"
        and flow.get("setupRegisterTriggerCallCount") == 1
        and flow.get("activePhaseEnableBetweenStateSetters") is True
        and isinstance(active_value, int)
    )
    all_active = (
        bool(rows)
        and len(rows) == len(header_ids)
        and all(row.get("triggerActiveDuring") == active_value for row in rows)
    )
    validated = (
        bool(header_ids)
        and isinstance(topology, dict)
        and safe_text(topology.get("status")).startswith(
            "exact_complete_action_map"
        )
        and not missing
        and not ambiguous
        and all_active
        and binary_validated
    )
    return {
        "schema": "exactActivePhaseReceiver.v1",
        "status": "validated" if validated else "unresolved",
        "classification": (
            "registered_active_phase_story_receivers"
            if validated
            else "receiver_phase_unresolved"
        ),
        "listenerHeaderCount": len(header_ids),
        "resolvedHeaderCount": len(rows),
        "missingHeaderLocalIds": missing,
        "ambiguousHeaderLocalIds": ambiguous,
        "allReceiversActivePhase": all_active,
        "triggerActiveDuringValues": flow.get("triggerActiveDuringValues") or {},
        "receiverHeaders": rows,
        "topologySchema": (
            topology.get("schema") if isinstance(topology, dict) else None
        ),
        "topologyStatus": (
            topology.get("status") if isinstance(topology, dict) else None
        ),
        "topologyDiagnostic": diagnostic,
        "runtimeFlow": {
            key: flow.get(key)
            for key in (
                "setupRegisterTriggerCallCount",
                "setupRegisterTriggerCallOffsets",
                "activePhaseEnableArguments",
                "activePhaseEnableCallOffsets",
                "activeBeginStateValue",
                "waitForSubEntityInitNewlyStateValue",
                "activeBeginSetterOffsets",
                "waitForSubEntityInitNewlySetterOffsets",
                "activePhaseEnableBetweenStateSetters",
            )
        },
        "methods": {
            key: (activation_control.get("methods") or {}).get(key) or {}
            for key in (
                "Setup",
                "RegisterTriggerFromLevelScript",
                "SetAllTriggerActiveByPhase",
                "UpdateRuntimeState",
            )
        },
        "finding": (
            "Every exact Story receiver header in this LevelScript is serialized "
            "for TriggerActiveDuring.Active. The current binary registers the "
            "LevelScript trigger graph during Setup and enables the Active phase "
            "while advancing through ActiveBegin."
            if validated
            else "The exact serialized receiver phase could not be validated."
        ),
        "evidenceBoundary": (
            "This proves receiver availability in the LevelScript Active phase. "
            "It does not prove who selected public Active state, that an event "
            "fired, mission ownership, branch choice, or cross-Story order. A "
            "Manual start policy governs the later Start phase and is not itself "
            "a missing carrier for these Active-phase receiver headers."
        ),
    }


def exact_client_active_request_contract(
    hosts: list[dict[str, Any]],
    activation_control: dict[str, Any],
    levelscript: dict[str, Any],
) -> dict[str, Any]:
    """Join one validated LevelData type to the generic binary selector.

    This is intentionally type-driven.  Script ids, filenames, Story keys, and
    mission candidates never select a branch.
    """
    selector = activation_control.get("activationSelectorFlow") or {}
    active_area_flow = activation_control.get("activeAreaFlow") or {}
    active_shapes = levelscript.get("activeShapeList") or {}
    type_values = selector.get("levelScriptTypeValues") or {}
    validation = activation_control.get("validation") or {}
    host_types = [
        (host.get("briefData") or {}).get("levelScriptType")
        for host in hosts
        if isinstance((host.get("briefData") or {}).get("levelScriptType"), int)
    ]
    binary_validated = (
        activation_control.get("schema") == "levelScriptActivationControl.v6"
        and validation.get("status") == "validated"
        and selector.get("nonSubLevelRequiresEnabledAndActiveArea") is True
        and selector.get("subLevelRequiresPublicActive") is True
        and selector.get("nonSubLevelSendsActiveTrueAfterPreActive") is True
        and selector.get("subLevelSkipsActiveTrueRequest") is True
        and type_values.get("SubLevelScript") == 4
    )
    exact_host = len(hosts) == 1 and len(host_types) == 1
    level_script_type = host_types[0] if exact_host else None
    type_name = next(
        (
            name for name, value in type_values.items()
            if value == level_script_type
        ),
        "",
    )
    validated = binary_validated and exact_host and bool(type_name)
    is_sublevel = validated and level_script_type == type_values.get(
        "SubLevelScript"
    )
    classification = "activation_selector_unresolved"
    if validated:
        classification = (
            "sublevel_waits_for_public_active"
            if is_sublevel
            else "client_runtime_active_request_after_enabled_area_gate"
        )
    spatial_gate_validated = (
        validated
        and not is_sublevel
        and active_shapes.get("status") == "decoded_unique"
        and active_shapes.get("candidateCount") == 1
        and isinstance(active_shapes.get("count"), int)
        and int(active_shapes["count"]) > 0
        and len(active_shapes.get("shapes") or []) == int(active_shapes["count"])
        and active_area_flow.get("emptyActiveListSetsWithinTrue") is True
        and active_area_flow.get("activeShapeHitSetsWithinTrue") is True
        and active_area_flow.get("missingOutsideListPreservesPriorWithin") is True
        and active_area_flow.get("outsideShapeMissPreservesPriorWithin") is True
        and active_area_flow.get("outsideShapeHitClearsWithin") is True
    )
    return {
        "schema": "exactClientActiveRequest.v1",
        "status": "validated" if validated else "unresolved",
        "classification": classification,
        "validatedLevelDataHostCount": len(hosts),
        "levelScriptType": level_script_type,
        "levelScriptTypeName": type_name,
        "clientProducesActiveRequest": validated and not is_sublevel,
        "entryPublicState": (
            "Active" if is_sublevel else "Enabled" if validated else ""
        ),
        "requiresActiveAreaGate": validated and not is_sublevel,
        "runtimePath": (
            [
                "Enabled(2)",
                "UpdateWithinActiveArea",
                "PreActive(7)",
                "PreActiveEndSendActiveState(9)",
                "SendLevelScriptSetActive(true)",
                "WaitForStateActive(10)",
            ]
            if validated and not is_sublevel
            else ["Active(3)", "PreActive(7)", "WaitForStateActive(10)"]
            if is_sublevel
            else []
        ),
        "selectorFlow": selector if validated else {},
        "spatialGateStatus": (
            "validated_runtime_position_dependent"
            if spatial_gate_validated
            else "not_applicable"
            if is_sublevel
            else "unresolved"
        ),
        "activeShapeList": active_shapes if spatial_gate_validated else {},
        "activeAreaFlow": active_area_flow if spatial_gate_validated else {},
        "finding": (
            "The exact LevelData type selects the generic non-SubLevelScript "
            "branch: after public Enabled and a successful active-area check, "
            "the client runtime enters PreActive and emits active=true."
            if validated and not is_sublevel
            else "The exact LevelData type selects the SubLevelScript branch, "
            "which waits for public Active and does not emit active=true."
            if is_sublevel
            else "The original LevelData type could not be joined uniquely to "
            "the validated binary activation selector."
        ),
        "evidenceBoundary": (
            "This proves the generic request-producing branch selected by the "
            "original LevelData type and, where decoded, its authored activation "
            "volume. The validated snapshot/notification carriers prove public "
            "Enabled is server-supplied, but not the server-side selection rule, player "
            "position, whether the spatial gate passed in a particular playthrough, "
            "which server branch accepted Active, mission ownership, event firing, "
            "or Story order."
        ),
    }


def build_report(
    index_payload: dict[str, Any],
    *,
    leveldata_root: Path = LEVELDATA_DIR,
    levelscript_root: Path = LEVELSCRIPT_DIR,
    mission_root: Path = DEFAULT_PIPELINE_MISSION_ROOT,
    mission_runtime_root: Path = MRA_DIR,
    spawner_root: Path = SPAWNER_CONFIG_DIR,
    script_task_extra_info_path: Path = DEFAULT_SCRIPT_TASK_EXTRA_INFO_TABLE,
    world_entity_registry_path: Path = DEFAULT_WORLD_ENTITY_REGISTRY,
    subgame_table_path: Path = DEFAULT_SUBGAME_TABLE,
    game_mechanic_condition_table_path: Path = (
        DEFAULT_GAME_MECHANIC_CONDITION_TABLE
    ),
    dungeon_table_path: Path = DEFAULT_DUNGEON_TABLE,
    structured_json_root: Path = DEFAULT_STRUCTURED_JSON_ROOT,
) -> dict[str, Any]:
    known_mission_ids = {
        safe_text(row.get("id"))
        for row in index_payload.get("missions") or []
        if isinstance(row, dict) and safe_text(row.get("id"))
    }
    authored_mission_ids = mission_runtime_ids(mission_runtime_root)
    task_authority = (
        (index_payload.get("runtimeContract") or {}).get(
            "levelScriptTaskAuthorityAudit"
        )
        or {}
    )
    start_policy = (
        (index_payload.get("runtimeContract") or {}).get(
            "levelScriptStartPolicyAudit"
        )
        or {}
    )
    start_policy_validated = (
        (start_policy.get("validation") or {}).get("status") == "validated"
        and safe_text(start_policy.get("classification"))
        == "same_with_active_enters_prestart_when_active"
        and (start_policy.get("discoveryPattern") or {}).get(
            "objectIdentityInputs"
        )
        == []
    )
    manual_self_control = (
        (index_payload.get("runtimeContract") or {}).get(
            "levelScriptManualSelfControlAudit"
        )
        or {}
    )
    manual_self_control_validated = (
        (manual_self_control.get("validation") or {}).get("status")
        == "validated"
        and safe_text(manual_self_control.get("classification"))
        == "current_context_manual_start_self_target"
        and (manual_self_control.get("discoveryPattern") or {}).get(
            "serializedObjectInputs"
        )
        == []
    )
    activation_control = (
        (index_payload.get("runtimeContract") or {}).get(
            "levelScriptActivationControlAudit"
        )
        or {}
    )
    activation_control_validated = (
        (activation_control.get("validation") or {}).get("status")
        == "validated"
        and safe_text(activation_control.get("classification"))
        == "server_state_subgame_and_runtime_request_paths"
        and (activation_control.get("discoveryPattern") or {}).get(
            "serializedObjectInputs"
        )
        == [
            "SubGameInstanceData.id",
            "SubGameInstanceData.bindScriptId",
        ]
    )
    manual_control_index = build_manual_control_index(
        levelscript_root=levelscript_root,
        self_control_contract=manual_self_control,
    )
    incoming_by_target = manual_control_index.targets
    subgames_by_script = subgame_script_bindings(index_payload)
    consumers_by_script = mission_runtime_script_consumers(mission_root)
    task_extra_info = script_task_extra_info_rows(
        read_json(script_task_extra_info_path) or {},
        source_file=rel_path(script_task_extra_info_path),
    )
    mission_areas = mission_areas_by_level()
    mission_operand_consumers = mission_runtime_operand_consumers(
        mission_runtime_root
    )
    logic_entities, slot_entities = world_entity_operand_sources(
        read_json(world_entity_registry_path) or {}
    )
    dungeon_contexts_by_scene = dungeon_scene_contexts(
        read_json(subgame_table_path) or {},
        read_json(dungeon_table_path) or {},
        read_json(game_mechanic_condition_table_path) or {},
        subgame_source=rel_path(subgame_table_path),
        dungeon_source=rel_path(dungeon_table_path),
        condition_source=rel_path(game_mechanic_condition_table_path),
    )
    receiver_sources = receiver_script_rows(index_payload)
    receiver_pairs = {
        (safe_text(row.get("levelId")), safe_text(row.get("scriptId")))
        for row in receiver_sources
        if safe_text(row.get("levelId")) and safe_text(row.get("scriptId"))
    }
    mission_area_leveldata_shells = (
        build_leveldata_mission_area_script_host_index(
            receiver_pairs,
            leveldata_root=leveldata_root,
            levelscript_root=levelscript_root,
            mission_area_table_path=DEFAULT_MISSION_AREA_TABLE,
            level_basic_info_table_path=DEFAULT_LEVEL_BASIC_INFO_TABLE,
            mission_runtime_root=mission_runtime_root,
        )
    )
    mission_area_shell_validation = (
        validate_mission_area_leveldata_shell_contexts(
            receiver_pairs,
            mission_area_leveldata_shells,
            authored_mission_ids,
        )
    )
    structured_identity_census = structured_identity_cocarrier_census(
        receiver_sources,
        structured_json_root=structured_json_root,
    )
    teleport_runtime_contract = teleport_finish_runtime_contract(index_payload)
    teleport_finish_census = build_teleport_finish_correlation_census(
        levelscript_root,
        teleport_runtime_contract,
    )
    teleport_context_index = teleport_finish_receiver_contexts(
        teleport_finish_census
    )
    rows: list[dict[str, Any]] = []
    classes: Counter[str] = Counter()
    start_types: Counter[str] = Counter()
    host_shapes: Counter[str] = Counter()
    task_condition_types: Counter[str] = Counter()
    task_operand_source_types: Counter[str] = Counter()
    task_mission_consumer_types: Counter[str] = Counter()
    authored_property_scripts: Counter[str] = Counter()
    task_conditions_with_operand_sources = 0
    task_conditions_with_mission_consumers = 0
    tasks_with_mission_consumers = 0

    for receiver in receiver_sources:
        level_id = receiver["levelId"]
        script_id = receiver["scriptId"]
        script_path = levelscript_root / level_id / f"{script_id}.json"
        levelscript = decode_levelscript_binary_file(script_path, script_id)
        try:
            script_data = read_bytes_cached(script_path)
        except OSError:
            script_data = b""
        hosts = validated_leveldata_hosts(
            level_id,
            script_id,
            known_mission_ids,
            leveldata_root=leveldata_root,
            levelscript_root=levelscript_root,
        )
        module_property_families = module_property_family_contexts(
            hosts,
            receiver_script_id=script_id,
        )
        encounter_contexts = encounter_controller_contexts(
            level_id,
            script_id,
            hosts,
            spawner_root=spawner_root,
        )
        story_candidates = nominal_story_mission_candidates(
            index_payload,
            receiver["storyKeys"],
        )
        nominal_host_comparison = nominal_mission_host_comparison(
            level_id,
            script_id,
            story_candidates,
            leveldata_root=leveldata_root,
            levelscript_root=levelscript_root,
        )
        incoming = incoming_by_target.get((level_id, script_id), [])
        subgames = subgames_by_script.get(script_id, [])
        dungeon_contexts = [
            {
                **context,
                "receiverIsBoundScript": (
                    safe_text(context.get("bindScriptId")) == script_id
                ),
            }
            for context in dungeon_contexts_by_scene.get(level_id, [])
        ]
        consumers = consumers_by_script.get((level_id, script_id), [])
        mission_area_leveldata_shell = (
            mission_area_leveldata_shells.get((level_id, script_id)) or {}
        )
        property_contract = authored_property_contract(hosts, consumers)
        authored_property_scripts.update(
            set(property_contract["authoredNames"])
        )
        start_shape_area_matches = exact_start_shape_mission_area_matches(
            levelscript.get("startShapeListShapes") or [],
            mission_areas.get(level_id, []),
        )
        serialized_mission_ids = exact_memorypack_string_tokens(
            script_data,
            authored_mission_ids,
        )
        decoded_task_maps = decode_levelscript_task_conditions(
            script_data,
            script_id,
        )
        decoded_task_map = (
            decoded_task_maps[0] if len(decoded_task_maps) == 1 else None
        )
        annotate_task_sources(
            decoded_task_map,
            level_id=level_id,
            script_id=script_id,
            subgames=subgames,
            extra_info=task_extra_info,
        )
        annotate_task_progress_property_contract(decoded_task_map, hosts)
        annotate_task_condition_operands(
            decoded_task_map,
            level_id=level_id,
            script_id=script_id,
            story_keys=receiver["storyKeys"],
            mission_areas=mission_areas.get(level_id, []),
            logic_entities=logic_entities,
            slot_entities=slot_entities,
            mission_consumers=mission_operand_consumers,
            levelscript_root=levelscript_root,
            spawner_root=spawner_root,
        )
        for task in (decoded_task_map or {}).get("tasks") or []:
            tasks_with_mission_consumers += bool(
                task.get("missionRuntimeTaskConsumers")
            )
            for condition_row in task.get("conditions") or []:
                condition = condition_row.get("condition") or {}
                condition_type = safe_text(condition.get("type"))
                if condition_type:
                    task_condition_types[condition_type] += 1
                operand_sources = condition_row.get("operandSources") or []
                mission_consumers = (
                    condition_row.get("missionRuntimeOperandConsumers") or []
                )
                task_conditions_with_operand_sources += bool(operand_sources)
                task_conditions_with_mission_consumers += bool(
                    mission_consumers
                )
                for source in operand_sources:
                    source_type = safe_text(source.get("kind"))
                    if source_type:
                        task_operand_source_types[source_type] += 1
                for consumer in mission_consumers:
                    consumer_type = safe_text(consumer.get("conditionType"))
                    if consumer_type:
                        task_mission_consumer_types[consumer_type] += 1
        active_phase_receiver = exact_active_phase_receiver_contract(
            script_data,
            receiver,
            activation_control,
        )
        active_phase_receiver_validated = (
            active_phase_receiver.get("status") == "validated"
        )
        teleport_finish_correlations = []
        for header_id in receiver.get("listenerHeaderLocalIds") or []:
            if not isinstance(header_id, int):
                continue
            context = teleport_context_index.get(
                (level_id, script_id, header_id)
            )
            if context:
                teleport_finish_correlations.append({
                    **context,
                    "listenerHeaderLocalId": header_id,
                })
        client_active_request = exact_client_active_request_contract(
            hosts,
            activation_control,
            levelscript,
        )
        classification = activation_class(
            levelscript,
            hosts,
            incoming,
            subgames,
            start_policy_validated=start_policy_validated,
            activation_control_validated=activation_control_validated,
            active_phase_receiver_validated=(
                active_phase_receiver_validated
            ),
        )
        classes[classification] += 1
        start_types[safe_text(levelscript.get("startTypeName")) or "[unresolved]"] += 1
        if not hosts:
            host_shapes["no_validated_host"] += 1
        elif all(host.get("dictionaryEntryCount") == 1 for host in hosts):
            host_shapes["singleton_only"] += 1
        else:
            host_shapes["includes_multi_script_host"] += 1

        related_original_files = collect_related_original_files(
            {"sourceFile": rel_path(script_path)},
            receiver,
            hosts,
            module_property_families,
            encounter_contexts,
            subgames,
            dungeon_contexts,
            consumers,
            mission_area_leveldata_shell,
            {
                "sourceFile": rel_path(DEFAULT_MISSION_AREA_TABLE),
            }
            if mission_area_leveldata_shell
            else {},
            {
                "sourceFile": rel_path(DEFAULT_LEVEL_BASIC_INFO_TABLE),
            }
            if mission_area_leveldata_shell
            else {},
            decoded_task_map,
        )
        row_task_authority = task_authority if decoded_task_map else {}
        row_start_policy = (
            start_policy
            if start_policy_validated
            and safe_text(levelscript.get("startTypeName")) == "SameWithActive"
            else {}
        )
        row_manual_self_control = (
            manual_self_control
            if manual_self_control_validated
            and any(
                safe_text(control.get("targetResolution"))
                == "current_context_self"
                for control in incoming
            )
            else {}
        )
        activation_methods = activation_control.get("methods") or {}
        row_activation_control = (
            {
                "schema": safe_text(activation_control.get("schema")),
                "source": safe_text(activation_control.get("source")),
                "classification": safe_text(
                    activation_control.get("classification")
                ),
                "stateNotifyMessageId": (
                    activation_control.get("messageIds") or {}
                ).get("ScSceneLevelScriptStateNotify"),
                "selfSceneInfoMessageId": (
                    activation_control.get("messageIds") or {}
                ).get("ScSelfSceneInfo"),
                "selfSceneInfoHandlerMethod": activation_methods.get(
                    "SelfSceneInfoHandler"
                )
                or {},
                "handlerMethod": activation_methods.get(
                    "StateNotifyHandler"
                )
                or {},
                "updateStateMethod": activation_methods.get("UpdateState")
                or {},
                "publicStateFlow": activation_control.get("publicStateFlow")
                or {},
                "publicStateSourceFlow": activation_control.get(
                    "publicStateSourceFlow"
                )
                or {},
                "finding": safe_text(activation_control.get("finding")),
                "evidenceBoundary": safe_text(
                    activation_control.get("evidenceBoundary")
                ),
                "relatedOriginalFiles": (
                    activation_control.get("relatedOriginalFiles") or []
                ),
                "validation": activation_control.get("validation") or {},
            }
            if activation_control_validated
            else {}
        )
        row_client_start_request_control = (
            {
                **row_activation_control,
                "activeRequestMessageId": (
                    activation_control.get("messageIds") or {}
                ).get("CsSceneSetLevelScriptActive"),
                "startRequestMessageId": (
                    activation_control.get("messageIds") or {}
                ).get("CsSceneSetLevelScriptStart"),
                "fieldOffsets": activation_control.get("fieldOffsets") or {},
                "networkSetStartMethod": activation_methods.get(
                    "NetworkSetStart"
                )
                or {},
                "manualStartMethod": activation_methods.get("ManualStart") or {},
                "runtimeSendStartMethod": activation_methods.get(
                    "RuntimeSendStart"
                )
                or {},
                "updateRuntimeStateMethod": activation_methods.get(
                    "UpdateRuntimeState"
                )
                or {},
                "clientRequestFlow": (
                    activation_control.get("clientRequestFlow") or {}
                ),
                "directCallers": activation_control.get("directCallers") or {},
            }
            if activation_control_validated
            else {}
        )
        row_subgame_start_control = (
            {
                **row_activation_control,
                "challengeMethod": activation_methods.get(
                    "ChallengeOnInteract"
                )
                or {},
                "manualStartMethod": activation_methods.get("ManualStart")
                or {},
                "fieldOffsets": activation_control.get("fieldOffsets") or {},
                "subGameInteractionFlow": (
                    activation_control.get("subGameInteractionFlow") or {}
                ),
                "manualStartDirectCallers": (
                    activation_control.get("manualStartDirectCallers") or []
                ),
            }
            if activation_control_validated and subgames
            else {}
        )
        related_paths = {
            safe_text(related.get("sourceFile"))
            for related in related_original_files
        }
        for related in row_task_authority.get("relatedOriginalFiles") or []:
            if (
                isinstance(related, dict)
                and safe_text(related.get("sourceFile"))
                and safe_text(related.get("sourceFile")) not in related_paths
            ):
                related_original_files.append(dict(related))
                related_paths.add(safe_text(related.get("sourceFile")))
        for related in row_start_policy.get("relatedOriginalFiles") or []:
            if (
                isinstance(related, dict)
                and safe_text(related.get("sourceFile"))
                and safe_text(related.get("sourceFile")) not in related_paths
            ):
                related_original_files.append(dict(related))
                related_paths.add(safe_text(related.get("sourceFile")))
        for related in row_manual_self_control.get("relatedOriginalFiles") or []:
            if (
                isinstance(related, dict)
                and safe_text(related.get("sourceFile"))
                and safe_text(related.get("sourceFile")) not in related_paths
            ):
                related_original_files.append(dict(related))
                related_paths.add(safe_text(related.get("sourceFile")))
        for related in row_activation_control.get("relatedOriginalFiles") or []:
            if (
                isinstance(related, dict)
                and safe_text(related.get("sourceFile"))
                and safe_text(related.get("sourceFile")) not in related_paths
            ):
                related_original_files.append(dict(related))
                related_paths.add(safe_text(related.get("sourceFile")))

        rows.append(
            {
                **receiver,
                "levelScript": {
                    "sourceFile": rel_path(script_path),
                    "scriptIdVerified": bool(levelscript.get("scriptIdVerified")),
                    "serializedMemberCount": levelscript.get(
                        "serializedMemberCount"
                    ),
                    "actionMapRecordCount": levelscript.get(
                        "actionMapRecordCount"
                    ),
                    "activeShapeList": levelscript.get("activeShapeList") or {},
                    "activeShapeListStatus": safe_text(
                        levelscript.get("activeShapeListStatus")
                    ),
                    "activeShapeListCount": levelscript.get(
                        "activeShapeListCount"
                    ),
                    "activeShapeListShapes": levelscript.get(
                        "activeShapeListShapes"
                    )
                    or [],
                    "startTypeRaw": levelscript.get("startTypeRaw"),
                    "startTypeName": safe_text(levelscript.get("startTypeName")),
                    "startShapeListStatus": safe_text(
                        levelscript.get("startShapeListStatus")
                    ),
                    "startShapeListCount": levelscript.get("startShapeListCount"),
                    "startShapeListShapes": levelscript.get(
                        "startShapeListShapes"
                    )
                    or [],
                    "taskMapStatus": safe_text(levelscript.get("taskMapStatus")),
                    "taskMapCount": levelscript.get("taskMapCount"),
                    "triggerVolumesStatus": safe_text(
                        levelscript.get("triggerVolumesStatus")
                    ),
                    "triggerVolumesCount": levelscript.get("triggerVolumesCount"),
                    "triggerVolumeSlotIds": levelscript.get(
                        "triggerVolumeSlotIds"
                    )
                    or [],
                },
                "levelDataHosts": hosts,
                "modulePropertyFamilies": module_property_families,
                "encounterControllerContexts": encounter_contexts,
                "nominalMissionHostComparison": nominal_host_comparison,
                "incomingLiteralManualControls": incoming,
                "manualSelfControl": row_manual_self_control,
                "publicStateControl": row_activation_control,
                "clientStartRequestControl": row_client_start_request_control,
                "activePhaseReceiverControl": active_phase_receiver,
                "teleportFinishCorrelations": teleport_finish_correlations,
                "clientActiveRequestControl": client_active_request,
                "subGameStartControl": row_subgame_start_control,
                "subGameBindings": subgames,
                "dungeonSceneContexts": dungeon_contexts,
                "missionRuntimeScriptConsumers": consumers,
                "missionAreaLevelDataShellContext": (
                    mission_area_leveldata_shell
                ),
                "authoredPropertyContract": property_contract,
                "startShapeMissionAreaMatches": start_shape_area_matches,
                "serializedMissionRuntimeIdTokens": serialized_mission_ids,
                "decodedTaskMap": decoded_task_map,
                "taskRuntimeAuthority": row_task_authority,
                "startRuntimePolicy": row_start_policy,
                "relatedOriginalFiles": related_original_files,
                "activationClass": classification,
                "missionOwnerStatus": "unresolved",
                "evidenceBoundary": (
                    "The exact LevelData type now selects the generic client/public "
                    "activation branch. The server supplies Enabled through the exact "
                    "snapshot/notification carriers, but its selection rule, "
                    "a mission or quest owner, event firing, playback ownership, or "
                    "Story order."
                ),
            }
        )

    return {
        "schemaVersion": SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "missionPipelineIndex": rel_path(DEFAULT_PIPELINE_INDEX),
            "manualControlIndex": {
                "sourceRoot": manual_control_index.source_root,
                "mappingId": manual_control_index.mapping_id,
                "validation": manual_control_index.validation,
                "evidenceBoundary": manual_control_index.evidence_boundary,
            },
            "levelDataRoot": rel_path(leveldata_root),
            "levelScriptRoot": rel_path(levelscript_root),
            "missionPipelineMissionRoot": rel_path(mission_root),
            "missionRuntimeRoot": rel_path(mission_runtime_root),
            "missionRuntimeIdCount": len(authored_mission_ids),
            "missionAreaTable": rel_path(DEFAULT_MISSION_AREA_TABLE),
            "levelBasicInfoTable": rel_path(DEFAULT_LEVEL_BASIC_INFO_TABLE),
            "taskRuntimeAuthority": {
                "schema": safe_text(task_authority.get("schema")),
                "source": safe_text(task_authority.get("source")),
                "classification": safe_text(
                    task_authority.get("classification")
                ),
                "validation": task_authority.get("validation") or {},
            },
            "startRuntimePolicy": {
                "schema": safe_text(start_policy.get("schema")),
                "source": safe_text(start_policy.get("source")),
                "classification": safe_text(
                    start_policy.get("classification")
                ),
                "validation": start_policy.get("validation") or {},
                "objectIdentityInputs": (
                    start_policy.get("discoveryPattern") or {}
                ).get("objectIdentityInputs"),
            },
            "manualSelfControl": {
                "schema": safe_text(manual_self_control.get("schema")),
                "source": safe_text(manual_self_control.get("source")),
                "classification": safe_text(
                    manual_self_control.get("classification")
                ),
                "validation": manual_self_control.get("validation") or {},
                "serializedObjectInputs": (
                    manual_self_control.get("discoveryPattern") or {}
                ).get("serializedObjectInputs"),
            },
            "activationControl": {
                "schema": safe_text(activation_control.get("schema")),
                "source": safe_text(activation_control.get("source")),
                "classification": safe_text(
                    activation_control.get("classification")
                ),
                "validation": activation_control.get("validation") or {},
                "serializedObjectInputs": (
                    activation_control.get("discoveryPattern") or {}
                ).get("serializedObjectInputs"),
            },
            "spawnerRoot": rel_path(spawner_root),
            "scriptTaskExtraInfo": rel_path(script_task_extra_info_path),
            "worldEntityRegistry": rel_path(world_entity_registry_path),
            "subGameTable": rel_path(subgame_table_path),
            "gameMechanicConditionTable": rel_path(
                game_mechanic_condition_table_path
            ),
            "dungeonTable": rel_path(dungeon_table_path),
            "structuredJsonRoot": rel_path(structured_json_root),
            "encounterRuntimeEvidence": {
                "runtimeType": ENCOUNTER_RUNTIME_TYPE,
                "dataType": ENCOUNTER_DATA_TYPE,
                "mappingId": ENCOUNTER_CONTROLLER_MAPPING_ID,
                "modulePrefixMethod": (
                    "Beyond.Gameplay.Core.LevelScriptModule."
                    "GetSaveKeyPrefixed"
                ),
                "modulePrefixMethodVa": "0x183be6a50",
                "moduleIdFieldOffset": "this+0x18",
                "gameAssemblySha256": ENCOUNTER_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": ENCOUNTER_METADATA_SHA256,
            },
            "modulePropertyFamilyEvidence": {
                "mappingId": LEVELSCRIPT_MODULE_PROPERTY_MAPPING_ID,
                "namespaceMethod": "Beyond.Gameplay.Core.LevelScriptModule.GetSaveKeyPrefixed",
                "moduleIdFieldOffset": "this+0x18",
                "gameAssemblySha256": (
                    LEVELSCRIPT_MODULE_PROPERTY_GAMEASSEMBLY_SHA256
                ),
                "globalMetadataSha256": (
                    LEVELSCRIPT_MODULE_PROPERTY_METADATA_SHA256
                ),
            },
        },
        "evidencePolicy": {
            "purpose": (
                "Locate the next static activation carrier for exact unresolved "
                "native Story receiver scripts."
            ),
            "noPromotion": (
                "This audit creates no mission/quest ownership, playback, branch, "
                "completion, or order edge."
            ),
            "manualBoundary": (
                "Manual start means the script does not use a decoded automatic "
                "start shape. Runtime/server state may still activate it through "
                "a carrier not serialized in the audited fields."
            ),
            "containerBoundary": (
                "A validated LevelData member-22 host proves loading/registration "
                "scope only. Even a mission-named host is context, not playback "
                "ownership."
            ),
            "missionAreaShellBoundary": (
                "A typed MissionRuntime MissionAreaTrackingInfo id joined through "
                "its authored sceneId and LevelBasicInfoTable.idNum to the exact "
                "level-specific MissionAreaTable.subDataParentId, then to a root "
                "in the same validated LevelData member-22 dictionary, proves only "
                "an authored mission shell. Shared mission unions stay shared; "
                "neither form proves activation, Story ownership, branch selection, "
                "or order."
            ),
            "encounterBoundary": (
                "The exact LevelScriptModule LsmPtr-prefixed "
                "EncounterBase<T>/EncounterData property contract and typed "
                "spawner id identify a reusable native encounter module and "
                "related original-data files. The module id can differ from "
                "the hosting LevelScript id; neither identity supplies a "
                "MissionRuntime owner, Story branch, or order edge."
            ),
            "modulePropertyFamilyBoundary": (
                "Every @module_suffix group is a generic serialized native "
                "module namespace census. Field names, value shapes, and "
                "related LevelData files are exact original-data context; "
                "module ids and repeated field families do not identify a "
                "mission, quest, Story owner, activation selector, branch, "
                "or chronology."
            ),
            "subGameBoundary": (
                "The hash-validated current binary proves that challenge-start "
                "interaction resolves the typed SubGame row, reads bindScriptId, "
                "looks up that LevelScript, and calls ManualStart. A SubGame row "
                "without dungeonMissionId still does not identify a mission or "
                "quest owner."
            ),
            "publicStateBoundary": (
                "SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY applies its exact scene, "
                "script, state, and completion tuple through the manager/container "
                "chain into LevelScriptRuntime.UpdateState. The packet carries no "
                "mission or quest identity and does not reveal the server-side "
                "branch that selected the state."
            ),
            "clientStartRequestBoundary": (
                "The hash-validated current client records ManualStart, enters "
                "PreStart, emits the typed CS start request, and enters "
                "PreStartActionRunning. The public network sender methods have "
                "zero direct current-AOT callers, and rows without an authored "
                "static carrier remain unresolved for mission/server selection."
            ),
            "dungeonSceneBoundary": (
                "An exact Dungeon.sceneId -> SubGame row proves that the "
                "receiver LevelScript lives in the scene loaded for that "
                "SubGame. It does not make a sibling receiver the bound script. "
                "Quest, mission, and prior-challenge conditions prove only "
                "SubGame availability, never Story ownership, activation, or "
                "order."
            ),
            "dungeonMissionBoundary": (
                "DungeonSubGameData.dungeonMissionId identifies the mission "
                "shell for that SubGame and its exact bindScriptId. A Story "
                "receiver that is only a sibling script in the same scene "
                "does not inherit that mission, even when its nominal Story "
                "name happens to match."
            ),
            "literalMissionIdBoundary": (
                "An exact MemoryPack string token proves only that the literal "
                "id of an original MissionRuntimeAsset exists somewhere in the "
                "LevelScript blob. Story-only shell ids are excluded. Absence "
                "closes literal-constant carriers, not dynamic, indirect, or "
                "server-authored activation."
            ),
            "structuredIdentityBoundary": (
                "Only exact LevelScript-identity and mission/quest-identity "
                "fields carried by the same authored JSON record are counted. "
                "Filename, ancestor, neighboring-record, OCR, and manual-name "
                "proximity create no identity or ownership edge."
            ),
            "taskRuntimeAuthorityBoundary": (
                "The hash-validated current binary and protobuf schemas prove "
                "that LevelScript task traffic is keyed by sceneNumId, scriptId, "
                "taskId, and condition/progress data. No packet co-carries a "
                "mission, quest, or Story identity, so server task lifecycle "
                "does not supply the missing ownership edge."
            ),
            "taskProgressPropertyBoundary": (
                "Exact lt:p/lt:mp LevelData property pairs persist per-condition "
                "task progress. They repeat task/condition identity only and do "
                "not identify a mission owner or playback order."
            ),
            "sameWithActiveBoundary": (
                "The hash-validated current binary proves generically that an "
                "Active, unfinished LevelScript with startType SameWithActive "
                "enters the internal PreStart state without a start-area or "
                "manual-start gate. It does not identify what mission/server "
                "transition made the script Active, or order its Story actions."
            ),
            "manualSelfControlBoundary": (
                "The hash-validated binary and metadata prove the generic "
                "CURRENT_LEVEL_ID/CURRENT_SCRIPT_ID ManualStart target. It is "
                "promoted only when the original serialized row carries both "
                "operands and an authored event-header link; this proves local "
                "self-start, not mission ownership or cross-Story order."
            ),
            "activePhaseReceiverBoundary": (
                "An exact receiver-header id is joined only to the matching "
                "header in that original LevelScript. The current binary proves "
                "Setup registration and Active-phase enabling as a general "
                "runtime rule. This establishes availability, not the public-"
                "Active producer, event occurrence, mission owner, branch, or "
                "cross-Story chronology."
            ),
            "teleportFinishCorrelationBoundary": (
                "The current binary compares the typed listener actionId with "
                "TeleportParam.actionId at runtime. A complete original "
                "LevelScript corpus scan classifies exact serialized occurrences "
                "without object allowlists. UID/text/raw-byte matches remain "
                "candidates only and create no producer, mission, branch, or "
                "Story-order edge."
            ),
            "taskConditionBoundary": (
                "A completely decoded task map proves authored task evaluation "
                "requirements inside this LevelScript. Entity, spawner, dialog, "
                "area, property, stage, and mission operands are dependencies "
                "or completion gates, not mission ownership, activation order, "
                "or proof that the task executes."
            ),
            "taskOperandBoundary": (
                "Exact operand-source resolution identifies the authored object "
                "evaluated by a task condition. Only an exact typed "
                "MissionRuntime objective consuming the same operand could add "
                "a mission-side cross-reference; source identity alone proves "
                "no mission ownership or execution order."
            ),
            "taskConsumerBoundary": (
                "An exact CheckLevelScriptTaskFinished tuple would prove that "
                "one MissionRuntime objective waits on this task. It would be a "
                "mission-side completion dependency, not proof that the task "
                "activates or owns any Story playback in the receiver script."
            ),
            "nominalMissionHostBoundary": (
                "Story filename-derived nominalMissionId values are candidate "
                "labels only. A validated mission-named LevelData member-22 "
                "dictionary can close container membership for that candidate, "
                "but same-level exclusion or inclusion alone is not runtime "
                "activation, Story ownership, or chronology."
            ),
        },
        "counts": {
            "structuredIdentityCandidateFiles": (
                structured_identity_census["candidateFileCount"]
            ),
            "structuredIdentityVisitedRecords": (
                structured_identity_census["visitedRecordCount"]
            ),
            "structuredDirectIdentityCarriers": (
                structured_identity_census["directCarrierCount"]
            ),
            "structuredReceiverIdentityMatches": (
                structured_identity_census["receiverMatchCount"]
            ),
            "structuredUnreviewedIdentityCarriers": sum(
                row.get("classification")
                == "unreviewed_direct_identity_carrier"
                for row in structured_identity_census.get("rows") or []
            ),
            "receiverNodes": sum(row["receiverNodeCount"] for row in rows),
            "receiverScripts": len(rows),
            "receiverToStoryPlacements": sum(
                row["receiverToStoryPlacementCount"] for row in rows
            ),
            "storyKeys": len(
                {story_key for row in rows for story_key in row["storyKeys"]}
            ),
            "activationClasses": dict(sorted(classes.items())),
            "authoredPropertyContracts": {
                "scriptsWithAuthoredProperties": sum(
                    bool(row["authoredPropertyContract"]["authoredNames"])
                    for row in rows
                ),
                "scriptsWithExactMissionObservedProperties": sum(
                    bool(row["authoredPropertyContract"]["missionObservedNames"])
                    for row in rows
                ),
                "recurringNames": [
                    {"name": name, "scriptCount": count}
                    for name, count in sorted(
                        authored_property_scripts.items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                    if count > 1
                ],
            },
            "startTypes": dict(sorted(start_types.items())),
            "scriptsWithValidatedSameWithActivePolicy": sum(
                bool(row.get("startRuntimePolicy")) for row in rows
            ),
            "storyKeysWithValidatedSameWithActivePolicy": len({
                story_key
                for row in rows
                if row.get("startRuntimePolicy")
                for story_key in row.get("storyKeys") or []
            }),
            "scriptsWithValidatedManualSelfControl": sum(
                bool(row.get("manualSelfControl")) for row in rows
            ),
            "storyKeysWithValidatedManualSelfControl": len({
                story_key
                for row in rows
                if row.get("manualSelfControl")
                for story_key in row.get("storyKeys") or []
            }),
            "scriptsWithValidatedPublicStateControlContract": sum(
                bool(row.get("publicStateControl")) for row in rows
            ),
            "scriptsWithValidatedClientStartRequestLifecycle": sum(
                bool(row.get("clientStartRequestControl")) for row in rows
            ),
            "scriptsWithValidatedActivePhaseReceivers": sum(
                (row.get("activePhaseReceiverControl") or {}).get("status")
                == "validated"
                for row in rows
            ),
            "scriptsWithValidatedClientActiveRequestSelector": sum(
                (row.get("clientActiveRequestControl") or {}).get("status")
                == "validated"
                for row in rows
            ),
            "scriptsWithClientProducedActiveRequest": sum(
                (row.get("clientActiveRequestControl") or {}).get(
                    "clientProducesActiveRequest"
                )
                is True
                for row in rows
            ),
            "scriptsWithValidatedActiveShapeGate": sum(
                (row.get("clientActiveRequestControl") or {}).get(
                    "spatialGateStatus"
                )
                == "validated_runtime_position_dependent"
                for row in rows
            ),
            "authoredActiveShapeCount": sum(
                int(
                    ((row.get("clientActiveRequestControl") or {}).get(
                        "activeShapeList"
                    ) or {}).get("count")
                    or 0
                )
                for row in rows
            ),
            "authoredActiveShapeTypes": dict(sorted(Counter(
                safe_text(shape.get("type"))
                for row in rows
                for shape in (
                    ((row.get("clientActiveRequestControl") or {}).get(
                        "activeShapeList"
                    ) or {}).get("shapes")
                    or []
                )
                if isinstance(shape, dict) and safe_text(shape.get("type"))
            ).items())),
            "clientActiveRequestLevelScriptTypes": dict(sorted(Counter(
                safe_text((row.get("clientActiveRequestControl") or {}).get(
                    "levelScriptTypeName"
                ))
                for row in rows
                if safe_text((row.get("clientActiveRequestControl") or {}).get(
                    "levelScriptTypeName"
                ))
            ).items())),
            "activePhaseReceiverHeaders": sum(
                (row.get("activePhaseReceiverControl") or {}).get(
                    "resolvedHeaderCount", 0
                )
                for row in rows
                if (row.get("activePhaseReceiverControl") or {}).get("status")
                == "validated"
            ),
            "storyKeysWithValidatedActivePhaseReceivers": len({
                story_key
                for row in rows
                if (row.get("activePhaseReceiverControl") or {}).get("status")
                == "validated"
                for story_key in row.get("storyKeys") or []
            }),
            "teleportFinishCorpusFiles": teleport_finish_census.get(
                "candidateFileCount", 0
            ),
            "teleportFinishCorpusListeners": teleport_finish_census.get(
                "listenerCount", 0
            ),
            "teleportFinishDistinctFilters": teleport_finish_census.get(
                "distinctFilterCount", 0
            ),
            "teleportFinishRuntimeOnlyFilters": teleport_finish_census.get(
                "runtimeOnlyFilterCount", 0
            ),
            "teleportFinishSerializedActionCandidates": (
                teleport_finish_census.get("serializedActionCandidateCount", 0)
            ),
            "receiverScriptsWithTeleportFinishCorrelation": sum(
                bool(row.get("teleportFinishCorrelations")) for row in rows
            ),
            "receiverStoryKeysWithTeleportFinishCorrelation": len({
                story_key
                for row in rows
                if row.get("teleportFinishCorrelations")
                for story_key in row.get("storyKeys") or []
            }),
            "scriptsWithRuntimeRequestButNoStaticCarrier": sum(
                row.get("activationClass")
                == "manual_start_runtime_request_no_static_carrier"
                for row in rows
            ),
            "scriptsWithValidatedSubGameInteractionStart": sum(
                bool(row.get("subGameStartControl")) for row in rows
            ),
            "storyKeysWithValidatedSubGameInteractionStart": len({
                story_key
                for row in rows
                if row.get("subGameStartControl")
                for story_key in row.get("storyKeys") or []
            }),
            "levelDataHostShapes": dict(sorted(host_shapes.items())),
            "scriptsWithMissionNamedHost": sum(
                any(host.get("missionNamedHost") for host in row["levelDataHosts"])
                for row in rows
            ),
            "scriptsWithMissionAreaLevelDataShellContext": sum(
                bool(row.get("missionAreaLevelDataShellContext"))
                for row in rows
            ),
            "scriptsWithUniqueMissionAreaLevelDataShellContext": sum(
                (row.get("missionAreaLevelDataShellContext") or {}).get(
                    "status"
                )
                == "unique"
                for row in rows
            ),
            "scriptsWithSharedMissionAreaLevelDataShellContext": sum(
                (row.get("missionAreaLevelDataShellContext") or {}).get(
                    "status"
                )
                == "shared"
                for row in rows
            ),
            "missionAreaLevelDataShellMissionPlacements": sum(
                len(
                    (row.get("missionAreaLevelDataShellContext") or {}).get(
                        "hostMissionIds"
                    )
                    or []
                )
                for row in rows
            ),
            "modulePropertyFamilyCount": sum(
                len(row.get("modulePropertyFamilies") or [])
                for row in rows
            ),
            "scriptsWithModulePropertyFamilies": sum(
                bool(row.get("modulePropertyFamilies")) for row in rows
            ),
            "modulePropertyFamilyRelatedFiles": len({
                safe_text(related.get("sourceFile"))
                for row in rows
                for family in row.get("modulePropertyFamilies") or []
                for related in family.get("relatedFiles") or []
                if isinstance(related, dict) and safe_text(related.get("sourceFile"))
            }),
            "modulePropertyFamilyFeatures": dict(sorted(Counter(
                feature
                for row in rows
                for family in row.get("modulePropertyFamilies") or []
                for feature in (family.get("pattern") or {}).get("features") or []
            ).items())),
            "scriptsWithEncounterControllerContract": sum(
                bool(row.get("encounterControllerContexts")) for row in rows
            ),
            "encounterControllerContracts": sum(
                len(row.get("encounterControllerContexts") or [])
                for row in rows
            ),
            "encounterControllerContractsWithForeignModuleId": sum(
                not context.get("moduleIdMatchesReceiverScript")
                for row in rows
                for context in row.get("encounterControllerContexts") or []
            ),
            "storyKeysWithEncounterControllerContract": len({
                story_key
                for row in rows
                if row.get("encounterControllerContexts")
                for story_key in row.get("storyKeys") or []
            }),
            "encounterControllerRelatedFiles": len({
                safe_text(related.get("sourceFile"))
                for row in rows
                for context in row.get("encounterControllerContexts") or []
                for related in context.get("relatedFiles") or []
                if safe_text(related.get("sourceFile"))
            }),
            "scriptsWithValidatedNominalMissionHostExclusion": sum(
                (
                    row.get("nominalMissionHostComparison") or {}
                ).get("classification")
                == "validated_nominal_mission_hosts_exclude_receiver_script"
                for row in rows
            ),
            "blackStoryKeysWithValidatedNominalMissionHostExclusion": len({
                candidate.get("storyKey")
                for row in rows
                if (
                    row.get("nominalMissionHostComparison") or {}
                ).get("classification")
                == "validated_nominal_mission_hosts_exclude_receiver_script"
                for candidate in (
                    row.get("nominalMissionHostComparison") or {}
                ).get("storyCandidates") or []
                if candidate.get("storyKind") == "black"
                and candidate.get("storyKey")
            }),
            "blackStoryKeysWithSubGameBindingAndNoNominalMissionHost": len({
                candidate.get("storyKey")
                for row in rows
                if row.get("subGameBindings")
                and (
                    row.get("nominalMissionHostComparison") or {}
                ).get("classification")
                == "no_same_level_nominal_mission_host"
                for candidate in (
                    row.get("nominalMissionHostComparison") or {}
                ).get("storyCandidates") or []
                if candidate.get("storyKind") == "black"
                and candidate.get("storyKey")
            }),
            "blackStoryKeysWithClosedStaticNominalMissionRoute": len({
                candidate.get("storyKey")
                for row in rows
                if (
                    (
                        row.get("nominalMissionHostComparison") or {}
                    ).get("classification")
                    == (
                        "validated_nominal_mission_hosts_exclude_"
                        "receiver_script"
                    )
                    or (
                        row.get("subGameBindings")
                        and (
                            row.get("nominalMissionHostComparison") or {}
                        ).get("classification")
                        == "no_same_level_nominal_mission_host"
                    )
                )
                for candidate in (
                    row.get("nominalMissionHostComparison") or {}
                ).get("storyCandidates") or []
                if candidate.get("storyKind") == "black"
                and candidate.get("storyKey")
            }),
            "scriptsWithIncomingLiteralCrossControl": sum(
                any(
                    not control.get("selfTarget")
                    for control in row["incomingLiteralManualControls"]
                )
                for row in rows
            ),
            "scriptsWithSubGameBinding": sum(
                bool(row["subGameBindings"]) for row in rows
            ),
            "scriptsWithExactDungeonSceneContext": sum(
                bool(row["dungeonSceneContexts"]) for row in rows
            ),
            "storyKeysWithExactDungeonSceneContext": len(
                {
                    story_key
                    for row in rows
                    if row["dungeonSceneContexts"]
                    for story_key in row["storyKeys"]
                }
            ),
            "exactDungeonSceneContextPlacements": sum(
                len(row["dungeonSceneContexts"]) for row in rows
            ),
            "exactDungeonSceneIds": len(
                {
                    safe_text(context.get("sceneId"))
                    for row in rows
                    for context in row["dungeonSceneContexts"]
                    if safe_text(context.get("sceneId"))
                }
            ),
            "directBoundDungeonSceneContextPlacements": sum(
                bool(context.get("receiverIsBoundScript"))
                for row in rows
                for context in row["dungeonSceneContexts"]
            ),
            "siblingDungeonSceneContextPlacements": sum(
                not context.get("receiverIsBoundScript")
                for row in rows
                for context in row["dungeonSceneContexts"]
            ),
            "dungeonSceneContextAvailabilityAssociations": sum(
                len(context.get("associations") or [])
                for row in rows
                for context in row["dungeonSceneContexts"]
            ),
            "scriptsWithDungeonMissionShellContext": sum(
                any(
                    context.get("dungeonMissionContext")
                    for context in row["dungeonSceneContexts"]
                )
                for row in rows
            ),
            "storyKeysWithDungeonMissionShellContext": len(
                {
                    story_key
                    for row in rows
                    if any(
                        context.get("dungeonMissionContext")
                        for context in row["dungeonSceneContexts"]
                    )
                    for story_key in row["storyKeys"]
                }
            ),
            "dungeonMissionShellContextPlacements": sum(
                bool(context.get("dungeonMissionContext"))
                for row in rows
                for context in row["dungeonSceneContexts"]
            ),
            "scriptsWithMissionRuntimeObjectiveConsumer": sum(
                bool(row["missionRuntimeScriptConsumers"]) for row in rows
            ),
            "missionObservedLevelScriptContextMissions": len({
                safe_text(consumer.get("missionId"))
                for row in rows
                for consumer in row["missionRuntimeScriptConsumers"]
                if safe_text(consumer.get("missionId"))
            }),
            "missionObservedLevelScriptContextStoryKeys": len({
                story_key
                for row in rows
                if row["missionRuntimeScriptConsumers"]
                for story_key in row["storyKeys"]
            }),
            "missionObservedLevelScriptContextPlacements": sum(
                len(row["storyKeys"])
                * len(row["missionRuntimeScriptConsumers"])
                for row in rows
            ),
            "relatedOriginalFilePlacements": sum(
                len(row.get("relatedOriginalFiles") or []) for row in rows
            ),
            "distinctRelatedOriginalFiles": len({
                related.get("sourceFile")
                for row in rows
                for related in row.get("relatedOriginalFiles") or []
                if related.get("sourceFile")
            }),
            "scriptsWithStartShapes": sum(
                bool((row.get("levelScript") or {}).get("startShapeListShapes"))
                for row in rows
            ),
            "scriptsWithExactStartShapeMissionAreaMatch": sum(
                bool(row["startShapeMissionAreaMatches"]) for row in rows
            ),
            "scriptsWithTaskMap": sum(
                safe_text((row.get("levelScript") or {}).get("taskMapStatus"))
                == "present"
                for row in rows
            ),
            "scriptsWithFullyDecodedTaskMap": sum(
                bool(row.get("decodedTaskMap")) for row in rows
            ),
            "scriptsWithValidatedTaskRuntimeAuthority": sum(
                bool(row.get("decodedTaskMap"))
                and (
                    (row.get("taskRuntimeAuthority") or {}).get(
                        "validation", {}
                    ).get("status")
                    == "validated"
                )
                for row in rows
            ),
            "decodedTaskCount": sum(
                len((row.get("decodedTaskMap") or {}).get("tasks") or [])
                for row in rows
            ),
            "decodedTasksWithCompleteProgressPropertyContract": sum(
                (
                    task.get("progressPropertyContract") or {}
                ).get("status")
                == "validated"
                for row in rows
                for task in (row.get("decodedTaskMap") or {}).get("tasks") or []
            ),
            "decodedTaskProgressPropertyPlacements": sum(
                (
                    task.get("progressPropertyContract") or {}
                ).get("matchedPropertyCount", 0)
                for row in rows
                for task in (row.get("decodedTaskMap") or {}).get("tasks") or []
            ),
            "decodedTaskConditionCount": sum(task_condition_types.values()),
            "decodedTaskConditionTypes": dict(
                sorted(task_condition_types.items())
            ),
            "decodedTaskConditionsWithExactOperandSource": (
                task_conditions_with_operand_sources
            ),
            "decodedTaskOperandSourceTypes": dict(
                sorted(task_operand_source_types.items())
            ),
            "decodedTaskConditionsWithMissionRuntimeOperandConsumer": (
                task_conditions_with_mission_consumers
            ),
            "decodedTaskMissionRuntimeOperandConsumerTypes": dict(
                sorted(task_mission_consumer_types.items())
            ),
            "decodedTasksWithMissionRuntimeTaskConsumer": (
                tasks_with_mission_consumers
            ),
            "decodedTasksWithExtraInfo": sum(
                bool(task.get("taskExtraInfo"))
                for row in rows
                for task in (row.get("decodedTaskMap") or {}).get("tasks") or []
            ),
            "decodedTasksWithSubGameMainTaskBinding": sum(
                bool(task.get("subGameMainTaskBindings"))
                for row in rows
                for task in (row.get("decodedTaskMap") or {}).get("tasks") or []
            ),
            "scriptsWithSerializedMissionRuntimeIdToken": sum(
                bool(row["serializedMissionRuntimeIdTokens"]) for row in rows
            ),
            "nonSubGameScriptsWithSerializedMissionRuntimeIdToken": sum(
                bool(row["serializedMissionRuntimeIdTokens"])
                and not row["subGameBindings"]
                for row in rows
            ),
            "nonSubGameTaskMapScriptsWithSerializedMissionRuntimeIdToken": sum(
                bool(row["serializedMissionRuntimeIdTokens"])
                and not row["subGameBindings"]
                and safe_text(
                    (row.get("levelScript") or {}).get("taskMapStatus")
                )
                == "present"
                for row in rows
            ),
        },
        "structuredIdentityCarrierCensus": structured_identity_census,
        "teleportFinishCorrelationCensus": teleport_finish_census,
        "missionAreaLevelDataShellCensus": {
            "receiverPairCount": len(receiver_pairs),
            "contextCount": len(mission_area_leveldata_shells),
            "uniqueContextCount": sum(
                context.get("status") == "unique"
                for context in mission_area_leveldata_shells.values()
            ),
            "sharedContextCount": sum(
                context.get("status") == "shared"
                for context in mission_area_leveldata_shells.values()
            ),
            "missionPlacementCount": sum(
                len(context.get("hostMissionIds") or [])
                for context in mission_area_leveldata_shells.values()
            ),
            "validation": mission_area_shell_validation,
        },
        "manualControlIndexSummary": manual_control_index.summary,
        "rows": rows,
    }


def publish_to_pipeline_index(
    index_payload: dict[str, Any],
    report: dict[str, Any],
    *,
    mission_root: Path | None = None,
) -> int:
    """Publish compact debug annotations without adding graph edges.

    Exact typed MissionRuntime operands are also copied onto their mission's
    Story-order payload as non-owning context.  This makes the source files
    inspectable beside the affected Story keys while preserving the unknown
    activation, property-writer, and ordering boundaries.
    """
    coverage = index_payload.get("storyCoverage")
    if not isinstance(coverage, dict):
        return 0
    shell_validation = (
        report.get("missionAreaLevelDataShellCensus") or {}
    ).get("validation") or {}
    if (
        shell_validation
        and shell_validation.get("status") != "validated"
    ):
        failure = (shell_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "mission-area LevelData shell validation failed: "
            f"validator={failure.get('validator')}; "
            f"gate={failure.get('gate')}; "
            f"identity={failure.get('identity')}; "
            f"source={failure.get('sourceFile')}; "
            f"expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}; "
            f"sourceHashes={failure.get('sourceHashes')!r}"
        )
    # Keep a compact Story-key lookup beside the full receiver nodes.  The
    # WebUI uses this to show exact native receiver files on unassigned Story
    # cards without copying the entire activation contract into every card.
    coverage["nativeReceiverStoryContextIndex"] = _receiver_story_context_index(
        report
    )
    row_index = {
        (safe_text(row.get("levelId")), safe_text(row.get("scriptId"))): row
        for row in report.get("rows") or []
        if isinstance(row, dict)
    }
    annotated = 0
    for node in coverage.get("missionlessNativeRuntimeNodes") or []:
        if not isinstance(node, dict):
            continue
        selector = node.get("selector") or {}
        row = row_index.get(
            (
                safe_text(selector.get("levelId")),
                safe_text(selector.get("listenerScriptId")),
            )
        )
        if not row:
            continue
        levelscript = row.get("levelScript") or {}
        node["activationFrontier"] = {
            "activationClass": safe_text(row.get("activationClass")),
            "startTypeName": safe_text(levelscript.get("startTypeName")),
            "startShapeListStatus": safe_text(
                levelscript.get("startShapeListStatus")
            ),
            "startShapeListCount": levelscript.get("startShapeListCount"),
            "activeShapeList": levelscript.get("activeShapeList") or {},
            "activeShapeListStatus": safe_text(
                levelscript.get("activeShapeListStatus")
            ),
            "activeShapeListCount": levelscript.get("activeShapeListCount"),
            "taskMapStatus": safe_text(levelscript.get("taskMapStatus")),
            "taskMapCount": levelscript.get("taskMapCount"),
            "levelDataHosts": [
                {
                    "fileName": safe_text(host.get("fileName")),
                    "dictionaryEntryCount": host.get("dictionaryEntryCount"),
                    "hostMissionId": host.get("hostMissionId"),
                }
                for host in row.get("levelDataHosts") or []
                if isinstance(host, dict)
            ],
            "missionAreaLevelDataShellContext": {
                "status": safe_text(
                    (row.get("missionAreaLevelDataShellContext") or {}).get(
                        "status"
                    )
                ),
                "hostMissionIds": [
                    safe_text(value)
                    for value in (
                        row.get("missionAreaLevelDataShellContext") or {}
                    ).get("hostMissionIds")
                    or []
                    if safe_text(value)
                ],
                "hostCount": len(
                    (row.get("missionAreaLevelDataShellContext") or {}).get(
                        "hosts"
                    )
                    or []
                ),
                "ownership": False,
                "activation": False,
                "orderEvidence": False,
            }
            if row.get("missionAreaLevelDataShellContext")
            else {},
            "modulePropertyFamilies": [
                {
                    "classification": safe_text(
                        family.get("classification")
                    ),
                    "mappingId": safe_text(family.get("mappingId")),
                    "runtimeType": safe_text(family.get("runtimeType")),
                    "moduleId": safe_text(family.get("moduleId")),
                    "receiverScriptId": safe_text(
                        family.get("receiverScriptId")
                    ),
                    "moduleIdMatchesReceiverScript": bool(
                        family.get("moduleIdMatchesReceiverScript")
                    ),
                    "familyKey": safe_text(family.get("familyKey")),
                    "pattern": family.get("pattern") or {},
                    "propertySignatures": [
                        {
                            "suffix": safe_text(signature.get("suffix")),
                            "valueType": signature.get("valueType"),
                            "atomCount": signature.get("atomCount"),
                            "atomShapes": signature.get("atomShapes") or [],
                        }
                        for signature in family.get("propertySignatures") or []
                        if isinstance(signature, dict)
                    ],
                    "relatedFiles": [
                        {
                            "kind": safe_text(related.get("kind")),
                            "sourceFile": safe_text(
                                related.get("sourceFile")
                            ),
                            "relationship": safe_text(
                                related.get("relationship")
                            ),
                        }
                        for related in family.get("relatedFiles") or []
                        if isinstance(related, dict)
                        and safe_text(related.get("sourceFile"))
                    ],
                    "missionOwnerStatus": "unresolved",
                    "storyBinding": False,
                    "orderEvidence": False,
                    "evidenceBoundary": safe_text(
                        family.get("evidenceBoundary")
                    ),
                }
                for family in row.get("modulePropertyFamilies") or []
                if isinstance(family, dict)
            ],
            "encounterControllerContexts": [
                {
                    "classification": safe_text(
                        context.get("classification")
                    ),
                    "mappingId": safe_text(context.get("mappingId")),
                    "runtimeType": safe_text(context.get("runtimeType")),
                    "dataType": safe_text(context.get("dataType")),
                    "moduleId": safe_text(context.get("moduleId")),
                    "receiverScriptId": safe_text(
                        context.get("receiverScriptId")
                    ),
                    "moduleIdMatchesReceiverScript": bool(
                        context.get("moduleIdMatchesReceiverScript")
                    ),
                    "spawnerId": safe_text(context.get("spawnerId")),
                    "relatedFiles": [
                        {
                            "kind": safe_text(related.get("kind")),
                            "sourceFile": safe_text(
                                related.get("sourceFile")
                            ),
                            "relationship": safe_text(
                                related.get("relationship")
                            ),
                        }
                        for related in context.get("relatedFiles") or []
                        if isinstance(related, dict)
                        and safe_text(related.get("sourceFile"))
                    ],
                    "missionOwnerStatus": "unresolved",
                    "storyBinding": False,
                    "orderEvidence": False,
                    "evidenceBoundary": safe_text(
                        context.get("evidenceBoundary")
                    ),
                }
                for context in row.get("encounterControllerContexts") or []
                if isinstance(context, dict)
            ],
            "nominalMissionHostComparison": {
                "classification": safe_text(
                    (
                        row.get("nominalMissionHostComparison") or {}
                    ).get("classification")
                ),
                "storyCandidates": (
                    row.get("nominalMissionHostComparison") or {}
                ).get("storyCandidates") or [],
                "sameLevelMissionNamedHosts": [
                    {
                        "missionId": safe_text(host.get("missionId")),
                        "fileName": safe_text(host.get("fileName")),
                        "dictionaryValidated": bool(
                            host.get("dictionaryValidated")
                        ),
                        "dictionaryEntryCount":
                            host.get("dictionaryEntryCount"),
                        "receiverScriptPresent": bool(
                            host.get("receiverScriptPresent")
                        ),
                    }
                    for host in (
                        row.get("nominalMissionHostComparison") or {}
                    ).get("sameLevelMissionNamedHosts") or []
                    if isinstance(host, dict)
                ],
                "missionOwnerStatus": "unresolved",
                "storyBinding": False,
                "orderEvidence": False,
                "missionGraphAction": "none",
            },
            "subGameIds": [
                safe_text(binding.get("subGameId"))
                for binding in row.get("subGameBindings") or []
                if isinstance(binding, dict) and safe_text(binding.get("subGameId"))
            ],
            "dungeonSceneContexts": [
                {
                    "subGameId": safe_text(context.get("subGameId")),
                    "sceneId": safe_text(context.get("sceneId")),
                    "levelId": safe_text(context.get("levelId")),
                    "dungeonSeriesId": safe_text(
                        context.get("dungeonSeriesId")
                    ),
                    "bindScriptId": safe_text(context.get("bindScriptId")),
                    "receiverIsBoundScript": bool(
                        context.get("receiverIsBoundScript")
                    ),
                    "dungeonMissionContext": (
                        {
                            "missionId": safe_text(
                                (
                                    context.get("dungeonMissionContext")
                                    or {}
                                ).get("missionId")
                            ),
                            "ownership": False,
                            "playback": False,
                            "finding": safe_text(
                                (
                                    context.get("dungeonMissionContext")
                                    or {}
                                ).get("finding")
                            ),
                        }
                        if context.get("dungeonMissionContext")
                        else None
                    ),
                    "associations": [
                        {
                            "relation": safe_text(
                                association.get("relation")
                            ),
                            "targetType": safe_text(
                                association.get("targetType")
                            ),
                            "targetId": safe_text(
                                association.get("targetId")
                            ),
                            "conditionTypeName": safe_text(
                                association.get("conditionTypeName")
                            ),
                            "ownership": False,
                            "finding": safe_text(
                                association.get("finding")
                            ),
                        }
                        for association in context.get("associations") or []
                        if isinstance(association, dict)
                    ],
                    "ownership": False,
                    "storyBinding": False,
                    "evidenceBoundary": safe_text(
                        context.get("evidenceBoundary")
                    ),
                }
                for context in row.get("dungeonSceneContexts") or []
                if isinstance(context, dict)
            ],
            "incomingLiteralCrossControlCount": sum(
                not control.get("selfTarget")
                for control in row.get("incomingLiteralManualControls") or []
                if isinstance(control, dict)
            ),
            "incomingManualControls": [
                {
                    "sourceLevelId": safe_text(
                        control.get("sourceLevelId")
                    ),
                    "sourceScriptId": safe_text(
                        control.get("sourceScriptId")
                    ),
                    "localId": control.get("localId"),
                    "action": safe_text(control.get("action")),
                    "selfTarget": bool(control.get("selfTarget")),
                    "targetResolution": safe_text(
                        control.get("targetResolution")
                    ),
                    "parameterSources": control.get("parameterSources") or {},
                    "headerLinkedEvent": control.get("headerLinkedEvent") or {},
                    "sourceFile": safe_text(control.get("sourceFile")),
                }
                for control in row.get("incomingLiteralManualControls") or []
                if isinstance(control, dict)
            ],
            "missionRuntimeObjectiveConsumerCount": len(
                row.get("missionRuntimeScriptConsumers") or []
            ),
            "authoredPropertyContract": row.get("authoredPropertyContract") or {},
            "missionRuntimeScriptConsumers": [
                {
                    "relation": (
                        "mission_runtime_objective_references_level_script"
                    ),
                    "missionId": safe_text(consumer.get("missionId")),
                    "questId": safe_text(consumer.get("questId")),
                    "objectiveIndex": consumer.get("objectiveIndex"),
                    "conditionTypes": [
                        safe_text(condition_type)
                        for condition_type in consumer.get("conditionTypes") or []
                        if safe_text(condition_type)
                    ],
                    "propertyKeys": [
                        safe_text(key)
                        for key in consumer.get("propertyKeys") or []
                        if safe_text(key)
                    ],
                    "sourceFile": safe_text(consumer.get("sourceFile")),
                    "pipelineSourceFile": safe_text(
                        consumer.get("pipelineSourceFile")
                    ),
                    "ownership": False,
                    "activation": False,
                    "storyPlayback": False,
                    "evidenceBoundary": (
                        "The typed MissionRuntime objective reads this "
                        "LevelScript as an operand. It does not prove that the "
                        "quest starts or owns Story playback, or that playback "
                        "sets the observed script property."
                    ),
                }
                for consumer in row.get("missionRuntimeScriptConsumers") or []
                if isinstance(consumer, dict)
            ],
            "exactStartShapeMissionAreaMatchCount": len(
                row.get("startShapeMissionAreaMatches") or []
            ),
            "serializedMissionRuntimeIdTokens": (
                row.get("serializedMissionRuntimeIdTokens") or []
            ),
            "decodedTaskMap": row.get("decodedTaskMap"),
            "taskRuntimeAuthority": row.get("taskRuntimeAuthority") or {},
            "startRuntimePolicy": row.get("startRuntimePolicy") or {},
            "manualSelfControl": row.get("manualSelfControl") or {},
            "publicStateControl": row.get("publicStateControl") or {},
            "clientStartRequestControl": (
                row.get("clientStartRequestControl") or {}
            ),
            "activePhaseReceiverControl": (
                row.get("activePhaseReceiverControl") or {}
            ),
            "clientActiveRequestControl": (
                row.get("clientActiveRequestControl") or {}
            ),
            "subGameStartControl": row.get("subGameStartControl") or {},
            "relatedOriginalFiles": [
                {
                    "kind": safe_text(related.get("kind")),
                    "sourceFile": safe_text(related.get("sourceFile")),
                    "relationship": safe_text(
                        related.get("relationship")
                    ),
                    "sha256": safe_text(related.get("sha256")),
                }
                for related in row.get("relatedOriginalFiles") or []
                if isinstance(related, dict)
                and safe_text(related.get("sourceFile"))
            ],
        }
        annotated += 1

    contexts_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in report.get("rows") or []:
        if not isinstance(row, dict):
            continue
        level_id = safe_text(row.get("levelId"))
        script_id = safe_text(row.get("scriptId"))
        story_keys = sorted({
            safe_text(key) for key in row.get("storyKeys") or [] if safe_text(key)
        })
        if not level_id or not script_id or not story_keys:
            continue
        related_files = [
            {
                "kind": safe_text(related.get("kind")),
                "sourceFile": safe_text(related.get("sourceFile")),
                "relationship": safe_text(related.get("relationship")),
                "sha256": safe_text(related.get("sha256")),
            }
            for related in row.get("relatedOriginalFiles") or []
            if isinstance(related, dict) and safe_text(related.get("sourceFile"))
        ]
        for consumer in row.get("missionRuntimeScriptConsumers") or []:
            if not isinstance(consumer, dict):
                continue
            mission_id = safe_text(consumer.get("missionId"))
            if not mission_id:
                continue
            contexts_by_mission[mission_id].append({
                "relation": "mission_objective_observes_story_receiver_levelscript",
                "missionId": mission_id,
                "questId": safe_text(consumer.get("questId")),
                "objectiveIndex": consumer.get("objectiveIndex"),
                "levelId": level_id,
                "scriptId": script_id,
                "storyKeys": story_keys,
                "eventNames": row.get("eventNames") or [],
                "listenerHeaderLocalIds": row.get("listenerHeaderLocalIds") or [],
                "conditionTypes": consumer.get("conditionTypes") or [],
                "propertyKeys": consumer.get("propertyKeys") or [],
                "propertyWriterStatus": "unresolved",
                "ownership": False,
                "activation": False,
                "storyPlayback": False,
                "orderEvidence": False,
                "relatedOriginalFiles": related_files,
                "evidenceBoundary": (
                    "The original typed MissionRuntime objective reads the same "
                    "(level, LevelScript) that contains exact native Story playback. "
                    "This attaches mission context and original files only: it does "
                    "not prove that the quest starts or owns playback, that playback "
                    "writes the observed property, or any Story order."
                ),
            })

    published_contexts = 0
    published_mission_named_contexts = 0
    published_mission_area_contexts = 0
    published_receiver_story_contexts = 0
    if mission_root is not None:
        mission_summaries = {
            safe_text(row.get("id")): row
            for row in index_payload.get("missions") or []
            if isinstance(row, dict) and safe_text(row.get("id"))
        }
        mission_named_contexts_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
        mission_area_contexts_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in report.get("rows") or []:
            if not isinstance(row, dict):
                continue
            level_id = safe_text(row.get("levelId"))
            script_id = safe_text(row.get("scriptId"))
            story_keys = sorted({
                safe_text(key)
                for key in row.get("storyKeys") or []
                if safe_text(key)
            })
            if not level_id or not script_id or not story_keys:
                continue
            related_files = [
                {
                    "kind": safe_text(related.get("kind")),
                    "sourceFile": safe_text(related.get("sourceFile")),
                    "relationship": safe_text(related.get("relationship")),
                    "sha256": safe_text(related.get("sha256")),
                }
                for related in row.get("relatedOriginalFiles") or []
                if isinstance(related, dict)
                and safe_text(related.get("sourceFile"))
            ]
            levelscript = row.get("levelScript") or {}
            mission_area_shell = (
                row.get("missionAreaLevelDataShellContext") or {}
            )
            shell_status = safe_text(mission_area_shell.get("status"))
            shell_mission_ids = sorted({
                safe_text(value)
                for value in mission_area_shell.get("hostMissionIds") or []
                if safe_text(value)
            })
            shell_hosts = [
                host
                for host in mission_area_shell.get("hosts") or []
                if isinstance(host, dict)
            ]
            if shell_status in {"unique", "shared"} and shell_mission_ids:
                shell_related = list(related_files)
                for source_file in sorted({
                    safe_text(host.get("levelDataFile"))
                    for host in shell_hosts
                    if safe_text(host.get("levelDataFile"))
                }):
                    if not any(
                        safe_text(item.get("sourceFile")) == source_file
                        for item in shell_related
                    ):
                        shell_related.append({
                            "kind": "leveldata",
                            "sourceFile": source_file,
                            "relationship": (
                                "typed_mission_area_leveldata_shell_context"
                            ),
                            "sha256": _source_file_sha256(source_file),
                        })
                for mission_id in shell_mission_ids:
                    if mission_id not in mission_summaries:
                        continue
                    mission_area_contexts_by_mission[mission_id].append({
                        "relation": (
                            "mission_area_leveldata_receiver_shell_context"
                        ),
                        "missionId": mission_id,
                        "scopeStatus": shell_status,
                        "hostMissionIds": shell_mission_ids,
                        "levelId": level_id,
                        "scriptId": script_id,
                        "storyKeys": story_keys,
                        "eventNames": [
                            safe_text(name)
                            for name in row.get("eventNames") or []
                            if safe_text(name)
                        ],
                        "listenerHeaderLocalIds": [
                            value
                            for value in row.get("listenerHeaderLocalIds") or []
                            if isinstance(value, int)
                        ],
                        "activationClass": safe_text(
                            row.get("activationClass")
                        ),
                        "missionAreaIds": sorted({
                            safe_text(reference.get("missionAreaId"))
                            for host in shell_hosts
                            for reference in host.get(
                                "missionAreaReferences"
                            )
                            or []
                            if isinstance(reference, dict)
                            and safe_text(reference.get("missionAreaId"))
                        }),
                        "levelNums": sorted({
                            safe_text(reference.get("levelNum"))
                            for host in shell_hosts
                            for reference in host.get(
                                "missionAreaReferences"
                            )
                            or []
                            if isinstance(reference, dict)
                            and safe_text(reference.get("levelNum"))
                        }),
                        "subDataParentIds": sorted({
                            safe_text(root_id)
                            for host in shell_hosts
                            for root_id in host.get("rootScriptIds") or []
                            if safe_text(root_id)
                        }),
                        "levelDataFiles": sorted({
                            safe_text(host.get("levelDataFile"))
                            for host in shell_hosts
                            if safe_text(host.get("levelDataFile"))
                        }),
                        "missionRuntimeFiles": sorted({
                            safe_text(reference.get("sourceFile"))
                            for host in shell_hosts
                            for reference in host.get(
                                "missionAreaReferences"
                            )
                            or []
                            if isinstance(reference, dict)
                            and safe_text(reference.get("sourceFile"))
                        }),
                        "ownership": False,
                        "activation": False,
                        "storyPlayback": False,
                        "orderEvidence": False,
                        "relatedOriginalFiles": shell_related,
                        "evidenceBoundary": (
                            "A typed MissionRuntime MissionAreaTrackingInfo "
                            "(sceneId, missionAreaId) resolves through "
                            "LevelBasicInfoTable.idNum and the exact level-specific "
                            "MissionAreaTable.subDataParentId to a root in the same "
                            "validated LevelData dictionary as this receiver. The "
                            "complete mission union is "
                            f"{shell_status}; this is authored shell context only, "
                            "not activation, Story ownership, branch selection, "
                            "completion, or order."
                        ),
                    })
            for host in row.get("levelDataHosts") or []:
                if not isinstance(host, dict) or not host.get("missionNamedHost"):
                    continue
                mission_id = safe_text(host.get("hostMissionId"))
                if not mission_id or mission_id not in mission_summaries:
                    continue
                if (
                    shell_status == "unique"
                    and shell_mission_ids == [mission_id]
                ):
                    # The typed MissionArea root join independently proves the
                    # same shell and supersedes filename-only presentation.
                    continue
                host_source = safe_text(host.get("sourceFile"))
                host_file = safe_text(host.get("fileName"))
                host_related = list(related_files)
                if host_source and not any(
                    safe_text(item.get("sourceFile")) == host_source
                    for item in host_related
                ):
                    host_related.append({
                        "kind": "leveldata",
                        "sourceFile": host_source,
                        "relationship": "exact_mission_named_leveldata_receiver_context",
                        "sha256": "",
                    })
                mission_named_contexts_by_mission[mission_id].append({
                    "relation": "mission_named_leveldata_receiver_context",
                    "missionId": mission_id,
                    "levelId": level_id,
                    "scriptId": script_id,
                    "storyKeys": story_keys,
                    "eventNames": [
                        safe_text(name)
                        for name in row.get("eventNames") or []
                        if safe_text(name)
                    ],
                    "listenerHeaderLocalIds": [
                        value
                        for value in row.get("listenerHeaderLocalIds") or []
                        if isinstance(value, int)
                    ],
                    "activationClass": safe_text(row.get("activationClass")),
                    "levelDataHost": {
                        "fileName": host_file,
                        "sourceFile": host_source,
                        "dictionaryEntryCount": host.get("dictionaryEntryCount"),
                        "hostMissionId": mission_id,
                        "briefData": host.get("briefData") or {},
                        "encoding": "leveldata_filename_mission_token_plus_member22_dictionary",
                    },
                    "ownership": False,
                    "activation": False,
                    "storyPlayback": False,
                    "orderEvidence": False,
                    "relatedOriginalFiles": host_related,
                    "evidenceBoundary": (
                        "The exact mission token in the LevelData filename and the "
                        "validated member-22 LevelScriptBriefData dictionary place "
                        "this receiver in an authored mission-named asset container. "
                        "That container context does not prove the server activation "
                        "selector, quest ownership, Story playback ownership, branch "
                        "selection, completion, or inter-file Story order."
                    ),
                })
        for mission_id, contexts in sorted(contexts_by_mission.items()):
            path = mission_root / f"{mission_id}.json"
            payload = read_json(path)
            if not isinstance(payload, dict):
                continue
            unique = {
                (
                    safe_text(context.get("questId")),
                    context.get("objectiveIndex"),
                    safe_text(context.get("levelId")),
                    safe_text(context.get("scriptId")),
                    tuple(context.get("storyKeys") or []),
                ): context
                for context in contexts
            }
            ordered = [unique[key] for key in sorted(unique, key=str)]
            story_order = payload.setdefault("storyOrder", {})
            story_order["missionObservedLevelScriptContexts"] = ordered
            summary = story_order.setdefault("summary", {})
            summary["missionObservedLevelScriptContextCount"] = len(ordered)
            summary["missionObservedLevelScriptContextStoryCount"] = len({
                key for context in ordered for key in context["storyKeys"]
            })
            write_json(path, payload)
            published_contexts += len(ordered)
            mission_summary = mission_summaries.get(mission_id)
            if mission_summary is not None:
                mission_summary["storyOrderMissionObservedLevelScriptContextCount"] = (
                    len(ordered)
                )
        for mission_id, contexts in sorted(mission_named_contexts_by_mission.items()):
            path = mission_root / f"{mission_id}.json"
            payload = read_json(path)
            if not isinstance(payload, dict):
                continue
            unique = {
                (
                    safe_text(context.get("levelId")),
                    safe_text(context.get("scriptId")),
                    safe_text(
                        (context.get("levelDataHost") or {}).get("sourceFile")
                    ),
                    tuple(context.get("storyKeys") or []),
                ): context
                for context in contexts
            }
            ordered = [unique[key] for key in sorted(unique, key=str)]
            story_order = payload.setdefault("storyOrder", {})
            story_order["missionNamedLevelDataReceiverContexts"] = ordered
            summary = story_order.setdefault("summary", {})
            summary["missionNamedLevelDataReceiverContextCount"] = len(ordered)
            summary["missionNamedLevelDataReceiverContextStoryCount"] = len({
                key for context in ordered for key in context["storyKeys"]
            })
            write_json(path, payload)
            published_mission_named_contexts += len(ordered)
            mission_summary = mission_summaries.get(mission_id)
            if mission_summary is not None:
                mission_summary[
                    "storyOrderMissionNamedLevelDataReceiverContextCount"
                ] = len(ordered)
        for mission_id, contexts in sorted(mission_area_contexts_by_mission.items()):
            path = mission_root / f"{mission_id}.json"
            payload = read_json(path)
            if not isinstance(payload, dict):
                continue
            unique = {
                (
                    safe_text(context.get("scopeStatus")),
                    safe_text(context.get("levelId")),
                    safe_text(context.get("scriptId")),
                    tuple(context.get("hostMissionIds") or []),
                    tuple(context.get("storyKeys") or []),
                ): context
                for context in contexts
            }
            ordered = [unique[key] for key in sorted(unique, key=str)]
            story_order = payload.setdefault("storyOrder", {})
            story_order["missionAreaLevelDataReceiverContexts"] = ordered
            summary = story_order.setdefault("summary", {})
            summary["missionAreaLevelDataReceiverContextCount"] = len(ordered)
            summary["missionAreaLevelDataReceiverUniqueContextCount"] = sum(
                context.get("scopeStatus") == "unique"
                for context in ordered
            )
            summary["missionAreaLevelDataReceiverSharedContextCount"] = sum(
                context.get("scopeStatus") == "shared"
                for context in ordered
            )
            summary["missionAreaLevelDataReceiverContextStoryCount"] = len({
                key for context in ordered for key in context["storyKeys"]
            })
            write_json(path, payload)
            published_mission_area_contexts += len(ordered)
            mission_summary = mission_summaries.get(mission_id)
            if mission_summary is not None:
                mission_summary[
                    "storyOrderMissionAreaLevelDataReceiverContextCount"
                ] = len(ordered)
        receiver_contexts_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for mission_id, mission_summary in sorted(mission_summaries.items()):
            path = mission_root / f"{mission_id}.json"
            payload = read_json(path)
            if not isinstance(payload, dict):
                continue
            story_order = payload.get("storyOrder") or {}
            if not isinstance(story_order, dict):
                continue
            mission_story_keys = _story_order_keys(story_order)
            if not mission_story_keys:
                continue
            for row in report.get("rows") or []:
                if not isinstance(row, dict):
                    continue
                context = _receiver_story_context(
                    row,
                    mission_id,
                    mission_story_keys,
                )
                if context is not None:
                    receiver_contexts_by_mission[mission_id].append(context)
        for mission_id, contexts in sorted(receiver_contexts_by_mission.items()):
            path = mission_root / f"{mission_id}.json"
            payload = read_json(path)
            if not isinstance(payload, dict):
                continue
            unique = {
                (
                    safe_text(context.get("levelId")),
                    safe_text(context.get("scriptId")),
                    tuple(context.get("missionStoryKeys") or []),
                    tuple(
                        (related.get("sourceFile"), related.get("sha256"))
                        for related in context.get("relatedOriginalFiles") or []
                    ),
                ): context
                for context in contexts
            }
            ordered = [unique[key] for key in sorted(unique, key=str)]
            story_order = payload.setdefault("storyOrder", {})
            story_order["nativeReceiverStoryContexts"] = ordered
            summary = story_order.setdefault("summary", {})
            summary["nativeReceiverStoryContextCount"] = len(ordered)
            summary["nativeReceiverStoryContextStoryCount"] = len({
                key for context in ordered for key in context["missionStoryKeys"]
            })
            summary["nativeReceiverStoryContextRelatedFileCount"] = len({
                related.get("sourceFile")
                for context in ordered
                for related in context.get("relatedOriginalFiles") or []
                if related.get("sourceFile")
            })
            write_json(path, payload)
            published_receiver_story_contexts += len(ordered)
            mission_summary = mission_summaries.get(mission_id)
            if mission_summary is None:
                continue
            mission_summary["storyOrderNativeReceiverStoryContextCount"] = len(
                ordered
            )
            mission_summary["storyOrderNativeReceiverStoryContextStoryCount"] = len({
                key for context in ordered for key in context["missionStoryKeys"]
            })
            mission_summary[
                "storyOrderNativeReceiverStoryContextRelatedFileCount"
            ] = len({
                related.get("sourceFile")
                for context in ordered
                for related in context.get("relatedOriginalFiles") or []
                if related.get("sourceFile")
            })

    coverage["nativeReceiverActivationFrontier"] = {
        "schemaVersion": report.get("schemaVersion"),
        "generated": report.get("generated"),
        "counts": report.get("counts") or {},
        "evidencePolicy": report.get("evidencePolicy") or {},
        "structuredIdentityCarrierCensus": {
            key: value
            for key, value in (
                report.get("structuredIdentityCarrierCensus") or {}
            ).items()
            if key != "rows"
        },
        "teleportFinishCorrelationCensus": {
            key: value
            for key, value in (
                report.get("teleportFinishCorrelationCensus") or {}
            ).items()
            if key != "filters"
        },
        "missionAreaLevelDataShellCensus": (
            report.get("missionAreaLevelDataShellCensus") or {}
        ),
        "reportJson": rel_path(DEFAULT_JSON),
        "reportMarkdown": rel_path(DEFAULT_MARKDOWN),
        "annotatedReceiverNodes": annotated,
        "publishedMissionObservedLevelScriptContexts": published_contexts,
        "publishedMissionNamedLevelDataReceiverContexts": (
            published_mission_named_contexts
        ),
        "publishedMissionAreaLevelDataReceiverContexts": (
            published_mission_area_contexts
        ),
        "publishedNativeReceiverStoryContexts": published_receiver_story_contexts,
    }
    return annotated


def markdown_report(payload: dict[str, Any]) -> str:
    counts = payload.get("counts") or {}
    identity_census = payload.get("structuredIdentityCarrierCensus") or {}
    mission_area_census = payload.get("missionAreaLevelDataShellCensus") or {}
    teleport_census = payload.get("teleportFinishCorrelationCensus") or {}
    lines = [
        "# Native Receiver Activation Frontier",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Result",
        "",
        f"- Exact unresolved receiver nodes: `{counts.get('receiverNodes')}`",
        f"- Hosting LevelScripts: `{counts.get('receiverScripts')}`",
        (
            "- Receiver-to-Story placements: "
            f"`{counts.get('receiverToStoryPlacements')}`"
        ),
        f"- Unique Story keys: `{counts.get('storyKeys')}`",
        f"- Start types: `{counts.get('startTypes')}`",
        (
            "- Teleport-finish corpus files / listeners / distinct filters: "
            f"`{teleport_census.get('candidateFileCount')}` / "
            f"`{teleport_census.get('listenerCount')}` / "
            f"`{teleport_census.get('distinctFilterCount')}`"
        ),
        (
            "- Runtime-only filters / serialized action candidates / "
            "external serialized occurrences: "
            f"`{teleport_census.get('runtimeOnlyFilterCount')}` / "
            f"`{teleport_census.get('serializedActionCandidateCount')}` / "
            f"`{teleport_census.get('externalSerializedOccurrenceCount')}`; "
            "validation "
            f"`{(teleport_census.get('validation') or {}).get('status')}`"
        ),
        (
            "- Receiver scripts / Story keys with exact teleport-finish "
            "correlation context: "
            f"`{counts.get('receiverScriptsWithTeleportFinishCorrelation')}` / "
            f"`{counts.get('receiverStoryKeysWithTeleportFinishCorrelation')}`"
        ),
        (
            "- Structured JSON candidate files / records / direct carriers: "
            f"`{identity_census.get('candidateFileCount')}` / "
            f"`{identity_census.get('visitedRecordCount')}` / "
            f"`{identity_census.get('directCarrierCount')}`"
        ),
        (
            "- Direct structured carriers matching unresolved receiver scripts "
            f"/ unreviewed carrier shapes: "
            f"`{identity_census.get('receiverMatchCount')}` / "
            f"`{sum(1 for row in identity_census.get('rows') or [] if row.get('classification') == 'unreviewed_direct_identity_carrier')}`"
        ),
        (
            "- Scripts / Story keys with binary-validated SameWithActive "
            f"policy: `{counts.get('scriptsWithValidatedSameWithActivePolicy')}` / "
            f"`{counts.get('storyKeysWithValidatedSameWithActivePolicy')}`"
        ),
        (
            "- Scripts / Story keys with binary-validated current-context "
            "ManualStart self control: "
            f"`{counts.get('scriptsWithValidatedManualSelfControl')}` / "
            f"`{counts.get('storyKeysWithValidatedManualSelfControl')}`"
        ),
        (
            "- Scripts with binary-validated public-state sync: "
            f"`{counts.get('scriptsWithValidatedPublicStateControlContract')}`"
        ),
        (
            "- Scripts with exact activation selector / client-produced "
            "active=true: "
            f"`{counts.get('scriptsWithValidatedClientActiveRequestSelector')}` / "
            f"`{counts.get('scriptsWithClientProducedActiveRequest')}` "
            f"(`{counts.get('clientActiveRequestLevelScriptTypes')}`)"
        ),
        (
            "- Scripts with exact authored active-volume gate / shapes / types: "
            f"`{counts.get('scriptsWithValidatedActiveShapeGate')}` / "
            f"`{counts.get('authoredActiveShapeCount')}` / "
            f"`{counts.get('authoredActiveShapeTypes')}`"
        ),
        (
            "- Scripts / exact headers / Story keys with binary-validated "
            "Active-phase receivers: "
            f"`{counts.get('scriptsWithValidatedActivePhaseReceivers')}` / "
            f"`{counts.get('activePhaseReceiverHeaders')}` / "
            f"`{counts.get('storyKeysWithValidatedActivePhaseReceivers')}`"
        ),
        (
            "- Scripts / Story keys with binary-validated SubGame interaction "
            "ManualStart: "
            f"`{counts.get('scriptsWithValidatedSubGameInteractionStart')}` / "
            f"`{counts.get('storyKeysWithValidatedSubGameInteractionStart')}`"
        ),
        f"- Activation classes: `{counts.get('activationClasses')}`",
        f"- LevelData host shapes: `{counts.get('levelDataHostShapes')}`",
        (
            "- Scripts in a validated mission-named LevelData host: "
            f"`{counts.get('scriptsWithMissionNamedHost')}`"
        ),
        (
            "- Typed MissionArea-to-LevelData shell contexts (unique / shared "
            "/ mission placements): "
            f"`{mission_area_census.get('contextCount')}` "
            f"(`{mission_area_census.get('uniqueContextCount')}` / "
            f"`{mission_area_census.get('sharedContextCount')}` / "
            f"`{mission_area_census.get('missionPlacementCount')}`); "
            "validation "
            f"`{(mission_area_census.get('validation') or {}).get('status')}`"
        ),
        (
            "- Generic serialized module property families / scripts / "
            "related files: "
            f"`{counts.get('modulePropertyFamilyCount')}` / "
            f"`{counts.get('scriptsWithModulePropertyFamilies')}` / "
            f"`{counts.get('modulePropertyFamilyRelatedFiles')}`"
        ),
        (
            "- Generic module family features: "
            f"`{counts.get('modulePropertyFamilyFeatures')}`"
        ),
        (
            "- Receiver scripts / Encounter modules / Story keys with the "
            "binary-proven controller contract: "
            f"`{counts.get('scriptsWithEncounterControllerContract')}` / "
            f"`{counts.get('encounterControllerContracts')}` / "
            f"`{counts.get('storyKeysWithEncounterControllerContract')}`"
        ),
        (
            "- Encounter module ids differing from the receiver script id: "
            f"`{counts.get('encounterControllerContractsWithForeignModuleId')}`"
        ),
        (
            "- Distinct related Encounter source files: "
            f"`{counts.get('encounterControllerRelatedFiles')}`"
        ),
        (
            "- Scripts excluded by validated same-level nominal-mission hosts: "
            f"`{counts.get('scriptsWithValidatedNominalMissionHostExclusion')}`"
        ),
        (
            "- Black Story keys on those excluded scripts: "
            f"`{counts.get('blackStoryKeysWithValidatedNominalMissionHostExclusion')}`"
        ),
        (
            "- Black Story keys with an exact SubGame carrier and no "
            "same-level nominal-mission host: "
            f"`{counts.get('blackStoryKeysWithSubGameBindingAndNoNominalMissionHost')}`"
        ),
        (
            "- Black Story keys with the static nominal-mission route closed: "
            f"`{counts.get('blackStoryKeysWithClosedStaticNominalMissionRoute')}`"
        ),
        (
            "- Scripts with an incoming literal cross-script manual control: "
            f"`{counts.get('scriptsWithIncomingLiteralCrossControl')}`"
        ),
        (
            "- Scripts with an exact SubGame `bindScriptId` carrier: "
            f"`{counts.get('scriptsWithSubGameBinding')}`"
        ),
        (
            "- Scripts / Story keys / scenes with exact Dungeon scene context: "
            f"`{counts.get('scriptsWithExactDungeonSceneContext')}` / "
            f"`{counts.get('storyKeysWithExactDungeonSceneContext')}` / "
            f"`{counts.get('exactDungeonSceneIds')}`"
        ),
        (
            "- Dungeon scene-context placements (bound / sibling): "
            f"`{counts.get('exactDungeonSceneContextPlacements')}` "
            f"(`{counts.get('directBoundDungeonSceneContextPlacements')}` / "
            f"`{counts.get('siblingDungeonSceneContextPlacements')}`)"
        ),
        (
            "- Availability prerequisites carried by those scene contexts: "
            f"`{counts.get('dungeonSceneContextAvailabilityAssociations')}`"
        ),
        (
            "- Scripts / Story keys / placements with typed dungeon-mission "
            "shell context: "
            f"`{counts.get('scriptsWithDungeonMissionShellContext')}` / "
            f"`{counts.get('storyKeysWithDungeonMissionShellContext')}` / "
            f"`{counts.get('dungeonMissionShellContextPlacements')}`"
        ),
        (
            "- Scripts named by a typed MissionRuntime objective operand: "
            f"`{counts.get('scriptsWithMissionRuntimeObjectiveConsumer')}`"
        ),
        (
            "- Related original-file placements / distinct files attached to "
            "receiver nodes: "
            f"`{counts.get('relatedOriginalFilePlacements')}` / "
            f"`{counts.get('distinctRelatedOriginalFiles')}`"
        ),
        (
            "- Scripts with authored start shapes / exact complete MissionArea "
            f"shape matches: `{counts.get('scriptsWithStartShapes')}` / "
            f"`{counts.get('scriptsWithExactStartShapeMissionAreaMatch')}`"
        ),
        (
            "- Scripts with task maps / exact serialized MissionRuntime-id "
            f"tokens: `{counts.get('scriptsWithTaskMap')}` / "
            f"`{counts.get('scriptsWithSerializedMissionRuntimeIdToken')}`"
        ),
        (
            "- Fully decoded task-map scripts / tasks / conditions: "
            f"`{counts.get('scriptsWithFullyDecodedTaskMap')}` / "
            f"`{counts.get('decodedTaskCount')}` / "
            f"`{counts.get('decodedTaskConditionCount')}`"
        ),
        (
            "- Task-map scripts with hash-validated binary task authority: "
            f"`{counts.get('scriptsWithValidatedTaskRuntimeAuthority')}`"
        ),
        (
            "- Tasks with complete LevelData `lt:p`/`lt:mp` progress pairs / "
            "property placements: "
            f"`{counts.get('decodedTasksWithCompleteProgressPropertyContract')}` / "
            f"`{counts.get('decodedTaskProgressPropertyPlacements')}`"
        ),
        (
            "- Decoded task condition types: "
            f"`{counts.get('decodedTaskConditionTypes')}`"
        ),
        (
            "- Conditions with exact authored operand sources / source types: "
            f"`{counts.get('decodedTaskConditionsWithExactOperandSource')}` / "
            f"`{counts.get('decodedTaskOperandSourceTypes')}`"
        ),
        (
            "- Conditions with an exact typed MissionRuntime operand consumer: "
            f"`{counts.get('decodedTaskConditionsWithMissionRuntimeOperandConsumer')}`"
        ),
        (
            "- Tasks with an exact `CheckLevelScriptTaskFinished` consumer: "
            f"`{counts.get('decodedTasksWithMissionRuntimeTaskConsumer')}`"
        ),
        (
            "- Tasks with exact ScriptTaskExtraInfo / SubGame main-task rows: "
            f"`{counts.get('decodedTasksWithExtraInfo')}` / "
            f"`{counts.get('decodedTasksWithSubGameMainTaskBinding')}`"
        ),
        (
            "- Non-SubGame task-map scripts with a serialized MissionRuntime-id "
            "token: "
            f"`{counts.get('nonSubGameTaskMapScriptsWithSerializedMissionRuntimeIdToken')}`"
        ),
        "",
        "The report is fail-closed: these fields narrow the missing activation "
        "carrier but create no mission, quest, playback, branch, completion, or "
        "order edge.",
        "",
        "## Receiver scripts",
        "",
        "| LevelScript | receivers | Story keys | start | LevelData host | class |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for row in payload.get("rows") or []:
        levelscript = row.get("levelScript") or {}
        hosts = row.get("levelDataHosts") or []
        host_text = ", ".join(
            (
                f"{host.get('fileName')} "
                f"({host.get('dictionaryEntryCount')} scripts"
                + (
                    f", mission {host.get('hostMissionId')}"
                    if host.get("missionNamedHost")
                    else ", generic"
                )
                + ")"
            )
            for host in hosts
        ) or "[no validated host]"
        lines.append(
            "| "
            + " | ".join(
                md_escape(value)
                for value in (
                    f"{row.get('levelId')}/{row.get('scriptId')}",
                    row.get("receiverNodeCount"),
                    ", ".join(row.get("storyKeys") or []),
                    (
                        f"{levelscript.get('startTypeName') or '[unresolved]'}; "
                        f"shapes={levelscript.get('startShapeListStatus')}/"
                        f"{levelscript.get('startShapeListCount')}; "
                        f"taskMap={levelscript.get('taskMapStatus')}/"
                        f"{levelscript.get('taskMapCount')}"
                    ),
                    host_text,
                    row.get("activationClass"),
                )
            )
            + " |"
        )
    checked_black_rows = [
        row
        for row in payload.get("rows") or []
        if (
            (
                row.get("nominalMissionHostComparison") or {}
            ).get("classification")
            == "validated_nominal_mission_hosts_exclude_receiver_script"
            or (
                row.get("subGameBindings")
                and (
                    row.get("nominalMissionHostComparison") or {}
                ).get("classification")
                == "no_same_level_nominal_mission_host"
            )
        )
        and any(
            candidate.get("storyKind") == "black"
            for candidate in (
                row.get("nominalMissionHostComparison") or {}
            ).get("storyCandidates") or []
        )
    ]
    lines.extend([
        "",
        "## Black playback static nominal-owner checks",
        "",
        (
            "These are exact static-carrier checks for filename-derived mission "
            "candidates, not ownership claims. Three keys have validated "
            "same-level nominal-mission hosts that exclude their receiver "
            "scripts; two instead have exact activity SubGame bind carriers and "
            "no same-level nominal-mission host."
        ),
        "",
        "| LevelScript | Black Story key | Nominal mission | Excluding host | Actual carrier |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in checked_black_rows:
        comparison = row.get("nominalMissionHostComparison") or {}
        black_candidates = [
            candidate
            for candidate in comparison.get("storyCandidates") or []
            if candidate.get("storyKind") == "black"
        ]
        actual_carrier = ", ".join(
            safe_text(binding.get("subGameId"))
            for binding in row.get("subGameBindings") or []
            if safe_text(binding.get("subGameId"))
        )
        if not actual_carrier:
            actual_carrier = ", ".join(
                safe_text(host.get("fileName"))
                for host in row.get("levelDataHosts") or []
                if safe_text(host.get("fileName"))
            )
        for candidate in black_candidates:
            excluding_hosts = ", ".join(
                safe_text(host.get("fileName"))
                for host in comparison.get("sameLevelMissionNamedHosts") or []
                if host.get("dictionaryValidated")
                and not host.get("receiverScriptPresent")
                and safe_text(host.get("missionId"))
                == safe_text(candidate.get("nominalMissionId"))
            )
            lines.append(
                "| "
                + " | ".join(
                    md_escape(value)
                    for value in (
                        f"{row.get('levelId')}/{row.get('scriptId')}",
                        candidate.get("storyKey"),
                        candidate.get("nominalMissionId"),
                        excluding_hosts or "[none]",
                        actual_carrier or "[no static carrier]",
                    )
                )
                + " |"
            )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-index", type=Path, default=DEFAULT_PIPELINE_INDEX)
    parser.add_argument(
        "--mission-root",
        type=Path,
        default=DEFAULT_PIPELINE_MISSION_ROOT,
    )
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--structured-json-root",
        type=Path,
        default=DEFAULT_STRUCTURED_JSON_ROOT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_report(
        read_json(args.pipeline_index) or {},
        mission_root=args.mission_root,
        structured_json_root=args.structured_json_root,
    )
    payload["sources"]["missionPipelineIndex"] = rel_path(args.pipeline_index)
    payload["sources"]["missionPipelineMissionRoot"] = rel_path(args.mission_root)
    payload["sources"]["structuredJsonRoot"] = rel_path(
        args.structured_json_root
    )
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, markdown_report(payload))
    counts = payload["counts"]
    print(
        f"wrote {rel_path(args.json)} and {rel_path(args.markdown)} "
        f"(scripts={counts['receiverScripts']}, "
        f"classes={counts['activationClasses']})"
    )
    validation = (
        payload.get("structuredIdentityCarrierCensus") or {}
    ).get("validation") or {}
    if validation.get("status") != "validated":
        failure = (validation.get("failures") or [{}])[0]
        raise SystemExit(
            "structured identity census failed: "
            f"validator={failure.get('validator')}; "
            f"gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; "
            f"expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )
    shell_validation = (
        payload.get("missionAreaLevelDataShellCensus") or {}
    ).get("validation") or {}
    if shell_validation.get("status") != "validated":
        failure = (shell_validation.get("failures") or [{}])[0]
        raise SystemExit(
            "mission-area LevelData shell validation failed: "
            f"validator={failure.get('validator')}; "
            f"gate={failure.get('gate')}; "
            f"identity={failure.get('identity')}; "
            f"source={failure.get('sourceFile')}; "
            f"expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}; "
            f"sourceHashes={failure.get('sourceHashes')!r}"
        )
    teleport_validation = (
        payload.get("teleportFinishCorrelationCensus") or {}
    ).get("validation") or {}
    if teleport_validation.get("status") != "validated":
        failure = (teleport_validation.get("failures") or [{}])[0]
        raise SystemExit(
            "teleport-finish correlation validation failed: "
            f"validator={failure.get('validator')}; "
            f"gate={failure.get('gate')}; "
            f"identity={failure.get('identity')}; "
            f"source={failure.get('sourceFile')}; "
            f"expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}; "
            f"sourceHashes={failure.get('sourceHashes')!r}"
        )


if __name__ == "__main__":
    main()
