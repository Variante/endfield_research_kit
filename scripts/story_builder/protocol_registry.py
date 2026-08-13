#!/usr/bin/env python3
"""Build the current-build protobuf message registry and Story-facing schemas.

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
import json
import re
import struct
import sys
from collections import Counter
from functools import partial
from pathlib import Path
from typing import Any


if __package__ == "story_builder":
    from common import (
        ROOT,
        check_installed_native_inputs,
        md_escape,
        native_evidence_required,
        native_evidence_skip_message,
        resolve_installed_game_data_root,
        sha256_file as file_sha256,
        write_report_json,
        write_text_if_changed,
    )
elif __package__ == "scripts.story_builder":
    from scripts.common import (
        ROOT,
        check_installed_native_inputs,
        md_escape,
        native_evidence_required,
        native_evidence_skip_message,
        resolve_installed_game_data_root,
        sha256_file as file_sha256,
        write_report_json,
        write_text_if_changed,
    )
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("run this module with python -m scripts.story_builder.protocol_registry")
from .mission_assets import select_complete_mission_runtime_root
from .native_protocol import il2cpp
from .levelscript_binary import (
    extract_levelscript_uid_records,
    levelscript_action_map_membership,
    levelscript_native_header_contract,
    summarize_levelscript_native_header_records,
)
from .native_contracts.mission_task_paths import (
    DEFAULT_CONTRACT as MISSION_TASK_PATH_CONTRACT,
    load_mission_task_paths,
)


DEFAULT_GAME_DATA_ROOT = resolve_installed_game_data_root()
DEFAULT_METADATA = DEFAULT_GAME_DATA_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_GAMEASSEMBLY = DEFAULT_GAME_DATA_ROOT.parent / "GameAssembly.dll"
METADATA_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
NATIVE_MAPPER_HELPER = (
    ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
)
REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
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
LEVELSCRIPT_ROOTS = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "LevelScriptData",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "LevelScriptData",
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
    mapper = il2cpp.load_native_mapper(mapper_path)
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
            il2cpp.runtime_type_name(pe, metadata, type_va)
            for type_va in il2cpp.runtime_generic_inst_type_pointers(pe, generic_inst_va)
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


def mission_event_asset_coverage(
    mission_runtime_root: Path,
    levelscript_roots: tuple[Path, ...],
    native_header_contract: dict[str, Any],
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

    if native_header_contract.get("schema") != "levelScriptNativeHeaderContract.v1":
        raise RuntimeError("LevelScript native-header contract schema mismatch")
    if native_header_contract.get("status") != "validated":
        raise RuntimeError(
            "LevelScript native-header contract is not valid for this build: "
            f"{native_header_contract.get('status') or 'missing'}"
        )
    target_header_names = {
        "MissionEvent_OnCustomEventForMission",
        "MissionEventHeader",
    }
    levelscript_files = 0
    levelscript_candidates: list[dict[str, Any]] = []
    for root in levelscript_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            levelscript_files += 1
            data = path.read_bytes()
            records = extract_levelscript_uid_records(data)
            _action_map, memberships = levelscript_action_map_membership(data, records)
            for row in summarize_levelscript_native_header_records(
                records,
                memberships,
                names=target_header_names,
            ):
                row = dict(row)
                row["sourceFile"] = str(path.resolve())
                levelscript_candidates.append(row)
    levelscript_candidate_count = sum(
        int(row.get("count") or 0) for row in levelscript_candidates
    )

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
        "levelScriptFilesScanned": levelscript_files,
        "levelScriptNativeHeaderContract": native_header_contract,
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
    mapper = il2cpp.load_native_mapper(mapper_path)
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
        type_name: il2cpp.enum_members(metadata, defaults, type_name)
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


def _mapped_native_method(
    metadata: Any,
    helper: Any,
    pointers_by_method_index: dict[int, set[int]],
    find_type: Any,
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


def levelscript_manual_self_control_contract(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    helper: Any,
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Discover current-level/current-script ManualStart semantics generically."""
    mapper = il2cpp.load_native_mapper(mapper_path)
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
        return type_va, il2cpp.runtime_type_name(pe, metadata, type_va)

    def find_type(type_name: str) -> list[Any]:
        return [
            type_def
            for type_def in metadata.types
            if metadata.type_full_name(type_def) == type_name
        ]

    mapped_method = partial(
        _mapped_native_method,
        metadata,
        helper,
        pointers_by_method_index,
        find_type,
    )

    param_sources = {
        row["name"]: row["id"]
        for row in il2cpp.enum_members(
            metadata, defaults, "Beyond.Gameplay.Actions.ParamSource"
        )
    }
    runtime_state_values = {
        row["name"]: row["id"]
        for row in il2cpp.enum_members(
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
        "ScSelfSceneInfo": 25,
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
        "selfSceneInfo": [
            ("sceneNumId", 1),
            ("sceneId", 2),
            ("levelScripts", 8),
        ],
        "levelScriptInfo": [
            ("scriptId", 1),
            ("state", 2),
            ("properties", 3),
            ("isDone", 4),
            ("stage", 5),
            ("triggerVolumeInfos", 6),
        ],
    }
    actual_fields = {
        key: [
            (row.get("name"), row.get("tag"))
            for row in ((observation.get("messageSchemas") or {}).get(key) or {}).get(
                "fields", []
            )
            if row.get("name") in {name for name, _tag in expected_fields[key]}
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
        "selfSceneInfo.sceneNumId_": 0x18,
        "selfSceneInfo.sceneId_": 0x20,
        "selfSceneInfo.levelScripts_": 0x38,
        "levelScriptInfo.scriptId_": 0x18,
        "levelScriptInfo.state_": 0x20,
        "levelScriptInfo.properties_": 0x28,
        "levelScriptInfo.isDone_": 0x30,
        "levelScriptInfo.stage_": 0x34,
        "levelScriptInfo.triggerVolumeInfos_": 0x38,
        "levelScriptRuntime.m_manualStartTriggered": 0xF8,
        "levelScriptRuntime.withinActiveArea": 0x68,
        "levelScriptRuntime.activeShapeList": 0x70,
        "levelScriptRuntime.activeShapeOutsideList": 0x78,
    }
    actual_offsets = {
        key: (observation.get("fieldOffsets") or {}).get(key)
        for key in expected_offsets
    }
    if actual_offsets != expected_offsets:
        fail("fieldOffsets", expected_offsets, actual_offsets)

    expected_methods = {
        "SelfSceneInfoHandler",
        "StateNotifyHandler",
        "ManagerStateShort",
        "ManagerStateFull",
        "ManagerServerSyncLevelScript",
        "ContainerState",
        "ContainerServerSyncLevelScript",
        "UpdateState",
        "RuntimeServerSync",
        "set_state",
        "set_runtimeState",
        "UpdateRuntimeState",
        "get_state",
        "get_levelScriptType",
        "UpdateWithinActiveArea",
        "Setup",
        "RegisterTriggerFromLevelScript",
        "SetAllTriggerActiveByPhase",
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

    expected_public_state_sources = {
        "snapshotMessageId": 25,
        "incrementalMessageId": 37,
        "snapshotLevelScriptsRuntimeType": (
            "Google.Protobuf.Collections.RepeatedField`1<Proto.LEVEL_SCRIPT_INFO>"
        ),
        "managerStateShortDirectCallers": [
            "Beyond.Gameplay.GameplayNetwork._Handle_SceneLevelScriptStateNotify",
            "Beyond.Gameplay.GameplayNetwork._Handle_SelfSceneInfo",
        ],
        "managerStateFullDirectCallers": [
            "Beyond.Gameplay.Core.LevelScriptManager.ServerSyncLevelScriptState",
        ],
        "managerServerSyncDirectCallers": [],
        "containerStateDirectCallers": [
            "Beyond.Gameplay.Core.LevelScriptManager.ServerSyncLevelScriptState",
        ],
        "updateStateDirectCallers": [
            "Beyond.Gameplay.Core.LevelScriptContainer.ServerSyncLevelScriptState",
        ],
        "runtimeServerSyncDirectCallers": [
            "Beyond.Gameplay.Core.LevelScriptContainer.ServerSyncLevelScript",
        ],
        "containerServerSyncDirectCallers": [
            "Beyond.Gameplay.Core.LevelScriptManager.ServerSyncLevelScript",
            "Beyond.Gameplay.GameplayNetwork._Handle_SelfSceneInfo",
        ],
        "publicStateSetterDirectCallers": [
            "Beyond.Gameplay.Core.LevelScriptContainer.LoadFromLevelData",
            "Beyond.Gameplay.Core.LevelScriptRuntime.Init",
            "Beyond.Gameplay.Core.LevelScriptRuntime.ServerSync",
            "Beyond.Gameplay.Core.LevelScriptRuntime.UpdateState",
        ],
        "publicStateSetterArguments": {
            "Beyond.Gameplay.Core.LevelScriptContainer.LoadFromLevelData": ["0"],
            "Beyond.Gameplay.Core.LevelScriptRuntime.Init": ["0"],
            "Beyond.Gameplay.Core.LevelScriptRuntime.ServerSync": ["param:state"],
            "Beyond.Gameplay.Core.LevelScriptRuntime.UpdateState": ["param:value"],
        },
    }
    actual_public_state_sources = {
        name: (observation.get("publicStateSourceFlow") or {}).get(name)
        for name in expected_public_state_sources
    }
    if actual_public_state_sources != expected_public_state_sources:
        fail(
            "publicStateSourceFlow",
            expected_public_state_sources,
            actual_public_state_sources,
        )

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

    expected_activation_selector_flow = {
        "levelScriptTypeValues": {
            "World": 0,
            "Mission": 1,
            "Game": 2,
            "Master": 3,
            "SubLevelScript": 4,
            "ControlledGame": 5,
        },
        "enabledStateValue": 2,
        "activeStateValue": 3,
        "preActiveStateValue": 7,
        "preActiveEndSendActiveStateValue": 9,
        "waitForStateActiveValue": 10,
        "inactiveLevelScriptTypeCallOffset": 1240,
        "nonSubLevelEnabledStateCallOffset": 1255,
        "activeAreaGateCallOffset": 1274,
        "subLevelActiveStateCallOffset": 1288,
        "preActiveSetterCallOffset": 1313,
        "preActiveLevelScriptTypeCallOffset": 2106,
        "activeTrueRequestCallOffset": 2124,
        "waitForStateActiveSetterOffsets": [2140, 2155],
        "nonSubLevelRequiresEnabledAndActiveArea": True,
        "subLevelRequiresPublicActive": True,
        "nonSubLevelSendsActiveTrueAfterPreActive": True,
        "subLevelSkipsActiveTrueRequest": True,
    }
    actual_activation_selector_flow = {
        name: (observation.get("activationSelectorFlow") or {}).get(name)
        for name in expected_activation_selector_flow
    }
    if actual_activation_selector_flow != expected_activation_selector_flow:
        fail(
            "activationSelectorFlow",
            expected_activation_selector_flow,
            actual_activation_selector_flow,
        )

    expected_active_area_flow = {
        "activeShapeListFieldOffset": 0x70,
        "activeShapeOutsideListFieldOffset": 0x78,
        "withinActiveAreaFieldOffset": 0x68,
        "activeShapeListReadOffsets": [363, 1356, 1374],
        "activeShapeOutsideListReadOffsets": [1630, 1648],
        "withinActiveAreaAccessOffsets": [1704, 1743, 3388, 3394, 3398],
        "activeListPositiveCountSetterOffset": 430,
        "emptyActiveListBranchOffset": 555,
        "activeShapeTestCallOffset": 1617,
        "activeShapeHitBranchOffset": 1624,
        "missingOutsideListBranchOffset": 1635,
        "outsideShapeTestCallOffset": 1691,
        "outsideShapeMissBranchOffset": 1698,
        "withinFalseSetterOffsets": [1743, 3388],
        "outsideShapeHitClearOffset": 1743,
        "withinTrueSetterOffset": 3394,
        "withinReturnOffset": 3398,
        "emptyActiveListSetsWithinTrue": True,
        "activeShapeHitSetsWithinTrue": True,
        "missingOutsideListPreservesPriorWithin": True,
        "outsideShapeMissPreservesPriorWithin": True,
        "outsideShapeHitClearsWithin": True,
    }
    actual_active_area_flow = {
        name: (observation.get("activeAreaFlow") or {}).get(name)
        for name in expected_active_area_flow
    }
    if actual_active_area_flow != expected_active_area_flow:
        fail(
            "activeAreaFlow",
            expected_active_area_flow,
            actual_active_area_flow,
        )

    expected_active_receiver_flow = {
        "triggerActiveDuringValues": {"Active": 0, "Start": 1},
        "setupRegisterTriggerCallCount": 1,
        "activePhaseEnableArguments": [
            {"active": True, "triggerActiveDuring": 0},
            {"active": True, "triggerActiveDuring": 0},
        ],
        "activeBeginStateValue": 14,
        "waitForSubEntityInitNewlyStateValue": 15,
        "activePhaseEnableBetweenStateSetters": True,
    }
    actual_active_receiver_flow = {
        name: (observation.get("activeReceiverFlow") or {}).get(name)
        for name in expected_active_receiver_flow
    }
    if actual_active_receiver_flow != expected_active_receiver_flow:
        fail(
            "activeReceiverFlow",
            expected_active_receiver_flow,
            actual_active_receiver_flow,
        )

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
    mapper = il2cpp.load_native_mapper(mapper_path)
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

    mapped_method = partial(
        _mapped_native_method,
        metadata,
        helper,
        pointers_by_method_index,
        find_type,
    )

    methods = {
        "SelfSceneInfoHandler": mapped_method(
            "Beyond.Gameplay.GameplayNetwork",
            "_Handle_SelfSceneInfo",
            1,
            "System.Void",
        ),
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
        "ManagerServerSyncLevelScript": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptManager",
            "ServerSyncLevelScript",
            7,
            "System.Void",
        ),
        "ContainerState": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptContainer",
            "ServerSyncLevelScriptState",
            4,
            "System.Void",
        ),
        "ContainerServerSyncLevelScript": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptContainer",
            "ServerSyncLevelScript",
            6,
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
        "RuntimeServerSync": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "ServerSync",
            5,
            "System.Void",
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
        "get_state": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "get_state",
            0,
            "Beyond.GEnums.LevelScriptState",
            parameter_types=(),
        ),
        "get_levelScriptType": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "get_levelScriptType",
            0,
            "Beyond.GEnums.LevelScriptType",
            parameter_types=(),
        ),
        "UpdateWithinActiveArea": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "UpdateWithinActiveArea",
            0,
            "System.Boolean",
            parameter_types=(),
        ),
        "Setup": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "Setup",
            1,
            "System.Boolean",
            parameter_types=("Beyond.Gameplay.LevelScriptData",),
        ),
        "RegisterTriggerFromLevelScript": mapped_method(
            "Beyond.Gameplay.Core.LevelEventManager",
            "RegisterTriggerFromLevelScript",
            3,
            "System.Void",
        ),
        "SetAllTriggerActiveByPhase": mapped_method(
            "Beyond.Gameplay.Core.LevelScriptRuntime",
            "_SetAllTriggerActive",
            2,
            "System.Void",
            parameter_types=(
                "System.Boolean",
                "Beyond.Gameplay.Actions.TriggerActiveDuring",
            ),
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
            "SelfSceneInfoHandler",
            "StateNotifyHandler",
            "ManagerStateShort",
            "ManagerStateFull",
            "ManagerServerSyncLevelScript",
            "ContainerState",
            "ContainerServerSyncLevelScript",
            "UpdateState",
            "RuntimeServerSync",
            "ChallengeOnInteract",
            "UpdateRuntimeState",
            "UpdateWithinActiveArea",
            "Setup",
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
    self_scene_info_fields = find_type("Proto.SC_SELF_SCENE_INFO")
    level_script_info_fields = find_type("Proto.LEVEL_SCRIPT_INFO")
    runtime_types_va = int(metadata_summary["types"], 16)

    def field_runtime_type(type_rows: list[Any], field_name: str) -> str:
        if len(type_rows) != 1:
            return ""
        matches = [
            field
            for field in metadata.fields_for(type_rows[0])
            if metadata.string(field.name_index) == field_name
        ]
        if len(matches) != 1:
            return ""
        type_va = pe.u64_at_va(runtime_types_va + matches[0].type_index * 8)
        return il2cpp.runtime_type_name(pe, metadata, type_va)

    snapshot_level_scripts_runtime_type = field_runtime_type(
        self_scene_info_fields,
        "levelScripts_",
    )
    field_offsets: dict[str, int | None] = {}
    if len(challenge_fields) == 1:
        current = il2cpp.runtime_type_field_offsets(
            metadata, pe, metadata_summary, challenge_fields[0].index
        )
        field_offsets["challengeStartPoint.m_subGameId"] = current.get(
            "m_subGameId"
        )
    if len(subgame_fields) == 1:
        current = il2cpp.runtime_type_field_offsets(
            metadata, pe, metadata_summary, subgame_fields[0].index
        )
        field_offsets["subGameInstanceData.bindScriptId"] = current.get(
            "bindScriptId"
        )
    if len(state_notify_fields) == 1:
        current = il2cpp.runtime_type_field_offsets(
            metadata, pe, metadata_summary, state_notify_fields[0].index
        )
        for name in ("sceneNumId_", "scriptId_", "state_", "isComplete_"):
            field_offsets[f"stateNotify.{name}"] = current.get(name)
    if len(self_scene_info_fields) == 1:
        current = il2cpp.runtime_type_field_offsets(
            metadata, pe, metadata_summary, self_scene_info_fields[0].index
        )
        for name in ("sceneNumId_", "sceneId_", "levelScripts_"):
            field_offsets[f"selfSceneInfo.{name}"] = current.get(name)
    if len(level_script_info_fields) == 1:
        current = il2cpp.runtime_type_field_offsets(
            metadata, pe, metadata_summary, level_script_info_fields[0].index
        )
        for name in (
            "scriptId_",
            "state_",
            "properties_",
            "isDone_",
            "stage_",
            "triggerVolumeInfos_",
        ):
            field_offsets[f"levelScriptInfo.{name}"] = current.get(name)
    runtime_fields = find_type("Beyond.Gameplay.Core.LevelScriptRuntime")
    if len(runtime_fields) == 1:
        current = il2cpp.runtime_type_field_offsets(
            metadata, pe, metadata_summary, runtime_fields[0].index
        )
        field_offsets["levelScriptRuntime.m_manualStartTriggered"] = current.get(
            "m_manualStartTriggered"
        )
        for name in (
            "withinActiveArea",
            "activeShapeList",
            "activeShapeOutsideList",
        ):
            field_offsets[f"levelScriptRuntime.{name}"] = current.get(name)

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
            "ManagerStateShort",
            "ManagerStateFull",
            "ManagerServerSyncLevelScript",
            "ContainerState",
            "ContainerServerSyncLevelScript",
            "UpdateState",
            "set_state",
            "RuntimeServerSync",
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
                            "argumentOrigins": decoded_call.get(
                                "argumentOrigins"
                            )
                            or {},
                            "argumentContext": decoded_call.get(
                                "argumentContext"
                            )
                            or {},
                        })
                offset = data.find(b"\xe8", offset + 1)
    direct_callers = {
        key: sorted(rows.values(), key=lambda row: (row["type"], row["method"]))
        for key, rows in caller_rows.items()
    }
    def direct_caller_symbols(target_key: str) -> list[str]:
        return [
            f"{row.get('type')}.{row.get('method')}"
            for row in direct_callers.get(target_key) or []
        ]

    public_state_source_flow = {
        "snapshotMessageId": next(
            (row["id"] for row in sc if row["name"] == "ScSelfSceneInfo"),
            None,
        ),
        "incrementalMessageId": next(
            (
                row["id"]
                for row in sc
                if row["name"] == "ScSceneLevelScriptStateNotify"
            ),
            None,
        ),
        "snapshotLevelScriptsRuntimeType": snapshot_level_scripts_runtime_type,
        "managerStateShortDirectCallers": direct_caller_symbols(
            "ManagerStateShort"
        ),
        "managerStateFullDirectCallers": direct_caller_symbols(
            "ManagerStateFull"
        ),
        "managerServerSyncDirectCallers": direct_caller_symbols(
            "ManagerServerSyncLevelScript"
        ),
        "containerStateDirectCallers": direct_caller_symbols("ContainerState"),
        "updateStateDirectCallers": direct_caller_symbols("UpdateState"),
        "runtimeServerSyncDirectCallers": direct_caller_symbols(
            "RuntimeServerSync"
        ),
        "containerServerSyncDirectCallers": direct_caller_symbols(
            "ContainerServerSyncLevelScript"
        ),
        "publicStateSetterDirectCallers": direct_caller_symbols("set_state"),
        "publicStateSetterArguments": {
            f"{row.get('type')}.{row.get('method')}": [
                (site.get("argumentOrigins") or {}).get("rdx")
                for site in row.get("callSites") or []
            ]
            for row in direct_callers.get("set_state") or []
        },
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

    trigger_active_during_values = {
        row["name"]: row["id"]
        for row in il2cpp.enum_members(
            metadata,
            defaults,
            "Beyond.Gameplay.Actions.TriggerActiveDuring",
        )
    }
    runtime_state_values = {
        row["name"]: row["id"]
        for row in il2cpp.enum_members(
            metadata,
            defaults,
            "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState",
        )
    }
    level_script_type_values = {
        row["name"]: row["id"]
        for row in il2cpp.enum_members(
            metadata,
            defaults,
            "Beyond.GEnums.LevelScriptType",
        )
    }

    runtime_pointer = int(methods["UpdateRuntimeState"]["methodPointerVa"], 16)
    runtime_instructions = mapper.decode_x64_subset(
        pe.bytes_at_va(runtime_pointer, int(bodies["UpdateRuntimeState"]["scanBytes"])),
        runtime_pointer,
        stop_offset=int(bodies["UpdateRuntimeState"]["scanBytes"]),
    )

    def instruction_texts(start: int, end: int) -> list[str]:
        return [
            str(row.get("text") or "").lower()
            for row in runtime_instructions
            if start < int(row.get("offset") or 0) < end
        ]

    level_type_calls = calls_to("UpdateRuntimeState", "get_levelScriptType")
    active_area_calls = calls_to("UpdateRuntimeState", "UpdateWithinActiveArea")
    get_state_calls = calls_to("UpdateRuntimeState", "get_state")

    inactive_type_call = next(
        (call for call in level_type_calls if int(call["offset"]) < 1500), None
    )
    active_area_call = next(
        (call for call in active_area_calls if int(call["offset"]) < 1500), None
    )
    non_sub_state_call = next(
        (
            call for call in get_state_calls
            if inactive_type_call
            and active_area_call
            and int(inactive_type_call["offset"]) < int(call["offset"])
            < int(active_area_call["offset"])
        ),
        None,
    )
    sublevel_state_call = next(
        (
            call for call in get_state_calls
            if active_area_call
            and int(active_area_call["offset"]) < int(call["offset"]) < 1350
        ),
        None,
    )
    def selector_runtime_setters(value: int | None) -> list[dict[str, Any]]:
        if not isinstance(value, int):
            return []
        expected = {f"mov edx, 0x{value:x}", f"mov dl, 0x{value:x}"}
        return [
            row
            for row in update_setter_calls
            if str(
                ((((row.get("argumentContext") or {}).get("argRegisterWrites") or {})
                 .get("rdx") or {}).get("text") or "")
            ).lower()
            in expected
        ]

    preactive_setters = selector_runtime_setters(runtime_state_values.get("PreActive"))
    preactive_end_setters = selector_runtime_setters(
        runtime_state_values.get("PreActiveEndSendActiveState")
    )
    wait_active_setters = selector_runtime_setters(
        runtime_state_values.get("WaitForStateActive")
    )
    preactive_type_call = next(
        (
            call for call in level_type_calls
            if preactive_end_setters
            and int(call["offset"]) > int(preactive_end_setters[0]["offset"])
        ),
        None,
    )
    active_true_call = next(
        (call for call in update_active_calls if boolean_argument(call) is True),
        None,
    )
    inactive_type_offset = int(inactive_type_call["offset"]) if inactive_type_call else -1
    non_sub_state_offset = int(non_sub_state_call["offset"]) if non_sub_state_call else -1
    active_area_offset = int(active_area_call["offset"]) if active_area_call else -1
    sublevel_state_offset = int(sublevel_state_call["offset"]) if sublevel_state_call else -1
    preactive_setter_offset = int(preactive_setters[0]["offset"]) if preactive_setters else -1
    preactive_type_offset = int(preactive_type_call["offset"]) if preactive_type_call else -1
    active_true_offset = int(active_true_call["offset"]) if active_true_call else -1
    activation_selector_flow = {
        "levelScriptTypeValues": level_script_type_values,
        "enabledStateValue": 2,
        "activeStateValue": 3,
        "preActiveStateValue": runtime_state_values.get("PreActive"),
        "preActiveEndSendActiveStateValue": runtime_state_values.get(
            "PreActiveEndSendActiveState"
        ),
        "waitForStateActiveValue": runtime_state_values.get("WaitForStateActive"),
        "inactiveLevelScriptTypeCallOffset": inactive_type_offset,
        "nonSubLevelEnabledStateCallOffset": non_sub_state_offset,
        "activeAreaGateCallOffset": active_area_offset,
        "subLevelActiveStateCallOffset": sublevel_state_offset,
        "preActiveSetterCallOffset": preactive_setter_offset,
        "preActiveLevelScriptTypeCallOffset": preactive_type_offset,
        "activeTrueRequestCallOffset": active_true_offset,
        "waitForStateActiveSetterOffsets": [
            int(call["offset"]) for call in wait_active_setters
        ],
        "nonSubLevelRequiresEnabledAndActiveArea": (
            "cmp eax, 0x4" in instruction_texts(inactive_type_offset, non_sub_state_offset)
            and "cmp eax, 0x2" in instruction_texts(non_sub_state_offset, active_area_offset)
            and "test al, al" in instruction_texts(active_area_offset, preactive_setter_offset)
        ),
        "subLevelRequiresPublicActive": (
            "cmp eax, 0x3" in instruction_texts(
                sublevel_state_offset, preactive_setter_offset
            )
        ),
        "nonSubLevelSendsActiveTrueAfterPreActive": (
            preactive_end_setters
            and preactive_type_offset < active_true_offset
            and level_script_type_values.get("SubLevelScript") == 4
            and "cmp eax, 0x4" in instruction_texts(
                preactive_type_offset, active_true_offset
            )
        ),
        "subLevelSkipsActiveTrueRequest": (
            len(wait_active_setters) == 2
            and active_true_offset < int(wait_active_setters[0]["offset"])
            < int(wait_active_setters[1]["offset"])
        ),
    }
    active_area_pointer = int(methods["UpdateWithinActiveArea"]["methodPointerVa"], 16)
    active_area_instructions = mapper.decode_x64_subset(
        pe.bytes_at_va(
            active_area_pointer,
            int(bodies["UpdateWithinActiveArea"]["scanBytes"]),
        ),
        active_area_pointer,
        stop_offset=int(bodies["UpdateWithinActiveArea"]["scanBytes"]),
    )

    def area_rows(text: str) -> list[dict[str, Any]]:
        return [
            row
            for row in active_area_instructions
            if str(row.get("text") or "").lower() == text.lower()
        ]

    def area_offset(text: str, rank: int = 0) -> int:
        rows = area_rows(text)
        return int(rows[rank]["offset"]) if len(rows) > rank else -1

    active_list_read_offsets = sorted({
        int(row["offset"])
        for row in active_area_instructions
        if "[rsi+0x70]" in str(row.get("text") or "").lower()
    })
    outside_list_read_offsets = sorted({
        int(row["offset"])
        for row in active_area_instructions
        if "[rsi+0x78]" in str(row.get("text") or "").lower()
    })
    within_access_offsets = sorted({
        int(row["offset"])
        for row in active_area_instructions
        if "[rsi+0x68]" in str(row.get("text") or "").lower()
    })
    within_false_offsets = [
        int(row["offset"])
        for row in area_rows("mov [rsi+0x68], 0x0")
    ]
    outside_hit_clear_offset = within_false_offsets[0] if within_false_offsets else -1
    within_true_offset = area_offset("mov [rsi+0x68], 0x1")
    within_return_offset = area_offset("movzx eax, [rsi+0x68]")
    active_count_setter_offset = area_offset("setg al")
    empty_active_branch_offset = area_offset(
        f"jcc 0x{active_area_pointer + within_true_offset:x}"
    )
    active_shape_test_offset = area_offset("call 0x1821e6930")
    active_shape_hit_branch_offset = area_offset(
        f"jcc 0x{active_area_pointer + within_true_offset:x}",
        1,
    )
    missing_outside_branch_offset = area_offset(
        f"jcc 0x{active_area_pointer + within_return_offset:x}"
    )
    outside_shape_test_offset = area_offset("call 0x1834c3790")
    outside_shape_miss_branch_offset = area_offset(
        f"jcc 0x{active_area_pointer + within_return_offset:x}",
        1,
    )

    def area_bytes(offset: int) -> str:
        row = next(
            (
                item
                for item in active_area_instructions
                if int(item.get("offset") or -1) == offset
            ),
            {},
        )
        return str(row.get("bytes") or "").lower()

    active_area_flow = {
        "activeShapeListFieldOffset": field_offsets.get(
            "levelScriptRuntime.activeShapeList"
        ),
        "activeShapeOutsideListFieldOffset": field_offsets.get(
            "levelScriptRuntime.activeShapeOutsideList"
        ),
        "withinActiveAreaFieldOffset": field_offsets.get(
            "levelScriptRuntime.withinActiveArea"
        ),
        "activeShapeListReadOffsets": active_list_read_offsets,
        "activeShapeOutsideListReadOffsets": outside_list_read_offsets,
        "withinActiveAreaAccessOffsets": within_access_offsets,
        "activeListPositiveCountSetterOffset": active_count_setter_offset,
        "emptyActiveListBranchOffset": empty_active_branch_offset,
        "activeShapeTestCallOffset": active_shape_test_offset,
        "activeShapeHitBranchOffset": active_shape_hit_branch_offset,
        "missingOutsideListBranchOffset": missing_outside_branch_offset,
        "outsideShapeTestCallOffset": outside_shape_test_offset,
        "outsideShapeMissBranchOffset": outside_shape_miss_branch_offset,
        "withinFalseSetterOffsets": within_false_offsets,
        "outsideShapeHitClearOffset": outside_hit_clear_offset,
        "withinTrueSetterOffset": within_true_offset,
        "withinReturnOffset": within_return_offset,
        "emptyActiveListSetsWithinTrue": (
            area_bytes(empty_active_branch_offset).startswith("0f 84")
            and active_count_setter_offset < empty_active_branch_offset
        ),
        "activeShapeHitSetsWithinTrue": (
            area_bytes(active_shape_hit_branch_offset).startswith("0f 85")
            and active_shape_test_offset < active_shape_hit_branch_offset
        ),
        "missingOutsideListPreservesPriorWithin": (
            area_bytes(missing_outside_branch_offset).startswith("0f 84")
            and missing_outside_branch_offset < outside_shape_test_offset
        ),
        "outsideShapeMissPreservesPriorWithin": (
            area_bytes(outside_shape_miss_branch_offset).startswith("0f 84")
            and outside_shape_test_offset < outside_shape_miss_branch_offset
        ),
        "outsideShapeHitClearsWithin": (
            outside_shape_miss_branch_offset < outside_hit_clear_offset
            < within_return_offset
            and within_false_offsets[-1] < within_true_offset < within_return_offset
        ),
    }
    setup_register_calls = calls_to("Setup", "RegisterTriggerFromLevelScript")
    phase_calls = calls_to("UpdateRuntimeState", "SetAllTriggerActiveByPhase")

    def phase_call_arguments(call: dict[str, Any]) -> dict[str, Any]:
        writes = (
            (call.get("argumentContext") or {}).get("argRegisterWrites") or {}
        )
        active_text = str((writes.get("rdx") or {}).get("text") or "").lower()
        phase_text = str((writes.get("r8") or {}).get("text") or "").lower()
        active: bool | None = None
        if active_text in {"mov dl, 0x1", "mov edx, 0x1"}:
            active = True
        elif active_text in {"xor edx, edx", "xor rdx, rdx"}:
            active = False
        phase: int | None = None
        if phase_text in {"xor r8d, r8d", "xor r8, r8"}:
            phase = 0
        else:
            match = re.fullmatch(r"mov r8d, 0x([0-9a-f]+)", phase_text)
            if match:
                phase = int(match.group(1), 16)
        return {
            "active": active,
            "triggerActiveDuring": phase,
            "callOffset": call.get("offset"),
        }

    active_phase_value = trigger_active_during_values.get("Active")
    active_phase_enables = [
        row
        for row in (phase_call_arguments(call) for call in phase_calls)
        if row["active"] is True
        and row["triggerActiveDuring"] == active_phase_value
    ]

    active_begin_setters = selector_runtime_setters(
        runtime_state_values.get("ActiveBegin")
    )
    wait_newly_setters = selector_runtime_setters(
        runtime_state_values.get("WaitForSubEntityInitNewly")
    )
    first_active_enable = active_phase_enables[0] if active_phase_enables else {}
    active_receiver_flow = {
        "triggerActiveDuringValues": trigger_active_during_values,
        "setupRegisterTriggerCallCount": len(setup_register_calls),
        "setupRegisterTriggerCallOffsets": [
            row.get("offset") for row in setup_register_calls
        ],
        "activePhaseEnableArguments": [
            {"active": row["active"], "triggerActiveDuring": row["triggerActiveDuring"]}
            for row in active_phase_enables
        ],
        "activePhaseEnableCallOffsets": [
            row.get("callOffset") for row in active_phase_enables
        ],
        "activeBeginStateValue": runtime_state_values.get("ActiveBegin"),
        "waitForSubEntityInitNewlyStateValue": runtime_state_values.get(
            "WaitForSubEntityInitNewly"
        ),
        "activeBeginSetterOffsets": [
            row.get("offset") for row in active_begin_setters
        ],
        "waitForSubEntityInitNewlySetterOffsets": [
            row.get("offset") for row in wait_newly_setters
        ],
        "activePhaseEnableBetweenStateSetters": (
            len(active_begin_setters) == 1
            and len(wait_newly_setters) == 1
            and bool(first_active_enable)
            and int(active_begin_setters[0]["offset"])
            < int(first_active_enable["callOffset"])
            < int(wait_newly_setters[0]["offset"])
        ),
    }

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
        "ScSelfSceneInfo": sc_by_name.get("ScSelfSceneInfo"),
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
        "selfSceneInfo": message_schema(
            metadata, defaults, "Proto.SC_SELF_SCENE_INFO"
        ),
        "levelScriptInfo": message_schema(
            metadata, defaults, "Proto.LEVEL_SCRIPT_INFO"
        ),
    }
    observation = {
        "messageIds": message_ids,
        "messageSchemas": message_schemas,
        "fieldOffsets": field_offsets,
        "methods": methods,
        "publicStateFlow": public_state_flow,
        "publicStateSourceFlow": public_state_source_flow,
        "subGameInteractionFlow": subgame_interaction_flow,
        "manualStartDirectCallers": manual_start_callers,
        "directCallers": direct_callers,
        "clientRequestFlow": client_request_flow,
        "activeReceiverFlow": active_receiver_flow,
        "activationSelectorFlow": activation_selector_flow,
        "activeAreaFlow": active_area_flow,
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
        "schema": "levelScriptActivationControl.v6",
        "classification": "server_state_subgame_and_runtime_request_paths",
        "discoveryPattern": {
            "methodSelection": "exact metadata type, name, signature, and return type",
            "messageSelection": "exact current enum IDs and protobuf fields",
            "fieldSelection": "MetadataRegistration instance offsets",
            "callers": (
                "complete current executable-code direct E8 caller census for "
                "both public-state application chains, the public state setter, "
                "ManualStart, and both public/runtime active/start sender methods"
            ),
            "serializedObjectInputs": [
                "SubGameInstanceData.id",
                "SubGameInstanceData.bindScriptId",
            ],
            "receiverPhaseInput": (
                "LevelScript action-header triggerActiveDuring from each original "
                "serialized object"
            ),
            "activationSelectorInput": (
                "LevelScriptData.levelScriptType from each exact validated LevelData "
                "brief dictionary; no per-script selector table"
            ),
        },
        **observation,
        "finding": (
            "The server supplies public LevelScript state through exactly two current "
            "AOT entry handlers: SC_SELF_SCENE_INFO carries repeated LEVEL_SCRIPT_INFO "
            "snapshot rows into LevelScriptRuntime.ServerSync, while "
            "SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY applies an incremental "
            "scene/script/state tuple through LevelScriptRuntime.UpdateState. The full "
            "direct-call census closes every later application layer and separates the "
            "two zero-valued initialization writes from those two server-derived state "
            "parameters. Separately, the only direct ManualStart "
            "callers in the current AOT client are ManualStartLevelScript.Execute and "
            "InteractiveLogicChallengeStartPoint._OnInteract; the interaction path "
            "resolves the typed SubGame row by id, reads bindScriptId, looks up that "
            "LevelScript, and calls ManualStart. The same generic runtime records the "
            "manual-start flag, enters PreStart, emits the typed client start request, "
            "and enters PreStartActionRunning. Independently, Setup registers the "
            "serialized LevelScript trigger graph, and the ActiveBegin runtime path "
            "enables the TriggerActiveDuring.Active group before advancing to the "
            "next activation state. The Inactive runtime path treats SubLevelScript "
            "separately: every other LevelScript type enters PreActive from public "
            "Enabled only after UpdateWithinActiveArea succeeds, then emits the typed "
            "active=true request after pre-active actions; SubLevelScript instead waits "
            "for public Active and skips that client request. UpdateWithinActiveArea "
            "uses a positive-count active list as the enter test, preserves prior state "
            "when no outside list or no outside hit exists, and clears the flag on an "
            "outside-list hit."
        ),
        "boundary": (
            "An exact SubGame id/bindScriptId row therefore proves an interaction "
            "ManualStart carrier for that bound script. Neither server state carrier "
            "has a mission, quest, Story, or branch-reason field, and neither path "
            "proves which mission owns Story "
            "playback, which server branch selected a state, or any cross-Story order. "
            "The public network sender methods have zero direct current-AOT callers; "
            "indirect/IFix/server selection remains outside this evidence. An Active-"
            "phase receiver proves availability after public activation, not the "
            "producer of that activation or that the event fired. For non-SubLevelScript "
            "types the client request producer and server-supplied public-state carriers "
            "are now exact, but the server-side rule choosing Enabled, player position, "
            "runtime list construction, and the spatial gate outcome remain separate "
            "questions."
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
                tags[il2cpp.normalized_field_name(name)] = {
                    "constantName": name,
                    "tag": il2cpp.constant_value(metadata, defaults, field),
                }
            elif name.endswith("_"):
                storage[il2cpp.normalized_field_name(name)] = {
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
    name = il2cpp.normalized_field_name(field_name)
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
    mapper = il2cpp.load_native_mapper(mapper_path)
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
                runtime_name_cache[type_index] = il2cpp.runtime_type_name(
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
        il2cpp.normalized_field_name(row["name"]): row
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
        il2cpp.normalized_field_name(row["name"]): row
        for row in server_registry
    }
    candidates: list[dict[str, Any]] = []
    for type_def in metadata.types:
        type_name = metadata.type_full_name(type_def)
        if not type_name.startswith("Proto.SC_"):
            continue
        storage_names = {
            il2cpp.normalized_field_name(metadata.string(field.name_index))
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
        registry_key = il2cpp.normalized_field_name(type_name.removeprefix("Proto."))
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


def validate_levelscript_task_lifecycle_observation(
    observation: dict[str, Any],
    *,
    source_file: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed on the reusable LevelScript task-state pattern.

    The validator deliberately checks structural discoveries rather than a
    catalog of scene, script, task, or dialog ids.  That keeps task recovery
    build-wide and makes current-binary drift actionable.
    """
    failures: list[dict[str, Any]] = []

    def check(gate: str, expected: Any, actual: Any) -> None:
        if actual == expected:
            return
        failures.append({
            "validator": "levelscript_task_lifecycle_contract",
            "gate": gate,
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    check(
        "scriptTaskStateEnum",
        {"None": 0, "Processing": 1, "Completed": 2},
        observation.get("scriptTaskStateEnum"),
    )
    check(
        "levelScriptTaskTypeEnum",
        {"None": 0, "Main": 1, "Extra": 2, "Fail": 3, "Custom": 4},
        observation.get("levelScriptTaskTypeEnum"),
    )
    check(
        "serverStateApplicationChain",
        [
            "Beyond.Gameplay.Core.LevelScriptManager.UpdateLevelScriptTaskState",
            "Beyond.Gameplay.Core.LevelScriptRuntime.UpdateTaskState",
            (
                "Beyond.Gameplay.Core.LevelScriptRuntime+"
                "ScriptTaskRuntime.UpdateTaskState"
            ),
        ],
        observation.get("serverStateApplicationChain"),
    )
    check(
        "stateArgumentForwarding",
        True,
        observation.get("stateArgumentForwarding"),
    )
    condition_calls = int(observation.get("processingConditionCallCount") or 0)
    if condition_calls < 1:
        check("processingConditionCallCount", ">=1", condition_calls)
    check(
        "conditionProcessingOperations",
        [
            "Beyond.Gameplay.GameCondition+ResultChange..ctor",
            "System.Delegate.Combine",
            "Beyond.Gameplay.GameCondition.Activate",
            "Beyond.Gameplay.GameCondition.BindingEvent",
        ],
        observation.get("conditionProcessingOperations"),
    )
    check(
        "conditionProgressSender",
        "Beyond.Gameplay.GameplayNetwork.SendLevelScriptUpdateTaskProgress",
        observation.get("conditionProgressSender"),
    )
    check(
        "conditionIdentityFieldReads",
        ["levelScriptPtr", "levelNum", "taskKey", "conditionId"],
        observation.get("conditionIdentityFieldReads"),
    )
    return {
        "status": "validation_failed" if failures else "validated",
        "validator": "levelscript_task_lifecycle_contract",
        "failures": failures,
    }


def levelscript_task_lifecycle_contract(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    helper: Any,
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
    metadata_path: Path = DEFAULT_METADATA,
) -> dict[str, Any]:
    """Recover the generic server-selected LevelScript task lifecycle.

    Types and methods are discovered from metadata field/method shapes.  The
    resulting contract contains no scene-, mission-, script-, task-, or dialog-
    specific ids.
    """
    mapper = il2cpp.load_native_mapper(mapper_path)
    pe = mapper.PeImage(gameassembly_path)
    metadata_registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if metadata_registration is None:
        raise RuntimeError(
            "validator=levelscript_task_lifecycle_contract "
            "gate=metadataRegistration expected=present actual=missing "
            f"source={gameassembly_path}"
        )
    metadata_summary = mapper.metadata_registration_summary(
        pe, metadata_registration
    )
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
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }

    def type_methods(type_def: Any) -> dict[str, list[dict[str, Any]]]:
        rows: dict[str, list[dict[str, Any]]] = {}
        for method in metadata.methods_for(type_def):
            row = helper.method_row(metadata, method)
            rows.setdefault(str(row["name"]), []).append(row)
        return rows

    def discover_type(
        *,
        required_fields: set[str],
        required_methods: set[str],
        gate: str,
    ) -> Any:
        candidates = []
        for type_def in metadata.types:
            fields = {
                metadata.string(field.name_index)
                for field in metadata.fields_for(type_def)
            }
            if not required_fields <= fields:
                continue
            methods = set(type_methods(type_def))
            if required_methods <= methods:
                candidates.append(type_def)
        if len(candidates) != 1:
            raise RuntimeError(
                "validator=levelscript_task_lifecycle_contract "
                f"gate={gate} expected=1 actual="
                f"{[metadata.type_full_name(row) for row in candidates]!r} "
                f"source={gameassembly_path} hashes={source_hashes!r}"
            )
        return candidates[0]

    task_runtime = discover_type(
        required_fields={
            "m_state",
            "scriptPtr",
            "taskKey",
            "taskType",
            "canBeTracked",
            "needManualCheck",
            "conditionDict",
        },
        required_methods={
            "UpdateTaskState",
            "_OnTaskStateProcessing",
            "_OnTaskStateCompleted",
            "_OnTaskStateNone",
        },
        gate="uniqueScriptTaskRuntimeShape",
    )
    task_condition = discover_type(
        required_fields={
            "levelScriptPtr",
            "levelNum",
            "taskKey",
            "conditionId",
            "condition",
            "isCompleted",
        },
        required_methods={
            "OnTaskStateProcessing",
            "_OnConditionResultChanged",
            "OnTaskStateNone",
            "OnTaskStateCompleted",
        },
        gate="uniqueTaskConditionShape",
    )

    def unique_method(type_def: Any, name: str) -> dict[str, Any]:
        rows = type_methods(type_def).get(name) or []
        if len(rows) != 1:
            raise RuntimeError(
                "validator=levelscript_task_lifecycle_contract "
                f"gate=uniqueMethod type={metadata.type_full_name(type_def)} "
                f"method={name} expected=1 actual={len(rows)} "
                f"source={gameassembly_path} hashes={source_hashes!r}"
            )
        return full_method_mapper_row(metadata, helper, int(rows[0]["index"]))

    def map_method(row: dict[str, Any], limit: int = 8192) -> dict[str, Any]:
        image_range = ranges.get(str(row["image"]))
        pointers = pointers_by_image.get(str(row["image"])) or []
        if not image_range:
            raise RuntimeError(f"missing method range for {row['image']}")
        slot = int(row["methodIndex"]) - int(image_range["methodStart"])
        if not 0 <= slot < len(pointers) or not pointers[slot]:
            raise RuntimeError(
                f"no native pointer for {row['type']}.{row['method']}"
            )
        pointer = int(pointers[slot])
        scan_size, next_pointer = mapper.estimate_scan_size(
            pointer, sorted_pointers, limit
        )
        body_bytes = pe.bytes_at_va(pointer, scan_size)
        body = mapper.build_method_body_summary(
            row,
            body_bytes,
            pointer,
            method_by_pointer,
            pe=pe,
            max_instructions=2400,
        )
        return {
            "symbol": f"{row['type']}.{row['method']}",
            "token": row["token"],
            "methodIndex": row["methodIndex"],
            "va": f"0x{pointer:x}",
            "rva": f"0x{pe.file_offset_for_va(pointer)[2]:x}",
            "scanBytes": scan_size,
            "nextMethodPointerVa": (
                f"0x{next_pointer:x}" if next_pointer else None
            ),
            "bodySha256": hashlib.sha256(body_bytes).hexdigest(),
            "bodySummary": body,
            "decodedInstructions": mapper.decode_x64_subset(
                body_bytes, pointer, stop_offset=scan_size
            ),
        }

    def call_rows(mapped: dict[str, Any]) -> list[dict[str, Any]]:
        return list((mapped.get("bodySummary") or {}).get("calls") or [])

    def calls_to(
        mapped: dict[str, Any], type_name: str, method_name: str
    ) -> list[dict[str, Any]]:
        return [
            call
            for call in call_rows(mapped)
            if any(
                target.get("type") == type_name
                and target.get("method") == method_name
                for target in call.get("resolved") or []
            )
        ]

    task_runtime_name = metadata.type_full_name(task_runtime)
    task_condition_name = metadata.type_full_name(task_condition)
    inner_update = map_method(unique_method(task_runtime, "UpdateTaskState"))
    processing = map_method(unique_method(task_runtime, "_OnTaskStateProcessing"))
    condition_processing = map_method(
        unique_method(task_condition, "OnTaskStateProcessing")
    )
    result_changed = map_method(
        unique_method(task_condition, "_OnConditionResultChanged")
    )

    # Discover the typed server handler from its protobuf parameter, then walk
    # each exact native call target rather than pinning method indices.
    handler_candidates: list[dict[str, Any]] = []
    for type_def in metadata.types:
        for method in metadata.methods_for(type_def):
            row = helper.method_row(metadata, method)
            parameter_types = [
                str(param.get("typeName") or "").split("+", 1)[0]
                for param in row.get("parameterDetails") or []
            ]
            if (
                "Proto.SC_SCENE_LEVEL_SCRIPT_TASK_STATE_UPDATE"
                in parameter_types
                and str(row.get("name") or "").startswith(("Handle_", "_Handle_"))
                and not metadata.type_full_name(type_def).startswith("Proto.")
            ):
                handler_candidates.append(
                    full_method_mapper_row(metadata, helper, int(row["index"]))
                )
    if len(handler_candidates) != 1:
        handler_symbols = [
            f"{row['type']}.{row['method']}" for row in handler_candidates
        ]
        raise RuntimeError(
            "validator=levelscript_task_lifecycle_contract "
            "gate=uniqueTypedStateHandler expected=1 actual="
            f"{handler_symbols!r} "
            f"source={gameassembly_path} hashes={source_hashes!r}"
        )
    handler = map_method(handler_candidates[0])
    handler_calls = [
        (call, target)
        for call in call_rows(handler)
        for target in call.get("resolved") or []
        if target.get("method") == "UpdateLevelScriptTaskState"
    ]
    if len(handler_calls) != 1:
        raise RuntimeError(
            "validator=levelscript_task_lifecycle_contract "
            "gate=handlerUpdateCall expected=1 actual="
            f"{len(handler_calls)} source={gameassembly_path} hashes={source_hashes!r}"
        )
    manager_target = handler_calls[0][1]
    manager_update = map_method(
        full_method_mapper_row(
            metadata, helper, int(manager_target["methodIndex"])
        )
    )
    outer_calls = [
        (call, target)
        for call in call_rows(manager_update)
        for target in call.get("resolved") or []
        if target.get("method") == "UpdateTaskState"
        and target.get("type") == "Beyond.Gameplay.Core.LevelScriptRuntime"
    ]
    if len(outer_calls) != 1:
        raise RuntimeError(
            "validator=levelscript_task_lifecycle_contract "
            "gate=managerRuntimeUpdateCall expected=1 actual="
            f"{len(outer_calls)} source={gameassembly_path} hashes={source_hashes!r}"
        )
    outer_update = map_method(
        full_method_mapper_row(
            metadata, helper, int(outer_calls[0][1]["methodIndex"])
        )
    )
    inner_calls = calls_to(outer_update, task_runtime_name, "UpdateTaskState")

    # The task-condition processing body is hot/cold split in the current
    # binary. Discover its outbound cold block from the native jump, then
    # resolve its calls through the current method-pointer index.
    condition_pointer = int(condition_processing["va"], 16)
    condition_end = condition_pointer + int(condition_processing["scanBytes"])
    cold_targets: list[int] = []
    for instruction in condition_processing["decodedInstructions"]:
        text = str(instruction.get("text") or "")
        match = re.fullmatch(r"jmp 0x([0-9a-f]+)", text, re.I)
        if not match:
            continue
        target = int(match.group(1), 16)
        if not condition_pointer <= target < condition_end:
            cold_targets.append(target)
    cold_operations: list[str] = []
    cold_blocks: list[dict[str, Any]] = []
    for target in sorted(set(cold_targets)):
        block_bytes = pe.bytes_at_va(target, 224)
        instructions = mapper.decode_x64_subset(
            block_bytes, target, stop_offset=len(block_bytes)
        )
        operations: list[str] = []
        for instruction in instructions:
            match = re.fullmatch(
                r"call 0x([0-9a-f]+)",
                str(instruction.get("text") or ""),
                re.I,
            )
            if not match:
                continue
            call_target = int(match.group(1), 16)
            for resolved in method_by_pointer.get(call_target, []):
                symbol = f"{resolved.get('type')}.{resolved.get('method')}"
                operations.append(symbol)
                cold_operations.append(symbol)
        cold_blocks.append({
            "va": f"0x{target:x}",
            "scanBytes": len(block_bytes),
            "bodySha256": hashlib.sha256(block_bytes).hexdigest(),
            "resolvedCalls": operations,
        })

    processing_calls = calls_to(
        processing, task_condition_name, "OnTaskStateProcessing"
    )
    progress_calls = calls_to(
        result_changed,
        "Beyond.Gameplay.GameplayNetwork",
        "SendLevelScriptUpdateTaskProgress",
    )
    condition_offsets = il2cpp.runtime_type_field_offsets(
        metadata, pe, metadata_summary, task_condition.index
    )
    identity_field_names = [
        name
        for name in ("levelScriptPtr", "levelNum", "taskKey", "conditionId")
        if any(
            access.get("origin") == f"this+0x{condition_offsets[name]:x}"
            for access in (result_changed.get("bodySummary") or {}).get(
                "fieldAccesses"
            ) or []
        )
    ]
    required_condition_operations = [
        "Beyond.Gameplay.GameCondition+ResultChange..ctor",
        "System.Delegate.Combine",
        "Beyond.Gameplay.GameCondition.Activate",
        "Beyond.Gameplay.GameCondition.BindingEvent",
    ]
    observed_operations = [
        symbol for symbol in required_condition_operations if symbol in cold_operations
    ]
    state_forwarding = (
        len(inner_calls) == 1
        and (outer_calls[0][0].get("argumentOrigins") or {}).get("r8")
        == "param:taskState"
        and (inner_calls[0].get("argumentOrigins") or {}).get("rdx")
        == "param:newState"
    )
    observation = {
        "scriptTaskStateEnum": {
            str(row["name"]): int(row["id"])
            for row in il2cpp.enum_members(
                metadata, defaults, "Beyond.GEnums.ScriptTaskState"
            )
        },
        "levelScriptTaskTypeEnum": {
            str(row["name"]): int(row["id"])
            for row in il2cpp.enum_members(
                metadata, defaults, "Beyond.Gameplay.LevelScriptTaskType"
            )
        },
        "serverStateApplicationChain": [
            manager_update["symbol"],
            outer_update["symbol"],
            inner_update["symbol"],
        ],
        "stateArgumentForwarding": state_forwarding,
        "processingConditionCallCount": len(processing_calls),
        "conditionProcessingOperations": observed_operations,
        "conditionProgressSender": (
            "Beyond.Gameplay.GameplayNetwork.SendLevelScriptUpdateTaskProgress"
            if len(progress_calls) == 1 else None
        ),
        "conditionIdentityFieldReads": identity_field_names,
    }
    validation = validate_levelscript_task_lifecycle_observation(
        observation,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
    )
    public_methods = {
        name: {
            key: value
            for key, value in mapped.items()
            if key not in {"bodySummary", "decodedInstructions"}
        }
        for name, mapped in (
            ("serverStateHandler", handler),
            ("managerUpdate", manager_update),
            ("runtimeUpdate", outer_update),
            ("taskRuntimeUpdate", inner_update),
            ("taskStateProcessing", processing),
            ("conditionStateProcessing", condition_processing),
            ("conditionResultChanged", result_changed),
        )
    }
    return {
        "schema": "levelScriptTaskLifecycle.v1",
        "classification": "generic_server_selected_task_condition_lifecycle",
        "discoveryPattern": {
            "taskRuntime": "unique metadata field+method shape",
            "taskCondition": "unique metadata field+method shape",
            "serverHandler": (
                "unique current method accepting the typed task-state protobuf"
            ),
            "application": "resolved native call chain and parameter provenance",
            "conditionActivation": (
                "resolved Processing handler calls plus its discovered hot/cold block"
            ),
        },
        "taskRuntimeType": task_runtime_name,
        "taskConditionType": task_condition_name,
        "scriptTaskStateEnum": observation["scriptTaskStateEnum"],
        "levelScriptTaskTypeEnum": observation["levelScriptTaskTypeEnum"],
        "methods": public_methods,
        "serverStateApplicationChain": observation[
            "serverStateApplicationChain"
        ],
        "stateArgumentForwarding": state_forwarding,
        "processingConditionCallCount": len(processing_calls),
        "conditionProcessingOperations": observed_operations,
        "conditionProcessingColdBlocks": cold_blocks,
        "conditionProgressSender": observation["conditionProgressSender"],
        "conditionIdentityFieldReads": identity_field_names,
        "finding": (
            "The typed server task-state packet is forwarded through the generic "
            "LevelScript manager and runtime to one ScriptTaskRuntime. Its Processing "
            "handler walks task conditions; each condition installs a result-change "
            "delegate, activates and binds its authored GameCondition, and reports "
            "changes with the exact level/script/task/condition identity."
        ),
        "boundary": (
            "This proves the reusable client task-condition lifecycle after the server "
            "selects a scene/script/task identity. It does not expose server selection "
            "policy, attach the task to a mission, choose a Story branch, or establish "
            "scene-file order. IFix replacement bodies and server-only logic remain "
            "outside the static bound."
        ),
        "relatedOriginalFiles": [
            {
                "kind": "original_game_binary",
                "sourceFile": str(gameassembly_path.resolve()),
                "sha256": source_hashes["gameAssemblySha256"],
            },
            {
                "kind": "original_game_metadata",
                "sourceFile": str(metadata_path.resolve()),
                "sha256": source_hashes["metadataSha256"],
            },
        ],
        "validation": validation,
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


def conditional_branch_kind(row: dict[str, Any]) -> str:
    """Return the exact equality branch kind, including compact decoder jcc rows."""
    text = str(row.get("text") or "").lower()
    mnemonic = text.split(" ", 1)[0]
    if mnemonic in {"je", "jne"}:
        return mnemonic
    raw = str(row.get("bytes") or "").lower().split()
    if raw[:2] == ["0f", "84"] or raw[:1] == ["74"]:
        return "je"
    if raw[:2] == ["0f", "85"] or raw[:1] == ["75"]:
        return "jne"
    return ""


def direct_branch_target_offset(
    row: dict[str, Any],
    method_va: int,
) -> int | None:
    """Resolve a decoded direct branch target to a method-relative offset."""
    target_text = str(row.get("targetVa") or "")
    if not target_text:
        match = re.search(r"\b0x[0-9a-f]+\b", str(row.get("text") or ""), re.I)
        target_text = match.group(0) if match else ""
    return (
        int(target_text, 16) - method_va
        if target_text.startswith("0x")
        else None
    )


def constrained_lifecycle_routes(
    instructions: list[dict[str, Any]],
    predicates: list[dict[str, Any]],
    lifecycle_calls: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    *,
    method_va: int,
) -> list[dict[str, Any]]:
    """Follow native CFG edges under discovered typed predicate assignments.

    Each predicate names a field, the value for which its preceding comparison
    is equal/zero, and the exact conditional-branch offset. All other native
    conditions remain possible. The solver therefore supports enum and boolean
    carriers without encoding message IDs, addresses, constants, or call names.
    """
    ordered = sorted(
        instructions,
        key=lambda row: int(row.get("offset") or 0),
    )
    by_offset = {int(row.get("offset") or 0): row for row in ordered}
    offsets = sorted(by_offset)
    next_offset = {
        offset: offsets[index + 1]
        for index, offset in enumerate(offsets[:-1])
    }
    predicate_by_offset = {
        int(row["branchOffset"]): row
        for row in predicates
        if isinstance(row.get("branchOffset"), int)
    }

    calls_by_offset: dict[int, list[dict[str, Any]]] = {}
    for call in lifecycle_calls:
        calls_by_offset.setdefault(int(call.get("callOffset") or 0), []).append(call)

    routes: list[dict[str, Any]] = []
    for scenario in scenarios:
        values = scenario.get("values") or {}
        pending = [offsets[0]] if offsets else []
        visited: set[int] = set()
        reached_calls: dict[tuple[str, int], dict[str, Any]] = {}
        while pending:
            offset = pending.pop()
            if offset in visited or offset not in by_offset:
                continue
            visited.add(offset)
            for call in calls_by_offset.get(offset, []):
                reached_calls[(str(call.get("method") or ""), offset)] = call
            instruction = by_offset[offset]
            text = str(instruction.get("text") or "").lower()
            following = next_offset.get(offset)
            target_offset = direct_branch_target_offset(instruction, method_va)
            successors: list[int] = []
            if text.startswith("jmp "):
                if target_offset in by_offset:
                    successors.append(target_offset)
            elif text.startswith(("ret", "int3")):
                pass
            elif re.match(r"^j[a-z]+\b", text):
                predicate = predicate_by_offset.get(offset)
                if predicate is None:
                    if following is not None:
                        successors.append(following)
                    if target_offset in by_offset:
                        successors.append(target_offset)
                else:
                    field_name = str(predicate.get("field") or "")
                    equal = values.get(field_name) == predicate.get("equalValue")
                    taken = (
                        equal
                        if conditional_branch_kind(instruction) == "je"
                        else not equal
                    )
                    selected = target_offset if taken else following
                    if selected in by_offset:
                        successors.append(selected)
            elif following is not None:
                successors.append(following)
            pending.extend(reversed(successors))
        calls = sorted(
            reached_calls.values(),
            key=lambda row: (int(row.get("callOffset") or 0), str(row.get("method") or "")),
        )
        routes.append({
            **{key: value for key, value in scenario.items() if key != "values"},
            "values": values,
            "reachableLifecycleCalls": [
                {
                    "method": call.get("method"),
                    "symbol": call.get("symbol"),
                    "token": call.get("token"),
                    "callOffset": call.get("callOffset"),
                    "samePacketIdentity": call.get("samePacketIdentity"),
                }
                for call in calls
            ],
        })
    return routes


def constrained_enum_lifecycle_routes(
    instructions: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    lifecycle_calls: list[dict[str, Any]],
    enum_values: list[dict[str, Any]],
    *,
    method_va: int,
) -> list[dict[str, Any]]:
    """Constrain a discovered enum field and project reachable lifecycle calls."""
    ordered = sorted(
        instructions,
        key=lambda row: int(row.get("offset") or 0),
    )
    predicates: list[dict[str, Any]] = []
    for comparison in comparisons:
        comparison_offset = int(comparison.get("offset") or 0)
        branch = next(
            (
                row for row in ordered
                if comparison_offset < int(row.get("offset") or 0)
                <= comparison_offset + 16
                and conditional_branch_kind(row)
            ),
            None,
        )
        if branch is not None:
            predicates.append({
                "field": "state",
                "equalValue": int(comparison["value"]),
                "comparisonOffset": comparison_offset,
                "branchOffset": int(branch.get("offset") or 0),
            })
    scenarios = [
        {
            "state": int(row["id"]),
            "stateName": row.get("name"),
            "values": {"state": int(row["id"])},
        }
        for row in enum_values
    ]
    return constrained_lifecycle_routes(
        instructions,
        predicates,
        lifecycle_calls,
        scenarios,
        method_va=method_va,
    )


def register_family(register: str) -> str:
    """Normalize an x64 general-purpose register alias to its 64-bit family."""
    value = str(register or "").lower()
    aliases = {
        "al": "rax", "ah": "rax", "ax": "rax", "eax": "rax", "rax": "rax",
        "bl": "rbx", "bh": "rbx", "bx": "rbx", "ebx": "rbx", "rbx": "rbx",
        "cl": "rcx", "ch": "rcx", "cx": "rcx", "ecx": "rcx", "rcx": "rcx",
        "dl": "rdx", "dh": "rdx", "dx": "rdx", "edx": "rdx", "rdx": "rdx",
        "sil": "rsi", "si": "rsi", "esi": "rsi", "rsi": "rsi",
        "dil": "rdi", "di": "rdi", "edi": "rdi", "rdi": "rdi",
        "bpl": "rbp", "bp": "rbp", "ebp": "rbp", "rbp": "rbp",
        "spl": "rsp", "sp": "rsp", "esp": "rsp", "rsp": "rsp",
    }
    if value in aliases:
        return aliases[value]
    match = re.fullmatch(r"r(1[0-5]|[8-9])(?:b|w|d)?", value)
    return f"r{match.group(1)}" if match else value


def discover_boolean_field_predicates(
    instructions: list[dict[str, Any]],
    *,
    field: str,
    field_read_offset: int,
    method_va: int,
) -> list[dict[str, Any]]:
    """Find every direct zero/nonzero branch while one typed bool stays live."""
    ordered = sorted(
        instructions,
        key=lambda row: int(row.get("offset") or 0),
    )
    by_offset = {int(row.get("offset") or 0): row for row in ordered}
    offsets = sorted(by_offset)
    next_offset = {
        offset: offsets[index + 1]
        for index, offset in enumerate(offsets[:-1])
    }
    read = by_offset.get(field_read_offset) or {}
    target_register = register_family((read.get("write") or {}).get("register") or "")
    start = next_offset.get(field_read_offset)
    if not target_register or start is None:
        return []
    volatile = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}
    pending = [start]
    visited: set[int] = set()
    predicates: dict[int, dict[str, Any]] = {}
    while pending:
        offset = pending.pop()
        if offset in visited or offset not in by_offset:
            continue
        visited.add(offset)
        instruction = by_offset[offset]
        text = str(instruction.get("text") or "").lower()
        write_register = register_family(
            (instruction.get("write") or {}).get("register") or ""
        )
        if write_register == target_register:
            continue
        test_match = re.fullmatch(
            r"test\s+([a-z0-9]+),\s*([a-z0-9]+)",
            text,
            re.I,
        )
        if test_match and (
            register_family(test_match.group(1)) == target_register
            and register_family(test_match.group(2)) == target_register
        ):
            branch_offset = next_offset.get(offset)
            branch = by_offset.get(branch_offset) if branch_offset is not None else None
            if branch is not None and conditional_branch_kind(branch):
                predicates[int(branch_offset)] = {
                    "field": field,
                    "equalValue": False,
                    "testOffset": offset,
                    "testText": text,
                    "branchOffset": int(branch_offset),
                    "branchText": branch.get("text"),
                }
        if text.startswith("call ") and target_register in volatile:
            continue
        following = next_offset.get(offset)
        target = direct_branch_target_offset(instruction, method_va)
        successors: list[int] = []
        if text.startswith("jmp "):
            if target in by_offset:
                successors.append(target)
        elif text.startswith(("ret", "int3")):
            pass
        else:
            if following is not None:
                successors.append(following)
            if re.match(r"^j[a-z]+\b", text) and target in by_offset:
                successors.append(target)
        pending.extend(reversed(successors))
    return [predicates[offset] for offset in sorted(predicates)]


def validate_quest_enable_lifecycle_application(
    *,
    candidate_rows: list[dict[str, Any]],
    packet_predicates: list[dict[str, Any]],
    runtime_predicates: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    unread_control_fields: list[str],
    packet_field: str,
    runtime_field: str,
    source_file: str,
    source_hashes: dict[str, str],
    prior_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fail closed on a complete two-boolean quest enable application matrix."""
    failures = list(prior_failures or [])

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_enable_lifecycle_application",
            "gate": gate,
            "message": (
                candidate_rows[0].get("type") if len(candidate_rows) == 1 else None
            ),
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    if len(candidate_rows) != 1:
        fail("uniqueQuestEnableUpdate", 1, [row.get("type") for row in candidate_rows])
    if len(packet_predicates) != 1:
        fail("packetEnablePredicate", 1, packet_predicates)
    if len(runtime_predicates) != 2:
        fail("runtimePausePredicates", 2, runtime_predicates)
    expected_inputs = {
        (False, False), (False, True), (True, False), (True, True)
    }
    actual_inputs = {
        ((row.get("values") or {}).get(packet_field),
         (row.get("values") or {}).get(runtime_field))
        for row in routes
    }
    typed_boolean_inputs = all(
        type(value) is bool
        for values in actual_inputs
        for value in values
    )
    if actual_inputs != expected_inputs or not typed_boolean_inputs:
        fail(
            "completeBooleanMatrix",
            sorted(expected_inputs),
            sorted(actual_inputs, key=repr),
        )
    invalid_routes = [
        row for row in routes
        if len(row.get("reachableLifecycleCalls") or []) != 1
    ]
    distinct_calls = {
        tuple(call.get("method") for call in row.get("reachableLifecycleCalls") or [])
        for row in routes
    }
    if invalid_routes or len(distinct_calls) < 3:
        fail(
            "oneDistinctLifecycleCallPerRoute",
            "4 single-call routes spanning >=3 lifecycle methods",
            routes,
        )
    mismatched = [
        {"values": row.get("values"), "method": call.get("method")}
        for row in routes
        for call in row.get("reachableLifecycleCalls") or []
        if call.get("samePacketIdentity") is not True
    ]
    if mismatched:
        fail("samePacketIdentity", [], mismatched)
    if not unread_control_fields:
        fail("unusedPacketControlReported", ">=1 unread control field", [])
    return {
        "status": "validated" if not failures else "validation_failed",
        "failures": failures,
    }


def validate_quest_state_lifecycle_application(
    *,
    candidate_rows: list[dict[str, Any]],
    enum_values: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    source_file: str,
    source_hashes: dict[str, str],
    prior_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fail closed on a field-shaped quest state-to-lifecycle application."""
    failures = list(prior_failures or [])

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_state_lifecycle_application",
            "gate": gate,
            "message": (
                candidate_rows[0].get("type") if len(candidate_rows) == 1 else None
            ),
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    if len(candidate_rows) != 1:
        fail("uniqueQuestStateUpdate", 1, [row.get("type") for row in candidate_rows])
    if len(enum_values) < 2:
        fail("enumMembers", ">=2", enum_values)
    compared_values = sorted({int(row["value"]) for row in comparisons})
    if len(compared_values) < 2:
        fail("stateFieldComparisons", ">=2 distinct enum values", compared_values)
    lifecycle_routes = [
        row for row in routes if row.get("reachableLifecycleCalls")
    ]
    distinct_shapes = {
        tuple(call.get("method") for call in row["reachableLifecycleCalls"])
        for row in lifecycle_routes
    }
    if len(lifecycle_routes) < 2 or len(distinct_shapes) < 2:
        fail(
            "stateConstrainedLifecycleRoutes",
            ">=2 states with distinct lifecycle-call sets",
            routes,
        )
    mismatched = [
        {"state": row.get("state"), "method": call.get("method")}
        for row in lifecycle_routes
        for call in row.get("reachableLifecycleCalls") or []
        if call.get("samePacketIdentity") is not True
    ]
    if mismatched:
        fail("samePacketIdentity", [], mismatched)
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
    semantic_reads = {
        name: field_reads.get(name, 0)
        for name in ("questType", "showMode")
    }
    if any(semantic_reads.values()):
        fail(
            "noQuestSemanticSelectorDuringStart",
            {"questType": 0, "showMode": 0},
            semantic_reads,
        )
    if topology_calls:
        fail("noClientSuccessorTraversalCall", [], topology_calls)
    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def validate_quest_succeed_action_observation(
    *,
    enum_values: dict[str, int],
    succeed_action_calls: list[dict[str, Any]],
    safe_run_action_flow: dict[str, Any],
    safe_run_direct_callers: list[dict[str, Any]],
    run_quest_action_flow: dict[str, Any],
    run_quest_action_direct_callers: list[dict[str, Any]],
    start_action_dispatchers: list[dict[str, Any]],
    source_file: str,
    source_hashes: dict[str, str],
    prior_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fail closed on the generic quest-success client-action path."""
    failures = list(prior_failures or [])

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_succeed_action_contract",
            "gate": gate,
            "message": "Beyond.Gameplay.MissionSystem.SucceedQuest",
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    expected_enum = {
        "OnStartClientAction": 1,
        "OnSucceedClientAction": 2,
        "OnFailedClientAction": 4,
    }
    if {key: enum_values.get(key) for key in expected_enum} != expected_enum:
        fail("questActionEnum", expected_enum, enum_values)
    if len(succeed_action_calls) != 1:
        fail("uniqueSucceedSafeRunCall", 1, succeed_action_calls)
    elif succeed_action_calls[0].get("questActionValue") != 2:
        fail(
            "succeedActionValue",
            expected_enum["OnSucceedClientAction"],
            succeed_action_calls[0].get("questActionValue"),
        )
    if not safe_run_action_flow.get("preservesQuestActionArgument"):
        fail("safeRunPreservesQuestAction", True, safe_run_action_flow)
    caller_actions = {
        str(row.get("symbol") or ""): row.get("questActionValue")
        for row in safe_run_direct_callers
        if row.get("symbol")
    }
    expected_caller_actions = {
        "Beyond.Gameplay.MissionSystem.FailQuest": 4,
        "Beyond.Gameplay.MissionSystem.SucceedQuest": 2,
    }
    if caller_actions != expected_caller_actions:
        fail(
            "safeRunDirectCallerActionCensus",
            expected_caller_actions,
            caller_actions,
        )
    run_callers = sorted({
        str(row.get("symbol") or "")
        for row in run_quest_action_direct_callers
        if row.get("symbol")
    })
    expected_run_callers = [
        "Beyond.Gameplay.MissionSystem.ProcessPendingQuestAction",
        "Beyond.Gameplay.MissionSystem.SafeRunQuestAction",
    ]
    if run_callers != expected_run_callers:
        fail("runQuestActionDirectCallerCensus", expected_run_callers, run_callers)
    if not run_quest_action_flow.get("preservesQuestActionArgument"):
        fail("runQuestActionPreservesQuestAction", True, run_quest_action_flow)
    if not run_quest_action_flow.get("sharedPendingCarrier"):
        fail("pendingReplayUsesSafeRunCarrier", True, run_quest_action_flow)
    if start_action_dispatchers:
        fail("noCurrentAotStartActionDispatcher", [], start_action_dispatchers)
    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def decode_direct_enum_argument(
    call: dict[str, Any],
    register: str,
    enum_values: dict[str, int],
) -> dict[str, Any]:
    """Decode immediates or zero-base LEA constants, never stack offsets."""
    write = (
        ((call.get("argumentContext") or {}).get("argRegisterWrites") or {})
        .get(register, {})
        .get("write", {})
        .get("value")
    )
    origin = (call.get("argumentOrigins") or {}).get(register)
    register_writes = (
        (call.get("argumentContext") or {}).get("argRegisterWrites") or {}
    )
    value = None
    for text in (write, origin):
        rendered = str(text or "")
        match = re.fullmatch(r"0x([0-9a-f]+)", rendered, re.I)
        if match:
            value = int(match.group(1), 16)
            break
        lea_match = re.fullmatch(
            r"&\[([a-z][a-z0-9]*)\+0x([0-9a-f]+)\]",
            rendered,
            re.I,
        )
        if lea_match:
            base_register = lea_match.group(1).lower()
            base_write = (register_writes.get(base_register) or {}).get("write") or {}
            if str(base_write.get("value") or "") in {"0", "0x0"}:
                value = int(lea_match.group(2), 16)
                break
    return {
        "questActionValue": value,
        "questActionName": next(
            (name for name, enum_value in enum_values.items() if enum_value == value),
            None,
        ),
        "argumentOrigin": origin,
        "argumentWrite": write,
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


def validate_action_extra_thread_scheduler_census(
    *,
    carrier_count: int,
    scheduler_method_count: int,
    direct_calls: list[dict[str, Any]],
    rejected_direct_calls: list[dict[str, Any]],
    extra_thread_execute_methods: list[dict[str, Any]],
    source_file: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed on every current ActionBase extra-thread writer shape.

    Counts are deliberately corpus-derived.  The validator does not encode the
    names or expected number of composite action classes; a future build must
    either match one of the structural writer shapes or make this gate fail.
    """
    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any, message: str = "") -> None:
        failures.append({
            "validator": "action_extra_thread_scheduler_census",
            "gate": gate,
            "message": message or None,
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    if carrier_count != 1:
        fail("uniqueStructuralCarrier", 1, carrier_count)
    if scheduler_method_count != 1:
        fail("uniqueSchedulerMethod", 1, scheduler_method_count)
    if rejected_direct_calls:
        fail("completeDecodedDirectCallerCensus", [], rejected_direct_calls)
    for call in direct_calls:
        if not call.get("thisArgumentPreserved"):
            fail("directCallerPreservesThis", True, call, str(call.get("caller") or ""))
        if not call.get("childIdFromOwnField"):
            fail("directChildIdFromTypedField", True, call, str(call.get("caller") or ""))
        if not call.get("thirdArgumentZero"):
            fail("directSchedulerFlagIsZero", True, call, str(call.get("caller") or ""))
    if not extra_thread_execute_methods:
        fail("observedCompositeWriter", ">=1", 0)
    for row in extra_thread_execute_methods:
        if row.get("writerShape") not in {
            "direct_scheduler_calls_from_typed_fields",
            "inline_list_add_from_typed_collection",
        }:
            fail(
                "knownStructuralWriterShape",
                [
                    "direct_scheduler_calls_from_typed_fields",
                    "inline_list_add_from_typed_collection",
                ],
                row,
                str(row.get("symbol") or ""),
            )
    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def action_extra_thread_scheduler_census(
    metadata: Any,
    helper: Any,
    gameassembly_path: Path,
    mapper_path: Path = NATIVE_MAPPER_HELPER,
) -> dict[str, Any]:
    """Recover parallel composite semantics from the generic ActionBase scheduler.

    Discovery starts with field/method shape, then scans every direct ActionBase
    child Execute body.  Display names are reported only after admission; they
    are never selection keys.
    """
    mapper = il2cpp.load_native_mapper(mapper_path)
    pe = mapper.PeImage(gameassembly_path)
    registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if registration is None:
        raise RuntimeError("extra-thread audit could not derive MetadataRegistration")
    registration_summary = mapper.metadata_registration_summary(pe, registration)
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
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }

    def mapped_method(type_def: Any, method: Any) -> tuple[dict[str, Any], int, int]:
        row = full_method_mapper_row(metadata, helper, method.index)
        image_range = ranges.get(row["image"])
        pointers = pointers_by_image.get(row["image"], [])
        if not image_range:
            raise RuntimeError(f"missing image method range for {row['image']}")
        slot = row["methodIndex"] - image_range["methodStart"]
        if not 0 <= slot < len(pointers) or not pointers[slot]:
            raise RuntimeError(f"unmapped method {row['type']}.{row['method']}")
        pointer = pointers[slot]
        size, _ = mapper.estimate_scan_size(pointer, sorted_pointers, 4096)
        return row, pointer, size

    carriers: list[dict[str, Any]] = []
    carrier_defs: list[Any] = []
    for type_def in metadata.types:
        field_names = {
            metadata.string(field.name_index)
            for field in metadata.fields_for(type_def)
        }
        scheduler_methods = [
            method
            for method in metadata.methods_for(type_def)
            if helper.method_row(metadata, method)["name"]
            == "SetResultLaunchExtraThread"
        ]
        if "m_extraThreadIDList" not in field_names or not scheduler_methods:
            continue
        offsets = il2cpp.runtime_type_field_offsets(
            metadata, pe, registration_summary, type_def.index
        )
        carriers.append({
            "type": metadata.type_full_name(type_def),
            "typeIndex": type_def.index,
            "typeToken": f"0x{type_def.token:08x}",
            "extraThreadListField": "m_extraThreadIDList",
            "extraThreadListOffset": f"0x{offsets['m_extraThreadIDList']:x}",
            "schedulerMethods": len(scheduler_methods),
        })
        carrier_defs.append((type_def, scheduler_methods, offsets))

    scheduler_method_count = sum(
        len(methods) for _, methods, _ in carrier_defs
    )
    scheduler_va = 0
    scheduler_row: dict[str, Any] = {}
    scheduler_size = 0
    if len(carrier_defs) == 1 and scheduler_method_count == 1:
        _, methods, _ = carrier_defs[0]
        scheduler_row, scheduler_va, scheduler_size = mapped_method(
            carrier_defs[0][0], methods[0]
        )

    raw_call_sites = direct_rel32_call_candidates(pe, scheduler_va) if scheduler_va else []
    direct_calls: list[dict[str, Any]] = []
    rejected_direct_calls: list[dict[str, Any]] = []
    calls_by_method: dict[int, list[dict[str, Any]]] = {}
    for site in raw_call_sites:
        position = bisect_right(sorted_pointers, site) - 1
        if position < 0:
            rejected_direct_calls.append({"callVa": f"0x{site:x}", "reason": "no_caller"})
            continue
        caller_va = sorted_pointers[position]
        aliases = method_by_pointer.get(caller_va) or []
        caller = aliases[0] if aliases else None
        if not caller:
            rejected_direct_calls.append({"callVa": f"0x{site:x}", "reason": "no_symbol"})
            continue
        caller_method = metadata.methods[int(caller["methodIndex"])]
        caller_def = metadata.types[caller_method.declaring_type]
        own_offsets = il2cpp.runtime_type_field_offsets(
            metadata, pe, registration_summary, caller_def.index
        )
        scan_start = max(caller_va, site - 24)
        instructions = mapper.decode_x64_subset(
            pe.bytes_at_va(scan_start, site + 5 - scan_start),
            scan_start,
            stop_offset=site + 5 - scan_start,
        )
        before = [str(row.get("text") or "") for row in instructions[-8:]]
        own_origin = None
        for field_name, offset in own_offsets.items():
            if any(re.search(rf"mov edx, \[[a-z0-9]+\+0x{offset:x}\]", text) for text in before):
                own_origin = {"field": field_name, "offset": f"0x{offset:x}"}
                break
        row = {
            "callVa": f"0x{site:x}",
            "caller": f"{caller.get('type')}.{caller.get('method')}",
            "callerToken": caller.get("token"),
            "callerVa": f"0x{caller_va:x}",
            "thisArgumentPreserved": any(
                re.fullmatch(r"mov rcx, (rbx|rsi|rdi|r1[2-5])", text)
                for text in before
            ),
            "childIdFromOwnField": own_origin is not None,
            "childIdOrigin": own_origin,
            "thirdArgumentZero": any(
                text in {"xor r8d, r8d", "mov r8d, 0x0"} for text in before
            ),
        }
        direct_calls.append(row)
        calls_by_method.setdefault(caller_va, []).append(row)

    extra_offset = (
        carrier_defs[0][2].get("m_extraThreadIDList")
        if len(carrier_defs) == 1
        else None
    )
    execute_rows: list[dict[str, Any]] = []
    non_child_extra_thread_consumers: list[dict[str, Any]] = []
    carrier_byval = carrier_defs[0][0].byval_type_index if len(carrier_defs) == 1 else -1
    for type_def in metadata.types:
        if type_def.declaring_type_index != carrier_byval:
            continue
        executes = [
            method
            for method in metadata.methods_for(type_def)
            if helper.method_row(metadata, method)["name"] == "Execute"
        ]
        for method in executes:
            try:
                method_row, pointer, size = mapped_method(type_def, method)
            except RuntimeError:
                # Open generic definitions can legitimately lack an AOT body;
                # their closed instantiations do not own serialized action fields.
                continue
            instructions = mapper.decode_x64_subset(
                pe.bytes_at_va(pointer, size), pointer, stop_offset=size
            )
            texts = [str(row.get("text") or "") for row in instructions]
            this_aliases = {"rcx"}
            changed = True
            while changed:
                changed = False
                for row in instructions:
                    if int(row.get("offset") or 0) > 96:
                        break
                    match = re.fullmatch(
                        r"mov ([a-z0-9]+), ([a-z0-9]+)",
                        str(row.get("text") or ""),
                    )
                    if match and match.group(2) in this_aliases and match.group(1) not in this_aliases:
                        this_aliases.add(match.group(1))
                        changed = True
            alias_pattern = "(?:" + "|".join(sorted(map(re.escape, this_aliases))) + ")"
            try:
                own_offsets = il2cpp.runtime_type_field_offsets(
                    metadata, pe, registration_summary, type_def.index
                )
            except RuntimeError:
                own_offsets = {}
            own_reads = [
                {"field": field_name, "offset": f"0x{offset:x}"}
                for field_name, offset in own_offsets.items()
                if any(re.search(rf"\[{alias_pattern}\+0x{offset:x}\]", text) for text in texts)
            ]
            extra_reads = [
                row for row in instructions
                if extra_offset is not None
                and re.match(
                    rf"mov [a-z0-9]+, \[{alias_pattern}\+0x{extra_offset:x}\]$",
                    str(row.get("text") or ""),
                )
            ]
            direct = calls_by_method.get(pointer, [])
            child_loads = [
                row for row in instructions
                if re.fullmatch(
                    r"mov ([a-z0-9]+), \[[a-z0-9]+\+0x20\+[a-z0-9]+\*4\]",
                    str(row.get("text") or ""),
                )
            ]
            loaded_registers = {
                re.fullmatch(r"mov ([a-z0-9]+), .*", str(row.get("text") or "")).group(1)
                for row in child_loads
            }
            inline_appends = [
                row for row in instructions
                if any(
                    str(row.get("text") or "").endswith(f", {register}")
                    and (
                        str(row.get("text") or "").startswith("mov edx,")
                        or "+0x20+" in str(row.get("text") or "")
                    )
                    for register in loaded_registers
                )
            ]
            writer_shape = ""
            if direct:
                writer_shape = "direct_scheduler_calls_from_typed_fields"
            elif extra_reads and own_reads and child_loads and inline_appends:
                writer_shape = "inline_list_add_from_typed_collection"
            if not extra_reads and not direct:
                continue
            if not writer_shape:
                non_child_extra_thread_consumers.append({
                    "symbol": f"{method_row['type']}.{method_row['method']}",
                    "token": method_row["token"],
                    "va": f"0x{pointer:x}",
                    "extraThreadListReads": [
                        {"offset": row["offset"], "text": row["text"]}
                        for row in extra_reads
                    ],
                    "classification": "no_typed_child_launch_shape_observed",
                })
                continue
            execute_rows.append({
                "symbol": f"{method_row['type']}.{method_row['method']}",
                "token": method_row["token"],
                "va": f"0x{pointer:x}",
                "scanBytes": size,
                "writerShape": writer_shape or "unclassified_extra_thread_access",
                "typedChildFields": own_reads,
                "directSchedulerCalls": direct,
                "extraThreadListReads": [
                    {"offset": row["offset"], "text": row["text"]}
                    for row in extra_reads
                ],
                "collectionChildLoads": [
                    {"offset": row["offset"], "text": row["text"]}
                    for row in child_loads
                ],
                "appendObservations": [
                    {"offset": row["offset"], "text": row["text"]}
                    for row in inline_appends
                ],
            })

    validation = validate_action_extra_thread_scheduler_census(
        carrier_count=len(carriers),
        scheduler_method_count=scheduler_method_count,
        direct_calls=direct_calls,
        rejected_direct_calls=rejected_direct_calls,
        extra_thread_execute_methods=execute_rows,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
    )
    return {
        "schema": "actionExtraThreadSchedulerCensus.v1",
        "classification": "typed_children_launch_as_parallel_extra_threads",
        "discoveryPattern": {
            "selection": "ActionBase field/method shape plus direct-child Execute bodies",
            "objectIdentityInputs": [],
            "acceptedWriterShapes": [
                "direct_scheduler_calls_from_typed_fields",
                "inline_list_add_from_typed_collection",
            ],
        },
        "carrier": carriers[0] if len(carriers) == 1 else None,
        "carrierCandidates": carriers,
        "schedulerMethod": ({
            "symbol": f"{scheduler_row.get('type')}.{scheduler_row.get('method')}",
            "token": scheduler_row.get("token"),
            "va": f"0x{scheduler_va:x}",
            "scanBytes": scheduler_size,
        } if scheduler_va else None),
        "rawDirectCallCandidates": len(raw_call_sites),
        "directCalls": direct_calls,
        "rejectedDirectCalls": rejected_direct_calls,
        "extraThreadExecuteMethods": execute_rows,
        "nonChildExtraThreadConsumers": non_child_extra_thread_consumers,
        "finding": (
            "Every current direct ActionBase child Execute body that writes the inherited "
            "extra-thread list either calls the structurally discovered scheduler with "
            "typed child fields or appends typed collection members inline. These child "
            "slots are parallel fan-out arms, not array-position chronology."
        ),
        "boundary": (
            "This proves the current installed GameAssembly AOT path. Execute methods "
            "carry IFix guards; an active runtime substitution, native memory mutation, "
            "future patch, or future build remains outside this static proof. Sibling "
            "completion order and order across separate Story files remain unknown."
        ),
        "validation": validation,
    }


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


def lifecycle_call_sites_from_body(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Return exact decoded lifecycle calls with their native body offsets."""
    rows: list[dict[str, Any]] = []
    for call in body.get("calls") or []:
        for target in call.get("resolved") or []:
            method = str(target.get("method") or "")
            if not STATE_LIFECYCLE_METHOD_RE.fullmatch(method):
                continue
            rows.append({
                "offset": int(call.get("offset") or 0),
                "targetVa": call.get("targetVa"),
                "symbol": f"{target.get('type')}.{method}",
                "token": target.get("token"),
            })
    unique = {
        (row["offset"], row["symbol"], row.get("targetVa")): row
        for row in rows
    }
    return sorted(
        unique.values(),
        key=lambda row: (row["offset"], row["symbol"]),
    )


def semantic_enum_branch_observations(
    body: dict[str, Any],
    field_reads: dict[str, list[dict[str, Any]]],
    *,
    method_pointer: int,
    method_size: int,
    enum_names: dict[str, dict[int, str]],
) -> list[dict[str, Any]]:
    """Describe enum comparisons and their bounded forward fallthrough calls.

    This is deliberately field-driven rather than method-name-driven.  It
    records the next decoded conditional branch after each exact typed field
    read and the calls in a forward fallthrough corridor.  A ``jne`` corridor
    is the enum-equal path; a ``je`` corridor is the enum-not-equal path.  More
    complex control flow remains explicitly unclassified.
    """
    controls = sorted(
        body.get("controlFlow") or [],
        key=lambda row: int(row.get("offset") or 0),
    )
    calls = sorted(
        body.get("calls") or [],
        key=lambda row: int(row.get("offset") or 0),
    )
    observations: list[dict[str, Any]] = []
    for field_name, reads in field_reads.items():
        value_names = enum_names.get(field_name) or {}
        if not value_names:
            continue
        for read in reads:
            text = str(read.get("text") or "")
            match = re.fullmatch(
                r"cmp\s+\[[^]]+\],\s*0x([0-9a-f]+)",
                text,
                re.I,
            )
            if not match:
                continue
            value = int(match.group(1), 16)
            read_offset = int(read.get("offset") or 0)
            branch = next(
                (
                    row for row in controls
                    if read_offset < int(row.get("offset") or 0) <= read_offset + 16
                    and re.match(r"^j(?:e|ne)\b", str(row.get("text") or ""), re.I)
                ),
                None,
            )
            branch_text = str((branch or {}).get("text") or "")
            branch_mnemonic = branch_text.split(" ", 1)[0].lower()
            target_text = str((branch or {}).get("targetVa") or "")
            target_offset = (
                int(target_text, 16) - method_pointer if target_text else None
            )
            forward_target = (
                isinstance(target_offset, int)
                and read_offset < target_offset < method_size
            )
            branch_offset = int((branch or {}).get("offset") or 0)
            corridor_calls = [
                call for call in calls
                if forward_target
                and branch_offset < int(call.get("offset") or 0) < target_offset
            ]
            call_rows = []
            for call in corridor_calls:
                symbols = sorted({
                    f"{target.get('type')}.{target.get('method')}"
                    for target in call.get("resolved") or []
                    if target.get("type") and target.get("method")
                })
                call_rows.append({
                    "offset": int(call.get("offset") or 0),
                    "targetVa": call.get("targetVa"),
                    "symbols": symbols,
                    "resolved": bool(symbols),
                })
            observations.append({
                "field": field_name,
                "value": value,
                "enumName": value_names.get(value),
                "readOffset": read_offset,
                "readText": text,
                "branchOffset": branch_offset if branch else None,
                "branchText": branch_text or None,
                "branchTargetOffset": target_offset,
                "forwardTargetInMethod": forward_target,
                "fallthroughCondition": (
                    "equal" if branch_mnemonic == "jne"
                    else "not_equal" if branch_mnemonic == "je"
                    else "unclassified"
                ),
                "fallthroughCalls": call_rows,
                "fallthroughResolvedSymbols": sorted({
                    symbol
                    for call in call_rows
                    for symbol in call["symbols"]
                }),
            })
    return observations


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
    enum_names: dict[str, dict[int, str]] | None = None,
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
        lifecycle_call_sites = lifecycle_call_sites_from_body(body)
        semantic_read_offsets = sorted({
            int(access.get("offset") or 0)
            for name in ("questType", "showMode")
            for access in reads.get(name) or []
        })
        lifecycle_offsets = [row["offset"] for row in lifecycle_call_sites]
        first_semantic_read = (
            semantic_read_offsets[0] if semantic_read_offsets else None
        )
        backward_lifecycle_branches: list[dict[str, Any]] = []
        if first_semantic_read is not None and lifecycle_offsets:
            latest_lifecycle = max(lifecycle_offsets)
            for control in body.get("controlFlow") or []:
                source_offset = int(control.get("offset") or 0)
                text = str(control.get("text") or "")
                if not text.startswith("j"):
                    continue
                target_text = str(control.get("targetVa") or "")
                if not target_text:
                    continue
                target_offset = int(target_text, 16) - pointer
                if (
                    source_offset >= first_semantic_read
                    and 0 <= target_offset < scan_size
                    and target_offset <= latest_lifecycle
                ):
                    backward_lifecycle_branches.append({
                        "offset": source_offset,
                        "targetOffset": target_offset,
                        "text": text,
                    })
        enum_branches = semantic_enum_branch_observations(
            body,
            reads,
            method_pointer=pointer,
            method_size=scan_size,
            enum_names=enum_names or {},
        )
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
        elif reads.get("showMode") and not lifecycle_call_sites:
            classification = "quest_visibility_or_tracker_presentation"
        elif reads.get("questType") and lifecycle_call_sites:
            if (
                first_semantic_read is not None
                and lifecycle_offsets
                and min(semantic_read_offsets) > max(lifecycle_offsets)
                and not backward_lifecycle_branches
            ):
                block_branches = [
                    branch for branch in enum_branches
                    if branch.get("field") == "questType"
                    and branch.get("enumName") == "Block"
                    and branch.get("fallthroughCondition") == "equal"
                    and branch.get("fallthroughResolvedSymbols")
                    == ["Beyond.EventManager.SendGlobal"]
                ]
                classification = (
                    "post_lifecycle_block_notification"
                    if len(block_branches) == len(enum_branches) == 1
                    else "post_lifecycle_quest_type_behavior"
                )
            else:
                classification = "quest_type_lifecycle_interleaved"
        elif reads.get("questType"):
            classification = "quest_type_query_or_presentation"
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
            "lifecycleCallSites": lifecycle_call_sites,
            "semanticFieldReadOffsets": semantic_read_offsets,
            "semanticEnumBranches": enum_branches,
            "backwardLifecycleBranches": backward_lifecycle_branches,
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


def validate_quest_semantic_field_observation(
    *,
    quest_type_values: dict[str, int],
    show_mode_values: dict[str, int],
    quest_type_rows: list[dict[str, Any]],
    show_mode_rows: list[dict[str, Any]],
    source_file: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed on enum identity and branch-neutral client consumption."""
    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_semantic_field_consumer_census",
            "gate": gate,
            "message": "QuestInfo.questType/showMode consumers",
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": source_hashes,
        })

    expected_quest_types = {"Normal": 0, "Block": 1, "Optional": 2}
    expected_show_modes = {"AlwaysShow": 1, "AlwaysHide": 1000}
    if quest_type_values != expected_quest_types:
        fail("questTypeEnum", expected_quest_types, quest_type_values)
    if show_mode_values != expected_show_modes:
        fail("questShowModeEnum", expected_show_modes, show_mode_values)
    if not quest_type_rows:
        fail("questTypeConsumerDiscovery", ">=1", 0)
    if not show_mode_rows:
        fail("showModeConsumerDiscovery", ">=1", 0)

    show_lifecycle_rows = [
        row for row in show_mode_rows if row.get("lifecycleCallSites")
    ]
    if show_lifecycle_rows:
        fail("showModeHasNoLifecycleConsumer", [], show_lifecycle_rows)
    interleaved_rows = [
        row for row in quest_type_rows
        if row.get("lifecycleCallSites")
        and row.get("classification") != "post_lifecycle_block_notification"
    ]
    if interleaved_rows:
        fail(
            "questTypeLifecycleReadsArePostApplicationBlockNotifications",
            [],
            interleaved_rows,
        )
    block_notification_rows = [
        row for row in quest_type_rows
        if row.get("classification") == "post_lifecycle_block_notification"
    ]
    if len(block_notification_rows) != 2:
        fail(
            "postLifecycleBlockNotificationConsumers",
            2,
            len(block_notification_rows),
        )
    invalid_block_branches = [
        row for row in block_notification_rows
        if len(row.get("semanticEnumBranches") or []) != 1
        or (row.get("semanticEnumBranches") or [{}])[0].get("enumName")
        != "Block"
        or (row.get("semanticEnumBranches") or [{}])[0].get(
            "fallthroughCondition"
        ) != "equal"
        or (row.get("semanticEnumBranches") or [{}])[0].get(
            "fallthroughResolvedSymbols"
        ) != ["Beyond.EventManager.SendGlobal"]
    ]
    if invalid_block_branches:
        fail(
            "blockEqualPathResolvedCall",
            ["Beyond.EventManager.SendGlobal"],
            invalid_block_branches,
        )
    backward_rows = [
        row for row in quest_type_rows
        if row.get("backwardLifecycleBranches")
    ]
    if backward_rows:
        fail("noSemanticFieldBackEdgeToLifecycle", [], backward_rows)
    return {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }


def quest_optional_objective_flag_contract(
    metadata: Any,
    helper: Any,
    mapper: Any,
    pe: Any,
    metadata_summary: dict[str, Any],
    method_by_pointer: dict[int, list[dict[str, Any]]],
    quest_consumers: dict[str, Any],
    *,
    optional_value: int,
    gameassembly_path: Path,
) -> dict[str, Any]:
    """Prove the current Optional comparison writes a presentation flag.

    The target type is found by its managed field shape, the field offset comes
    from the installed MetadataRegistration, and the consumer is selected from
    the complete typed GetQuestInfo caller census.  No mission or quest id is
    named here.
    """
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }
    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_optional_objective_flag_contract",
            "gate": gate,
            "message": "QuestType.Optional objective presentation flag",
            "expected": expected,
            "actual": actual,
            "sourceFile": str(gameassembly_path.resolve()),
            "sourceHashes": source_hashes,
        })

    required_fields = {
        "questId",
        "objectiveIdx",
        "isShowProgress",
        "description",
        "optional",
        "distanceText",
    }
    type_candidates = []
    for type_def in metadata.types:
        names = {
            metadata.string(field.name_index)
            for field in metadata.fields_for(type_def)
        }
        if required_fields <= names:
            type_candidates.append(type_def)
    if len(type_candidates) != 1:
        fail(
            "uniqueObjectiveShowDataShape",
            1,
            [metadata.type_full_name(row) for row in type_candidates],
        )
        return {
            "schema": "questOptionalObjectiveFlag.v1",
            "classification": "validation_failed",
            "validation": {"status": "validation_failed", "failures": failures},
        }

    type_def = type_candidates[0]
    type_name = metadata.type_full_name(type_def)
    field_offsets = il2cpp.runtime_type_field_offsets(
        metadata,
        pe,
        metadata_summary,
        type_def.index,
    )
    optional_offset = field_offsets.get("optional")
    if not isinstance(optional_offset, int):
        fail("optionalFieldOffset", "integer offset", optional_offset)

    optional_rows = [
        row for row in quest_consumers.get("rows") or []
        if any(
            branch.get("field") == "questType"
            and branch.get("value") == optional_value
            and branch.get("enumName") == "Optional"
            for branch in row.get("semanticEnumBranches") or []
        )
    ]
    if len(optional_rows) != 1:
        fail(
            "uniqueOptionalConsumer",
            1,
            [
                f"{row.get('caller', {}).get('type')}."
                f"{row.get('caller', {}).get('method')}"
                for row in optional_rows
            ],
        )
    observation: dict[str, Any] = {}
    if len(optional_rows) == 1 and isinstance(optional_offset, int):
        row = optional_rows[0]
        caller = row.get("caller") or {}
        pointer = int(str(caller.get("va")), 16)
        scan_size = int(caller.get("scanBytes") or 0)
        mapper_row = full_method_mapper_row(
            metadata,
            helper,
            int(caller.get("methodIndex")),
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
        instructions = mapper.decode_x64_subset(
            body_bytes,
            pointer,
            stop_offset=len(body_bytes),
        )
        instruction_by_offset = {
            int(inst.get("offset") or 0): inst for inst in instructions
        }
        optional_branch = next(
            branch for branch in row.get("semanticEnumBranches") or []
            if branch.get("field") == "questType"
            and branch.get("value") == optional_value
        )
        target_offset = optional_branch.get("branchTargetOffset")
        target_inst = instruction_by_offset.get(int(target_offset or -1))
        target_text = str((target_inst or {}).get("text") or "")
        target_index = next(
            (
                index for index, inst in enumerate(instructions)
                if int(inst.get("offset") or 0) == target_offset
            ),
            -1,
        )
        target_tail = (
            instructions[target_index:target_index + 4]
            if target_index >= 0 else []
        )
        join_target = None
        for inst in target_tail:
            match = re.fullmatch(
                r"jmp\s+0x([0-9a-f]+)",
                str(inst.get("text") or ""),
                re.I,
            )
            if match:
                join_target = int(match.group(1), 16) - pointer
                break
        write_match = None
        write_inst = None
        if isinstance(join_target, int):
            for inst in instructions:
                offset = int(inst.get("offset") or 0)
                if not join_target <= offset <= join_target + 16:
                    continue
                match = re.fullmatch(
                    rf"mov\s+\[([a-z0-9]+)\+0x{optional_offset:x}\],\s*al",
                    str(inst.get("text") or ""),
                    re.I,
                )
                if match:
                    write_match = match
                    write_inst = inst
                    break
        constructor_calls = [
            call for call in body.get("calls") or []
            if any(
                target.get("type") == type_name
                and target.get("method") == ".ctor"
                for target in call.get("resolved") or []
            )
        ]
        output_register = write_match.group(1) if write_match else None
        output_alias_before_constructor = False
        if output_register and len(constructor_calls) == 1:
            ctor_offset = int(constructor_calls[0].get("offset") or 0)
            output_alias_before_constructor = any(
                ctor_offset - 48 <= int(inst.get("offset") or 0) < ctor_offset
                and str(inst.get("text") or "").lower()
                == f"mov {output_register.lower()}, rax"
                for inst in instructions
            )
        observation = {
            "caller": caller,
            "comparison": optional_branch,
            "objectiveShowDataType": type_name,
            "optionalFieldOffset": f"0x{optional_offset:x}",
            "constructorCalls": len(constructor_calls),
            "outputRegister": output_register,
            "outputAliasBeforeConstructor": output_alias_before_constructor,
            "equalTargetInstruction": {
                "offset": target_inst.get("offset") if target_inst else None,
                "va": target_inst.get("va") if target_inst else None,
                "text": target_text,
            },
            "joinTargetOffset": join_target,
            "optionalFieldWrite": {
                "offset": write_inst.get("offset") if write_inst else None,
                "va": write_inst.get("va") if write_inst else None,
                "text": write_inst.get("text") if write_inst else None,
            },
        }
        if optional_branch.get("branchText", "").split(" ", 1)[0].lower() != "je":
            fail("optionalEqualBranch", "je", optional_branch)
        if target_text.lower() != "mov al, 0x1":
            fail("optionalEqualValue", "mov al, 0x1", target_text)
        if not isinstance(join_target, int):
            fail("optionalEqualJoin", "forward jmp", target_tail)
        if write_inst is None:
            fail(
                "optionalFieldWrite",
                f"mov [object+0x{optional_offset:x}], al",
                None,
            )
        if len(constructor_calls) != 1 or not output_alias_before_constructor:
            fail(
                "objectiveShowDataObjectIdentity",
                "one constructor and output-register alias",
                {
                    "constructorCalls": len(constructor_calls),
                    "outputRegister": output_register,
                    "outputAliasBeforeConstructor": output_alias_before_constructor,
                },
            )

    validation = {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }
    return {
        "schema": "questOptionalObjectiveFlag.v1",
        "classification": "optional_objective_presentation_flag",
        "observation": observation,
        "finding": (
            "The sole current QuestType.Optional comparison is in the objective "
            "presentation builder. Its equal branch writes true to the exact "
            "MetadataRegistration-backed ObjectiveShowData.optional field."
        ),
        "boundary": (
            "This is a client objective-display flag after QuestInfo lookup. It "
            "does not activate an Optional quest, select a successor, or establish "
            "parallel or exclusive execution."
        ),
        "validation": validation,
    }


def quest_topology_field_consumer_census(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
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
        if name in {
            "questType",
            "showMode",
            "prevQuestIdList",
            "flowIndex",
        } and value
    }
    getter_rows = quest_start.get("questInfoGetterCalls") or []
    getter_va = int(str(getter_rows[0]["targetVa"]), 16)
    quest_type_enum = il2cpp.enum_members(
        metadata,
        defaults,
        "Beyond.GEnums.QuestType",
    )
    show_mode_enum = il2cpp.enum_members(
        metadata,
        defaults,
        "Beyond.Gameplay.QuestShowMode",
    )
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
        enum_names={
            "questType": {
                int(row["id"]): str(row["name"])
                for row in quest_type_enum
            },
            "showMode": {
                int(row["id"]): str(row["name"])
                for row in show_mode_enum
            },
        },
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
        all_offsets = il2cpp.runtime_type_field_offsets(
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
    quest_type_rows = [
        row for row in quest_consumers["rows"]
        if row["fieldReads"].get("questType")
    ]
    show_mode_rows = [
        row for row in quest_consumers["rows"]
        if row["fieldReads"].get("showMode")
    ]
    quest_type_values = {
        row["name"]: row["id"] for row in quest_type_enum
    }
    optional_flag = quest_optional_objective_flag_contract(
        metadata,
        helper,
        mapper,
        pe,
        metadata_summary,
        method_by_pointer,
        quest_consumers,
        optional_value=int(quest_type_values.get("Optional", -1)),
        gameassembly_path=gameassembly_path,
    )
    semantic_validation = validate_quest_semantic_field_observation(
        quest_type_values=quest_type_values,
        show_mode_values={row["name"]: row["id"] for row in show_mode_enum},
        quest_type_rows=quest_type_rows,
        show_mode_rows=show_mode_rows,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
    )
    optional_validation = optional_flag.get("validation") or {}
    if optional_validation.get("status") != "validated":
        semantic_validation["failures"].extend(
            optional_validation.get("failures") or []
        )
        semantic_validation["status"] = "validation_failed"
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
        "questSemanticFields": {
            "schema": "questSemanticFieldConsumers.v2",
            "classification": "client_presentation_and_post_application_only",
            "questType": {
                "type": "Beyond.GEnums.QuestType",
                "values": quest_type_enum,
                "consumerCount": len(quest_type_rows),
                "postLifecycleConsumerCount": sum(
                    row.get("classification")
                    == "post_lifecycle_block_notification"
                    for row in quest_type_rows
                ),
                "blockNotificationConsumerCount": sum(
                    row.get("classification")
                    == "post_lifecycle_block_notification"
                    for row in quest_type_rows
                ),
                "comparisonCounts": dict(sorted(Counter(
                    branch.get("enumName") or f"value:{branch.get('value')}"
                    for row in quest_type_rows
                    for branch in row.get("semanticEnumBranches") or []
                ).items())),
            },
            "showMode": {
                "type": "Beyond.Gameplay.QuestShowMode",
                "values": show_mode_enum,
                "consumerCount": len(show_mode_rows),
                "lifecycleConsumerCount": sum(
                    bool(row.get("lifecycleCallSites"))
                    for row in show_mode_rows
                ),
                "comparisonCounts": dict(sorted(Counter(
                    branch.get("enumName") or f"value:{branch.get('value')}"
                    for row in show_mode_rows
                    for branch in row.get("semanticEnumBranches") or []
                ).items())),
            },
            "optionalObjectiveFlag": optional_flag,
            "finding": (
                "The installed metadata names questType as Normal, Block, or "
                "Optional and showMode as AlwaysShow or AlwaysHide. Every direct "
                "showMode consumer is presentation/tracker-only. The sole Optional "
                "comparison writes ObjectiveShowData.optional. The two network "
                "handlers that compare Block apply their typed quest lifecycle calls "
                "first, then the Block-equal corridor emits EventManager.SendGlobal, "
                "with no native back-edge to lifecycle application. Neither field "
                "selects a successor arm."
            ),
            "boundary": (
                "These enum names explain authored arm metadata and current client "
                "consumption. Normal, Block, Optional, AlwaysShow, and AlwaysHide do "
                "not prove parallel execution, exclusivity, eligibility, or server "
                "successor selection."
            ),
            "validation": semantic_validation,
        },
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
        "questType",
        "showMode",
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
    offsets = il2cpp.runtime_type_field_offsets(
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
            "state. It does not read questType, showMode, prevQuestIdList, or flowIndex "
            "and makes no native predecessor/successor traversal call."
        ),
        "boundary": (
            "A MissionRuntime fan-out therefore proves authored prerequisite topology, "
            "not whether the server starts every arm, selects one exclusive arm, or "
            "applies another server-only eligibility rule. Explicit typed conditions or "
            "runtime branch carriers remain authoritative when present."
        ),
        "validation": validation,
    }


def quest_succeed_action_contract(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    helper: Any,
    mapper: Any,
    pe: Any,
    metadata_summary: dict[str, Any],
    method_by_pointer: dict[int, list[dict[str, Any]]],
    sorted_pointers: list[int],
    state_rows: list[dict[str, Any]],
    gameassembly_path: Path,
) -> dict[str, Any]:
    """Recover every current AOT path into the typed quest-action dispatcher."""
    failures: list[dict[str, Any]] = []
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_succeed_action_contract",
            "gate": gate,
            "message": "Beyond.Gameplay.MissionSystem.SucceedQuest",
            "expected": expected,
            "actual": actual,
            "sourceFile": str(gameassembly_path.resolve()),
            "sourceHashes": source_hashes,
        })

    enum_rows = il2cpp.enum_members(
        metadata,
        defaults,
        "Beyond.Gameplay.QuestAction",
    )
    enum_values = {str(row["name"]): int(row["id"]) for row in enum_rows}
    succeed_targets = {
        int(str(call["targetVa"]), 16)
        for row in state_rows
        if row.get("entityKind") == "quest"
        for call in row.get("lifecycleCalls") or []
        if call.get("method") == "SucceedQuest" and call.get("targetVa")
    }
    if len(succeed_targets) != 1:
        fail("uniqueSucceedQuestLifecycleTarget", 1, sorted(succeed_targets))
        return {
            "classification": "validation_failed",
            "questActionEnum": enum_values,
            "validation": {
                "status": "validation_failed",
                "failures": failures,
            },
        }

    succeed_va = next(iter(succeed_targets))
    succeed_aliases = [
        row for row in method_by_pointer.get(succeed_va, [])
        if row.get("method") == "SucceedQuest"
    ]
    if len(succeed_aliases) != 1:
        fail("uniqueSucceedQuestMetadataTarget", 1, succeed_aliases)
        return {
            "classification": "validation_failed",
            "questActionEnum": enum_values,
            "validation": {
                "status": "validation_failed",
                "failures": failures,
            },
        }

    def decode(pointer: int, alias: dict[str, Any]) -> tuple[dict[str, Any], int | None]:
        scan_size, next_pointer = mapper.estimate_scan_size(
            pointer,
            sorted_pointers,
            8192,
        )
        body = mapper.build_method_body_summary(
            full_method_mapper_row(metadata, helper, int(alias["methodIndex"])),
            pe.bytes_at_va(pointer, scan_size),
            pointer,
            method_by_pointer,
            pe=pe,
            max_instructions=2400,
        )
        return body, next_pointer

    succeed_body, succeed_next = decode(succeed_va, succeed_aliases[0])
    safe_calls = [
        call for call in succeed_body.get("calls") or []
        if any(
            target.get("method") == "SafeRunQuestAction"
            and target.get("type") == "Beyond.Gameplay.MissionSystem"
            for target in call.get("resolved") or []
        )
    ]
    succeed_action_calls: list[dict[str, Any]] = []
    for call in safe_calls:
        succeed_action_calls.append({
            "callOffset": call.get("offset"),
            "targetVa": call.get("targetVa"),
                **decode_direct_enum_argument(call, "r8", enum_values),
        })

    safe_va_values = {
        int(str(call["targetVa"]), 16)
        for call in safe_calls
        if call.get("targetVa")
    }
    safe_run_action_flow: dict[str, Any] = {}
    safe_run_direct_callers: list[dict[str, Any]] = []
    rejected_direct_calls: list[dict[str, Any]] = []
    safe_body: dict[str, Any] = {}
    run_va = 0
    safe_next = None
    if len(safe_va_values) != 1:
        fail("uniqueSafeRunQuestActionTarget", 1, sorted(safe_va_values))
    else:
        safe_va = next(iter(safe_va_values))
        safe_aliases = [
            row for row in method_by_pointer.get(safe_va, [])
            if row.get("method") == "SafeRunQuestAction"
        ]
        if len(safe_aliases) != 1:
            fail("uniqueSafeRunQuestActionMetadataTarget", 1, safe_aliases)
        else:
            safe_body, safe_next = decode(safe_va, safe_aliases[0])
            quest_action_flow = (
                safe_body.get("paramFlow") or {}
            ).get("param:questAction") or []
            run_calls = [
                call for call in safe_body.get("calls") or []
                if any(
                    target.get("method") == "RunQuestAction"
                    and target.get("type") == "Beyond.Gameplay.MissionSystem"
                    for target in call.get("resolved") or []
                )
            ]
            run_va_values = {
                int(str(call["targetVa"]), 16)
                for call in run_calls
                if call.get("targetVa")
            }
            if len(run_va_values) != 1:
                fail("uniqueRunQuestActionTarget", 1, sorted(run_va_values))
            else:
                run_va = next(iter(run_va_values))
            flow_text = [str(row.get("text") or "") for row in quest_action_flow]
            safe_run_action_flow = {
                "symbol": "Beyond.Gameplay.MissionSystem.SafeRunQuestAction",
                "token": safe_aliases[0].get("token"),
                "va": f"0x{safe_va:x}",
                "scanBytes": (
                    safe_next - safe_va if isinstance(safe_next, int) else None
                ),
                "paramQuestActionFlow": quest_action_flow,
                "runQuestActionCalls": [
                    {
                        "callOffset": call.get("offset"),
                        "targetVa": call.get("targetVa"),
                    }
                    for call in run_calls
                ],
                "preservesQuestActionArgument": (
                    len(run_calls) == 1
                    and any("mov ebx, r8d" in text for text in flow_text)
                    and any("mov r8d, ebx" in text for text in flow_text)
                ),
            }

        for site in direct_rel32_call_candidates(pe, safe_va):
            position = bisect_right(sorted_pointers, site) - 1
            pointer = sorted_pointers[position] if position >= 0 else 0
            aliases = method_by_pointer.get(pointer) or []
            scan_size, _next_pointer = mapper.estimate_scan_size(
                pointer,
                sorted_pointers,
                65536,
            ) if pointer else (0, None)
            if not aliases or site - pointer >= scan_size:
                rejected_direct_calls.append({
                    "va": f"0x{site:x}",
                    "precedingMethodVa": f"0x{pointer:x}" if pointer else None,
                    "span": site - pointer if pointer else None,
                    "reason": "outsideBoundedMappedMethod",
                })
                continue
            method_indexes = sorted({
                int(row["methodIndex"])
                for row in aliases
                if row.get("methodIndex") is not None
            })
            if len(method_indexes) != 1:
                rejected_direct_calls.append({
                    "va": f"0x{site:x}",
                    "precedingMethodVa": f"0x{pointer:x}",
                    "reason": "ambiguousCallerMethod",
                    "methodIndexes": method_indexes,
                })
                continue
            caller_row = full_method_mapper_row(
                metadata,
                helper,
                method_indexes[0],
            )
            caller_body = mapper.build_method_body_summary(
                caller_row,
                pe.bytes_at_va(pointer, scan_size),
                pointer,
                method_by_pointer,
                pe=pe,
                max_instructions=30000,
            )
            decoded_calls = [
                call for call in caller_body.get("calls") or []
                if call.get("targetVa") == f"0x{safe_va:x}"
                and int(call.get("offset") or 0) == site - pointer
            ]
            if len(decoded_calls) != 1:
                rejected_direct_calls.append({
                    "va": f"0x{site:x}",
                    "precedingMethodVa": f"0x{pointer:x}",
                    "reason": "rawE8NotDecodedAsCallInstruction",
                })
                continue
            safe_run_direct_callers.append({
                "symbol": f"{caller_row['type']}.{caller_row['method']}",
                "callerVa": f"0x{pointer:x}",
                "callVa": f"0x{site:x}",
                "callOffset": site - pointer,
                **decode_direct_enum_argument(decoded_calls[0], "r8", enum_values),
            })

    run_quest_action_flow: dict[str, Any] = {}
    run_quest_action_direct_callers: list[dict[str, Any]] = []
    rejected_run_direct_calls: list[dict[str, Any]] = []
    start_action_dispatchers: list[dict[str, Any]] = [
        row for row in safe_run_direct_callers
        if row.get("questActionValue") == enum_values.get("OnStartClientAction")
    ]
    if run_va:
        run_aliases = [
            row for row in method_by_pointer.get(run_va, [])
            if row.get("method") == "RunQuestAction"
            and row.get("type") == "Beyond.Gameplay.MissionSystem"
        ]
        if len(run_aliases) != 1:
            fail("uniqueRunQuestActionMetadataTarget", 1, run_aliases)
        else:
            run_body, run_next = decode(run_va, run_aliases[0])
            run_param_flow = (
                run_body.get("paramFlow") or {}
            ).get("param:action") or []
            run_flow_text = [str(row.get("text") or "") for row in run_param_flow]
            mission_system_def = metadata.types[
                metadata.methods[int(run_aliases[0]["methodIndex"])].declaring_type
            ]
            field_offsets = il2cpp.runtime_type_field_offsets(
                metadata, pe, metadata_summary, mission_system_def.index
            )
            field_names_by_origin = {
                f"this+0x{offset:x}": name
                for name, offset in field_offsets.items()
                if isinstance(offset, int) and offset > 0
            }
            decoded_caller_bodies: dict[str, dict[str, Any]] = {}
            for site in direct_rel32_call_candidates(pe, run_va):
                position = bisect_right(sorted_pointers, site) - 1
                pointer = sorted_pointers[position] if position >= 0 else 0
                aliases = method_by_pointer.get(pointer) or []
                scan_size, _next_pointer = mapper.estimate_scan_size(
                    pointer, sorted_pointers, 65536
                ) if pointer else (0, None)
                if not aliases or site - pointer >= scan_size:
                    rejected_run_direct_calls.append({
                        "va": f"0x{site:x}",
                        "precedingMethodVa": f"0x{pointer:x}" if pointer else None,
                        "reason": "outsideBoundedMappedMethod",
                    })
                    continue
                method_indexes = sorted({
                    int(row["methodIndex"])
                    for row in aliases if row.get("methodIndex") is not None
                })
                if len(method_indexes) != 1:
                    rejected_run_direct_calls.append({
                        "va": f"0x{site:x}",
                        "reason": "ambiguousCallerMethod",
                        "methodIndexes": method_indexes,
                    })
                    continue
                caller_row = full_method_mapper_row(metadata, helper, method_indexes[0])
                caller_body = mapper.build_method_body_summary(
                    caller_row,
                    pe.bytes_at_va(pointer, scan_size),
                    pointer,
                    method_by_pointer,
                    pe=pe,
                    max_instructions=30000,
                )
                decoded_calls = [
                    call for call in caller_body.get("calls") or []
                    if call.get("targetVa") == f"0x{run_va:x}"
                    and int(call.get("offset") or 0) == site - pointer
                ]
                if len(decoded_calls) != 1:
                    rejected_run_direct_calls.append({
                        "va": f"0x{site:x}",
                        "reason": "rawE8NotDecodedAsCallInstruction",
                    })
                    continue
                symbol = f"{caller_row['type']}.{caller_row['method']}"
                decoded_caller_bodies[symbol] = caller_body
                caller = {
                    "symbol": symbol,
                    "callerVa": f"0x{pointer:x}",
                    "callVa": f"0x{site:x}",
                    "callOffset": site - pointer,
                    **decode_direct_enum_argument(decoded_calls[0], "r8", enum_values),
                }
                run_quest_action_direct_callers.append(caller)
                if caller.get("questActionValue") == enum_values.get(
                    "OnStartClientAction"
                ):
                    start_action_dispatchers.append(caller)
            safe_origins = {
                str(row.get("origin") or "")
                for row in safe_body.get("fieldAccesses") or []
                if str(row.get("origin") or "").startswith("this+")
            }
            pending_body = decoded_caller_bodies.get(
                "Beyond.Gameplay.MissionSystem.ProcessPendingQuestAction", {}
            )
            pending_origins = {
                str(row.get("origin") or "")
                for row in pending_body.get("fieldAccesses") or []
                if str(row.get("origin") or "").startswith("this+")
            }
            shared_origins = sorted(safe_origins & pending_origins)
            shared_fields = [
                {"origin": origin, "field": field_names_by_origin.get(origin)}
                for origin in shared_origins
            ]
            run_quest_action_flow = {
                "symbol": "Beyond.Gameplay.MissionSystem.RunQuestAction",
                "token": run_aliases[0].get("token"),
                "va": f"0x{run_va:x}",
                "scanBytes": run_next - run_va if isinstance(run_next, int) else None,
                "paramQuestActionFlow": run_param_flow,
                "preservesQuestActionArgument": (
                    any("mov edi, r8d" in text for text in run_flow_text)
                    and any("mov r8d, edi" in text for text in run_flow_text)
                ),
                "sharedPendingCarrier": (
                    len(shared_fields) == 1
                    and shared_fields[0].get("field") == "m_pendingQuestActionList"
                ),
                "sharedPendingFields": shared_fields,
            }

    validation = validate_quest_succeed_action_observation(
        enum_values=enum_values,
        succeed_action_calls=succeed_action_calls,
        safe_run_action_flow=safe_run_action_flow,
        safe_run_direct_callers=safe_run_direct_callers,
        run_quest_action_flow=run_quest_action_flow,
        run_quest_action_direct_callers=run_quest_action_direct_callers,
        start_action_dispatchers=start_action_dispatchers,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
        prior_failures=failures,
    )
    return {
        "schema": "questLifecycleClientAction.v2",
        "classification": "bounded_current_aot_quest_action_dispatch",
        "questActionEnum": enum_values,
        "succeedQuest": {
            "symbol": "Beyond.Gameplay.MissionSystem.SucceedQuest",
            "token": succeed_aliases[0].get("token"),
            "va": f"0x{succeed_va:x}",
            "scanBytes": (
                succeed_next - succeed_va
                if isinstance(succeed_next, int)
                else None
            ),
        },
        "succeedActionCalls": succeed_action_calls,
        "safeRunActionFlow": safe_run_action_flow,
        "safeRunDirectCallers": safe_run_direct_callers,
        "runQuestActionFlow": run_quest_action_flow,
        "runQuestActionDirectCallers": run_quest_action_direct_callers,
        "startActionDispatchers": start_action_dispatchers,
        "rejectedDirectCallCandidates": rejected_direct_calls,
        "rejectedRunDirectCallCandidates": rejected_run_direct_calls,
        "finding": (
            "The current fallback SucceedQuest and FailQuest paths pass QuestAction "
            "values 2 and 4 through SafeRunQuestAction. ProcessPendingQuestAction "
            "only replays that same typed pending carrier into RunQuestAction. The "
            "complete bounded direct-caller census finds no current AOT producer for "
            "OnStartClientAction value 1."
        ),
        "boundary": (
            "Authored slot-1 rows remain definitions without a current fallback AOT "
            "dispatch path; indirect native invocation, reflection, runtime memory "
            "mutation, future IFix, server behavior, and future builds remain outside "
            "this static proof. Success/failure dispatch does not choose a successor "
            "arm or order Story rows without an independent typed action path."
        ),
        "validation": validation,
    }


def quest_state_lifecycle_application_contract(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    rows: list[dict[str, Any]],
    mapped_bodies: dict[str, dict[str, Any]],
    decoded_instructions: dict[str, list[dict[str, Any]]],
    gameassembly_path: Path,
) -> dict[str, Any]:
    """Recover the state-gated quest lifecycle calls from packet field shape."""
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }
    candidates = [
        row for row in rows
        if row.get("entityKind") == "quest"
        and row.get("controlKind") == "state_update"
        and len(row.get("consumedControlFields") or []) == 1
    ]
    failures: list[dict[str, Any]] = []
    enum_values: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    enum_type = ""
    candidate = candidates[0] if len(candidates) == 1 else None
    if candidate is not None:
        state_field = str(candidate.get("stateField") or "")
        expected_enum_name = state_field[:1].upper() + state_field[1:]
        enum_type_candidates = [
            metadata.type_full_name(type_def)
            for type_def in metadata.types
            if metadata.type_full_name(type_def).rsplit(".", 1)[-1]
            == expected_enum_name
        ]
        if len(enum_type_candidates) == 1:
            enum_type = enum_type_candidates[0]
            enum_values = il2cpp.enum_members(metadata, defaults, enum_type)
        else:
            failures.append({
                "validator": "quest_state_lifecycle_application",
                "gate": "uniqueStateEnumType",
                "message": candidate.get("type"),
                "expected": 1,
                "actual": enum_type_candidates,
                "sourceFile": str(gameassembly_path.resolve()),
                "sourceHashes": source_hashes,
            })
        expected_origin = (
            f"param:msg+{candidate.get('fieldOffsets', {}).get(state_field)}"
        )
        body = mapped_bodies.get(str(candidate.get("type") or "")) or {}
        for access in body.get("fieldAccesses") or []:
            if access.get("origin") != expected_origin:
                continue
            text = str(access.get("text") or "")
            match = re.fullmatch(
                r"cmp\s+\[[^]]+\],\s*0x([0-9a-f]+)",
                text,
                re.I,
            )
            if not match:
                continue
            comparisons.append({
                "offset": int(access.get("offset") or 0),
                "text": text,
                "value": int(match.group(1), 16),
            })
        method_va = int(str((candidate.get("handler") or {}).get("va") or "0"), 16)
        routes = constrained_enum_lifecycle_routes(
            decoded_instructions.get(str(candidate.get("type") or "")) or [],
            comparisons,
            candidate.get("lifecycleCalls") or [],
            enum_values,
            method_va=method_va,
        )
    validation = validate_quest_state_lifecycle_application(
        candidate_rows=candidates,
        enum_values=enum_values,
        comparisons=comparisons,
        routes=routes,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
        prior_failures=failures,
    )
    transitions = [
        row for row in routes if row.get("reachableLifecycleCalls")
    ]
    return {
        "schema": "questStateLifecycleApplication.v1",
        "classification": "server_selected_quest_identity_state_transition",
        "discoveryPattern": {
            "message": (
                "unique quest identity+state server packet from the generic "
                "state-update census"
            ),
            "enum": "unique metadata enum whose type name matches the state field",
            "controlFlow": (
                "exact packet-field comparisons constrain direct native CFG edges; "
                "all unrelated conditional edges remain possible"
            ),
        },
        "message": ({
            "type": candidate.get("type"),
            "messageId": candidate.get("messageId"),
            "identityField": candidate.get("identityField"),
            "stateField": candidate.get("stateField"),
            "fields": candidate.get("fields") or [],
            "successorLikeFields": candidate.get("successorLikeFields") or [],
            "handler": candidate.get("handler") or {},
        } if candidate else {}),
        "stateEnum": {
            "type": enum_type,
            "values": enum_values,
        },
        "stateComparisons": comparisons,
        "transitions": transitions,
        "statesWithoutDirectLifecycleCall": [
            {"state": row.get("state"), "stateName": row.get("stateName")}
            for row in routes if not row.get("reachableLifecycleCalls")
        ],
        "finding": (
            "The native handler constrains the exact server-supplied questState field "
            "before applying distinct lifecycle calls to the same packet questId. "
            "The packet has no successor identity field, so each recovered fork arm "
            "is activated only after the server supplies that arm's quest identity."
        ),
        "boundary": (
            "This recovers client-side application of a server-selected quest identity "
            "and state. It does not recover the server-only arm-selection policy, prove "
            "that sibling arms are exclusive, or order Story files within an arm. "
            "States without a direct call here may be handled by other packets or paths."
        ),
        "validation": validation,
    }


def quest_enable_lifecycle_application_contract(
    metadata: Any,
    pe: Any,
    metadata_summary: dict[str, Any],
    rows: list[dict[str, Any]],
    mapped_bodies: dict[str, dict[str, Any]],
    decoded_instructions: dict[str, list[dict[str, Any]]],
    gameassembly_path: Path,
) -> dict[str, Any]:
    """Recover packet-enable/runtime-pause lifecycle routing by field shape."""
    source_hashes = {
        "gameAssemblySha256": file_sha256(gameassembly_path),
        "metadataSha256": hashlib.sha256(metadata.buf).hexdigest(),
    }
    candidates = [
        row for row in rows
        if row.get("entityKind") == "quest"
        and row.get("controlKind") == "enable_update"
        and len(row.get("identityFields") or []) == 1
    ]
    failures: list[dict[str, Any]] = []
    packet_field = ""
    runtime_field = ""
    runtime_owner = ""
    runtime_field_type = ""
    runtime_offset: int | None = None
    packet_predicates: list[dict[str, Any]] = []
    runtime_predicates: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    unread_control_fields: list[str] = []
    candidate = candidates[0] if len(candidates) == 1 else None

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "quest_enable_lifecycle_application",
            "gate": gate,
            "message": candidate.get("type") if candidate else None,
            "expected": expected,
            "actual": actual,
            "sourceFile": str(gameassembly_path.resolve()),
            "sourceHashes": source_hashes,
        })

    if candidate is not None:
        body = mapped_bodies.get(str(candidate.get("type") or "")) or {}
        instructions = decoded_instructions.get(str(candidate.get("type") or "")) or []
        field_accesses = body.get("fieldAccesses") or []
        packet_fields = [
            name for name in candidate.get("controlFields") or []
            if any(
                access.get("origin")
                == f"param:msg+{candidate.get('fieldOffsets', {}).get(name)}"
                for access in field_accesses
            )
        ]
        unread_control_fields = [
            name for name in candidate.get("controlFields") or []
            if name not in packet_fields
        ]
        if len(packet_fields) == 1:
            packet_field = packet_fields[0]
        else:
            fail("uniqueConsumedPacketControl", 1, packet_fields)
        packet_origin = (
            f"param:msg+{candidate.get('fieldOffsets', {}).get(packet_field)}"
            if packet_field else ""
        )
        packet_reads = [
            access for access in field_accesses
            if access.get("kind") == "read"
            and access.get("origin") == packet_origin
        ]
        runtime_reads: list[tuple[dict[str, Any], str, int, str, str]] = []
        runtime_types_va = int(metadata_summary["types"], 16)
        runtime_type_count = int(metadata_summary["typesCount"])
        for access in field_accesses:
            if access.get("kind") != "read":
                continue
            origin = str(access.get("origin") or "")
            match = re.fullmatch(r"return:(.+)\+0x([0-9a-f]+)", origin, re.I)
            if not match:
                continue
            owner_name = match.group(1)
            field_offset = int(match.group(2), 16)
            owner_types = [
                type_def for type_def in metadata.types
                if metadata.type_full_name(type_def) == owner_name
            ]
            if len(owner_types) != 1:
                continue
            try:
                offsets = il2cpp.runtime_type_field_offsets(
                    metadata,
                    pe,
                    metadata_summary,
                    owner_types[0].index,
                )
            except RuntimeError as exc:
                fail(
                    "runtimeFieldOffsetResolution",
                    "current MetadataRegistration field-offset row",
                    {"ownerType": owner_name, "error": str(exc)},
                )
                continue
            for field_def in metadata.fields_for(owner_types[0]):
                field_name = metadata.string(field_def.name_index)
                if offsets.get(field_name) != field_offset:
                    continue
                if not 0 <= field_def.type_index < runtime_type_count:
                    continue
                type_va = pe.u64_at_va(runtime_types_va + field_def.type_index * 8)
                field_type = il2cpp.runtime_type_name(pe, metadata, type_va)
                if field_type == "bool":
                    runtime_reads.append(
                        (access, owner_name, field_offset, field_name, field_type)
                    )
        if len(packet_reads) != 1:
            fail("uniquePacketControlRead", 1, packet_reads)
        if len(runtime_reads) != 1:
            fail("uniqueRuntimeBooleanRead", 1, runtime_reads)
        if len(runtime_reads) == 1:
            (
                runtime_access,
                runtime_owner,
                runtime_offset,
                runtime_field,
                runtime_field_type,
            ) = runtime_reads[0]
        method_va = int(str((candidate.get("handler") or {}).get("va") or "0"), 16)
        if len(packet_reads) == 1 and packet_field:
            packet_predicates = discover_boolean_field_predicates(
                instructions,
                field=packet_field,
                field_read_offset=int(packet_reads[0].get("offset") or 0),
                method_va=method_va,
            )
        if len(runtime_reads) == 1 and runtime_field:
            runtime_predicates = discover_boolean_field_predicates(
                instructions,
                field=runtime_field,
                field_read_offset=int(runtime_reads[0][0].get("offset") or 0),
                method_va=method_va,
            )
        if packet_field and runtime_field:
            scenarios = [
                {
                    "values": {
                        packet_field: enabled,
                        runtime_field: paused,
                    },
                }
                for enabled in (False, True)
                for paused in (False, True)
            ]
            routes = constrained_lifecycle_routes(
                instructions,
                [*packet_predicates, *runtime_predicates],
                candidate.get("lifecycleCalls") or [],
                scenarios,
                method_va=method_va,
            )
    validation = validate_quest_enable_lifecycle_application(
        candidate_rows=candidates,
        packet_predicates=packet_predicates,
        runtime_predicates=runtime_predicates,
        routes=routes,
        unread_control_fields=unread_control_fields,
        packet_field=packet_field,
        runtime_field=runtime_field,
        source_file=str(gameassembly_path.resolve()),
        source_hashes=source_hashes,
        prior_failures=failures,
    )
    return {
        "schema": "questEnableLifecycleApplication.v1",
        "classification": "server_selected_quest_enable_local_pause_application",
        "discoveryPattern": {
            "message": (
                "unique quest identity+enable server packet from the generic "
                "state-update census"
            ),
            "runtimeField": (
                "unique exact returned-object Boolean field read resolved through "
                "the current MetadataRegistration field-offset and runtime-type tables"
            ),
            "controlFlow": (
                "live boolean register provenance into exact zero/nonzero native "
                "branches, followed by the shared constrained CFG solver"
            ),
        },
        "message": ({
            "type": candidate.get("type"),
            "messageId": candidate.get("messageId"),
            "identityField": candidate.get("identityField"),
            "controlFields": candidate.get("controlFields") or [],
            "consumedControlFields": [packet_field] if packet_field else [],
            "unreadControlFields": unread_control_fields,
            "fields": candidate.get("fields") or [],
            "successorLikeFields": candidate.get("successorLikeFields") or [],
            "handler": candidate.get("handler") or {},
        } if candidate else {}),
        "runtimeControl": {
            "ownerType": runtime_owner,
            "field": runtime_field,
            "type": runtime_field_type,
            "offset": f"0x{runtime_offset:x}" if runtime_offset is not None else None,
        },
        "packetPredicates": packet_predicates,
        "runtimePredicates": runtime_predicates,
        "routes": routes,
        "finding": (
            "The quest-enable handler routes the same server-supplied questId by the "
            "packet enable flag and the exact current QuestData pause flag. Enabling "
            "starts an unpaused quest but preserves a paused quest through PauseQuest; "
            "disabling reaches DisableQuest for either pause value. The serialized "
            "previous-state field is not read by this handler."
        ),
        "boundary": (
            "This proves client-side enable/pause/disable application after the server "
            "selects a quest identity. It does not recover server arm eligibility, "
            "successor selection, sibling exclusivity, or Story-file order. Other "
            "runtime state mutations and server policy remain outside this static path."
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
    mapper = il2cpp.load_native_mapper(mapper_path)
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
    mapped_bodies: dict[str, dict[str, Any]] = {}
    decoded_instructions: dict[str, list[dict[str, Any]]] = {}

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
            all_offsets = il2cpp.runtime_type_field_offsets(
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
        mapped_bodies[candidate["type"]] = body
        method_va = int(mapped["va"], 16)
        decoded_instructions[candidate["type"]] = mapper.decode_x64_subset(
            pe.bytes_at_va(method_va, int(mapped["scanBytes"])),
            method_va,
            stop_offset=int(mapped["scanBytes"]),
        )
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
            if il2cpp.normalized_field_name(field["name"]) in {"missionid", "questid"}
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
    quest_state_lifecycle = quest_state_lifecycle_application_contract(
        metadata,
        defaults,
        rows,
        mapped_bodies,
        decoded_instructions,
        gameassembly_path,
    )
    quest_enable_lifecycle = quest_enable_lifecycle_application_contract(
        metadata,
        pe,
        metadata_summary,
        rows,
        mapped_bodies,
        decoded_instructions,
        gameassembly_path,
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
    quest_succeed = quest_succeed_action_contract(
        metadata,
        defaults,
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
        defaults,
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
        "questStateLifecycleApplication": quest_state_lifecycle,
        "questEnableLifecycleApplication": quest_enable_lifecycle,
        "questStartApplication": quest_start,
        "questSucceedActionApplication": quest_succeed,
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
            il2cpp.normalized_field_name(type_name.removeprefix("Proto."))
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
    task_contract_path: Path = MISSION_TASK_PATH_CONTRACT,
    mission_runtime_root: Path = MISSION_RUNTIME_ROOT,
    levelscript_roots: tuple[Path, ...] = LEVELSCRIPT_ROOTS,
) -> dict[str, Any]:
    helper = il2cpp.load_metadata_helper(helper_path)
    metadata = helper.Metadata(metadata_path)
    defaults = il2cpp.field_defaults(metadata)
    native_task_paths = load_mission_task_paths(task_contract_path)
    mission_event_assets = mission_event_asset_coverage(
        mission_runtime_root,
        levelscript_roots,
        levelscript_native_header_contract(
            file_sha256(gameassembly_path),
            file_sha256(metadata_path),
        ),
    )
    cs = il2cpp.enum_members(metadata, defaults, "Proto.CSMessageID")
    sc = il2cpp.enum_members(metadata, defaults, "Proto.SCMessageID")
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
    extra_thread_scheduler_census = action_extra_thread_scheduler_census(
        metadata,
        helper,
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
    task_lifecycle_contract = levelscript_task_lifecycle_contract(
        metadata,
        defaults,
        helper,
        gameassembly_path,
        mapper_path,
        metadata_path,
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
        "_schema": "endfieldProtocolRegistryAudit.v20",
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
            "nativeTaskContract": native_task_paths["source"],
            "nativeTaskContractSha256": native_task_paths["sha256"],
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
            "questActionDispatchValidated": (
                (state_application_census["questSucceedActionApplication"].get(
                    "validation"
                ) or {}).get("status")
                == "validated"
            ),
            "questActionStartDispatchers": len(
                state_application_census["questSucceedActionApplication"].get(
                    "startActionDispatchers"
                ) or []
            ),
            "topologyActivePredecessorConsumers": state_application_census[
                "questTopologyFieldConsumers"
            ].get("activePredecessorConsumerCount", 0),
            "topologyFlowIndexNonSortConsumers": state_application_census[
                "questTopologyFieldConsumers"
            ].get("flowIndexNonSortConsumerCount", 0),
            "topologyLifecycleCalls": len(state_application_census[
                "questTopologyFieldConsumers"
            ].get("topologyLifecycleCalls") or []),
            "questTypeConsumers": (
                state_application_census["questTopologyFieldConsumers"]
                ["questSemanticFields"]["questType"]["consumerCount"]
            ),
            "questTypePostLifecycleConsumers": (
                state_application_census["questTopologyFieldConsumers"]
                ["questSemanticFields"]["questType"]
                ["postLifecycleConsumerCount"]
            ),
            "questTypeBlockNotificationConsumers": (
                state_application_census["questTopologyFieldConsumers"]
                ["questSemanticFields"]["questType"]
                ["blockNotificationConsumerCount"]
            ),
            "questOptionalObjectiveFlagValidated": (
                state_application_census["questTopologyFieldConsumers"]
                ["questSemanticFields"]["optionalObjectiveFlag"]
                ["validation"]["status"]
                == "validated"
            ),
            "questShowModeConsumers": (
                state_application_census["questTopologyFieldConsumers"]
                ["questSemanticFields"]["showMode"]["consumerCount"]
            ),
            "questShowModeLifecycleConsumers": (
                state_application_census["questTopologyFieldConsumers"]
                ["questSemanticFields"]["showMode"]
                ["lifecycleConsumerCount"]
            ),
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
            "levelScriptTaskLifecycleValidated": (
                (task_lifecycle_contract.get("validation") or {}).get("status")
                == "validated"
            ),
            "actionExtraThreadWriterMethods": len(
                extra_thread_scheduler_census["extraThreadExecuteMethods"]
            ),
            "actionExtraThreadDirectCalls": len(
                extra_thread_scheduler_census["directCalls"]
            ),
            "actionExtraThreadSchedulerValidated": (
                extra_thread_scheduler_census["validation"]["status"]
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
            "questClientActionDispatch": state_application_census[
                "questSucceedActionApplication"
            ]["boundary"],
            "questSemanticFields": state_application_census[
                "questTopologyFieldConsumers"
            ]["questSemanticFields"]["boundary"],
            "actionExtraThreadScheduler": extra_thread_scheduler_census["boundary"],
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
            "levelScriptTaskLifecycle": task_lifecycle_contract["boundary"],
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
        "actionExtraThreadSchedulerCensus": extra_thread_scheduler_census,
        "levelScriptStartPolicy": start_policy_contract,
        "levelScriptManualSelfControl": manual_self_control_contract,
        "levelScriptActivationControl": activation_control_contract,
        "levelScriptTaskLifecycle": task_lifecycle_contract,
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
            "- Quest lifecycle dispatch census: "
            f"**{'validated' if summary['questActionDispatchValidated'] else 'failed'}**; "
            f"**{summary['questActionStartDispatchers']}** current AOT start-action dispatchers"
        ),
        (
            "- Action extra-thread composite writers: "
            f"**{summary['actionExtraThreadWriterMethods']}** methods / "
            f"**{summary['actionExtraThreadDirectCalls']}** direct scheduler calls; "
            f"**{'validated' if summary['actionExtraThreadSchedulerValidated'] else 'failed'}**"
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
        (
            "- Generic LevelScript task-condition lifecycle: "
            f"**{'validated' if summary['levelScriptTaskLifecycleValidated'] else 'failed'}**"
        ),
        f"- Native task-path contract SHA-256: `{report['source']['nativeTaskContractSha256']}`",
        "",
        "## Evidence boundary",
        "",
    ]
    lines.extend(f"- **{md_escape(key)}:** {md_escape(value)}" for key, value in policy.items())
    scheduler = report["actionExtraThreadSchedulerCensus"]
    lines.extend([
        "",
        "## Action extra-thread scheduler",
        "",
        md_escape(scheduler["finding"]),
        "",
        "| Execute method | Writer shape | Token | VA | Child fields |",
        "|---|---|---|---|---|",
    ])
    for row in scheduler["extraThreadExecuteMethods"]:
        child_fields = ", ".join(
            f"{field.get('field')}@{field.get('offset')}"
            for field in row.get("typedChildFields") or []
        )
        lines.append(
            f"| `{md_escape(row.get('symbol', ''))}` | "
            f"`{md_escape(row.get('writerShape', ''))}` | "
            f"`{md_escape(row.get('token', ''))}` | "
            f"`{md_escape(row.get('va', ''))}` | "
            f"{md_escape(child_fields)} |"
        )
    lines.extend([
        "",
        (
            f"Complete direct-call census: **{len(scheduler['directCalls'])}** "
            f"decoded / **{len(scheduler['rejectedDirectCalls'])}** rejected."
        ),
        "",
        md_escape(scheduler["boundary"]),
    ])
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
    task_lifecycle = report.get("levelScriptTaskLifecycle") or {}
    lines.extend([
        "",
        "## Generic LevelScript task lifecycle",
        "",
        md_escape(task_lifecycle.get("finding") or "[task lifecycle unavailable]"),
        "",
        (
            "Application chain: "
            + " -> ".join(
                f"`{md_escape(str(symbol))}`"
                for symbol in task_lifecycle.get("serverStateApplicationChain") or []
            )
        ),
        "",
        (
            "Processing-time condition operations: "
            + ", ".join(
                f"`{md_escape(str(symbol))}`"
                for symbol in task_lifecycle.get("conditionProcessingOperations") or []
            )
        ),
        "",
        md_escape(task_lifecycle.get("boundary") or ""),
    ])
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
    level_events = report["nativeLevelScriptEventPaths"]
    level_event = level_events.get(57) or level_events["57"]
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
    quest_state_lifecycle = state_census.get("questStateLifecycleApplication") or {}
    quest_enable_lifecycle = state_census.get("questEnableLifecycleApplication") or {}
    quest_succeed = state_census.get("questSucceedActionApplication") or {}
    quest_fields = quest_start.get("questInfoFieldOffsets") or {}
    quest_reads = quest_start.get("fieldReadCounts") or {}
    topology = state_census.get("questTopologyFieldConsumers") or {}
    quest_semantics = topology.get("questSemanticFields") or {}
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
    public_state_sources = activation_control.get("publicStateSourceFlow") or {}
    subgame_flow = activation_control.get("subGameInteractionFlow") or {}
    client_request_flow = activation_control.get("clientRequestFlow") or {}
    lines.extend(
        [
            "",
            state_census["boundary"],
            "",
            "### Quest state lifecycle application",
            "",
            quest_state_lifecycle.get("finding")
            or "[quest-state lifecycle audit unavailable]",
            "",
            "| Server state | Native lifecycle calls |",
            "|---|---|",
            *[
                "| `{name}` ({value}) | {calls} |".format(
                    name=md_escape(str(route.get("stateName") or "?")),
                    value=route.get("state"),
                    calls=", ".join(
                        f"`{md_escape(str(call.get('method') or '?'))}`"
                        for call in route.get("reachableLifecycleCalls") or []
                    ),
                )
                for route in quest_state_lifecycle.get("transitions") or []
            ],
            "",
            quest_state_lifecycle.get("boundary") or "",
            "",
            "### Quest enable/pause application",
            "",
            quest_enable_lifecycle.get("finding")
            or "[quest-enable lifecycle audit unavailable]",
            "",
            "| Packet enable | Current pause | Native lifecycle call |",
            "|---|---|---|",
            *[
                "| `{enable}` | `{paused}` | {calls} |".format(
                    enable=route.get("values", {}).get("isEnable"),
                    paused=route.get("values", {}).get("isPaused"),
                    calls=", ".join(
                        f"`{md_escape(str(call.get('method') or '?'))}`"
                        for call in route.get("reachableLifecycleCalls") or []
                    ),
                )
                for route in quest_enable_lifecycle.get("routes") or []
            ],
            "",
            (
                "Serialized but unread packet controls: "
                + ", ".join(
                    f"`{md_escape(str(field))}`"
                    for field in (
                        quest_enable_lifecycle.get("message", {}).get(
                            "unreadControlFields"
                        )
                        or []
                    )
                )
                + "."
            ),
            "",
            quest_enable_lifecycle.get("boundary") or "",
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
            "### Quest client-action dispatch",
            "",
            quest_succeed.get("finding") or "[quest action audit unavailable]",
            "",
            (
                "Validated success action: **{action}**; SafeRun callers: **{safe_callers}**; "
                "RunQuestAction callers: **{run_callers}**; start-action dispatchers: "
                "**{start_callers}**."
            ).format(
                action=(
                    (quest_succeed.get("succeedActionCalls") or [{}])[0].get(
                        "questActionName", "?"
                    )
                ),
                safe_callers=len(quest_succeed.get("safeRunDirectCallers") or []),
                run_callers=len(quest_succeed.get("runQuestActionDirectCallers") or []),
                start_callers=len(quest_succeed.get("startActionDispatchers") or []),
            ),
            "",
            quest_succeed.get("boundary") or "",
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
            "### Quest type and visibility semantics",
            "",
            quest_semantics.get("finding") or "[quest semantic-field audit unavailable]",
            "",
            (
                "Quest types: {quest_types}; show modes: {show_modes}; "
                "post-lifecycle questType consumers: **{post_count}**; "
                "showMode lifecycle consumers: **{show_lifecycle}**."
            ).format(
                quest_types=", ".join(
                    f"`{row.get('name')}={row.get('id')}`"
                    for row in (quest_semantics.get("questType") or {}).get(
                        "values", []
                    )
                ),
                show_modes=", ".join(
                    f"`{row.get('name')}={row.get('id')}`"
                    for row in (quest_semantics.get("showMode") or {}).get(
                        "values", []
                    )
                ),
                post_count=(quest_semantics.get("questType") or {}).get(
                    "postLifecycleConsumerCount", 0
                ),
                show_lifecycle=(quest_semantics.get("showMode") or {}).get(
                    "lifecycleConsumerCount", 0
                ),
            ),
            "",
            quest_semantics.get("boundary") or "",
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
                "Full-scene message `SC_SELF_SCENE_INFO` ({snapshot_id}) carries "
                "tag 8 as `{snapshot_type}`; each `LEVEL_SCRIPT_INFO` row supplies "
                "scriptId/state/properties/isDone/stage/triggerVolumeInfos to "
                "`LevelScriptRuntime.ServerSync`. Incremental message `{message}` "
                "({message_id}) carries only "
                "`sceneNumId`, `scriptId`, `state`, and `isComplete`; its native "
                "handler reaches `LevelScriptRuntime.UpdateState` through three "
                "typed wrappers, then calls `set_state` before "
                "`UpdateRuntimeState`."
            ).format(
                snapshot_id=public_state_sources.get("snapshotMessageId", "?"),
                snapshot_type=md_escape(str(
                    public_state_sources.get("snapshotLevelScriptsRuntimeType")
                    or "?"
                )),
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
                "public-state entry handlers: **{entry_count}**; direct state writers: "
                "**{writer_count}**; SubGame id/bindScriptId field reads validated: "
                "**{fields}**."
            ).format(
                count=len(activation_control.get("manualStartDirectCallers") or []),
                ordered=activation_state_flow.get(
                    "setterBeforeRuntimeEvaluation", False
                ),
                entry_count=len(
                    public_state_sources.get("managerStateShortDirectCallers") or []
                ),
                writer_count=len(
                    public_state_sources.get("publicStateSetterDirectCallers") or []
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
            "Reuse an existing validated v20 report when its original "
            "GameAssembly, metadata, and task-contract hashes still match; "
            "otherwise rebuild it."
        ),
    )
    return parser.parse_args()


def current_report_status(
    report_path: Path,
    metadata_path: Path,
    gameassembly_path: Path,
    *,
    measured_hashes: dict[str, str] | None = None,
    task_contract_path: Path = MISSION_TASK_PATH_CONTRACT,
) -> tuple[bool, str]:
    """Fail closed unless a report describes these exact original inputs.

    ``measured_hashes`` lets a caller that already hashed the installed client
    reuse those digests instead of re-reading ~340 MB of binaries.
    """
    if not report_path.is_file():
        return False, "report missing"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"report unreadable: {exc}"
    if report.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        return False, f"schema is {report.get('_schema')!r}"
    scheduler_validation = (
        (report.get("actionExtraThreadSchedulerCensus") or {}).get("validation")
        or {}
    )
    if scheduler_validation.get("status") != "validated":
        return False, (
            "action-extra-thread validation is "
            f"{scheduler_validation.get('status')!r}"
        )
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
    quest_state_lifecycle_validation = (
        ((report.get("stateUpdateApplicationCensus") or {}).get(
            "questStateLifecycleApplication"
        ) or {}).get("validation") or {}
    )
    if quest_state_lifecycle_validation.get("status") != "validated":
        return False, (
            "quest-state lifecycle validation is "
            f"{quest_state_lifecycle_validation.get('status')!r}"
        )
    quest_enable_lifecycle_validation = (
        ((report.get("stateUpdateApplicationCensus") or {}).get(
            "questEnableLifecycleApplication"
        ) or {}).get("validation") or {}
    )
    if quest_enable_lifecycle_validation.get("status") != "validated":
        return False, (
            "quest-enable lifecycle validation is "
            f"{quest_enable_lifecycle_validation.get('status')!r}"
        )
    quest_succeed_validation = (
        ((report.get("stateUpdateApplicationCensus") or {}).get(
            "questSucceedActionApplication"
        ) or {}).get("validation") or {}
    )
    if quest_succeed_validation.get("status") != "validated":
        return False, (
            "quest-action-dispatch validation is "
            f"{quest_succeed_validation.get('status')!r}"
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
    semantic_validation = (
        (((report.get("stateUpdateApplicationCensus") or {}).get(
            "questTopologyFieldConsumers"
        ) or {}).get("questSemanticFields") or {}).get("validation") or {}
    )
    if semantic_validation.get("status") != "validated":
        return False, (
            "quest-semantic-field validation is "
            f"{semantic_validation.get('status')!r}"
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
    task_lifecycle_validation = (
        (report.get("levelScriptTaskLifecycle") or {}).get("validation") or {}
    )
    if task_lifecycle_validation.get("status") != "validated":
        return False, (
            "LevelScript task-lifecycle validation is "
            f"{task_lifecycle_validation.get('status')!r}"
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
        actual = (measured_hashes or {}).get(hash_key) or file_sha256(source_path)
        if actual != expected:
            return False, f"{hash_key} differs: expected={expected!r} actual={actual!r}"
    expected_contract = str(source.get("nativeTaskContractSha256") or "").lower()
    if not task_contract_path.is_file():
        return False, f"source missing: {task_contract_path}"
    actual_contract = file_sha256(task_contract_path)
    if actual_contract != expected_contract:
        return False, (
            "nativeTaskContractSha256 differs: "
            f"expected={expected_contract!r} actual={actual_contract!r}"
        )
    return True, "validated report hashes match original inputs"


def main() -> int:
    args = parse_args()
    native = check_installed_native_inputs(
        gameassembly=args.gameassembly,
        metadata=args.metadata,
    )
    if not native.validated:
        required = native_evidence_required()
        print(
            native_evidence_skip_message(
                "protocol-registry", native, required=required
            ),
            file=sys.stderr,
        )
        return 1 if required else 0
    if not args.helper.is_file():
        raise SystemExit(f"metadata helper not found: {args.helper}")
    if not args.native_mapper.is_file():
        raise SystemExit(f"native mapper not found: {args.native_mapper}")
    if args.ensure_current:
        is_current, reason = current_report_status(
            args.json_output,
            args.metadata,
            args.gameassembly,
            measured_hashes={
                "metadataSha256": native.metadata_sha256,
                "gameAssemblySha256": native.gameassembly_sha256,
            },
        )
        if is_current:
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
    try:
        report = build_report(
            args.metadata,
            args.helper,
            gameassembly_path=args.gameassembly,
            mapper_path=args.native_mapper,
            mission_runtime_root=args.mission_runtime_root,
        )
    except il2cpp.load_metadata_helper(args.helper).MetadataParseError as exc:
        # Re-deriving the registry is how a different client build is
        # supported; metadata this parser cannot read is a real stop.
        print(
            f"[protocol-registry] cannot read {args.metadata}: {exc}",
            file=sys.stderr,
        )
        return 1
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
    quest_state_lifecycle_validation = report["stateUpdateApplicationCensus"][
        "questStateLifecycleApplication"
    ]["validation"]
    if quest_state_lifecycle_validation["status"] != "validated":
        first = quest_state_lifecycle_validation["failures"][0]
        print(
            "quest-state lifecycle validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"message={first.get('message')} expected={first['expected']!r} "
            f"actual={first['actual']!r} source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    quest_enable_lifecycle_validation = report["stateUpdateApplicationCensus"][
        "questEnableLifecycleApplication"
    ]["validation"]
    if quest_enable_lifecycle_validation["status"] != "validated":
        first = quest_enable_lifecycle_validation["failures"][0]
        print(
            "quest-enable lifecycle validator failed: "
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
    quest_succeed_validation = report["stateUpdateApplicationCensus"][
        "questSucceedActionApplication"
    ]["validation"]
    if quest_succeed_validation["status"] != "validated":
        first = quest_succeed_validation["failures"][0]
        print(
            "quest-succeed-action validator failed: "
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
    semantic_validation = report["stateUpdateApplicationCensus"][
        "questTopologyFieldConsumers"
    ]["questSemanticFields"]["validation"]
    if semantic_validation["status"] != "validated":
        first = semantic_validation["failures"][0]
        print(
            "quest-semantic-field validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"message={first.get('message')} expected={first['expected']!r} "
            f"actual={first['actual']!r} source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    scheduler_validation = report["actionExtraThreadSchedulerCensus"]["validation"]
    if scheduler_validation["status"] != "validated":
        first = scheduler_validation["failures"][0]
        print(
            "action-extra-thread validator failed: "
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
    task_lifecycle_validation = report["levelScriptTaskLifecycle"]["validation"]
    if task_lifecycle_validation["status"] != "validated":
        first = task_lifecycle_validation["failures"][0]
        print(
            "LevelScript task-lifecycle validator failed: "
            f"validator={first['validator']} gate={first['gate']} "
            f"expected={first['expected']!r} actual={first['actual']!r} "
            f"source={first['sourceFile']}",
            file=sys.stderr,
        )
        return 1
    print(
        f"wrote {args.json_output} and {args.markdown_output}: "
        f"{report['summary']['totalMessages']} messages, "
        f"{report['summary']['selectedSchemas']} selected schemas, "
        f"{report['summary']['stateUpdateApplicationCandidatesValidated']}/"
        f"{report['summary']['stateUpdateApplicationCandidates']} state-update paths validated, "
        "LevelScript start policy, manual self-control, activation control, task "
        "lifecycle, and ActionBase extra-thread scheduler validated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
