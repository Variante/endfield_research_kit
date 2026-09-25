#!/usr/bin/env python3
"""Verify that the WebUI export matches the installed Endfield data.

This is a cheap guard for direct builder runs and for future game updates: the
WebUI reads ``export_full/``, while the source of truth is the installed
``Endfield_Data`` tree. If those fingerprints drift, rerun ``export.bat``
before rebuilding story/assets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.game_data.extraction.verify_export_freshness"
    )

from scripts.common import ROOT, native_evidence_required, read_json, rel_path as slash
from scripts.source_paths import PACKED_GAME_DIRS, ExportLayout, ExportLayoutError, packed_game_dir
from scripts.game_data.game_file_store import open_game_files_if_present
from scripts.game_data.unity_store import open_store_if_present
from scripts.game_data.extraction.export_full_from_game import (
    DEFAULT_GAME_ROOT,
    DEFAULT_OUTPUT,
    DEFAULT_REPORTS,
    SOURCES,
    animestudio_stage_dir,
    collect_source_sizes,
)


DEFAULT_SUMMARY = DEFAULT_REPORTS / "export_full_summary.json"
# Published game data every WebUI build needs, and the per-layer metadata
# that proves it. Unity types are single-tree (their object documents are
# rows of game/Unity.sqlite, their media loose files); a game/ folder that holds
# a packed folder (game/Json holds Json/LipSync) is counted as its loose files
# plus its rows of game/GameFiles.sqlite; asset maps stay per layer.
REQUIRED_GAME_DIRS = ("Table", "Json")
REQUIRED_UNITY_TYPES = ("TextAsset", "MonoBehaviour")


def ordered_unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def source_fingerprint_drift(source: str, current: dict[str, Any], exported: dict[str, Any]) -> dict[str, Any]:
    fields = ("fingerprint", "files", "bytes", "latest_mtime_ns")
    drift = {
        field: {
            "current": current.get(field),
            "exported": exported.get(field),
        }
        for field in fields
        if current.get(field) != exported.get(field)
    }
    return {
        "source": source,
        "fresh": not drift,
        "current": current,
        "exported": exported,
        "drift": drift,
    }


def _skipped(path: str, skip_dirs: frozenset[str]) -> bool:
    return os.path.normcase(os.path.abspath(path)) in skip_dirs


def directory_has_file(path: Path, skip_dirs: frozenset[str] = frozenset()) -> bool:
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_file():
                            return True
                        if entry.is_dir() and not _skipped(entry.path, skip_dirs):
                            pending.append(Path(entry.path))
                    except OSError:
                        continue
        except OSError:
            continue
    return False


def count_files(path: Path, skip_dirs: frozenset[str] = frozenset()) -> int:
    count = 0
    for dirpath, dirnames, filenames in os.walk(path):
        if skip_dirs:
            dirnames[:] = [name for name in dirnames if not _skipped(os.path.join(dirpath, name), skip_dirs)]
        count += len(filenames)
    return count


def output_dir_status(
    path: Path, *, exact_count: bool = False, skip_dirs: frozenset[str] = frozenset()
) -> dict[str, Any]:
    """A folder's existence and file count; ``skip_dirs`` (normcased absolute) are not walked."""
    exists = path.exists()
    file_count = 0
    file_count_exact = True
    if exists:
        if exact_count:
            file_count = count_files(path, skip_dirs)
        else:
            file_count = 1 if directory_has_file(path, skip_dirs) else 0
            file_count_exact = False
    return {
        "path": slash(path),
        "exists": exists,
        "fileCount": file_count,
        "fileCountExact": file_count_exact,
    }


def unity_type_status(layout: ExportLayout, type_name: str, *, exact_count: bool = False) -> dict[str, Any]:
    """One Unity type's published output: its store rows plus its loose media files.

    Store rows are always counted exactly (one indexed query); the loose
    media folder follows ``exact_count`` like every other output folder.
    """
    store = open_store_if_present(layout.root)
    row_count = store.count(type_name) if store is not None else 0
    media = output_dir_status(layout.unity_type_dir(type_name), exact_count=exact_count)
    return {
        "path": slash(layout.unity_type_dir(type_name)),
        "storePath": slash(layout.unity_store_path),
        "exists": row_count > 0 or media["exists"],
        "storeRowCount": row_count,
        "mediaFileCount": media["fileCount"],
        "fileCount": row_count + media["fileCount"],
        "fileCountExact": media["fileCountExact"],
    }


