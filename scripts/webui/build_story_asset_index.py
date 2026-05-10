from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path

from build_story_paths import _asset_source_family, resolve_asset_source_roots, resolve_material_source_roots

ASSET_KIND_BY_EXT = {
    ".obj": "model",
    ".fbx": "model",
    ".gltf": "model",
    ".glb": "model",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".bmp": "image",
    ".gif": "image",
    ".tga": "image",
    ".tif": "image",
    ".tiff": "image",
}
VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mov",
    ".avi",
    ".m4v",
    ".ogv",
    ".usm",
}
ASSET_SINGLE_PREFIX_RE = re.compile(r"^[A-Za-z]_")
ASSET_LOD_SUFFIX_RE = re.compile(r"(?:[_-])lod\d+$", re.IGNORECASE)

def build_asset_index(out_path: Path, *, root: Path, export_root: Path) -> dict:
    """Scan exported image/model files into a lightweight search index."""
    entries: list[dict] = []
    counts = defaultdict(int)
    image_rels_by_stem: dict[str, list[str]] = defaultdict(list)
    model_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    model_rels_by_base: dict[str, list[str]] = defaultdict(list)
    obj_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    obj_rels_by_base: dict[str, list[str]] = defaultdict(list)
    asset_roots = resolve_asset_source_roots(export_root)
    material_roots = resolve_material_source_roots(export_root)
    source_root_labels = {
        source: (path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path))
        for source, path in [*asset_roots, *material_roots]
    }

    def strip_asset_prefix(name: str) -> str:
        return ASSET_SINGLE_PREFIX_RE.sub("", name, count=1)

    def normalize_model_base(stem: str) -> str:
        return ASSET_LOD_SUFFIX_RE.sub("", strip_asset_prefix(stem)).lower()

    def normalize_material_base(stem: str) -> str:
        return strip_asset_prefix(stem).lower()

    def split_source_name(name: str) -> tuple[str, int | None]:
        match = re.match(r"^(.*?)(\d+)?$", name)
        if not match:
            return name, None
        prefix, suffix = match.groups()
        return prefix, int(suffix) if suffix else None

    def choose_preferred_rel(candidates: list[str], source: str) -> str:
        if not candidates:
            return ""
        source_prefix = f"{source}/" if source else ""
        for rel_path in candidates:
            if source_prefix and rel_path.startswith(source_prefix):
                return rel_path

        source_family = _asset_source_family(source)
        for rel_path in candidates:
            rel_source = rel_path.split("/", 1)[0]
            if _asset_source_family(rel_source) == source_family:
                return rel_path

        src_prefix, src_num = split_source_name(source_family)

        def affinity(rel_path: str) -> tuple[int, int, str]:
            rel_source = _asset_source_family(rel_path.split("/", 1)[0])
            rel_prefix, rel_num = split_source_name(rel_source)
            if rel_source == source_family:
                return (0, 0, rel_path)
            if rel_prefix == src_prefix:
                if src_num is not None and rel_num is not None:
                    return (1, abs(rel_num - src_num), rel_path)
                if src_num is None and rel_num is None:
                    return (1, 0, rel_path)
                return (2, 9999, rel_path)
            return (3, 0, rel_path)

        return min(candidates, key=affinity)

    def extract_material_texture_refs(material_payload: dict) -> list[dict]:
        tex_envs = ((material_payload.get("m_SavedProperties") or {}).get("m_TexEnvs") or {})
        out: list[dict] = []
        for slot, tex_env in sorted(tex_envs.items()):
            texture = (tex_env or {}).get("m_Texture") or {}
            texture_name = str(texture.get("Name") or "").strip()
            if not texture_name or texture.get("IsNull"):
                continue
            out.append({
                "slot": slot,
                "name": texture_name,
            })
        return out

    def append_unique(items: list[dict], candidate: dict) -> None:
        if candidate not in items:
            items.append(candidate)

    label_text = ", ".join(f"{source}:{label}" for source, label in source_root_labels.items()) or str(export_root)
    print(f"\nScanning exported image and model assets from {label_text}...")
    for source, source_root in asset_roots:
        for dirpath, dirnames, filenames in os.walk(source_root):
            dirnames.sort()
            filenames.sort()
            base_dir = Path(dirpath)
            for filename in filenames:
                suffix = Path(filename).suffix.lower()
                kind = ASSET_KIND_BY_EXT.get(suffix)
                if not kind:
                    continue

                path = base_dir / filename
                rel_suffix = path.relative_to(source_root).as_posix()
                rel_path = f"{source}/{rel_suffix}" if rel_suffix else source
                entry = {
                    "k": kind,
                    "r": rel_path,
                    "s": path.stat().st_size,
                }
                entries.append(entry)
                stem = path.stem
                if kind == "image":
                    image_rels_by_stem[stem.lower()].append(rel_path)
                elif kind == "model":
                    model_base = normalize_model_base(stem)
                    source_family = _asset_source_family(source).lower()
                    entry["_mb"] = model_base
                    model_rels_by_source_base[(source_family, model_base)].append(rel_path)
                    model_rels_by_base[model_base].append(rel_path)
                    if suffix == ".obj":
                        obj_rels_by_source_base[(source_family, model_base)].append(rel_path)
                        obj_rels_by_base[model_base].append(rel_path)
                counts["total"] += 1
                counts[kind] += 1

    relations: dict[str, dict] = {}
    material_count = 0
    texture_link_count = 0
    preview_proxy_count = 0

    for entry in entries:
        if entry.get("k") != "model":
            continue

        model_base = str(entry.pop("_mb", "") or "")
        rel_path = str(entry.get("r") or "")
        if not model_base or Path(rel_path).suffix.lower() == ".obj":
            continue

        source = rel_path.split("/", 1)[0]
        preview_rel = choose_preferred_rel(
            obj_rels_by_source_base.get((_asset_source_family(source).lower(), model_base))
            or obj_rels_by_base.get(model_base)
            or [],
            source,
        )
        if preview_rel:
            entry["p"] = preview_rel
            preview_proxy_count += 1

    for source, source_root in material_roots:
        for material_path in sorted(source_root.rglob("Material/*.json")):
            try:
                with material_path.open(encoding="utf-8") as f:
                    material_payload = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            texture_refs = extract_material_texture_refs(material_payload)
            if not texture_refs:
                continue

            material_count += 1
            rel_suffix = material_path.relative_to(source_root).as_posix()
            material_rel = f"{source}/{rel_suffix}" if rel_suffix else source
            material_name = material_path.stem
            material_ref = {
                "name": material_name,
                "rel": material_rel,
            }

            material_base = normalize_material_base(material_name)
            source_family = _asset_source_family(source).lower()
            model_rels = (
                model_rels_by_source_base.get((source_family, material_base))
                or model_rels_by_base.get(material_base)
                or []
            )

            resolved_texture_refs: list[dict] = []
            for ref in texture_refs:
                image_rel = choose_preferred_rel(image_rels_by_stem.get(ref["name"].lower(), []), source)
                resolved_ref = {
                    "slot": ref["slot"],
                    "name": ref["name"],
                }
                if image_rel:
                    resolved_ref["rel"] = image_rel
                resolved_texture_refs.append(resolved_ref)
                if image_rel:
                    texture_link_count += 1

            for model_rel in model_rels:
                model_relations = relations.setdefault(model_rel, {})
                materials = model_relations.setdefault("materials", [])
                textures = model_relations.setdefault("textures", [])
                append_unique(materials, material_ref)
                for texture_ref in resolved_texture_refs:
                    append_unique(textures, texture_ref)

            for texture_ref in resolved_texture_refs:
                image_rel = texture_ref.get("rel")
                if not image_rel:
                    continue

                image_relations = relations.setdefault(image_rel, {})
                back_materials = image_relations.setdefault("referencedByMaterials", [])
                append_unique(back_materials, {
                    "name": material_name,
                    "rel": material_rel,
                    "slot": texture_ref["slot"],
                })

                if model_rels:
                    back_models = image_relations.setdefault("referencedByModels", [])
                    for model_rel in model_rels:
                        append_unique(back_models, {
                            "name": Path(model_rel).stem,
                            "rel": model_rel,
                        })

    payload = {
        "generated": int(time.time()),
        "root": export_root.relative_to(root).as_posix() if export_root.is_relative_to(root) else str(export_root),
        "sourceRoots": source_root_labels,
        "counts": {
            "total": counts["total"],
            "image": counts["image"],
            "model": counts["model"],
        },
        "entries": entries,
        "relations": relations,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(
        "Asset index written:",
        out_path,
        (
            f"({counts['total']} assets; {counts['image']} images; {counts['model']} models; "
            f"{material_count} materials; {texture_link_count} texture links; "
            f"{preview_proxy_count} model preview proxies)"
        )
    )
    return {
        "sourceRoot": label_text,
        "sourceRoots": source_root_labels,
        "assets": counts["total"],
        "images": counts["image"],
        "models": counts["model"],
        "materials": material_count,
        "previewModels": preview_proxy_count,
        "indexBytes": out_path.stat().st_size,
    }


def build_video_index(out_path: Path, *, root: Path, export_root: Path) -> dict:
    """Scan exported video files into a small exact-name lookup index."""
    entries: list[dict] = []
    counts = defaultdict(int)
    asset_roots = resolve_asset_source_roots(export_root)
    source_root_labels = {
        source: (path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path))
        for source, path in asset_roots
    }

    label_text = ", ".join(f"{source}:{label}" for source, label in source_root_labels.items()) or str(export_root)
    print(f"\nScanning exported video assets from {label_text}...")
    for source, source_root in asset_roots:
        for dirpath, dirnames, filenames in os.walk(source_root):
            dirnames.sort()
            filenames.sort()
            base_dir = Path(dirpath)
            for filename in filenames:
                suffix = Path(filename).suffix.lower()
                if suffix not in VIDEO_EXTENSIONS:
                    continue

                path = base_dir / filename
                rel_suffix = path.relative_to(source_root).as_posix()
                rel_path = f"{source}/{rel_suffix}" if rel_suffix else source
                entries.append({
                    "k": "video",
                    "r": rel_path,
                    "s": path.stat().st_size,
                })
                counts["total"] += 1
                counts["video"] += 1

    payload = {
        "generated": int(time.time()),
        "root": export_root.relative_to(root).as_posix() if export_root.is_relative_to(root) else str(export_root),
        "sourceRoots": source_root_labels,
        "counts": {
            "total": counts["total"],
            "video": counts["video"],
        },
        "entries": entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(
        "Video index written:",
        out_path,
        f"({counts['video']} videos)",
    )
    return {
        "sourceRoot": label_text,
        "sourceRoots": source_root_labels,
        "assets": counts["total"],
        "videos": counts["video"],
        "indexBytes": out_path.stat().st_size,
    }
