#!/usr/bin/env python3
"""Build the WebUI update feed.

This builder compares WebUI-facing exported text JSON and exported assets
between two exported game-data trees, such as ``export_1d2/`` and
``export_full/``, and writes the resulting diff for the WebUI Updates tab. The
previous export is cached as the scanner baseline, then the current export is
scanned against that baseline using the same focused roots.

Run from the repo root:
    python scripts/build_updates.py
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
from contextlib import closing
from pathlib import Path
from typing import Any

from common import (
    EXPORT_ROOT,
    OUT_DIR,
    REPORTS_DIR,
    ROOT,
    display_extension,
    normalize_posix,
    path_id_export_base_stem,
    read_json,
    rel_requires_path_id_export_name,
    write_json,
)

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from asset_builder.index import ASSET_KIND_BY_EXT, VIDEO_EXTENSIONS
from source_paths import resolve_asset_source_roots

DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_STATE_DIR = ROOT / ".game-data-tracker"
DEFAULT_EXPORT_ROOT = EXPORT_ROOT
DEFAULT_PREVIOUS_EXPORT_ROOT = ROOT / "export_1d2"
DEFAULT_OUT = OUT_DIR / "updates" / "latest.json"
DEFAULT_REPORT_JSON = REPORTS_DIR / "game-data-change-summary.json"
DEFAULT_REPORT_MD = REPORTS_DIR / "game-data-change-summary.md"
TRACKER = ROOT / "scripts" / "track_export_changes.py"
SCHEMA_VERSION = 1
ASSET_STATE_SCHEMA_VERSION = 1
EXPORT_BASELINE_CONFIG_SCHEMA_VERSION = 2
STATUS_ORDER = {"added": 0, "modified": 1, "deleted": 2}
ASSET_HASH_CHUNK_SIZE = 1024 * 1024
ASSET_DEFAULT_FINGERPRINT_MODE = "size"
ASSET_HASH_FINGERPRINT_MODE = "content_hash"
AUDIO_EXTENSIONS = {
    ".wav",
    ".wem",
}
AUDIO_EXPORT_RELATIVE_ROOT = "structured/Audio"
AUDIO_SOURCE_LABEL = "Audio"
DECODED_IMPACT_SAMPLE_LIMIT = 200
PRUNE_SAMPLE_LIMIT = 200
IGNORED_GAME_PATH_PREFIXES = (
    # CrashSight writes local crash/telemetry state under the game install.
    # These files churn between runs but are not installed content updates.
    "plugins/x86_64/wesight/crashsight_data/",
)
WEBUI_TEXT_JSON_RELATIVE_PATHS = (
    "structured/StreamingAssets/Table",
    "structured/Persistent/Table",
    "structured/StreamingAssets/Data/Json/MissionRuntimeAsset",
    "structured/Persistent/Data/Json/MissionRuntimeAsset",
    "structured/StreamingAssets/Data/Json/LevelData",
    "structured/StreamingAssets/Data/Json/LevelScriptData",
    "structured/StreamingAssets/Data/Json/LevelScriptTemplateData",
    "structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json",
    "structured/StreamingAssets/Data/Json/GameplayConfig/MissionAreaTable.json",
    "structured/StreamingAssets/Data/Json/GameplayConfig/NpcProxyTable.json",
    "structured/StreamingAssets/Data/Json/GameplayConfig/NpcProxyExDataTable.json",
    "structured/StreamingAssets/Data/Json/GameplayConfig/AtmosphericNpcClusterDataTable.json",
    "recovered/dialog_id_table_index.json",
    "recovered/story_source_links.json",
    "recovered/video_bindings.json",
    "recovered/AnimeStudio-cli/timeline_line_orders.json",
)

CHK_DECODE_DIR = SCRIPT_DIR / "chk_decode"
if str(CHK_DECODE_DIR) not in sys.path:
    sys.path.insert(0, str(CHK_DECODE_DIR))

try:
    from decode_persistent_vfs import decrypt_blc, parse_block_main_info
except Exception:  # pragma: no cover - update feed should still build without optional decode context.
    decrypt_blc = None
    parse_block_main_info = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build webui/data/updates/latest.json from focused exported text "
            "JSON and media asset diffs."
        ),
    )
    parser.add_argument(
        "--game-root",
        type=Path,
        default=DEFAULT_GAME_ROOT,
        help=(
            "Installed Endfield_Data directory used only for optional decoded-impact "
            "mapping when applicable."
        ),
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=DEFAULT_STATE_DIR,
        help="Persistent scanner cache and feed-history directory. Keep this outside webui/.",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=DEFAULT_EXPORT_ROOT,
        help="Current exported game-data tree, usually export_full/.",
    )
    parser.add_argument(
        "--previous-export-root",
        "--old-export-root",
        dest="previous_export_root",
        type=Path,
        default=DEFAULT_PREVIOUS_EXPORT_ROOT,
        help="Previous exported game-data tree to compare against, usually export_1d2/.",
    )
    parser.add_argument(
        "--refresh-previous-export-baseline",
        action="store_true",
        help="Rebuild the cached scanner baseline for --previous-export-root before comparing.",
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
        help="Delete cached update-diff state before rebuilding the previous-export baseline.",
    )
    parser.add_argument(
        "--skip-asset-updates",
        dest="skip_asset_updates",
        action="store_true",
        help=(
            "Skip the exported image/model/video/audio asset diff. By default "
            "Updates tracks media assets plus WebUI-facing text JSON."
        ),
    )
    parser.add_argument(
        "--include-asset-updates",
        dest="skip_asset_updates",
        action="store_false",
        help="Compatibility flag; asset updates are included by default.",
    )
    parser.set_defaults(skip_asset_updates=False)
    parser.add_argument(
        "--full-export-scan",
        action="store_true",
        help=(
            "Use the older broad export-folder scan instead of the focused "
            "WebUI text JSON scan."
        ),
    )
    parser.add_argument(
        "--hash-asset-updates",
        action="store_true",
        help=(
            "Hash exported asset contents when comparing assets. Slower, but "
            "detects same-size binary modifications."
        ),
    )
    parser.add_argument(
        "--prune-previous-export-untracked",
        action="store_true",
        help=(
            "After a successful comparison, delete previous-export files that "
            "exist byte-identically at the same relative path in the current "
            "export root."
        ),
    )
    parser.add_argument(
        "--dry-run-prune-previous-export-untracked",
        action="store_true",
        help=(
            "Report which previous-export files would be deleted by "
            "--prune-previous-export-untracked without deleting them."
        ),
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help=(
            "Suppress reported changes and skip exported media asset diffing. "
            "Use for initial WebUI data builds."
        ),
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not write timestamped raw scanner history for this comparison.",
    )
    return parser.parse_args(argv)


def tracker_has_baseline(state_dir: Path) -> bool:
    db_path = state_dir / "state.sqlite3"
    if not db_path.exists():
        return False
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'files'"
            ).fetchone()
            if row is None:
                return False
            count = conn.execute("SELECT COUNT(*) FROM files").fetchone()
            return bool(count and int(count[0]) > 0)
    except sqlite3.Error:
        return False


def empty_tracker_payload() -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    return {
        "started_at": now.isoformat(),
        "finished_at": now.isoformat(),
        "duration_seconds": 0.0,
        "scanned_files": 0,
        "changes": {
            "added": 0,
            "modified": 0,
            "deleted": 0,
            "metadata_only_updates": 0,
            "reused_metadata_matches": 0,
        },
        "breakdown": {
            "added_by_extension": {},
            "modified_by_extension": {},
            "deleted_by_extension": {},
        },
        "samples": {
            "added": [],
            "modified": [],
            "deleted": [],
            "largest_line_changes": [],
        },
    }


def export_baseline_state_dir(state_dir: Path) -> Path:
    return state_dir / "previous-export-baseline"


def export_compare_state_dir(state_dir: Path) -> Path:
    return state_dir / "export-diff-work"


def export_baseline_config_path(state_dir: Path) -> Path:
    return export_baseline_state_dir(state_dir) / "baseline.json"


def normalized_relative_paths(paths: list[str] | tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for path in paths:
        normalized = normalize_posix(path)
        if normalized:
            out.append(normalized)
    return out


def export_baseline_config_matches(
    state_dir: Path,
    previous_export_root: Path,
    *,
    include_relative_paths: list[str],
) -> bool:
    config = read_json(export_baseline_config_path(state_dir), default={})
    if not isinstance(config, dict):
        return False
    return (
        int(config.get("schemaVersion") or 0) == EXPORT_BASELINE_CONFIG_SCHEMA_VERSION
        and normalize_posix(str(config.get("previousExportRoot") or ""))
        == normalize_posix(str(previous_export_root))
        and list(config.get("includeRelativePaths") or []) == normalized_relative_paths(include_relative_paths)
    )


def write_export_baseline_config(
    state_dir: Path,
    previous_export_root: Path,
    *,
    include_relative_paths: list[str],
) -> None:
    write_json(
        export_baseline_config_path(state_dir),
        {
            "schemaVersion": EXPORT_BASELINE_CONFIG_SCHEMA_VERSION,
            "source": "previous_export_root",
            "previousExportRoot": str(previous_export_root),
            "includeRelativePaths": normalized_relative_paths(include_relative_paths),
            "generated": int(time.time()),
            "generatedAt": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
        },
        indent=2,
        compact=False,
    )


def classify_game_data_path(path: str) -> str:
    normalized = normalize_posix(path)
    lower = normalized.lower()
    parts = [part for part in lower.split("/") if part]
    if parts[:1] == ["structured"]:
        source = parts[1] if len(parts) > 1 else "unknown"
        if len(parts) > 2 and parts[2] in {"data", "table"}:
            return f"structured_{source}_{parts[2]}"
        if len(parts) > 2:
            return f"structured_{source}_{parts[2]}"
        return f"structured_{source}"
    if parts[:2] == ["recovered", "animestudio-cli"]:
        source = parts[2] if len(parts) > 2 else "unknown"
        stage = parts[3] if len(parts) > 3 else "root"
        if source in {"persistent", "streamingassets"}:
            return f"recovered_{source}_{stage}"
        return "recovered_animestudio"
    if parts[:1] == ["raw_vfs"]:
        source = parts[1] if len(parts) > 1 else "unknown"
        return f"raw_vfs_{source}"
    if parts[:1] == ["unresolved"]:
        return "unresolved_export"
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


def normalized_entry(status: str, raw: dict[str, Any], *, domain: str = "game") -> dict[str, Any]:
    path = normalize_posix(str(raw.get("path") or ""))
    extension = str(raw.get("extension") or "")
    entry: dict[str, Any] = {
        "status": status,
        "domain": domain,
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
    if raw.get("text_diff"):
        entry["text_diff"] = raw["text_diff"]
        if raw.get("text_diff_truncated"):
            entry["text_diff_truncated"] = True
    return entry


def persistent_vfs_parts(path: str) -> tuple[str, str, str] | None:
    normalized = normalize_posix(path)
    parts = normalized.split("/")
    if len(parts) < 4:
        return None
    if parts[0].lower() != "persistent" or parts[1].lower() != "vfs":
        return None
    return parts[2], parts[3], Path(parts[3]).suffix.lower()


def decoded_display_tags(decoded_rel: str) -> list[str]:
    lower = normalize_posix(decoded_rel).lower()
    tags: list[str] = []
    suffix = Path(lower).suffix
    if "/bundles/" in lower or suffix in {".ab", ".bundle"}:
        tags.append("bundle")
    if "/dialog/" in lower or "dlgtl_" in lower or "dialog" in lower:
        tags.append("story")
    if "/timeline/" in lower or suffix in {".playable", ".controller"}:
        tags.append("timeline")
    if "/audio/" in lower or suffix in {".pck", ".bnk", ".wem"}:
        tags.append("audio")
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tga", ".ktx", ".ktx2", ".dds"}:
        tags.append("image")
    if suffix in {".mp4", ".webm", ".mov", ".usm"}:
        tags.append("video")
    if suffix in {".prefab", ".mat", ".asset", ".anim", ".fbx"}:
        tags.append("unity_asset")
    if "/lua/" in lower or suffix == ".lua":
        tags.append("lua")
    if "/table/" in lower or "/config/" in lower or suffix in {".json", ".bytes", ".csv"}:
        tags.append("data")
    return tags or ["decoded_file"]


def summarize_decoded_files(block: str, rel_files: list[str]) -> dict[str, Any]:
    paths: list[str] = []
    tags = Counter()
    extensions = Counter()
    for rel in rel_files:
        rel_norm = normalize_posix(rel)
        decoded_path = normalize_posix(str(Path("export_full") / "raw_vfs" / "Persistent" / "files" / block / rel_norm))
        paths.append(decoded_path)
        extensions[display_extension(Path(rel_norm).suffix)] += 1
        tags.update(decoded_display_tags(rel_norm))
    return {
        "count": len(paths),
        "sample": paths[:DECODED_IMPACT_SAMPLE_LIMIT],
        "truncated": max(0, len(paths) - DECODED_IMPACT_SAMPLE_LIMIT),
        "byExtension": dict(extensions.most_common(12)),
        "tags": dict(tags.most_common()),
    }


def parse_current_block_manifest(game_root: Path, block: str) -> tuple[dict[str, list[str]], str | None]:
    if decrypt_blc is None or parse_block_main_info is None:
        return {}, "decode_persistent_vfs helpers unavailable"
    blc_path = game_root / "Persistent" / "VFS" / block / f"{block}.blc"
    if not blc_path.exists():
        return {}, f"current .blc not found: {normalize_posix(str(blc_path))}"
    try:
        info = parse_block_main_info(decrypt_blc(blc_path), verify_crc=True)
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    return {
        chunk.chk_file_name(): [file_info.file_name for file_info in chunk.files if file_info.file_name]
        for chunk in info.chunks
    }, None


def decoded_impact_for_entry(
    entry: dict[str, Any],
    *,
    game_root: Path,
    manifest_cache: dict[str, tuple[dict[str, list[str]], str | None]],
) -> dict[str, Any] | None:
    parts = persistent_vfs_parts(str(entry.get("path") or ""))
    if parts is None:
        return None
    block, name, suffix = parts
    if suffix not in {".chk", ".blc"}:
        return None
    if block not in manifest_cache:
        manifest_cache[block] = parse_current_block_manifest(game_root, block)
    manifest, error = manifest_cache[block]
    status = str(entry.get("status") or "")
    impact: dict[str, Any] = {
        "source": "current_persistent_vfs_manifest",
        "block": block,
        "sourceFile": name,
        "sourceExtension": suffix,
        "sampleLimit": DECODED_IMPACT_SAMPLE_LIMIT,
        "confidence": "current_manifest",
    }
    if error:
        impact["error"] = error
        impact["count"] = 0
        impact["sample"] = []
        impact["truncated"] = 0
        return impact

    if suffix == ".chk":
        rel_files = manifest.get(name, [])
        impact.update(summarize_decoded_files(block, rel_files))
        if not rel_files and status == "deleted":
            impact["confidence"] = "deleted_chunk_unmapped"
            impact["note"] = "The chunk is deleted and the current .blc no longer maps it to decoded filenames."
        elif status == "deleted":
            impact["confidence"] = "current_manifest_possible_stale"
            impact["note"] = "Deleted chunks are mapped only if the current .blc still references them."
        else:
            impact["confidence"] = "chunk_to_current_manifest"
        return impact

    rel_files = []
    for chunk_files in manifest.values():
        rel_files.extend(chunk_files)
    impact.update(summarize_decoded_files(block, sorted(rel_files)))
    impact["confidence"] = "block_manifest_current_files"
    impact["note"] = "The .blc changed, so this lists files in the current block manifest; exact old-vs-new membership requires the previous .blc."
    return impact


def attach_decoded_impacts(payload: dict[str, Any], *, game_root: Path) -> None:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return
    manifest_cache: dict[str, tuple[dict[str, list[str]], str | None]] = {}
    totals = Counter()
    tag_totals = Counter()
    with_impacts = 0
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("domain") != "game":
            continue
        impact = decoded_impact_for_entry(entry, game_root=game_root, manifest_cache=manifest_cache)
        if impact is None:
            continue
        entry["decodedImpact"] = impact
        with_impacts += 1
        totals[str(entry.get("status") or "")] += int(impact.get("count") or 0)
        tag_totals.update(impact.get("tags") or {})
    payload["decodedImpacts"] = {
        "source": "current_persistent_vfs_manifest",
        "available": decrypt_blc is not None and parse_block_main_info is not None,
        "entriesWithImpact": with_impacts,
        "decodedFileMentions": sum(totals.values()),
        "byStatus": dict(totals),
        "byTag": dict(tag_totals.most_common()),
        "sampleLimit": DECODED_IMPACT_SAMPLE_LIMIT,
        "note": "For modified .blc files, impact uses current manifest contents. Deleted chunks may not map without historical .blc data.",
    }


def filtered_game_entries(
    samples: dict[str, Any],
    *,
    suppress_changes: bool,
    domain: str = "game",
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
            entries.append(normalized_entry(status, raw_entry, domain=domain))
    return entries, ignored_counts


def asset_kind_for_suffix(suffix: str) -> str:
    lower = suffix.lower()
    if lower in AUDIO_EXTENSIONS:
        return "audio"
    if lower in VIDEO_EXTENSIONS:
        return "video"
    return ASSET_KIND_BY_EXT.get(lower, "")


def resolve_update_asset_source_roots(export_root: Path) -> list[tuple[str, Path]]:
    roots = list(resolve_asset_source_roots(export_root))
    audio_root = export_root / AUDIO_EXPORT_RELATIVE_ROOT
    if audio_root.exists():
        roots.append((AUDIO_SOURCE_LABEL, audio_root))
    return roots


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
    *,
    hash_contents: bool = False,
    preserve_missing_prior_assets: bool = False,
) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    prior_assets = prior_assets or {}
    if not export_root.exists():
        return assets

    for source, source_root in resolve_update_asset_source_roots(export_root):
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
                if rel_requires_path_id_export_name(rel_path) and not path_id_export_base_stem(path.stem):
                    continue
                stat = path.stat()
                export_rel = path.relative_to(export_root).as_posix()
                old_asset = prior_assets.get(rel_path) or {}
                fingerprint_mode = ASSET_HASH_FINGERPRINT_MODE if hash_contents else ASSET_DEFAULT_FINGERPRINT_MODE
                if hash_contents:
                    old_mode = str(old_asset.get("fingerprintMode") or ASSET_HASH_FINGERPRINT_MODE)
                    digest = str(old_asset.get("digest") or "")
                    if (
                        old_mode != ASSET_HASH_FINGERPRINT_MODE
                        or not digest
                        or int(old_asset.get("size") or -1) != stat.st_size
                        or int(old_asset.get("mtime_ns") or -1) != stat.st_mtime_ns
                    ):
                        digest = hash_file(path)
                else:
                    digest = f"size:{stat.st_size}"
                if not digest:
                    digest = hash_file(path)
                assets[rel_path] = {
                    "kind": kind,
                    "source": source,
                    "path": rel_path,
                    "export_rel": export_rel,
                    "extension": suffix,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "digest": digest,
                    "fingerprintMode": fingerprint_mode,
                }
    if preserve_missing_prior_assets:
        for rel_path, old_asset in prior_assets.items():
            if rel_path in assets or not isinstance(old_asset, dict):
                continue
            preserved = dict(old_asset)
            preserved["missing_on_disk"] = True
            assets[rel_path] = preserved
    return assets


def asset_source_roots_payload(export_root: Path) -> dict[str, str]:
    roots: dict[str, str] = {}
    for source, source_root in resolve_update_asset_source_roots(export_root):
        roots[source] = normalize_posix(str(source_root))
    return roots


def load_asset_state(path: Path, *, export_root: Path | None = None) -> dict[str, dict[str, Any]]:
    payload = read_json(path, default={})
    if int(payload.get("schemaVersion") or 0) != ASSET_STATE_SCHEMA_VERSION:
        return {}
    if export_root is not None:
        state_root = normalize_posix(str(payload.get("sourceRoot") or ""))
        expected_root = normalize_posix(str(export_root))
        if state_root and state_root.lower() != expected_root.lower():
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


def iter_existing_relative_files(root: Path) -> list[str]:
    out: list[str] = []
    if not root.exists():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()
        base_dir = Path(dirpath)
        for filename in filenames:
            path = base_dir / filename
            if path.is_file():
                out.append(path.relative_to(root).as_posix())
    return out


def files_match_for_prune(previous_path: Path, current_path: Path) -> bool:
    try:
        previous_stat = previous_path.stat()
        current_stat = current_path.stat()
    except OSError:
        return False
    if previous_stat.st_size != current_stat.st_size:
        return False
    try:
        with previous_path.open("rb") as previous_file, current_path.open("rb") as current_file:
            while True:
                previous_chunk = previous_file.read(ASSET_HASH_CHUNK_SIZE)
                current_chunk = current_file.read(ASSET_HASH_CHUNK_SIZE)
                if previous_chunk != current_chunk:
                    return False
                if not previous_chunk:
                    return True
    except OSError:
        return False


def collect_unchanged_current_relative_files(previous_root: Path, current_root: Path) -> set[str]:
    """Return previous files that current export already carries unchanged."""
    unchanged: set[str] = set()
    for rel_path in iter_existing_relative_files(previous_root):
        previous_path = previous_root / rel_path
        current_path = current_root / rel_path
        try:
            if current_path.is_file() and files_match_for_prune(previous_path, current_path):
                unchanged.add(rel_path)
        except OSError:
            continue
    return unchanged


def assert_safe_previous_export_prune(previous_export_root: Path, current_export_root: Path) -> None:
    previous_resolved = previous_export_root.resolve()
    current_resolved = current_export_root.resolve()
    repo_root = ROOT.resolve()
    if previous_resolved == current_resolved:
        raise SystemExit(
            "--prune-previous-export-untracked refuses to delete from the current export root. "
            "Pass a distinct --previous-export-root."
        )
    if previous_resolved == repo_root:
        raise SystemExit("--prune-previous-export-untracked refuses to delete from the repository root.")
    if not previous_resolved.exists() or not previous_resolved.is_dir():
        raise SystemExit(f"Previous export root is not a directory: {previous_export_root}")
    if not ((previous_resolved / "structured").exists() or (previous_resolved / "recovered").exists()):
        raise SystemExit(
            "--prune-previous-export-untracked expected an export tree with "
            f"'structured' or 'recovered': {previous_export_root}"
        )


def remove_empty_dirs(root: Path) -> int:
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        path = Path(dirpath)
        if path == root:
            continue
        try:
            path.rmdir()
        except OSError:
            continue
        removed += 1
    return removed


def prune_previous_export_untracked(
    *,
    previous_export_root: Path,
    current_export_root: Path,
    dry_run: bool,
) -> dict[str, Any]:
    assert_safe_previous_export_prune(previous_export_root, current_export_root)

    previous_resolved = previous_export_root.resolve()
    unchanged_current_paths = collect_unchanged_current_relative_files(previous_resolved, current_export_root.resolve())
    all_paths = set(iter_existing_relative_files(previous_resolved))
    delete_paths = sorted(unchanged_current_paths)

    deleted_files = 0
    bytes_deleted = 0
    for rel_path in delete_paths:
        path = previous_resolved / rel_path
        try:
            resolved = path.resolve()
            resolved.relative_to(previous_resolved)
            size = resolved.stat().st_size
        except (OSError, ValueError):
            continue
        bytes_deleted += int(size)
        if not dry_run:
            resolved.unlink()
        deleted_files += 1

    empty_dirs_deleted = 0 if dry_run else remove_empty_dirs(previous_resolved)
    return {
        "enabled": True,
        "dryRun": dry_run,
        "previousExportRoot": str(previous_export_root),
        "trackedFiles": len(all_paths),
        "unchangedCurrentFiles": len(unchanged_current_paths),
        "keptFiles": len(all_paths - unchanged_current_paths),
        "deletedFiles": deleted_files,
        "bytesDeleted": bytes_deleted,
        "emptyDirsDeleted": empty_dirs_deleted,
        "sampleLimit": PRUNE_SAMPLE_LIMIT,
        "sample": delete_paths[:PRUNE_SAMPLE_LIMIT],
    }


def asset_update_entry(status: str, asset: dict[str, Any], old_asset: dict[str, Any] | None = None) -> dict[str, Any]:
    rel_path = normalize_posix(str(asset.get("path") or (old_asset or {}).get("path") or ""))
    old_rel_path = normalize_posix(str((old_asset or {}).get("path") or ""))
    new_rel_path = normalize_posix(str(asset.get("path") or ""))
    old_export_rel = normalize_posix(str((old_asset or {}).get("export_rel") or ""))
    new_export_rel = normalize_posix(str(asset.get("export_rel") or ""))
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
    if old_rel_path:
        entry["old_asset_rel"] = old_rel_path
    if new_rel_path:
        entry["new_asset_rel"] = new_rel_path
    if old_export_rel:
        entry["old_asset_export_rel"] = old_export_rel
    if new_export_rel:
        entry["new_asset_export_rel"] = new_export_rel
    old_size = None if status == "added" else (old_asset or {}).get("size")
    new_size = None if status == "deleted" else asset.get("size")
    if old_size is not None:
        entry["old_size"] = old_size
    if new_size is not None:
        entry["new_size"] = new_size
    if old_size is not None and new_size is not None:
        entry["size_delta"] = int(new_size) - int(old_size)
    return entry


def asset_is_modified(old_asset: dict[str, Any], new_asset: dict[str, Any]) -> bool:
    if old_asset.get("digest") == new_asset.get("digest"):
        return False
    if (
        old_asset.get("missing_on_disk")
        and old_asset.get("size") is not None
        and new_asset.get("size") is not None
        and int(old_asset.get("size") or -1) == int(new_asset.get("size") or -2)
    ):
        return False
    return True


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
        if asset_is_modified(old_asset, new_asset):
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


def total_reported_changes(payload: dict[str, Any]) -> int:
    totals = payload.get("totals") or payload.get("gameTotals") or {}
    return int(totals.get("changed") or 0)


def total_game_changes(payload: dict[str, Any]) -> int:
    totals = payload.get("gameTotals") or {}
    return int(totals.get("changed") or 0)


def find_latest_changed_history(
    *,
    state_dir: Path,
    game_root: Path,
    sample_limit: int,
    scan_scope: str,
    include_relative_paths: list[str],
) -> tuple[dict[str, Any], Path] | None:
    history_dir = state_dir / "history"
    if not history_dir.exists():
        return None
    candidates = sorted(
        history_dir.glob("export-change-summary-*.json"),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    for path in candidates:
        raw_payload = read_json(path, default={})
        if not isinstance(raw_payload, dict):
            continue
        candidate = build_update_payload(
            raw_payload,
            game_root=game_root,
            baseline_initialized=False,
            baseline_only=False,
            sample_limit=sample_limit,
            scan_scope=scan_scope,
            include_relative_paths=include_relative_paths,
        )
        if total_game_changes(candidate) > 0:
            return raw_payload, path
    return None


def find_latest_update_feed_history(state_dir: Path) -> tuple[dict[str, Any], Path] | None:
    history_dir = state_dir / "history"
    if not history_dir.exists():
        return None
    candidates = sorted(
        history_dir.glob("update-feed-*.json"),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    for path in candidates:
        payload = read_json(path, default={})
        if isinstance(payload, dict) and total_reported_changes(payload) > 0:
            return payload, path
    return None


def write_update_feed_history(payload: dict[str, Any], state_dir: Path) -> Path | None:
    if total_reported_changes(payload) <= 0:
        return None
    history_dir = state_dir / "history"
    stamp = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    history_path = history_dir / f"update-feed-{stamp}.json"
    write_json(history_path, payload, indent=2, compact=False)
    return history_path


def restore_zero_change_feed(
    *,
    current_payload: dict[str, Any],
    out_path: Path,
    state_dir: Path,
    game_root: Path,
    export_root: Path,
    sample_limit: int,
    scan_scope: str,
    include_relative_paths: list[str],
) -> tuple[dict[str, Any], str] | None:
    existing_payload = read_json(out_path, default={})
    if isinstance(existing_payload, dict) and total_reported_changes(existing_payload) > 0:
        return existing_payload, "preserved_existing_feed"

    latest_feed = find_latest_update_feed_history(state_dir)
    if latest_feed is not None:
        payload, history_path = latest_feed
        payload["restoredAfterZeroChangeScan"] = {
            "source": "update_feed_history",
            "historyPath": str(history_path),
            "zeroChangeTracker": current_payload.get("tracker") or {},
        }
        return payload, "restored_from_feed_history"

    latest_history = find_latest_changed_history(
        state_dir=state_dir,
        game_root=game_root,
        sample_limit=sample_limit,
        scan_scope=scan_scope,
        include_relative_paths=include_relative_paths,
    )
    if latest_history is None:
        return None

    raw_payload, history_path = latest_history
    restored_payload = build_update_payload(
        raw_payload,
        game_root=game_root,
        baseline_initialized=False,
        baseline_only=False,
        sample_limit=sample_limit,
        scan_scope=scan_scope,
        include_relative_paths=include_relative_paths,
    )
    attach_asset_updates(
        restored_payload,
        export_root=export_root,
        state_dir=state_dir,
        sample_limit=sample_limit,
        skip_asset_updates=True,
        hash_asset_updates=False,
    )
    restored_payload["restoredAfterZeroChangeScan"] = {
        "source": "tracker_history",
        "historyPath": str(history_path),
        "zeroChangeTracker": current_payload.get("tracker") or {},
    }
    return restored_payload, "restored_from_history"


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
    previous_game_root: Path | None = None,
    baseline_initialized: bool,
    baseline_only: bool,
    sample_limit: int,
    scan_scope: str,
    include_relative_paths: list[str],
) -> dict[str, Any]:
    changes = raw_payload.get("changes") or {}
    samples = raw_payload.get("samples") or {}
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    suppress_changes = baseline_initialized or baseline_only

    entry_domain = "text" if scan_scope == "webui_text_json" else "game"
    entries, ignored_counts = filtered_game_entries(
        samples,
        suppress_changes=suppress_changes,
        domain=entry_domain,
    )

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
    if scan_scope == "webui_text_json":
        source = "webui_text_json_export_diff"
    else:
        source = "export_folder_diff" if previous_game_root is not None else "original_game_data"
    tracker_payload = {
        "startedAt": raw_payload.get("started_at"),
        "finishedAt": raw_payload.get("finished_at"),
        "durationSeconds": raw_payload.get("duration_seconds"),
        "scannedFiles": raw_payload.get("scanned_files"),
        "scanScope": scan_scope,
        "includeRelativePaths": normalized_relative_paths(include_relative_paths),
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
    }
    if previous_game_root is not None:
        tracker_payload.update(
            {
                "comparisonMode": "export_folder_diff",
                "previousSourceRoot": str(previous_game_root),
                "currentSourceRoot": str(game_root),
            }
        )

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "generatedAt": now.isoformat(),
        "generatedBy": "scripts/build_updates.py",
        "source": source,
        "sourceRoot": str(game_root),
        "baselineInitialized": baseline_initialized,
        "baselineOnly": baseline_only,
        "gameTotals": game_totals,
        "textTotals": game_totals if entry_domain == "text" else zero_totals(),
        "totals": totals,
        "tracker": tracker_payload,
        "breakdown": {
            "byCategory": dict(categories.most_common()),
            "byExtension": dict(extensions.most_common()),
            "rawByExtension": raw_payload.get("breakdown") or {},
        },
        "entries": entries,
    }
    if previous_game_root is not None:
        payload["previousSourceRoot"] = str(previous_game_root)
    return payload


def attach_asset_updates(
    payload: dict[str, Any],
    *,
    export_root: Path,
    previous_export_root: Path | None = None,
    state_dir: Path,
    sample_limit: int,
    skip_asset_updates: bool = False,
    hash_asset_updates: bool = False,
) -> None:
    asset_state_path = state_dir / "asset-state.json"
    old_assets = load_asset_state(asset_state_path, export_root=export_root)
    asset_scan_available = export_root.exists()
    asset_source_roots = asset_source_roots_payload(export_root)
    previous_asset_source_roots = (
        asset_source_roots_payload(previous_export_root) if previous_export_root is not None else {}
    )
    if skip_asset_updates:
        payload["assetTotals"] = zero_totals()
        payload["totals"] = combine_totals(payload.get("gameTotals") or zero_totals())
        payload["assets"] = {
            "source": "exported_assets",
            "sourceRoot": str(export_root),
            "previousSourceRoot": str(previous_export_root) if previous_export_root is not None else None,
            "sourceRoots": asset_source_roots,
            "previousSourceRoots": previous_asset_source_roots,
            "statePath": str(asset_state_path),
            "available": asset_scan_available,
            "skipped": True,
            "skipReason": "skip_asset_updates",
            "stateUpdated": False,
            "baselineInitialized": False,
            "existingBaseline": bool(old_assets),
            "reported": False,
            "reportedOnlyWhenGameDataChanges": previous_export_root is None,
            "comparisonMode": "export_folder_diff" if previous_export_root is not None else "stateful_exported_assets",
            "scannedAssets": 0,
            "sampleLimit": sample_limit,
            "totals": zero_totals(),
            "truncated": {"added": 0, "modified": 0, "deleted": 0},
            "breakdown": {"byKind": {}, "byExtension": {}},
        }
        return

    if previous_export_root is not None:
        previous_asset_scan_available = previous_export_root.exists()
        if not asset_scan_available or not previous_asset_scan_available:
            payload["assetTotals"] = zero_totals()
            payload["totals"] = combine_totals(payload.get("gameTotals") or zero_totals())
            payload["assets"] = {
                "source": "exported_assets",
                "sourceRoot": str(export_root),
                "previousSourceRoot": str(previous_export_root),
                "sourceRoots": asset_source_roots,
                "previousSourceRoots": previous_asset_source_roots,
                "statePath": str(asset_state_path),
                "available": False,
                "previousAvailable": previous_asset_scan_available,
                "baselineInitialized": False,
                "reported": False,
                "reportedOnlyWhenGameDataChanges": False,
                "comparisonMode": "export_folder_diff",
                "scannedAssets": 0,
                "previousScannedAssets": 0,
                "sampleLimit": sample_limit,
                "totals": zero_totals(),
                "truncated": {"added": 0, "modified": 0, "deleted": 0},
                "breakdown": {"byKind": {}, "byExtension": {}},
            }
            return

        previous_asset_state_path = state_dir / "asset-state-previous-export.json"
        current_asset_state_path = state_dir / "asset-state-current-export.json"
        old_assets = build_asset_snapshot(
            previous_export_root,
            load_asset_state(previous_asset_state_path, export_root=previous_export_root),
            hash_contents=hash_asset_updates,
            preserve_missing_prior_assets=True,
        )
        new_assets = build_asset_snapshot(
            export_root,
            load_asset_state(current_asset_state_path, export_root=export_root),
            hash_contents=hash_asset_updates,
        )
        diff = build_asset_diff(old_assets, new_assets, sample_limit=sample_limit)
        asset_totals = diff["totals"]
        asset_entries = diff["entries"]
        write_asset_state(previous_asset_state_path, old_assets, export_root=previous_export_root)
        write_asset_state(current_asset_state_path, new_assets, export_root=export_root)

        payload["assetTotals"] = asset_totals
        payload["totals"] = combine_totals(payload.get("gameTotals") or zero_totals(), asset_totals)
        payload["assets"] = {
            "source": "exported_assets",
            "sourceRoot": str(export_root),
            "previousSourceRoot": str(previous_export_root),
            "sourceRoots": asset_source_roots,
            "previousSourceRoots": previous_asset_source_roots,
            "statePath": str(current_asset_state_path),
            "previousStatePath": str(previous_asset_state_path),
            "available": True,
            "previousAvailable": True,
            "stateUpdated": True,
            "baselineInitialized": False,
            "reported": bool(asset_entries),
            "reportedOnlyWhenGameDataChanges": False,
            "comparisonMode": "export_folder_diff",
            "scannedAssets": len(new_assets),
            "previousScannedAssets": len(old_assets),
            "sampleLimit": sample_limit,
            "fingerprintMode": ASSET_HASH_FINGERPRINT_MODE if hash_asset_updates else ASSET_DEFAULT_FINGERPRINT_MODE,
            "totals": asset_totals,
            "truncated": diff["truncated"],
            "breakdown": diff["breakdown"],
        }
        payload.setdefault("entries", []).extend(asset_entries)
        payload["entries"].sort(key=lambda entry: (
            0 if str(entry.get("domain") or "game") != "asset" else 1,
            STATUS_ORDER.get(str(entry.get("status")), 99),
            str(entry.get("path", "")).lower(),
        ))
        return

    if not asset_scan_available:
        payload["assetTotals"] = zero_totals()
        payload["totals"] = combine_totals(payload.get("gameTotals") or zero_totals())
        payload["assets"] = {
            "source": "exported_assets",
            "sourceRoot": str(export_root),
            "sourceRoots": asset_source_roots,
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

    new_assets = build_asset_snapshot(export_root, old_assets, hash_contents=hash_asset_updates)
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
        "sourceRoots": asset_source_roots,
        "statePath": str(asset_state_path),
        "available": True,
        "baselineInitialized": asset_baseline_initialized,
        "reported": bool(asset_entries),
        "reportedOnlyWhenGameDataChanges": True,
        "scannedAssets": len(new_assets),
        "sampleLimit": sample_limit,
        "fingerprintMode": ASSET_HASH_FINGERPRINT_MODE if hash_asset_updates else ASSET_DEFAULT_FINGERPRINT_MODE,
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
    return


def run_tracker(
    *,
    game_root: Path,
    state_dir: Path,
    report_json: Path,
    report_md: Path,
    sample_limit: int,
    top_line_limit: int,
    write_history: bool,
    include_relative_paths: list[str],
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
    for rel_path in normalized_relative_paths(include_relative_paths):
        command.extend(["--include-relative-path", rel_path])
    if write_history:
        command.extend(["--history-dir", str(state_dir / "history")])
    else:
        command.append("--no-history")
    subprocess.run(command, cwd=ROOT, check=True)


def prepare_export_diff_tracker_state(
    *,
    previous_export_root: Path,
    state_dir: Path,
    sample_limit: int,
    top_line_limit: int,
    refresh_previous_baseline: bool,
    include_relative_paths: list[str],
) -> tuple[Path, bool]:
    previous_state_dir = export_baseline_state_dir(state_dir)
    compare_state_dir = export_compare_state_dir(state_dir)
    previous_baseline_ready = (
        tracker_has_baseline(previous_state_dir)
        and export_baseline_config_matches(
            state_dir,
            previous_export_root,
            include_relative_paths=include_relative_paths,
        )
    )
    rebuilt_previous_baseline = False

    if refresh_previous_baseline or not previous_baseline_ready:
        if previous_state_dir.exists():
            shutil.rmtree(previous_state_dir)
        run_tracker(
            game_root=previous_export_root,
            state_dir=previous_state_dir,
            report_json=previous_state_dir / "previous-export-baseline-summary.json",
            report_md=previous_state_dir / "previous-export-baseline-summary.md",
            sample_limit=sample_limit,
            top_line_limit=top_line_limit,
            write_history=False,
            include_relative_paths=include_relative_paths,
        )
        write_export_baseline_config(
            state_dir,
            previous_export_root,
            include_relative_paths=include_relative_paths,
        )
        rebuilt_previous_baseline = True

    if compare_state_dir.exists():
        shutil.rmtree(compare_state_dir)
    shutil.copytree(previous_state_dir, compare_state_dir)
    return compare_state_dir, rebuilt_previous_baseline


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    game_root = args.game_root.resolve()
    state_dir = args.state_dir.resolve()
    export_root = args.export_root.resolve()
    previous_export_root = args.previous_export_root.resolve()
    out_path = args.out.resolve()
    report_json = args.report_json.resolve()
    report_md = args.report_md.resolve()

    if args.reset_baseline and state_dir.exists():
        shutil.rmtree(state_dir)

    if not export_root.exists():
        raise SystemExit(f"Current export root does not exist: {export_root}")
    if not export_root.is_dir():
        raise SystemExit(f"Current export root is not a directory: {export_root}")

    previous_baseline_rebuilt = False
    scan_scope = "full_export" if args.full_export_scan else "webui_text_json"
    include_relative_paths = [] if args.full_export_scan else list(WEBUI_TEXT_JSON_RELATIVE_PATHS)
    prune_requested = bool(args.prune_previous_export_untracked or args.dry_run_prune_previous_export_untracked)
    if prune_requested:
        if args.baseline_only:
            raise SystemExit("--prune-previous-export-untracked is not valid with --baseline-only.")
        assert_safe_previous_export_prune(previous_export_root, export_root)
    if args.baseline_only:
        raw_payload = empty_tracker_payload()
    else:
        if not previous_export_root.exists():
            raise SystemExit(
                f"Previous export root does not exist: {previous_export_root}. "
                "Pass --previous-export-root or run with --baseline-only for an empty initial feed."
            )
        if not previous_export_root.is_dir():
            raise SystemExit(f"Previous export root is not a directory: {previous_export_root}")
        compare_state_dir, previous_baseline_rebuilt = prepare_export_diff_tracker_state(
            previous_export_root=previous_export_root,
            state_dir=state_dir,
            sample_limit=args.sample_limit,
            top_line_limit=args.top_line_limit,
            refresh_previous_baseline=bool(args.refresh_previous_export_baseline),
            include_relative_paths=include_relative_paths,
        )
        run_tracker(
            game_root=export_root,
            state_dir=compare_state_dir,
            report_json=report_json,
            report_md=report_md,
            sample_limit=args.sample_limit,
            top_line_limit=args.top_line_limit,
            write_history=bool(not args.no_history),
            include_relative_paths=include_relative_paths,
        )
        raw_payload = json.loads(report_json.read_text(encoding="utf-8"))

    webui_payload = build_update_payload(
        raw_payload,
        game_root=export_root,
        previous_game_root=previous_export_root,
        baseline_initialized=bool(args.baseline_only),
        baseline_only=args.baseline_only,
        sample_limit=args.sample_limit,
        scan_scope=scan_scope,
        include_relative_paths=include_relative_paths,
    )
    attach_asset_updates(
        webui_payload,
        export_root=export_root,
        previous_export_root=previous_export_root,
        state_dir=state_dir,
        sample_limit=args.sample_limit,
        skip_asset_updates=bool(args.skip_asset_updates or args.baseline_only),
        hash_asset_updates=bool(args.hash_asset_updates),
    )

    prune_result: dict[str, Any] | None = None
    if prune_requested:
        prune_result = prune_previous_export_untracked(
            previous_export_root=previous_export_root,
            current_export_root=export_root,
            dry_run=bool(args.dry_run_prune_previous_export_untracked),
        )
        webui_payload["previousExportPrune"] = prune_result

    attach_decoded_impacts(webui_payload, game_root=game_root if game_root.exists() else export_root)
    write_json(out_path, webui_payload, indent=2, compact=False)
    write_update_feed_history(webui_payload, state_dir)

    totals = webui_payload["gameTotals"]
    if webui_payload["baselineInitialized"]:
        print(f"[build_updates] Baseline-only feed from current export {export_root}")
    elif webui_payload.get("baselineOnly"):
        suppressed = (webui_payload.get("tracker") or {}).get("suppressedBaselineOnly") or {}
        print(
            "[build_updates] Baseline-only feed:"
            f" suppressed added={int(suppressed.get('added') or 0)},"
            f" modified={int(suppressed.get('modified') or 0)},"
            f" deleted={int(suppressed.get('deleted') or 0)}"
        )
    else:
        label = "Full export diff" if args.full_export_scan else "WebUI text JSON diff"
        scope_note = "" if args.full_export_scan else f"; scan_roots={len(include_relative_paths)}"
        print(
            f"[build_updates] {label}:"
            f" previous={previous_export_root}, current={export_root};"
            f" added={totals['added']}, modified={totals['modified']}, deleted={totals['deleted']}"
            f"{scope_note}"
        )
    if previous_baseline_rebuilt:
        print(f"[build_updates] Cached previous-export baseline rebuilt from {previous_export_root}")
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
    if prune_result:
        verb = "would delete" if prune_result.get("dryRun") else "deleted"
        print(
            f"[build_updates] Previous export prune: {verb} "
            f"{int(prune_result.get('deletedFiles') or 0)} file(s), "
            f"{int(prune_result.get('bytesDeleted') or 0)} byte(s)"
        )
        unchanged_current = int(prune_result.get("unchangedCurrentFiles") or 0)
        tracked_files = int(prune_result.get("trackedFiles") or 0)
        if unchanged_current:
            print(
                "[build_updates] Previous export byte-identical matches:"
                f" {unchanged_current}/{tracked_files} file(s)"
            )
    print(f"[build_updates] WebUI feed: {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(1)
