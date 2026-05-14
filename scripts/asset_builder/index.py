from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from source_paths import (
    _asset_source_family,
    resolve_asset_source_roots,
    resolve_material_source_roots,
)
from common import rel_path, write_json

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


def _strip_asset_prefix(name: str) -> str:
    return ASSET_SINGLE_PREFIX_RE.sub("", name, count=1)


def _normalize_model_base(stem: str) -> str:
    return ASSET_LOD_SUFFIX_RE.sub("", _strip_asset_prefix(stem)).lower()


def _normalize_material_base(stem: str) -> str:
    return _strip_asset_prefix(stem).lower()


def _split_source_name(name: str) -> tuple[str, int | None]:
    match = re.match(r"^(.*?)(\d+)?$", name)
    if not match:
        return name, None
    prefix, suffix = match.groups()
    return prefix, int(suffix) if suffix else None


def _choose_preferred_rel(candidates: list[str], source: str) -> str:
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

    src_prefix, src_num = _split_source_name(source_family)

    def affinity(rel_path: str) -> tuple[int, int, str]:
        rel_source = _asset_source_family(rel_path.split("/", 1)[0])
        rel_prefix, rel_num = _split_source_name(rel_source)
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


def _extract_material_texture_refs(material_payload: dict) -> list[dict]:
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


def _append_unique(items: list[dict], candidate: dict) -> None:
    if candidate not in items:
        items.append(candidate)


def _label_text(labels: dict[str, str], fallback: Path) -> str:
    return ", ".join(f"{source}:{label}" for source, label in labels.items()) or str(fallback)


