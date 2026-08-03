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
from bisect import bisect_right
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
        "type": "Proto.CS_SCENE_SET_LEVEL_SCRIPT_ACTIVE",
        "direction": "client_to_server",
        "enumName": "CsSceneSetLevelScriptActive",
        "expectedId": 94,
        "classification": "native_sender_method_proven",
    },
    {
        "type": "Proto.CS_SCENE_SET_LEVEL_SCRIPT_START",
        "direction": "client_to_server",
        "enumName": "CsSceneSetLevelScriptStart",
        "expectedId": 101,
        "classification": "native_sender_method_proven",
    },
    {
        "type": "Proto.SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY",
        "direction": "server_to_client",
        "enumName": "ScSceneLevelScriptStateNotify",
        "expectedId": 37,
        "classification": "native_handler_proven",
    },
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
    "CsSceneSetLevelScriptActive": 94,
    "CsUpdateQuestObjective": 314,
    "CsAcceptMission": 315,
    "CsFinishDialog": 341,
    "CsGameMechanicsReqActive": 381,
    "ScQuestStateUpdate": 111,
    "ScMissionStateUpdate": 112,
    "ScQuestObjectivesUpdate": 116,
    "ScFinishDialog": 131,
    "ScGameMechanicsSyncEnterGameInst": 1257,
    "ScSceneLevelScriptStateNotify": 37,
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


def validate_levelscript_start_policy_observation(
    observation: dict[str, Any],
    *,
    source_file: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed on the generic native LevelScript start-policy shape."""
    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "levelscript_start_policy_contract",
            "gate": gate,
            "message": "LevelScriptRuntime SameWithActive start policy",
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    enum_values = observation.get("enumValues") or {}
    for enum_name, required_names in (
        (
            "Beyond.GEnums.LevelScriptState",
            ("Active",),
        ),
        (
            "Beyond.Gameplay.LevelScriptStartType",
            ("ByEnterStartShape", "Manual", "SameWithActive", "Never"),
        ),
        (
            "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState",
            ("PreStart",),
        ),
    ):
        members = enum_values.get(enum_name) or {}
        missing = [name for name in required_names if not isinstance(members.get(name), int)]
        if missing:
            fail(
                "enumMembers",
                {enum_name: list(required_names)},
                {enum_name: {name: members.get(name) for name in required_names}},
            )

    methods = observation.get("methods") or {}
    required_methods = (
        "get_state",
        "get_isDone",
        "get_startType",
        "UpdateWithinStartArea",
        "set_runtimeState",
        "UpdateRuntimeState",
    )
    unresolved_methods = [
        name
        for name in required_methods
        if (methods.get(name) or {}).get("mappingStatus") != "mapped_unique"
    ]
    if unresolved_methods:
        fail("uniqueMappedMethods", [], unresolved_methods)

    active_gate = observation.get("activeStateGate") or {}
    expected_active = (enum_values.get("Beyond.GEnums.LevelScriptState") or {}).get(
        "Active"
    )
    if not (
        active_gate.get("comparedValue") == expected_active
        and active_gate.get("branchTargetIsDoneCheck") is True
    ):
        fail(
            "activeStateGate",
            {
                "comparedValue": expected_active,
                "branchTargetIsDoneCheck": True,
            },
            active_gate,
        )

    done_gate = observation.get("doneGate") or {}
    if not (
        done_gate.get("doneResultTested") is True
        and done_gate.get("notDoneFallsThroughToStartPolicy") is True
    ):
        fail(
            "notDoneStartPolicyGate",
            {
                "doneResultTested": True,
                "notDoneFallsThroughToStartPolicy": True,
            },
            done_gate,
        )

    start_type_values = enum_values.get(
        "Beyond.Gameplay.LevelScriptStartType"
    ) or {}
    start_gates = observation.get("startTypeGates") or {}
    expected_start_gates = {
        "Never": {
            "comparedValue": start_type_values.get("Never"),
            "branchesAwayFromPreStart": True,
        },
        "ByEnterStartShape": {
            "comparedValue": start_type_values.get("ByEnterStartShape"),
            "branchTargetIsStartAreaCheck": True,
        },
        "SameWithActive": {
            "comparedValue": start_type_values.get("SameWithActive"),
            "branchTargetIsCommonPreStart": True,
        },
    }
    for name, expected in expected_start_gates.items():
        actual = start_gates.get(name) or {}
        if any(actual.get(key) != value for key, value in expected.items()):
            fail(f"{name}Gate", expected, actual)

    start_area_gate = observation.get("startAreaGate") or {}
    if not (
        start_area_gate.get("resultTested") is True
        and start_area_gate.get("trueFallsThroughToCommonPreStart") is True
    ):
        fail(
            "startAreaResultGate",
            {
                "resultTested": True,
                "trueFallsThroughToCommonPreStart": True,
            },
            start_area_gate,
        )

    transition = observation.get("preStartTransition") or {}
    expected_pre_start = (
        enum_values.get(
            "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState"
        )
        or {}
    ).get("PreStart")
    if not (
        transition.get("runtimeStateValue") == expected_pre_start
        and transition.get("setterReceivesValue") is True
    ):
        fail(
            "commonPreStartTransition",
            {
                "runtimeStateValue": expected_pre_start,
                "setterReceivesValue": True,
            },
            transition,
        )

    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def levelscript_start_policy_contract(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    helper: Any,
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Discover SameWithActive semantics from names, enums, and native flow."""
    mapper = load_native_mapper(mapper_path)
    pe = mapper.PeImage(gameassembly_path)
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    sorted_pointers = sorted({
        pointer
        for pointers in pointers_by_image.values()
        for pointer in pointers
        if pointer
    })
    pointers_by_method_index: dict[int, set[int]] = {}
    for pointer, aliases in method_by_pointer.items():
        for alias in aliases:
            method_index = alias.get("methodIndex")
            if isinstance(method_index, int):
                pointers_by_method_index.setdefault(method_index, set()).add(pointer)

    enum_type_names = (
        "Beyond.GEnums.LevelScriptState",
        "Beyond.Gameplay.LevelScriptStartType",
        "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState",
    )
    enum_rows = {
        type_name: enum_members(metadata, defaults, type_name)
        for type_name in enum_type_names
    }
    enum_values = {
        type_name: {row["name"]: row["id"] for row in rows}
        for type_name, rows in enum_rows.items()
    }

    runtime_type_name = "Beyond.Gameplay.Core.LevelScriptRuntime"
    runtime_types = [
        type_def
        for type_def in metadata.types
        if metadata.type_full_name(type_def) == runtime_type_name
    ]
    method_specs = {
        "get_state": ("get_state", (), "Beyond.GEnums.LevelScriptState"),
        "get_isDone": ("get_isDone", (), "System.Boolean"),
        "get_startType": (
            "get_startType",
            (),
            "Beyond.Gameplay.LevelScriptStartType",
        ),
        "UpdateWithinStartArea": (
            "UpdateWithinStartArea",
            (),
            "System.Boolean",
        ),
        "set_runtimeState": (
            "set_runtimeState",
            ("Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState",),
            "System.Void",
        ),
        "UpdateRuntimeState": (
            "UpdateRuntimeState",
            ("Beyond.Gameplay.Core.ScriptEndReason",),
            "System.Void",
        ),
    }
    method_rows: dict[str, dict[str, Any]] = {}
    if len(runtime_types) == 1:
        runtime_type = runtime_types[0]
        for key, (name, parameter_types, return_type) in method_specs.items():
            candidates: list[dict[str, Any]] = []
            for method_def in metadata.methods_for(runtime_type):
                info = helper.method_row(metadata, method_def)
                actual_parameter_types = tuple(
                    row.get("typeName")
                    for row in info.get("parameterDetails") or []
                )
                if (
                    info.get("name") == name
                    and actual_parameter_types == parameter_types
                    and info.get("returnTypeName") == return_type
                ):
                    method_index = method_def.index
                    pointers = sorted(
                        pointers_by_method_index.get(method_index) or []
                    )
                    candidates.append({
                        "methodIndex": method_index,
                        "token": info.get("token"),
                        "parameterTypes": list(actual_parameter_types),
                        "returnTypeName": info.get("returnTypeName"),
                        "pointers": pointers,
                    })
            if len(candidates) == 1 and len(candidates[0]["pointers"]) == 1:
                candidate = candidates[0]
                pointer = candidate["pointers"][0]
                method_rows[key] = {
                    **candidate,
                    "pointers": [f"0x{value:x}" for value in candidate["pointers"]],
                    "methodPointerVa": f"0x{pointer:x}",
                    "mappingStatus": "mapped_unique",
                }
            else:
                method_rows[key] = {
                    "mappingStatus": "unresolved",
                    "candidateCount": len(candidates),
                    "candidates": candidates,
                }
    else:
        method_rows = {
            key: {
                "mappingStatus": "unresolved",
                "candidateCount": 0,
                "runtimeTypeCount": len(runtime_types),
            }
            for key in method_specs
        }

    observation: dict[str, Any] = {
        "enumValues": enum_values,
        "methods": method_rows,
        "activeStateGate": {},
        "doneGate": {},
        "startTypeGates": {},
        "startAreaGate": {},
        "preStartTransition": {},
    }
    runtime_method = method_rows.get("UpdateRuntimeState") or {}
    if runtime_method.get("mappingStatus") == "mapped_unique":
        runtime_pointer = int(runtime_method["methodPointerVa"], 16)
        scan_size, next_pointer = mapper.estimate_scan_size(
            runtime_pointer, sorted_pointers, 65536
        )
        method_index = int(runtime_method["methodIndex"])
        mapper_row = full_method_mapper_row(metadata, helper, method_index)
        body_bytes = pe.bytes_at_va(runtime_pointer, scan_size)
        body = mapper.build_method_body_summary(
            mapper_row,
            body_bytes,
            runtime_pointer,
            method_by_pointer,
            pe=pe,
            max_instructions=30000,
        )
        instructions = mapper.decode_x64_subset(
            body_bytes, runtime_pointer, stop_offset=len(body_bytes)
        )
        calls = sorted(body.get("calls") or [], key=lambda row: row["offset"])

        def calls_to(method_key: str) -> list[dict[str, Any]]:
            expected_index = (method_rows.get(method_key) or {}).get("methodIndex")
            return [
                call
                for call in calls
                if any(
                    target.get("methodIndex") == expected_index
                    for target in call.get("resolved") or []
                )
            ]

        def instructions_between(start: int, end: int) -> list[dict[str, Any]]:
            return [
                row
                for row in instructions
                if start < int(row.get("offset") or 0) < end
            ]

        def compared_value(rows: list[dict[str, Any]]) -> int | None:
            for row in rows:
                match = re.fullmatch(
                    r"cmp eax, (?:0x([0-9a-f]+)|(-?\d+))",
                    str(row.get("text") or ""),
                )
                if match:
                    return int(match.group(1), 16) if match.group(1) else int(match.group(2))
                if str(row.get("text") or "") == "test eax, eax":
                    return 0
            return None

        def branch_target(rows: list[dict[str, Any]]) -> int | None:
            for row in rows:
                match = re.fullmatch(
                    r"(?:je|jne|jcc) 0x([0-9a-f]+)",
                    str(row.get("text") or ""),
                )
                if match:
                    return int(match.group(1), 16)
            return None

        state_calls = calls_to("get_state")
        done_calls = calls_to("get_isDone")
        start_type_calls = calls_to("get_startType")
        start_area_calls = calls_to("UpdateWithinStartArea")
        state_setter_calls = calls_to("set_runtimeState")
        first_done = done_calls[0] if done_calls else None
        first_start_area = start_area_calls[0] if start_area_calls else None
        start_policy_calls = (
            [
                call
                for call in start_type_calls
                if int(first_done["offset"]) < int(call["offset"])
                < int(first_start_area["offset"])
            ]
            if first_done and first_start_area
            else []
        )
        first_start_type = start_policy_calls[0] if start_policy_calls else None
        if first_done and first_start_type:
            active_gate_candidates: list[dict[str, Any]] = []
            for state_call in state_calls:
                if int(state_call["offset"]) >= int(first_done["offset"]):
                    continue
                rows = instructions_between(
                    int(state_call["offset"]), int(first_done["offset"])
                )
                if compared_value(rows) == enum_values[
                    "Beyond.GEnums.LevelScriptState"
                ].get("Active"):
                    candidate = {
                        "callOffset": state_call["offset"],
                        "comparedValue": compared_value(rows),
                        "branchTargetVa": (
                            f"0x{branch_target(rows):x}"
                            if branch_target(rows) is not None
                            else None
                        ),
                        "branchTargetIsDoneCheck": (
                            branch_target(rows)
                            == runtime_pointer + int(first_done["offset"])
                        ),
                    }
                    active_gate_candidates.append(candidate)
                    if candidate["branchTargetIsDoneCheck"]:
                        observation["activeStateGate"] = candidate
                        break
            if not observation["activeStateGate"] and active_gate_candidates:
                observation["activeStateGate"] = active_gate_candidates[0]
            observation["activeStateGateCandidates"] = active_gate_candidates
            done_rows = instructions_between(
                int(first_done["offset"]), int(first_start_type["offset"])
            )
            observation["doneGate"] = {
                "callOffset": first_done["offset"],
                "doneResultTested": any(
                    str(row.get("text") or "") == "test al, al"
                    for row in done_rows
                ),
                "notDoneFallsThroughToStartPolicy": any(
                    str(row.get("text") or "").startswith(("je ", "jne ", "jcc "))
                    for row in done_rows
                ),
            }

        common_pre_start_va: int | None = None
        if len(start_policy_calls) == 3 and start_area_calls:
            boundary_offsets = [
                int(start_policy_calls[1]["offset"]),
                int(start_policy_calls[2]["offset"]),
                int(start_area_calls[0]["offset"]),
            ]
            gate_names = ("Never", "ByEnterStartShape", "SameWithActive")
            for index, (name, call) in enumerate(zip(gate_names, start_policy_calls)):
                rows = instructions_between(
                    int(call["offset"]), boundary_offsets[index]
                )
                target = branch_target(rows)
                gate = {
                    "callOffset": call["offset"],
                    "comparedValue": compared_value(rows),
                    "branchTargetVa": f"0x{target:x}" if target is not None else None,
                }
                if name == "Never":
                    gate["branchesAwayFromPreStart"] = target is not None
                elif name == "ByEnterStartShape":
                    gate["branchTargetIsStartAreaCheck"] = (
                        target
                        == runtime_pointer + int(start_area_calls[0]["offset"])
                    )
                else:
                    common_pre_start_va = target
                    gate["branchTargetIsCommonPreStart"] = target is not None
                observation["startTypeGates"][name] = gate

        if start_area_calls and common_pre_start_va is not None:
            start_area_offset = int(start_area_calls[0]["offset"])
            common_offset = common_pre_start_va - runtime_pointer
            area_rows = instructions_between(start_area_offset, common_offset)
            observation["startAreaGate"] = {
                "callOffset": start_area_offset,
                "resultTested": any(
                    str(row.get("text") or "") == "test al, al"
                    for row in area_rows
                ),
                "trueFallsThroughToCommonPreStart": any(
                    str(row.get("text") or "").startswith(("je ", "jne ", "jcc "))
                    for row in area_rows
                ),
            }
            setter = next(
                (
                    call
                    for call in state_setter_calls
                    if int(call["offset"]) > common_offset
                ),
                None,
            )
            if setter:
                transition_rows = [
                    row
                    for row in instructions
                    if common_offset <= int(row.get("offset") or 0) < int(setter["offset"])
                ]
                pre_start_value = enum_values[
                    "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState"
                ].get("PreStart")
                expected_move = f"mov edx, 0x{pre_start_value:x}"
                observation["preStartTransition"] = {
                    "commonTargetVa": f"0x{common_pre_start_va:x}",
                    "setterCallOffset": setter["offset"],
                    "runtimeStateValue": pre_start_value,
                    "setterReceivesValue": any(
                        str(row.get("text") or "") == expected_move
                        for row in transition_rows
                    ),
                    "instructionWindow": [
                        {
                            "offset": row.get("offset"),
                            "va": row.get("va"),
                            "text": row.get("text"),
                            "bytes": row.get("bytes"),
                        }
                        for row in transition_rows
                    ],
                }
        observation["methodBody"] = {
            "methodPointerVa": f"0x{runtime_pointer:x}",
            "methodPointerRva": f"0x{runtime_pointer - pe.image_base:x}",
            "scanBytes": scan_size,
            "nextMethodPointerVa": f"0x{next_pointer:x}" if next_pointer else None,
            "instructionCount": body.get("instructionCount"),
            "unknownInstructionCount": body.get("unknownInstructionCount"),
            "startTypeCallCount": len(start_type_calls),
            "startPolicyCallCount": len(start_policy_calls),
        }

    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }
    validation = validate_levelscript_start_policy_observation(
        observation,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
    )
    return {
        "schema": "levelScriptStartPolicy.v1",
        "classification": "same_with_active_enters_prestart_when_active",
        "discoveryPattern": {
            "runtimeType": runtime_type_name,
            "methodSelection": "exact metadata name, signature, and return type",
            "enumSelection": "exact metadata enum types and constant values",
            "nativeFlow": (
                "decoded current-binary direct calls, comparisons, conditional "
                "targets, and common runtime-state setter"
            ),
            "objectIdentityInputs": [],
        },
        **observation,
        "finding": (
            "When a LevelScript's public state is Active and it is not done, "
            "startType SameWithActive branches directly to the same internal "
            "PreStart transition used after a successful start-area check."
        ),
        "boundary": (
            "This proves the generic client start policy for every serialized "
            "SameWithActive LevelScript in this exact binary. It does not identify "
            "which mission or server transition made the script Active, nor does it "
            "order multiple Story actions inside or across scripts."
        ),
        "validation": validation,
    }


