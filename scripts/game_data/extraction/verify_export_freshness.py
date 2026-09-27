#!/usr/bin/env python3
"""Verify that the outputs a WebUI build reads match the installed Endfield data.

The WebUI reads ``export_full/``; the source of truth is the installed
``Endfield_Data`` tree. An extraction run exports only its scope, so each
published structured block, Unity class and the asset maps carry their own
source fingerprint (``meta/extraction/provenance.json``, written by the
exporter). A build names what it reads (``--require-*``, or the page registry
through ``build_report(requirements=...)``) and passes only when each of those
outputs exists and was extracted from the build installed now.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, replace
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
    EXTRACTION_PROVENANCE_SCHEMA,
    PROVENANCE_FINGERPRINT_FIELDS,
    SOURCES,
    animestudio_stage_dir,
    collect_source_sizes,
)
from scripts.game_data.extraction.scope import STRUCTURED_BLOCKS, UNITY_CONVERT_TYPES, UNITY_JSON_TYPES


DEFAULT_SUMMARY = DEFAULT_REPORTS / "export_full_summary.json"
#: The game/ folder a structured block publishes into, for the blocks whose
#: folder must be non-empty. Other blocks are checked by provenance only.
BLOCK_GAME_DIRS = {
    "table": "Table",
    "json-data": "Json",
    "video": "Video",
    "lua": "Lua",
    "terrain-height": "Terrain",
    "terrain": "Terrain",
}


@dataclass(frozen=True)
class Requirements:
    """The outputs one build reads: structured blocks, Unity classes, asset maps.

    A required output must exist and be current. An optional one may be absent
    (its builder degrades) but, when present, must be current too: data from two
    builds must not meet in one page. ``reused`` names outputs the build knowingly
    takes from an earlier build -- a section (``unity``, ``meta``) or one
    ``section/key`` -- which are reported but do not block. ``partial_ok`` names the
    Unity classes a name-filtered export still satisfies.

    Unity classes are single-tree (object documents are rows of
    game/Unity.sqlite, media loose files); a game/ folder that holds a packed
    folder (game/Json holds Json/LipSync) counts its loose files plus its rows of
    game/GameFiles.sqlite; asset maps stay per layer.
    """

    structured: tuple[str, ...] = ()
    unity: tuple[str, ...] = ()
    asset_map: bool = False
    optional_structured: tuple[str, ...] = ()
    optional_unity: tuple[str, ...] = ()
    optional_asset_map: bool = False
    reused: frozenset[str] = frozenset()
    partial_ok: frozenset[str] = frozenset()


#: What a build that names nothing reads: the Story/Text inputs.
DEFAULT_REQUIREMENTS = Requirements(("table", "json-data"), ("TextAsset", "MonoBehaviour"), True)


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


def required_output_status(
    output_root: Path,
    sources: tuple[str, ...],
    *,
    exact_counts: bool = False,
    requirements: Requirements = DEFAULT_REQUIREMENTS,
) -> list[dict[str, Any]]:
    """Each named output's presence, with the provenance key that dates it."""
    layout = ExportLayout(output_root)
    rows: list[dict[str, Any]] = []
    folders_seen: dict[str, dict[str, Any]] = {}

    def structured_row(block: str, required: bool) -> None:
        folder = BLOCK_GAME_DIRS.get(block)
        if folder is None:
            rows.append({
                "source": "game",
                "kind": f"structured/{block}",
                "provenance": ("structured", block),
                "required": required,
                "path": None,
                "exists": True,
                "fileCount": 1,
                "fileCountExact": False,
            })
            return
        if folder in folders_seen:
            folders_seen[folder]["required"] |= required
            return
        row = {
            "source": "game",
            "kind": f"game/{folder}",
            "provenance": ("structured", block),
            "required": required,
            **game_dir_status(layout, folder, exact_count=exact_counts),
        }
        folders_seen[folder] = row
        rows.append(row)

    for block in requirements.structured:
        structured_row(block, True)
    for block in requirements.optional_structured:
        if block not in requirements.structured:
            structured_row(block, False)
    unity = dict.fromkeys(requirements.optional_unity, False)
    unity.update(dict.fromkeys(requirements.unity, True))
    for type_name, required in unity.items():
        rows.append({
            "source": "game",
            "kind": f"game/Unity/{type_name}",
            "provenance": ("unity", type_name),
            "required": required,
            **unity_type_status(layout, type_name, exact_count=exact_counts),
        })
    if requirements.asset_map or requirements.optional_asset_map:
        for source in sources:
            rows.append({
                "source": source,
                "kind": "meta/asset_map",
                "provenance": ("meta", "asset_map"),
                "required": requirements.asset_map,
                **output_dir_status(animestudio_stage_dir(output_root, source, "maps"), exact_count=exact_counts),
            })
    return rows


