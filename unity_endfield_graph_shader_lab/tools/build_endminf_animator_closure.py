#!/usr/bin/env python3
"""Build a fail-closed Endminf Animator/controller playback evidence report.

This report joins only exact evidence: the terminal external UI-effect stage,
its source snapshot, CAB-map owner/dependency indices, Animator JSON PPtrs,
AnimatorController metadata and state clip indices, and AssetMap source,
offset, PathID, and type rows.  Names or PathIDs alone never resolve a
controller or AnimationClip.  Missing artifacts and null serialized fields
remain explicit; this tool does not infer a ``ui_overview_start -> loop``
chain.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    from build_endminf_external_pptr_closure import (
        ClosureError,
        _assert_index_summaries_match,
        _asset_map_rows,
        _canonical,
        _digest,
        _file_snapshot,
        _int,
        _iter_json_files,
        _iter_jsonl,
        _json,
        _load_stage,
        _normal_source,
        _relative_path,
        _signed_int64,
        _source_matches,
        _unsigned_path_id,
        _validate_snapshot,
        _object_index_records,
    )
except ModuleNotFoundError:  # pragma: no cover - package-style imports
    from .build_endminf_external_pptr_closure import (
        ClosureError,
        _assert_index_summaries_match,
        _asset_map_rows,
        _canonical,
        _digest,
        _file_snapshot,
        _int,
        _iter_json_files,
        _iter_jsonl,
        _json,
        _load_stage,
        _normal_source,
        _relative_path,
        _signed_int64,
        _source_matches,
        _unsigned_path_id,
        _validate_snapshot,
        _object_index_records,
    )


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_STAGE = LAB_ROOT / "Temp" / "Codex" / "endminf_fx_exact_stage"
DEFAULT_CONTROLLER_ROOT = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "json_by_type"
    / "AnimatorController"
)
DEFAULT_ANIMATION_ROOT = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "json_by_type"
    / "AnimationClip"
)
DEFAULT_ASSET_MAP = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "maps"
    / "endfield_streamingassets_assets.json"
)
DEFAULT_CAB_MAP = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Maps"
    / "endfield_streamingassets_assets.bin"
)
DEFAULT_OUTPUT = (
    LAB_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
    / "Endminf"
    / "ExternalUiEffects"
    / "endminf_animator_playback_closure.json"
)
SCHEMA = "endfield.endminf-animator-playback-closure.v1"
_PATH_ID_RE = re.compile(r"(?:^|[_#])p(?P<hex>[0-9a-f]{16})(?:\.|$)", re.IGNORECASE)


def _stage_filter(stage_path: Path) -> tuple[Path, list[dict[str, Any]]]:
    filters = sorted((stage_path.parent / "filters").glob("*.json"))
    if len(filters) != 1:
        raise ClosureError(f"expected exactly one exact stage filter, found {len(filters)}")
    value = _json(filters[0])
    if not isinstance(value, list) or not value:
        raise ClosureError(f"exact stage filter is not a non-empty list: {filters[0]}")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise ClosureError(f"stage filter row {index} is not an object: {filters[0]}")
        for field in ("Name", "Source", "PathID", "Type", "Offset"):
            if field not in row:
                raise ClosureError(f"stage filter row {index} lacks {field}: {filters[0]}")
        rows.append(row)
    return filters[0], rows


def _path_id_from_filename(path: Path) -> int | None:
    match = _PATH_ID_RE.search(path.name)
    if not match:
        return None
    value = int(match.group("hex"), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def _pint(value: Any, *, field: str, path: Path | None = None) -> int:
    return _signed_int64(value, field=field, path=path)


def _load_cab_map(paths: Iterable[Path]) -> dict[str, list[dict[str, Any]]]:
    try:
        from character_import.audit_generic_actor_animations import parse_cab_map
    except ModuleNotFoundError as exc:  # pragma: no cover - direct CLI adds tools
        raise ClosureError(f"cannot import maintained CAB-map parser: {exc}") from exc
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        if not path.is_file():
            raise ClosureError(f"CAB map is missing: {path}")
        stem = path.stem.casefold()
        if "persistent" in stem:
            asset_root = "Persistent"
        elif "streamingassets" in stem:
            asset_root = "StreamingAssets"
        else:
            raise ClosureError(f"cannot infer AssetRoot from CAB map name: {path}")
        try:
            records = parse_cab_map(path, asset_root)
        except (OSError, EOFError, ValueError) as exc:
            raise ClosureError(f"cannot parse CAB map {path}: {exc}") from exc
        cab_map_relative = _relative_path(path)
        source_snapshots: dict[str, dict[str, Any]] = {}
        for record in records:
            source = str(record.source)
            if source not in source_snapshots:
                source_snapshots[source] = _file_snapshot(Path(source))
            result[str(record.cab)].append(
                {
                    "cabMap": cab_map_relative,
                    "assetRoot": str(record.asset_root),
                    "cab": str(record.cab),
                    "baseFolder": str(record.base_folder),
                    "relativePath": str(record.relative_path),
                    "source": source,
                    "sourceOffset": int(record.offset),
                    "dependencies": [str(dep) for dep in record.dependencies],
                    "sourceSnapshot": dict(source_snapshots[source]),
                }
            )
    for cab in result:
        result[cab].sort(key=lambda row: _canonical(row))
    return result


def _cab_at_source(
    cab_rows: dict[str, list[dict[str, Any]]], source: str, offset: int
) -> dict[str, Any]:
    matches = [
        row
        for rows in cab_rows.values()
        for row in rows
        if int(row["sourceOffset"]) == int(offset)
        and _normal_source(row["source"]) == _normal_source(source)
    ]
    if len(matches) != 1:
        raise ClosureError(
            f"stage source/offset does not identify exactly one CAB: {source} @ {offset}"
        )
    return matches[0]


def _resolve_dependency(
    cab_rows: dict[str, list[dict[str, Any]]], owner_cab: str, file_id: int, path_id: int
) -> dict[str, Any]:
    owners = cab_rows.get(owner_cab) or []
    if len(owners) != 1:
        raise ClosureError(f"CAB owner is missing or ambiguous: {owner_cab}")
    owner = owners[0]
    deps = list(owner.get("dependencies") or [])
    if file_id < 0 or file_id > len(deps):
        raise ClosureError(
            f"PPtr FileID {file_id} is outside {owner_cab} dependency table for PathID {path_id}"
        )
    target_cab = owner_cab if file_id == 0 else deps[file_id - 1]
    targets = cab_rows.get(target_cab) or []
    if len(targets) != 1:
        raise ClosureError(f"PPtr target CAB is missing or ambiguous: {target_cab}")
    target = dict(targets[0])
    target["ownerCab"] = owner_cab
    target["fileId"] = file_id
    target["pathId"] = path_id
    target["dependencyIndex"] = None if file_id == 0 else file_id
    return target


def _metadata(value: dict[str, Any], path: Path) -> dict[str, Any]:
    metadata = value.get("$animestudio")
    if not isinstance(metadata, dict):
        raise ClosureError(f"exact artifact lacks $animestudio metadata: {path}")
    for field in ("pathId", "type", "sourceFile", "sourceOriginalPath", "sourceOffset"):
        if metadata.get(field) is None:
            raise ClosureError(f"exact artifact metadata lacks {field}: {path}")
    return metadata


def _artifact_candidates(
    roots: Iterable[Path],
    *,
    path_id: int,
    cab: str,
    cab_row: dict[str, Any],
    types: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exact: list[dict[str, Any]] = []
    mismatched: list[dict[str, Any]] = []
    for path in (path for root in roots for path in _iter_json_files(root)):
        value = _json(path)
        if not isinstance(value, dict) or not isinstance(value.get("$animestudio"), dict):
            continue
        meta = value["$animestudio"]
        try:
            meta_path_id = _signed_int64(meta.get("pathId"), field="$animestudio.pathId", path=path)
            meta_offset = int(meta.get("sourceOffset"))
        except (TypeError, ValueError, ClosureError):
            continue
        if meta_path_id != path_id or str(meta.get("type") or "") not in types:
            continue
        candidate = {
            "path": _relative_path(path),
            "type": str(meta.get("type") or ""),
            "pathId": meta_path_id,
            "sourceFile": str(meta.get("sourceFile") or ""),
            "sourceOriginalPath": str(meta.get("sourceOriginalPath") or ""),
            "sourceOffset": meta_offset,
            "name": str(value.get("m_Name") or meta.get("name") or ""),
            "snapshot": _file_snapshot(path),
        }
        exact_match = (
            candidate["sourceFile"].casefold() == cab.casefold()
            and candidate["sourceOffset"] == int(cab_row["sourceOffset"])
            and _normal_source(candidate["sourceOriginalPath"]) == _normal_source(cab_row["source"])
        )
        (exact if exact_match else mismatched).append(candidate)
    return exact, mismatched


def _stage_artifact(
    stage_clips: dict[int, dict[str, Any]],
    *,
    path_id: int,
    name: str,
    source: str,
    offset: int,
) -> dict[str, Any] | None:
    entry = stage_clips.get(path_id)
    if entry is None:
        return None
    path = Path(entry["path"])
    value = entry.get("value")
    filter_row = entry.get("filter")
    if not isinstance(value, dict) or not isinstance(filter_row, dict):
        raise ClosureError(f"exact stage AnimationClip provenance is malformed: {path}")
    if filter_row.get("Type") != "AnimationClip":
        raise ClosureError(f"exact stage entry has the wrong type for AnimationClip {path_id}: {path}")
    if int(filter_row.get("PathID")) != int(path_id) or str(filter_row.get("Name") or "") != name:
        raise ClosureError(f"exact stage AnimationClip identity drifted: {path}")
    if _normal_source(filter_row.get("Source")) != _normal_source(source):
        raise ClosureError(
            f"exact stage AnimationClip source mismatch for {name}: "
            f"stage={filter_row.get('Source')!r}, requested={source!r}"
        )
    if int(filter_row.get("Offset")) != int(offset):
        raise ClosureError(
            f"exact stage AnimationClip offset mismatch for {name}: "
            f"stage={filter_row.get('Offset')!r}, requested={offset!r}"
        )
    if str(value.get("m_Name") or "") != name:
        raise ClosureError(f"exact stage AnimationClip name drifted from its object payload: {path}")
    return {
        "basis": "exact_stage_animationclip_json",
        "path": _relative_path(path),
        "name": name,
        "pathId": path_id,
        "source": source,
        "sourceOffset": int(offset),
        "stageEntry": {
            "Name": str(filter_row["Name"]),
            "Source": str(filter_row["Source"]),
            "PathID": int(filter_row["PathID"]),
            "Type": str(filter_row["Type"]),
            "Offset": int(filter_row["Offset"]),
        },
        "snapshot": _file_snapshot(path),
        "loopTime": value.get("m_LoopTime"),
    }


def _cab_source_snapshots(cab_rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for rows in cab_rows.values():
        for row in rows:
            snapshot = row.get("sourceSnapshot")
            if not isinstance(snapshot, dict):
                raise ClosureError(f"CAB row lacks a physical source snapshot: {row.get('cab')}")
            path = str(snapshot.get("path") or "").casefold()
            if not path:
                raise ClosureError(f"CAB row source snapshot lacks a path: {row.get('cab')}")
            previous = snapshots.setdefault(path, snapshot)
            if previous != snapshot:
                raise ClosureError(f"CAB source snapshot is inconsistent: {snapshot.get('path')}")
    return sorted(snapshots.values(), key=_canonical)


def _target_asset_map_rows(paths: Iterable[Path], path_ids: set[int]) -> dict[int, list[dict[str, Any]]]:
    """Read only requested AssetMap objects without decoding the 759 MB map.

    ``endfield_asset_map_filter.iter_asset_entries`` is the maintained broad
    iterator, but this closure needs a handful of exact PathIDs from a very
    large generated map.  The object framing is the same contract used by
    that iterator; non-target rows are never JSON-decoded.  The whole source
    is still streamed once, so a replaced/truncated map cannot be skipped.
    """
    wanted = {int(path_id) for path_id in path_ids}
    rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        if not path.is_file():
            raise ClosureError(f"AssetMap is missing: {path}")
        # ripgrep's literal/regex scanner is substantially faster than
        # decoding every object in this generated 759 MB JSON map.  Context
        # includes the flat AssetEntry object around each requested PathID.
        rg = shutil.which("rg")
        if rg:
            pattern = r'"PathID"\s*:\s*(?:' + "|".join(re.escape(str(value)) for value in sorted(wanted)) + r')\b'
            completed = subprocess.run(
                [rg, "-n", "-C", "10", "--no-heading", "--color", "never", pattern, str(path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if completed.returncode not in (0, 1):
                raise ClosureError(f"cannot scan exact AssetMap {path}: {completed.stderr.strip()}")
            groups = re.split(r"^--\s*$", completed.stdout, flags=re.MULTILINE)
            for group in groups:
                object_lines: list[str] = []
                for line in group.splitlines():
                    match = re.match(r"^\d+[:-](.*)$", line)
                    if not match:
                        continue
                    payload = match.group(1)
                    if not object_lines:
                        if payload.strip().startswith("{"):
                            object_lines.append(payload)
                        continue
                    object_lines.append(payload)
                    if not payload.strip().startswith("}"):
                        continue
                    text = "\n".join(object_lines).rstrip().rstrip(",")
                    object_lines = []
                    try:
                        value = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(value, dict):
                        continue
                    path_id = _signed_int64(value.get("PathID"), field="AssetMap.PathID", path=path)
                    if path_id not in wanted:
                        continue
                    rows[path_id].append(
                        {
                            "assetMap": _relative_path(path),
                            "Name": str(value.get("Name") or ""),
                            "Container": str(value.get("Container") or ""),
                            "Source": str(value.get("Source") or ""),
                            "PathID": path_id,
                            "Type": str(value.get("Type") or ""),
                            "Offset": _int(value.get("Offset"), field="AssetMap.Offset", path=path),
                            "Hash": str(value.get("Hash") or ""),
                        }
                    )
            continue
        inside_entries = False
        buffer: list[str] = []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not inside_entries:
                        if stripped == '"AssetEntries": [':
                            inside_entries = True
                        continue
                    if stripped == "]":
                        break
                    if not buffer:
                        if stripped.startswith("{"):
                            buffer.append(line)
                        continue
                    buffer.append(line)
                    if not (stripped.startswith("}") or stripped.startswith("},")):
                        continue
                    text = "".join(buffer).rstrip().rstrip(",")
                    buffer = []
                    if '"PathID"' not in text:
                        continue
                    match = re.search(r'"PathID"\s*:\s*(-?\d+)', text)
                    if not match or int(match.group(1)) not in wanted:
                        continue
                    try:
                        value = json.loads(text)
                    except json.JSONDecodeError as exc:
                        raise ClosureError(f"invalid exact AssetMap object in {path}: {exc}") from exc
                    if not isinstance(value, dict):
                        continue
                    path_id = _signed_int64(value.get("PathID"), field="AssetMap.PathID", path=path)
                    rows[path_id].append(
                        {
                            "assetMap": _relative_path(path),
                            "Name": str(value.get("Name") or ""),
                            "Container": str(value.get("Container") or ""),
                            "Source": str(value.get("Source") or ""),
                            "PathID": path_id,
                            "Type": str(value.get("Type") or ""),
                            "Offset": _int(value.get("Offset"), field="AssetMap.Offset", path=path),
                            "Hash": str(value.get("Hash") or ""),
                        }
                    )
        except OSError as exc:
            raise ClosureError(f"cannot read AssetMap {path}: {exc}") from exc
    return rows


def _stage_rows(
    stage_root: Path, filter_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    filtered = defaultdict(list)
    for row in filter_rows:
        filtered[str(row["Type"])].append(row)
    animator_filters = filtered.get("Animator", [])
    clip_filters = filtered.get("AnimationClip", [])
    if len(animator_filters) != 7 or len(clip_filters) != 4:
        raise ClosureError(
            f"exact stage filter must contain 7 Animators and 4 AnimationClips, got "
            f"{len(animator_filters)} and {len(clip_filters)}"
        )
    animator_by_path: dict[int, dict[str, Any]] = {}
    for path in sorted((stage_root / "Animator").glob("*.json")):
        value = _json(path)
        # Animator JSON has no $animestudio envelope in this exact stage;
        # its own PathID is the signed value encoded by the p<hex> filename.
        path_id = _path_id_from_filename(path)
        if path_id is None:
            raise ClosureError(f"Animator stage artifact lacks an exact PathID filename: {path}")
        matches = [row for row in animator_filters if int(row["PathID"]) == path_id]
        if len(matches) != 1:
            raise ClosureError(f"Animator stage artifact has no unique filter row: {path}")
        row = matches[0]
        if str(value.get("Name") or "") != str(row["Name"]):
            raise ClosureError(f"Animator name drifted from exact filter: {path}")
        animator_by_path[path_id] = {"path": path, "value": value, "filter": row}
    if len(animator_by_path) != 7:
        raise ClosureError(f"exact stage has {len(animator_by_path)} Animator artifacts, expected 7")
    clip_by_path: dict[int, dict[str, Any]] = {}
    for row in clip_filters:
        path_id = _pint(row["PathID"], field="AnimationClip filter PathID")
        candidates = [
            path
            for path in sorted((stage_root / "AnimationClip").glob("*.json"))
            if _path_id_from_filename(path) == path_id
        ]
        if len(candidates) != 1:
            raise ClosureError(f"AnimationClip stage artifact is not unique: {row['Name']}")
        value = _json(candidates[0])
        if str(value.get("m_Name") or "") != str(row["Name"]):
            raise ClosureError(f"AnimationClip name drifted from exact filter: {candidates[0]}")
        clip_by_path[path_id] = {"path": candidates[0], "value": value, "filter": row}
    if len(clip_by_path) != 4:
        raise ClosureError(f"exact stage has {len(clip_by_path)} AnimationClip artifacts, expected 4")
    return list(animator_by_path.values()), animator_by_path, clip_by_path


def _pptr(value: Any, *, field: str, path: Path) -> tuple[int, int, bool]:
    if not isinstance(value, dict):
        raise ClosureError(f"{field} is not a PPtr in {path}")
    file_id = _int(value.get("m_FileID"), field=f"{field}.m_FileID", path=path)
    path_id = _pint(value.get("m_PathID"), field=f"{field}.m_PathID", path=path)
    return file_id, path_id, file_id == 0 and path_id == 0


def _clip_ids(value: Any) -> list[int]:
    found: list[int] = []
    if isinstance(value, dict):
        if "m_ClipID" in value and isinstance(value["m_ClipID"], (int, float)):
            found.append(int(value["m_ClipID"]))
        for child in value.values():
            found.extend(_clip_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_clip_ids(child))
    return found


def _controller_states(value: dict[str, Any]) -> list[dict[str, Any]]:
    controller = value.get("m_Controller")
    if not isinstance(controller, dict):
        raise ClosureError("AnimatorController artifact lacks m_Controller")
    states: list[dict[str, Any]] = []
    machines = controller.get("m_StateMachineArray") or []
    for machine_index, machine in enumerate(machines):
        data = machine.get("data") if isinstance(machine, dict) else None
        if not isinstance(data, dict):
            raise ClosureError("AnimatorController state-machine entry lacks data")
        for state_index, state in enumerate(data.get("m_StateConstantArray") or []):
            state_data = state.get("data") if isinstance(state, dict) else None
            if not isinstance(state_data, dict):
                raise ClosureError("AnimatorController state entry lacks data")
            ids = _clip_ids(state_data.get("m_BlendTreeConstantArray"))
            states.append(
                {
                    "stateMachineIndex": machine_index,
                    "stateIndex": state_index,
                    "nameId": state_data.get("m_NameID"),
                    "loop": state_data.get("m_Loop"),
                    "clipIds": sorted(set(ids)),
                }
            )
    return states


def _playback_rows(stage_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((stage_root / "MonoBehaviour").glob("*.json")):
        value = _json(path)
        if "startAnimationClip" not in value:
            continue
        meta = value.get("$animestudio") or {}
        source = str(meta.get("sourceOriginalPath") or "")
        source_file = str(meta.get("sourceFile") or "")
        source_offset = _int(meta.get("sourceOffset"), field="$animestudio.sourceOffset", path=path)
        start = _pptr(value["startAnimationClip"], field="startAnimationClip", path=path)
        loop = _pptr(value.get("loopAnimationClip"), field="loopAnimationClip", path=path)
        end = _pptr(value.get("endAnimationClip"), field="endAnimationClip", path=path)
        game_object = value.get("m_GameObject") or {}
        rows.append(
            {
                "artifact": _relative_path(path),
                "sourceCab": source_file,
                "source": source,
                "sourceOffset": source_offset,
                "pathId": _signed_int64(meta.get("pathId"), field="$animestudio.pathId", path=path),
                "gameObjectPathId": _pint(game_object.get("m_PathID"), field="m_GameObject.m_PathID", path=path),
                "start": {"fileId": start[0], "pathId": start[1], "isNull": start[2]},
                "loop": {"fileId": loop[0], "pathId": loop[1], "isNull": loop[2]},
                "end": {"fileId": end[0], "pathId": end[1], "isNull": end[2]},
                "isEnableChangeState": value.get("isEnableChangeState"),
                "evidence": "exact_stage_monobehaviour_json",
            }
        )
    if len(rows) != 3:
        raise ClosureError(f"exact stage must expose 3 EffectAnimation rows, found {len(rows)}")
    return rows


def _bind_playback_owner(
    row: dict[str, Any], cab_rows: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    owner = _cab_at_source(cab_rows, str(row["source"]), int(row["sourceOffset"]))
    verified = owner["cab"] == row["sourceCab"]
    if not verified:
        raise ClosureError(
            f"EffectAnimation owner CAB mismatch for {row.get('artifact')}: "
            f"stage={row.get('sourceCab')!r}, current={owner.get('cab')!r}"
        )
    row["ownerCabVerified"] = True
    row["ownerCabRecord"] = owner
    return row


def _validate_source_stage(stage: dict[str, Any], stage_path: Path) -> tuple[list[Path], dict[Path, dict[str, Any]]]:
    paths = [Path(path) for path in stage.get("object_index_paths") or []]
    if any(not path.is_file() for path in paths):
        raise ClosureError("exact stage object-index source is missing")
    _, _, summaries = _object_index_records(paths, set())
    _assert_index_summaries_match(stage, paths, summaries)
    return paths, summaries


def build_report(
    stage_input: Path,
    *,
    controller_roots: Iterable[Path] = (DEFAULT_CONTROLLER_ROOT,),
    animation_roots: Iterable[Path] = (DEFAULT_ANIMATION_ROOT,),
    asset_maps: Iterable[Path] = (DEFAULT_ASSET_MAP,),
    cab_maps: Iterable[Path] = (DEFAULT_CAB_MAP,),
) -> dict[str, Any]:
    stage, stage_path, stamp_path, stamp = _load_stage(stage_input)
    stage_root = stage_path.parent
    stage_indexes, _ = _validate_source_stage(stage, stage_path)
    filter_path, filter_rows = _stage_filter(stage_path)
    animator_rows, animator_by_path, stage_clips = _stage_rows(stage_root, filter_rows)
    cab_rows = _load_cab_map(cab_maps)
    asset_map_paths = [Path(path) for path in asset_maps]
    for path in asset_map_paths:
        if not path.is_file():
            raise ClosureError(f"AssetMap is missing: {path}")
    controller_paths = [Path(path) for path in controller_roots]
    # A missing broad AnimationClip export is itself an evidence gap.  The
    # exact stage clips remain available through ``stage_artifact`` below;
    # do not fail before recording the missing external actor clip.
    animation_paths = [Path(path) for path in animation_roots if Path(path).is_file() or Path(path).is_dir()]
    controller_artifacts = [
        path for root in controller_paths for path in _iter_json_files(root)
    ]
    if not controller_artifacts:
        raise ClosureError("no AnimatorController JSON artifacts were found")
    controller_targets: dict[int, dict[str, Any]] = {}
    for record in animator_rows:
        value = record["value"]
        filter_row = record["filter"]
        owner = _cab_at_source(cab_rows, str(filter_row["Source"]), int(filter_row["Offset"]))
        file_id, controller_path_id, is_null = _pptr(
            value.get("m_Controller"), field="Animator.m_Controller", path=record["path"]
        )
        if not is_null:
            if file_id < 0:
                raise ClosureError(f"non-null Animator controller PPtr has invalid FileID: {record['path']}")
            controller_targets[int(filter_row["PathID"])] = _resolve_dependency(
                cab_rows, str(owner["cab"]), file_id, controller_path_id
            )
    # Include every clip PathID advertised by the candidate controller files,
    # then perform one targeted textual pass over the large AssetMap.  The
    # later CAB/source/offset/type join still decides whether each row is
    # exact; this pre-scan is only an I/O optimization.
    asset_path_ids = set(stage_clips)
    target_controller_keys = {
        (str(target["cab"]).casefold(), int(target["pathId"]))
        for target in controller_targets.values()
    }
    for artifact_path in controller_artifacts:
        value = _json(artifact_path)
        metadata = value.get("$animestudio")
        if not isinstance(metadata, dict) or metadata.get("type") not in {
            "AnimatorController",
            "AnimatorOverrideController",
        }:
            continue
        try:
            artifact_key = (
                str(metadata.get("sourceFile") or "").casefold(),
                _signed_int64(metadata.get("pathId"), field="$animestudio.pathId", path=artifact_path),
            )
        except ClosureError:
            continue
        if artifact_key not in target_controller_keys:
            continue
        for pointer in value.get("m_AnimationClips") or []:
            if isinstance(pointer, dict) and pointer.get("m_PathID") is not None:
                asset_path_ids.add(_signed_int64(pointer["m_PathID"], field="m_AnimationClips.m_PathID", path=artifact_path))
    clip_map_rows = _target_asset_map_rows(asset_map_paths, asset_path_ids)

    controllers: list[dict[str, Any]] = []
    missing_artifacts: list[dict[str, Any]] = []
    for record in sorted(animator_rows, key=lambda row: (str(row["filter"]["Name"]), int(row["filter"]["PathID"]))):
        path = record["path"]
        value = record["value"]
        filter_row = record["filter"]
        owner = _cab_at_source(cab_rows, str(filter_row["Source"]), int(filter_row["Offset"]))
        owner_cab = str(owner["cab"])
        file_id, controller_path_id, is_null = _pptr(value.get("m_Controller"), field="Animator.m_Controller", path=path)
        item: dict[str, Any] = {
            "animator": {
                "name": str(filter_row["Name"]),
                "pathId": int(filter_row["PathID"]),
                "pathIdHex": f"{_unsigned_path_id(int(filter_row['PathID'])):016X}",
                "artifact": _relative_path(path),
                "gameObjectPathId": int((value.get("m_GameObject") or {}).get("m_PathID")),
                "ownerCab": owner_cab,
                "ownerSource": owner["source"],
                "ownerSourceOffset": owner["sourceOffset"],
                "container": filter_row.get("Container"),
            },
            "controller": None,
        }
        if is_null:
            item["controller"] = {
                "status": "null_serialized_pointer",
                "fileId": file_id,
                "pathId": controller_path_id,
            }
            controllers.append(item)
            continue
        if file_id < 0:
            raise ClosureError(f"non-null Animator controller PPtr has invalid FileID: {path}")
        target = _resolve_dependency(cab_rows, owner_cab, file_id, controller_path_id)
        target_cab = str(target["cab"])
        exact, mismatched = _artifact_candidates(
            controller_paths,
            path_id=controller_path_id,
            cab=target_cab,
            cab_row=target,
            types={"AnimatorController", "AnimatorOverrideController"},
        )
        if len(exact) > 1:
            raise ClosureError(f"AnimatorController target is ambiguous: {target_cab}/{controller_path_id}")
        artifact = exact[0] if exact else None
        if artifact is None:
            missing_artifacts.append(
                {
                    "kind": "AnimatorController",
                    "cab": target_cab,
                    "pathId": controller_path_id,
                    "mismatchedCandidates": mismatched,
                }
            )
            item["controller"] = {
                "status": "artifact_missing",
                "fileId": file_id,
                "pathId": controller_path_id,
                "ownerCab": owner_cab,
                "targetCab": target_cab,
                "dependencyIndex": file_id,
                "targetCabRecord": target,
                "mismatchedCandidates": mismatched,
            }
            controllers.append(item)
            continue
        artifact_path = REPO_ROOT / artifact["path"] if not Path(artifact["path"]).is_absolute() else Path(artifact["path"])
        controller_value = _json(artifact_path)
        clips = controller_value.get("m_AnimationClips")
        if not isinstance(clips, list):
            raise ClosureError(f"AnimatorController lacks m_AnimationClips: {artifact_path}")
        resolved_clips: list[dict[str, Any]] = []
        state_rows = _controller_states(controller_value)
        for clip_index, clip_pointer in enumerate(clips):
            clip_file_id, clip_path_id, clip_null = _pptr(
                clip_pointer, field=f"m_AnimationClips[{clip_index}]", path=artifact_path
            )
            if clip_null:
                raise ClosureError(f"AnimatorController has null animation clip PPtr: {artifact_path}")
            clip_target = _resolve_dependency(cab_rows, target_cab, clip_file_id, clip_path_id)
            map_candidates = [
                row
                for row in clip_map_rows.get(clip_path_id, [])
                if row.get("Type") == "AnimationClip"
                and int(row.get("Offset") or -1) == int(clip_target["sourceOffset"])
                and _source_matches(row.get("Source"), clip_target["source"])
            ]
            if len(map_candidates) != 1:
                raise ClosureError(
                    f"AnimationClip PPtr lacks one exact AssetMap source/offset/PathID row: "
                    f"{clip_target['cab']}/{clip_path_id}"
                )
            map_row = map_candidates[0]
            stage_artifact = _stage_artifact(
                stage_clips,
                path_id=clip_path_id,
                name=str(map_row["Name"]),
                source=str(map_row["Source"]),
                offset=int(map_row["Offset"]),
            )
            exact_clip, mismatched_clip = _artifact_candidates(
                animation_paths,
                path_id=clip_path_id,
                cab=str(clip_target["cab"]),
                cab_row=clip_target,
                types={"AnimationClip"},
            )
            if len(exact_clip) > 1:
                raise ClosureError(f"AnimationClip artifact is ambiguous: {clip_path_id}")
            clip_artifact = exact_clip[0] if exact_clip else stage_artifact
            if clip_artifact is None:
                missing_artifacts.append(
                    {
                        "kind": "AnimationClip",
                        "name": map_row["Name"],
                        "cab": clip_target["cab"],
                        "pathId": clip_path_id,
                        "mismatchedCandidates": mismatched_clip,
                    }
                )
            resolved_clips.append(
                {
                    "index": clip_index,
                    "fileId": clip_file_id,
                    "pathId": clip_path_id,
                    "pathIdHex": f"{_unsigned_path_id(clip_path_id):016X}",
                    "targetCab": clip_target["cab"],
                    "dependencyIndex": clip_target["dependencyIndex"],
                    "targetCabRecord": clip_target,
                    "assetMap": map_row,
                    "artifactStatus": "resolved_exact" if clip_artifact else "artifact_missing",
                    "artifact": clip_artifact,
                    "mismatchedCandidates": mismatched_clip,
                }
            )
        state_refs: list[dict[str, Any]] = []
        for state in state_rows:
            for clip_id in state["clipIds"]:
                pointer = resolved_clips[clip_id] if 0 <= clip_id < len(resolved_clips) else None
                state_refs.append(
                    {
                        **state,
                        "clipId": clip_id,
                        "clip": pointer,
                    }
                )
        item["controller"] = {
            "status": "resolved_exact",
            "fileId": file_id,
            "pathId": controller_path_id,
            "ownerCab": owner_cab,
            "targetCab": target_cab,
            "dependencyIndex": file_id,
            "targetCabRecord": target,
            "artifact": artifact,
            "metadata": {
                "sourceFile": artifact["sourceFile"],
                "sourceOriginalPath": artifact["sourceOriginalPath"],
                "sourceOffset": artifact["sourceOffset"],
                "pathId": artifact["pathId"],
                "type": artifact["type"],
                "name": artifact["name"],
            },
            "animationClipPointers": resolved_clips,
            "states": state_rows,
            "stateClipReferences": state_refs,
        }
        controllers.append(item)

    playback = _playback_rows(stage_root)
    for row in playback:
        _bind_playback_owner(row, cab_rows)
        for key in ("start", "loop", "end"):
            pointer = row[key]
            if pointer["isNull"]:
                pointer["status"] = "null_serialized_pointer"
            else:
                pointer["status"] = "exact_local_pointer" if pointer["fileId"] == 0 else "external_pointer"
    unique_missing: dict[tuple[Any, ...], dict[str, Any]] = {}
    for missing in missing_artifacts:
        key = (missing.get("kind"), missing.get("cab"), missing.get("pathId"))
        unique_missing.setdefault(key, missing)
    missing_artifacts = list(unique_missing.values())
    playback_proof = {
        "startToLoopProven": False,
        "endProven": False,
        "reason": (
            "All exact EffectAnimation loopAnimationClip and endAnimationClip PPtrs are null; "
            "the four exact stage AnimationClip JSON objects do not expose a positive loop-time "
            "field in their serialized TypeTree, and both non-null AnimatorController states have "
            "m_Loop=false. No ui_overview_start->ui_overview_loop playback chain is established."
        ),
        "stageAnimationClipCount": len(stage_clips),
        "stageAnimationClips": [
            {
                "name": row["filter"]["Name"],
                "pathId": int(row["filter"]["PathID"]),
                "source": row["filter"]["Source"],
                "sourceOffset": int(row["filter"]["Offset"]),
                "artifact": _relative_path(row["path"]),
                "loopTimeField": "absent_from_exact_stage_json",
            }
            for row in sorted(stage_clips.values(), key=lambda item: int(item["filter"]["PathID"]))
        ],
        "effectAnimationRows": playback,
    }
    source_inputs = {
        "stage": _relative_path(stage_path),
        "stageStamp": _relative_path(stamp_path),
        "stageFilter": _relative_path(filter_path),
        "stageObjectIndexes": [_relative_path(path) for path in stage_indexes],
        "animatorArtifacts": sorted(_relative_path(row["path"]) for row in animator_rows),
        "animationClipStageArtifacts": sorted(_relative_path(row["path"]) for row in stage_clips.values()),
        "controllerRoots": [_relative_path(path) for path in controller_paths],
        "animationRoots": [_relative_path(path) for path in animation_paths],
        "assetMaps": [_relative_path(path) for path in asset_map_paths],
        "cabMaps": [_relative_path(path) for path in cab_maps],
    }
    snapshots = {
        "stage": _file_snapshot(stage_path),
        "stageStamp": _file_snapshot(stamp_path),
        "stageFilter": _file_snapshot(filter_path),
        "assetMaps": [_file_snapshot(path) for path in asset_map_paths],
        "cabMaps": [_file_snapshot(path) for path in cab_maps],
        "cabSources": _cab_source_snapshots(cab_rows),
        "stageArtifacts": [
            _file_snapshot(row["path"])
            for row in animator_rows
        ]
        + [_file_snapshot(row["path"]) for row in stage_clips.values()],
    }
    status = "complete" if not missing_artifacts else "incomplete_missing_artifacts"
    report = {
        "schema": SCHEMA,
        "status": status,
        "characterId": stage.get("character_id"),
        "actorToken": stage.get("actor_token"),
        "stage": {
            "path": _relative_path(stage_path),
            "stageFingerprint": stage["validation"]["stage_fingerprint"],
            "stampFingerprint": stamp["fingerprint"],
            "entryCount": int(stage.get("entry_count") or 0),
            "rootCount": int(stage.get("expected_root_count") or 0),
            "clipCount": int(stage.get("expected_clip_count") or 0),
            "sourceSnapshotsValidated": True,
        },
        "sourceInputs": source_inputs,
        "sourceSnapshots": snapshots,
        "animators": controllers,
        "missingArtifacts": sorted(missing_artifacts, key=_canonical),
        "playbackProof": playback_proof,
        "summary": {
            "animatorCount": len(controllers),
            "nullControllerCount": sum(row["controller"]["status"] == "null_serialized_pointer" for row in controllers),
            "resolvedControllerCount": sum(row["controller"]["status"] == "resolved_exact" for row in controllers),
            "controllerArtifactMissingCount": sum(row["controller"]["status"] == "artifact_missing" for row in controllers),
            "effectAnimationCount": len(playback),
            "missingArtifactCount": len(missing_artifacts),
            "sourceFingerprint": _digest(
                {
                    "stageFingerprint": stage["validation"]["stage_fingerprint"],
                    "sourceInputs": source_inputs,
                    "animators": controllers,
                    "playbackProof": playback_proof,
                }
            ),
        },
        "evidenceBoundary": (
            "Exact stage fingerprint/source snapshots, exact Animator owner CAB+FileID dependency, "
            "exact AnimatorController source/CAB/offset/PathID metadata, state clip PPtrs, and "
            "AssetMap source/offset/PathID/Type are required. Null controllers, null loop/end PPtrs, "
            "missing artifacts, and unresolved playback are explicit evidence; no start->loop claim "
            "is made from names or clip duration."
        ),
    }
    return report


def _validate_report(report: dict[str, Any]) -> None:
    if report.get("schema") != SCHEMA:
        raise ClosureError(f"unsupported report schema: {report.get('schema')!r}")
    if report.get("status") not in {"complete", "incomplete_missing_artifacts"}:
        raise ClosureError(f"invalid report status: {report.get('status')!r}")
    stage = report.get("stage") or {}
    if not stage.get("stageFingerprint") or stage.get("stageFingerprint") != stage.get("stampFingerprint"):
        raise ClosureError("report stage/stamp fingerprint contract is not exact")
    snapshots = report.get("sourceSnapshots")
    if not isinstance(snapshots, dict) or not isinstance(snapshots.get("cabSources"), list) or not snapshots["cabSources"]:
        raise ClosureError("report lacks current CAB physical-source snapshots")
    for group, values in snapshots.items():
        if isinstance(values, dict):
            _validate_snapshot(values, field=f"sourceSnapshots.{group}")
            continue
        if not isinstance(values, list):
            raise ClosureError(f"report source snapshot group is not an array/object: {group}")
        for index, snapshot in enumerate(values):
            _validate_snapshot(snapshot, field=f"sourceSnapshots.{group}[{index}]")
    animators = report.get("animators")
    if not isinstance(animators, list) or len(animators) != 7:
        raise ClosureError("report must contain exactly 7 Animator rows")
    for row in animators:
        controller = row.get("controller") or {}
        if controller.get("status") not in {"null_serialized_pointer", "resolved_exact", "artifact_missing"}:
            raise ClosureError("report has invalid Animator controller status")
        if controller.get("status") == "resolved_exact":
            metadata = controller.get("metadata") or {}
            if metadata.get("pathId") != controller.get("pathId"):
                raise ClosureError("controller metadata PathID does not match Animator PPtr")
            if metadata.get("sourceFile") != controller.get("targetCab"):
                raise ClosureError("controller metadata CAB does not match dependency target")
            if not isinstance(controller.get("stateClipReferences"), list):
                raise ClosureError("resolved controller lacks state clip references")
    playback = report.get("playbackProof") or {}
    if playback.get("startToLoopProven") is not False:
        raise ClosureError("report must not claim start-to-loop playback")
    if playback.get("endProven") is not False:
        raise ClosureError("report must not claim end playback")
    effect_rows = playback.get("effectAnimationRows")
    if effect_rows is not None:
        if not isinstance(effect_rows, list):
            raise ClosureError("report playback effect rows are not an array")
        for index, row in enumerate(effect_rows):
            if not isinstance(row, dict) or row.get("ownerCabVerified") is not True:
                raise ClosureError(f"report playback owner CAB is not verified: row {index}")
    summary = report.get("summary") or {}
    if int(summary.get("animatorCount") or -1) != 7:
        raise ClosureError("report summary Animator count drifted")
    if (report.get("status") == "complete") != (not report.get("missingArtifacts")):
        raise ClosureError("report status does not match missing artifact evidence")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--controller-root", type=Path, action="append", default=[])
    parser.add_argument("--animation-root", type=Path, action="append", default=[])
    parser.add_argument("--asset-map", type=Path, action="append", default=[])
    parser.add_argument("--cab-map", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_report(
            args.stage,
            controller_roots=args.controller_root or [DEFAULT_CONTROLLER_ROOT],
            animation_roots=args.animation_root or [DEFAULT_ANIMATION_ROOT],
            asset_maps=args.asset_map or [DEFAULT_ASSET_MAP],
            cab_maps=args.cab_map or [DEFAULT_CAB_MAP],
        )
        _validate_report(report)
        if report["status"] != "complete" and not args.allow_incomplete:
            raise ClosureError(
                "Animator/controller closure is incomplete; use --allow-incomplete only to publish explicit gaps"
            )
        if args.check:
            if not args.output.is_file():
                raise ClosureError(f"report does not exist for --check: {args.output}")
            existing = _json(args.output)
            _validate_report(existing)
            if existing != report:
                raise ClosureError(f"report differs from deterministic rebuild: {args.output}")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"{('checked' if args.check else 'wrote')} {args.output}: "
            f"animators={report['summary']['animatorCount']} "
            f"controllers={report['summary']['resolvedControllerCount']} exact/"
            f"{report['summary']['nullControllerCount']} null/"
            f"{report['summary']['controllerArtifactMissingCount']} missing "
            f"artifacts={report['summary']['missingArtifactCount']} status={report['status']}"
        )
        return 0
    except (ClosureError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
