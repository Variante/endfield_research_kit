#!/usr/bin/env python3
"""Build inferred HLOD top-down previews for every recovered map.

The HLOD bundles publish `Mesh`, `Material` and `Texture2D` only - no
`GameObject` or `Transform` record survives the export - so a cluster's world
placement cannot be read out and has to be inferred from its name. A cluster is
named `S_HLOD<lod>_<i>_<j>_Cluster_<hash>`, and its vertices are stored centred
on the cluster's own origin, so the only unknowns are the grid cell size and the
grid origin.

Both are recovered rather than assumed:

  * current-build `DynamicSceneUtil.GetGridSizeByLen` uses 32 m as the base
    grid length and doubles it per encoded level. The exported HLOD indices
    halve between adjacent levels, so `HLOD0` is 32 m and `HLOD1` is 64 m.
  * the origin is fitted per level by asking which origin makes the level's own
    exact marker transforms land on cells that actually carry geometry, at every
    LOD at once. The fit is corroborated across levels: one shared, power-of-two
    aligned origin explains every `map01_*`/`indie_*` level and another explains
    every `map02_*` level, which a per-level curve fit would not produce.

The result is still an inferred diagnostic backdrop, not an exact scene
transform, and every manifest publishes the fit that produced it - coverage,
sample size and how many origins tied - so a weak background is visible as weak.
A level whose fit is under-determined publishes no background at all.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import struct
import sys
import zlib
from array import array
from pathlib import Path

try:  # Optional: only the PNG unfilter loop below is accelerated by it.
    from PIL import Image as _PILImage
except ImportError:  # pragma: no cover - exercised by the stdlib fallback path
    _PILImage = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_map_asset_closure import iter_asset_entries, sha256_file
from scripts.map_recovery_sources import isolated_art_source, projection_streaming_scene

DEFAULT_ASSET_MAP = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json"
MESH_ROOT = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh"
TEXTURE_ROOT = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D"
MAPS_ROOT = ROOT / "webui/data/map_recovery/maps"
OUTPUT_ROOT = ROOT / "webui/data/map_recovery/render"
HLOD_INDEX = ROOT / "reports/assets/map_recovery/hlod_grid_index.json"
ASSET_INDEX = ROOT / "webui/data/assets/index.json"

CLUSTER_RE = re.compile(r"^S_HLOD(\d+)_(-?\d+)_(-?\d+)_Cluster_")
# `.../<levelId>_art/hlod_v2/pc/hlod<n>/mesh` - the container names the level
# directly, so no per-level needle scan of the 750 MB asset map is needed.
LEVEL_RE = re.compile(r"/([a-z0-9_]+)_art/hlod_v2/", re.IGNORECASE)
REGION_LEVEL_RE = re.compile(r"^(map0[12])_lv\d+$", re.IGNORECASE)
OVERHEAD_COVER_RE = re.compile(r"(?:roof|ceiling)", re.IGNORECASE)
DETAIL_STRUCTURAL_RE = re.compile(r"(?:^|[_+])(?:floor|roof|ceiling|ground|terrain)(?:[_+]|$)", re.IGNORECASE)
DETAIL_PROP_RE = re.compile(r"(?:^|[_+])(?:prop|decal|bush|tree|vine)(?:[_+]|$)", re.IGNORECASE)
WATER_SECTOR_RE = re.compile(
    r"/lunascenes/([^/]+)/releasedata/waterdata/sector/t_(-?\d+)_(-?\d+)[.]asset$",
    re.IGNORECASE,
)

# Current-build GameAssembly's DynamicSceneUtil.GetGridSizeByLen starts at
# 32 m. Exported HLOD0/HLOD1/HLOD2 indices halve at each adjacent level, so
# their numeric suffix is the same doubling exponent used by the runtime grid.
BASE_CELL = 32.0
COVERAGE_TOLERANCE = 0.03  # origins this close to the best fit stay candidates
MIN_COVERAGE = 0.90  # below this the fit is not published as a background
MIN_SAMPLES = 50  # marker transforms needed before an origin is claimed
VIEW_ASPECT = 1024 / 1280  # the page's SVG viewBox, so the raster is undistorted
BOUNDS_PAD = 0.08
LONG_EDGE = 1100  # long side of the rendered raster, in pixels
# A browser scene is an optional inspection aid, not the full HLOD export.
# Keep its manifest bounded so opening a map never schedules hundreds of large
# OBJ downloads.  The PNG remains the complete, cheap backdrop.
MAX_SCENE_MESHES = 24
MAX_SCENE_TRIANGLES = 120_000
NO_HIT = -1e30  # empty depth-buffer sentinel
EDGE_EPSILON = 0.002  # half-pixel slack so adjacent triangles do not seam

# Elevation layers use a bounded grow-and-smooth pass while surface and point
# layers retain only exact depth hits.
FILL_ROUNDS = 6  # pixels of surface grown into gaps between scattered props
BLUR_RADIUS = 3
BLUR_PASSES = 2
HILLSHADE_AZIMUTH = 315.0
HILLSHADE_ALTITUDE = 45.0
HILLSHADE_SCALE = 1.6
AMBIENT = 0.80  # hillshade only modulates the top 20%, keeping the wash calm
# Grown pixels are more transparent than pixels that carry real geometry, so the
# reader can still see where the export actually had a surface.
ALPHA_REAL = 210
ALPHA_GROWN = 150

# A full oblique projection would move every marker by world Y and break the
# page's X/Z overlay contract.  For dg002 retain the exact top-down anchor and
# add one lighter, height-proportional sample toward screen +Z.  This exposes
# elevated roofs/towers without filling side walls that the HLOD evidence does
# not actually contain.
# dg002's screenshot-era appearance came from irregular mesh samples, not a
# screen-space stipple over filled triangles. Keep that choice level-scoped;
# other HLOD maps retain the conservative depth-point renderer.
LEVEL_SCAN_MODES = {"indie_dg002": "mesh_vertices"}
LEVEL_PREFERRED_LODS = {"indie_dg002": 0}
BASE_TEXTURE_SLOTS = ("_BaseColorMap", "_BaseMap", "_MainTex", "_Layer1BaseMap")
HLOD_CLUSTER_RE = re.compile(r"^S_HLOD(?P<lod>\d+)_-?\d+_-?\d+_Cluster_(?P<hash>-?\d+)$", re.IGNORECASE)
HLOD_MATERIAL_REL_RE = re.compile(
    r"/Material/M_auto_generated_HLOD(?P<lod>\d+)_(?P<level>.+?)_art_(?P<hash>-?\d+)_p[0-9A-F]+[.]json$",
    re.IGNORECASE,
)
TEXTURE_PREVIEW_EDGE = 96
WATER_SECTOR_SIZE = 128.0
DETAIL_HORIZONTAL_NORMAL_Y = 0.985
DETAIL_HORIZONTAL_AREA = 0.1
DETAIL_PROP_ONLY_LEVELS = {"base01_lv001", "base01_lv003"}
DEFAULT_SURFACE_POINT_DENSITY = 0.25  # deterministic world-space samples per square metre
# HLOD cluster indices use one fixed region grid. The dominant exact fits are
# Map01=(-1024,-1024) and Map02=(-2048,-2048); individual level marker
# occupancy must not move a member by one cell. GameAssembly's map UI path maps
# world coordinates linearly through UILevelMapLoadConfig and has no per-level
# presentation scale/translation, so no image-registration correction belongs
# in the render manifest.
REGION_HLOD_GRID_ORIGINS = {"map01": (-1024.0, -1024.0), "map02": (-2048.0, -2048.0)}
LEVEL_RENDER_ALIGNMENTS = {}

_TEXTURE_BINDINGS: dict[str, dict] | None = None
_HLOD_TEXTURE_BINDINGS: dict[tuple[str, int, int], dict] | None = None
_TEXTURE_PREVIEWS: dict[Path, tuple[int, int, bytes] | None] = {}
_MATERIAL_PARAMS: dict[tuple[Path, str], dict] = {}


def build_hlod_index(asset_map: Path) -> dict:
    """One streaming pass over the asset map, grouped by level and LOD."""
    levels: dict[str, dict[str, list]] = {}
    water_sectors: dict[str, list[dict]] = {}
    for entry in iter_asset_entries(asset_map):
        water = WATER_SECTOR_RE.search(str(entry.get("Container", "")))
        if (water and entry.get("Type") == "Texture2D"
                and str(entry.get("Name", "")).lower().startswith("t_water_sector_flowmap_")):
            water_sectors.setdefault(water.group(1), []).append({
                "i": int(water.group(2)),
                "j": int(water.group(3)),
                "pathId": entry.get("PathID"),
                "name": entry.get("Name"),
            })
        if entry.get("Type") != "Mesh":
            continue
        matched = CLUSTER_RE.match(str(entry.get("Name", "")))
        if not matched:
            continue
        level = LEVEL_RE.search(str(entry.get("Container", "")))
        if not level:
            continue
        levels.setdefault(level.group(1), {}).setdefault(matched.group(1), []).append({
            "i": int(matched.group(2)),
            "j": int(matched.group(3)),
            "pathId": entry.get("PathID"),
            "name": entry.get("Name"),
        })
    return {
        "schemaVersion": 2,
        "assetMap": str(asset_map),
        "assetMapSha256": sha256_file(asset_map),
        "levels": levels,
        "waterSectors": water_sectors,
    }


def load_hlod_index(asset_map: Path, cache: Path, refresh: bool) -> dict:
    if not refresh and cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("schemaVersion") == 2 and cached.get("assetMapSha256") == sha256_file(asset_map):
            return cached
    index = build_hlod_index(asset_map)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return index


def _alignment_bits(value: float) -> int:
    """How many times the origin divides by two; a proxy for grid alignment."""
    magnitude = abs(int(value))
    if magnitude == 0:
        return 99
    bits = 0
    while magnitude % 2 == 0:
        magnitude //= 2
        bits += 1
    return bits


def cell_size(lod: int) -> float:
    return BASE_CELL * (2 ** lod)


def origin_coverage(lods: dict[str, list], points: list[tuple[float, float]], origin_x: float, origin_z: float) -> float:
    """Return the worst per-LOD marker occupancy for one fixed grid origin."""
    if not points:
        return 0.0
    occupancy = {int(lod): {(row["i"], row["j"]) for row in rows} for lod, rows in lods.items()}
    if 0 not in occupancy:
        return 0.0
    return min(
        sum(
            1 for x, z in points
            if (math.floor((x - origin_x) / cell_size(lod)),
                math.floor((z - origin_z) / cell_size(lod))) in cells
        ) / len(points)
        for lod, cells in occupancy.items()
    )


def select_shared_origin(fits: list[dict]) -> tuple[float, float] | None:
    """Choose one region origin by marker-weighted agreement across levels."""
    votes: dict[tuple[float, float], int] = {}
    for fit in fits:
        key = (float(fit["originX"]), float(fit["originZ"]))
        votes[key] = votes.get(key, 0) + int(fit.get("samplePoints") or 0)
    if not votes:
        return None
    return max(
        votes,
        key=lambda key: (votes[key], min(_alignment_bits(key[0]), _alignment_bits(key[1]))),
    )


def fit_origin(lods: dict[str, list], points: list[tuple[float, float]]) -> dict | None:
    """Recover the grid origin that best explains the level's own transforms.

    Every LOD has to agree at once: a candidate origin is scored by its *worst*
    per-LOD marker coverage, so an origin cannot win by suiting one coarse LOD
    while misplacing the fine one. Among origins within `COVERAGE_TOLERANCE` of
    the best score the most power-of-two aligned one is chosen, because a
    streaming grid origin is aligned and a stray marker outside the art should
    not drag the answer off that alignment by one cell.
    """
    if len(points) < MIN_SAMPLES:
        return None
    occupancy = {int(lod): {(row["i"], row["j"]) for row in rows} for lod, rows in lods.items()}
    if 0 not in occupancy:
        return None
    base = occupancy[0]
    i_min, i_max = min(c[0] for c in base), max(c[0] for c in base)
    j_min, j_max = min(c[1] for c in base), max(c[1] for c in base)
    xs = [p[0] for p in points]
    zs = [p[1] for p in points]

    scored: list[tuple[float, float, float]] = []
    for kx in range(int(min(xs) // BASE_CELL) - i_max - 1, int(max(xs) // BASE_CELL) - i_min + 2):
        for kz in range(int(min(zs) // BASE_CELL) - j_max - 1, int(max(zs) // BASE_CELL) - j_min + 2):
            origin_x, origin_z = kx * BASE_CELL, kz * BASE_CELL
            worst = origin_coverage(lods, points, origin_x, origin_z)
            scored.append((worst, origin_x, origin_z))
    if not scored:
        return None

    best = max(row[0] for row in scored)
    band = [row for row in scored if row[0] >= best - COVERAGE_TOLERANCE]
    coverage, origin_x, origin_z = max(
        band, key=lambda row: (min(_alignment_bits(row[1]), _alignment_bits(row[2])), row[0])
    )
    return {
        "originX": origin_x,
        "originZ": origin_z,
        "baseCellSize": BASE_CELL,
        "coverage": round(coverage, 4),
        "bestCoverage": round(best, 4),
        "samplePoints": len(points),
        "tiedOrigins": sum(1 for row in scored if row[0] >= best - COVERAGE_TOLERANCE),
        "alignmentBits": min(_alignment_bits(origin_x), _alignment_bits(origin_z)),
        "lods": sorted(occupancy),
    }


def plot_bounds(points: list[tuple[float, float]], min_pad: float = 32.0) -> dict[str, float]:
    """Marker bounds padded out to the page's viewBox aspect.

    The frontend projects onto these bounds when they are declared, so matching
    the SVG aspect here is what keeps the raster from being stretched against
    the marker positions drawn over it.
    """
    xs = [p[0] for p in points]
    zs = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    pad_x = max((max_x - min_x) * BOUNDS_PAD, min_pad)
    pad_z = max((max_z - min_z) * BOUNDS_PAD, min_pad)
    min_x, max_x = min_x - pad_x, max_x + pad_x
    min_z, max_z = min_z - pad_z, max_z + pad_z

    width, height = max_x - min_x, max_z - min_z
    if width / height > VIEW_ASPECT:
        extra = width / VIEW_ASPECT - height
        min_z -= extra / 2
        max_z += extra / 2
    else:
        extra = height * VIEW_ASPECT - width
        min_x -= extra / 2
        max_x += extra / 2
    return {"minX": min_x, "maxX": max_x, "minZ": min_z, "maxZ": max_z}


def shade(value: float) -> int:
    """Clamp a 0..1 channel to a byte."""
    return max(0, min(255, round(value * 255)))


def write_png(path: Path, width: int, height: int, rows: list[bytes], compression: int = 9) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\0" + row for row in rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, compression))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    return up if up_distance <= upper_left_distance else upper_left


def read_png_preview(path: Path, max_edge: int = TEXTURE_PREVIEW_EDGE) -> tuple[int, int, bytes] | None:
    """Decode an exported 8-bit RGBA PNG into a bounded nearest-sample preview."""
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    cursor = 8
    width = height = 0
    compressed = bytearray()
    while cursor + 12 <= len(payload):
        length = struct.unpack_from(">I", payload, cursor)[0]
        kind = payload[cursor + 4:cursor + 8]
        data = payload[cursor + 8:cursor + 8 + length]
        cursor += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", data
            )
            if (bit_depth, color_type, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                return None
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            break
    if width <= 0 or height <= 0 or not compressed:
        return None
    stride = width * 4
    scale = max(width / max_edge, height / max_edge, 1.0)
    sample_width = max(1, round(width / scale))
    sample_height = max(1, round(height / scale))
    sample_x = [min(width - 1, int(index * width / sample_width)) for index in range(sample_width)]
    sample_y = {min(height - 1, int(index * height / sample_height)): index for index in range(sample_height)}
    rows = _unfilter_rgba8_rows(payload, bytes(compressed), width, height)
    if rows is None:
        return None
    sampled = bytearray(sample_width * sample_height * 4)
    # Only sampled rows are ever read, so this walks the preview grid rather
    # than every scanline in the source image.
    for source_y, target_y in sample_y.items():
        row = source_y * stride
        target = target_y * sample_width * 4
        for target_x, source_x in enumerate(sample_x):
            source = row + source_x * 4
            sampled[target + target_x * 4:target + target_x * 4 + 4] = rows[source:source + 4]
    return sample_width, sample_height, bytes(sampled)


def _unfilter_rgba8_rows(payload: bytes, compressed: bytes, width: int, height: int) -> bytes | None:
    """Return the image's unfiltered 8-bit RGBA rows, without the filter bytes.

    PNG's Sub/Average/Paeth filters each depend on the pixel to their left, so
    the reconstruction cannot be vectorised along a scanline and the stdlib
    loop below costs about three quarters of a full preview build. Pillow does
    the same reconstruction in C, so it is used when importable and the pure
    Python loop stays as an exact fallback. Both paths are byte-identical: the
    caller has already rejected anything that is not non-interlaced 8-bit RGBA,
    which is the one layout where Pillow's ``RGBA`` buffer is precisely these
    reconstructed rows. Pillow inflates the IDAT stream itself, so the caller
    hands over the still-compressed bytes and only the fallback pays for a
    ``zlib.decompress``; a stream Pillow cannot decode raises and is rejected
    here exactly as a short inflate was before.
    """
    if _PILImage is not None:
        try:
            with _PILImage.open(io.BytesIO(payload)) as image:
                if image.mode != "RGBA":
                    return None
                return image.tobytes()
        except Exception:
            return None
    stride = width * 4
    try:
        raw = zlib.decompress(compressed)
    except zlib.error:
        return None
    if len(raw) != (stride + 1) * height:
        return None
    rows = bytearray(stride * height)
    previous = bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        filter_type = raw[start]
        current = bytearray(raw[start + 1:start + 1 + stride])
        for index in range(stride):
            left = current[index - 4] if index >= 4 else 0
            up = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if filter_type == 1:
                current[index] = (current[index] + left) & 255
            elif filter_type == 2:
                current[index] = (current[index] + up) & 255
            elif filter_type == 3:
                current[index] = (current[index] + ((left + up) >> 1)) & 255
            elif filter_type == 4:
                current[index] = (current[index] + _paeth(left, up, upper_left)) & 255
            elif filter_type != 0:
                return None
        rows[y * stride:(y + 1) * stride] = current
        previous = current
    return bytes(rows)


def _relation_path(relative: str, source_roots: dict[str, str]) -> Path | None:
    normalized = str(relative or "").replace("\\", "/")
    if "/" not in normalized:
        return None
    source, tail = normalized.split("/", 1)
    configured = source_roots.get(source)
    if not configured:
        return None
    path = Path(configured)
    resolved = (path if path.is_absolute() else ROOT / path) / tail
    try:
        resolved.resolve().relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def _asset_rel_from_obj(value: object) -> str:
    obj = str(value or "").replace("\\", "/")
    parts = obj.split("/recovered/AnimeStudio-cli/", 1)
    if len(parts) != 2:
        return ""
    tail = parts[1].split("/")
    if len(tail) < 4 or tail[1] != "convert_by_type":
        return ""
    return f"{tail[0]}/{'/'.join(tail[2:])}"


def texture_bindings() -> dict[str, dict]:
    """Compact exact one-material Mesh -> base-color texture relations."""
    global _TEXTURE_BINDINGS, _HLOD_TEXTURE_BINDINGS
    if _TEXTURE_BINDINGS is not None:
        return _TEXTURE_BINDINGS
    _TEXTURE_BINDINGS = {}
    _HLOD_TEXTURE_BINDINGS = {}
    if not ASSET_INDEX.is_file():
        return _TEXTURE_BINDINGS
    try:
        payload = json.loads(ASSET_INDEX.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _TEXTURE_BINDINGS
    source_roots = payload.get("sourceRoots") or {}
    for asset_rel, relation in (payload.get("relations") or {}).items():
        material_match = HLOD_MATERIAL_REL_RE.search(str(asset_rel).replace("\\", "/"))
        if material_match and isinstance(relation, dict):
            selected = None
            for slot in BASE_TEXTURE_SLOTS:
                candidates = [
                    row for row in (relation.get("textures") or [])
                    if row.get("slot") == slot and row.get("rel")
                ]
                if candidates:
                    if len(candidates) == 1:
                        selected = candidates[0]
                    break
            texture_path = _relation_path(selected["rel"], source_roots) if selected else None
            material_path = _relation_path(asset_rel, source_roots)
            key = (
                material_match.group("level").lower(),
                int(material_match.group("lod")),
                int(material_match.group("hash")),
            )
            # Ownership is ambiguous as soon as a second generated material
            # claims the same level/LOD/signed suffix, even if only one of the
            # candidates happens to have an exportable texture today.
            if key in _HLOD_TEXTURE_BINDINGS:
                _HLOD_TEXTURE_BINDINGS[key] = None
                continue
            _HLOD_TEXTURE_BINDINGS[key] = None
            if selected and texture_path and material_path and texture_path.is_file() and material_path.is_file():
                binding = {
                    "slot": selected["slot"],
                    "textureRel": selected["rel"],
                    "texturePath": texture_path,
                    "materialRel": asset_rel,
                    "materialPath": material_path,
                    "mappingMethod": "exact_hlod_level_lod_signed_suffix_to_generated_material",
                }
                _HLOD_TEXTURE_BINDINGS[key] = binding
        if "/Mesh/" not in asset_rel or not isinstance(relation, dict):
            continue
        materials = relation.get("materials") or []
        if len(materials) != 1 or not materials[0].get("rel"):
            continue
        selected = None
        for slot in BASE_TEXTURE_SLOTS:
            candidates = [
                row for row in (relation.get("textures") or [])
                if row.get("slot") == slot and row.get("rel")
            ]
            if candidates:
                if len(candidates) == 1:
                    selected = candidates[0]
                break
        if not selected:
            continue
        texture_path = _relation_path(selected["rel"], source_roots)
        material_path = _relation_path(materials[0]["rel"], source_roots)
        if texture_path and material_path and texture_path.is_file() and material_path.is_file():
            _TEXTURE_BINDINGS[asset_rel] = {
                "slot": selected["slot"],
                "textureRel": selected["rel"],
                "texturePath": texture_path,
                "materialRel": materials[0]["rel"],
                "materialPath": material_path,
            }
    del payload
    return _TEXTURE_BINDINGS


def hlod_texture_bindings(level_id: str, lod: int, clusters: list[dict]) -> dict[int, dict]:
    """Bind HLOD clusters to generated materials by their exact authored suffix contract."""
    texture_bindings()
    available = _HLOD_TEXTURE_BINDINGS or {}
    result = {}
    for cluster in clusters:
        match = HLOD_CLUSTER_RE.fullmatch(str(cluster.get("name") or ""))
        if not match or int(match.group("lod")) != lod:
            continue
        binding = available.get((level_id.lower(), lod, int(match.group("hash"))))
        path_id = cluster.get("pathId")
        if binding and isinstance(path_id, int):
            result[path_id] = binding
    return result


def _material_render_params(binding: dict) -> dict:
    key = (Path(binding["materialPath"]), str(binding["slot"]))
    if key in _MATERIAL_PARAMS:
        return _MATERIAL_PARAMS[key]
    result = {
        "scale": (1.0, 1.0), "offset": (0.0, 0.0), "tint": (1.0, 1.0, 1.0),
        "alphaMode": "opaque", "cutoff": 0.05,
    }
    try:
        payload = json.loads(key[0].read_text(encoding="utf-8"))
        saved = payload.get("m_SavedProperties") or {}
        env = (saved.get("m_TexEnvs") or {}).get(key[1]) or {}
        scale = env.get("m_Scale") or {}
        offset = env.get("m_Offset") or {}
        result["scale"] = (float(scale.get("X", 1.0)), float(scale.get("Y", 1.0)))
        result["offset"] = (float(offset.get("X", 0.0)), float(offset.get("Y", 0.0)))
        colors = saved.get("m_Colors") or {}
        tint = colors.get("_BaseColor") or colors.get("_Color") or colors.get("_SurfaceAlbedo") or {}
        result["tint"] = tuple(max(0.0, float(tint.get(channel, 1.0))) for channel in ("r", "g", "b"))
        floats = saved.get("m_Floats") or {}
        result["cutoff"] = max(0.0, min(1.0, float(floats.get("_AlphaClipThreshold", 0.05))))
        valid_keywords = {str(value).upper() for value in (payload.get("m_ValidKeywords") or [])}
        render_type = str((payload.get("m_StringTagMap") or {}).get("RenderType") or "").lower()
        queue = int(payload.get("m_CustomRenderQueue", -1))
        if "_ALPHATEST_ON" in valid_keywords or render_type in {"transparentcutout", "alphatest"}:
            result["alphaMode"] = "cutout"
        elif "transparent" in render_type or queue >= 3000:
            result["alphaMode"] = "transparent"
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        pass
    _MATERIAL_PARAMS[key] = result
    return result


def _texture_render_source(binding: dict | None) -> dict | None:
    if not binding:
        return None
    path = Path(binding["texturePath"])
    if path not in _TEXTURE_PREVIEWS:
        _TEXTURE_PREVIEWS[path] = read_png_preview(path)
    preview = _TEXTURE_PREVIEWS[path]
    if not preview:
        return None
    width, height, pixels = preview
    return {**_material_render_params(binding), "width": width, "height": height, "pixels": pixels,
            "textureRel": binding["textureRel"], "materialRel": binding["materialRel"]}


def _sample_texture(texture: dict, u: float, v: float) -> tuple[int, int, int, int] | None:
    texture_x = min(texture["width"] - 1, int((u % 1.0) * texture["width"]))
    texture_y = min(texture["height"] - 1, int(((1.0 - v) % 1.0) * texture["height"]))
    offset = (texture_y * texture["width"] + texture_x) * 4
    source = texture["pixels"]
    alpha = source[offset + 3]
    alpha_mode = texture.get("alphaMode", "opaque")
    if alpha_mode == "cutout" and alpha / 255 < texture["cutoff"]:
        return None
    tint = texture["tint"]
    return (
        min(255, round(source[offset] * tint[0])),
        min(255, round(source[offset + 1] * tint[1])),
        min(255, round(source[offset + 2] * tint[2])),
        alpha if alpha_mode == "transparent" else 255,
    )


def level_positions(path: Path) -> list[tuple[float, float, float]]:
    """Exact registry/quest X/Y/Z positions published for one map."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    points = []
    for node in [*(payload.get("markers") or []), *(payload.get("questPoints") or [])]:
        position = node.get("position") or {}
        x, y, z = position.get("x"), position.get("y"), position.get("z")
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (x, y, z)):
            points.append((float(x), float(y), float(z)))
    return points


