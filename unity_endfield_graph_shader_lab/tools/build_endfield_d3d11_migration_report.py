#!/usr/bin/env python3
"""Build the fail-closed Unity-lab D3D11 migration report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
OUTPUT = REPO / "reports/assets/character_recovery/endminf_d3d11_migration.json"
CAPTURE = LAB / "scratch/character_recovery/endminf_viewer_playmode_sequence_d3d11"
HISTORICAL_CAPTURE = LAB / "scratch/character_recovery/endminf_viewer_playmode_sequence"

ACTIVE_D3D11_FILES = (
    LAB / "build_all_character_recovery.bat",
    LAB / "open_character_recovery_lab.bat",
    LAB / "tools/character_import/pipeline.py",
    LAB / "tools/character_import/model_pipeline.py",
    LAB / "tools/run_settled_phase_sweeps.py",
)
ACTIVE_D3D11_RUNTIME_FILES = (
    LAB / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRenderDocAutoCapture.cs",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def aggregate_frames(root: Path) -> str:
    frames = sorted(root.glob("frame_*.png"))
    if len(frames) != 41:
        raise ValueError(f"{relative(root)}: expected 41 frames, found {len(frames)}")
    digest = hashlib.sha256()
    for frame in frames:
        digest.update(bytes.fromhex(sha256(frame)))
    return digest.hexdigest()


def build() -> dict[str, object]:
    settings = LAB / "ProjectSettings/ProjectSettings.asset"
    settings_text = settings.read_text(encoding="utf-8")
    if "m_APIs: 02000000" not in settings_text or "m_APIs: 12000000" in settings_text:
        raise ValueError("WindowsStandaloneSupport is not explicit Direct3D11-only")

    workflow_rows = []
    for path in ACTIVE_D3D11_FILES:
        text = path.read_text(encoding="utf-8")
        if "-force-d3d11" not in text or "-force-d3d12" in text:
            raise ValueError(f"{relative(path)} is not an exclusive D3D11 workflow")
        workflow_rows.append({"path": relative(path), "sha256": sha256(path)})
    for path in ACTIVE_D3D11_RUNTIME_FILES:
        text = path.read_text(encoding="utf-8")
        if "GraphicsDeviceType.Direct3D11" not in text:
            raise ValueError(f"{relative(path)} does not require Direct3D11")
        if "GraphicsDeviceType.Direct3D12" in text:
            raise ValueError(f"{relative(path)} still contains an active Direct3D12 gate")
        workflow_rows.append({"path": relative(path), "sha256": sha256(path)})

    report_path = CAPTURE / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    required_true = (
        "observedTransition",
        "observedSettledLoop",
        "observedAnimatorContract",
        "observedEntranceVfx",
        "observedEntranceVfxCleanup",
        "observedRotationOnlyRootMotion",
        "observedPrimaryRockCompatibilityBinding",
    )
    if report.get("status") != "ok" or report.get("graphicsDeviceType") != "Direct3D11":
        raise ValueError("canonical capture is not a successful Direct3D11 run")
    if not all(report.get(name) is True for name in required_true):
        raise ValueError("canonical capture lost a required observation")
    frames = report.get("frames", [])
    if len(frames) != 41:
        raise ValueError("canonical capture report does not contain 41 frames")
    first = frames[0]
    blocked = first.get("blockedRendererIdentities", [])
    expected_blocked = ("Particle System (9)", "suikuai (2)", "Particle System (10)")
    if first.get("admittedRenderers") != 67 or len(blocked) != 3:
        raise ValueError("canonical D3D11 admission boundary drifted")
    if not all(any(name in row for row in blocked) for name in expected_blocked):
        raise ValueError("canonical D3D11 blocked-renderer identities drifted")

    comparison_rows = []
    for name in ("reference_comparison.json", "reference_no_framegen_comparison.json"):
        path = CAPTURE / name
        comparison = json.loads(path.read_text(encoding="utf-8"))
        rows = comparison.get("rows", [])
        comparison_rows.append(
            {
                "path": relative(path),
                "sha256": sha256(path),
                "recordingId": comparison.get("recordingId"),
                "comparisonBoundary": comparison.get("comparisonBoundary"),
                "rowCount": len(rows),
                "crystalContaminatedRows": sum(
                    row.get("crystalContaminated") is True for row in rows
                ),
                "crystalCleanRows": sum(
                    row.get("crystalContaminated") is not True for row in rows
                ),
                "phaseErrorSpreadFrames": comparison.get("phaseErrorSpreadFrames"),
            }
        )

    historical = None
    historical_report = HISTORICAL_CAPTURE / "report.json"
    if historical_report.is_file():
        historical = {
            "path": relative(HISTORICAL_CAPTURE),
            "role": "pre-migration D3D12 comparison snapshot",
            "reportSha256": sha256(historical_report),
            "aggregateFrameSha256": aggregate_frames(HISTORICAL_CAPTURE),
        }

    return {
        "schema": "endfield.character-recovery.d3d11-migration.v1",
        "status": "validated",
        "authoritativeBackend": "Direct3D11",
        "projectSettings": {
            "path": relative(settings),
            "windowsStandaloneGraphicsApiBytes": "02000000",
            "automaticGraphicsApiSelection": False,
        },
        "activeWorkflows": workflow_rows,
        "canonicalCapture": {
            "path": relative(CAPTURE),
            "reportSha256": sha256(report_path),
            "aggregateFrameSha256": aggregate_frames(CAPTURE),
            "graphicsDeviceType": report["graphicsDeviceType"],
            "frameCount": len(frames),
            "admittedRenderersAtEntrance": first["admittedRenderers"],
            "blockedRendererCountAtEntrance": len(blocked),
            "requiredObservations": list(required_true),
        },
        "referenceComparisons": comparison_rows,
        "historicalCapture": historical,
        "boundary": (
            "D3D11 is authoritative for current Windows execution. Historical D3D12 "
            "diagnostics remain labeled evidence and are not rewritten. The August 24 "
            "comparison continues to exclude crystal-contaminated rows."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != payload:
            raise SystemExit(f"stale or missing report: {OUTPUT}")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(payload, encoding="utf-8")
    print(f"PASS D3D11 migration contract: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
