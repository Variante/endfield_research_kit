#!/usr/bin/env python3
"""Resolve the external PPtr closure of the validated Endminf UI-effect stage.

Unity's serialized external PPtrs identify a target by the serialized-file CAB
name and PathID.  An AssetMap row has a source path, offset, and PathID but no
CAB name, so the two evidence sets are joined only when an exported JSON
``$animestudio`` record or a complete object index proves the CAB-to-source
identity.  Names, containers, and PathIDs without a CAB/source join are never
used as fallbacks.

The report is deliberately useful when the closure is incomplete: every
identity is classified as resolved, unresolved, or ambiguous, while
``--check`` fails closed unless ``--allow-incomplete`` is supplied.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_OUTPUT = (
    LAB_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
    / "Endminf"
    / "ExternalUiEffects"
    / "endminf_external_pptr_closure.json"
)
TARGET_TYPES = (
    "Material",
    "Mesh",
    "Shader",
    "Texture2D",
    "AnimatorController",
    "MonoScript",
)
SCHEMA = "endfield.endminf-external-pptr-closure.v1"
_SOURCE_RE = re.compile(r"(?:^|/)vfs/(?P<suffix>.+)$", re.IGNORECASE)


class ClosureError(RuntimeError):
    """Raised when a source contract is malformed or not safely joinable."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClosureError(f"cannot read JSON input {path}: {exc}") from exc


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _int(value: Any, *, field: str, path: Path | None = None) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        where = f" in {path}" if path else ""
        raise ClosureError(f"{field} must be an integer{where}: {value!r}") from exc


def _normal_source(value: Any) -> str:
    return str(value or "").replace("\\", "/").casefold().rstrip("/")


def _source_suffix(value: Any) -> str | None:
    normal = _normal_source(value)
    match = _SOURCE_RE.search(normal)
    if match:
        return match.group("suffix")
    return normal or None


def _source_matches(candidate: Any, asset_map_source: Any) -> bool:
    """Match an index's relative VFS source to an AssetMap's full source.

    The suffix after the VFS directory is the stable source identity.  A
    bare/empty path does not establish provenance and therefore never matches.
    """

    left = _source_suffix(candidate)
    right = _source_suffix(asset_map_source)
    return bool(left and right and left == right)


def _target_type(path: str) -> str:
    lower = path.casefold()
    if "m_material" in lower or "m_materials" in lower:
        return "Material"
    if re.search(r"(?:^|[.\[])m_mesh\d*(?:$|[.\[])", lower):
        return "Mesh"
    if "m_script" in lower:
        return "MonoScript"
    if "m_shader" in lower:
        return "Shader"
    if "m_texture" in lower or "texture" in lower:
        return "Texture2D"
    if "controller" in lower:
        return "AnimatorController"
    return "Unknown"


def _unsigned_path_id(path_id: int) -> int:
    return int(path_id) & ((1 << 64) - 1)


def _load_stage(stage_input: Path) -> tuple[dict[str, Any], Path]:
    stage_path = stage_input / "external_ui_effect_stage.json" if stage_input.is_dir() else stage_input
    stage = _json(stage_path)
    if not isinstance(stage, dict) or stage.get("schema_version") != 1:
        raise ClosureError(f"unsupported external UI-effect stage: {stage_path}")
    if stage.get("status") != "ok":
        raise ClosureError(f"external UI-effect stage is not terminal-ok: {stage_path}")
    validation = stage.get("validation") or {}
    if not isinstance(validation, dict) or not validation.get("stage_fingerprint"):
        raise ClosureError(f"external UI-effect stage lacks validation fingerprint: {stage_path}")
    summaries = validation.get("object_index_summaries") or []
    if not summaries or any(
        not isinstance(row, dict)
        or row.get("complete") is not True
        or row.get("errors")
        or int((row.get("counts") or {}).get("errors") or 0) != 0
        for row in summaries
    ):
        raise ClosureError(f"external UI-effect stage has no complete error-free object index: {stage_path}")
    if int(validation.get("root_clip_count") or 0) != int(stage.get("expected_root_count") or 0) + int(
        stage.get("expected_clip_count") or 0
    ):
        raise ClosureError(f"external UI-effect stage root/clip count is not terminal: {stage_path}")
    return stage, stage_path


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.casefold() == ".gz" else Path.open
    try:
        if path.suffix.casefold() == ".gz":
            handle = gzip.open(path, "rt", encoding="utf-8")
        else:
            handle = path.open("r", encoding="utf-8")
        with handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ClosureError(f"invalid JSONL {path}:{number}: {exc}") from exc
                if isinstance(value, dict):
                    yield value
    except OSError as exc:
        raise ClosureError(f"cannot read object index {path}: {exc}") from exc


