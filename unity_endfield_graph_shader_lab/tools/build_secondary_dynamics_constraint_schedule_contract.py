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
OUTPUT = SOURCE_ROOT / "secondary_dynamics_constraint_schedule_contract.json"
SOLVER_INPUTS_SHA256 = "1f8e4a881a7f82aefe159e0596220e730653ea101e765163757cac756dfffd2b"
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
    rows = []
    for cloth in cloths:
        data = cloth["serialized_data"]
        angle = data["angleRestorationConstraint"]
        angle_limit = data["angleLimitConstraint"]
        motion = data["motionConstraint"]
        self_collision = data["selfCollisionConstraint"]
        colliders = cloth["collider_references"]
        rows.append({
            "owner": cloth["game_object_path"],
            "proxyBindingCount": len(cloth["proxy_transform_bindings"]),
            "colliderReferenceCount": len(colliders),
            "activeFamilies": {
                "tether": data["tetherConstraint"]["distanceCompression"] > 0,
                "distance": data["distanceConstraint"]["stiffness"]["value"] > 0,
                "angle": bool(angle["useAngleRestoration"] or angle_limit["useAngleLimit"]),
                "triangleBending": data["triangleBendingConstraint"]["stiffness"] > 0,
                "colliderCollision": bool(data["colliderCollisionConstraint"]["mode"] and colliders),
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
        },
        "orderedCalls": call_rows,
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
            "requiredForAllOwners": ["tether", "distance", "angle", "triangleBending", "springPrediction"],
            "requiredForOwnersWithColliderReferences": "colliderCollision",
            "authoredNoOpFamilies": ["motion", "selfCollision"],
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
