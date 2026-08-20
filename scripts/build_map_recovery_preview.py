#!/usr/bin/env python3
"""Build inferred HLOD top-down previews for every recovered map.

The HLOD bundles publish `Mesh`, `Material` and `Texture2D` only - no
`GameObject` or `Transform` record survives the export - so a cluster's world
placement cannot be read out and has to be inferred from its name. A cluster is
named `S_HLOD<lod>_<i>_<j>_Cluster_<hash>`, and its vertices are stored centred
on the cluster's own origin, so the only unknowns are the grid cell size and the
grid origin.

Both are recovered rather than assumed:

  * cell size doubles per LOD and `HLOD0` is 64 m. `indie_dg002`'s previously
    hand-derived `HLOD1` cell of 128 m is the independent check on that.
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
import json
import math
import re
import struct
import sys
import zlib
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_map_asset_closure import iter_asset_entries, sha256_file

DEFAULT_ASSET_MAP = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json"
MESH_ROOT = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh"
MAPS_ROOT = ROOT / "webui/data/map_recovery/maps"
OUTPUT_ROOT = ROOT / "webui/data/map_recovery/render"
HLOD_INDEX = ROOT / "reports/assets/map_recovery/hlod_grid_index.json"

CLUSTER_RE = re.compile(r"^S_HLOD(\d+)_(-?\d+)_(-?\d+)_Cluster_")
# `.../<levelId>_art/hlod_v2/pc/hlod<n>/mesh` - the container names the level
# directly, so no per-level needle scan of the 750 MB asset map is needed.
LEVEL_RE = re.compile(r"/([a-z0-9_]+)_art/hlod_v2/", re.IGNORECASE)

BASE_CELL = 64.0  # HLOD0 cell size in metres; each further LOD doubles it
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

# Relief helpers remain available for focused diagnostics, but the published
# screenshot-matched preview uses only real depth hits as black scan points.
# These constants define the older optional smoothed-height calculation.
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


def build_hlod_index(asset_map: Path) -> dict:
    """One streaming pass over the asset map, grouped by level and LOD."""
    levels: dict[str, dict[str, list]] = {}
    for entry in iter_asset_entries(asset_map):
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
        "schemaVersion": 1,
        "assetMap": str(asset_map),
        "assetMapSha256": sha256_file(asset_map),
        "levels": levels,
    }


def load_hlod_index(asset_map: Path, cache: Path, refresh: bool) -> dict:
    if not refresh and cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("assetMapSha256") == sha256_file(asset_map):
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
            worst = 1.0
            for lod, cells in occupancy.items():
                size = cell_size(lod)
                hits = sum(
                    1 for x, z in points
                    if (math.floor((x - origin_x) / size), math.floor((z - origin_z) / size)) in cells
                )
                worst = min(worst, hits / len(points))
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


def write_png(path: Path, width: int, height: int, rows: list[bytes]) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\0" + row for row in rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


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
    """Normalize legacy single-mesh and composite streaming-instance rows."""
    meshes = instance.get("meshes")
    if isinstance(meshes, list):
        rows = [row for row in meshes if isinstance(row, dict)]
        if rows:
            return rows
    mesh = instance.get("mesh")
    return [mesh] if isinstance(mesh, dict) else []


def render_point_cloud(
    level_id: str,
    positions: list[tuple[float, float, float]],
    output_root: Path,
    map_payload: dict | None = None,
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
    streaming_xz = [
        (float(row["matrixColumnMajor"][12]), float(row["matrixColumnMajor"][14]))
        for row in streaming
        if isinstance(row.get("matrixColumnMajor"), list) and len(row["matrixColumnMajor"]) == 16
    ]
    # A recovered streaming scene with hundreds of transforms is not the old
    # sparse registry fallback. Four metres keeps its exact extents readable;
    # small evidence sets retain the conservative 32 m context margin.
    bounds = plot_bounds(
        streaming_xz or [(x, z) for x, _y, z in positions],
        min_pad=1.0 if streaming_xz else (4.0 if len(positions) >= 100 else 32.0),
    )
    span_x = max(bounds["maxX"] - bounds["minX"], 1.0)
    span_z = max(bounds["maxZ"] - bounds["minZ"], 1.0)
    if span_x / span_z >= VIEW_ASPECT:
        width = LONG_EDGE
        height = max(1, round(width / VIEW_ASPECT))
    else:
        height = LONG_EDGE
        width = max(1, round(height * VIEW_ASPECT))
    pixels = [bytearray(width * 4) for _ in range(height)]
    ys = [row[1] for row in positions]
    low, high = min(ys), max(ys)
    y_span = max(high - low, 1.0)
    radius = max(2, min(6, round(9 - math.log2(max(len(positions), 2)) / 2)))

    def blend(px: int, py: int, color: tuple[int, int, int], alpha: int) -> None:
        if not (0 <= px < width and 0 <= py < height) or alpha <= 0:
            return
        row = pixels[py]
        offset = px * 4
        inverse = 255 - alpha
        row[offset] = (color[0] * alpha + row[offset] * inverse) // 255
        row[offset + 1] = (color[1] * alpha + row[offset + 1] * inverse) // 255
        row[offset + 2] = (color[2] * alpha + row[offset + 2] * inverse) // 255
        row[offset + 3] = min(255, alpha + row[offset + 3] * inverse // 255)

    resolved = [row for row in streaming if _instance_meshes(row)]
    rendered_instances = rendered_triangles = rendered_vertex_samples = 0
    real_pixel_ratio = 0.0
    if resolved:
        depth, rendered_instances, rendered_triangles, rendered_vertex_samples = rasterise_streaming_depth(
            resolved, bounds, width, height
        )
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
                    grey = shade(0.32 - 0.24 * tint)
                    offset = px * 4
                    row[offset:offset + 4] = bytes((grey, grey, grey, 220))
    else:
        # Sparse non-streaming fallbacks remain exact transform points. A soft
        # halo keeps isolated transforms legible without connecting them.
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
                        blend(px + dx, py + dy, color, round(42 * height_alpha * (1 - distance / (radius * 2 + 0.01))))
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    distance = math.hypot(dx, dy)
                    if distance <= radius:
                        blend(px + dx, py + dy, color, round(210 * height_alpha * (1 - 0.55 * distance / (radius + 0.01))))

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
    image_name = f"{level_id}_streaming_topdown.png" if rendered_instances else f"{level_id}_registry_point_cloud.png"
    write_png(output_root / image_name, width, height, [bytes(row) for row in pixels])
    return {
        "schemaVersion": 1,
        "status": "recovered_streaming_mesh_topdown" if rendered_instances else "inferred_registry_point_cloud_preview",
        "levelId": level_id,
        "src": f"render/{image_name}",
        "worldBounds": bounds,
        "coordinateSystem": "Unity world X/Z; image top is +Z; tint derives from exact world Y",
        "render": {
            "method": "exact_streaming_matrix_obj_depth_pass" if rendered_instances else "exact_registry_transform_point_cloud",
            "pointCount": 0 if rendered_instances else len(positions),
            "pointRadius": 0 if rendered_instances else radius,
            "renderedInstanceCount": rendered_instances,
            "renderedTriangleCount": rendered_triangles,
            "renderedVertexSampleCount": rendered_vertex_samples,
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
            f"InitChunkData 4x4 matrices ({rendered_triangles} prop triangles and {rendered_vertex_samples} "
            f"floor-edge vertex samples). The remaining "
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


def rasterise_streaming_depth(streaming, bounds, width, height):
    """Rasterize resolved static OBJ instances with their exact 4x4 matrices."""
    span_x = bounds["maxX"] - bounds["minX"]
    span_z = bounds["maxZ"] - bounds["minZ"]
    depth = [NO_HIT] * (width * height)
    cache: dict[Path, tuple[list, list] | None] = {}
    used_instances = 0
    triangles = 0
    vertex_samples = 0
    export_root = (ROOT / "export_full").resolve()

    for instance in streaming:
        matrix = instance.get("matrixColumnMajor")
        meshes = _instance_meshes(instance)
        if not meshes or not isinstance(matrix, list) or len(matrix) != 16:
            continue
        instance_drawn = False
        for mesh in meshes:
            path = (ROOT / str(mesh.get("obj") or "")).resolve()
            try:
                path.relative_to(export_root)
            except ValueError:
                continue
            if path not in cache:
                cache[path] = _read_cluster(path)
            parsed = cache[path]
            if not parsed:
                continue
            raw_vertices, faces = parsed
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
            # Filling the level-wide floor mesh would turn the white map into one
            # grey rectangle and hide every prop. Keep its real mesh vertices as
            # the floor outline while volumetric props use a normal depth pass.
            if str(mesh.get("name") or "").lower().startswith("s_build_indie_floor"):
                landed = 0
                for world_x, world_y, world_z in vertices:
                    px = round((world_x - bounds["minX"]) / span_x * (width - 1))
                    py = round((bounds["maxZ"] - world_z) / span_z * (height - 1))
                    if 0 <= px < width and 0 <= py < height:
                        index = py * width + px
                        depth[index] = max(depth[index], world_y)
                        landed += 1
                if landed:
                    instance_drawn = True
                    vertex_samples += landed
                continue
            drawn = 0
            for face in faces:
                try:
                    points = [vertices[index] for index in face]
                except IndexError:
                    continue
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
                        if elevation > depth[index]:
                            depth[index] = elevation
            if drawn:
                instance_drawn = True
                triangles += drawn
        if instance_drawn:
            used_instances += 1
    return depth, used_instances, triangles, vertex_samples


def rasterise_depth(clusters, lod, fit, bounds, mesh_files, width, height):
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
        parsed = _read_cluster(path)
        if not parsed:
            continue
        raw_vertices, faces = parsed
        # The cluster's vertices are centred on its own origin, so its world
        # position is the centre of the grid cell its name declares. AnimeStudio
        # writes OBJ right-handed, so X is mirrored back onto Unity's world.
        translate_x = fit["originX"] + cluster["i"] * size + size / 2
        translate_z = fit["originZ"] + cluster["j"] * size + size / 2
        vertices = [(translate_x - v[0], v[1], translate_z + v[2]) for v in raw_vertices]

        drawn = 0
        for face in faces:
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
                        depth[index] = elevation
        if drawn:
            triangles += drawn
            used.append({"pathId": cluster["pathId"], "name": cluster["name"], "triangles": drawn})
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
) -> dict | None:
    """Restore the earlier smoothed DEM as a quiet layer below a point scan."""
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
            value = shade((0.97 - 0.16 * tint) * (0.88 + 0.12 * lighting[index]))
            row.extend((value, value, value, 225 if real[index] else 165))
        rows.append(bytes(row))
    image_name = f"{level_id}_hlod_elevation.png"
    write_png(output_root / image_name, width, height, rows)
    return {
        "src": f"render/{image_name}",
        "method": "orthographic_depth_pass_then_smoothed_hillshade",
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
        "boundary": "Recovered HLOD triangle depth only; gap growth is visibly translucent and does not claim authored ground geometry.",
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
) -> dict | None:
    """Render recovered HLOD geometry as a dense orthographic point cloud."""
    width, height = raster_size(bounds["maxX"] - bounds["minX"], bounds["maxZ"] - bounds["minZ"])
    mode = scan_mode or LEVEL_SCAN_MODES.get(level_id, "depth_points")
    if mode == "mesh_vertices":
        depth, used, primitive_count = rasterise_vertices(
            clusters, lod, fit, bounds, mesh_files, width, height
        )
        triangles = 0
    else:
        depth, used, triangles = rasterise_depth(clusters, lod, fit, bounds, mesh_files, width, height)
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
            grey = shade((0.28 - 0.22 * tint) if mode == "mesh_vertices" else (0.40 - 0.34 * tint))
            offset = x * 4
            row[offset:offset + 4] = bytes((grey, grey, grey, 215 if mode == "mesh_vertices" else 205))

    output_root.mkdir(parents=True, exist_ok=True)
    image_name = f"{level_id}_hlod_grid_inferred.png"
    write_png(output_root / image_name, width, height, rows)
    elevation_underlay = None
    if level_id == "indie_dg002":
        elevation_depth, elevation_used, _ = rasterise_depth(
            clusters, lod, fit, bounds, mesh_files, width, height
        )
        if elevation_used:
            elevation_underlay = render_elevation_underlay(
                level_id, elevation_depth, width, height, output_root
            )
    size = cell_size(lod)
    scene_meshes = _scene_meshes(used, mesh_files, lod=lod, fit=fit)
    return {
        "schemaVersion": 3,
        "status": "inferred_hlod_grid_preview",
        "levelId": level_id,
        "src": f"render/{image_name}",
        "elevationUnderlay": elevation_underlay,
        "worldBounds": bounds,
        "coordinateSystem": "Unity world X/Z; image top is +Z",
        "hlodLevel": lod,
        "render": {
            "method": "orthographic_hlod_mesh_vertex_scan" if mode == "mesh_vertices" else "orthographic_hlod_depth_black_point_density",
            "shading": (
                "actual OBJ vertices projected orthographically, with world-Y encoded as grey-black on white"
                if mode == "mesh_vertices" else
                "the 87b60f49 screen-door sample of real HLOD depth pixels, with its height palette inverted"
            ),
            "pointDensity": 1.0 if mode == "mesh_vertices" else 8 / 11,
            "sourceSampleCount": primitive_count,
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
            "status": "origin_fitted_to_exact_marker_occupancy_not_scene_transform",
        },
        "gridFit": fit,
        "candidateMeshCount": len(clusters),
        "renderedMeshCount": len(used),
        "renderedTriangleCount": triangles,
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
            "coordinateSystem": "inferred Unity world X/Y/Z; grid origin fitted to marker occupancy",
            "axisConversion": "worldX = translationX - objX; worldY = objY; worldZ = translationZ + objZ",
            "boundary": (
                "Optional diagnostic OBJ inspection only. HLOD files carry mesh geometry but no authored "
                "GameObject/Transform or mesh-to-material binding; missing or failed files must leave the "
                "PNG/marker map visible rather than inventing scene placement."
            ),
        },
        "boundary": (
            "Diagnostic orthographic black point-density preview only. The HLOD bundles publish no GameObject or Transform "
            "record, so cluster placement is inferred from the grid index in each cluster's name and an "
            "origin fitted to this level's exact marker transforms. No mesh-to-material binding survives "
            "the export, so the surface is shaded, never textured."
        ),
    }


def level_points(path: Path) -> list[tuple[float, float]]:
    return [(x, z) for x, _y, z in level_positions(path)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--mesh-root", type=Path, default=MESH_ROOT)
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
    args = parser.parse_args()

    # Asset export is optional. HLOD rendering needs the AssetMap, while the
    # exact-transform point-cloud fallback remains available without it.
    index = load_hlod_index(args.asset_map, args.hlod_index, args.refresh_index) if args.asset_map.is_file() else {"levels": {}, "assetMapSha256": None}
    if not args.asset_map.is_file():
        print(f"map previews: HLOD skipped - AssetMap not found: {args.asset_map}")
    mesh_files = mesh_file_index(args.mesh_root) if index["levels"] else {}
    only = set(args.level)

    published, skipped = [], []
    published_ids: set[str] = set()
    for level_id, lods in sorted(index["levels"].items()):
        if only and level_id not in only:
            continue
        map_path = args.maps_root / f"{level_id}.json"
        if not map_path.exists():
            skipped.append((level_id, "no published map"))
            continue
        payload = json.loads(map_path.read_text(encoding="utf-8"))
        if (payload.get("minimap") or {}).get("src"):
            continue
        points = level_points(map_path)
        fit = fit_origin(lods, points)
        if fit is None:
            skipped.append((level_id, f"origin under-determined ({len(points)} marker transforms)"))
            continue
        if fit["coverage"] < MIN_COVERAGE:
            skipped.append((level_id, f"best origin only explains {fit['coverage']:.0%} of markers"))
            continue

        preferred_lod = args.lod if args.lod is not None else LEVEL_PREFERRED_LODS.get(level_id, 1)
        lod = preferred_lod if str(preferred_lod) in lods else min(int(key) for key in lods)
        manifest = render_level(
            level_id, lods[str(lod)], lod, fit, plot_bounds(points), mesh_files, args.output_root,
            None if args.scan_mode == "auto" else args.scan_mode,
        )
        if manifest is None:
            skipped.append((level_id, "no exported cluster mesh landed in bounds"))
            continue
        manifest["assetMapSha256"] = index["assetMapSha256"]
        (args.output_root / f"{level_id}_hlod_grid_inferred.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        published.append((level_id, manifest))
        published_ids.add(level_id)
        print(
            f"{level_id}: HLOD{lod} {manifest['renderedMeshCount']}/{manifest['candidateMeshCount']} clusters, "
            f"{manifest['renderedPrimitiveCount']} source samples, {manifest['render']['realPixelRatio']:.0%} real geometry"
            f" / {manifest['render']['pointDensity']:.0%} point density, "
            f"origin ({fit['originX']:g},{fit['originZ']:g}), "
            f"fit {fit['coverage']:.0%} of {fit['samplePoints']} markers"
        )
    # Every remaining published map without in-game art receives an exact
    # transform cloud. HLOD success stays preferred; maps with no model export
    # still gain a useful, explicitly non-geometric spatial backdrop.
    point_clouds = []
    for map_path in sorted(args.maps_root.glob("*.json")):
        level_id = map_path.stem
        if only and level_id not in only:
            continue
        payload = json.loads(map_path.read_text(encoding="utf-8"))
        if (payload.get("minimap") or {}).get("src") or level_id in published_ids:
            continue
        manifest = render_point_cloud(level_id, level_positions(map_path), args.output_root, payload)
        if manifest is None:
            skipped.append((level_id, "no exact X/Y/Z positions for point-cloud fallback"))
            continue
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