def _object_index_records(
    paths: Iterable[Path],
    requested: set[tuple[str, int]],
) -> tuple[dict[tuple[str, int], list[dict[str, Any]]], dict[str, set[tuple[str, int]]]]:
    """Load only complete indexes and retain exact targets plus CAB sources."""

    targets: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    cab_sources: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for path in paths:
        complete = False
        for row in _iter_jsonl(path):
            if row.get("recordType") == "summary":
                complete = complete or (
                    row.get("complete") is True
                    and not row.get("errors")
                    and int((row.get("counts") or {}).get("errors") or 0) == 0
                )
                continue
            obj = row.get("object") or {}
            serialized_file = str(obj.get("serializedFile") or "")
            if not serialized_file:
                continue
            source = str(obj.get("source") or "")
            offset = obj.get("sourceOffset")
            if source and offset is not None:
                cab_sources[serialized_file].add((source, _int(offset, field="sourceOffset", path=path)))
            if (serialized_file, int(obj.get("pathId") or 0)) not in requested:
                continue
            record_type = str(row.get("type") or row.get("recordType") or "")
            target_type = "MonoScript" if row.get("recordType") == "monoScript" else record_type
            name = str(row.get("name") or row.get("className") or "")
            targets[(serialized_file, int(obj.get("pathId") or 0))].append(
                {
                    "basis": "complete_object_index",
                    "index": _relative_path(path),
                    "serializedFile": serialized_file,
                    "pathId": int(obj.get("pathId") or 0),
                    "type": target_type,
                    "name": name,
                    "source": source or None,
                    "sourceOffset": int(offset) if offset is not None else None,
                }
            )
        if not complete:
            raise ClosureError(f"object index is not a complete error-free index: {path}")
    return targets, cab_sources


def _iter_json_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if not root.is_dir():
        raise ClosureError(f"exported JSON root does not exist: {root}")
    yield from sorted((path for path in root.rglob("*.json") if path.is_file()), key=lambda p: p.as_posix().casefold())


def _json_metadata_candidates(
    roots: Iterable[Path],
    requested: set[tuple[str, int]],
) -> tuple[dict[tuple[str, int], list[dict[str, Any]]], dict[str, set[tuple[str, int]]]]:
    targets: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    cab_sources: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for root in roots:
        for path in _iter_json_files(root):
            value = _json(path)
            if not isinstance(value, dict):
                continue
            metadata = value.get("$animestudio")
            if not isinstance(metadata, dict):
                continue
            serialized_file = str(metadata.get("sourceFile") or "")
            if not serialized_file or metadata.get("pathId") is None:
                continue
            path_id = _int(metadata.get("pathId"), field="$animestudio.pathId", path=path)
            source = str(metadata.get("sourceOriginalPath") or metadata.get("source") or "")
            offset = metadata.get("sourceOffset")
            if source and offset is not None:
                cab_sources[serialized_file].add((source, _int(offset, field="$animestudio.sourceOffset", path=path)))
            key = (serialized_file, path_id)
            if key not in requested:
                continue
            targets[key].append(
                {
                    "basis": "exported_json_metadata",
                    "path": _relative_path(path),
                    "serializedFile": serialized_file,
                    "pathId": path_id,
                    "type": str(metadata.get("type") or ""),
                    "name": str(metadata.get("name") or value.get("m_Name") or ""),
                    "source": source or None,
                    "sourceOffset": int(offset) if offset is not None else None,
                }
            )
    return targets, cab_sources