def validate_levelscript_manual_self_control_observation(
    observation: dict[str, Any],
    *,
    source_file: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed on the generic current-context ManualStart contract."""
    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "levelscript_manual_self_control_contract",
            "gate": gate,
            "message": "current-context ManualStartLevelScript self target",
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    enum_values = observation.get("paramSourceValues") or {}
    expected_sources = {
        "CURRENT_LEVEL_ID": 1000,
        "CURRENT_SCRIPT_ID": 1002,
    }
    actual_sources = {
        name: enum_values.get(name) for name in expected_sources
    }
    if actual_sources != expected_sources:
        fail("paramSourceEnum", expected_sources, actual_sources)

    expected_fields = {
        "levelId": "Beyond.Gameplay.Actions.Param`1<string>",
        "scriptId": (
            "Beyond.Gameplay.Actions.Param`1<"
            "Beyond.Gameplay.Core.LevelScriptPtr>"
        ),
    }
    actual_fields = {
        name: (observation.get("actionFields") or {}).get(name, {}).get(
            "runtimeType"
        )
        for name in expected_fields
    }
    if actual_fields != expected_fields:
        fail("manualStartFieldTypes", expected_fields, actual_fields)

    methods = observation.get("methods") or {}
    required_methods = (
        "Execute",
        "TryGetLevelScript",
        "ManualStart",
        "set_runtimeState",
        "UpdateRuntimeState",
    )
    unresolved_methods = {
        name: (methods.get(name) or {}).get("mappingStatus")
        for name in required_methods
        if (methods.get(name) or {}).get("mappingStatus") != "mapped_unique"
    }
    if unresolved_methods:
        fail("methodMapping", "all mapped_unique", unresolved_methods)

    execute = observation.get("executeFlow") or {}
    expected_execute = {
        "tryGetLevelScriptCallCount": 1,
        "manualStartCallCount": 1,
        "tryGetBeforeManualStart": True,
    }
    actual_execute = {
        name: execute.get(name) for name in expected_execute
    }
    if actual_execute != expected_execute:
        fail("executeFlow", expected_execute, actual_execute)

    manual_start = observation.get("manualStartFlow") or {}
    expected_transition = {
        "runtimeStateValue": (
            (observation.get("runtimeStateValues") or {}).get("PreStart")
        ),
        "setterReceivesValue": True,
        "updateRuntimeStateCallCount": 1,
        "setterBeforeUpdate": True,
    }
    actual_transition = {
        name: manual_start.get(name) for name in expected_transition
    }
    if actual_transition != expected_transition:
        fail("manualStartTransition", expected_transition, actual_transition)

    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def levelscript_manual_self_control_contract(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    helper: Any,
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Discover current-level/current-script ManualStart semantics generically."""
    mapper = load_native_mapper(mapper_path)
    pe = mapper.PeImage(gameassembly_path)
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    sorted_pointers = sorted({
        pointer
        for pointers in pointers_by_image.values()
        for pointer in pointers
        if pointer
    })
    pointers_by_method_index: dict[int, set[int]] = {}
    for pointer, aliases in method_by_pointer.items():
        for alias in aliases:
            method_index = alias.get("methodIndex")
            if isinstance(method_index, int):
                pointers_by_method_index.setdefault(method_index, set()).add(
                    pointer
                )

    metadata_registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if metadata_registration is None:
        raise RuntimeError(
            "ManualStart audit could not derive MetadataRegistration"
        )
    metadata_summary = mapper.metadata_registration_summary(
        pe, metadata_registration
    )
    runtime_types_va = int(metadata_summary["types"], 16)

    def resolved_field_type(type_index: int) -> tuple[int, str]:
        type_va = pe.u64_at_va(runtime_types_va + type_index * 8)
        return type_va, runtime_type_name(pe, metadata, type_va)

    def find_type(type_name: str) -> list[Any]:
        return [
            type_def
            for type_def in metadata.types
            if metadata.type_full_name(type_def) == type_name
        ]

    def mapped_method(
        type_name: str,
        method_name: str,
        parameter_count: int,
        return_type: str,
        *,
        parameter_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        types = find_type(type_name)
        if len(types) == 1:
            for method_def in metadata.methods_for(types[0]):
                info = helper.method_row(metadata, method_def)
                actual_parameter_types = tuple(
                    row.get("typeName")
                    for row in info.get("parameterDetails") or []
                )
                if (
                    info.get("name") != method_name
                    or info.get("parameterCount") != parameter_count
                    or info.get("returnTypeName") != return_type
                    or (
                        parameter_types is not None
                        and actual_parameter_types != parameter_types
                    )
                ):
                    continue
                pointers = sorted(
                    pointers_by_method_index.get(method_def.index) or []
                )
                candidates.append({
                    "methodIndex": method_def.index,
                    "token": info.get("token"),
                    "parameterTypes": list(actual_parameter_types),
                    "returnTypeName": info.get("returnTypeName"),
                    "pointers": pointers,
                })
        if len(candidates) == 1 and len(candidates[0]["pointers"]) == 1:
            candidate = candidates[0]
            pointer = candidate["pointers"][0]
            return {
                **candidate,
                "pointers": [f"0x{value:x}" for value in candidate["pointers"]],
                "methodPointerVa": f"0x{pointer:x}",
                "mappingStatus": "mapped_unique",
            }
        return {
            "mappingStatus": "unresolved",
            "candidateCount": len(candidates),
            "declaringTypeCount": len(types),
            "candidates": candidates,
        }

    param_sources = {
        row["name"]: row["id"]
        for row in enum_members(
            metadata, defaults, "Beyond.Gameplay.Actions.ParamSource"
        )
    }
    runtime_state_values = {
        row["name"]: row["id"]
        for row in enum_members(
            metadata,
            defaults,
            "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState",
        )
    }

    action_type_name = "Beyond.Gameplay.Actions.ManualStartLevelScript"
    action_fields: dict[str, dict[str, Any]] = {}
    action_types = find_type(action_type_name)
    if len(action_types) == 1:
        for field in metadata.fields_for(action_types[0]):
            name = metadata.string(field.name_index)
            if name not in {"levelId", "scriptId"}:
                continue
            type_va, type_name = resolved_field_type(field.type_index)
            action_fields[name] = {
                "fieldIndex": field.index,
                "token": f"0x{field.token:08x}",
                "metadataTypeIndex": field.type_index,
                "runtimeTypeVa": f"0x{type_va:x}",
                "runtimeType": type_name,
            }

    methods = {
        "Execute": mapped_method(
            action_type_name,
            "Execute",
            1,
            "System.Void",
            parameter_types=("System.Single",),
        ),
        "TryGetLevelScript": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptManager",
            "TryGetLevelScript",
            3,
            "System.Boolean",
        ),
        "ManualStart": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "ManualStart",
            0,
            "System.Void",
            parameter_types=(),
        ),
        "set_runtimeState": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "set_runtimeState",
            1,
            "System.Void",
            parameter_types=(
                "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState",
            ),
        ),
        "UpdateRuntimeState": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "UpdateRuntimeState",
            1,
            "System.Void",
            parameter_types=("Beyond.Gameplay.Core.ScriptEndReason",),
        ),
    }

    def method_body(method_key: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        method = methods.get(method_key) or {}
        if method.get("mappingStatus") != "mapped_unique":
            return {}, []
        pointer = int(method["methodPointerVa"], 16)
        scan_size, next_pointer = mapper.estimate_scan_size(
            pointer, sorted_pointers, 65536
        )
        mapper_row = full_method_mapper_row(
            metadata, helper, int(method["methodIndex"])
        )
        body_bytes = pe.bytes_at_va(pointer, scan_size)
        body = mapper.build_method_body_summary(
            mapper_row,
            body_bytes,
            pointer,
            method_by_pointer,
            pe=pe,
            max_instructions=30000,
        )
        body["methodPointerVa"] = f"0x{pointer:x}"
        body["methodPointerRva"] = f"0x{pointer - pe.image_base:x}"
        body["scanBytes"] = scan_size
        body["nextMethodPointerVa"] = (
            f"0x{next_pointer:x}" if next_pointer else None
        )
        instructions = mapper.decode_x64_subset(
            body_bytes, pointer, stop_offset=len(body_bytes)
        )
        return body, instructions

    def calls_to(body: dict[str, Any], method_key: str) -> list[dict[str, Any]]:
        expected_index = (methods.get(method_key) or {}).get("methodIndex")
        return [
            call
            for call in sorted(body.get("calls") or [], key=lambda row: row["offset"])
            if any(
                target.get("methodIndex") == expected_index
                for target in call.get("resolved") or []
            )
        ]

    execute_body, _execute_instructions = method_body("Execute")
    try_get_calls = calls_to(execute_body, "TryGetLevelScript")
    manual_start_calls = calls_to(execute_body, "ManualStart")
    execute_flow = {
        "tryGetLevelScriptCallCount": len(try_get_calls),
        "manualStartCallCount": len(manual_start_calls),
        "tryGetBeforeManualStart": (
            len(try_get_calls) == 1
            and len(manual_start_calls) == 1
            and int(try_get_calls[0]["offset"])
            < int(manual_start_calls[0]["offset"])
        ),
        "tryGetLevelScriptCallOffset": (
            try_get_calls[0]["offset"] if len(try_get_calls) == 1 else None
        ),
        "manualStartCallOffset": (
            manual_start_calls[0]["offset"]
            if len(manual_start_calls) == 1
            else None
        ),
        "methodBody": {
            key: execute_body.get(key)
            for key in (
                "methodPointerVa",
                "methodPointerRva",
                "scanBytes",
                "nextMethodPointerVa",
                "instructionCount",
                "unknownInstructionCount",
            )
        },
    }

    start_body, start_instructions = method_body("ManualStart")
    setter_calls = calls_to(start_body, "set_runtimeState")
    update_calls = calls_to(start_body, "UpdateRuntimeState")
    pre_start_value = runtime_state_values.get("PreStart")
    setter_receives_pre_start = False
    setter_window: list[dict[str, Any]] = []
    if len(setter_calls) == 1 and isinstance(pre_start_value, int):
        setter_offset = int(setter_calls[0]["offset"])
        setter_window = [
            row
            for row in start_instructions
            if setter_offset - 24 <= int(row.get("offset") or 0) < setter_offset
        ]
        texts = {str(row.get("text") or "") for row in setter_window}
        setter_receives_pre_start = (
            f"mov edx, 0x{pre_start_value:x}" in texts
            or (
                "xor r8d, r8d" in texts
                and f"lea rdx, [r8+0x{pre_start_value:x}]" in texts
            )
        )
    manual_start_flow = {
        "runtimeStateValue": pre_start_value,
        "setterCallCount": len(setter_calls),
        "setterReceivesValue": setter_receives_pre_start,
        "updateRuntimeStateCallCount": len(update_calls),
        "setterBeforeUpdate": (
            len(setter_calls) == 1
            and len(update_calls) == 1
            and int(setter_calls[0]["offset"]) < int(update_calls[0]["offset"])
        ),
        "setterCallOffset": (
            setter_calls[0]["offset"] if len(setter_calls) == 1 else None
        ),
        "updateRuntimeStateCallOffset": (
            update_calls[0]["offset"] if len(update_calls) == 1 else None
        ),
        "setterInstructionWindow": [
            {
                "offset": row.get("offset"),
                "va": row.get("va"),
                "text": row.get("text"),
                "bytes": row.get("bytes"),
            }
            for row in setter_window
        ],
        "methodBody": {
            key: start_body.get(key)
            for key in (
                "methodPointerVa",
                "methodPointerRva",
                "scanBytes",
                "nextMethodPointerVa",
                "instructionCount",
                "unknownInstructionCount",
            )
        },
    }

    observation = {
        "paramSourceValues": param_sources,
        "runtimeStateValues": runtime_state_values,
        "actionFields": action_fields,
        "methods": methods,
        "executeFlow": execute_flow,
        "manualStartFlow": manual_start_flow,
    }
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }
    validation = validate_levelscript_manual_self_control_observation(
        observation,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
    )
    return {
        "schema": "levelScriptManualSelfControl.v1",
        "classification": "current_context_manual_start_self_target",
        "discoveryPattern": {
            "actionType": action_type_name,
            "fieldSelection": "exact metadata field names and runtime generic types",
            "enumSelection": "exact ParamSource metadata constants",
            "nativeFlow": (
                "decoded current-binary calls from Execute through "
                "TryGetLevelScript and ManualStart into PreStart"
            ),
            "serializedObjectInputs": [],
        },
        "serializedOperandContract": {
            "levelIdParamSource": param_sources.get("CURRENT_LEVEL_ID"),
            "scriptIdParamSource": param_sources.get("CURRENT_SCRIPT_ID"),
            "targetResolution": "hosting_level_and_script",
        },
        **observation,
        "finding": (
            "A ManualStartLevelScript action whose serialized levelId and scriptId "
            "parameters use CURRENT_LEVEL_ID and CURRENT_SCRIPT_ID resolves the "
            "hosting LevelScript, looks it up, and calls ManualStart; ManualStart "
            "enters PreStart before continuing runtime-state evaluation."
        ),
        "boundary": (
            "This proves a self-start carrier only when an original serialized "
            "ManualStart action has both current-context operands and an authored "
            "header link into that action. It does not supply a mission/quest owner, "
            "choose a Story branch, or order separate playback actions."
        ),
        "validation": validation,
    }


