"""Build the exported asset index for the unified asset browser.

Run from the repo root:
    python scripts/build_assets.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from asset_builder.index import (
    build_asset_payload,
    build_asset_indexes,
    build_video_payload,
    scan_exported_media_assets,
)
from asset_builder.story_media import build_story_media_payload, write_story_media_payload
from common import ASSET_DIR, EXPORT_ROOT, OUT_DIR, ROOT, write_json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the WebUI exported asset indexes.",
    )
    parser.add_argument(
        "--mode",
        choices=("focused", "default", "debug"),
        default="focused",
        help=(
            "`focused` writes compact Story/Wiki media indexes; `default` and "
            "`debug` write the broad browser index. The debug distinction applies "
            "to AnimeStudio export scope, not index construction."
        ),
    )
    return parser.parse_args(argv)


def _source_root_label(source_roots: dict) -> str:
    return ", ".join(
        f"{source}:{label}"
        for source, label in sorted((source_roots or {}).items())
    )


def _stats_from_compact_payloads(
    asset_payload: dict,
    video_payload: dict,
    asset_index_path: Path,
) -> tuple[dict, dict]:
    asset_counts = asset_payload.get("counts") or {}
    video_counts = video_payload.get("counts") or {}
    asset_stats = {
        "sourceRoot": _source_root_label(asset_payload.get("sourceRoots") or {}),
        "assets": int(asset_counts.get("total") or 0),
        "images": int(asset_counts.get("image") or 0),
        "models": int(asset_counts.get("model") or 0),
        "videos": int(asset_counts.get("video") or 0),
        "json": int(asset_counts.get("json") or 0),
        "previewModels": sum(
            1
            for entry in (asset_payload.get("entries") or [])
            if isinstance(entry, dict) and entry.get("p")
        ),
        "indexBytes": asset_index_path.stat().st_size,
    }
    video_stats = {
        "videos": int(video_counts.get("video") or 0),
        "indexBytes": 0,
    }
    return asset_stats, video_stats


def build_webui_asset_indexes(asset_index_path: Path) -> tuple[dict, dict, dict]:
    scan = scan_exported_media_assets(
        root=ROOT,
        export_root=EXPORT_ROOT,
    )
    full_asset_payload = build_asset_payload(scan, root=ROOT, export_root=EXPORT_ROOT)
    full_video_payload = build_video_payload(scan, root=ROOT, export_root=EXPORT_ROOT)
    story_payload = build_story_media_payload(full_asset_payload, full_video_payload)

    entries = story_payload.get("entries") or []
    image_entries = [
        entry for entry in entries
        if isinstance(entry, dict) and entry.get("k") == "image"
    ]
    video_entries = [
        entry for entry in entries
        if isinstance(entry, dict) and entry.get("k") == "video"
    ]
    image_categories: dict[str, int] = {}
    for entry in image_entries:
        category = entry.get("ic")
        if category:
            image_categories[str(category)] = image_categories.get(str(category), 0) + 1

    compact_asset_payload = {
        "generated": story_payload.get("generated"),
        "root": story_payload.get("root") or "export_full",
        "mode": "webui",
        "sourceRoots": story_payload.get("sourceRoots") or {},
        "counts": {
            "total": len(entries),
            "image": len(image_entries),
            "model": 0,
            "video": len(video_entries),
            "json": 0,
        },
        "entries": entries,
        "relations": {},
        "imageCategories": dict(sorted(image_categories.items())),
        "materialLikeImages": sum(
            1 for entry in image_entries
            if isinstance(entry, dict) and entry.get("mt")
        ),
    }
    compact_video_payload = {
        "generated": story_payload.get("generated"),
        "root": story_payload.get("root") or "export_full",
        "mode": "webui",
        "sourceRoots": story_payload.get("sourceRoots") or {},
        "counts": {
            "total": len(video_entries),
            "video": len(video_entries),
        },
        "entries": video_entries,
    }

    write_json(asset_index_path, compact_asset_payload)
    story_media_stats = write_story_media_payload(story_payload)
    asset_stats, video_stats = _stats_from_compact_payloads(
        compact_asset_payload,
        compact_video_payload,
        asset_index_path,
    )
    print(
        "WebUI asset index written:",
        asset_index_path,
        (
            f"({asset_stats['assets']} Story/Wiki media assets; "
            f"{asset_stats['images']} images; {asset_stats['videos']} videos)"
        ),
    )
    print("WebUI video index:", f"{video_stats['videos']} videos (in-memory Story media input)")
    return asset_stats, video_stats, story_media_stats


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Keep existing files so write-if-changed can avoid rewriting identical
    # indexes.
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building {args.mode} asset index from {EXPORT_ROOT}...")
    asset_index_path = ASSET_DIR / "index.json"
    story_media_stats = None
    if args.mode == "focused":
        asset_stats, video_stats, story_media_stats = build_webui_asset_indexes(asset_index_path)
    else:
        asset_stats, video_stats, asset_payload, video_payload = build_asset_indexes(
            asset_index_path,
            root=ROOT,
            export_root=EXPORT_ROOT,
        )
        # Story media reuses the freshly scanned payloads instead of re-reading
        # and re-parsing the ~150 MB asset index that was just written.
        story_media_stats = write_story_media_payload(
            build_story_media_payload(asset_payload, video_payload)
        )
    print(
        "\nAsset root copy:",
        asset_index_path,
        (
            f"(source root: {asset_stats['sourceRoot']}; "
            f"{asset_stats['assets']} source assets indexed; "
            f"{asset_stats['images']} images; {asset_stats['models']} models; "
            f"{asset_stats.get('videos', 0)} videos; {asset_stats.get('json', 0)} JSON files; "
            f"{asset_stats['previewModels']} reviewable non-OBJ models)"
        ),
    )
    print("Video index:", f"{video_stats['videos']} videos (in-memory Story media input)")
    print(
        "Story media index:",
        ASSET_DIR / "story_media.json",
        (
            f"({story_media_stats['images']} images from {story_media_stats['imageIds']} ids "
            f"plus {story_media_stats['storyFileImages']} Story image files "
            f"({story_media_stats['cgImages']} CG; {story_media_stats['bigLogoImages']} BigLogo; "
            f"{story_media_stats['remoteCommImages']} remote comm); "
            f"{story_media_stats['videos']} videos from {story_media_stats['videoRefs']} refs)"
        ),
    )
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
