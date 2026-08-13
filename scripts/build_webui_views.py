"""Build post-Story WebUI views in dependency-safe parallel phases.

The root export wrapper owns extraction, freshness, evidence, and Story. This
runner starts after those inputs are current and keeps every existing builder
as an independently callable command.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
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


@dataclass(frozen=True)
class TaskSpec:
    name: str
    commands: tuple[CommandSpec, ...]


def python_command(path: str, *args: str) -> CommandSpec:
    return CommandSpec((sys.executable, str(ROOT / path), *args))


def build_phases(args: argparse.Namespace) -> list[tuple[str, list[TaskSpec]]]:
    mission = TaskSpec(
        "mission_pipeline",
        (
            python_command(
                "scripts/story_builder/protocol_registry.py",
                "--ensure-current",
            ),
            python_command(
                "scripts/build_mission_pipeline_data.py",
                "--refresh-source-story-gap-queue",
            ),
        ),
    )
    character = TaskSpec(
        "characters",
        (
            python_command(
                "scripts/build_character_data.py",
                "--languages",
                "CN",
                "--default-language",
                "CN",
            ),
        ),
    )

    if args.mission_pipeline_only:
        return [("post_story", [mission])]

    gameplay = TaskSpec(
        "gameplay",
        (
            python_command(
                "scripts/build_gameplay.py",
                "--stage",
                "base",
                "--languages",
                "CN",
                "--default-language",
                "CN",
            ),
        ),
    )
    projectile = TaskSpec(
        "projectiles",
        (python_command("scripts/build_gameplay.py", "--stage", "projectiles"),),
    )

    phase_one = [mission]
    if args.with_assets:
        asset_mode = "default" if args.asset_mode == "debug" else args.asset_mode
        phase_one.append(
            TaskSpec(
                "assets",
                (
                    python_command(
                        "scripts/build_assets.py",
                        "--mode",
                        asset_mode,
                        "--skip-gameplay-refs",
                    ),
                ),
            )
        )
    else:
        phase_one.append(character)
    phase_one.extend((gameplay, projectile))

    gameplay_refs = TaskSpec(
        "gameplay_asset_refs",
        (
            python_command(
                "scripts/build_gameplay.py",
                "--stage",
                "asset-refs",
                "--default-language",
                "CN",
            ),
        ),
    )
    phase_two = [gameplay_refs]
    if args.with_assets:
        audio_args: list[str] = []
        if not args.decode_audio:
            audio_args.append("--skip-decode")
        if args.game_root:
            audio_args.extend(("--game-root", str(args.game_root)))
        if args.export_root:
            audio_args.extend(("--export-root", str(args.export_root)))
        phase_two = [
            character,
            gameplay_refs,
            TaskSpec(
                "audio",
                (python_command("scripts/build_audio.py", *audio_args),),
            ),
        ]

    graph_args = ["build", "--language", "CN"]
    if not args.full_source_graph:
        graph_args.extend(
            ("--relevant-asset-maps", "--skip-reference-rows", "--skip-followups")
        )
    graph = TaskSpec(
        "source_graph",
        (python_command("tools/endfield_source_graph.py", *graph_args),),
    )
    consumers = [
        TaskSpec(
            "combat_relationships",
            (
                python_command(
                    "scripts/build_gameplay.py",
                    "--stage",
                    "combat",
                    "--languages",
                    "CN",
                ),
            ),
        ),
    ]
    return [
        ("independent_views", phase_one),
        ("joined_sidecars", phase_two),
        ("source_graph", [graph]),
        ("graph_consumers", consumers),
    ]


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
            completed = subprocess.run(command.argv, cwd=ROOT, check=False)
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


def run_phase(name: str, tasks: Sequence[TaskSpec], jobs: int) -> dict:
    started = time.perf_counter()
    print(f"[webui-build] phase {name}: {', '.join(task.name for task in tasks)}", flush=True)
    results_by_name: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(jobs, len(tasks))) as executor:
        futures = {executor.submit(run_task, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                results_by_name[task.name] = future.result()
            except Exception as exc:  # fail closed on unexpected worker errors
                results_by_name[task.name] = {
                    "name": task.name,
                    "returnCode": 1,
                    "seconds": 0.0,
                    "commands": [],
                    "diagnostic": f"{type(exc).__name__}: {exc}",
                }
    results = [results_by_name[task.name] for task in tasks]
    seconds = round(time.perf_counter() - started, 3)
    serial_task_seconds = round(sum(result["seconds"] for result in results), 3)
    return {
        "name": name,
        "returnCode": next(
            (result["returnCode"] for result in results if result["returnCode"]),
            0,
        ),
        "seconds": seconds,
        "serialTaskSeconds": serial_task_seconds,
        "overlapSecondsSaved": round(max(0.0, serial_task_seconds - seconds), 3),
        "tasks": results,
    }


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
        "| Phase | Task | Result | Seconds |",
        "| --- | --- | ---: | ---: |",
    ]
    for phase in payload["phases"]:
        for task in phase["tasks"]:
            result = "ok" if task["returnCode"] == 0 else f"failed ({task['returnCode']})"
            lines.append(
                f"| {phase['name']} | {task['name']} | {result} | {task['seconds']:.3f} |"
            )
    md_tmp = REPORT_MD.with_suffix(".md.tmp")
    md_tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(md_tmp, REPORT_MD)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build post-Story WebUI views in dependency-safe parallel phases.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Maximum concurrent independent builders (default: 4).",
    )
    parser.add_argument("--mission-pipeline-only", action="store_true")
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
        help="Print the dependency phases and commands without running builders.",
    )
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if args.mission_pipeline_only and args.with_assets:
        parser.error("--mission-pipeline-only cannot be combined with --with-assets")
    if args.decode_audio and not args.with_assets:
        parser.error("--decode-audio requires --with-assets")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    phases = build_phases(args)
    if args.dry_run:
        for phase_name, tasks in phases:
            print(f"[{phase_name}]")
            for task in tasks:
                print(f"  {task.name}")
                for command in task.commands:
                    print(f"    {display_command(command)}")
        return 0

    started = time.perf_counter()
    phase_results = []
    returncode = 0
    for phase_name, tasks in phases:
        phase_result = run_phase(phase_name, tasks, args.jobs)
        phase_results.append(phase_result)
        if phase_result["returnCode"]:
            returncode = phase_result["returnCode"]
            print(
                f"[webui-build] phase {phase_name} failed; downstream phases were skipped.",
                file=sys.stderr,
                flush=True,
            )
            break

    payload = {
        "schemaVersion": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if returncode == 0 else "failed",
        "returnCode": returncode,
        "jobs": args.jobs,
        "wallSeconds": round(time.perf_counter() - started, 3),
        "options": {
            "missionPipelineOnly": args.mission_pipeline_only,
            "withAssets": args.with_assets,
            "assetMode": args.asset_mode,
            "decodeAudio": args.decode_audio,
            "fullSourceGraph": args.full_source_graph,
        },
        "phases": phase_results,
    }
    payload["serialTaskSeconds"] = round(
        sum(phase["serialTaskSeconds"] for phase in phase_results),
        3,
    )
    payload["overlapSecondsSaved"] = round(
        sum(phase["overlapSecondsSaved"] for phase in phase_results),
        3,
    )
    write_reports(payload)
    print(f"[webui-build] timing report: {REPORT_MD.relative_to(ROOT)}", flush=True)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