def validate_levelscript_activation_control_observation(
    observation: dict[str, Any],
    *,
    source_file: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed on public-state sync and SubGame interaction start flow."""
    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "levelscript_activation_control",
            "gate": gate,
            "message": "current-build LevelScript activation control",
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    expected_ids = {
        "CsSceneSetLevelScriptActive": 94,
        "CsSceneSetLevelScriptStart": 101,
        "ScSceneLevelScriptStateNotify": 37,
    }
    actual_ids = {
        name: (observation.get("messageIds") or {}).get(name)
        for name in expected_ids
    }
    if actual_ids != expected_ids:
        fail("messageIds", expected_ids, actual_ids)

    expected_fields = {
        "activationRequest": [
            ("sceneNumId", 1),
            ("scriptId", 2),
            ("isActive", 3),
            ("leaderPos", 4),
        ],
        "startRequest": [
            ("sceneNumId", 1),
            ("scriptId", 2),
            ("isStart", 3),
            ("leaderPos", 4),
        ],
        "stateNotify": [
            ("sceneNumId", 1),
            ("scriptId", 2),
            ("state", 3),
            ("isComplete", 4),
        ],
    }
    actual_fields = {
        key: [
            (row.get("name"), row.get("tag"))
            for row in ((observation.get("messageSchemas") or {}).get(key) or {}).get(
                "fields", []
            )
        ]
        for key in expected_fields
    }
    if actual_fields != expected_fields:
        fail("messageSchemas", expected_fields, actual_fields)

    expected_offsets = {
        "challengeStartPoint.m_subGameId": 0x68,
        "subGameInstanceData.bindScriptId": 0x50,
        "stateNotify.sceneNumId_": 0x18,
        "stateNotify.scriptId_": 0x20,
        "stateNotify.state_": 0x28,
        "stateNotify.isComplete_": 0x2C,
        "levelScriptRuntime.m_manualStartTriggered": 0xF8,
    }
    actual_offsets = {
        key: (observation.get("fieldOffsets") or {}).get(key)
        for key in expected_offsets
    }
    if actual_offsets != expected_offsets:
        fail("fieldOffsets", expected_offsets, actual_offsets)

    expected_methods = {
        "StateNotifyHandler",
        "ManagerStateShort",
        "ManagerStateFull",
        "ContainerState",
        "UpdateState",
        "set_state",
        "set_runtimeState",
        "UpdateRuntimeState",
        "ChallengeOnInteract",
        "SubGameTableTryGetValue",
        "LevelScriptPtrImplicit",
        "TryGetLevelScript",
        "ManualStart",
        "ManualStartActionExecute",
        "NetworkSetActive",
        "NetworkSetStart",
        "RuntimeSendActive",
        "RuntimeSendStart",
        "BaseSendMsg",
    }
    unresolved = sorted(
        name
        for name in expected_methods
        if ((observation.get("methods") or {}).get(name) or {}).get(
            "mappingStatus"
        )
        != "mapped_unique"
    )
    if unresolved:
        fail("methodMapping", "all mapped_unique", unresolved)

    expected_state_flow = {
        "handlerToManagerShort": 1,
        "managerShortToManagerFull": 1,
        "managerFullToContainer": 1,
        "containerToUpdateState": 1,
        "updateStateToSetter": 1,
        "updateStateToRuntimeEvaluation": 1,
        "setterBeforeRuntimeEvaluation": True,
    }
    actual_state_flow = {
        name: (observation.get("publicStateFlow") or {}).get(name)
        for name in expected_state_flow
    }
    if actual_state_flow != expected_state_flow:
        fail("publicStateFlow", expected_state_flow, actual_state_flow)

    expected_subgame_flow = {
        "subGameLookupCallCount": 1,
        "scriptPtrConversionCallCount": 1,
        "tryGetLevelScriptCallCount": 1,
        "manualStartCallCount": 1,
        "callsInCarrierOrder": True,
        "subGameIdFieldRead": True,
        "bindScriptIdFieldRead": True,
    }
    actual_subgame_flow = {
        name: (observation.get("subGameInteractionFlow") or {}).get(name)
        for name in expected_subgame_flow
    }
    if actual_subgame_flow != expected_subgame_flow:
        fail("subGameInteractionFlow", expected_subgame_flow, actual_subgame_flow)

    expected_callers = [
        {
            "type": "Beyond.Gameplay.Actions.ManualStartLevelScript",
            "method": "Execute",
        },
        {
            "type": "Beyond.Gameplay.InteractiveLogicChallengeStartPoint",
            "method": "_OnInteract",
        },
    ]
    actual_callers = [
        {"type": row.get("type"), "method": row.get("method")}
        for row in observation.get("manualStartDirectCallers") or []
    ]
    if actual_callers != expected_callers:
        fail("manualStartDirectCallers", expected_callers, actual_callers)

    expected_request_flow = {
        "networkActiveToSendMsg": 1,
        "networkStartToSendMsg": 1,
        "runtimeActiveToSendMsg": 1,
        "runtimeStartToSendMsg": 1,
        "networkActiveDirectCallerCount": 0,
        "networkStartDirectCallerCount": 0,
        "runtimeActiveDirectCallerCount": 2,
        "runtimeStartDirectCallerCount": 2,
        "runtimeActiveArguments": [True, False],
        "runtimeStartArguments": [True, False],
        "manualStartFlagWrite": True,
        "manualStartFlagBeforeStateSetter": True,
        "startTrueFollowedByPreStartActionRunning": True,
    }
    actual_request_flow = {
        name: (observation.get("clientRequestFlow") or {}).get(name)
        for name in expected_request_flow
    }
    if actual_request_flow != expected_request_flow:
        fail("clientRequestFlow", expected_request_flow, actual_request_flow)

    expected_runtime_callers = {
        "RuntimeSendActive": [
            ("Beyond.Gameplay.Core.LevelScriptRuntime", "UpdateRuntimeState", 2)
        ],
        "RuntimeSendStart": [
            ("Beyond.Gameplay.Core.LevelScriptRuntime", "UpdateRuntimeState", 2)
        ],
        "NetworkSetActive": [],
        "NetworkSetStart": [],
    }
    actual_runtime_callers = {
        key: [
            (row.get("type"), row.get("method"), len(row.get("callSites") or []))
            for row in (observation.get("directCallers") or {}).get(key) or []
        ]
        for key in expected_runtime_callers
    }
    if actual_runtime_callers != expected_runtime_callers:
        fail("requestDirectCallers", expected_runtime_callers, actual_runtime_callers)

    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def levelscript_activation_control_contract(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    helper: Any,
    cs: list[dict[str, Any]],
    sc: list[dict[str, Any]],
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Recover general public-state and SubGame ManualStart producers."""
    mapper = load_native_mapper(mapper_path)
    pe = mapper.PeImage(gameassembly_path)
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    metadata_registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if metadata_registration is None:
        raise RuntimeError(
            "LevelScript activation audit could not derive MetadataRegistration"
        )
    generic_index = mapper.build_generic_method_index(
        pe,
        metadata,
        mapper.DEFAULT_CODE_REGISTRATION,
        metadata_registration,
    )
    for pointer, aliases in generic_index.items():
        if pointer not in method_by_pointer:
            method_by_pointer[pointer] = aliases
    sorted_pointers = sorted(method_by_pointer)
    pointers_by_method_index: dict[int, set[int]] = {}
    for pointer, aliases in method_by_pointer.items():
        for alias in aliases:
            method_index = alias.get("methodIndex")
            if isinstance(method_index, int):
                pointers_by_method_index.setdefault(method_index, set()).add(pointer)

    metadata_summary = mapper.metadata_registration_summary(
        pe, metadata_registration
    )

    def find_type(type_name: str) -> list[Any]:
        return [
            type_def
            for type_def in metadata.types
            if metadata.type_full_name(type_def) == type_name
        ]

    def mapped_method(
        type_name: str,
        method_name: str,
        parameter_count: int,
        return_type: str,
        *,
        parameter_types: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        types = find_type(type_name)
        if len(types) == 1:
            for method_def in metadata.methods_for(types[0]):
                info = helper.method_row(metadata, method_def)
                actual_parameter_types = tuple(
                    row.get("typeName")
                    for row in info.get("parameterDetails") or []
                )
                if (
                    info.get("name") != method_name
                    or info.get("parameterCount") != parameter_count
                    or info.get("returnTypeName") != return_type
                    or (
                        parameter_types is not None
                        and actual_parameter_types != parameter_types
                    )
                ):
                    continue
                pointers = sorted(
                    pointers_by_method_index.get(method_def.index) or []
                )
                candidates.append({
                    "methodIndex": method_def.index,
                    "token": info.get("token"),
                    "parameterTypes": list(actual_parameter_types),
                    "returnTypeName": info.get("returnTypeName"),
                    "pointers": pointers,
                })
        if len(candidates) == 1 and len(candidates[0]["pointers"]) == 1:
            candidate = candidates[0]
            pointer = candidate["pointers"][0]
            return {
                **candidate,
                "pointers": [f"0x{value:x}" for value in candidate["pointers"]],
                "methodPointerVa": f"0x{pointer:x}",
                "mappingStatus": "mapped_unique",
            }
        return {
            "mappingStatus": "unresolved",
            "candidateCount": len(candidates),
            "declaringTypeCount": len(types),
            "candidates": candidates,
        }

    methods = {
        "StateNotifyHandler": mapped_method(
            "Beyond.Gameplay.GameplayNetwork",
            "_Handle_SceneLevelScriptStateNotify",
            1,
            "System.Void",
            parameter_types=("Proto.SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY+<>c&",),
        ),
        "ManagerStateShort": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptManager",
            "ServerSyncLevelScriptState",
            4,
            "System.Void",
        ),
        "ManagerStateFull": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptManager",
            "ServerSyncLevelScriptState",
            5,
            "System.Void",
        ),
        "ContainerState": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptContainer",
            "ServerSyncLevelScriptState",
            4,
            "System.Void",
        ),
        "UpdateState": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "UpdateState",
            3,
            "System.Void",
            parameter_types=(
                "Beyond.GEnums.LevelScriptState",
                "Beyond.Gameplay.Core.ScriptEndReason",
                "System.Boolean",
            ),
        ),
        "set_state": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "set_state",
            1,
            "System.Void",
            parameter_types=("Beyond.GEnums.LevelScriptState",),
        ),
        "set_runtimeState": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "set_runtimeState",
            1,
            "System.Void",
            parameter_types=(
                "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState",
            ),
        ),
        "UpdateRuntimeState": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "UpdateRuntimeState",
            1,
            "System.Void",
            parameter_types=("Beyond.Gameplay.Core.ScriptEndReason",),
        ),
        "ChallengeOnInteract": mapped_method(
            "Beyond.Gameplay.InteractiveLogicChallengeStartPoint",
            "_OnInteract",
            0,
            "System.Void",
            parameter_types=(),
        ),
        "SubGameTableTryGetValue": mapped_method(
            "Beyond.Gameplay.Core.SubGameInstanceDataTable",
            "TryGetValue",
            2,
            "System.Boolean",
        ),
        "LevelScriptPtrImplicit": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptPtr",
            "op_Implicit",
            1,
            "Beyond.Gameplay.Core.LevelScriptPtr",
        ),
        "TryGetLevelScript": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptManager",
            "TryGetLevelScript",
            3,
            "System.Boolean",
        ),
        "ManualStart": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "ManualStart",
            0,
            "System.Void",
            parameter_types=(),
        ),
        "ManualStartActionExecute": mapped_method(
            "Beyond.Gameplay.Actions.ManualStartLevelScript",
            "Execute",
            1,
            "System.Void",
            parameter_types=("System.Single",),
        ),
        "NetworkSetActive": mapped_method(
            "Beyond.Gameplay.GameplayNetwork",
            "SendLevelScriptSetActive",
            3,
            "System.Void",
            parameter_types=("System.UInt64", "System.Int32", "System.Boolean"),
        ),
        "NetworkSetStart": mapped_method(
            "Beyond.Gameplay.GameplayNetwork",
            "SendLevelScriptSetStart",
            3,
            "System.Void",
            parameter_types=("System.UInt64", "System.Int32", "System.Boolean"),
        ),
        "RuntimeSendActive": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "_SendLevelScriptSetActive",
            1,
            "System.Void",
            parameter_types=("System.Boolean",),
        ),
        "RuntimeSendStart": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "_SendLevelScriptSetStart",
            1,
            "System.Void",
            parameter_types=("System.Boolean",),
        ),
        "BaseSendMsg": mapped_method(
            "Beyond.Gameplay.BaseNetworkSystem",
            "SendMsg",
            2,
            "System.Void",
        ),
    }

    def method_body(method_key: str) -> dict[str, Any]:
        method = methods.get(method_key) or {}
        if method.get("mappingStatus") != "mapped_unique":
            return {}
        pointer = int(method["methodPointerVa"], 16)
        scan_size, next_pointer = mapper.estimate_scan_size(
            pointer, sorted_pointers, 65536
        )
        mapper_row = full_method_mapper_row(
            metadata, helper, int(method["methodIndex"])
        )
        body = mapper.build_method_body_summary(
            mapper_row,
            pe.bytes_at_va(pointer, scan_size),
            pointer,
            method_by_pointer,
            pe=pe,
            max_instructions=30000,
        )
        body["methodPointerVa"] = f"0x{pointer:x}"
        body["methodPointerRva"] = f"0x{pointer - pe.image_base:x}"
        body["scanBytes"] = scan_size
        body["nextMethodPointerVa"] = (
            f"0x{next_pointer:x}" if next_pointer else None
        )
        return body

    bodies = {
        name: method_body(name)
        for name in (
            "StateNotifyHandler",
            "ManagerStateShort",
            "ManagerStateFull",
            "ContainerState",
            "UpdateState",
            "ChallengeOnInteract",
            "UpdateRuntimeState",
            "ManualStart",
            "NetworkSetActive",
            "NetworkSetStart",
            "RuntimeSendActive",
            "RuntimeSendStart",
        )
    }

    def calls_to(body_key: str, target_key: str) -> list[dict[str, Any]]:
        expected = (methods.get(target_key) or {}).get("methodIndex")
        return [
            call
            for call in sorted(
                (bodies.get(body_key) or {}).get("calls") or [],
                key=lambda row: row["offset"],
            )
            if any(
                target.get("methodIndex") == expected
                for target in call.get("resolved") or []
            )
        ]

    state_links = {
        "handlerToManagerShort": calls_to(
            "StateNotifyHandler", "ManagerStateShort"
        ),
        "managerShortToManagerFull": calls_to(
            "ManagerStateShort", "ManagerStateFull"
        ),
        "managerFullToContainer": calls_to(
            "ManagerStateFull", "ContainerState"
        ),
        "containerToUpdateState": calls_to("ContainerState", "UpdateState"),
        "updateStateToSetter": calls_to("UpdateState", "set_state"),
        "updateStateToRuntimeEvaluation": calls_to(
            "UpdateState", "UpdateRuntimeState"
        ),
    }
    public_state_flow = {
        name: len(calls) for name, calls in state_links.items()
    }
    setter_calls = state_links["updateStateToSetter"]
    runtime_calls = state_links["updateStateToRuntimeEvaluation"]
    public_state_flow["setterBeforeRuntimeEvaluation"] = (
        len(setter_calls) == 1
        and len(runtime_calls) == 1
        and int(setter_calls[0]["offset"]) < int(runtime_calls[0]["offset"])
    )
    public_state_flow["callOffsets"] = {
        name: [row.get("offset") for row in calls]
        for name, calls in state_links.items()
    }

    subgame_links = {
        "subGameLookupCallCount": calls_to(
            "ChallengeOnInteract", "SubGameTableTryGetValue"
        ),
        "scriptPtrConversionCallCount": calls_to(
            "ChallengeOnInteract", "LevelScriptPtrImplicit"
        ),
        "tryGetLevelScriptCallCount": calls_to(
            "ChallengeOnInteract", "TryGetLevelScript"
        ),
        "manualStartCallCount": calls_to("ChallengeOnInteract", "ManualStart"),
    }
    ordered_calls = [
        subgame_links[name]
        for name in (
            "subGameLookupCallCount",
            "scriptPtrConversionCallCount",
            "tryGetLevelScriptCallCount",
            "manualStartCallCount",
        )
    ]
    offsets = [
        int(rows[0]["offset"]) for rows in ordered_calls if len(rows) == 1
    ]
    challenge_fields = find_type(
        "Beyond.Gameplay.InteractiveLogicChallengeStartPoint"
    )
    subgame_fields = find_type("Beyond.Gameplay.Core.SubGameInstanceData")
    state_notify_fields = find_type(
        "Proto.SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY"
    )
    field_offsets: dict[str, int | None] = {}
    if len(challenge_fields) == 1:
        current = runtime_type_field_offsets(
            metadata, pe, metadata_summary, challenge_fields[0].index
        )
        field_offsets["challengeStartPoint.m_subGameId"] = current.get(
            "m_subGameId"
        )
    if len(subgame_fields) == 1:
        current = runtime_type_field_offsets(
            metadata, pe, metadata_summary, subgame_fields[0].index
        )
        field_offsets["subGameInstanceData.bindScriptId"] = current.get(
            "bindScriptId"
        )
    if len(state_notify_fields) == 1:
        current = runtime_type_field_offsets(
            metadata, pe, metadata_summary, state_notify_fields[0].index
        )
        for name in ("sceneNumId_", "scriptId_", "state_", "isComplete_"):
            field_offsets[f"stateNotify.{name}"] = current.get(name)
    runtime_fields = find_type("Beyond.Gameplay.Core.LevelScriptRuntime")
    if len(runtime_fields) == 1:
        current = runtime_type_field_offsets(
            metadata, pe, metadata_summary, runtime_fields[0].index
        )
        field_offsets["levelScriptRuntime.m_manualStartTriggered"] = current.get(
            "m_manualStartTriggered"
        )

    challenge_body = bodies.get("ChallengeOnInteract") or {}
    field_accesses = challenge_body.get("fieldAccesses") or []
    subgame_id_offset = field_offsets.get("challengeStartPoint.m_subGameId")
    bind_script_offset = field_offsets.get("subGameInstanceData.bindScriptId")
    subgame_interaction_flow = {
        name: len(rows) for name, rows in subgame_links.items()
    }
    subgame_interaction_flow.update({
        "callsInCarrierOrder": len(offsets) == 4 and offsets == sorted(offsets),
        "subGameIdFieldRead": any(
            row.get("kind") == "read"
            and row.get("origin") == f"this+0x{subgame_id_offset:x}"
            for row in field_accesses
            if isinstance(subgame_id_offset, int)
        ),
        "bindScriptIdFieldRead": any(
            (call.get("argumentContext") or {})
            .get("argRegisterWrites", {})
            .get("rdx", {})
            .get("text")
            == f"mov rdx, [rdx+0x{bind_script_offset:x}]"
            for call in subgame_links["scriptPtrConversionCallCount"]
            if isinstance(bind_script_offset, int)
        ),
        "callOffsets": {
            name: [row.get("offset") for row in rows]
            for name, rows in subgame_links.items()
        },
    })

    target_pointers = {
        int(methods[key]["methodPointerVa"], 16): key
        for key in (
            "ManualStart",
            "NetworkSetActive",
            "NetworkSetStart",
            "RuntimeSendActive",
            "RuntimeSendStart",
        )
        if methods[key].get("mappingStatus") == "mapped_unique"
    }
    caller_rows: dict[str, dict[tuple[str, str, int], dict[str, Any]]] = {
        key: {} for key in target_pointers.values()
    }
    caller_body_cache: dict[int, dict[str, Any]] = {}
    if target_pointers:
        for section in pe.sections:
            if section["name"] not in {".text", "il2cpp"} or not section["rawSize"]:
                continue
            data = pe.buf[
                section["rawPointer"] : section["rawPointer"]
                + section["rawSize"]
            ]
            section_va = pe.image_base + section["virtualAddress"]
            offset = data.find(b"\xe8")
            while 0 <= offset <= len(data) - 5:
                relative = struct.unpack_from("<i", data, offset + 1)[0]
                call_va = section_va + offset
                target_pointer = call_va + 5 + relative
                target_key = target_pointers.get(target_pointer)
                if target_key is not None:
                    position = bisect_right(sorted_pointers, call_va) - 1
                    caller_pointer = (
                        sorted_pointers[position] if position >= 0 else 0
                    )
                    aliases = method_by_pointer.get(caller_pointer) or []
                    next_pointer = (
                        sorted_pointers[position + 1]
                        if 0 <= position + 1 < len(sorted_pointers)
                        else 0
                    )
                    if (
                        not caller_pointer
                        or (next_pointer and call_va >= next_pointer)
                        or not aliases
                    ):
                        offset = data.find(b"\xe8", offset + 1)
                        continue
                    if caller_pointer not in caller_body_cache:
                        scan_size, _ = mapper.estimate_scan_size(
                            caller_pointer, sorted_pointers, 65536
                        )
                        caller_body_cache[caller_pointer] = (
                            mapper.build_method_body_summary(
                                full_method_mapper_row(
                                    metadata,
                                    helper,
                                    int(aliases[0]["methodIndex"]),
                                ),
                                pe.bytes_at_va(caller_pointer, scan_size),
                                caller_pointer,
                                method_by_pointer,
                                pe=pe,
                                max_instructions=30000,
                            )
                        )
                    call_offset = call_va - caller_pointer
                    decoded_call = next((
                        row
                        for row in (
                            caller_body_cache[caller_pointer].get("calls") or []
                        )
                        if row.get("offset") == call_offset
                        and any(
                            target.get("methodIndex")
                            == methods[target_key].get("methodIndex")
                            for target in row.get("resolved") or []
                        )
                    ), None)
                    if decoded_call is None:
                        offset = data.find(b"\xe8", offset + 1)
                        continue
                    for alias in aliases:
                        key = (
                            str(alias.get("type") or ""),
                            str(alias.get("method") or ""),
                            int(alias.get("methodIndex") or -1),
                        )
                        row = caller_rows[target_key].setdefault(key, {
                            "type": key[0],
                            "method": key[1],
                            "methodIndex": key[2],
                            "token": alias.get("token"),
                            "methodPointerVa": f"0x{caller_pointer:x}",
                            "callSites": [],
                        })
                        row["callSites"].append({
                            "callVa": f"0x{call_va:x}",
                            "callOffset": call_offset,
                            "section": section["name"],
                            "decodedDirectCall": True,
                        })
                offset = data.find(b"\xe8", offset + 1)
    direct_callers = {
        key: sorted(rows.values(), key=lambda row: (row["type"], row["method"]))
        for key, rows in caller_rows.items()
    }
    manual_start_callers = [
        {
            **row,
            **((row.get("callSites") or [{}])[0]),
        }
        for row in direct_callers.get("ManualStart") or []
    ]

    def boolean_argument(call: dict[str, Any]) -> bool | None:
        text = str(
            (((call.get("argumentContext") or {}).get("argRegisterWrites") or {})
             .get("rdx") or {}).get("text") or ""
        ).lower()
        if text in {"mov dl, 0x1", "mov edx, 0x1"}:
            return True
        if text in {"xor edx, edx", "xor rdx, rdx"}:
            return False
        return None

    update_active_calls = calls_to("UpdateRuntimeState", "RuntimeSendActive")
    update_start_calls = calls_to("UpdateRuntimeState", "RuntimeSendStart")
    manual_body = bodies.get("ManualStart") or {}
    manual_flag_offset = field_offsets.get(
        "levelScriptRuntime.m_manualStartTriggered"
    )
    manual_flag_writes = [
        row for row in manual_body.get("fieldAccesses") or []
        if isinstance(manual_flag_offset, int)
        and row.get("kind") == "write"
        and row.get("origin") == f"this+0x{manual_flag_offset:x}"
    ]
    manual_setter_calls = calls_to("ManualStart", "set_runtimeState")
    start_true = [
        row for row in update_start_calls if boolean_argument(row) is True
    ]
    update_setter_calls = calls_to("UpdateRuntimeState", "set_runtimeState")
    prestart_action_running_calls = [
        row for row in update_setter_calls
        if str((((row.get("argumentContext") or {}).get("argRegisterWrites") or {})
                .get("rdx") or {}).get("text") or "").lower()
        in {"mov edx, 0x17", "mov dl, 0x17"}
    ]
    request_links = {
        "networkActiveToSendMsg": calls_to("NetworkSetActive", "BaseSendMsg"),
        "networkStartToSendMsg": calls_to("NetworkSetStart", "BaseSendMsg"),
        "runtimeActiveToSendMsg": calls_to("RuntimeSendActive", "BaseSendMsg"),
        "runtimeStartToSendMsg": calls_to("RuntimeSendStart", "BaseSendMsg"),
    }
    client_request_flow = {
        name: len(rows) for name, rows in request_links.items()
    }
    client_request_flow.update({
        "networkActiveDirectCallerCount": sum(
            len(row.get("callSites") or [])
            for row in direct_callers.get("NetworkSetActive") or []
        ),
        "networkStartDirectCallerCount": sum(
            len(row.get("callSites") or [])
            for row in direct_callers.get("NetworkSetStart") or []
        ),
        "runtimeActiveDirectCallerCount": sum(
            len(row.get("callSites") or [])
            for row in direct_callers.get("RuntimeSendActive") or []
        ),
        "runtimeStartDirectCallerCount": sum(
            len(row.get("callSites") or [])
            for row in direct_callers.get("RuntimeSendStart") or []
        ),
        "runtimeActiveArguments": [boolean_argument(row) for row in update_active_calls],
        "runtimeStartArguments": [boolean_argument(row) for row in update_start_calls],
        "manualStartFlagWrite": len(manual_flag_writes) == 1,
        "manualStartFlagBeforeStateSetter": (
            len(manual_flag_writes) == 1
            and len(manual_setter_calls) == 1
            and int(manual_flag_writes[0]["offset"])
            < int(manual_setter_calls[0]["offset"])
        ),
        "startTrueFollowedByPreStartActionRunning": (
            len(start_true) == 1
            and len(prestart_action_running_calls) == 1
            and int(start_true[0]["offset"])
            < int(prestart_action_running_calls[0]["offset"])
        ),
        "callOffsets": {
            **{name: [row.get("offset") for row in rows]
               for name, rows in request_links.items()},
            "runtimeActive": [row.get("offset") for row in update_active_calls],
            "runtimeStart": [row.get("offset") for row in update_start_calls],
            "manualStartFlag": [row.get("offset") for row in manual_flag_writes],
            "manualStartSetter": [row.get("offset") for row in manual_setter_calls],
            "preStartActionRunningSetter": [
                row.get("offset") for row in prestart_action_running_calls
            ],
        },
    })

    cs_by_name = {row["name"]: row["id"] for row in cs}
    sc_by_name = {row["name"]: row["id"] for row in sc}
    message_ids = {
        "CsSceneSetLevelScriptActive": cs_by_name.get(
            "CsSceneSetLevelScriptActive"
        ),
        "CsSceneSetLevelScriptStart": cs_by_name.get(
            "CsSceneSetLevelScriptStart"
        ),
        "ScSceneLevelScriptStateNotify": sc_by_name.get(
            "ScSceneLevelScriptStateNotify"
        ),
    }
    message_schemas = {
        "activationRequest": message_schema(
            metadata, defaults, "Proto.CS_SCENE_SET_LEVEL_SCRIPT_ACTIVE"
        ),
        "startRequest": message_schema(
            metadata, defaults, "Proto.CS_SCENE_SET_LEVEL_SCRIPT_START"
        ),
        "stateNotify": message_schema(
            metadata, defaults, "Proto.SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY"
        ),
    }
    observation = {
        "messageIds": message_ids,
        "messageSchemas": message_schemas,
        "fieldOffsets": field_offsets,
        "methods": methods,
        "publicStateFlow": public_state_flow,
        "subGameInteractionFlow": subgame_interaction_flow,
        "manualStartDirectCallers": manual_start_callers,
        "directCallers": direct_callers,
        "clientRequestFlow": client_request_flow,
    }
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }
    validation = validate_levelscript_activation_control_observation(
        observation,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
    )
    return {
        "schema": "levelScriptActivationControl.v2",
        "classification": "server_state_subgame_and_runtime_request_paths",
        "discoveryPattern": {
            "methodSelection": "exact metadata type, name, signature, and return type",
            "messageSelection": "exact current enum IDs and protobuf fields",
            "fieldSelection": "MetadataRegistration instance offsets",
            "callers": (
                "complete current executable-code direct E8 caller census for "
                "ManualStart and both public/runtime active/start sender methods"
            ),
            "serializedObjectInputs": [
                "SubGameInstanceData.id",
                "SubGameInstanceData.bindScriptId",
            ],
        },
        **observation,
        "finding": (
            "The server state notification applies its exact scene/script/state tuple "
            "through LevelScriptManager and LevelScriptContainer into "
            "LevelScriptRuntime.UpdateState. Separately, the only direct ManualStart "
            "callers in the current AOT client are ManualStartLevelScript.Execute and "
            "InteractiveLogicChallengeStartPoint._OnInteract; the interaction path "
            "resolves the typed SubGame row by id, reads bindScriptId, looks up that "
            "LevelScript, and calls ManualStart. The same generic runtime records the "
            "manual-start flag, enters PreStart, emits the typed client start request, "
            "and enters PreStartActionRunning."
        ),
        "boundary": (
            "An exact SubGame id/bindScriptId row therefore proves an interaction "
            "ManualStart carrier for that bound script. The server state packet has no "
            "mission or quest field, and neither path proves which mission owns Story "
            "playback, which server branch selected a state, or any cross-Story order. "
            "The public network sender methods have zero direct current-AOT callers; "
            "indirect/IFix/server selection remains outside this evidence."
        ),
        "validation": validation,
    }


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


