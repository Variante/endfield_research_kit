from __future__ import annotations

from pathlib import Path

from common import ASSET_DIR, OUT_DIR, write_json
from package_webui import (
    build_inline_image_lookup,
    build_video_lookup,
    collect_inline_image_ids,
    collect_wiki_media_image_ids,
    collect_wiki_video_refs,
    load_asset_index,
    resolve_exact_image_assets,
    resolve_exact_video_asset,
    resolve_inline_image_assets,
)


def source_roots_for_entries(
    payloads: list[dict],
    entries: list[dict],
    *,
    include_all_sources: bool = False,
) -> dict:
    roots: dict[str, str] = {}
    available: dict[str, str] = {}
    for payload in payloads:
        source_roots = payload.get("sourceRoots") if isinstance(payload.get("sourceRoots"), dict) else {}
        for key, value in source_roots.items():
            available[str(key)] = str(value)
    if include_all_sources:
        return {key: available[key] for key in sorted(available)}
    for entry in entries:
        rel = str(entry.get("r") or "").replace("\\", "/").strip("/")
        source = rel.split("/", 1)[0] if rel else ""
        if source and source in available:
            roots[source] = available[source]
    return {key: roots[key] for key in sorted(roots)}


def write_story_media_index(asset_index_path: Path, video_index_path: Path) -> dict:
    asset_payload = load_asset_index(asset_index_path)
    video_payload = load_asset_index(video_index_path)
    webui_root = OUT_DIR.parent

    inline_image_ids = collect_inline_image_ids(webui_root)
    wiki_image_ids = collect_wiki_media_image_ids(webui_root)
    video_refs = collect_wiki_video_refs(webui_root)

    by_stem, by_number = build_inline_image_lookup(asset_payload.get("entries") or [])
    video_by_stem = build_video_lookup(video_payload.get("entries") or [])

    selected_images: dict[str, dict] = {}
    selected_videos: dict[str, dict] = {}

    for image_id in sorted(inline_image_ids):
        for candidate in resolve_inline_image_assets(image_id, by_stem, by_number):
            entry = dict(candidate.entry)
            entry["k"] = "image"
            entry["r"] = candidate.rel
            selected_images[candidate.rel] = entry

    for image_id in sorted(wiki_image_ids):
        for candidate in resolve_exact_image_assets(image_id, by_stem):
            entry = dict(candidate.entry)
            entry["k"] = "image"
            entry["r"] = candidate.rel
            selected_images[candidate.rel] = entry

    for video_id, device_type in sorted(video_refs):
        candidate = resolve_exact_video_asset(video_id, device_type, video_by_stem)
        if not candidate:
            continue
        entry = dict(candidate.entry)
        entry["k"] = "video"
        entry["r"] = candidate.rel
        selected_videos[candidate.rel] = entry

    images = [selected_images[rel] for rel in sorted(selected_images)]
    videos = [selected_videos[rel] for rel in sorted(selected_videos)]
    entries = images + videos
    story_media_path = ASSET_DIR / "story_media.json"
    payload = {
        "generated": asset_payload.get("generated") or video_payload.get("generated"),
        "root": asset_payload.get("root") or video_payload.get("root") or "export_full",
        "sourceRoots": source_roots_for_entries(
            [asset_payload, video_payload],
            entries,
            include_all_sources=True,
        ),
        "counts": {
            "total": len(entries),
            "image": len(images),
            "video": len(videos),
            "imageIds": len(inline_image_ids | wiki_image_ids),
            "videoRefs": len(video_refs),
        },
        "entries": entries,
    }
    write_json(story_media_path, payload)
    return {
        "imageIds": len(inline_image_ids | wiki_image_ids),
        "videoRefs": len(video_refs),
        "images": len(images),
        "videos": len(videos),
        "indexBytes": story_media_path.stat().st_size,
    }
