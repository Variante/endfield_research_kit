#!/usr/bin/env python3
"""Write a focused GameAssembly body audit for LevelScript recovery.

This follows the metadata-only LevelScript action audit with a small static
body-target pass. It maps the relevant IL2CPP method indexes to
GameAssembly.dll, then keeps only the compact facts needed for mission timeline
recovery: manual start/end calls, property getter reads, property-change
listener registration, and the runtime property update/reset path.

Output:

    reports/mission_order/levelscript_action_body_targets_gameassembly.json
    reports/mission_order/levelscript_action_body_targets_gameassembly.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
BODY_HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_CATALOG_TMP = ROOT / "tmp" / "story" / "mission_order" / "levelscript_action_body_catalog.json"

RUNTIME_EXACT_NAMES = {
    "Beyond.Gameplay.Actions.Set`1",
    "Beyond.Gameplay.Actions.SetList`1",
    "Beyond.Gameplay.Actions.SetBool",
    "Beyond.Gameplay.Actions.SetInt",
    "Beyond.Gameplay.Actions.SetFloat",
    "Beyond.Gameplay.Actions.SetString",
    "Beyond.Gameplay.Actions.SetListBool",
    "Beyond.Gameplay.Actions.SetListInt",
    "Beyond.Gameplay.Actions.SetListFloat",
    "Beyond.Gameplay.Actions.SetListString",
    "Beyond.Gameplay.Actions.ManualStartLevelScript",
    "Beyond.Gameplay.Actions.ManualEndLevelScript",
    "Beyond.Gameplay.Actions.Branch",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyBool",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyInt",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyFloat",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyEntityPtrList",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericBool",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericInt",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericFloat",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericString",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericPropertyPath",
    "Beyond.Gameplay.Actions.GetLevelScriptPropertyGenericLevelScriptPtr",
    "Beyond.Gameplay.Actions.SetLevelScriptPtr",
    "Beyond.Gameplay.Actions.SetPropertyPath",
    "Beyond.Gameplay.Actions.SetListLevelScriptPtr",
    "Beyond.Gameplay.Actions.SetListPropertyPath",
    "Beyond.Gameplay.Actions.ActionHeader",
    "Beyond.Gameplay.Actions.ScriptEventHeader",
    "Beyond.Gameplay.Actions.ActionMapAssetRaw",
    "Beyond.Gameplay.Actions.ActionMapAsset",
    "Beyond.Gameplay.Actions.ActionMapRuntime",
    "Beyond.Gameplay.Actions.ActionSerializedMap",
    "Beyond.Gameplay.Actions.CheckLevelScriptState",
    "Beyond.Gameplay.Actions.CheckLevelScriptStage",
    "Beyond.Gameplay.Actions.CheckMissionOrQuestIsComplete",
    "Beyond.Gameplay.Actions.ScriptEvent.OnPropertyChanged",
    "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolume",
    "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderLeaveTriggerVolume",
    "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolumeList",
    "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderLeaveTriggerVolumeList",
    "Beyond.Gameplay.CheckLevelScriptPropertyBool",
    "Beyond.Gameplay.CheckLevelScriptPropertyInt",
    "Beyond.Gameplay.CheckLevelScriptPropertyString",
    "Beyond.Gameplay.ParamBlackboard",
    "Beyond.Gameplay.ParamVariable",
    "Beyond.Gameplay.Actions.ParamExtensions",
    "Beyond.Gameplay.Actions.Param`1",
    "Beyond.Gameplay.Core.LevelScriptManager",
    "Beyond.Gameplay.Core.LevelScriptModule",
    "Beyond.Gameplay.Core.LevelScriptRuntime",
    "Beyond.Gameplay.LevelData",
    "Beyond.Gameplay.LevelScriptBriefData",
    "Beyond.Gameplay.LevelScriptData",
}

MEMORYPACK_NAME_PARTS = (
    "SetBool",
    "SetInt",
    "SetFloat",
    "SetString",
    "Set_bool",
    "Set_int",
    "Set_float",
    "Set_string",
    "Set_Beyond_Gameplay_Core_LevelScriptPtr",
    "Set_Beyond_PropertyPath",
    "SetListBool",
    "SetListInt",
    "SetListFloat",
    "SetListString",
    "SetList_bool",
    "SetList_int",
    "SetList_float",
    "SetList_string",
    "SetList_Beyond_Gameplay_Core_LevelScriptPtr",
    "SetList_Beyond_PropertyPath",
    "ListSetValue",
    "ManualStartLevelScript",
    "ManualEndLevelScript",
    "BranchForMemoryPack",
    "GetLevelScriptPropertyBool",
    "GetLevelScriptPropertyInt",
    "GetLevelScriptPropertyFloat",
    "GetLevelScriptPropertyEntityPtrList",
    "GetLevelScriptPropertyGeneric_bool",
    "GetLevelScriptPropertyGeneric_int",
    "GetLevelScriptPropertyGeneric_float",
    "GetLevelScriptPropertyGeneric_string",
    "GetLevelScriptPropertyGenericPropertyPath",
    "GetLevelScriptPropertyGenericLevelScriptPtr",
    "SetLevelScriptPtr",
    "SetPropertyPath",
    "SetListLevelScriptPtr",
    "SetListPropertyPath",
    "CheckLevelScriptPropertyBool",
    "CheckLevelScriptPropertyInt",
    "CheckLevelScriptPropertyString",
    "CheckLevelScriptStage",
    "CheckMissionOrQuestIsComplete",
    "ActionHeader",
    "ScriptEventHeader",
    "ActionMapAssetRaw",
    "ActionMapAsset",
    "ActionSerializedMap",
    "ScriptEvent_OnPropertyChanged",
    "ScriptEvent_OnLeaderEnterTriggerVolume",
    "ScriptEvent_OnLeaderLeaveTriggerVolume",
    "ScriptEvent_OnLeaderEnterTriggerVolumeList",
    "ScriptEvent_OnLeaderLeaveTriggerVolumeList",
    "LevelScriptData",
    "LevelScriptBriefData",
)

TARGET_METHOD_RE = re.compile(
    r"^(?:"
    r"CollectParams|Execute|GetResult|Process|Deserialize|"
    r"ManualStart|ManualEnd|OnScriptActive|OnScriptStart|OnScriptEnd|"
    r"OnAfterLevelScriptTriggerRegistered|Tick|TryGetLevelScript|"
    r"TryGetVariable|NewParamVariable|GetParamVariableOrNewOne|"
    r"TryGetProperty|set_properties|get_properties|ModuleResetUpdateProperty|"
    r"RawSetValue|set_rawValue|set____key__|set____value__|"
    r"set____(?:filterLevel|filterMask|filterMode|nextID|priority|targetScript|triggerActiveDuring|triggerTarget|validate)__|"
    r"set___instance|"
    r"set___actionList__|set___getterList__|set___headerList__|"
    r"Invoke.*PropertyChanged|_RaiseOnPropertyChangedEvent|"
    r"Update.*|ResetUpdateProperty|SendLevelScript.*|Set.*|Get.*|Setup|Register.*PropertyChanged"
    r")$"
)

BODY_SUMMARY_RE = (
    "LevelScript|Property|properties|Manual|Execute|GetResult|Process|"
    "Deserialize|CollectParams|TryGet|Update|SendLevelScript|Setup|Tick|OnScript|"
    "ParamBlackboard|ParamVariable|RawSetValue|SetValue|TryGetVariable|"
    "NewParamVariable|GetParamVariableOrNewOne|PropertyChanged|set____|set___instance"
    "|set___actionList__|set___getterList__|set___headerList__"
)

SELECTED_TARGETS = {
    ("Beyond.Gameplay.Actions.Set`1", "CollectParams"),
    ("Beyond.Gameplay.Actions.Set`1", "Execute"),
    ("Beyond.Gameplay.Actions.SetList`1", "CollectParams"),
    ("Beyond.Gameplay.Actions.SetList`1", "Execute"),
    ("Beyond.Gameplay.Actions.GetLevelScriptPropertyBool", "CollectParams"),
    ("Beyond.Gameplay.Actions.GetLevelScriptPropertyBool", "GetResult"),
    ("Beyond.Gameplay.Actions.GetLevelScriptPropertyInt", "CollectParams"),
    ("Beyond.Gameplay.Actions.GetLevelScriptPropertyInt", "GetResult"),
    ("Beyond.Gameplay.Actions.ManualStartLevelScript", "CollectParams"),
    ("Beyond.Gameplay.Actions.ManualStartLevelScript", "Execute"),
    ("Beyond.Gameplay.Actions.ManualEndLevelScript", "CollectParams"),
    ("Beyond.Gameplay.Actions.ManualEndLevelScript", "Execute"),
    ("Beyond.Gameplay.Actions.Branch", "CollectParams"),
    ("Beyond.Gameplay.Actions.Branch", "Execute"),
    ("Beyond.Gameplay.Actions.Branch", "DoClean"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnPropertyChanged", "CollectParams"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnPropertyChanged", "Process"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnPropertyChanged", "OnAfterLevelScriptTriggerRegistered"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolume", "CollectParams"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolume", "Process"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderLeaveTriggerVolume", "CollectParams"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderLeaveTriggerVolume", "Process"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolumeList", "CollectParams"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolumeList", "Process"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderLeaveTriggerVolumeList", "CollectParams"),
    ("Beyond.Gameplay.Actions.ScriptEvent.OnLeaderLeaveTriggerVolumeList", "Process"),
    ("Beyond.Gameplay.Actions.ScriptEventHeader", "CollectParams"),
    ("Beyond.Gameplay.Actions.ActionHeader", "CollectParams"),
    ("Beyond.Gameplay.Actions.ActionHeader", "Process"),
    ("Beyond.Gameplay.Core.LevelScriptModule", "ResetUpdateProperty"),
    ("Beyond.Gameplay.Core.LevelScriptModule", "RegisterScriptOnPropertyChanged"),
    ("Beyond.Gameplay.Core.LevelScriptRuntime", "get_properties"),
    ("Beyond.Gameplay.Core.LevelScriptRuntime", "set_properties"),
    ("Beyond.Gameplay.Core.LevelScriptRuntime", "TryGetProperty"),
    ("Beyond.Gameplay.Core.LevelScriptRuntime", "ModuleResetUpdateProperty"),
    ("Beyond.Gameplay.Core.LevelScriptRuntime", "UpdateRuntimeState"),
    ("Beyond.Gameplay.ParamBlackboard", "SetVariableValue"),
    ("Beyond.Gameplay.ParamBlackboard", "GetParamVariableOrNewOne"),
    ("Beyond.Gameplay.ParamBlackboard", "NewParamVariable"),
    ("Beyond.Gameplay.ParamVariable", "set_rawValue"),
    ("Beyond.Gameplay.ParamVariable", "RawSetValue"),
    ("Beyond.Gameplay.ParamVariable", "SetupOnPropertyChangedEventForLevelScript"),
    ("Beyond.Gameplay.ParamVariable", "_RaiseOnPropertyChangedEvent"),
    ("Beyond.Gameplay.Actions.ParamExtensions", "GetValue"),
    ("Beyond.Gameplay.Actions.ParamExtensions", "SetValue"),
    ("Beyond.Gameplay.Actions.Param`1", "SetterSetValue"),
    ("Beyond_Gameplay_Actions_SetLevelScriptPtrForMemoryPack", "Deserialize"),
    ("Beyond_Gameplay_Actions_SetPropertyPathForMemoryPack", "Deserialize"),
    ("Beyond_Gameplay_Actions_SetBoolForMemoryPack", "Deserialize"),
    ("Beyond_Gameplay_Actions_SetIntForMemoryPack", "Deserialize"),
    ("Beyond_Gameplay_Actions_SetStringForMemoryPack", "Deserialize"),
    ("Beyond_Gameplay_Actions_Set_bool_ForMemoryPack", "set____key__"),
    ("Beyond_Gameplay_Actions_Set_bool_ForMemoryPack", "set____value__"),
    ("Beyond_Gameplay_Actions_Set_int_ForMemoryPack", "set____key__"),
    ("Beyond_Gameplay_Actions_Set_int_ForMemoryPack", "set____value__"),
    ("Beyond_Gameplay_Actions_Set_Beyond_PropertyPath_ForMemoryPack", "set____key__"),
    ("Beyond_Gameplay_Actions_Set_Beyond_PropertyPath_ForMemoryPack", "set____value__"),
    ("Beyond_Gameplay_Actions_Set_Beyond_Gameplay_Core_LevelScriptPtr_ForMemoryPack", "set____key__"),
    ("Beyond_Gameplay_Actions_Set_Beyond_Gameplay_Core_LevelScriptPtr_ForMemoryPack", "set____value__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set____filterLevel__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set____filterMask__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set____filterMode__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set____nextID__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set____priority__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set____triggerActiveDuring__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set____validate__"),
    ("Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", "set___instance"),
    (
        "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack+Beyond_Gameplay_Actions_ActionHeaderForMemoryPackFormatter",
        "Deserialize",
    ),
    (
        "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack+Beyond_Gameplay_Actions_ActionHeaderFormatter",
        "Deserialize",
    ),
    ("Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack", "set___actionList__"),
    ("Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack", "set___getterList__"),
    ("Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack", "set___headerList__"),
    ("Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack", "Deserialize"),
    (
        "Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack+Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPackFormatter",
        "Deserialize",
    ),
    (
        "Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack+Beyond_Gameplay_Actions_ActionSerializedMapFormatter",
        "Deserialize",
    ),
}


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def include_type(full_name: str) -> bool:
    if full_name in RUNTIME_EXACT_NAMES:
        return True
    if "ForMemoryPack" not in full_name:
        return False
    if not full_name.startswith(("Beyond_Gameplay_", "Beyond_Gameplay_Actions_")):
        return False
    return any(part in full_name for part in MEMORYPACK_NAME_PARTS)


def build_body_catalog(catalog_helper: Any, metadata: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    targets: list[dict[str, Any]] = []
    focused_types: list[dict[str, Any]] = []
    for type_def in metadata.types:
        full_name = metadata.type_full_name(type_def)
        if not include_type(full_name):
            continue
        fields = [catalog_helper.field_row(metadata, field) for field in metadata.fields_for(type_def)]
        methods = list(metadata.methods_for(type_def))
        method_rows = [catalog_helper.method_row(metadata, method) for method in methods]
        focused_types.append(
            {
                "type": full_name,
                "image": metadata.image_name_by_type_index.get(type_def.index, ""),
                "typeIndex": type_def.index,
                "typeToken": f"0x{type_def.token:08x}",
                "fieldCount": type_def.field_count,
                "methodCount": type_def.method_count,
                "fields": fields,
                "methods": method_rows,
            }
        )
        for offset, method in enumerate(methods):
            current = method_rows[offset]
            if not TARGET_METHOD_RE.search(str(current.get("name") or "")):
                continue
            neighbors = []
            for neighbor_offset in range(max(0, offset - 2), min(len(methods), offset + 3)):
                neighbor = dict(method_rows[neighbor_offset])
                neighbor["relativeOffset"] = neighbor_offset - offset
                neighbor["isTarget"] = neighbor_offset == offset
                neighbors.append(neighbor)
            targets.append(
                {
                    "type": full_name,
                    "image": metadata.image_name_by_type_index.get(type_def.index, ""),
                    "typeIndex": type_def.index,
                    "typeToken": f"0x{type_def.token:08x}",
                    "method": current["name"],
                    "methodIndex": current["index"],
                    "methodOffsetInType": offset,
                    "token": current["token"],
                    "parameters": current["parameters"],
                    "parameterDetails": current["parameterDetails"],
                    "returnTypeIndex": current["returnTypeIndex"],
                    "returnTypeName": current["returnTypeName"],
                    "flags": current["flags"],
                    "iflags": current["iflags"],
                    "slot": current["slot"],
                    "typeFields": fields,
                    "methodNeighborhood": neighbors,
                }
            )
    targets.sort(key=lambda row: (str(row["type"]), str(row["method"]), int(row["methodIndex"])))
    focused_types.sort(key=lambda row: str(row["type"]))
    catalog = {
        "metadata": catalog_helper.catalog_metadata_summary(metadata),
        "summary": {
            "focusedTypeCount": len(focused_types),
            "bodyTargetMethodCount": len(targets),
        },
        "focusedTypes": focused_types,
        "bodyTargets": targets,
    }
    return catalog, focused_types


def compact_fields(fields: list[dict[str, Any]], limit: int = 6) -> list[str]:
    out = []
    for field in fields[:limit]:
        out.append(f"{field.get('name')}:{field.get('typeName') or field.get('typeIndex')}")
    if len(fields) > limit:
        out.append(f"... (+{len(fields) - limit})")
    return out


def prioritized_resolved_targets(resolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def priority(row: dict[str, Any]) -> tuple[int, str, str]:
        type_name = str(row.get("type") or "")
        method_name = str(row.get("method") or "")
        if "ActionSerializedMapForMemoryPack" in type_name:
            return (0, type_name, method_name)
        if "ActionMap" in type_name or "ActionHeader" in type_name or "ScriptEventHeader" in type_name:
            return (1, type_name, method_name)
        return (2, type_name, method_name)

    return sorted(resolved, key=priority)


def compact_call(call: dict[str, Any]) -> dict[str, Any]:
    resolved = prioritized_resolved_targets(call.get("resolved") or [])
    return {
        "offset": call.get("offset"),
        "targetVa": call.get("targetVa"),
        "resolved": [
            {
                "methodIndex": row.get("methodIndex"),
                "type": row.get("type"),
                "method": row.get("method"),
            }
            for row in resolved[:4]
        ],
        "argumentSummary": {
            key: value.get("text")
            for key, value in ((call.get("argumentContext") or {}).get("argRegisterWrites") or {}).items()
            if value.get("text")
        },
    }


def call_label(call: dict[str, Any]) -> str:
    resolved = prioritized_resolved_targets(call.get("resolved") or [])
    if resolved:
        labels = [f"{row.get('type', '').split('.')[-1]}.{row.get('method')}" for row in resolved[:2]]
        return f"+0x{int(call.get('offset') or 0):x} -> {'; '.join(labels)}"
    return f"+0x{int(call.get('offset') or 0):x} -> {call.get('targetVa', '')}"


def target_summary(row: dict[str, Any]) -> dict[str, Any]:
    summary = row.get("methodBodySummary") or {}
    item = {
        "type": row.get("type"),
        "method": row.get("method"),
        "methodIndex": row.get("methodIndex"),
        "mappingStatus": row.get("mappingStatus"),
        "methodPointerVa": row.get("methodPointerVa"),
        "fields": compact_fields(row.get("typeFields") or []),
        "instructionCount": summary.get("instructionCount"),
        "unknownInstructionCount": summary.get("unknownInstructionCount"),
        "fieldAccesses": [
            {
                "offset": access.get("offset"),
                "kind": access.get("kind"),
                "origin": access.get("origin"),
                "text": access.get("text"),
            }
            for access in (summary.get("fieldAccesses") or [])[:16]
        ],
        "interestingInstructions": [
            {
                "offset": instruction.get("offset"),
                "text": instruction.get("text"),
            }
            for instruction in (summary.get("interestingInstructions") or [])[:16]
        ],
        "directCalls": [compact_call(call) for call in (row.get("directCalls") or [])[:16]],
    }
    generic_candidates = []
    for candidate in row.get("genericBodyCandidates") or []:
        instantiations = []
        for instantiation in candidate.get("instantiations") or []:
            instantiations.append(
                {
                    "methodSpecIndex": instantiation.get("methodSpecIndex"),
                    "classInstantiation": instantiation.get("classInstantiation"),
                    "methodInstantiation": instantiation.get("methodInstantiation"),
                }
            )
        generic_candidates.append(
            {
                "methodPointerVa": candidate.get("methodPointerVa"),
                "instantiations": instantiations,
                "body": {
                    "methodPointerRva": (candidate.get("body") or {}).get("methodPointerRva"),
                    "scanBytes": (candidate.get("body") or {}).get("scanBytes"),
                    "methodBodySummary": (candidate.get("body") or {}).get("methodBodySummary"),
                    "directCalls": [
                        compact_call(call)
                        for call in ((candidate.get("body") or {}).get("directCalls") or [])[:16]
                    ],
                    "unresolvedDirectCallCount": (candidate.get("body") or {}).get(
                        "unresolvedDirectCallCount"
                    ),
                },
            }
        )
    if generic_candidates:
        item["genericBodyCandidates"] = generic_candidates
    return item


def selected_target_summaries(mapped_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen_counts: dict[tuple[str, str], int] = {}
    for row in mapped_targets:
        key = (str(row.get("type") or ""), str(row.get("method") or ""))
        if key not in SELECTED_TARGETS:
            continue
        # Keep overloaded LevelScriptRuntime.UpdateRuntimeState and
        # RegisterScriptOnPropertyChanged rows, but avoid duplicate wrapper rows.
        count = seen_counts.get(key, 0)
        seen_counts[key] = count + 1
        item = target_summary(row)
        item["overloadIndex"] = count
        rows.append(item)
    return rows


def find_summary(targets: list[dict[str, Any]], type_name: str, method: str) -> list[dict[str, Any]]:
    return [row for row in targets if row.get("type") == type_name and row.get("method") == method]


def generic_argument_names(
    instantiation: dict[str, Any],
    key: str,
) -> tuple[str, ...]:
    return tuple(
        str(argument.get("typeName") or "")
        for argument in (instantiation.get(key) or {}).get("arguments") or []
        if argument.get("status") == "decoded" and argument.get("typeName")
    )


def generic_candidate_has_edge(
    candidate: dict[str, Any],
    *,
    callee_type: str,
    callee_method: str,
    callee_instantiation_key: str,
    argument_name: str,
) -> bool:
    summary = (candidate.get("body") or {}).get("methodBodySummary") or {}
    return any(
        resolved.get("type") == callee_type
        and resolved.get("method") == callee_method
        and generic_argument_names(resolved, callee_instantiation_key)
        == (argument_name,)
        for flow in summary.get("controlFlow") or []
        for resolved in flow.get("resolved") or []
    )


def build_key_findings(report: dict[str, Any], focused_types: list[dict[str, Any]]) -> list[str]:
    targets = report.get("bodyTargets") or []
    type_by_name = {row.get("type"): row for row in focused_types}
    set_generic = type_by_name.get("Beyond.Gameplay.Actions.Set`1") or {}
    set_list_generic = type_by_name.get("Beyond.Gameplay.Actions.SetList`1") or {}
    set_property_path = type_by_name.get("Beyond.Gameplay.Actions.SetPropertyPath") or {}
    set_levelscript_ptr = type_by_name.get("Beyond.Gameplay.Actions.SetLevelScriptPtr") or {}

    findings = [
        "ManualStartLevelScript.Execute and ManualEndLevelScript.Execute both call LevelScriptManager.TryGetLevelScript, then LevelScriptRuntime.ManualStart/ManualEnd.",
        "GetLevelScriptPropertyBool/Int GetResult calls LevelScriptManager.TryGetLevelScript and then LevelScriptRuntime.get_properties; these records are reads/gates, not setters.",
        "ScriptEvent.OnPropertyChanged registers through LevelScriptModule/LevelEventManager and its Process body reads ParamBlackboard variables; this is listener evidence.",
        "LevelScriptRuntime.UpdateRuntimeState calls ModuleResetUpdateProperty, which calls LevelScriptModule.ResetUpdateProperty; the module method only toggles small reset/update flags in the recovered body.",
        "LevelScriptRuntime.TryGetProperty is present in metadata but mapped to a null GameAssembly pointer in this build, so it cannot currently explain the serialized setter edge.",
        "Generic Set<T> and SetList<T> runtime types carry _key + _value fields. Their open-generic body slots are null, but shipped MethodSpecs resolve through MetadataRegistration to multiple type-specific entry points; the audit keeps the open method ambiguous and exposes every decoded candidate instead of selecting one by address.",
        "Concrete MemoryPack wrappers for Set<bool>/Set<int>/Set<PropertyPath>/Set<LevelScriptPtr> deserialize key before value and their generic wrapper setters store key at the real instance +0xd0 and value at +0xd8.",
        "ActionSerializedMapForMemoryPack.Deserialize calls setters in actionList, getterList, headerList order; the setters write runtime ActionSerializedMap fields at +0x18, +0x20, and +0x10 respectively.",
        "ParamVariable._RaiseOnPropertyChangedEvent can call ParamBlackboard.SetVariableValue, so property-change listeners can feed blackboard writes; this still does not identify an authored LevelScript setter opcode.",
    ]
    branch_execute = find_summary(
        targets,
        "Beyond.Gameplay.Actions.Branch",
        "Execute",
    )
    if branch_execute:
        branch_callees = {
            (
                str(resolved.get("type") or ""),
                str(resolved.get("method") or ""),
            )
            for row in branch_execute
            for call in row.get("directCalls") or []
            for resolved in call.get("resolved") or []
        }
        branch_instructions = [
            str(instruction.get("text") or "")
            for row in branch_execute
            for call in row.get("directCalls") or []
            for instruction in (
                (call.get("argumentContext") or {}).get("nearbyInstructions") or []
            )
        ]
        if (
            ("Beyond.Gameplay.Actions.ActionBase", "SetResultReservedID")
            in branch_callees
            and ("Beyond.Gameplay.Actions.ActionBase", "SetResultNextID")
            in branch_callees
            and any("[rbx+0xd0]" in text for text in branch_instructions)
            and any("[rbx+0xd8]" in text for text in branch_instructions)
        ):
            findings.append(
                "Branch.Execute reads the _idList field at +0xd0 and m_index at "
                "+0xd8, calls ActionBase.SetResultReservedID before non-final "
                "entries, calls SetResultNextID with the indexed list value, "
                "increments m_index, and resets it after the list end. "
                "Branch._idList is ordered continuation, not fan-out."
            )
        else:
            findings.append(
                "Branch.Execute was body-mapped, but its ordered _idList "
                "reserved/next contract did not pass the current instruction "
                "guard; keep Branch sequence traversal disabled."
            )
    for type_row, name in (
        (set_generic, "Set<T>"),
        (set_list_generic, "SetList<T>"),
    ):
        fields = type_row.get("fields") or []
        methods = type_row.get("methods") or []
        findings.append(
            f"{name} has {len(fields)} runtime fields and {len(methods)} runtime methods in metadata; its open Execute method remains fail-closed when multiple concrete MethodSpecs have distinct entry points."
        )
    set_execute_rows = find_summary(
        targets,
        "Beyond.Gameplay.Actions.Set`1",
        "Execute",
    )
    typed_set_routes = set()
    for row in set_execute_rows:
        for candidate in row.get("genericBodyCandidates") or []:
            instantiations = candidate.get("instantiations") or []
            if not instantiations:
                continue
            arguments = generic_argument_names(
                instantiations[0],
                "classInstantiation",
            )
            if len(arguments) != 1:
                continue
            argument_name = arguments[0]
            if generic_candidate_has_edge(
                candidate,
                callee_type="Beyond.Gameplay.Actions.ParamExtensions",
                callee_method="SetValue",
                callee_instantiation_key="methodInstantiation",
                argument_name=argument_name,
            ):
                typed_set_routes.add(argument_name)
    required_set_routes = {"System.Boolean", "System.Int32"}
    if required_set_routes <= typed_set_routes:
        findings.append(
            "The concrete Set<bool>.Execute and Set<int>.Execute MethodSpecs "
            "both read _key/_value, resolve the typed value through "
            "ParamExtensions.GetValue<T>, and tail-call the matching "
            "ParamExtensions.SetValue<T>. This proves a general typed Param "
            "write, not a LevelScript-property writer or Story-order edge."
        )
    else:
        findings.append(
            "The concrete Set<bool>/Set<int> typed Param route did not pass "
            "the current native-body guard; do not classify Set<T> as a "
            "LevelScript-property writer."
        )
    for type_row, name in (
        (set_property_path, "SetPropertyPath"),
        (set_levelscript_ptr, "SetLevelScriptPtr"),
    ):
        fields = type_row.get("fields") or []
        methods = type_row.get("methods") or []
        findings.append(
            f"{name} has {len(fields)} runtime fields and {len(methods)} runtime methods in the focused metadata view; only MemoryPack wrapper shells were body-mapped."
        )
    if not find_summary(targets, "Beyond.Gameplay.Core.LevelScriptModule", "ResetUpdateProperty"):
        findings.append("LevelScriptModule.ResetUpdateProperty was not body-mapped; rerun after checking metadata/body registration drift.")
    return findings


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines: list[str] = [
        "# LevelScript Action GameAssembly Body Audit",
        "",
        "## Summary",
        "",
        f"- Metadata: `{md_escape(payload['metadata'].get('metadataPath', ''))}`",
        f"- Metadata SHA-256: `{md_escape(payload['metadata'].get('metadataSha256', ''))}`",
        f"- GameAssembly: `{md_escape(payload['metadata'].get('gameAssembly', ''))}`",
        f"- GameAssembly SHA-256: `{md_escape(payload['metadata'].get('gameAssemblySha256', ''))}`",
        f"- Catalog body targets: `{payload['summary'].get('catalogBodyTargetCount')}`",
        f"- Mapped body targets: `{payload['summary'].get('mappedTargetCount')}`",
        f"- Resolved direct calls: `{payload['summary'].get('resolvedDirectCallCount')}`",
        f"- Direct calls to focused targets: `{payload['summary'].get('catalogTargetDirectCallCount')}`",
        "",
        "## Interpretation",
        "",
    ]
    for finding in payload.get("keyFindings") or []:
        lines.append(f"- {md_escape(finding)}")

    lines.extend(["", "## Important Direct-Call Edges", ""])
    edge_rows = payload.get("directCallEdges") or []
    if not edge_rows:
        lines.append("- None.")
    for edge in edge_rows:
        caller = edge.get("caller") or {}
        callees = prioritized_resolved_targets(edge.get("callees") or [])
        labels = [
            f"{callee.get('type', '').split('.')[-1]}.{callee.get('method')}"
            for callee in callees[:3]
        ]
        lines.append(
            "- "
            f"`{md_escape(caller.get('type', '').split('.')[-1])}.{md_escape(caller.get('method', ''))}` "
            f"+0x{int(edge.get('offset') or 0):x} -> `{md_escape('; '.join(labels))}`"
        )

    lines.extend(["", "## Selected Targets", ""])
    for row in payload.get("selectedTargets") or []:
        title = f"{row.get('type', '').split('.')[-1]}.{row.get('method')}"
        overload = row.get("overloadIndex")
        if overload:
            title += f" overload {overload}"
        lines.extend(
            [
                f"### `{md_escape(title)}`",
                "",
                f"- methodIndex: `{row.get('methodIndex')}`; mapping: `{md_escape(row.get('mappingStatus', ''))}`; VA: `{md_escape(row.get('methodPointerVa', ''))}`",
                f"- fields: `{md_escape(', '.join(row.get('fields') or []) or '-')}`",
                f"- body decode: `{row.get('instructionCount')}` instructions, `{row.get('unknownInstructionCount')}` unknown",
            ]
        )
        accesses = row.get("fieldAccesses") or []
        if accesses:
            lines.append("- field accesses:")
            for access in accesses[:8]:
                lines.append(
                    f"  - +0x{int(access.get('offset') or 0):x} "
                    f"{md_escape(access.get('kind', ''))} `{md_escape(access.get('origin', ''))}`: "
                    f"`{md_escape(access.get('text', ''))}`"
                )
        instructions = row.get("interestingInstructions") or []
        if instructions:
            lines.append("- interesting instructions:")
            for instruction in instructions[:8]:
                lines.append(
                    f"  - +0x{int(instruction.get('offset') or 0):x}: "
                    f"`{md_escape(instruction.get('text', ''))}`"
                )
        calls = row.get("directCalls") or []
        if calls:
            lines.append("- direct calls:")
            for call in calls[:12]:
                lines.append(f"  - `{md_escape(call_label(call))}`")
        generic_candidates = row.get("genericBodyCandidates") or []
        if generic_candidates:
            lines.append("- generic body candidates:")
            for candidate in generic_candidates:
                argument_labels = []
                for instantiation in candidate.get("instantiations") or []:
                    arguments = []
                    for kind in ("classInstantiation", "methodInstantiation"):
                        decoded = instantiation.get(kind) or {}
                        arguments.extend(
                            str(argument.get("typeName") or argument.get("status") or "unknown")
                            for argument in decoded.get("arguments") or []
                        )
                    argument_labels.append(
                        f"spec {instantiation.get('methodSpecIndex')}: "
                        f"{', '.join(arguments) or 'no generic arguments'}"
                    )
                lines.append(
                    f"  - `{md_escape(candidate.get('methodPointerVa', ''))}` — "
                    f"{md_escape('; '.join(argument_labels))}"
                )
        lines.append("")

    write_text_if_changed(path, "\n".join(lines).rstrip() + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--catalog-tmp", type=Path, default=DEFAULT_CATALOG_TMP)
    parser.add_argument(
        "--json",
        type=Path,
        default=REPORT_DIR / "levelscript_action_body_targets_gameassembly.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=REPORT_DIR / "levelscript_action_body_targets_gameassembly.md",
    )
    parser.add_argument("--max-scan-bytes", type=int, default=0x3000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog_helper = load_module(CATALOG_HELPER, "endfield_il2cpp_catalog")
    body_helper = load_module(BODY_HELPER, "endfield_il2cpp_body_map")
    metadata_path = catalog_helper.resolve_metadata_path(args.metadata, prefer_cache=True)
    metadata = catalog_helper.Metadata(metadata_path)
    catalog, focused_types = build_body_catalog(catalog_helper, metadata)
    args.catalog_tmp.parent.mkdir(parents=True, exist_ok=True)
    args.catalog_tmp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    map_args = SimpleNamespace(
        metadata=metadata_path,
        gameassembly=args.gameassembly,
        catalog=args.catalog_tmp,
        code_registration=hex(body_helper.DEFAULT_CODE_REGISTRATION),
        head_bytes=32,
        max_scan_bytes=args.max_scan_bytes,
        # Open generic IL2CPP method slots are commonly null. Resolve shipped
        # MethodSpecs through MetadataRegistration before concluding that a
        # generic action body is unavailable; ambiguous instantiations remain
        # explicitly unresolved in the mapper.
        include_generic_instantiations=True,
        metadata_registration="",
        include_unresolved_calls=False,
        arg_context_window=96,
        body_summary_method_regex=BODY_SUMMARY_RE,
        body_summary_max_instructions=140,
    )
    raw_report = body_helper.build_report(map_args)
    payload = {
        "metadata": raw_report["metadata"],
        "settings": raw_report["settings"] | {"catalogTmp": repo_rel(args.catalog_tmp)},
        "summary": raw_report["summary"] | {
            "focusedTypeCount": len(focused_types),
        },
        "keyFindings": build_key_findings(raw_report, focused_types),
        "directCallEdges": raw_report.get("directCallEdges") or [],
        "selectedTargets": selected_target_summaries(raw_report.get("bodyTargets") or []),
    }
    write_report_json(args.json, payload)
    write_markdown(args.markdown, payload)
    summary = payload["summary"]
    print(f"LevelScript action body audit: {args.json}")
    print(f"LevelScript action body report: {args.markdown}")
    print(
        "mapped="
        f"{summary.get('mappedTargetCount')}/{summary.get('catalogBodyTargetCount')} "
        f"directTargetCalls={summary.get('catalogTargetDirectCallCount')} "
        f"selected={len(payload.get('selectedTargets') or [])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
