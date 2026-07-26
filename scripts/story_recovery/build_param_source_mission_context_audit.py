#!/usr/bin/env python3
"""Audit the implicit CURRENT_MISSION_ID action-parameter carrier.

The action system can source a parameter from the current execution context
instead of serializing a literal value. This is a plausible way for a
LevelScript playback action to inherit mission identity without declaring a
``missionId`` field, so this audit checks both authored action surfaces:

* structured MissionRuntimeAsset JSON; and
* raw MemoryPack LevelScriptData records.

The result is intentionally fail-closed and build-scoped. It proves only the
current exported corpus and installed metadata/binary/IFix hashes.
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


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import md_escape, write_report_json, write_text_if_changed  # noqa: E402
from story_builder import levelscript_binary  # noqa: E402


CATALOG_PATH = (
    ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
)
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = (
    DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
)
DEFAULT_MISSION_ROOT = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset"
)
DEFAULT_LEVELSCRIPT_ROOT = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "LevelScriptData"
)
DEFAULT_IFIX = (
    ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
)
DEFAULT_JSON = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "param_source_mission_context_audit.json"
)
DEFAULT_MARKDOWN = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "param_source_mission_context_audit.md"
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
EXPECTED_PARAM_SOURCE_VALUES = {
    "CURRENT_LEVEL_ID": 1000,
    "CURRENT_ENTITY_ID": 1001,
    "CURRENT_SCRIPT_ID": 1002,
    "CURRENT_EVENT_ARGS": 1003,
    "CURRENT_MISSION_ID": 1004,
    "CURRENT_SUB_GAME_ID": 1005,
    "CURRENT_SCRIPT_STAGE": 1006,
    "CURRENT_LSM_ID": 1007,
    "CURRENT_PARENT_SCRIPT_ID": 1008,
    "CURRENT_ACTIVITY_ID": 1009,
    "CURRENT_MAP_ID": 1010,
}
EXPECTED_COUNTS = {
    "missionFiles": 490,
    "missionParamSourceOccurrences": 18,
    "missionCurrentMissionOccurrences": 18,
    "missionCurrentMissionMissions": 6,
    "levelScriptFiles": 4512,
    "levelScriptRecords": 74839,
    "levelScriptCurrentMissionRawOccurrences": 0,
    "levelScriptCurrentMissionParamTailOccurrences": 0,
    "levelScriptEmbeddedJsonCurrentMissionOccurrences": 0,
}
EXPECTED_MISSION_ACTION_TYPES = {
    "Beyond.Gameplay.CheckMissionBoolProperty, Gameplay.Beyond": 1,
    "Beyond.Gameplay.CheckMissionIntProperty, Gameplay.Beyond": 17,
}
RELEVANT_IFIX_TERMS = (
    "ActionContext",
    "ParamExtensions",
    "MissionRuntimeAsset::_RunActionInMission",
    "LevelScriptRuntime::GetActionContext",
)
CURRENT_MISSION_SOURCE = 1004
CURRENT_MISSION_BYTES = struct.pack("<i", CURRENT_MISSION_SOURCE)
EMBEDDED_PARAM_SOURCE_RE = re.compile(rb'"paramSource"\s*:\s*(\d+)')


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


def read_compressed_uint(data: bytes, offset: int) -> tuple[int, int]:
    """Read the IL2CPP metadata compressed unsigned-integer encoding."""
    first = data[offset]
    if first < 0x80:
        return first, offset + 1
    if first < 0xC0:
        return ((first & 0x3F) << 8) | data[offset + 1], offset + 2
    if first < 0xE0:
        return (
            ((first & 0x1F) << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3],
            offset + 4,
        )
    if first == 0xF0:
        return struct.unpack_from(">I", data, offset + 1)[0], offset + 5
    raise ValueError(f"unsupported compressed integer prefix 0x{first:02x}")


def zigzag_decode(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def field_default_data_indices(metadata: Any) -> dict[int, int]:
    section = metadata.sections["fieldDefaultValues"]
    rows: dict[int, int] = {}
    for index in range(section.size // 12):
        field_index, _type_index, data_index = struct.unpack_from(
            "<iii", metadata.buf, section.offset + index * 12
        )
        rows[field_index] = data_index
    return rows


def metadata_contract(metadata_path: Path) -> dict[str, Any]:
    catalog = load_module("param_source_catalog", CATALOG_PATH)
    metadata = catalog.Metadata(metadata_path)
    default_data_indices = field_default_data_indices(metadata)

    def find_type(full_name: str) -> Any:
        matches = [
            type_def
            for type_def in metadata.types
            if metadata.type_full_name(type_def) == full_name
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one metadata type {full_name}, found {len(matches)}")
        return matches[0]

    def fields(type_def: Any) -> list[dict[str, Any]]:
        return [
            {
                "name": metadata.string(field.name_index),
                "token": f"0x{field.token:08x}",
                "type": metadata.metadata_type_name(field.type_index),
            }
            for field in metadata.fields_for(type_def)
        ]

    def methods(type_def: Any, selected: set[str]) -> list[dict[str, Any]]:
        return [
            {
                "name": metadata.string(method.name_index),
                "token": f"0x{method.token:08x}",
                "methodIndex": method.index,
            }
            for method in metadata.methods_for(type_def)
            if metadata.string(method.name_index) in selected
        ]

    param_source = find_type("Beyond.Gameplay.Actions.ParamSource")
    default_data = metadata.sections["fieldAndParameterDefaultValueData"]
    values: dict[str, int] = {}
    for field in metadata.fields_for(param_source):
        data_index = default_data_indices.get(field.index)
        if data_index is None:
            continue
        raw, _ = read_compressed_uint(
            metadata.buf,
            default_data.offset + data_index,
        )
        values[metadata.string(field.name_index)] = zigzag_decode(raw)
    param = find_type("Beyond.Gameplay.Actions.Param`1")
    action_context = find_type("Beyond.Gameplay.Actions.ActionContext")
    mission_runtime = find_type("Beyond.Gameplay.MissionRuntimeAsset")
    levelscript_runtime = find_type("Beyond.Gameplay.Core.LevelScriptRuntime")
    param_extensions = find_type("Beyond.Gameplay.Actions.ParamExtensions")
    return {
        "metadataVersion": metadata.version,
        "typeCount": len(metadata.types),
        "fieldCount": len(metadata.fields),
        "methodCount": len(metadata.methods),
        "paramSource": {
            "typeToken": f"0x{param_source.token:08x}",
            "values": values,
        },
        "param": {
            "typeToken": f"0x{param.token:08x}",
            "fields": fields(param),
            "methods": methods(param, {"get_isCurrentMissionId"}),
        },
        "actionContext": {
            "typeToken": f"0x{action_context.token:08x}",
            "fields": fields(action_context),
            "methods": methods(action_context, {"TryGetSelfLevelScript"}),
        },
        "missionRuntime": {
            "typeToken": f"0x{mission_runtime.token:08x}",
            "fields": fields(mission_runtime),
            "methods": methods(
                mission_runtime,
                {"_RunActionInMission", "RunMissionAction", "RunQuestAction"},
            ),
        },
        "levelScriptRuntime": {
            "typeToken": f"0x{levelscript_runtime.token:08x}",
            "fields": fields(levelscript_runtime),
            "methods": methods(levelscript_runtime, {"GetActionContext"}),
        },
        "paramExtensions": {
            "typeToken": f"0x{param_extensions.token:08x}",
            "methods": methods(param_extensions, {"GetValue", "TryGetValue"}),
        },
    }


def find_param_sources(
    value: Any,
    *,
    path: str = "$",
    ancestors: tuple[dict[str, Any], ...] = (),
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        source = value.get("paramSource")
        if isinstance(source, int):
            action_type = next(
                (
                    str(parent.get("$type"))
                    for parent in reversed(ancestors)
                    if parent.get("$type")
                ),
                "",
            )
            rows.append(
                {
                    "path": path,
                    "paramSource": source,
                    "actionType": action_type,
                    "value": value,
                }
            )
        next_ancestors = ancestors + (value,)
        for key, child in value.items():
            rows.extend(
                find_param_sources(
                    child,
                    path=f"{path}.{key}",
                    ancestors=next_ancestors,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(
                find_param_sources(
                    child,
                    path=f"{path}[{index}]",
                    ancestors=ancestors,
                )
            )
    return rows


def scan_missions(root: Path) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    files = [
        path
        for path in sorted(root.glob("*.json"))
        if not path.stem.endswith("_meta")
    ]
    for path in files:
        payload = json.loads(path.read_bytes())
        mission_id = str(payload.get("missionId") or path.stem)
        for row in find_param_sources(payload):
            row["missionId"] = mission_id
            row["sourceFile"] = repo_rel(path)
            all_rows.append(row)
    current_rows = [
        row for row in all_rows if row["paramSource"] == CURRENT_MISSION_SOURCE
    ]
    action_types = Counter(str(row["actionType"]) for row in current_rows)
    return {
        "missionFiles": len(files),
        "paramSourceOccurrences": len(all_rows),
        "paramSourceCounts": dict(
            sorted(Counter(row["paramSource"] for row in all_rows).items())
        ),
        "currentMissionOccurrences": len(current_rows),
        "currentMissionMissions": len(
            {str(row["missionId"]) for row in current_rows}
        ),
        "currentMissionActionTypes": dict(sorted(action_types.items())),
        "currentMissionRows": current_rows,
    }


def validated_param_tail_hits(
    data: bytes,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        next_start = (
            levelscript_binary._record_start(records[index + 1])
            if index + 1 < len(records)
            else len(data)
        )
        payload_start, payload = levelscript_binary._record_payload_window(
            data,
            record,
            next_start,
        )
        search_from = 0
        while True:
            source_offset = payload.find(CURRENT_MISSION_BYTES, search_from)
            if source_offset < 0:
                break
            search_from = source_offset + 1
            tail_offset = source_offset - 4
            if tail_offset < 0 or tail_offset + 12 > len(payload):
                continue
            id_ref, source, path_size = struct.unpack_from(
                "<iii", payload, tail_offset
            )
            if id_ref < -1 or source != CURRENT_MISSION_SOURCE:
                continue
            if path_size == -1:
                path = None
            elif 0 <= path_size <= 1024 and tail_offset + 12 + path_size <= len(payload):
                try:
                    path = payload[
                        tail_offset + 12 : tail_offset + 12 + path_size
                    ].decode("utf-8")
                except UnicodeDecodeError:
                    continue
            else:
                continue
            hits.append(
                {
                    "recordOffset": hex(levelscript_binary._record_start(record)),
                    "payloadOffset": hex(payload_start + tail_offset),
                    "semanticKey": [
                        f"0x{part:04x}"
                        for part in levelscript_binary.levelscript_record_semantic_key(
                            record
                        )
                    ],
                    "localId": record.get("localId"),
                    "uid": record.get("uid"),
                    "idRef": id_ref,
                    "path": path,
                }
            )
    return hits


def scan_levelscripts(root: Path) -> dict[str, Any]:
    files = sorted(root.rglob("*.json"))
    record_count = 0
    raw_rows: list[dict[str, Any]] = []
    tail_rows: list[dict[str, Any]] = []
    embedded_counts: Counter[int] = Counter()
    for path in files:
        data = path.read_bytes()
        records = levelscript_binary.extract_levelscript_uid_records(data)
        record_count += len(records)
        raw_count = data.count(CURRENT_MISSION_BYTES)
        if raw_count:
            raw_rows.append(
                {
                    "sourceFile": repo_rel(path),
                    "occurrences": raw_count,
                }
            )
            for row in validated_param_tail_hits(data, records):
                row["sourceFile"] = repo_rel(path)
                tail_rows.append(row)
        for match in EMBEDDED_PARAM_SOURCE_RE.finditer(data):
            embedded_counts[int(match.group(1))] += 1
    return {
        "levelScriptFiles": len(files),
        "levelScriptRecords": record_count,
        "currentMissionRawOccurrences": sum(
            int(row["occurrences"]) for row in raw_rows
        ),
        "currentMissionRawRows": raw_rows,
        "currentMissionParamTailOccurrences": len(tail_rows),
        "currentMissionParamTailRows": tail_rows,
        "embeddedJsonParamSourceCounts": dict(sorted(embedded_counts.items())),
        "embeddedJsonCurrentMissionOccurrences": embedded_counts[
            CURRENT_MISSION_SOURCE
        ],
    }


def scan_ifix(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_bytes())
    source = payload.get("source") or {}
    fixed = payload.get("fixedMethods") or []
    relevant = [
        row
        for row in fixed
        if any(
            term.casefold() in str(row.get("signature") or "").casefold()
            for term in RELEVANT_IFIX_TERMS
        )
    ]
    return {
        "patchSha256": str(source.get("patchSha256") or "").casefold(),
        "fixedMethodCount": len(fixed),
        "relevantFixedMethods": relevant,
    }


def validate_expected(report: dict[str, Any], *, allow_drift: bool) -> list[str]:
    errors: list[str] = []
    source = report["source"]
    if source["gameAssemblySha256"] != EXPECTED_GAME_ASSEMBLY_SHA256:
        errors.append("GameAssembly SHA256 changed")
    if source["metadataSha256"] != EXPECTED_METADATA_SHA256:
        errors.append("global-metadata SHA256 changed")
    if source["ifixSha256"] != EXPECTED_IFIX_SHA256:
        errors.append("Gameplay IFix SHA256 changed")
    if report["metadataContract"]["paramSource"]["values"] != EXPECTED_PARAM_SOURCE_VALUES:
        errors.append("ParamSource enum values changed")

    mission = report["authored"]["missionRuntime"]
    levelscript = report["authored"]["levelScript"]
    actual_counts = {
        "missionFiles": mission["missionFiles"],
        "missionParamSourceOccurrences": mission["paramSourceOccurrences"],
        "missionCurrentMissionOccurrences": mission["currentMissionOccurrences"],
        "missionCurrentMissionMissions": mission["currentMissionMissions"],
        "levelScriptFiles": levelscript["levelScriptFiles"],
        "levelScriptRecords": levelscript["levelScriptRecords"],
        "levelScriptCurrentMissionRawOccurrences": levelscript[
            "currentMissionRawOccurrences"
        ],
        "levelScriptCurrentMissionParamTailOccurrences": levelscript[
            "currentMissionParamTailOccurrences"
        ],
        "levelScriptEmbeddedJsonCurrentMissionOccurrences": levelscript[
            "embeddedJsonCurrentMissionOccurrences"
        ],
    }
    for key, expected in EXPECTED_COUNTS.items():
        if actual_counts.get(key) != expected:
            errors.append(
                f"{key} changed: expected {expected}, got {actual_counts.get(key)}"
            )
    if mission["currentMissionActionTypes"] != EXPECTED_MISSION_ACTION_TYPES:
        errors.append("MissionRuntime CURRENT_MISSION_ID action types changed")
    if report["installedIfix"]["relevantFixedMethods"]:
        errors.append("installed IFix now replaces a reviewed context method")
    if errors and not allow_drift:
        raise RuntimeError("; ".join(errors))
    return errors


def render_markdown(report: dict[str, Any]) -> str:
    mission = report["authored"]["missionRuntime"]
    levelscript = report["authored"]["levelScript"]
    lines = [
        "# ParamSource mission-context audit",
        "",
        f"- Classification: `{report['classification']}`",
        f"- Story bindings added: `{report['storyBindingsAdded']}`",
        f"- Mission-order edges added: `{report['missionOrderEdgesAdded']}`",
        f"- GameAssembly SHA256: `{report['source']['gameAssemblySha256']}`",
        f"- metadata SHA256: `{report['source']['metadataSha256']}`",
        f"- Gameplay IFix SHA256: `{report['source']['ifixSha256']}`",
        "",
        "## Exact current-build contract",
        "",
        "- `Beyond.Gameplay.Actions.ParamSource.CURRENT_MISSION_ID = 1004`.",
        "- `Param<T>` stores `paramSource`, `path`, `constValue`, `idRef`, and an action context; its metadata exposes `get_isCurrentMissionId`.",
        "- `MissionRuntimeAsset` carries `missionId` and runs mission/quest actions. `LevelScriptRuntime` carries script/level/action-context fields but declares no mission or quest identity.",
        "",
        "## Authored census",
        "",
        f"- MissionRuntime files: `{mission['missionFiles']}`",
        f"- MissionRuntime `paramSource` occurrences: `{mission['paramSourceOccurrences']}`",
        f"- MissionRuntime source `1004` occurrences: `{mission['currentMissionOccurrences']}` across `{mission['currentMissionMissions']}` missions",
        f"- LevelScript files / UID records: `{levelscript['levelScriptFiles']}` / `{levelscript['levelScriptRecords']}`",
        f"- Raw little-endian `1004` values in LevelScript bytes: `{levelscript['currentMissionRawOccurrences']}`",
        f"- Validated `Param` tails using source `1004`: `{levelscript['currentMissionParamTailOccurrences']}`",
        f"- Embedded JSON parameter blobs using source `1004`: `{levelscript['embeddedJsonCurrentMissionOccurrences']}`",
        "",
        "MissionRuntime source-1004 action types:",
        "",
        "| action type | rows |",
        "|---|---:|",
    ]
    for action_type, count in mission["currentMissionActionTypes"].items():
        lines.append(f"| `{md_escape(action_type)}` | {count} |")
    lines.extend(
        [
            "",
            "All 18 current uses are self-mission property checks. None is a Story playback operand, and the complete LevelScript corpus contains no serialized `CURRENT_MISSION_ID` source at all.",
            "",
            "## Boundary",
            "",
            report["finding"],
            "",
            report["coverage"],
            "",
        ]
    )
    if report["validationWarnings"]:
        lines.extend(
            [
                "## Drift warnings",
                "",
                *[f"- {md_escape(item)}" for item in report["validationWarnings"]],
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--mission-root", type=Path, default=DEFAULT_MISSION_ROOT)
    parser.add_argument(
        "--levelscript-root",
        type=Path,
        default=DEFAULT_LEVELSCRIPT_ROOT,
    )
    parser.add_argument("--ifix", type=Path, default=DEFAULT_IFIX)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--allow-drift",
        action="store_true",
        help="write a warning-bearing report instead of failing on corpus/hash drift",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (
        args.gameassembly,
        args.metadata,
        args.mission_root,
        args.levelscript_root,
        args.ifix,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    installed_ifix = scan_ifix(args.ifix)
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "source": {
            "gameAssembly": str(args.gameassembly.resolve()),
            "gameAssemblySha256": sha256_file(args.gameassembly),
            "metadata": str(args.metadata.resolve()),
            "metadataSha256": sha256_file(args.metadata),
            "missionRoot": repo_rel(args.mission_root),
            "levelScriptRoot": repo_rel(args.levelscript_root),
            "ifixAudit": repo_rel(args.ifix),
            "ifixSha256": installed_ifix["patchSha256"],
        },
        "metadataContract": metadata_contract(args.metadata),
        "authored": {
            "missionRuntime": scan_missions(args.mission_root),
            "levelScript": scan_levelscripts(args.levelscript_root),
        },
        "installedIfix": installed_ifix,
        "classification": (
            "implicit_context_only_missionruntime_no_levelscript_story_edge"
        ),
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "finding": (
            "CURRENT_MISSION_ID is a real implicit action-context source, but the "
            "current authored use is confined to 18 MissionRuntime self-property "
            "checks whose mission owner is already explicit. No current LevelScript "
            "byte stream contains the source value, and none of the MissionRuntime "
            "uses supplies a Story id. The carrier therefore adds no mission-to-"
            "LevelScript, mission-to-Story, quest, or order edge."
        ),
        "coverage": (
            "Covers every current structured MissionRuntimeAsset file and every "
            "current raw LevelScriptData file/UID record, the exact ParamSource enum "
            "defaults in installed global metadata, the installed GameAssembly hash, "
            "and the decoded installed Gameplay IFix target list. Server-only action "
            "graphs, opaque runtime-created Param objects, reflection/XLua construction, "
            "future patches, and future builds remain outside the bound."
        ),
        "validationWarnings": [],
    }
    report["validationWarnings"] = validate_expected(
        report,
        allow_drift=args.allow_drift,
    )
    write_report_json(args.out, report)
    write_text_if_changed(args.markdown, render_markdown(report))
    print(
        "param-source mission-context audit: "
        f"{report['authored']['missionRuntime']['currentMissionOccurrences']} "
        "MissionRuntime uses, "
        f"{report['authored']['levelScript']['currentMissionParamTailOccurrences']} "
        "LevelScript uses, 0 Story bindings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
