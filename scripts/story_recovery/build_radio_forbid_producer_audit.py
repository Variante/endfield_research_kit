#!/usr/bin/env python3
"""Audit the current ForbidSystem-to-SHOW_RADIO value-production boundary."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
MAPPER = ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"
CARRIER = ROOT / "scripts/story_recovery/build_native_value_carrier_audit.py"
GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = GAME_ROOT / "il2cpp_data/Metadata/global-metadata.dat"
DEFAULT_INDEX_ROOT = ROOT / "export_full/recovered/AnimeStudio-cli"
DEFAULT_LUA_ROOT = ROOT / "scratch/animestudio/zhuangfy_lizi_lua_dither_20260724/Lua/Data/LuaScripts"
DEFAULT_IFIX = ROOT / "reports/story/recovery/current_ifix_mission_graph_audit.json"
DEFAULT_JSON = ROOT / "reports/story/recovery/radio_forbid_producer_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports/story/recovery/radio_forbid_producer_audit.md"

RADIO_PARAM = "Beyond.Gameplay.ForbidParamsWithRadioReason"
FORBID_PARAM = "Beyond.Gameplay.ForbidParams"
FORBID_ENUM = "Beyond.Gameplay.ForbidType"
SET_FORBID = "Beyond.Gameplay.Actions.SetForbid"
TARGET_ENUM = "ForbidInteractFacBuilding"
TARGET_RADIOS = ("radio_e0m0_9d5", "radio_e0m0_10", "radio_e0m0_21")
LUA_PRODUCER = re.compile(
    r"RadioRuntimeData\s*\(\s*forbidReason\.radioId\s*,\s*true\s*,\s*0\s*\)"
)


class AuditError(RuntimeError):
    pass


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def read_compressed_uint32(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first < 0x80:
        return first, 1
    if first < 0xC0:
        return ((first & 0x7F) << 8) | data[offset + 1], 2
    if first < 0xE0:
        return ((first & 0x3F) << 16) | (data[offset + 1] << 8) | data[offset + 2], 3
    if first < 0xF0:
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
    raise AuditError(f"unsupported compressed integer prefix 0x{first:02x}")


def read_compressed_int32(data: bytes, offset: int) -> tuple[int, int]:
    value, size = read_compressed_uint32(data, offset)
    return (value >> 1) ^ -(value & 1), size


def find_type(metadata: Any, full_name: str) -> Any:
    rows = [row for row in metadata.types if metadata.type_full_name(row) == full_name]
    if len(rows) != 1:
        raise AuditError(f"metadata type {full_name!r}: expected 1, found {len(rows)}")
    return rows[0]


def enum_members(metadata: Any, full_name: str) -> dict[str, int]:
    defaults_section = metadata.sections["fieldDefaultValues"]
    if defaults_section.size % 12:
        raise AuditError("fieldDefaultValues is not aligned to 12-byte records")
    defaults = {}
    for offset in range(
        defaults_section.offset,
        defaults_section.offset + defaults_section.size,
        12,
    ):
        field_index, _type_index, data_index = struct.unpack_from("<iii", metadata.buf, offset)
        defaults[field_index] = data_index
    data = metadata.sections["fieldAndParameterDefaultValueData"]
    values = {}
    for field in metadata.fields_for(find_type(metadata, full_name)):
        name = metadata.string(field.name_index)
        if name != "value__" and field.index in defaults:
            values[name] = read_compressed_int32(
                metadata.buf, data.offset + defaults[field.index]
            )[0]
    return values


def method_matches(
    metadata: Any,
    runtime: Any,
    owner_name: str,
    method_name: str,
    parameter_types: tuple[str, ...],
) -> list[int]:
    matches = []
    for method in metadata.methods_for(find_type(metadata, owner_name)):
        if metadata.string(method.name_index) != method_name:
            continue
        actual = tuple(
            runtime.type_name(parameter.type_index)
            for parameter in metadata.parameters_for(method)
        )
        if actual == parameter_types:
            matches.append(method.index)
    return matches


def instruction_texts(instructions: Iterable[dict[str, Any]]) -> list[str]:
    return [str(row.get("text") or "") for row in instructions]


def extract_default_radio_factory_branch(
    instructions: list[dict[str, Any]], enum_value: int, constructor_va: int
) -> dict[str, Any]:
    texts = instruction_texts(instructions)
    selectors = (
        f"cmp ebx, 0x{enum_value:x}",
        f"lea rcx, [rbx-0x{enum_value:x}]",
    )
    target = f"call 0x{constructor_va:x}"
    starts = [index for index, text in enumerate(texts) if text in selectors]
    ends = [index for index, text in enumerate(texts) if text == target]
    if len(starts) != 1 or len(ends) != 1:
        raise AuditError(
            "validator=radioForbidProducerAudit gate=defaultFactoryBranch "
            f"expected=one compare/call actual={len(starts)}/{len(ends)}"
        )
    start, end = starts[0], ends[0]
    window = instructions[start : end + 1]
    constructor_window = instructions[max(start, end - 10) : end + 1]
    required = {"xor edx, edx", "xor r8d, r8d", "mov rcx, rax", target}
    missing = sorted(required - set(instruction_texts(constructor_window)))
    if start >= end or missing:
        raise AuditError(
            "validator=radioForbidProducerAudit gate=nullRadioIdFactoryArguments "
            f"expected={sorted(required)!r} actualMissing={missing!r}"
        )
    return {
        "enumSelector": texts[start],
        "radioIdArgument": "null",
        "methodInfoArgument": "null",
        "selectorInstructions": [
            {"va": row.get("va"), "text": row.get("text")}
            for row in window[:3]
        ],
        "constructorInstructions": [
            {"va": row.get("va"), "text": row.get("text")}
            for row in constructor_window
        ],
    }


def extract_set_forbid_null_params(
    instructions: list[dict[str, Any]], add_forbid_va: int
) -> dict[str, Any]:
    texts = instruction_texts(instructions)
    target = f"call 0x{add_forbid_va:x}"
    calls = [index for index, text in enumerate(texts) if text == target]
    if len(calls) != 1:
        raise AuditError(
            "validator=radioForbidProducerAudit gate=setForbidAddCall "
            f"expected=1 actual={len(calls)}"
        )
    window = instructions[max(0, calls[0] - 20) : calls[0] + 1]
    required = {"and [rsp+0x28], 0x0", "and [rsp+0x30], 0x0", target}
    missing = sorted(required - set(instruction_texts(window)))
    if missing:
        raise AuditError(
            "validator=radioForbidProducerAudit gate=setForbidNullOptionalParams "
            f"expected={sorted(required)!r} actualMissing={missing!r}"
        )
    return {
        "forbidParamsArgument": "null",
        "methodInfoArgument": "null",
        "instructions": [{"va": row.get("va"), "text": row.get("text")} for row in window],
    }


def scan_object_indexes(index_root: Path) -> dict[str, Any]:
    sources = []
    radio_rows = []
    target_counts = {target: 0 for target in TARGET_RADIOS}
    for source in ("StreamingAssets", "Persistent"):
        directory = index_root / source / "object_index"
        summary_path = directory / "summary.json"
        objects_path = directory / "objects.jsonl.gz"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("complete") is not True or summary.get("errors"):
            raise AuditError(f"{source} object index is incomplete")
        expected_hash = str(summary["outputs"]["objects"]["sha256"])
        actual_hash = sha256(objects_path)
        if actual_hash != expected_hash:
            raise AuditError(f"{source} object index hash drifted")
        line_count = 0
        with gzip.open(objects_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                line_count += 1
                for target in TARGET_RADIOS:
                    if target in line:
                        target_counts[target] += 1
                if RADIO_PARAM in line:
                    row = json.loads(line)
                    radio_rows.append({
                        "source": source,
                        "object": row.get("object") or {},
                    })
        sources.append({
            "source": source,
            "summary": repo_path(summary_path),
            "objects": repo_path(objects_path),
            "objectsSha256": actual_hash,
            "lineCount": line_count,
            "mergedObjectCount": int((summary.get("counts") or {}).get("objects") or 0),
        })
    return {
        "sources": sources,
        "linesRead": sum(row["lineCount"] for row in sources),
        "mergedObjects": sum(row["mergedObjectCount"] for row in sources),
        "radioParamRows": radio_rows,
        "targetIdentifierCounts": target_counts,
    }


def exported_object_path(index_root: Path, row: dict[str, Any]) -> Path:
    path_id = int((row.get("object") or {}).get("pathId") or 0)
    suffix = f"_p{path_id & ((1 << 64) - 1):016X}.json"
    root = index_root / str(row["source"]) / "json_by_type/MonoBehaviour"
    matches = list(root.glob(f"*{suffix}"))
    if len(matches) != 1:
        raise AuditError(f"exported object {suffix}: expected 1, found {len(matches)}")
    return matches[0]


def collect_serialized_instances(index_root: Path, scan: dict[str, Any]) -> dict[str, Any]:
    instances = []
    for row in scan["radioParamRows"]:
        path = exported_object_path(index_root, row)
        payload = json.loads(path.read_text(encoding="utf-8"))
        usages: dict[int, list[str]] = {}

        def walk(value: Any, location: str = "$") -> None:
            if isinstance(value, dict):
                if isinstance(value.get("rid"), int):
                    usages.setdefault(value["rid"], []).append(location)
                for key, child in value.items():
                    if key != "references":
                        walk(child, f"{location}.{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{location}[{index}]")

        walk(payload)
        refs = ((payload.get("references") or {}).get("RefIds") or [])
        for ref in refs:
            if (ref.get("type") or {}).get("class") != "ForbidParamsWithRadioReason":
                continue
            rid = int(ref.get("rid") or 0)
            data = ref.get("data") or {}
            instances.append({
                "object": row["object"],
                "path": repo_path(path),
                "rid": rid,
                "usagePaths": sorted(usages.get(rid) or []),
                "radioId": data.get("radioId"),
                "dataLength": ref.get("dataLength"),
                "layout": data.get("layout"),
            })
    nonempty = sorted({str(row["radioId"]) for row in instances if row.get("radioId")})
    return {"instances": instances, "nonEmptyRadioIds": nonempty}


def scan_lua(lua_root: Path) -> dict[str, Any]:
    producers = []
    constructors = []
    paths = sorted(lua_root.rglob("*.lua"))
    corpus_digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(lua_root).as_posix()
        raw = path.read_bytes()
        corpus_digest.update(relative.encode("utf-8"))
        corpus_digest.update(b"\0")
        corpus_digest.update(hashlib.sha256(raw).digest())
        source = raw.decode("utf-8", errors="replace")
        for match in LUA_PRODUCER.finditer(source):
            producers.append({
                "module": relative,
                "line": source.count("\n", 0, match.start()) + 1,
                "expression": match.group(0),
            })
        if "ForbidParamsWithRadioReason" in source:
            constructors.append(relative)
    return {
        "root": repo_path(lua_root),
        "moduleCount": len(paths),
        "corpusSha256": corpus_digest.hexdigest(),
        "producerReads": sorted(producers, key=lambda row: (row["module"], row["line"])),
        "modulesMentioningRadioParamType": sorted(constructors),
    }


def active_ifix(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    terms = (
        "Radio", "ForbidSystem", "ForbidSettings", "ForbidParams",
        "SendGlobal", "EventManager",
    )
    relevant = [
        row for row in payload.get("fixedMethods") or []
        if any(term.casefold() in str(row.get("signature") or "").casefold() for term in terms)
    ]
    return {
        "path": repo_path(path),
        "patchSha256": str((payload.get("source") or {}).get("patchSha256") or ""),
        "fixedMethodCount": len(payload.get("fixedMethods") or []),
        "relevantFixedMethods": relevant,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog = load_module("radio_forbid_catalog", CATALOG)
    mapper = load_module("radio_forbid_mapper", MAPPER)
    carrier = load_module("radio_forbid_carrier", CARRIER)
    metadata = catalog.Metadata(args.metadata)
    pe = mapper.PeImage(args.gameassembly)
    registration = mapper.find_metadata_registration(pe, mapper.DEFAULT_CODE_REGISTRATION)
    if registration is None:
        raise AuditError("could not derive MetadataRegistration")
    runtime = carrier.RuntimeTypes(pe, metadata, mapper, registration)
    pointers, methods_by_pointer, pointers_by_method = carrier.build_pointer_index(pe, metadata, mapper)

    enum_value = enum_members(metadata, FORBID_ENUM).get(TARGET_ENUM)
    if enum_value is None:
        raise AuditError(f"{TARGET_ENUM} has no metadata constant")
    radio_layout = runtime.layout(find_type(metadata, RADIO_PARAM).index)
    if [(row["name"], row["offset"], row["type"]) for row in radio_layout] != [
        ("radioId", 0x18, "string")
    ]:
        raise AuditError(f"{RADIO_PARAM} layout drifted: {radio_layout!r}")

    selected = {
        "radioConstructor": method_matches(metadata, runtime, RADIO_PARAM, ".ctor", ("string",)),
        "defaultFactory": method_matches(metadata, runtime, FORBID_PARAM, "CreateForbidParams", (FORBID_ENUM,)),
        "addForbid": method_matches(
            metadata, runtime, "Beyond.Gameplay.ForbidSystem", "AddForbid",
            (FORBID_ENUM, "string", "bool", FORBID_PARAM),
        ),
        "setForbidExecute": method_matches(
            metadata, runtime, SET_FORBID, "Execute", ("float",)
        ),
    }
    if any(len(rows) != 1 for rows in selected.values()):
        raise AuditError(f"method selection drifted: {selected!r}")
    method_ids = {key: rows[0] for key, rows in selected.items()}
    method_ptrs = {key: sorted(pointers_by_method.get(index) or []) for key, index in method_ids.items()}
    if any(len(rows) != 1 for rows in method_ptrs.values()):
        raise AuditError(f"method pointer selection drifted: {method_ptrs!r}")
    vas = {key: rows[0] for key, rows in method_ptrs.items()}

    def decode(key: str) -> list[dict[str, Any]]:
        va = vas[key]
        body = carrier.method_body(pe, pointers, va)
        return mapper.decode_x64_subset(body, va, stop_offset=len(body))

    factory_branch = extract_default_radio_factory_branch(
        decode("defaultFactory"), enum_value, vas["radioConstructor"]
    )
    set_forbid_null = extract_set_forbid_null_params(decode("setForbidExecute"), vas["addForbid"])
    ctor_callers = carrier.scan_direct_calls(
        pe, pointers, methods_by_pointer, {vas["radioConstructor"]}
    )
    if len(ctor_callers) != 1 or int(ctor_callers[0]["callerVa"], 16) != vas["defaultFactory"]:
        raise AuditError(
            "validator=radioForbidProducerAudit gate=constructorDirectCaller "
            f"expected=only:0x{vas['defaultFactory']:x} actual={ctor_callers!r}"
        )

    object_scan = scan_object_indexes(args.object_index_root)
    serialized = collect_serialized_instances(args.object_index_root, object_scan)
    lua = scan_lua(args.lua_root)
    ifix = active_ifix(args.ifix)
    failures = []
    if serialized["nonEmptyRadioIds"]:
        failures.append(f"serialized nonempty values={serialized['nonEmptyRadioIds']!r}")
    if any(object_scan["targetIdentifierCounts"].values()):
        failures.append(f"object-index targets={object_scan['targetIdentifierCounts']!r}")
    if lua["modulesMentioningRadioParamType"]:
        failures.append(f"Lua constructors={lua['modulesMentioningRadioParamType']!r}")
    if ifix["relevantFixedMethods"]:
        failures.append(f"IFix targets={ifix['relevantFixedMethods']!r}")
    if failures:
        raise AuditError(
            "validator=radioForbidProducerAudit gate=currentOfflineProducerExclusion "
            "expected=no-nonempty-producers actual=" + "; ".join(failures)
        )

    summary = {
        "objectIndexLinesRead": object_scan["linesRead"],
        "mergedObjects": object_scan["mergedObjects"],
        "serializedRadioParamInstances": len(serialized["instances"]),
        "nonEmptySerializedRadioIds": len(serialized["nonEmptyRadioIds"]),
        "shippedLuaModules": lua["moduleCount"],
        "shippedLuaProducerReads": len(lua["producerReads"]),
        "shippedLuaRadioParamConstructors": len(lua["modulesMentioningRadioParamType"]),
        "activeIfixTargets": ifix["fixedMethodCount"],
        "relevantActiveIfixTargets": len(ifix["relevantFixedMethods"]),
        "e0m0TargetIdentifierMatches": sum(object_scan["targetIdentifierCounts"].values()),
    }
    return {
        "schema": "radioForbidProducerAudit.v1",
        "status": "validated",
        "source": {
            "gameAssembly": str(args.gameassembly.resolve()),
            "gameAssemblySha256": sha256(args.gameassembly),
            "globalMetadata": str(args.metadata.resolve()),
            "globalMetadataSha256": sha256(args.metadata),
            "metadataRegistrationVa": f"0x{registration:x}",
        },
        "managedContract": {
            "forbidType": {"name": TARGET_ENUM, "value": enum_value},
            "radioParamType": RADIO_PARAM,
            "layout": radio_layout,
            "setForbidFields": runtime.layout(find_type(metadata, SET_FORBID).index),
        },
        "nativeContract": {
            "methods": {
                key: {"methodIndex": method_ids[key], "va": f"0x{vas[key]:x}"}
                for key in method_ids
            },
            "defaultFactoryBranch": factory_branch,
            "setForbidAction": set_forbid_null,
            "radioConstructorDirectCallers": ctor_callers,
        },
        "objectIndexes": object_scan,
        "serializedRadioParams": serialized,
        "shippedLua": lua,
        "currentIFix": ifix,
        "summary": summary,
        "conclusion": (
            "The two shipped Lua SHOW_RADIO producers read radioId from a local ForbidParams "
            "subtype, but current offline producers do not supply a non-empty value. The "
            "only direct AOT string-constructor call is the ForbidType default factory, "
            "whose ForbidInteractFacBuilding branch passes null; the SetForbid LevelScript "
            "action also passes null forbidParams. Both serialized subtype instances are "
            "empty, shipped Lua never constructs the subtype, and the active IFix replaces "
            "none of this surface."
        ),
        "evidenceBoundary": (
            "This closes current direct AOT construction, complete indexed MonoBehaviour/"
            "PlayableDirector objects, shipped Lua, and the active Gameplay IFix list. "
            "Indirect/native dispatch, runtime mutation from an unindexed source, "
            "server-provided generic script data, and future builds remain open. "
            "Registration and source grouping do not establish order."
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Radio Forbid Producer Audit",
        "",
        f"- Validation: **{report['status']}**",
        f"- Object-index rows / merged objects: **{summary['objectIndexLinesRead']:,} / {summary['mergedObjects']:,}**",
        f"- Serialized radio-param instances / non-empty ids: **{summary['serializedRadioParamInstances']} / {summary['nonEmptySerializedRadioIds']}**",
        f"- Shipped Lua modules / corpus SHA-256: **{summary['shippedLuaModules']:,} / `{report['shippedLua']['corpusSha256']}`**",
        f"- Shipped Lua producer reads / constructors: **{summary['shippedLuaProducerReads']} / {summary['shippedLuaRadioParamConstructors']}**",
        f"- Relevant active IFix targets: **{summary['relevantActiveIfixTargets']} / {summary['activeIfixTargets']}**",
        f"- e0m0 target identifier matches: **{summary['e0m0TargetIdentifierMatches']}**",
        "",
        "## Exact value path",
        "",
        "`Utils.isForbiddenWithReason(ForbidInteractFacBuilding)` returns `ForbidParams`; "
        "the subtype with the value is `ForbidParamsWithRadioReason` (`radioId:string` "
        "at `+0x18`). The current metadata value of `ForbidInteractFacBuilding` is `25`. "
        "Its default-factory branch passes a null string to the subtype constructor. "
        "The serialized `SetForbid` action has only `_type`, `_isForbid`, and "
        "`m_forbidHandle`, and passes null `forbidParams` to `AddForbid`.",
        "",
        "## Serialized instances",
        "",
        "| Asset | Usage | radioId | Data bytes |",
        "|---|---|---|---:|",
    ]
    for row in report["serializedRadioParams"]["instances"]:
        lines.append(
            f"| `{row['path']}` | `{', '.join(row['usagePaths'])}` | "
            f"`{row.get('radioId') or ''}` | {row.get('dataLength')} |"
        )
    lines.extend([
        "", "## Conclusion", "", report["conclusion"],
        "", "## Boundary", "", report["evidenceBoundary"], "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--object-index-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--lua-root", type=Path, default=DEFAULT_LUA_ROOT)
    parser.add_argument("--ifix", type=Path, default=DEFAULT_IFIX)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(args)
    except (AuditError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"radio forbid producer audit failed: {exc}", file=sys.stderr)
        return 1
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], **report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
