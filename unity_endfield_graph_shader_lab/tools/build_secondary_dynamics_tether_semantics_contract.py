#!/usr/bin/env python3
"""Pin the active Endminf TetherConstraint AVX2 equations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_tether_semantics_contract.json"
)
CORE_RVA = 0x29F7D0
CORE_BYTES = 648
CORE_SHA256 = "39f9eb3cd9771cbd921c9091d3821fedd510b1efc9b86161713a9010fd2c7b4a"


def _require(rows: dict[int, Any], rva: int, mnemonic: str, operand: str) -> None:
    row = rows.get(rva)
    if row is None or row.mnemonic != mnemonic or row.op_str != operand:
        actual = "missing" if row is None else f"{row.mnemonic} {row.op_str}"
        raise burst.ContractError(f"Tether instruction drift at 0x{rva:x}: {actual}")


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    _, instructions = burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    rows = {ins.address - pe["imageBase"]: ins for ins in instructions}
    for pin in (
        (0x29F8ED, "movsxd", "r14, dword ptr [rcx]"),
        (0x29F915, "test", "byte ptr [rbx + r13], 2"),
        (0x29F91C, "mov", "r13d, dword ptr [rdi + r13*4]"),
        (0x29F961, "vsubpd", "ymm6, ymm6, ymm5"),
        (0x29F980, "vucomisd", "xmm0, xmm7"),
        (0x29F9B0, "vsubpd", "ymm8, ymm9, ymm8"),
        (0x29F9E8, "vdivsd", "xmm10, xmm7, xmm8"),
        (0x29F9ED, "vsubss", "xmm9, xmm2, dword ptr [r8 + r15 + 0xec]"),
        (0x29FA07, "vaddss", "xmm9, xmm2, dword ptr [r8 + r15 + 0xf0]"),
        (0x29F88D, "vmulpd", "ymm6, ymm6, ymm7"),
        (0x29F8A2, "vmovupd", "xmmword ptr [r11 + r14], xmm5"),
        (0x29F8C4, "vmulpd", "ymm6, ymm6, ymm7"),
        (0x29F8CC, "vmovupd", "xmmword ptr [r10 + r14], xmm5"),
    ):
        _require(rows, *pin)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-tether-semantics.v1",
        "status": "compression_stretch_projection_and_velocity_position_writeback_closed",
        "nativeGate": gate,
        "core": {
            "export": "5f353c4e9c4136cbe284ba1795d08c96",
            "cpuVariant": "avx2",
            "rva": f"0x{CORE_RVA:x}",
            "bytes": CORE_BYTES,
            "sha256": CORE_SHA256,
            "directCallCount": 0,
        },
        "arguments": [
            {"index": 1, "name": "stepParticleIndexArray", "strideBytes": 4},
            {"index": 2, "name": "teamDataArray", "strideBytes": 464},
            {"index": 3, "name": "parameterArray", "strideBytes": 808},
            {"index": 4, "name": "centerDataArray", "strideBytes": 696, "accessed": False},
            {"index": 5, "name": "attributes", "strideBytes": 1},
            {"index": 6, "name": "vertexDepths", "strideBytes": 4, "accessed": False},
            {"index": 7, "name": "vertexRootIndices", "strideBytes": 4},
            {"index": 8, "name": "teamIdArray", "strideBytes": 2},
            {"index": 9, "name": "nextPosArray", "strideBytes": 24},
            {"index": 10, "name": "velocityPosArray", "strideBytes": 24},
            {"index": 11, "name": "frictionArray", "strideBytes": 4, "accessed": False},
            {"index": 12, "name": "stepBasicPositionBuffer", "strideBytes": 24},
            {"index": 13, "name": "_indexCount", "strideBytes": None},
        ],
        "fields": {
            "teamParticleChunkStart": "TeamData+0x174",
            "teamProxyCommonChunkStart": "TeamData+0x124",
            "compressionLimit": "ClothParameters+0xec",
            "stretchLimit": "ClothParameters+0xf0",
        },
        "constants": {
            "lengthEpsilon": 9.99999993922529e-9,
            "activationWidth": 0.30000001192092896,
            "maximumActivation": 1.0,
            "velocityPositionCorrectionRatio": 0.699999988079071,
        },
        "selection": [
            "particle = stepParticleIndexArray[rangeIndex]",
            "teamId = teamIdArray[particle]",
            "proxy = particle - team.particleChunk.startIndex + team.proxyCommonChunk.startIndex",
            "skip unless (attributes[proxy] & 2) != 0",
            "rootVertex = vertexRootIndices[proxy]; skip when rootVertex < 0",
            "rootParticle = team.particleChunk.startIndex + rootVertex",
        ],
        "equations": [
            "currentDelta = nextPos[rootParticle] - nextPos[particle]; currentLength = length(currentDelta); skip when currentLength < 1e-8",
            "basicDelta = stepBasicPosition[rootParticle] - stepBasicPosition[particle]; basicLength = length(basicDelta); skip when basicLength == 0",
            "ratio = currentLength / basicLength",
            "compressionThreshold = 1 - parameters.compressionLimit; stretchThreshold = 1 + parameters.stretchLimit",
            "if ratio < compressionThreshold: targetRatio=compressionThreshold; signedError=currentLength-basicLength*targetRatio; activation=clamp((targetRatio-ratio)/0.30000001192092896,0,1)",
            "else if ratio > stretchThreshold: targetRatio=stretchThreshold; signedError=currentLength-basicLength*targetRatio; activation=clamp((ratio-targetRatio)/0.30000001192092896,0,1)",
            "else: no writes",
            "correction = currentDelta/currentLength * (signedError*activation)",
            "nextPos[particle] += correction",
            "velocityPos[particle] += correction * 0.699999988079071",
        ],
        "writeBoundary": {
            "movesOnlyChildParticle": True,
            "rootParticleUnchanged": True,
            "nextPosAndVelocityPosUseDouble3": True,
            "frictionUnchanged": True,
        },
        "implementationBoundary": {
            "equationsClosed": True,
            "helperGap": False,
            "goldenVectorsCaptured": False,
            "solverImplemented": False,
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
            raise SystemExit("Tether semantics contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
