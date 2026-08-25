#!/usr/bin/env python3
"""Pin the active Endminf AngleConstraint AVX2 equations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_angle_semantics_contract.json"
)
SPANS = {
    "core": (0x303D40, 6480, "d3d5d8f685a57d0495d39a5068d8bae97db9fae0b247235a734293264edd2666"),
    "rangeWrapper": (0x3108B0, 334, "362a8deabacb21f171f513ee892cabccfc47c1bd6a565d2b0d8ffd67dbaafc34"),
    "sincos": (0x1E5D30, 521, "3021151e64547f2cc7e4266b846da35bbb8eef05f00d864a357f9757e730f0a6"),
    "largeReducer": (0x1DE840, 1134, "4e59a40ed0e7702288ddad778c7048e66844dd9f29e024b920961257c082537a"),
}


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    for rva, byte_count, sha256 in SPANS.values():
        burst._exact_rva_span(pe, rva, byte_count, sha256)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-angle-semantics.v1",
        "status": "three_sweep_limit_restoration_and_scratch_writeback_closed",
        "nativeGate": gate,
        "dispatch": {
            "export": "1835a4d768d0158271d1bcd27c64126f",
            "dispatchSlotRva": "0x3c49d0",
            "entryRva": "0x310300",
            "coreCallRva": "0x3109d9",
        },
        "spans": {
            name: {"rva": f"0x{rva:x}", "bytes": size, "sha256": digest}
            for name, (rva, size, digest) in SPANS.items()
        },
        "arguments": [
            "simulationPower.float4.w", "stepBaseLineIndex.uint32", "TeamData[464]",
            "ClothParameters[808]", "attributes.byte", "vertexDepths.float",
            "vertexParentIndices.int32", "baseLineStartDataIndices.uint16",
            "baseLineDataCounts.uint16", "baseLineData.uint16", "nextPos.double3",
            "velocityPos.double3", "friction.float", "stepBasicPosition.double3",
            "stepBasicRotation.float4", "lengthBuffer.float", "localPos.float3",
            "localRot.float4", "rotationBuffer.float4", "restorationVector.float3",
            "rangeIndex.int32",
        ],
        "fields": {
            "teamGravityDot": "TeamData+0x44",
            "teamProxyChunk": "TeamData+0x124",
            "teamBaseLineChunk": "TeamData+0x164",
            "teamParticleChunk": "TeamData+0x174",
            "useRestoration": "ClothParameters+0x140",
            "restorationCurve16": "ClothParameters+0x144",
            "restorationVelocityAttenuation": "ClothParameters+0x184",
            "restorationGravityFalloff": "ClothParameters+0x188",
            "useLimit": "ClothParameters+0x18c",
            "limitCurve16": "ClothParameters+0x190",
            "limitStiffness": "ClothParameters+0x1d0",
        },
        "selection": [
            "teamId=packed>>16; baseLineIndex=packed&0xffff",
            "return when restoration and limit are both disabled, or baseline count is zero",
            "process children baseline-forward only when child attribute has movable bit 2",
            "parent correction is independently gated by the parent's movable bit 2",
        ],
        "precompute": [
            "root rotationBuffer receives stepBasicRotation[root]",
            "each child rotationBuffer receives stepBasicRotation[child]",
            "limit stores current parent-child length, parent-local normalized basic direction, and parent-local basic rotation",
            "restoration stores float3(stepBasicPosition[child]-stepBasicPosition[parent])",
            "precompute normalization has no zero-length guard",
        ],
        "shared": {
            "sweeps": 3,
            "sweepBlend": "float32(sweep*0.5f*0.4f+0.1f), producing float paths near 0.1,0.3,0.5",
            "mobility": "float32(1 / float32(1 + float32(3*friction)))",
            "curve": "16-sample float interpolation uses clamped index but original depth in fraction",
            "acos": "four inlined Burst asin-polynomial transforms; no libm acos and no FMA",
            "axisAngle": "float axis/angle and pinned Burst sincos at angle/2; quaternion rotation of double3 promotes components to double",
            "parallelEpsilon": 9.999999974752427e-7,
            "antiparallelPi": 3.1415927410125732,
        },
        "limit": [
            "v=(P-Q)/length(P-Q) * (length(P-Q)+0.5*(restLength-length(P-Q)))",
            "u=rotate(rotationBuffer[parent],localPos[child]); limitRad=float32(Sample16(limitCurve,depth)*0.01745329238474369f)",
            "when outside, beta=phi+double(limitStiffness)*(double(limitRad)-phi) and rotate v toward u by the remaining excess",
            "childTarget=Q+0.4000000059604645*v+0.6000000238418579*vLimit",
            "childCorr=mobility(childFriction)*(childTarget-P); velocityPos child adds 0.8999999761581421*childCorr",
            "active parent adds mobility(parentFriction)*0.4000000059604645*(v-vLimit), with the same velocity ratio",
            "rotationBuffer child is updated from the corrected direction and parent/local rotations",
        ],
        "restoration": [
            "runs after limit and sees its immediate position writes",
            "rotate current child-parent direction toward restorationVector by theta=angleBasis*double(strength)",
            "strength=clamp(curve*simulationPower.w,0,1)*float32((1-falloff)+gravityDot*falloff), with no final clamp",
            "mixed=t*d+(1-t)*dRot",
            "child uses parent-friction mobility: mobility(parent)*(Q+mixed-P)",
            "active parent uses child-friction mobility*t*(d-dRot)",
            "both velocityPos writes use double(restorationVelocityAttenuation)",
        ],
        "endminf": {
            "restorationOwners": ["MC_Ribbon2", "Hair", "MC_Ribbon", "MC_Coat"],
            "limitOwners": ["Hair"],
            "hairBaselineCount": 8,
            "hairLimitStiffness": 1.0,
            "hairGravityFalloff": 0.0,
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
            raise SystemExit("Angle semantics contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
