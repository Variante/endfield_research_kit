"""Publish chunk-streamed 3D scene data for the Map page's scene viewer.

For each level this joins the static renderer draws of every exported
``InitChunkData`` chunk (``scripts.game_data.streaming.init_chunk_draws``) to
exported meshes, materials and textures:

* draw ref mesh/material hash -> stored path through the installed
  StringPathHash catalog (``exact`` hash lookup);
* stored path -> exported object. A mesh path ``<container>##<sub-asset>`` or
  a material ``.mat`` container that the StreamingAssets/Persistent asset maps
  list with one PathID is ``exact``; when the maps do not list the container,
  the sub-asset (or ``.mat`` file) name is matched to exactly one exported
  object name and is ``conditional`` on that name being unique;
* Material -> Texture2D through the material's ``m_TexEnvs`` PathID, matched to
  exactly one exported ``<name>_p<PathID>.png`` (``direct``).

The draw-ref column role is ``structuralOnly`` (see the reader). Draws are
kept for LOD 0 and without the shadow-only flag. Matrices are published in the
exported OBJ frame: AnimeStudio negates X when writing a Mesh, so each Unity
object-to-world matrix ``M`` is published as ``S M S`` with
``S = diag(-1, 1, 1)``.

Outputs, under ``webui/data/map_recovery/scene3d/<level>/``: ``index.json``
(chunk list, mesh table, material table, evidence counts) and
``chunks/<key>.json`` (entity instances). ``scene3d/index.json`` lists the
published levels. Nothing here reads another page's output.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    raise SystemExit("Run this maintained entry point as: python -m scripts.webui.map.build_map_scene3d")

from scripts.common import OUT_DIR, write_canonical_json
from scripts.game_data.streaming.init_chunk_draws import (
    StringPathCatalog,
    decode_init_chunk,
    iter_entity_draws,
    scan_asset_map,
    split_mesh_path,
)
from scripts.game_data.unity_store import UnityObjectStore
from scripts.source_paths import ExportLayout

SCHEMA = "endfield.map-scene3d.v1"
# A dungeon of ~190 cells: small enough for a page run, dense enough to stream.
DEFAULT_LEVEL = "dung02_dg002"
DEFAULT_OUTPUT = OUT_DIR / "map_recovery" / "scene3d"
CHUNK_RE = re.compile(r"^InitChunkData_(?:(-?\d+)_(-?\d+)|Global)_(\d+)_(\d+)\.bytes$")
PID_FILE_RE = re.compile(r"^(.*)_p([0-9A-F]{16})\.(obj|png)$")
BASE_SLOTS = ("_BaseColorMap", "_BaseMap", "_MainTex")
MRO_SLOTS = ("_MROMap",)
NORMAL_SLOTS = ("_NormalMap", "_BumpMap")
EMISSIVE_SLOTS = ("_EmissiveMap", "_EmissionMap")
CHUNK_SIZE = 128.0


def _pid_hex(value: int) -> str:
    return f"{value & ((1 << 64) - 1):016X}"


def _file_index(folder: Path, suffix: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Exported ``<name>_p<PID>.<ext>`` files keyed by PathID and by casefolded name."""
    by_pid: dict[str, list[str]] = defaultdict(list)
    by_name: dict[str, list[str]] = defaultdict(list)
    for path in folder.iterdir():
        match = PID_FILE_RE.match(path.name)
        if not match or match.group(3) != suffix:
            continue
        by_pid[match.group(2)].append(path.name)
        by_name[match.group(1).casefold()].append(path.name)
    return by_pid, by_name


def _mirror(matrix: tuple[float, ...]) -> list[float]:
    """Column-major ``S M S`` with ``S = diag(-1, 1, 1)``."""
    out = list(matrix)
    for column in range(4):
        for row in range(4):
            if (row == 0) != (column == 0):
                out[column * 4 + row] = -out[column * 4 + row]
    return [round(value, 6) for value in out]


def _color(colors: dict, name: str) -> list[float] | None:
    value = colors.get(name)
    if not isinstance(value, dict):
        return None
    return [round(float(value.get(channel, 0.0)), 4) for channel in "rgba"]


