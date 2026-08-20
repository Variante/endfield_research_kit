"""Build an evidence-backed Character Info overview phase contract.

This helper joins two independently recovered timelines:

* ``video_segment_boundaries.json`` supplies the pinned recording's
  model-swap event and the following segment boundary.
* ``controller_asset_audit.json`` plus the imported ``.anim`` files supply
  the runtime controller's start/transition/loop timing.

The loop boundary is deliberately *composite* evidence.  The recording does
not independently measure the instant at which ``ui_overview_loop`` starts;
that instant is computed from ``video model-swap + runtime entry-to-exit time
+ runtime transition duration``.  In particular, this tool never turns the central-band spike or
the settled reference frame into a video-only loop measurement.

Endminf is fail-closed.  The current recording calls that segment ``endmin``
and gives it ``chr_9000_endmin``; that is not enough to identify the female
``chr_0003_endminf`` asset.  The alias is reported as unresolved rather than
silently being mapped to Endminf.

Typical use from the repository root::

    python unity_endfield_graph_shader_lab/tools/build_overview_phase_contract.py \
        --actors pelica,chen

To write a diagnostic contract containing the unresolved Endminf row while
keeping it inadmissible::

    python unity_endfield_graph_shader_lab/tools/build_overview_phase_contract.py \
        --allow-unresolved

The default inputs are the current priority recovery evidence.  The output is
scratch evidence, not a Unity runtime input; a consumer must require
``admission.ready`` before using an entry.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
DEFAULT_BOUNDARIES = (
    PROJECT_ROOT
    / "scratch"
    / "character_recovery"
    / "gameplay_reference"
    / "video_segment_boundaries.json"
)
DEFAULT_VIDEO = REPO_ROOT / "videos" / "2026-08-15_10-32-32.mkv"
DEFAULT_RUNTIME_CONTRACT = (
    PROJECT_ROOT
    / "scratch"
    / "character_recovery"
    / "overview_controller_native"
    / "controller_asset_audit.json"
)
DEFAULT_ANIMATION_ROOT = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "scratch"
    / "character_recovery"
    / "gameplay_reference"
    / "overview_phase_contracts.json"
)
DEFAULT_ACTORS = ("endminf", "pelica", "chen")

SCHEMA = "endfield.charinfo.overview-phase.v1"
EXPECTED_TEMPLATES = {
    "endminf": "chr_0003_endminf",
    "pelica": "chr_0004_pelica",
    "chen": "chr_0005_chen",
}


class PhaseContractError(RuntimeError):
    """Raised when source evidence is missing or contradictory."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PhaseContractError(f"missing JSON evidence: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PhaseContractError(f"cannot read JSON evidence {path}: {error}") from error
    if not isinstance(value, dict):
        raise PhaseContractError(f"JSON evidence must be an object: {path}")
    return value