def _instance_meshes(instance: dict) -> list[dict]:
    """Return the current composite mesh list for one streaming instance."""
    meshes = instance.get("meshes")
    return [row for row in meshes if isinstance(row, dict)] if isinstance(meshes, list) else []


def _is_explicit_overhead_cover(instance: dict) -> bool:
    """Recognize authored roof/ceiling instances without guessing by height."""
    names = [instance.get("entityBase"), instance.get("name")]
    names.extend(mesh.get("name") for mesh in _instance_meshes(instance))
    return any(OVERHEAD_COVER_RE.search(str(name or "")) for name in names)


def _is_detail_structural(instance: dict, mesh: dict) -> bool:
    """Exclude explicitly authored broad structure from analytical detail."""
    names = (instance.get("entityBase"), instance.get("name"), mesh.get("name"))
    return any(DETAIL_STRUCTURAL_RE.search(str(name or "")) for name in names)


def _is_detail_prop(instance: dict, mesh: dict) -> bool:
    """Keep authored props and vegetation even when their useful top is flat."""
    names = (instance.get("entityBase"), instance.get("name"), mesh.get("name"))
    return any(DETAIL_PROP_RE.search(str(name or "")) for name in names)


def _is_large_horizontal_triangle(points: list[tuple[float, float, float]]) -> bool:
    """Recognize slab interiors while retaining small table/prop tops."""
    a, b, c = points
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    magnitude = math.sqrt(nx * nx + ny * ny + nz * nz)
    if magnitude <= 1e-9 or abs(ny) / magnitude < DETAIL_HORIZONTAL_NORMAL_Y:
        return False
    projected_area = abs(ux * vz - uz * vx) * 0.5
    return projected_area >= DETAIL_HORIZONTAL_AREA


def streaming_projection_payload(source: Path) -> tuple[list[tuple[float, float, float]], dict]:
    """Adapt one exact InitChunkData sidecar to the renderer's compact input."""
    payload = json.loads(source.read_text(encoding="utf-8"))
    mesh_by_base = {
        row.get("entityBase"): row.get("meshes")
        for row in payload.get("entityBases") or []
        if row.get("entityBase") and isinstance(row.get("meshes"), list) and row.get("meshes")
    }
    positions = []
    markers = []
    for instance in payload.get("instances") or []:
        matrix = instance.get("matrixColumnMajor")
        if not isinstance(matrix, list) or len(matrix) != 16:
            continue
        position = (float(matrix[12]), float(matrix[13]), float(matrix[14]))
        positions.append(position)
        meshes = mesh_by_base.get(instance.get("entityBase")) or []
        markers.append({
            "streamingInstance": {
                "entityId": instance.get("entityId"),
                "entityBase": instance.get("entityBase"),
                "name": instance.get("name"),
                "matrixColumnMajor": matrix,
                "sourceFile": instance.get("sourceFile"),
                "meshes": meshes,
            },
        })
    return positions, {
        "markers": markers,
        "exactHlodMatrices": (payload.get("hlodIdentityContract") or {}).get("status") == "exact",
    }


