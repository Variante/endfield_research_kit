#!/usr/bin/env python3
"""Decode the mission-control identity spine in DynamicStreaming fb_main files.

This maintained candidate audit decodes only current-build FlatBuffer fields
whose layouts are established by IL2CPP metadata/native accessors:

FBDynamicSceneChunkData -> FBDynamicSceneSingleGrid -> RootComp -> DataIndex
  -> IdComp / MissionControlComp -> MissionCondition

The report keeps exact numeric IdComp.logicId == exported LevelScript scriptId
joins as cross-system candidates. It never promotes them to ownership or order.
"""

from __future__ import annotations

import argparse
import base64
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import resolve_installed_game_data_root  # noqa: E402

DEFAULT_CLI = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_LEVEL_SCRIPT_ROOT = (
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "LevelScriptData"
)
DEFAULT_METADATA = (
    DEFAULT_GAME_ROOT
    / "il2cpp_data"
    / "Metadata"
    / "global-metadata.dat"
)
DEFAULT_OUT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "dynamic_scene_mission_control_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")


TYPE_NAMES = {
    0: "None",
    1: "DataIndex",
    14: "MissionCondition",
    15: "IdComp",
    18: "TriggerComp",
    25: "MissionControlComp",
    29: "ScriptControlComp",
    30: "ResourceComp",
    31: "RootComp",
    54: "BlightMiasmaComp",
}

GRID_FIELD_DATA_INDEX = 5
GRID_FIELD_MISSION_CONDITION = 16
GRID_FIELD_ID_COMP = 17
GRID_FIELD_MISSION_CONTROL_COMP = 27
GRID_FIELD_SCRIPT_CONTROL_COMP = 31
GRID_FIELD_ROOT_COMP = 33


class DecodeError(ValueError):
    pass


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def _check(data: bytes, offset: int, size: int) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise DecodeError(
            f"out-of-bounds read offset={offset} size={size} len={len(data)}"
        )


def _table_field(data: bytes, table: int, field_index: int) -> int | None:
    _check(data, table, 4)
    vtable = table - _i32(data, table)
    _check(data, vtable, 4)
    vtable_length = _u16(data, vtable)
    slot = 4 + field_index * 2
    if slot + 2 > vtable_length:
        return None
    _check(data, vtable + slot, 2)
    object_offset = _u16(data, vtable + slot)
    if not object_offset:
        return None
    result = table + object_offset
    _check(data, result, 1)
    return result


def _table_vector(data: bytes, table: int, field_index: int) -> tuple[int, int] | None:
    field = _table_field(data, table, field_index)
    if field is None:
        return None
    _check(data, field, 4)
    vector = field + _u32(data, field)
    _check(data, vector, 4)
    length = _u32(data, vector)
    return vector + 4, length


def _vector_table(data: bytes, vector_data: int, index: int) -> int:
    element = vector_data + index * 4
    _check(data, element, 4)
    table = element + _u32(data, element)
    _check(data, table, 4)
    return table


def _vector_string(data: bytes, vector_data: int, index: int) -> str:
    element = vector_data + index * 4
    _check(data, element, 4)
    string = element + _u32(data, element)
    _check(data, string, 4)
    length = _u32(data, string)
    _check(data, string + 4, length)
    return data[string + 4 : string + 4 + length].decode("utf-8")


def _data_index(data: bytes, offset: int) -> dict[str, int | bool | str]:
    _check(data, offset, 16)
    is_invalid, type_id, grid_id, index = struct.unpack_from(
        "<B3x i I i", data, offset
    )
    return {
        "isInvalid": bool(is_invalid),
        "type": type_id,
        "typeName": TYPE_NAMES.get(type_id, str(type_id)),
        "gridId": grid_id,
        "index": index,
    }


