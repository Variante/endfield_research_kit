#!/usr/bin/env python3
"""Build Endfield WebUI updates from logical installed-game VFS patches.

No-change checks are read-only.  Changed builds clone the current export into a
staging tree, selectively refresh directly dumpable VFS files, refresh broader
asset/audio scopes only when their source blocks changed, validate the result,
archive the previous export, publish the new current export, rebuild WebUI data,
and finally generate the Updates feed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing, contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "scripts" / "track_game_data_updates.py"
FRESHNESS_CHECK = ROOT / "scripts" / "verify_export_freshness.py"
EXPORTER = ROOT / "scripts" / "export_full_from_game.py"
BUILD_AUDIO = ROOT / "scripts" / "build_audio.py"
EXPORT_WRAPPER = ROOT / "export.bat"
UPDATES_WRAPPER = ROOT / "build_updates.bat"
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_PREVIOUS_EXPORT_ROOT = ROOT / "export_1d2"
DEFAULT_BASELINE_REL = Path("recovered/AnimeStudio-cli/source_update_snapshot.sqlite3")
DEFAULT_OPERATIONAL_ROOT = ROOT / ".game-data-tracker" / "original-data"
DEFAULT_PLAN = ROOT / "reports" / "updates" / "original-game-data-change-plan.json"
DEFAULT_ANIMESTUDIO = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
ANIMESTUDIO_ASSET_MODES = {
    "focused": "focused",
    "default": "default",
    "debug": "debug",
}
WEBUI_ASSET_FLAGS = {
    "focused": "--focused-assets",
    "default": "--default-assets",
    "debug": "--debug-assets",
}
DIRECT_STRUCTURED_BLOCKS = frozenset(
    {"table", "jsondata", "video", "auditvideo", "lua"}
)
AUDIO_BLOCKS = frozenset(
    {
        "initaudio",
        "auditaudio",
        "audio",
        "hotfixaudio",
        "audiochinese",
        "audioenglish",
        "audiojapanese",
        "audiokorean",
    }
)
IGNORED_WEBUI_BLOCKS: frozenset[str] = frozenset()
PATCH_REGEX_LIMIT = 6000


class WorkflowError(RuntimeError):
    """Expected user-facing workflow failure."""


def _run(command: list[str]) -> None:
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise WorkflowError(f"command failed: {exc}") from exc


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(raw_temporary)
    try:
        shutil.copyfile(source, temporary)
        with temporary.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _copy_atomic_no_replace(source: Path, destination: Path) -> None:
    """Publish a file atomically while refusing a concurrently-created target."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(raw_temporary)
    try:
        shutil.copyfile(source, temporary)
        with temporary.open("rb+") as stream:
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise WorkflowError(f"refusing to overwrite existing file: {destination}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(raw_temporary)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _exclusive_lock(operational_root: Path) -> Iterator[None]:
    operational_root.mkdir(parents=True, exist_ok=True)
    lock = operational_root / "workflow.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise WorkflowError(
            f"another game-data update workflow is active, or left a stale lock: {lock}"
        ) from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        lock.unlink(missing_ok=True)


def _baseline_path(export_root: Path, override: Path | None) -> Path:
    return (override if override is not None else export_root / DEFAULT_BASELINE_REL).resolve()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _require_distinct_paths(**paths: Path) -> None:
    resolved = {name: path.resolve() for name, path in paths.items()}
    names = list(resolved)
    for index, left_name in enumerate(names):
        left = resolved[left_name]
        for right_name in names[index + 1 :]:
            right = resolved[right_name]
            same = os.path.normcase(str(left)) == os.path.normcase(str(right))
            if not same and left.exists() and right.exists():
                try:
                    same = os.path.samefile(left, right)
                except OSError:
                    same = False
            if same:
                raise WorkflowError(
                    f"{left_name} and {right_name} must be different paths: {left}"
                )


def _verify_freshness(game_root: Path, export_root: Path) -> None:
    _run(
        [
            sys.executable,
            str(FRESHNESS_CHECK),
            "--game-root",
            str(game_root),
            "--output",
            str(export_root),
        ]
    )


