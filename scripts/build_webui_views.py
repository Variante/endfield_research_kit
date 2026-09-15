"""Build post-Story WebUI views from a declared dependency graph.

The root export wrapper owns extraction, freshness, evidence, and Story. This
runner starts after those inputs are current and keeps every existing builder
as an independently callable command.

Each ``TaskSpec`` declares the tasks it reads output from (``after``). The
scheduler starts any task whose dependencies have all succeeded, bounded by
``--jobs``; a failed task skips everything downstream of it and the run exits
non-zero. Barrier phases are gone: a slow producer only delays its own
consumers, not every builder that happens to be queued behind it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "export"
REPORT_JSON = REPORT_DIR / "webui_build_steps_latest.json"
REPORT_MD = REPORT_DIR / "webui_build_steps_latest.md"


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    environment: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class TaskSpec:
    name: str
    commands: tuple[CommandSpec, ...]
    # Names of the tasks whose published output this task reads. Every edge is
    # justified in `build_tasks`; nothing is listed "to be safe".
    after: tuple[str, ...] = ()


def python_command(
    path: str,
    *args: str,
    environment: tuple[tuple[str, str], ...] = (),
) -> CommandSpec:
    return CommandSpec((sys.executable, str(ROOT / path), *args), environment)


def python_module(
    module: str,
    *args: str,
    environment: tuple[tuple[str, str], ...] = (),
) -> CommandSpec:
    return CommandSpec((sys.executable, "-m", module, *args), environment)


def build_environment(args: argparse.Namespace) -> tuple[tuple[str, str], ...]:
    values = {}
    if args.export_root:
        values["ENDFIELD_EXPORT_ROOT"] = str(args.export_root.resolve())
    if args.game_root:
        values["ENDFIELD_GAME_ROOT"] = str(args.game_root.resolve())
    return tuple(sorted(values.items()))


def build_tasks(args: argparse.Namespace) -> list[TaskSpec]:
    """Return the post-Story build graph.

    Every `after=` edge below names a file one task writes and the next reads.
    Nothing else is ordered; in particular the audio builder, the map preview
    and the source graph no longer wait on each other.
    """
    environment = build_environment(args)

    def command(path: str, *command_args: str) -> CommandSpec:
        return python_command(path, *command_args, environment=environment)

    def module(name: str, *command_args: str) -> CommandSpec:
        return python_module(name, *command_args, environment=environment)

    # The map builder's per-level loop and streaming extractor are independently
    # process-parallel. Both inherit the configured post-Story worker budget;
    # AnimeStudio extraction has already completed before this runner starts.
    map_recovery_jobs = str(args.jobs)

    tasks: list[TaskSpec] = []

    # ---- roots: builders that only read the completed export ----------------

    # Mission Pipeline is a standalone recovery tool now. Keep map recovery
    # in the WebUI build, but do not make the export wrapper run Mission
    # Pipeline's expensive native/story recovery pass.
    # Reads export_full/structured + the AnimeStudio export, both complete
    # before this runner starts, so it has no in-runner dependency.
    tasks.append(
        TaskSpec(
            "map_recovery",
            (module("scripts.build_map_recovery_data", "--jobs", map_recovery_jobs),),
        )
    )

    if args.with_assets:
        # scripts/build_assets.py scans export_full and writes
        # webui/data/assets/{index,story_media}.json. No in-runner input.
        tasks.append(
            TaskSpec(
                "assets",
                (module("scripts.build_assets", "--mode", args.asset_mode),),
            )
        )

    # gameplay_builder/base_data reads export_full structured tables only.
    tasks.append(
        TaskSpec(
            "gameplay",
            (
                module(
                    "scripts.build_gameplay",
                    "--stage",
                    "base",
                    "--stage",
                    "audit",
                    "--languages",
                    "CN",
                    "--default-language",
                    "CN",
                ),
            ),
        )
    )
    # gameplay_builder/projectiles reads export_full only; it writes
    # webui/data/gameplay/projectiles.json.
    tasks.append(
        TaskSpec(
            "projectiles",
            (module("scripts.build_gameplay", "--stage", "projectiles"),),
        )
    )

    # ---- consumers of the asset index --------------------------------------

    # build_character_data.py:103 defaults --asset-index to
    # webui/data/assets/index.json, so it must follow the assets task whenever
    # that task is in the plan. Without --with-assets the index is whatever the
    # previous run published and there is nothing to wait for.
    assets_edge: tuple[str, ...] = ("assets",) if args.with_assets else ()
    tasks.append(
        TaskSpec(
            "characters",
            (
                module(
                    "scripts.build_character_data",
                    "--languages",
                    "CN",
                    "--default-language",
                    "CN",
                ),
            ),
            after=assets_edge,
        )
    )

    def gameplay_asset_refs_task(name: str, after: tuple[str, ...]) -> TaskSpec:
        return TaskSpec(
            name,
            (
                module(
                    "scripts.build_gameplay",
                    "--stage",
                    "asset-refs",
                    "--default-language",
                    "CN",
                ),
            ),
            after=after,
        )

    # build_gameplay.build_asset_refs_stage reads
    # webui/data/lang/CN/gameplay/index.json (gameplay) and
    # webui/data/assets/index.json (assets).
    tasks.append(
        gameplay_asset_refs_task("gameplay_asset_refs", ("gameplay", *assets_edge))
    )

    if args.with_assets:
        audio_args: list[str] = []
        if not args.decode_audio:
            audio_args.append("--skip-decode")
        if args.game_root:
            audio_args.extend(("--game-root", str(args.game_root)))
        if args.export_root:
            audio_args.extend(("--export-root", str(args.export_root)))
        # build_audio.py reads data/lang/<LANG>/gameplay/index.json (gameplay)
        # and data/gameplay/projectiles.json (projectiles) directly, and it
        # reaches the streaming-instance sidecars transitively:
        # build_audio.py:14851 calls build_audio_semantic_data, which at
        # build_audio_semantics.py:13206 calls
        # scene_backgrounds.collect_scene_background_semantics ->
        # _load_streaming_instance_identity_catalog (scene_backgrounds.py:2779
        # -> :168), globbing
        # export_full/recovered/AnimeStudio-cli/*/map_streaming_instances/*.json.
        # The old barrier plan ran audio in the same phase as the streaming
        # extractor, so it could read that directory while it was being
        # rewritten; the edge closes that race.
        # It reads nothing under webui/data/assets or webui/data/map_recovery,
        # so it is still not tied to the asset index or the map preview.
        tasks.append(
            TaskSpec(
                "audio",
                (module("scripts.build_audio", *audio_args),),
                after=("gameplay", "projectiles", "map_streaming_instances"),
            )
        )

    # ---- map recovery streaming instances and preview -----------------------

    # recover_map_streaming_instances.py:39 resolves its scene list from
    # webui/data/map_recovery/maps, which the map_recovery data build writes.
    # The AnimeStudio mesh export it also reads is already complete.
    streaming_args = ["--all-published-map-scenes", "--jobs", map_recovery_jobs]
    if args.game_root:
        streaming_args.extend(("--game-root", str(args.game_root)))
    if args.export_root:
        anime_root = args.export_root / "recovered/AnimeStudio-cli/StreamingAssets"
        streaming_args.extend((
            "--asset-map", str(anime_root / "maps/endfield_streamingassets_assets.json"),
            "--mesh-root", str(anime_root / "convert_by_type/Mesh"),
            "--output-root", str(anime_root / "map_streaming_instances"),
        ))
    tasks.append(
        TaskSpec(
            "map_streaming_instances",
            (command("scripts/recover_map_streaming_instances.py", *streaming_args),),
            after=("map_recovery",),
        )
    )

    # build_map_recovery_preview.py imports map_recovery_sources
    # .projection_streaming_scene, which reads the map_streaming_instances
    # sidecars, and it reads webui/data/assets/index.json directly
    # (build_map_recovery_preview.py:73/937) for the mesh -> material ->
    # base-colour texture relations that the rendered backgrounds use. The
    # published maps arrive transitively through map_streaming_instances.
    tasks.append(
        TaskSpec(
            "map_recovery_preview",
            (
                module(
                    "scripts.build_map_recovery_data",
                    "--preview-only",
                    "--jobs",
                    map_recovery_jobs,
                ),
            ),
            after=("map_streaming_instances", *assets_edge),
        )
    )

    # ---- source graph and its consumers ------------------------------------

    graph_args = ["build", "--language", "CN"]
    if not args.full_source_graph:
        graph_args.extend(
            ("--relevant-asset-maps", "--skip-reference-rows", "--skip-followups")
        )
    # The audio builder rewrites lang/<L>/conv/*.json (attached audio ids) and
    # lang/<L>/gameplay/sound_effects*.json while this graph may be reading
    # lang/<L>. That is deliberately not an edge: the graph's conv ingestion
    # reads only story keys, mission storyOrder and flow, none of which audio
    # touches, and build_audio.json_dump replaces files atomically, so the graph
    # sees whole files and identical graph-relevant content either way.
    # tools/endfield_source_graph.py touches webui/data at exactly these paths:
    # assets/index.json and assets/videos.json (assets), lang/<L>/gameplay
    # /index.json (gameplay), plus lang/<L>/{index.json,conv,reference},
    # game_data/groups, mission_pipeline and updates/latest.json, none of which
    # this runner produces. It reads no audio, character, projectile,
    # gameplay_refs or map_recovery payload, so those are not edges.
    tasks.append(
        TaskSpec(
            "source_graph",
            (command("tools/endfield_source_graph.py", *graph_args),),
            after=("gameplay", *assets_edge),
        )
    )
    # The same asset-ref stage re-runs so the sidecar can carry source-graph
    # proof (asset_builder/gameplay_refs.py:1069 picks the sqlite up when it
    # exists). It writes the same webui/data/assets/gameplay_refs.json as the
    # pre-graph run, so it must also follow that run rather than race it.
    tasks.append(
        gameplay_asset_refs_task(
            "gameplay_asset_refs_after_graph",
            ("source_graph", "gameplay_asset_refs"),
        )
    )
    # gameplay_builder/combat_relationships.py:35 reads
    # reports/source_graph/endfield_source_graph.sqlite.
    tasks.append(
        TaskSpec(
            "combat_relationships",
            (
                module(
                    "scripts.build_gameplay",
                    "--stage",
                    "combat",
                    "--languages",
                    "CN",
                ),
            ),
            after=("source_graph",),
        )
    )

    validate_tasks(tasks)
    return tasks


def validate_tasks(tasks: Sequence[TaskSpec]) -> None:
    """Fail closed on a malformed graph instead of scheduling part of it."""
    names: set[str] = set()
    for task in tasks:
        if task.name in names:
            raise ValueError(f"duplicate task name in the build graph: {task.name}")
        names.add(task.name)
    for task in tasks:
        for dependency in task.after:
            if dependency not in names:
                raise ValueError(
                    f"task {task.name} depends on unknown task {dependency}"
                )
            if dependency == task.name:
                raise ValueError(f"task {task.name} depends on itself")
    # A cycle would leave tasks permanently unrunnable; catch it at plan time.
    dependency_depths(tasks)


def dependency_depths(tasks: Sequence[TaskSpec]) -> dict[str, int]:
    """Return each task's longest-path depth, raising on a dependency cycle."""
    by_name = {task.name: task for task in tasks}
    remaining = {name: len(task.after) for name, task in by_name.items()}
    dependents: dict[str, list[str]] = {name: [] for name in by_name}
    for task in tasks:
        for dependency in task.after:
            dependents[dependency].append(task.name)
    depths = {name: 0 for name in by_name}
    ready = deque(name for name, count in remaining.items() if count == 0)
    resolved = 0
    while ready:
        name = ready.popleft()
        resolved += 1
        for dependent in dependents[name]:
            depths[dependent] = max(depths[dependent], depths[name] + 1)
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                ready.append(dependent)
    if resolved != len(by_name):
        unresolved = sorted(name for name, count in remaining.items() if count)
        raise ValueError(f"dependency cycle in the build graph: {', '.join(unresolved)}")
    return depths