def render_point_cloud(
    level_id: str,
    positions: list[tuple[float, float, float]],
    output_root: Path,
    map_payload: dict | None = None,
    bounds_override: dict[str, float] | None = None,
    surface_point_density: float = DEFAULT_SURFACE_POINT_DENSITY,
) -> dict | None:
    """Render an evidence-only height-tinted point cloud when no map art exists.

    This deliberately draws only exact published transforms. It gives sparse
    scenes a spatial backdrop without connecting points into invented terrain
    or claiming that registry entities are recovered scene meshes.
    """
    if not positions:
        return None
    streaming = [
        row.get("streamingInstance")
        for row in ((map_payload or {}).get("markers") or [])
        if isinstance(row.get("streamingInstance"), dict)
    ]
    exact_hlod_matrices = bool((map_payload or {}).get("exactHlodMatrices"))
    streaming_xz = [
        (float(row["matrixColumnMajor"][12]), float(row["matrixColumnMajor"][14]))
        for row in streaming
        if isinstance(row.get("matrixColumnMajor"), list) and len(row["matrixColumnMajor"]) == 16
    ]
    # A recovered streaming scene with hundreds of transforms is not the old
    # sparse registry fallback. Four metres keeps its exact extents readable;
    # small evidence sets retain the conservative 32 m context margin.
    bounds = bounds_override or plot_bounds(
        streaming_xz or [(x, z) for x, _y, z in positions],
        min_pad=1.0 if streaming_xz else (4.0 if len(positions) >= 100 else 32.0),
    )
    span_x = max(bounds["maxX"] - bounds["minX"], 1.0)
    span_z = max(bounds["maxZ"] - bounds["minZ"], 1.0)
    # The PNG is later fitted to this exact world rectangle. Giving every
    # streaming scene the UI canvas aspect silently stretched its geometry
    # when the rectangle was square or portrait (most visibly Dijiang).
    width, height = raster_size(span_x, span_z)
    pixels = [bytearray(width * 4) for _ in range(height)]
    sparse_point_depth = [NO_HIT] * (width * height)
    ys = [row[1] for row in positions]
    low, high = min(ys), max(ys)
    y_span = max(high - low, 1.0)
    radius = max(2, min(6, round(9 - math.log2(max(len(positions), 2)) / 2)))

    def blend(
        px: int,
        py: int,
        color: tuple[int, int, int],
        alpha: int,
        point_height: float | None = None,
    ) -> None:
        if not (0 <= px < width and 0 <= py < height) or alpha <= 0:
            return
        if point_height is not None:
            index = py * width + px
            sparse_point_depth[index] = max(sparse_point_depth[index], point_height)
        row = pixels[py]
        offset = px * 4
        inverse = 255 - alpha
        row[offset] = (color[0] * alpha + row[offset] * inverse) // 255
        row[offset + 1] = (color[1] * alpha + row[offset + 1] * inverse) // 255
        row[offset + 2] = (color[2] * alpha + row[offset + 2] * inverse) // 255
        row[offset + 3] = min(255, alpha + row[offset + 3] * inverse // 255)

    # Elevation and material surfaces retain floors and other authored
    # environment geometry, but explicit roof/ceiling covers remain omitted.
    overhead_covers = [
        row for row in streaming
        if _instance_meshes(row) and _is_explicit_overhead_cover(row)
    ]
    resolved = [
        row for row in streaming
        if _instance_meshes(row) and not _is_explicit_overhead_cover(row)
    ]
    rendered_instances = rendered_triangles = rendered_vertex_samples = 0
    textured_instances = textured_triangles = textured_pixels = 0
    used_textures: list[str] = []
    real_pixel_ratio = 0.0
    surface_depth: list[float] | None = None
    detail_depth: list[float] | None = None
    detail_albedo: bytearray | None = None
    detail_triangles = excluded_detail_triangles = 0
    if resolved:
        render_bindings = streaming_texture_bindings(level_id, resolved)
        detail_props_only = level_id in DETAIL_PROP_ONLY_LEVELS
        if detail_props_only:
            raster = rasterise_streaming_depth(
                resolved, bounds, width, height, render_bindings, detail_props_only=True
            )
        else:
            raster = rasterise_streaming_depth(resolved, bounds, width, height, render_bindings)
        depth = raster["depth"]
        albedo = raster["albedo"]
        surface_depth = depth
        detail_depth = raster.get("detailDepth", depth)
        detail_albedo = raster.get("detailAlbedo", albedo)
        rendered_instances = raster["usedInstances"]
        textured_instances = raster["texturedInstances"]
        rendered_triangles = raster["triangles"]
        textured_triangles = raster["texturedTriangles"]
        rendered_vertex_samples = raster["vertexSamples"]
        textured_pixels = raster["texturedPixels"]
        used_textures = raster["usedTextures"]
        detail_triangles = raster.get("detailTriangles", rendered_triangles)
        excluded_detail_triangles = raster.get("excludedDetailTriangles", 0)
        real = [value > NO_HIT for value in depth]
        covered = [value for value in depth if value > NO_HIT]
        if covered:
            mesh_low, mesh_high = min(covered), max(covered)
            mesh_span = max(mesh_high - mesh_low, 1.0)
            real_pixel_ratio = sum(real) / (width * height)
            low, high = mesh_low, mesh_high
            for py in range(height):
                row = pixels[py]
                for px in range(width):
                    value = depth[py * width + px]
                    if value <= NO_HIT:
                        continue
                    tint = (value - mesh_low) / mesh_span
                    offset = px * 4
                    color_offset = (py * width + px) * 4
                    if albedo[color_offset + 3]:
                        row[offset:offset + 4] = bytes((
                            albedo[color_offset],
                            albedo[color_offset + 1],
                            albedo[color_offset + 2],
                            albedo[color_offset + 3],
                        ))
                    else:
                        base = elevation_color(tint)
                        light = 0.72 + 0.24 * (1.0 - tint)
                        base = tuple(min(255, round(channel * light)) for channel in base)
                        row[offset:offset + 4] = bytes((*base, 225))
    if not rendered_instances:
        # Sparse fallbacks remain exact transform points. This also covers a
        # resolved streaming mesh that produces zero analytical hits (for
        # example indie_dg011's sole structural floor is intentionally
        # excluded from the point/elevation pass). A soft halo keeps isolated
        # transforms legible without connecting them.
        for x, y, z in sorted(positions, key=lambda row: row[1]):
            px = round((x - bounds["minX"]) / span_x * (width - 1))
            py = round((bounds["maxZ"] - z) / span_z * (height - 1))
            height_t = (y - low) / y_span
            color = (8, 10, 11)
            height_alpha = 0.78 + 0.22 * height_t
            for dy in range(-radius * 2, radius * 2 + 1):
                for dx in range(-radius * 2, radius * 2 + 1):
                    distance = math.hypot(dx, dy)
                    if distance <= radius * 2:
                        blend(
                            px + dx, py + dy, color,
                            round(42 * height_alpha * (1 - distance / (radius * 2 + 0.01))), y,
                        )
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    distance = math.hypot(dx, dy)
                    if distance <= radius:
                        blend(
                            px + dx, py + dy, color,
                            round(210 * height_alpha * (1 - 0.55 * distance / (radius + 0.01))), y,
                        )

    mesh_rows: dict[str, dict] = {}
    for row in resolved:
        for mesh in _instance_meshes(row):
            obj = str(mesh.get("obj") or "").replace("\\", "/")
            parts = obj.split("/recovered/AnimeStudio-cli/", 1)
            asset_rel = ""
            if len(parts) == 2:
                tail = parts[1].split("/")
                if len(tail) >= 4 and tail[1] == "convert_by_type":
                    asset_rel = f"{tail[0]}/{'/'.join(tail[2:])}"
            key = str(mesh.get("pathId") or mesh.get("name") or obj)
            current = mesh_rows.setdefault(key, {
                "name": mesh.get("name"),
                "pathId": mesh.get("pathId"),
                "assetRel": asset_rel,
                "instanceCount": 0,
            })
            current["instanceCount"] += 1

    output_root.mkdir(parents=True, exist_ok=True)
    elevation_underlay = None
    point_cloud_overlay = None
    if rendered_instances and detail_depth:
        # Material and grayscale elevation layers retain the full recovered
        # depth surface, including floors. Structural filtering is a
        # point-cloud presentation rule only.
        elevation_depth = surface_depth or detail_depth
        elevation_underlay = render_elevation_underlay(
            level_id, elevation_depth, width, height, output_root,
            image_suffix="streaming_elevation",
            source_label=(
                "full exact streaming-mesh triangle depth"
                if exact_hlod_matrices else "full recovered streaming-mesh triangle depth"
            ),
        )
        point_cloud_overlay = (
            render_streaming_surface_samples(
                level_id, resolved, bounds, width, height, output_root,
                surface_point_density, render_bindings,
            )
            if exact_hlod_matrices else
            render_depth_point_overlay(
                level_id, detail_depth, width, height, output_root,
                image_suffix="streaming_points",
                material_colors=detail_albedo,
            )
        )
    image_name = (
        f"{level_id}_streaming_textured_topdown.png" if textured_pixels else
        f"{level_id}_streaming_topdown.png" if rendered_instances else
        f"{level_id}_registry_point_cloud.png"
    )
    write_png(output_root / image_name, width, height, [bytes(row) for row in pixels])
    point_height_mask = None if rendered_instances else render_point_height_mask(
        level_id, sparse_point_depth, width, height, output_root,
        image_suffix="registry_height_mask", sampling="all",
    )
    if not rendered_instances:
        elevation_underlay = render_sparse_point_elevation(
            level_id, sparse_point_depth, width, height, output_root,
        )
        point_cloud_overlay = {
            "src": f"render/{image_name}",
            "method": "exact_registry_transform_point_cloud",
            "defaultOpacity": 1.0,
            "heightMask": point_height_mask,
        }
    return {
        "schemaVersion": 1,
        "status": (
            "recovered_streaming_textured_topdown" if textured_pixels else
            "recovered_streaming_mesh_topdown" if rendered_instances else
            "exact_registry_transform_point_cloud"
        ),
        "levelId": level_id,
        "src": f"render/{image_name}",
        "elevationUnderlay": elevation_underlay,
        "pointCloudOverlay": point_cloud_overlay,
        "worldBounds": bounds,
        "coordinateSystem": "Unity world X/Z; image top is +Z; tint derives from exact world Y",
        "render": {
            "method": (
                "exact_streaming_matrix_obj_uv_material_texture_depth_pass" if textured_pixels else
                "exact_streaming_matrix_obj_depth_pass" if rendered_instances else
                "exact_registry_transform_point_cloud"
            ),
            "pointCount": 0 if rendered_instances else len(positions),
            "pointRadius": 0 if rendered_instances else radius,
            "renderedInstanceCount": rendered_instances,
            "renderedTriangleCount": rendered_triangles,
            "renderedVertexSampleCount": rendered_vertex_samples,
            "texturedInstanceCount": textured_instances,
            "texturedTriangleCount": textured_triangles,
            "texturedPixelCount": textured_pixels,
            "detailTriangleCount": detail_triangles,
            "excludedDetailTriangleCount": excluded_detail_triangles,
            "detailRule": (
                "authored prop/decal/vegetation instances only"
                if level_id in DETAIL_PROP_ONLY_LEVELS else
                "exclude explicitly named floor/roof/ceiling/ground/terrain meshes and near-horizontal "
                f"non-prop triangles >= {DETAIL_HORIZONTAL_AREA:g} m2"
            ),
            "baseColorTextureCount": len(used_textures),
            "baseColorTextures": used_textures,
            "excludedOverheadCoverInstanceCount": len(overhead_covers),
            "overheadCoverRule": "authored entity/mesh name contains roof or ceiling",
            "realPixelRatio": round(real_pixel_ratio, 4),
            "elevationRange": {"min": low, "max": high},
        },
        "modelScene": {
            "status": "streaming_meshes_rasterized" if rendered_instances else "no_recovered_scene_meshes",
            "positionStatus": "exact_streaming_matrix" if mesh_rows else "unavailable",
            "meshes": list(mesh_rows.values()),
            "meshCount": len(mesh_rows),
            "instanceCount": len(resolved),
        },
        "boundary": (
            f"Orthographic depth raster of {rendered_instances} static OBJ instances placed by their recovered "
            f"InitChunkData 4x4 matrices ({rendered_triangles} triangles and {rendered_vertex_samples} "
            f"legacy vertex samples). The point layer retains {detail_triangles} detail triangles and "
            f"exclude {excluded_detail_triangles} broad structural/slab triangles. {textured_pixels} visible pixels sample {len(used_textures)} exact "
            "single-material base-color texture bindings through exported OBJ UVs; unresolved or multi-material "
            f"meshes retain colored elevation shading. {len(overhead_covers)} explicitly named roof/ceiling instances are "
            "omitted so capped interiors remain readable; no height-based structural culling is applied. The remaining "
            f"{len(streaming) - rendered_instances} non-rasterized instances are not drawn as location dots."
            if rendered_instances else
            f"Evidence-only point cloud drawn from {len(positions)} exact published registry and quest X/Y/Z transforms. "
            "Points are not connected into terrain and do not claim recovered scene geometry."
        ),
    }


def mesh_file_index(mesh_root: Path) -> dict[str, Path]:
    """Exported OBJ files keyed by the PathID hex suffix AnimeStudio appends."""
    if not mesh_root.is_dir():
        return {}
    return {path.stem.rsplit("_p", 1)[-1].upper(): path for path in mesh_root.glob("*.obj") if "_p" in path.stem}


def texture_file_index(texture_root: Path) -> dict[str, Path]:
    """Exported PNG files keyed by AnimeStudio's PathID hex suffix."""
    if not texture_root.is_dir():
        return {}
    return {
        path.stem.rsplit("_p", 1)[-1].upper(): path
        for path in texture_root.glob("*.png") if "_p" in path.stem
    }


def water_scene_id(level_id: str, source_scene: str | None = None) -> str:
    """Map gameplay slices to the LunaScene that owns WaterData sectors."""
    candidate = source_scene or level_id
    # The map01 WaterData flow fields do not establish an authored minimap
    # water surface; cyan segmentation there misclassifies Wuling terrain.
    # Valley map screens are the validated regional consumer of the shared
    # map02 WaterData sectors. Other/isolated scenes keep their own exact id.
    matched = re.match(r"^(map02)_lv[0-9]+$", candidate, re.IGNORECASE)
    return matched.group(1) if matched else candidate


def render_water_overlay(
    level_id: str,
    scene_id: str,
    bounds: dict[str, float],
    sectors_by_scene: dict[str, list[dict]],
    texture_files: dict[str, Path],
    output_root: Path,
) -> dict | None:
    """Render authored minimap water colors as an independent transparent layer.

    WaterData's ``T_water_*flowmap*`` textures are vector/height fields, not
    binary coverage masks. Treating their blue channel as occupancy produced
    long rays and bands that do not describe shore geometry. Until the actual
    water-surface mesh consumer is recovered, maps without authored minimap art
    deliberately publish no water layer.
    """
    sectors = sectors_by_scene.get(scene_id) or []
    if not sectors:
        return None
    minimap_path = output_root / f"{level_id}_minimap.png"
    preview = read_png_preview(minimap_path, LONG_EDGE) if minimap_path.is_file() else None
    if not preview:
        return None
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    width, height = raster_size(span_x, span_z)
    rows = [bytearray(width * 4) for _ in range(height)]
    source_width, source_height, pixels = preview
    water_pixels = 0
    for target_y in range(height):
        source_y = min(source_height - 1, int((target_y + 0.5) / height * source_height))
        row = rows[target_y]
        for target_x in range(width):
            source_x = min(source_width - 1, int((target_x + 0.5) / width * source_width))
            source = (source_y * source_width + source_x) * 4
            red, green, blue, alpha = pixels[source:source + 4]
            # Authored Wuling/Valley minimaps paint water in a stable cyan
            # family. Blue and green must both dominate red; requiring a
            # visible midtone rejects transparent padding and near-black map
            # shadows without tracing roads or the flowmap's vector rays.
            if not (
                alpha > 0 and green > red * 1.12 and blue > red * 1.18
                and green > 55 and blue > 55 and blue > green * 0.62
            ):
                continue
            target = target_x * 4
            row[target:target + 4] = bytes((32, 142, 184, 168))
            water_pixels += 1
    if not water_pixels:
        return None
    image_name = f"{level_id}_water.png"
    write_png(output_root / image_name, width, height, [bytes(row) for row in rows])
    return {
        "src": f"render/{image_name}",
        "status": "recovered_authored_minimap_water_color_mask",
        "method": "authored minimap cyan-family water-color segmentation",
        "worldBounds": bounds,
        "sceneId": scene_id,
        "sectorSize": WATER_SECTOR_SIZE,
        "sourceSectorCount": len(sectors),
        "renderedSectorCount": 0,
        "waterPixelRatio": round(water_pixels / (width * height), 4),
        "boundary": (
            "Independent authored-minimap water-color layer. WaterData sector flowmaps corroborate that the "
            "scene uses HGWater, but are not treated as coverage: their packed flow/height channels contain "
            "long vector bands. Maps without authored minimap art remain empty until water meshes are recovered."
        ),
    }


def _scene_meshes(
    used: list[dict],
    mesh_files: dict[str, Path],
    *,
    lod: int,
    fit: dict,
) -> list[dict]:
    """Publish a bounded, safe OBJ scene manifest for the frontend viewer.

    The rasterizer has already established that these meshes landed in the
    recovered grid.  Reusing that exact list keeps the optional 3D inspection
    view from inventing a second asset selection algorithm.  Paths are only
    published when they resolve below the repository's ``export_full`` tree;
    custom probe directories and absolute paths therefore fail closed.  The
    viewer receives the same inferred cell transform and axis conversion as
    the PNG renderer, so it can label this as diagnostic geometry rather than
    presenting it as an authored scene transform.
    """
    export_root = (ROOT / "export_full").resolve()
    cell = cell_size(lod)
    rows: list[dict] = []
    triangles = 0
    for cluster in used:
        try:
            path_id = int(cluster.get("pathId"))
        except (TypeError, ValueError):
            continue
        suffix = f"{path_id & ((1 << 64) - 1):X}"
        path = mesh_files.get(suffix)
        if path is None:
            continue
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(export_root).as_posix()
        except (OSError, ValueError):
            # Do not publish a file URL outside the selected export.  This is
            # important when a developer points --mesh-root at a scratch tree.
            continue
        try:
            mesh_triangles = max(0, int(cluster.get("triangles") or 0))
        except (TypeError, ValueError):
            continue
        if rows and triangles + mesh_triangles > MAX_SCENE_TRIANGLES:
            break
        match = CLUSTER_RE.match(str(cluster.get("name") or ""))
        if not match:
            continue
        grid_i, grid_j = int(match.group(2)), int(match.group(3))
        # Keep the compact asset-index spelling alongside the direct raw URL.
        # This lets the map link into the existing Assets OBJ viewer without
        # making that page scan or understand map-recovery manifests.
        asset_rel = ""
        relative_parts = relative.split("/")
        if len(relative_parts) >= 5 and relative_parts[0:2] == ["recovered", "AnimeStudio-cli"]:
            source = relative_parts[2]
            if len(relative_parts) >= 5 and relative_parts[3] == "convert_by_type":
                asset_rel = f"{source}/{'/'.join(relative_parts[4:])}"
        if mesh_triangles > MAX_SCENE_TRIANGLES:
            # One pathological OBJ must not defeat the scene cap by being the
            # first accepted row; the PNG path already rendered it safely.
            continue
        rows.append({
            "name": str(cluster.get("name") or resolved.stem),
            "pathId": path_id,
            "src": f"/export_full/{relative}",
            "assetRel": asset_rel,
            "triangles": mesh_triangles,
            "gridIndex": {"i": grid_i, "j": grid_j},
            "translation": {
                "x": fit["originX"] + grid_i * cell + cell / 2,
                "y": 0.0,
                "z": fit["originZ"] + grid_j * cell + cell / 2,
            },
        })
        triangles += mesh_triangles
        if len(rows) >= MAX_SCENE_MESHES:
            break
    return rows


def raster_size(span_x: float, span_z: float) -> tuple[int, int]:
    """Raster dimensions for a world area, preserving its aspect."""
    if span_x >= span_z:
        return LONG_EDGE, max(1, round(LONG_EDGE * span_z / span_x))
    return max(1, round(LONG_EDGE * span_x / span_z)), LONG_EDGE


def _read_cluster(path: Path):
    """Vertices and triangles of one exported cluster OBJ.

    Vertex normals are deliberately not read: the published scan view only
    needs triangle positions for its orthographic world-Y depth pass.
    """
    vertices = []
    faces = []
    try:
        stream = path.open("r", encoding="utf-8", errors="strict")
    except OSError:
        return None
    with stream:
        for line in stream:
            if line.startswith("v "):
                parts = line.split()
                try:
                    vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except (IndexError, ValueError):
                    return None
            elif line.startswith("f "):
                corners = []
                for token in line.split()[1:4]:
                    try:
                        corners.append(int(token.split("/")[0]) - 1)
                    except ValueError:
                        corners = []
                        break
                if len(corners) == 3:
                    faces.append(tuple(corners))
    return vertices, faces


def _read_textured_mesh(path: Path):
    """Read OBJ positions, UVs, and their triangle-corner indices."""
    vertices = []
    texcoords = []
    faces = []
    try:
        stream = path.open("r", encoding="utf-8", errors="strict")
    except OSError:
        return None
    with stream:
        for line in stream:
            if line.startswith("v "):
                parts = line.split()
                try:
                    vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except (IndexError, ValueError):
                    return None
            elif line.startswith("vt "):
                parts = line.split()
                try:
                    texcoords.append((float(parts[1]), float(parts[2])))
                except (IndexError, ValueError):
                    return None
            elif line.startswith("f "):
                vertex_indices = []
                texture_indices = []
                for token in line.split()[1:4]:
                    fields = token.split("/")
                    try:
                        vertex_indices.append(int(fields[0]) - 1)
                        texture_indices.append(int(fields[1]) - 1 if len(fields) > 1 and fields[1] else -1)
                    except ValueError:
                        vertex_indices = []
                        break
                if len(vertex_indices) == 3:
                    faces.append((tuple(vertex_indices), tuple(texture_indices)))
    return vertices, texcoords, faces


def rasterise_vertices(clusters, lod, fit, bounds, mesh_files, width, height):
    """Project actual OBJ vertices, preserving their irregular scan spacing."""
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    depth = [NO_HIT] * (width * height)
    used = []
    vertex_count = 0
    size = cell_size(lod)
    for cluster in clusters:
        suffix = f"{int(cluster['pathId']) & ((1 << 64) - 1):X}"
        path = mesh_files.get(suffix)
        if path is None:
            continue
        parsed = _read_cluster(path)
        if not parsed:
            continue
        raw_vertices, faces = parsed
        translate_x = fit["originX"] + cluster["i"] * size + size / 2
        translate_z = fit["originZ"] + cluster["j"] * size + size / 2
        landed = 0
        for obj_x, obj_y, obj_z in raw_vertices:
            world_x = translate_x - obj_x
            world_z = translate_z + obj_z
            px = round((world_x - bounds["minX"]) / span_x * (width - 1))
            py = round((bounds["maxZ"] - world_z) / span_z * (height - 1))
            if not (0 <= px < width and 0 <= py < height):
                continue
            index = py * width + px
            depth[index] = max(depth[index], obj_y)
            landed += 1
        if landed:
            vertex_count += landed
            used.append({
                "pathId": cluster["pathId"],
                "name": cluster["name"],
                "vertices": landed,
                "triangles": len(faces),
            })
    return depth, used, vertex_count


def render_hlod_point_samples(
    level_id: str,
    clusters: list[dict],
    lod: int,
    fit: dict,
    bounds: dict[str, float],
    mesh_files: dict[str, Path],
    width: int,
    height: int,
    output_root: Path,
    bindings: dict[int, dict] | None = None,
) -> dict | None:
    """Preserve every projected HLOD vertex so height cuts reveal lower geometry."""
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    size = cell_size(lod)
    samples: dict[int, list[tuple[float, tuple[int, int, int, int] | None]]] = {}
    used_textures: set[str] = set()
    epsilon = 1e-4

    def add(index: int, world_y: float, color: tuple[int, int, int, int] | None) -> None:
        rows = samples.setdefault(index, [])
        for position, (existing_y, existing_color) in enumerate(rows):
            if abs(existing_y - world_y) <= epsilon:
                if existing_color is None and color is not None:
                    rows[position] = (world_y, color)
                return
        rows.append((world_y, color))

    for cluster in clusters:
        suffix = f"{int(cluster['pathId']) & ((1 << 64) - 1):X}"
        path = mesh_files.get(suffix)
        if path is None:
            continue
        texture = _texture_render_source((bindings or {}).get(cluster.get("pathId")))
        parsed = _read_textured_mesh(path) if texture else _read_cluster(path)
        if not parsed:
            continue
        translate_x = fit["originX"] + cluster["i"] * size + size / 2
        translate_z = fit["originZ"] + cluster["j"] * size + size / 2
        if texture:
            raw_vertices, texcoords, faces = parsed
            used_textures.add(texture["textureRel"])
            corners = []
            for vertex_face, texture_face in faces:
                corners.extend(zip(vertex_face, texture_face))
        else:
            raw_vertices, _faces = parsed
            texcoords = []
            corners = [(index, -1) for index in range(len(raw_vertices))]
        for vertex_index, texture_index in corners:
            try:
                obj_x, obj_y, obj_z = raw_vertices[vertex_index]
            except IndexError:
                continue
            world_x = translate_x - obj_x
            world_z = translate_z + obj_z
            px = round((world_x - bounds["minX"]) / span_x * (width - 1))
            py = round((bounds["maxZ"] - world_z) / span_z * (height - 1))
            if not (0 <= px < width and 0 <= py < height):
                continue
            color = None
            if texture and texture_index >= 0:
                try:
                    u, v = texcoords[texture_index]
                except IndexError:
                    pass
                else:
                    color = _sample_texture(texture, u * texture["scale"][0] + texture["offset"][0],
                                            v * texture["scale"][1] + texture["offset"][1])
                    if color is None:
                        continue
            add(py * width + px, obj_y, color)

    all_heights = [world_y for rows in samples.values() for world_y, _color in rows]
    if not all_heights:
        return None
    low, high = min(all_heights), max(all_heights)
    span = max(high - low, 1.0)
    top_depth = [NO_HIT] * (width * height)
    top_colors = bytearray(width * height * 4)
    records = bytearray(b"MRPS" + struct.pack("<HHII", 1, 12, width, height))
    record_count = 0
    for index in sorted(samples):
        ordered = sorted(samples[index], key=lambda row: row[0])
        for world_y, recovered_color in ordered:
            tint = (world_y - low) / span
            color = recovered_color or (*[max(18, round(channel * 0.62)) for channel in elevation_color(tint)], 225)
            records.extend(struct.pack("<IfBBBB", index, world_y, *color))
            record_count += 1
        top_y, top_color = ordered[-1]
        tint = (top_y - low) / span
        color = top_color or (*[max(18, round(channel * 0.62)) for channel in elevation_color(tint)], 225)
        top_depth[index] = top_y
        offset = index * 4
        top_colors[offset:offset + 4] = bytes((*color[:3], 225))

    output_root.mkdir(parents=True, exist_ok=True)
    image_name = f"{level_id}_hlod_vertex_points.png"
    write_png(
        output_root / image_name, width, height,
        [bytes(top_colors[row * width * 4:(row + 1) * width * 4]) for row in range(height)],
    )
    sample_name = f"{level_id}_hlod_vertex_points.samples"
    (output_root / sample_name).write_bytes(records)
    height_mask = render_point_height_mask(
        level_id, top_depth, width, height, output_root,
        image_suffix="hlod_vertex_points_height_mask", sampling="all",
    )
    return {
        "src": f"render/{image_name}",
        "method": "orthographic_hlod_layered_mesh_vertex_samples",
        "defaultOpacity": 0.72,
        "pointDensity": 1.0,
        "heightMask": height_mask,
        "sampleSet": {
            "src": f"render/{sample_name}",
            "encoding": "mrps_v1_le_u32_pixel_f32_height_rgba8",
            "width": width,
            "height": height,
            "recordCount": record_count,
            "pixelCount": len(samples),
            "elevationRange": {"min": low, "max": high},
            "dedupeEpsilon": epsilon,
        },
        "baseColorTextures": sorted(used_textures),
        "boundary": (
            "Every projected OBJ vertex is retained by pixel and world Y. The default PNG shows the highest sample; "
            "the sample sidecar lets a bounded height filter reveal the next lower sample without changing surface depth."
        ),
    }


def rasterise_streaming_depth(streaming, bounds, width, height, bindings=None, detail_props_only=False):
    """Rasterize exact static instances, sampling proven material base textures."""
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    depth = [NO_HIT] * (width * height)
    detail_depth = [NO_HIT] * (width * height)
    albedo = bytearray(width * height * 4)
    detail_albedo = bytearray(width * height * 4)
    cache: dict[Path, tuple[list, list, list] | None] = {}
    used_instances = 0
    textured_instances = 0
    triangles = 0
    textured_triangles = 0
    detail_triangles = 0
    excluded_detail_triangles = 0
    vertex_samples = 0
    used_textures: set[str] = set()
    export_root = (ROOT / "export_full").resolve()

    for instance in streaming:
        matrix = instance.get("matrixColumnMajor")
        meshes = _instance_meshes(instance)
        if not meshes or not isinstance(matrix, list) or len(matrix) != 16:
            continue
        instance_drawn = False
        instance_textured = False
        for mesh in meshes:
            path = (ROOT / str(mesh.get("obj") or "")).resolve()
            try:
                path.relative_to(export_root)
            except ValueError:
                continue
            if path not in cache:
                cache[path] = _read_textured_mesh(path)
            parsed = cache[path]
            if not parsed:
                continue
            raw_vertices, texcoords, faces = parsed
            structural_detail = _is_detail_structural(instance, mesh)
            binding = (bindings or {}).get(_asset_rel_from_obj(mesh.get("obj")))
            texture = _texture_render_source(binding)
            # AnimeStudio's OBJ conversion mirrors Unity X. Undo that conversion
            # before applying the recovered Unity column-major instance matrix.
            vertices = []
            for obj_x, obj_y, obj_z in raw_vertices:
                local_x = -obj_x
                vertices.append((
                    matrix[0] * local_x + matrix[4] * obj_y + matrix[8] * obj_z + matrix[12],
                    matrix[1] * local_x + matrix[5] * obj_y + matrix[9] * obj_z + matrix[13],
                    matrix[2] * local_x + matrix[6] * obj_y + matrix[10] * obj_z + matrix[14],
                ))
            drawn = 0
            for vertex_face, texture_face in faces:
                try:
                    points = [vertices[index] for index in vertex_face]
                except IndexError:
                    continue
                authored_detail_prop = _is_detail_prop(instance, mesh)
                detail_face = (
                    authored_detail_prop
                    if detail_props_only else
                    not structural_detail
                    and (authored_detail_prop or not _is_large_horizontal_triangle(points))
                )
                if detail_face:
                    detail_triangles += 1
                else:
                    excluded_detail_triangles += 1
                uvs = None
                if texture and min(texture_face) >= 0:
                    try:
                        uvs = [texcoords[index] for index in texture_face]
                    except IndexError:
                        uvs = None
                screen_x = [(point[0] - bounds["minX"]) / span_x * width for point in points]
                screen_y = [(bounds["maxZ"] - point[2]) / span_z * height for point in points]
                x0, x1 = max(0, int(min(screen_x))), min(width - 1, int(max(screen_x)) + 1)
                y0, y1 = max(0, int(min(screen_y))), min(height - 1, int(max(screen_y)) + 1)
                if x0 > x1 or y0 > y1:
                    continue
                area = ((screen_y[1] - screen_y[2]) * (screen_x[0] - screen_x[2])
                        + (screen_x[2] - screen_x[1]) * (screen_y[0] - screen_y[2]))
                if abs(area) < 1e-12:
                    continue
                drawn += 1
                if uvs is not None:
                    textured_triangles += 1
                    used_textures.add(texture["textureRel"])
                for pixel_y in range(y0, y1 + 1):
                    sample_y = pixel_y + 0.5
                    base = pixel_y * width
                    for pixel_x in range(x0, x1 + 1):
                        sample_x = pixel_x + 0.5
                        w0 = ((screen_y[1] - screen_y[2]) * (sample_x - screen_x[2])
                              + (screen_x[2] - screen_x[1]) * (sample_y - screen_y[2])) / area
                        w1 = ((screen_y[2] - screen_y[0]) * (sample_x - screen_x[2])
                              + (screen_x[0] - screen_x[2]) * (sample_y - screen_y[2])) / area
                        w2 = 1.0 - w0 - w1
                        if min(w0, w1, w2) < -EDGE_EPSILON:
                            continue
                        elevation = w0 * points[0][1] + w1 * points[1][1] + w2 * points[2][1]
                        index = base + pixel_x
                        wins_full = elevation > depth[index]
                        wins_detail = detail_face and elevation > detail_depth[index]
                        if not wins_full and not wins_detail:
                            continue
                        sampled = None
                        if uvs is not None:
                            scale_u, scale_v = texture["scale"]
                            offset_u, offset_v = texture["offset"]
                            u = (w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]) * scale_u + offset_u
                            v = (w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]) * scale_v + offset_v
                            texture_x = min(texture["width"] - 1, int((u % 1.0) * texture["width"]))
                            texture_y = min(texture["height"] - 1, int(((1.0 - v) % 1.0) * texture["height"]))
                            texture_offset = (texture_y * texture["width"] + texture_x) * 4
                            source = texture["pixels"]
                            alpha = source[texture_offset + 3]
                            if alpha / 255 < texture["cutoff"]:
                                continue
                            tint = texture["tint"]
                            sampled = (
                                min(255, round(source[texture_offset] * tint[0])),
                                min(255, round(source[texture_offset + 1] * tint[1])),
                                min(255, round(source[texture_offset + 2] * tint[2])),
                                alpha,
                            )
                        if wins_full:
                            depth[index] = elevation
                            color_offset = index * 4
                            if sampled:
                                albedo[color_offset:color_offset + 4] = bytes(sampled)
                                instance_textured = True
                            else:
                                albedo[color_offset:color_offset + 4] = b"\0\0\0\0"
                        if wins_detail:
                            detail_depth[index] = elevation
                            color_offset = index * 4
                            if sampled:
                                detail_albedo[color_offset:color_offset + 4] = bytes(sampled)
                            else:
                                detail_albedo[color_offset:color_offset + 4] = b"\0\0\0\0"
            if drawn:
                instance_drawn = True
                triangles += drawn
        if instance_drawn:
            used_instances += 1
        if instance_textured:
            textured_instances += 1
    textured_pixels = sum(1 for index in range(3, len(albedo), 4) if albedo[index])
    return {
        "depth": depth,
        "detailDepth": detail_depth,
        "albedo": albedo,
        "detailAlbedo": detail_albedo,
        "usedInstances": used_instances,
        "texturedInstances": textured_instances,
        "triangles": triangles,
        "texturedTriangles": textured_triangles,
        "detailTriangles": detail_triangles,
        "excludedDetailTriangles": excluded_detail_triangles,
        "vertexSamples": vertex_samples,
        "texturedPixels": textured_pixels,
        "usedTextures": sorted(used_textures),
    }