def _asset_map_rows(paths: Iterable[Path], path_ids: set[int]) -> dict[int, list[dict[str, Any]]]:
    try:
        from endfield_asset_map_filter import iter_asset_entries
    except ModuleNotFoundError as exc:  # pragma: no cover - direct CLI adds this directory
        raise ClosureError(f"cannot import maintained AssetMap iterator: {exc}") from exc
    rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        try:
            entries = iter_asset_entries(path)
            for row in entries:
                path_id = _int(row.get("PathID"), field="AssetMap.PathID", path=path)
                if path_id in path_ids:
                    rows[path_id].append(
                        {
                            "assetMap": _relative_path(path),
                            "Name": str(row.get("Name") or ""),
                            "Container": str(row.get("Container") or ""),
                            "Source": str(row.get("Source") or ""),
                            "PathID": path_id,
                            "Type": str(row.get("Type") or ""),
                            "Offset": _int(row.get("Offset"), field="AssetMap.Offset", path=path),
                            "Hash": str(row.get("Hash") or ""),
                        }
                    )
        except OSError as exc:
            raise ClosureError(f"cannot read AssetMap {path}: {exc}") from exc
    return rows


def _cab_map_rows(
    paths: Iterable[Path],
    serialized_files: set[str],
) -> tuple[dict[str, set[tuple[str, int]]], dict[str, list[dict[str, Any]]]]:
    """Read the maintained AnimeStudio CAB maps as source provenance.

    A CAB map is the authoritative bridge from a serialized-file CAB name to
    its hosting ``(source, offset)``.  The PathID and target type still come
    from the unresolved PPtr and the AssetMap row, respectively.
    """

    try:
        from character_import.audit_generic_actor_animations import parse_cab_map
    except ModuleNotFoundError as exc:  # pragma: no cover - direct CLI adds this directory
        raise ClosureError(f"cannot import maintained CAB-map parser: {exc}") from exc
    wanted = {value.casefold() for value in serialized_files}
    source_pairs: dict[str, set[tuple[str, int]]] = defaultdict(set)
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        stem = path.stem.casefold()
        if "persistent" in stem:
            asset_root = "Persistent"
        elif "streamingassets" in stem:
            asset_root = "StreamingAssets"
        else:
            raise ClosureError(
                f"cannot infer AssetRoot from CAB map name {path}; use an endfield_*_assets.bin map"
            )
        try:
            cab_records = parse_cab_map(path, asset_root)
        except (OSError, EOFError, ValueError) as exc:
            raise ClosureError(f"cannot read CAB map {path}: {exc}") from exc
        for record in cab_records:
            if record.cab.casefold() not in wanted:
                continue
            source = record.source
            pair = (source, int(record.offset))
            source_pairs[record.cab].add(pair)
            records[record.cab].append(
                {
                    "cabMap": _relative_path(path),
                    "assetRoot": record.asset_root,
                    "cab": record.cab,
                    "baseFolder": record.base_folder,
                    "relativePath": record.relative_path,
                    "source": source,
                    "sourceOffset": int(record.offset),
                    "dependencies": list(record.dependencies),
                }
            )
    return source_pairs, records


def _dedupe_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        key = (
            record.get("serializedFile"),
            int(record.get("pathId") or 0),
            record.get("type"),
            record.get("name"),
            record.get("source"),
            record.get("sourceOffset"),
        )
        unique.setdefault(key, record)
    return sorted(unique.values(), key=lambda row: _canonical(row))


def _dedupe_map_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = (
            _normal_source(row.get("Source")),
            row.get("Offset"),
            row.get("PathID"),
            row.get("Type"),
            row.get("Name"),
            row.get("Container"),
        )
        unique.setdefault(key, row)
    return sorted(unique.values(), key=lambda row: _canonical(row))


def _occurrence(row: dict[str, Any], pptr: dict[str, Any], target_type: str) -> dict[str, Any]:
    obj = row.get("object") or {}
    return {
        "ownerType": str(row.get("type") or ""),
        "ownerName": str(row.get("name") or ""),
        "ownerSerializedFile": str(obj.get("serializedFile") or ""),
        "ownerPathId": int(obj.get("pathId") or 0),
        "path": str(pptr.get("path") or ""),
        "fileId": int(pptr.get("fileId") or 0),
        "targetType": target_type,
    }


