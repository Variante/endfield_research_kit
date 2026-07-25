#!/usr/bin/env python3
"""Write a focused IL2CPP metadata audit for LevelScript action classes.

This is a small wrapper around `tools/endfield-il2cpp/catalog_option_flow_metadata.py`.
The generic metadata catalog can match thousands of property-related types; this
script keeps only the LevelScript action/event classes that matter for scene
timeline recovery.

Output:

    reports/mission_order/levelscript_action_runtime_metadata.json
    reports/mission_order/levelscript_action_runtime_metadata.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"

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
    "Beyond.Gameplay.LevelScriptData",
    "Beyond.Gameplay.LevelScriptBriefData",
    "Beyond.Gameplay.LevelData",
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
    "ScriptEvent_OnPropertyChanged",
    "ScriptEvent_OnLeaderEnterTriggerVolume",
    "ScriptEvent_OnLeaderLeaveTriggerVolume",
    "ScriptEvent_OnLeaderEnterTriggerVolumeList",
    "ScriptEvent_OnLeaderLeaveTriggerVolumeList",
    "ActionHeader",
    "ScriptEventHeader",
    "ActionMapAssetRaw",
    "ActionMapAsset",
    "ActionSerializedMap",
    "LevelScriptData",
    "LevelScriptBriefData",
)
ABSENT_TYPE_TERMS = (
    "UpdateLevelScriptProperty",
    "OperateLevelScriptNumber",
    "SetLevelScriptDone",
)


def load_catalog_helper() -> Any:
    spec = importlib.util.spec_from_file_location("endfield_il2cpp_catalog", CATALOG_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load metadata helper: {CATALOG_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def include_type(full_name: str) -> bool:
    if full_name in RUNTIME_EXACT_NAMES:
        return True
    if "ForMemoryPack" not in full_name:
        return False
    if not full_name.startswith(("Beyond_Gameplay_", "Beyond_Gameplay_Actions_")):
        return False
    if re.match(r"^Beyond_Gameplay_(?:LevelData|LevelScriptData|LevelScriptBriefData)ForMemoryPack(?:$|\+)", full_name):
        return True
    return any(part in full_name for part in MEMORYPACK_NAME_PARTS)


def field_row(helper: Any, md: Any, field: Any) -> dict[str, Any]:
    return helper.field_row(md, field)


def method_row(helper: Any, md: Any, method: Any) -> dict[str, Any]:
    return helper.method_row(md, method)


def type_row(helper: Any, md: Any, type_def: Any) -> dict[str, Any]:
    methods = [method_row(helper, md, method) for method in md.methods_for(type_def)]
    setter_methods = [
        method["name"]
        for method in methods
        if str(method.get("name") or "").startswith("set_")
    ]
    execute_methods = [
        method["name"]
        for method in methods
        if method.get("name") in {"Execute", "Process", "CollectParams", "GetResult", "Deserialize"}
    ]
    full_name = md.type_full_name(type_def)
    row = {
        "index": type_def.index,
        "fullName": full_name,
        "name": md.type_name(type_def),
        "namespace": md.type_namespace(type_def),
        "image": md.image_name_by_type_index.get(type_def.index, ""),
        "token": f"0x{type_def.token:08x}",
        "category": "memorypack" if "ForMemoryPack" in full_name else "runtime",
        "fieldCount": type_def.field_count,
        "methodCount": type_def.method_count,
        "fields": [field_row(helper, md, field) for field in md.fields_for(type_def)],
        "setterMethods": setter_methods,
        "keyMethods": execute_methods,
    }
    return {key: value for key, value in row.items() if value not in ("", None, [], {})}


def compact_shape(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "fullName": row.get("fullName"),
        "category": row.get("category"),
        "fields": [
            {
                "name": field.get("name"),
                "typeName": field.get("typeName"),
            }
            for field in row.get("fields") or []
        ],
        "setterMethods": row.get("setterMethods") or [],
        "keyMethods": row.get("keyMethods") or [],
    }


def build_audit(*, metadata_path: Path | None = None) -> dict[str, Any]:
    helper = load_catalog_helper()
    resolved_metadata = helper.resolve_metadata_path(metadata_path, prefer_cache=True)
    md = helper.Metadata(resolved_metadata)
    rows: list[dict[str, Any]] = []
    absent_hits: dict[str, list[str]] = {term: [] for term in ABSENT_TYPE_TERMS}

    for type_def in md.types:
        full_name = md.type_full_name(type_def)
        for term in ABSENT_TYPE_TERMS:
            if term in full_name:
                absent_hits[term].append(full_name)
        if include_type(full_name):
            rows.append(type_row(helper, md, type_def))

    rows.sort(key=lambda row: (row.get("category") != "runtime", safe_text(row.get("fullName"))))
    category_counts = Counter(row.get("category") or "unknown" for row in rows)
    shape_names = {
        "genericSet": "Beyond.Gameplay.Actions.Set`1",
        "genericSetList": "Beyond.Gameplay.Actions.SetList`1",
        "manualStart": "Beyond.Gameplay.Actions.ManualStartLevelScript",
        "manualEnd": "Beyond.Gameplay.Actions.ManualEndLevelScript",
        "branchSequence": "Beyond.Gameplay.Actions.Branch",
        "propertyGetterBool": "Beyond.Gameplay.Actions.GetLevelScriptPropertyBool",
        "propertyGetterInt": "Beyond.Gameplay.Actions.GetLevelScriptPropertyInt",
        "propertyChangedEvent": "Beyond.Gameplay.Actions.ScriptEvent.OnPropertyChanged",
        "triggerEnterEvent": "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolume",
        "triggerLeaveEvent": "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderLeaveTriggerVolume",
        "actionHeader": "Beyond.Gameplay.Actions.ActionHeader",
        "scriptEventHeader": "Beyond.Gameplay.Actions.ScriptEventHeader",
        "actionMapAssetRaw": "Beyond.Gameplay.Actions.ActionMapAssetRaw",
        "actionSerializedMap": "Beyond.Gameplay.Actions.ActionSerializedMap",
        "actionMapAsset": "Beyond.Gameplay.Actions.ActionMapAsset",
        "actionMapRuntime": "Beyond.Gameplay.Actions.ActionMapRuntime",
        "paramBlackboard": "Beyond.Gameplay.ParamBlackboard",
        "paramVariable": "Beyond.Gameplay.ParamVariable",
    }
    by_name = {row.get("fullName"): row for row in rows}
    key_shapes = {
        key: compact_shape(by_name[name])
        for key, name in shape_names.items()
        if name in by_name
    }
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metadata": helper.catalog_metadata_summary(md),
        "summary": {
            "matchedTypes": len(rows),
            "categoryCounts": dict(category_counts.most_common()),
            "absentTypeTerms": {
                term: hits for term, hits in absent_hits.items() if hits
            },
            "confirmedAbsentTypeTerms": [
                term for term, hits in absent_hits.items() if not hits
            ],
        },
        "interpretation": {
            "manualStartEndShape": (
                "ManualStartLevelScript and ManualEndLevelScript runtime fields are "
                "levelId + scriptId; their MemoryPack wrappers expose setters for "
                "levelId then scriptId."
            ),
            "branchSequenceShape": (
                "Branch carries _idList + m_index, and its MemoryPack wrapper "
                "deserializes _idList. The original GameAssembly Execute body is "
                "still required to distinguish ordered continuation from fan-out."
            ),
            "propertyGetterShape": (
                "GetLevelScriptPropertyBool/Int runtime fields are _target + _path; "
                "their MemoryPack wrappers expose setters for _path then _target. "
                "Property-key records matching this family are reads/gates, not setters."
            ),
            "propertyEventShape": (
                "ScriptEvent.OnPropertyChanged fields are _propertyKey, _value, "
                "_oldValue, and m_propertyPath; this is listener evidence."
            ),
            "genericSetterShape": (
                "The generic Set<T> and SetList<T> runtime action shapes exist and "
                "carry _key + _value fields. Concrete MemoryPack wrappers for "
                "Set<bool>/Set<int>/Set<PropertyPath>/Set<LevelScriptPtr> expose "
                "key/value setters, but this does not by itself map any LevelScript "
                "opcode to the setter class."
            ),
            "serializedActionMapShape": (
                "LevelScriptData.actionMap deserializes through ActionMapAssetRaw. "
                "Its dataMap is ActionSerializedMap, split into headerList, "
                "actionList, and getterList runtime fields. Body recovery shows "
                "the generated setter dispatch order as actionList, getterList, "
                "then headerList; MetadataRegistration resolves those fields to "
                "List<ActionBase>, List<PureGetter>, and List<ActionHeader>. "
                "Unnamed compact high-code records such as 0x0a03/0x00 "
                "and 0x0bed/0x00 therefore belong to this serialized map layer "
                "rather than to a missing ActionBase union tag."
            ),
            "blackboardWriterShape": (
                "ParamBlackboard and ParamVariable expose the lower runtime property "
                "storage/writeback surface. They help explain property mutation, but "
                "the authored action opcode still needs an independent class bridge."
            ),
            "missingSetterClassNames": (
                "No metadata type name contains UpdateLevelScriptProperty, "
                "OperateLevelScriptNumber, or SetLevelScriptDone. These names appear "
                "as enum/runtime concepts elsewhere, but not as serialized action "
                "classes in the metadata table."
            ),
        },
        "keyShapes": key_shapes,
        "types": rows,
    }


def format_fields(fields: list[dict[str, Any]]) -> str:
    return ", ".join(
        f"{field.get('name')}:{field.get('typeName')}"
        for field in fields
    )


def markdown_report(payload: dict[str, Any], *, cap: int) -> str:
    summary = payload.get("summary") or {}
    metadata = payload.get("metadata") or {}
    lines = [
        "# LevelScript Action Runtime Metadata",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- Metadata: `{md_escape(metadata.get('path'))}`",
        f"- SHA-256: `{md_escape(metadata.get('sha256'))}`",
        f"- Matched focused types: `{summary.get('matchedTypes')}`",
        f"- Category counts: `{summary.get('categoryCounts')}`",
        f"- Confirmed absent type-name terms: `{summary.get('confirmedAbsentTypeTerms')}`",
        "",
        "## Interpretation",
        "",
    ]
    for value in (payload.get("interpretation") or {}).values():
        lines.append(f"- {value}")

    lines.extend([
        "",
        "## Key Shapes",
        "",
        "| key | type | fields | MemoryPack setters / key methods |",
        "| --- | --- | --- | --- |",
    ])
    for key, shape in (payload.get("keyShapes") or {}).items():
        lines.append(
            f"| `{md_escape(key)}` "
            f"| `{md_escape(shape.get('fullName'))}` "
            f"| `{md_escape(format_fields(shape.get('fields') or []))}` "
            f"| `{md_escape(', '.join((shape.get('setterMethods') or []) + (shape.get('keyMethods') or [])))}` |"
        )

    lines.extend([
        "",
        "## Focused Types",
        "",
        "| category | type | fields | setters | key methods |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in (payload.get("types") or [])[:cap]:
        lines.append(
            f"| `{md_escape(row.get('category'))}` "
            f"| `{md_escape(row.get('fullName'))}` "
            f"| `{md_escape(format_fields(row.get('fields') or []))}` "
            f"| `{md_escape(', '.join(row.get('setterMethods') or []))}` "
            f"| `{md_escape(', '.join(row.get('keyMethods') or []))}` |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--reports-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--markdown-cap", type=int, default=120)
    args = parser.parse_args()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_audit(metadata_path=args.metadata)
    out_json = args.reports_dir / "levelscript_action_runtime_metadata.json"
    out_md = args.reports_dir / "levelscript_action_runtime_metadata.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload, cap=max(1, args.markdown_cap)))
    print(f"LevelScript action metadata audit: {out_json}")
    print(f"LevelScript action metadata report: {out_md}")
    summary = payload.get("summary") or {}
    print(
        f"types={summary.get('matchedTypes')} "
        f"categories={json.dumps(summary.get('categoryCounts') or {}, sort_keys=True)} "
        f"absent={summary.get('confirmedAbsentTypeTerms')}"
    )


if __name__ == "__main__":
    main()
