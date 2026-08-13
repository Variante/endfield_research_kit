from __future__ import annotations

import base64
import binascii
import json
import hashlib
import os
import re
import struct
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from source_paths import (
    _asset_source_family,
    resolve_asset_source_roots,
    resolve_material_source_roots,
)
from common import (
    path_id_export_base_stem,
    path_id_export_path_id,
    rel_path,
    rel_requires_path_id_export_name,
    write_json,
)

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
JSON_EXTENSIONS = {
    ".json",
}
JSON_SCRIPT_SEARCH_CHAR_LIMIT = 6000
JSON_SCRIPT_SCAN_PREFIX_BYTES = 8192
JSON_SCRIPT_SEARCH_MAX_FILE_BYTES = 5_000_000
ASSET_HASH_HEADER_BYTES = 4096
ASSET_HASH_CHUNK_SIZE = 1024 * 1024
BASE64_TEXT_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")

BROWSER_JSON_TYPE_DIRS = {
    "AnimatorController",
    "AnimatorOverrideController",
    "AvatarMask",
    "Material",
    "MonoScript",
    "PlayableDirector",
    "PreloadData",
    "TextAsset",
}
ASSET_SINGLE_PREFIX_RE = re.compile(r"^[A-Za-z]_")
ASSET_LOD_SUFFIX_RE = re.compile(r"(?:[_-])lod\d+$", re.IGNORECASE)
MATERIAL_TEXTURE_SUFFIXES = (
    "_basemap",
    "_bumpmap",
    "_normalmap",
    "_emissionmap",
    "_metallicglossmap",
    "_maskmap",
    "_occlusionmap",
    "_detailmap",
    "_specglossmap",
)
IMAGE_CATEGORY_PREFIXES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("pic_",), "character"),
    (("icon_round",), "icon_round"),
    (("icon_",), "icon"),
    (("item_topic",), "item_topic"),
    (("item_potential",), "item_potential"),
    (("item_",), "item"),
    (("business_card",), "business_card"),
    (("sns_",), "sns"),
    (("bg_", "background", "activity_bg"), "background"),
    (("logo",), "logo"),
    (("loading",), "loading"),
    (("tutorial",), "tutorial"),
    (("cg_",), "cg"),
    (("splash",), "splash"),
    (("chr_",), "chr_thumb"),
    (("title",), "title"),
    (("tips",), "tips"),
    (("achv_", "achievement_", "achievement-"), "achievement"),
    (("wpn_", "weapon_", "weapon-"), "weapon"),
    (("activity_",), "activity"),
    (("prts_",), "prts"),
    (("dung", "slu__dung"), "dungeon"),
    (("slu__map",), "map"),
    (("slu__ld",), "level"),
    (("slu__",), "snapshot"),
    (("dlg_",), "dialog"),
    (("gacha",), "gacha"),
    (("image_", "img_", "img-"), "image"),
    (("deco_", "deco-", "line_", "line-"), "decoration"),
    (("btn_", "btn-"), "button"),
    (("common_", "common-"), "common_ui"),
    (("uisprite",), "ui_sprite"),
    (("emoji_", "emoji-"), "emoji"),
    (("guide_", "guide-"), "guide"),
    (("tech_", "tech-"), "tech"),
    (("eny_", "eny-", "enemy_", "enemy-"), "enemy"),
    (("wiki_", "wiki-"), "wiki"),
    (("shop_", "shop-", "monthlypass"), "shop"),
    (("map_", "map-"), "map"),
    (("collection_", "collection-"), "collection"),
    (("document_", "document-"), "document"),
    (("seasonal_", "seasonal-"), "seasonal"),
    (("textfactorycommonui",), "factory_ui"),
    (("dwr_", "dwr-"), "dwr"),
    (("facskill_", "facskill-"), "factory_skill"),
    (("aibark_", "aibark-"), "aibark"),
    (("reception_", "reception-"), "reception"),
    (("racing_", "racing-"), "racing"),
    (("remotecomm_", "remotecomm-"), "remotecomm"),
    (("potential_", "potential-"), "item_potential"),
    (("boss_", "boss-"), "boss"),
    (("snapshot_", "snapshot-"), "snapshot"),
    (("poster_", "poster-"), "poster"),
    (("adventure_", "adventure-"), "adventure"),
    (("mail_", "mail-"), "mail"),
    (("chapter_", "chapter-"), "chapter"),
    (("cover_", "cover-"), "cover"),
    (("reading_", "reading-"), "reading"),
    (("text_", "text-"), "text"),
    (("ui_", "ui-"), "ui"),
    (("prgs_", "prgs-"), "progress"),
    (("decal_", "decal-"), "decal"),
)


