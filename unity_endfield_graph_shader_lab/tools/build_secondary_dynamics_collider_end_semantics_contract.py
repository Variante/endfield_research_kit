#!/usr/bin/env python3
"""Pin Collider End's exact current-to-previous transform snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_collider_end_semantics_contract.json"
)
CORE_RVA = 0x24A1A0
CORE_BYTES = 117
CORE_SHA256 = "fe354aabb5d9e1763b597a9f72608fe0a9ee62ab962ef451ea6515cf6137d97c"


def _require(rows: dict[int, Any], rva: int, mnemonic: str, operand: str) -> None:
    row = rows.get(rva)
    if row is None or row.mnemonic != mnemonic or row.op_str != operand:
        actual = "missing" if row is None else f"{row.mnemonic} {row.op_str}"
        raise burst.ContractError(f"Collider End instruction drift at 0x{rva:x}: {actual}")


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    pe = burst._pe_exports(Path(gate["libBurstGenerated"]["path"]))
    _, instructions = burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    rows = {ins.address - pe["imageBase"]: ins for ins in instructions}
    for pin in (
        (0x24A1A5, "mov", "rax, qword ptr [rcx + 0x50]"),
        (0x24A1D0, "movsxd", "r11, dword ptr [rdx]"),
        (0x24A1DF, "vmovups", "xmm0, xmmword ptr [r8 + rsi]"),
        (0x24A1EC, "vmovsd", "qword ptr [r9 + rsi + 0x10], xmm1"),
        (0x24A1F3, "vmovups", "xmmword ptr [r9 + rsi], xmm0"),
        (0x24A203, "vmovups", "xmmword ptr [rcx + r11], xmm0"),
        (0x24A210, "jne", "0x18024a1d0"),
    ):
        _require(rows, *pin)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-collider-end-semantics.v1",
        "status": "collider_transform_snapshot_equations_closed_not_contact_solver",
        "nativeGate": gate,
        "export": "b44b8d6a5416f62541c69d9812961578",
        "functionPointerSlotRva": "0x3c6060",
        "core": {
            "cpuVariant": "avx2",
            "entryRva": "0x24a030",
            "rva": f"0x{CORE_RVA:x}",
            "bytes": CORE_BYTES,
            "sha256": CORE_SHA256,
            "fileOffset": "0x2495a0",
        },
        "payload": [
            {"offset": "0x0", "field": "jobColliderIndexList", "element": "int32", "strideBytes": 4},
            {"offset": "0x10", "field": "nowPositions", "element": "double3", "strideBytes": 24},
            {"offset": "0x20", "field": "nowRotations", "element": "quaternion", "strideBytes": 16},
            {"offset": "0x30", "field": "oldPositions", "element": "double3", "strideBytes": 24},
            {"offset": "0x40", "field": "oldRotations", "element": "quaternion", "strideBytes": 16},
            {"offset": "0x50", "field": "_indexCount", "element": "int32 pointer", "strideBytes": None},
        ],
        "equations": [
            "count = *_indexCount; return when count <= 0",
            "for each k in [0,count): colliderIndex = jobColliderIndexList[k]",
            "oldPositions[colliderIndex] = nowPositions[colliderIndex]",
            "oldRotations[colliderIndex] = nowRotations[colliderIndex]",
        ],
        "nonAccesses": [
            "particle nextPos/oldPos/velocityPos",
            "friction/staticFriction",
            "collisionNormal",
            "collider type or shape data",
        ],
        "implementationBoundary": {
            "equationsClosed": True,
            "contactProducer": False,
            "contactProducerStage": "ColliderCollisionConstraint.SolverConstraint at SimulationStepUpdate+0x1060",
            "runtimeResolverObserved": False,
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
            raise SystemExit("Collider End semantics contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
