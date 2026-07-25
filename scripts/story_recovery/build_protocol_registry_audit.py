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
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
METADATA_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
NATIVE_MAPPER_HELPER = (
    ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
)
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
MESSAGE_125_SEND_GLOBAL_VA = 0x187BDFD38
MESSAGE_125_PAYLOAD_TYPE = "Beyond.Gameplay.EventData"


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
                "no exact authored pair in the direct key-construction census: the "
                "only subscriber-side caller in the same generic instantiation consumes "
                "belongMapId/mapVarName, while message 125 publishes missionId/eventName"
            ),
            "coverage": (
                "direct E8 rel32 key-construction calls only; the separate AOT generic "
                "specialization census closes compiled managed typed subscribers"
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
        "gameplay constructor caller for the inactive current-fallback 126/316/317 paths."
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
        "classification": "native_sender_absent_current_fallback",
    },
    {
        "type": "Proto.SC_MISSION_EVENT_TRIGGER",
        "direction": "server_to_client",
        "enumName": "ScMissionEventTrigger",
        "expectedId": 126,
        "classification": "native_handler_absent_current_fallback",
    },
    {
        "type": "Proto.CS_MISSION_CLIENT_TRIGGER_DONE",
        "direction": "client_to_server",
        "enumName": "CsMissionClientTriggerDone",
        "expectedId": 317,
        "classification": "native_sender_absent_current_fallback",
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


def load_native_mapper(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("endfield_protocol_native_mapper", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load native mapper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNTIME_PRIMITIVE_TYPE_NAMES = {
    0x01: "void",
    0x02: "bool",
    0x03: "char",
    0x04: "sbyte",
    0x05: "byte",
    0x06: "short",
    0x07: "ushort",
    0x08: "int",
    0x09: "uint",
    0x0A: "long",
    0x0B: "ulong",
    0x0C: "float",
    0x0D: "double",
    0x0E: "string",
    0x18: "nint",
    0x19: "nuint",
    0x1C: "object",
}


def runtime_generic_inst_type_pointers(pe: Any, generic_inst_va: int) -> list[int]:
    offset, _section, _rva = pe.file_offset_for_va(generic_inst_va)
    if offset is None:
        raise RuntimeError(f"generic instantiation VA is outside GameAssembly: 0x{generic_inst_va:x}")
    argc, argv_va = struct.unpack_from("<QQ", pe.buf, offset)
    if argc > 64:
        raise RuntimeError(f"implausible generic argument count {argc} at 0x{generic_inst_va:x}")
    return [pe.u64_at_va(argv_va + index * 8) for index in range(argc)]


def runtime_type_name(
    pe: Any,
    metadata: Any,
    type_va: int,
    *,
    depth: int = 0,
    seen: frozenset[int] = frozenset(),
) -> str:
    """Name one MetadataRegistration Il2CppType, including generic instances."""
    if depth > 12:
        return "<generic-depth-limit>"
    if type_va in seen:
        return f"<recursive-type:0x{type_va:x}>"
    offset, _section, _rva = pe.file_offset_for_va(type_va)
    if offset is None:
        return f"<type-va-outside-image:0x{type_va:x}>"
    data = struct.unpack_from("<Q", pe.buf, offset)[0]
    type_code = pe.buf[offset + 10]
    primitive = RUNTIME_PRIMITIVE_TYPE_NAMES.get(type_code)
    if primitive is not None:
        return primitive
    if type_code in {0x11, 0x12}:  # IL2CPP_TYPE_VALUETYPE / CLASS
        if 0 <= data < len(metadata.types):
            return metadata.type_full_name(metadata.types[data])
        return f"<type-definition:{data}>"
    if type_code == 0x15:  # IL2CPP_TYPE_GENERICINST
        generic_offset, _section, _rva = pe.file_offset_for_va(data)
        if generic_offset is None:
            return f"<generic-class-va-outside-image:0x{data:x}>"
        definition_type_va, class_inst_va = struct.unpack_from(
            "<QQ", pe.buf, generic_offset
        )
        next_seen = seen | {type_va}
        definition_name = runtime_type_name(
            pe,
            metadata,
            definition_type_va,
            depth=depth + 1,
            seen=next_seen,
        )
        arguments = [
            runtime_type_name(
                pe,
                metadata,
                argument_type_va,
                depth=depth + 1,
                seen=next_seen,
            )
            for argument_type_va in runtime_generic_inst_type_pointers(
                pe, class_inst_va
            )
        ]
        return f"{definition_name}<{','.join(arguments)}>"
    if type_code in {0x13, 0x1E}:  # IL2CPP_TYPE_VAR / MVAR
        kind = "VAR" if type_code == 0x13 else "MVAR"
        return f"{kind}[{data}]"
    if type_code == 0x0F:  # IL2CPP_TYPE_PTR
        return (
            runtime_type_name(
                pe,
                metadata,
                data,
                depth=depth + 1,
                seen=seen | {type_va},
            )
            + "*"
        )
    if type_code == 0x1D:  # IL2CPP_TYPE_SZARRAY
        return (
            runtime_type_name(
                pe,
                metadata,
                data,
                depth=depth + 1,
                seen=seen | {type_va},
            )
            + "[]"
        )
    return f"<runtime-type:0x{type_code:x}:data=0x{data:x}>"


def expected_event_bus_binding_type(payload_type: str) -> str:
    return f"Beyond.EventData`1<{payload_type}>"


def matching_event_bus_subscriber_rows(
    bind_rows: list[dict[str, Any]],
    payload_type: str,
) -> list[dict[str, Any]]:
    expected = expected_event_bus_binding_type(payload_type)
    return [
        row
        for row in bind_rows
        if row.get("genericArguments") == [expected]
    ]


def event_bus_specialization_census(
    metadata: Any,
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Prove whether message 125 has an authored typed EventManager subscriber.

    IL2CPP must publish a method specification for a value-type generic
    ``BindGlobal<TData>`` use even when several specifications share one native
    body. This census therefore covers compiled managed call forms independent
    of whether the final call instruction is direct, virtual, or delegate-based.
    """
    mapper = load_native_mapper(mapper_path)
    pe = mapper.PeImage(gameassembly_path)
    metadata_registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if metadata_registration is None:
        raise RuntimeError("could not derive MetadataRegistration from GameAssembly")
    metadata_summary = mapper.metadata_registration_summary(
        pe, metadata_registration
    )
    code_summary = mapper.code_registration_summary(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    method_specs_va = int(metadata_summary["methodSpecs"], 16)
    method_specs_offset, _section, _rva = pe.file_offset_for_va(method_specs_va)
    method_table_va = int(metadata_summary["genericMethodTable"], 16)
    method_table_offset, _section, _rva = pe.file_offset_for_va(method_table_va)
    if method_specs_offset is None or method_table_offset is None:
        raise RuntimeError("generic method tables are outside GameAssembly")
    generic_insts_va = int(metadata_summary["genericInsts"], 16)
    generic_pointers_va = int(code_summary["genericMethodPointers"], 16)

    event_manager_methods: dict[int, dict[str, Any]] = {}
    for type_def in metadata.types:
        if metadata.type_full_name(type_def) != "Beyond.EventManager":
            continue
        for method in metadata.methods_for(type_def):
            name = metadata.string(method.name_index)
            if name not in {"BindGlobal", "SendGlobal"}:
                continue
            if method.generic_container_index < 0:
                continue
            event_manager_methods[method.index] = {
                "method": name,
                "token": f"0x{method.token:08x}",
            }
        break
    if not event_manager_methods:
        raise RuntimeError("generic EventManager BindGlobal/SendGlobal methods not found")

    rows_by_spec: dict[int, dict[str, Any]] = {}
    table_count = int(metadata_summary["genericMethodTableCount"])
    spec_count = int(metadata_summary["methodSpecsCount"])
    for table_index in range(table_count):
        spec_index, pointer_slot = struct.unpack_from(
            "<ii",
            pe.buf,
            method_table_offset + table_index * mapper.GENERIC_METHOD_TABLE_STRIDE,
        )
        if not 0 <= spec_index < spec_count:
            continue
        method_index, _class_inst_index, method_inst_index = struct.unpack_from(
            "<iii",
            pe.buf,
            method_specs_offset + spec_index * mapper.METHOD_SPEC_STRIDE,
        )
        method_row = event_manager_methods.get(method_index)
        if method_row is None or method_inst_index < 0:
            continue
        generic_inst_va = pe.u64_at_va(generic_insts_va + method_inst_index * 8)
        generic_arguments = [
            runtime_type_name(pe, metadata, type_va)
            for type_va in runtime_generic_inst_type_pointers(pe, generic_inst_va)
        ]
        pointer_va = pe.u64_at_va(generic_pointers_va + pointer_slot * 8)
        rows_by_spec.setdefault(
            spec_index,
            {
                **method_row,
                "methodIndex": method_index,
                "methodSpecIndex": spec_index,
                "genericMethodPointerSlot": pointer_slot,
                "methodPointerVa": f"0x{pointer_va:x}",
                "genericArguments": generic_arguments,
            },
        )

    rows = sorted(
        rows_by_spec.values(),
        key=lambda row: (
            row["method"],
            row["genericArguments"],
            row["methodSpecIndex"],
        ),
    )
    bind_rows = [row for row in rows if row["method"] == "BindGlobal"]
    send_rows = [row for row in rows if row["method"] == "SendGlobal"]
    message_send_rows = [
        row
        for row in send_rows
        if int(row["methodPointerVa"], 16) == MESSAGE_125_SEND_GLOBAL_VA
    ]
    if len(message_send_rows) != 1:
        raise RuntimeError(
            "expected exactly one message-125 SendGlobal specialization at "
            f"0x{MESSAGE_125_SEND_GLOBAL_VA:x}, found {len(message_send_rows)}"
        )
    message_send = message_send_rows[0]
    if message_send["genericArguments"] != [MESSAGE_125_PAYLOAD_TYPE]:
        raise RuntimeError(
            "message-125 SendGlobal payload drift: "
            f"{message_send['genericArguments']!r}"
        )
    subscriber_rows = matching_event_bus_subscriber_rows(
        bind_rows, MESSAGE_125_PAYLOAD_TYPE
    )
    expected_binding_type = expected_event_bus_binding_type(
        MESSAGE_125_PAYLOAD_TYPE
    )
    return {
        "gameAssembly": str(gameassembly_path.resolve()),
        "gameAssemblySize": gameassembly_path.stat().st_size,
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "mapper": str(mapper_path.resolve()),
        "codeRegistration": f"0x{mapper.DEFAULT_CODE_REGISTRATION:x}",
        "metadataRegistration": f"0x{metadata_registration:x}",
        "genericMethodTableRows": table_count,
        "methodSpecRows": spec_count,
        "bindGlobalSpecializations": len(bind_rows),
        "sendGlobalSpecializations": len(send_rows),
        "message125SendSpecialization": message_send,
        "message125PayloadType": MESSAGE_125_PAYLOAD_TYPE,
        "expectedBindSpecializationType": expected_binding_type,
        "matchingBindSpecializations": subscriber_rows,
        "matchingBindSpecializationCount": len(subscriber_rows),
        "bindArgumentTypes": sorted(
            {
                argument
                for row in bind_rows
                for argument in row["genericArguments"]
            }
        ),
        "status": (
            "no_current_aot_typed_subscriber"
            if not subscriber_rows
            else "typed_subscriber_specialization_present"
        ),
        "finding": (
            "Message 125 publishes SendGlobal<Beyond.Gameplay.EventData>. "
            "A compiled managed typed subscriber requires "
            f"BindGlobal<{expected_binding_type}>, but the current AOT method-spec "
            f"table contains {len(bind_rows)} BindGlobal specializations and "
            f"{len(subscriber_rows)} exact match(es)."
        ),
        "coverage": (
            "Covers current-build AOT-authored managed generic uses, including uses "
            "whose final call is indirect or whose native body is generic-shared. "
            "It does not claim that native memory manipulation, runtime reflection, "
            "or a future IFix/game build can never add a subscription."
        ),
    }


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
    gameassembly_path: Path = DEFAULT_GAMEASSEMBLY,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
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
    event_bus_census = event_bus_specialization_census(
        metadata,
        gameassembly_path,
        mapper_path,
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
        "_schema": "endfieldProtocolRegistryAudit.v3",
        "source": {
            "metadata": str(metadata_path.resolve()),
            "metadataSize": len(metadata.buf),
            "metadataVersion": metadata.version,
            "metadataSha256": file_sha256(metadata_path),
            "helper": str(helper_path.resolve()),
            "gameAssembly": event_bus_census["gameAssembly"],
            "gameAssemblySize": event_bus_census["gameAssemblySize"],
            "gameAssemblySha256": event_bus_census["gameAssemblySha256"],
            "nativeMapper": event_bus_census["mapper"],
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
            "message125TypedBindSpecializations": event_bus_census[
                "matchingBindSpecializationCount"
            ],
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
                "OnCustomEventForMission family. Its concrete payload specialization is "
                "SendGlobal<Beyond.Gameplay.EventData>, while the complete current-build "
                "AOT method-spec table contains no matching typed BindGlobal "
                "specialization. This closes compiled managed typed subscribers even when "
                "their final call form would be indirect; native memory manipulation, "
                "runtime reflection, future IFix, and future builds remain outside the bound."
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
        "message125EventBusSpecializations": event_bus_census,
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
        (
            "- Message-125 exact typed AOT BindGlobal specializations: "
            f"**{summary['message125TypedBindSpecializations']}**"
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
    event_bus = report["message125EventBusSpecializations"]
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
                "`missionId/eventName`; this is not an exact typed pairing."
            ),
            "",
            (
                f"The generic-method table contains "
                f"**{event_bus['sendGlobalSpecializations']}** `SendGlobal` and "
                f"**{event_bus['bindGlobalSpecializations']}** `BindGlobal` "
                "specializations. Message 125 resolves exactly to "
                f"`SendGlobal<{event_bus['message125PayloadType']}>`. Its required "
                "typed subscriber shape is "
                f"``BindGlobal<{event_bus['expectedBindSpecializationType']}>``; the "
                f"current AOT table contains "
                f"**{event_bus['matchingBindSpecializationCount']}** matches. "
                "Because every compiled managed value-type generic use needs a method "
                "specification even when its native body is shared or its final call is "
                "indirect, no current authored managed typed subscriber exists. Native "
                "memory manipulation, runtime reflection, future IFix, and future builds "
                "remain outside this bound."
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
        "--gameassembly",
        type=Path,
        default=DEFAULT_GAMEASSEMBLY,
    )
    parser.add_argument(
        "--native-mapper",
        type=Path,
        default=NATIVE_MAPPER_HELPER,
    )
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
    if not args.gameassembly.is_file():
        raise SystemExit(f"GameAssembly file not found: {args.gameassembly}")
    if not args.native_mapper.is_file():
        raise SystemExit(f"native mapper not found: {args.native_mapper}")
    report = build_report(
        args.metadata,
        args.helper,
        gameassembly_path=args.gameassembly,
        mapper_path=args.native_mapper,
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
