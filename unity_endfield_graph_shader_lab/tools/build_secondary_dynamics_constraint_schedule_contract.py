#!/usr/bin/env python3
"""Pin the managed constraint-call order and Endminf's authored requirements."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

import build_secondary_dynamics_schedule_contract as schedule


LAB_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
SOLVER_INPUTS = SOURCE_ROOT / "secondary_dynamics_solver_inputs.json"
PAYLOAD_DECODE = SOURCE_ROOT / "secondary_dynamics_payload_decode.json"
OUTPUT = SOURCE_ROOT / "secondary_dynamics_constraint_schedule_contract.json"
SOLVER_INPUTS_SHA256 = "1f8e4a881a7f82aefe159e0596220e730653ea101e765163757cac756dfffd2b"
PAYLOAD_DECODE_SHA256 = "3e1841d21c8e249b505ca74379632b8ab308a1ffedc166130206a9f706737e35"
SIMULATION_STEP_VA = 0x182F8F430
SIMULATION_STEP_BYTES = 5968
SIMULATION_STEP_SHA256 = "5106aa8354dfe1d73e8a4ecb6a693cf8586938da5d456f7fc748267e08743335"

CALLS = (
    (0x07DC, 0x182F8E710, "ColliderManager.CreateUpdateColliderList", None),
    (0x0813, 0x183A95170, "ColliderManager.StartSimulationStep", None),
    (0x0FB8, 0x182F8DF00, "TetherConstraint.SolverConstraint", 0x98),
    (0x0FE2, 0x182F90C60, "DistanceConstraint.SolverConstraint", 0x88),
    (0x100C, 0x1830A2120, "AngleConstraint.SolverConstraint", 0xA0),
    (0x1036, 0x182F8ED70, "TriangleBendingConstraint.SolverConstraint", 0x90),
    (0x1060, 0x182F8EF20, "ColliderCollisionConstraint.SolverConstraint", 0xB0),
    (0x108A, 0x182F90C60, "DistanceConstraint.SolverConstraint", 0x88),
    (0x10B4, 0x182F8DA50, "MotionConstraint.SolverConstraint", 0xB8),
    (0x111F, 0x182F91300, "SelfCollisionConstraint.SolverRuntimeSelfCollision", 0xC0),
    (0x113C, 0x182F91240, "SelfCollisionConstraint.SolveIntersect", 0xC0),
    (0x14A4, 0x182F8EA60, "ColliderManager.EndSimulationStep", None),
)

BURST_KERNELS = (
    ("tether", "5f353c4e9c4136cbe284ba1795d08c96", 0x29F7D0, 648, "39f9eb3cd9771cbd921c9091d3821fedd510b1efc9b86161713a9010fd2c7b4a"),
    ("distance", "166b2138a31dc6d21b37fb45b233bcbc", 0x321EF0, 1624, "bca4c3f13dff30f5de4cdc982372849514c7a3cd21641e82cf0ecca536764a1c"),
    ("angle", "1835a4d768d0158271d1bcd27c64126f", 0x303D40, 6480, "d3d5d8f685a57d0495d39a5068d8bae97db9fae0b247235a734293264edd2666"),
    ("triangleBending", "542bcd5aaaa49ef7126b0d6322cf8e33", 0x2A36B0, 2019, "2f9387d6e1f0010b1958e06e3a1f71c2f0e26284156124120ad4f1d86d59d05b"),
    ("triangleAggregate", "18a84ab1967a6a10c557a91c565be282", 0x26F010, 290, "67ac6c9cb26df5d1db9dce4c0f8e61daf0e0241eea0e808f89202698e49fbbb6"),
    ("pointCollider", "6a5470d135bde394bed7e7182cdf7c65", 0x2FCDA0, 3660, "bead77afdd711f8049af5b48df8eed513a7deeb74285be97dcd8cdf4c9a75b1d"),
    ("edgeCollider", "5d2de5fa1d3044afb09aaa1af2a12205", 0x307D80, 4296, "3c85d4e00fe318982d0068310719c0823c43170aefd5eed64fc8b3db0e56638f"),
    ("motion", "506453e9c91acf679338d5b09990e7d8", 0x2FE180, 1804, "adf914f3366a63b0faed668f5fbcf7576d722bb95760571daea506fcd60d1c33"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _endminf_requirements() -> list[dict[str, Any]]:
    actual = _sha256(SOLVER_INPUTS)
    if actual != SOLVER_INPUTS_SHA256:
        raise schedule.ContractError(f"solver-input drift: {actual}")
    payload = json.loads(SOLVER_INPUTS.read_text(encoding="utf-8"))
    cloths = payload["actors"]["endminf"]["cloths"]
    payload_actual = _sha256(PAYLOAD_DECODE)
    if payload_actual != PAYLOAD_DECODE_SHA256:
        raise schedule.ContractError(f"payload-decode drift: {payload_actual}")
    decoded = json.loads(PAYLOAD_DECODE.read_text(encoding="utf-8"))
    decoded_by_owner = {
        row["game_object_path"]: row
        for row in decoded["actors"]["endminf"]["cloths"]
    }
    rows = []
    for cloth in cloths:
        data = cloth["serialized_data"]
        angle = data["angleRestorationConstraint"]
        angle_limit = data["angleLimitConstraint"]
        motion = data["motionConstraint"]
        self_collision = data["selfCollisionConstraint"]
        collision_mode = data["colliderCollisionConstraint"]["mode"]
        colliders = cloth["collider_references"]
        arrays = decoded_by_owner[cloth["game_object_path"]]["proxy_mesh_arrays"]
        vertex_count = arrays["referenceIndices"]["count"]
        line_count = arrays["lines"]["count"]
        triangle_count = arrays["triangles"]["count"]
        rows.append({
            "owner": cloth["game_object_path"],
            "proxyBindingCount": len(cloth["proxy_transform_bindings"]),
            "colliderReferenceCount": len(colliders),
            "simulatedVertexCount": vertex_count,
            "lineCount": line_count,
            "triangleCount": triangle_count,
            "colliderCollisionMode": collision_mode,
            "authoredTriangleBendingStiffness": data["triangleBendingConstraint"]["stiffness"],
            "activeFamilies": {
                "tether": data["tetherConstraint"]["distanceCompression"] > 0,
                "distance": data["distanceConstraint"]["stiffness"]["value"] > 0,
                "angle": bool(angle["useAngleRestoration"] or angle_limit["useAngleLimit"]),
                "triangleBending": data["triangleBendingConstraint"]["stiffness"] > 0 and triangle_count > 0,
                "colliderCollision": bool(collision_mode == 1 and colliders),
                "edgeColliderCollision": bool(collision_mode == 2 and colliders and line_count > 0),
                "motion": bool(motion["useMaxDistance"] or motion["useBackstop"]),
                "selfCollision": self_collision["selfMode"] != 0,
                "springPrediction": bool(data["springConstraint"]["useSpring"]),
            },
        })
    return rows


def build_contract() -> dict[str, Any]:
    gate = schedule._gate(None, None)
    _, native = schedule._helpers()
    pe = native.PeImage(Path(gate["gameAssembly"]["path"]))
    body = pe.bytes_at_va(SIMULATION_STEP_VA, SIMULATION_STEP_BYTES)
    if hashlib.sha256(body).hexdigest() != SIMULATION_STEP_SHA256:
        raise schedule.ContractError("SimulationStepUpdate body drift")
    decoded = {ins.address - SIMULATION_STEP_VA: ins for ins in Cs(CS_ARCH_X86, CS_MODE_64).disasm(body, SIMULATION_STEP_VA)}
    call_rows = []
    for order, (offset, target, method, field_offset) in enumerate(CALLS, 1):
        ins = decoded.get(offset)
        expected_operand = f"0x{target:x}"
        if ins is None or ins.mnemonic != "call" or ins.op_str != expected_operand:
            actual = "missing" if ins is None else f"{ins.mnemonic} {ins.op_str}"
            raise schedule.ContractError(f"constraint call drift at +0x{offset:x}: {actual}")
        call_rows.append({
            "order": order,
            "callOffset": f"0x{offset:x}",
            "targetVa": f"0x{target:x}",
            "method": f"BeyondDynamicBone.{method}",
            "simulationManagerObjectOffset": f"0x{field_offset:x}" if field_offset is not None else None,
        })

    burst_gate = schedule._load(
        "constraint_burst_export",
        LAB_ROOT / "tools/build_secondary_dynamics_burst_export_contract.py",
    )
    burst_pe = burst_gate._pe_exports(Path(burst_gate._native_gate(None, None)["libBurstGenerated"]["path"]))
    kernel_rows = []
    for name, export, rva, byte_count, digest in BURST_KERNELS:
        burst_gate._exact_rva_span(burst_pe, rva, byte_count, digest)
        kernel_rows.append({
            "name": name,
            "export": export,
            "cpuVariant": "avx2",
            "coreRva": f"0x{rva:x}",
            "bytes": byte_count,
            "sha256": digest,
        })

    owners = _endminf_requirements()
    required = {
        family: [row["owner"] for row in owners if row["activeFamilies"][family]]
        for family in owners[0]["activeFamilies"]
    }
    return {
        "schema": "endfield.charinfo.secondary-dynamics-constraint-schedule.v1",
        "status": "managed_projection_and_collider_call_order_closed_endminf_requirements_source_bound",
        "nativeGate": gate,
        "source": {
            "simulationStepUpdate": {
                "va": f"0x{SIMULATION_STEP_VA:x}",
                "bytes": SIMULATION_STEP_BYTES,
                "sha256": SIMULATION_STEP_SHA256,
            },
            "solverInputs": {
                "path": SOLVER_INPUTS.relative_to(LAB_ROOT.parent).as_posix(),
                "sha256": SOLVER_INPUTS_SHA256,
            },
            "payloadDecode": {
                "path": PAYLOAD_DECODE.relative_to(LAB_ROOT.parent).as_posix(),
                "sha256": PAYLOAD_DECODE_SHA256,
            },
        },
        "orderedCalls": call_rows,
        "burstKernels": kernel_rows,
        "projectionOrder": [
            "Tether",
            "Distance pass 1",
            "Angle",
            "Triangle Bending",
            "Collider Collision",
            "Distance pass 2",
            "Motion",
            "Self Collision runtime",
            "Self Collision intersection",
        ],
        "distancePassCount": 2,
        "endminfOwners": owners,
        "endminfRequiredOwnersByFamily": required,
        "endminfBoundary": {
            "requiredForAllOwners": ["tether", "distance", "angle", "springPrediction"],
            "requiredForOwnersWithColliderReferences": "colliderCollision",
            "authoredOrTopologyNoOpFamilies": ["triangleBending", "motion", "selfCollision"],
            "colliderModeBoundary": "all four owners author Point mode 1; three owners have capsule references, Hair has none",
            "edgeColliderBoundary": "Edge requires mode 2, so Endminf line-edge topology does not activate the Edge collision kernel",
            "hairAngleLimitEnabled": owners[1]["activeFamilies"]["angle"],
        },
        "implementationBoundary": {
            "managedCallOrderClosed": True,
            "endminfAuthoredActivationClosed": True,
            "constraintBurstNumericsClosed": False,
            "colliderContactNumericsClosed": False,
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
            raise SystemExit("constraint schedule contract differs")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
