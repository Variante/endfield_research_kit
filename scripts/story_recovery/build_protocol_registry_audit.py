#!/usr/bin/env python3
"""Recover the current-build protobuf message registry and Story-facing schemas.

This is a metadata/schema audit. Message presence and field names do not prove
that a native sender or handler is active, nor do they create Mission Pipeline
ownership or ordering edges.

Outputs:

    reports/story/recovery/protocol_registry_audit.json
    reports/story/recovery/protocol_registry_audit.md
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402


DEFAULT_METADATA = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat"
)
METADATA_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
RUNTIME_HOOK_MANIFEST = (
    ROOT / "scripts" / "story_recovery" / "mission_runtime_trace_hooks.json"
)
MISSION_RUNTIME_ROOT = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset"
)
MEMORYPACK_UNION_AUDIT = (
    REPORT_ROOT / "memorypack_union_formatter_tag_audit.json"
)


NATIVE_MISSION_EVENT_PATHS: dict[int, dict[str, Any]] = {
    125: {
        "symbol": "Beyond.Gameplay.MissionSystem.Handle_ClientMissionEvent",
        "token": "0x060052a6",
        "methodIndex": 21157,
        "va": "0x1873bdf58",
        "rva": "0x73bdf58",
        "dispatchTarget": "0x184a428a0",
        "fieldOffsets": {
            "missionId": "0x18",
            "eventName": "0x20",
        },
        "keyGenerator": {
            "symbol": "Beyond.KeyGenerator`2.GetKey",
            "va": "0x184a428a0",
            "genericMethodPointerSlot": 193461,
            "methodSpecIndex": 204894,
        },
        "keyBackend": {
            "symbol": "Beyond.CombineKeyManager.GetKey",
            "va": "0x1846a2e60",
        },
        "dispatch": {
            "symbol": "Beyond.EventManager.SendGlobal",
            "va": "0x187bdfd38",
        },
        "consumerSurface": "keyed_global_event_bus",
        "directCallCensus": {
            "keyGenerator2Instantiations": 7,
            "namedCallSites": 35,
            "sameInstantiationClass": 1055,
            "sameInstantiationCallers": [
                "Beyond.Gameplay.MapVarSystem.SetClientMapVar",
                "Beyond.Gameplay.MapVarSystem._Handle_UpdateMapVar",
                "Beyond.Gameplay.SimpleConditionCheckMapVar.InnerStartListening",
                "Beyond.Gameplay.MissionSystem.Handle_ClientMissionEvent",
            ],
            "typedPairingStatus": (
                "unproven: the only subscriber-side caller in the same generic "
                "instantiation consumes belongMapId/mapVarName, while message 125 "
                "publishes missionId/eventName"
            ),
            "coverage": (
                "direct E8 rel32 calls only; vtable, delegate, IFix, and XLua "
                "indirect dispatch are outside this census"
            ),
        },
        "finding": (
            "The native handler reads missionId/eventName from the protobuf object and "
            "interns that pair as a two-part CombineKey before publishing it through "
            "EventManager.SendGlobal. It does not dispatch to the serialized "
            "MissionEvent_OnCustomEventForMission surface."
        ),
    },
}

NATIVE_LEVEL_SCRIPT_EVENT_PATHS: dict[int, dict[str, Any]] = {
    57: {
        "symbol": "Beyond.Gameplay.GameplayNetwork._Handle_SceneTriggerClientLevelScriptEvent",
        "token": "0x06004dbf",
        "methodIndex": 19902,
        "va": "0x187386320",
        "rva": "0x7386320",
        "ifixPatchId": "0x5ac7",
        "fieldOffsets": {
            "sceneNumId": "0x18",
            "scriptId": "0x20",
            "eventName": "0x28",
            "ctxToken": "0x30",
        },
        "eventParamsPath": {
            "allocate": "Beyond.Gameplay.Core.EventParams.Allocate",
            "receiver": "Beyond.Gameplay.Core.LevelScriptPtr(scriptId)",
            "receiverSetter": "Beyond.Gameplay.Core.EventParams.SetReceiver",
            "ctxToken": (
                "when the protobuf ByteString is non-empty, store it in the "
                "EventParams/ParamBlackboard before dispatch"
            ),
            "dispatch": "Beyond.Gameplay.Core.LevelEventManager.RaiseScriptEvent",
        },
        "ctxTokenFinding": (
            "ctxToken is propagated as opaque event context; it is not discarded. "
            "The handler does not decode it into missionId or questId, and the packet "
            "contains neither identity."
        ),
        "finding": (
            "The handler constructs a LevelScript receiver from scriptId, optionally "
            "copies ctxToken into EventParams, and raises eventName through "
            "LevelEventManager.RaiseScriptEvent."
        ),
    },
}


MISSION_EVENT_CONSTRUCTOR_XREF_FINDING = {
    "messages": [125, 126, 316, 317],
    "constructorXrefs": 8,
    "gameplayConstructorXrefs": 0,
    "finding": (
        "Direct constructor-call scanning found only generated protobuf copy constructors "
        "and static parser factories for messages 125, 126, 316, and 317. It found no "
        "gameplay constructor caller for the schema-only 126/316/317 paths."
    ),
}


# Enum member spelling comes directly from Proto.CSMessageID/SCMessageID.
# Type names are the generated protobuf message class names.
RELEVANT_MESSAGES: tuple[dict[str, Any], ...] = (
    {
        "type": "Proto.CS_SCENE_UPDATE_SCRIPT_TASK_PROGRESS",
        "direction": "client_to_server",
        "enumName": "CsSceneUpdateScriptTaskProgress",
        "expectedId": 105,
        "classification": "native_sender_proven_elsewhere",
    },
    {
        "type": "Proto.SC_SCENE_LEVEL_SCRIPT_TASK_STATE_UPDATE",
        "direction": "server_to_client",
        "enumName": "ScSceneLevelScriptTaskStateUpdate",
        "expectedId": 813,
        "classification": "native_handler_proven_elsewhere",
    },
    {
        "type": "Proto.SC_SCENE_LEVEL_SCRIPT_TASK_PROGRESS_UPDATE",
        "direction": "server_to_client",
        "enumName": "ScSceneLevelScriptTaskProgressUpdate",
        "expectedId": 815,
        "classification": "native_handler_proven_elsewhere",
    },
    {
        "type": "Proto.SC_SCENE_LEVEL_SCRIPT_TASK_START_FINISH",
        "direction": "server_to_client",
        "enumName": "ScSceneLevelScriptTaskStartFinish",
        "expectedId": 816,
        "classification": "native_handler_proven_elsewhere",
    },
    {
        "type": "Proto.SC_SCENE_LEVEL_SCRIPT_SET_DONE",
        "direction": "server_to_client",
        "enumName": "ScSceneLevelScriptSetDone",
        "expectedId": 823,
        "classification": "native_handler_proven_elsewhere",
    },
    {
        "type": "Proto.CS_MISSION_EVENT_TRIGGER",
        "direction": "client_to_server",
        "enumName": "CsMissionEventTrigger",
        "expectedId": 316,
        "classification": "schema_only_sender_unconfirmed",
    },
    {
        "type": "Proto.SC_MISSION_EVENT_TRIGGER",
        "direction": "server_to_client",
        "enumName": "ScMissionEventTrigger",
        "expectedId": 126,
        "classification": "schema_only_pairing_unconfirmed",
    },
    {
        "type": "Proto.CS_MISSION_CLIENT_TRIGGER_DONE",
        "direction": "client_to_server",
        "enumName": "CsMissionClientTriggerDone",
        "expectedId": 317,
        "classification": "schema_only_sender_unconfirmed",
    },
    {
        "type": "Proto.SC_SCENE_TRIGGER_CLIENT_MISSION_EVENT",
        "direction": "server_to_client",
        "enumName": "ScSceneTriggerClientMissionEvent",
        "expectedId": 125,
        "classification": "native_handler_proven",
    },
    {
        "type": "Proto.SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT",
        "direction": "server_to_client",
        "enumName": "ScSceneTriggerClientLevelScriptEvent",
        "expectedId": 57,
        "classification": "native_handler_proven_elsewhere",
    },
    {
        "type": "Proto.SC_SYNC_ALL_MISSION",
        "direction": "server_to_client",
        "enumName": "ScSyncAllMission",
        "expectedId": 110,
        "classification": "native_handler_proven_elsewhere",
    },
    {
        "type": "Proto.SC_MISSION_STATE_UPDATE",
        "direction": "server_to_client",
        "enumName": "ScMissionStateUpdate",
        "expectedId": 112,
        "classification": "native_handler_proven_elsewhere",
    },
    {
        "type": "Proto.SC_MISSION_UPDATE_CUR_MAIN_MISSION",
        "direction": "server_to_client",
        "enumName": "ScMissionUpdateCurMainMission",
        "expectedId": 136,
        "classification": "schema_only",
    },
    {
        "type": "Proto.SC_TRY_TRACK_BLOCK_QUEST_MISSION",
        "direction": "server_to_client",
        "enumName": "ScTryTrackBlockQuestMission",
        "expectedId": 120,
        "classification": "schema_only",
    },
    {
        "type": "Proto.SC_SET_MISSION_ENABLE",
        "direction": "server_to_client",
        "enumName": "ScSetMissionEnable",
        "expectedId": 121,
        "classification": "schema_only",
    },
    {
        "type": "Proto.SC_SET_QUEST_ENABLE",
        "direction": "server_to_client",
        "enumName": "ScSetQuestEnable",
        "expectedId": 122,
        "classification": "schema_only",
    },
)


KNOWN_ID_CHECKS = {
    "CsUpdateQuestObjective": 314,
    "CsAcceptMission": 315,
    "CsFinishDialog": 341,
    "CsGameMechanicsReqActive": 381,
    "ScQuestStateUpdate": 111,
    "ScMissionStateUpdate": 112,
    "ScQuestObjectivesUpdate": 116,
    "ScFinishDialog": 131,
    "ScGameMechanicsSyncEnterGameInst": 1257,
}


def load_metadata_helper(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("endfield_protocol_metadata", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load metadata helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_compressed_uint32(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first & 0x80 == 0:
        return first, 1
    if first & 0xC0 == 0x80:
        return ((first & 0x3F) << 8) | data[offset + 1], 2
    if first & 0xE0 == 0xC0:
        return (
            ((first & 0x1F) << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3],
            4,
        )
    if first == 0xF0:
        return struct.unpack_from(">I", data, offset + 1)[0], 5
    if first == 0xFE:
        return 0xFFFFFFFE, 1
    if first == 0xFF:
        return 0xFFFFFFFF, 1
    raise ValueError(f"unsupported compressed uint prefix 0x{first:02x}")


def read_compressed_int32(data: bytes, offset: int) -> tuple[int, int]:
    unsigned, size = read_compressed_uint32(data, offset)
    return (unsigned >> 1) ^ -(unsigned & 1), size


def normalized_field_name(value: str) -> str:
    if value.endswith("FieldNumber"):
        value = value[: -len("FieldNumber")]
    value = value.rstrip("_")
    return re.sub(r"[^a-z0-9]", "", value.lower())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_native_task_paths(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    hooks = payload.get("hooks", {}).get("levelScriptTask")
    if not isinstance(hooks, dict) or not hooks:
        raise RuntimeError(f"runtime hook manifest has no levelScriptTask hooks: {path}")
    normalized: dict[str, dict[str, Any]] = {}
    for name, row in hooks.items():
        if not isinstance(row, dict):
            raise RuntimeError(f"invalid levelScriptTask hook {name!r} in {path}")
        normalized[name] = {
            key: row[key]
            for key in (
                "symbol",
                "token",
                "methodIndex",
                "rva",
                "message",
                "messageId",
                "captureScope",
                "fieldOffsets",
            )
            if key in row
        }
    return {
        "manifest": str(path.resolve()),
        "manifestSha256": file_sha256(path),
        "gameBuild": payload.get("gameBuild"),
        "hooks": normalized,
    }


def mission_event_asset_coverage(
    mission_runtime_root: Path,
    union_audit_path: Path,
) -> dict[str, Any]:
    """Measure serialized consumers of the native mission-event surface."""
    if not mission_runtime_root.is_dir():
        raise RuntimeError(f"MissionRuntimeAsset root not found: {mission_runtime_root}")
    action_types: Counter[str] = Counter()
    file_count = 0
    mission_asset_count = 0
    header_count = 0
    client_action_mapping_count = 0
    resolved_client_action_mapping_count = 0
    custom_listener_count = 0

    def count_custom_listeners(value: Any) -> int:
        if isinstance(value, dict):
            own = int(
                "MissionEvent_OnCustomEventForMission"
                in str(value.get("$type") or "")
            )
            return own + sum(count_custom_listeners(child) for child in value.values())
        if isinstance(value, list):
            return sum(count_custom_listeners(child) for child in value)
        return 0

    for path in sorted(mission_runtime_root.glob("*.json")):
        file_count += 1
        raw = json.loads(path.read_text(encoding="utf-8"))
        data_map = ((raw.get("actionMapRaw") or {}).get("dataMap") or {})
        if not isinstance(data_map, dict):
            data_map = {}
        action_rows = data_map.get("actionList")
        header_rows = data_map.get("headerList")
        if not isinstance(action_rows, list):
            action_rows = []
        if not isinstance(header_rows, list):
            header_rows = []
        keys = raw.get("clientActionMapKey")
        values = raw.get("clientActionMapValue")
        if not isinstance(keys, list):
            keys = []
        if not isinstance(values, list):
            values = []
        if "questDic" in raw or "actionMapRaw" in raw:
            mission_asset_count += 1
        header_count += len(header_rows)
        custom_listener_count += count_custom_listeners(raw)
        actions_by_id: dict[int, dict[str, Any]] = {}
        for action in action_rows:
            if not isinstance(action, dict):
                continue
            action_type = str(action.get("$type") or "<missing>")
            action_types[action_type] += 1
            action_id = action.get("_ID")
            if isinstance(action_id, int):
                actions_by_id[action_id] = action
        for key, action_id in zip(keys, values):
            if not isinstance(key, dict) or not isinstance(action_id, int):
                continue
            client_action_mapping_count += 1
            if action_id in actions_by_id:
                resolved_client_action_mapping_count += 1

    levelscript_candidate_count = 0
    levelscript_candidates: list[dict[str, Any]] = []
    if union_audit_path.is_file():
        union_audit = json.loads(union_audit_path.read_text(encoding="utf-8"))
        for row in union_audit.get("derivedOpcodeMappings") or []:
            if not isinstance(row, dict):
                continue
            if (
                row.get("headerName") == "MissionEvent_OnCustomEventForMission"
                or row.get("headerName") == "MissionEventHeader"
                or row.get("headerTagHex") in {"0x00b6", "0x00b8"}
            ):
                levelscript_candidates.append(row)
                levelscript_candidate_count += int(row.get("count") or 0)

    return {
        "missionRuntimeRoot": str(mission_runtime_root.resolve()),
        "files": file_count,
        "missionAssets": mission_asset_count,
        "missionActionHeaders": header_count,
        "customMissionEventListeners": custom_listener_count,
        "clientActionMappings": client_action_mapping_count,
        "resolvedClientActionMappings": resolved_client_action_mapping_count,
        "unresolvedClientActionMappings": (
            client_action_mapping_count - resolved_client_action_mapping_count
        ),
        "actionTypes": dict(sorted(action_types.items())),
        "levelScriptUnionAudit": (
            str(union_audit_path.resolve()) if union_audit_path.is_file() else None
        ),
        "levelScriptCustomMissionEventRecords": levelscript_candidate_count,
        "levelScriptCandidateOpcodeMappings": levelscript_candidates,
        "finding": (
            "The refreshed serialized assets contain no "
            "MissionEvent_OnCustomEventForMission listener. This bounds that serialized "
            "action family only: message 125 actually publishes through the keyed global "
            "EventManager bus, so this scan cannot establish whether that bus has a "
            "runtime or indirect consumer."
        ),
    }


def field_defaults(metadata: Any) -> dict[int, tuple[int, int]]:
    section = metadata.sections["fieldDefaultValues"]
    if section.size % 12:
        raise RuntimeError("fieldDefaultValues is not aligned to 12-byte records")
    out: dict[int, tuple[int, int]] = {}
    for position in range(section.offset, section.offset + section.size, 12):
        field_index, type_index, data_index = struct.unpack_from(
            "<iii", metadata.buf, position
        )
        if field_index in out:
            raise RuntimeError(f"duplicate field default for field {field_index}")
        out[field_index] = (type_index, data_index)
    return out


def constant_value(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    field: Any,
) -> int | None:
    default = defaults.get(field.index)
    if default is None:
        return None
    _type_index, data_index = default
    section = metadata.sections["fieldAndParameterDefaultValueData"]
    value, _size = read_compressed_int32(metadata.buf, section.offset + data_index)
    return value


def enum_members(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    type_name: str,
) -> list[dict[str, Any]]:
    for type_def in metadata.types:
        if metadata.type_full_name(type_def) != type_name:
            continue
        rows: list[dict[str, Any]] = []
        for field in metadata.fields_for(type_def):
            name = metadata.string(field.name_index)
            if name == "value__":
                continue
            value = constant_value(metadata, defaults, field)
            if value is None:
                continue
            rows.append(
                {
                    "id": value,
                    "name": name,
                    "fieldIndex": field.index,
                    "token": f"0x{field.token:08x}",
                }
            )
        return sorted(rows, key=lambda row: (row["id"], row["name"]))
    raise RuntimeError(f"metadata type not found: {type_name}")


def message_schema(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    type_name: str,
) -> dict[str, Any]:
    for type_def in metadata.types:
        if metadata.type_full_name(type_def) != type_name:
            continue
        tags: dict[str, dict[str, Any]] = {}
        storage: dict[str, dict[str, Any]] = {}
        for field in metadata.fields_for(type_def):
            name = metadata.string(field.name_index)
            if name.endswith("FieldNumber"):
                tags[normalized_field_name(name)] = {
                    "constantName": name,
                    "tag": constant_value(metadata, defaults, field),
                }
            elif name.endswith("_"):
                storage[normalized_field_name(name)] = {
                    "name": name[:-1],
                    "storageName": name,
                    "storageTypeIndex": field.type_index,
                    "metadataType": metadata.metadata_type_name(field.type_index),
                }
        fields: list[dict[str, Any]] = []
        for key in sorted(set(tags) | set(storage)):
            row = {**storage.get(key, {}), **tags.get(key, {})}
            row["matchedTagAndStorage"] = key in tags and key in storage
            fields.append(row)
        fields.sort(key=lambda row: (row.get("tag") is None, row.get("tag", 0), row.get("name", "")))
        return {
            "type": type_name,
            "token": f"0x{type_def.token:08x}",
            "fields": fields,
        }
    raise RuntimeError(f"metadata type not found: {type_name}")


def build_report(
    metadata_path: Path,
    helper_path: Path = METADATA_HELPER,
    hook_manifest_path: Path = RUNTIME_HOOK_MANIFEST,
    mission_runtime_root: Path = MISSION_RUNTIME_ROOT,
    union_audit_path: Path = MEMORYPACK_UNION_AUDIT,
) -> dict[str, Any]:
    helper = load_metadata_helper(helper_path)
    metadata = helper.Metadata(metadata_path)
    defaults = field_defaults(metadata)
    native_task_paths = load_native_task_paths(hook_manifest_path)
    mission_event_assets = mission_event_asset_coverage(
        mission_runtime_root,
        union_audit_path,
    )
    native_hooks_by_message_id: dict[int, list[str]] = {}
    for hook_name, hook in native_task_paths["hooks"].items():
        message_id = hook.get("messageId")
        if isinstance(message_id, int):
            native_hooks_by_message_id.setdefault(message_id, []).append(hook_name)
    cs = enum_members(metadata, defaults, "Proto.CSMessageID")
    sc = enum_members(metadata, defaults, "Proto.SCMessageID")
    registry_by_name = {row["name"]: row["id"] for row in (*cs, *sc)}

    checks = [
        {
            "name": name,
            "expectedId": expected,
            "actualId": registry_by_name.get(name),
            "matches": registry_by_name.get(name) == expected,
        }
        for name, expected in KNOWN_ID_CHECKS.items()
    ]

    schemas: list[dict[str, Any]] = []
    for selection in RELEVANT_MESSAGES:
        schema = message_schema(metadata, defaults, selection["type"])
        actual_id = registry_by_name.get(selection["enumName"])
        schemas.append(
            {
                **schema,
                "direction": selection["direction"],
                "enumName": selection["enumName"],
                "messageId": actual_id,
                "expectedId": selection["expectedId"],
                "idMatches": actual_id == selection["expectedId"],
                "classification": selection["classification"],
                "nativeHooks": sorted(native_hooks_by_message_id.get(actual_id, [])),
                "nativeEvidence": (
                    NATIVE_MISSION_EVENT_PATHS.get(actual_id)
                    or NATIVE_LEVEL_SCRIPT_EVENT_PATHS.get(actual_id)
                ),
            }
        )

    return {
        "_schema": "endfieldProtocolRegistryAudit.v2",
        "source": {
            "metadata": str(metadata_path.resolve()),
            "metadataSize": len(metadata.buf),
            "metadataVersion": metadata.version,
            "metadataSha256": file_sha256(metadata_path),
            "helper": str(helper_path.resolve()),
            "runtimeHookManifest": native_task_paths["manifest"],
            "runtimeHookManifestSha256": native_task_paths["manifestSha256"],
            "gameBuild": native_task_paths["gameBuild"],
        },
        "summary": {
            "clientToServerMessages": len(cs),
            "serverToClientMessages": len(sc),
            "totalMessages": len(cs) + len(sc),
            "knownIdChecks": len(checks),
            "knownIdChecksPassed": sum(row["matches"] for row in checks),
            "selectedSchemas": len(schemas),
            "selectedSchemaIdsMatched": sum(row["idMatches"] for row in schemas),
            "nativeTaskHooks": len(native_task_paths["hooks"]),
            "nativeMissionEventPaths": len(NATIVE_MISSION_EVENT_PATHS),
            "nativeLevelScriptEventPaths": len(NATIVE_LEVEL_SCRIPT_EVENT_PATHS),
            "serializedCustomMissionEventListeners": (
                mission_event_assets["customMissionEventListeners"]
                + mission_event_assets["levelScriptCustomMissionEventRecords"]
            ),
        },
        "evidencePolicy": {
            "registry": (
                "Enum constants prove current-build message IDs; they do not prove that "
                "a sender, handler, or request/response pairing is active."
            ),
            "schemas": (
                "Generated protobuf fields prove payload shape only. Type/member names "
                "do not create Mission Pipeline ownership, order, branch, or merge edges."
            ),
            "succeedId": (
                "SC_MISSION_STATE_UPDATE.succeedId is a mission-completion outcome/result "
                "selector passed to CompleteMission and checked by CheckMissionSucceedId; "
                "it is not a successor mission id."
            ),
            "curMainMissionId": (
                "curMainMissionId is synchronized current-main selection/state. It is not "
                "a chronological predecessor or successor edge."
            ),
            "levelScriptTasks": (
                "The task packet family exposes exact (sceneNumId, scriptId, taskId) "
                "identity, and current-build native sender/handler paths are proven "
                "separately by the runtime-hook manifest and disassembly. No packet "
                "co-carries missionId or questId, so it still cannot attach Story to a mission."
            ),
            "missionClientEvent": (
                "Message 125 has a current-build native handler that interns its exact "
                "missionId/eventName pair and publishes the resulting key through "
                "EventManager.SendGlobal. It does not dispatch to the serialized "
                "OnCustomEventForMission family. The complete direct two-part-key call "
                "census finds no typed exact-pair subscriber, but indirect delegate, IFix, "
                "and XLua consumers remain outside that bound."
            ),
            "levelScriptEventContext": (
                "Message 57 constructs a LevelScript receiver from scriptId, preserves a "
                "non-empty ctxToken in EventParams, and raises eventName. ctxToken is "
                "therefore opaque propagated event context, not a discarded field. The "
                "handler neither decodes it as mission/quest identity nor receives either "
                "identity in the packet, so it creates no Mission Pipeline ownership edge."
            ),
            "traffic": (
                "Header-only traffic can recover message-type chronology. Payload-aware "
                "capture is required for missionId, questId, sceneNumId, scriptId, taskId, "
                "and eventName identity. Observation alone remains runtime evidence, not an "
                "authored global order."
            ),
        },
        "knownIdChecks": checks,
        "nativeTaskPaths": native_task_paths["hooks"],
        "nativeMissionEventPaths": NATIVE_MISSION_EVENT_PATHS,
        "nativeLevelScriptEventPaths": NATIVE_LEVEL_SCRIPT_EVENT_PATHS,
        "missionEventConstructorXrefs": MISSION_EVENT_CONSTRUCTOR_XREF_FINDING,
        "missionEventAssetCoverage": mission_event_assets,
        "selectedSchemas": schemas,
        "registry": {
            "clientToServer": cs,
            "serverToClient": sc,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    policy = report["evidencePolicy"]
    lines = [
        "# Protocol registry and Story schema audit",
        "",
        "## Summary",
        "",
        f"- Client to server messages: **{summary['clientToServerMessages']:,}**",
        f"- Server to client messages: **{summary['serverToClientMessages']:,}**",
        f"- Total enum entries: **{summary['totalMessages']:,}**",
        (
            f"- Known-ID checks: **{summary['knownIdChecksPassed']}/"
            f"{summary['knownIdChecks']}** passed"
        ),
        (
            f"- Selected schema IDs: **{summary['selectedSchemaIdsMatched']}/"
            f"{summary['selectedSchemas']}** matched"
        ),
        f"- Metadata SHA-256: `{report['source']['metadataSha256']}`",
        f"- Native task hooks: **{summary['nativeTaskHooks']}**",
        f"- Native mission-event paths: **{summary['nativeMissionEventPaths']}**",
        (
            "- Native LevelScript-event paths: "
            f"**{summary['nativeLevelScriptEventPaths']}**"
        ),
        (
            "- Serialized custom-mission-event listeners (separate action family): "
            f"**{summary['serializedCustomMissionEventListeners']}**"
        ),
        f"- Runtime-hook manifest SHA-256: `{report['source']['runtimeHookManifestSha256']}`",
        "",
        "## Evidence boundary",
        "",
    ]
    lines.extend(f"- **{md_escape(key)}:** {md_escape(value)}" for key, value in policy.items())
    lines.extend(
        [
            "",
            "## Current-build native task paths",
            "",
            "| Hook | Message | Token | RVA | Capture scope |",
            "|---|---|---|---|---|",
        ]
    )
    for name, hook in report["nativeTaskPaths"].items():
        message = (
            f"{hook['messageId']} `{hook.get('message', '')}`"
            if "messageId" in hook
            else "local/runtime"
        )
        lines.append(
            "| {name} | {message} | `{token}` | `{rva}` | {scope} |".format(
                name=md_escape(name),
                message=md_escape(message),
                token=md_escape(str(hook.get("token", ""))),
                rva=md_escape(str(hook.get("rva", ""))),
                scope=md_escape(str(hook.get("captureScope", ""))),
            )
        )
    coverage = report["missionEventAssetCoverage"]
    lines.extend(
        [
            "",
            "## Current-build mission-event path",
            "",
            (
                "`SC_SCENE_TRIGGER_CLIENT_MISSION_EVENT (125)` reaches "
                "`MissionSystem.Handle_ClientMissionEvent` at `0x1873bdf58`. The handler "
                "reads `missionId` from object offset `+0x18`, reads `eventName` from "
                "`+0x20`, and calls `KeyGenerator<T1,T2>.GetKey` at `0x184a428a0`. "
                "That generic body reaches `CombineKeyManager.GetKey`; the returned "
                "runtime-interned key is then published through "
                "`EventManager.SendGlobal` at `0x187bdfd38`."
            ),
            "",
            (
                f"The refreshed asset scan found **{coverage['missionActionHeaders']:,}** "
                "MissionRuntime action headers, "
                f"**{coverage['customMissionEventListeners']:,}** typed custom-mission "
                "listeners, and "
                f"**{coverage['levelScriptCustomMissionEventRecords']:,}** matching "
                "LevelScript records. Those zeroes describe the separate serialized "
                "`MissionEvent_OnCustomEventForMission` family; they are not a consumer "
                "census for the keyed global event bus."
            ),
            "",
            (
                "Across all seven `KeyGenerator<T1,T2>.GetKey` instantiations, the "
                "direct-call census names all 35 `E8 rel32` callers. Message 125 shares "
                "one instantiation with `SimpleConditionCheckMapVar`, but the subscriber "
                "serializes `belongMapId/mapVarName` while the publisher supplies "
                "`missionId/eventName`; this does not prove an exact typed pairing. "
                "Delegate, vtable, IFix, and XLua dispatch remain outside this bound."
            ),
            "",
            (
                f"All **{coverage['clientActionMappings']:,}** real quest client-action "
                "mappings resolve to an exported typed action; these are a separate, "
                "already-consumed quest transition surface."
            ),
            "",
            (
                report["missionEventConstructorXrefs"]["finding"]
            ),
        ]
    )
    level_event = report["nativeLevelScriptEventPaths"][57]
    lines.extend(
        [
            "",
            "## Current-build LevelScript event context",
            "",
            (
                "`SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT (57)` reaches "
                f"`{level_event['symbol']}` at `{level_event['va']}`. The handler "
                "constructs a `LevelScriptPtr` receiver from `scriptId`, allocates "
                "`EventParams`, and raises `eventName` through "
                "`LevelEventManager.RaiseScriptEvent`."
            ),
            "",
            (
                "When `ctxToken` is non-empty, the handler copies the protobuf bytes into "
                "the EventParams/ParamBlackboard before raising the event. It does not "
                "interpret the token as a mission or quest id. This proves context "
                "propagation into downstream event actions, but message 57 still carries "
                "no mission/quest identity and therefore creates no ownership or order edge."
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## Story-facing message schemas",
            "",
            "| ID | Direction | Message | Fields by protobuf tag | Classification |",
            "|---:|---|---|---|---|",
        ]
    )
    for schema in report["selectedSchemas"]:
        fields = ", ".join(
            f"{field.get('tag', '?')}:{field.get('name') or field.get('constantName', '?')}"
            for field in schema["fields"]
        )
        lines.append(
            "| {message_id} | {direction} | `{message}` | {fields} | `{classification}` |".format(
                message_id=schema.get("messageId", "?"),
                direction=md_escape(schema["direction"]),
                message=md_escape(schema["type"].removeprefix("Proto.")),
                fields=md_escape(fields),
                classification=md_escape(schema["classification"]),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The task family names an exact scene, LevelScript, and task. Current-build "
                "native sender/handler paths are now mapped, but the family still stops one "
                "join short of mission/quest ownership because its packets contain no mission "
                "or quest id."
            ),
            "",
            (
                "`succeedId` must not be used as a mission successor. Native "
                "`MissionSystem.Handle_MissionStateUpdate` copies it into local mission "
                "completion state and passes it to `CompleteMission`; typed "
                "`CheckMissionSucceedId` conditions compare that outcome selector."
            ),
            "",
            (
                "The complete registry is retained in the JSON report. This Markdown view "
                "intentionally lists only Story-facing schemas."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--helper", type=Path, default=METADATA_HELPER)
    parser.add_argument(
        "--mission-runtime-root",
        type=Path,
        default=MISSION_RUNTIME_ROOT,
    )
    parser.add_argument(
        "--union-audit",
        type=Path,
        default=MEMORYPACK_UNION_AUDIT,
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=REPORT_ROOT / "protocol_registry_audit.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=REPORT_ROOT / "protocol_registry_audit.md",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.metadata.is_file():
        raise SystemExit(f"metadata file not found: {args.metadata}")
    if not args.helper.is_file():
        raise SystemExit(f"metadata helper not found: {args.helper}")
    report = build_report(
        args.metadata,
        args.helper,
        mission_runtime_root=args.mission_runtime_root,
        union_audit_path=args.union_audit,
    )
    write_report_json(args.json_output, report)
    write_text_if_changed(args.markdown_output, render_markdown(report))
    print(
        f"wrote {args.json_output} and {args.markdown_output}: "
        f"{report['summary']['totalMessages']} messages, "
        f"{report['summary']['selectedSchemas']} selected schemas"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
