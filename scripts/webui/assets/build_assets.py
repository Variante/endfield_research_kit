"""Build the exported asset index for the unified asset browser.

It writes only Assets-owned indexes and media lookup. ``--mode`` defaults to
``focused``, the Story/Wiki media projection; the served Assets page is built
with ``--mode default``, which the wrapper passes, so a direct run without it
replaces the full index with the focused projection. It also writes
``webui/data/assets/table_owners.json`` from ``table_asset_owners``: exact
table-row ownership for indexed assets, always derived from the complete scan
even when the published index is the focused projection. ``activity_media.json``
is the compact exact activity/instruction/fixed-reward image lookup, derived
from that same scan by ``activity_media``. The legacy economy,
world, presentation and broad data index helpers are diagnostic only and feed
no active page.

Run from the repo root:
    python -m scripts.webui.assets.build_assets --mode default
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.assets.build_assets"
    )

from scripts.webui.assets.index import AssetScanResult, scan_exported_media_assets
from scripts.webui.assets.story_media import build_story_media_payload, write_story_media_payload
from scripts.webui.assets.activity_media import build_activity_media_payload
from scripts.webui.assets.table_asset_owners import build_table_asset_owner_payload
from scripts.webui.assets.collision import add_collision_publication, publish_collision_previews
from scripts.common import ASSET_DIR, EXPORT_ROOT, ROOT, TABLE_DIR, rel_path, require_export_layout, write_json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the WebUI exported asset indexes.",
    )
    parser.add_argument(
        "--collision-corpus", type=Path, default=ROOT / "reports/assets/cooked_collision_current_latest.json",
        help="Optional authenticated selected-corpus receipt for separate collision previews (broad Assets index only).",
    )
    parser.add_argument(
        "--collision-vfs-summary", type=Path,
        help="VFS audit summary for older collision receipts without outerSummaryPath.",
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
    parser.add_argument(
        "--publish",
        choices=("all", "index", "story-media", "collision"),
        default="all",
        help=(
            "`index` writes the Assets page's index.json, table_owners.json and activity_media.json; "
            "`story-media` writes only the Story page's story_media.json (its "
            "images and videos); `all` writes both. `collision` refreshes only "
            "collision previews in the existing broad Assets index without rescanning render media."
        ),
    )
    return parser.parse_args(argv)


def build_output_payloads(
    scan: AssetScanResult,
    *,
    mode: str,
    root: Path,
    export_root: Path,
    story_media: bool = True,
) -> tuple[dict, dict, dict, dict]:
    """Derive every published/in-memory payload from one completed scan.

    The fourth payload is always the complete asset index, even when the
    published index is the focused Story/Wiki projection, so consumers that
    need the full exported set (the table-owner sidecar) do not rescan.
    Story media reads Story's published pages; it is built only when it is
    published (``story_media``) or projects the focused index, so the full
    index never depends on Story.
    """
    full_asset_payload, full_video_payload = scan.payloads(root=root, export_root=export_root)
    story_payload = (
        build_story_media_payload(full_asset_payload, full_video_payload)
        if story_media or mode == "focused"
        else {}
    )

    if mode != "focused":
        return full_asset_payload, full_video_payload, story_payload, full_asset_payload

    entries = story_payload["entries"]
    image_entries = [entry for entry in entries if entry["k"] == "image"]
    video_entries = [entry for entry in entries if entry["k"] == "video"]
    image_categories = Counter(str(entry["ic"]) for entry in image_entries if entry.get("ic"))
    media_header = {
        "generated": story_payload["generated"],
        "root": story_payload["root"],
        "mode": "webui",
        "sourceRoots": story_payload["sourceRoots"],
    }

    asset_payload = {
        **media_header,
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
        "materialLikeImages": sum(bool(entry.get("mt")) for entry in image_entries),
    }
    video_payload = {
        **media_header,
        "counts": {
            "total": len(video_entries),
            "video": len(video_entries),
        },
        "entries": video_entries,
    }

    return asset_payload, video_payload, story_payload, full_asset_payload


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    require_export_layout()

    if args.publish == "collision":
        publish_collision_only(args)
        return

    print(f"Building {args.mode} asset index ({args.publish}) from {EXPORT_ROOT}...")
    asset_index_path = ASSET_DIR / "index.json"
    scan = scan_exported_media_assets(root=ROOT, export_root=EXPORT_ROOT)
    asset_payload, video_payload, story_payload, full_asset_payload = build_output_payloads(
        scan,
        mode=args.mode,
        root=ROOT,
        export_root=EXPORT_ROOT,
        story_media=args.publish != "index",
    )
    if args.publish in ("all", "story-media"):
        report_story_media(write_story_media_payload(story_payload))
    if args.publish == "story-media":
        return
    if args.mode != "focused":
        collision = publish_collision_previews(
            args.collision_corpus, root=ROOT, asset_dir=ASSET_DIR, summary_path=args.collision_vfs_summary,
        )
        add_collision_publication(asset_payload, collision)
        print("Collision previews:", collision["status"], collision.get("counts", collision.get("diagnostic", "")))
    # Material/texture/model relations feed only the detail panel and model
    # viewer; the page fetches them on first use so the list loads without them.
    write_json(ASSET_DIR / "relations.json", {"relations": asset_payload.pop("relations", {})})
    write_json(asset_index_path, asset_payload)
    # Exact table-row ownership for the indexed assets. The scan is the full
    # index, not the focused Story/Wiki projection, so the sidecar describes
    # every exported asset regardless of the published index mode.
    owner_index_path = ASSET_DIR / "table_owners.json"
    owner_payload = build_table_asset_owner_payload(
        [entry for entry in full_asset_payload["entries"] if "cl" not in entry],
        TABLE_DIR,
    )
    write_json(owner_index_path, owner_payload)
    write_json(ASSET_DIR / "activity_media.json", build_activity_media_payload(full_asset_payload["entries"], TABLE_DIR))
    owner_counts = owner_payload["counts"]
    print(
        "Table asset owners:",
        owner_index_path,
        (
            f"({owner_counts['ownedStems']} of {owner_counts['assetStems']} "
            f"asset stems owned by an exact table field across "
            f"{owner_counts['tables']} tables)"
        ),
    )
    counts = asset_payload["counts"]
    scope = "Story/Wiki media" if args.mode == "focused" else "source assets"
    print(
        "Asset index written:",
        asset_index_path,
        (
            f"({counts['total']} {scope}; {counts['image']} images; "
            f"{counts['model']} models; {counts['video']} videos; "
            f"{counts.get('json', 0)} JSON files)"
        ),
    )
    print("Video index:", f"{video_payload['counts']['video']} videos (in-memory Story media input)")


def publish_collision_only(args: argparse.Namespace) -> None:
    """Refresh this optional projection while preserving the last media scan."""
    index_path = ASSET_DIR / "index.json"
    original = index_path.read_bytes()
    payload = json.loads(original)
    if payload.get("mode") == "webui" or payload.get("root") != rel_path(EXPORT_ROOT, ROOT):
        raise ValueError("collision publication needs a broad Assets index for the selected export root")
    payload["entries"] = [row for row in payload["entries"] if "cl" not in row]
    counts = Counter(row["k"] for row in payload["entries"])
    payload["counts"] = {"total": len(payload["entries"]), **{kind: counts[kind] for kind in ("image", "model", "video")}}
    payload["sourceRoots"].pop("Collision", None)
    collision = publish_collision_previews(args.collision_corpus, root=ROOT, asset_dir=ASSET_DIR,
                                            summary_path=args.collision_vfs_summary)
    add_collision_publication(payload, collision)
    payload["generated"] = int(time.time())
    if hashlib.sha256(index_path.read_bytes()).digest() != hashlib.sha256(original).digest():
        raise ValueError("Assets index changed during collision publication; rerun against its new publication")
    write_json(index_path, payload)
    print("Collision previews:", collision["status"], collision.get("counts", collision.get("diagnostic", "")), flush=True)


def report_story_media(stats: dict) -> None:
    print(
        "Story media index:",
        ASSET_DIR / "story_media.json",
        (
            f"({stats['images']} images from {stats['imageIds']} ids "
            f"plus {stats['storyFileImages']} Story image files "
            f"({stats['cgImages']} CG; {stats['bigLogoImages']} BigLogo; "
            f"{stats['remoteCommImages']} remote comm); "
            f"{stats['videos']} videos from {stats['videoRefs']} refs)"
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(1)