def load_provenance(output_root: Path) -> dict[str, Any] | None:
    """The exporter's per-output provenance, or None for an export that predates it."""
    path = ExportLayout(output_root).extraction_provenance_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if payload.get("schema") == EXTRACTION_PROVENANCE_SCHEMA else None


def output_stamp(
    provenance: dict[str, Any] | None,
    summary: dict[str, Any],
    section: str,
    key: str,
) -> dict[str, Any] | None:
    """The source fingerprints one output was extracted from.

    An export that predates per-output provenance keeps its one historical
    authority, the summary's structured fingerprint. With provenance, an output
    it does not name falls back to its `default` stamp and otherwise has no
    known origin, which fails closed.
    """
    if provenance is None:
        sizes = summary.get("source_sizes") or {}
        return {"run": summary.get("report_run_id"), "sources": sizes} if sizes else None
    stamp = (provenance.get(section) or {}).get(key)
    return stamp if isinstance(stamp, dict) else provenance.get("default")


def stamp_drift(stamp: dict[str, Any] | None, current: dict[str, Any], sources: tuple[str, ...]) -> dict[str, Any]:
    """Per-source fields where ``stamp`` differs from the installed build; empty when current."""
    if stamp is None:
        return {source: "no extraction provenance" for source in sources}
    drift: dict[str, Any] = {}
    for source in sources:
        exported = (stamp.get("sources") or {}).get(source) or {}
        fields = {
            field: {"current": current[source].get(field), "exported": exported.get(field)}
            for field in PROVENANCE_FINGERPRINT_FIELDS
            if current[source].get(field) != exported.get(field)
        }
        if fields:
            drift[source] = fields
    return drift


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
    requirements: Requirements = DEFAULT_REQUIREMENTS,
) -> dict[str, Any]:
    """Whether every required output exists and every present one is current."""
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

    current_source_sizes = collect_source_sizes(game_root, selected_sources)
    provenance = load_provenance(output_root)
    output_rows = required_output_status(
        output_root, selected_sources, exact_counts=exact_output_counts, requirements=requirements,
    )
    missing_outputs: list[dict[str, Any]] = []
    absent_optional: list[dict[str, Any]] = []
    for row in output_rows:
        section, key = row.pop("provenance")
        present = bool(row["exists"]) and int(row.get("fileCount") or 0) > 0
        if not present:
            (missing_outputs if row["required"] else absent_optional).append(row)
            row.update(fresh=True, drift={}, partial=None, staleAccepted=False, extractedBy=None)
            continue
        stamp = output_stamp(provenance, summary, section, key)
        drift = stamp_drift(stamp, current_source_sizes, selected_sources)
        partial = (stamp or {}).get("partial")
        refused_partial = bool(partial) and key not in requirements.partial_ok
        row["extractedBy"] = (stamp or {}).get("run")
        row["drift"] = drift
        row["partial"] = partial
        row["fresh"] = not drift and not refused_partial
        row["staleAccepted"] = (
            bool(drift) and not refused_partial
            and (section in requirements.reused or f"{section}/{key}" in requirements.reused)
        )
    stale_outputs = [row for row in output_rows if not row["fresh"]]
    blocking = [row for row in stale_outputs if not row["staleAccepted"]]
    source_rows = [
        {
            "source": source,
            "fresh": not any(source in row["drift"] for row in blocking),
            "current": current_source_sizes[source],
            "staleOutputs": [row["kind"] for row in stale_outputs if source in row["drift"]],
        }
        for source in selected_sources
    ]
    return {
        "fresh": not blocking and not missing_outputs,
        "gameRoot": str(game_root),
        "outputRoot": slash(output_root),
        "summaryPath": slash(summary_path),
        "provenance": (
            "per-output provenance" if provenance is not None
            else "export summary; this export predates per-output provenance"
        ),
        "selectedSources": list(selected_sources),
        "sources": source_rows,
        "requiredOutputs": output_rows,
        "missingOutputs": missing_outputs,
        "absentOptionalOutputs": absent_optional,
        "staleOutputs": stale_outputs,
        "topLevelSourceAudit": top_level_source_audit(game_root, selected_sources),
    }