def build_phases(args: argparse.Namespace) -> list[tuple[str, list[TaskSpec]]]:
    """Group the graph by dependency depth for plan printing and reporting.

    The scheduler does not use these groups; they exist so the timing report
    keeps a readable phase column. Depth N holds the tasks whose longest
    dependency chain is N edges long.
    """
    tasks = build_tasks(args)
    depths = dependency_depths(tasks)
    phases: list[tuple[str, list[TaskSpec]]] = []
    for depth in range(max(depths.values(), default=-1) + 1):
        grouped = [task for task in tasks if depths[task.name] == depth]
        if grouped:
            phases.append((f"depth{depth}", grouped))
    return phases


def display_command(command: CommandSpec) -> str:
    argv = list(command.argv)
    try:
        argv[0] = Path(argv[0]).name
        argv[1] = Path(argv[1]).resolve().relative_to(ROOT).as_posix()
    except (IndexError, OSError, ValueError):
        pass
    return subprocess.list2cmdline(argv)


def run_task(task: TaskSpec) -> dict:
    started = time.perf_counter()
    command_results = []
    task_returncode = 0
    diagnostic = ""
    for command in task.commands:
        shown = display_command(command)
        print(f"[webui-build:{task.name}] {shown}", flush=True)
        command_started = time.perf_counter()
        try:
            environment = os.environ.copy()
            environment.update(command.environment)
            completed = subprocess.run(
                command.argv,
                cwd=ROOT,
                check=False,
                env=environment,
            )
            returncode = completed.returncode
        except OSError as exc:
            returncode = 1
            diagnostic = f"{type(exc).__name__}: {exc}"
            print(f"[webui-build:{task.name}] {diagnostic}", file=sys.stderr, flush=True)
        command_results.append(
            {
                "command": shown,
                "returnCode": returncode,
                "seconds": round(time.perf_counter() - command_started, 3),
            }
        )
        if returncode:
            task_returncode = returncode
            break
    seconds = round(time.perf_counter() - started, 3)
    state = "ok" if task_returncode == 0 else "failed"
    print(f"[webui-build:{task.name}] {state} in {seconds:.3f}s", flush=True)
    result = {
        "name": task.name,
        "returnCode": task_returncode,
        "seconds": seconds,
        "commands": command_results,
    }
    if diagnostic:
        result["diagnostic"] = diagnostic
    return result


