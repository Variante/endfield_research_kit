"""Run a declared WebUI build graph and write its timing report.

The scheduler starts any task whose edges (``TaskSpec.after``, already resolved
for the plan by ``scripts.webui.pages.plan_build``) have all succeeded, bounded
by ``jobs``. A failed task skips everything downstream of it and the run exits
non-zero, so a slow producer only delays its own consumers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from scripts.repo_paths import REPO_ROOT
from scripts.webui.pages import CommandSpec, TaskSpec

REPORT_DIR = REPO_ROOT / "reports" / "export"
REPORT_JSON = REPORT_DIR / "webui_build_steps_latest.json"
REPORT_MD = REPORT_DIR / "webui_build_steps_latest.md"


def dependency_depths(tasks: Sequence[TaskSpec]) -> dict[str, int]:
    """Each task's longest-path depth; raises on an unknown edge or a cycle."""
    by_name = {task.name: task for task in tasks}
    for task in tasks:
        for dependency in task.after:
            if dependency not in by_name or dependency == task.name:
                raise ValueError(f"task {task.name} has an invalid edge to {dependency}")
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


def display_command(command: CommandSpec) -> str:
    argv = list(command.argv)
    try:
        argv[0] = Path(argv[0]).name
        if argv[1] != "-m":
            argv[1] = Path(argv[1]).resolve().relative_to(REPO_ROOT).as_posix()
    except (IndexError, OSError, ValueError):
        pass
    return subprocess.list2cmdline(argv)


def plan_lines(tasks: Sequence[TaskSpec]) -> list[str]:
    depths = dependency_depths(tasks)
    lines: list[str] = []
    for depth in range(max(depths.values(), default=-1) + 1):
        grouped = [task for task in tasks if depths[task.name] == depth]
        lines.append(f"[depth{depth}]")
        for task in grouped:
            lines.append(f"  {task.name} (after: {', '.join(task.after) or '-'})")
            lines.extend(f"    {display_command(command)}" for command in task.commands)
    return lines


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
            returncode = subprocess.run(command.argv, cwd=REPO_ROOT, check=False, env=environment).returncode
        except OSError as exc:
            returncode = 1
            diagnostic = f"{type(exc).__name__}: {exc}"
            print(f"[webui-build:{task.name}] {diagnostic}", file=sys.stderr, flush=True)
        command_results.append({
            "command": shown,
            "returnCode": returncode,
            "seconds": round(time.perf_counter() - command_started, 3),
        })
        if returncode:
            task_returncode = returncode
            break
    seconds = round(time.perf_counter() - started, 3)
    print(f"[webui-build:{task.name}] {'ok' if task_returncode == 0 else 'failed'} in {seconds:.3f}s", flush=True)
    result = {"name": task.name, "returnCode": task_returncode, "seconds": seconds, "commands": command_results}
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
    failure_order = sorted(order, key=depths.__getitem__)
    returncode = 0
    started = time.perf_counter()

    def ready(name: str) -> bool:
        return all(runs[dependency].status == "ok" for dependency in runs[name].spec.after)

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        pending: dict = {}
        while True:
            # Skip anything whose inputs will never be published, then start
            # every runnable task the job budget allows.
            # Parents come first, so skips propagate through the whole graph
            # in one pass even when the registry lists children first.
            for name in failure_order:
                run = runs[name]
                if run.status == "pending" and any(
                    runs[dependency].status in {"failed", "skipped"}
                    for dependency in run.spec.after
                ):
                    run.status = "skipped"
                    print(f"[webui-build] skipping {name}: a dependency did not succeed", file=sys.stderr, flush=True)
            for name in order:
                run = runs[name]
                if run.status != "pending" or len(pending) >= jobs or not ready(name):
                    continue
                run.status = "running"
                run.start_offset = round(time.perf_counter() - started, 3)
                after = f" (after {', '.join(run.spec.after)})" if run.spec.after else ""
                print(f"[webui-build] start {name}{after}", flush=True)
                pending[executor.submit(run_task, run.spec)] = name
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
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
                    print(f"[webui-build] task {name} failed; its dependents are skipped.", file=sys.stderr, flush=True)
                else:
                    run.status = "ok"

    skipped = [name for name in order if runs[name].status == "skipped"]
    if skipped:
        print(f"[webui-build] skipped after failure: {', '.join(skipped)}", file=sys.stderr, flush=True)
    return returncode, [runs[name] for name in order]


def task_payload(run: TaskRun) -> dict:
    if run.status in {"ok", "failed"}:
        payload = dict(run.result)
    else:
        payload = {"name": run.spec.name, "returnCode": None, "seconds": 0.0, "commands": []}
    payload.update(
        status=run.status,
        after=list(run.spec.after),
        depth=run.depth,
        startOffsetSeconds=run.start_offset,
        endOffsetSeconds=run.end_offset,
    )
    return payload


def phase_payloads(runs: Sequence[TaskRun]) -> list[dict]:
    """Group finished task runs by dependency depth for the timing report."""
    phases: list[dict] = []
    for depth in sorted({run.depth for run in runs}):
        grouped = [run for run in runs if run.depth == depth]
        tasks = [task_payload(run) for run in grouped]
        executed = [run for run in grouped if run.status in {"ok", "failed"}]
        seconds = (
            round(max(run.end_offset for run in executed) - min(run.start_offset for run in executed), 3)
            if executed else 0.0
        )
        serial_task_seconds = round(sum(task["seconds"] for task in tasks), 3)
        phases.append({
            "name": f"depth{depth}",
            "depth": depth,
            "returnCode": next((task["returnCode"] for task in tasks if task["returnCode"]), 0),
            "seconds": seconds,
            "serialTaskSeconds": serial_task_seconds,
            "overlapSecondsSaved": round(max(0.0, serial_task_seconds - seconds), 3),
            "tasks": tasks,
        })
    return phases


def write_reports(payload: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_tmp = REPORT_JSON.with_suffix(".json.tmp")
    json_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(json_tmp, REPORT_JSON)

    lines = [
        "# WebUI build steps",
        "",
        f"- Status: `{payload['status']}`",
        f"- Generated: `{payload['generated']}`",
        f"- Pages: `{', '.join(payload['options']['pages'])}`",
        f"- Parallel jobs: `{payload['jobs']}`",
        f"- Wall time: `{payload['wallSeconds']:.3f}s`",
        f"- Builder time hidden by overlap: `{payload['overlapSecondsSaved']:.3f}s`",
        "",
        "| Phase | Task | After | Result | Seconds |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for phase in payload["phases"]:
        for task in phase["tasks"]:
            if task["status"] not in {"ok", "failed"}:
                result = task["status"]
            else:
                result = "ok" if task["returnCode"] == 0 else f"failed ({task['returnCode']})"
            after = ", ".join(task["after"]) or "-"
            lines.append(f"| {phase['name']} | {task['name']} | {after} | {result} | {task['seconds']:.3f} |")
    md_tmp = REPORT_MD.with_suffix(".md.tmp")
    md_tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(md_tmp, REPORT_MD)