def _load_unresolved(stage_object_indexes: Iterable[Path]) -> dict[tuple[str, int, str], list[dict[str, Any]]]:
    result: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for path in stage_object_indexes:
        for row in _iter_jsonl(path):
            if row.get("recordType") != "object":
                continue
            for pptr in row.get("pptrs") or []:
                if pptr.get("status") != "external_target_unavailable":
                    continue
                expected = pptr.get("expected") or {}
                serialized_file = str(expected.get("serializedFile") or "")
                if not serialized_file or pptr.get("pathId") is None:
                    raise ClosureError(f"malformed unresolved PPtr in {path}: {pptr}")
                target_type = _target_type(str(pptr.get("path") or ""))
                if target_type not in TARGET_TYPES:
                    raise ClosureError(
                        f"unsupported unresolved PPtr target type {target_type!r} in {path}: {pptr.get('path')!r}"
                    )
                key = (serialized_file, _int(pptr.get("pathId"), field="PPtr.pathId", path=path), target_type)
                result[key].append(_occurrence(row, pptr, target_type))
    return result


def _candidate_identity(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("serializedFile"),
        int(record.get("pathId") or 0),
        str(record.get("type") or ""),
        str(record.get("name") or ""),
    )


def _resolve_identity(
    key: tuple[str, int, str],
    occurrences: list[dict[str, Any]],
    index_records: dict[tuple[str, int], list[dict[str, Any]]],
    json_records: dict[tuple[str, int], list[dict[str, Any]]],
    cab_sources: dict[str, set[tuple[str, int]]],
    cab_map_records: dict[str, list[dict[str, Any]]],
    map_rows: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    serialized_file, path_id, target_type = key
    exact_records = _dedupe_records(
        [*index_records.get((serialized_file, path_id), []), *json_records.get((serialized_file, path_id), [])]
    )
    target_records = [row for row in exact_records if not row.get("type") or row.get("type") == target_type]
    conflicting_types = [row for row in exact_records if row.get("type") and row.get("type") != target_type]
    source_pairs = sorted(cab_sources.get(serialized_file) or [])
    exact_map_rows: list[dict[str, Any]] = []
    for row in map_rows.get(path_id) or []:
        if row.get("Type") != target_type:
            continue
        if any(
            int(row.get("Offset") or 0) == int(offset)
            and _source_matches(source, row.get("Source"))
            for source, offset in source_pairs
        ):
            exact_map_rows.append(row)
    exact_map_rows = _dedupe_map_rows(exact_map_rows)
    unique_target_records = {
        _candidate_identity(row): row
        for row in target_records
        if row.get("type") or row.get("basis") == "exported_json_metadata"
    }
    if conflicting_types or len(unique_target_records) > 1 or len(exact_map_rows) > 1:
        status = "ambiguous"
    elif exact_map_rows:
        status = "resolved"
    elif len(unique_target_records) == 1:
        status = "resolved"
    else:
        status = "unresolved"
    bases = sorted(
        {
            str(row.get("basis"))
            for row in target_records
            if row.get("basis")
        }
        | ({"asset_map_exact_source_offset_pathid"} if exact_map_rows else set())
        | ({"cab_map_source_offset_to_cab"} if cab_map_records.get(serialized_file) else set())
    )
    source = None
    if len(exact_map_rows) == 1:
        source = exact_map_rows[0]
    elif len(unique_target_records) == 1:
        source = next(iter(unique_target_records.values()))
    return {
        "serializedFile": serialized_file,
        "pathId": path_id,
        "pathIdUnsigned": _unsigned_path_id(path_id),
        "pathIdHex": f"{_unsigned_path_id(path_id):016X}",
        "targetType": target_type,
        "occurrenceCount": len(occurrences),
        "occurrences": sorted(occurrences, key=lambda row: _canonical(row)),
        "status": status,
        "resolutionBasis": bases,
        "sourceCandidates": [
            {"source": source_value, "sourceOffset": offset} for source_value, offset in source_pairs
        ],
        "cabMapCandidates": sorted(
            cab_map_records.get(serialized_file) or [], key=lambda row: _canonical(row)
        ),
        "candidateRecords": sorted(exact_records, key=lambda row: _canonical(row)),
        "assetMapCandidates": exact_map_rows,
        "extraction": source if status == "resolved" else None,
    }


def build_report(
    stage_input: Path,
    *,
    object_indexes: Iterable[Path] = (),
    json_roots: Iterable[Path] = (),
    asset_maps: Iterable[Path] = (),
    cab_maps: Iterable[Path] = (),
) -> dict[str, Any]:
    stage, stage_path = _load_stage(stage_input)
    stage_indexes = [Path(path) for path in stage.get("object_index_paths") or []]
    if not stage_indexes:
        raise ClosureError(f"external UI-effect stage has no object-index paths: {stage_path}")
    stage_indexes = [path if path.is_absolute() else stage_path.parent / path for path in stage_indexes]
    missing = [path for path in stage_indexes if not path.is_file()]
    if missing:
        raise ClosureError(f"external UI-effect stage object index is missing: {missing[0]}")
    unresolved = _load_unresolved(stage_indexes)
    requested = {(sf, pid) for sf, pid, _ in unresolved}
    index_paths = [Path(path) for path in object_indexes]
    index_records, index_sources = _object_index_records(index_paths, requested) if index_paths else ({}, {})
    json_paths = [Path(path) for path in json_roots]
    json_records, json_sources = _json_metadata_candidates(json_paths, requested) if json_paths else ({}, {})
    source_proof: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for source_map in (index_sources, json_sources):
        for serialized_file, pairs in source_map.items():
            source_proof[serialized_file].update(pairs)
    cab_map_paths = [Path(path) for path in cab_maps]
    cab_sources, cab_map_records = (
        _cab_map_rows(cab_map_paths, {sf for sf, _ in requested})
        if cab_map_paths
        else ({}, {})
    )
    for serialized_file, pairs in cab_sources.items():
        source_proof[serialized_file].update(pairs)
    maps = [Path(path) for path in asset_maps]
    map_rows = _asset_map_rows(maps, {pid for _, pid in requested}) if maps else {}
    identities = [
        _resolve_identity(
            key,
            occurrences,
            index_records,
            json_records,
            source_proof,
            cab_map_records,
            map_rows,
        )
        for key, occurrences in sorted(unresolved.items(), key=lambda item: item[0])
    ]
    summary_by_type: dict[str, dict[str, int]] = {
        target_type: {status: 0 for status in ("resolved", "unresolved", "ambiguous")}
        for target_type in TARGET_TYPES
    }
    for identity in identities:
        summary_by_type[identity["targetType"]][identity["status"]] += 1
    resolved = sum(row["status"] == "resolved" for row in identities)
    unresolved_count = sum(row["status"] == "unresolved" for row in identities)
    ambiguous = sum(row["status"] == "ambiguous" for row in identities)
    extraction_entries = {
        target_type: [
            {
                "serializedFile": row["serializedFile"],
                "pathId": row["pathId"],
                "pathIdUnsigned": row["pathIdUnsigned"],
                "pathIdHex": row["pathIdHex"],
                "status": row["status"],
                "source": row["extraction"],
            }
            for row in identities
            if row["targetType"] == target_type
        ]
        for target_type in TARGET_TYPES
    }
    source_inputs = {
        "stage": _relative_path(stage_path),
        "stageObjectIndexes": [_relative_path(path) for path in stage_indexes],
        "completeObjectIndexes": [_relative_path(path) for path in index_paths],
        "exportedJsonRoots": [_relative_path(path) for path in json_paths],
        "assetMaps": [_relative_path(path) for path in maps],
        "cabMaps": [_relative_path(path) for path in cab_map_paths],
    }
    source_fingerprint = _digest(
        {
            "stageFingerprint": stage["validation"]["stage_fingerprint"],
            "sourceInputs": source_inputs,
            "identities": identities,
        }
    )
    status = "complete" if unresolved_count == 0 and ambiguous == 0 else "incomplete_unresolved_dependencies"
    return {
        "schema": SCHEMA,
        "status": status,
        "characterId": stage.get("character_id"),
        "actorToken": stage.get("actor_token"),
        "stage": {
            "path": _relative_path(stage_path),
            "stageFingerprint": stage["validation"]["stage_fingerprint"],
            "entryCount": int(stage.get("entry_count") or 0),
            "containerCount": int(stage.get("container_count") or 0),
            "expectedRootCount": int(stage.get("expected_root_count") or 0),
            "expectedClipCount": int(stage.get("expected_clip_count") or 0),
        },
        "sourceInputs": source_inputs,
        "summary": {
            "identityCount": len(identities),
            "occurrenceCount": sum(int(row["occurrenceCount"]) for row in identities),
            "resolvedCount": resolved,
            "unresolvedCount": unresolved_count,
            "ambiguousCount": ambiguous,
            "byTargetType": summary_by_type,
            "sourceFingerprint": source_fingerprint,
        },
        "identities": identities,
        "extractionEntries": extraction_entries,
        "evidenceBoundary": (
            "Only exact serializedFile+CAB PathID identities are joined. AssetMap extraction rows additionally "
            "require a proven source path+offset+PathID+Type match. Names, containers, PathIDs alone, playback, "
            "mounting, and renderability are not resolution evidence."
        ),
    }


def _validate_report(report: dict[str, Any]) -> None:
    if report.get("schema") != SCHEMA:
        raise ClosureError(f"unsupported closure report schema: {report.get('schema')!r}")
    identities = report.get("identities")
    if not isinstance(identities, list):
        raise ClosureError("closure report identities must be a list")
    expected = {target_type: [] for target_type in TARGET_TYPES}
    for row in identities:
        target_type = row.get("targetType")
        if target_type not in expected:
            raise ClosureError(f"closure report has unsupported target type: {target_type!r}")
        if row.get("status") not in {"resolved", "unresolved", "ambiguous"}:
            raise ClosureError(f"closure report has invalid identity status: {row.get('status')!r}")
        if not isinstance(row.get("serializedFile"), str) or not row["serializedFile"].startswith("CAB-"):
            raise ClosureError("closure report identity lacks an exact CAB serializedFile")
        path_id = int(row.get("pathId"))
        if int(row.get("pathIdUnsigned")) != _unsigned_path_id(path_id):
            raise ClosureError("closure report signed/unsigned PathID pair is inconsistent")
        if str(row.get("pathIdHex")) != f"{_unsigned_path_id(path_id):016X}":
            raise ClosureError("closure report PathID hex encoding is inconsistent")
        expected[target_type].append(row)
    extraction = report.get("extractionEntries")
    if not isinstance(extraction, dict) or set(extraction) != set(TARGET_TYPES):
        raise ClosureError("closure report extractionEntries must cover the reviewed target types")
    for target_type, rows in expected.items():
        actual = extraction[target_type]
        if not isinstance(actual, list) or len(actual) != len(rows):
            raise ClosureError(f"closure report extractionEntries count drifted for {target_type}")
    summary = report.get("summary") or {}
    if int(summary.get("identityCount") or -1) != len(identities):
        raise ClosureError("closure report identity count is inconsistent")
    if int(summary.get("resolvedCount") or 0) + int(summary.get("unresolvedCount") or 0) + int(
        summary.get("ambiguousCount") or 0
    ) != len(identities):
        raise ClosureError("closure report status counts are inconsistent")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True, help="validated external_ui_effect_stage.json or its directory")
    parser.add_argument("--object-index", type=Path, action="append", default=[], help="additional complete JSONL(.gz) index")
    parser.add_argument("--json-root", type=Path, action="append", default=[], help="exported JSON file or directory with $animestudio metadata")
    parser.add_argument("--asset-map", type=Path, action="append", default=[], help="exact Endfield AssetMap JSON")
    parser.add_argument("--cab-map", type=Path, action="append", default=[], help="AnimeStudio endfield_*_assets.bin CAB/source map")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="rebuild and compare an existing report; never writes")
    parser.add_argument("--allow-incomplete", action="store_true", help="write/check an explicitly incomplete report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_report(
            args.stage,
            object_indexes=args.object_index,
            json_roots=args.json_root,
            asset_maps=args.asset_map,
            cab_maps=args.cab_map,
        )
        _validate_report(report)
        if report["status"] != "complete" and not args.allow_incomplete:
            raise ClosureError(
                "external PPtr closure is incomplete; rerun with --allow-incomplete only to publish explicit gaps"
            )
        if args.check:
            if not args.output.is_file():
                raise ClosureError(f"closure report does not exist for --check: {args.output}")
            existing = _json(args.output)
            _validate_report(existing)
            if existing != report:
                raise ClosureError(f"closure report differs from deterministic rebuild: {args.output}")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"{('checked' if args.check else 'wrote')} {args.output}: "
            f"identities={report['summary']['identityCount']} occurrences={report['summary']['occurrenceCount']} "
            f"resolved={report['summary']['resolvedCount']} unresolved={report['summary']['unresolvedCount']} "
            f"ambiguous={report['summary']['ambiguousCount']} status={report['status']}"
        )
        return 0
    except ClosureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
