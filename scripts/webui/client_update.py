"""Refresh the export after a client update, keeping the old export for Updates.

    python -m scripts.webui.client_update [--label NAME] [--pages PAGE ...]
                                          [--plan-only] [--force] [--stop-after PHASE]
    python -m scripts.webui.client_update --resume
    python -m scripts.webui.client_update --rollback

Phases, each recorded in ``webui/data/_build/client_update/state.json`` so an
interrupted run resumes where it stopped:

1. ``plan``: ``package_diff`` compares the installed client with the VFS ledger
   the export was certified from and predicts the old outputs a refresh will
   replace. Nothing is written; an up-to-date export stops here unless
   ``--force``.
2. ``archive``: the export folder is renamed to ``<export>_<label>`` and
   snapshotted back to its own path (``export_sync.snapshot_export``: Unity
   media hard-linked, since publication replaces rather than rewrites them;
   everything else copied). Extracting in place keeps every absolute path the
   export records about itself (layout, summary, evidence receipts) correct.
3. ``extract``: ``export.py PAGES --from-game --extract-only``.
4. ``verify``: the new export is compared with the archive (hard link
   identity, untouched copy by size and mtime, else bytes; stores by row
   SHA256) and every change is matched against the plan. A change the plan did
   not predict stops the run here, before any page is built, unless
   ``--accept-unexpected``. ``--rollback`` restores the old export up to this
   point.
5. ``pages``: ``export.py PAGES`` (with ``--decode-audio`` when Audio is built).
6. ``updates``: ``build_updates.py`` compares archive and export and prunes the
   archive's byte-identical game files.
7. ``trim``: the archive's ``meta/`` is removed, so the archive keeps only
   the old copies of the game data the update changed or removed.

Reports go to ``reports/updates/client_update/<label>/``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

if __package__ in {None, ""}:
    raise SystemExit("Run this maintained entry point as: python -m scripts.webui.client_update")

from scripts.common import resolve_installed_game_data_root
from scripts.game_data.extraction import package_diff
from scripts.game_data.extraction.export_changed_game_data import exclusive_workflow_lock
from scripts.game_data.extraction.export_sync import snapshot_export, sync_root
from scripts.game_data.unity_store import UnityObjectStore, UnityStoreError
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import (
    ExportLayout,
    ExportLayoutError,
    configured_animestudio_cli,
    configured_export_root,
)
from scripts.webui.pages import resolve_pages

SCHEMA = "endfield.client-update.v1"
STATE_PATH = REPO_ROOT / "webui/data/_build/client_update/state.json"
REPORT_ROOT = REPO_ROOT / "reports/updates/client_update"
PHASES = ("plan", "archive", "extract", "verify", "pages", "updates", "trim")
STORE_SUFFIX = ".sqlite"
# Decoded later by the Audio page build, so not part of the extraction check.
AUDIO_PREFIX = "game/Audio/"
UNITY_STORE = "game/Unity.sqlite"
SPACE_MARGIN = 20 << 30


class ClientUpdateError(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"[client-update {time.strftime('%H:%M:%S')}] {message}", flush=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_state() -> dict[str, Any] | None:
    if not STATE_PATH.is_file():
        return None
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    state["updated"] = datetime.now(timezone.utc).isoformat()
    write_json(STATE_PATH, state)


def run_module(module: str, *arguments: str) -> int:
    command = [sys.executable, "-m", module, *arguments]
    log(subprocess.list2cmdline(command))
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


# -- comparing two export trees ------------------------------------------------

def walk_files(root: Path) -> Iterator[tuple[str, os.stat_result]]:
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    yield Path(entry.path).relative_to(root).as_posix(), entry.stat()


def is_data_store(rel: str) -> bool:
    """Game object stores, compared by row; evidence databases under meta/ are files."""
    return rel.startswith("game/") and rel.endswith(STORE_SUFFIX)


def same_bytes(left: Path, right: Path) -> bool:
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            x, y = a.read(1 << 20), b.read(1 << 20)
            if x != y:
                return False
            if not x:
                return True


def compare_trees(old_root: Path, new_root: Path) -> dict[str, Any]:
    """Changed/added/deleted files between two export trees; stores listed apart."""
    old = {rel: stat for rel, stat in walk_files(old_root) if not rel.endswith(("-wal", "-shm", "-journal"))}
    result: dict[str, Any] = {"changed": [], "added": [], "deleted": [], "stores": [],
                              "identical": 0, "compared": 0}
    started = time.monotonic()
    for rel, stat in walk_files(new_root):
        if rel.endswith(("-wal", "-shm", "-journal")):
            continue
        before = old.pop(rel, None)
        if is_data_store(rel):
            result["stores"].append(rel)
            continue
        if before is None:
            result["added"].append(rel)
        elif before.st_size != stat.st_size:
            result["changed"].append(rel)
        elif before.st_mtime_ns == stat.st_mtime_ns:
            # The snapshot copy keeps the old mtime and a hard-linked Unity
            # file is the old file itself; a rewrite or replacement does not.
            # (os.scandir leaves st_ino zero on Windows, so samestat is no
            # use here.)
            result["identical"] += 1
        else:
            result["compared"] += 1
            if same_bytes(old_root / rel, new_root / rel):
                result["identical"] += 1
            else:
                result["changed"].append(rel)
        if time.monotonic() - started >= 60:
            log(f"compared so far: {len(result['changed'])} changed, {result['identical']} identical")
            started = time.monotonic()
    result["deleted"] = sorted(rel for rel in old if not is_data_store(rel))
    result["stores"] += [rel for rel in old if is_data_store(rel)]
    for key in ("changed", "added", "stores"):
        result[key].sort()
    return result


def compare_store(old_path: Path, new_path: Path) -> dict[str, list[str]]:
    """Row keys ``<type>/<name>`` that differ between two object stores."""
    if not old_path.is_file() or not new_path.is_file():
        return {"storeMissing": [str(old_path if not old_path.is_file() else new_path)]}
    with closing(sqlite3.connect(f"file:{new_path.as_posix()}?mode=ro", uri=True)) as connection:
        connection.execute("attach database ? as old", (f"file:{old_path.as_posix()}?mode=ro",))
        tables = {row[0] for row in connection.execute("select name from old.sqlite_master where type='table'")}
        if "objects" not in tables:
            same = same_bytes(old_path, new_path)
            return {} if same else {"storeBytesDiffer": [new_path.name]}
        key = lambda rows: sorted(f"{t}/{n}" for t, n in rows)  # noqa: E731
        return {
            "changed": key(connection.execute(
                "select n.type, n.name from main.objects n join old.objects o "
                "on o.type = n.type and o.name = n.name where o.sha256 is not n.sha256")),
            "added": key(connection.execute(
                "select n.type, n.name from main.objects n where not exists "
                "(select 1 from old.objects o where o.type = n.type and o.name = n.name)")),
            "deleted": key(connection.execute(
                "select o.type, o.name from old.objects o where not exists "
                "(select 1 from main.objects n where n.type = o.type and n.name = o.name)")),
        }


LOCATION_KEY_RE = re.compile(r"sourceoriginalpath$|sourceoffset$", re.IGNORECASE)
LOCATION_LINE_RE = re.compile(rb"^# source_(?:offset|original_path):.*$", re.MULTILINE)
LOCATION_CHECK_LIMIT = 64 << 20


def without_location(document: bytes) -> Any:
    """A document with its recorded source chunk path and offset removed."""
    try:
        value = json.loads(document)
    except (UnicodeDecodeError, ValueError):
        return LOCATION_LINE_RE.sub(b"", document)

    def strip(item: Any) -> Any:
        if isinstance(item, dict):
            return {k: strip(v) for k, v in item.items() if not LOCATION_KEY_RE.search(k)}
        if isinstance(item, list):
            return [strip(v) for v in item]
        return item
    return strip(value)


def content_changed(archive: Path, export_root: Path, files: list[str], store: str | None,
                    rows: list[str]) -> list[str]:
    """Relocation-tier changes that differ in more than their recorded source location."""
    changed: list[str] = []
    for rel in files:
        old, new = archive / rel, export_root / rel
        if (max(old.stat().st_size, new.stat().st_size) > LOCATION_CHECK_LIMIT
                or without_location(old.read_bytes()) != without_location(new.read_bytes())):
            changed.append(rel)
    if rows and store:
        with UnityObjectStore(archive / store) as before, UnityObjectStore(export_root / store) as after:
            for row in rows:
                type_name, name = row.split("/", 1)
                try:
                    same = (without_location(before.read_bytes(type_name, name))
                            == without_location(after.read_bytes(type_name, name)))
                except UnityStoreError:
                    same = False
                if not same:
                    changed.append(f"{store}:{row}")
    return changed


def match_prediction(tree: dict[str, Any], stores: dict[str, dict[str, list[str]]],
                     prediction: dict[str, list[str]], relocated_content: list[str] = ()) -> dict[str, Any]:
    """Sort every observed data change into predicted, unexpected and false alarm.

    A relocation-tier change is expected only when it differs in its recorded
    source location alone; ``relocated_content`` lists those that differ in more.
    """
    rejected = {item.casefold() for item in relocated_content}
    predicted_files = {path.casefold() for key in ("exactFiles", "unityMediaFiles", "dependentMediaFiles")
                       for path in prediction.get(key, ())}
    predicted_rows = {row.casefold() for key in ("gameFileStoreEntries", "unityStoreRows", "dependentStoreRows")
                      for row in prediction.get(key, ())}
    predicted_files |= {p.casefold() for p in prediction.get("relocatedMediaFiles", ())} - rejected
    predicted_rows |= {r.casefold() for r in prediction.get("relocatedStoreRows", ())
                       if f"{UNITY_STORE}:{r}".casefold() not in rejected}
    data = lambda path: path.startswith(("game/", "raw/")) and not path.startswith(AUDIO_PREFIX)  # noqa: E731
    observed_files = [path for path in tree["changed"] + tree["deleted"] if data(path)]
    observed_rows = [(store, row) for store, diff in stores.items()
                     for kind in ("changed", "deleted") for row in diff.get(kind, ())]
    unexpected_files = [path for path in observed_files if path.casefold() not in predicted_files]
    unexpected_rows = [f"{store}:{row}" for store, row in observed_rows if row.casefold() not in predicted_rows]
    expected_count = len(observed_files) - len(unexpected_files) + len(observed_rows) - len(unexpected_rows)
    unexpected_rows += [f"{store}:{kind}" for store, diff in stores.items()
                        for kind in ("storeMissing", "storeBytesDiffer") if diff.get(kind)]
    observed = {path.casefold() for path in observed_files} | {row.casefold() for _store, row in observed_rows}
    exact_alarm = [path for path in prediction.get("exactFiles", ()) if path.casefold() not in observed]
    return {
        "predictedAndChanged": expected_count,
        "relocatedContentChanged": list(relocated_content),
        "unexpectedFiles": unexpected_files,
        "unexpectedStoreRows": unexpected_rows,
        "exactPredictedButUnchanged": exact_alarm,
        "unityPredictedButUnchanged": len([p for p in prediction.get("unityMediaFiles", ())
                                           if p.casefold() not in observed]),
        "addedFiles": [path for path in tree["added"] if data(path)],
        "metaChanged": len([p for p in tree["changed"] + tree["added"] + tree["deleted"]
                            if not p.startswith(("game/", "raw/"))]),
    }


# -- phases ---------------------------------------------------------------------

def phase_plan(state: dict[str, Any], args: argparse.Namespace) -> bool:
    plan_args = argparse.Namespace(
        export_root=Path(state["exportRoot"]), game_root=Path(state["gameRoot"]),
        animestudio=Path(state["animestudio"]), output=Path(state["reportDir"]) / "package_diff.json",
        sample_limit=200, self_check=False, keep_prediction=True)
    report = package_diff.run(plan_args)
    prediction = package_diff.prediction_payload(report.pop("_prediction"))
    write_json(plan_args.output, report)
    write_json(Path(state["reportDir"]) / "prediction.json", prediction)
    package_diff.print_summary(report)
    state["upToDate"] = report["upToDate"]
    if report["upToDate"] and not args.force:
        log("the export already matches the installed client; nothing to refresh (--force to run anyway)")
        return False
    return True


def phase_archive(state: dict[str, Any], args: argparse.Namespace) -> bool:
    export_root, archive = Path(state["exportRoot"]), Path(state["archiveRoot"])
    if not archive.exists():
        ExportLayout(export_root).require()
        copied = sum(stat.st_size for rel, stat in walk_files(export_root)
                     if not rel.startswith("game/Unity/"))
        free = shutil.disk_usage(export_root.parent).free
        log(f"snapshot copies {copied / (1 << 30):.1f} GiB; {free / (1 << 30):.1f} GiB free")
        if copied + SPACE_MARGIN > free:
            raise ClientUpdateError("not enough free space for the snapshot copy")
        try:
            export_root.rename(archive)
        except OSError as exc:
            raise ClientUpdateError(
                f"cannot rename {export_root} to {archive} ({exc}); stop serve.py and anything "
                "else reading the export, then --resume") from exc
        log(f"archived the old export as {archive}")
    if export_root.exists():
        # A half-made snapshot is removed by snapshot_export itself; anything
        # else at the export path is not ours to delete.
        if not (export_root / "snapshot.json").is_file():
            raise ClientUpdateError(f"{export_root} exists but is not this run's snapshot")
    else:
        log("snapshotting the archive back to the export path (Unity media hard-linked)")
        snapshot_export(archive, export_root, owner=STATE_PATH)
    (export_root / "snapshot.json").unlink(missing_ok=True)
    return True


def export_args(state: dict[str, Any]) -> list[str]:
    return [*state["pages"], "--game-root", state["gameRoot"], "--export-root", state["exportRoot"],
            "--animestudio", state["animestudio"]]


def phase_extract(state: dict[str, Any], args: argparse.Namespace) -> bool:
    code = run_module("scripts.webui.export", *export_args(state), "--from-game", "--extract-only")
    if code:
        raise ClientUpdateError(f"extraction failed ({code}); fix it and --resume, or --rollback")
    return True


def phase_verify(state: dict[str, Any], args: argparse.Namespace) -> bool:
    export_root, archive = Path(state["exportRoot"]), Path(state["archiveRoot"])
    report_dir = Path(state["reportDir"])
    log("comparing the new export with the archive")
    tree = compare_trees(archive, export_root)
    stores = {}
    for rel in sorted(set(tree["stores"])):
        log(f"comparing store rows of {rel}")
        stores[rel] = compare_store(archive / rel, export_root / rel)
    prediction = json.loads((report_dir / "prediction.json").read_text(encoding="utf-8"))
    changed_files = {p.casefold() for p in tree["changed"]}
    moved_files = [p for p in prediction.get("relocatedMediaFiles", ()) if p.casefold() in changed_files]
    store_changed = {r.casefold() for r in stores.get(UNITY_STORE, {}).get("changed", ())}
    moved_rows = [r for r in prediction.get("relocatedStoreRows", ()) if r.casefold() in store_changed]
    if moved_files or moved_rows:
        log(f"checking {len(moved_files)} media files and {len(moved_rows)} rows of relocated bundles "
            f"for changes beyond their source location")
    relocated_content = content_changed(archive, export_root, moved_files,
                                        UNITY_STORE if UNITY_STORE in stores else None, moved_rows)
    verdict = match_prediction(tree, stores, prediction, relocated_content)
    write_json(report_dir / "verify.json", {"schema": SCHEMA, "tree": tree, "stores": stores, "verdict": verdict})
    log(f"files: {len(tree['changed'])} changed, {len(tree['added'])} added, {len(tree['deleted'])} deleted, "
        f"{tree['identical']} identical ({tree['compared']} byte-compared)")
    for store, diff in stores.items():
        log(f"{store}: " + ", ".join(f"{len(rows)} {kind}" for kind, rows in diff.items()))
    log(f"predicted changes observed: {verdict['predictedAndChanged']}; predicted exact files unchanged: "
        f"{len(verdict['exactPredictedButUnchanged'])}; predicted Unity media unchanged: "
        f"{verdict['unityPredictedButUnchanged']}; relocated with other changes: "
        f"{len(verdict['relocatedContentChanged'])}; meta files changed: {verdict['metaChanged']}")
    unexpected = verdict["unexpectedFiles"] + verdict["unexpectedStoreRows"]
    if unexpected:
        for item in unexpected[:20]:
            log(f"  unexpected: {item}")
        log(f"{len(unexpected)} changes the plan did not predict; details in {report_dir / 'verify.json'}")
        if not args.accept_unexpected:
            raise ClientUpdateError("stopping before pages: review the unexpected changes, then "
                                    "--resume --accept-unexpected, or --rollback")
    return True


def phase_pages(state: dict[str, Any], args: argparse.Namespace) -> bool:
    extra = ["--decode-audio"] if "audio" in state["pages"] else []
    code = run_module("scripts.webui.export", *export_args(state), *extra)
    if code:
        raise ClientUpdateError(f"page build failed ({code}); fix it and --resume")
    return True


def phase_updates(state: dict[str, Any], args: argparse.Namespace) -> bool:
    code = run_module("scripts.webui.updates.build_updates",
                      "--previous-export-root", state["archiveRoot"], "--export-root", state["exportRoot"],
                      "--refresh-previous-export-baseline", "--prune-previous-export-untracked")
    if code:
        raise ClientUpdateError(f"Updates build failed ({code}); fix it and --resume")
    return True


def phase_trim(state: dict[str, Any], args: argparse.Namespace) -> bool:
    """Keep only the archive's game data: ``game/``, ``raw/`` and the layout marker.

    ``meta/`` holds indexes, asset maps, provenance and evidence that each
    export rebuilds from the installed client; Updates compares game data
    only, so the archived copy serves nothing once the new export is built.
    """
    archive = Path(state["archiveRoot"])
    if (archive / "meta").is_dir():
        shutil.rmtree(archive / "meta")
        log("archive meta/: removed (Updates compares game data only)")
    log(f"done. The old export is {archive}; point ENDFIELD_PREVIOUS_EXPORT_ROOT at it for later Updates runs.")
    return True


RUNNERS = {"plan": phase_plan, "archive": phase_archive, "extract": phase_extract, "verify": phase_verify,
           "pages": phase_pages, "updates": phase_updates, "trim": phase_trim}
# Phases that touch the export or the archive run under the export's workflow
# lock; extract and pages run export.py, which takes the same lock itself.
LOCKED = {"archive", "verify", "trim"}


def rollback(state: dict[str, Any]) -> int:
    done = state.get("done", [])
    if "pages" in done or state.get("current") in {"pages", "updates", "trim"}:
        log("pages were already built from the new export; rollback is no longer available")
        return 1
    export_root, archive = Path(state["exportRoot"]), Path(state["archiveRoot"])
    if not archive.is_dir():
        log("nothing to roll back: the export was never archived")
        STATE_PATH.unlink()
        return 0
    with exclusive_workflow_lock(export_root, state_root=sync_root(export_root)):
        if export_root.exists():
            log(f"removing the new export {export_root}")
            shutil.rmtree(export_root)
        archive.rename(export_root)
    STATE_PATH.unlink()
    log(f"restored {export_root}")
    return 0


def default_label(export_root: Path) -> str:
    summary = ExportLayout(export_root).export_summary_path
    stamp = datetime.fromtimestamp(summary.stat().st_mtime)
    return stamp.strftime("%Y%m%d")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", help="archive suffix: <export>_<label> (default: the old export's date)")
    parser.add_argument("--pages", nargs="+", default=[], help="pages to refresh (default: every page)")
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--animestudio", type=Path)
    parser.add_argument("--plan-only", action="store_true", help="stop after the plan")
    parser.add_argument("--stop-after", choices=PHASES, help="stop after this phase (resume later)")
    parser.add_argument("--force", action="store_true", help="refresh even when the plan finds no change")
    parser.add_argument("--accept-unexpected", action="store_true",
                        help="continue past changes the plan did not predict")
    parser.add_argument("--resume", action="store_true", help="continue the recorded run")
    parser.add_argument("--rollback", action="store_true",
                        help="before pages are built: delete the new export and restore the archive")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except (ClientUpdateError, ExportLayoutError, ValueError) as exc:
        log(str(exc))
        return 1


def run(args: argparse.Namespace) -> int:
    state = load_state()
    if args.rollback:
        if state is None:
            log("no client update in progress")
            return 1
        return rollback(state)
    if args.resume:
        if state is None:
            log("no client update in progress to resume")
            return 1
    else:
        if state is not None and not args.plan_only:
            log(f"a client update is in progress ({STATE_PATH}); --resume or --rollback it first")
            return 1
        export_root = (args.export_root or configured_export_root()).resolve()
        label = args.label or default_label(export_root)
        archive = export_root.with_name(f"{export_root.name}_{label}")
        if archive.exists():
            log(f"archive path already exists: {archive}; pass another --label")
            return 1
        state = {
            "schema": SCHEMA, "label": label, "done": [],
            "pages": list(resolve_pages(args.pages)),
            "exportRoot": str(export_root), "archiveRoot": str(archive),
            "gameRoot": str((args.game_root or resolve_installed_game_data_root()).resolve()),
            "animestudio": str((args.animestudio or configured_animestudio_cli()).resolve()),
            "reportDir": str(REPORT_ROOT / label),
        }
    export_root = Path(state["exportRoot"])
    try:
        for phase in PHASES:
            if phase in state["done"]:
                continue
            state["current"] = phase
            if phase != "plan" or not args.plan_only:
                save_state(state)
            log(f"=== {phase} ===")
            if phase in LOCKED:
                with exclusive_workflow_lock(export_root, state_root=sync_root(export_root)):
                    proceed = RUNNERS[phase](state, args)
            else:
                proceed = RUNNERS[phase](state, args)
            if not proceed:
                STATE_PATH.unlink(missing_ok=True)
                return 0
            if args.plan_only:
                return 0
            state["done"].append(phase)
            state["current"] = None
            save_state(state)
            if args.stop_after == phase:
                log(f"stopped after {phase}; continue with --resume")
                return 0
    except (ClientUpdateError, package_diff.PackageDiffError, OSError, sqlite3.Error) as exc:
        log(f"stopped in {state.get('current')}: {exc}")
        return 1
    STATE_PATH.unlink(missing_ok=True)
    write_json(Path(state["reportDir"]) / "state.json", state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
