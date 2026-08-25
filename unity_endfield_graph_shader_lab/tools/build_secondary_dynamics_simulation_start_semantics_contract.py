#!/usr/bin/env python3
"""Pin the source-level semantics recovered from Simulation Start's AVX2 core."""

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
    "secondary_dynamics_simulation_start_semantics_contract.json"
)
CORE_RVA = 0x25E830
CORE_BYTES = 5074
CORE_SHA256 = "19b635fc37d878779e286408bcb58ea5abd3746f2f508f90fe634028d6bae9cc"


def _instruction(rows: dict[int, Any], rva: int, mnemonic: str, operand: str) -> Any:
    row = rows.get(rva)
    if row is None or row.mnemonic != mnemonic or row.op_str != operand:
        actual = "missing" if row is None else f"{row.mnemonic} {row.op_str}"
        raise burst.ContractError(
            f"Simulation Start instruction drift at 0x{rva:x}: {actual}"
        )
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
    if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-6):
        raise burst.ContractError(
            f"Simulation Start constant drift at RVA 0x{rva:x}: {value} != {expected}"
        )
    return value


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    _, instructions = burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    rows = {ins.address - pe["imageBase"]: ins for ins in instructions}

    pins = [
        (0x25E914, "movsxd", "r12, dword ptr [rbx + r14*4]"),
        (0x25E918, "movsx", "r15, word ptr [rsi + r12*2]"),
        (0x25EC63, "vmovss", "xmm10, dword ptr [rsp + 0x1cc]"),
        (0x25EF20, "test", "sil, 2"),
        (0x25EF26, "test", "byte ptr [rsp + 0x191], 0x20"),
        (0x25F138, "vmulss", "xmm7, xmm0, dword ptr [rsp + 0x464]"),
        (0x25F546, "vmulss", "xmm3, xmm3, dword ptr [rsp + 0x80]"),
        (0x25F5AF, "cmp", "r8d, 2"),
        (0x25F718, "call", "0x180247190"),
        (0x25F72F, "vbroadcastss", "xmm0, dword ptr [rsp + 0x1f0]"),
        (0x25F73D, "vbroadcastss", "xmm2, dword ptr [rsp + 0xa0]"),
        (0x25F74F, "vmulps", "xmm1, xmm2, xmm1"),
        (0x25F760, "test", "byte ptr [rsp + 0x191], 0x20"),
        (0x25F76A, "and", "r12b, 1"),
        (0x25F86E, "call", "0x18023c490"),
        (0x25F8D3, "vmovlpd", "qword ptr [rcx + rdi + 0x10], xmm0"),
        (0x25F8D9, "vmovupd", "xmmword ptr [rcx + rdi], xmm1"),
        (0x25F8E4, "vmovlpd", "qword ptr [rax + rdi + 0x10], xmm0"),
        (0x25F8EA, "vmovupd", "xmmword ptr [rax + rdi], xmm3"),
        (0x25FB74, "call", "0x18023c1c0"),
    ]
    for rva, mnemonic, operand in pins:
        _instruction(rows, rva, mnemonic, operand)

    constants = {
        "quaternionNlerpThreshold": _rip_float(
            pe, _instruction(rows, 0x25ECEE, "vmovss", "xmm13, dword ptr [rip + 0x105b2e]"), 0.9995
        ),
        "curveSampleMaximum": _rip_float(
            pe, _instruction(rows, 0x25F464, "vmulss", "xmm3, xmm3, dword ptr [rip + 0x1051b0]"), 15.0
        ),
        "impactDepthAttenuation": _rip_float(
            pe, _instruction(rows, 0x25F5FE, "vmulss", "xmm3, xmm3, dword ptr [rip + 0x1053ee]"), 5.0
        ),
        "springIndexPhase": _rip_float(
            pe, _instruction(rows, 0x25F781, "vmulss", "xmm2, xmm1, dword ptr [rip + 0x1058af]"), 49.6198
        ),
        "springTimePhase": _rip_float(
            pe, _instruction(rows, 0x25F844, "vmulss", "xmm1, xmm6, dword ptr [rip + 0x1057f0]"), 2.4512
        ),
        "springNoiseAmplitude": _rip_float(
            pe, _instruction(rows, 0x25F87C, "vmulss", "xmm1, xmm8, dword ptr [rip + 0x104fcc]"), 0.6
        ),
    }

    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-start-semantics.v1",
        "status": "main_integration_and_spring_distance_noise_semantics_closed_two_nested_helpers_open",
        "native_gate": gate,
        "core": {
            "cpuVariant": "avx2",
            "rva": f"0x{CORE_RVA:x}",
            "bytes": CORE_BYTES,
            "sha256": CORE_SHA256,
            "dispatch": ["0x26a370 entry", "0x26a440 range", "0x25e830 core"],
        },
        "consumedScalars": ["simulationPower.z", "simulationDeltaTime"],
        "constants": constants,
        "stages": [
            {
                "name": "selection",
                "range": "0x25e8b1..0x25ea31",
                "equations": [
                    "particleIndex = stepParticleIndexArray[rangeIndex]",
                    "teamId = teamIdArray[particleIndex]",
                    "derivedVertex = particleIndex - teamData.particleChunk.startIndex + teamData.proxyCommonChunk.startIndex",
                ],
            },
            {
                "name": "base_transform_interpolation",
                "range": "0x25ec1a..0x25ef1a",
                "equations": [
                    "basePosition = oldPosition + frameInterpolation * (authoredPosition - oldPosition)",
                    "baseRotation = shortest_arc_slerp(oldRotation, authoredRotation, frameInterpolation, nlerp_threshold=0.9995)",
                ],
                "writebacks": ["basePos", "baseRot", "stepBasicPosition", "stepBasicRotation"],
            },
            {
                "name": "simulation_bypass",
                "range": "0x25ef20..0x25ef39",
                "equations": [
                    "if !(attribute & 2) and !(teamFlag1 & 0x20): velocityPos = nextPos = basePosition",
                ],
            },
            {
                "name": "inertia",
                "range": "0x25f0f1..0x25f449",
                "equations": [
                    "k = (1 - depth * depth) * parameters.inertiaDepth",
                    "translation = lerp(center.inertiaVector, center.stepVector, k)",
                    "qInertia = shortest_arc_slerp(center.inertiaRotation, center.stepRotation, k)",
                    "inertiaPosition = center.oldWorldPosition + rotate(qInertia, oldPos - center.oldWorldPosition) + translation",
                    "inertiaVelocity = rotate(qInertia, velocity) * team.velocityWeight",
                ],
            },
            {
                "name": "damping_forces_prediction",
                "range": "0x25f457..0x25f757",
                "equations": [
                    "curve = sample16(parameters.dampingCurveData, clamp01(depth))",
                    "dampedVelocity = inertiaVelocity * clamp01(1 - curve * simulationPower.z)",
                    "gravityAcceleration = parameters.worldGravityDirection * parameters.gravity * team.gravityRatio",
                    "forceMode 1/2 attenuates impactForce by 1 + 5 * (1-depth)^2; 10/11 preserves it; other modes contribute zero",
                    "newVelocity = dampedVelocity + simulationDeltaTime * team.scaleRatio * (gravityAcceleration + impactForce + windForce)",
                    "predictedPosition = inertiaPosition + simulationDeltaTime * newVelocity",
                ],
            },
            {
                "name": "spring_distance_and_noise",
                "range": "0x25f760..0x25f8c2",
                "gate": "(teamFlag1 & 0x20) && (attribute & 1)",
                "equations": [
                    "constrainedDelta = clamp_length(predictedPosition - basePosition, team.scaleRatio * spring.limitDistance)",
                    "phase = sum(predictedPosition.xyz) + 2.4512 * (team.time + 49.6198 * rangeIndex)",
                    "springFactor = max(0, springPower * (1 + 0.6 * springNoise * sin(phase)))",
                    "nextPosition = basePosition + constrainedDelta * (1 - springFactor)",
                ],
            },
            {
                "name": "normal_cone_restriction",
                "range": "0x25f9c3..0x25fbfd",
                "status": "operands_and_control_flow_closed_helper_algebra_open",
                "nestedHelperRva": "0x23c1c0",
            },
            {
                "name": "writeback",
                "range": "0x25f8c6..0x25f8ea",
                "equations": [
                    "velocityPosArray[particleIndex] = inertiaPosition",
                    "nextPosArray[particleIndex] = springAdjustedPredictedPosition",
                ],
            },
        ],
        "nested_helpers": {
            "wind": {"rva": "0x247190", "status": "call_abi_bounded_equations_open"},
            "normalConeTrig": {"rva": "0x23c1c0", "status": "call_site_bounded_equations_open"},
            "springNoiseSin": {"rva": "0x23c490", "status": "scalar_sine_role_closed"},
        },
        "implementation_boundary": {
            "solverImplemented": False,
            "retailEquivalent": False,
            "safeToImplement": [
                "selection", "base_transform_interpolation", "simulation_bypass",
                "inertia", "damping", "gravity", "impact_force_dispatch",
                "semi_implicit_prediction", "spring_distance", "spring_noise", "writeback_layout",
            ],
            "blocked": ["wind helper equations", "normal-cone helper equation", "later constraint/collision stages"],
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
            raise SystemExit("Simulation Start semantics contract differs from regenerated output")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