def full_method_mapper_row(metadata: Any, helper: Any, method_index: int) -> dict[str, Any]:
    method_def = metadata.methods[method_index]
    owner_def = metadata.types[method_def.declaring_type]
    method_info = helper.method_row(metadata, method_def)
    return {
        "type": metadata.type_full_name(owner_def),
        "image": metadata.image_name_by_type_index.get(owner_def.index, ""),
        "method": method_info["name"],
        "methodIndex": method_index,
        "token": method_info["token"],
        "returnTypeName": method_info["returnTypeName"],
        "parameters": method_info["parameters"],
        "parameterDetails": method_info["parameterDetails"],
        "flags": method_info["flags"],
    }


def direct_rel32_call_candidates(
    pe: Any,
    target_va: int,
    section_names: frozenset[str] = frozenset({".text", "il2cpp"}),
) -> list[int]:
    """Find raw E8 candidates; callers must re-decode them before admission."""
    sites: list[int] = []
    for section in pe.sections:
        if section.get("name") not in section_names:
            continue
        start = int(section["rawPointer"])
        data = pe.buf[start:start + int(section["rawSize"])]
        base_va = pe.image_base + int(section["virtualAddress"])
        offset = 0
        while True:
            offset = data.find(b"\xe8", offset)
            if offset < 0:
                break
            if offset + 5 <= len(data):
                relative = struct.unpack_from("<i", data, offset + 1)[0]
                if base_va + offset + 5 + relative == target_va:
                    sites.append(base_va + offset)
            offset += 1
    return sites


