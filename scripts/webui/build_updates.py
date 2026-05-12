#!/usr/bin/env python3
"""Build the WebUI game-data update feed.

This builder intentionally gates the feed on the installed game data tree, not
generated WebUI files. The first run initializes the baseline and writes an
empty update feed so the browser only reports later changes made by game
updates. Exported asset diffs from ``export_full/`` are included only when the
original game-data tracker reports a real game update.

Run from the repo root:
    python scripts/webui/build_updates.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_story_asset_index import ASSET_KIND_BY_EXT, VIDEO_EXTENSIONS
from build_story_paths import resolve_asset_source_roots
from common import display_extension, normalize_posix, read_json, write_json

DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_STATE_DIR = ROOT / ".game-data-tracker"
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_OUT = ROOT / "webui" / "data" / "updates" / "latest.json"
DEFAULT_REPORT_JSON = ROOT / "reports" / "game-data-change-summary.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "game-data-change-summary.md"
TRACKER = ROOT / "scripts" / "track_export_changes.py"
SCHEMA_VERSION = 1
ASSET_STATE_SCHEMA_VERSION = 1
STATUS_ORDER = {"added": 0, "modified": 1, "deleted": 2}
ASSET_HASH_CHUNK_SIZE = 1024 * 1024
IGNORED_GAME_PATH_PREFIXES = (
    # CrashSight writes local crash/telemetry state under the game install.
    # These files churn between runs but are not installed content updates.
    "plugins/x86_64/wesight/crashsight_data/",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build webui/data/updates/latest.json from original game data changes.",
    )
    parser.add_argument(
        "--game-root",
        type=Path,
        default=DEFAULT_GAME_ROOT,
        help="Installed Endfield_Data directory to track.",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=DEFAULT_STATE_DIR,
        help="Persistent tracker state directory. Keep this outside webui/.",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=DEFAULT_EXPORT_ROOT,
        help="Export tree whose image/model/video assets should be diffed after game data changes.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="WebUI update feed JSON path.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=DEFAULT_REPORT_JSON,
        help="Raw tracker JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        default=DEFAULT_REPORT_MD,
        help="Raw tracker Markdown report path.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5000,
        help="Maximum entries per status to carry from the tracker.",
    )
    parser.add_argument(
        "--top-line-limit",
        type=int,
        default=50,
        help="Maximum line-delta entries to preserve in the raw tracker report.",
    )
    parser.add_argument(
        "--reset-baseline",
        action="store_true",
        help="Delete existing tracker state, rescan, and write an empty baseline feed.",
    )
    parser.add_argument(
        "--skip-asset-updates",
        "--skip-exported-assets",
        dest="skip_asset_updates",
        action="store_true",
        help=(
            "Skip the exported image/model/video asset diff. Useful for initial "
            "WebUI builds where only a game-data baseline/feed is needed."
        ),
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help=(
            "Update the game-data tracker state but suppress reported changes "
            "and skip exported asset diffing. Use for initial WebUI data builds."
        ),
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not write timestamped raw tracker history under the state directory.",
    )
    return parser.parse_args(argv)


def tracker_has_baseline(state_dir: Path) -> bool:
    db_path = state_dir / "state.sqlite3"
    if not db_path.exists():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'files'"
            ).fetchone()
            if row is None:
                return False
            count = conn.execute("SELECT COUNT(*) FROM files").fetchone()
            return bool(count and int(count[0]) > 0)
    except sqlite3.Error:
        return False


def classify_game_data_path(path: str) -> str:
    normalized = normalize_posix(path)
    lower = normalized.lower()
    if lower.startswith("streamingassets/"):
        if "/vfs/" in lower:
            return "streaming_vfs"
        if "/aa/" in lower or "/bundles/" in lower:
            return "streaming_bundles"
        return "streaming_assets"
    if lower.startswith("persistent/"):
        if "/vfs/" in lower:
            return "persistent_vfs"
        return "persistent"
    if lower.startswith("managed/"):
        return "managed"
    if lower.startswith("plugins/"):
        return "plugins"
    if lower.startswith("resources/"):
        return "resources"
    if "/" not in lower:
        return "root"
    return lower.split("/", 1)[0] or "other"


def is_ignored_game_update_path(path: str) -> bool:
    lower = normalize_posix(path).lower()
    return any(lower.startswith(prefix) for prefix in IGNORED_GAME_PATH_PREFIXES)


def normalized_entry(status: str, raw: dict[str, Any]) -> dict[str, Any]:
    path = normalize_posix(str(raw.get("path") or ""))
    extension = str(raw.get("extension") or "")
    entry: dict[str, Any] = {
        "status": status,
        "domain": "game",
        "category": classify_game_data_path(path),
        "path": path,
        "extension": extension,
    }
    for key in (
        "old_size",
        "new_size",
        "size_delta",
        "old_line_count",
        "new_line_count",
        "line_delta",
    ):
        if raw.get(key) is not None:
            entry[key] = raw[key]
    return entry


def filtered_game_entries(
    samples: dict[str, Any],
    *,
    suppress_changes: bool,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    entries: list[dict[str, Any]] = []
    ignored_counts: Counter[str] = Counter()
    if suppress_changes:
        return entries, ignored_counts
    for status in ("added", "modified", "deleted"):
        for raw_entry in samples.get(status, []) or []:
            if not isinstance(raw_entry, dict):
                continue
            if is_ignored_game_update_path(str(raw_entry.get("path") or "")):
                ignored_counts[status] += 1
                continue
            entries.append(normalized_entry(status, raw_entry))
    return entries, ignored_counts


def asset_kind_for_suffix(suffix: str) -> str:
    lower = suffix.lower()
    if lower in VIDEO_EXTENSIONS:
        return "video"
    return ASSET_KIND_BY_EXT.get(lower, "")


def hash_file(path: Path) -> str:
    digest = hashlib.blake2b(digest_size=16)
    with path.open("rb") as f:
        while True:
            chunk = f.read(ASSET_HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_asset_snapshot(
    export_root: Path,
    prior_assets: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    prior_assets = prior_assets or {}
    if not export_root.exists():
        return assets

    for source, source_root in resolve_asset_source_roots(export_root):
        if not source_root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(source_root):
            dirnames.sort()
            filenames.sort()
            base_dir = Path(dirpath)
            for filename in filenames:
                path = base_dir / filename
                suffix = path.suffix.lower()
                kind = asset_kind_for_suffix(suffix)
                if not kind:
                    continue
                rel_suffix = path.relative_to(source_root).as_posix()
                rel_path = f"{source}/{rel_suffix}" if rel_suffix else source
                stat = path.stat()
                old_asset = prior_assets.get(rel_path) or {}
                digest = str(old_asset.get("digest") or "")
                if (
                    not digest
                    or int(old_asset.get("size") or -1) != stat.st_size
                    or int(old_asset.get("mtime_ns") or -1) != stat.st_mtime_ns
                ):
                    digest = hash_file(path)
                assets[rel_path] = {
                    "kind": kind,
                    "source": source,
                    "path": rel_path,
                    "extension": suffix,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "digest": digest,
                }
    return assets


def load_asset_state(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path, default={})
    if int(payload.get("schemaVersion") or 0) != ASSET_STATE_SCHEMA_VERSION:
        return {}
    assets = payload.get("assets")
    return assets if isinstance(assets, dict) else {}


def write_asset_state(path: Path, assets: dict[str, dict[str, Any]], *, export_root: Path) -> None:
    payload = {
        "schemaVersion": ASSET_STATE_SCHEMA_VERSION,
        "generated": int(time.time()),
        "generatedAt": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
        "source": "exported_assets",
        "sourceRoot": str(export_root),
        "assets": assets,
    }
    write_json(path, payload)


def asset_update_entry(status: str, asset: dict[str, Any], old_asset: dict[str, Any] | None = None) -> dict[str, Any]:
    rel_path = normalize_posix(str(asset.get("path") or (old_asset or {}).get("path") or ""))
    extension = str(asset.get("extension") or (old_asset or {}).get("extension") or "")
    kind = str(asset.get("kind") or (old_asset or {}).get("kind") or "asset")
    entry: dict[str, Any] = {
        "status": status,
        "domain": "asset",
        "category": f"asset_{kind}",
        "path": rel_path,
        "asset_rel": rel_path,
        "asset_kind": kind,
        "extension": extension,
    }
    old_size = None if status == "added" else (old_asset or {}).get("size")
    new_size = None if status == "deleted" else asset.get("size")
    if old_size is not None:
        entry["old_size"] = old_size
    if new_size is not None:
        entry["new_size"] = new_size
    if old_size is not None and new_size is not None:
        entry["size_delta"] = int(new_size) - int(old_size)
    return entry


def build_asset_diff(
    old_assets: dict[str, dict[str, Any]],
    new_assets: dict[str, dict[str, Any]],
    *,
    sample_limit: int,
) -> dict[str, Any]:
    added: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []

    old_paths = set(old_assets)
    new_paths = set(new_assets)

    for rel_path in sorted(new_paths - old_paths):
        added.append(asset_update_entry("added", new_assets[rel_path]))
    for rel_path in sorted(old_paths - new_paths):
        old_asset = old_assets[rel_path]
        deleted.append(asset_update_entry("deleted", old_asset, old_asset))
    for rel_path in sorted(old_paths & new_paths):
        old_asset = old_assets[rel_path]
        new_asset = new_assets[rel_path]
        if old_asset.get("digest") != new_asset.get("digest"):
            modified.append(asset_update_entry("modified", new_asset, old_asset))

    totals = {
        "added": len(added),
        "modified": len(modified),
        "deleted": len(deleted),
    }
    totals["changed"] = totals["added"] + totals["modified"] + totals["deleted"]

    limited_entries: list[dict[str, Any]] = []
    truncated: dict[str, int] = {}
    for status, entries in (("added", added), ("modified", modified), ("deleted", deleted)):
        limited_entries.extend(entries[:sample_limit])
        truncated[status] = max(0, len(entries) - sample_limit)

    kinds = Counter(str(entry.get("asset_kind") or "asset") for entry in limited_entries)
    extensions = Counter(display_extension(str(entry.get("extension") or "")) for entry in limited_entries)
    return {
        "totals": totals,
        "entries": limited_entries,
        "truncated": truncated,
        "breakdown": {
            "byKind": dict(kinds.most_common()),
            "byExtension": dict(extensions.most_common()),
        },
    }


def zero_totals() -> dict[str, int]:
    return {"added": 0, "modified": 0, "deleted": 0, "changed": 0}


def combine_totals(*totals_list: dict[str, Any]) -> dict[str, int]:
    combined = {"added": 0, "modified": 0, "deleted": 0}
    for totals in totals_list:
        for status in combined:
            combined[status] += int((totals or {}).get(status) or 0)
    combined["changed"] = combined["added"] + combined["modified"] + combined["deleted"]
    return combined


def build_update_payload(
    raw_payload: dict[str, Any],
    *,
    game_root: Path,
    baseline_initialized: bool,
    baseline_only: bool,
    sample_limit: int,
) -> dict[str, Any]:
    changes = raw_payload.get("changes") or {}
    samples = raw_payload.get("samples") or {}
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    suppress_changes = baseline_initialized or baseline_only

    entries, ignored_counts = filtered_game_entries(samples, suppress_changes=suppress_changes)

    entries.sort(key=lambda entry: (STATUS_ORDER.get(str(entry.get("status")), 99), str(entry.get("path", "")).lower()))

    totals = {
        status: max(
            0,
            0 if suppress_changes else int(changes.get(status) or 0) - int(ignored_counts.get(status) or 0),
        )
        for status in ("added", "modified", "deleted")
    }
    totals["changed"] = totals["added"] + totals["modified"] + totals["deleted"]

    captured = Counter(str(entry.get("status") or "") for entry in entries)
    categories = Counter(str(entry.get("category") or "other") for entry in entries)
    extensions = Counter(str(entry.get("extension") or "[no extension]") for entry in entries)

    truncated = {
        status: max(0, totals[status] - captured.get(status, 0))
        for status in ("added", "modified", "deleted")
    }

    game_totals = dict(totals)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "generatedAt": now.isoformat(),
        "generatedBy": "scripts/webui/build_updates.py",
        "source": "original_game_data",
        "sourceRoot": str(game_root),
        "baselineInitialized": baseline_initialized,
        "baselineOnly": baseline_only,
        "gameTotals": game_totals,
        "totals": totals,
        "tracker": {
            "startedAt": raw_payload.get("started_at"),
            "finishedAt": raw_payload.get("finished_at"),
            "durationSeconds": raw_payload.get("duration_seconds"),
            "scannedFiles": raw_payload.get("scanned_files"),
            "metadataOnlyUpdates": 0 if suppress_changes else int(changes.get("metadata_only_updates") or 0),
            "reusedMetadataMatches": int(changes.get("reused_metadata_matches") or 0),
            "sampleLimit": sample_limit,
            "truncated": truncated,
            "ignoredVolatileChanges": dict(ignored_counts),
            "ignoredVolatilePathPrefixes": list(IGNORED_GAME_PATH_PREFIXES),
            "suppressedInitialAdded": int(changes.get("added") or 0) if baseline_initialized else 0,
            "suppressedBaselineOnly": {
                "added": int(changes.get("added") or 0) if baseline_only else 0,
                "modified": int(changes.get("modified") or 0) if baseline_only else 0,
                "deleted": int(changes.get("deleted") or 0) if baseline_only else 0,
            },
        },
        "breakdown": {
            "byCategory": dict(categories.most_common()),
            "byExtension": dict(extensions.most_common()),
            "rawByExtension": raw_payload.get("breakdown") or {},
        },
        "entries": entries,
    }


def attach_asset_updates(
    payload: dict[str, Any],
    *,
    export_root: Path,
    state_dir: Path,
    sample_limit: int,
    skip_asset_updates: bool = False,
) -> None:
    asset_state_path = state_dir / "asset-state.json"
    old_assets = load_asset_state(asset_state_path)
    asset_scan_available = export_root.exists()
    if skip_asset_updates:
        payload["assetTotals"] = zero_totals()
        payload["totals"] = combine_totals(payload.get("gameTotals") or zero_totals())
        payload["assets"] = {
            "source": "exported_assets",
            "sourceRoot": str(export_root),
            "statePath": str(asset_state_path),
            "available": asset_scan_available,
            "skipped": True,
            "skipReason": "skip_asset_updates",
            "stateUpdated": False,
            "baselineInitialized": False,
            "existingBaseline": bool(old_assets),
            "reported": False,
            "reportedOnlyWhenGameDataChanges": True,
            "scannedAssets": 0,
            "sampleLimit": sample_limit,
            "totals": zero_totals(),
            "truncated": {"added": 0, "modified": 0, "deleted": 0},
            "breakdown": {"byKind": {}, "byExtension": {}},
        }
        return

    if not asset_scan_available:
        payload["assetTotals"] = zero_totals()
        payload["totals"] = combine_totals(payload.get("gameTotals") or zero_totals())
        payload["assets"] = {
            "source": "exported_assets",
            "sourceRoot": str(export_root),
            "statePath": str(asset_state_path),
            "available": False,
            "baselineInitialized": not old_assets,
            "reported": False,
            "reportedOnlyWhenGameDataChanges": True,
            "scannedAssets": 0,
            "sampleLimit": sample_limit,
            "totals": zero_totals(),
            "truncated": {"added": 0, "modified": 0, "deleted": 0},
            "breakdown": {"byKind": {}, "byExtension": {}},
        }
        return

    new_assets = build_asset_snapshot(export_root, old_assets)
    asset_baseline_initialized = not old_assets
    game_changed = int((payload.get("gameTotals") or {}).get("changed") or 0) > 0
    game_baseline_initialized = bool(payload.get("baselineInitialized"))

    asset_totals = zero_totals()
    asset_entries: list[dict[str, Any]] = []
    asset_truncated = {"added": 0, "modified": 0, "deleted": 0}
    asset_breakdown = {"byKind": {}, "byExtension": {}}

    if old_assets and game_changed and not game_baseline_initialized:
        diff = build_asset_diff(old_assets, new_assets, sample_limit=sample_limit)
        asset_totals = diff["totals"]
        asset_entries = diff["entries"]
        asset_truncated = diff["truncated"]
        asset_breakdown = diff["breakdown"]

    write_asset_state(asset_state_path, new_assets, export_root=export_root)

    payload["assetTotals"] = asset_totals
    payload["totals"] = combine_totals(payload.get("gameTotals") or zero_totals(), asset_totals)
    payload["assets"] = {
        "source": "exported_assets",
        "sourceRoot": str(export_root),
        "statePath": str(asset_state_path),
        "available": True,
        "baselineInitialized": asset_baseline_initialized,
        "reported": bool(asset_entries),
        "reportedOnlyWhenGameDataChanges": True,
        "scannedAssets": len(new_assets),
        "sampleLimit": sample_limit,
        "totals": asset_totals,
        "truncated": asset_truncated,
        "breakdown": asset_breakdown,
    }
    payload.setdefault("entries", []).extend(asset_entries)
    payload["entries"].sort(key=lambda entry: (
        0 if str(entry.get("domain") or "game") != "asset" else 1,
        STATUS_ORDER.get(str(entry.get("status")), 99),
        str(entry.get("path", "")).lower(),
    ))


def run_tracker(
    *,
    game_root: Path,
    state_dir: Path,
    report_json: Path,
    report_md: Path,
    sample_limit: int,
    top_line_limit: int,
    write_history: bool,
) -> None:
    command = [
        sys.executable,
        str(TRACKER),
        "--root",
        str(game_root),
        "--state-dir",
        str(state_dir),
        "--summary-json",
        str(report_json),
        "--summary-md",
        str(report_md),
        "--sample-limit",
        str(sample_limit),
        "--top-line-limit",
        str(top_line_limit),
    ]
    if write_history:
        command.extend(["--history-dir", str(state_dir / "history")])
    else:
        command.append("--no-history")
    subprocess.run(command, cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    game_root = args.game_root.resolve()
    state_dir = args.state_dir.resolve()
    export_root = args.export_root.resolve()
    out_path = args.out.resolve()
    report_json = args.report_json.resolve()
    report_md = args.report_md.resolve()

    if args.reset_baseline and state_dir.exists():
        shutil.rmtree(state_dir)

    if not game_root.exists():
        raise SystemExit(f"Game data root does not exist: {game_root}")
    if not game_root.is_dir():
        raise SystemExit(f"Game data root is not a directory: {game_root}")

    had_baseline = tracker_has_baseline(state_dir)
    if not had_baseline:
        report_json = state_dir / "initial-baseline-summary.json"
        report_md = state_dir / "initial-baseline-summary.md"

    run_tracker(
        game_root=game_root,
        state_dir=state_dir,
        report_json=report_json,
        report_md=report_md,
        sample_limit=args.sample_limit,
        top_line_limit=args.top_line_limit,
        write_history=bool(had_baseline and not args.no_history and not args.baseline_only),
    )

    raw_payload = json.loads(report_json.read_text(encoding="utf-8"))
    webui_payload = build_update_payload(
        raw_payload,
        game_root=game_root,
        baseline_initialized=not had_baseline,
        baseline_only=args.baseline_only,
        sample_limit=args.sample_limit,
    )
    attach_asset_updates(
        webui_payload,
        export_root=export_root,
        state_dir=state_dir,
        sample_limit=args.sample_limit,
        skip_asset_updates=bool(args.skip_asset_updates or args.baseline_only),
    )

    write_json(out_path, webui_payload, indent=2, compact=False)

    totals = webui_payload["gameTotals"]
    if webui_payload["baselineInitialized"]:
        print(f"[build_updates] Baseline initialized from {game_root}")
    elif webui_payload.get("baselineOnly"):
        suppressed = (webui_payload.get("tracker") or {}).get("suppressedBaselineOnly") or {}
        print(
            "[build_updates] Baseline-only feed:"
            f" suppressed added={int(suppressed.get('added') or 0)},"
            f" modified={int(suppressed.get('modified') or 0)},"
            f" deleted={int(suppressed.get('deleted') or 0)}"
        )
    else:
        print(
            "[build_updates] Game-data changes:"
            f" added={totals['added']}, modified={totals['modified']}, deleted={totals['deleted']}"
        )
    asset_totals = webui_payload.get("assetTotals") or {}
    if (webui_payload.get("assets") or {}).get("skipped"):
        print("[build_updates] Asset changes: skipped (--skip-asset-updates)")
    else:
        print(
            "[build_updates] Asset changes:"
            f" added={int(asset_totals.get('added') or 0)},"
            f" modified={int(asset_totals.get('modified') or 0)},"
            f" deleted={int(asset_totals.get('deleted') or 0)}"
        )
    print(f"[build_updates] WebUI feed: {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(1)
