"""Build the exported asset index for the unified asset browser.

Run from the repo root:
    python scripts/build_assets.py
    python scripts/build_assets.py --fast
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from asset_builder.bundles import build_asset_bundles
from asset_builder.index import (
    _asset_payload,
    _video_payload,
    build_asset_indexes,
    scan_exported_media_assets,
)
from asset_builder.story_media import build_story_media_payload, write_story_media_index, write_story_media_payload
from common import ASSET_DIR, EXPORT_ROOT, OUT_DIR, ROOT, read_json, write_json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the WebUI exported asset indexes.",
    )
    parser.add_argument(
        "--skip-bundles",
        "--index-only",
        dest="skip_bundles",
        action="store_true",
        help="Build only index.json/videos.json and write an empty bundle index.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: reuse existing asset indexes when present and skip demo bundle zip generation.",
    )
    parser.add_argument(
        "--mode",
        choices=("focused", "default"),
        default="focused",
        help="`focused` writes compact Story/Wiki media indexes; `default` writes the broad Assets browser index.",
    )
    return parser.parse_args(argv)


def write_empty_bundle_index() -> dict:
    bundle_dir = ASSET_DIR / "bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    index_path = bundle_dir / "index.json"
    payload = {
        "generated": 0,
        "bundles": [],
        "byAssetRel": {},
    }
    write_json(index_path, payload)
    return {
        "bundles": 0,
        "bytes": 0,
        "errors": [],
        "indexBytes": index_path.stat().st_size,
    }


def load_existing_index_stats(asset_index_path: Path, video_index_path: Path) -> tuple[dict, dict] | None:
    asset_payload = read_json(asset_index_path, default={})
    video_payload = read_json(video_index_path, default={})
    if not isinstance(asset_payload, dict) or not isinstance(video_payload, dict):
        return None
    asset_counts = asset_payload.get("counts") or {}
    video_counts = video_payload.get("counts") or {}
    if not asset_counts or not video_counts:
        return None

    asset_stats = {
        "sourceRoot": ", ".join(
            f"{source}:{label}"
            for source, label in (asset_payload.get("sourceRoots") or {}).items()
        ),
        "assets": int(asset_counts.get("total") or 0),
        "images": int(asset_counts.get("image") or 0),
        "models": int(asset_counts.get("model") or 0),
        "videos": int(asset_counts.get("video") or 0),
        "json": int(asset_counts.get("json") or 0),
        "previewModels": sum(1 for entry in (asset_payload.get("entries") or []) if isinstance(entry, dict) and entry.get("p")),
        "indexBytes": asset_index_path.stat().st_size,
    }
    video_stats = {
        "videos": int(video_counts.get("video") or 0),
        "indexBytes": video_index_path.stat().st_size,
    }
    return asset_stats, video_stats


def _source_root_label(source_roots: dict) -> str:
    return ", ".join(
        f"{source}:{label}"
        for source, label in sorted((source_roots or {}).items())
    )


def _stats_from_compact_payloads(
    asset_payload: dict,
    video_payload: dict,
    asset_index_path: Path,
    video_index_path: Path,
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
        "indexBytes": video_index_path.stat().st_size,
    }
    return asset_stats, video_stats


def build_webui_asset_indexes(asset_index_path: Path, video_index_path: Path) -> tuple[dict, dict, dict]:
    scan = scan_exported_media_assets(
        root=ROOT,
        export_root=EXPORT_ROOT,
    )
    full_asset_payload = _asset_payload(scan, root=ROOT, export_root=EXPORT_ROOT)
    full_video_payload = _video_payload(scan, root=ROOT, export_root=EXPORT_ROOT)
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
    write_json(video_index_path, compact_video_payload)
    story_media_stats = write_story_media_payload(story_payload)
    asset_stats, video_stats = _stats_from_compact_payloads(
        compact_asset_payload,
        compact_video_payload,
        asset_index_path,
        video_index_path,
    )
    print(
        "WebUI asset index written:",
        asset_index_path,
        (
            f"({asset_stats['assets']} Story/Wiki media assets; "
            f"{asset_stats['images']} images; {asset_stats['videos']} videos)"
        ),
    )
    print("WebUI video index written:", video_index_path, f"({video_stats['videos']} videos)")
    return asset_stats, video_stats, story_media_stats


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Keep existing files so write-if-changed can avoid rewriting identical
    # indexes. Bundle output is regenerated or explicitly emptied below.
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building {args.mode} asset index from {EXPORT_ROOT}...")
    asset_index_path = ASSET_DIR / "index.json"
    video_index_path = ASSET_DIR / "videos.json"
    existing_stats = load_existing_index_stats(asset_index_path, video_index_path) if args.fast else None
    story_media_stats = None
    if existing_stats:
        asset_stats, video_stats = existing_stats
        print("Asset index scan: reused existing indexes (--fast)")
        story_media_stats = write_story_media_index(asset_index_path, video_index_path)
    elif args.mode == "focused":
        asset_stats, video_stats, story_media_stats = build_webui_asset_indexes(asset_index_path, video_index_path)
    else:
        asset_stats, video_stats = build_asset_indexes(
            asset_index_path,
            video_index_path,
            root=ROOT,
            export_root=EXPORT_ROOT,
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
    print(
        "Video index:",
        video_index_path,
        f"({video_stats['videos']} videos)",
    )
    if story_media_stats is None:
        story_media_stats = write_story_media_index(asset_index_path, video_index_path)
    print(
        "Story media index:",
        ASSET_DIR / "story_media.json",
        (
            f"({story_media_stats['images']} images from {story_media_stats['imageIds']} ids; "
            f"{story_media_stats['videos']} videos from {story_media_stats['videoRefs']} refs)"
        ),
    )
    if args.mode == "focused" or args.fast or args.skip_bundles:
        write_empty_bundle_index()
        print("Asset bundle output: skipped (focused/fast/index-only mode)")
        return

    bundle_stats = build_asset_bundles(ASSET_DIR / "index.json", ASSET_DIR / "bundles")
    print(
        "Asset bundle output:",
        ASSET_DIR / "bundles" / "index.json",
        (
            f"({bundle_stats['bundles']} bundle(s); "
            f"{bundle_stats['bytes']} bytes zipped)"
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