def _image_category_name_candidates(name: str) -> list[str]:
    lower = (name or "").lower()
    candidates = [lower] if lower else []
    stripped = _strip_asset_prefix(lower)
    if stripped and stripped != lower:
        candidates.append(stripped)
    return candidates


def _has_name_token(name: str, token: str) -> bool:
    return bool(re.search(rf"(?:^|[_-]){re.escape(token)}(?:$|[_-])", name))


def classify_image_name(name: str) -> str:
    if not name:
        return "other"
    for lower in _image_category_name_candidates(name):
        for prefixes, category in IMAGE_CATEGORY_PREFIXES:
            if lower.startswith(prefixes):
                return category
        if _has_name_token(lower, "boss"):
            return "boss"
        if _has_name_token(lower, "enemy"):
            return "enemy"
        if lower.startswith("map02") or lower.startswith("map03"):
            return "map"
    return "other"


def is_material_like_texture_name(name: str) -> bool:
    if not name:
        return False
    lower = name.lower()
    if len(lower) > 2 and lower[0] == "t" and lower[1] == "_":
        return True
    if lower.startswith("terrain"):
        return True
    if len(lower) >= 2 and lower[1] == "_" and lower[0] in {"h", "m", "l"}:
        return True
    if lower.startswith("layer"):
        return True
    if lower.startswith("mask"):
        return True
    if lower.startswith("splatindexmap") or lower.startswith("etchlist"):
        return True
    return lower.endswith(MATERIAL_TEXTURE_SUFFIXES)


def _strip_asset_prefix(name: str) -> str:
    return ASSET_SINGLE_PREFIX_RE.sub("", name, count=1)


def _normalize_model_base(stem: str) -> str:
    return ASSET_LOD_SUFFIX_RE.sub("", _strip_asset_prefix(stem)).lower()


def _normalize_material_base(stem: str) -> str:
    return _strip_asset_prefix(stem).lower()


def _logical_export_stem(rel: str, stem: str) -> tuple[str, str] | None:
    base_stem = path_id_export_base_stem(stem)
    path_id = path_id_export_path_id(stem)
    if rel_requires_path_id_export_name(rel):
        if not base_stem:
            return None
        return base_stem, path_id
    return base_stem or stem, path_id


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


def _normalize_path_id_hex(value: Any) -> str:
    if value in (None, "", 0, "0"):
        return ""
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return ""
        try:
            number = int(raw, 16) if raw.lower().startswith("0x") else int(raw, 10)
        except ValueError:
            try:
                number = int(raw, 16)
            except ValueError:
                return ""
    else:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return ""
    if number == 0:
        return ""
    return f"{number & ((1 << 64) - 1):016X}"


def _extract_material_texture_refs(material_payload: dict) -> list[dict]:
    tex_envs = ((material_payload.get("m_SavedProperties") or {}).get("m_TexEnvs") or {})
    out: list[dict] = []
    for slot, tex_env in sorted(tex_envs.items()):
        texture = (tex_env or {}).get("m_Texture") or {}
        if texture.get("IsNull"):
            continue
        texture_name = str(texture.get("Name") or "").strip()
        path_id = _normalize_path_id_hex(texture.get("m_PathID", texture.get("PathID")))
        if not texture_name and not path_id:
            continue
        ref = {"slot": slot}
        if texture_name:
            ref["name"] = texture_name
        if path_id:
            ref["pid"] = path_id
        out.append(ref)
    return out


def _append_unique(items: list[dict], candidate: dict) -> None:
    if candidate not in items:
        items.append(candidate)


def _label_text(labels: dict[str, str], fallback: Path) -> str:
    return ", ".join(f"{source}:{label}" for source, label in labels.items()) or str(fallback)


def _browser_asset_kind_for_suffix(
    suffix: str,
    *,
    include_regular_assets: bool = True,
    include_media: bool = True,
    include_json: bool = True,
) -> str:
    if include_regular_assets and suffix in ASSET_KIND_BY_EXT:
        return ASSET_KIND_BY_EXT[suffix]
    if include_media and suffix in VIDEO_EXTENSIONS:
        return "video"
    if include_json and suffix in JSON_EXTENSIONS:
        return "json"
    return ""


