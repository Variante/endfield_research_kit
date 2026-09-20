"""Render the authored Map01 RegionMap3D panel from AnimeStudio JSON assets.

The normal map recovery path publishes the gameplay map and its authored 2D
minimap.  RegionMap3D is a separate UI asset: Region01 owns the model roots,
each Map01 level supplies a ground texture and a low-poly building mesh, and
RegionMapSetting stores the UI rectangles that arrange those level cards.

This builder keeps that distinction explicit.  It uses the serialized prefab
transforms for model geometry, the serialized ``uiRect`` values for layout,
and writes a compact raster plus a provenance sidecar for the WebUI.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


from scripts.repo_paths import REPO_ROOT
from scripts.common import EXPORT_LAYOUT

ROOT = REPO_ROOT
# A targeted AnimeStudio re-export made only for this package; run
# intermediate, so it lives in the export's tmp work area, not in game/.
DEFAULT_ASSET_ROOT = EXPORT_LAYOUT.work_dir / "region3d"
DEFAULT_OUTPUT_ROOT = ROOT / "standalone/map01_region3d"
DEFAULT_REPORT_ROOT = DEFAULT_OUTPUT_ROOT

LEVELS = (
    "map01_lv001",
    "map01_lv002",
    "map01_lv003",
    "map01_lv005",
    "map01_lv006",
    "map01_lv007",
)

# Map01's authored gameplay rectangles.  The RegionMap3D render is a compact
# panel preview and is normalized into this stable page rectangle when it is
# overlaid in the WebUI.  The exact RegionMapSetting uiRects remain in the
# sidecar and are the source layout used to draw the asset.
MAP01_WORLD_BOUNDS = {"minX": -1024.0, "maxX": 1024.0, "minZ": -1024.0, "maxZ": 896.0}
PLANE_HALF_SIZE = 5.0  # Unity's built-in Plane (mesh path ID 10209)
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 960
IMAGE_PADDING = 54


class RegionMap3DError(RuntimeError):
    """Raised when the targeted RegionMap3D export is incomplete."""


def path_id_from_filename(path: Path) -> int:
    match = re.search(r"_p([0-9A-Fa-f]{16})\.json$", path.name)
    if not match:
        raise RegionMap3DError(f"AnimeStudio object filename has no path ID: {path}")
    raw = int(match.group(1), 16)
    return raw - (1 << 64) if raw >= (1 << 63) else raw


def pptr_id(value: Any) -> int | None:
    if not isinstance(value, dict):
        return None
    candidate = value.get("m_PathID", value.get("pathId"))
    if candidate is None:
        return None
    return int(candidate)


def vector3(value: Any) -> tuple[float, float, float]:
    if not isinstance(value, dict):
        return (0.0, 0.0, 0.0)
    return (float(value.get("X", value.get("x", 0.0))), float(value.get("Y", value.get("y", 0.0))), float(value.get("Z", value.get("z", 0.0))))


def quaternion(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, dict):
        return (0.0, 0.0, 0.0, 1.0)
    return (
        float(value.get("X", value.get("x", 0.0))),
        float(value.get("Y", value.get("y", 0.0))),
        float(value.get("Z", value.get("z", 0.0))),
        float(value.get("W", value.get("w", 1.0))),
    )


def add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def component_mul(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])


def rotate(q: tuple[float, float, float, float], point: tuple[float, float, float]) -> tuple[float, float, float]:
    """Apply Unity's normalized quaternion to a point."""

    x, y, z, w = q
    px, py, pz = point
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return (
        (1.0 - 2.0 * (yy + zz)) * px + 2.0 * (xy - wz) * py + 2.0 * (xz + wy) * pz,
        2.0 * (xy + wz) * px + (1.0 - 2.0 * (xx + zz)) * py + 2.0 * (yz - wx) * pz,
        2.0 * (xz - wy) * px + 2.0 * (yz + wx) * py + (1.0 - 2.0 * (xx + yy)) * pz,
    )


def apply_transform(transform: dict[str, Any], point: tuple[float, float, float]) -> tuple[float, float, float]:
    scaled = component_mul(vector3(transform.get("m_LocalScale")), point)
    return add(vector3(transform.get("m_LocalPosition")), rotate(quaternion(transform.get("m_LocalRotation")), scaled))


