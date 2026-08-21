"""Extract and validate Endminf's exact actor overview AnimationClip.

This is deliberately narrower than the external UI-effect extraction.  The
input identity is taken from the playback-closure report and is joined to the
AssetMap and CABMap by source, source offset, signed PathID, and Unity type.
Name is checked as an additional identity field; it is never used as a
fallback selector.  A successful run leaves a terminal stage stamp only after
the AnimeStudio object-index sidecar, source freshness, and clip JSON have all
passed their contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.audit_generic_actor_animations import parse_cab_map
from endfield_asset_map_filter import iter_asset_entries


TARGET_NAME = "A_actor_endminf_ui_overview_02"
TARGET_TYPE = "AnimationClip"
DEFAULT_CLOSURE = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
    / "Endminf"
    / "ExternalUiEffects"
    / "endminf_animator_playback_closure.json"
)
DEFAULT_ASSET_MAP = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "maps"
    / "endfield_streamingassets_assets.json"
)
DEFAULT_CAB_MAP = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Maps"
    / "endfield_streamingassets_assets.bin"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "Temp" / "Codex" / "endminf_actor_overview_02_exact_stage"
ANIMESTUDIO_CLI = (
    REPO_ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
U64_MASK = (1 << 64) - 1
STAGE_SCHEMA = "endfield.endminf.actor-animation-clip-extraction.v1"


class ExtractionError(RuntimeError):
    """Raised when exact source or output evidence cannot be established."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"JSON is missing or malformed: {path}: {exc}") from exc


def _normal_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").rstrip("/").casefold()


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ExtractionError(f"cannot hash file: {path}: {exc}") from exc
    return digest.hexdigest()


