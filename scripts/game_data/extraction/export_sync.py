"""Rolling, independent export snapshots for installed-game synchronization.

Updates continues to compare two real layout-v4 exports. Snapshots copy mutable
files and back up SQLite stores; only converted Unity media shares immutable
inodes (the exporter unlinks those files before replacement). Audio is copied.
State advances only after extraction, page builds and Updates all succeed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
from contextlib import closing
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scripts.common import read_json, sha256_file
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout, ExportLayoutError, INSTALLED_LAYERS
from scripts.game_data.extraction.export_full_from_game import (
    DEFAULT_ANIMESTUDIO, collect_source_sizes, build_animestudio_object_index_cli_provenance,
)

SCHEMA = "endfield.export-sync.v1"
SNAPSHOT_SCHEMA = "endfield.export-snapshot.v1"


class SyncError(RuntimeError):
    pass


def write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sync_root(export_root: Path) -> Path:
    key = hashlib.sha256(str(export_root.resolve()).casefold().encode("utf-8")).hexdigest()[:16]
    return REPO_ROOT / "reports" / "export" / "sync" / key


def input_identity(game_root: Path) -> dict[str, Any]:
    """Selected installed sources, native inputs and the actual exporter code."""
    sources = tuple(layer for layer in INSTALLED_LAYERS if (game_root / layer).is_dir())
    native_paths = {
        "GameAssembly.dll": game_root.parent / "GameAssembly.dll",
        "global-metadata.dat": game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat",
    }
    return {
        "gameRoot": str(game_root.resolve()),
        "sources": collect_source_sizes(game_root, sources),
        "native": {name: sha256_file(path) if path.is_file() else None for name, path in native_paths.items()},
        "cli": build_animestudio_object_index_cli_provenance(DEFAULT_ANIMESTUDIO),
    }


def coherent_export(export_root: Path, summary: dict[str, Any]) -> bool:
    """Whether the current root is safe to adopt as a previously completed export."""
    try:
        ExportLayout(export_root).require()
    except ExportLayoutError:
        return False
    if Path(str(summary.get("output_root") or "")).resolve() != export_root.resolve():
        return False
    if summary.get("command_failure_count", 0):
        return False
    delta = summary.get("structured_incremental") or {}
    if delta and delta.get("baselineAdvanced") is not True:
        finalized = read_json(ExportLayout(export_root).extraction_incremental_dir / "pending_manifest.json", {})
        if (finalized.get("baselineAdvanced") is not True
                or finalized.get("outputRoot") != str(export_root.resolve())
                or finalized.get("sourceFingerprints") != delta.get("sourceFingerprints")):
            return False
    provenance = read_json(ExportLayout(export_root).extraction_provenance_path, {})
    expected = summary.get("source_sizes")
    if not isinstance(expected, dict) or not expected:
        return False
    for section in ("structured", "unity", "meta"):
        for stamp in (provenance.get(section) or {}).values():
            if not isinstance(stamp, dict) or stamp.get("partial"):
                return False
            for source, current in expected.items():
                exported = (stamp.get("sources") or {}).get(source) or {}
                if any(exported.get(field) != current.get(field) for field in ("files", "bytes", "fingerprint")):
                    return False
    return True


def snapshot_export(source: Path, destination: Path, owner: Path) -> Path:
    """Publish a complete independent snapshot, with the layout marker last."""
    source, destination = source.resolve(), destination.resolve()
    ExportLayout(source).require()
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise SyncError("snapshot and source export must be disjoint")
    if destination.exists():
        raise SyncError(f"snapshot destination already exists: {destination}")
    destination.mkdir(parents=True)
    layout_bytes = (source / "layout.json").read_bytes()
    counts = {"copied": 0, "linked": 0, "stores": 0}
    started = time.monotonic()
    try:
        for directory, dirs, names in os.walk(source):
            base = Path(directory)
            if (base.is_symlink() or base.resolve() != base
                    or any((base / name).is_symlink() or (base / name).resolve() != base / name for name in dirs)):
                raise SyncError(f"snapshot refuses directory links: {base}")
            relative_dir = base.relative_to(source)
            target_dir = destination / relative_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            for name in names:
                path = base / name
                relative = path.relative_to(source)
                if relative.as_posix() == "layout.json" or name.endswith(("-wal", "-shm", "-journal")):
                    continue
                if path.is_symlink() or path.resolve() != path:
                    raise SyncError(f"snapshot refuses a file link: {path}")
                target = target_dir / name
                if path.suffix.lower() == ".sqlite":
                    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as old:
                        with closing(sqlite3.connect(target)) as new:
                            old.backup(new)
                    shutil.copystat(path, target)
                    counts["stores"] += 1
                elif relative.parts[:2] == ("game", "Unity"):
                    try:
                        os.link(path, target)
                        counts["linked"] += 1
                    except OSError:
                        shutil.copy2(path, target)
                        counts["copied"] += 1
                else:
                    shutil.copy2(path, target)
                    counts["copied"] += 1
            shutil.copystat(base, target_dir)
            if time.monotonic() - started >= 30:
                print(f"[export-sync] snapshot progress: {counts}", flush=True)
                started = time.monotonic()
        ExportLayout(source).require()
        if (source / "layout.json").read_bytes() != layout_bytes:
            raise SyncError("source export changed while its snapshot was copied")
        write_state(destination / "snapshot.json", {
            "schema": SNAPSHOT_SCHEMA, "owner": str(owner.resolve()),
            "source": str(source), "counts": counts,
        })
        (destination / "layout.json").write_bytes(layout_bytes)
    except BaseException:
        # This path was created by this invocation and checked disjoint above.
        shutil.rmtree(destination)
        raise
    print(f"[export-sync] saved {destination}: {counts}", flush=True)
    return destination


class SyncTransaction:
    def __init__(self, export_root: Path, *, state_root: Path | None = None):
        self.export_root = export_root.resolve()
        self.root = (state_root or sync_root(export_root)).resolve()
        if self.root.is_relative_to(self.export_root) or self.export_root.is_relative_to(self.root):
            raise SyncError("sync state and export root must be disjoint")
        self.path = self.root / "state.json"
        self.state = read_json(self.path, None) if self.path.exists() else {}
        if not isinstance(self.state, dict) or (self.path.exists() and not self.state):
            raise SyncError(f"invalid sync state; preserve it for recovery: {self.path}")
        if self.state and (self.state.get("schema") != SCHEMA or self.state.get("exportRoot") != str(self.export_root)):
            raise SyncError(f"unsupported or foreign sync state: {self.path}")

    def _snapshot(self, source: Path) -> Path:
        return snapshot_export(source, self.root / "snapshots" / uuid.uuid4().hex, self.export_root)

    def begin(
        self, identity: dict[str, Any], summary: dict[str, Any], previous: Path | None, *, allow_noop: bool = True,
    ) -> bool:
        """Return True for an unchanged committed export; otherwise keep one pending baseline."""
        if allow_noop and self.state.get("status") == "complete" and self.state.get("lastSuccessfulInputs") == identity:
            if coherent_export(self.export_root, summary):
                return True
        if self.state.get("status") != "pending":
            baseline = self.state.get("lastSuccessfulExport")
            kind = "last_successful_sync"
            if not baseline:
                if coherent_export(self.export_root, summary):
                    baseline, kind = str(self._snapshot(self.export_root)), "existing_complete_export"
                elif previous is not None and previous.resolve() != self.export_root:
                    ExportLayout(previous).require()
                    baseline, kind = str(self._snapshot(previous)), "saved_previous_export"
                else:
                    baseline, kind = None, "first_sync_without_previous_export"
            self.state.update({
                "schema": SCHEMA, "exportRoot": str(self.export_root), "status": "pending",
                "baseline": baseline, "baselineKind": kind,
            })
        if self.state.get("baseline"):
            ExportLayout(Path(self.state["baseline"])).require()
        self.state["pendingInputs"] = identity
        write_state(self.path, self.state)
        return False

    @property
    def baseline(self) -> Path | None:
        return Path(self.state["baseline"]) if self.state.get("baseline") else None

    def commit(
        self, identity: dict[str, Any], *, publish: Callable[[], None] | None = None,
        current_inputs: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        if self.state.get("pendingInputs") != identity:
            raise SyncError("installed game or exporter changed during synchronization; baseline was not advanced")
        successful = self._snapshot(self.export_root)
        try:
            if current_inputs is not None and current_inputs() != identity:
                raise SyncError("installed inputs changed while saving the export snapshot; baseline was not advanced")
            if publish is not None:
                publish()
        except BaseException:
            if successful.resolve().parent != (self.root / "snapshots").resolve():
                raise SyncError(f"unsafe uncommitted snapshot cleanup: {successful}")
            shutil.rmtree(successful)
            raise
        self.state.update({
            "status": "complete", "lastSuccessfulExport": str(successful),
            "lastSuccessfulInputs": identity, "comparisonPreviousExport": str(self.baseline) if self.baseline else None,
        })
        self.state.pop("pendingInputs", None)
        write_state(self.path, self.state)
        # Retain the last comparison's old side and the next run's successful
        # baseline. Never prune a user-owned export or a foreign snapshot.
        keep = {successful, self.baseline}
        snapshots = self.root / "snapshots"
        for path in snapshots.iterdir():
            if path in keep or not path.is_dir() or path.is_symlink():
                continue
            receipt = read_json(path / "snapshot.json", {})
            if receipt.get("schema") != SNAPSHOT_SCHEMA or receipt.get("owner") != str(self.export_root):
                continue
            if path.resolve().parent != snapshots.resolve():
                raise SyncError(f"unsafe snapshot prune target: {path}")
            print(f"[export-sync] pruning superseded managed snapshot: {path}", flush=True)
            shutil.rmtree(path)