def game_dir_status(layout: ExportLayout, folder: str, *, exact_count: bool = False) -> dict[str, Any]:
    """One game/ folder's published files: loose files plus any packed rows under it.

    A packed folder (``PACKED_GAME_DIRS``) at or under ``folder``, or holding
    it, is read only from game/GameFiles.sqlite: its rows are always counted
    exactly, and loose files on disk inside it are not counted, so the total
    stays comparable with the loose count of an older layout. The loose part
    follows ``exact_count`` like every other output folder.
    """
    folder = folder.replace("\\", "/").strip("/")
    key = folder.casefold()
    path = layout.game.joinpath(*folder.split("/"))
    whole_packed = [
        packed for packed in PACKED_GAME_DIRS
        if packed.casefold() == key or packed.casefold().startswith(key + "/")
    ]
    inside_packed = packed_game_dir(folder)
    if not whole_packed and inside_packed is None:
        return output_dir_status(path, exact_count=exact_count)

    store = open_game_files_if_present(layout.root)
    row_count = 0
    if store is not None:
        if inside_packed is not None and inside_packed.casefold() != key:
            row_count = sum(
                1 for row in store.iter_rows(inside_packed)
                if row.path.casefold().startswith(key + "/")
            )
        else:
            row_count = sum(store.count(packed) for packed in whole_packed)
    if inside_packed is not None:
        loose = {"exists": False, "fileCount": 0, "fileCountExact": True}
    else:
        skip = frozenset(
            os.path.normcase(os.path.abspath(layout.game.joinpath(*packed.split("/"))))
            for packed in whole_packed
        )
        loose = output_dir_status(path, exact_count=exact_count, skip_dirs=skip)
    return {
        "path": slash(path),
        "storePath": slash(layout.game_file_store_path),
        "exists": row_count > 0 or loose["exists"],
        "storeRowCount": row_count,
        "looseFileCount": loose["fileCount"],
        "fileCount": row_count + loose["fileCount"],
        "fileCountExact": loose["fileCountExact"],
    }


def required_output_status(output_root: Path, sources: tuple[str, ...], *, exact_counts: bool = False) -> list[dict[str, Any]]:
    layout = ExportLayout(output_root)
    rows: list[dict[str, Any]] = []
    for folder in REQUIRED_GAME_DIRS:
        rows.append({
            "source": "game",
            "kind": f"game/{folder}",
            **game_dir_status(layout, folder, exact_count=exact_counts),
        })
    for type_name in REQUIRED_UNITY_TYPES:
        rows.append({
            "source": "game",
            "kind": f"game/Unity/{type_name}",
            **unity_type_status(layout, type_name, exact_count=exact_counts),
        })
    for source in sources:
        rows.append({
            "source": source,
            "kind": "meta/asset_map",
            **output_dir_status(animestudio_stage_dir(output_root, source, "maps"), exact_count=exact_counts),
        })
    return rows


def top_level_source_audit(game_root: Path, selected_sources: tuple[str, ...]) -> dict[str, Any]:
    selected = {source.lower() for source in selected_sources}
    entries: list[dict[str, Any]] = []
    unselected_data_roots: list[dict[str, Any]] = []
    for entry in sorted(game_root.iterdir(), key=lambda item: item.name.lower()):
        info = {
            "name": entry.name,
            "isDir": entry.is_dir(),
            "selectedForExport": entry.name.lower() in selected,
        }
        if entry.is_file():
            info["size"] = entry.stat().st_size
        entries.append(info)
        if entry.is_dir() and not info["selectedForExport"]:
            try:
                file_count = sum(1 for item in entry.rglob("*") if item.is_file())
            except OSError:
                file_count = -1
            if file_count:
                unselected_data_roots.append({
                    "name": entry.name,
                    "fileCount": file_count,
                })
    return {
        "entries": entries,
        "unselectedDataRoots": unselected_data_roots,
    }


