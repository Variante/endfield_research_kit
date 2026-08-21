#!/usr/bin/env python3
"""Build the exact Material -> Shader/Texture closure for Endminf UI effects."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from build_endminf_external_pptr_closure import (
    ClosureError,
    _asset_map_rows,
    _cab_map_rows,
    _canonical,
    _normal_source,
    _relative_path,
    _signed_int64,
    _unsigned_path_id,
)

SCHEMA = "endfield.endminf-material-closure.v1"
_PATH_HEX_RE = re.compile(r"(?:^|[^0-9a-z])p(?P<hex>[0-9a-f]{16})$", re.IGNORECASE)
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClosureError(f"cannot read JSON {path}: {exc}") from exc


def _snapshot(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ClosureError(f"cannot snapshot {path}: {exc}") from exc
    return {
        "path": _relative_path(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _source_snapshot(path: Path) -> dict[str, Any]:
    """Record cheap provenance for a source payload without hashing a .chk."""

    try:
        stat = path.stat()
    except OSError as exc:
        raise ClosureError(f"cannot stat source {path}: {exc}") from exc
    if not path.is_file():
        raise ClosureError(f"source is not a regular file: {path}")
    return {
        "path": _relative_path(path),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _integer(value: Any, *, field: str, path: Path | None = None) -> int:
    if isinstance(value, bool):
        where = f" in {path}" if path else ""
        raise ClosureError(f"{field} must be an integer{where}: {value!r}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        where = f" in {path}" if path else ""
        raise ClosureError(f"{field} must be an integer{where}: {value!r}") from exc


def _file_id(value: Any, *, field: str, path: Path) -> int:
    result = _integer(value, field=field, path=path)
    if not 0 <= result <= 0x7FFFFFFF:
        raise ClosureError(f"{field} is outside Unity FileID range in {path}: {value!r}")
    return result


def _candidate_list(value: Any, message: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ClosureError(f"{message}: expected an array")
    if any(not isinstance(item, dict) for item in value):
        raise ClosureError(f"{message}: every candidate must be an object")
    return value


def _target_cab(host_cab: str, dependencies: list[str], file_id: int, *, field: str) -> str:
    """Apply Unity's PPtr FileID rule: zero is the local hosting CAB."""

    if file_id == 0:
        return host_cab
    if file_id > len(dependencies):
        raise ClosureError(f"{field} FileID {file_id} is out of range")
    return dependencies[file_id - 1]


def _validate_owner_cab(
    serialized_file: str,
    source: str,
    source_offset: int,
    dependencies: list[str],
    records_by_cab: dict[str, list[dict[str, Any]]],
    *,
    material_hex: str,
) -> dict[str, Any]:
    """Require one current CABMap physical row and its ordered dependency list."""

    records = records_by_cab.get(serialized_file.casefold(), [])
    if not records:
        raise ClosureError(f"material {material_hex} owner CAB {serialized_file} is missing from current CAB maps")
    physical_pairs = {
        (_normal_source(record.get("source")), _integer(record.get("sourceOffset"), field="CABMap sourceOffset"))
        for record in records
    }
    expected_pair = (_normal_source(source), source_offset)
    if len(physical_pairs) != 1 or expected_pair not in physical_pairs:
        raise ClosureError(
            f"material {material_hex} owner CAB {serialized_file} has no unique current source/offset "
            f"match (expected {source}:{source_offset}, found {len(physical_pairs)} physical sources)"
        )
    matches = [
        record
        for record in records
        if _normal_source(record.get("source")) == expected_pair[0]
        and _integer(record.get("sourceOffset"), field="CABMap sourceOffset") == expected_pair[1]
    ]
    if len(matches) != 1:
        raise ClosureError(
            f"material {material_hex} owner CAB {serialized_file} source/offset is not unique "
            f"in current CAB maps (found {len(matches)} rows)"
        )
    current_dependencies = matches[0].get("dependencies")
    if not isinstance(current_dependencies, list) or current_dependencies != dependencies:
        raise ClosureError(
            f"material {material_hex} owner CAB {serialized_file} dependencies differ from current CAB map "
            "(ordered FileID mapping is not trustworthy)"
        )
    return matches[0]


def _one(items: Iterable[Any], message: str) -> Any:
    values = list(items)
    if len(values) != 1:
        raise ClosureError(f"{message}: expected 1, found {len(values)}")
    return values[0]


