"""Build the exported asset index for the unified asset browser.

Run from the repo root:
    python scripts/webui/build_assets.py
    python scripts/webui/build_assets.py --fast
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_asset_bundles import build_asset_bundles
from build_story_asset_index import build_asset_indexes
from common import ASSET_DIR, EXPORT_ROOT, OUT_DIR, ROOT, read_json, write_json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the WebUI exported asset indexes.",
    )
    parser.add_argument(
        "--include-extra-roots",
        action="store_true",
        help="Also scan legacy export_full/inventory, raw_vfs, and unresolved roots.",
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
        "previewModels": sum(1 for entry in (asset_payload.get("entries") or []) if isinstance(entry, dict) and entry.get("p")),
        "indexBytes": asset_index_path.stat().st_size,
    }
    video_stats = {
        "videos": int(video_counts.get("video") or 0),
        "indexBytes": video_index_path.stat().st_size,
    }
    return asset_stats, video_stats


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Keep existing files so write-if-changed can avoid rewriting identical
    # indexes. Bundle output is regenerated or explicitly emptied below.
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building asset browser index from {EXPORT_ROOT}...")
    asset_index_path = ASSET_DIR / "index.json"
    video_index_path = ASSET_DIR / "videos.json"
    existing_stats = load_existing_index_stats(asset_index_path, video_index_path) if args.fast else None
    if existing_stats:
        asset_stats, video_stats = existing_stats
        print("Asset index scan: reused existing indexes (--fast)")
    else:
        asset_stats, video_stats = build_asset_indexes(
            asset_index_path,
            video_index_path,
            root=ROOT,
            export_root=EXPORT_ROOT,
            include_extra_roots=args.include_extra_roots,
        )
    print(
        "\nAsset root copy:",
        asset_index_path,
        (
            f"(source root: {asset_stats['sourceRoot']}; "
            f"{asset_stats['assets']} source assets indexed; "
            f"{asset_stats['images']} images; {asset_stats['models']} models; "
            f"{asset_stats['previewModels']} reviewable non-OBJ models)"
        ),
    )
    print(
        "Video index:",
        video_index_path,
        f"({video_stats['videos']} videos)",
    )
    if args.fast or args.skip_bundles:
        write_empty_bundle_index()
        print("Asset bundle output: skipped (fast/index-only mode)")
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