def _tracker_input_args(args: argparse.Namespace) -> list[str]:
    return [
        "--game-root",
        str(args.game_root.resolve()),
        "--animestudio",
        str(args.animestudio.resolve()),
    ]


def initialize_current_baseline(args: argparse.Namespace) -> dict[str, Any]:
    game_root = args.game_root.resolve()
    export_root = args.export_root.resolve()
    baseline = _baseline_path(export_root, args.baseline)

    if not game_root.is_dir():
        raise WorkflowError(f"installed game-data root not found: {game_root}")
    if not export_root.is_dir():
        raise WorkflowError(f"current export root not found: {export_root}")
    if baseline.exists():
        raise WorkflowError(f"source baseline already exists: {baseline}")
    operational_root = args.operational_root.resolve()
    if _is_within(operational_root, export_root):
        raise WorkflowError("operational root must be outside the current export root")
    _require_distinct_paths(
        baseline=baseline,
        lock=operational_root / "workflow.lock",
    )

    if not args.skip_freshness_check:
        _verify_freshness(game_root, export_root)

    with _exclusive_lock(operational_root):
        work_parent = ROOT / "tmp" / "updates" / "source_scan"
        work_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="init-", dir=work_parent) as raw_work:
            work = Path(raw_work)
            staged_baseline = work / "baseline.sqlite3"
            _run(
                [
                    sys.executable,
                    str(TRACKER),
                    "snapshot",
                    "--output",
                    str(staged_baseline),
                    *_tracker_input_args(args),
                ]
            )
            if not staged_baseline.is_file():
                raise WorkflowError("baseline initialization did not produce a snapshot")
            if not args.skip_freshness_check:
                # The tracker rejects a game-data mutation during its two VFS scans.
                # Rechecking here also prevents attaching a consistent new-game
                # snapshot to an export that belonged to the previous version.
                _verify_freshness(game_root, export_root)
            _copy_atomic_no_replace(staged_baseline, baseline)

    return {
        "mode": "init-baseline",
        "baseline": str(baseline),
        "exportRoot": str(export_root),
        "baselineInitialized": True,
    }


