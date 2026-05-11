"""Build the exported asset index for the unified asset browser.

Run from the repo root:
    python scripts/webui/build_assets.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_asset_bundles import build_asset_bundles
from build_story_asset_index import build_asset_index, build_video_index
from common import ASSET_DIR, EXPORT_ROOT, OUT_DIR, ROOT


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(ASSET_DIR, ignore_errors=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building asset browser index from {EXPORT_ROOT}...")
    asset_stats = build_asset_index(ASSET_DIR / "index.json", root=ROOT, export_root=EXPORT_ROOT)
    video_stats = build_video_index(ASSET_DIR / "videos.json", root=ROOT, export_root=EXPORT_ROOT)
    print(
        "\nAsset root copy:",
        ASSET_DIR / "index.json",
        (
            f"(source root: {asset_stats['sourceRoot']}; "
            f"{asset_stats['assets']} source assets indexed; "
            f"{asset_stats['images']} images; {asset_stats['models']} models; "
            f"{asset_stats['previewModels']} reviewable non-OBJ models)"
        ),
    )
    print(
        "Video index:",
        ASSET_DIR / "videos.json",
        f"({video_stats['videos']} videos)",
    )
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