def _data_group(data: bytes, offset: int) -> dict[str, int | bool | str]:
    result = _data_index(data, offset)
    _check(data, offset + 16, 8)
    result["num"], result["totalInGrid"] = struct.unpack_from("<ii", data, offset + 16)
    return result


def _script_control(data: bytes, offset: int) -> dict[str, int]:
    _check(data, offset, 4)
    return {"defaultLoad": _i32(data, offset)}


def _scene_name(file_name: str) -> str:
    match = re.search(r"/Scene/([^/]+)/", file_name)
    return match.group(1) if match else ""


def decode_chunks(
    lines: Iterable[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chunks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip().startswith("{"):
            continue
        try:
            row = json.loads(line)
            file_name = str(row["fileName"])
            data = base64.b64decode(row["dataBase64"], validate=True)
            if len(data) != int(row["length"]):
                raise DecodeError("base64 payload length does not match stream row")
            _check(data, 0, 4)
            root = _u32(data, 0)
            _check(data, root, 4)
            total_strings_vector = _table_vector(data, root, 4)
            total_strings = (
                [
                    _vector_string(data, total_strings_vector[0], index)
                    for index in range(total_strings_vector[1])
                ]
                if total_strings_vector
                else []
            )
            grids_vector = _table_vector(data, root, 3)
            grids: list[dict[str, Any]] = []
            if grids_vector:
                for grid_index in range(grids_vector[1]):
                    grid_table = _vector_table(data, grids_vector[0], grid_index)
                    unique_id_field = _table_field(data, grid_table, 0)
                    if unique_id_field is None:
                        raise DecodeError("SingleGrid is missing UniqueId")
                    grids.append(
                        {
                            "data": data,
                            "table": grid_table,
                            "uniqueId": _u32(data, unique_id_field),
                            "gridIndex": grid_index,
                            "strings": total_strings,
                            "fileName": file_name,
                            "scene": _scene_name(file_name),
                        }
                    )
            chunks.append(
                {
                    "fileName": file_name,
                    "scene": _scene_name(file_name),
                    "byteLength": len(data),
                    "grids": grids,
                }
            )
        except Exception as exc:  # keep a full-file audit instead of stopping early
            errors.append(
                {
                    "line": line_number,
                    "fileName": locals().get("file_name", ""),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return chunks, errors


def _grid_vector(grid: dict[str, Any], field_index: int) -> tuple[int, int] | None:
    return _table_vector(grid["data"], grid["table"], field_index)


def build_mission_roots(chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grid_candidates: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        for grid in chunk["grids"]:
            grid_candidates[(grid["scene"], grid["uniqueId"])].append(grid)

    duplicate_grids = [
        {
            "scene": key[0],
            "gridId": key[1],
            "files": sorted({grid["fileName"] for grid in grids}),
        }
        for key, grids in sorted(grid_candidates.items())
        if len(grids) != 1
    ]

    roots: list[dict[str, Any]] = []
    for chunk in chunks:
        for owner_grid in chunk["grids"]:
            root_vector = _grid_vector(owner_grid, GRID_FIELD_ROOT_COMP)
            if not root_vector:
                continue
            data = owner_grid["data"]
            for root_index in range(root_vector[1]):
                root_offset = root_vector[0] + root_index * 84
                _check(data, root_offset, 84)
                root_type, state = struct.unpack_from("<iI", data, root_offset)
                component_group = _data_group(data, root_offset + 8)
                if component_group["isInvalid"] or component_group["type"] != 1:
                    continue
                group_targets = grid_candidates.get(
                    (owner_grid["scene"], int(component_group["gridId"])), []
                )
                if len(group_targets) != 1:
                    continue
                component_index_grid = group_targets[0]
                data_index_vector = _grid_vector(
                    component_index_grid, GRID_FIELD_DATA_INDEX
                )
                if not data_index_vector:
                    continue
                refs: list[dict[str, Any]] = []
                start = int(component_group["index"])
                count = int(component_group["num"])
                if start < 0 or count < 0 or start + count > data_index_vector[1]:
                    continue
                for ref_index in range(start, start + count):
                    refs.append(
                        _data_index(
                            component_index_grid["data"],
                            data_index_vector[0] + ref_index * 16,
                        )
                    )
                mission_refs = [ref for ref in refs if ref["type"] == 25]
                id_refs = [ref for ref in refs if ref["type"] == 15]
                script_refs = [ref for ref in refs if ref["type"] == 29]
                if not mission_refs or len(id_refs) != 1:
                    continue

                id_ref = id_refs[0]
                id_targets = grid_candidates.get(
                    (owner_grid["scene"], int(id_ref["gridId"])), []
                )
                if len(id_targets) != 1:
                    continue
                id_grid = id_targets[0]
                id_vector = _grid_vector(id_grid, GRID_FIELD_ID_COMP)
                id_index = int(id_ref["index"])
                if not id_vector or id_index < 0 or id_index >= id_vector[1]:
                    continue
                logic_id = _u64(id_grid["data"], id_vector[0] + id_index * 8)

                mission_controls: list[dict[str, Any]] = []
                for mission_ref in mission_refs:
                    mission_targets = grid_candidates.get(
                        (owner_grid["scene"], int(mission_ref["gridId"])), []
                    )
                    if len(mission_targets) != 1:
                        continue
                    mission_grid = mission_targets[0]
                    mission_vector = _grid_vector(
                        mission_grid, GRID_FIELD_MISSION_CONTROL_COMP
                    )
                    mission_index = int(mission_ref["index"])
                    if (
                        not mission_vector
                        or mission_index < 0
                        or mission_index >= mission_vector[1]
                    ):
                        continue
                    mission_offset = mission_vector[0] + mission_index * 32
                    condition_group = _data_group(mission_grid["data"], mission_offset)
                    compare_type, to_be_true = struct.unpack_from(
                        "<ii", mission_grid["data"], mission_offset + 24
                    )
                    conditions: list[dict[str, Any]] = []
                    condition_targets = grid_candidates.get(
                        (owner_grid["scene"], int(condition_group["gridId"])), []
                    )
                    if (
                        not condition_group["isInvalid"]
                        and condition_group["type"] == 14
                        and len(condition_targets) == 1
                    ):
                        condition_grid = condition_targets[0]
                        condition_vector = _grid_vector(
                            condition_grid, GRID_FIELD_MISSION_CONDITION
                        )
                        condition_start = int(condition_group["index"])
                        condition_count = int(condition_group["num"])
                        if (
                            condition_vector
                            and condition_start >= 0
                            and condition_count >= 0
                            and condition_start + condition_count <= condition_vector[1]
                        ):
                            for condition_index in range(
                                condition_start, condition_start + condition_count
                            ):
                                condition_offset = (
                                    condition_vector[0] + condition_index * 16
                                )
                                string_index, is_quest, condition_state, is_same = (
                                    struct.unpack_from(
                                        "<iiii", condition_grid["data"], condition_offset
                                    )
                                )
                                identifier = (
                                    condition_grid["strings"][string_index]
                                    if 0 <= string_index < len(condition_grid["strings"])
                                    else ""
                                )
                                conditions.append(
                                    {
                                        "identifier": identifier,
                                        "stringIndex": string_index,
                                        "isQuest": bool(is_quest),
                                        "state": condition_state,
                                        "isSame": bool(is_same),
                                    }
                                )
                    mission_controls.append(
                        {
                            "componentIndex": mission_index,
                            "compareType": compare_type,
                            "toBeTrue": bool(to_be_true),
                            "conditions": conditions,
                        }
                    )

                script_controls: list[dict[str, Any]] = []
                for script_ref in script_refs:
                    script_targets = grid_candidates.get(
                        (owner_grid["scene"], int(script_ref["gridId"])), []
                    )
                    if len(script_targets) != 1:
                        continue
                    script_grid = script_targets[0]
                    script_vector = _grid_vector(
                        script_grid, GRID_FIELD_SCRIPT_CONTROL_COMP
                    )
                    script_index = int(script_ref["index"])
                    if (
                        not script_vector
                        or script_index < 0
                        or script_index >= script_vector[1]
                    ):
                        continue
                    script_controls.append({
                        "componentIndex": script_index,
                        **_script_control(
                            script_grid["data"],
                            script_vector[0] + script_index * 4,
                        ),
                    })

                if mission_controls:
                    row = {
                        "scene": owner_grid["scene"],
                        "sourceFile": owner_grid["fileName"],
                        "gridId": owner_grid["uniqueId"],
                        "gridIndex": owner_grid["gridIndex"],
                        "rootIndex": root_index,
                        "rootType": root_type,
                        "state": state,
                        "logicId": str(logic_id),
                        "componentRefs": refs,
                        "missionControls": mission_controls,
                    }
                    if script_controls:
                        row["scriptControls"] = script_controls
                    roots.append(row)
    return roots, duplicate_grids


def exported_level_scripts(root: Path) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not root.exists():
        return result
    for path in root.rglob("*.json"):
        if not path.stem.isdigit():
            continue
        row = {
            "levelId": path.parent.name,
            "scriptId": path.stem,
            "sourceFile": path.as_posix(),
        }
        key = json.dumps(row, sort_keys=True)
        if all(json.dumps(existing, sort_keys=True) != key for existing in result[path.stem]):
            result[path.stem].append(row)
    return result


def story_occurrences(
    level_script_root: Path = DEFAULT_LEVEL_SCRIPT_ROOT,
) -> dict[str, list[dict[str, Any]]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.story_builder.level_bindings import (  # local import is expensive
        build_levelscript_action_story_occurrences,
    )

    by_script: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for story_key, rows in build_levelscript_action_story_occurrences(
        level_script_root
    ).items():
        for row in rows:
            compact = {
                "storyKey": story_key,
                "levelId": str(row.get("levelId") or ""),
                "scriptId": str(row.get("scriptId") or ""),
                "sourceFile": str(row.get("sourceFile") or ""),
                "recordOffset": row.get("recordOffset"),
                "actionName": str(row.get("actionName") or ""),
                "nativeEventOwnerStatus": str(
                    row.get("nativeEventOwnerStatus") or ""
                ),
            }
            by_script[compact["scriptId"]].append(compact)
    return by_script


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# DynamicScene mission-control / LevelScript identity audit",
        "",
        "This report uses installed DynamicStreaming FlatBuffers and exported "
        "LevelScript data only. Exact numeric equality is retained as a typed "
        "cross-system candidate; promotion still requires runtime namespace/owner "
        "semantics.",
        "",
        "## Counts",
        "",
        f"- fb_main files decoded: {counts['filesDecoded']}",
        f"- grids decoded: {counts['gridsDecoded']}",
        f"- mission-controlled roots: {counts['missionControlledRoots']}",
        f"- roots whose IdComp.logicId equals an exported LevelScript id: {counts['levelScriptIdentityRoots']}",
        f"- identity-matched roots with Story action-list occurrences: {counts['storyIdentityRoots']}",
        f"- matching Story action-list occurrences: {counts['storyOccurrences']}",
        f"- mission-controlled roots with ScriptControlComp: {counts['missionControlledRootsWithScriptControl']}",
        f"- LevelScript-id matches with ScriptControlComp: {counts['levelScriptIdentityRootsWithScriptControl']}",
        f"- Story-bearing id matches with ScriptControlComp: {counts['storyIdentityRootsWithScriptControl']}",
        f"- mission-controlled roots with TriggerComp: {counts.get('missionControlledRootsWithTriggerComp', 0)}",
        f"- LevelScript-id matches with TriggerComp: {counts.get('levelScriptIdentityRootsWithTriggerComp', 0)}",
        f"- Story-bearing id matches with TriggerComp: {counts.get('storyIdentityRootsWithTriggerComp', 0)}",
        f"- decode errors: {counts['decodeErrors']}",
        f"- duplicate scene/grid ids: {counts['duplicateSceneGridIds']}",
        "",
        "## Story-bearing exact identity candidates",
        "",
        "| Scene | logicId / scriptId | Mission conditions | Story playback | Source |",
        "|---|---:|---|---|---|",
    ]
    for row in report["storyIdentityCandidates"]:
        conditions = ", ".join(
            condition["identifier"]
            for control in row["missionControls"]
            for condition in control["conditions"]
            if condition["identifier"]
        )
        stories = ", ".join(
            occurrence["storyKey"] for occurrence in row["storyOccurrences"]
        )
        lines.append(
            f"| {row['scene']} | {row['logicId']} | {conditions} | {stories} | `{row['sourceFile']}` |"
        )
    if not report["storyIdentityCandidates"]:
        lines.append("| — | — | — | — | — |")
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "`IdComp.logicId` is an authored DynamicScene identity and the exported "
            "LevelScript dictionary/file key is an authored script identity. Their "
            "numeric equality is exact original-data evidence, but this audit does "
            "not assume the two identity namespaces are equivalent. Native ownership "
            "or a serialized typed carrier must establish that before Story edges are "
            "promoted.",
            "",
            f"- Classification: `{report['nativeIdentityBoundary']['classification']}`",
            f"- Mission graph action: `{report['nativeIdentityBoundary']['missionGraphAction']}`",
            f"- Direct runtime bridge found: `{str(report['nativeIdentityBoundary']['directBridgeFound']).lower()}`",
            "",
            "### ScriptControlComp closure",
            "",
            "`FBDynamicSceneScriptControlComp` serializes only "
            "`DefaultLoad:int32`. `DynamicSceneScriptControlSystem` indexes "
            "component/entity and DynamicScene logic identities for local "
            "decoration, animation, audio, view-state, and attachment control. "
            "It has no LevelScript pointer, mission/quest identity, or Story "
            "field and therefore does not close the namespace bridge.",
            "",
            "### TriggerComp closure",
            "",
            "`FBDynamicSceneSingleGrid` constructor order maps component type "
            "`18` to `FBDynamicSceneTriggerComp`, type `30` to "
            "`FBDynamicSceneResourceComp`, and type `54` to "
            "`FBDynamicSceneBlightMiasmaComp`.",
            "",
            "Every current mission-controlled root carries IdComp, "
            "MissionControlComp, ResourceComp, and BlightMiasmaComp; none "
            "carries TriggerComp. TriggerComp itself serializes shape, radius, "
            "center, size, transform, and a position-list group, with no "
            "trigger-slot, LevelScript, mission, quest, or Story identity. "
            "ResourceComp contains resource/mount/navigation/LOD groups and "
            "NavState; BlightMiasmaComp contains only Empty.",
            "",
            "Therefore the LevelScript slot-80001 event in the focused action "
            "bridge is not a DynamicScene TriggerComp foreign key.",
            "",
        ]
    )
    return "\n".join(lines)


def load_stream_lines(
    cli: Path,
    game_root: Path,
    input_path: Path | None,
) -> tuple[list[str], dict[str, Any]]:
    if input_path is not None:
        raw = input_path.read_bytes()
        return raw.decode("utf-8-sig").splitlines(), {
            "mode": "prepared_jsonl",
            "path": str(input_path),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    if not cli.is_file():
        raise FileNotFoundError(cli)
    command = [
        str(cli),
        "stream",
        "--streaming-assets",
        str(game_root / "Persistent"),
        "--fallback-assets",
        str(game_root / "StreamingAssets"),
        "--block-type",
        "dynamic-streaming",
        "--file-regex",
        r"(?i)/fb_main_[^/]*\.bytes$",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if completed.returncode:
        raise RuntimeError(
            f"AnimeStudio stream failed with {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    raw = completed.stdout.encode("utf-8")
    return completed.stdout.splitlines(), {
        "mode": "current_persistent_with_streaming_fallback",
        "streamingAssets": str(game_root / "Persistent"),
        "fallbackAssets": str(game_root / "StreamingAssets"),
        "command": command,
        "stdoutBytes": len(raw),
        "stdoutSha256": hashlib.sha256(raw).hexdigest(),
        "stderr": completed.stderr.strip(),
    }


def fingerprint_file(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {
        "path": str(path),
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Prepared AnimeStudio stream JSONL; defaults to current game data.",
    )
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument(
        "--level-script-root",
        type=Path,
        default=DEFAULT_LEVEL_SCRIPT_ROOT,
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--markdown",
        type=Path,
        default=DEFAULT_MARKDOWN,
    )
    args = parser.parse_args()

    lines, dynamic_source = load_stream_lines(
        args.cli,
        args.game_root,
        args.input,
    )
    chunks, errors = decode_chunks(lines)
    roots, duplicate_grids = build_mission_roots(chunks)
    scripts = exported_level_scripts(args.level_script_root)
    occurrences = story_occurrences(args.level_script_root)
    metadata_source = (
        fingerprint_file(args.metadata)
        if args.metadata.is_file()
        else {"path": str(args.metadata), "missing": True}
    )

    identity_roots: list[dict[str, Any]] = []
    story_candidates: list[dict[str, Any]] = []
    for root in roots:
        matches = scripts.get(root["logicId"], [])
        if not matches:
            continue
        row = dict(root)
        row["levelScriptMatches"] = matches
        matched_levels = {match["levelId"] for match in matches}
        row["storyOccurrences"] = [
            occurrence
            for occurrence in occurrences.get(root["logicId"], [])
            if occurrence["levelId"] in matched_levels
        ]
        identity_roots.append(row)
        if row["storyOccurrences"]:
            story_candidates.append(row)

    roots.sort(key=lambda row: (row["scene"], int(row["logicId"]), row["sourceFile"]))
    identity_roots.sort(
        key=lambda row: (row["scene"], int(row["logicId"]), row["sourceFile"])
    )
    story_candidates.sort(
        key=lambda row: (row["scene"], int(row["logicId"]), row["sourceFile"])
    )
    report = {
        "schemaVersion": 1,
        "policy": (
            "Installed DynamicStreaming FlatBuffers and exported "
            "LevelData/LevelScript only. Exact numeric equality is retained as "
            "a cross-system candidate, never mission ownership or chronology. "
            "OCR, gameplay, filenames, and coordinates do not create bindings."
        ),
        "sources": {
            "dynamicStreaming": dynamic_source,
            "levelScriptRoot": str(args.level_script_root),
            "il2cppMetadata": metadata_source,
        },
        "counts": {
            "filesDecoded": len(chunks),
            "gridsDecoded": sum(len(chunk["grids"]) for chunk in chunks),
            "missionControlledRoots": len(roots),
            "levelScriptIdentityRoots": len(identity_roots),
            "storyIdentityRoots": len(story_candidates),
            "storyOccurrences": sum(
                len(row["storyOccurrences"]) for row in story_candidates
            ),
            "missionControlledRootsWithScriptControl": sum(
                bool(row.get("scriptControls")) for row in roots
            ),
            "levelScriptIdentityRootsWithScriptControl": sum(
                bool(row.get("scriptControls")) for row in identity_roots
            ),
            "storyIdentityRootsWithScriptControl": sum(
                bool(row.get("scriptControls")) for row in story_candidates
            ),
            "missionControlledRootsWithTriggerComp": sum(
                any(ref.get("type") == 18 for ref in row.get("componentRefs") or [])
                for row in roots
            ),
            "levelScriptIdentityRootsWithTriggerComp": sum(
                any(ref.get("type") == 18 for ref in row.get("componentRefs") or [])
                for row in identity_roots
            ),
            "storyIdentityRootsWithTriggerComp": sum(
                any(ref.get("type") == 18 for ref in row.get("componentRefs") or [])
                for row in story_candidates
            ),
            "decodeErrors": len(errors),
            "duplicateSceneGridIds": len(duplicate_grids),
        },
        "storyIdentityCandidates": story_candidates,
        "levelScriptIdentityCandidates": identity_roots,
        "missionControlledRoots": roots,
        "duplicateSceneGridIds": duplicate_grids,
        "decodeErrors": errors,
        "nativeIdentityBoundary": {
            "classification": "exact_cross_reference_not_runtime_owner",
            "dynamicIdentity": (
                "FBDynamicSceneIdComp.UniqueId is registered in the "
                "DynamicScene logic-id-to-entity-id map"
            ),
            "levelScriptIdentity": (
                "LevelScriptBriefData.scriptId is resolved through a "
                "LevelScriptContainer selected by LevelScriptPtr"
            ),
            "directBridgeFound": False,
            "directBridgeMeaning": (
                "no DynamicScene MissionControl condition to LevelScript "
                "activation edge"
            ),
            "missionActivationBridgeFound": False,
            "missionGraphAction": "none",
            "promotionRequirement": (
                "a typed serialized or runtime edge must show that the "
                "DynamicScene mission condition activates the matched "
                "LevelScript header/action chain"
            ),
            "scriptControlBoundary": {
                "serializedType":
                    "Beyond.Gameplay.Core.DynamicScene."
                    "FBDynamicSceneScriptControlComp",
                "serializedFields": ["DefaultLoad:int32"],
                "runtimeSystem":
                    "Beyond.Gameplay.Core.DynamicScene."
                    "DynamicSceneScriptControlSystem",
                "runtimeIdentityMaps": [
                    "m_compIdToScriptRuntimeIndexMap",
                    "m_logicIdToScriptRuntimeIndexMap",
                ],
                "levelScriptPointerFieldFound": False,
                "missionOrQuestFieldFound": False,
                "storyFieldFound": False,
                "classification":
                    "dynamic_scene_entity_control_not_levelscript_bridge",
            },
            "triggerComponentBoundary": {
                "componentTypeMap": {
                    "18": "FBDynamicSceneTriggerComp",
                    "30": "FBDynamicSceneResourceComp",
                    "54": "FBDynamicSceneBlightMiasmaComp",
                },
                "rootComponentPopulation": [
                    "IdComp",
                    "MissionControlComp",
                    "ResourceComp",
                    "BlightMiasmaComp",
                ],
                "triggerCompFields": [
                    "Shape:int32",
                    "Radius:float",
                    "Center:FBDynamicSceneVector3",
                    "Size:FBDynamicSceneVector3",
                    "Trans:FBDynamicSceneTransform",
                    "PosListGroup:FBDynamicSceneDataGroup",
                ],
                "resourceCompFields": [
                    "Res:FBDynamicSceneDataGroup",
                    "Mount:FBDynamicSceneDataGroup",
                    "MountViewModel:FBDynamicSceneDataGroup",
                    "NavState:int32",
                    "NavData:FBDynamicSceneDataGroup",
                    "LodInfo:FBDynamicSceneDataGroup",
                ],
                "blightMiasmaCompFields": ["Empty:bool"],
                "triggerSlotFieldFound": False,
                "levelScriptPointerFieldFound": False,
                "missionOrQuestFieldFound": False,
                "storyFieldFound": False,
                "classification":
                    "no_dynamic_scene_trigger_slot_or_levelscript_carrier",
            },
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))
    print(f"wrote {args.out}")
    print(f"wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