def _snapshot(path: Path, *, with_hash: bool = False) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError as exc:
        raise ExtractionError(f"installed source or tool is missing: {path}") from exc
    if not path.is_file():
        raise ExtractionError(f"expected a file, got: {path}")
    result: dict[str, Any] = {
        "path": str(path.resolve()).replace("\\", "/"),
        "bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }
    if with_hash:
        result["sha256"] = _sha256(path)
    return result


def _unsigned_hex(path_id: int) -> str:
    return f"{int(path_id) & U64_MASK:016X}"


def _find_dicts(value: Any, predicate: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if predicate(value):
            yield value
        for child in value.values():
            yield from _find_dicts(child, predicate)
    elif isinstance(value, list):
        for child in value:
            yield from _find_dicts(child, predicate)


def _target_from_closure(closure_path: Path) -> dict[str, Any]:
    closure = _json(closure_path)
    if not isinstance(closure, dict):
        raise ExtractionError("playback closure is not an object")
    missing = [
        row
        for row in closure.get("missingArtifacts") or []
        if isinstance(row, dict)
        and row.get("kind") == TARGET_TYPE
        and row.get("name") == TARGET_NAME
    ]
    if len(missing) != 1:
        raise ExtractionError(
            f"playback closure must contain exactly one missing {TARGET_NAME} artifact; found {len(missing)}"
        )
    missing_row = missing[0]
    try:
        path_id = int(missing_row["pathId"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ExtractionError("closure target PathID is malformed") from exc
    cab = str(missing_row.get("cab") or "")
    if not cab or not isinstance(missing_row.get("mismatchedCandidates"), list):
        raise ExtractionError("closure target lacks exact CAB/mismatch evidence")
    if missing_row["mismatchedCandidates"]:
        raise ExtractionError("closure target has mismatched artifact candidates")

    candidates = list(
        _find_dicts(
            closure,
            lambda row: (
                row.get("Name") == TARGET_NAME
                and row.get("Type") == TARGET_TYPE
                and int(row.get("PathID") or 0) == path_id
                and "Source" in row
                and "Offset" in row
            ),
        )
    )
    identities = {
        (
            str(row.get("Name") or ""),
            _normal_path(row.get("Source")),
            int(row.get("PathID")),
            str(row.get("Type") or ""),
            int(row.get("Offset")),
            str(row.get("Container") or ""),
        )
        for row in candidates
    }
    if len(identities) != 1:
        raise ExtractionError(
            f"closure target has {len(identities)} conflicting AssetMap identities"
        )
    name, source, identity_path_id, entry_type, offset, container = next(iter(identities))
    if identity_path_id != path_id or entry_type != TARGET_TYPE or name != TARGET_NAME:
        raise ExtractionError("closure target identity drifted")

    # Capture the closure's expected physical source snapshot when available.
    source_records = [
        row
        for row in _find_dicts(
            closure,
            lambda row: (
                str(row.get("cab") or "").casefold() == cab.casefold()
                and _normal_path(row.get("source")) == source
                and int(row.get("sourceOffset") or -1) == offset
            ),
        )
        if isinstance(row.get("sourceSnapshot"), dict)
    ]
    snapshots = {
        (
            int(row["sourceSnapshot"].get("bytes")),
            int(row["sourceSnapshot"].get("mtime_ns")),
        )
        for row in source_records
        if row["sourceSnapshot"].get("bytes") is not None
        and row["sourceSnapshot"].get("mtime_ns") is not None
    }
    if len(snapshots) > 1:
        raise ExtractionError("closure has conflicting physical source snapshots")
    return {
        "name": name,
        "source": source,
        "sourceRaw": next(row.get("Source") for row in candidates),
        "pathId": path_id,
        "type": entry_type,
        "offset": offset,
        "container": container,
        "cab": cab,
        "expectedSourceSnapshot": (
            {"bytes": next(iter(snapshots))[0], "mtime_ns": next(iter(snapshots))[1]}
            if snapshots
            else None
        ),
        "closure": _relative(closure_path),
    }


def _asset_map_row(asset_map_path: Path, target: dict[str, Any]) -> dict[str, Any]:
    if not asset_map_path.is_file():
        raise ExtractionError(f"AssetMap is missing: {asset_map_path}")
    matches: list[dict[str, Any]] = []
    for row in iter_asset_entries(asset_map_path):
        if (
            str(row.get("Name") or "") == target["name"]
            and str(row.get("Type") or "") == target["type"]
            and int(row.get("PathID") or 0) == target["pathId"]
            and int(row.get("Offset") or -1) == target["offset"]
            and _normal_path(row.get("Source")) == target["source"]
        ):
            matches.append(row)
    if len(matches) != 1:
        raise ExtractionError(
            f"AssetMap exact identity must resolve once, found {len(matches)}: {target['name']}"
        )
    row = dict(matches[0])
    if str(row.get("Container") or "") != target["container"]:
        raise ExtractionError("AssetMap exact target container differs from closure")
    return row


def _cab_row(cab_map_path: Path, target: dict[str, Any]) -> dict[str, Any]:
    if not cab_map_path.is_file():
        raise ExtractionError(f"CABMap is missing: {cab_map_path}")
    try:
        records = list(parse_cab_map(cab_map_path, "StreamingAssets"))
    except (OSError, EOFError, ValueError) as exc:
        raise ExtractionError(f"cannot parse CABMap {cab_map_path}: {exc}") from exc
    rows = [
        record
        for record in records
        if str(record.cab).casefold() == target["cab"].casefold()
        and int(record.offset) == target["offset"]
        and _normal_path(record.source) == target["source"]
    ]
    if len(rows) != 1:
        raise ExtractionError(
            f"CABMap exact CAB/source/offset must resolve once, found {len(rows)}: {target['cab']}"
        )
    row = rows[0]
    return {
        "cab": str(row.cab),
        "assetRoot": str(row.asset_root),
        "source": str(row.source),
        "sourceOffset": int(row.offset),
        "relativePath": str(row.relative_path),
        "baseFolder": str(row.base_folder),
        "dependencies": [str(value) for value in row.dependencies],
    }


def _finite_number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _clip_metrics(value: dict[str, Any]) -> dict[str, Any]:
    name = str(value.get("m_Name") or value.get("Name") or "")
    if name != TARGET_NAME:
        raise ExtractionError(f"AnimationClip JSON name mismatch: {name!r}")
    sample_rate = _finite_number(value.get("m_SampleRate"))
    muscle = value.get("m_MuscleClip")
    stop_time = _finite_number(muscle.get("m_StopTime")) if isinstance(muscle, dict) else None
    if sample_rate is None or sample_rate <= 0:
        raise ExtractionError("AnimationClip has no positive finite m_SampleRate")
    if stop_time is None or stop_time <= 0:
        raise ExtractionError("AnimationClip has no positive finite m_MuscleClip.m_StopTime")
    binding_constant = value.get("m_ClipBindingConstant")
    if not isinstance(binding_constant, dict):
        raise ExtractionError("AnimationClip lacks m_ClipBindingConstant")
    generic = binding_constant.get("genericBindings")
    pptr_mapping = binding_constant.get("pptrCurveMapping")
    if not isinstance(generic, list) or not isinstance(pptr_mapping, list):
        raise ExtractionError("AnimationClip binding arrays are malformed")
    curve_keys = (
        "m_RotationCurves",
        "m_CompressedRotationCurves",
        "m_EulerCurves",
        "m_PositionCurves",
        "m_ScaleCurves",
        "m_FloatCurves",
        "m_PPtrCurves",
    )
    curves: dict[str, int] = {}
    for key in curve_keys:
        rows = value.get(key)
        if not isinstance(rows, list):
            raise ExtractionError(f"AnimationClip curve array is malformed: {key}")
        curves[key] = len(rows)
    acl = value.get("m_AclCompressedBuffer")
    acl_count = acl.get("FloatCurveCount") if isinstance(acl, dict) else None
    if acl_count is not None and (not isinstance(acl_count, int) or acl_count < 0):
        raise ExtractionError("AnimationClip ACL FloatCurveCount is malformed")
    return {
        "name": name,
        "sampleRate": sample_rate,
        "lengthSeconds": stop_time,
        "loopTime": value.get("m_MuscleClip", {}).get("m_LoopTime"),
        "bindingCounts": {
            "genericBindings": len(generic),
            "pptrCurveMapping": len(pptr_mapping),
            "totalBindingEntries": len(generic) + len(pptr_mapping),
            **curves,
            "aclFloatCurveCount": acl_count,
        },
    }


def _safe_reset(output: Path, *, force: bool) -> None:
    allowed = (PROJECT_ROOT / "Temp" / "Codex").resolve()
    resolved = output.resolve()
    try:
        relative = resolved.relative_to(allowed)
    except ValueError as exc:
        raise ExtractionError(f"output is outside scoped Temp/Codex root: {output}") from exc
    if not relative.parts:
        raise ExtractionError("refusing to clear Temp/Codex itself")
    if not output.exists():
        return
    stamp = output / ".character_import_stage.json"
    if not force:
        raise ExtractionError(f"output already exists; pass --force to replace only {output}")
    if output.is_dir():
        shutil.rmtree(output)
    else:
        output.unlink()


def _load_existing_if_exact(output: Path, expected_identity: dict[str, Any]) -> dict[str, Any] | None:
    stamp_path = output / ".character_import_stage.json"
    if not stamp_path.is_file():
        return None
    stamp = _json(stamp_path)
    identity = stamp.get("identity") if isinstance(stamp, dict) else None
    if identity == expected_identity and stamp.get("status") == "ok":
        return stamp
    raise ExtractionError("existing stage stamp does not match the requested exact identity; use --force")


def _validate_file_snapshot(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    current = _snapshot(path, with_hash="sha256" in expected)
    for key in ("path", "bytes", "mtime_ns", "sha256"):
        if key in expected and current.get(key) != expected.get(key):
            raise ExtractionError(f"stage file provenance is stale for {path}: {key}")
    return current


def _validate_filter_file(path: Path, target: dict[str, Any], expected_row: dict[str, Any]) -> None:
    value = _json(path)
    if not isinstance(value, list) or len(value) != 1 or value[0] != expected_row:
        raise ExtractionError("stage filter_data is not the one exact AssetMap row")
    row = value[0]
    expected = {
        "Name": target["name"],
        "Type": target["type"],
        "PathID": target["pathId"],
        "Offset": target["offset"],
    }
    for key in ("Name", "Type", "PathID", "Offset", "Source"):
        if key == "Source":
            matches = _normal_path(row.get(key)) == target["source"]
        elif key in {"PathID", "Offset"}:
            matches = int(row.get(key) or 0) == expected[key]
        else:
            matches = row.get(key) == expected[key]
        if not matches:
            raise ExtractionError(f"stage filter_data identity drifted at {key}")


def _validate_existing_stage(
    *,
    output: Path,
    identity: dict[str, Any],
    target: dict[str, Any],
    row: dict[str, Any],
    cab: dict[str, Any],
    asset_map_path: Path,
    cab_map_path: Path,
) -> dict[str, Any]:
    stamp_path = output / ".character_import_stage.json"
    stamp = _json(stamp_path)
    if not isinstance(stamp, dict) or stamp.get("schema") != STAGE_SCHEMA or stamp.get("status") != "ok":
        raise ExtractionError("stage stamp is not a terminal successful exact extraction")
    if stamp.get("identity") != identity:
        raise ExtractionError("stage stamp identity differs from the requested exact target")
    current_source = _snapshot(Path(identity["source"]))
    source_freshness = stamp.get("sourceFreshness") or {}
    expected_source = source_freshness.get("expected")
    if source_freshness.get("status") != "validated" or expected_source is None:
        raise ExtractionError("stage source freshness is not validated")
    if current_source.get("bytes") != expected_source.get("bytes") or current_source.get("mtime_ns") != expected_source.get("mtime_ns"):
        raise ExtractionError("stage source provenance is stale")
    filter_record = stamp.get("filterData") or {}
    filter_path = Path(filter_record.get("path") or "")
    _validate_file_snapshot(filter_path, filter_record)
    _validate_filter_file(filter_path, target, row)
    artifact_record = (stamp.get("artifact") or {}).get("path") or {}
    artifact_path = Path(artifact_record.get("path") or "")
    _validate_file_snapshot(artifact_path, artifact_record)
    clip_value = _json(artifact_path)
    if not isinstance(clip_value, dict):
        raise ExtractionError("stage AnimationClip artifact is not an object")
    metrics = _clip_metrics(clip_value)
    if metrics != (stamp.get("artifact") or {}).get("metrics"):
        raise ExtractionError("stage AnimationClip metrics drifted")
    provenance_record = (stamp.get("objectProvenance") or {}).get("path") or {}
    provenance_path = Path(provenance_record.get("path") or "")
    _validate_file_snapshot(provenance_path, provenance_record)
    provenance = _json(provenance_path)
    if not isinstance(provenance, dict) or provenance.get("status") != "ok" or provenance.get("identity") != identity:
        raise ExtractionError("stage object provenance is missing or drifted")
    if provenance != (stamp.get("objectProvenance") or {}).get("value"):
        raise ExtractionError("stage object provenance stamp/file values differ")
    cli_record = stamp.get("cli") or {}
    _validate_file_snapshot(Path(cli_record.get("path") or ""), cli_record)
    log_record = stamp.get("log") or {}
    log_path = Path(log_record.get("path") or "")
    _validate_file_snapshot(log_path, log_record)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\bExport .* error\b|\[Error\]", log_text):
        raise ExtractionError("stage AnimeStudio log contains an export error")
    # Re-join the current maps, so an old stamp cannot mask a changed map.
    if _asset_map_row(asset_map_path, target) != row or _cab_row(cab_map_path, target) != cab:
        raise ExtractionError("stage source-map provenance differs from current maps")
    print(
        f"checked {output}: name={metrics['name']} length={metrics['lengthSeconds']}s "
        f"sampleRate={metrics['sampleRate']} bindings={metrics['bindingCounts']['totalBindingEntries']} "
        "objectProvenance=validated"
    )
    return stamp


def _run_cli(
    *,
    source: Path,
    output: Path,
    filter_path: Path,
    cli_log: Path,
) -> None:
    command = [
        str(ANIMESTUDIO_CLI),
        str(source),
        str(output),
        "--game",
        "ArknightsEndfield",
        "--types",
        "AnimationClip:Both",
        "--export_type",
        "JSON",
        "--group_assets",
        "ByType",
        "--logger_flags",
        "Warning",
        "Error",
        "--filter_data",
        str(filter_path),
    ]
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    cli_log.write_text(
        "COMMAND: " + subprocess.list2cmdline(command) + "\n\n"
        + "STDOUT:\n" + completed.stdout
        + "\nSTDERR:\n" + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise ExtractionError(f"AnimeStudio targeted extraction failed with exit code {completed.returncode}")
    log_text = completed.stdout + "\n" + completed.stderr
    errors = [line for line in log_text.splitlines() if re.search(r"\bExport .* error\b|\[Error\]", line)]
    if errors:
        raise ExtractionError(f"AnimeStudio targeted extraction reported {len(errors)} error log lines")


def extract(
    *,
    closure_path: Path,
    asset_map_path: Path,
    cab_map_path: Path,
    output: Path,
    force: bool,
    dry_run: bool,
    check: bool,
) -> dict[str, Any]:
    if not ANIMESTUDIO_CLI.is_file():
        raise ExtractionError(f"AnimeStudio CLI is missing: {ANIMESTUDIO_CLI}")
    target = _target_from_closure(closure_path)
    row = _asset_map_row(asset_map_path, target)
    cab = _cab_row(cab_map_path, target)
    current_source = Path(str(row["Source"]))
    source_snapshot = _snapshot(current_source)
    expected_source = target.get("expectedSourceSnapshot")
    if expected_source is not None and source_snapshot != {
        "path": source_snapshot["path"],
        "bytes": int(expected_source["bytes"]),
        "mtime_ns": int(expected_source["mtime_ns"]),
    }:
        raise ExtractionError(
            "installed source freshness differs from the playback-closure snapshot: "
            f"{current_source}"
        )
    if str(cab["cab"]).casefold() != target["cab"].casefold():
        raise ExtractionError("CABMap resolved a different CAB than the playback closure")
    identity = {
        "name": target["name"],
        "type": target["type"],
        "pathId": target["pathId"],
        "pathIdHex": _unsigned_hex(target["pathId"]),
        "source": source_snapshot["path"],
        "sourceOffset": target["offset"],
        "cab": cab["cab"],
        "container": target["container"],
    }
    output = output.resolve()
    if check:
        if not output.is_dir():
            raise ExtractionError(f"stage does not exist for --check: {output}")
        return _validate_existing_stage(
            output=output,
            identity=identity,
            target=target,
            row=row,
            cab=cab,
            asset_map_path=asset_map_path,
            cab_map_path=cab_map_path,
        )
    existing = _load_existing_if_exact(output, identity) if output.exists() and not force else None
    if existing is not None:
        print(f"reuse exact actor AnimationClip stage: {output}")
        return existing
    _safe_reset(output, force=force)
    output.mkdir(parents=True, exist_ok=True)
    filters = output / "filters"
    filters.mkdir()
    filter_path = filters / f"endminf_actor_overview_02_001_{Path(current_source).stem}.json"
    filter_path.write_text(json.dumps([row], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cli_log = output / "animestudio.log"
    cli_snapshot = _snapshot(ANIMESTUDIO_CLI, with_hash=True)
    if not dry_run:
        _run_cli(
            source=current_source,
            output=output,
            filter_path=filter_path,
            cli_log=cli_log,
        )
    expected_file = output / "AnimationClip" / f"{TARGET_NAME}_p{_unsigned_hex(target['pathId'])}.json"
    if dry_run:
        report = {
            "schema": STAGE_SCHEMA,
            "status": "planned",
            "identity": identity,
            "sourceFreshness": {"status": "validated", "current": source_snapshot, "expected": expected_source},
            "cabMap": cab,
            "filterData": _relative(filter_path),
            "cli": cli_snapshot,
            "output": _relative(output),
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return report

    if not expected_file.is_file():
        raise ExtractionError(f"targeted extraction did not produce exact AnimationClip JSON: {expected_file}")
    clip_value = _json(expected_file)
    if not isinstance(clip_value, dict):
        raise ExtractionError("AnimationClip JSON is not an object")
    metrics = _clip_metrics(clip_value)
    artifact_snapshot = _snapshot(expected_file, with_hash=True)
    filter_snapshot = _snapshot(filter_path, with_hash=True)
    object_provenance = {
        "schema": "endfield.exact-object-provenance.v1",
        "status": "ok",
        "identity": identity,
        "assetMap": {"path": _relative(asset_map_path), "row": row},
        "cabMap": {"path": _relative(cab_map_path), "row": cab},
        "sourceSnapshot": source_snapshot,
        "filterData": filter_snapshot,
        "artifact": artifact_snapshot,
        "selection": "source+offset+signed PathID+type+name exact join; no name-only fallback",
    }
    object_provenance_path = output / "object_provenance.json"
    object_provenance_path.write_text(
        json.dumps(object_provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    stamp = {
        "schema": STAGE_SCHEMA,
        "status": "ok",
        "identity": identity,
        "sourceFreshness": {
            "status": "validated",
            "current": source_snapshot,
            "expected": expected_source,
        },
        "assetMap": {"path": _relative(asset_map_path), "row": row},
        "cabMap": {"path": _relative(cab_map_path), "row": cab},
        "cli": cli_snapshot,
        "filterData": filter_snapshot,
        "objectProvenance": {
            "path": _snapshot(object_provenance_path, with_hash=True),
            "value": object_provenance,
        },
        "artifact": {"path": artifact_snapshot, "metrics": metrics},
        "log": _snapshot(cli_log, with_hash=True),
        "evidenceBoundary": (
            "one exact AnimationClip selected by closure AssetMap identity and CABMap source/offset; "
            "serialized clip timing/binding evidence only, no actor mount or runtime playback claim"
        ),
    }
    (output / ".character_import_stage.json").write_text(
        json.dumps(stamp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "endminf_actor_overview_02_stage.json").write_text(
        json.dumps(stamp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {output}: name={metrics['name']} length={metrics['lengthSeconds']}s "
        f"sampleRate={metrics['sampleRate']} bindings={metrics['bindingCounts']['totalBindingEntries']} "
        f"objectProvenance=validated"
    )
    return stamp


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", type=Path, default=DEFAULT_CLOSURE)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--cab-map", type=Path, default=DEFAULT_CAB_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true", help="validate an existing exact stage without running AnimeStudio")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        extract(
            closure_path=args.closure,
            asset_map_path=args.asset_map,
            cab_map_path=args.cab_map,
            output=args.output,
            force=args.force,
            dry_run=args.dry_run,
            check=args.check,
        )
        return 0
    except (ExtractionError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