def rasterise_depth(
    clusters, lod, fit, bounds, mesh_files, width, height,
    bindings: dict[int, dict] | None = None,
    material_colors: bytearray | None = None,
):
    """Render the level's triangles into a top-down height field.

    This is an orthographic depth pass from directly above: every triangle is
    rasterised with a depth test on world Y so the surface nearest the camera
    wins. The result is a digital elevation model of the level, which is what
    the shading below works from.
    """
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    depth = [NO_HIT] * (width * height)
    used = []
    triangles = 0
    size = cell_size(lod)

    for cluster in clusters:
        suffix = f"{int(cluster['pathId']) & ((1 << 64) - 1):X}"
        path = mesh_files.get(suffix)
        if path is None:
            continue
        texture = _texture_render_source((bindings or {}).get(cluster.get("pathId")))
        parsed = _read_textured_mesh(path) if texture else _read_cluster(path)
        if not parsed:
            continue
        if texture:
            raw_vertices, texcoords, textured_faces = parsed
            faces = [row[0] for row in textured_faces]
            texture_faces = [row[1] for row in textured_faces]
        else:
            raw_vertices, faces = parsed
            texcoords = []
            texture_faces = [(-1, -1, -1)] * len(faces)
        # The cluster's vertices are centred on its own origin, so its world
        # position is the centre of the grid cell its name declares. AnimeStudio
        # writes OBJ right-handed, so X is mirrored back onto Unity's world.
        translate_x = fit["originX"] + cluster["i"] * size + size / 2
        translate_z = fit["originZ"] + cluster["j"] * size + size / 2
        vertices = [(translate_x - v[0], v[1], translate_z + v[2]) for v in raw_vertices]

        drawn = 0
        for face_index, face in enumerate(faces):
            try:
                points = [vertices[index] for index in face]
            except IndexError:
                continue
            screen_x = [(p[0] - bounds["minX"]) / span_x * width for p in points]
            screen_y = [(bounds["maxZ"] - p[2]) / span_z * height for p in points]
            x0 = max(0, int(min(screen_x)))
            x1 = min(width - 1, int(max(screen_x)) + 1)
            y0 = max(0, int(min(screen_y)))
            y1 = min(height - 1, int(max(screen_y)) + 1)
            if x0 > x1 or y0 > y1:
                continue
            area = ((screen_y[1] - screen_y[2]) * (screen_x[0] - screen_x[2])
                    + (screen_x[2] - screen_x[1]) * (screen_y[0] - screen_y[2]))
            if abs(area) < 1e-12:
                continue
            drawn += 1
            for pixel_y in range(y0, y1 + 1):
                sample_y = pixel_y + 0.5
                base = pixel_y * width
                for pixel_x in range(x0, x1 + 1):
                    sample_x = pixel_x + 0.5
                    w0 = ((screen_y[1] - screen_y[2]) * (sample_x - screen_x[2])
                          + (screen_x[2] - screen_x[1]) * (sample_y - screen_y[2])) / area
                    if w0 < -EDGE_EPSILON:
                        continue
                    w1 = ((screen_y[2] - screen_y[0]) * (sample_x - screen_x[2])
                          + (screen_x[0] - screen_x[2]) * (sample_y - screen_y[2])) / area
                    if w1 < -EDGE_EPSILON:
                        continue
                    w2 = 1.0 - w0 - w1
                    if w2 < -EDGE_EPSILON:
                        continue
                    elevation = w0 * points[0][1] + w1 * points[1][1] + w2 * points[2][1]
                    index = base + pixel_x
                    if elevation > depth[index]:
                        sampled = None
                        texture_face = texture_faces[face_index]
                        if texture and min(texture_face) >= 0:
                            try:
                                uvs = [texcoords[uv_index] for uv_index in texture_face]
                            except IndexError:
                                uvs = None
                            if uvs:
                                scale_u, scale_v = texture["scale"]
                                offset_u, offset_v = texture["offset"]
                                u = (w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]) * scale_u + offset_u
                                v = (w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]) * scale_v + offset_v
                                texture_x = min(texture["width"] - 1, int((u % 1.0) * texture["width"]))
                                texture_y = min(texture["height"] - 1, int(((1.0 - v) % 1.0) * texture["height"]))
                                texture_offset = (texture_y * texture["width"] + texture_x) * 4
                                source = texture["pixels"]
                                alpha = source[texture_offset + 3]
                                if alpha / 255 < texture["cutoff"]:
                                    continue
                                tint = texture["tint"]
                                sampled = (
                                    min(255, round(source[texture_offset] * tint[0])),
                                    min(255, round(source[texture_offset + 1] * tint[1])),
                                    min(255, round(source[texture_offset + 2] * tint[2])),
                                    alpha,
                                )
                        depth[index] = elevation
                        if material_colors is not None:
                            color_offset = index * 4
                            material_colors[color_offset:color_offset + 4] = bytes(sampled or (0, 0, 0, 0))
        if drawn:
            triangles += drawn
            used.append({
                "pathId": cluster["pathId"],
                "name": cluster["name"],
                "triangles": drawn,
                "materialColor": bool(texture),
                "baseColorTexture": texture["textureRel"] if texture else None,
            })
    return depth, used, triangles


