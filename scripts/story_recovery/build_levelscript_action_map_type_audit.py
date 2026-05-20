#!/usr/bin/env python3
"""Resolve ActionSerializedMap type-index rows through MetadataRegistration.

The global-metadata table alone leaves generic/list/array type indexes as
`<type-index:N>`. This focused audit uses GameAssembly's
Il2CppMetadataRegistration type table to resolve the specific indexes that
matter for LevelScript ActionSerializedMap recovery.

Output:

    reports/mission_order/levelscript_action_map_type_indices.json
    reports/mission_order/levelscript_action_map_type_indices.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
BODY_HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
REPORT_DIR = ROOT / "reports" / "mission_order"

DEFAULT_METADATA_REGISTRATION = 0x18A31FCD0
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")

IL2CPP_TYPE_NAMES = {
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
    0x11: "valuetype",
    0x12: "class",
    0x13: "var",
    0x14: "array",
    0x15: "genericinst",
    0x1D: "szarray",
    0x1E: "mvar",
}

TARGET_TYPE_INDICES = [
    {
        "group": "ActionSerializedMap fields",
        "name": "actionList",
        "typeIndex": 61412,
        "source": "Beyond.Gameplay.Actions.ActionSerializedMap.actionList",
    },
    {
        "group": "ActionSerializedMap fields",
        "name": "getterList",
        "typeIndex": 62867,
        "source": "Beyond.Gameplay.Actions.ActionSerializedMap.getterList",
    },
    {
        "group": "ActionSerializedMap fields",
        "name": "headerList",
        "typeIndex": 61419,
        "source": "Beyond.Gameplay.Actions.ActionSerializedMap.headerList",
    },
    {
        "group": "MemoryPack setter parameter types",
        "name": "set___actionList__ value",
        "typeIndex": 61411,
        "source": "Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack.set___actionList__",
    },
    {
        "group": "MemoryPack setter parameter types",
        "name": "set___getterList__ value",
        "typeIndex": 62866,
        "source": "Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack.set___getterList__",
    },
    {
        "group": "MemoryPack setter parameter types",
        "name": "set___headerList__ value",
        "typeIndex": 61418,
        "source": "Beyond_Gameplay_Actions_ActionSerializedMapForMemoryPack.set___headerList__",
    },
    {
        "group": "ActionMapRuntime fields",
        "name": "actionArray",
        "typeIndex": 109877,
        "source": "Beyond.Gameplay.Actions.ActionMapRuntime.actionArray",
    },
    {
        "group": "ActionMapRuntime fields",
        "name": "getterArray",
        "typeIndex": 110815,
        "source": "Beyond.Gameplay.Actions.ActionMapRuntime.getterArray",
    },
    {
        "group": "ActionMapRuntime fields",
        "name": "headerArray",
        "typeIndex": 109879,
        "source": "Beyond.Gameplay.Actions.ActionMapRuntime.headerArray",
    },
    {
        "group": "ActionMapRuntime fields",
        "name": "nodeArray",
        "typeIndex": 110732,
        "source": "Beyond.Gameplay.Actions.ActionMapRuntime.nodeArray",
    },
]


def load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TypeResolver:
    def __init__(self, pe: Any, metadata: Any, metadata_registration: int) -> None:
        self.pe = pe
        self.metadata = metadata
        self.metadata_registration = metadata_registration
        self.summary = self._read_metadata_registration()
        self.types_table_va = int(self.summary["types"]["pointerVa"], 16)
        self.types_table_offset = self._offset_for_va(self.types_table_va)

    def _offset_for_va(self, va: int) -> int:
        offset, _, _ = self.pe.file_offset_for_va(va)
        if offset is None:
            raise ValueError(f"VA outside image: 0x{va:x}")
        return offset

    def _u32_at_va(self, va: int, offset: int = 0) -> int:
        return struct.unpack_from("<I", self.pe.buf, self._offset_for_va(va) + offset)[0]

    def _u64_at_va(self, va: int, offset: int = 0) -> int:
        return struct.unpack_from("<Q", self.pe.buf, self._offset_for_va(va) + offset)[0]

    def _read_pair(self, name: str, offset: int) -> dict[str, Any]:
        count = self._u32_at_va(self.metadata_registration, offset)
        pointer = self._u64_at_va(self.metadata_registration, offset + 8)
        pointer_offset, section, _ = self.pe.file_offset_for_va(pointer)
        return {
            "name": name,
            "count": count,
            "pointerVa": f"0x{pointer:x}",
            "pointerSection": section,
            "pointerMapped": pointer_offset is not None,
        }

    def _read_metadata_registration(self) -> dict[str, Any]:
        return {
            "va": f"0x{self.metadata_registration:x}",
            "genericClasses": self._read_pair("genericClasses", 0x00),
            "genericInsts": self._read_pair("genericInsts", 0x10),
            "genericMethodTable": self._read_pair("genericMethodTable", 0x20),
            "types": self._read_pair("types", 0x30),
            "methodSpecs": self._read_pair("methodSpecs", 0x40),
            "fieldOffsets": self._read_pair("fieldOffsets", 0x50),
            "typeDefinitionsSizes": self._read_pair("typeDefinitionsSizes", 0x60),
            "metadataUsages": self._read_pair("metadataUsages", 0x70),
        }

    def type_pointer_for_index(self, type_index: int) -> int:
        if type_index < 0 or type_index >= self.summary["types"]["count"]:
            raise ValueError(f"type index outside MetadataRegistration.types: {type_index}")
        return struct.unpack_from("<Q", self.pe.buf, self.types_table_offset + type_index * 8)[0]

    def resolve_type_index(self, type_index: int) -> dict[str, Any]:
        type_pointer = self.type_pointer_for_index(type_index)
        resolved = self.resolve_type_pointer(type_pointer)
        return {
            "typeIndex": type_index,
            "typePointerVa": f"0x{type_pointer:x}",
            **resolved,
        }

    def resolve_type_pointer(self, type_pointer: int, *, depth: int = 0) -> dict[str, Any]:
        if depth > 8:
            return {
                "resolvedName": "<max-depth>",
                "kind": "max-depth",
            }
        data = self._u64_at_va(type_pointer, 0)
        bits = self._u32_at_va(type_pointer, 8)
        kind_value = (bits >> 16) & 0xFF
        attrs = bits & 0xFFFF
        kind = IL2CPP_TYPE_NAMES.get(kind_value, f"unknown-0x{kind_value:x}")
        row: dict[str, Any] = {
            "kind": kind,
            "kindValue": kind_value,
            "attrs": attrs,
            "data": f"0x{data:x}",
            "bits": f"0x{bits:x}",
        }
        if kind in {"class", "valuetype"}:
            row["typeDefIndex"] = data
            row["resolvedName"] = (
                self.metadata.type_full_name(self.metadata.types[data])
                if 0 <= data < len(self.metadata.types)
                else f"<typedef:{data}>"
            )
            return row
        if kind == "genericinst":
            base_type_pointer = self._u64_at_va(data, 0)
            class_inst = self._u64_at_va(data, 8)
            method_inst = self._u64_at_va(data, 16)
            base = self.resolve_type_pointer(base_type_pointer, depth=depth + 1)
            args = self.resolve_generic_inst(class_inst, depth=depth + 1)
            arg_names = [arg.get("resolvedName") or arg.get("kind") for arg in args]
            row.update({
                "genericClassVa": f"0x{data:x}",
                "baseTypePointerVa": f"0x{base_type_pointer:x}",
                "classInstVa": f"0x{class_inst:x}",
                "methodInstVa": f"0x{method_inst:x}",
                "baseType": base,
                "genericArgs": args,
                "resolvedName": f"{base.get('resolvedName') or base.get('kind')}<{', '.join(arg_names)}>",
            })
            return row
        if kind == "szarray":
            element = self.resolve_type_pointer(data, depth=depth + 1)
            row["elementType"] = element
            row["resolvedName"] = f"{element.get('resolvedName') or element.get('kind')}[]"
            return row
        if kind == "array":
            element_pointer = self._u64_at_va(data, 0)
            element = self.resolve_type_pointer(element_pointer, depth=depth + 1)
            row["arrayTypeVa"] = f"0x{data:x}"
            row["elementType"] = element
            row["resolvedName"] = f"{element.get('resolvedName') or element.get('kind')}[array]"
            return row
        row["resolvedName"] = kind
        return row

    def resolve_generic_inst(self, inst_pointer: int, *, depth: int) -> list[dict[str, Any]]:
        if not inst_pointer:
            return []
        argc = self._u32_at_va(inst_pointer, 0)
        argv = self._u64_at_va(inst_pointer, 8)
        if argc > 32:
            return [{
                "resolvedName": f"<unexpected-generic-argc:{argc}>",
                "kind": "error",
            }]
        argv_offset = self._offset_for_va(argv)
        args: list[dict[str, Any]] = []
        for index in range(argc):
            type_pointer = struct.unpack_from("<Q", self.pe.buf, argv_offset + index * 8)[0]
            arg = self.resolve_type_pointer(type_pointer, depth=depth + 1)
            arg["typePointerVa"] = f"0x{type_pointer:x}"
            args.append(arg)
        return args


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog_helper = load_module(CATALOG_HELPER, "endfield_il2cpp_catalog")
    body_helper = load_module(BODY_HELPER, "endfield_il2cpp_body_map")
    metadata_path = catalog_helper.resolve_metadata_path(args.metadata, prefer_cache=True)
    metadata = catalog_helper.Metadata(metadata_path)
    pe = body_helper.PeImage(args.gameassembly)
    resolver = TypeResolver(pe, metadata, args.metadata_registration)
    rows = []
    for target in TARGET_TYPE_INDICES:
        rows.append(target | resolver.resolve_type_index(int(target["typeIndex"])))
    return {
        "metadata": {
            "globalMetadata": str(metadata_path),
            "gameAssembly": str(args.gameassembly),
        },
        "metadataRegistration": resolver.summary,
        "summary": {
            "targetCount": len(rows),
            "resolvedCount": sum(1 for row in rows if row.get("resolvedName")),
            "typesCount": resolver.summary["types"]["count"],
        },
        "typeIndices": rows,
        "interpretation": [
            "ActionSerializedMap actionList resolves to List<ActionBase>.",
            "ActionSerializedMap getterList resolves to List<PureGetter>.",
            "ActionSerializedMap headerList resolves to List<ActionHeader>.",
            "ActionMapRuntime mirrors those lists as ActionBase[], PureGetter[], and ActionHeader[].",
        ],
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    meta = payload["metadata"]
    registration = payload["metadataRegistration"]
    lines = [
        "# LevelScript ActionMap Type-Index Audit",
        "",
        "## Summary",
        "",
        f"- Global metadata: `{md_escape(meta.get('globalMetadata', ''))}`",
        f"- GameAssembly: `{md_escape(meta.get('gameAssembly', ''))}`",
        f"- MetadataRegistration: `{registration.get('va')}`",
        f"- Types table: `{registration['types'].get('pointerVa')}` (`{registration['types'].get('count')}` entries)",
        f"- Target type indexes: `{payload['summary'].get('targetCount')}`",
        "",
        "## Interpretation",
        "",
    ]
    for item in payload.get("interpretation") or []:
        lines.append(f"- {md_escape(item)}")
    lines.extend([
        "",
        "## Resolved Type Indexes",
        "",
        "| group | name | type index | resolved type | source |",
        "| --- | --- | ---: | --- | --- |",
    ])
    for row in payload.get("typeIndices") or []:
        lines.append(
            f"| {md_escape(row.get('group', ''))} "
            f"| {md_code(row.get('name', ''))} "
            f"| `{row.get('typeIndex')}` "
            f"| {md_code(row.get('resolvedName', ''))} "
            f"| {md_code(row.get('source', ''))} |"
        )
    write_text_if_changed(path, "\n".join(lines).rstrip() + "\n")


def md_code(value: Any) -> str:
    text = md_escape(value)
    if "`" in text:
        return f"`` {text} ``"
    return f"`{text}`"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument(
        "--metadata-registration",
        type=lambda value: int(value, 0),
        default=DEFAULT_METADATA_REGISTRATION,
    )
    parser.add_argument("--json", type=Path, default=REPORT_DIR / "levelscript_action_map_type_indices.json")
    parser.add_argument("--markdown", type=Path, default=REPORT_DIR / "levelscript_action_map_type_indices.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_report(args)
    write_report_json(args.json, payload)
    write_markdown(args.markdown, payload)
    summary = payload["summary"]
    print(f"LevelScript ActionMap type-index audit: {args.json}")
    print(f"LevelScript ActionMap type-index report: {args.markdown}")
    print(
        f"resolved={summary.get('resolvedCount')}/{summary.get('targetCount')} "
        f"types={summary.get('typesCount')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