def scan_exported_media_assets(
    *,
    root: Path,
    export_root: Path,
) -> dict[str, Any]:
    """Scan exported media once and derive image/model/video indexes from it."""
    asset_entries: list[dict] = []
    video_entries: list[dict] = []
    counts = defaultdict(int)
    video_counts = defaultdict(int)
    image_rels_by_stem: dict[str, list[str]] = defaultdict(list)
    model_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    model_rels_by_base: dict[str, list[str]] = defaultdict(list)
    obj_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    obj_rels_by_base: dict[str, list[str]] = defaultdict(list)

    asset_roots = resolve_asset_source_roots(export_root)
    material_roots = resolve_material_source_roots(export_root)
    media_root_labels = {source: rel_path(path, root) for source, path in asset_roots}
    asset_root_labels = {
        source: rel_path(path, root)
        for source, path in [*asset_roots, *material_roots]
    }

    print(f"\nScanning exported media assets from {_label_text(media_root_labels, export_root)}...")
    for source, source_root in asset_roots:
        for dirpath, dirnames, filenames in os.walk(source_root):
            dirnames.sort()
            filenames.sort()
            base_dir = Path(dirpath)
            for filename in filenames:
                path = base_dir / filename
                suffix = path.suffix.lower()
                rel_suffix = path.relative_to(source_root).as_posix()
                asset_rel = f"{source}/{rel_suffix}" if rel_suffix else source
                size = path.stat().st_size

                kind = ASSET_KIND_BY_EXT.get(suffix)
                if kind:
                    entry = {
                        "k": kind,
                        "r": asset_rel,
                        "s": size,
                    }
                    asset_entries.append(entry)
                    stem = path.stem
                    if kind == "image":
                        image_rels_by_stem[stem.lower()].append(asset_rel)
                    elif kind == "model":
                        model_base = _normalize_model_base(stem)
                        source_family = _asset_source_family(source).lower()
                        entry["_mb"] = model_base
                        model_rels_by_source_base[(source_family, model_base)].append(asset_rel)
                        model_rels_by_base[model_base].append(asset_rel)
                        if suffix == ".obj":
                            obj_rels_by_source_base[(source_family, model_base)].append(asset_rel)
                            obj_rels_by_base[model_base].append(asset_rel)
                    counts["total"] += 1
                    counts[kind] += 1

                if suffix in VIDEO_EXTENSIONS:
                    video_entries.append({
                        "k": "video",
                        "r": asset_rel,
                        "s": size,
                    })
                    video_counts["total"] += 1
                    video_counts["video"] += 1

    relations: dict[str, dict] = {}
    material_count = 0
    texture_link_count = 0
    preview_proxy_count = 0

    for entry in asset_entries:
        if entry.get("k") != "model":
            continue

        model_base = str(entry.pop("_mb", "") or "")
        model_rel = str(entry.get("r") or "")
        if not model_base or Path(model_rel).suffix.lower() == ".obj":
            continue

        source = model_rel.split("/", 1)[0]
        preview_rel = _choose_preferred_rel(
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

            texture_refs = _extract_material_texture_refs(material_payload)
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

            material_base = _normalize_material_base(material_name)
            source_family = _asset_source_family(source).lower()
            model_rels = (
                model_rels_by_source_base.get((source_family, material_base))
                or model_rels_by_base.get(material_base)
                or []
            )

            resolved_texture_refs: list[dict] = []
            for ref in texture_refs:
                image_rel = _choose_preferred_rel(image_rels_by_stem.get(ref["name"].lower(), []), source)
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
                _append_unique(materials, material_ref)
                for texture_ref in resolved_texture_refs:
                    _append_unique(textures, texture_ref)

            for texture_ref in resolved_texture_refs:
                image_rel = texture_ref.get("rel")
                if not image_rel:
                    continue

                image_relations = relations.setdefault(image_rel, {})
                back_materials = image_relations.setdefault("referencedByMaterials", [])
                _append_unique(back_materials, {
                    "name": material_name,
                    "rel": material_rel,
                    "slot": texture_ref["slot"],
                })

                if model_rels:
                    back_models = image_relations.setdefault("referencedByModels", [])
                    for model_rel in model_rels:
                        _append_unique(back_models, {
                            "name": Path(model_rel).stem,
                            "rel": model_rel,
                        })

    return {
        "assetEntries": asset_entries,
        "videoEntries": video_entries,
        "counts": counts,
        "videoCounts": video_counts,
        "assetRootLabels": asset_root_labels,
        "mediaRootLabels": media_root_labels,
        "relations": relations,
        "materials": material_count,
        "textureLinks": texture_link_count,
        "previewModels": preview_proxy_count,
    }


def _asset_payload(scan: dict[str, Any], *, root: Path, export_root: Path) -> dict:
    counts = scan["counts"]
    return {
        "generated": int(time.time()),
        "root": rel_path(export_root, root),
        "sourceRoots": scan["assetRootLabels"],
        "counts": {
            "total": counts["total"],
            "image": counts["image"],
            "model": counts["model"],
        },
        "entries": scan["assetEntries"],
        "relations": scan["relations"],
    }


def _video_payload(scan: dict[str, Any], *, root: Path, export_root: Path) -> dict:
    counts = scan["videoCounts"]
    return {
        "generated": int(time.time()),
        "root": rel_path(export_root, root),
        "sourceRoots": scan["mediaRootLabels"],
        "counts": {
            "total": counts["total"],
            "video": counts["video"],
        },
        "entries": scan["videoEntries"],
    }


def _asset_stats(scan: dict[str, Any], out_path: Path, export_root: Path) -> dict:
    counts = scan["counts"]
    label_text = _label_text(scan["assetRootLabels"], export_root)
    return {
        "sourceRoot": label_text,
        "sourceRoots": scan["assetRootLabels"],
        "assets": counts["total"],
        "images": counts["image"],
        "models": counts["model"],
        "materials": scan["materials"],
        "previewModels": scan["previewModels"],
        "indexBytes": out_path.stat().st_size,
    }


def _video_stats(scan: dict[str, Any], out_path: Path, export_root: Path) -> dict:
    counts = scan["videoCounts"]
    return {
        "sourceRoot": _label_text(scan["mediaRootLabels"], export_root),
        "sourceRoots": scan["mediaRootLabels"],
        "assets": counts["total"],
        "videos": counts["video"],
        "indexBytes": out_path.stat().st_size,
    }


def build_asset_index(
    out_path: Path,
    *,
    root: Path,
    export_root: Path,
) -> dict:
    """Scan exported image/model files into a lightweight search index."""
    scan = scan_exported_media_assets(
        root=root,
        export_root=export_root,
    )
    payload = _asset_payload(scan, root=root, export_root=export_root)
    write_json(out_path, payload)
    counts = scan["counts"]
    print(
        "Asset index written:",
        out_path,
        (
            f"({counts['total']} assets; {counts['image']} images; {counts['model']} models; "
            f"{scan['materials']} materials; {scan['textureLinks']} texture links; "
            f"{scan['previewModels']} model preview proxies)"
        ),
    )
    return _asset_stats(scan, out_path, export_root)


def build_video_index(
    out_path: Path,
    *,
    root: Path,
    export_root: Path,
) -> dict:
    """Scan exported video files into a small exact-name lookup index."""
    scan = scan_exported_media_assets(
        root=root,
        export_root=export_root,
    )
    payload = _video_payload(scan, root=root, export_root=export_root)
    write_json(out_path, payload)
    counts = scan["videoCounts"]
    print("Video index written:", out_path, f"({counts['video']} videos)")
    return _video_stats(scan, out_path, export_root)


def build_asset_indexes(
    asset_out_path: Path,
    video_out_path: Path,
    *,
    root: Path,
    export_root: Path,
) -> tuple[dict, dict]:
    """Build image/model and video indexes from a single filesystem scan."""
    scan = scan_exported_media_assets(
        root=root,
        export_root=export_root,
    )
    asset_payload = _asset_payload(scan, root=root, export_root=export_root)
    video_payload = _video_payload(scan, root=root, export_root=export_root)
    write_json(asset_out_path, asset_payload)
    write_json(video_out_path, video_payload)

    asset_counts = scan["counts"]
    video_counts = scan["videoCounts"]
    print(
        "Asset index written:",
        asset_out_path,
        (
            f"({asset_counts['total']} assets; {asset_counts['image']} images; "
            f"{asset_counts['model']} models; {scan['materials']} materials; "
            f"{scan['textureLinks']} texture links; {scan['previewModels']} model preview proxies)"
        ),
    )
    print("Video index written:", video_out_path, f"({video_counts['video']} videos)")
    return (
        _asset_stats(scan, asset_out_path, export_root),
        _video_stats(scan, video_out_path, export_root),
    )
