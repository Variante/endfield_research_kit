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
no active page. ``--publish material-appearance`` reprojects only existing
Material appearance in ``relations.json`` from the selected Unity store,
without scanning media or rebuilding collision evidence.
``--publish fbx-content`` refreshes FBX grouping in an existing broad index,
preserving its other entries, collision evidence and media/ownership sidecars.
``--publish collision-authored`` refreshes only stored collider/prefab owners
from existing authenticated scene/Mesh receipts, with no extraction or capture.

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

from scripts.webui.assets.index import AssetScanResult, refresh_material_appearance, scan_exported_media_assets
from scripts.webui.assets.fbx_content import publish_fbx_content
from scripts.webui.assets.story_media import build_story_media_payload, write_story_media_payload
from scripts.webui.assets.activity_media import build_activity_media_payload
from scripts.webui.assets.table_asset_owners import build_table_asset_owner_payload
from scripts.webui.assets.collision import add_collision_publication, publish_collision_previews
from scripts.webui.assets.collision_runtime import apply_runtime_publication
from scripts.webui.assets.collision_authored import apply_authored_publication
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
    parser.add_argument("--collision-runtime-selection", type=Path,
                        default=ROOT / "reports/assets/collision_runtime_selection.json",
                        help="Local runtime input selection; every publication revalidates its evidence.")
    parser.add_argument("--collision-runtime-session", type=Path, action="append",
                        help="Select a saved collision capture (repeatable); also select its stored receipts.")
    parser.add_argument("--collision-runtime-stored-receipt", type=Path, action="append",
                        help="Authenticated stored Mesh selection used by the runtime audit (repeatable).")
    parser.add_argument("--collision-authored-selection", type=Path,
                        default=ROOT / "reports/assets/collision_authored_selection.json",
                        help="Local scene-receipt selection; stored owner joins are revalidated each publication.")
    parser.add_argument("--collision-scene-receipt", type=Path, action="append",
                        help="Select an existing authenticated v4 scene extraction without exporting (repeatable).")
    parser.add_argument("--collision-model-receipt", type=Path,
                        help="Select a saved Model source corpus alongside scene receipts; revalidate source/native gates.")
    parser.add_argument('--collision-box-receipt', type=Path,
                        help='Select a supplemental stored BoxCollider corpus alongside its scene receipt.')
    parser.add_argument('--collision-render-receipt', type=Path,
                        help='Select a supplemental stored MeshFilter/MeshRenderer corpus alongside its scene receipt.')
    parser.add_argument('--collision-render-resource-receipt',type=Path,action='append',
                        help='Select an admitted source-directory/resource receipt alongside scene and render receipts (repeatable).')
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
        choices=("all", "index", "story-media", "collision", "collision-runtime", "collision-authored", "material-appearance", "fbx-content"),
        default="all",
        help=(
            "`index` writes the Assets page's index.json, table_owners.json and activity_media.json; "
            "`story-media` writes only the Story page's story_media.json (its "
            "images and videos); `all` writes both. `collision` refreshes only "
            "collision previews in the existing broad Assets index without rescanning render media; "
            "`collision-runtime` updates only their runtime evidence metadata; "
            "`collision-authored` updates only their stored collider/prefab owners; "
            "`material-appearance` refreshes only existing Material appearance in relations.json; "
            "`fbx-content` refreshes only FBX grouping in the existing broad Assets index."
        ),
    )
    args = parser.parse_args(argv)
    if (args.collision_runtime_session or args.collision_runtime_stored_receipt) and (
            args.publish in ("story-media", "material-appearance", "fbx-content", "collision-authored") or args.mode == "focused" and args.publish not in ("collision", "collision-runtime")):
        parser.error("runtime collision selection needs a broad index or --publish collision[-runtime]")
    if (args.collision_scene_receipt or args.collision_model_receipt or args.collision_box_receipt or args.collision_render_receipt or args.collision_render_resource_receipt) and (args.publish in ("story-media", "material-appearance", "fbx-content", "collision-runtime")
            or args.mode == "focused" and args.publish not in ("collision", "collision-authored")):
        parser.error("scene receipt selection needs a broad index or --publish collision[-authored]")
    if args.collision_model_receipt and not args.collision_scene_receipt:
        parser.error("select --collision-scene-receipt alongside --collision-model-receipt")
    if args.collision_box_receipt and not args.collision_scene_receipt:
        parser.error('select --collision-scene-receipt alongside --collision-box-receipt')
    if args.collision_render_receipt and not args.collision_scene_receipt:
        parser.error('select --collision-scene-receipt alongside --collision-render-receipt')
    if args.collision_render_resource_receipt and not (args.collision_scene_receipt and args.collision_render_receipt):
        parser.error('select scene and render receipts alongside render resource receipts')
    return args


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

    if args.publish == "fbx-content":
        publish_fbx_content(root=ROOT, export_root=EXPORT_ROOT, asset_dir=ASSET_DIR)
        return
    if args.publish == "material-appearance":
        publish_material_appearance()
        return
    if args.publish in ("collision", "collision-runtime", "collision-authored"):
        publish_collision_only(args)
        return

    print(f"Building {args.mode} asset index ({args.publish}) from {EXPORT_ROOT}...")
    asset_index_path = ASSET_DIR / "index.json"
    scan = scan_exported_media_assets(
        root=ROOT, export_root=EXPORT_ROOT,
        build_fbx_content=args.mode != "focused" and args.publish != "story-media",
    )
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
        publish_runtime_metadata(asset_payload, args)
        publish_authored_metadata(asset_payload, args)
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


