#!/usr/bin/env python3
"""Build the WebUI update feed.

This builder compares WebUI-facing exported text JSON and exported assets
between two exported game-data trees, such as ``export_1d2/`` and
``export_full/``, and writes the resulting diff for the WebUI Updates tab. The
previous export is cached as the scanner baseline, then the current export is
scanned against that baseline using the same focused roots.

Run from the repo root:
    python scripts/webui/updates/build_updates.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import time
from collections import Counter
from contextlib import closing
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.updates.build_updates"
    )

from scripts.common import (
    WEBUI_BUILD_DIR,
    EXPORT_ROOT,
    OUT_DIR,
    UPDATES_REPORTS_DIR,
    ROOT,
    display_extension,
    normalize_posix,
    path_id_export_base_stem,
    read_json,
    rel_requires_path_id_export_name,
    write_json,
)
from scripts.webui.assets.index import ASSET_KIND_BY_EXT, VIDEO_EXTENSIONS
from scripts.webui.audio.semantics.identifiers import (
    AUDIO_DUMPER_LANGUAGE_BY_CODE,
    audio_dialog_external_media_id,
)
from scripts.source_paths import ExportLayout, ExportLayoutError, prune_nested_source_dirs, resolve_asset_source_roots
from scripts.webui.updates.scanner import ScanConfig, scan_export_changes
from scripts.webui.updates.characters import build_character_updates, comparison_character_catalog_dir

DEFAULT_STATE_DIR = ROOT / ".game-data-tracker"
DEFAULT_EXPORT_ROOT = EXPORT_ROOT
DEFAULT_PREVIOUS_EXPORT_ROOT = ROOT / "export_full_1d4d1"
DEFAULT_OUT = OUT_DIR / "updates" / "latest.json"
DEFAULT_CHARACTERS_OUT = OUT_DIR / "updates" / "characters.json"
DEFAULT_REPORT_JSON = UPDATES_REPORTS_DIR / "game-data-change-summary.json"
DEFAULT_REPORT_MD = UPDATES_REPORTS_DIR / "game-data-change-summary.md"
SCHEMA_VERSION = 1
# v2: asset keys use layout-v2 source labels (Unity/, Game/, Audio/). A state
# cached under v1 labels (StreamingAssets/, Persistent-structured/) must not be
# reused, or every old asset appears deleted.
ASSET_STATE_SCHEMA_VERSION = 2
EXPORT_BASELINE_CONFIG_SCHEMA_VERSION = 3
STATUS_ORDER = {"added": 0, "modified": 1, "deleted": 2}
ASSET_HASH_CHUNK_SIZE = 1024 * 1024
ASSET_DEFAULT_FINGERPRINT_MODE = "size"
ASSET_HASH_FINGERPRINT_MODE = "content_hash"
AUDIO_EXTENSIONS = {
    ".flac",
    ".wav",
    ".wem",
}
AUDIO_EXPORT_RELATIVE_ROOT = "game/Audio"
AUDIO_SOURCE_LABEL = "Audio"
PRUNE_SAMPLE_LIMIT = 200
IGNORED_GAME_PATH_PREFIXES = (
    # CrashSight writes local crash/telemetry state under the game install.
    # These files churn between runs but are not installed content updates.
    "plugins/x86_64/wesight/crashsight_data/",
)
# Layout v2: only game/ is game data. meta/ (indexes, asset maps, provenance)
# and the layout marker describe an export, so they never appear as updates.
EXPORT_METADATA_RELATIVE_PATHS = ("meta", "layout.json")
WEBUI_TEXT_JSON_RELATIVE_PATHS = (
    "game/Table",
    "game/Json/MissionRuntimeAsset",
    "game/Json/LevelData",
    "game/Json/LevelScriptData",
    "game/Json/LevelScriptTemplateData",
    "game/Json/GameplayConfig/DialogIdTable.json",
    "game/Json/GameplayConfig/MissionAreaTable.json",
    "game/Json/GameplayConfig/NpcProxyTable.json",
    "game/Json/GameplayConfig/NpcProxyExDataTable.json",
    "game/Json/GameplayConfig/AtmosphericNpcClusterDataTable.json",
)

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build webui/data/updates/latest.json from focused exported text "
            "JSON and media asset diffs."
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
        "--characters-out",
        type=Path,
        default=DEFAULT_CHARACTERS_OUT,
        help="Characters-page added/modified/deleted sidecar JSON path.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=DEFAULT_REPORT_JSON,
        help="Raw scanner JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        default=DEFAULT_REPORT_MD,
        help="Raw scanner Markdown report path.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5000,
        help="Maximum entries per status to carry from the scanner.",
    )
    parser.add_argument(
        "--top-line-limit",
        type=int,
        default=50,
        help="Maximum line-delta entries to preserve in the raw scanner report.",
    )
    parser.add_argument(
        "--reset-baseline",
        action="store_true",
        help="Delete cached update-diff state before rebuilding the previous-export baseline.",
    )
    parser.add_argument(
        "--text-only",
        dest="skip_asset_updates",
        action="store_true",
        help=(
            "Skip the exported image/model/video/audio asset diff. By default "
            "Updates tracks media assets plus WebUI-facing text JSON."
        ),
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
        "--exact",
        dest="hash_asset_updates",
        action="store_true",
        help=(
            "Hash exported asset contents when comparing assets. Slower, but "
            "detects same-size binary modifications."
        ),
    )
    parser.add_argument(
        "--no-audio",
        dest="skip_audio_updates",
        action="store_true",
        help=(
            "Skip decoded audio assets in the exported asset diff while still "
            "comparing images, models, and videos."
        ),
    )
    parser.set_defaults(skip_audio_updates=False)
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
        "--no-history",
        action="store_true",
        help="Do not write timestamped raw scanner history for this comparison.",
    )
    return parser.parse_args(argv)


def scanner_has_baseline(state_dir: Path) -> bool:
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
    if parts[:1] == ["game"]:
        if len(parts) > 2 and parts[1] == "unity":
            return f"unity_{parts[2]}"
        return f"game_{parts[1]}" if len(parts) > 1 else "game"
    if parts[:1] == ["meta"]:
        return "export_metadata"
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
    return any(lower.startswith(prefix) for prefix in IGNORED_GAME_PATH_PREFIXES) or is_ignored_export_metadata_path(lower)


def is_ignored_export_metadata_path(path: str) -> bool:
    """Exclude export metadata (meta/, layout.json); game/ is the only game data."""
    normalized = normalize_posix(path).lower().lstrip("/")
    return any(
        normalized == prefix or normalized.startswith(prefix + "/")
        for prefix in EXPORT_METADATA_RELATIVE_PATHS
    )


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
        "old_digest",
        "new_digest",
    ):
        if raw.get(key) is not None:
            entry[key] = raw[key]
    if raw.get("text_diff"):
        entry["text_diff"] = raw["text_diff"]
        if raw.get("text_diff_truncated"):
            entry["text_diff_truncated"] = True
    return entry


def filtered_game_entries(
    samples: dict[str, Any],
    *,
    suppress_changes: bool,
    game_root: Path,
    previous_game_root: Path | None,
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


def resolve_update_asset_source_roots(
    export_root: Path,
    *,
    include_audio: bool = True,
) -> list[tuple[str, Path]]:
    roots = list(resolve_asset_source_roots(export_root))
    audio_root = export_root / AUDIO_EXPORT_RELATIVE_ROOT
    if include_audio and audio_root.exists():
        roots.append((AUDIO_SOURCE_LABEL, audio_root))
    return roots


def asset_is_audio(asset: dict[str, Any]) -> bool:
    if str(asset.get("kind") or "") == "audio":
        return True
    if str(asset.get("source") or "") == AUDIO_SOURCE_LABEL:
        return True
    return str(asset.get("path") or "").startswith(f"{AUDIO_SOURCE_LABEL}/")


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
    include_audio: bool = True,
) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    prior_assets = prior_assets or {}
    if not export_root.exists():
        return assets

    for source, source_root in resolve_update_asset_source_roots(export_root, include_audio=include_audio):
        if not source_root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(source_root):
            prune_nested_source_dirs(source, source_root, dirpath, dirnames)
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
            if not include_audio and asset_is_audio(old_asset):
                continue
            preserved = dict(old_asset)
            preserved["missing_on_disk"] = True
            assets[rel_path] = preserved
    return assets


def asset_source_roots_payload(export_root: Path, *, include_audio: bool = True) -> dict[str, str]:
    roots: dict[str, str] = {}
    for source, source_root in resolve_update_asset_source_roots(export_root, include_audio=include_audio):
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
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not is_ignored_game_update_path(
                (base_dir / dirname).relative_to(root).as_posix()
            )
        ]
        for filename in filenames:
            path = base_dir / filename
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                if not is_ignored_game_update_path(relative):
                    out.append(relative)
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
    try:
        ExportLayout(previous_resolved).require()
    except ExportLayoutError as exc:
        raise SystemExit(f"--prune-previous-export-untracked needs a complete v2 export root: {exc}") from exc


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


def asset_content_digest(asset: dict[str, Any] | None) -> str:
    if not isinstance(asset, dict):
        return ""
    if str(asset.get("fingerprintMode") or "") != ASSET_HASH_FINGERPRINT_MODE:
        return ""
    digest = str(asset.get("digest") or "")
    return "" if not digest or digest.startswith("size:") else digest

def asset_update_entry(
    status: str,
    asset: dict[str, Any],
    old_asset: dict[str, Any] | None = None,
    *,
    relocation_match: str = "",
) -> dict[str, Any]:
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
    old_digest = asset_content_digest(old_asset if status != "added" else None)
    new_digest = asset_content_digest(asset if status != "deleted" else None)
    if old_digest:
        entry["old_digest"] = old_digest
    if new_digest:
        entry["new_digest"] = new_digest
    if relocation_match:
        entry["change_kind"] = "relocated"
        entry["relocation_match"] = relocation_match
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


def path_id_relocation_identity(asset: dict[str, Any]) -> str:
    rel_path = normalize_posix(str(asset.get("path") or ""))
    if not rel_path or not rel_requires_path_id_export_name(rel_path):
        return ""
    path = PurePosixPath(rel_path)
    base_stem = path_id_export_base_stem(path.stem)
    if not base_stem:
        return ""
    stable_path = str(path.with_name(f"{base_stem}{path.suffix.lower()}"))
    return "|".join((
        str(asset.get("kind") or ""),
        str(asset.get("extension") or "").lower(),
        stable_path.casefold(),
    ))


def unique_path_id_relocations(
    old_assets: dict[str, dict[str, Any]],
    new_assets: dict[str, dict[str, Any]],
    deleted_paths: set[str],
    added_paths: set[str],
) -> dict[str, tuple[str, str]]:
    old_by_identity: dict[str, list[str]] = {}
    new_by_identity: dict[str, list[str]] = {}
    for rel_path in deleted_paths:
        identity = path_id_relocation_identity(old_assets[rel_path])
        if identity:
            old_by_identity.setdefault(identity, []).append(rel_path)
    for rel_path in added_paths:
        identity = path_id_relocation_identity(new_assets[rel_path])
        if identity:
            new_by_identity.setdefault(identity, []).append(rel_path)

    matches: dict[str, tuple[str, str]] = {}
    for identity in sorted(set(old_by_identity) & set(new_by_identity)):
        old_paths = old_by_identity[identity]
        new_paths = new_by_identity[identity]
        if len(old_paths) == len(new_paths) == 1:
            matches[new_paths[0]] = (old_paths[0], "unity_path_id")
    return matches


def asset_file_path(export_root: Path, asset: dict[str, Any]) -> Path | None:
    export_rel = normalize_posix(str(asset.get("export_rel") or ""))
    if not export_rel:
        return None
    root = export_root.resolve()
    path = (root / export_rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.is_file() else None


def flac_pcm_identity(path: Path) -> tuple[int, int, int, int, str] | None:
    """Return the lossless decoded-audio identity stored by FLAC STREAMINFO."""
    try:
        with path.open("rb") as stream:
            if stream.read(4) != b"fLaC":
                return None
            header = stream.read(4)
            if len(header) != 4 or (header[0] & 0x7F) != 0:
                return None
            block_size = int.from_bytes(header[1:4], "big")
            if block_size != 34:
                return None
            streaminfo = stream.read(block_size)
    except OSError:
        return None
    if len(streaminfo) != 34:
        return None
    packed = int.from_bytes(streaminfo[10:18], "big")
    sample_rate = packed >> 44
    channels = ((packed >> 41) & 0x07) + 1
    bits_per_sample = ((packed >> 36) & 0x1F) + 1
    total_samples = packed & ((1 << 36) - 1)
    pcm_md5 = streaminfo[18:34].hex()
    if sample_rate <= 0 or total_samples <= 0 or pcm_md5 == "0" * 32:
        return None
    return sample_rate, channels, bits_per_sample, total_samples, pcm_md5


def add_unambiguous_audio_identity_matches(
    matches: dict[str, tuple[str, str]],
    old_by_identity: dict[Any, list[str]],
    new_by_identity: dict[Any, list[str]],
    *,
    name_method: str,
    parent_method: str,
    unique_method: str,
) -> None:
    """Pair identity buckets without guessing among duplicate audio files."""
    for identity in sorted(set(old_by_identity) & set(new_by_identity), key=str):
        old_paths = old_by_identity[identity]
        new_paths = new_by_identity[identity]
        old_by_name: dict[str, list[str]] = {}
        new_by_name: dict[str, list[str]] = {}
        for rel_path in old_paths:
            old_by_name.setdefault(PurePosixPath(rel_path).name.casefold(), []).append(rel_path)
        for rel_path in new_paths:
            new_by_name.setdefault(PurePosixPath(rel_path).name.casefold(), []).append(rel_path)
        paired_old: set[str] = set()
        paired_new: set[str] = set()
        for name in sorted(set(old_by_name) & set(new_by_name)):
            if len(old_by_name[name]) == len(new_by_name[name]) == 1:
                old_path = old_by_name[name][0]
                new_path = new_by_name[name][0]
                matches[new_path] = (old_path, name_method)
                paired_old.add(old_path)
                paired_new.add(new_path)

        # Numeric Wwise media ids can change while the same decoded file is
        # exported into parallel category/unknown folders. The unchanged
        # parent folder resolves those duplicate-content buckets without
        # crossing categories or pairing multiple candidates in one folder.
        remaining_old = [path for path in old_paths if path not in paired_old]
        remaining_new = [path for path in new_paths if path not in paired_new]
        old_by_parent: dict[str, list[str]] = {}
        new_by_parent: dict[str, list[str]] = {}
        for rel_path in remaining_old:
            old_by_parent.setdefault(str(PurePosixPath(rel_path).parent).casefold(), []).append(rel_path)
        for rel_path in remaining_new:
            new_by_parent.setdefault(str(PurePosixPath(rel_path).parent).casefold(), []).append(rel_path)
        for parent in sorted(set(old_by_parent) & set(new_by_parent)):
            if len(old_by_parent[parent]) == len(new_by_parent[parent]) == 1:
                old_path = old_by_parent[parent][0]
                new_path = new_by_parent[parent][0]
                matches[new_path] = (old_path, parent_method)
                paired_old.add(old_path)
                paired_new.add(new_path)

        remaining_old = [path for path in old_paths if path not in paired_old]
        remaining_new = [path for path in new_paths if path not in paired_new]
        if len(remaining_old) == len(remaining_new) == 1:
            matches[remaining_new[0]] = (remaining_old[0], unique_method)


def exact_audio_relocations(
    old_assets: dict[str, dict[str, Any]],
    new_assets: dict[str, dict[str, Any]],
    deleted_paths: set[str],
    added_paths: set[str],
    *,
    previous_export_root: Path,
    current_export_root: Path,
) -> dict[str, tuple[str, str]]:
    old_by_shape: dict[tuple[str, int], list[str]] = {}
    new_by_shape: dict[tuple[str, int], list[str]] = {}
    for rel_path in deleted_paths:
        asset = old_assets[rel_path]
        if not asset_is_audio(asset) or asset.get("size") is None:
            continue
        key = (str(asset.get("extension") or "").lower(), int(asset["size"]))
        old_by_shape.setdefault(key, []).append(rel_path)
    for rel_path in added_paths:
        asset = new_assets[rel_path]
        if not asset_is_audio(asset) or asset.get("size") is None:
            continue
        key = (str(asset.get("extension") or "").lower(), int(asset["size"]))
        new_by_shape.setdefault(key, []).append(rel_path)

    digest_cache: dict[tuple[str, str], str] = {}

    def relocation_digest(side: str, rel_path: str) -> str:
        cache_key = (side, rel_path)
        if cache_key in digest_cache:
            return digest_cache[cache_key]
        asset = old_assets[rel_path] if side == "old" else new_assets[rel_path]
        root = previous_export_root if side == "old" else current_export_root
        path = asset_file_path(root, asset)
        try:
            digest = hash_file(path) if path is not None else ""
        except OSError:
            digest = ""
        digest_cache[cache_key] = digest
        return digest

    matches: dict[str, tuple[str, str]] = {}
    for shape in sorted(set(old_by_shape) & set(new_by_shape)):
        old_by_digest: dict[str, list[str]] = {}
        new_by_digest: dict[str, list[str]] = {}
        for rel_path in old_by_shape[shape]:
            digest = relocation_digest("old", rel_path)
            if digest:
                old_by_digest.setdefault(digest, []).append(rel_path)
        for rel_path in new_by_shape[shape]:
            digest = relocation_digest("new", rel_path)
            if digest:
                new_by_digest.setdefault(digest, []).append(rel_path)
        for digest in sorted(set(old_by_digest) & set(new_by_digest)):
            add_unambiguous_audio_identity_matches(
                matches,
                {digest: old_by_digest[digest]},
                {digest: new_by_digest[digest]},
                name_method="exact_content_and_name",
                parent_method="exact_content_and_parent",
                unique_method="unique_exact_content",
            )

    # Container metadata and encoder settings can change while the lossless
    # decoded signal stays identical. FLAC's STREAMINFO MD5 is defined over the
    # decoded PCM, so it is a stronger relocation identity than duration or a
    # fuzzy waveform comparison and does not require an external decoder.
    paired_new = set(matches)
    paired_old = {old_path for old_path, _method in matches.values()}
    old_by_pcm: dict[tuple[int, int, int, int, str], list[str]] = {}
    new_by_pcm: dict[tuple[int, int, int, int, str], list[str]] = {}
    for side, paths, assets, root, grouped in (
        ("old", deleted_paths - paired_old, old_assets, previous_export_root, old_by_pcm),
        ("new", added_paths - paired_new, new_assets, current_export_root, new_by_pcm),
    ):
        for rel_path in paths:
            asset = assets[rel_path]
            if str(asset.get("extension") or "").lower() != ".flac":
                continue
            path = asset_file_path(root, asset)
            identity = flac_pcm_identity(path) if path is not None else None
            if identity is not None:
                grouped.setdefault(identity, []).append(rel_path)
    add_unambiguous_audio_identity_matches(
        matches,
        old_by_pcm,
        new_by_pcm,
        name_method="flac_pcm_and_name",
        parent_method="flac_pcm_and_parent",
        unique_method="unique_flac_pcm",
    )
    return matches


def audio_dialog_paths_by_external_id(export_root: Path) -> dict[tuple[str, int], list[str]]:
    table_path = ExportLayout(export_root).table_dir / "AudioDialog.json"
    payload = read_json(table_path, {})
    if not isinstance(payload, dict):
        return {}
    paths_by_id: dict[tuple[str, int], list[str]] = {}
    for row in payload.values():
        if not isinstance(row, dict):
            continue
        dialog_path = normalize_posix(str(row.get("path") or "")).strip()
        if not dialog_path:
            continue
        for language, dumper_language in AUDIO_DUMPER_LANGUAGE_BY_CODE.items():
            external_id = audio_dialog_external_media_id(dialog_path, dumper_language)
            paths_by_id.setdefault((language, external_id), []).append(dialog_path)
    return paths_by_id


def numeric_unknown_audio_identity(asset: dict[str, Any]) -> tuple[str, int] | None:
    rel_path = PurePosixPath(normalize_posix(str(asset.get("path") or "")))
    parts = rel_path.parts
    if (
        len(parts) != 5
        or parts[0].casefold() != "audio"
        or parts[2].casefold() != "wwise"
        or parts[3].casefold() != "unknown"
        or not rel_path.stem.isdigit()
    ):
        return None
    media_id = int(rel_path.stem)
    if media_id <= 0xFFFFFFFF:
        return None
    language = parts[1].upper()
    if language not in AUDIO_DUMPER_LANGUAGE_BY_CODE:
        return None
    return language, media_id


def authored_voice_candidates(
    assets: dict[str, dict[str, Any]],
) -> dict[tuple[str, str, str], list[str]]:
    candidates: dict[tuple[str, str, str], list[str]] = {}
    for rel_path, asset in assets.items():
        if not asset_is_audio(asset):
            continue
        parts = PurePosixPath(rel_path).parts
        if len(parts) < 4 or parts[0].casefold() != "audio" or parts[2].casefold() != "voice":
            continue
        key = (
            parts[1].upper(),
            PurePosixPath(rel_path).stem.casefold(),
            str(asset.get("extension") or "").lower(),
        )
        candidates.setdefault(key, []).append(rel_path)
    return candidates


def redundant_audio_dialog_copies(
    old_assets: dict[str, dict[str, Any]],
    new_assets: dict[str, dict[str, Any]],
    deleted_paths: set[str],
    added_paths: set[str],
    *,
    previous_export_root: Path,
    current_export_root: Path,
) -> tuple[set[str], set[str]]:
    """Find obsolete numeric copies when the authored voice file survives.

    A numeric AKPK external-source id is joined to a current AudioDialog path
    only by its exact 64-bit path hash. The authored basename must resolve to
    one voice asset, and the numeric/canonical files must be byte-identical.
    Same-name ambiguity therefore remains visible instead of being guessed.
    """

    dialog_paths = audio_dialog_paths_by_external_id(current_export_root)
    old_voice = authored_voice_candidates(old_assets)
    new_voice = authored_voice_candidates(new_assets)

    def exact_match(
        source_root: Path,
        source_asset: dict[str, Any],
        target_root: Path,
        target_asset: dict[str, Any],
    ) -> bool:
        if source_asset.get("size") != target_asset.get("size"):
            return False
        source_path = asset_file_path(source_root, source_asset)
        target_path = asset_file_path(target_root, target_asset)
        if source_path is None or target_path is None:
            return False
        try:
            return hash_file(source_path) == hash_file(target_path)
        except OSError:
            return False

    ignored_deleted: set[str] = set()
    for rel_path in deleted_paths:
        asset = old_assets[rel_path]
        identity = numeric_unknown_audio_identity(asset)
        if identity is None:
            continue
        dialog_candidates = dialog_paths.get(identity, [])
        if len(dialog_candidates) != 1:
            continue
        key = (
            identity[0],
            PurePosixPath(dialog_candidates[0]).stem.casefold(),
            str(asset.get("extension") or "").lower(),
        )
        canonical_paths = new_voice.get(key, [])
        if len(canonical_paths) != 1 or canonical_paths[0] not in old_assets:
            continue
        canonical_path = canonical_paths[0]
        if exact_match(previous_export_root, asset, current_export_root, new_assets[canonical_path]):
            ignored_deleted.add(rel_path)

    ignored_added: set[str] = set()
    for rel_path in added_paths:
        asset = new_assets[rel_path]
        identity = numeric_unknown_audio_identity(asset)
        if identity is None:
            continue
        dialog_candidates = dialog_paths.get(identity, [])
        if len(dialog_candidates) != 1:
            continue
        key = (
            identity[0],
            PurePosixPath(dialog_candidates[0]).stem.casefold(),
            str(asset.get("extension") or "").lower(),
        )
        canonical_paths = old_voice.get(key, [])
        if len(canonical_paths) != 1 or canonical_paths[0] not in new_assets:
            continue
        canonical_path = canonical_paths[0]
        if exact_match(current_export_root, asset, previous_export_root, old_assets[canonical_path]):
            ignored_added.add(rel_path)
    return ignored_deleted, ignored_added


def build_asset_diff(
    old_assets: dict[str, dict[str, Any]],
    new_assets: dict[str, dict[str, Any]],
    *,
    sample_limit: int,
    previous_export_root: Path | None = None,
    current_export_root: Path | None = None,
) -> dict[str, Any]:
    added: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []

    old_paths = set(old_assets)
    new_paths = set(new_assets)
    added_paths = new_paths - old_paths
    deleted_paths = old_paths - new_paths
    ignored_deleted_paths: set[str] = set()
    ignored_added_paths: set[str] = set()
    if previous_export_root is not None and current_export_root is not None:
        ignored_deleted_paths, ignored_added_paths = redundant_audio_dialog_copies(
            old_assets,
            new_assets,
            deleted_paths,
            added_paths,
            previous_export_root=previous_export_root,
            current_export_root=current_export_root,
        )
    effective_added_paths = added_paths - ignored_added_paths
    effective_deleted_paths = deleted_paths - ignored_deleted_paths
    relocation_matches = unique_path_id_relocations(
        old_assets,
        new_assets,
        effective_deleted_paths,
        effective_added_paths,
    )
    ignored_path_only_relocations: dict[str, tuple[str, str]] = {}
    if previous_export_root is not None and current_export_root is not None:
        path_id_matches = relocation_matches
        relocation_matches = {}
        for new_path, (old_path, match_method) in path_id_matches.items():
            old_file = asset_file_path(previous_export_root, old_assets[old_path])
            new_file = asset_file_path(current_export_root, new_assets[new_path])
            if (
                old_file is not None
                and new_file is not None
                and files_match_for_prune(old_file, new_file)
            ):
                ignored_path_only_relocations[new_path] = (old_path, match_method)
            else:
                relocation_matches[new_path] = (old_path, match_method)

        path_id_added = set(path_id_matches)
        path_id_deleted = {old_path for old_path, _method in path_id_matches.values()}
        ignored_path_only_relocations.update(exact_audio_relocations(
            old_assets,
            new_assets,
            effective_deleted_paths - path_id_deleted,
            effective_added_paths - path_id_added,
            previous_export_root=previous_export_root,
            current_export_root=current_export_root,
        ))
    ignored_relocation_added_paths = set(ignored_path_only_relocations)
    ignored_relocation_deleted_paths = {
        old_path for old_path, _method in ignored_path_only_relocations.values()
    }
    relocated_added_paths = set(relocation_matches)
    relocated_deleted_paths = {
        old_path for old_path, _method in relocation_matches.values()
    }

    for rel_path in sorted(
        effective_added_paths - relocated_added_paths - ignored_relocation_added_paths
    ):
        added.append(asset_update_entry("added", new_assets[rel_path]))
    for rel_path in sorted(
        effective_deleted_paths - relocated_deleted_paths - ignored_relocation_deleted_paths
    ):
        old_asset = old_assets[rel_path]
        deleted.append(asset_update_entry("deleted", old_asset, old_asset))
    for new_path in sorted(relocation_matches):
        old_path, match_method = relocation_matches[new_path]
        modified.append(asset_update_entry(
            "modified",
            new_assets[new_path],
            old_assets[old_path],
            relocation_match=match_method,
        ))
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

    published_entries: list[dict[str, Any]] = []
    truncated: dict[str, int] = {}
    for status, entries in (("added", added), ("modified", modified), ("deleted", deleted)):
        status_entries = entries if sample_limit == 0 else entries[:sample_limit]
        published_entries.extend(status_entries)
        truncated[status] = len(entries) - len(status_entries)

    kinds = Counter(str(entry.get("asset_kind") or "asset") for entry in published_entries)
    extensions = Counter(display_extension(str(entry.get("extension") or "")) for entry in published_entries)
    return {
        "totals": totals,
        "entries": published_entries,
        "truncated": truncated,
        "breakdown": {
            "byKind": dict(kinds.most_common()),
            "byExtension": dict(extensions.most_common()),
        },
        "ignoredStructuredSourceRelocations": {
            "added": 0,
            "deleted": 0,
        },
        "recognizedRelocations": {
            "total": len(relocation_matches),
            "byMethod": dict(Counter(
                method for _old_path, method in relocation_matches.values()
            ).most_common()),
        },
        "ignoredPathOnlyRelocations": {
            "total": len(ignored_path_only_relocations),
            "byMethod": dict(Counter(
                method for _old_path, method in ignored_path_only_relocations.values()
            ).most_common()),
        },
        "ignoredRedundantAudioCopies": {
            "total": len(ignored_deleted_paths) + len(ignored_added_paths),
            "added": len(ignored_added_paths),
            "deleted": len(ignored_deleted_paths),
            "matchMethod": "exactAudioDialogExternalPathHashAndContent",
        },
    }


def zero_totals() -> dict[str, int]:
    return {"added": 0, "modified": 0, "deleted": 0, "changed": 0}


def total_reported_changes(payload: dict[str, Any]) -> int:
    totals = payload.get("totals") or payload.get("gameTotals") or {}
    return int(totals.get("changed") or 0)


def write_update_feed_history(payload: dict[str, Any], state_dir: Path) -> Path | None:
    if total_reported_changes(payload) <= 0:
        return None
    history_dir = state_dir / "history"
    stamp = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    history_path = history_dir / f"update-feed-{stamp}.json"
    write_json(history_path, payload, indent=2, compact=False)
    return history_path


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
    sample_limit: int,
    scan_scope: str,
    include_relative_paths: list[str],
) -> dict[str, Any]:
    changes = raw_payload.get("changes") or {}
    samples = raw_payload.get("samples") or {}
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    suppress_changes = baseline_initialized

    entry_domain = "text" if scan_scope == "webui_text_json" else "game"
    entries, ignored_counts = filtered_game_entries(
        samples,
        suppress_changes=suppress_changes,
        game_root=game_root,
        previous_game_root=previous_game_root,
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
        "generatedBy": "scripts/webui/updates/build_updates.py",
        "source": source,
        "sourceRoot": str(game_root),
        "baselineInitialized": baseline_initialized,
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
    skip_audio_updates: bool = False,
) -> None:
    include_audio_updates = not skip_audio_updates
    asset_state_path = state_dir / "asset-state.json"
    old_assets = load_asset_state(asset_state_path, export_root=export_root)
    asset_scan_available = export_root.exists()
    asset_source_roots = asset_source_roots_payload(export_root, include_audio=include_audio_updates)
    previous_asset_source_roots = (
        asset_source_roots_payload(previous_export_root, include_audio=include_audio_updates)
        if previous_export_root is not None
        else {}
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
            include_audio=include_audio_updates,
        )
        new_assets = build_asset_snapshot(
            export_root,
            load_asset_state(current_asset_state_path, export_root=export_root),
            hash_contents=hash_asset_updates,
            include_audio=include_audio_updates,
        )
        diff = build_asset_diff(
            old_assets,
            new_assets,
            sample_limit=sample_limit,
            previous_export_root=previous_export_root,
            current_export_root=export_root,
        )
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
            "ignoredStructuredSourceRelocations": diff["ignoredStructuredSourceRelocations"],
            "recognizedRelocations": diff["recognizedRelocations"],
            "ignoredPathOnlyRelocations": diff["ignoredPathOnlyRelocations"],
            "ignoredRedundantAudioCopies": diff["ignoredRedundantAudioCopies"],
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

    new_assets = build_asset_snapshot(
        export_root,
        old_assets,
        hash_contents=hash_asset_updates,
        include_audio=include_audio_updates,
    )
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
        "recognizedRelocations": (
            diff.get("recognizedRelocations")
            if old_assets and game_changed and not game_baseline_initialized
            else {"total": 0, "byMethod": {}}
        ),
        "ignoredPathOnlyRelocations": (
            diff.get("ignoredPathOnlyRelocations")
            if old_assets and game_changed and not game_baseline_initialized
            else {"total": 0, "byMethod": {}}
        ),
        "ignoredRedundantAudioCopies": (
            diff.get("ignoredRedundantAudioCopies")
            if old_assets and game_changed and not game_baseline_initialized
            else {
                "total": 0,
                "added": 0,
                "deleted": 0,
                "matchMethod": "exactAudioDialogExternalPathHashAndContent",
            }
        ),
    }
    payload.setdefault("entries", []).extend(asset_entries)
    payload["entries"].sort(key=lambda entry: (
        0 if str(entry.get("domain") or "game") != "asset" else 1,
        STATUS_ORDER.get(str(entry.get("status")), 99),
        str(entry.get("path", "")).lower(),
    ))
    return


def scan_export_tree(
    *,
    export_root: Path,
    state_dir: Path,
    report_json: Path,
    report_md: Path,
    sample_limit: int,
    top_line_limit: int,
    write_history: bool,
    include_relative_paths: list[str],
) -> dict[str, object]:
    result = scan_export_changes(
        ScanConfig(
            root=export_root,
            state_dir=state_dir,
            summary_json=report_json,
            summary_md=report_md,
            history_dir=state_dir / "history" if write_history else None,
            sample_limit=sample_limit,
            top_line_limit=top_line_limit,
            ignore_relative_paths=EXPORT_METADATA_RELATIVE_PATHS,
            include_relative_paths=tuple(normalized_relative_paths(include_relative_paths)),
        )
    )
    return result.payload


def prepare_export_diff_scanner_state(
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
        scanner_has_baseline(previous_state_dir)
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
        scan_export_tree(
            export_root=previous_export_root,
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
    state_dir = args.state_dir.resolve()
    export_root = args.export_root.resolve()
    previous_export_root = args.previous_export_root.resolve()
    out_path = args.out.resolve()
    characters_out_path = args.characters_out.resolve()
    report_json = args.report_json.resolve()
    report_md = args.report_md.resolve()

    if args.reset_baseline and state_dir.exists():
        shutil.rmtree(state_dir)

    for label, root in (("current", export_root), ("previous", previous_export_root)):
        try:
            ExportLayout(root).require()
        except ExportLayoutError as exc:
            raise SystemExit(f"{label} export root: {exc}") from exc
    if not export_root.exists():
        raise SystemExit(f"Current export root does not exist: {export_root}")
    if not export_root.is_dir():
        raise SystemExit(f"Current export root is not a directory: {export_root}")

    previous_baseline_rebuilt = False
    scan_scope = "full_export" if args.full_export_scan else "webui_text_json"
    include_relative_paths = [] if args.full_export_scan else list(WEBUI_TEXT_JSON_RELATIVE_PATHS)
    prune_requested = bool(args.prune_previous_export_untracked or args.dry_run_prune_previous_export_untracked)
    if prune_requested:
        assert_safe_previous_export_prune(previous_export_root, export_root)
    if not previous_export_root.exists():
        raise SystemExit(f"Previous export root does not exist: {previous_export_root}.")
    if not previous_export_root.is_dir():
        raise SystemExit(f"Previous export root is not a directory: {previous_export_root}")
    compare_state_dir, previous_baseline_rebuilt = prepare_export_diff_scanner_state(
        previous_export_root=previous_export_root,
        state_dir=state_dir,
        sample_limit=args.sample_limit,
        top_line_limit=args.top_line_limit,
        refresh_previous_baseline=bool(args.refresh_previous_export_baseline),
        include_relative_paths=include_relative_paths,
    )
    raw_payload = scan_export_tree(
        export_root=export_root,
        state_dir=compare_state_dir,
        report_json=report_json,
        report_md=report_md,
        sample_limit=args.sample_limit,
        top_line_limit=args.top_line_limit,
        write_history=bool(not args.no_history),
        include_relative_paths=include_relative_paths,
    )

    webui_payload = build_update_payload(
        raw_payload,
        game_root=export_root,
        previous_game_root=previous_export_root,
        baseline_initialized=False,
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
        skip_asset_updates=bool(args.skip_asset_updates),
        hash_asset_updates=bool(args.hash_asset_updates),
        skip_audio_updates=bool(args.skip_audio_updates),
    )
    character_updates = build_character_updates(
        comparison_character_catalog_dir(previous_export_root, state_dir),
        comparison_character_catalog_dir(export_root, state_dir),
        previous_source_root=previous_export_root,
        source_root=export_root,
    )

    prune_result: dict[str, Any] | None = None
    if prune_requested:
        prune_result = prune_previous_export_untracked(
            previous_export_root=previous_export_root,
            current_export_root=export_root,
            dry_run=bool(args.dry_run_prune_previous_export_untracked),
        )
        webui_payload["previousExportPrune"] = prune_result

    write_json(out_path, webui_payload, indent=2, compact=False)
    write_json(characters_out_path, character_updates, indent=2, compact=False)
    write_update_feed_history(webui_payload, state_dir)

    totals = webui_payload["gameTotals"]
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
        print("[build_updates] Asset changes: skipped (--text-only)")
    else:
        if args.skip_audio_updates:
            print("[build_updates] Audio asset changes: skipped (--no-audio)")
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
    character_totals = character_updates["totals"]
    if character_updates.get("available"):
        print(
            "[build_updates] Character changes:"
            f" added={character_totals['added']},"
            f" modified={character_totals['modified']},"
            f" deleted={character_totals['deleted']}"
        )
    else:
        print(f"[build_updates] Character changes: skipped ({character_updates.get('skipReason')})")
    print(f"[build_updates] Character change sidecar: {characters_out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(1)
