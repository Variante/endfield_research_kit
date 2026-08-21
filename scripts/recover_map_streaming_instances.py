#!/usr/bin/env python3
"""Recover exact transform-bearing entities from one Endfield streaming level.

The maintained input boundary is AnimeStudio.CLI ``stream`` JSONL.  The script
does not read VFS group internals itself and writes a compact, provenance-rich
sidecar for the map preview builder.  InitChunkData is an inverted-LZ4 payload
containing FlatBuffer column groups; only entities with a complete 4x4 matrix
are published.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_map_asset_closure import iter_asset_entries, sha256_file
from scripts.common import resolve_installed_game_data_root

DEFAULT_CLI = ROOT / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
DEFAULT_ASSET_MAP = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json"
DEFAULT_MESH_ROOT = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh"
DEFAULT_OUTPUT_ROOT = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances"
LEVEL_RE = re.compile(r"^[a-z0-9_]+$", re.IGNORECASE)


def decompress_inverted_lz4(source: bytes, expected: int) -> bytes:
    output = bytearray(expected)
    source_pos = output_pos = 0
    while source_pos < len(source) and output_pos < expected:
        token = source[source_pos]
        source_pos += 1
        literal_length = token & 0x33
        match_length = (token & 0xCC) >> 2
        match_length = (match_length & 3) | (match_length >> 2)
        literal_length = (literal_length & 3) | (literal_length >> 2)
        if literal_length == 15:
            while True:
                value = source[source_pos]
                source_pos += 1
                literal_length += value
                if value != 255:
                    break
        if source_pos + literal_length > len(source) or output_pos + literal_length > expected:
            raise ValueError("truncated inverted-LZ4 literal")
        output[output_pos:output_pos + literal_length] = source[source_pos:source_pos + literal_length]
        source_pos += literal_length
        output_pos += literal_length
        if source_pos >= len(source):
            break
        if source_pos + 2 > len(source):
            raise ValueError("truncated inverted-LZ4 match offset")
        offset = (source[source_pos] << 8) | source[source_pos + 1]
        source_pos += 2
        if offset <= 0 or offset > output_pos:
            raise ValueError(f"invalid inverted-LZ4 match offset: {offset}")
        if match_length == 15:
            while True:
                value = source[source_pos]
                source_pos += 1
                match_length += value
                if value != 255:
                    break
        match_length += 4
        match_pos = output_pos - offset
        if output_pos + match_length > expected:
            raise ValueError("inverted-LZ4 match exceeds output")
        for _ in range(match_length):
            output[output_pos] = output[match_pos]
            output_pos += 1
            match_pos += 1
    if source_pos != len(source) or output_pos != expected:
        raise ValueError(
            f"inverted-LZ4 size mismatch: source={source_pos}/{len(source)}, output={output_pos}/{expected}"
        )
    return bytes(output)


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _fields(data: bytes, table: int) -> list[int]:
    vtable = table - _i32(data, table)
    size = _u16(data, vtable)
    return [_u16(data, vtable + 4 + index * 2) for index in range((size - 4) // 2)]


def _field(data: bytes, table: int, index: int) -> int | None:
    fields = _fields(data, table)
    return table + fields[index] if index < len(fields) and fields[index] else None


def _target(data: bytes, address: int) -> int:
    return address + _u32(data, address)


def _vector(data: bytes, table: int, index: int) -> tuple[int, int]:
    address = _field(data, table, index)
    if address is None:
        return 0, 0
    vector = _target(data, address)
    return vector + 4, _u32(data, vector)


def _table_element(data: bytes, vector: int, index: int) -> int:
    return _target(data, vector + index * 4)


def _wrapped_vector(data: bytes, table: int) -> tuple[int, int]:
    return _vector(data, table, 0)


def entity_base(name: str | None) -> str | None:
    if not name:
        return None
    value = name.split("#", 1)[0]
    value = re.sub(r" \(\d+\)", "", value)
    return re.sub(r"_ECSMerged$", "", value, flags=re.IGNORECASE)


def iter_entities(data: bytes):
    root = _u32(data, 0)
    if len(_fields(data, root)) != 8:
        raise ValueError("unexpected InitChunkData root layout")
    ids_vector, id_groups = _vector(data, root, 6)
    data_vector, data_groups = _vector(data, root, 7)
    if id_groups != data_groups:
        raise ValueError("parallel InitChunkData group count mismatch")
    for group_index in range(data_groups):
        ids_data, id_count = _wrapped_vector(data, _table_element(data, ids_vector, group_index))
        group = _table_element(data, data_vector, group_index)
        count_address = _field(data, group, 1)
        if count_address is None or _u32(data, count_address) != id_count:
            raise ValueError(f"InitChunkData group {group_index} count mismatch")
        descriptors_data, descriptor_count = _vector(data, group, 3)
        descriptors = [struct.unpack_from("<HHI", data, descriptors_data + index * 8) for index in range(descriptor_count)]
        if any(reserved for _, _, reserved in descriptors):
            raise ValueError(f"InitChunkData group {group_index} descriptor reserved value")
        wrapper = _field(data, group, 4)
        if wrapper is None:
            raise ValueError(f"InitChunkData group {group_index} missing column blob")
        blob, blob_length = _wrapped_vector(data, _target(data, wrapper))
        columns, cursor = {}, 0
        for type_id, stride, _ in descriptors:
            columns[type_id] = (cursor, stride)
            cursor += id_count * stride
        if cursor != blob_length:
            raise ValueError(f"InitChunkData group {group_index} column size mismatch")
        component_type_ids = [type_id for type_id, _stride, _reserved in descriptors]
        component_strides = {
            str(type_id): stride for type_id, stride, _reserved in descriptors
        }
        matrix_type = 18 if 18 in columns else 27 if 27 in columns else None
        if matrix_type is None:
            continue
        matrix_column, matrix_stride = columns[matrix_type]
        if matrix_stride < 64:
            raise ValueError(f"InitChunkData group {group_index} matrix stride is too short")
        for entity_index in range(id_count):
            matrix_address = blob + matrix_column + entity_index * matrix_stride
            matrix = struct.unpack_from("<16f", data, matrix_address)
            name = None
            if 21 in columns:
                name_column, name_stride = columns[21]
                raw_name = data[blob + name_column + entity_index * name_stride:blob + name_column + (entity_index + 1) * name_stride]
                raw_name = raw_name.split(b"\0", 1)[0]
                name = raw_name.decode("utf-8", errors="replace") if raw_name else None
            yield {
                "entityId": _u32(data, ids_data + entity_index * 4),
                "name": name,
                "entityBase": entity_base(name),
                "matrixType": matrix_type,
                "matrixColumnMajor": [round(value, 7) for value in matrix],
                "position": {"x": matrix[12], "y": matrix[13], "z": matrix[14]},
                "groupIndex": group_index,
                "entityIndex": entity_index,
                "initChunkComponentTypeIds": component_type_ids,
                "initChunkComponentStrides": component_strides,
                "prefabIdentity": {
                    "status": "unavailableInValidatedInitChunkSchema",
                    "reason": "noKnownPrefabSourcePathIdOrHashColumnInValidatedSchema",
                    "evidence": "InitChunkData entity id/name/transform and ECS component columns",
                },
            }


def _mesh_file_index(root: Path) -> dict[int, Path]:
    out = {}
    for path in root.glob("*.obj") if root.is_dir() else ():
        match = re.search(r"_p([0-9A-F]{16})\.obj$", path.name, flags=re.IGNORECASE)
        if match:
            raw = int(match.group(1), 16)
            out[raw if raw < 2 ** 63 else raw - 2 ** 64] = path
    return out


ENTITY_MESH_FAMILY_OVERRIDES = {
    # The sphub prefab has no same-name Mesh row. Its recovered static family
    # contains a low base and the 21 m tower body; both use the prefab's exact
    # InitChunkData transform. This is an asset-family closure, not a recovered
    # serialized prefab-child hierarchy.
    "P_prop_indie_sphub+1_001_04": (
        "S_prop_indie_sphub+1_001_03_lod0",
        "S_prop_indie_sphub+1_001_02_lod0",
    ),
}


def _mesh_candidates(bases: set[str], asset_map: Path, mesh_root: Path) -> dict[str, list[dict]]:
    wanted = {base.casefold(): base for base in bases if base}
    candidates: dict[str, list[dict]] = {base: [] for base in wanted.values()}
    override_names = {
        name.casefold(): base
        for base, names in ENTITY_MESH_FAMILY_OVERRIDES.items()
        if base in bases
        for name in names
    }
    exported = _mesh_file_index(mesh_root)
    for entry in iter_asset_entries(asset_map) if asset_map.is_file() else ():
        if entry.get("Type") != "Mesh":
            continue
        name = str(entry.get("Name") or "")
        folded = name.casefold()
        body = re.sub(r"^[sp]_", "", folded)
        body = re.sub(r"_(?:lod|cardmesh)\d*$", "", body)
        override_base = override_names.get(folded)
        if override_base:
            path_id = int(entry.get("PathID"))
            obj = exported.get(path_id)
            if obj is not None:
                candidates[override_base].append({
                    "name": name,
                    "pathId": path_id,
                    "container": entry.get("Container"),
                    "obj": str(obj.relative_to(ROOT)).replace("\\", "/"),
                    "rank": ENTITY_MESH_FAMILY_OVERRIDES[override_base].index(name),
                    "match": "explicit_static_asset_family_closure",
                })
            continue
        for folded_base, original in wanted.items():
            if original in ENTITY_MESH_FAMILY_OVERRIDES:
                continue
            base_body = re.sub(r"^[sp]_", "", folded_base)
            if body != base_body and not body.startswith(base_body + "_"):
                continue
            path_id = int(entry.get("PathID"))
            obj = exported.get(path_id)
            if obj is None:
                continue
            rank = 0 if "_lod0" in folded else 1 if "_lod1" in folded else 2 if "_lod2" in folded else 3
            candidates[original].append({
                "name": name,
                "pathId": path_id,
                "container": entry.get("Container"),
                "obj": str(obj.relative_to(ROOT)).replace("\\", "/"),
                "rank": rank,
            })
    return {
        base: (sorted(rows, key=lambda row: (row["rank"], row["name"].casefold()))
               if base in ENTITY_MESH_FAMILY_OVERRIDES
               else [min(rows, key=lambda row: (row["rank"], row["name"].casefold()))])
        for base, rows in candidates.items() if rows
    }


def _build_prefab_identity_contract(instances: list[dict]) -> dict:
    """Build the published, row-validated prefab identity contract."""
    def identity(row: Any) -> dict:
        value = row.get("prefabIdentity") if isinstance(row, dict) else None
        return value if isinstance(value, dict) else {}
    statuses = Counter(str(identity(row).get("status") or "missing") for row in instances)
    invalid = sum(
        1 for row in instances
        if identity(row).get("status") == "exact"
        and (
            not isinstance(identity(row).get("source"), str)
            or not identity(row).get("source")
            or isinstance(identity(row).get("pathId"), bool)
            or not isinstance(identity(row).get("pathId"), int)
        )
    )
    exact = statuses.get("exact", 0) - invalid
    return {
        "status": "exact" if exact == len(instances) and instances and not invalid else "unavailable",
        "joinKey": "AssetMap Source+PathID (or build-gated equivalent hash)",
        "requiredFields": ["source", "pathId"],
        "verificationScope": "knownInitChunkDataColumnsObservedByCurrentDecoder",
        "exactInstanceCount": exact,
        "unresolvedInstanceCount": len(instances) - exact,
        "invalidExactIdentityCount": invalid,
        "statusCounts": dict(sorted(statuses.items())),
        "diagnostic": (
            "The current InitChunkData recovery contract exposes no known prefab "
            "Source+PathID/hash field in the observed schema; entity names, positions, "
            "matrices, and Mesh joins are not accepted as prefab identity. A separately "
            "proven StreamingChunkData relation may add evidence and remains a recovery gap."
        ),
        "diagnostics": ([{
            "status": "invalidPrefabIdentityRows",
            "reason": "exactIdentityRequiresNonEmptySourceAndIntegerPathId",
            "count": invalid,
        }] if invalid else []),
    }

def _compact_component_shapes(instances: list[dict]) -> dict[str, dict[str, Any]]:
    """Move repeated InitChunkData shape columns to one group-level table."""
    shapes: dict[str, dict[str, Any]] = {}
    for row in instances:
        if not isinstance(row, dict):
            continue
        shape_id = f"{row.get('sourceFile', '')}#group{row.get('groupIndex')}"
        shapes.setdefault(shape_id, {
            "componentTypeIds": row.pop("initChunkComponentTypeIds", []),
            "componentStrides": row.pop("initChunkComponentStrides", {}),
        })
        row["initChunkComponentShapeId"] = shape_id
    return shapes

def recover(level_id: str, cli: Path, game_root: Path, asset_map: Path, mesh_root: Path) -> dict:
    pattern = rf"^Data/Streaming/PC/{re.escape(level_id)}/Streaming/InitChunkData_.*[.]bytes$"
    command = [str(cli), "stream", "--streaming-assets", str(game_root / "StreamingAssets"),
               "--fallback-assets", str(game_root / "Persistent"), "--block-type", "streaming",
               "--file-regex", pattern]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"AnimeStudio stream failed ({result.returncode}): {result.stderr.strip()}")
    instances, sources, by_id, duplicates = [], [], {}, 0
    for line in result.stdout.splitlines():
        if not line.startswith("{"):
            continue
        row = json.loads(line)
        packed = base64.b64decode(row["dataBase64"])
        expected = struct.unpack_from("<I", packed)[0]
        clear = decompress_inverted_lz4(packed[4:], expected)
        parsed = list(iter_entities(clear))
        kept = 0
        for entity in parsed:
            entity["sourceFile"] = row["fileName"]
            existing = by_id.get(entity["entityId"])
            if existing is not None:
                duplicates += 1
                continue
            by_id[entity["entityId"]] = entity
            instances.append(entity)
            kept += 1
        sources.append({"fileName": row["fileName"], "packedBytes": len(packed), "clearBytes": len(clear),
                        "packedSha256": hashlib.sha256(packed).hexdigest(), "uniqueInstances": kept})
    if not sources:
        raise RuntimeError(f"No InitChunkData files matched {level_id}")
    bases = Counter(row["entityBase"] for row in instances if row.get("entityBase"))
    mesh_candidates = _mesh_candidates(set(bases), asset_map, mesh_root)
    component_shapes = _compact_component_shapes(instances)
    prefab_identity_contract = _build_prefab_identity_contract(instances)
    return {
        "schemaVersion": 2,
        "levelId": level_id,
        "coordinateSystem": "Unity column-major 4x4 matrices; translation at indices 12/13/14",
        "source": {"method": "AnimeStudio.CLI stream / Streaming / InitChunkData", "cli": str(cli.relative_to(ROOT)),
                   "cliSha256": sha256_file(cli), "files": sources},
        "prefabIdentityContract": prefab_identity_contract,
        "initChunkComponentShapes": component_shapes,
        "summary": {"sourceFileCount": len(sources), "instanceCount": len(instances), "duplicateCount": duplicates,
                    "uniqueEntityBaseCount": len(bases), "meshResolvedBaseCount": len(mesh_candidates),
                    "meshResolvedInstanceCount": sum(count for base, count in bases.items() if base in mesh_candidates)},
        "entityBases": [{
            "entityBase": base,
            "instanceCount": count,
            "mesh": (mesh_candidates.get(base) or [None])[0],
            "meshes": mesh_candidates.get(base) or [],
        } for base, count in sorted(bases.items())],
        "instances": sorted(instances, key=lambda row: row["entityId"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", required=True)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--game-root", type=Path, default=None)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--mesh-root", type=Path, default=DEFAULT_MESH_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    if not LEVEL_RE.fullmatch(args.level):
        raise SystemExit(f"Unsafe level id: {args.level!r}")
    game_root = (args.game_root or resolve_installed_game_data_root()).resolve()
    if not args.cli.is_file():
        raise SystemExit(f"AnimeStudio CLI not found: {args.cli}")
    payload = recover(args.level, args.cli.resolve(), game_root, args.asset_map.resolve(), args.mesh_root.resolve())
    args.output_root.mkdir(parents=True, exist_ok=True)
    output = args.output_root / f"{args.level}.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{args.level}: {payload['summary']['instanceCount']} instances, "
          f"{payload['summary']['meshResolvedInstanceCount']} mesh-resolved, "
          f"{payload['summary']['uniqueEntityBaseCount']} bases")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