def publish_material_appearance() -> None:
    """Refresh material shading without rescanning media or collision evidence."""
    index_path = ASSET_DIR / "index.json"
    index_before = index_path.read_bytes()
    index = json.loads(index_before)
    if index.get("mode") == "webui" or index.get("root") != rel_path(EXPORT_ROOT, ROOT):
        raise ValueError("material appearance refresh needs a broad Assets index for the selected export root")
    relations_path = ASSET_DIR / "relations.json"
    relations_before = relations_path.read_bytes()
    payload = json.loads(relations_before)
    changed = refresh_material_appearance(payload["relations"], export_root=EXPORT_ROOT)
    if index_path.read_bytes() != index_before or relations_path.read_bytes() != relations_before:
        raise ValueError("Assets publication changed during material appearance refresh; rerun against its new publication")
    write_json(relations_path, payload)
    print(f"Material appearance refreshed: {relations_path} ({changed} changed materials)")


def publish_collision_only(args: argparse.Namespace) -> None:
    """Refresh this optional projection while preserving the last media scan."""
    index_path = ASSET_DIR / "index.json"
    original = index_path.read_bytes()
    payload = json.loads(original)
    if payload.get("mode") == "webui" or payload.get("root") != rel_path(EXPORT_ROOT, ROOT):
        raise ValueError("collision publication needs a broad Assets index for the selected export root")
    if args.publish == "collision":
        payload["entries"] = [row for row in payload["entries"] if "cl" not in row]
        counts = Counter(row["k"] for row in payload["entries"])
        payload["counts"] = {"total": len(payload["entries"]), **{kind: counts[kind] for kind in ("image", "model", "video")}}
        payload["sourceRoots"].pop("Collision", None)
        collision = publish_collision_previews(args.collision_corpus, root=ROOT, asset_dir=ASSET_DIR,
                                                summary_path=args.collision_vfs_summary)
        add_collision_publication(payload, collision)
        print("Collision previews:", collision["status"], collision.get("counts", collision.get("diagnostic", "")), flush=True)
    if args.publish != "collision-authored":
        publish_runtime_metadata(payload, args)
    if args.publish != "collision-runtime":
        publish_authored_metadata(payload, args)
    payload["generated"] = int(time.time())
    if hashlib.sha256(index_path.read_bytes()).digest() != hashlib.sha256(original).digest():
        raise ValueError("Assets index changed during collision publication; rerun against its new publication")
    write_json(index_path, payload)


def publish_runtime_metadata(payload: dict, args: argparse.Namespace) -> None:
    evidence = apply_runtime_publication(
        payload, root=ROOT, selection_path=args.collision_runtime_selection,
        corpus_path=args.collision_corpus, summary_path=args.collision_vfs_summary,
        sessions=args.collision_runtime_session, stored_receipts=args.collision_runtime_stored_receipt,
    )
    print("Collision runtime evidence:", evidence["status"], evidence.get("counts", evidence.get("diagnostic", "")), flush=True)


def publish_authored_metadata(payload: dict, args: argparse.Namespace) -> None:
    evidence = apply_authored_publication(
        payload, root=ROOT, selection_path=args.collision_authored_selection,
        corpus_path=args.collision_corpus, summary_path=args.collision_vfs_summary,
        receipts=args.collision_scene_receipt,
        model_receipt=args.collision_model_receipt,
        asset_dir=ASSET_DIR,
        box_receipt=args.collision_box_receipt,
        render_receipt=args.collision_render_receipt,
        render_resource_receipts=args.collision_render_resource_receipt,
    )
    print("Collision authored owners:", evidence["status"], evidence.get("counts", evidence.get("diagnostic", "")), flush=True)
    renderers=evidence.get('renderers',{})
    if renderers.get('status') not in (None,'missing'):
        print('Collision prefab renderers:',renderers['status'],
              renderers.get('counts',renderers.get('diagnostic','')),flush=True)
    resources=renderers.get('resources',{})
    if resources:
        print('Stored render assets:',resources['status'],resources.get('counts',resources.get('diagnostic','')),flush=True)
        textures=resources.get('texturePreviews',{})
        if textures.get('status') not in (None,'missing'):
            print('Stored texture previews:',textures['status'],dict(decoded=textures.get('decoded',0),unavailable=textures.get('unavailable',0)),textures.get('diagnostic',''),flush=True)


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