def grow_surface(depth, width, height, rounds=FILL_ROUNDS):
    """Grow the height field a few pixels into the gaps between props.

    HLOD publishes cliffs and props but no ground, so a raw depth pass is a
    cloud of disconnected shards. Growing the surface outward joins them into
    the landform they sit on. Only the frontier is visited each round, so this
    stays proportional to the coverage edge rather than to the whole image.
    """
    filled = list(depth)
    real = [value > NO_HIT for value in depth]
    frontier = set()
    for index, covered in enumerate(real):
        if not covered:
            continue
        y, x = divmod(index, width)
        for dy in (-1, 0, 1):
            ny = y + dy
            if ny < 0 or ny >= height:
                continue
            for dx in (-1, 0, 1):
                nx = x + dx
                if 0 <= nx < width and filled[ny * width + nx] <= NO_HIT:
                    frontier.add(ny * width + nx)

    for _ in range(rounds):
        if not frontier:
            break
        updates = {}
        for index in frontier:
            y, x = divmod(index, width)
            total = 0.0
            count = 0
            for dy in (-1, 0, 1):
                ny = y + dy
                if ny < 0 or ny >= height:
                    continue
                for dx in (-1, 0, 1):
                    nx = x + dx
                    if nx < 0 or nx >= width:
                        continue
                    value = filled[ny * width + nx]
                    if value > NO_HIT:
                        total += value
                        count += 1
            if count:
                updates[index] = total / count
        if not updates:
            break
        next_frontier = set()
        for index, value in updates.items():
            filled[index] = value
            y, x = divmod(index, width)
            for dy in (-1, 0, 1):
                ny = y + dy
                if ny < 0 or ny >= height:
                    continue
                for dx in (-1, 0, 1):
                    nx = x + dx
                    if 0 <= nx < width and filled[ny * width + nx] <= NO_HIT:
                        next_frontier.add(ny * width + nx)
        frontier = next_frontier
    return filled, real


def _blur_axis(values, mask, width, height, radius, horizontal):
    """One separable box-blur pass over covered pixels, with a sliding window."""
    out = list(values)
    outer, inner = (height, width) if horizontal else (width, height)
    for a in range(outer):
        def at(b):
            return a * width + b if horizontal else b * width + a

        total = 0.0
        count = 0
        for b in range(min(radius, inner - 1) + 1):
            index = at(b)
            if mask[index]:
                total += values[index]
                count += 1
        for b in range(inner):
            index = at(b)
            if mask[index] and count:
                out[index] = total / count
            drop = b - radius
            if drop >= 0:
                dropped = at(drop)
                if mask[dropped]:
                    total -= values[dropped]
                    count -= 1
            add = b + radius + 1
            if add < inner:
                added = at(add)
                if mask[added]:
                    total += values[added]
                    count += 1
    return out


def smooth_surface(values, mask, width, height, radius=BLUR_RADIUS, passes=BLUR_PASSES):
    """Blur the height field so shading follows landforms, not single props."""
    current = list(values)
    for _ in range(passes):
        current = _blur_axis(current, mask, width, height, radius, True)
        current = _blur_axis(current, mask, width, height, radius, False)
    return current


def hillshade(dem, mask, width, height):
    """Standard DEM hillshade from the smoothed height field's own gradient."""
    azimuth = math.radians(360.0 - HILLSHADE_AZIMUTH + 90.0)
    altitude = math.radians(HILLSHADE_ALTITUDE)
    sin_alt = math.sin(altitude)
    cos_alt = math.cos(altitude)
    out = [0.0] * (width * height)
    for y in range(height):
        row = y * width
        up = max(0, y - 1) * width
        down = min(height - 1, y + 1) * width
        for x in range(width):
            index = row + x
            if not mask[index]:
                continue
            left = max(0, x - 1)
            right = min(width - 1, x + 1)
            dzdx = (dem[row + right] - dem[row + left]) * 0.5 * HILLSHADE_SCALE
            dzdy = (dem[down + x] - dem[up + x]) * 0.5 * HILLSHADE_SCALE
            slope = math.atan(math.sqrt(dzdx * dzdx + dzdy * dzdy))
            aspect = math.atan2(dzdy, -dzdx)
            value = sin_alt * math.cos(slope) + cos_alt * math.sin(slope) * math.cos(azimuth - aspect)
            out[index] = max(0.0, min(1.0, value))
    return out