def check_current_version(args: argparse.Namespace) -> dict[str, Any]:
    game_root = args.game_root.resolve()
    export_root = args.export_root.resolve()
    baseline = _baseline_path(export_root, args.baseline)
    operational_root = args.operational_root.resolve()
    published_plan = args.plan.resolve()

    if not game_root.is_dir():
        raise WorkflowError(f"installed game-data root not found: {game_root}")
    if not baseline.is_file():
        raise WorkflowError(
            f"source baseline not found: {baseline}; run --init-baseline first"
        )
    if _is_within(operational_root, export_root):
        raise WorkflowError("operational root must be outside the current export root")
    if _is_within(published_plan, export_root):
        raise WorkflowError("change plan must be outside the current export root")
    if _is_within(published_plan, operational_root / "candidates"):
        raise WorkflowError("change plan must be outside the candidate snapshot directory")
    _require_distinct_paths(
        baseline=baseline,
        plan=published_plan,
        lock=operational_root / "workflow.lock",
    )

    with _exclusive_lock(operational_root):
        work_parent = ROOT / "tmp" / "updates" / "source_scan"
        work_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="check-", dir=work_parent) as raw_work:
            work = Path(raw_work)
            candidate = work / "candidate.sqlite3"
            plan = work / "plan.json"
            _run(
                [
                    sys.executable,
                    str(TRACKER),
                    "check",
                    "--baseline",
                    str(baseline),
                    "--candidate",
                    str(candidate),
                    "--plan",
                    str(plan),
                    *_tracker_input_args(args),
                ]
            )
            try:
                payload = json.loads(plan.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise WorkflowError(f"unable to read generated change plan: {exc}") from exc

            if not bool(payload.get("logicalChanged")):
                published_plan.unlink(missing_ok=True)
                return {
                    "mode": "check",
                    "logicalChanged": False,
                    "baselineUnchanged": True,
                    "totals": payload.get("totals") or {},
                }

            candidate_id = str((payload.get("candidate") or {}).get("snapshotId") or "").strip()
            if len(candidate_id) != 64 or any(ch not in "0123456789abcdef" for ch in candidate_id):
                raise WorkflowError("change plan has an invalid candidate snapshot ID")
            candidate_digest = _file_sha256(candidate)
            candidate_destination = (
                operational_root
                / "candidates"
                / f"{candidate_id}_{candidate_digest[:12]}.sqlite3"
            )
            _require_distinct_paths(
                baseline=baseline,
                plan=published_plan,
                candidate=candidate_destination,
            )
            _copy_atomic(candidate, candidate_destination)
            payload.setdefault("candidate", {})["path"] = str(candidate_destination)
            _write_json_atomic(published_plan, payload)

    return {
        "mode": "check",
        "logicalChanged": True,
        "baselineUnchanged": True,
        "candidate": str(candidate_destination),
        "plan": str(published_plan),
        "totals": payload.get("totals") or {},
    }


def _normalized_block(value: object) -> str:
    return str(value or "").replace("-", "").replace("_", "").casefold()


def _snapshot_id_from_database(path: Path) -> str:
    try:
        with closing(
            sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        ) as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key='snapshot_id'"
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise WorkflowError(f"invalid source snapshot {path}: {exc}") from exc
    value = str(row[0] if row else "").strip()
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise WorkflowError(f"source snapshot has an invalid ID: {path}")
    return value


def _logical_diff_rows(baseline: Path, candidate: Path) -> list[dict[str, str]]:
    query = """
        SELECT new.source, new.block, new.logical_path, 'added'
        FROM candidate.files AS new
        LEFT JOIN files AS old USING (source, block, logical_path)
        WHERE old.logical_path IS NULL
        UNION ALL
        SELECT old.source, old.block, old.logical_path, 'deleted'
        FROM files AS old
        LEFT JOIN candidate.files AS new USING (source, block, logical_path)
        WHERE new.logical_path IS NULL
        UNION ALL
        SELECT new.source, new.block, new.logical_path, 'modified'
        FROM candidate.files AS new
        JOIN files AS old USING (source, block, logical_path)
        WHERE old.data_md5 != new.data_md5 OR old.length != new.length
        ORDER BY 1, 2, 3, 4
    """
    try:
        with closing(
            sqlite3.connect(f"file:{baseline.resolve()}?mode=ro", uri=True)
        ) as connection:
            connection.execute(
                "ATTACH DATABASE ? AS candidate",
                (f"file:{candidate.resolve()}?mode=ro",),
            )
            rows = connection.execute(query).fetchall()
    except sqlite3.DatabaseError as exc:
        raise WorkflowError(f"cannot read logical source diff: {exc}") from exc
    return [
        {
            "source": str(source),
            "block": str(block),
            "logicalPath": str(logical_path),
            "status": str(status),
        }
        for source, block, logical_path, status in rows
    ]


def _structured_output_relative(block: str, logical_path: str) -> Path:
    logical = PurePosixPath(logical_path.replace("\\", "/"))
    normalized_block = _normalized_block(block)
    if normalized_block == "table":
        return Path("Table") / f"{logical.stem}.json"
    if normalized_block == "lua":
        name = logical.as_posix()
        if not name.endswith(".lua"):
            while name.endswith(".lua.enc"):
                name = name[: -len(".lua.enc")]
            name += ".lua"
        return Path("Lua") / Path(*PurePosixPath(name).parts)
    if normalized_block in {"video", "auditvideo"} and logical.suffix.casefold() == ".usm":
        logical = logical.with_suffix(".mp4")
    return Path(*logical.parts)


def _candidate_structured_owners(candidate: Path) -> set[tuple[str, str]]:
    owners: set[tuple[str, str]] = set()
    try:
        with closing(
            sqlite3.connect(f"file:{candidate.resolve()}?mode=ro", uri=True)
        ) as connection:
            with closing(
                connection.execute("SELECT source, block, logical_path FROM files")
            ) as cursor:
                for source, block, logical_path in cursor:
                    if _normalized_block(block) not in DIRECT_STRUCTURED_BLOCKS:
                        continue
                    relative = _structured_output_relative(str(block), str(logical_path))
                    owners.add((str(source).casefold(), relative.as_posix().casefold()))
    except sqlite3.DatabaseError as exc:
        raise WorkflowError(f"cannot build structured output ownership: {exc}") from exc
    return owners


def _regex_batches(paths: list[str]) -> Iterator[str]:
    pieces: list[str] = []
    length = len("^(?:)$")
    for logical_path in paths:
        piece = re.escape(logical_path.replace("\\", "/"))
        added = len(piece) + (1 if pieces else 0)
        if pieces and length + added > PATCH_REGEX_LIMIT:
            yield "^(?:" + "|".join(pieces) + ")$"
            pieces = []
            length = len("^(?:)$")
        pieces.append(piece)
        length += added
    if pieces:
        yield "^(?:" + "|".join(pieces) + ")$"


def _apply_structured_patch(
    args: argparse.Namespace,
    stage_root: Path,
    candidate: Path,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    relevant = [
        row for row in rows if _normalized_block(row["block"]) in DIRECT_STRUCTURED_BLOCKS
    ]
    owners = _candidate_structured_owners(candidate)
    removed: list[str] = []
    for row in relevant:
        if row["status"] != "deleted":
            continue
        relative = _structured_output_relative(row["block"], row["logicalPath"])
        owner_key = (row["source"].casefold(), relative.as_posix().casefold())
        if owner_key in owners:
            continue
        output = stage_root / "structured" / row["source"] / relative
        if output.is_file():
            output.unlink()
            removed.append(f"{row['source']}/{relative.as_posix()}")

    grouped: dict[tuple[str, str], list[str]] = {}
    for row in relevant:
        if row["status"] == "deleted":
            continue
        grouped.setdefault((row["source"], row["block"]), []).append(row["logicalPath"])

    command_count = 0
    for (source, block), logical_paths in sorted(grouped.items()):
        source_root = args.game_root.resolve() / source
        output_root = stage_root / "structured" / source
        output_root.mkdir(parents=True, exist_ok=True)
        for regex in _regex_batches(sorted(logical_paths)):
            command = [
                str(args.animestudio.resolve()),
                "dump",
                "--streaming-assets",
                str(source_root),
                "--output",
                str(output_root),
                "--block-type",
                block,
                "--file-regex",
                regex,
            ]
            if source.casefold() == "persistent":
                command.extend(
                    ["--fallback-assets", str(args.game_root.resolve() / "StreamingAssets")]
                )
            _run(command)
            command_count += 1

    missing: list[str] = []
    for row in relevant:
        if row["status"] == "deleted":
            continue
        relative = _structured_output_relative(row["block"], row["logicalPath"])
        output = stage_root / "structured" / row["source"] / relative
        if not output.is_file():
            missing.append(f"{row['source']}/{row['block']}/{row['logicalPath']}")
    if missing:
        raise WorkflowError(
            "selective structured export did not produce expected outputs: "
            + ", ".join(missing[:10])
        )
    return {
        "changedFiles": len(relevant),
        "deletedOutputs": len(removed),
        "commands": command_count,
        "samples": relevant[:20],
    }


def _patch_scope(rows: list[dict[str, str]]) -> dict[str, Any]:
    blocks = sorted({row["block"] for row in rows}, key=str.casefold)
    normalized = {_normalized_block(block) for block in blocks}
    return {
        "blocks": blocks,
        "structured": any(block in DIRECT_STRUCTURED_BLOCKS for block in normalized),
        "audio": any(block in AUDIO_BLOCKS for block in normalized),
        "animestudio": any(
            block not in DIRECT_STRUCTURED_BLOCKS | AUDIO_BLOCKS | IGNORED_WEBUI_BLOCKS
            for block in normalized
        ),
    }


def _copy_current_export_to_stage(export_root: Path) -> Path:
    raw_stage = tempfile.mkdtemp(
        prefix=f".{export_root.name}.patch-stage-", dir=export_root.parent
    )
    stage = Path(raw_stage)
    try:
        shutil.copytree(export_root, stage, dirs_exist_ok=True, symlinks=True)
    except BaseException:
        _remove_patch_stage(stage, export_root)
        raise
    return stage


def _remove_patch_stage(stage: Path, export_root: Path) -> None:
    resolved_stage = stage.resolve()
    expected_parent = export_root.resolve().parent
    if resolved_stage.parent != expected_parent or not resolved_stage.name.startswith(
        f".{export_root.name}.patch-stage-"
    ):
        raise WorkflowError(f"refusing to remove unexpected patch staging path: {stage}")
    if resolved_stage.exists():
        shutil.rmtree(resolved_stage)


def _prepare_audio_webui(work: Path) -> Path:
    temporary_webui = work / "audio_webui"
    temporary_webui.mkdir(parents=True)
    source_webui = ROOT / "webui"
    overrides = source_webui / "overrides"
    conversations = source_webui / "data" / "lang" / "CN" / "conv"
    if overrides.is_dir():
        shutil.copytree(overrides, temporary_webui / "overrides")
    if not conversations.is_dir():
        raise WorkflowError(f"CN conversation data not found: {conversations}")
    shutil.copytree(conversations, temporary_webui / "data" / "lang" / "CN" / "conv")
    return temporary_webui


def _refresh_patch_scopes(
    args: argparse.Namespace,
    stage: Path,
    scope: Mapping[str, Any],
    work: Path,
) -> None:
    exporter_command = [
        sys.executable,
        str(EXPORTER),
        "--game-root",
        str(args.game_root.resolve()),
        "--output",
        str(stage),
        "--skip-structured",
    ]
    if scope.get("animestudio"):
        exporter_command.extend(
            [
                "--animestudio-scope",
                "all",
                "--animestudio-asset-mode",
                ANIMESTUDIO_ASSET_MODES[args.asset_mode],
                "--animestudio-stages",
                "maps",
                "convert_by_type",
                "json_by_type",
                "--animestudio-jobs",
                str(args.animestudio_jobs),
            ]
        )
    else:
        exporter_command.extend(["--skip-animestudio", "--report-only"])
    _run(exporter_command)

    if scope.get("audio"):
        temporary_webui = _prepare_audio_webui(work)
        _run(
            [
                sys.executable,
                str(BUILD_AUDIO),
                "--game-root",
                str(args.game_root.resolve()),
                "--export-root",
                str(stage),
                "--audio-root",
                str(stage / "structured" / "Audio"),
                "--webui-root",
                str(temporary_webui),
            ]
        )


def _choose_archive_destination(preferred: Path, baseline_snapshot_id: str) -> Path:
    preferred = preferred.resolve()
    if not preferred.exists():
        return preferred
    stem = f"{preferred.name}_{baseline_snapshot_id[:12]}"
    candidate = preferred.with_name(stem)
    counter = 2
    while candidate.exists():
        candidate = preferred.with_name(f"{stem}_{counter}")
        counter += 1
    return candidate


def _validate_candidate_still_current(args: argparse.Namespace, candidate: Path, work: Path) -> None:
    post_scan = work / "post-export-snapshot.sqlite3"
    _run(
        [
            sys.executable,
            str(TRACKER),
            "snapshot",
            "--output",
            str(post_scan),
            *_tracker_input_args(args),
        ]
    )
    if _snapshot_id_from_database(post_scan) != _snapshot_id_from_database(candidate):
        raise WorkflowError(
            "installed logical VFS data changed during patch export; staged output was discarded"
        )


def _run_webui_build(args: argparse.Namespace) -> None:
    asset_flag = WEBUI_ASSET_FLAGS[args.asset_mode]
    _run(
        [
            "cmd.exe",
            "/d",
            "/c",
            str(EXPORT_WRAPPER),
            "--with-assets",
            asset_flag,
            "--game-root",
            str(args.game_root.resolve()),
        ]
    )


def _run_updates_build(args: argparse.Namespace, archive: Path, export_root: Path) -> None:
    _run(
        [
            "cmd.exe",
            "/d",
            "/c",
            str(UPDATES_WRAPPER),
            "--previous-export-root",
            str(archive),
            "--export-root",
            str(export_root),
            "--refresh-previous-export-baseline",
        ]
    )


def _backup_optional_file(path: Path, work: Path) -> Path | None:
    if not path.is_file():
        return None
    backup = work / "published_file_backups" / path.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    return backup


def _restore_optional_files(backups: Mapping[Path, Path | None]) -> None:
    for published, backup in backups.items():
        if backup is None:
            published.unlink(missing_ok=True)
            continue
        published.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, published)


def build_patch_update(args: argparse.Namespace) -> dict[str, Any]:
    operational_root = args.operational_root.resolve()
    journal = operational_root / "patch-transaction.json"
    if journal.exists():
        raise WorkflowError(
            f"unfinished patch transaction requires inspection before retry: {journal}"
        )

    check = check_current_version(args)
    if not check.get("logicalChanged"):
        return {
            **check,
            "mode": "build-patch",
            "exportUpdated": False,
            "updatesPageBuilt": False,
        }

    export_root = args.export_root.resolve()
    expected_export_root = DEFAULT_EXPORT_ROOT.resolve()
    if export_root != expected_export_root:
        raise WorkflowError(
            f"patch apply currently requires the canonical export root {expected_export_root}"
        )
    baseline = _baseline_path(export_root, args.baseline)
    expected_baseline = export_root / DEFAULT_BASELINE_REL
    if baseline != expected_baseline.resolve():
        raise WorkflowError("patch apply requires the baseline stored inside export_full")
    candidate = Path(str(check["candidate"])).resolve()
    preferred_archive = args.previous_export_root.resolve()
    if _is_within(preferred_archive, export_root) or preferred_archive == export_root:
        raise WorkflowError("previous export destination must be outside export_full")
    if os.path.splitdrive(str(preferred_archive))[0].casefold() != os.path.splitdrive(
        str(export_root)
    )[0].casefold():
        raise WorkflowError("previous and current export roots must be on the same volume")

    with _exclusive_lock(operational_root):
        baseline_snapshot_id = _snapshot_id_from_database(baseline)
        plan_payload = json.loads(args.plan.resolve().read_text(encoding="utf-8"))
        if str((plan_payload.get("baseline") or {}).get("snapshotId") or "") != baseline_snapshot_id:
            raise WorkflowError("source baseline changed after detection; rerun the patch build")
        rows = _logical_diff_rows(baseline, candidate)
        if not rows:
            raise WorkflowError("changed plan contains no logical VFS file changes")
        scope = _patch_scope(rows)
        archive = _choose_archive_destination(preferred_archive, baseline_snapshot_id)
        archive.parent.mkdir(parents=True, exist_ok=True)
        _require_distinct_paths(
            current=export_root,
            archive=archive,
            candidate=candidate,
            plan=args.plan.resolve(),
        )

        work_parent = ROOT / "tmp" / "updates" / "patch_build"
        work_parent.mkdir(parents=True, exist_ok=True)
        stage: Path | None = None
        with tempfile.TemporaryDirectory(prefix="build-", dir=work_parent) as raw_work:
            work = Path(raw_work)
            if journal.exists():
                raise WorkflowError(
                    f"unfinished patch transaction requires inspection before retry: {journal}"
                )
            stage = _copy_current_export_to_stage(export_root)
            webui_data = ROOT / "webui" / "data"
            webui_backup = work / "webui_data_backup"
            if webui_data.is_dir():
                shutil.copytree(webui_data, webui_backup)
            published_file_backups: dict[Path, Path | None] = {}
            for summary_name in ("export_full_summary.json", "export_full_summary.md"):
                summary = ROOT / "reports" / "export" / summary_name
                published_file_backups[summary] = _backup_optional_file(summary, work)
            patch_receipt = (
                ROOT / "reports" / "updates" / "vfs-patch-build-latest.json"
            )
            published_file_backups[patch_receipt] = _backup_optional_file(
                patch_receipt, work
            )
            archived = False
            rotated = False
            structured_receipt: dict[str, Any] = {}
            try:
                structured_receipt = _apply_structured_patch(
                    args, stage, candidate, rows
                )
                _refresh_patch_scopes(args, stage, scope, work)
                _validate_candidate_still_current(args, candidate, work)
                _copy_atomic(candidate, stage / DEFAULT_BASELINE_REL)

                journal_payload = {
                    "schemaVersion": 1,
                    "phase": "prepared",
                    "current": str(export_root),
                    "archive": str(archive),
                    "stage": str(stage),
                    "candidate": str(candidate),
                }
                _write_json_atomic(journal, journal_payload)
                export_root.rename(archive)
                archived = True
                journal_payload["phase"] = "archived_previous"
                _write_json_atomic(journal, journal_payload)
                stage.rename(export_root)
                rotated = True
                journal_payload["phase"] = "published_current"
                _write_json_atomic(journal, journal_payload)

                _run(
                    [
                        sys.executable,
                        str(EXPORTER),
                        "--game-root",
                        str(args.game_root.resolve()),
                        "--output",
                        str(export_root),
                        "--skip-structured",
                        "--skip-animestudio",
                        "--report-only",
                    ]
                )
                _run_webui_build(args)
                _run_updates_build(args, archive, export_root)
                receipt = {
                    "schemaVersion": 1,
                    "mode": "build-patch",
                    "logicalChanged": True,
                    "exportUpdated": True,
                    "updatesPageBuilt": True,
                    "baselineAdvanced": True,
                    "archive": str(archive),
                    "current": str(export_root),
                    "candidateSnapshotId": _snapshot_id_from_database(candidate),
                    "totals": check.get("totals") or {},
                    "scope": scope,
                    "structured": structured_receipt,
                }
                _write_json_atomic(patch_receipt, receipt)
                journal_payload["phase"] = "complete"
                _write_json_atomic(journal, journal_payload)
                journal.unlink()
                stage = None
            except BaseException as exc:
                rollback_error: Exception | None = None
                if archived:
                    try:
                        if rotated and export_root.exists():
                            failed_root = operational_root / "failed"
                            failed_root.mkdir(parents=True, exist_ok=True)
                            failed = failed_root / (
                                f"{_snapshot_id_from_database(candidate)[:12]}-{int(time.time())}"
                            )
                            suffix = 2
                            while failed.exists():
                                failed = failed.with_name(f"{failed.name}-{suffix}")
                                suffix += 1
                            export_root.rename(failed)
                        archive.rename(export_root)
                        if webui_backup.exists():
                            if webui_data.exists():
                                shutil.rmtree(webui_data)
                            webui_backup.rename(webui_data)
                        if not rotated and stage is not None and stage.exists():
                            _remove_patch_stage(stage, export_root)
                            stage = None
                        _restore_optional_files(published_file_backups)
                    except Exception as rollback_exc:  # pragma: no cover - catastrophic path
                        rollback_error = rollback_exc
                elif stage is not None and stage.exists():
                    _remove_patch_stage(stage, export_root)
                    stage = None
                    _restore_optional_files(published_file_backups)
                journal.unlink(missing_ok=True)
                if rollback_error is not None:
                    raise WorkflowError(
                        f"patch build failed ({exc}); rollback also failed ({rollback_error})"
                    ) from exc
                raise

        return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--init-baseline",
        "--baseline-current",
        dest="init_baseline",
        action="store_true",
        help="seed the source baseline from only the current installed version and export",
    )
    modes.add_argument(
        "--check",
        action="store_true",
        help="scan and compare without changing the baseline or current export",
    )
    modes.add_argument(
        "--apply",
        action="store_true",
        help=(
            "build and publish a changed-VFS patch, archive the previous export, "
            "rebuild WebUI data, and generate the Updates feed"
        ),
    )
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument(
        "--previous-export-root",
        type=Path,
        default=DEFAULT_PREVIOUS_EXPORT_ROOT,
        help=(
            "preferred archive destination for the previous export; when occupied, "
            "a snapshot-suffixed sibling is created"
        ),
    )
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--animestudio", type=Path, default=DEFAULT_ANIMESTUDIO)
    parser.add_argument("--operational-root", type=Path, default=DEFAULT_OPERATIONAL_ROOT)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument(
        "--asset-mode",
        choices=("focused", "default", "debug"),
        default="default",
        help="AnimeStudio asset scope used when changed VFS blocks affect assets",
    )
    parser.add_argument(
        "--animestudio-jobs",
        type=int,
        default=8,
        help="maximum AnimeStudio workers for an asset-affecting patch",
    )
    parser.add_argument(
        "--skip-freshness-check",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.init_baseline:
            result = initialize_current_baseline(args)
        elif args.apply:
            if args.animestudio_jobs < 1:
                raise WorkflowError("--animestudio-jobs must be at least 1")
            result = build_patch_update(args)
        else:
            result = check_current_version(args)
    except (WorkflowError, OSError, sqlite3.DatabaseError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