def print_report(report: dict[str, Any]) -> None:
    if report.get("error"):
        print(f"[verify_export_freshness] {report['error']}: {report.get('summaryPath')}", file=sys.stderr)
        return

    status = "fresh" if report.get("fresh") else "stale"
    print(f"[verify_export_freshness] required export outputs are {status} (checked by {report.get('provenance')})")
    for row in report.get("staleOutputs") or []:
        if row.get("drift"):
            sources = ", ".join(sorted(row["drift"]))
            reason = f"extracted by run {row.get('extractedBy') or 'unknown'}, differs from the installed {sources}"
        else:
            reason = f"exported in part ({row.get('partial')})"
        note = "; reused from an earlier build" if row.get("staleAccepted") else ""
        print(f"[verify_export_freshness]   {row['kind']}: {reason}{note}", file=sys.stderr)
    for row in report.get("absentOptionalOutputs") or []:
        print(
            f"[verify_export_freshness] note: optional output absent, its builder degrades: {row['kind']}",
            file=sys.stderr,
        )
    for row in report.get("missingOutputs") or []:
        print(
            f"[verify_export_freshness] missing/empty output: {row['kind']} {row.get('path') or ''}".rstrip(),
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
        "--require-structured", nargs="+", choices=STRUCTURED_BLOCKS, metavar="BLOCK", default=None,
        help="Structured blocks the build reads. Naming any requirement replaces the default Story/Text set.",
    )
    parser.add_argument(
        "--require-unity", nargs="+", choices=sorted(set(UNITY_JSON_TYPES) | set(UNITY_CONVERT_TYPES)),
        metavar="CLASS", default=None, help="Unity classes the build reads.",
    )
    parser.add_argument("--require-asset-map", action="store_true", help="The build reads the asset maps.")
    parser.add_argument(
        "--accept-reused", nargs="+", metavar="KEY", default=(),
        help=(
            "Outputs knowingly taken from an earlier build, reported but not blocking: a section "
            "(`unity`, `meta`, `structured`) or one `section/key` such as `structured/terrain-height`."
        ),
    )
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


def requirements_from_args(args: argparse.Namespace) -> Requirements:
    if args.require_structured is None and args.require_unity is None and not args.require_asset_map:
        base = DEFAULT_REQUIREMENTS
    else:
        base = Requirements(
            tuple(args.require_structured or ()),
            tuple(args.require_unity or ()),
            bool(args.require_asset_map),
        )
    return replace(base, reused=frozenset(args.accept_reused))


def verify(
    *,
    game_root: Path | None = None,
    output_root: Path | None = None,
    summary_path: Path = DEFAULT_SUMMARY,
    requirements: Requirements = DEFAULT_REQUIREMENTS,
    sources: tuple[str, ...] | None = None,
    exact_output_counts: bool = False,
    json_out: Path | None = None,
    warn_only: bool = False,
    remedy: str = "re-extract them with export.bat PAGE --from-game before building WebUI data",
) -> int:
    """Check ``requirements`` against the installed build, print the result, return an exit code."""
    summary_path = summary_path.resolve()
    summary = read_json(summary_path, {})
    summary_game_root = summary.get("game_root") if isinstance(summary, dict) else None
    summary_output_root = summary.get("output_root") if isinstance(summary, dict) else None
    game_root = (game_root or Path(summary_game_root or DEFAULT_GAME_ROOT)).resolve()
    output_root = (output_root or Path(summary_output_root or DEFAULT_OUTPUT)).resolve()
    try:
        ExportLayout(output_root).require()
    except ExportLayoutError as exc:
        print(f"[verify_export_freshness] {exc}", file=sys.stderr)
        return 1
    if not game_root.exists():
        # Rebuilding from an existing export does not need the client, so only
        # the freshness comparison itself is lost here.
        if native_evidence_required():
            raise SystemExit(f"Game root not found: {game_root}")
        print(
            "[verify_export_freshness] skipped: installed game data not found "
            f"at {game_root}; cannot compare the export against the client. "
            "Point endfield_paths.bat or ENDFIELD_GAME_ROOT at the install.",
            file=sys.stderr,
        )
        return 0
    report = build_report(
        game_root=game_root,
        output_root=output_root,
        summary_path=summary_path,
        sources=sources,
        exact_output_counts=exact_output_counts,
        requirements=requirements,
    )
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_report(report)
    if report.get("fresh") or warn_only:
        return 0
    print(f"[verify_export_freshness] {remedy}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return verify(
        game_root=args.game_root,
        output_root=args.output,
        summary_path=args.summary,
        requirements=requirements_from_args(args),
        sources=tuple(args.sources) if args.sources else None,
        exact_output_counts=args.full_output_counts,
        json_out=args.json_out,
        warn_only=args.warn_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
