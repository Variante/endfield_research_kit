#!/usr/bin/env python3
"""Pin the Endminf Point-mode capsule collision equations and Edge exclusion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_point_collision_semantics_contract.json"
)
POINT_RVA = 0x2FCDA0
POINT_BYTES = 3660
POINT_SHA256 = "bead77afdd711f8049af5b48df8eed513a7deeb74285be97dcd8cdf4c9a75b1d"
EDGE_RVA = 0x307D80
EDGE_BYTES = 4296
EDGE_SHA256 = "3c85d4e00fe318982d0068310719c0823c43170aefd5eed64fc8b3db0e56638f"


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    burst._exact_rva_span(pe, POINT_RVA, POINT_BYTES, POINT_SHA256)
    burst._exact_rva_span(pe, EDGE_RVA, EDGE_BYTES, EDGE_SHA256)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-point-collision-semantics.v1",
        "status": "endminf_point_capsule_projection_closed_and_edge_excluded",
        "nativeGate": gate,
        "kernels": {
            "point": {
                "export": "6a5470d135bde394bed7e7182cdf7c65",
                "cpuVariant": "avx2",
                "rva": f"0x{POINT_RVA:x}",
                "bytes": POINT_BYTES,
                "sha256": POINT_SHA256,
                "capsuleRoutineInline": True,
            },
            "edge": {
                "export": "5d2de5c2427baff59f278070e45d3123",
                "cpuVariant": "avx2",
                "rva": f"0x{EDGE_RVA:x}",
                "bytes": EDGE_BYTES,
                "sha256": EDGE_SHA256,
                "excludedByEndminfMode": True,
            },
        },
        "modeBoundary": {
            "point": 1,
            "edge": 2,
            "endminfAuthoredModes": {
                "MC_Ribbon2": 1,
                "Hair": 1,
                "MC_Ribbon": 1,
                "MC_Coat": 1,
            },
            "ownersUsingPointCapsules": ["MC_Ribbon2", "MC_Ribbon", "MC_Coat"],
            "ownersWithoutColliderReferences": ["Hair"],
            "edgeTopologyDoesNotOverrideMode": True,
        },
        "arguments": [
            {"index": 1, "name": "stepParticleIndexArray", "strideBytes": 4},
            {"index": 2, "name": "teamDataArray", "strideBytes": 464},
            {"index": 3, "name": "parameterArray", "strideBytes": 808},
            {"index": 4, "name": "attributes", "strideBytes": 1},
            {"index": 5, "name": "vertexDepths", "strideBytes": 4},
            {"index": 6, "name": "teamIdArray", "strideBytes": 2},
            {"index": 7, "name": "nextPosArray", "strideBytes": 24},
            {"index": 8, "name": "frictionArray", "strideBytes": 4},
            {"index": 9, "name": "collisionNormalArray", "strideBytes": 12},
            {"index": 10, "name": "velocityPosArray", "strideBytes": 24},
            {"index": 11, "name": "basePosArray", "strideBytes": 24},
            {"index": 12, "name": "colliderFlagArray", "strideBytes": 1},
            {"index": 13, "name": "colliderWorkDataArray", "strideBytes": 184},
            {"index": 14, "name": "rangeIndex", "strideBytes": None},
        ],
        "collider": {
            "enabledGate": "(flag & 0x30) == 0x30",
            "typeMask": "flag & 0x0f",
            "capsuleTypes": [2, 3, 4, 5, 6, 7],
            "workData": {
                "strideBytes": 184,
                "aabbMin": "0x00 double3",
                "aabbMax": "0x18 double3",
                "radius": "0x30 float2",
                "oldEndpoints": "0x38/0x50 double3",
                "newEndpoints": "0x68/0x80 double3",
                "inverseOldRotation": "0x98 float4",
                "currentRotation": "0xa8 float4",
            },
        },
        "selection": [
            "require team.colliderCount > 0 and colliderCollisionConstraint.mode == 1",
            "require (attribute & 3) != 0 and (attribute & 0x10) == 0",
            "require movable unless team.flag has BoneSpring bit 0x2000",
            "particle radius is max(interpolated 16-sample depth curve, 1e-4) * team.scaleRatio",
            "particle AABB is P +/- 2*particleRadius",
        ],
        "capsuleProjection": [
            "t=0 for a degenerate old centerline, otherwise clamp(float(dot(P-A0,A1-A0)/dot(A1-A0,A1-A0)),0,1)",
            "old offset P-lerp(A0,A1,t) is rotated by inverseOldRotation into collider-local space",
            "normal=normalize(rotate(currentRotation,localOffset)); new center=lerp(B0,B1,t)",
            "surface=newCenter+normal*(lerp(r0,r1,t)+particleRadius); dist=dot(P-surface,normal)",
            "when dist<0 projected=P-normal*dist; otherwise projected=P",
        ],
        "accumulation": [
            "for dist<=0 accumulate projected-P and normal, then average contacts",
            "final correction=(addPos/addCount)*min(length(addNormal/addCount),1), or zero when normal length<1e-8",
            "for dist<=particleRadius accumulate contact normal and minimum distance",
            "friction=max(oldFriction,1-clamp(minDistance/particleRadius,0,1)); collisionNormal=normalize(sum)",
            "otherwise collisionNormal is written as zero",
            "BoneSpring additionally adds raw addPos to velocityPos when addCount>0",
        ],
        "writeBoundary": {
            "nextPosAlwaysWrittenForSelectedParticle": True,
            "collisionNormalAlwaysWrittenForSelectedParticle": True,
            "frictionConditionallyIncreased": True,
            "basePosReadOnly": True,
        },
        "implementationBoundary": {
            "equationsClosed": True,
            "helperGap": False,
            "goldenVectorsCaptured": True,
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
            raise SystemExit("Point collision semantics contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
