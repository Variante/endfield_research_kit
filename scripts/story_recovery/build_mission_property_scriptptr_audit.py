#!/usr/bin/env python3
"""Audit the Mission property -> ParamVariable.m_scriptPtr bridge candidate.

MissionRuntimeAsset serializes initial ParamKeyValue rows and also declares a
runtime-only Dictionary<string, ParamVariable>. ParamVariable in turn carries a
LevelScriptPtr used by local LevelScript change subscriptions. This audit keeps
those facts separate and fails closed when the reviewed binaries, authored
shape, direct-call census, or current IFix boundary changes.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import md_escape, write_report_json, write_text_if_changed  # noqa: E402


MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
CATALOG_PATH = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_MISSION_ROOTS = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset",
)
DEFAULT_IFIX = (
    ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
)
DEFAULT_JSON = (
    ROOT / "reports" / "story" / "recovery" / "mission_property_scriptptr_audit.json"
)
DEFAULT_MARKDOWN = (
    ROOT / "reports" / "story" / "recovery" / "mission_property_scriptptr_audit.md"
)

EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_IFIX_SHA256 = (
    "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21"
)

NATIVE_METHODS = {
    "MissionRuntimeAsset::.ctor": {
        "token": "0x06002b84",
        "va": 0x182F20750,
        "bytes": 528,
        "sha256": "435fae7322a5c24d356cd3263d876af8848c791b9697dd0a6af7e855d3f8f138",
    },
    "MissionData::.ctor": {
        "token": "0x060052f8",
        "va": 0x183378380,
        "bytes": 272,
        "sha256": "c30f539186327cc5e751413b7987ed89590588a09d31a75cc73b78b90ec05c12",
    },
    "MissionSystem::Handle_SyncAllMission": {
        "token": "0x0600529c",
        "va": 0x1833784E0,
        "bytes": 14368,
        "sha256": "a83ea25aa1555aaf4f3ee5d5255bad12aa44933f35f6c461db12d040bed159c1",
    },
    "MissionSystem::Handle_UpdateMissionProperty": {
        "token": "0x060052a1",
        "va": 0x1873C02E4,
        "bytes": 1188,
        "sha256": "59333b3a0c69e6d38e6621a41ae071d03adea8c4bbc902e81684c1ef95ec40b4",
    },
    "MissionSystem::Handle_MissionStateUpdate": {
        "token": "0x060052a2",
        "va": 0x1873BE300,
        "bytes": 2416,
        "sha256": "4f9fdcd64f410918ead2400c2a39a0889ea68fe614b856dd11ae3170a8da1704",
    },
    "ParamVariable::SetupOnPropertyChangedEventForLevelScript": {
        "token": "0x06003626",
        "va": 0x183BE53E0,
        "bytes": 736,
        "sha256": "77192cfc4f797ba7507862fe56bc4440b27d5c0d781646879da5d96d7075d4c5",
    },
    "ParamVariable::SetupOnBBVariableChangedEventForLevelScript": {
        "token": "0x0600362d",
        "va": 0x1849832C0,
        "bytes": 208,
        "sha256": "f3eb3722c7d689a43e662e215b7181a5df0d9b9315621b9e98b2c60d8ac5be15",
    },
}

DIRECT_TARGETS = {
    "ParamVariableExtensions.ToVariable": 0x18390C9C0,
    "ParamVariable.SetupOnPropertyChangedEventForEntity": 0x183BE59C0,
    "ParamVariable.SetupOnPropertyChangedEventForLevelScript": 0x183BE53E0,
    "ParamVariable.SetupOnBBVariableChangedEventForEntity": 0x1872905D0,
    "ParamVariable.SetupOnBBVariableChangedEventForLevelScript": 0x1849832C0,
}
EXPECTED_DIRECT_COUNTS = {
    "ParamVariableExtensions.ToVariable": 7,
    "ParamVariable.SetupOnPropertyChangedEventForEntity": 4,
    "ParamVariable.SetupOnPropertyChangedEventForLevelScript": 2,
    "ParamVariable.SetupOnBBVariableChangedEventForEntity": 2,
    "ParamVariable.SetupOnBBVariableChangedEventForLevelScript": 2,
}
EXPECTED_SCRIPT_CALLERS = {
    "ParamVariable.SetupOnPropertyChangedEventForLevelScript": {
        "Beyond.Gameplay.Core.LevelEventManager.RegisterScriptEventActionTriggerOnPropertyChanged",
        "Beyond.Gameplay.Actions.ScriptEvent.OnPropertyChanged.OnAfterLevelScriptTriggerRegistered",
    },
    "ParamVariable.SetupOnBBVariableChangedEventForLevelScript": {
        "Beyond.Gameplay.Actions.ScriptEvent.OnBBVariableChanged.OnAfterLevelScriptTriggerRegistered",
    },
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(recursive_keys(child))
    return keys


def scan_authored_properties(roots: list[Path]) -> dict[str, Any]:
    mission_count = 0
    missions_with_properties = 0
    property_rows = 0
    unique_property_keys: set[str] = set()
    value_types: Counter[str] = Counter()
    serialized_keys: set[str] = set()
    forbidden_rows: list[dict[str, Any]] = []
    literal_runtime_field_hits: list[dict[str, Any]] = []
    layered_paths: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            if path.stem.endswith("_meta"):
                continue
            layered_paths[path.name.casefold()] = path
    for path in sorted(layered_paths.values(), key=lambda item: item.name.casefold()):
        raw = path.read_bytes()
        for term in (b"propertyDic", b"propertyDict", b"m_scriptPtr"):
            if term in raw:
                literal_runtime_field_hits.append(
                    {"path": repo_rel(path), "term": term.decode("ascii")}
                )
        payload = json.loads(raw)
        properties = payload.get("properties") or []
        mission_count += 1
        if properties:
            missions_with_properties += 1
        for index, row in enumerate(properties):
            property_rows += 1
            unique_property_keys.add(str(row.get("key") or ""))
            value = row.get("value") or {}
            value_types[str(value.get("type"))] += 1
            row_keys = recursive_keys(row)
            serialized_keys.update(row_keys)
            forbidden = sorted(
                key
                for key in row_keys
                if any(
                    marker in key.casefold()
                    for marker in (
                        "scriptptr",
                        "scriptid",
                        "levelscript",
                        "propertydic",
                        "propertydict",
                    )
                )
            )
            if forbidden:
                forbidden_rows.append(
                    {
                        "path": repo_rel(path),
                        "index": index,
                        "keys": forbidden,
                    }
                )
    return {
        "missionFiles": mission_count,
        "missionsWithProperties": missions_with_properties,
        "propertyRows": property_rows,
        "uniquePropertyKeys": len(unique_property_keys),
        "valueTypeCounts": dict(sorted(value_types.items())),
        "serializedFieldKeys": sorted(serialized_keys),
        "forbiddenNestedFieldRows": forbidden_rows,
        "literalRuntimeFieldHits": literal_runtime_field_hits,
    }


def verify_native(mapper: Any, game_assembly: Path) -> list[dict[str, Any]]:
    pe = mapper.PeImage(game_assembly)
    rows = []
    for name, expected in NATIVE_METHODS.items():
        raw = pe.bytes_at_va(expected["va"], expected["bytes"])
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected["sha256"]:
            raise RuntimeError(
                f"{name} body changed: expected {expected['sha256']}, got {actual}"
            )
        rows.append(
            {
                "symbol": name,
                "token": expected["token"],
                "address": f"0x{expected['va']:x}",
                "bodyBytes": expected["bytes"],
                "bodySha256": actual,
            }
        )
    return rows


def direct_call_census(
    mapper: Any,
    catalog: Any,
    game_assembly: Path,
    metadata_path: Path,
) -> dict[str, Any]:
    pe = mapper.PeImage(game_assembly)
    metadata = catalog.Metadata(metadata_path)
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    generic_index = mapper.build_generic_method_index(
        pe,
        metadata,
        mapper.DEFAULT_CODE_REGISTRATION,
        mapper.DEFAULT_METADATA_REGISTRATION,
    )
    for pointer, rows in generic_index.items():
        method_by_pointer.setdefault(pointer, rows)
    method_pointers = sorted(
        set(method_by_pointer)
        | {
            pointer
            for pointers in pointers_by_image.values()
            for pointer in pointers
            if pointer
        }
    )
    target_by_va = {va: name for name, va in DIRECT_TARGETS.items()}
    callers: dict[str, list[dict[str, Any]]] = {
        name: [] for name in DIRECT_TARGETS
    }
    for section in pe.sections:
        if section["name"] not in {".text", "il2cpp"} or not section["rawSize"]:
            continue
        raw_start = section["rawPointer"]
        data = pe.buf[raw_start : raw_start + section["rawSize"]]
        position = data.find(b"\xe8")
        while position >= 0:
            if position + 5 <= len(data):
                call_va = pe.image_base + section["virtualAddress"] + position
                relative = struct.unpack_from("<i", data, position + 1)[0]
                target_name = target_by_va.get(call_va + 5 + relative)
                if target_name is not None:
                    pointer_pos = bisect.bisect_right(method_pointers, call_va) - 1
                    method_pointer = (
                        method_pointers[pointer_pos] if pointer_pos >= 0 else None
                    )
                    resolved = method_by_pointer.get(method_pointer, [])
                    labels = sorted(
                        {
                            f"{row.get('type')}.{row.get('method')}"
                            for row in resolved
                            if row.get("type") and row.get("method")
                        }
                    )
                    callers[target_name].append(
                        {
                            "callAddress": f"0x{call_va:x}",
                            "methodPointer": (
                                f"0x{method_pointer:x}" if method_pointer else None
                            ),
                            "offset": (
                                f"0x{call_va - method_pointer:x}"
                                if method_pointer
                                else None
                            ),
                            "resolvedCallers": labels,
                        }
                    )
            position = data.find(b"\xe8", position + 1)

    rows = []
    for name, expected_count in EXPECTED_DIRECT_COUNTS.items():
        target_callers = callers[name]
        if len(target_callers) != expected_count:
            raise RuntimeError(
                f"{name} direct caller count changed: "
                f"expected {expected_count}, got {len(target_callers)}"
            )
        resolved_labels = {
            label
            for caller in target_callers
            for label in caller["resolvedCallers"]
        }
        expected_labels = EXPECTED_SCRIPT_CALLERS.get(name)
        if expected_labels is not None and resolved_labels != expected_labels:
            raise RuntimeError(
                f"{name} resolved callers changed: "
                f"expected {sorted(expected_labels)}, got {sorted(resolved_labels)}"
            )
        rows.append(
            {
                "target": name,
                "address": f"0x{DIRECT_TARGETS[name]:x}",
                "callerCount": len(target_callers),
                "resolvedManagedCallers": sorted(resolved_labels),
                "unresolvedCallerCount": sum(
                    not caller["resolvedCallers"] for caller in target_callers
                ),
                "callers": target_callers,
            }
        )
    return {
        "targets": rows,
        "boundary": (
            "Complete E8 rel32 census over GameAssembly .text/il2cpp sections; "
            "virtual, delegate, reflection, and future IFix dispatch are outside it."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    authored = payload["authoredMissionProperties"]
    lines = [
        "# Mission property / LevelScript pointer audit",
        "",
        f"- GameAssembly SHA-256: `{payload['source']['gameAssemblySha256']}`",
        f"- Metadata SHA-256: `{payload['source']['metadataSha256']}`",
        f"- MissionRuntimeAsset files: `{authored['missionFiles']}`",
        f"- Missions with serialized properties: `{authored['missionsWithProperties']}`",
        f"- Serialized ParamKeyValue rows: `{authored['propertyRows']}`",
        f"- Unique property keys: `{authored['uniquePropertyKeys']}`",
        f"- Story bindings added: `{payload['summary']['storyBindingsAdded']}`",
        "",
        "## Finding",
        "",
        payload["summary"]["finding"],
        "",
        "## Exact separation",
        "",
    ]
    for row in payload["runtimeSeparation"]:
        lines.append(
            f"- `{md_escape(row['carrier'])}`: {md_escape(row['finding'])}"
        )
    lines.extend(["", "## Direct-call census", ""])
    for row in payload["wholeBinaryDirectCallCensus"]["targets"]:
        callers = ", ".join(row["resolvedManagedCallers"]) or "none"
        lines.append(
            f"- `{md_escape(row['target'])}`: `{row['callerCount']}` direct calls; "
            f"resolved managed callers: `{md_escape(callers)}`; unresolved: "
            f"`{row['unresolvedCallerCount']}`."
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            payload["boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument(
        "--mission-root",
        type=Path,
        action="append",
        dest="mission_roots",
        help="MissionRuntimeAsset root; repeat for multiple source layers.",
    )
    parser.add_argument("--ifix", type=Path, default=DEFAULT_IFIX)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    game_hash = sha256_file(args.gameassembly)
    metadata_hash = sha256_file(args.metadata)
    if game_hash != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise RuntimeError(
            f"GameAssembly hash changed: expected {EXPECTED_GAME_ASSEMBLY_SHA256}, "
            f"got {game_hash}"
        )
    if metadata_hash != EXPECTED_METADATA_SHA256:
        raise RuntimeError(
            f"metadata hash changed: expected {EXPECTED_METADATA_SHA256}, "
            f"got {metadata_hash}"
        )

    authored = scan_authored_properties(
        args.mission_roots or list(DEFAULT_MISSION_ROOTS)
    )
    expected_authored = {
        "missionFiles": 490,
        "missionsWithProperties": 70,
        "propertyRows": 214,
        "uniquePropertyKeys": 186,
        "valueTypeCounts": {"1": 10, "3": 204},
    }
    for key, expected in expected_authored.items():
        if authored[key] != expected:
            raise RuntimeError(
                f"authored {key} changed: expected {expected!r}, "
                f"got {authored[key]!r}"
            )
    if authored["forbiddenNestedFieldRows"] or authored["literalRuntimeFieldHits"]:
        raise RuntimeError(
            "MissionRuntimeAsset authored property shape now contains a "
            "LevelScript/runtime-dictionary candidate; inspect before publishing"
        )

    ifix = json.loads(args.ifix.read_text(encoding="utf-8"))
    if ifix["source"]["patchSha256"] != EXPECTED_IFIX_SHA256:
        raise RuntimeError(
            "current IFix hash changed; rebuild and review the IFix mission graph audit"
        )
    relevant_markers = (
        "MissionRuntimeAsset",
        "Handle_SyncAllMission",
        "Handle_UpdateMissionProperty",
        "Handle_MissionStateUpdate",
        "ParamVariable",
        "ParamVariableExtensions",
    )
    ifix_matches = [
        row
        for row in ifix.get("fixedMethods", [])
        if any(
            marker in str(row.get("signature") or "")
            for marker in relevant_markers
        )
    ]
    if ifix_matches:
        raise RuntimeError(
            "current IFix replaces a reviewed mission-property/script-pointer path"
        )

    mapper = load_module("mission_property_audit_mapper", MAPPER_PATH)
    catalog = load_module("mission_property_audit_catalog", CATALOG_PATH)
    native_methods = verify_native(mapper, args.gameassembly)
    call_census = direct_call_census(
        mapper, catalog, args.gameassembly, args.metadata
    )

    payload = {
        "schemaVersion": 1,
        "source": {
            "gameAssembly": str(args.gameassembly.resolve()),
            "gameAssemblySha256": game_hash,
            "metadata": str(args.metadata.resolve()),
            "metadataSha256": metadata_hash,
        },
        "managedLayout": {
            "MissionRuntimeAsset": {
                "missionId": {"token": "0x04003206", "offset": "0x10"},
                "properties": {"token": "0x04003224", "offset": "0xe0"},
                "propertyDic": {"token": "0x0400322b", "offset": "0xf8"},
            },
            "MissionSystem+MissionData": {
                "missionId": {"token": "0x0400487f", "offset": "0x10"},
                "propertyDict": {"token": "0x04004882", "offset": "0x20"},
            },
            "ParamKeyValue": {
                "key": {"token": "0x04003890", "offset": "0x10"},
                "value": {"token": "0x04003891", "offset": "0x18"},
            },
            "ParamVariable": {
                "m_sendToScript": {"token": "0x040038d4", "offset": "0x68"},
                "m_scriptPtr": {"token": "0x040038d5", "offset": "0x70"},
            },
        },
        "authoredMissionProperties": authored,
        "nativeMethods": native_methods,
        "runtimeSeparation": [
            {
                "carrier": "MissionRuntimeAsset.properties",
                "finding": (
                    "Authored ParamKeyValue initial values only; 214 current rows "
                    "contain no LevelScriptPtr/scriptId field."
                ),
            },
            {
                "carrier": "MissionRuntimeAsset.propertyDic",
                "finding": (
                    "A separate empty Dictionary<string, ParamVariable> allocated "
                    "by the constructor at +0xf8; it is not serialized in current "
                    "MissionRuntimeAsset JSON."
                ),
            },
            {
                "carrier": "MissionData.propertyDict",
                "finding": (
                    "Server-synchronized mission values. Sync-all (+0x2044), "
                    "property-update (+0x2c8), and mission-state-update (+0x416) "
                    "call ToVariable(Proto.DYNAMIC_PARAMETER) and write this dictionary."
                ),
            },
            {
                "carrier": "ParamVariable.m_scriptPtr",
                "finding": (
                    "Written by explicit LevelScript property/blackboard event "
                    "subscription setup at +0x70; the mapped managed callers are "
                    "LevelEventManager/ScriptEvent registration, not MissionSystem."
                ),
            },
        ],
        "wholeBinaryDirectCallCensus": call_census,
        "installedPatch": {
            "source": ifix["source"]["label"],
            "sha256": ifix["source"]["patchSha256"],
            "signatureTargetCount": ifix["format"]["fixedMethodCount"],
            "relevantMethodMatches": ifix_matches,
        },
        "summary": {
            "classification": "runtime_context_only_no_mission_levelscript_edge",
            "storyBindingsAdded": 0,
            "confidence": "native_proven_bounded",
            "finding": (
                "The nested managed type shape is not a mission-to-LevelScript "
                "foreign key. Mission properties are authored/server values; "
                "m_scriptPtr is attached later only for local LevelScript event "
                "subscriptions. Add zero mission graph edges."
            ),
        },
        "boundary": (
            "One BB LevelScript setter callsite is native/generic and has no mapped "
            "managed owner; its local call shape carries a LevelScriptPtr and key but "
            "no mission identity. Indirect/delegate/reflection construction, unexported "
            "data, future IFix, and future game builds remain outside the bound."
        ),
    }
    write_report_json(args.out, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    print(
        json.dumps(
            {
                "report": repo_rel(args.out),
                "missions": authored["missionFiles"],
                "missionsWithProperties": authored["missionsWithProperties"],
                "propertyRows": authored["propertyRows"],
                "storyBindingsAdded": 0,
                "classification": payload["summary"]["classification"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
