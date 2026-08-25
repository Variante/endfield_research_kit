#!/usr/bin/env python3
"""Pin Simulation End's recovered AVX2 friction and velocity equations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_simulation_end_semantics_contract.json"
)
CORE_RVA = 0x24FA60
CORE_BYTES = 1745
CORE_SHA256 = "f623b3ca9c367210ca74998645797c72cefa6d393d708f8665788b85aba41780"


def _require(rows: dict[int, Any], rva: int, mnemonic: str, operand: str) -> Any:
    row = rows.get(rva)
    if row is None or row.mnemonic != mnemonic or row.op_str != operand:
        actual = "missing" if row is None else f"{row.mnemonic} {row.op_str}"
        raise burst.ContractError(f"Simulation End instruction drift at 0x{rva:x}: {actual}")
    return row


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    _, instructions = burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    rows = {ins.address - pe["imageBase"]: ins for ins in instructions}

    pins = [
        (0x24FADE, "movsxd", "r10, dword ptr [rbp + 0x140]"),
        (0x24FBAE, "test", "byte ptr [r11 + r15], 2"),
        (0x24FC60, "vucomiss", "xmm9, dword ptr [rip + 0x114d90]"),
        (0x24FCB1, "vsubpd", "ymm4, ymm1, ymm4"),
        (0x24FD46, "vaddsd", "xmm7, xmm7, qword ptr [rip + 0x11550a]"),
        (0x24FD80, "vmovss", "dword ptr [rsi + r10*4], xmm4"),
        (0x24FD86, "vsubpd", "ymm4, ymm1, ymm6"),
        (0x24FE2A, "vmulps", "xmm2, xmm2, xmm6"),
        (0x24FE8D, "vmovss", "dword ptr [r11 + r10*4], xmm2"),
        (0x24FEFB, "vmulpd", "ymm12, ymm12, ymm2"),
        (0x24FF35, "vbroadcastsd", "ymm2, qword ptr [rsp + 0x10]"),
        (0x24FFF1, "vpermpd", "ymm5, ymm2, 0xc9"),
        (0x250086, "vaddpd", "ymm12, ymm12, ymm2"),
        (0x2500B1, "vmovss", "dword ptr [r9 + r8 + 8], xmm4"),
        (0x2500D4, "vmovss", "dword ptr [rcx + r8 + 8], xmm2"),
        (0x2500E7, "vmovupd", "xmmword ptr [rax + rdx], xmm1"),
    ]
    for pin in pins:
        _require(rows, *pin)

    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-end-semantics.v1",
        "status": "friction_speed_limit_centrifugal_and_state_write_equations_closed",
        "native_gate": gate,
        "core": {
            "cpuVariant": "avx2",
            "rva": f"0x{CORE_RVA:x}",
            "bytes": CORE_BYTES,
            "sha256": CORE_SHA256,
            "fileOffset": "0x24ee60",
            "dispatch": ["0x2630a0 entry", "0x263250 range", "0x24fa60 core"],
            "directCallCount": 0,
        },
        "argumentElementStridesBytes": [
            4, 464, 808, 696, 1, 4, 2, 24, 24, 12, 12, 24, 4, 4, 12
        ],
        "constants": {
            "contactAndAngularEpsilon": 9.99999993922529e-9,
            "speedLimitNormalizationEpsilon": 9.999999717180685e-10,
            "staticReleaseDivisor": 0.2,
            "staticMinimumLoss": 0.05,
            "staticNoContactDecay": 0.05,
            "staticAccumulation": 0.04,
            "dynamicHemisphereRemap": 0.5,
            "dynamicMemoryRetention": 0.6000000238418579,
            "centrifugalCoefficient": 0.019999999552965164,
        },
        "selection": {
            "range": "0x24fade..0x24fb7a",
            "equations": [
                "particle = stepParticleIndexArray[rangeIndex]",
                "teamId = teamIdArray[particle]",
                "proxyVertex = particle - team.particleChunk.startIndex + team.proxyCommonChunk.startIndex",
                "attribute = attributes[proxyVertex]",
                "depth = vertexDepths[proxyVertex]",
            ],
        },
        "stages": [
            {
                "name": "inactive_bypass",
                "range": "0x24fbae..0x2500e7",
                "gate": "(attribute & 2) == 0 and (team.flag & 0x2000) == 0",
                "equations": [
                    "realVelocity[particle] = float3((nextPos[particle] - oldPos[particle]) / dt)",
                    "oldPos[particle] = nextPos[particle]",
                ],
                "nonWrites": ["velocity", "friction", "staticFriction", "nextPos", "velocityPos", "collisionNormal"],
            },
            {
                "name": "static_friction",
                "range": "0x24fbfc..0x24fd80",
                "gate": "dot(N,N) > 1e-8 and friction > 0 and team.scaleRatio * parameters.staticFriction > 0",
                "equations": [
                    "delta = P - O; tangent = delta - N * dot(N, delta)",
                    "tangentSpeed = length(tangent) / dt",
                    "threshold = team.scaleRatio * parameters.staticFriction",
                    "if threshold > tangentSpeed: sf += 0.04",
                    "else: sf -= max((tangentSpeed - threshold) / 0.2, 0.05)",
                    "if the contact gate fails: sf -= 0.05",
                    "sf = clamp(sf, 0, 1)",
                    "Pprime = P - tangent * sf; VPprime = VP - tangent * sf",
                    "staticFriction[particle] = float(sf)",
                ],
                "normalBoundary": "N is assumed normalized; the core neither normalizes it nor divides by dot(N,N)",
            },
            {
                "name": "initial_velocity_and_dynamic_friction",
                "range": "0x24fd86..0x24fe8d",
                "equations": [
                    "v0 = (Pprime - VPprime) / dt; speed0Squared = dot(v0,v0)",
                    "direction0 = speed0Squared > 1e-8 ? normalize(float3(v0)) : 0",
                    "when friction > 1e-8 and dot(N,N) > 1e-8 and parameters.dynamicFriction > 0 and speed0Squared >= 1e-8: hemisphere=0.5*dot(N,direction0)+0.5; strength=clamp(parameters.dynamicFriction*friction,0,1); v1=v0*(1-strength*(1-hemisphere*hemisphere))",
                    "otherwise v1 = v0",
                    "friction[particle] = friction * 0.6000000238418579",
                ],
                "precisionBoundary": "direction0 is normalized after float3 conversion and remains the pre-friction direction for centrifugal alignment",
            },
            {
                "name": "particle_speed_limit",
                "range": "0x24fe93..0x24fefb",
                "gate": "parameters.particleSpeedLimit >= 0",
                "equations": [
                    "limit = parameters.particleSpeedLimit * team.scaleRatio",
                    "if length(v1) > limit and length(v1) > 9.999999717180685e-10: v2 = v1 * limit / length(v1); else v2 = v1",
                ],
            },
            {
                "name": "center_centrifugal_effect",
                "range": "0x24ff06..0x250086",
                "gate": "center.angularVelocity > 1e-8 and parameters.centrifualAcceleration > 1e-8 and speed0Squared >= 1e-8",
                "equations": [
                    "radial = (Pprime-center.nowWorldPosition) - axis*dot(axis,Pprime-center.nowWorldPosition)",
                    "when length(radial) > 1e-8: radialDirection=radial/length(radial); rotationTangent=normalize(cross(axis,radialDirection)); alignment=clamp(dot(rotationTangent,direction0),0,1)",
                    "angularMagnitude = length(radial) * center.angularVelocity^2 * (2-depth) * alignment * parameters.centrifualAcceleration * 0.019999999552965164",
                    "vFinal = v2 + radialDirection * angularMagnitude",
                ],
                "axisBoundary": "center.rotationAxis is assumed normalized; no denominator or normalization is applied",
            },
            {
                "name": "final_state_writeback",
                "range": "0x25008f..0x2500e7",
                "equations": [
                    "active only: velocity[particle] = float3(vFinal * team.velocityWeight)",
                    "both paths: realVelocity[particle] = float3((Pprime - O) / dt)",
                    "both paths: oldPos[particle] = Pprime",
                ],
                "nonWrites": ["nextPos", "velocityPos", "collisionNormal"],
            },
        ],
        "implementation_boundary": {
            "solverImplemented": False,
            "retailEquivalent": False,
            "equationsClosed": True,
            "helperGap": False,
            "goldenVectorsCaptured": False,
            "requiresExactFloatDoubleConversionOrder": True,
            "requiresBurstMinMaxNaNBehavior": True,
            "upstreamStagesRequired": ["constraint projection", "collider contact generation"],
            "downstreamStageRequired": "central transform writeback",
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
            raise SystemExit("Simulation End semantics contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
