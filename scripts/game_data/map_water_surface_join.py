"""Join one reviewed LevelData water volume to its stored Mesh resource path.

The polygon is authored X/Y/Z evidence. The native initial-plane calculation
is conditional; this source gate does not evaluate runtime observations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mmap
import struct
from pathlib import Path
from typing import Any

from scripts.common import EXPORT_LAYOUT, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.extend_data_binary import parse_string_path_hash
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.leveldata_binary import frame_leveldata_named_prefix
from scripts.game_data.map_water_getmesh_native import validate_map_water_getmesh_native_contract


CONTRACT = CONTRACTS_DIR / "map_water_surface_join.json"
SCHEMA = "endfield.map-water-surface-join.v2"
LABEL = "map_water_surface_join"


def _source_path(export_root: Path, relative: str) -> Path:
    path = (export_root / relative).resolve()
    if not path.is_relative_to(export_root.resolve()) or not path.is_file():
        raise ValueError(f"{LABEL}:missing-or-outside-export:{relative}")
    return path


def _checked_bytes(export_root: Path, row: dict[str, Any]) -> bytes:
    path = _source_path(export_root, row["relativePath"])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
        raise ValueError(f"{LABEL}:source-sha256:{row['relativePath']}")
    return raw


def _catalog_path(raw: bytes, value: int) -> str:
    parsed = parse_string_path_hash(raw, source="map-water StringPathHash")
    if parsed.consumed_bytes != len(raw):
        raise ValueError(f"{LABEL}:catalog-not-exact-eof")
    slot = value % parsed.count
    offset, count = struct.unpack_from("<II", raw, 8 + slot * 8)
    paths: list[str] = []
    for index in range(count):
        _word, found, path_offset = struct.unpack_from("<IQI", raw, offset + index * 16)
        if found != value:
            continue
        start = parsed.str_data_offset + path_offset
        byte_length = struct.unpack_from("<I", raw, start)[0]
        paths.append(raw[start + 4:start + 4 + byte_length].decode("utf-16-le", "strict"))
    if len(paths) != 1:
        raise ValueError(f"{LABEL}:catalog-hash-match-count:{len(paths)}")
    return paths[0]


def _selected_asset_map_row(path: Path, container: str) -> dict[str, Any]:
    """Read only rows carrying one exact container from a large AssetMap."""
    needle = ('"Container": ' + json.dumps(container, ensure_ascii=False)).encode("utf-8")
    rows: list[dict[str, Any]] = []
    with path.open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as view:
        cursor = 0
        while (at := view.find(needle, cursor)) >= 0:
            start = view.rfind(b"\n    {", 0, at)
            end = view.find(b"\n    }", at)
            if start < 0 or end < 0:
                raise ValueError(f"{LABEL}:asset-map-row-boundary")
            row = json.loads(view[start + 5:end + 6])
            if str(row.get("Container", "")).casefold() == container.casefold():
                rows.append(row)
            cursor = at + len(needle)
    if len(rows) != 1:
        raise ValueError(f"{LABEL}:asset-map-container-match-count:{len(rows)}")
    return rows[0]


def _check_local_plane(obj: bytes, points: list[list[float]], pivot: list[float]) -> None:
    vertices: list[list[float]] = []
    faces = 0
    for line in obj.decode("utf-8").splitlines():
        if line.startswith("v "):
            vertices.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            faces += 1
    if len(vertices) != 4 or faces != 2 or len(points) != 4:
        raise ValueError(f"{LABEL}:local-plane-shape")
    if any(len(point) != 3 or not all(math.isfinite(value) for value in point) for point in points):
        raise ValueError(f"{LABEL}:nonfinite-world-point")
    if len(pivot) != 3 or not all(math.isfinite(value) for value in pivot):
        raise ValueError(f"{LABEL}:nonfinite-pivot")
    unmatched = list(vertices)
    for point in points:
        local = [point[axis] - pivot[axis] for axis in range(3)]
        match = next((vertex for vertex in unmatched if max(abs(a - b) for a, b in zip(local, vertex)) < 0.001), None)
        if match is None:
            raise ValueError(f"{LABEL}:world-points-do-not-match-mesh")
        unmatched.remove(match)
    if unmatched:
        raise ValueError(f"{LABEL}:unmatched-mesh-vertices")


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _conditional_initial_plane(row: dict[str, Any], expected: dict[str, Any]) -> dict[str, float]:
    for field, value in expected.items():
        if type(row.get(field)) is not type(value) or row[field] != value:
            raise ValueError(f"{LABEL}:initial-height-source:{field}")
    if row["isPrototype"] or not row["isInfinite"] or int(row["id"]) == 0:
        raise ValueError(f"{LABEL}:initial-height-branch")
    current, maximum = row["amountCurrent"], row["amountMax"]
    if maximum <= 0 or current < 0 or not math.isfinite(row["heightMax"]):
        raise ValueError(f"{LABEL}:initial-height-input")
    ratio = _f32(_f32(float(current)) / _f32(float(maximum)))
    height = _f32(ratio * _f32(float(row["heightMax"])))
    plane_y = _f32(_f32(float(row["pivot"][1])) + height)
    if not all(math.isfinite(value) for value in (ratio, height, plane_y)):
        raise ValueError(f"{LABEL}:initial-height-nonfinite")
    return {"initialRatio": ratio, "heightAbovePivot": height, "requestedPlaneY": plane_y}


def validate_map_water_surface_join(
    export_root: Path = EXPORT_LAYOUT.root,
    contract_path: Path = CONTRACT,
) -> dict[str, Any]:
    """Return one selected authored footprint, or a diagnostic with no row."""
    report: dict[str, Any] = {"schema": "endfield.map-water-surface-join-validation.v2", "status": "unresolved"}
    try:
        contract, digest = read_reviewed_contract(contract_path, schema=SCHEMA, label=LABEL, status="validated")
        report["contractSha256"] = digest
        native = validate_map_water_getmesh_native_contract()
        report["nativeStatus"] = native["status"]
        if native["status"] != "validated":
            report.update(status=native["status"], diagnostic=native.get("diagnostic") or native.get("nativeGate", {}).get("detail"))
            return report

        source = contract["selectedSource"]
        decoded = _checked_bytes(export_root, source)
        framed = frame_leveldata_named_prefix(decoded)
        if framed["schemaStatus"] != "named_exact" or framed["bytesConsumed"] != len(decoded):
            raise ValueError(f"{LABEL}:leveldata-not-named-exact")
        fields = framed["fields"]
        if fields["sceneId"]["value"] != source["levelId"] or fields["levelIdNum"]["value"] != source["levelIdNum"]:
            raise ValueError(f"{LABEL}:scene-identity")
        rows = [row for row in fields["waterVolumes"]["rows"] if row["id"] == source["waterVolumeId"]]
        if len(rows) != 1 or rows[0]["memberCount"] != 26:
            raise ValueError(f"{LABEL}:water-volume-match-count:{len(rows)}")
        row = rows[0]
        report["conditionalInitialPlane"] = _conditional_initial_plane(row, source["initialHeightInputs"])
        mesh = contract["mesh"]
        if row["meshPathHash"] != mesh["meshPathHash"]:
            raise ValueError(f"{LABEL}:mesh-path-hash")
        resource = _catalog_path(_checked_bytes(export_root, contract["catalog"]), row["meshPathHash"])
        if resource != mesh["resourcePath"]:
            raise ValueError(f"{LABEL}:catalog-resource-path:{resource}")
        asset_spec = contract["assetMap"]
        asset_map = _source_path(export_root, asset_spec["relativePath"])
        if sha256_file(asset_map).upper() != asset_spec["sha256"].upper():
            raise ValueError(f"{LABEL}:asset-map-sha256")
        asset = _selected_asset_map_row(asset_map, resource.casefold())
        if (asset.get("Type") != "Mesh" or asset.get("Name") != mesh["name"]
                or int(asset.get("PathID")) != mesh["pathId"]):
            raise ValueError(f"{LABEL}:asset-map-mesh-identity")
        obj = _checked_bytes(export_root, {"relativePath": mesh["objRelativePath"], "sha256": mesh["objSha256"]})
        points = row["points"]["value"]
        if row["points"]["count"] != 4 or not isinstance(points, list):
            raise ValueError(f"{LABEL}:water-points")
        _check_local_plane(obj, points, row["pivot"])
        report.update(
            status="validated",
            waterSurface={
                "sceneId": source["levelId"],
                "waterVolumeId": row["id"],
                "worldPoints": points,
                "pivot": row["pivot"],
                "meshPathHash": str(row["meshPathHash"]),
                "meshAssetPath": resource,
                "meshPathId": str(mesh["pathId"]),
                "source": source["relativePath"],
                "evidence": "exact_authored_leveldata_mesh_join",
                "boundary": "Authored LevelData water footprint joined by hash to an exact Mesh asset. The validated unpatched native branch would pass this row's initial plane position and hash to GetMesh; runtime observations are evaluated by the separate selected live capture gate.",
            },
        )
    except (KeyError, TypeError, ValueError, IndexError, OSError) as exc:
        report.update(status="unresolved", diagnostic=str(exc))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=EXPORT_LAYOUT.root)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    args = parser.parse_args()
    report = validate_map_water_surface_join(args.export_root, args.contract)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