def render_elevation_underlay(
    level_id: str,
    depth: list[float],
    width: int,
    height: int,
    output_root: Path,
    image_suffix: str = "hlod_elevation",
    source_label: str = "HLOD triangle depth",
    material_colors: bytearray | bytes | None = None,
) -> dict | None:
    """Restore a neutral grayscale DEM below a point scan.

    The elevation layer is analytical rather than an authored surface, so it
    must never inherit material colors. Material/texture evidence remains
    available on the separate surface and point layers.
    """
    grown, real = grow_surface(depth, width, height)
    mask = [value > NO_HIT for value in grown]
    if not any(mask):
        return None
    dem = smooth_surface(grown, mask, width, height)
    lighting = hillshade(dem, mask, width, height)
    covered = [dem[index] for index, present in enumerate(mask) if present]
    low, high = min(covered), max(covered)
    span = max(high - low, 1.0)
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            index = y * width + x
            if not mask[index]:
                row.extend((255, 255, 255, 0))
                continue
            tint = (dem[index] - low) / span
            shade = round((54 + 154 * (1.0 - tint)) * (0.84 + 0.16 * lighting[index]))
            shade = max(24, min(224, shade))
            row.extend((shade, shade, shade, 225 if real[index] else 165))
        rows.append(bytes(row))
    image_name = f"{level_id}_{image_suffix}.png"
    write_png(output_root / image_name, width, height, rows)
    return {
        "src": f"render/{image_name}",
        "method": "orthographic_depth_pass_grayscale_hillshade",
        "defaultOpacity": 1.0,
        "hillshade": {
            "azimuth": HILLSHADE_AZIMUTH,
            "altitude": HILLSHADE_ALTITUDE,
            "scale": HILLSHADE_SCALE,
            "growRounds": FILL_ROUNDS,
            "blurRadius": BLUR_RADIUS,
            "blurPasses": BLUR_PASSES,
        },
        "realPixelRatio": round(sum(real) / (width * height), 4),
        "coveredPixelRatio": round(sum(mask) / (width * height), 4),
        "elevationRange": {"min": low, "max": high},
        "boundary": (
            f"Recovered {source_label} only. This analytical elevation layer is intentionally grayscale; "
            "material color remains confined to the separate surface/point layers. Gap growth is visibly "
            "translucent and does not claim authored ground geometry."
        ),
    }


def render_sparse_point_elevation(
    level_id: str,
    depth: list[float],
    width: int,
    height: int,
    output_root: Path,
) -> dict | None:
    """Render exact point footprints as grayscale elevation without inventing a surface."""
    real = [value > NO_HIT for value in depth]
    covered = [value for value in depth if value > NO_HIT]
    if not covered:
        return None
    low, high = min(covered), max(covered)
    span = max(high - low, 1.0)
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            value = depth[y * width + x]
            if value <= NO_HIT:
                row.extend((255, 255, 255, 0))
                continue
            shade = max(32, min(224, round(224 - 176 * ((value - low) / span))))
            row.extend((shade, shade, shade, 225))
        rows.append(bytes(row))
    image_name = f"{level_id}_registry_elevation_points.png"
    write_png(output_root / image_name, width, height, rows)
    ratio = round(sum(real) / (width * height), 4)
    return {
        "src": f"render/{image_name}",
        "method": "exact_registry_transform_grayscale_elevation_points",
        "defaultOpacity": 1.0,
        "realPixelRatio": ratio,
        "coveredPixelRatio": ratio,
        "elevationRange": {"min": low, "max": high},
        "boundary": (
            "Grayscale elevation is drawn only on the visible footprints of exact published registry/quest "
            "X/Y/Z points. Transparent gaps remain empty; no growth, smoothing, triangulation, or inferred "
            "terrain is applied."
        ),
    }


def refresh_water_overlay_manifests(
    level_ids: list[str],
    sectors_by_scene: dict[str, list[dict]],
    texture_files: dict[str, Path],
    output_root: Path,
) -> int:
    """Refresh only derived water layers in already-rendered map manifests."""
    refreshed = 0
    for level_id in level_ids:
        manifest_path = output_root / f"{level_id}_hlod_grid_inferred.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"water-only refresh requires existing manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bounds = manifest.get("worldBounds")
        if not isinstance(bounds, dict):
            raise RuntimeError(f"water-only refresh requires worldBounds: {manifest_path}")
        projection = manifest.get("projectionSource") or {}
        scene_id = water_scene_id(level_id, projection.get("sceneId"))
        overlay = render_water_overlay(
            level_id, scene_id, bounds, sectors_by_scene, texture_files, output_root,
        )
        if overlay is None:
            stale_image = output_root / f"{level_id}_water.png"
            if stale_image.is_file():
                stale_image.unlink()
        manifest["waterOverlay"] = overlay
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        refreshed += 1
    return refreshed


def elevation_color(tint: float) -> tuple[int, int, int]:
    """A restrained terrain palette for geometry with no proven material binding."""
    stops = ((91, 126, 116), (167, 151, 105), (151, 104, 82))
    value = max(0.0, min(1.0, tint)) * 2
    left = min(1, int(value))
    mix = value - left
    return tuple(round(stops[left][channel] * (1 - mix) + stops[left + 1][channel] * mix) for channel in range(3))


def render_depth_surface(
    level_id: str,
    depth: list[float],
    width: int,
    height: int,
    output_root: Path,
    image_suffix: str,
    material_colors: bytearray | bytes | None = None,
) -> dict | None:
    """Render exact depth hits as a continuous height-shaded surface layer."""
    real = [value > NO_HIT for value in depth]
    covered = [value for value in depth if value > NO_HIT]
    if not covered:
        return None
    low, high = min(covered), max(covered)
    span = max(high - low, 1.0)
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            index = y * width + x
            if not real[index]:
                row.extend((255, 255, 255, 0))
                continue
            tint = (depth[index] - low) / span
            color_offset = index * 4
            if material_colors is not None and len(material_colors) > color_offset + 3 and material_colors[color_offset + 3]:
                base = tuple(material_colors[color_offset + channel] for channel in range(3))
                alpha = material_colors[color_offset + 3]
            else:
                base = elevation_color(tint)
                light = 0.72 + 0.24 * (1.0 - tint)
                base = tuple(min(255, round(channel * light)) for channel in base)
                alpha = 225
            row.extend((*base, alpha))
        rows.append(bytes(row))
    image_name = f"{level_id}_{image_suffix}.png"
    write_png(output_root / image_name, width, height, rows)
    return {
        "src": f"render/{image_name}",
        "method": "orthographic_exact_depth_material_color_or_elevation_palette_surface",
        "defaultOpacity": 1.0,
        "realPixelRatio": round(sum(real) / (width * height), 4),
        "elevationRange": {"min": low, "max": high},
        "boundary": "Only exact triangle depth hits are filled; gaps remain transparent.",
    }


def render_depth_point_overlay(
    level_id: str,
    depth: list[float],
    width: int,
    height: int,
    output_root: Path,
    image_suffix: str,
    material_colors: bytearray | bytes | None = None,
) -> dict | None:
    """Render a transparent colored point scan from exact triangle depth hits."""
    covered = [value for value in depth if value > NO_HIT]
    if not covered:
        return None
    low, high = min(covered), max(covered)
    span = max(high - low, 1.0)
    emitted = 0
    rows = []
    for y in range(height):
        row = bytearray(width * 4)
        for x in range(width):
            index = y * width + x
            value = depth[index]
            if value <= NO_HIT or ((x * 37 + y * 17) % 11) >= 6:
                continue
            tint = (value - low) / span
            color_offset = index * 4
            if material_colors is not None and len(material_colors) > color_offset + 3 and material_colors[color_offset + 3]:
                base = tuple(material_colors[color_offset + channel] for channel in range(3))
            else:
                base = elevation_color(tint)
                base = tuple(max(18, round(channel * 0.68)) for channel in base)
            offset = x * 4
            row[offset:offset + 4] = bytes((*base, 225))
            emitted += 1
        rows.append(bytes(row))
    image_name = f"{level_id}_{image_suffix}.png"
    write_png(output_root / image_name, width, height, rows)
    height_mask = render_point_height_mask(
        level_id, depth, width, height, output_root,
        image_suffix=f"{image_suffix}_height_mask",
        sampling="streaming",
    )
    return {
        "src": f"render/{image_name}",
        "method": "orthographic_exact_depth_material_color_or_elevation_palette_points",
        "defaultOpacity": 0.72,
        "pointDensity": 6 / 11,
        "pointPixelCount": emitted,
        "elevationRange": {"min": low, "max": high},
        "heightMask": height_mask,
        "boundary": (
            "Only exact triangle depth-hit pixels can emit points; exact exported material color is retained "
            "where available and unresolved pixels use the elevation palette. No geometry is grown."
        ),
    }


def render_point_height_mask(
    level_id: str,
    depth: list[float],
    width: int,
    height: int,
    output_root: Path,
    image_suffix: str,
    sampling: str,
) -> dict | None:
    """Encode exact emitted-point height as opaque unsigned 16-bit RG pixels."""
    covered = [value for value in depth if value > NO_HIT]
    if not covered:
        return None
    low, high = min(covered), max(covered)
    span = max(high - low, 1e-9)
    rows = []
    encoded_pixels = 0
    for y in range(height):
        row = bytearray(width * 4)
        for x in range(width):
            index = y * width + x
            value = depth[index]
            if value <= NO_HIT:
                continue
            sample = (x * 37 + y * 17) % 11
            if sampling == "streaming" and sample >= 6:
                continue
            if sampling == "hlod_depth" and sample >= 8:
                continue
            encoded = max(0, min(65535, round((value - low) / span * 65535)))
            offset = x * 4
            row[offset:offset + 4] = bytes((encoded >> 8, encoded & 255, 0, 255))
            encoded_pixels += 1
        rows.append(bytes(row))
    if not encoded_pixels:
        return None
    image_name = f"{level_id}_{image_suffix}.png"
    write_png(output_root / image_name, width, height, rows)
    return {
        "src": f"render/{image_name}",
        "encoding": "uint16_rg_normalized_world_y",
        "elevationRange": {"min": low, "max": high},
        "pointPixelCount": encoded_pixels,
        "boundary": "Opaque pixels correspond exactly to emitted point pixels; RG stores normalized world Y.",
    }


def render_level(
    level_id: str,
    clusters: list[dict],
    lod: int,
    fit: dict,
    bounds: dict[str, float],
    mesh_files: dict[str, Path],
    output_root: Path,
    scan_mode: str | None = None,
    bindings: dict[int, dict] | None = None,
) -> dict | None:
    """Render recovered HLOD geometry as a dense orthographic point cloud."""
    width, height = raster_size(bounds["maxX"] - bounds["minX"], bounds["maxZ"] - bounds["minZ"])
    mode = scan_mode or LEVEL_SCAN_MODES.get(level_id, "depth_points")
    material_colors = bytearray(width * height * 4) if bindings else None
    if mode == "mesh_vertices":
        depth, used, primitive_count = rasterise_vertices(
            clusters, lod, fit, bounds, mesh_files, width, height
        )
        triangles = 0
    else:
        depth, used, triangles = rasterise_depth(
            clusters, lod, fit, bounds, mesh_files, width, height,
            bindings=bindings, material_colors=material_colors,
        )
        primitive_count = triangles
    if not used:
        return None

    real = [value > NO_HIT for value in depth]
    covered = [depth[index] for index in range(len(depth)) if real[index]]
    if not covered:
        return None
    low, high = min(covered), max(covered)
    span = max(high - low, 1.0)

    rows = [bytearray(width * 4) for _ in range(height)]
    for y in range(height):
        row = rows[y]
        base_index = y * width
        for x in range(width):
            index = base_index + x
            if not real[index]:
                continue
            # The screenshot-era vertex scan is irregular because its samples
            # are mesh vertices. The depth mode retains the later deterministic
            # 8/11 screen-door alternative for explicit comparisons.
            if mode == "depth_points" and ((x * 37 + y * 17) % 11) >= 8:
                continue
            tint = (depth[index] - low) / span
            base = elevation_color(tint)
            light = 0.62 if mode == "mesh_vertices" else 0.72
            offset = x * 4
            row[offset:offset + 4] = bytes((
                *[max(18, round(channel * light)) for channel in base],
                225 if mode == "mesh_vertices" else 215,
            ))

    output_root.mkdir(parents=True, exist_ok=True)
    image_name = f"{level_id}_hlod_grid_inferred.png"
    write_png(output_root / image_name, width, height, rows)
    if mode == "mesh_vertices":
        surface_depth, surface_used, surface_triangles = rasterise_depth(
            clusters, lod, fit, bounds, mesh_files, width, height,
            bindings=bindings, material_colors=material_colors,
        )
    else:
        surface_depth, surface_used, surface_triangles = depth, used, triangles
    elevation_underlay = render_elevation_underlay(
        level_id, surface_depth, width, height, output_root
    ) if surface_used else None
    surface_render = render_depth_surface(
        level_id, surface_depth, width, height, output_root, "hlod_surface",
        material_colors=material_colors,
    ) if surface_used else None
    textured_pixels = sum(
        1 for index in range(3, len(material_colors or ()), 4)
        if material_colors[index]
    )
    layered_point_overlay = render_hlod_point_samples(
        level_id, clusters, lod, fit, bounds, mesh_files, width, height, output_root,
        bindings=bindings,
    )
    point_cloud_overlay = layered_point_overlay or {
        "src": f"render/{image_name}",
        "method": "orthographic_hlod_mesh_vertex_scan" if mode == "mesh_vertices" else "orthographic_hlod_depth_black_point_density",
        "defaultOpacity": 0.72,
        "pointDensity": 1.0 if mode == "mesh_vertices" else 8 / 11,
        "heightMask": render_point_height_mask(
            level_id, depth, width, height, output_root,
            image_suffix="hlod_height_mask",
            sampling="all" if mode == "mesh_vertices" else "hlod_depth",
        ),
        "boundary": (
            "Only recovered OBJ vertices emit points."
            if mode == "mesh_vertices" else
            "Only pixels hit by recovered HLOD triangles can emit points."
        ),
    }
    size = cell_size(lod)
    scene_meshes = _scene_meshes(used, mesh_files, lod=lod, fit=fit)
    result = {
        "schemaVersion": 3,
        "status": "inferred_hlod_textured_preview" if textured_pixels else "inferred_hlod_grid_preview",
        "levelId": level_id,
        "src": surface_render["src"] if surface_render else f"render/{image_name}",
        "elevationUnderlay": elevation_underlay,
        "pointCloudOverlay": point_cloud_overlay if surface_render else None,
        "surfaceRender": surface_render,
        "worldBounds": bounds,
        "coordinateSystem": "Unity world X/Z; image top is +Z",
        "hlodLevel": lod,
        "render": {
            "method": "orthographic_hlod_mesh_vertex_scan" if mode == "mesh_vertices" else "orthographic_hlod_depth_black_point_density",
            "shading": (
                "actual OBJ vertices projected orthographically, with world-Y encoded by the bounded elevation palette"
                if mode == "mesh_vertices" else
                "the 87b60f49 screen-door sample of real HLOD depth pixels, colored by the bounded elevation palette"
            ),
            "pointDensity": 1.0 if mode == "mesh_vertices" else 8 / 11,
            "sourceSampleCount": primitive_count,
            "materialBindingCount": len(bindings or {}),
            "materialColoredMeshCount": sum(1 for row in surface_used if row.get("materialColor")),
            "materialColoredPixelCount": textured_pixels,
            "baseColorTextures": sorted({
                row["baseColorTexture"] for row in surface_used if row.get("baseColorTexture")
            }),
            "materialMappingMethod": (
                "exact_hlod_level_lod_signed_suffix_to_generated_material_then_base_color_pathid"
                if textured_pixels else None
            ),
            "heightEcho": {
                "enabled": False,
                "boundary": "Disabled for the mesh-vertex scan: height is encoded by tone without duplicating coordinates.",
            },
            "realPixelRatio": round(sum(1 for value in real if value) / (width * height), 4),
            "coveredPixelRatio": round(sum(1 for value in real if value) / (width * height), 4),
            "elevationRange": {"min": low, "max": high},
            "boundary": (
                "Only recovered OBJ vertices emit points; triangle interiors, gaps and side walls are not filled."
                if mode == "mesh_vertices" else
                "Only pixels hit by recovered HLOD triangles can emit points; gaps are not filled."
            ),
        },
        "transform": {
            "objAxisConversion": "worldX = translationX - objX; worldZ = translationZ + objZ",
            "cellSize": size,
            "translation": f"translation = origin + gridIndex * {size:g} + {size / 2:g}",
            "originX": fit["originX"],
            "originZ": fit["originZ"],
            "status": fit.get("method", "origin_fitted_to_exact_marker_occupancy_not_scene_transform"),
        },
        "gridFit": fit,
        "candidateMeshCount": len(clusters),
        "renderedMeshCount": len(used),
        "renderedTriangleCount": surface_triangles,
        "renderedPrimitiveCount": primitive_count,
        "imageSize": {"width": width, "height": height},
        "meshes": used,
        # The browser may offer a lightweight interactive OBJ inspection view
        # when these files are present.  It is deliberately separate from the
        # PNG contract: consumers can always fall back to the raster backdrop
        # without treating an incomplete scene as a complete map.
        "modelScene": {
            "status": "obj_cluster_subset" if scene_meshes else "obj_cluster_files_unavailable",
            "method": "recovered_hlod_obj_clusters",
            "meshes": scene_meshes,
            "meshCount": len(scene_meshes),
            "triangleCount": sum(row["triangles"] for row in scene_meshes),
            "coordinateSystem": "Unity world X/Y/Z; Map01/Map02 use their fixed shared HLOD grid origin",
            "axisConversion": "worldX = translationX - objX; worldY = objY; worldZ = translationZ + objZ",
            "boundary": (
                "Optional diagnostic OBJ inspection only. HLOD files carry mesh geometry but no authored "
                "GameObject/Transform; generated material ownership is accepted only through the exact "
                "level/LOD/signed-suffix naming contract. Missing or failed files must leave the "
                "PNG/marker map visible rather than inventing scene placement."
            ),
        },
        "boundary": (
            "Diagnostic orthographic HLOD preview. The HLOD bundles publish no GameObject or Transform "
            "record, so cluster placement uses the grid index in each cluster's name. Map01/Map02 share one "
            "fixed regional grid origin; marker occupancy remains validation, not a per-level transform. Material color is sampled only when the "
            "cluster and generated material share one exact level/LOD/signed suffix and that material owns "
            "one exact base-color PathID; every missing or ambiguous link retains the elevation palette."
        ),
    }
    alignment = LEVEL_RENDER_ALIGNMENTS.get(level_id)
    if alignment:
        result["renderAlignment"] = alignment
    return result


