#!/usr/bin/env python3
"""Render and compare the settled-reference phase refinement sweep.

The settled reference gives a phase estimate, but the estimate is only known
to be within a small residual window.  For each selected actor this runner
samples the seven phases ``center +/- 0.6`` at 0.2 second intervals, wrapping
each sample by that actor's loop duration.  Unity is run once per actor, in
the order requested, and the successful render is then ranked against the
settled video frame.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETTLED = (
    PROJECT_ROOT
    / "scratch"
    / "character_recovery"
    / "gameplay_reference"
    / "settled_reference_frames.json"
)
DEFAULT_VISUAL_DELTA = (
    PROJECT_ROOT / "scratch" / "character_recovery" / "visual_delta"
)
SWEEP_ROOT = PROJECT_ROOT.parent / "scratch" / "charinfo_phase_sweep"
DEFAULT_UNITY = Path(r"D:\Program Files\2022.3.62f3\Editor\Unity.exe")
DEFAULT_ACTORS = ("endmin", "chen", "pelica")
UNITY_METHOD = (
    "EndfieldGraphShaderLabEditor.EndfieldRecoveredOverviewPhaseSweep."
    "RenderFromEnvironment"
)
COMPARE_TOOL = Path(__file__).with_name("compare_video_phase_sweep.py")

HALF_WINDOW_SECONDS = 0.6
STEP_SECONDS = 0.2


class SweepError(RuntimeError):
    """A fail-closed settled phase sweep error."""


def _number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SweepError(f"{field} is not numeric: {value!r}") from exc
    if not math.isfinite(result):
        raise SweepError(f"{field} is not finite: {value!r}")
    return result


def wrap_phase(phase_seconds: float, loop_clip_seconds: float) -> float:
    """Wrap a phase into the Unity loop interval ``[0, duration)``."""
    phase = _number(phase_seconds, "phase")
    duration = _number(loop_clip_seconds, "loopClipSeconds")
    if duration <= 0.0:
        raise SweepError(f"loopClipSeconds must be positive, got {duration}")
    wrapped = phase % duration
    # Keep output stable and ensure a value rounded up at the endpoint does
    # not become a duration that Unity would clamp to its final frame.
    wrapped = round(wrapped, 6)
    if wrapped >= duration:
        return 0.0
    return wrapped


def phase_times(
    center_phase_seconds: float,
    loop_clip_seconds: float,
    *,
    half_window: float = HALF_WINDOW_SECONDS,
    step: float = STEP_SECONDS,
) -> list[float]:
    """Return the seven wrapped phase samples around a settled phase."""
    center = _number(center_phase_seconds, "loopPhaseSeconds")
    duration = _number(loop_clip_seconds, "loopClipSeconds")
    window = _number(half_window, "half_window")
    spacing = _number(step, "step")
    if duration <= 0.0:
        raise SweepError(f"loopClipSeconds must be positive, got {duration}")
    if window < 0.0:
        raise SweepError(f"half_window must be non-negative, got {window}")
    if spacing <= 0.0:
        raise SweepError(f"step must be positive, got {spacing}")
    count = int(round((2.0 * window) / spacing))
    if count < 0 or not math.isclose(count * spacing, 2.0 * window):
        raise SweepError("half_window must be an exact multiple of step")
    return [
        wrap_phase(center - window + index * spacing, duration)
        for index in range(count + 1)
    ]


def parse_actors(values: Iterable[str] | None) -> tuple[str, ...]:
    """Parse repeated actor options, preserving order and removing duplicates."""
    raw = values if values is not None else DEFAULT_ACTORS
    actors: list[str] = []
    for value in raw:
        for token in value.split(","):
            actor = token.strip().lower()
            if not actor:
                raise SweepError("actor token must not be empty")
            if actor not in actors:
                actors.append(actor)
    if not actors:
        raise SweepError("at least one actor is required")
    return tuple(actors)


def _settled_rows(path: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SweepError(f"could not read settled references: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SweepError(f"invalid settled references JSON: {path}") from exc
    rows = payload.get("frames")
    if not isinstance(rows, list):
        raise SweepError("settled references JSON has no frames list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("actor"):
            continue
        actor = str(row["actor"]).strip().lower()
        if actor in result:
            raise SweepError(f"duplicate settled reference for actor: {actor}")
        result[actor] = row
    return result


def build_plan(
    settled_path: Path = DEFAULT_SETTLED,
    actors: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Load settled references and build a Unity-ready plan."""
    rows = _settled_rows(settled_path)
    selected = parse_actors(actors)
    missing = [actor for actor in selected if actor not in rows]
    if missing:
        raise SweepError("no settled reference for actor(s): " + ", ".join(missing))

    planned: list[dict[str, Any]] = []
    for actor in selected:
        row = rows[actor]
        actor_directory = str(row.get("actorDirectory") or "").strip()
        clip = str(row.get("loopClip") or "").strip()
        if not actor_directory or not clip:
            raise SweepError(f"{actor}: settled row lacks actorDirectory or loopClip")
        duration = _number(row.get("loopClipSeconds"), f"{actor}.loopClipSeconds")
        center = _number(row.get("loopPhaseSeconds"), f"{actor}.loopPhaseSeconds")
        planned.append(
            {
                "actor": actor,
                "actorDirectory": actor_directory,
                "loopClip": clip,
                "loopClipSeconds": duration,
                "centerPhaseSeconds": center,
                "times": phase_times(center, duration),
            }
        )
    return {
        "schema": "endfield.charinfo.settled-phase-sweeps.v1",
        "reference": str(settled_path.resolve()),
        "halfWindowSeconds": HALF_WINDOW_SECONDS,
        "stepSeconds": STEP_SECONDS,
        "actors": planned,
    }