def _number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PhaseContractError(f"{label} must be numeric, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise PhaseContractError(f"{label} must be finite, got {value!r}")
    if nonnegative and result < 0:
        raise PhaseContractError(f"{label} must be non-negative, got {value!r}")
    return result


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PhaseContractError(f"{label} must be a non-empty string")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise PhaseContractError(f"cannot hash evidence {path}: {error}") from error
    return digest.hexdigest()


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _repository_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _normalise_actor(actor: str) -> str:
    return actor.strip().lower()


def _unique_requested_actors(actors: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for actor in actors:
        token = _normalise_actor(actor)
        if not token:
            continue
        if token not in EXPECTED_TEMPLATES:
            raise PhaseContractError(
                f"unsupported priority actor {actor!r}; expected "
                f"{', '.join(sorted(EXPECTED_TEMPLATES))}"
            )
        if token not in seen:
            result.append(token)
            seen.add(token)
    if not result:
        raise PhaseContractError("at least one actor is required")
    return tuple(result)


def _boundaries_by_index(boundaries: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = boundaries.get("boundaries")
    if not isinstance(raw, list) or not raw:
        raise PhaseContractError("video boundary manifest has no boundaries list")
    rows: list[dict[str, Any]] = []
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise PhaseContractError(f"video boundary row {index} is not an object")
        rows.append(value)
    try:
        rows.sort(key=lambda row: int(row["index"]))
    except (KeyError, TypeError, ValueError) as error:
        raise PhaseContractError(f"video boundary rows need integer index: {error}") from error
    return rows


def _resolve_video_row(
    boundaries: Mapping[str, Any], actor: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve an exact actor row, refusing the current Endminf alias."""

    rows = _boundaries_by_index(boundaries)
    token = _normalise_actor(actor)
    if token == "endminf":
        # Never consume ``coverage.actorAlias`` as identity evidence.  The
        # current recording's endmin row is visibly compatible with more than
        # one Endmin variant and its template is not chr_0003_endminf.
        exact = [row for row in rows if _normalise_actor(str(row.get("actor", ""))) == token]
        alias = [row for row in rows if _normalise_actor(str(row.get("actor", ""))) == "endmin"]
        if len(exact) != 1 or alias:
            return None, (
                "recording does not provide an unambiguous exact endminf row; "
                "the endmin alias/template cannot prove chr_0003_endminf identity"
            )
        row = exact[0]
        if row.get("templateId") != EXPECTED_TEMPLATES[token]:
            return None, (
                f"endminf row template {row.get('templateId')!r} does not match "
                f"{EXPECTED_TEMPLATES[token]!r}"
            )
        return row, None

    matches = [
        row
        for row in rows
        if _normalise_actor(str(row.get("actor", ""))) == token
    ]
    if len(matches) != 1:
        return None, f"expected one exact video row for {token}, found {len(matches)}"
    row = matches[0]
    expected_template = EXPECTED_TEMPLATES[token]
    if row.get("templateId") != expected_template:
        return None, (
            f"video row for {token} has template {row.get('templateId')!r}, "
            f"expected {expected_template!r}"
        )
    return row, None


def _runtime_rows(runtime: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw = runtime.get("actors")
    if not isinstance(raw, list):
        raise PhaseContractError("runtime controller contract has no actors list")
    result: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise PhaseContractError(f"runtime actor row {index} is not an object")
        token = _normalise_actor(str(value.get("actor_token", "")))
        if not token:
            raise PhaseContractError(f"runtime actor row {index} has no actor_token")
        if token in result:
            raise PhaseContractError(f"duplicate runtime actor token: {token}")
        result[token] = value
    return result


_STOP_TIME_RE = re.compile(r"^\s*m_StopTime:\s*([-+0-9.eE]+)\s*$", re.MULTILINE)


def _animation_directory(animation_root: Path, actor: str) -> Path:
    if not animation_root.is_dir():
        raise PhaseContractError(f"missing animation root: {animation_root}")
    matches = [
        path
        for path in animation_root.iterdir()
        if path.is_dir() and path.name.lower() == actor.lower()
    ]
    if len(matches) != 1:
        raise PhaseContractError(
            f"expected one animation directory for {actor}, found "
            f"{[path.name for path in matches]}"
        )
    directory = matches[0] / "Animations"
    if not directory.is_dir():
        raise PhaseContractError(f"missing Animations directory for {actor}: {directory}")
    return directory


def _animation_duration(animation_root: Path, actor: str, clip: str) -> dict[str, Any]:
    directory = _animation_directory(animation_root, actor)
    path = directory / f"{clip}.anim"
    if not path.is_file():
        raise PhaseContractError(f"missing runtime animation clip: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise PhaseContractError(f"cannot read runtime animation clip {path}: {error}") from error
    matches = _STOP_TIME_RE.findall(text)
    if len(matches) != 1:
        raise PhaseContractError(
            f"expected one m_StopTime in {path}, found {len(matches)}"
        )
    duration = _number(float(matches[0]), f"{path} m_StopTime", nonnegative=True)
    if duration <= 0:
        raise PhaseContractError(f"{path} m_StopTime must be positive")
    return {
        "clip": clip,
        "path": _project_relative(path),
        "sha256": _sha256(path),
        "durationSeconds": duration,
    }


def _runtime_timing(
    runtime_row: Mapping[str, Any], animation_root: Path, actor: str,
    sidecar: Mapping[str, Any] | None = None,
    sidecar_path: Path | None = None,
) -> dict[str, Any]:
    overview = runtime_row.get("main_overview")
    if not isinstance(overview, dict):
        raise PhaseContractError(f"runtime actor {actor} has no main_overview contract")
    start_clip = _required_string(overview.get("start_clip"), f"{actor} start_clip")
    loop_clip = _required_string(overview.get("loop_clip"), f"{actor} loop_clip")
    if sidecar is None:
        start = _animation_duration(animation_root, actor, start_clip)
        loop = _animation_duration(animation_root, actor, loop_clip)
    else:
        # The transparent capture sidecar records the exact source clip
        # durations used by the runtime sampler.  Prefer this recovered
        # runtime contract over reparsing the very large imported YAML clips.
        clip_rows = sidecar.get("clips")
        if sidecar.get("status") != "ok":
            raise PhaseContractError(f"{actor} runtime sidecar status is not ok")
        if _normalise_actor(str(sidecar.get("actor", ""))) != actor:
            raise PhaseContractError(f"{actor} runtime sidecar actor does not match")
        if not isinstance(clip_rows, list):
            raise PhaseContractError(f"{actor} runtime sidecar has no clips list")
        start_row = next(
            (row for row in clip_rows if isinstance(row, dict) and row.get("role") == "ui_overview_start"),
            None,
        )
        loop_row = next(
            (row for row in clip_rows if isinstance(row, dict) and row.get("role") == "ui_overview_loop"),
            None,
        )
        if not isinstance(start_row, dict) or not isinstance(loop_row, dict):
            raise PhaseContractError(f"{actor} runtime sidecar lacks start/loop clip rows")
        if start_row.get("name") != start_clip or loop_row.get("name") != loop_clip:
            raise PhaseContractError(f"{actor} runtime sidecar clip names do not match controller")
        start_duration = _number(start_row.get("duration_seconds"), f"{actor} sidecar start duration", nonnegative=True)
        loop_duration = _number(loop_row.get("duration_seconds"), f"{actor} sidecar loop duration", nonnegative=True)
        if start_duration <= 0 or loop_duration <= 0:
            raise PhaseContractError(f"{actor} runtime sidecar clip durations must be positive")
        start = {
            "clip": start_clip,
            "path": _project_relative(sidecar_path) if sidecar_path else "runtime-sidecar",
            "sha256": _sha256(sidecar_path) if sidecar_path else "",
            "durationSeconds": start_duration,
        }
        loop = {
            "clip": loop_clip,
            "path": _project_relative(sidecar_path) if sidecar_path else "runtime-sidecar",
            "sha256": start["sha256"],
            "durationSeconds": loop_duration,
        }
    start_duration = start["durationSeconds"]
    entry_normalized = _number(
        overview.get("entry_normalized_offset"), f"{actor} entry_normalized_offset"
    )
    destination_normalized = _number(
        overview.get("destination_normalized_offset"),
        f"{actor} destination_normalized_offset",
    )
    if not 0 <= entry_normalized <= 1 or not 0 <= destination_normalized <= 1:
        raise PhaseContractError(f"{actor} entry/destination offsets must be in [0, 1]")
    exit_normalized = _number(
        overview.get("exit_normalized_time"), f"{actor} exit_normalized_time"
    )
    if not 0 < exit_normalized <= 1:
        raise PhaseContractError(
            f"{actor} exit_normalized_time must be in (0, 1], got {exit_normalized}"
        )
    fixed = overview.get("transition_duration_fixed")
    if not isinstance(fixed, bool):
        raise PhaseContractError(f"{actor} transition_duration_fixed must be boolean")
    if sidecar is not None:
        sidecar_exit = _number(
            sidecar.get("controller_exit_normalized_time"),
            f"{actor} sidecar controller_exit_normalized_time",
        )
        if abs(sidecar_exit - exit_normalized) > 1e-5:
            raise PhaseContractError(f"{actor} runtime sidecar exit time does not match controller")
        transition_seconds = _number(
            sidecar.get("controller_transition_seconds"),
            f"{actor} sidecar controller_transition_seconds",
            nonnegative=True,
        )
        # The sidecar is the runtime timing contract; retain the serialized
        # controller value when available for audit, but do not substitute a
        # normalized value for the measured transition seconds.
        transition_value = _number(
            overview.get("transition_duration"), f"{actor} transition_duration", nonnegative=True
        )
    else:
        transition_value = _number(
            overview.get("transition_duration"), f"{actor} transition_duration", nonnegative=True
        )
        transition_seconds = (
            transition_value if fixed else start_duration * transition_value
        )
    normalized_transition_seconds = start_duration * (1.0 - exit_normalized)
    if transition_seconds <= 0 or transition_seconds >= start_duration:
        raise PhaseContractError(
            f"{actor} transition duration {transition_seconds} is outside start clip "
            f"duration {start_duration}"
        )
    # The serialized transition and the serialized exit time are two views of
    # the same controller edge.  Keep a tight but practical tolerance for
    # float serialization (Pelica's fixed-duration edge differs by ~2.5 ms).
    if abs(transition_seconds - normalized_transition_seconds) > 0.02:
        raise PhaseContractError(
            f"{actor} transition/exit mismatch: {transition_seconds:.6f}s vs "
            f"{normalized_transition_seconds:.6f}s"
        )
    controller_source = overview.get("source_json")
    if not isinstance(controller_source, str) or not controller_source:
        raise PhaseContractError(f"{actor} runtime controller has no source_json")
    controller_source_path = Path(controller_source)
    controller_source = (
        _repository_relative(controller_source_path)
        if controller_source_path.is_absolute()
        else controller_source.replace("\\", "/")
    )
    return {
        "characterId": _required_string(
            runtime_row.get("character_id"), f"{actor} character_id"
        ),
        "actorToken": actor,
        "controllerName": _required_string(
            overview.get("controller_name"), f"{actor} controller_name"
        ),
        "sourceJson": controller_source,
        "runtimeSidecar": _project_relative(sidecar_path) if sidecar_path else None,
        "startClip": start,
        "loopClip": loop,
        "entryNormalizedOffset": entry_normalized,
        "destinationNormalizedOffset": destination_normalized,
        "exitNormalizedTime": exit_normalized,
        "transitionDurationValue": transition_value,
        "transitionDurationFixed": fixed,
        "transitionDurationSeconds": transition_seconds,
        "transitionStartNormalizedTime": exit_normalized,
        "normalizedTransitionDurationSeconds": normalized_transition_seconds,
    }


def _video_fingerprint(
    boundaries: Mapping[str, Any], boundaries_path: Path, video_path: Path | None
) -> dict[str, Any]:
    video = boundaries.get("video")
    if not isinstance(video, dict):
        raise PhaseContractError("video boundary manifest has no video fingerprint")
    path = _required_string(video.get("path"), "video.path")
    digest = _required_string(video.get("sha256"), "video.sha256")
    size = video.get("bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise PhaseContractError("video.bytes must be a positive integer")
    verification = "manifest_declaration_only"
    if video_path is not None:
        if not video_path.is_file():
            raise PhaseContractError(f"pinned reference video is missing: {video_path}")
        actual_size = video_path.stat().st_size
        if actual_size != size:
            raise PhaseContractError(
                f"reference video size mismatch: expected {size}, got {actual_size}"
            )
        actual_digest = _sha256(video_path)
        if actual_digest.upper() != digest.upper():
            raise PhaseContractError(
                f"reference video sha256 mismatch: expected {digest}, got {actual_digest}"
            )
        verification = "actual_file_size_and_sha256"
    return {
        "path": path,
        "bytes": size,
        "sha256": digest,
        "verification": verification,
        "boundaryManifest": _project_relative(boundaries_path),
        "boundaryManifestSha256": _sha256(boundaries_path),
    }


def _load_runtime_sidecars(
    paths: Iterable[Path] | Path | None,
) -> dict[str, dict[str, Any]]:
    if paths is None:
        return {}
    if isinstance(paths, Path):
        roots = (paths,)
    else:
        roots = tuple(paths)
    result: dict[str, dict[str, Any]] = {}
    for root in roots:
        if not root.is_dir():
            raise PhaseContractError(f"missing runtime sidecar directory: {root}")
        for sidecar_path in sorted(root.rglob("*_overview_capture.json")):
            sidecar = _read_json(sidecar_path)
            actor = _normalise_actor(str(sidecar.get("actor", "")))
            if not actor:
                raise PhaseContractError(f"runtime sidecar has no actor: {sidecar_path}")
            if actor in result:
                raise PhaseContractError(f"duplicate runtime sidecar actor: {actor}")
            sidecar["_source_path"] = str(sidecar_path)
            result[actor] = sidecar
    return result


def _next_boundary(rows: list[dict[str, Any]], row: Mapping[str, Any]) -> dict[str, Any]:
    current_index = int(row["index"])
    candidates = [candidate for candidate in rows if int(candidate["index"]) > current_index]
    if not candidates:
        raise PhaseContractError(
            f"video row {current_index} has no following model-swap boundary; "
            "loop end is not safely known"
        )
    next_row = candidates[0]
    _number(next_row.get("modelSwapSeconds"), "next modelSwapSeconds", nonnegative=True)
    return next_row


def _entry(
    actor: str,
    video_row: Mapping[str, Any],
    next_row: Mapping[str, Any],
    runtime_row: Mapping[str, Any],
    animation_root: Path,
    sidecar: Mapping[str, Any] | None = None,
    sidecar_path: Path | None = None,
) -> dict[str, Any]:
    runtime = _runtime_timing(runtime_row, animation_root, actor, sidecar, sidecar_path)
    if runtime["characterId"] != EXPECTED_TEMPLATES[actor]:
        raise PhaseContractError(
            f"{actor} runtime character_id {runtime['characterId']!r} does not match "
            f"{EXPECTED_TEMPLATES[actor]!r}"
        )
    model_swap_frame = video_row.get("modelSwapFrame")
    if isinstance(model_swap_frame, bool) or not isinstance(model_swap_frame, int):
        raise PhaseContractError(f"{actor} modelSwapFrame must be an integer")
    model_swap_seconds = _number(
        video_row.get("modelSwapSeconds"), f"{actor} modelSwapSeconds", nonnegative=True
    )
    peak_ratio = _number(
        video_row.get("bandPeakRatio"), f"{actor} bandPeakRatio", nonnegative=True
    )
    next_model_swap_seconds = _number(
        next_row.get("modelSwapSeconds"), f"{actor} next modelSwapSeconds", nonnegative=True
    )
    if next_model_swap_seconds <= model_swap_seconds:
        raise PhaseContractError(
            f"{actor} next model swap {next_model_swap_seconds} is not after "
            f"{model_swap_seconds}"
        )
    start_duration = runtime["startClip"]["durationSeconds"]
    transition_seconds = runtime["transitionDurationSeconds"]
    entry_normalized = runtime["entryNormalizedOffset"]
    exit_normalized = runtime["exitNormalizedTime"]
    if exit_normalized < entry_normalized:
        raise PhaseContractError(
            f"{actor} exit time {exit_normalized} precedes entry offset {entry_normalized}"
        )
    transition_start = model_swap_seconds + (
        exit_normalized - entry_normalized
    ) * start_duration
    loop_start = transition_start + transition_seconds
    if loop_start >= next_model_swap_seconds:
        raise PhaseContractError(
            f"{actor} runtime loop starts at {loop_start:.6f}s after next "
            f"model swap {next_model_swap_seconds:.6f}s"
        )
    loop_window = next_model_swap_seconds - loop_start
    loop_duration = runtime["loopClip"]["durationSeconds"]
    loop_cycles = math.floor(loop_window / loop_duration)
    if loop_cycles < 1:
        raise PhaseContractError(
            f"{actor} has less than one runtime loop cycle in the video window: "
            f"{loop_window:.6f}s / {loop_duration:.6f}s"
        )
    return {
        "actor": actor,
        "identity": {
            "videoActor": video_row.get("actor"),
            "videoTemplateId": video_row.get("templateId"),
            "runtimeActorToken": actor,
            "runtimeCharacterId": runtime["characterId"],
            "expectedTemplateId": EXPECTED_TEMPLATES[actor],
            "identityEvidence": "exact video actor/template and exact runtime actor/character contract",
        },
        "videoBoundary": {
            "segmentIndex": video_row.get("index"),
            "modelSwapFrame": model_swap_frame,
            "modelSwapSeconds": model_swap_seconds,
            "bandPeakRatio": peak_ratio,
            "nextSegmentIndex": next_row.get("index"),
            "nextModelSwapSeconds": next_model_swap_seconds,
        },
        "runtimeTiming": runtime,
        "phaseEvidence": {
            "evidenceClass": "composite_video_model_swap_plus_runtime_controller",
            "videoAnchor": "modelSwapFrame/bandPeak from the pinned recording",
            "runtimeAnchor": "imported clip duration plus recovered entry, exit, and transition values",
            "loopBoundaryMethod": (
                "video modelSwapSeconds + (exitNormalizedTime - "
                "entryNormalizedOffset) * startClip.durationSeconds + "
                "transitionDurationSeconds"
            ),
            "videoOnlyLoopMeasurement": "not_claimed",
            "identityAliasPolicy": "endmin alias is never accepted as endminf identity",
        },
        "phases": [
            {
                "role": "ui_overview_start",
                "startSeconds": model_swap_seconds,
                "endSeconds": transition_start,
                "durationSeconds": transition_start - model_swap_seconds,
                "clip": runtime["startClip"]["clip"],
                "timingSource": "runtime controller exit normalized time",
            },
            {
                "role": "ui_overview_transition",
                "startSeconds": transition_start,
                "endSeconds": loop_start,
                "durationSeconds": transition_seconds,
                "clip": f"{runtime['startClip']['clip']}->{runtime['loopClip']['clip']}",
                "timingSource": "runtime controller transition",
            },
            {
                "role": "ui_overview_loop",
                "startSeconds": loop_start,
                "endSeconds": next_model_swap_seconds,
                "durationSeconds": loop_window,
                "clip": runtime["loopClip"]["clip"],
                "runtimeClipDurationSeconds": loop_duration,
                "destinationNormalizedOffset": runtime["destinationNormalizedOffset"],
                "completeRuntimePeriods": loop_cycles,
                "timingSource": "composite; runtime loop period plus video segment end",
            },
        ],
    }


def build_contract(
    boundaries_path: Path = DEFAULT_BOUNDARIES,
    runtime_contract_path: Path = DEFAULT_RUNTIME_CONTRACT,
    animation_root: Path = DEFAULT_ANIMATION_ROOT,
    actors: Iterable[str] = DEFAULT_ACTORS,
    *,
    allow_unresolved: bool = False,
    runtime_sidecars_path: Iterable[Path] | Path | None = None,
    video_path: Path | None = None,
) -> dict[str, Any]:
    """Build the contract without writing it.

    By default any unresolved actor is fatal.  ``allow_unresolved`` is only
    for producing a diagnostic report; the returned contract is explicitly
    inadmissible whenever it contains unresolved evidence.
    """

    boundaries_path = Path(boundaries_path)
    runtime_contract_path = Path(runtime_contract_path)
    animation_root = Path(animation_root)
    requested = _unique_requested_actors(actors)
    boundaries = _read_json(boundaries_path)
    runtime_contract = _read_json(runtime_contract_path)
    rows = _boundaries_by_index(boundaries)
    runtime_rows = _runtime_rows(runtime_contract)
    sidecars = _load_runtime_sidecars(runtime_sidecars_path)
    video = _video_fingerprint(boundaries, boundaries_path, video_path)
    entries: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    for actor in requested:
        video_row, reason = _resolve_video_row(boundaries, actor)
        if video_row is None:
            unresolved.append({"actor": actor, "reason": reason or "unresolved video identity"})
            continue
        runtime_row = runtime_rows.get(actor)
        if runtime_row is None:
            unresolved.append({"actor": actor, "reason": "missing exact runtime actor contract"})
            continue
        try:
            next_row = _next_boundary(rows, video_row)
            sidecar = sidecars.get(actor)
            entries.append(
                _entry(
                    actor,
                    video_row,
                    next_row,
                    runtime_row,
                    animation_root,
                    sidecar,
                    Path(sidecar["_source_path"]) if sidecar else None,
                )
            )
        except PhaseContractError as error:
            unresolved.append({"actor": actor, "reason": str(error)})
    if unresolved and not allow_unresolved:
        first = unresolved[0]
        raise PhaseContractError(f"{first['actor']}: {first['reason']}")
    ready = not unresolved
    return {
        "schema": SCHEMA,
        "boundary": "video_model_swap_plus_runtime_controller",
        "status": "ready" if ready else "incomplete_unresolved_evidence",
        "admission": {
            "ready": ready,
            "reason": "all requested actors have exact composite evidence"
            if ready
            else "one or more requested actors lack exact identity/timing evidence",
        },
        "requestedActors": list(requested),
        "evidencePolicy": {
            "phaseBoundary": "composite_video_model_swap_plus_runtime_controller",
            "videoOnlyLoopMeasurement": "not_claimed",
            "endminfIdentity": "requires exact video actor endminf and template chr_0003_endminf; endmin alias is rejected",
            "consumerGate": "require admission.ready == true",
        },
        "video": video,
        "runtimeControllerContract": {
            "path": _project_relative(runtime_contract_path),
            "sha256": _sha256(runtime_contract_path),
        },
        "entries": entries,
        "unresolved": unresolved,
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boundaries", type=Path, default=DEFAULT_BOUNDARIES)
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument("--runtime-contract", type=Path, default=DEFAULT_RUNTIME_CONTRACT)
    parser.add_argument(
        "--runtime-sidecars",
        type=Path,
        action="append",
        default=None,
        help="runtime capture sidecar root; may be repeated",
    )
    parser.add_argument("--animation-root", type=Path, default=DEFAULT_ANIMATION_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--actors",
        default=",".join(DEFAULT_ACTORS),
        help="comma-separated priority actor tokens (default: endminf,pelica,chen)",
    )
    parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="write an explicitly inadmissible diagnostic contract for unresolved actors",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare the generated contract to --output instead of writing it",
    )
    args = parser.parse_args(argv)
    try:
        contract = build_contract(
            args.boundaries,
            args.runtime_contract,
            args.animation_root,
            args.actors.split(","),
            allow_unresolved=args.allow_unresolved,
            runtime_sidecars_path=args.runtime_sidecars,
            video_path=args.video,
        )
    except PhaseContractError as error:
        print(f"overview phase contract failed: {error}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file():
            print(f"missing contract: {args.output}", file=sys.stderr)
            return 2
        existing = _read_json(args.output)
        if existing != contract:
            print("overview phase contract differs from source evidence", file=sys.stderr)
            return 1
        print(f"overview phase contract matches: {len(contract['entries'])} actors")
        return 0
    _write_json(args.output, contract)
    print(f"wrote {_project_relative(args.output)}")
    print(f"  status: {contract['status']}")
    print(f"  entries: {len(contract['entries'])}, unresolved: {len(contract['unresolved'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