def _should_index_browser_json(path: Path, source_root: Path) -> bool:
    if path.suffix.lower() not in JSON_EXTENSIONS:
        return False
    rel_parts = path.relative_to(source_root).parts
    if not rel_parts:
        return False
    return rel_parts[0] in BROWSER_JSON_TYPE_DIRS

def _looks_like_base64_text(value: str) -> bool:
    compact = re.sub(r"\s+", "", value or "")
    return len(compact) >= 8 and len(compact) % 4 != 1 and bool(BASE64_TEXT_RE.fullmatch(compact))


def _is_mostly_readable_text(value: str) -> bool:
    if not value:
        return False
    checked = 0
    bad = 0
    for ch in value[:4096]:
        checked += 1
        code = ord(ch)
        if code == 0xFFFD or (code < 32 and ch not in "\n\r\t"):
            bad += 1
    return checked > 0 and bad / checked <= 0.04


def _normalize_decoded_script_text(value: str) -> str:
    cleaned = (value or "").replace("\x00", "").strip()
    if not cleaned or not _is_mostly_readable_text(cleaned):
        return ""
    return cleaned[:JSON_SCRIPT_SEARCH_CHAR_LIMIT]


def _decode_script_value(value: Any) -> str:
    if isinstance(value, str):
        if _looks_like_base64_text(value):
            compact = re.sub(r"\s+", "", value)
            remainder = len(compact) % 4
            if remainder:
                compact += "=" * (4 - remainder)
            try:
                raw = base64.b64decode(compact, validate=True)
                return _normalize_decoded_script_text(raw.decode("utf-8", errors="replace"))
            except (binascii.Error, UnicodeError, ValueError):
                return ""
        return _normalize_decoded_script_text(value)

    if isinstance(value, list) and value and all(isinstance(item, int) and 0 <= item <= 255 for item in value):
        return _normalize_decoded_script_text(bytes(value).decode("utf-8", errors="replace"))

    return ""


def _iter_m_script_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "m_Script":
                yield item
            else:
                yield from _iter_m_script_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_m_script_values(item)


def _decoded_m_script_search_text(path: Path) -> str:
    try:
        if path.stat().st_size > JSON_SCRIPT_SEARCH_MAX_FILE_BYTES:
            return ""
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            prefix = f.read(JSON_SCRIPT_SCAN_PREFIX_BYTES)
            if "m_Script" not in prefix:
                return ""
            f.seek(0)
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""

    chunks: list[str] = []
    total = 0
    for value in _iter_m_script_values(payload):
        decoded = _decode_script_value(value)
        if not decoded:
            continue
        chunks.append(decoded)
        total += len(decoded)
        if total >= JSON_SCRIPT_SEARCH_CHAR_LIMIT:
            break

    if not chunks:
        return ""
    compact = re.sub(r"\s+", " ", " ".join(chunks)).strip()
    return compact[:JSON_SCRIPT_SEARCH_CHAR_LIMIT]



