#!/usr/bin/env python3
"""Pin the active Endminf DistanceConstraint AVX2 equations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_distance_semantics_contract.json"
)
CORE_RVA = 0x321EF0
CORE_BYTES = 1624
CORE_SHA256 = "bca4c3f13dff30f5de4cdc982372849514c7a3cd21641e82cf0ecca536764a1c"


def _require(rows: dict[int, Any], rva: int, mnemonic: str, operand: str) -> None:
    row = rows.get(rva)
    if row is None or row.mnemonic != mnemonic or row.op_str != operand:
        actual = "missing" if row is None else f"{row.mnemonic} {row.op_str}"
        raise burst.ContractError(f"Distance instruction drift at 0x{rva:x}: {actual}")


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    _, instructions = burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    rows = {ins.address - pe["imageBase"]: ins for ins in instructions}
    for pin in (
        (0x321F66, "movsxd", "r10, dword ptr [rbp + 0x2b0]"),
        (0x322187, "vmulss", "xmm10, xmm0, dword ptr [rip + 0x4248d]"),
        (0x322239, "vdivss", "xmm8, xmm3, xmm2"),
        (0x322418, "vdivss", "xmm2, xmm3, xmm2"),
        (0x32246E, "test", "r13d, r13d"),
        (0x32249D, "vmovupd", "xmmword ptr [rbx + r8], xmm1"),
        (0x3224CE, "vmovupd", "xmmword ptr [rax + r8], xmm0"),
        (0x3224DA, "vmovlpd", "qword ptr [rax + r8 + 0x10], xmm0"),
    ):
        _require(rows, *pin)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-distance-semantics.v1",
        "status": "two_pass_distance_projection_and_velocity_position_writeback_closed",
        "nativeGate": gate,
        "core": {
            "export": "166b2138a31dc6d21b37fb45b233bcbc",
            "ordinal": 53,
            "cpuVariant": "avx2",
            "rva": f"0x{CORE_RVA:x}",
            "bytes": CORE_BYTES,
            "sha256": CORE_SHA256,
            "directCallCount": 0,
        },
        "arguments": [
            {"index": 1, "name": "simulationPower", "strideBytes": 16, "component": "y"},
            {"index": 2, "name": "stepParticleIndexArray", "strideBytes": 4},
            {"index": 3, "name": "teamDataArray", "strideBytes": 464},
            {"index": 4, "name": "parameterArray", "strideBytes": 808},
            {"index": 5, "name": "attributes", "strideBytes": 1},
            {"index": 6, "name": "depthArray", "strideBytes": 4},
            {"index": 7, "name": "teamIdArray", "strideBytes": 2},
            {"index": 8, "name": "nextPosArray", "strideBytes": 24},
            {"index": 9, "name": "basePosArray", "strideBytes": 24},
            {"index": 10, "name": "velocityPosArray", "strideBytes": 24},
            {"index": 11, "name": "frictionArray", "strideBytes": 4},
            {"index": 12, "name": "indexArray", "strideBytes": 4},
            {"index": 13, "name": "dataArray", "strideBytes": 2},
            {"index": 14, "name": "distanceArray", "strideBytes": 4},
            {"index": 15, "name": "rangeIndex", "strideBytes": None},
        ],
        "fields": {
            "teamFlag": "TeamData+0x0",
            "teamInitScaleX": "TeamData+0x54",
            "teamScaleRatio": "TeamData+0x60",
            "teamAnimationPoseRatio": "TeamData+0xe8",
            "teamProxyCommonChunk": "TeamData+0x124",
            "teamParticleChunk": "TeamData+0x174",
            "teamDistanceStartChunk": "TeamData+0x190",
            "teamDistanceDataChunk": "TeamData+0x198",
            "restorationStiffness16": "ClothParameters+0xf4",
            "velocityAttenuation": "ClothParameters+0x134",
        },
        "selection": [
            "particle = stepParticleIndexArray[rangeIndex]; team = teamDataArray[teamIdArray[particle]]",
            "localVertex = particle - team.particleChunk.startIndex; proxyVertex = localVertex + team.proxyCommonChunk.startIndex",
            "return when distanceStartChunk.dataLength == 0 or (attribute & 3) == 0",
            "return when (attribute & 2) == 0 and (team.flag & 0x2000) == 0",
            "packed = indexArray[distanceStartChunk.startIndex + localVertex]; return when packed < 0x100000",
            "constraintCount = packed >> 20; constraintStart = distanceDataChunk.startIndex + (packed & 0xfffff)",
        ],
        "binary32": [
            "u=clamp(depth,0,1)*15; q=trunc(u); q1=min(q+1,15)",
            "fraction=(depth-float(q)*0.06666667014360428)/0.06666667014360428; curve=clamp(R[q]+fraction*(R[q1]-R[q]),0,1)",
            "baseStiffness=simulationPower.y*curve; signedRest>0 uses full stiffness, otherwise half, then clamp to [0,1]",
            "dynamic denominator=1+3*friction+5*(1-depth)^2; fixed denominator is 10 under team flag 0x2000, otherwise 50",
            "wi=1/denominatorCurrent; wj=1/denominatorNeighbor; weightSum=float(wi+wj)",
            "referenceLength=float(abs(signedRest)*float(initScale.x*scaleRatio))",
        ],
        "binary64": [
            "delta=Pj-Pi; length=sqrt(dot(delta,delta)); reject only when length < 9.99999993922529e-9",
            "baseLength=length(basePos[neighbor]-basePos[particle])",
            "targetLength=double(referenceLength)+(baseLength-double(referenceLength))*double(animationPoseRatio)",
            "correction=delta/length*double(edgeStiffness)*(length-targetLength)/double(weightSum)*double(wi)",
            "accumulate every nondegenerate correction and divide by acceptedCount",
        ],
        "writeback": [
            "nextPos[particle] = Pi + meanCorrection",
            "velocityPos[particle] += meanCorrection * double(velocityAttenuation)",
        ],
        "schedule": {
            "passCountPerSubstep": 2,
            "sameKernelAndEquations": True,
            "betweenPasses": ["Angle", "conditional Triangle", "Point/conditional Edge collision"],
        },
        "precision": {
            "noFma": True,
            "floatStagesRoundSeparately": True,
            "positionAndCorrectionDomain": "binary64",
        },
        "implementationBoundary": {
            "equationsClosed": True,
            "helperGap": False,
            "goldenVectorsCaptured": True,
            "solverImplemented": True,
            "solverConnectedToRuntime": False,
            "retailEquivalent": False,
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
            raise SystemExit("Distance semantics contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
