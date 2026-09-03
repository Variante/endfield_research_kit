"""Indexed, fail-closed Terrain `_H` height-grid support for map recovery."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from scripts.terrain_tret import parse_tret_record


HEIGHT_NAME_RE = re.compile(r"^Terrain_(?P<lod>\d+)_(?P<i>\d+)_(?P<j>\d+)_H\.bytes$")
GRID_SAMPLES = 65
GRID_VALUE_COUNT = GRID_SAMPLES * GRID_SAMPLES
GRID_BYTES = GRID_VALUE_COUNT * 2
WORLD_SPAN = 2048.0
KNOWN_SCENE_ORIGINS = {"map01": (-1024.0, -1024.0), "map02": (-1024.0, -1024.0)}
KNOWN_SCENE_FINEST_LODS = {"map01": 5, "map02": 6}


@dataclass(frozen=True)
class HeightTile:
    scene: str
    lod: int
    i: int
    j: int
    path: Path
    sha256: str
    minimum: int
    maximum: int
    payload: bytes

    @property
    def cell_size(self) -> float:
        return WORLD_SPAN / (1 << self.lod)

    def world_bounds(self) -> dict[str, float] | None:
        origin = KNOWN_SCENE_ORIGINS.get(self.scene.lower())
        if origin is None:
            return None
        size = self.cell_size
        return {
            "minX": origin[0] + self.i * size,
            "maxX": origin[0] + (self.i + 1) * size,
            "minZ": origin[1] + self.j * size,
            "maxZ": origin[1] + (self.j + 1) * size,
        }


def load_height_tiles(
    root: Path,
    *,
    scene: str | None = None,
    lod: int | None = None,
    grid_bounds: tuple[int, int, int, int] | None = None,
) -> list[HeightTile]:
    """Decode exact `_H` grids and reject any shape/header disagreement."""
    if not root.is_dir():
        return []
    rows: list[HeightTile] = []
    scene_filter = scene.casefold() if scene else None
    for path in sorted(root.glob("*/Terrain_*_H.bytes")):
        match = HEIGHT_NAME_RE.fullmatch(path.name)
        if match is None:
            continue
        path_scene = path.parent.name
        path_lod = int(match.group("lod"))
        if scene_filter and path_scene.casefold() != scene_filter:
            continue
        if lod is not None and path_lod != lod:
            continue
        path_i = int(match.group("i"))
        path_j = int(match.group("j"))
        if grid_bounds is not None:
            min_i, max_i, min_j, max_j = grid_bounds
            if not (min_i <= path_i < max_i and min_j <= path_j < max_j):
                continue
        raw = path.read_bytes()
        record = parse_tret_record(raw)
        # Offset 14 is a fixed record-format value in the current `_H`
        # corpus, not the quadtree level encoded in the filename.
        expected_prefix = (GRID_SAMPLES, GRID_SAMPLES, 1, 6, GRID_BYTES, 0)
        if record.body_u16le_offsets_8_18 != expected_prefix or len(record.opaque_payload) != GRID_BYTES:
            raise ValueError(
                f"Terrain height shape mismatch for {path}: "
                f"{record.body_u16le_offsets_8_18}, payload={len(record.opaque_payload)}"
            )
        values = struct.unpack("<4225H", record.opaque_payload)
        rows.append(HeightTile(
            scene=path_scene,
            lod=path_lod,
            i=path_i,
            j=path_j,
            path=path,
            sha256=hashlib.sha256(raw).hexdigest(),
            minimum=min(values),
            maximum=max(values),
            payload=record.opaque_payload,
        ))
    return rows


def write_height_index(root: Path, output: Path, *, relative_to: Path) -> dict:
    """Publish the currently consumable finest-grid inventory.

    Other scenes and coarser quadtree levels stay exported for research, but
    decoding them on every WebUI rebuild would add work without a validated
    world origin or a map consumer.
    """
    selected_paths = []
    for scene, lod in sorted(KNOWN_SCENE_FINEST_LODS.items()):
        scene_root = root / scene
        for path in sorted(scene_root.glob(f"Terrain_{lod}_*_*_H.bytes")):
            stat = path.stat()
            selected_paths.append((path.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns))
    signature = hashlib.sha256(
        "\n".join(f"{name}\0{size}\0{mtime}" for name, size, mtime in selected_paths).encode("utf-8")
    ).hexdigest()
    try:
        previous = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        previous = None
    if isinstance(previous, dict) and previous.get("sourceFingerprint") == signature:
        return previous

    tiles = [
        tile
        for scene in sorted(KNOWN_SCENE_ORIGINS)
        for tile in load_height_tiles(root, scene=scene, lod=KNOWN_SCENE_FINEST_LODS[scene])
    ]
    entries = []
    scene_counts: dict[str, int] = {}
    for tile in tiles:
        scene_counts[tile.scene] = scene_counts.get(tile.scene, 0) + 1
        entries.append({
            "scene": tile.scene,
            "lod": tile.lod,
            "i": tile.i,
            "j": tile.j,
            "cellSize": tile.cell_size,
            "worldBounds": tile.world_bounds(),
            "sampleShape": [GRID_SAMPLES, GRID_SAMPLES],
            "encoding": "row_major_uint16le",
            "valueRange": [tile.minimum, tile.maximum],
            "source": tile.path.relative_to(relative_to).as_posix(),
            "sha256": tile.sha256,
        })
    payload = {
        "schemaVersion": 1,
        "status": "complete" if tiles else "unavailable",
        "sourceFingerprint": signature,
        "sourceRoot": root.relative_to(relative_to).as_posix() if root.is_relative_to(relative_to) else str(root),
        "tileCount": len(tiles),
        "sceneCounts": dict(sorted(scene_counts.items())),
        "entries": entries,
        "boundary": (
            "Terrain `_H` files are exact 65x65 row-major uint16 grids. World rectangles are "
            "published only for scene origins already validated by the map coordinate contract; "
            "absolute world-Y scale and no-data sentinel semantics remain unresolved."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return payload


def _png_chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def _write_png(path: Path, width: int, height: int, rows: list[bytearray]) -> None:
    data = b"\x89PNG\r\n\x1a\n"
    data += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    data += _png_chunk(b"IDAT", zlib.compress(b"".join(b"\x00" + bytes(row) for row in rows), 6))
    data += _png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def render_height_layer(
    root: Path,
    scene: str,
    bounds: dict[str, float],
    output: Path,
    *,
    lod: int | None = None,
    long_edge: int = 1024,
    relative_to: Path,
) -> dict | None:
    """Render only Terrain cells intersecting one authored level rectangle."""
    origin = KNOWN_SCENE_ORIGINS.get(scene.casefold())
    if origin is None:
        return None
    lod = KNOWN_SCENE_FINEST_LODS[scene.casefold()] if lod is None else lod
    size = WORLD_SPAN / (1 << lod)
    min_i = math.floor((bounds["minX"] - origin[0]) / size)
    max_i = math.ceil((bounds["maxX"] - origin[0]) / size)
    min_j = math.floor((bounds["minZ"] - origin[1]) / size)
    max_j = math.ceil((bounds["maxZ"] - origin[1]) / size)
    selected = {
        (tile.i, tile.j): tile
        for tile in load_height_tiles(
            root,
            scene=scene,
            lod=lod,
            grid_bounds=(min_i, max_i, min_j, max_j),
        )
    }
    if not selected:
        return None
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    if span_x <= 0 or span_z <= 0:
        return None
    if span_x >= span_z:
        width, height = long_edge, max(1, round(long_edge * span_z / span_x))
    else:
        width, height = max(1, round(long_edge * span_x / span_z)), long_edge
    low = min(tile.minimum for tile in selected.values())
    high = max(tile.maximum for tile in selected.values())
    sources = {f"{i}_{j}": tile.sha256 for (i, j), tile in sorted(selected.items())}
    sidecar = output.with_suffix(".sources.json")
    sidecar_payload = {
        "scene": scene,
        "lod": lod,
        "worldBounds": bounds,
        "imageSize": [width, height],
        "valueRange": [low, high],
        "sources": sources,
    }
    info = {
        "src": f"render/{output.name}",
        "status": "terrain_height_grid_diagnostic",
        "worldBounds": bounds,
        "sceneId": scene,
        "lod": lod,
        "cellSize": size,
        "sampleSpacing": size / 64,
        "tileCount": len(selected),
        "valueRange": [low, high],
        "boundary": (
            "Exact Terrain `_H` samples cropped by the authored UI map rectangle. Values preserve "
            "their uint16 ordering for relative relief only; absolute world Y and no-data sentinel "
            "semantics are not claimed."
        ),
    }
    try:
        previous_sidecar = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        previous_sidecar = None
    if output.is_file() and isinstance(previous_sidecar, dict) and all(
        previous_sidecar.get(key) == value for key, value in sidecar_payload.items()
    ):
        return {**info, "coverageRatio": previous_sidecar.get("coverageRatio", 1.0)}
    unpacked = {key: memoryview(tile.payload).cast("H") for key, tile in selected.items()}
    rows: list[bytearray] = []
    covered = 0
    for py in range(height):
        world_z = bounds["maxZ"] - (py + 0.5) / height * span_z
        tile_j = math.floor((world_z - origin[1]) / size)
        local_z = ((world_z - origin[1]) / size - tile_j) * 64
        sy = max(0, min(64, round(local_z)))
        row = bytearray()
        for px in range(width):
            world_x = bounds["minX"] + (px + 0.5) / width * span_x
            tile_i = math.floor((world_x - origin[0]) / size)
            values = unpacked.get((tile_i, tile_j))
            if values is None:
                row += b"\x00\x00\x00\x00"
                continue
            local_x = ((world_x - origin[0]) / size - tile_i) * 64
            sx = max(0, min(64, round(local_x)))
            value = int(values[sy * GRID_SAMPLES + sx])
            shade = max(0, min(255, round((value - low) * 255 / max(1, high - low))))
            row += bytes((shade, shade, shade, 210))
            covered += 1
        rows.append(row)
    _write_png(output, width, height, rows)
    coverage_ratio = round(covered / (width * height), 6)
    sidecar_payload["coverageRatio"] = coverage_ratio
    sidecar.write_text(json.dumps(sidecar_payload, separators=(",", ":")) + "\n", encoding="utf-8")
    return {**info, "coverageRatio": coverage_ratio}