def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(ASSET_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _header_signature(path: Path) -> str:
    try:
        with path.open("rb") as fh:
            return fh.read(ASSET_HASH_HEADER_BYTES).hex()
    except OSError:
        return ""


def _image_dimensions(path: Path) -> tuple[int, int] | None:
    """Read image dimensions without adding a runtime imaging dependency.

    The asset index is also used by the compact Gameplay sidecar to choose
    between exported Sprite/Texture2D variants.  File size is only a proxy
    for resolution, so keep the real pixel dimensions when the common image
    headers expose them.
    """
    try:
        with path.open("rb") as fh:
            header = fh.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                width, height = struct.unpack(">II", header[16:24])
                return (width, height) if width and height else None
            if header[:6] in {b"GIF87a", b"GIF89a"} and len(header) >= 10:
                width, height = struct.unpack("<HH", header[6:10])
                return (width, height) if width and height else None
            if header[:2] == b"BM" and len(header) >= 26:
                width, height = struct.unpack("<ii", header[18:26])
                width, height = abs(width), abs(height)
                return (width, height) if width and height else None
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                chunk = header[12:16]
                if chunk == b"VP8X" and len(header) >= 30:
                    width = 1 + int.from_bytes(header[24:27], "little")
                    height = 1 + int.from_bytes(header[27:30], "little")
                    return (width, height) if width and height else None
                if chunk == b"VP8L" and len(header) >= 25 and header[20] == 0x2F:
                    packed = int.from_bytes(header[21:25], "little")
                    width = 1 + (packed & 0x3FFF)
                    height = 1 + ((packed >> 14) & 0x3FFF)
                    return (width, height) if width and height else None
                if chunk == b"VP8 " and len(header) >= 30 and header[23:26] == b"\x9d\x01\x2a":
                    width = int.from_bytes(header[26:28], "little") & 0x3FFF
                    height = int.from_bytes(header[28:30], "little") & 0x3FFF
                    return (width, height) if width and height else None

            if header[:2] == b"\xff\xd8":
                # JPEG stores dimensions in one of the SOF marker segments.
                fh.seek(2)
                sof_markers = {
                    *range(0xC0, 0xC4),
                    *range(0xC5, 0xC8),
                    *range(0xC9, 0xCC),
                    *range(0xCD, 0xD0),
                }
                while True:
                    byte = fh.read(1)
                    if not byte:
                        break
                    if byte != b"\xFF":
                        continue
                    marker_byte = fh.read(1)
                    while marker_byte == b"\xFF":
                        marker_byte = fh.read(1)
                    if not marker_byte:
                        break
                    marker = marker_byte[0]
                    if marker in {0xD8, 0xD9}:
                        continue
                    length_bytes = fh.read(2)
                    if len(length_bytes) != 2:
                        break
                    length = int.from_bytes(length_bytes, "big")
                    if length < 2:
                        break
                    if marker in sof_markers:
                        payload = fh.read(length - 2)
                        if len(payload) >= 5:
                            height = int.from_bytes(payload[1:3], "big")
                            width = int.from_bytes(payload[3:5], "big")
                            return (width, height) if width and height else None
                    else:
                        fh.seek(length - 2, os.SEEK_CUR)

            if path.suffix.lower() == ".tga" and len(header) >= 16:
                width, height = struct.unpack("<HH", header[12:16])
                return (width, height) if width and height else None
    except (OSError, struct.error, ValueError):
        return None
    return None


def _add_duplicate_candidate_hashes(entries: list[dict], paths_by_rel: dict[str, Path]) -> None:
    coarse_counts: Counter[tuple[str, str, int]] = Counter()
    for entry in entries:
        rel = str(entry.get("r") or "")
        key = (str(entry.get("k") or ""), Path(rel).suffix.lower(), int(entry.get("s") or 0))
        coarse_counts[key] += 1

    header_counts: Counter[tuple[str, str, int, str]] = Counter()
    header_keys: dict[str, tuple[str, str, int, str]] = {}
    for entry in entries:
        rel = str(entry.get("r") or "")
        coarse_key = (str(entry.get("k") or ""), Path(rel).suffix.lower(), int(entry.get("s") or 0))
        if coarse_counts[coarse_key] <= 1:
            continue
        path = paths_by_rel.get(rel)
        if not path:
            continue
        key = (*coarse_key, _header_signature(path))
        header_keys[rel] = key
        header_counts[key] += 1

    for entry in entries:
        rel = str(entry.get("r") or "")
        key = header_keys.get(rel)
        if not key or header_counts[key] <= 1:
            continue
        path = paths_by_rel.get(rel)
        if path:
            entry["h"] = _file_sha256(path)

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
    image_category_counts = defaultdict(int)
    material_like_image_count = 0
    image_rels_by_stem: dict[str, list[str]] = defaultdict(list)
    image_rels_by_pid: dict[str, list[str]] = defaultdict(list)
    model_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    model_rels_by_base: dict[str, list[str]] = defaultdict(list)
    obj_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    obj_rels_by_base: dict[str, list[str]] = defaultdict(list)
    asset_paths_by_rel: dict[str, Path] = {}

    asset_roots = resolve_asset_source_roots(export_root)
    material_roots = resolve_material_source_roots(export_root)
    media_root_labels = {source: rel_path(path, root) for source, path in asset_roots}
    asset_root_labels = {
        source: rel_path(path, root)
        for source, path in [*asset_roots, *material_roots]
    }

    def add_asset_file(
        *,
        source: str,
        source_root: Path,
        path: Path,
        include_regular_assets: bool = True,
        include_media: bool = True,
        include_json: bool = True,
    ) -> None:
        nonlocal material_like_image_count
        suffix = path.suffix.lower()
        kind = _browser_asset_kind_for_suffix(
            suffix,
            include_regular_assets=include_regular_assets,
            include_media=include_media,
            include_json=include_json,
        )
        if not kind:
            return

        rel_suffix = path.relative_to(source_root).as_posix()
        asset_rel = f"{source}/{rel_suffix}" if rel_suffix else source
        logical = _logical_export_stem(asset_rel, path.stem)
        if logical is None:
            return
        stem, path_id = logical
        size = path.stat().st_size
        entry = {
            "k": kind,
            "r": asset_rel,
            "s": size,
        }
        if path_id:
            entry["pid"] = path_id
        if kind == "image":
            dimensions = _image_dimensions(path)
            if dimensions:
                # `h` is already reserved for duplicate-content SHA-256.
                entry["iw"], entry["ih"] = dimensions
            image_category = classify_image_name(stem)
            image_category_counts[image_category] += 1
            if image_category != "other":
                entry["ic"] = image_category
            if is_material_like_texture_name(stem):
                entry["mt"] = 1
                material_like_image_count += 1
        elif kind == "json":
            script_search = _decoded_m_script_search_text(path)
            if script_search:
                entry["sx"] = script_search
        asset_entries.append(entry)
        asset_paths_by_rel[asset_rel] = path

        if kind == "image":
            image_rels_by_stem[stem.lower()].append(asset_rel)
            if path_id:
                image_rels_by_pid[path_id.upper()].append(asset_rel)
        elif kind == "model":
            model_base = _normalize_model_base(stem)
            source_family = _asset_source_family(source).lower()
            entry["_mb"] = model_base
            model_rels_by_source_base[(source_family, model_base)].append(asset_rel)
            model_rels_by_base[model_base].append(asset_rel)
            if suffix == ".obj":
                obj_rels_by_source_base[(source_family, model_base)].append(asset_rel)
                obj_rels_by_base[model_base].append(asset_rel)
        elif kind == "video":
            video_entry = {
                "k": "video",
                "r": asset_rel,
                "s": size,
            }
            video_entries.append(video_entry)
            video_counts["total"] += 1
            video_counts["video"] += 1

        counts["total"] += 1
        counts[kind] += 1

    print(f"\nScanning exported media assets from {_label_text(media_root_labels, export_root)}...")
    for source, source_root in asset_roots:
        for dirpath, dirnames, filenames in os.walk(source_root):
            dirnames.sort()
            filenames.sort()
            base_dir = Path(dirpath)
            for filename in filenames:
                add_asset_file(
                    source=source,
                    source_root=source_root,
                    path=base_dir / filename,
                    include_json=False,
                )

    for source, source_root in material_roots:
        for dirpath, dirnames, filenames in os.walk(source_root):
            dirnames.sort()
            filenames.sort()
            base_dir = Path(dirpath)
            for filename in filenames:
                path = base_dir / filename
                if not _should_index_browser_json(path, source_root):
                    continue
                add_asset_file(
                    source=source,
                    source_root=source_root,
                    path=path,
                    include_regular_assets=False,
                    include_media=False,
                    include_json=True,
                )

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
            logical = _logical_export_stem(material_rel, material_path.stem)
            if logical is None:
                continue
            material_name, _path_id = logical
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
                texture_name = str(ref.get("name") or "").strip()
                texture_pid = str(ref.get("pid") or "").strip().upper()
                image_rel = ""
                if texture_name:
                    image_rel = _choose_preferred_rel(image_rels_by_stem.get(texture_name.lower(), []), source)
                if not image_rel and texture_pid:
                    image_rel = _choose_preferred_rel(image_rels_by_pid.get(texture_pid, []), source)
                resolved_ref = {
                    "slot": ref["slot"],
                    "name": texture_name or f"pid:{texture_pid}",
                }
                if texture_pid:
                    resolved_ref["pid"] = texture_pid
                if image_rel:
                    resolved_ref["rel"] = image_rel
                resolved_texture_refs.append(resolved_ref)
                if image_rel:
                    texture_link_count += 1

            material_relations = relations.setdefault(material_rel, {})
            material_textures = material_relations.setdefault("textures", [])
            for texture_ref in resolved_texture_refs:
                _append_unique(material_textures, texture_ref)

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

    _add_duplicate_candidate_hashes(asset_entries, asset_paths_by_rel)
    _add_duplicate_candidate_hashes(video_entries, asset_paths_by_rel)

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
        "imageCategories": dict(sorted(image_category_counts.items())),
        "materialLikeImages": material_like_image_count,
    }


