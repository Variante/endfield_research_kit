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
SOLVER_INPUTS_SHA256 = "fe91726b102a1104ed223be0aeb9138a76d58887a79851cc70736fd0d4ed6251"
PAYLOAD_DECODE_SHA256 = "6c8eed435f2acd645d3fb3560acf7c993b5ef34c8ff2336de1a9fa87a1cbff1a"
SIMULATION_STEP_VA = 0x182F8F430
SIMULATION_STEP_BYTES = 5968
SIMULATION_STEP_SHA256 = "5106aa8354dfe1d73e8a4ecb6a693cf8586938da5d456f7fc748267e08743335"

NUMERIC_CONTRACTS = (
    (
        "tetherSemantics",
        "secondary_dynamics_tether_semantics_contract.json",
        "2e2a8aea902190c62ff2c6e730258fdede241d006e95f5793c53ab533fd756e7",
        "endfield.charinfo.secondary-dynamics-tether-semantics.v1",
        "compression_stretch_projection_and_velocity_position_writeback_closed",
    ),
    (
        "tetherGolden",
        "secondary_dynamics_tether_golden_vectors.json",
        "f4ec55d7caa7f0e4460130d8a238c1dea2cbc7d3f4aa088e5dc5e66520273f78",
        "endfield.charinfo.secondary-dynamics-tether-golden-vectors.v1",
        "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
    ),
    (
        "distanceSemantics",
        "secondary_dynamics_distance_semantics_contract.json",
        "fa0dd243a48982a79e3289b1786d30c418ff0a1ab8f9403adb440df5b041fa3c",
        "endfield.charinfo.secondary-dynamics-distance-semantics.v1",
        "two_pass_distance_projection_and_velocity_position_writeback_closed",
    ),
    (
        "distanceGolden",
        "secondary_dynamics_distance_golden_vectors.json",
        "41cb4574c9f7ea431315afe4ba9c86241ba842fa790a773516baa141b22ca23e",
        "endfield.charinfo.secondary-dynamics-distance-golden-vectors.v1",
        "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
    ),
    (
        "angleSemantics",
        "secondary_dynamics_angle_semantics_contract.json",
        "ead14c3ba8ef715fb80aede93651fc417a7a77ec47c71dd3b299a057fedd4cb4",
        "endfield.charinfo.secondary-dynamics-angle-semantics.v1",
        "three_sweep_limit_restoration_and_scratch_writeback_closed",
    ),
    (
        "angleGolden",
        "secondary_dynamics_angle_golden_vectors.json",
        "1a885ce498f96de821b26bf25100b51307262d8caa986bd1db51e92280aca99d",
        "endfield.charinfo.secondary-dynamics-angle-golden-vectors.v1",
        "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
    ),
    (
        "floatSinCosGolden",
        "secondary_dynamics_float_sincos_golden_vectors.json",
        "10374aaf8188a1d250bafb4979b45b07a96c25fe3db593f735ee83414e9eb9e3",
        "endfield.charinfo.secondary-dynamics-float-sincos-golden-vectors.v1",
        "native_helper_and_source_only_transcription_exact_for_controlled_and_boundary_cases",
    ),
    (
        "pointCollisionSemantics",
        "secondary_dynamics_point_collision_semantics_contract.json",
        "4716855d45a4acd85570072fa469e69e972b58758adb3488b0003b5a06c680ec",
        "endfield.charinfo.secondary-dynamics-point-collision-semantics.v1",
        "endminf_point_capsule_projection_closed_and_edge_excluded",
    ),
    (
        "pointCollisionGolden",
        "secondary_dynamics_point_collision_golden_vectors.json",
        "1459f81d2cf7e95d8ea25f3a978d79d9571143888fe54e90a3ea2dc0792854a0",
        "endfield.charinfo.secondary-dynamics-point-collision-golden-vectors.v1",
        "native_avx2_vectors_and_source_transcription_exact_for_bounded_point_capsule_cases",
    ),
)

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


