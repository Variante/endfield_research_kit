from __future__ import annotations

from pathlib import Path

from common import ASSET_DIR, OUT_DIR, write_json
from pack_webui import (
    build_inline_image_lookup,
    build_video_lookup,
    collect_inline_image_ids,
    collect_wiki_media_image_ids,
    collect_wiki_video_refs,
    media_lookup_stem,
    resolve_exact_image_assets,
    resolve_exact_video_asset,
    resolve_inline_image_assets,
    score_inline_image_asset,
)


STORY_FILE_IMAGE_PREFIXES = ("cg_image_", "dlg_biglogo_", "remotecomm_image_")
EXCLUDED_STORY_FILE_IMAGE_STEMS = {"cg_image_e2m6_1_m"}


def collect_story_file_images(entries: list[dict]) -> dict[str, dict]:
    """Return one preferred Sprite export for each logical Story image."""
    selected_by_stem: dict[str, tuple[int, str, dict]] = {}
    for raw in entries:
        if not isinstance(raw, dict) or raw.get("k") != "image" or not raw.get("r"):
            continue
        rel = str(raw.get("r") or "").replace("\\", "/").strip("/")
        stem_info = media_lookup_stem(rel)
        if not stem_info or not stem_info[0].startswith(STORY_FILE_IMAGE_PREFIXES):
            continue
        stem = stem_info[0]
        if stem in EXCLUDED_STORY_FILE_IMAGE_STEMS:
            continue
        entry = dict(raw)
        entry["k"] = "image"
        entry["r"] = rel
        rank = score_inline_image_asset(rel, stem)
        current = selected_by_stem.get(stem)
        if current is None or rank > current[0] or (rank == current[0] and rel < current[1]):
            selected_by_stem[stem] = (rank, rel, entry)
    return {rel: entry for _rank, rel, entry in selected_by_stem.values()}


def source_roots_for_entries(
    payloads: list[dict],
) -> dict:
    available: dict[str, str] = {}
    for payload in payloads:
        source_roots = payload.get("sourceRoots") if isinstance(payload.get("sourceRoots"), dict) else {}
        for key, value in source_roots.items():
            available[str(key)] = str(value)
    return {key: available[key] for key in sorted(available)}


def build_story_media_payload(asset_payload: dict, video_payload: dict) -> dict:
    webui_root = OUT_DIR.parent

    inline_image_ids = collect_inline_image_ids(webui_root)
    wiki_image_ids = collect_wiki_media_image_ids(webui_root)
    video_refs = collect_wiki_video_refs(webui_root)

    by_stem, by_number = build_inline_image_lookup(asset_payload.get("entries") or [])
    video_by_stem = build_video_lookup(video_payload.get("entries") or [])

    selected_images: dict[str, dict] = {}
    selected_videos: dict[str, dict] = {}

    # CG illustrations are valid standalone Story media even when no current
    # conversation payload names them. Import the complete exported family so
    # direct cg_image_* references can resolve and packaging copies the files.
    story_file_images = collect_story_file_images(asset_payload.get("entries") or [])
    selected_images.update(story_file_images)
    story_file_stems = [media_lookup_stem(rel)[0] for rel in story_file_images]

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
        "sourceRoots": source_roots_for_entries([asset_payload, video_payload]),
        "counts": {
            "total": len(entries),
            "image": len(images),
            "video": len(videos),
            "imageIds": len(inline_image_ids | wiki_image_ids),
            "storyFileImages": len(story_file_images),
            "cgImages": sum(stem.startswith("cg_image_") for stem in story_file_stems),
            "bigLogoImages": sum(stem.startswith("dlg_biglogo_") for stem in story_file_stems),
            "remoteCommImages": sum(stem.startswith("remotecomm_image_") for stem in story_file_stems),
            "videoRefs": len(video_refs),
        },
        "entries": entries,
    }
    return payload


def story_media_stats(payload: dict, story_media_path: Path) -> dict:
    counts = payload.get("counts") or {}
    return {
        "imageIds": int(counts.get("imageIds") or 0),
        "videoRefs": int(counts.get("videoRefs") or 0),
        "images": int(counts.get("image") or 0),
        "cgImages": int(counts.get("cgImages") or 0),
        "bigLogoImages": int(counts.get("bigLogoImages") or 0),
        "remoteCommImages": int(counts.get("remoteCommImages") or 0),
        "storyFileImages": int(counts.get("storyFileImages") or 0),
        "videos": int(counts.get("video") or 0),
        "indexBytes": story_media_path.stat().st_size,
    }


def write_story_media_payload(payload: dict) -> dict:
    story_media_path = ASSET_DIR / "story_media.json"
    write_json(story_media_path, payload)
    return story_media_stats(payload, story_media_path)