def build_asset_payload(scan: dict[str, Any], *, root: Path, export_root: Path) -> dict:
    counts = scan["counts"]
    return {
        "generated": int(time.time()),
        "root": rel_path(export_root, root),
        "sourceRoots": scan["assetRootLabels"],
        "counts": {
            "total": counts["total"],
            "image": counts["image"],
            "model": counts["model"],
            "video": counts["video"],
            "json": counts["json"],
        },
        "entries": scan["assetEntries"],
        "relations": scan["relations"],
        "imageCategories": scan["imageCategories"],
        "materialLikeImages": scan["materialLikeImages"],
    }


def build_video_payload(scan: dict[str, Any], *, root: Path, export_root: Path) -> dict:
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
        "videos": counts["video"],
        "json": counts["json"],
        "materials": scan["materials"],
        "imageCategories": scan["imageCategories"],
        "materialLikeImages": scan["materialLikeImages"],
        "previewModels": scan["previewModels"],
        "indexBytes": out_path.stat().st_size,
    }


def _video_stats(scan: dict[str, Any], out_path: Path | None, export_root: Path) -> dict:
    counts = scan["videoCounts"]
    return {
        "sourceRoot": _label_text(scan["mediaRootLabels"], export_root),
        "sourceRoots": scan["mediaRootLabels"],
        "assets": counts["total"],
        "videos": counts["video"],
        "indexBytes": out_path.stat().st_size if out_path is not None else 0,
    }


