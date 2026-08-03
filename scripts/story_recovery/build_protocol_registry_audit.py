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
import os
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
from story_builder.mission_assets import select_complete_mission_runtime_root  # noqa: E402


DEFAULT_GAME_DATA_ROOT = Path(
    os.environ.get(
        "ENDFIELD_GAME_ROOT",
        r"D:\Program Files\Endfield Game\Endfield_Data",
    )
)
DEFAULT_METADATA = DEFAULT_GAME_DATA_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_GAMEASSEMBLY = DEFAULT_GAME_DATA_ROOT.parent / "GameAssembly.dll"
METADATA_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
NATIVE_MAPPER_HELPER = (
    ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
)
REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
RUNTIME_HOOK_MANIFEST = (
    ROOT / "scripts" / "story_recovery" / "mission_runtime_trace_hooks.json"
)
MISSION_RUNTIME_ROOT = select_complete_mission_runtime_root(
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset",
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
            "ctxToken is propagated as event context rather than discarded. Its sole "
            "current direct AOT key-slot reader is CallServer.Execute, which recovers it "
            "as netToken and returns it on CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER. Neither "
            "side decodes it into missionId or questId, and neither packet contains "
            "either identity."
        ),
        "ctxTokenReaderAudit": {
            "paramBlackboardKeySlotVa": "0x18e2eef08",
            "directRipReferenceCount": 4,
            "referencingMethodCount": 2,
            "referencingMethods": [
                {
                    "symbol": (
                        "Beyond.Gameplay.GameplayNetwork."
                        "_Handle_SceneTriggerClientLevelScriptEvent"
                    ),
                    "va": "0x187386320",
                    "references": ["0x187386362", "0x187386442"],
                    "role": "static-key initialization and ctxToken writer",
                },
                {
                    "symbol": "Beyond.Gameplay.Actions.CallServer.Execute",
                    "token": "0x06008f04",
                    "va": "0x1845f6000",
                    "references": ["0x1845f6098", "0x1845f618f"],
                    "role": (
                        "static-key initialization and "
                        "ParamBlackboard.TryGetValue(netToken) reader"
                    ),
                },
            ],
            "readerCall": {
                "symbol": "Beyond.Gameplay.ParamBlackboard.TryGetValue",
                "va": "0x1836eb730",
                "callSite": "0x1845f61a6",
                "genericInstantiation": True,
            },
            "outboundPath": [
                {
                    "symbol": "Beyond.Gameplay.Actions.GameAction.TriggerServerEvent",
                    "token": "0x060080c7",
                    "va": "0x1845f6640",
                    "parameter": "netToken",
                },
                {
                    "symbol": (
                        "Beyond.Gameplay.GameplayNetwork."
                        "TriggerLevelScriptServerEvent"
                    ),
                    "token": "0x06004dc5",
                    "va": "0x1845f6710",
                    "parameter": "netToken",
                },
                {
                    "symbol": (
                        "Proto.CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.set_CtxToken"
                    ),
                    "token": "0x0600891c",
                    "va": "0x1865a3aac",
                },
            ],
            "installedIfix": {
                "sha256": (
                    "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21"
                ),
                "signatureTargetCount": 30,
                "fallbackPatchIds": ["0x5ac7", "0x8939", "0x39bb", "0x39bc"],
                "matchedMethods": 0,
            },
            "classification": "level_script_event_round_trip_correlation",
            "missionQuestReaders": 0,
            "storyBindingsAdded": 0,
            "coverage": (
                "Current installed AOT direct RIP references to the exact static key "
                "slot, including the generic-shared TryGetValue instantiation, plus the "
                "decoded installed IFix target list. Separately constructed equal keys, "
                "reflection, native memory manipulation, future IFix, and future builds "
                "remain outside the bound."
            ),
        },
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
        "type": "Proto.SC_QUEST_STATE_UPDATE",
        "direction": "server_to_client",
        "enumName": "ScQuestStateUpdate",
        "expectedId": 111,
        "classification": "native_handler_proven",
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
        "classification": "native_handler_proven",
    },
    {
        "type": "Proto.SC_SET_QUEST_ENABLE",
        "direction": "server_to_client",
        "enumName": "ScSetQuestEnable",
        "expectedId": 122,
        "classification": "native_handler_proven",
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


def protobuf_identity_field_classes(field_name: str) -> set[str]:
    """Classify protobuf storage fields relevant to the missing ownership join."""
    name = normalized_field_name(field_name)
    classes: set[str] = set()
    name_without_request_id = name.replace("requestid", "")
    if "missionid" in name or "questid" in name_without_request_id:
        classes.add("mission_or_quest")
    if "scriptid" in name.replace("transcriptid", ""):
        classes.add("level_script")
    if (
        name in {"scenenumid", "sceneid", "scenename", "levelid", "mapid"}
        or name.endswith(("scenenumid", "scenename", "levelid", "mapid"))
        or (
            name.endswith("sceneid")
            and not name.endswith("cutsceneid")
        )
    ):
        classes.add("scene_host")
    if any(
        token in name
        for token in ("dialogid", "radioid", "cutsceneid", "timelineid", "storyid")
    ):
        classes.add("story")
    return classes


def protobuf_runtime_dependencies(
    runtime_type_name_value: str,
    known_proto_types: set[str],
) -> list[str]:
    """Return exact Proto type dependencies from one recovered runtime type."""
    return sorted(
        {
            candidate
            for candidate in re.findall(
                r"Proto\.[A-Za-z0-9_+`]+",
                runtime_type_name_value,
            )
            if candidate in known_proto_types
        }
    )


def protobuf_identity_carrier_census(
    metadata: Any,
    gameassembly_path: Path,
    registry_rows: list[dict[str, Any]],
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Census direct and nested message identity carriers in the current build."""
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
    runtime_types_va = int(metadata_summary["types"], 16)
    runtime_type_count = int(metadata_summary["typesCount"])
    runtime_name_cache: dict[int, str] = {}

    def runtime_field_type_name(type_index: int) -> str:
        if type_index not in runtime_name_cache:
            if not 0 <= type_index < runtime_type_count:
                runtime_name_cache[type_index] = f"<type-index:{type_index}>"
            else:
                type_va = pe.u64_at_va(runtime_types_va + type_index * 8)
                runtime_name_cache[type_index] = runtime_type_name(
                    pe,
                    metadata,
                    type_va,
                )
        return runtime_name_cache[type_index]

    proto_types: dict[str, list[dict[str, str]]] = {}
    cs_sc_type_count = 0
    for type_def in metadata.types:
        type_name = metadata.type_full_name(type_def)
        if not type_name.startswith("Proto."):
            continue
        if type_name.startswith(("Proto.CS_", "Proto.SC_")):
            cs_sc_type_count += 1
        fields: list[dict[str, str]] = []
        for field in metadata.fields_for(type_def):
            storage_name = metadata.string(field.name_index)
            if not storage_name.endswith("_"):
                continue
            fields.append(
                {
                    "name": storage_name[:-1],
                    "runtimeType": runtime_field_type_name(field.type_index),
                }
            )
        proto_types[type_name] = fields

    registry_by_normalized_name = {
        normalized_field_name(row["name"]): row
        for row in registry_rows
    }
    return finish_protobuf_identity_carrier_census(
        metadata_registration=metadata_registration,
        runtime_types_va=runtime_types_va,
        runtime_type_count=runtime_type_count,
        proto_types=proto_types,
        cs_sc_type_count=cs_sc_type_count,
        registry_rows=registry_rows,
        registry_by_normalized_name=registry_by_normalized_name,
    )


STATE_LIFECYCLE_METHOD_RE = re.compile(
    r"^(?:Available|Start|Complete|Succeed|Fail|Cancel|Abort|Pause|Disable)"
    r"(?:Mission|Quest)$"
)


def state_update_candidate_schemas(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    server_registry: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Discover enum-backed mission/quest state messages from their field shape."""
    registry_by_normalized_name = {
        normalized_field_name(row["name"]): row
        for row in server_registry
    }
    candidates: list[dict[str, Any]] = []
    for type_def in metadata.types:
        type_name = metadata.type_full_name(type_def)
        if not type_name.startswith("Proto.SC_"):
            continue
        storage_names = {
            normalized_field_name(metadata.string(field.name_index))
            for field in metadata.fields_for(type_def)
            if metadata.string(field.name_index).endswith("_")
        }
        matches: list[tuple[str, list[str], str]] = []
        for stem in ("mission", "quest"):
            if f"{stem}id" not in storage_names:
                continue
            if f"{stem}state" in storage_names:
                matches.append((stem, [f"{stem}State"], "state_update"))
            elif "isenable" in storage_names and f"prev{stem}state" in storage_names:
                matches.append(
                    (stem, ["isEnable", f"prev{stem.title()}State"], "enable_update")
                )
        if len(matches) != 1:
            continue
        stem, control_names, control_kind = matches[0]
        registry_key = normalized_field_name(type_name.removeprefix("Proto."))
        registry_row = registry_by_normalized_name.get(registry_key)
        if registry_row is None:
            continue
        schema = message_schema(metadata, defaults, type_name)
        identity_name = f"{stem}Id"
        candidates.append(
            {
                "type": type_name,
                "typeIndex": type_def.index,
                "typeToken": f"0x{type_def.token:08x}",
                "entityKind": stem,
                "controlKind": control_kind,
                "messageId": registry_row["id"],
                "enumName": registry_row["name"],
                "identityField": identity_name,
                "controlFields": control_names,
                "schema": schema,
            }
        )
    return sorted(candidates, key=lambda row: (row["messageId"], row["type"]))


def runtime_type_field_offsets(
    metadata: Any,
    pe: Any,
    metadata_registration_summary: dict[str, Any],
    type_index: int,
) -> dict[str, int]:
    """Read one type's current-build instance offsets from MetadataRegistration."""
    table_count = int(metadata_registration_summary["fieldOffsetsCount"])
    if not 0 <= type_index < table_count:
        raise RuntimeError(
            f"field-offset type index {type_index} outside current table count {table_count}"
        )
    table_va = int(metadata_registration_summary["fieldOffsets"], 16)
    type_offsets_va = pe.u64_at_va(table_va + type_index * 8)
    if not type_offsets_va:
        raise RuntimeError(f"type {type_index} has no runtime field-offset row")
    type_def = metadata.types[type_index]
    return {
        metadata.string(field.name_index): pe.u32_at_va(type_offsets_va + index * 4)
        for index, field in enumerate(metadata.fields_for(type_def))
    }


def discover_state_update_handlers(
    metadata: Any,
    helper: Any,
    candidates: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Find native handler metadata by protobuf parameter type, not method token."""
    by_type = {row["type"]: [] for row in candidates}
    for type_def in metadata.types:
        owner_name = metadata.type_full_name(type_def)
        image_name = metadata.image_name_by_type_index.get(type_def.index, "")
        for method_offset, method in enumerate(metadata.methods_for(type_def)):
            method_info = helper.method_row(metadata, method)
            if not str(method_info["name"]).startswith(("Handle_", "_Handle_")):
                continue
            parameter_types = [
                str(param.get("typeName") or "")
                for param in method_info.get("parameterDetails") or []
            ]
            for candidate_type in by_type:
                if not any(
                    param_type == candidate_type
                    or param_type.startswith(candidate_type + "+")
                    for param_type in parameter_types
                ):
                    continue
                by_type[candidate_type].append(
                    {
                        "type": owner_name,
                        "image": image_name,
                        "typeIndex": type_def.index,
                        "method": method_info["name"],
                        "methodIndex": method_info["index"],
                        "methodOffsetInType": method_offset,
                        "token": method_info["token"],
                        "parameters": method_info["parameters"],
                        "parameterDetails": method_info["parameterDetails"],
                        "flags": method_info["flags"],
                    }
                )
    return by_type


def map_state_update_handler(
    row: dict[str, Any],
    mapper: Any,
    pe: Any,
    ranges: dict[str, dict[str, Any]],
    pointers_by_image: dict[str, list[int]],
    method_by_pointer: dict[int, list[dict[str, Any]]],
    sorted_pointers: list[int],
) -> dict[str, Any]:
    image_range = ranges.get(row["image"])
    pointers = pointers_by_image.get(row["image"], [])
    if not image_range:
        raise RuntimeError(f"missing image method range for {row['image']}")
    slot = row["methodIndex"] - image_range["methodStart"]
    if not 0 <= slot < len(pointers):
        raise RuntimeError(
            f"method slot {slot} outside {row['image']} pointer table ({len(pointers)})"
        )
    pointer = pointers[slot]
    if not pointer:
        raise RuntimeError(f"null native pointer for {row['type']}.{row['method']}")
    scan_size, next_pointer = mapper.estimate_scan_size(
        pointer, sorted_pointers, 4096
    )
    summary = mapper.build_method_body_summary(
        row,
        pe.bytes_at_va(pointer, scan_size),
        pointer,
        method_by_pointer,
        pe=pe,
        max_instructions=1200,
    )
    return {
        "symbol": f"{row['type']}.{row['method']}",
        "token": row["token"],
        "methodIndex": row["methodIndex"],
        "va": f"0x{pointer:x}",
        "rva": f"0x{pe.file_offset_for_va(pointer)[2]:x}",
        "scanBytes": scan_size,
        "nextMethodPointerVa": f"0x{next_pointer:x}" if next_pointer else None,
        "bodySummary": summary,
    }


def validate_state_update_application_rows(
    candidate_count: int,
    rows: list[dict[str, Any]],
    *,
    source_file: str,
    source_hashes: dict[str, str],
    prior_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fail closed with bounded diagnostics for the recovered application pattern."""
    failures = list(prior_failures or [])

    def add(gate: str, message: str | None, expected: Any, actual: Any) -> None:
        failures.append(
            {
                "validator": "state_update_application_census",
                "gate": gate,
                "message": message,
                "expected": expected,
                "actual": actual,
                "sourceFile": source_file,
                "sourceHashes": source_hashes,
            }
        )

    if len(rows) != candidate_count:
        add("validatedCandidateCount", None, candidate_count, len(rows))
    for row in rows:
        message = str(row.get("type") or "")
        if not row.get("samePacketIdentityForwardedToEveryLifecycleCall"):
            add(
                "sameIdentityForwarding",
                message,
                True,
                [
                    {
                        "method": call.get("method"),
                        "origin": call.get("observedArgumentOrigin"),
                    }
                    for call in row.get("lifecycleCalls") or []
                    if not call.get("samePacketIdentity")
                ],
            )
        if row.get("clientSuccessorSelectorPresent"):
            add(
                "noClientSuccessorSelector",
                message,
                [],
                row.get("successorLikeFields") or row.get("identityFields"),
            )
    return {
        "status": "validated" if not failures else "validation_failed",
        "failures": failures,
    }


def validate_quest_start_application_observation(
    *,
    field_reads: dict[str, int],
    quest_info_getters: list[dict[str, Any]],
    topology_calls: list[str],
    source_file: str,
    source_hashes: dict[str, str],
    prior_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fail closed on the reusable single-object initialization pattern."""
    failures = list(prior_failures or [])

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_start_application_contract",
            "gate": gate,
            "message": "Beyond.Gameplay.MissionSystem.StartQuest",
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    if len(quest_info_getters) != 1:
        fail("uniqueQuestInfoGetter", 1, quest_info_getters)
    if field_reads.get("objectiveList", 0) < 1:
        fail("objectiveInitializationRead", ">=1 objectiveList read", field_reads)
    topology_reads = {
        name: field_reads.get(name, 0)
        for name in ("prevQuestIdList", "flowIndex")
    }
    if any(topology_reads.values()):
        fail(
            "noClientTopologyReadDuringStart",
            {"prevQuestIdList": 0, "flowIndex": 0},
            topology_reads,
        )
    if topology_calls:
        fail("noClientSuccessorTraversalCall", [], topology_calls)
    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def quest_start_application_contract(
    metadata: Any,
    helper: Any,
    mapper: Any,
    pe: Any,
    metadata_summary: dict[str, Any],
    method_by_pointer: dict[int, list[dict[str, Any]]],
    sorted_pointers: list[int],
    state_rows: list[dict[str, Any]],
    gameassembly_path: Path,
) -> dict[str, Any]:
    """Trace the selected quest into its fields without assuming a mission id."""
    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_start_application_contract",
            "gate": gate,
            "message": "Beyond.Gameplay.MissionSystem.StartQuest",
            "expected": expected,
            "actual": actual,
            "sourceFile": str(gameassembly_path.resolve()),
            "sourceHashes": {
                "gameAssemblySha256": file_sha256(gameassembly_path),
                "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
            },
        })

    required_fields = {
        "questId",
        "objectiveList",
        "prevQuestIdList",
        "flowIndex",
    }
    quest_info_candidates: list[Any] = []
    for type_def in metadata.types:
        fields = {
            metadata.string(field.name_index)
            for field in metadata.fields_for(type_def)
        }
        if required_fields <= fields:
            quest_info_candidates.append(type_def)
    if len(quest_info_candidates) != 1:
        fail(
            "uniqueQuestInfoShape",
            1,
            [metadata.type_full_name(row) for row in quest_info_candidates],
        )
        return {
            "classification": "validation_failed",
            "validation": {"status": "validation_failed", "failures": failures},
        }
    quest_info = quest_info_candidates[0]
    quest_info_type = metadata.type_full_name(quest_info)

    start_calls = {
        (call.get("targetVa"), call.get("token"), call.get("symbol"))
        for row in state_rows
        if row.get("entityKind") == "quest"
        for call in row.get("lifecycleCalls") or []
        if call.get("method") == "StartQuest" and call.get("targetVa")
    }
    if len(start_calls) != 1:
        fail("uniqueStartQuestLifecycleTarget", 1, sorted(start_calls))
        return {
            "classification": "validation_failed",
            "questInfoType": quest_info_type,
            "validation": {"status": "validation_failed", "failures": failures},
        }
    start_va_text, _start_token, start_symbol = next(iter(start_calls))
    start_va = int(str(start_va_text), 16)
    target_rows = [
        row
        for row in method_by_pointer.get(start_va, [])
        if row.get("method") == "StartQuest"
    ]
    if len(target_rows) != 1:
        fail("uniqueStartQuestMetadataTarget", 1, target_rows)
        return {
            "classification": "validation_failed",
            "questInfoType": quest_info_type,
            "validation": {"status": "validation_failed", "failures": failures},
        }

    method_index = int(target_rows[0]["methodIndex"])
    method_def = metadata.methods[method_index]
    owner_def = metadata.types[method_def.declaring_type]
    method_info = helper.method_row(metadata, method_def)
    mapper_row = {
        "type": metadata.type_full_name(owner_def),
        "image": metadata.image_name_by_type_index.get(owner_def.index, ""),
        "method": method_info["name"],
        "methodIndex": method_index,
        "token": method_info["token"],
        "parameters": method_info["parameters"],
        "parameterDetails": method_info["parameterDetails"],
        "flags": method_info["flags"],
    }
    scan_size, next_pointer = mapper.estimate_scan_size(
        start_va, sorted_pointers, 8192
    )
    body = mapper.build_method_body_summary(
        mapper_row,
        pe.bytes_at_va(start_va, scan_size),
        start_va,
        method_by_pointer,
        pe=pe,
        max_instructions=2400,
    )
    offsets = runtime_type_field_offsets(
        metadata,
        pe,
        metadata_summary,
        quest_info.index,
    )
    selected_offsets = {
        name: offsets.get(name)
        for name in sorted(required_fields)
    }
    if any(offset is None for offset in selected_offsets.values()):
        fail("questInfoFieldOffsets", sorted(required_fields), selected_offsets)

    origin_counts = Counter(
        str(row.get("origin") or "")
        for row in body.get("fieldAccesses") or []
    )
    field_reads: dict[str, int] = {}
    for name, offset in selected_offsets.items():
        field_reads[name] = (
            origin_counts.get(f"return:{quest_info_type}+0x{offset:x}", 0)
            if isinstance(offset, int)
            else 0
        )
    quest_info_getters = [
        {
            "offset": call.get("offset"),
            "targetVa": call.get("targetVa"),
            "symbol": f"{target.get('type')}.{target.get('method')}",
            "returnOrigin": call.get("returnOrigin"),
        }
        for call in body.get("calls") or []
        for target in call.get("resolved") or []
        if target.get("returnTypeName") == quest_info_type
    ]
    topology_calls = sorted({
        f"{target.get('type')}.{target.get('method')}"
        for call in body.get("calls") or []
        for target in call.get("resolved") or []
        if re.search(
            r"(?:next|successor|previous|predecessor).*(?:mission|quest)|"
            r"(?:mission|quest).*(?:next|successor|previous|predecessor)",
            str(target.get("method") or ""),
            re.I,
        )
    })
    validation = validate_quest_start_application_observation(
        field_reads=field_reads,
        quest_info_getters=quest_info_getters,
        topology_calls=topology_calls,
        source_file=str(gameassembly_path.resolve()),
        source_hashes={
            "gameAssemblySha256": file_sha256(gameassembly_path),
            "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
        },
        prior_failures=failures,
    )

    return {
        "classification": "single_server_selected_quest_objective_initialization",
        "questInfoType": quest_info_type,
        "questInfoFieldOffsets": {
            name: f"0x{offset:x}" if isinstance(offset, int) else None
            for name, offset in selected_offsets.items()
        },
        "fieldReadCounts": field_reads,
        "questInfoGetterCalls": quest_info_getters,
        "topologyTraversalCalls": topology_calls,
        "startQuest": {
            "symbol": start_symbol,
            "token": method_info["token"],
            "va": f"0x{start_va:x}",
            "scanBytes": scan_size,
            "nextMethodPointerVa": f"0x{next_pointer:x}" if next_pointer else None,
            "parameters": method_info["parameters"],
        },
        "sourceMessages": sorted({
            row.get("type")
            for row in state_rows
            if row.get("entityKind") == "quest"
            and any(
                call.get("method") == "StartQuest"
                for call in row.get("lifecycleCalls") or []
            )
        }),
        "finding": (
            "StartQuest receives one server-selected quest identity, resolves only that "
            "QuestInfo, and reads its objectiveList while initializing client objective "
            "state. It does not read prevQuestIdList or flowIndex and makes no native "
            "predecessor/successor traversal call."
        ),
        "boundary": (
            "A MissionRuntime fan-out therefore proves authored prerequisite topology, "
            "not whether the server starts every arm, selects one exclusive arm, or "
            "applies another server-only eligibility rule. Explicit typed conditions or "
            "runtime branch carriers remain authoritative when present."
        ),
        "validation": validation,
    }


def state_update_application_census(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    helper: Any,
    server_registry: list[dict[str, Any]],
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Recover the general server-selected mission/quest state application pattern."""
    mapper = load_native_mapper(mapper_path)
    pe = mapper.PeImage(gameassembly_path)
    metadata_registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if metadata_registration is None:
        raise RuntimeError("state-update audit could not derive MetadataRegistration")
    metadata_summary = mapper.metadata_registration_summary(pe, metadata_registration)
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    sorted_pointers = sorted(
        {
            pointer
            for pointers in pointers_by_image.values()
            for pointer in pointers
            if pointer
        }
    )
    candidates = state_update_candidate_schemas(metadata, defaults, server_registry)
    handlers_by_type = discover_state_update_handlers(metadata, helper, candidates)
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    def fail(gate: str, candidate: dict[str, Any] | None, expected: Any, actual: Any) -> None:
        failures.append(
            {
                "validator": "state_update_application_census",
                "gate": gate,
                "message": candidate.get("type") if candidate else None,
                "expected": expected,
                "actual": actual,
                "sourceFile": str(gameassembly_path.resolve()),
                "sourceHashes": {
                    "gameAssemblySha256": file_sha256(gameassembly_path),
                    "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
                },
            }
        )

    if not candidates:
        fail("candidateDiscovery", None, ">=1 enum-backed identity+state schema", 0)
    for candidate in candidates:
        handlers = handlers_by_type.get(candidate["type"], [])
        if len(handlers) != 1:
            fail(
                "uniqueTypedHandler",
                candidate,
                1,
                [f"{row['type']}.{row['method']}" for row in handlers],
            )
            continue
        try:
            mapped = map_state_update_handler(
                handlers[0],
                mapper,
                pe,
                ranges,
                pointers_by_image,
                method_by_pointer,
                sorted_pointers,
            )
            all_offsets = runtime_type_field_offsets(
                metadata, pe, metadata_summary, candidate["typeIndex"]
            )
        except RuntimeError as exc:
            fail("nativeMapping", candidate, "mapped typed handler and fields", str(exc))
            continue
        schema_fields = candidate["schema"]["fields"]
        field_offsets = {
            field["name"]: all_offsets.get(field["storageName"])
            for field in schema_fields
        }
        identity_offset = field_offsets.get(candidate["identityField"])
        control_offsets = {
            name: field_offsets.get(name) for name in candidate["controlFields"]
        }
        if identity_offset is None or any(
            offset is None for offset in control_offsets.values()
        ):
            fail(
                "identityStateOffsets",
                candidate,
                [candidate["identityField"], *candidate["controlFields"]],
                field_offsets,
            )
            continue
        expected_identity_origin = f"param:msg+0x{identity_offset:x}"
        expected_control_origins = {
            name: f"param:msg+0x{offset:x}"
            for name, offset in control_offsets.items()
            if isinstance(offset, int)
        }
        body = mapped["bodySummary"]
        field_origins = {
            row.get("origin") for row in body.get("fieldLikeOrigins") or []
        }
        identity_operands = {
            row.get("operand")
            for row in body.get("fieldAccesses") or []
            if row.get("origin") == expected_identity_origin and row.get("operand")
        }
        consumed_control_fields = [
            name
            for name, origin in expected_control_origins.items()
            if origin in field_origins
        ]
        if expected_identity_origin not in field_origins or not consumed_control_fields:
            fail(
                "handlerFieldReads",
                candidate,
                {
                    "identity": expected_identity_origin,
                    "oneOfControls": expected_control_origins,
                },
                sorted(field_origins),
            )
        lifecycle_calls: list[dict[str, Any]] = []
        entity_suffix = candidate["entityKind"].title()
        for call in body.get("calls") or []:
            for target in call.get("resolved") or []:
                method_name = str(target.get("method") or "")
                if not STATE_LIFECYCLE_METHOD_RE.fullmatch(method_name):
                    continue
                if not method_name.endswith(entity_suffix):
                    continue
                observed_origin = (call.get("argumentOrigins") or {}).get("rdx")
                same_packet_identity = (
                    observed_origin == expected_identity_origin
                    or observed_origin in identity_operands
                )
                lifecycle_calls.append(
                    {
                        "method": method_name,
                        "symbol": f"{target.get('type')}.{method_name}",
                        "token": target.get("token"),
                        "callOffset": call.get("offset"),
                        "targetVa": call.get("targetVa"),
                        "identityArgumentRegister": "rdx",
                        "identityArgumentOrigin": expected_identity_origin,
                        "observedArgumentOrigin": observed_origin,
                        "samePacketIdentity": same_packet_identity,
                    }
                )
        if len(lifecycle_calls) < 2:
            fail(
                "lifecycleCalls",
                candidate,
                ">=2 typed lifecycle calls",
                [row["method"] for row in lifecycle_calls],
            )
        mismatched_calls = [
            row for row in lifecycle_calls if not row["samePacketIdentity"]
        ]
        if mismatched_calls:
            fail(
                "sameIdentityForwarding",
                candidate,
                expected_identity_origin,
                [
                    {
                        "method": row["method"],
                        "origin": row["observedArgumentOrigin"],
                    }
                    for row in mismatched_calls
                ],
            )
        identity_fields = [
            field["name"]
            for field in schema_fields
            if normalized_field_name(field["name"]) in {"missionid", "questid"}
        ]
        successor_like_fields = [
            field["name"]
            for field in schema_fields
            if re.search(r"(?:next|successor|prev)(?:mission|quest)?id", field["name"], re.I)
        ]
        rows.append(
            {
                **{key: value for key, value in candidate.items() if key != "schema"},
                "fields": [field["name"] for field in schema_fields],
                "stateField": consumed_control_fields[0]
                if consumed_control_fields
                else candidate["controlFields"][0],
                "consumedControlFields": consumed_control_fields,
                "fieldOffsets": {
                    name: f"0x{offset:x}" if isinstance(offset, int) else None
                    for name, offset in field_offsets.items()
                },
                "identityFields": identity_fields,
                "successorLikeFields": successor_like_fields,
                "handler": {
                    key: value for key, value in mapped.items() if key != "bodySummary"
                },
                "handlerFieldOrigins": sorted(field_origins),
                "lifecycleCalls": lifecycle_calls,
                "samePacketIdentityForwardedToEveryLifecycleCall": (
                    bool(lifecycle_calls) and not mismatched_calls
                ),
                "clientSuccessorSelectorPresent": bool(
                    len(identity_fields) > 1 or successor_like_fields
                ),
            }
        )
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }
    validation = validate_state_update_application_rows(
        len(candidates),
        rows,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
        prior_failures=failures,
    )
    quest_start = quest_start_application_contract(
        metadata,
        helper,
        mapper,
        pe,
        metadata_summary,
        method_by_pointer,
        sorted_pointers,
        rows,
        gameassembly_path,
    )
    return {
        "classification": "server_selected_identity_state_application",
        "discoveryPattern": {
            "message": (
                "enum-backed Proto.SC_* schema with exactly one missionId or questId "
                "plus either its matching state field or the isEnable/previous-state "
                "control pair"
            ),
            "handler": (
                "Handle_/_Handle_ method discovered by exact protobuf parameter type"
            ),
            "fieldLayout": "MetadataRegistration field-offset table",
            "nativeFlow": (
                "method-body origin tracking from the packet parameter into typed "
                "mission/quest lifecycle call arguments"
            ),
        },
        "candidateCount": len(candidates),
        "validatedCandidateCount": len(rows),
        "rows": rows,
        "allLifecycleCallsUsePacketIdentity": bool(rows) and all(
            row["samePacketIdentityForwardedToEveryLifecycleCall"] for row in rows
        ),
        "clientSuccessorSelectors": sum(
            int(row["clientSuccessorSelectorPresent"]) for row in rows
        ),
        "questStartApplication": quest_start,
        "finding": (
            "The current client receives one selected mission/quest identity and "
            "state/control value per update and forwards that same packet identity into "
            "its lifecycle calls. "
            "The audited update paths contain no second identity or successor field, so "
            "they apply server-selected state rather than choosing a successor branch."
        ),
        "boundary": (
            "This proves the current client update-application paths. It does not recover "
            "server-only successor policy, and prerequisite edges remain topology rather "
            "than proof of exclusive branch selection."
        ),
        "validation": validation,
    }


def finish_protobuf_identity_carrier_census(
    *,
    metadata_registration: int,
    runtime_types_va: int,
    runtime_type_count: int,
    proto_types: dict[str, list[dict[str, str]]],
    cs_sc_type_count: int,
    registry_rows: list[dict[str, Any]],
    registry_by_normalized_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    roots: list[dict[str, Any]] = []
    for type_name in sorted(proto_types):
        if not type_name.startswith(("Proto.CS_", "Proto.SC_")):
            continue
        registry = registry_by_normalized_name.get(
            normalized_field_name(type_name.removeprefix("Proto."))
        )
        if registry is None:
            continue
        roots.append(
            {
                "type": type_name,
                "messageId": registry["id"],
                "enumName": registry["name"],
                "direction": (
                    "client_to_server"
                    if type_name.startswith("Proto.CS_")
                    else "server_to_client"
                ),
            }
        )

    known_proto_types = set(proto_types)

    def identity_evidence(root_type: str) -> dict[str, list[dict[str, str]]]:
        evidence: dict[str, list[dict[str, str]]] = {
            "mission_or_quest": [],
            "level_script": [],
            "scene_host": [],
            "story": [],
        }
        visited: set[str] = set()

        def visit(type_name: str, path: list[str]) -> None:
            if type_name in visited:
                return
            visited.add(type_name)
            for field in proto_types.get(type_name, []):
                field_path = [*path, field["name"]]
                for identity_class in protobuf_identity_field_classes(field["name"]):
                    evidence[identity_class].append(
                        {
                            "path": ".".join(field_path),
                            "ownerType": type_name,
                            "field": field["name"],
                            "runtimeType": field["runtimeType"],
                        }
                    )
                for dependency in protobuf_runtime_dependencies(
                    field["runtimeType"],
                    known_proto_types,
                ):
                    visit(dependency, field_path)

        visit(root_type, [root_type])
        return evidence

    mission_roots = 0
    script_roots = 0
    exact_candidates: list[dict[str, Any]] = []
    weak_scene_candidates: list[dict[str, Any]] = []
    field_bearing_roots = 0
    for root in roots:
        if proto_types[root["type"]]:
            field_bearing_roots += 1
        evidence = identity_evidence(root["type"])
        has_mission = bool(evidence["mission_or_quest"])
        has_script = bool(evidence["level_script"])
        has_story = bool(evidence["story"])
        has_scene = bool(evidence["scene_host"])
        mission_roots += int(has_mission)
        script_roots += int(has_script)
        candidate = {
            **root,
            "evidence": evidence,
        }
        if has_mission and (has_script or has_story):
            exact_candidates.append(candidate)
        elif has_mission and has_scene:
            weak_scene_candidates.append(candidate)

    weak_findings = {
        "Proto.CS_MISSION_CLIENT_TRIGGER_DONE": {
            "classification": "inactive_current_fallback_sender",
            "finding": (
                "The schema co-carries missionId and sceneName, but the current fallback "
                "has no gameplay constructor/sender and the installed IFix does not add "
                "one. It creates no active ownership or order edge."
            ),
        },
        "Proto.SC_MISSION_STATE_UPDATE": {
            "classification": "role_snapshot_position_correction",
            "finding": (
                "roleBaseInfo.sceneName travels with leader position/rotation and is "
                "consumed by MissionSystem.CharacterPositionCorrection. It selects the "
                "map for operational character-position reconciliation, not an authored "
                "mission host, LevelScript, or Story file."
            ),
        },
        "Proto.SC_QUEST_STATE_UPDATE": {
            "classification": "role_snapshot_position_correction",
            "finding": (
                "roleBaseInfo.sceneName travels with leader position/rotation and is "
                "consumed by MissionSystem.CharacterPositionCorrection. It selects the "
                "map for operational character-position reconciliation, not an authored "
                "quest host, LevelScript, or Story file."
            ),
        },
    }
    for candidate in weak_scene_candidates:
        candidate.update(
            weak_findings.get(
                candidate["type"],
                {
                    "classification": "unclassified_scene_co_carrier",
                    "finding": (
                        "This message needs native consumer review before its scene field "
                        "can be treated as host evidence."
                    ),
                },
            )
        )

    expected_weak_types = set(weak_findings)
    actual_weak_types = {row["type"] for row in weak_scene_candidates}
    return {
        "metadataRegistration": f"0x{metadata_registration:x}",
        "runtimeTypesTable": f"0x{runtime_types_va:x}",
        "runtimeTypeCount": runtime_type_count,
        "protoTypeDefinitions": len(proto_types),
        "csScTypeDefinitions": cs_sc_type_count,
        "registryEntries": len(registry_rows),
        "registryMessageTypes": len(roots),
        "fieldBearingRegistryMessageTypes": field_bearing_roots,
        "missionOrQuestMessageTypes": mission_roots,
        "levelScriptMessageTypes": script_roots,
        "exactMissionScriptOrStoryCandidates": exact_candidates,
        "exactMissionScriptOrStoryCandidateCount": len(exact_candidates),
        "weakMissionSceneCandidates": weak_scene_candidates,
        "weakMissionSceneCandidateCount": len(weak_scene_candidates),
        "expectedWeakCandidateTypes": sorted(expected_weak_types),
        "weakCandidateSetMatchesExpected": actual_weak_types == expected_weak_types,
        "roleSnapshotConsumer": {
            "missionHandler": {
                "symbol": "Beyond.Gameplay.MissionSystem.Handle_MissionStateUpdate",
                "token": "0x060052a2",
                "va": "0x1873be300",
                "fallbackPatchId": "0x5ec5",
            },
            "questHandler": {
                "symbol": "Beyond.Gameplay.MissionSystem.Handle_QuestStateUpdate",
                "token": "0x0600529e",
                "va": "0x1873bf0a0",
                "fallbackPatchId": "0x5ebe",
            },
            "consumer": {
                "symbol": "Beyond.Gameplay.MissionSystem.CharacterPositionCorrection",
                "token": "0x0600527b",
                "va": "0x1873b84c4",
                "fallbackPatchId": "0x5ea7",
                "fields": [
                    "roleBaseInfo.leaderPosition",
                    "roleBaseInfo.leaderRotation",
                    "roleBaseInfo.sceneName",
                ],
                "operation": (
                    "Resolve sceneName through GameUtil.GetLevelConfigMapIdByLevelId, "
                    "compare it with the current player/controller level and map, then "
                    "teleport the squad only when the synchronization guards require it."
                ),
            },
            "installedIfix": {
                "sha256": (
                    "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21"
                ),
                "signatureTargetCount": 30,
                "relevantPatchIds": ["0x5ec5", "0x5ebe", "0x5ea7"],
                "matchedMethods": 0,
            },
        },
        "storyBindingsAdded": 0,
        "finding": (
            f"Recursive runtime-type traversal across {len(roots):,} enum-backed "
            f"message classes found {mission_roots} mission/quest message types and "
            f"{script_roots} LevelScript message types, with "
            f"{len(exact_candidates)} message carrying mission/quest identity beside a "
            "LevelScript or Story identity. The only weaker mission/scene candidates are "
            "one inactive sender and two operational role-position snapshots."
        ),
        "coverage": (
            "Covers direct and recursively nested Proto fields whose runtime generic "
            "types are recovered from the current MetadataRegistration type table. "
            "Opaque bytes, dynamic parameter values, server-only schemas, native memory "
            "construction, future IFix, and future builds remain outside the bound."
        ),
    }


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
    cs = enum_members(metadata, defaults, "Proto.CSMessageID")
    sc = enum_members(metadata, defaults, "Proto.SCMessageID")
    event_bus_census = event_bus_specialization_census(
        metadata, gameassembly_path, mapper_path
    )
    identity_carrier_census = protobuf_identity_carrier_census(
        metadata,
        gameassembly_path,
        [*cs, *sc],
        mapper_path,
    )
    state_application_census = state_update_application_census(
        metadata,
        defaults,
        helper,
        sc,
        gameassembly_path,
        mapper_path,
    )
    native_hooks_by_message_id: dict[int, list[str]] = {}
    for hook_name, hook in native_task_paths["hooks"].items():
        message_id = hook.get("messageId")
        if isinstance(message_id, int):
            native_hooks_by_message_id.setdefault(message_id, []).append(hook_name)
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
        "_schema": "endfieldProtocolRegistryAudit.v6",
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
            "protobufMissionScriptOrStoryCoCarriers": identity_carrier_census[
                "exactMissionScriptOrStoryCandidateCount"
            ],
            "protobufWeakMissionSceneCoCarriers": identity_carrier_census[
                "weakMissionSceneCandidateCount"
            ],
            "stateUpdateApplicationCandidates": state_application_census[
                "candidateCount"
            ],
            "stateUpdateApplicationCandidatesValidated": state_application_census[
                "validatedCandidateCount"
            ],
            "stateUpdateClientSuccessorSelectors": state_application_census[
                "clientSuccessorSelectors"
            ],
            "questStartPredecessorReads": state_application_census[
                "questStartApplication"
            ].get("fieldReadCounts", {}).get("prevQuestIdList", 0),
            "questStartFlowIndexReads": state_application_census[
                "questStartApplication"
            ].get("fieldReadCounts", {}).get("flowIndex", 0),
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
            "questSuccessorPolicy": state_application_census["boundary"],
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
                "non-empty ctxToken in EventParams, and raises eventName. The sole current "
                "direct AOT key-slot reader is CallServer.Execute, which reads the value "
                "as netToken and returns it on CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER. This "
                "closes the token as round-trip/correlation context rather than a hidden "
                "mission/quest carrier, so it creates no Mission Pipeline ownership edge."
            ),
            "protobufIdentityCarriers": (
                "A complete recursive runtime-type census of enum-backed protobuf "
                "messages finds no message that co-carries mission/quest identity with a "
                "LevelScript or Story identity. The three weaker mission/scene carriers "
                "are the inactive message 317 sender and roleBaseInfo.sceneName in mission/"
                "quest state updates; the active pair feeds character-position correction, "
                "not authored scene ownership."
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
        "protobufIdentityCarrierCensus": identity_carrier_census,
        "stateUpdateApplicationCensus": state_application_census,
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
        (
            "- Recursive protobuf mission/quest + LevelScript/Story co-carriers: "
            f"**{summary['protobufMissionScriptOrStoryCoCarriers']}**"
        ),
        (
            "- Weaker protobuf mission/quest + scene carriers requiring review: "
            f"**{summary['protobufWeakMissionSceneCoCarriers']}**"
        ),
        (
            "- Typed state-update application paths: "
            f"**{summary['stateUpdateApplicationCandidatesValidated']}/"
            f"{summary['stateUpdateApplicationCandidates']}** validated; "
            f"**{summary['stateUpdateClientSuccessorSelectors']}** client successor selectors"
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
                "the EventParams/ParamBlackboard before raising the event. The exact key "
                "slot has four direct RIP references in two methods: this writer and "
                "`CallServer.Execute`. CallServer reads the value as `netToken`, passes it "
                "through `GameAction.TriggerServerEvent` and "
                "`GameplayNetwork.TriggerLevelScriptServerEvent`, and writes it to "
                "`CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.CtxToken`. This proves a server-event "
                "round trip, not mission/quest identity, and therefore creates no ownership "
                "or order edge."
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## Recursive protobuf identity-carrier census",
            "",
        ]
    )
    carrier_census = report["protobufIdentityCarrierCensus"]
    lines.extend(
        [
            (
                f"The current enum registry resolves to "
                f"**{carrier_census['registryMessageTypes']:,}** generated CS/SC message "
                f"classes. Recursive traversal of exact runtime field types across "
                f"**{carrier_census['protoTypeDefinitions']:,}** `Proto.*` definitions "
                f"found **{carrier_census['missionOrQuestMessageTypes']}** mission/quest "
                f"message types and **{carrier_census['levelScriptMessageTypes']}** "
                "LevelScript message types."
            ),
            "",
            (
                f"Exactly **{carrier_census['exactMissionScriptOrStoryCandidateCount']}** "
                "message carries mission/quest identity beside a LevelScript or Story "
                "identity. The weaker mission/scene pass produced the following "
                f"**{carrier_census['weakMissionSceneCandidateCount']}** candidates:"
            ),
            "",
            "| ID | Direction | Message | Classification | Finding |",
            "|---:|---|---|---|---|",
        ]
    )
    for candidate in carrier_census["weakMissionSceneCandidates"]:
        lines.append(
            "| {message_id} | {direction} | `{type_name}` | `{classification}` | "
            "{finding} |".format(
                message_id=candidate["messageId"],
                direction=md_escape(candidate["direction"]),
                type_name=md_escape(candidate["type"]),
                classification=md_escape(candidate["classification"]),
                finding=md_escape(candidate["finding"]),
            )
        )
    role_consumer = carrier_census["roleSnapshotConsumer"]
    lines.extend(
        [
            "",
            (
                "For messages 111 and 112, the native handlers pass "
                "`roleBaseInfo.leaderPosition`, `leaderRotation`, and `sceneName` to "
                f"`MissionSystem.CharacterPositionCorrection` at "
                f"`{role_consumer['consumer']['va']}`. The scene value selects the map "
                "for guarded player-position reconciliation; it is not retained as an "
                "authored mission/quest scene owner. The current installed 30-target "
                "Gameplay IFix matches none of the two handlers or that consumer."
            ),
            "",
            carrier_census["coverage"],
            "",
            "## Server-selected state application",
            "",
        ]
    )
    state_census = report["stateUpdateApplicationCensus"]
    lines.extend(
        [
            state_census["finding"],
            "",
            "| Message | Identity/state layout | Native handler | Lifecycle calls |",
            "|---|---|---|---|",
        ]
    )
    for row in state_census["rows"]:
        layout = ", ".join(
            f"{name}@{offset}"
            for name, offset in row["fieldOffsets"].items()
            if name in {row["identityField"], row["stateField"]}
        )
        lifecycle = ", ".join(
            f"{call['method']}({call['identityArgumentOrigin']})"
            for call in row["lifecycleCalls"]
        )
        lines.append(
            "| `{message}` ({message_id}) | {layout} | `{handler}` `{token}` @ `{va}` | "
            "{lifecycle} |".format(
                message=md_escape(row["type"].removeprefix("Proto.")),
                message_id=row["messageId"],
                layout=md_escape(layout),
                handler=md_escape(row["handler"]["symbol"]),
                token=md_escape(row["handler"]["token"]),
                va=md_escape(row["handler"]["va"]),
                lifecycle=md_escape(lifecycle),
            )
        )
    quest_start = state_census.get("questStartApplication") or {}
    quest_fields = quest_start.get("questInfoFieldOffsets") or {}
    quest_reads = quest_start.get("fieldReadCounts") or {}
    lines.extend(
        [
            "",
            state_census["boundary"],
            "",
            "### Quest-start fork authority",
            "",
            quest_start.get("finding") or "[quest-start audit unavailable]",
            "",
            (
                "`objectiveList@{objective}` reads: **{objective_reads}**; "
                "`prevQuestIdList@{previous}` reads: **{previous_reads}**; "
                "`flowIndex@{flow}` reads: **{flow_reads}**."
            ).format(
                objective=quest_fields.get("objectiveList", "?"),
                objective_reads=quest_reads.get("objectiveList", 0),
                previous=quest_fields.get("prevQuestIdList", "?"),
                previous_reads=quest_reads.get("prevQuestIdList", 0),
                flow=quest_fields.get("flowIndex", "?"),
                flow_reads=quest_reads.get("flowIndex", 0),
            ),
            "",
            quest_start.get("boundary") or "",
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
    parser.add_argument(
        "--ensure-current",
        action="store_true",
        help=(
            "Reuse an existing validated v6 report when its original "
            "GameAssembly and metadata hashes still match; otherwise rebuild it."
        ),
    )
    return parser.parse_args()


def current_report_status(
    report_path: Path,
    metadata_path: Path,
    gameassembly_path: Path,
) -> tuple[bool, str]:
    """Fail closed unless a report describes these exact original inputs."""
    if not report_path.is_file():
        return False, "report missing"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"report unreadable: {exc}"
    if report.get("_schema") != "endfieldProtocolRegistryAudit.v6":
        return False, f"schema is {report.get('_schema')!r}"
    validation = (
        (report.get("stateUpdateApplicationCensus") or {}).get("validation") or {}
    )
    if validation.get("status") != "validated":
        return False, f"validation is {validation.get('status')!r}"
    quest_start_validation = (
        ((report.get("stateUpdateApplicationCensus") or {}).get(
            "questStartApplication"
        ) or {}).get("validation") or {}
    )
    if quest_start_validation.get("status") != "validated":
        return False, (
            "quest-start validation is "
            f"{quest_start_validation.get('status')!r}"
        )
    source = report.get("source") or {}
    checks = (
        (metadata_path, "metadataSha256"),
        (gameassembly_path, "gameAssemblySha256"),
    )
    for source_path, hash_key in checks:
        if not source_path.is_file():
            return False, f"source missing: {source_path}"
        expected = str(source.get(hash_key) or "").lower()
        actual = file_sha256(source_path)
        if actual != expected:
            return False, f"{hash_key} differs: expected={expected!r} actual={actual!r}"
    return True, "validated report hashes match original inputs"


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
    if args.ensure_current:
        is_current, reason = current_report_status(
            args.json_output,
            args.metadata,
            args.gameassembly,
        )
        if is_current:
            if not args.markdown_output.is_file():
                existing_report = json.loads(
                    args.json_output.read_text(encoding="utf-8")
                )
                write_text_if_changed(
                    args.markdown_output,
                    render_markdown(existing_report),
                )
            print(f"protocol registry audit current: {reason}")
            return 0
        print(f"protocol registry audit refresh required: {reason}")
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
    validation = report["stateUpdateApplicationCensus"]["validation"]
    if validation["status"] != "validated":
        first = validation["failures"][0]
        print(
            "state-update validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"message={first.get('message')} expected={first['expected']!r} "
            f"actual={first['actual']!r} source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    quest_start_validation = report["stateUpdateApplicationCensus"][
        "questStartApplication"
    ]["validation"]
    if quest_start_validation["status"] != "validated":
        first = quest_start_validation["failures"][0]
        print(
            "quest-start validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"message={first.get('message')} expected={first['expected']!r} "
            f"actual={first['actual']!r} source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    print(
        f"wrote {args.json_output} and {args.markdown_output}: "
        f"{report['summary']['totalMessages']} messages, "
        f"{report['summary']['selectedSchemas']} selected schemas, "
        f"{report['summary']['stateUpdateApplicationCandidatesValidated']}/"
        f"{report['summary']['stateUpdateApplicationCandidates']} state-update paths validated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