def lifecycle_symbols_from_body(body: dict[str, Any]) -> list[str]:
    targets = [
        target
        for row in [*(body.get("calls") or []), *(body.get("controlFlow") or [])]
        for target in row.get("resolved") or []
    ]
    return sorted({
        f"{target.get('type')}.{target.get('method')}"
        for target in targets
        if STATE_LIFECYCLE_METHOD_RE.fullmatch(str(target.get("method") or ""))
    })


def typed_getter_field_consumer_census(
    metadata: Any,
    helper: Any,
    mapper: Any,
    pe: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    sorted_pointers: list[int],
    *,
    getter_va: int,
    return_type: str,
    field_offsets: dict[str, int],
    max_method_bytes: int = 65536,
) -> dict[str, Any]:
    """Decode every direct typed-getter caller and census exact root fields."""
    raw_sites = direct_rel32_call_candidates(pe, getter_va)
    sites_by_pointer: dict[int, list[int]] = {}
    rejected_sites: list[dict[str, Any]] = []
    for site in raw_sites:
        position = bisect_right(sorted_pointers, site) - 1
        if position < 0:
            rejected_sites.append({"va": f"0x{site:x}", "reason": "noPrecedingMethod"})
            continue
        pointer = sorted_pointers[position]
        span = site - pointer
        if span > max_method_bytes:
            rejected_sites.append({
                "va": f"0x{site:x}",
                "reason": "outsideBoundedMethodSpan",
                "precedingMethodVa": f"0x{pointer:x}",
                "span": span,
            })
            continue
        sites_by_pointer.setdefault(pointer, []).append(site)

    rows: list[dict[str, Any]] = []
    verified_sites: list[int] = []
    return_prefix = f"return:{return_type}"
    for pointer, candidate_sites in sorted(sites_by_pointer.items()):
        aliases = method_by_pointer.get(pointer) or []
        method_indexes = sorted({
            int(row["methodIndex"])
            for row in aliases
            if row.get("methodIndex") is not None
        })
        if len(method_indexes) != 1:
            rejected_sites.extend({
                "va": f"0x{site:x}",
                "reason": "ambiguousCallerMethod",
                "methodIndexes": method_indexes,
            } for site in candidate_sites)
            continue
        mapper_row = full_method_mapper_row(metadata, helper, method_indexes[0])
        scan_size, next_pointer = mapper.estimate_scan_size(
            pointer, sorted_pointers, max_method_bytes
        )
        body = mapper.build_method_body_summary(
            mapper_row,
            pe.bytes_at_va(pointer, scan_size),
            pointer,
            method_by_pointer,
            pe=pe,
            max_instructions=30000,
        )
        decoded_call_offsets = {
            int(call.get("offset") or 0)
            for call in body.get("calls") or []
            if call.get("targetVa") == f"0x{getter_va:x}"
        }
        local_verified = [
            site for site in candidate_sites if site - pointer in decoded_call_offsets
        ]
        verified_sites.extend(local_verified)
        rejected_sites.extend({
            "va": f"0x{site:x}",
            "reason": "rawE8NotDecodedAsCallInstruction",
            "callerVa": f"0x{pointer:x}",
        } for site in candidate_sites if site not in local_verified)
        if not local_verified:
            continue
        reads: dict[str, list[dict[str, Any]]] = {}
        for name, field_offset in field_offsets.items():
            origin = f"{return_prefix}+0x{field_offset:x}"
            matches = [
                {
                    "offset": access.get("offset"),
                    "va": access.get("va"),
                    "text": access.get("text"),
                }
                for access in body.get("fieldAccesses") or []
                if access.get("origin") == origin and access.get("kind") == "read"
            ]
            if matches:
                reads[name] = matches
        if not reads:
            continue
        parameter_details = mapper_row.get("parameterDetails") or []
        is_two_value_comparator = (
            mapper_row.get("returnTypeName") == "System.Int32"
            and len(parameter_details) == 2
            and parameter_details[0].get("typeName")
            == parameter_details[1].get("typeName")
        )
        if reads.get("flowIndex") and is_two_value_comparator:
            classification = "two_value_display_sort_comparator"
        elif reads.get("prevQuestIdList") and "deprecated" in str(
            mapper_row.get("method") or ""
        ).lower():
            classification = "deprecated_description_fallback"
        else:
            classification = "typed_field_consumer"
        rows.append({
            "caller": {
                "type": mapper_row["type"],
                "method": mapper_row["method"],
                "methodIndex": mapper_row["methodIndex"],
                "token": mapper_row["token"],
                "va": f"0x{pointer:x}",
                "returnTypeName": mapper_row.get("returnTypeName"),
                "parameterTypes": [
                    row.get("typeName") for row in parameter_details
                ],
                "scanBytes": scan_size,
                "nextMethodPointerVa": (
                    f"0x{next_pointer:x}" if next_pointer else None
                ),
            },
            "getterCallOffsets": [site - pointer for site in local_verified],
            "fieldReads": reads,
            "classification": classification,
            "lifecycleCalls": lifecycle_symbols_from_body(body),
        })
    return {
        "getterVa": f"0x{getter_va:x}",
        "returnType": return_type,
        "rawE8CandidateCount": len(raw_sites),
        "verifiedDirectCallCount": len(verified_sites),
        "rejectedRawCandidates": rejected_sites,
        "fieldConsumerMethodCount": len(rows),
        "fieldReadCounts": {
            name: sum(len(row["fieldReads"].get(name) or []) for row in rows)
            for name in field_offsets
        },
        "rows": rows,
    }


