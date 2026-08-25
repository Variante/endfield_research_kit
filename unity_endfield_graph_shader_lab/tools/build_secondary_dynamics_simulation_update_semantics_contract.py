#!/usr/bin/env python3
"""Pin Simulation Update Basic Posture's recovered AVX2 equations."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_simulation_update_semantics_contract.json"
)
CORE_RVA = 0x241AA0
CORE_BYTES = 1804
CORE_SHA256 = "1a83498696a2e50778d1aed396decdafacbae129c3ae4196daa9391497eaae98"
SIN_RVA = 0x1DE610
SIN_BYTES = 557
SIN_SHA256 = "d11fc448307689e5bf1c981bf1cae17af4604d6fa0105aa2196b162048a1c6ac"


def _require(rows: dict[int, Any], rva: int, mnemonic: str, operand: str) -> Any:
    row = rows.get(rva)
    if row is None or row.mnemonic != mnemonic or row.op_str != operand:
        actual = "missing" if row is None else f"{row.mnemonic} {row.op_str}"
        raise burst.ContractError(f"Update posture instruction drift at 0x{rva:x}: {actual}")
    return row


def _rip_float(pe: dict[str, Any], ins: Any, expected: float) -> float:
    operand = next(
        (op for op in ins.operands if op.type == 3 and ins.reg_name(op.mem.base) == "rip"),
        None,
    )
    if operand is None:
        raise burst.ContractError(f"expected RIP float at 0x{ins.address:x}")
    rva = ins.address + ins.size + operand.mem.disp - pe["imageBase"]
    offset = burst._rva_file_offset(pe, rva, 4)
    value = struct.unpack_from("<f", pe["data"], offset)[0]
    if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-7):
        raise burst.ContractError(f"Update posture constant drift: {value} != {expected}")
    return value


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    _, instructions = burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    burst._exact_rva_span(pe, SIN_RVA, SIN_BYTES, SIN_SHA256)
    rows = {ins.address - pe["imageBase"]: ins for ins in instructions}

    pins = [
        (0x241AF8, "mov", "ecx, dword ptr [rcx + rax*4]"),
        (0x241B2E, "movzx", "esi, word ptr [r10 + r11*2]"),
        (0x241EC4, "test", "byte ptr [r8 + r15], 2"),
        (0x241ED6, "mov", "r12d, dword ptr [rcx + r15*4]"),
        (0x241E46, "vextractps", "dword ptr [rbx + r15*4 + 8], xmm6, 2"),
        (0x241E4E, "vmovlps", "qword ptr [rbx + r15*4], xmm6"),
        (0x241EA0, "vmovups", "xmmword ptr [rdi + rax], xmm5"),
        (0x242128, "call", "0x1801de610"),
        (0x242136, "call", "0x1801de610"),
    ]
    for pin in pins:
        _require(rows, *pin)

    constants = {
        "skipReconstructionRatio": _rip_float(
            pe,
            _require(rows, 0x241B15, "vucomiss", "xmm0, dword ptr [rip + 0x122dd3]"),
            0.99,
        ),
        "minimumBlendRatio": _rip_float(
            pe,
            _require(rows, 0x241EED, "vucomiss", "xmm0, dword ptr [rip + 0x122b03]"),
            1e-8,
        ),
        "quaternionNlerpThreshold": _rip_float(
            pe,
            _require(rows, 0x241F1E, "vmovss", "xmm9, dword ptr [rip + 0x1228fe]"),
            0.9995,
        ),
    }

    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-update-semantics.v1",
        "status": "baseline_hierarchy_and_animation_pose_blend_equations_closed_sine_body_pinned",
        "native_gate": gate,
        "core": {
            "cpuVariant": "avx2",
            "rva": f"0x{CORE_RVA:x}",
            "bytes": CORE_BYTES,
            "sha256": CORE_SHA256,
            "dispatch": ["0x241910 entry", "0x2421b0 range", "0x241aa0 core"],
        },
        "argumentElementStridesBytes": [
            4, 464, 1, 4, 12, 16, 2, 2, 2, 12, 16, 12, 16, 4
        ],
        "representationBoundary": (
            "the pinned Burst cores use packed float3 for basePos and stepBasicPosition; "
            "the managed fallback contract separately reports double3"
        ),
        "constants": constants,
        "stages": [
            {
                "name": "baseline_selection",
                "range": "0x241af1..0x241b33",
                "equations": [
                    "baselineIndex = stepBaseLineIndexArray[rangeIndex] & 0xffff",
                    "teamId = stepBaseLineIndexArray[rangeIndex] >> 16",
                    "baselineStart = baseLineStartDataIndices[baselineIndex]",
                    "baselineCount = baseLineDataCounts[baselineIndex]",
                    "dataStart = team.baseLineDataChunk.startIndex + baselineStart",
                ],
            },
            {
                "name": "hierarchy_reconstruction",
                "range": "0x241bd0..0x241ee3",
                "gate": "team.animationPoseRatio <= 0.99 and baselineCount > 0",
                "equations": [
                    "vertex = baseLineData[dataStart + i]",
                    "proxy = team.proxyCommonChunk.startIndex + vertex",
                    "particle = team.particleChunk.startIndex + vertex",
                    "if (attributes[proxy] & 2) and parentVertex >= 0: reconstruct from parent",
                    "scaledLocalPosition = vertexLocalPositions[proxy] * team.negativeScaleDirection * team.initScale * team.scaleRatio",
                    "stepBasicPosition[particle] = stepBasicPosition[parentParticle] + rotate(stepBasicRotation[parentParticle], scaledLocalPosition)",
                    "adjustedLocalRotation = team.negativeScaleQuaternionValue * vertexLocalRotations[proxy] (component-wise sign adjustment)",
                    "stepBasicRotation[particle] = stepBasicRotation[parentParticle] * adjustedLocalRotation",
                    "root rotation = normalize(quaternion(float3x3(normalize(cross(up,forward)), cross(forward,right), forward)))",
                ],
            },
            {
                "name": "animation_pose_blend",
                "range": "0x241ee8..0x242160",
                "gate": "1e-8 < team.animationPoseRatio <= 0.99",
                "equations": [
                    "stepBasicPosition = lerp(stepBasicPosition, basePos, animationPoseRatio)",
                    "baseRot sign is flipped when dot(stepBasicRotation, baseRot) < 0",
                    "dot >= 0.9995: normalize(lerp(stepBasicRotation, signedBaseRot, animationPoseRatio))",
                    "otherwise theta=acos(dot), wa=sin((1-t)*theta)/sqrt(1-dot^2), wb=sin(t*theta)/sqrt(1-dot^2), result=wa*a+wb*b",
                ],
            },
        ],
        "sineHelper": {
            "rva": f"0x{SIN_RVA:x}",
            "bytes": SIN_BYTES,
            "sha256": SIN_SHA256,
            "role": "scalar sine for the two spherical-interpolation weights",
            "status": "function_body_and_semantic_role_closed_coefficients_not_transcribed",
        },
        "implementation_boundary": {
            "solverImplemented": False,
            "retailEquivalent": False,
            "equationsClosed": True,
            "bitIdenticalSinePort": False,
            "laterStagesRequired": ["Simulation End", "constraints", "collisions", "central transform writeback"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_contract(), indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit("Simulation Update semantics contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