def _material_file(root: Path, path_hex: str) -> Path:
    matches = []
    for path in root.rglob(f"*p{path_hex}.json"):
        match = _PATH_HEX_RE.search(path.stem)
        if match and match.group("hex").upper() == path_hex.upper():
            matches.append(path)
    return _one(matches, f"material artifact p{path_hex}")


def _artifact(root: Path, target_type: str, path_hex: str) -> Path:
    suffixes = (".shader",) if target_type == "Shader" else (".png", ".tga", ".jpg", ".jpeg")
    matches = []
    for path in root.rglob(f"*p{path_hex}.*"):
        if path.suffix.casefold() not in suffixes:
            continue
        match = _PATH_HEX_RE.search(path.stem)
        if match and match.group("hex").upper() == path_hex.upper():
            matches.append(path)
    artifact = _one(matches, f"{target_type} artifact p{path_hex}")
    try:
        size = artifact.stat().st_size
        with artifact.open("rb") as handle:
            header = handle.read(16)
    except OSError as exc:
        raise ClosureError(f"cannot validate {target_type} artifact {artifact}: {exc}") from exc
    if size <= 0:
        raise ClosureError(f"{target_type} artifact is empty: {artifact}")
    if target_type == "Texture2D":
        suffix = artifact.suffix.casefold()
        if suffix == ".png" and not header.startswith(_PNG_MAGIC):
            raise ClosureError(f"Texture2D PNG artifact has an invalid header: {artifact}")
        if suffix in {".jpg", ".jpeg"} and not header.startswith(b"\xff\xd8\xff"):
            raise ClosureError(f"Texture2D JPEG artifact has an invalid header: {artifact}")
        if suffix == ".tga" and size < 18:
            raise ClosureError(f"Texture2D TGA artifact is truncated: {artifact}")
    return artifact