def apply_chain(transforms: Iterable[dict[str, Any]], point: tuple[float, float, float]) -> tuple[float, float, float]:
    result = point
    for transform in reversed(tuple(transforms)):
        result = apply_transform(transform, result)
    return result


def bounds(points: Iterable[tuple[float, float, float]]) -> dict[str, float]:
    rows = list(points)
    if not rows:
        raise RegionMap3DError("cannot calculate bounds for an empty point set")
    return {
        "minX": min(row[0] for row in rows),
        "maxX": max(row[0] for row in rows),
        "minY": min(row[1] for row in rows),
        "maxY": max(row[1] for row in rows),
        "minZ": min(row[2] for row in rows),
        "maxZ": max(row[2] for row in rows),
    }


def finite_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def fit_axis(rows: list[tuple[float, float]], label: str) -> tuple[float, float, float]:
    if len(rows) < 2:
        raise RegionMap3DError(f"need at least two RegionMap3D {label} anchors")
    mean_world = sum(row[0] for row in rows) / len(rows)
    mean_layout = sum(row[1] for row in rows) / len(rows)
    denominator = sum((row[0] - mean_world) ** 2 for row in rows)
    if denominator <= 1e-9:
        raise RegionMap3DError(f"RegionMap3D {label} anchors have no span")
    scale = sum((row[0] - mean_world) * (row[1] - mean_layout) for row in rows) / denominator
    offset = mean_layout - scale * mean_world
    residual = max(abs(scale * world + offset - layout) for world, layout in rows)
    return scale, offset, residual


def source_record(data: dict[str, Any] | None) -> dict[str, Any]:
    info = data.get("$animestudio", {}) if isinstance(data, dict) else {}
    keys = ("pathId", "type", "name", "sourceFile", "sourceOriginalPath", "sourceOffset", "rawDataSha256")
    return {key: info[key] for key in keys if key in info}


def require_file(path: Path, description: str) -> Path:
    if not path.is_file():
        raise RegionMap3DError(f"missing {description}: {path}")
    return path


class ExportedObjects:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.objects: dict[str, dict[int, dict[str, Any]]] = {}
        self.paths: dict[str, dict[int, Path]] = {}
        for kind in ("GameObject", "Transform", "Mesh", "MonoBehaviour", "Material"):
            object_dir = root / kind
            if not object_dir.is_dir():
                continue
            objects: dict[int, dict[str, Any]] = {}
            paths: dict[int, Path] = {}
            for path in object_dir.glob("*.json"):
                try:
                    path_id = path_id_from_filename(path)
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError, RegionMap3DError) as exc:
                    raise RegionMap3DError(f"cannot read {kind} export {path}: {exc}") from exc
                objects[path_id] = data
                paths[path_id] = path
            self.objects[kind] = objects
            self.paths[kind] = paths
        self.transform_by_game_object: dict[int, tuple[int, dict[str, Any]]] = {}
        for path_id, data in self.objects.get("Transform", {}).items():
            game_object_id = pptr_id(data.get("m_GameObject"))
            if game_object_id is not None:
                self.transform_by_game_object[game_object_id] = (path_id, data)

    def by_id(self, kind: str, path_id: int | None, description: str) -> tuple[int, dict[str, Any]]:
        if path_id is None or path_id not in self.objects.get(kind, {}):
            raise RegionMap3DError(f"missing {description} {kind} path ID {path_id}")
        return path_id, self.objects[kind][path_id]

    def game_object(self, name: str) -> tuple[int, dict[str, Any]]:
        matches = [(path_id, data) for path_id, data in self.objects.get("GameObject", {}).items() if data.get("m_Name") == name]
        if len(matches) != 1:
            raise RegionMap3DError(f"expected one GameObject named {name}, found {len(matches)}")
        return matches[0]

    def transform_for_game_object(self, game_object_id: int, description: str) -> tuple[int, dict[str, Any]]:
        match = self.transform_by_game_object.get(game_object_id)
        if not match:
            raise RegionMap3DError(f"missing Transform for {description} GameObject path ID {game_object_id}")
        return match

    def first_named(self, kind: str, name: str) -> tuple[int, dict[str, Any]]:
        matches = [(path_id, data) for path_id, data in self.objects.get(kind, {}).items() if data.get("m_Name") == name]
        if not matches:
            raise RegionMap3DError(f"missing {kind} named {name}")
        return matches[0]