def validate_quest_topology_consumer_observation(
    *,
    verified_direct_calls: int,
    active_predecessor_rows: list[dict[str, Any]],
    non_sort_flow_rows: list[dict[str, Any]],
    main_path_read_rows: list[dict[str, Any]],
    lifecycle_calls: list[str],
    source_file: str,
    source_hashes: dict[str, str],
    prior_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    failures = list(prior_failures or [])

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_topology_field_consumer_census",
            "gate": gate,
            "message": "client quest topology consumers",
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    if verified_direct_calls < 1:
        fail("verifiedQuestInfoCallers", ">=1", verified_direct_calls)
    if active_predecessor_rows:
        fail("noActivePredecessorRuntimeConsumer", [], active_predecessor_rows)
    if non_sort_flow_rows:
        fail("flowIndexOnlyDisplayComparator", [], non_sort_flow_rows)
    if not main_path_read_rows:
        fail("mainPathConsumerDiscovery", ">=1", main_path_read_rows)
    if lifecycle_calls:
        fail("noTopologyDrivenLifecycleCall", [], lifecycle_calls)
    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def quest_topology_field_consumer_census(
    metadata: Any,
    helper: Any,
    mapper: Any,
    pe: Any,
    metadata_summary: dict[str, Any],
    method_by_pointer: dict[int, list[dict[str, Any]]],
    sorted_pointers: list[int],
    quest_start: dict[str, Any],
    gameassembly_path: Path,
) -> dict[str, Any]:
    """Classify all discovered client consumers of authored quest topology."""
    quest_fields = {
        name: int(str(value), 16)
        for name, value in (quest_start.get("questInfoFieldOffsets") or {}).items()
        if name in {"prevQuestIdList", "flowIndex"} and value
    }
    getter_rows = quest_start.get("questInfoGetterCalls") or []
    getter_va = int(str(getter_rows[0]["targetVa"]), 16)
    quest_consumers = typed_getter_field_consumer_census(
        metadata,
        helper,
        mapper,
        pe,
        method_by_pointer,
        sorted_pointers,
        getter_va=getter_va,
        return_type=str(quest_start.get("questInfoType") or ""),
        field_offsets=quest_fields,
    )

    required_mission_fields = {
        "missionId",
        "questDic",
        "mainPathQuests",
        "m_mainPathQuestsHashSet",
        "overrideDescOnlyConsiderMainPath",
    }
    mission_candidates = []
    for type_def in metadata.types:
        names = {
            metadata.string(field.name_index)
            for field in metadata.fields_for(type_def)
        }
        if required_mission_fields <= names:
            mission_candidates.append(type_def)
    failures: list[dict[str, Any]] = []
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_topology_field_consumer_census",
            "gate": gate,
            "message": "client quest topology consumers",
            "expected": expected,
            "actual": actual,
            "sourceFile": str(gameassembly_path.resolve()),
            "sourceHashes": source_hashes,
        })

    mission_rows: list[dict[str, Any]] = []
    mission_type = ""
    mission_offsets: dict[str, int] = {}
    if len(mission_candidates) != 1:
        fail(
            "uniqueMissionRuntimeShape",
            1,
            [metadata.type_full_name(row) for row in mission_candidates],
        )
    else:
        mission_def = mission_candidates[0]
        mission_type = metadata.type_full_name(mission_def)
        all_offsets = runtime_type_field_offsets(
            metadata, pe, metadata_summary, mission_def.index
        )
        mission_offsets = {
            name: all_offsets.get(name)
            for name in ("mainPathQuests", "m_mainPathQuestsHashSet")
        }
        if any(value is None for value in mission_offsets.values()):
            fail(
                "missionTopologyFieldOffsets",
                ["mainPathQuests", "m_mainPathQuestsHashSet"],
                mission_offsets,
            )
        methods_by_index: dict[int, list[int]] = {}
        for pointer, aliases in method_by_pointer.items():
            for alias in aliases:
                method_index = int(alias.get("methodIndex", -1))
                if method_index >= 0:
                    methods_by_index.setdefault(method_index, []).append(pointer)
        for method_offset, method_def in enumerate(metadata.methods_for(mission_def)):
            method_index = mission_def.method_start + method_offset
            pointers = sorted(set(methods_by_index.get(method_index) or []))
            if len(pointers) != 1:
                continue
            pointer = pointers[0]
            mapper_row = full_method_mapper_row(metadata, helper, method_index)
            scan_size, next_pointer = mapper.estimate_scan_size(
                pointer, sorted_pointers, 65536
            )
            body = mapper.build_method_body_summary(
                mapper_row,
                pe.bytes_at_va(pointer, scan_size),
                pointer,
                method_by_pointer,
                pe=pe,
                max_instructions=30000,
            )
            accesses: dict[str, dict[str, list[dict[str, Any]]]] = {}
            for name, field_offset in mission_offsets.items():
                if not isinstance(field_offset, int):
                    continue
                origin = f"this+0x{field_offset:x}"
                for access in body.get("fieldAccesses") or []:
                    if access.get("origin") != origin:
                        continue
                    kind = str(access.get("kind") or "read")
                    accesses.setdefault(name, {}).setdefault(kind, []).append({
                        "offset": access.get("offset"),
                        "va": access.get("va"),
                        "text": access.get("text"),
                    })
            if not accesses:
                continue
            reads_main = bool((accesses.get("mainPathQuests") or {}).get("read"))
            writes_cache = bool(
                (accesses.get("m_mainPathQuestsHashSet") or {}).get("write")
            )
            if reads_main and writes_cache:
                classification = "derived_main_path_membership_cache"
            elif reads_main and "String" in str(mapper_row.get("returnTypeName") or ""):
                classification = "level_or_description_context_selection"
            elif all(
                not kinds.get("read") or name == "m_mainPathQuestsHashSet"
                for name, kinds in accesses.items()
            ):
                classification = "storage_initialization"
            else:
                classification = "typed_field_consumer"
            mission_rows.append({
                "caller": {
                    "type": mapper_row["type"],
                    "method": mapper_row["method"],
                    "methodIndex": method_index,
                    "token": mapper_row["token"],
                    "va": f"0x{pointer:x}",
                    "returnTypeName": mapper_row.get("returnTypeName"),
                    "scanBytes": scan_size,
                    "nextMethodPointerVa": (
                        f"0x{next_pointer:x}" if next_pointer else None
                    ),
                },
                "fieldAccesses": accesses,
                "classification": classification,
                "lifecycleCalls": lifecycle_symbols_from_body(body),
                "stackOriginFlow": body.get("stackOriginFlow") or {},
            })

    topology_rows = [
        row for row in quest_consumers["rows"]
        if row["fieldReads"].get("prevQuestIdList")
        or row["fieldReads"].get("flowIndex")
    ]
    active_predecessor_rows = [
        row for row in topology_rows
        if row["fieldReads"].get("prevQuestIdList")
        and row["classification"] != "deprecated_description_fallback"
    ]
    non_sort_flow_rows = [
        row for row in topology_rows
        if row["fieldReads"].get("flowIndex")
        and row["classification"] != "two_value_display_sort_comparator"
    ]
    lifecycle_calls = sorted({
        call
        for row in [*topology_rows, *mission_rows]
        for call in row.get("lifecycleCalls") or []
    })
    main_path_read_rows = [
        row for row in mission_rows
        if (row.get("fieldAccesses", {}).get("mainPathQuests") or {}).get("read")
    ]
    validation = validate_quest_topology_consumer_observation(
        verified_direct_calls=quest_consumers["verifiedDirectCallCount"],
        active_predecessor_rows=active_predecessor_rows,
        non_sort_flow_rows=non_sort_flow_rows,
        main_path_read_rows=main_path_read_rows,
        lifecycle_calls=lifecycle_calls,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
        prior_failures=failures,
    )

    return {
        "classification": "client_display_and_context_topology_only",
        "questInfoConsumers": quest_consumers,
        "missionRuntimeType": mission_type,
        "missionRuntimeFieldOffsets": {
            name: f"0x{value:x}" if isinstance(value, int) else None
            for name, value in mission_offsets.items()
        },
        "missionRuntimeConsumers": mission_rows,
        "activePredecessorConsumerCount": len(active_predecessor_rows),
        "flowIndexNonSortConsumerCount": len(non_sort_flow_rows),
        "topologyLifecycleCalls": lifecycle_calls,
        "finding": (
            "Across every verified direct GetQuestInfo caller, flowIndex is consumed "
            "only by a two-value MissionShowData comparator and prevQuestIdList only "
            "by a binary-named deprecated description fallback. Structurally discovered "
            "MissionRuntime mainPathQuests builds a membership cache and selects level "
            "or description context. None of these field consumers calls a quest "
            "lifecycle transition."
        ),
        "boundary": (
            "This is the current direct AOT consumer surface. Indirect native calls, "
            "active IFix replacement bodies, and server-only eligibility remain outside "
            "the proof. These fields therefore cannot by themselves label a fork as "
            "parallel or exclusive."
        ),
        "validation": validation,
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
    topology_consumers = quest_topology_field_consumer_census(
        metadata,
        helper,
        mapper,
        pe,
        metadata_summary,
        method_by_pointer,
        sorted_pointers,
        quest_start,
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
        "questTopologyFieldConsumers": topology_consumers,
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
    start_policy_contract = levelscript_start_policy_contract(
        metadata,
        defaults,
        helper,
        gameassembly_path,
        mapper_path,
    )
    manual_self_control_contract = levelscript_manual_self_control_contract(
        metadata,
        defaults,
        helper,
        gameassembly_path,
        mapper_path,
    )
    activation_control_contract = levelscript_activation_control_contract(
        metadata,
        defaults,
        helper,
        cs,
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
        "_schema": "endfieldProtocolRegistryAudit.v11",
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
            "topologyActivePredecessorConsumers": state_application_census[
                "questTopologyFieldConsumers"
            ].get("activePredecessorConsumerCount", 0),
            "topologyFlowIndexNonSortConsumers": state_application_census[
                "questTopologyFieldConsumers"
            ].get("flowIndexNonSortConsumerCount", 0),
            "topologyLifecycleCalls": len(state_application_census[
                "questTopologyFieldConsumers"
            ].get("topologyLifecycleCalls") or []),
            "levelScriptStartPolicyValidated": (
                (start_policy_contract.get("validation") or {}).get("status")
                == "validated"
            ),
            "levelScriptManualSelfControlValidated": (
                (manual_self_control_contract.get("validation") or {}).get(
                    "status"
                )
                == "validated"
            ),
            "levelScriptActivationControlValidated": (
                (activation_control_contract.get("validation") or {}).get(
                    "status"
                )
                == "validated"
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
            "questSuccessorPolicy": state_application_census["boundary"],
            "levelScriptTasks": (
                "The task packet family exposes exact (sceneNumId, scriptId, taskId) "
                "identity, and current-build native sender/handler paths are proven "
                "separately by the runtime-hook manifest and disassembly. No packet "
                "co-carries missionId or questId, so it still cannot attach Story to a mission."
            ),
            "levelScriptStartPolicy": start_policy_contract["boundary"],
            "levelScriptManualSelfControl": (
                manual_self_control_contract["boundary"]
            ),
            "levelScriptActivationControl": (
                activation_control_contract["boundary"]
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
        "levelScriptStartPolicy": start_policy_contract,
        "levelScriptManualSelfControl": manual_self_control_contract,
        "levelScriptActivationControl": activation_control_contract,
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
        (
            "- LevelScript SameWithActive start policy: "
            f"**{'validated' if summary['levelScriptStartPolicyValidated'] else 'failed'}**"
        ),
        (
            "- LevelScript current-context ManualStart self control: "
            f"**{'validated' if summary['levelScriptManualSelfControlValidated'] else 'failed'}**"
        ),
        (
            "- LevelScript public-state / SubGame interaction activation control: "
            f"**{'validated' if summary['levelScriptActivationControlValidated'] else 'failed'}**"
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
    topology = state_census.get("questTopologyFieldConsumers") or {}
    quest_consumer_census = topology.get("questInfoConsumers") or {}
    topology_rows = quest_consumer_census.get("rows") or []
    mission_topology_rows = topology.get("missionRuntimeConsumers") or []
    start_policy = report.get("levelScriptStartPolicy") or {}
    start_policy_methods = start_policy.get("methods") or {}
    start_policy_gates = start_policy.get("startTypeGates") or {}
    start_policy_transition = start_policy.get("preStartTransition") or {}
    activation_control = report.get("levelScriptActivationControl") or {}
    activation_methods = activation_control.get("methods") or {}
    activation_state_flow = activation_control.get("publicStateFlow") or {}
    subgame_flow = activation_control.get("subGameInteractionFlow") or {}
    client_request_flow = activation_control.get("clientRequestFlow") or {}
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
            "### Whole-client topology-field consumers",
            "",
            topology.get("finding") or "[topology consumer audit unavailable]",
            "",
            (
                "Verified direct `GetQuestInfo` calls: "
                f"**{quest_consumer_census.get('verifiedDirectCallCount', 0)}** / "
                f"{quest_consumer_census.get('rawE8CandidateCount', 0)} raw E8 candidates; "
                f"active predecessor consumers: "
                f"**{topology.get('activePredecessorConsumerCount', 0)}**; "
                f"non-sort flow-index consumers: "
                f"**{topology.get('flowIndexNonSortConsumerCount', 0)}**; "
                f"topology-driven lifecycle calls: "
                f"**{len(topology.get('topologyLifecycleCalls') or [])}**."
            ),
            "",
            "| Native consumer | Classification | Fields | Lifecycle calls |",
            "|---|---|---|---|",
            *[
                "| `{type}.{method}` `{token}` @ `{va}` | `{classification}` | "
                "{fields} | {calls} |".format(
                    type=md_escape(row["caller"]["type"]),
                    method=md_escape(row["caller"]["method"]),
                    token=md_escape(row["caller"]["token"]),
                    va=md_escape(row["caller"]["va"]),
                    classification=md_escape(row["classification"]),
                    fields=md_escape(", ".join(
                        f"{name}:{len(reads)} read(s)"
                        for name, reads in row.get("fieldReads", {}).items()
                    )),
                    calls=md_escape(", ".join(row.get("lifecycleCalls") or []) or "none"),
                )
                for row in topology_rows
            ],
            *[
                "| `{type}.{method}` `{token}` @ `{va}` | `{classification}` | "
                "{fields} | {calls} |".format(
                    type=md_escape(row["caller"]["type"]),
                    method=md_escape(row["caller"]["method"]),
                    token=md_escape(row["caller"]["token"]),
                    va=md_escape(row["caller"]["va"]),
                    classification=md_escape(row["classification"]),
                    fields=md_escape(", ".join(
                        f"{name}:" + "/".join(
                            f"{kind}={len(accesses)}"
                            for kind, accesses in kinds.items()
                        )
                        for name, kinds in row.get("fieldAccesses", {}).items()
                    )),
                    calls=md_escape(", ".join(row.get("lifecycleCalls") or []) or "none"),
                )
                for row in mission_topology_rows
            ],
            "",
            topology.get("boundary") or "",
            "",
            "## Generic LevelScript start policy",
            "",
            start_policy.get("finding") or "[start-policy audit unavailable]",
            "",
            (
                "The contract discovers methods by exact metadata name/signature and "
                "then validates current-binary branch targets. It supplies no level, "
                "script, mission, quest, or Story object id as a discovery input."
            ),
            "",
            "| Gate | Enum value | Native call/target | Result |",
            "|---|---:|---|---|",
            (
                "| public state `Active` | {value} | `+0x{offset:x}` -> `{target}` | "
                "exact done-check block |"
            ).format(
                value=(start_policy.get("activeStateGate") or {}).get(
                    "comparedValue", "?"
                ),
                offset=int(
                    (start_policy.get("activeStateGate") or {}).get(
                        "callOffset", 0
                    )
                ),
                target=(start_policy.get("activeStateGate") or {}).get(
                    "branchTargetVa", "?"
                ),
            ),
            *[
                "| startType `{name}` | {value} | `+0x{offset:x}` -> `{target}` | "
                "{result} |".format(
                    name=md_escape(name),
                    value=gate.get("comparedValue", "?"),
                    offset=int(gate.get("callOffset", 0)),
                    target=md_escape(str(gate.get("branchTargetVa") or "?")),
                    result=md_escape(
                        "common PreStart"
                        if name == "SameWithActive"
                        else (
                            "start-area check"
                            if name == "ByEnterStartShape"
                            else "skip start"
                        )
                    ),
                )
                for name, gate in start_policy_gates.items()
            ],
            (
                "| internal runtime state `PreStart` | {value} | "
                "`{target}` -> `{setter}` | exact `set_runtimeState` call |"
            ).format(
                value=start_policy_transition.get("runtimeStateValue", "?"),
                target=md_escape(
                    str(start_policy_transition.get("commonTargetVa") or "?")
                ),
                setter=md_escape(
                    str(
                        (start_policy_methods.get("set_runtimeState") or {}).get(
                            "methodPointerVa"
                        )
                        or "?"
                    )
                ),
            ),
            "",
            start_policy.get("boundary") or "",
            "",
            "## Generic LevelScript activation control",
            "",
            activation_control.get("finding") or "[activation-control audit unavailable]",
            "",
            (
                "Server state message `{message}` ({message_id}) carries only "
                "`sceneNumId`, `scriptId`, `state`, and `isComplete`; its native "
                "handler reaches `LevelScriptRuntime.UpdateState` through three "
                "typed wrappers, then calls `set_state` before "
                "`UpdateRuntimeState`."
            ).format(
                message="SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY",
                message_id=(activation_control.get("messageIds") or {}).get(
                    "ScSceneLevelScriptStateNotify", "?"
                ),
            ),
            "",
            (
                "The exact SubGame interaction chain is "
                "`SubGameInstanceDataTable.TryGetValue` +0x{lookup:x} -> "
                "`LevelScriptPtr.op_Implicit(bindScriptId)` +0x{convert:x} -> "
                "`LevelScriptManager.TryGetLevelScript` +0x{resolve:x} -> "
                "`LevelScriptRuntime.ManualStart` +0x{start:x}."
            ).format(
                lookup=int((subgame_flow.get("callOffsets") or {}).get(
                    "subGameLookupCallCount", [0]
                )[:1][0] if (subgame_flow.get("callOffsets") or {}).get(
                    "subGameLookupCallCount"
                ) else 0),
                convert=int((subgame_flow.get("callOffsets") or {}).get(
                    "scriptPtrConversionCallCount", [0]
                )[:1][0] if (subgame_flow.get("callOffsets") or {}).get(
                    "scriptPtrConversionCallCount"
                ) else 0),
                resolve=int((subgame_flow.get("callOffsets") or {}).get(
                    "tryGetLevelScriptCallCount", [0]
                )[:1][0] if (subgame_flow.get("callOffsets") or {}).get(
                    "tryGetLevelScriptCallCount"
                ) else 0),
                start=int((subgame_flow.get("callOffsets") or {}).get(
                    "manualStartCallCount", [0]
                )[:1][0] if (subgame_flow.get("callOffsets") or {}).get(
                    "manualStartCallCount"
                ) else 0),
            ),
            "",
            (
                "Whole-client direct ManualStart callers: **{count}**; "
                "public-state setter precedes runtime evaluation: **{ordered}**; "
                "SubGame id/bindScriptId field reads validated: **{fields}**."
            ).format(
                count=len(activation_control.get("manualStartDirectCallers") or []),
                ordered=activation_state_flow.get(
                    "setterBeforeRuntimeEvaluation", False
                ),
                fields=(
                    subgame_flow.get("subGameIdFieldRead", False)
                    and subgame_flow.get("bindScriptIdFieldRead", False)
                ),
            ),
            "",
            (
                "The generic client start lifecycle is `ManualStart flag` -> "
                "`PreStart` -> `CS_SCENE_SET_LEVEL_SCRIPT_START` ({message_id}) -> "
                "`PreStartActionRunning`. Runtime start request arguments are "
                "**{arguments}**; runtime sender direct calls are **{runtime_calls}**; "
                "public network sender direct AOT calls are **{network_calls}**."
            ).format(
                message_id=(activation_control.get("messageIds") or {}).get(
                    "CsSceneSetLevelScriptStart", "?"
                ),
                arguments=md_escape(str(
                    client_request_flow.get("runtimeStartArguments") or []
                )),
                runtime_calls=client_request_flow.get(
                    "runtimeStartDirectCallerCount", 0
                ),
                network_calls=client_request_flow.get(
                    "networkStartDirectCallerCount", 0
                ),
            ),
            "",
            (
                "Native entry points: state handler `{handler}`, runtime update "
                "`{update}`, challenge interaction `{challenge}`, ManualStart `{start}`."
            ).format(
                handler=(activation_methods.get("StateNotifyHandler") or {}).get(
                    "methodPointerVa", "?"
                ),
                update=(activation_methods.get("UpdateState") or {}).get(
                    "methodPointerVa", "?"
                ),
                challenge=(activation_methods.get("ChallengeOnInteract") or {}).get(
                    "methodPointerVa", "?"
                ),
                start=(activation_methods.get("ManualStart") or {}).get(
                    "methodPointerVa", "?"
                ),
            ),
            "",
            activation_control.get("boundary") or "",
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
            "Reuse an existing validated v10 report when its original "
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
    if report.get("_schema") != "endfieldProtocolRegistryAudit.v11":
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
    topology_validation = (
        ((report.get("stateUpdateApplicationCensus") or {}).get(
            "questTopologyFieldConsumers"
        ) or {}).get("validation") or {}
    )
    if topology_validation.get("status") != "validated":
        return False, (
            "topology-consumer validation is "
            f"{topology_validation.get('status')!r}"
        )
    start_policy_validation = (
        (report.get("levelScriptStartPolicy") or {}).get("validation") or {}
    )
    if start_policy_validation.get("status") != "validated":
        return False, (
            "LevelScript start-policy validation is "
            f"{start_policy_validation.get('status')!r}"
        )
    manual_self_validation = (
        (report.get("levelScriptManualSelfControl") or {}).get("validation")
        or {}
    )
    if manual_self_validation.get("status") != "validated":
        return False, (
            "LevelScript manual-self-control validation is "
            f"{manual_self_validation.get('status')!r}"
        )
    activation_control_validation = (
        (report.get("levelScriptActivationControl") or {}).get("validation")
        or {}
    )
    if activation_control_validation.get("status") != "validated":
        return False, (
            "LevelScript activation-control validation is "
            f"{activation_control_validation.get('status')!r}"
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
    topology_validation = report["stateUpdateApplicationCensus"][
        "questTopologyFieldConsumers"
    ]["validation"]
    if topology_validation["status"] != "validated":
        first = topology_validation["failures"][0]
        print(
            "topology-consumer validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"message={first.get('message')} expected={first['expected']!r} "
            f"actual={first['actual']!r} source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    start_policy_validation = report["levelScriptStartPolicy"]["validation"]
    if start_policy_validation["status"] != "validated":
        first = start_policy_validation["failures"][0]
        print(
            "LevelScript start-policy validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"message={first.get('message')} expected={first['expected']!r} "
            f"actual={first['actual']!r} source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    manual_self_validation = report["levelScriptManualSelfControl"][
        "validation"
    ]
    if manual_self_validation["status"] != "validated":
        first = manual_self_validation["failures"][0]
        print(
            "LevelScript manual-self-control validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"message={first.get('message')} expected={first['expected']!r} "
            f"actual={first['actual']!r} source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    activation_control_validation = report["levelScriptActivationControl"][
        "validation"
    ]
    if activation_control_validation["status"] != "validated":
        first = activation_control_validation["failures"][0]
        print(
            "LevelScript activation-control validator failed: "
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
        f"{report['summary']['stateUpdateApplicationCandidates']} state-update paths validated, "
        "LevelScript start policy, manual self-control, and activation control validated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