@dataclass
class TaskRun:
    """Per-task scheduling state and wall-clock window inside the run."""

    spec: TaskSpec
    depth: int
    status: str = "pending"
    result: dict = field(default_factory=dict)
    start_offset: float = 0.0
    end_offset: float = 0.0


def run_graph(tasks: Sequence[TaskSpec], jobs: int) -> tuple[int, list[TaskRun]]:
    """Run the graph, starting each task as soon as its inputs are published."""
    depths = dependency_depths(tasks)
    runs = {task.name: TaskRun(task, depths[task.name]) for task in tasks}
    order = [task.name for task in tasks]
    returncode = 0
    started = time.perf_counter()

    def ready(name: str) -> bool:
        return all(
            runs[dependency].status == "ok" for dependency in runs[name].spec.after
        )

    def blocked(name: str) -> bool:
        return any(
            runs[dependency].status in {"failed", "skipped"}
            for dependency in runs[name].spec.after
        )

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        pending: dict = {}
        while True:
            # Skip anything whose inputs will never be published, then start
            # every runnable task the job budget allows.
            progressed = True
            while progressed:
                progressed = False
                for name in order:
                    run = runs[name]
                    if run.status != "pending":
                        continue
                    if blocked(name):
                        run.status = "skipped"
                        print(
                            f"[webui-build] skipping {name}: a dependency did not succeed",
                            file=sys.stderr,
                            flush=True,
                        )
                        progressed = True
            for name in order:
                run = runs[name]
                if run.status != "pending" or len(pending) >= jobs or not ready(name):
                    continue
                run.status = "running"
                run.start_offset = round(time.perf_counter() - started, 3)
                print(
                    f"[webui-build] start {name}"
                    + (f" (after {', '.join(run.spec.after)})" if run.spec.after else ""),
                    flush=True,
                )
                pending[executor.submit(run_task, run.spec)] = name
            if not pending:
                stalled = [name for name in order if runs[name].status == "pending"]
                if stalled:
                    # Unreachable for a validated DAG; never leave work silently
                    # unbuilt if the scheduler ever regresses.
                    raise RuntimeError(
                        "build graph stalled with runnable work left: "
                        + ", ".join(stalled)
                    )
                break
            done, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for future in done:
                name = pending.pop(future)
                run = runs[name]
                try:
                    run.result = future.result()
                except Exception as exc:  # fail closed on unexpected worker errors
                    run.result = {
                        "name": name,
                        "returnCode": 1,
                        "seconds": 0.0,
                        "commands": [],
                        "diagnostic": f"{type(exc).__name__}: {exc}",
                    }
                run.end_offset = round(time.perf_counter() - started, 3)
                if run.result["returnCode"]:
                    run.status = "failed"
                    returncode = returncode or run.result["returnCode"]
                    print(
                        f"[webui-build] task {name} failed; its dependents are skipped.",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    run.status = "ok"

    skipped = [name for name in order if runs[name].status == "skipped"]
    if skipped:
        print(
            f"[webui-build] skipped after failure: {', '.join(skipped)}",
            file=sys.stderr,
            flush=True,
        )
    return returncode, [runs[name] for name in order]


def task_payload(run: TaskRun) -> dict:
    if run.status in {"ok", "failed"}:
        payload = dict(run.result)
    else:
        payload = {
            "name": run.spec.name,
            "returnCode": None,
            "seconds": 0.0,
            "commands": [],
        }
    payload["status"] = run.status
    payload["after"] = list(run.spec.after)
    payload["depth"] = run.depth
    payload["startOffsetSeconds"] = run.start_offset
    payload["endOffsetSeconds"] = run.end_offset
    return payload


def phase_payloads(runs: Sequence[TaskRun]) -> list[dict]:
    """Group finished task runs by dependency depth for the timing report."""
    phases: list[dict] = []
    for depth in sorted({run.depth for run in runs}):
        grouped = [run for run in runs if run.depth == depth]
        tasks = [task_payload(run) for run in grouped]
        executed = [run for run in grouped if run.status in {"ok", "failed"}]
        if executed:
            seconds = round(
                max(run.end_offset for run in executed)
                - min(run.start_offset for run in executed),
                3,
            )
        else:
            seconds = 0.0
        serial_task_seconds = round(sum(task["seconds"] for task in tasks), 3)
        phases.append(
            {
                "name": f"depth{depth}",
                "depth": depth,
                "returnCode": next(
                    (
                        task["returnCode"]
                        for task in tasks
                        if task["returnCode"]
                    ),
                    0,
                ),
                "seconds": seconds,
                "serialTaskSeconds": serial_task_seconds,
                "overlapSecondsSaved": round(max(0.0, serial_task_seconds - seconds), 3),
                "tasks": tasks,
            }
        )
    return phases


def write_reports(payload: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    json_tmp = REPORT_JSON.with_suffix(".json.tmp")
    json_tmp.write_text(json_text, encoding="utf-8")
    os.replace(json_tmp, REPORT_JSON)

    lines = [
        "# WebUI post-Story build steps",
        "",
        f"- Status: `{payload['status']}`",
        f"- Generated: `{payload['generated']}`",
        f"- Parallel jobs: `{payload['jobs']}`",
        f"- Wall time: `{payload['wallSeconds']:.3f}s`",
        f"- Builder time hidden by overlap: `{payload['overlapSecondsSaved']:.3f}s`",
        "",
        "| Phase | Task | After | Result | Seconds |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for phase in payload["phases"]:
        for task in phase["tasks"]:
            returncode = task["returnCode"]
            if task.get("status") not in {"ok", "failed"}:
                result = task.get("status") or "pending"
            else:
                result = "ok" if returncode == 0 else f"failed ({returncode})"
            after = ", ".join(task.get("after") or []) or "-"
            lines.append(
                f"| {phase['name']} | {task['name']} | {after} | {result} "
                f"| {task['seconds']:.3f} |"
            )
    md_tmp = REPORT_MD.with_suffix(".md.tmp")
    md_tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(md_tmp, REPORT_MD)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build post-Story WebUI views from a declared dependency graph.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Maximum concurrent independent builders (default: 4).",
    )
    parser.add_argument("--with-assets", action="store_true")
    parser.add_argument(
        "--asset-mode",
        choices=("focused", "default", "debug"),
        default="default",
    )
    parser.add_argument("--decode-audio", action="store_true")
    parser.add_argument("--full-source-graph", action="store_true")
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the dependency graph and commands without running builders.",
    )
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if args.decode_audio and not args.with_assets:
        parser.error("--decode-audio requires --with-assets")
    return args


def print_plan(tasks: Sequence[TaskSpec]) -> None:
    depths = dependency_depths(tasks)
    for depth in range(max(depths.values(), default=-1) + 1):
        grouped = [task for task in tasks if depths[task.name] == depth]
        if not grouped:
            continue
        print(f"[depth{depth}]")
        for task in grouped:
            after = ", ".join(task.after) if task.after else "-"
            print(f"  {task.name} (after: {after})")
            for command in task.commands:
                print(f"    {display_command(command)}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tasks = build_tasks(args)
    if args.dry_run:
        print_plan(tasks)
        return 0

    started = time.perf_counter()
    returncode, runs = run_graph(tasks, args.jobs)
    wall_seconds = round(time.perf_counter() - started, 3)
    phases = phase_payloads(runs)

    payload = {
        "schemaVersion": 2,
        "generated": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if returncode == 0 else "failed",
        "returnCode": returncode,
        "jobs": args.jobs,
        "wallSeconds": wall_seconds,
        "options": {
            "withAssets": args.with_assets,
            "assetMode": args.asset_mode,
            "decodeAudio": args.decode_audio,
            "fullSourceGraph": args.full_source_graph,
            "exportRoot": str(args.export_root.resolve()) if args.export_root else None,
            "gameRoot": str(args.game_root.resolve()) if args.game_root else None,
        },
        "graph": [
            {"name": task.name, "after": list(task.after)} for task in tasks
        ],
        "phases": phases,
    }
    payload["serialTaskSeconds"] = round(
        sum(task["seconds"] for phase in phases for task in phase["tasks"]),
        3,
    )
    payload["overlapSecondsSaved"] = round(
        max(0.0, payload["serialTaskSeconds"] - wall_seconds),
        3,
    )
    write_reports(payload)
    print(f"[webui-build] timing report: {REPORT_MD.relative_to(ROOT)}", flush=True)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
