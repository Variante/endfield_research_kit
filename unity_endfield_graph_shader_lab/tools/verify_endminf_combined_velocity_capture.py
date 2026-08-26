#!/usr/bin/env python3
"""Verify the retail DLSS velocity-combine runtime descriptor contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SHADER_HASH = "c47ae110dd014417"
INPUT_HASH = "72d2b22c"
OUTPUT_HASH = "f68eddc6"
EXPECTED_SESSIONS = {
    "FrameAnalysis-2026-08-24-182534": 117,
    "FrameAnalysis-2026-08-24-182744": 138,
    "FrameAnalysis-2026-08-24-182819": 127,
    "FrameAnalysis-2026-08-24-182850": 142,
}
INPUT_DESCRIPTOR = (
    'type=Texture2D width=3840 height=2160 mips=1 array=1 '
    'format="R10G10B10A2_UNORM"'
)
OUTPUT_DESCRIPTOR = (
    'type=Texture2D width=3840 height=2160 mips=1 array=1 '
    'format="R16G16_FLOAT"'
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_single_descriptor(session: Path, pattern: str) -> str:
    matches = sorted(session.glob(pattern))
    require(len(matches) == 1, f"{session.name}: expected one {pattern}, got {len(matches)}")
    return matches[0].read_text(encoding="utf-8", errors="strict").strip()


def verify_session(session: Path, dispatch: int) -> None:
    require(session.is_dir(), f"missing capture session: {session}")
    log = (session / "log.txt").read_text(encoding="utf-8", errors="replace")
    shader_line = re.search(
        rf"(?m)^{dispatch:06d} CSSetShader\([^\r\n]+hash={SHADER_HASH}\r?$",
        log,
    )
    require(shader_line is not None, f"{session.name}: missing shader dispatch {dispatch}")
    next_dispatch = log.find(f"{dispatch + 1:06d} ", shader_line.end())
    block = log[shader_line.start() : next_dispatch if next_dispatch >= 0 else None]
    require(
        f"resource=" in block and f"hash={INPUT_HASH}" in block,
        f"{session.name}: packed input {INPUT_HASH} is not bound",
    )
    require(
        f"resource=" in block and f"hash={OUTPUT_HASH}" in block,
        f"{session.name}: combined output {OUTPUT_HASH} is not bound",
    )
    require(
        f"{dispatch:06d} Dispatch(ThreadGroupCountX:480, "
        "ThreadGroupCountY:270, ThreadGroupCountZ:1)" in block,
        f"{session.name}: dispatch is not 480x270x1",
    )

    input_descriptor = read_single_descriptor(
        session, f"*-cs-t0={INPUT_HASH}-cs={SHADER_HASH}.dsc"
    )
    output_descriptor = read_single_descriptor(
        session, f"*-u0={OUTPUT_HASH}-cs={SHADER_HASH}.dsc"
    )
    require(INPUT_DESCRIPTOR in input_descriptor, f"{session.name}: input descriptor mismatch")
    require(
        'bind_flags="shader_resource render_target"' in input_descriptor,
        f"{session.name}: input bind flags mismatch",
    )
    require(OUTPUT_DESCRIPTOR in output_descriptor, f"{session.name}: output descriptor mismatch")
    require(
        'bind_flags="shader_resource render_target unordered_access"'
        in output_descriptor,
        f"{session.name}: output bind flags mismatch",
    )


def verify_report(report_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    velocity = report["nativeStreamlineRuntimeContract"]["velocityCombine"]
    require("R16G16_SFloat" in velocity["storageFormats"]["combinedOutput"],
            "report does not publish the closed R16G16_SFloat format")
    evidence = velocity["allocationFormatAudit"]["runtimeDescriptorEvidence"]
    require(evidence["shader3DMigotoHash"] == SHADER_HASH, "report shader hash mismatch")
    require(evidence["dispatchGroups"] == [480, 270, 1], "report dispatch mismatch")
    observed = {row["session"]: row["dispatch"] for row in evidence["captures"]}
    require(observed == EXPECTED_SESSIONS, "report capture inventory mismatch")


def verify_unity_producer(project_root: Path) -> None:
    compute = (
        project_root
        / "Assets/EndfieldGraphShaderLab/Resources/EndfieldRecoveredDLSSVelocityCombine.compute"
    ).read_text(encoding="utf-8")
    producer = (
        project_root
        / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredCombinedVelocityProducer.cs"
    ).read_text(encoding="utf-8")
    require("[numthreads(8, 8, 1)]" in compute, "Unity kernel is not 8x8x1")
    require(
        "sign(signedDistance) * squared * squared" in compute,
        "Unity kernel does not contain the exact signed fourth-power decode",
    )
    require(
        "GraphicsFormat.R16G16_SFloat" in producer,
        "Unity producer output format mismatch",
    )
    require(
        "SetComputeIntParams" in producer,
        "Unity producer does not publish integer input extents",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--capture-root",
        type=Path,
        default=Path("scratch/character_recovery/3dmigoto-dev-v1.0.0/package"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/assets/character_recovery/endminf_temporal_motion_admission.json"),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("unity_endfield_graph_shader_lab"),
    )
    args = parser.parse_args()

    for name, dispatch in EXPECTED_SESSIONS.items():
        verify_session(args.capture_root / name, dispatch)
    verify_report(args.report)
    verify_unity_producer(args.project_root)
    print(
        "combined_velocity_capture_ok: 4 sessions, packed R10G10B10A2_UNORM, "
        "3840x2160 R16G16_FLOAT UAV, dispatch 480x270x1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