class _Resolver:
    def __init__(self, layout: ExportLayout) -> None:
        self.layout = layout
        self.store = UnityObjectStore.for_export(layout.root)
        self.mesh_by_pid, self.mesh_by_name = _file_index(layout.unity_type_dir("Mesh"), "obj")
        self.tex_by_pid, _ = _file_index(layout.unity_type_dir("Texture2D"), "png")
        self.asset_rows: dict[tuple[str, str], dict[str, set[int]]] = {}

    def scan(self, containers: set[str]) -> None:
        for layer, name in (
            ("StreamingAssets", "endfield_streamingassets_assets.json"),
            ("Persistent", "endfield_persistent_assets.json"),
        ):
            path = self.layout.asset_map_dir(layer) / name
            if not path.is_file():
                continue
            for key, rows in scan_asset_map(path, containers).items():
                target = self.asset_rows.setdefault(key, {})
                for row_name, ids in rows.items():
                    target.setdefault(row_name, set()).update(ids)

    def mesh(self, path: str) -> dict[str, Any]:
        container, sub_asset = split_mesh_path(path)
        name = sub_asset or Path(container).stem
        rows = self.asset_rows.get(("Mesh", container), {})
        ids = rows.get(name.casefold(), set()) if sub_asset else set().union(*rows.values()) if len(rows) == 1 else set()
        files = sorted({file for pid in ids for file in self.mesh_by_pid.get(_pid_hex(pid), ())})
        if len(files) == 1:
            return {"rel": f"Unity/Mesh/{files[0]}", "tier": "exact", "path": path}
        if not rows or not ids:
            candidates = self.mesh_by_name.get(name.casefold(), [])
            if len(candidates) == 1:
                return {"rel": f"Unity/Mesh/{candidates[0]}", "tier": "conditional", "path": path}
            return {"tier": "unresolved", "path": path, "reason": f"name-matches:{len(candidates)}"}
        return {"tier": "unresolved", "path": path, "reason": f"asset-map-objects:{len(files)}"}

    def material(self, path: str) -> dict[str, Any]:
        name = Path(path).stem
        rows = self.asset_rows.get(("Material", path.casefold()), {})
        ids = set().union(*rows.values()) if rows else set()
        documents = [
            row for pid in ids for row in self.store.rows_by_path_id(pid) if row.type == "Material"
        ]
        tier = "exact"
        if len(documents) != 1:
            if ids:
                return {"tier": "unresolved", "path": path, "reason": f"asset-map-documents:{len(documents)}"}
            documents = self.store.rows_by_object_name("Material", name)
            tier = "conditional"
            if len(documents) != 1:
                return {"tier": "unresolved", "path": path, "reason": f"name-matches:{len(documents)}"}
        payload = self.store.read_json("Material", documents[0].name)
        return {"name": name, "tier": tier, "path": path, **self._appearance(payload)}

    def _texture(self, tex_envs: dict, slots: tuple[str, ...]) -> dict[str, Any] | None:
        for slot in slots:
            env = tex_envs.get(slot) or {}
            texture = env.get("m_Texture") or {}
            pid = texture.get("m_PathID")
            if texture.get("IsNull") or not pid:
                continue
            files = self.tex_by_pid.get(_pid_hex(int(pid)), [])
            if len(files) != 1:
                return {"slot": slot, "tier": "unresolved", "reason": f"texture-files:{len(files)}"}
            scale = env.get("m_Scale") or {}
            offset = env.get("m_Offset") or {}
            out: dict[str, Any] = {"slot": slot, "rel": f"Unity/Texture2D/{files[0]}", "tier": "direct"}
            st = [float(scale.get("X", 1.0)), float(scale.get("Y", 1.0)),
                  float(offset.get("X", 0.0)), float(offset.get("Y", 0.0))]
            if st != [1.0, 1.0, 0.0, 0.0]:
                out["st"] = [round(value, 5) for value in st]
            return out
        return None

    def _appearance(self, payload: dict) -> dict[str, Any]:
        saved = payload.get("m_SavedProperties") or {}
        tex_envs = saved.get("m_TexEnvs") or {}
        floats = saved.get("m_Floats") or {}
        colors = saved.get("m_Colors") or {}
        queue = payload.get("m_CustomRenderQueue")
        queue = queue if isinstance(queue, int) and queue >= 0 else None
        out: dict[str, Any] = {"queue": queue}
        textures = {}
        for key, slots in (("base", BASE_SLOTS), ("mro", MRO_SLOTS), ("normal", NORMAL_SLOTS),
                           ("emissive", EMISSIVE_SLOTS)):
            texture = self._texture(tex_envs, slots)
            if texture:
                textures[key] = texture
        if textures:
            out["textures"] = textures
        base_color = _color(colors, "_BaseColor") or _color(colors, "_Color")
        if base_color:
            out["baseColor"] = base_color
        emissive = _color(colors, "_EmissiveColor") or _color(colors, "_EmissionColor")
        if emissive and any(emissive[:3]):
            out["emissiveColor"] = emissive
        for key in ("_BaseColorBrighterScale", "_BaseColorTintCover", "_Metallic", "_RoughnessMin",
                    "_RoughnessMax", "_NormalScale", "_BaseTextureMapCount", "_CullMode", "_Cull"):
            if isinstance(floats.get(key), (int, float)):
                out[key.lstrip("_")] = round(float(floats[key]), 4)
        transparent = (queue or 0) > 2500 or floats.get("_SurfaceType", floats.get("_Surface")) == 1.0
        if transparent:
            out["blend"] = [int(floats.get("_SrcBlend", 5)), int(floats.get("_DstBlend", 10))]
        if any(floats.get(flag) == 1.0 for flag in ("_AlphaClip", "_AlphaTest", "_EnableAlphaTest")) or (
            queue is not None and 2450 <= queue < 2500
        ):
            out["clip"] = round(float(floats.get("_AlphaClipThreshold", floats.get("_Cutoff", 0.5))), 4)
        return out