def streaming_texture_bindings(level_id: str, instances: list[dict]) -> dict[str, dict]:
    """Add exact generated-HLOD material bindings to ordinary Mesh bindings."""
    generic = dict(texture_bindings())
    available = _HLOD_TEXTURE_BINDINGS or {}
    for instance in instances:
        for mesh in _instance_meshes(instance):
            match = HLOD_CLUSTER_RE.fullmatch(str(mesh.get("name") or ""))
            asset_rel = _asset_rel_from_obj(mesh.get("obj"))
            if not match or not asset_rel:
                continue
            binding = available.get((level_id.lower(), int(match.group("lod")), int(match.group("hash"))))
            if binding:
                generic[asset_rel] = binding
    return generic


def render_streaming_surface_samples(
    level_id: str,
    streaming: list[dict],
    bounds: dict[str, float],
    width: int,
    height: int,
    output_root: Path,
    density: float,
    bindings: dict[str, dict] | None = None,
) -> dict | None:
    """Sample exact transformed triangle surfaces on a global X/Z lattice."""
    spacing = math.sqrt(1.0 / density)
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    samples: dict[int, list[tuple[float, tuple[int, int, int, int] | None]]] = {}
    cache: dict[Path, tuple[list, list, list] | None] = {}
    used_textures: set[str] = set()
    sampled_triangles = source_samples = 0
    excluded_structural_triangles = excluded_horizontal_triangles = 0
    epsilon = 1e-4
    export_root = (ROOT / "export_full").resolve()

    def add(index: int, world_y: float, color: tuple[int, int, int, int] | None) -> None:
        rows = samples.setdefault(index, [])
        for position, (existing_y, existing_color) in enumerate(rows):
            if abs(existing_y - world_y) <= epsilon:
                if existing_color is None and color is not None:
                    rows[position] = (world_y, color)
                return
        rows.append((world_y, color))

    for instance in streaming:
        matrix = instance.get("matrixColumnMajor")
        if not isinstance(matrix, list) or len(matrix) != 16:
            continue
        for mesh in _instance_meshes(instance):
            path = (ROOT / str(mesh.get("obj") or "")).resolve()
            try:
                path.relative_to(export_root)
            except ValueError:
                continue
            if path not in cache:
                cache[path] = _read_textured_mesh(path)
            parsed = cache[path]
            if not parsed:
                continue
            raw_vertices, texcoords, faces = parsed
            structural_detail = _is_detail_structural(instance, mesh)
            authored_detail_prop = _is_detail_prop(instance, mesh)
            texture = _texture_render_source((bindings or {}).get(_asset_rel_from_obj(mesh.get("obj"))))
            vertices = []
            for obj_x, obj_y, obj_z in raw_vertices:
                local_x = -obj_x  # undo AnimeStudio OBJ's Unity-X mirror
                vertices.append((
                    matrix[0] * local_x + matrix[4] * obj_y + matrix[8] * obj_z + matrix[12],
                    matrix[1] * local_x + matrix[5] * obj_y + matrix[9] * obj_z + matrix[13],
                    matrix[2] * local_x + matrix[6] * obj_y + matrix[10] * obj_z + matrix[14],
                ))
            for vertex_face, texture_face in faces:
                try:
                    points = [vertices[index] for index in vertex_face]
                except IndexError:
                    continue
                if structural_detail:
                    excluded_structural_triangles += 1
                    continue
                if not authored_detail_prop and _is_large_horizontal_triangle(points):
                    excluded_horizontal_triangles += 1
                    continue
                x0, x1, x2 = (point[0] for point in points)
                z0, z1, z2 = (point[2] for point in points)
                area = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2)
                if abs(area) < 1e-12:
                    continue
                min_kx = math.ceil(min(x0, x1, x2) / spacing - 0.5)
                max_kx = math.floor(max(x0, x1, x2) / spacing - 0.5)
                min_kz = math.ceil(min(z0, z1, z2) / spacing - 0.5)
                max_kz = math.floor(max(z0, z1, z2) / spacing - 0.5)
                landed = False
                uvs = None
                if texture and min(texture_face) >= 0:
                    try:
                        uvs = [texcoords[index] for index in texture_face]
                    except IndexError:
                        uvs = None
                for kz in range(min_kz, max_kz + 1):
                    world_z = (kz + 0.5) * spacing
                    if not bounds["minZ"] <= world_z <= bounds["maxZ"]:
                        continue
                    for kx in range(min_kx, max_kx + 1):
                        world_x = (kx + 0.5) * spacing
                        if not bounds["minX"] <= world_x <= bounds["maxX"]:
                            continue
                        w0 = ((z1 - z2) * (world_x - x2) + (x2 - x1) * (world_z - z2)) / area
                        w1 = ((z2 - z0) * (world_x - x2) + (x0 - x2) * (world_z - z2)) / area
                        w2 = 1.0 - w0 - w1
                        if min(w0, w1, w2) < -EDGE_EPSILON:
                            continue
                        world_y = w0 * points[0][1] + w1 * points[1][1] + w2 * points[2][1]
                        px = round((world_x - bounds["minX"]) / span_x * (width - 1))
                        py = round((bounds["maxZ"] - world_z) / span_z * (height - 1))
                        if not (0 <= px < width and 0 <= py < height):
                            continue
                        color = None
                        if uvs is not None:
                            scale_u, scale_v = texture["scale"]
                            offset_u, offset_v = texture["offset"]
                            u = (w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]) * scale_u + offset_u
                            v = (w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]) * scale_v + offset_v
                            color = _sample_texture(texture, u, v)
                            if color is None:
                                continue
                            used_textures.add(texture["textureRel"])
                        add(py * width + px, world_y, color)
                        source_samples += 1
                        landed = True
                if landed:
                    sampled_triangles += 1

    all_heights = [world_y for rows in samples.values() for world_y, _color in rows]
    if not all_heights:
        return None
    low, high = min(all_heights), max(all_heights)
    y_span = max(high - low, 1.0)
    top_depth = [NO_HIT] * (width * height)
    top_colors = bytearray(width * height * 4)
    records = bytearray(b"MRPS" + struct.pack("<HHII", 1, 12, width, height))
    record_count = 0
    for index in sorted(samples):
        ordered = sorted(samples[index], key=lambda row: row[0])
        for world_y, recovered_color in ordered:
            tint = (world_y - low) / y_span
            color = recovered_color or (*[max(18, round(channel * 0.68)) for channel in elevation_color(tint)], 225)
            records.extend(struct.pack("<IfBBBB", index, world_y, *color))
            record_count += 1
        top_y, top_color = ordered[-1]
        tint = (top_y - low) / y_span
        color = top_color or (*[max(18, round(channel * 0.68)) for channel in elevation_color(tint)], 225)
        top_depth[index] = top_y
        offset = index * 4
        top_colors[offset:offset + 4] = bytes((*color[:3], 225))

    output_root.mkdir(parents=True, exist_ok=True)
    image_name = f"{level_id}_streaming_surface_points.png"
    write_png(
        output_root / image_name, width, height,
        [bytes(top_colors[row * width * 4:(row + 1) * width * 4]) for row in range(height)],
    )
    sample_name = f"{level_id}_streaming_surface_points.samples"
    (output_root / sample_name).write_bytes(records)
    height_mask = render_point_height_mask(
        level_id, top_depth, width, height, output_root,
        image_suffix="streaming_surface_points_height_mask", sampling="all",
    )
    return {
        "src": f"render/{image_name}",
        "method": "exact_matrix_world_surface_area_samples",
        "defaultOpacity": 0.72,
        "densityPerSquareMeter": density,
        "spacingMeters": spacing,
        "sourceSampleCount": source_samples,
        "sampledTriangleCount": sampled_triangles,
        "excludedStructuralTriangleCount": excluded_structural_triangles,
        "excludedHorizontalTriangleCount": excluded_horizontal_triangles,
        "heightMask": height_mask,
        "sampleSet": {
            "src": f"render/{sample_name}",
            "encoding": "mrps_v1_le_u32_pixel_f32_height_rgba8",
            "width": width,
            "height": height,
            "recordCount": record_count,
            "pixelCount": len(samples),
            "elevationRange": {"min": low, "max": high},
            "dedupeEpsilon": epsilon,
        },
        "baseColorTextures": sorted(used_textures),
        "boundary": (
            "Deterministic world-space X/Z lattice samples on exact matrix-transformed detail triangle surfaces. "
            "Named floor/roof/ceiling/ground/terrain geometry and broad near-horizontal non-prop slabs are excluded. "
            "The density changes presentation only; it does not change transforms, bounds, or alignment."
        ),
    }


def level_points(path: Path) -> list[tuple[float, float]]:
    return [(x, z) for x, _y, z in level_positions(path)]


def minimap_world_bounds(payload: dict) -> dict[str, float] | None:
    """Return the authoritative screen rectangle when in-game art exists."""
    bounds = (payload.get("minimap") or {}).get("worldBounds") or {}
    keys = ("minX", "maxX", "minZ", "maxZ")
    if not all(isinstance(bounds.get(key), (int, float)) for key in keys):
        return None
    normalized = {key: float(bounds[key]) for key in keys}
    if normalized["maxX"] <= normalized["minX"] or normalized["maxZ"] <= normalized["minZ"]:
        return None
    return normalized


def union_bounds(rows: list[dict[str, float]]) -> dict[str, float] | None:
    if not rows:
        return None
    return {
        "minX": min(row["minX"] for row in rows),
        "maxX": max(row["maxX"] for row in rows),
        "minZ": min(row["minZ"] for row in rows),
        "maxZ": max(row["maxZ"] for row in rows),
    }