def find_texture(texture_root: Path, level: str) -> Path:
    matches = sorted(
        path for path in texture_root.rglob(f"T_buildingGround_{level.removeprefix('map01_')}*.png")
        if path.is_file()
    )
    if not matches:
        raise RegionMap3DError(f"missing converted ground texture for {level} under {texture_root}")
    return matches[0]


def load_config(export: ExportedObjects) -> tuple[int, dict[str, Any]]:
    matches = [
        (path_id, data)
        for path_id, data in export.objects.get("MonoBehaviour", {}).items()
        # AnimeStudio names an unnamed MonoBehaviour after its script class.
        if data.get("$animestudio", {}).get("name") == "RegionMapSetting"
    ]
    if len(matches) != 1:
        raise RegionMap3DError(f"expected one RegionMapSetting MonoBehaviour, found {len(matches)}")
    return matches[0]


def load_levels(export: ExportedObjects, config: dict[str, Any], texture_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = config.get("_cfg") or {}
    keys = list(cfg.get("_keyData") or [])
    values = list(cfg.get("_valueData") or [])
    entries = dict(zip(keys, values))
    missing = [level for level in LEVELS if level not in entries]
    if missing:
        raise RegionMap3DError(f"RegionMapSetting config has no Map01 entries: {', '.join(missing)}")

    model_parent_id = pptr_id(config.get("_modelNode"))
    building_parent_id = pptr_id(config.get("buildingRoot"))
    ground_parent_id = pptr_id(config.get("groundRoot"))
    _, model_parent = export.by_id("Transform", model_parent_id, "Region01 ModelNode")
    _, building_parent = export.by_id("Transform", building_parent_id, "Region01 building root")
    _, ground_parent = export.by_id("Transform", ground_parent_id, "Region01 ground root")

    levels: list[dict[str, Any]] = []
    for level in LEVELS:
        value = entries[level]
        ui_rect = value.get("uiRect") or {}
        rect = {
            "x": finite_number(ui_rect.get("x")),
            "y": finite_number(ui_rect.get("y")),
            "width": finite_number(ui_rect.get("z")),
            "height": finite_number(ui_rect.get("w")),
        }
        building_go_id, building_go = export.game_object(f"{level}_building")
        ground_go_id, ground_go = export.game_object(f"{level}_ground")
        building_transform_id, building_transform = export.transform_for_game_object(building_go_id, f"{level}_building")
        ground_transform_id, ground_transform = export.transform_for_game_object(ground_go_id, f"{level}_ground")
        mesh_id = pptr_id((building_go.get("m_MeshFilter") or {}).get("m_Mesh"))
        _, mesh = export.by_id("Mesh", mesh_id, f"{level} building")
        flat_vertices = list(mesh.get("m_Vertices") or [])
        if len(flat_vertices) < 3 or len(flat_vertices) % 3:
            raise RegionMap3DError(f"{level} mesh has malformed vertex data")
        vertices_local = [tuple(float(flat_vertices[index + offset]) for offset in range(3)) for index in range(0, len(flat_vertices), 3)]
        vertices_world = [
            apply_chain((model_parent, building_parent, building_transform), point)
            for point in vertices_local
        ]
        ground_world = [
            apply_chain((model_parent, ground_parent, ground_transform), (x, 0.0, z))
            for x in (-PLANE_HALF_SIZE, PLANE_HALF_SIZE)
            for z in (-PLANE_HALF_SIZE, PLANE_HALF_SIZE)
        ]
        levels.append(
            {
                "id": level,
                "uiRect": rect,
                "buildingGameObject": source_record(building_go),
                "groundGameObject": source_record(ground_go),
                "buildingTransform": {"pathId": building_transform_id, **{key: building_transform.get(key) for key in ("m_LocalPosition", "m_LocalRotation", "m_LocalScale")}},
                "groundTransform": {"pathId": ground_transform_id, **{key: ground_transform.get(key) for key in ("m_LocalPosition", "m_LocalRotation", "m_LocalScale")}},
                "buildingMesh": {"pathId": mesh_id, "name": mesh.get("m_Name"), "vertexCount": int(mesh.get("m_VertexCount") or 0), "source": source_record(mesh)},
                "verticesWorld": vertices_world,
                "indices": [int(value) for value in (mesh.get("m_Indices") or [])],
                "groundWorldBounds": bounds(ground_world),
                "groundTexture": find_texture(texture_root, level),
                "groundWorldPoints": ground_world,
            }
        )
    return levels, {
        "modelNode": {"pathId": model_parent_id, "localScale": model_parent.get("m_LocalScale"), "source": source_record(model_parent)},
        "buildingRoot": {"pathId": building_parent_id, "localPosition": building_parent.get("m_LocalPosition"), "source": source_record(building_parent)},
        "groundRoot": {"pathId": ground_parent_id, "localPosition": ground_parent.get("m_LocalPosition"), "source": source_record(ground_parent)},
    }


def build_layout_projection(levels: list[dict[str, Any]]) -> dict[str, float]:
    x_rows: list[tuple[float, float]] = []
    y_rows: list[tuple[float, float]] = []
    for level in levels:
        ground = level["groundWorldBounds"]
        rect = level["uiRect"]
        x_rows.append(((ground["minX"] + ground["maxX"]) / 2.0, rect["x"] + rect["width"] / 2.0))
        y_rows.append(((ground["minZ"] + ground["maxZ"]) / 2.0, rect["y"] + rect["height"] / 2.0))
    x_scale, x_offset, x_residual = fit_axis(x_rows, "X")
    y_scale, y_offset, y_residual = fit_axis(y_rows, "Z")
    return {"xScale": x_scale, "xOffset": x_offset, "yScale": y_scale, "yOffset": y_offset, "maxXResidual": x_residual, "maxYResidual": y_residual}


def world_to_layout(point: tuple[float, float, float], projection: dict[str, float]) -> tuple[float, float]:
    return (
        projection["xScale"] * point[0] + projection["xOffset"],
        projection["yScale"] * point[2] + projection["yOffset"],
    )


def layout_bounds(levels: list[dict[str, Any]], projection: dict[str, float]) -> dict[str, float]:
    points: list[tuple[float, float]] = []
    for level in levels:
        rect = level["uiRect"]
        points.extend(((rect["x"], rect["y"]), (rect["x"] + rect["width"], rect["y"] + rect["height"])))
        points.extend(world_to_layout(point, projection) for point in level["verticesWorld"])
    return {
        "minX": min(point[0] for point in points),
        "maxX": max(point[0] for point in points),
        "minY": min(point[1] for point in points),
        "maxY": max(point[1] for point in points),
    }


def pixel_mapper(layout: dict[str, float]) -> tuple[Any, dict[str, float]]:
    span_x = max(layout["maxX"] - layout["minX"], 1e-6)
    span_y = max(layout["maxY"] - layout["minY"], 1e-6)
    scale = min((IMAGE_WIDTH - 2 * IMAGE_PADDING) / span_x, (IMAGE_HEIGHT - 2 * IMAGE_PADDING) / span_y)
    content_w = span_x * scale
    content_h = span_y * scale
    offset_x = (IMAGE_WIDTH - content_w) / 2.0
    offset_y = (IMAGE_HEIGHT - content_h) / 2.0

    def map_point(point: tuple[float, float]) -> tuple[int, int]:
        return (round(offset_x + (point[0] - layout["minX"]) * scale), round(offset_y + (point[1] - layout["minY"]) * scale))

    return map_point, {"scale": scale, "offsetX": offset_x, "offsetY": offset_y, "contentWidth": content_w, "contentHeight": content_h}


def tint_ground_texture(path: Path, selected: bool, size: tuple[int, int]):
    from PIL import Image, ImageOps

    source = Image.open(path).convert("RGBA")
    source = source.resize(size, Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(source)
    line = (244, 193, 31) if selected else (185, 191, 195)
    dark = (25, 29, 32)
    tinted = ImageOps.colorize(gray, black=dark, white=line).convert("RGBA")
    # The source is an opaque black material texture. Lower its base opacity so
    # the six authored level cards read as a single panel on the dark canvas.
    alpha = gray.point(lambda value: min(242, 120 + int(value * 0.55)))
    tinted.putalpha(alpha)
    return tinted


def draw_building(draw: Any, level: dict[str, Any], map_point: Any, selected: bool) -> None:
    vertices = [map_point(world_to_layout(point, level["projection"])) for point in level["verticesWorld"]]
    indices = level["indices"]
    if len(indices) < 3:
        return
    # Draw triangles low-to-high to retain the model's subtle vertical relief.
    triangles: list[tuple[float, tuple[int, int, int]]] = []
    for start in range(0, len(indices) - 2, 3):
        ia, ib, ic = indices[start : start + 3]
        if not all(0 <= index < len(vertices) for index in (ia, ib, ic)):
            continue
        triangles.append((sum(level["verticesWorld"][index][1] for index in (ia, ib, ic)) / 3.0, (ia, ib, ic)))
    if not triangles:
        return
    min_y = min(row[0] for row in triangles)
    max_y = max(row[0] for row in triangles)
    for average_y, (ia, ib, ic) in sorted(triangles):
        shade = (average_y - min_y) / max(max_y - min_y, 1e-6)
        base = 86 + round(shade * 42)
        draw.polygon((vertices[ia], vertices[ib], vertices[ic]), fill=(base, base + 5, base + 9, 235))
    # Only the mesh boundary is outlined. Internal triangle edges would turn
    # the low-poly asset into a noisy wireframe at the page's normal zoom.
    edge_counts: dict[tuple[int, int], int] = {}
    for _, (ia, ib, ic) in triangles:
        for left, right in ((ia, ib), (ib, ic), (ic, ia)):
            edge = (left, right) if left < right else (right, left)
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    edge_color = (244, 193, 31, 255) if selected else (154, 161, 166, 235)
    for (left, right), count in edge_counts.items():
        if count == 1:
            draw.line((vertices[left], vertices[right]), fill=edge_color, width=2 if selected else 1, joint="curve")


def render(levels: list[dict[str, Any]], projection: dict[str, float], output_path: Path, selected_level: str) -> dict[str, Any]:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RegionMap3DError("Pillow is required to render the RegionMap3D preview") from exc

    layout = layout_bounds(levels, projection)
    map_point, raster_projection = pixel_mapper(layout)
    image = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (17, 21, 24, 255))
    draw = ImageDraw.Draw(image, "RGBA")

    # A faint panel frame makes transparent ground texture areas readable while
    # leaving the authored black material base visible.
    draw.rounded_rectangle((18, 18, IMAGE_WIDTH - 19, IMAGE_HEIGHT - 19), radius=18, outline=(62, 69, 74, 220), width=2)
    for level in levels:
        rect = level["uiRect"]
        top_left = map_point((rect["x"], rect["y"]))
        bottom_right = map_point((rect["x"] + rect["width"], rect["y"] + rect["height"]))
        texture = tint_ground_texture(level["groundTexture"], level["id"] == selected_level, (max(1, bottom_right[0] - top_left[0]), max(1, bottom_right[1] - top_left[1])))
        image.alpha_composite(texture, dest=top_left)

    # Keep level silhouettes above the ground texture, just as the normal and
    # selected M_building materials sit above M_buildingGround_white/yellow.
    for level in levels:
        level["projection"] = projection
        draw_building(draw, level, map_point, level["id"] == selected_level)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return {"layoutBounds": layout, "rasterProjection": raster_projection, "width": IMAGE_WIDTH, "height": IMAGE_HEIGHT}


def serializable_level(level: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in level.items()
        if key not in {"verticesWorld", "indices", "groundTexture", "groundWorldPoints", "projection"}
    } | {
        "groundTexture": level["groundTexture"].relative_to(ROOT).as_posix() if level["groundTexture"].is_relative_to(ROOT) else str(level["groundTexture"]),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    asset_root = args.asset_root.resolve()
    json_root = (args.json_root or asset_root / "json").resolve()
    texture_root = (args.texture_root or asset_root / "textures/Texture2D").resolve()
    output_root = args.output_root.resolve()
    report_root = args.report_root.resolve()
    if not (json_root / "MonoBehaviour").is_dir():
        raise RegionMap3DError(f"missing AnimeStudio JSON root: {json_root}")
    if not texture_root.is_dir():
        raise RegionMap3DError(f"missing converted Texture2D root: {texture_root}")
    export = ExportedObjects(json_root)
    config_id, config = load_config(export)
    levels, parents = load_levels(export, config, texture_root)
    projection = build_layout_projection(levels)
    output_image = output_root / "render/map01_regionmap3d_topdown.png"
    raster = render(levels, projection, output_image, args.selected_level)
    map_bounds = dict(MAP01_WORLD_BOUNDS)
    sidecar = {
        "schemaVersion": 1,
        "id": "map01_regionmap3d",
        "title": "Map01 RegionMap3D",
        "sourceKind": "regionmap3d",
        "status": "authored_prefab_raster",
        "src": output_image.relative_to(output_root).as_posix(),
        "worldBounds": map_bounds,
        "mapInverted": False,
        "coordinateStatus": "layout_normalized",
        "layoutSpace": "Region01.RegionMapSetting.cfg.uiRect",
        "modelSpace": "Region01.ModelNode",
        "selectedLevel": args.selected_level,
        "colors": {
            "normalOuter": config.get("_normalModelOuterColor"),
            "selectedOuter": config.get("_selectedModelOuterColor"),
            "normalGroundMaterial": "M_buildingGround_white",
            "selectedGroundMaterial": "M_buildingGround_yellow",
            "buildingMaterial": "M_building",
        },
        "projection": projection,
        "raster": raster,
        "region": parents,
        "config": {"pathId": config_id, "source": source_record(config), "levelIds": list(config.get("_cfg", {}).get("_keyData") or [])},
        "levels": [serializable_level(level) for level in levels],
        "source": {
            "jsonRoot": json_root.relative_to(ROOT).as_posix() if json_root.is_relative_to(ROOT) else str(json_root),
            "textureRoot": texture_root.relative_to(ROOT).as_posix() if texture_root.is_relative_to(ROOT) else str(texture_root),
            "assetClosure": "reports/assets/map_recovery/region3d_asset_closure.json",
            "luaController": "game/Lua/Data/LuaScripts/UI/Panels/RegionMap3D/RegionMap3DCtrl.lua",
        },
    }
    sidecar_path = output_root / "region3d.json"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schemaVersion": 1,
        "status": "complete",
        "id": "map01_regionmap3d",
        "image": output_image.relative_to(ROOT).as_posix(),
        "sidecar": sidecar_path.relative_to(ROOT).as_posix(),
        "selectedLevel": args.selected_level,
        "levelCount": len(levels),
        "levels": [level["id"] for level in levels],
        "projection": projection,
        "sourceJsonRoot": json_root.relative_to(ROOT).as_posix() if json_root.is_relative_to(ROOT) else str(json_root),
    }
    report_root.mkdir(parents=True, exist_ok=True)
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    report_path = report_root / "region3d_map01_latest.json"
    try:
        report_path.write_text(report_text, encoding="utf-8")
    except PermissionError:
        # Some generated report trees are mounted read-only in export-review
        # sandboxes.  Keep the build successful because the WebUI sidecar and
        # image are the published product, while retaining the audit beside it.
        fallback = output_root / "region3d_map01_report.json"
        fallback.write_text(report_text, encoding="utf-8")
        report["reportFallback"] = fallback.relative_to(ROOT).as_posix() if fallback.is_relative_to(ROOT) else str(fallback)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT, help="targeted export root containing json/ and textures/")
    parser.add_argument("--json-root", type=Path, help="AnimeStudio JSON root; defaults to <asset-root>/json")
    parser.add_argument("--texture-root", type=Path, help="converted Texture2D root; defaults to <asset-root>/textures/Texture2D")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="WebUI map recovery data root")
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT, help="map recovery report root")
    parser.add_argument("--selected-level", choices=LEVELS, default="map01_lv001", help="level rendered with the yellow selected-state material")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build(args)
    except RegionMap3DError as exc:
        print(f"RegionMap3D build failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
