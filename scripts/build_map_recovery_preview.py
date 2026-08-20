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

# Shading is derived from the smoothed height field, not from per-facet mesh
# normals. Normals give every rock shard its own highlight, which reads as noise
# rather than as terrain; a hillshade over a blurred DEM keeps the landforms and
# drops the shards. These are the standard hillshade parameters.
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


def plot_bounds(points: list[tuple[float, float]]) -> dict[str, float]:
    """Marker bounds padded out to the page's viewBox aspect.

    The frontend projects onto these bounds when they are declared, so matching
    the SVG aspect here is what keeps the raster from being stretched against
    the marker positions drawn over it.
    """
    xs = [p[0] for p in points]
    zs = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    pad_x = max((max_x - min_x) * BOUNDS_PAD, 32.0)
    pad_z = max((max_z - min_z) * BOUNDS_PAD, 32.0)
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

    Vertex normals are deliberately not read: the render shades a smoothed
    height field instead, so per-facet normals would only add noise.
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


def render_level(
    level_id: str,
    clusters: list[dict],
    lod: int,
    fit: dict,
    bounds: dict[str, float],
    mesh_files: dict[str, Path],
    output_root: Path,
) -> dict | None:
    """Render one level as a softened shaded-relief backdrop."""
    width, height = raster_size(bounds["maxX"] - bounds["minX"], bounds["maxZ"] - bounds["minZ"])
    depth, used, triangles = rasterise_depth(clusters, lod, fit, bounds, mesh_files, width, height)
    if not used:
        return None

    grown, real = grow_surface(depth, width, height)
    mask = [value > NO_HIT for value in grown]
    dem = smooth_surface(grown, mask, width, height)
    shading = hillshade(dem, mask, width, height)

    covered = [dem[index] for index in range(len(dem)) if mask[index]]
    if not covered:
        return None
    low, high = min(covered), max(covered)
    span = max(high - low, 1.0)

    rows = []
    for y in range(height):
        row = bytearray()
        base_index = y * width
        for x in range(width):
            index = base_index + x
            if not mask[index]:
                # Nothing was recovered here at all, so the page's own surface
                # shows through rather than an invented floor.
                row.extend((255, 255, 255, 0))
                continue
            tint = (dem[index] - low) / span
            lambert = AMBIENT + (1.0 - AMBIENT) * shading[index]
            row.extend((
                shade((0.95 - 0.17 * tint) * lambert),
                shade((0.94 - 0.08 * tint) * lambert),
                shade((0.90 + 0.03 * tint) * lambert),
                ALPHA_REAL if real[index] else ALPHA_GROWN,
            ))
        rows.append(bytes(row))

    output_root.mkdir(parents=True, exist_ok=True)
    image_name = f"{level_id}_hlod_grid_inferred.png"
    write_png(output_root / image_name, width, height, rows)
    size = cell_size(lod)
    scene_meshes = _scene_meshes(used, mesh_files, lod=lod, fit=fit)
    return {
        "schemaVersion": 3,
        "status": "inferred_hlod_grid_preview",
        "levelId": level_id,
        "src": f"render/{image_name}",
        "worldBounds": bounds,
        "coordinateSystem": "Unity world X/Z; image top is +Z",
        "hlodLevel": lod,
        "render": {
            "method": "orthographic_depth_pass_then_smoothed_hillshade",
            "shading": (
                "hillshade over a grown and blurred height field, with an elevation tint; "
                "per-facet mesh normals are deliberately not used"
            ),
            "hillshade": {
                "azimuth": HILLSHADE_AZIMUTH,
                "altitude": HILLSHADE_ALTITUDE,
                "scale": HILLSHADE_SCALE,
                "growRounds": FILL_ROUNDS,
                "blurRadius": BLUR_RADIUS,
                "blurPasses": BLUR_PASSES,
            },
            "realPixelRatio": round(sum(1 for value in real if value) / (width * height), 4),
            "coveredPixelRatio": round(len(covered) / (width * height), 4),
            "elevationRange": {"min": low, "max": high},
            "boundary": (
                "HLOD publishes cliffs, props and structures but no ground surface for these scenes, so "
                "the height field is grown a few pixels to join scattered props into the landform they sit "
                "on. Grown pixels are drawn more transparently than pixels carrying real geometry, and "
                "everything outside them is left empty rather than filled with an invented floor."
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
            "Diagnostic orthographic preview only. The HLOD bundles publish no GameObject or Transform "
            "record, so cluster placement is inferred from the grid index in each cluster's name and an "
            "origin fitted to this level's exact marker transforms. No mesh-to-material binding survives "
            "the export, so the surface is shaded, never textured."
        ),
    }


def level_points(path: Path) -> list[tuple[float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    points = []
    for node in [*(payload.get("markers") or []), *(payload.get("questPoints") or [])]:
        position = node.get("position") or {}
        x, z = position.get("x"), position.get("z")
        if isinstance(x, (int, float)) and isinstance(z, (int, float)):
            points.append((float(x), float(z)))
    return points


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--mesh-root", type=Path, default=MESH_ROOT)
    parser.add_argument("--maps-root", type=Path, default=MAPS_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--hlod-index", type=Path, default=HLOD_INDEX)
    parser.add_argument("--refresh-index", action="store_true", help="rescan the asset map even if the cache matches")
    parser.add_argument("--lod", type=int, default=1, help="preferred HLOD level; falls back to the finest available")
    parser.add_argument("--level", action="append", default=[], help="build only these level ids (repeatable)")
    args = parser.parse_args()

    index = load_hlod_index(args.asset_map, args.hlod_index, args.refresh_index)
    mesh_files = mesh_file_index(args.mesh_root)
    only = set(args.level)

    published, skipped = [], []
    for level_id, lods in sorted(index["levels"].items()):
        if only and level_id not in only:
            continue
        map_path = args.maps_root / f"{level_id}.json"
        if not map_path.exists():
            skipped.append((level_id, "no published map"))
            continue
        points = level_points(map_path)
        fit = fit_origin(lods, points)
        if fit is None:
            skipped.append((level_id, f"origin under-determined ({len(points)} marker transforms)"))
            continue
        if fit["coverage"] < MIN_COVERAGE:
            skipped.append((level_id, f"best origin only explains {fit['coverage']:.0%} of markers"))
            continue

        lod = args.lod if str(args.lod) in lods else min(int(key) for key in lods)
        manifest = render_level(
            level_id, lods[str(lod)], lod, fit, plot_bounds(points), mesh_files, args.output_root
        )
        if manifest is None:
            skipped.append((level_id, "no exported cluster mesh landed in bounds"))
            continue
        manifest["assetMapSha256"] = index["assetMapSha256"]
        (args.output_root / f"{level_id}_hlod_grid_inferred.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        published.append((level_id, manifest))
        print(
            f"{level_id}: HLOD{lod} {manifest['renderedMeshCount']}/{manifest['candidateMeshCount']} clusters, "
            f"{manifest['renderedTriangleCount']} tris, {manifest['render']['realPixelRatio']:.0%} real"
            f" / {manifest['render']['coveredPixelRatio']:.0%} shaded, "
            f"origin ({fit['originX']:g},{fit['originZ']:g}), "
            f"fit {fit['coverage']:.0%} of {fit['samplePoints']} markers"
        )
    for level_id, reason in skipped:
        print(f"{level_id}: skipped - {reason}")
    print(f"map previews: {len(published)} published, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