def preferred_background_preview(exact: dict | None, hlod: dict | None) -> dict | None:
    """Prefer transform-backed scene geometry; keep inferred HLOD as fallback.

    A registry-only point plot does not supersede a recovered HLOD surface, but
    a streaming render whose meshes use exact InitChunkData matrices does.
    """
    if exact and exact.get("status") in {
        "recovered_streaming_textured_topdown",
        "recovered_streaming_mesh_topdown",
    }:
        return exact
    return hlod or exact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--mesh-root", type=Path, default=MESH_ROOT)
    parser.add_argument("--texture-root", type=Path, default=TEXTURE_ROOT)
    parser.add_argument("--maps-root", type=Path, default=MAPS_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--hlod-index", type=Path, default=HLOD_INDEX)
    parser.add_argument("--refresh-index", action="store_true", help="rescan the asset map even if the cache matches")
    parser.add_argument("--lod", type=int, default=None, help="preferred HLOD level; overrides the verified per-level choice")
    parser.add_argument(
        "--scan-mode", choices=("auto", "mesh_vertices", "depth_points"), default="auto",
        help="HLOD sampling method; auto uses the verified per-level choice",
    )
    parser.add_argument("--level", action="append", default=[], help="build only these level ids (repeatable)")
    parser.add_argument(
        "--water-only", action="store_true",
        help="refresh derived water overlays in existing manifests without rerendering model geometry",
    )
    parser.add_argument(
        "--exact-point-fallback-only", action="store_true",
        help="skip inferred HLOD rendering and publish only exact registry/quest transform point layers",
    )
    parser.add_argument(
        "--surface-point-density", type=float, default=DEFAULT_SURFACE_POINT_DENSITY,
        help=("exact-matrix HLOD surface samples per square metre; default 0.25 "
              "(approximately 2 m spacing); presentation only"),
    )
    args = parser.parse_args(argv)
    if not math.isfinite(args.surface_point_density) or args.surface_point_density <= 0:
        raise SystemExit("--surface-point-density must be a finite number greater than zero")

    # Asset export is optional. HLOD rendering needs the AssetMap, while the
    # exact-transform point-cloud fallback remains available without it.
    index = load_hlod_index(args.asset_map, args.hlod_index, args.refresh_index) if args.asset_map.is_file() else {"levels": {}, "assetMapSha256": None}
    if args.exact_point_fallback_only:
        index = {"levels": {}, "waterSectors": {}, "assetMapSha256": None}
    if not args.asset_map.is_file():
        print(f"map previews: HLOD skipped - AssetMap not found: {args.asset_map}")
    mesh_files = mesh_file_index(args.mesh_root) if index["levels"] else {}
    texture_files = texture_file_index(args.texture_root) if index.get("waterSectors") else {}
    only = set(args.level)
    if args.water_only:
        if not args.level:
            raise SystemExit("--water-only requires at least one --level")
        refreshed = refresh_water_overlay_manifests(
            args.level, index.get("waterSectors") or {}, texture_files, args.output_root,
        )
        print(f"map previews: refreshed {refreshed} water overlays")
        return 0

    published, skipped = [], []
    published_ids: set[str] = set()
    diagnostic_hlods: dict[str, dict] = {}
    # Map01 and Map02 are seamless authored regions. Their HLOD cell indices
    # share one grid origin, so a sparse member is not allowed to drift by one
    # cell merely because its own occupancy score has several near ties.
    local_fits: dict[str, dict] = {}
    region_fits: dict[str, list[dict]] = {}
    for candidate_id, candidate_lods in index["levels"].items():
        match = REGION_LEVEL_RE.match(candidate_id)
        candidate_map = args.maps_root / f"{candidate_id}.json"
        if not match or not candidate_map.is_file():
            continue
        candidate_fit = fit_origin(candidate_lods, level_points(candidate_map))
        if candidate_fit is None:
            continue
        local_fits[candidate_id] = candidate_fit
        region_fits.setdefault(match.group(1).lower(), []).append(candidate_fit)
    shared_origins = {
        region: origin
        for region, fits in region_fits.items()
        if (origin := select_shared_origin(fits)) is not None
    }
    for level_id, lods in sorted(index["levels"].items()):
        if only and level_id not in only:
            continue
        map_path = args.maps_root / f"{level_id}.json"
        if not map_path.exists():
            skipped.append((level_id, "no published map"))
            continue
        payload = json.loads(map_path.read_text(encoding="utf-8"))
        if projection_streaming_scene(level_id):
            # Exact InitChunkData matrices supersede the older grid-name/origin
            # diagnostic. Do not spend time rendering or publish an inferred
            # transform when the authored matrix path is available.
            continue
        points = level_points(map_path)
        fit = local_fits.get(level_id) or fit_origin(lods, points)
        if fit is None:
            skipped.append((level_id, f"origin under-determined ({len(points)} marker transforms)"))
            continue
        region_match = REGION_LEVEL_RE.match(level_id)
        region_key = region_match.group(1).lower() if region_match else None
        shared_origin = REGION_HLOD_GRID_ORIGINS.get(region_key) or shared_origins.get(region_key)
        if shared_origin:
            local_origin = (fit["originX"], fit["originZ"])
            shared_coverage = origin_coverage(lods, points, *shared_origin)
            fit = {
                **fit,
                "originX": shared_origin[0],
                "originZ": shared_origin[1],
                "coverage": round(shared_coverage, 4),
                "method": "fixed_region_hlod_grid_origin",
                "localBestOrigin": {"x": local_origin[0], "z": local_origin[1]},
                "localBestCoverage": fit["bestCoverage"],
                "regionMemberCount": len(region_fits.get(region_key, [])),
            }
        if fit["coverage"] < MIN_COVERAGE and not shared_origin:
            skipped.append((level_id, f"best origin only explains {fit['coverage']:.0%} of markers"))
            continue

        preferred_lod = args.lod if args.lod is not None else LEVEL_PREFERRED_LODS.get(level_id, 1)
        lod = preferred_lod if str(preferred_lod) in lods else min(int(key) for key in lods)
        render_bounds = minimap_world_bounds(payload) or plot_bounds(points)
        manifest = render_level(
            level_id, lods[str(lod)], lod, fit, render_bounds, mesh_files, args.output_root,
            None if args.scan_mode == "auto" else args.scan_mode,
            bindings=hlod_texture_bindings(level_id, lod, lods[str(lod)]),
        )
        if manifest is None:
            skipped.append((level_id, "no exported cluster mesh landed in bounds"))
            continue
        manifest["waterOverlay"] = render_water_overlay(
            level_id, water_scene_id(level_id), manifest["worldBounds"],
            index.get("waterSectors") or {}, texture_files, args.output_root,
        )
        manifest["assetMapSha256"] = index["assetMapSha256"]
        if not minimap_world_bounds(payload):
            manifest["exactPointFallback"] = render_point_cloud(
                level_id, points, args.output_root, payload,
                surface_point_density=args.surface_point_density,
            )
        exact_projection = projection_streaming_scene(level_id)
        manifest_name = (
            f"{level_id}_hlod_diagnostic.json" if exact_projection else
            f"{level_id}_hlod_grid_inferred.json"
        )
        (args.output_root / manifest_name).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if exact_projection:
            diagnostic_hlods[level_id] = manifest
        else:
            published.append((level_id, manifest))
            published_ids.add(level_id)
        print(
            f"{level_id}: HLOD{lod} {manifest['renderedMeshCount']}/{manifest['candidateMeshCount']} clusters, "
            f"{manifest['renderedPrimitiveCount']} source samples, {manifest['render']['realPixelRatio']:.0%} real geometry"
            f" / {manifest['render']['pointDensity']:.0%} point density, "
            f"origin ({fit['originX']:g},{fit['originZ']:g}), "
            f"fit {fit['coverage']:.0%} of {fit['samplePoints']} markers"
        )
    map_paths = [
        path for path in sorted(args.maps_root.glob("*.json"))
        if not only or path.stem in only
    ]
    # Non-seamless dungeon maps can reuse one large-world art level but are not
    # members of that level's WebUI region. Reuse the source level's recovered
    # HLOD grid transform, crop it around the danger map's own exact markers,
    # and publish an independent layered diagnostic surface.
    source_fits: dict[str, dict | None] = {}
    for map_path in map_paths:
        level_id = map_path.stem
        if level_id in published_ids:
            continue
        payload = json.loads(map_path.read_text(encoding="utf-8"))
        art_source = isolated_art_source(level_id)
        if not art_source:
            continue
        source_level = str(art_source["levelId"])
        lods = index["levels"].get(source_level)
        source_map_path = args.maps_root / f"{source_level}.json"
        if not lods or not source_map_path.is_file():
            skipped.append((level_id, f"source art level {source_level} has no recoverable HLOD/map payload"))
            continue
        if source_level not in source_fits:
            source_fits[source_level] = fit_origin(lods, level_points(source_map_path))
        fit = source_fits[source_level]
        if not fit or fit["coverage"] < MIN_COVERAGE:
            skipped.append((level_id, f"source art level {source_level} has no validated HLOD grid fit"))
            continue
        points = level_points(map_path)
        if not points:
            skipped.append((level_id, "no exact marker bounds for source-art HLOD crop"))
            continue
        lod = 0 if "0" in lods else min(int(key) for key in lods)
        manifest = render_level(
            level_id, lods[str(lod)], lod, fit, plot_bounds(points, min_pad=64.0),
            mesh_files, args.output_root, "depth_points",
            bindings=hlod_texture_bindings(source_level, lod, lods[str(lod)]),
        )
        if manifest is None:
            skipped.append((level_id, f"source art HLOD {source_level} has no geometry in danger-map crop"))
            continue
        manifest["waterOverlay"] = render_water_overlay(
            level_id, water_scene_id(level_id, water_scene_id(source_level)), manifest["worldBounds"],
            index.get("waterSectors") or {}, texture_files, args.output_root,
        )
        manifest["assetMapSha256"] = index["assetMapSha256"]
        manifest["projectionSource"] = {
            "sourceArtLevelId": source_level,
            "mappingMethod": art_source["method"],
            "mapConfigSource": art_source["source"],
            "cropMethod": "independent_dungeon_exact_marker_bounds_with_64m_pad",
            "boundary": "Source-art reuse only; this non-seamless gameplay map remains an independent WebUI region.",
        }
        manifest["exactPointFallback"] = render_point_cloud(
            level_id, points, args.output_root, payload,
            surface_point_density=args.surface_point_density,
        )
        (args.output_root / f"{level_id}_hlod_grid_inferred.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        published.append((level_id, manifest))
        published_ids.add(level_id)
        print(f"{level_id}: independent dungeon crop from {source_level} HLOD{lod}")
    # Every remaining published map without in-game art first resolves its
    # authored streaming scene. Several gameplay map ids can point at one
    # shared art scene (the blackbox tutorials are the main example), so render
    # that exact scene once and publish level-specific manifests that reuse it.
    # Only maps without such evidence fall back to registry transform points.
    point_clouds = []
    shared_streaming_payloads: dict[str, tuple[list[tuple[float, float, float]], dict]] = {}
    shared_streaming_renders: dict[str, dict] = {}
    scene_level_positions: dict[str, list[tuple[float, float, float]]] = {}
    scene_minimap_bounds: dict[str, list[dict[str, float]]] = {}
    for map_path in map_paths:
        projection = projection_streaming_scene(map_path.stem)
        if projection:
            scene_id = str(projection["sceneId"])
            scene_level_positions.setdefault(scene_id, []).extend(level_positions(map_path))
            payload = json.loads(map_path.read_text(encoding="utf-8"))
            exact_bounds = minimap_world_bounds(payload)
            if exact_bounds:
                scene_minimap_bounds.setdefault(scene_id, []).append(exact_bounds)

    for map_path in map_paths:
        level_id = map_path.stem
        payload = json.loads(map_path.read_text(encoding="utf-8"))
        if level_id in published_ids:
            continue
        projection = projection_streaming_scene(level_id)
        manifest = None
        if projection:
            scene_id = str(projection["sceneId"])
            if scene_id not in shared_streaming_payloads:
                shared_streaming_payloads[scene_id] = streaming_projection_payload(Path(projection["instanceSource"]))
            scene_positions, scene_payload = shared_streaming_payloads[scene_id]
            group_positions = scene_level_positions.get(scene_id) or scene_positions
            exact_minimap_bounds = union_bounds(scene_minimap_bounds.get(scene_id, []))
            # Small interior scenes can have only one or two registry markers,
            # whose generous view padding used to reduce the recovered props
            # to a few pixels (the simulation training room exposed this).
            # Their own InitChunkData translations are the tighter exact
            # placement envelope. Large shared scenes retain the member-union
            # crop so unrelated streaming cells do not enlarge the view.
            if exact_minimap_bounds:
                group_bounds = exact_minimap_bounds
            elif scene_positions and len(scene_positions) <= 200:
                group_bounds = plot_bounds([(x, z) for x, _y, z in scene_positions], min_pad=32.0)
            else:
                group_bounds = plot_bounds([(x, z) for x, _y, z in group_positions], min_pad=128.0)
            # Instance translations just outside the member-union crop can own
            # geometry that crosses its edge. Retain a conservative 128 m
            # collar while the published image stays on the stitched rectangle.
            collar = 128.0
            selected_markers = []
            for row in scene_payload.get("markers") or []:
                instance = row.get("streamingInstance") or {}
                matrix = instance.get("matrixColumnMajor")
                if not isinstance(matrix, list) or len(matrix) != 16:
                    continue
                if (group_bounds["minX"] - collar <= float(matrix[12]) <= group_bounds["maxX"] + collar
                        and group_bounds["minZ"] - collar <= float(matrix[14]) <= group_bounds["maxZ"] + collar):
                    selected_markers.append(row)
            base_manifest = shared_streaming_renders.get(scene_id)
            if base_manifest is None:
                selected_positions = [
                    (float(row["streamingInstance"]["matrixColumnMajor"][12]),
                     float(row["streamingInstance"]["matrixColumnMajor"][13]),
                     float(row["streamingInstance"]["matrixColumnMajor"][14]))
                    for row in selected_markers
                ]
                base_manifest = render_point_cloud(
                    scene_id,
                    selected_positions or group_positions,
                    args.output_root,
                    {
                        "markers": selected_markers,
                        "exactHlodMatrices": bool(scene_payload.get("exactHlodMatrices")),
                    },
                    bounds_override=group_bounds,
                    surface_point_density=args.surface_point_density,
                )
                if base_manifest:
                    shared_streaming_renders[scene_id] = base_manifest
            if base_manifest:
                manifest = {**base_manifest,
                    "levelId": level_id,
                    "projectionSource": {
                        "sceneId": scene_id,
                        "mappingMethod": projection["method"],
                        "mapConfigSource": projection["source"],
                        "instanceSource": str(Path(projection["instanceSource"]).relative_to(ROOT)).replace("\\", "/"),
                        "cropMethod": (
                            "authoritative_member_minimap_world_bounds_with_128m_instance_collar"
                            if exact_minimap_bounds else
                            "exact_sparse_scene_instance_bounds_with_32m_view_pad_and_instance_collar"
                            if scene_positions and len(scene_positions) <= 200 else
                            "shared_scene_member_transform_union_with_128m_view_pad_and_instance_collar"
                        ),
                    },
                }
                manifest["waterOverlay"] = render_water_overlay(
                    level_id, water_scene_id(level_id, scene_id), manifest["worldBounds"],
                    index.get("waterSectors") or {}, texture_files, args.output_root,
                )
                if scene_id != level_id:
                    manifest["boundary"] = (
                        f"This gameplay map declares the shared art scene {scene_id}; the orthographic image is that "
                        "scene's exact static projection. Level-specific registry and mission markers remain separate. "
                        + str(base_manifest.get("boundary") or "")
                    )
        if manifest is None:
            manifest = render_point_cloud(
                level_id, level_positions(map_path), args.output_root, payload,
                surface_point_density=args.surface_point_density,
            )
        manifest = preferred_background_preview(manifest, diagnostic_hlods.get(level_id))
        if manifest is None:
            skipped.append((level_id, "no exact X/Y/Z positions for point-cloud fallback"))
            continue
        if "waterOverlay" not in manifest:
            manifest["waterOverlay"] = render_water_overlay(
                level_id, water_scene_id(level_id), manifest["worldBounds"],
                index.get("waterSectors") or {}, texture_files, args.output_root,
            )
        (args.output_root / f"{level_id}_hlod_grid_inferred.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        point_clouds.append((level_id, manifest))
        published_ids.add(level_id)

    skipped = [(level_id, reason) for level_id, reason in skipped if level_id not in published_ids]
    for level_id, reason in skipped:
        print(f"{level_id}: skipped - {reason}")
    print(f"map previews: {len(published)} HLOD, {len(point_clouds)} point clouds, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
