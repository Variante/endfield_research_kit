"""Refresh independent Story builder evidence files in parallel."""
from __future__ import annotations

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from scripts.common import ROOT, is_native_evidence_skip
from scripts.story_builder.mission_assets import (
    select_complete_mission_runtime_root,
)

DATA_JSON_DIR = ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
PERSISTENT_DATA_JSON_DIR = (
    ROOT / "export_full" / "structured" / "Persistent" / "Data" / "Json"
)
REQUIRED_SOURCE_LINK_ROOTS = (
    select_complete_mission_runtime_root(
        DATA_JSON_DIR / "MissionRuntimeAsset",
        PERSISTENT_DATA_JSON_DIR / "MissionRuntimeAsset",
    ),
    DATA_JSON_DIR / "LevelScriptData",
    DATA_JSON_DIR / "LevelScriptTemplateData",
)


@dataclass(frozen=True)
class EvidenceStep:
    name: str
    module: str
    argv: tuple[str, ...] = ()


@dataclass
class EvidenceResult:
    step: EvidenceStep
    returncode: int
    seconds: float
    stdout: str
    stderr: str


STEPS = (
    EvidenceStep("dialog_registry", "scripts.story_builder.dialog_registry", ("--quiet",)),
    EvidenceStep("video_bindings", "scripts.story_builder.video_bindings"),
    EvidenceStep("source_links", "scripts.story_builder.source_links"),
    EvidenceStep(
        "spaceship_story_content",
        "scripts.story_builder.spaceship_story_content",
    ),
)


def run_step(step: EvidenceStep) -> EvidenceResult:
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", step.module, *step.argv],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return EvidenceResult(
        step=step,
        returncode=proc.returncode,
        seconds=time.time() - started,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def print_stream(label: str, text: str) -> None:
    if not text.strip():
        return
    print(f"[story-evidence] {label}:")
    print(text.rstrip())


def main() -> int:
    if not any(path.is_dir() for path in REQUIRED_SOURCE_LINK_ROOTS):
        roots = ", ".join(str(path) for path in REQUIRED_SOURCE_LINK_ROOTS)
        print(
            "[story-evidence] missing Story source roots; refusing to overwrite evidence. "
            "Run .\\export.bat --from-game to refresh export_full first.",
            file=sys.stderr,
        )
        print(f"[story-evidence] checked roots: {roots}", file=sys.stderr)
        return 1

    print(
        "[story-evidence] refreshing dialog registry, video bindings, source "
        "links, and spaceship Story content"
    )
    results_by_name: dict[str, EvidenceResult] = {}
    with ThreadPoolExecutor(max_workers=len(STEPS)) as executor:
        future_to_step = {executor.submit(run_step, step): step for step in STEPS}
        for future in as_completed(future_to_step):
            result = future.result()
            results_by_name[result.step.name] = result
            if result.returncode != 0:
                status = f"failed ({result.returncode})"
            elif is_native_evidence_skip(result.stderr):
                status = "skipped"
            else:
                status = "ok"
            print(f"[story-evidence] {result.step.name}: {status} in {result.seconds:.3f}s")

    failed = False
    for step in STEPS:
        result = results_by_name[step.name]
        print_stream(f"{step.name} stdout", result.stdout)
        print_stream(f"{step.name} stderr", result.stderr)
        if result.returncode != 0:
            failed = True

    if failed:
        return 1
    print("[story-evidence] evidence refresh complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