def _nonnull_refs(material: dict[str, Any], *, path: Path | None = None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    shader = material.get("m_Shader")
    if shader is not None:
        if not isinstance(shader, dict):
            raise ClosureError(f"Material m_Shader is not an object{f' in {path}' if path else ''}")
        shader_path_id = _signed_int64(shader.get("m_PathID"), field="Material m_Shader PathID", path=path)
        if not shader.get("IsNull"):
            if shader_path_id:
                if "m_FileID" not in shader:
                    raise ClosureError(f"Material m_Shader lacks m_FileID{f' in {path}' if path else ''}")
                refs.append({"property": "m_Shader", "targetType": "Shader", "pptr": shader})
    saved_properties = material.get("m_SavedProperties", {})
    if not isinstance(saved_properties, dict):
        raise ClosureError(f"Material m_SavedProperties is not an object{f' in {path}' if path else ''}")
    tex_envs = saved_properties.get("m_TexEnvs", {})
    if not isinstance(tex_envs, dict):
        raise ClosureError("Material m_SavedProperties.m_TexEnvs is not an object")
    for name, value in sorted(tex_envs.items()):
        if not isinstance(value, dict):
            raise ClosureError(f"Material texture environment {name!r} is not an object")
        texture = value.get("m_Texture")
        if texture is None:
            continue
        if not isinstance(texture, dict):
            raise ClosureError(f"Material texture environment {name!r} m_Texture is not an object")
        texture_path_id = _signed_int64(
            texture.get("m_PathID"),
            field=f"Material m_TexEnvs.{name}.m_Texture PathID",
            path=path,
        )
        if not texture.get("IsNull"):
            if texture_path_id:
                if "m_FileID" not in texture:
                    raise ClosureError(f"Material texture environment {name!r} lacks m_FileID")
                refs.append({"property": f"m_TexEnvs.{name}.m_Texture", "targetType": "Texture2D", "pptr": texture})
    return refs


def build_report(
    closure_path: Path,
    material_root: Path,
    asset_maps: Iterable[Path],
    cab_maps: Iterable[Path],
    shader_root: Path,
    texture_root: Path,
) -> dict[str, Any]:
    closure = _load_json(closure_path)
    if not isinstance(closure, dict):
        raise ClosureError(f"external PPtr closure is not an object: {closure_path}")
    if closure.get("schema") != "endfield.endminf-external-pptr-closure.v1":
        raise ClosureError("unexpected external PPtr closure schema")
    if closure.get("status") not in {"complete", "incomplete_ambiguous"}:
        raise ClosureError(f"external PPtr closure is unusable: {closure.get('status')}")

    identities = closure.get("identities")
    if not isinstance(identities, list) or any(not isinstance(row, dict) for row in identities):
        raise ClosureError("external PPtr closure identities are not an array of objects")
    materials = [row for row in identities if row.get("targetType") == "Material" and row.get("status") == "resolved"]
    if len(materials) != 27:
        raise ClosureError(f"expected 27 resolved Endminf materials, found {len(materials)}")

    occurrences: list[dict[str, Any]] = []
    requested: set[int] = set()
    material_files: list[Path] = []
    owner_sources: set[str] = set()
    owner_specs: list[dict[str, Any]] = []
    for owner in materials:
        owner_path_id = _signed_int64(owner.get("pathId"), field="Material identity PathID", path=closure_path)
        expected_path_hex = f"{_unsigned_path_id(owner_path_id):016X}"
        path_hex = str(owner.get("pathIdHex") or "").upper()
        if path_hex != expected_path_hex:
            raise ClosureError(
                f"material identity PathID hex mismatch: expected {expected_path_hex}, found {path_hex or '<missing>'}"
            )
        serialized_file = str(owner.get("serializedFile") or "")
        if not serialized_file:
            raise ClosureError(f"material {path_hex} lacks serialized-file CAB provenance")
        material_path = _material_file(material_root, path_hex)
        payload = _load_json(material_path)
        if not isinstance(payload, dict):
            raise ClosureError(f"material artifact is not a JSON object: {material_path}")
        cab_candidate = _one(
            _candidate_list(owner.get("cabMapCandidates"), f"material {path_hex} CAB provenance"),
            f"material {path_hex} CAB provenance",
        )
        source_candidate = _one(
            _candidate_list(owner.get("sourceCandidates"), f"material {path_hex} physical source"),
            f"material {path_hex} physical source",
        )
        asset_candidates = _candidate_list(
            owner.get("assetMapCandidates"), f"material {path_hex} AssetMap provenance"
        )
        asset_candidate = _one(asset_candidates, f"material {path_hex} AssetMap provenance")
        cab_source = str(cab_candidate.get("source") or "")
        source_source = str(source_candidate.get("source") or "")
        cab_name = cab_candidate.get("cab")
        if not isinstance(cab_name, str) or not cab_name:
            raise ClosureError(f"material {path_hex} CAB provenance lacks a CAB name")
        cab_offset = _integer(cab_candidate.get("sourceOffset"), field=f"material {path_hex} CAB sourceOffset")
        source_offset = _integer(source_candidate.get("sourceOffset"), field=f"material {path_hex} sourceOffset")
        asset_offset = _integer(asset_candidate.get("Offset"), field=f"material {path_hex} AssetMap Offset")
        if cab_offset < 0 or source_offset < 0 or asset_offset < 0:
            raise ClosureError(f"material {path_hex} provenance has a negative source offset")
        if cab_name.casefold() != serialized_file.casefold():
            raise ClosureError(f"material {path_hex} CAB provenance names the wrong serialized file")
        if (
            not cab_source
            or _normal_source(cab_source) != _normal_source(source_source)
            or cab_offset != source_offset
            or cab_offset != asset_offset
            or _normal_source(cab_source) != _normal_source(asset_candidate.get("Source"))
        ):
            raise ClosureError(f"material {path_hex} CAB/source provenance mismatch")
        if _signed_int64(asset_candidate.get("PathID"), field=f"material {path_hex} AssetMap PathID") != owner_path_id:
            raise ClosureError(f"material {path_hex} AssetMap PathID does not match its owner identity")
        if asset_candidate.get("Type") != "Material":
            raise ClosureError(f"material {path_hex} AssetMap type is not Material")
        dependencies = cab_candidate.get("dependencies")
        if not isinstance(dependencies, list):
            raise ClosureError(f"material {path_hex} CAB dependencies are missing")
        dependencies = []
        for index, dependency in enumerate(cab_candidate.get("dependencies"), 1):
            if not isinstance(dependency, str) or not dependency:
                raise ClosureError(f"material {path_hex} CAB dependency {index} is not a non-empty CAB name")
            dependencies.append(dependency)
        material_name = str(payload.get("m_Name") or payload.get("Name") or "")
        if not material_name:
            raise ClosureError(f"material {path_hex} JSON has no material name")
        if str(payload.get("m_Name") or payload.get("Name") or "") != str(asset_candidate.get("Name") or ""):
            raise ClosureError(f"material {path_hex} JSON name does not match its AssetMap owner")
        material_files.append(material_path)
        owner_sources.add(cab_source)
        owner_specs.append(
            {
                "materialHex": path_hex,
                "serializedFile": serialized_file,
                "source": cab_source,
                "sourceOffset": cab_offset,
                "dependencies": dependencies,
            }
        )
        refs = _nonnull_refs(payload, path=material_path)
        for ref in refs:
            pptr = ref["pptr"]
            file_id = _file_id(pptr.get("m_FileID"), field=f"material {path_hex} {ref['property']} FileID", path=material_path)
            path_id = _signed_int64(pptr.get("m_PathID"), field="Material PPtr PathID", path=material_path)
            requested.add(path_id)
            target_cab = _target_cab(
                serialized_file,
                dependencies,
                file_id,
                field=f"material {path_hex} {ref['property']}",
            )
            occurrences.append({
                "materialPathIdHex": path_hex,
                "materialPathId": owner_path_id,
                "materialPathIdUnsigned": _unsigned_path_id(owner_path_id),
                "materialSerializedFile": serialized_file,
                "materialSource": cab_source,
                "materialSourceOffset": cab_offset,
                "material": material_name,
                "materialArtifact": _relative_path(material_path),
                "property": ref["property"],
                "targetType": ref["targetType"],
                "targetCab": target_cab,
                "fileId": file_id,
                "fileIdRule": "local hosting CAB" if file_id == 0 else f"host dependency[{file_id - 1}]",
                "pathId": path_id,
                "pathIdUnsigned": _unsigned_path_id(path_id),
                "pathIdHex": f"{_unsigned_path_id(path_id):016X}",
            })

    maps = [Path(p) for p in asset_maps]
    rows_by_pid = _asset_map_rows(maps, requested)
    cab_paths = [Path(p) for p in cab_maps]
    target_cabs = {row["targetCab"] for row in occurrences}
    owner_cabs = {spec["serializedFile"] for spec in owner_specs}
    source_pairs_raw, cab_records_raw = _cab_map_rows(cab_paths, target_cabs | owner_cabs)
    source_pairs: dict[str, set[tuple[str, int]]] = defaultdict(set)
    cab_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cab, pairs in source_pairs_raw.items():
        source_pairs[str(cab).casefold()].update(pairs)
    for cab, records in cab_records_raw.items():
        cab_records[str(cab).casefold()].extend(records)
    for spec in owner_specs:
        _validate_owner_cab(
            spec["serializedFile"],
            spec["source"],
            spec["sourceOffset"],
            spec["dependencies"],
            cab_records,
            material_hex=spec["materialHex"],
        )
    identities: dict[tuple[str, int, str], dict[str, Any]] = {}
    for occurrence in occurrences:
        key = (occurrence["targetCab"].casefold(), occurrence["pathId"], occurrence["targetType"])
        candidates = []
        for row in rows_by_pid.get(occurrence["pathId"], []):
            if row.get("Type") != occurrence["targetType"]:
                continue
            # The target CAB must itself be present as a dependency provenance row in
            # at least one resolved owner.  AssetMap source/offset remains the physical target.
            candidates.append(row)
        target_records = sorted(cab_records.get(occurrence["targetCab"].casefold(), []), key=_canonical)
        target_pairs = source_pairs.get(occurrence["targetCab"].casefold(), set())
        if not target_records or not target_pairs:
            raise ClosureError(f"CABMap has no physical target for {occurrence['targetCab']}")
        if any(int(offset) < 0 for _, offset in target_pairs):
            raise ClosureError(f"CABMap has a negative source offset for {occurrence['targetCab']}")
        unique_rows: dict[tuple[str, int], dict[str, Any]] = {}
        for row in candidates:
            row_source = _normal_source(row.get("Source"))
            row_offset = _integer(row.get("Offset"), field="AssetMap.Offset")
            if row_offset < 0:
                raise ClosureError(f"AssetMap has a negative source offset for {occurrence['targetCab']}")
            if any(row_source == _normal_source(source) and row_offset == int(offset) for source, offset in target_pairs):
                unique_rows.setdefault((row_source, row_offset), row)
        if not unique_rows:
            raise ClosureError(
                f"target {occurrence['targetCab']} p{occurrence['pathIdHex']} {occurrence['targetType']} "
                "has no exact CABMap/AssetMap physical target"
            )
        if len(unique_rows) > 1:
            identity = identities.setdefault(key, {
                "serializedFile": occurrence["targetCab"],
                "pathId": occurrence["pathId"],
                "pathIdUnsigned": occurrence["pathIdUnsigned"],
                "pathIdHex": occurrence["pathIdHex"],
                "targetType": occurrence["targetType"],
                "status": "ambiguous_physical_source",
                "assetMapCandidates": sorted(unique_rows.values(), key=_canonical),
                "cabMapCandidates": target_records,
                "occurrences": [],
            })
            identity["occurrences"].append({k: v for k, v in occurrence.items() if k not in {"targetCab", "pathId", "pathIdUnsigned", "pathIdHex", "targetType"}})
            continue
        target = next(iter(unique_rows.values()))
        root = shader_root if occurrence["targetType"] == "Shader" else texture_root
        artifact = _artifact(root, occurrence["targetType"], occurrence["pathIdHex"])
        identity = identities.setdefault(key, {
            "serializedFile": occurrence["targetCab"],
            "pathId": occurrence["pathId"],
            "pathIdUnsigned": occurrence["pathIdUnsigned"],
            "pathIdHex": occurrence["pathIdHex"],
            "targetType": occurrence["targetType"],
            "targetName": str(target.get("Name") or ""),
            "status": "resolved",
            "assetMap": target,
            "cabMapCandidates": target_records,
            "artifact": _snapshot(artifact),
            "occurrences": [],
        })
        identity["occurrences"].append({k: v for k, v in occurrence.items() if k not in {"targetCab", "pathId", "pathIdUnsigned", "pathIdHex", "targetType"}})

    for identity in identities.values():
        identity["occurrences"] = sorted(identity["occurrences"], key=_canonical)
    ordered = sorted(identities.values(), key=lambda row: (row["targetType"], row["serializedFile"], row["pathIdUnsigned"]))
    resolved_counts = Counter(row["targetType"] for row in ordered if row["status"] == "resolved")
    ambiguous_counts = Counter(row["targetType"] for row in ordered if row["status"].startswith("ambiguous"))
    ambiguous_count = sum(ambiguous_counts.values())
    return {
        "schema": SCHEMA,
        "status": "incomplete_ambiguous_physical_sources" if ambiguous_count else "asset_closure_complete_render_pipeline_incomplete",
        "characterId": "endminf",
        "inputs": {
            "externalClosure": _snapshot(closure_path),
            "materialRoot": _relative_path(material_root),
            "materialFiles": sorted((_snapshot(path) for path in material_files), key=_canonical),
            "assetMaps": [_snapshot(p) for p in maps],
            "cabMaps": [_snapshot(p) for p in cab_paths],
            "cabSources": sorted(
                (_source_snapshot(Path(source)) for source in owner_sources | {
                    str(record.get("source") or "")
                    for records in cab_records.values()
                    for record in records
                }),
                key=_canonical,
            ),
            "shaderRoot": _relative_path(shader_root),
            "textureRoot": _relative_path(texture_root),
        },
        "summary": {
            "materialCount": len(materials),
            "occurrenceCount": len(occurrences),
            "identityCount": len(ordered),
            "resolvedCount": sum(resolved_counts.values()),
            "ambiguousCount": ambiguous_count,
            "resolvedShaderCount": resolved_counts["Shader"],
            "resolvedTextureCount": resolved_counts["Texture2D"],
            "ambiguousShaderCount": ambiguous_counts["Shader"],
            "ambiguousTextureCount": ambiguous_counts["Texture2D"],
        },
        "identities": ordered,
        "renderPipelineBoundary": {
            "shaderArtifacts": "Exact AnimeStudio HGRP program blobs; not valid ShaderLab source.",
            "compatibleProjectImplementations": [
                "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldVFXBaseV2SampleStack.shader",
                "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldVFXRefractRecovered.shader",
            ],
            "unimplementedShader": "HGRP/LitEffect",
            "renderReady": False,
        },
    }


def _args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--closure", type=Path, required=True)
    p.add_argument("--material-root", type=Path, required=True)
    p.add_argument("--asset-map", type=Path, action="append", required=True)
    p.add_argument("--cab-map", type=Path, action="append", required=True)
    p.add_argument("--shader-root", type=Path, required=True)
    p.add_argument("--texture-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--check", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _args(argv)
    try:
        report = build_report(args.closure, args.material_root, args.asset_map, args.cab_map, args.shader_root, args.texture_root)
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.check:
            try:
                existing = args.output.read_text(encoding="utf-8") if args.output.is_file() else None
            except (OSError, UnicodeError) as exc:
                raise ClosureError(f"cannot read material closure report for --check: {args.output}: {exc}") from exc
            if existing != text:
                raise ClosureError(f"material closure report is stale: {args.output}")
            print(f"checked {args.output}: {report['summary']}")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"wrote {args.output}: {report['summary']}")
        return 0
    except ClosureError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