def _level_chunks(layout: ExportLayout, level: str) -> list[tuple[str, Path, int | None, int | None]]:
    folder = layout.raw / "Streaming" / "PC" / level / "Streaming"
    out = []
    for path in sorted(folder.glob("InitChunkData_*.bytes")):
        match = CHUNK_RE.match(path.name)
        if not match:
            raise SystemExit(f"build_map_scene3d: unexpected chunk name {path}")
        x, z, state, area = match.groups()
        if (state, area) != ("0", "0"):
            continue  # alternate scene states are not part of the base scene
        key = "global" if x is None else f"{x}_{z}"
        out.append((key, path, None if x is None else int(x), None if z is None else int(z)))
    return out


def build_level(layout: ExportLayout, resolver: _Resolver, catalog: StringPathCatalog, level: str,
                output: Path) -> dict[str, Any]:
    chunks = _level_chunks(layout, level)
    if not chunks:
        raise SystemExit(f"build_map_scene3d: no InitChunkData for {level}")
    entities_by_chunk = {}
    mesh_paths: set[str] = set()
    material_paths: set[str] = set()
    stats: Counter = Counter()
    for key, path, _x, _z in chunks:
        rows = list(iter_entity_draws(decode_init_chunk(path.read_bytes())))
        entities_by_chunk[key] = rows
        for entity in rows:
            for draw in entity.draws:
                stats["draws"] += 1
                if draw.lod or draw.shadow_only:
                    stats["drawsSkippedLodOrShadow"] += 1
                    continue
                mesh = catalog.lookup(draw.mesh_hash)
                material = catalog.lookup(draw.material_hash)
                if mesh is None or material is None:
                    stats["drawsHashUnresolved"] += 1
                    continue
                mesh_paths.add(mesh)
                material_paths.add(material)
    resolver.scan({split_mesh_path(path)[0] for path in mesh_paths} | {path.casefold() for path in material_paths}
                  - set(key for _type, key in resolver.asset_rows))
    mesh_index: dict[str, int] = {}
    meshes: list[dict[str, Any]] = []
    for path in sorted(mesh_paths):
        mesh_index[path] = len(meshes)
        meshes.append(resolver.mesh(path))
    material_index: dict[str, int] = {}
    materials: list[dict[str, Any]] = []
    for path in sorted(material_paths):
        material_index[path] = len(materials)
        materials.append(resolver.material(path))
    chunk_rows = []
    level_out = output / level
    for key, path, x, z in chunks:
        instances = []
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        for entity in entities_by_chunk[key]:
            draws = []
            for draw in entity.draws:
                if draw.lod or draw.shadow_only:
                    continue
                mesh = catalog.lookup(draw.mesh_hash)
                material = catalog.lookup(draw.material_hash)
                if mesh is None or material is None:
                    continue
                mesh_row = meshes[mesh_index[mesh]]
                if "rel" not in mesh_row:
                    stats["drawsMeshUnresolved"] += 1
                    continue
                stats["drawsPublished"] += 1
                stats[f"meshTier:{mesh_row['tier']}"] += 1
                stats[f"materialTier:{materials[material_index[material]]['tier']}"] += 1
                draws.append([mesh_index[mesh], draw.submesh, material_index[material]])
            if not draws:
                continue
            matrix = _mirror(entity.matrix)
            for axis in range(3):
                lo[axis] = min(lo[axis], matrix[12 + axis])
                hi[axis] = max(hi[axis], matrix[12 + axis])
            instances.append({"id": entity.entity_id, "n": entity.name, "m": matrix, "d": draws})
        if not instances:
            continue
        write_canonical_json(level_out / "chunks" / f"{key}.json", {"schema": SCHEMA, "level": level,
                                                                     "chunk": key, "instances": instances})
        chunk_rows.append({
            "key": key, "x": x, "z": z, "instances": len(instances),
            "draws": sum(len(row["d"]) for row in instances),
            "bounds": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]],
            "source": path.name,
        })
    index = {
        "schema": SCHEMA,
        "level": level,
        "chunkSize": CHUNK_SIZE,
        "coordinateSystem": "exported OBJ frame (Unity X negated); matrices column-major S*M*S",
        "evidence": {
            "drawRefColumns": "structuralOnly",
            "hashToPath": "exact",
            "meshPathToObject": "exact via asset map Container+Name+PathID; conditional via unique exported name",
            "materialPathToObject": "exact via asset map Container+PathID; conditional via unique exported name",
            "materialTextures": "direct via m_TexEnvs PathID to one exported Texture2D",
            "shading": "approximate HGRP lit preview; not the game's lighting, GI or post-processing",
        },
        "stats": dict(sorted(stats.items())),
        "chunks": chunk_rows,
        "meshes": meshes,
        "materials": materials,
    }
    write_canonical_json(level_out / "index.json", index)
    return {"level": level, "chunks": len(chunk_rows), "draws": stats["drawsPublished"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--level", action="append", default=[], help="streaming level id (repeatable)")
    parser.add_argument("--published-levels", action="store_true",
                        help=f"rebuild the levels scene3d/index.json already lists ({DEFAULT_LEVEL} when none)")
    parser.add_argument("--export-root", type=Path, help="export root (default: configured)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    layout = ExportLayout(args.export_root) if args.export_root else ExportLayout.configured()
    catalog_path = layout.raw / "ExtendData" / "Main" / "StringPathHash.bin"
    if not catalog_path.is_file():
        raise SystemExit(f"build_map_scene3d: missing StringPathHash catalog {catalog_path}")
    catalog = StringPathCatalog(catalog_path.read_bytes(), source=str(catalog_path))
    levels = list(args.level)
    if args.published_levels:
        listed = args.output / "index.json"
        if listed.is_file():
            import json

            levels += [row["level"] for row in json.loads(listed.read_text(encoding="utf-8")).get("levels", [])]
        levels = levels or [DEFAULT_LEVEL]
    if not levels:
        parser.error("name a --level or pass --published-levels")
    resolver = _Resolver(layout)
    published = []
    for level in dict.fromkeys(levels):
        summary = build_level(layout, resolver, catalog, level, args.output)
        print(f"build_map_scene3d: {summary['level']}: {summary['chunks']} chunks, {summary['draws']} draws",
              file=sys.stderr)
        published.append(summary)
    levels_path = args.output / "index.json"
    existing = []
    if levels_path.is_file():
        import json

        existing = [row for row in json.loads(levels_path.read_text(encoding="utf-8")).get("levels", [])
                    if row.get("level") not in {row["level"] for row in published}]
    write_canonical_json(levels_path, {"schema": SCHEMA, "levels": sorted(existing + published,
                                                                         key=lambda row: row["level"])})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