def _numeric_constraint_coverage(
    contracts: tuple[tuple[str, str, str, str, str], ...] | None = None,
    source_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    contract_rows = NUMERIC_CONTRACTS if contracts is None else contracts
    root = SOURCE_ROOT if source_root is None else source_root
    sources: dict[str, Any] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for key, filename, expected_sha256, expected_schema, expected_status in contract_rows:
        path = root / filename
        actual_sha256 = _sha256(path)
        if actual_sha256 != expected_sha256:
            raise schedule.ContractError(
                f"numeric contract drift for {filename}: {actual_sha256}"
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != expected_schema:
            raise schedule.ContractError(f"numeric contract schema drift for {filename}")
        if payload.get("status") != expected_status:
            raise schedule.ContractError(f"numeric contract status drift for {filename}")
        payloads[key] = payload
        sources[key] = {
            "path": path.relative_to(LAB_ROOT.parent).as_posix(),
            "sha256": expected_sha256,
            "schema": expected_schema,
            "status": expected_status,
        }

    for key in ("tetherSemantics", "distanceSemantics", "angleSemantics", "pointCollisionSemantics"):
        if payloads[key].get("implementationBoundary", {}).get("equationsClosed") is not True:
            raise schedule.ContractError(f"{key} no longer closes its equations")

    golden_requirements = {
        "tetherGolden": (5, "sourceTranscriptionBinary64Matched"),
        "distanceGolden": (8, "sourceTranscriptionBinary64Matched"),
        "angleGolden": (25, "sourceTranscriptionAllWrittenBitsMatched"),
        "pointCollisionGolden": (6, "sourceTranscriptionExactBitsMatched"),
    }
    vector_counts: dict[str, int] = {}
    for key, (expected_count, exact_key) in golden_requirements.items():
        payload = payloads[key]
        boundary = payload.get("boundary", {})
        count = len(payload.get("vectors", []))
        if (
            count != expected_count
            or boundary.get("nativeCoreExecuted") is not True
            or boundary.get(exact_key) is not True
            or boundary.get("unityPortExecuted") is not True
        ):
            raise schedule.ContractError(f"{key} exact-vector boundary drift")
        vector_counts[key.removesuffix("Golden")] = count

    angle_boundary = payloads["angleGolden"].get("boundary", {})
    if (
        angle_boundary.get("orderedSweepCount") != 3
        or angle_boundary.get("orderedInterParticleWritesPreserved") is not True
        or angle_boundary.get("endminfFullBaselineVectorCount") != 18
        or angle_boundary.get("standaloneSincosTranscriptionComplete") is not True
    ):
        raise schedule.ContractError("angle ordered-sweep or Endminf baseline coverage drift")

    sincos_boundary = payloads["floatSinCosGolden"].get("boundary", {})
    if (
        sincos_boundary.get("sourceOnlyTranscriptionMatchedBitForBit") is not True
        or sincos_boundary.get("unityPortExecuted") is not True
        or sincos_boundary.get("nativeCpuVariantsExecuted") != ["x64_sse2", "avx2"]
        or sincos_boundary.get("caseCount") != 24
    ):
        raise schedule.ContractError("float sin/cos helper coverage drift")

    coverage = {
        "scope": "source-static Endminf active constraint candidate; no retail route selection",
        "cpuCandidate": "avx2",
        "closedFamilies": ["tether", "distance", "angle", "pointCollider"],
        "nativeGoldenVectorCounts": vector_counts,
        "angleEndminfBaselineVectorCount": 18,
        "floatSinCosHelper": {
            "nativeCpuVariants": ["x64_sse2", "avx2"],
            "caseCount": 24,
            "sourceAndUnityBitsClosed": True,
        },
        "sourceStaticEquationsClosed": True,
        "nativeCandidateVectorsMatched": True,
        "unityValuePortsExecuted": True,
        "selectedRetailCpuRouteProven": False,
        "runtimeSolverCompositionConnected": False,
        "transformWritebackConnected": False,
    }
    return sources, coverage


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
    numeric_sources, numeric_coverage = _numeric_constraint_coverage()
    return {
        "schema": "endfield.charinfo.secondary-dynamics-constraint-schedule.v2",
        "status": "endminf_active_constraint_candidate_equations_and_managed_order_closed_route_unobserved",
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
            "numericContracts": numeric_sources,
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
        "activeConstraintCandidate": numeric_coverage,
        "implementationBoundary": {
            "managedCallOrderClosed": True,
            "endminfAuthoredActivationClosed": True,
            "endminfActiveAvx2CandidateNumericsClosed": True,
            "constraintBurstNumericsClosed": False,
            "colliderContactNumericsClosed": False,
            "solverImplemented": False,
            "selectedRetailRouteProven": False,
            "runtimeSolverCompositionConnected": False,
            "transformWritebackConnected": False,
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