def build_asset_index(
    out_path: Path,
    *,
    root: Path,
    export_root: Path,
) -> dict:
    """Scan exported browser-visible assets into a lightweight search index."""
    scan = scan_exported_media_assets(
        root=root,
        export_root=export_root,
    )
    payload = build_asset_payload(scan, root=root, export_root=export_root)
    write_json(out_path, payload)
    counts = scan["counts"]
    print(
        "Asset index written:",
        out_path,
        (
            f"({counts['total']} assets; {counts['image']} images; {counts['model']} models; "
            f"{counts['video']} videos; {counts['json']} JSON files; "
            f"{scan['materialLikeImages']} material-like images; "
            f"{len(scan['imageCategories'])} image categories; "
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
    payload = build_video_payload(scan, root=root, export_root=export_root)
    write_json(out_path, payload)
    counts = scan["videoCounts"]
    print("Video index written:", out_path, f"({counts['video']} videos)")
    return _video_stats(scan, out_path, export_root)


def build_asset_indexes(
    asset_out_path: Path,
    *,
    root: Path,
    export_root: Path,
) -> tuple[dict, dict, dict, dict]:
    """Build image/model and video indexes from a single filesystem scan.

    Only the asset index is written. The video payload is a Story-media build
    input that no WebUI page fetches, so it is returned in memory instead of
    round-tripping through ``webui/data/assets/videos.json``.
    """
    scan = scan_exported_media_assets(
        root=root,
        export_root=export_root,
    )
    asset_payload = build_asset_payload(scan, root=root, export_root=export_root)
    video_payload = build_video_payload(scan, root=root, export_root=export_root)
    write_json(asset_out_path, asset_payload)

    asset_counts = scan["counts"]
    video_counts = scan["videoCounts"]
    print(
        "Asset index written:",
        asset_out_path,
        (
            f"({asset_counts['total']} assets; {asset_counts['image']} images; "
            f"{asset_counts['model']} models; {asset_counts['video']} videos; "
            f"{asset_counts['json']} JSON files; "
            f"{scan['materialLikeImages']} material-like images; "
            f"{len(scan['imageCategories'])} image categories; "
            f"{scan['materials']} materials; "
            f"{scan['textureLinks']} texture links; {scan['previewModels']} model preview proxies)"
        ),
    )
    print("Video index:", f"{video_counts['video']} videos (in-memory Story media input)")
    return (
        _asset_stats(scan, asset_out_path, export_root),
        _video_stats(scan, None, export_root),
        asset_payload,
        video_payload,
    )