def unity_command(
    row: dict[str, Any],
    *,
    unity_exe: Path,
    project_path: Path = PROJECT_ROOT,
) -> tuple[list[str], dict[str, str]]:
    """Build one Unity command and its four phase-sweep environment values."""
    times = ",".join(f"{value:.3f}" for value in row["times"])
    environment = {
        "ENDFIELD_PHASE_SWEEP_ACTOR": str(row["actorDirectory"]),
        "ENDFIELD_PHASE_SWEEP_CLIP": str(row["loopClip"]),
        "ENDFIELD_PHASE_SWEEP_TIMES": times,
        "ENDFIELD_PHASE_SWEEP_STEM": str(row["actor"]),
    }
    command = [
        str(unity_exe),
        "-batchmode",
        "-quit",
        "-projectPath",
        str(project_path),
        "-force-d3d12",
        "-executeMethod",
        UNITY_METHOD,
    ]
    return command, environment


def expected_render_paths(row: dict[str, Any]) -> list[Path]:
    """Return the exact files Unity must produce for this invocation."""
    actor = str(row["actor"])
    names = [
        f"{actor}_t{value:.3f}".replace(".", "p") + ".png"
        for value in row["times"]
    ]
    if len(names) != len(set(names)):
        raise SweepError(f"{actor}: phase samples collide after 3-decimal formatting")
    return [SWEEP_ROOT / name for name in names]


def run_plan(
    plan: dict[str, Any],
    *,
    unity_exe: Path,
    project_path: Path = PROJECT_ROOT,
    visual_delta_root: Path = DEFAULT_VISUAL_DELTA,
    dry_run: bool = False,
) -> None:
    """Run Unity and compare each actor sequentially, or print the plan."""
    if not dry_run:
        if not unity_exe.is_file():
            raise SweepError(f"Unity executable not found: {unity_exe}")
        if not COMPARE_TOOL.is_file():
            raise SweepError(f"phase comparison tool not found: {COMPARE_TOOL}")
        visual_delta_root.mkdir(parents=True, exist_ok=True)
        SWEEP_ROOT.mkdir(parents=True, exist_ok=True)

    for row in plan["actors"]:
        actor = row["actor"]
        command, phase_environment = unity_command(
            row, unity_exe=unity_exe, project_path=project_path
        )
        report_path = visual_delta_root / f"{actor}_refine_phase.json"
        print("plan " + actor + ": " + subprocess.list2cmdline(command))
        print("  " + json.dumps(phase_environment, sort_keys=True))
        if dry_run:
            print(f"  compare report: {report_path}")
            continue

        expected_paths = expected_render_paths(row)
        for stale_path in SWEEP_ROOT.glob(f"{actor}_t*.png"):
            stale_path.unlink()

        environment = os.environ.copy()
        environment.update(phase_environment)
        completed = subprocess.run(
            command, cwd=str(project_path), env=environment, check=False
        )
        if completed.returncode != 0:
            raise SweepError(f"Unity sweep failed for {actor}")
        missing = [path.name for path in expected_paths if not path.is_file()]
        unexpected = sorted(
            path.name
            for path in SWEEP_ROOT.glob(f"{actor}_t*.png")
            if path not in expected_paths
        )
        if missing or unexpected:
            raise SweepError(
                f"{actor}: rendered file set mismatch; missing={missing}, "
                f"unexpected={unexpected}"
            )

        compare_command = [
            sys.executable,
            str(COMPARE_TOOL),
            "--actor",
            actor,
            "--stem",
            actor,
            "--settled",
            "--report",
            str(report_path),
        ]
        print("compare " + actor + ": " + subprocess.list2cmdline(compare_command))
        compared = subprocess.run(
            compare_command, cwd=str(PROJECT_ROOT.parent), check=False
        )
        if compared.returncode != 0:
            raise SweepError(f"phase comparison failed for {actor}: {report_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actor",
        action="append",
        dest="actors",
        help="actor token; repeat for multiple actors (default: endmin, chen, pelica)",
    )
    parser.add_argument(
        "--unity-exe",
        type=Path,
        default=Path(os.environ.get("UNITY_EXE", str(DEFAULT_UNITY))),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the commands and plan without starting Unity or comparison",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = build_plan(DEFAULT_SETTLED, parse_actors(args.actors))
        if args.dry_run:
            print(json.dumps(plan, indent=2))
        run_plan(plan, unity_exe=args.unity_exe, dry_run=args.dry_run)
        print(
            f"settled phase sweeps {'planned' if args.dry_run else 'completed'}: "
            f"{len(plan['actors'])} actors"
        )
        return 0
    except SweepError as exc:
        print(f"settled phase sweeps failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