def build_report(
    *,
    game_root: Path,
    output_root: Path,
    summary_path: Path,
    sources: tuple[str, ...] | None,
    exact_output_counts: bool = False,
) -> dict[str, Any]:
    summary = read_json(summary_path, {})
    if not isinstance(summary, dict) or not summary:
        return {
            "fresh": False,
            "summaryPath": slash(summary_path),
            "error": "export summary missing or invalid",
        }

    selected_sources = sources or tuple(summary.get("sources_selected") or SOURCES)
    selected_sources = ordered_unique([source for source in selected_sources if source in SOURCES])
    if not selected_sources:
        selected_sources = SOURCES

    exported_source_sizes = summary.get("source_sizes") or {}
    current_source_sizes = collect_source_sizes(game_root, selected_sources)
    source_rows = [
        source_fingerprint_drift(source, current_source_sizes[source], exported_source_sizes.get(source) or {})
        for source in selected_sources
    ]
    output_rows = required_output_status(output_root, selected_sources, exact_counts=exact_output_counts)
    layout = top_level_source_audit(game_root, selected_sources)
    missing_outputs = [
        row for row in output_rows
        if not row["exists"] or int(row.get("fileCount") or 0) <= 0
    ]
    stale_sources = [row for row in source_rows if not row["fresh"]]
    return {
        "fresh": not stale_sources and not missing_outputs,
        "gameRoot": str(game_root),
        "outputRoot": slash(output_root),
        "summaryPath": slash(summary_path),
        "selectedSources": list(selected_sources),
        "sources": source_rows,
        "requiredOutputs": output_rows,
        "missingOutputs": missing_outputs,
        "topLevelSourceAudit": layout,
    }


def print_report(report: dict[str, Any]) -> None:
    if report.get("error"):
        print(f"[verify_export_freshness] {report['error']}: {report.get('summaryPath')}", file=sys.stderr)
        return

    status = "fresh" if report.get("fresh") else "stale"
    print(f"[verify_export_freshness] WebUI export is {status}")
    for row in report.get("sources") or []:
        source_status = "fresh" if row.get("fresh") else "stale"
        print(f"[verify_export_freshness] source {row['source']}: {source_status}")
        if row.get("drift"):
            print(
                f"[verify_export_freshness]   drift fields: {', '.join(sorted(row['drift']))}",
                file=sys.stderr,
            )
    for row in report.get("missingOutputs") or []:
        print(
            f"[verify_export_freshness] missing/empty output: {row['kind']} {row['path']}",
            file=sys.stderr,
        )
    unselected = (report.get("topLevelSourceAudit") or {}).get("unselectedDataRoots") or []
    if unselected:
        names = ", ".join(f"{row['name']}({row['fileCount']})" for row in unselected[:12])
        print(
            "[verify_export_freshness] note: top-level roots not exported by the WebUI source set: "
            f"{names}"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-root",
        type=Path,
        help="Installed Endfield_Data root. Defaults to the latest export summary's game_root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Export root to verify. Defaults to the latest export summary's output_root.",
    )
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--sources", nargs="+", choices=SOURCES)
    parser.add_argument("--json-out", type=Path, help="Optional path to write the verification report JSON.")
    parser.add_argument("--warn-only", action="store_true", help="Print stale status but exit 0.")
    parser.add_argument(
        "--full-output-counts",
        action="store_true",
        help=(
            "Count every file in required export output dirs instead of using the fast non-empty check. "
            "Unity object documents are always counted exactly as game/Unity.sqlite rows, "
            "and packed game files (e.g. game/Json/LipSync) as game/GameFiles.sqlite rows."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary_path = args.summary.resolve()
    summary = read_json(summary_path, {})
    summary_game_root = summary.get("game_root") if isinstance(summary, dict) else None
    summary_output_root = summary.get("output_root") if isinstance(summary, dict) else None
    game_root = (args.game_root or Path(summary_game_root or DEFAULT_GAME_ROOT)).resolve()
    output_root = (args.output or Path(summary_output_root or DEFAULT_OUTPUT)).resolve()
    try:
        ExportLayout(output_root).require()
    except ExportLayoutError as exc:
        print(f"[verify_export_freshness] {exc}", file=sys.stderr)
        return 1
    if not game_root.exists():
        # Rebuilding from an existing export_full does not need the client, so
        # only the freshness comparison itself is lost here.
        if native_evidence_required():
            raise SystemExit(f"Game root not found: {game_root}")
        print(
            "[verify_export_freshness] skipped: installed game data not found "
            f"at {game_root}; cannot compare export_full against the client. "
            "Point endfield_paths.bat or ENDFIELD_GAME_ROOT at the install.",
            file=sys.stderr,
        )
        return 0
    report = build_report(
        game_root=game_root,
        output_root=output_root,
        summary_path=summary_path,
        sources=tuple(args.sources) if args.sources else None,
        exact_output_counts=args.full_output_counts,
    )
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_report(report)
    if report.get("fresh") or args.warn_only:
        return 0
    print("[verify_export_freshness] rerun .\\export.bat --from-game before building WebUI data", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
