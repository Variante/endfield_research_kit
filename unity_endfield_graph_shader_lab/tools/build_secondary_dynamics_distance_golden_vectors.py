#!/usr/bin/env python3
"""Execute the pinned Burst DistanceConstraint core and publish golden vectors."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_distance_golden_vectors.json"
)
CORE_RVA = 0x321EF0
CORE_BYTES = 1624
CORE_SHA256 = "bca4c3f13dff30f5de4cdc982372849514c7a3cd21641e82cf0ecca536764a1c"
RANGE_WRAPPER_RVA = 0x322550
RANGE_WRAPPER_BYTES = 244
RANGE_WRAPPER_SHA256 = "b2aad3d1ae110f5f06e25daacf399a8efbac95fd4ab23941409d1703b531918d"

CASES: tuple[dict[str, Any], ...] = (
    {
        "name": "single_constraint_stretch",
        "next": [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
        "base": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        "constraints": [(1, 1.0)],
    },
    {
        "name": "single_constraint_compression",
        "next": [(0.0, 0.0, 0.0), (0.5, 0.0, 0.0)],
        "base": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        "constraints": [(1, 1.0)],
    },
    {
        "name": "negative_signed_rest_half_stiffness",
        "next": [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
        "base": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        "constraints": [(1, -1.0)],
    },
    {
        "name": "fractional_curve_stiffness",
        "next": [(0.0, 0.0, 0.0), (2.0, 1.0, -0.5)],
        "base": [(0.0, 0.0, 0.0), (1.0, 0.5, -0.25)],
        "constraints": [(1, 1.0)],
        "simulationPowerY": 0.8,
        "depths": [0.37, 0.62],
        "friction": [0.2, 0.4],
        "stiffnessCurve": [index / 15.0 for index in range(16)],
        "velocityAttenuation": 0.65,
    },
    {
        "name": "animation_pose_blend",
        "next": [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
        "base": [(0.0, 0.0, 0.0), (1.5, 0.0, 0.0)],
        "constraints": [(1, 1.0)],
        "animationPoseRatio": 0.25,
    },
    {
        "name": "two_constraint_mean",
        "next": [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)],
        "base": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        "constraints": [(1, 1.0), (2, 1.0)],
    },
    {
        "name": "degenerate_constraint_no_write",
        "next": [(0.125, -0.25, 0.5), (0.125, -0.25, 0.5)],
        "base": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        "constraints": [(1, 1.0)],
        "velocity": [(3.0, 4.0, 5.0), (0.0, 0.0, 0.0)],
    },
    {
        "name": "empty_packed_range_no_write",
        "next": [(-0.75, 0.5, 1.25), (2.0, 0.0, 0.0)],
        "base": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        "constraints": [],
        "velocity": [(-2.0, 7.0, 0.25), (0.0, 0.0, 0.0)],
    },
)


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _fadd(left: float, right: float) -> float:
    return _f32(_f32(left) + _f32(right))


def _fsub(left: float, right: float) -> float:
    return _f32(_f32(left) - _f32(right))


def _fmul(left: float, right: float) -> float:
    return _f32(_f32(left) * _f32(right))


def _fdiv(left: float, right: float) -> float:
    return _f32(_f32(left) / _f32(right))


def _hex3(values: tuple[float, float, float]) -> list[str]:
    return [struct.pack("<d", value).hex() for value in values]


def _defaults(case: dict[str, Any]) -> dict[str, Any]:
    count = len(case["next"])
    return {
        "simulationPowerY": _f32(case.get("simulationPowerY", 1.0)),
        "depths": [_f32(value) for value in case.get("depths", [0.0] * count)],
        "friction": [_f32(value) for value in case.get("friction", [0.0] * count)],
        "attributes": list(case.get("attributes", [2] * count)),
        "stiffnessCurve": [
            _f32(value) for value in case.get("stiffnessCurve", [1.0] * 16)
        ],
        "velocityAttenuation": _f32(case.get("velocityAttenuation", 0.7)),
        "animationPoseRatio": _f32(case.get("animationPoseRatio", 0.0)),
        "initScaleX": _f32(case.get("initScaleX", 1.0)),
        "scaleRatio": _f32(case.get("scaleRatio", 1.0)),
        "teamFlag": int(case.get("teamFlag", 0)),
        "velocity": list(case.get("velocity", case["next"])),
    }


def _weight(attribute: int, depth: float, friction: float, team_flag: int) -> float:
    if attribute & 2:
        denominator = _fadd(_fmul(friction, 3.0), 1.0)
        one_minus_depth = _fsub(1.0, depth)
        denominator = _fadd(
            denominator,
            _fmul(_fmul(one_minus_depth, one_minus_depth), 5.0),
        )
    else:
        denominator = _f32(10.0 if team_flag & 0x2000 else 50.0)
    return _fdiv(1.0, denominator)


def _curve_value(depth: float, curve: list[float]) -> float:
    clamped = min(max(_f32(depth), _f32(0.0)), _f32(1.0))
    scaled = _fmul(clamped, 15.0)
    index = math.trunc(scaled)
    next_index = min(index + 1, 15)
    step = _f32(0.06666667014360428)
    fraction = _fdiv(_fsub(depth, _fmul(float(index), step)), step)
    value = _fadd(curve[index], _fmul(fraction, _fsub(curve[next_index], curve[index])))
    return min(max(value, _f32(0.0)), _f32(1.0))


def source_port(case: dict[str, Any]) -> dict[str, Any]:
    values = _defaults(case)
    current = tuple(float(value) for value in case["next"][0])
    velocity = tuple(float(value) for value in values["velocity"][0])
    constraints = case["constraints"]
    if not constraints:
        return {"next": current, "velocityPos": velocity, "acceptedCount": 0}

    current_weight = _weight(
        values["attributes"][0], values["depths"][0], values["friction"][0],
        values["teamFlag"],
    )
    curve = _curve_value(values["depths"][0], values["stiffnessCurve"])
    base_stiffness = _fmul(values["simulationPowerY"], curve)
    scale = _fmul(values["initScaleX"], values["scaleRatio"])
    accumulated = [0.0, 0.0, 0.0]
    accepted = 0

    for neighbor, signed_rest_source in constraints:
        signed_rest = _f32(signed_rest_source)
        stiffness = base_stiffness if signed_rest > 0.0 else _fmul(base_stiffness, 0.5)
        stiffness = max(min(stiffness, _f32(1.0)), _f32(0.0))
        delta = tuple(float(case["next"][neighbor][axis]) - current[axis] for axis in range(3))
        length = math.sqrt(sum(component * component for component in delta))
        if length < 9.99999993922529e-9:
            continue
        base_delta = tuple(
            float(case["base"][neighbor][axis]) - float(case["base"][0][axis])
            for axis in range(3)
        )
        base_length = math.sqrt(sum(component * component for component in base_delta))
        reference_length = float(_fmul(abs(signed_rest), scale))
        target_length = reference_length + (
            base_length - reference_length
        ) * float(values["animationPoseRatio"])
        neighbor_weight = _weight(
            values["attributes"][neighbor], values["depths"][neighbor],
            values["friction"][neighbor], values["teamFlag"],
        )
        weight_sum = _fadd(current_weight, neighbor_weight)
        for axis in range(3):
            correction = delta[axis] * (1.0 / length)
            correction *= float(stiffness)
            correction *= length - target_length
            correction /= float(weight_sum)
            correction *= float(current_weight)
            accumulated[axis] += correction
        accepted += 1

    if accepted == 0:
        return {"next": current, "velocityPos": velocity, "acceptedCount": 0}
    correction = tuple(component / float(accepted) for component in accumulated)
    return {
        "next": tuple(current[axis] + correction[axis] for axis in range(3)),
        "velocityPos": tuple(
            velocity[axis] + correction[axis] * float(values["velocityAttenuation"])
            for axis in range(3)
        ),
        "acceptedCount": accepted,
    }


def _make_native_function(dll: Path) -> tuple[Any, Any]:
    module = ctypes.WinDLL(str(dll))
    signature = ctypes.CFUNCTYPE(
        None, *([ctypes.c_void_p] * 14), ctypes.c_int32
    )
    return module, signature(module._handle + CORE_RVA)


def _run_native(function: Any, case: dict[str, Any]) -> dict[str, Any]:
    values = _defaults(case)
    particle_count = len(case["next"])
    constraint_count = len(case["constraints"])
    buffers = [
        ctypes.create_string_buffer(16),
        ctypes.create_string_buffer(4),
        ctypes.create_string_buffer(464),
        ctypes.create_string_buffer(808),
        ctypes.create_string_buffer(max(1, particle_count)),
        ctypes.create_string_buffer(max(4, particle_count * 4)),
        ctypes.create_string_buffer(max(2, particle_count * 2)),
        ctypes.create_string_buffer(max(24, particle_count * 24)),
        ctypes.create_string_buffer(max(24, particle_count * 24)),
        ctypes.create_string_buffer(max(24, particle_count * 24)),
        ctypes.create_string_buffer(max(4, particle_count * 4)),
        ctypes.create_string_buffer(4),
        ctypes.create_string_buffer(max(2, constraint_count * 2)),
        ctypes.create_string_buffer(max(4, constraint_count * 4)),
    ]
    (simulation_power, step, team, parameters, attributes, depths, team_ids,
     next_pos, base_pos, velocity_pos, friction, index_array, data_array,
     distance_array) = buffers

    struct.pack_into("<f", simulation_power, 4, values["simulationPowerY"])
    struct.pack_into("<i", step, 0, 0)
    struct.pack_into("<Q", team, 0, values["teamFlag"])
    struct.pack_into("<f", team, 0x54, values["initScaleX"])
    struct.pack_into("<f", team, 0x60, values["scaleRatio"])
    struct.pack_into("<f", team, 0xE8, values["animationPoseRatio"])
    struct.pack_into("<i", team, 0x124, 0)
    struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<2i", team, 0x190, 0, 1)
    struct.pack_into("<i", team, 0x198, 0)
    struct.pack_into("<16f", parameters, 0xF4, *values["stiffnessCurve"])
    struct.pack_into("<f", parameters, 0x134, values["velocityAttenuation"])
    for particle in range(particle_count):
        struct.pack_into("<B", attributes, particle, values["attributes"][particle])
        struct.pack_into("<f", depths, particle * 4, values["depths"][particle])
        struct.pack_into("<h", team_ids, particle * 2, 0)
        struct.pack_into("<3d", next_pos, particle * 24, *case["next"][particle])
        struct.pack_into("<3d", base_pos, particle * 24, *case["base"][particle])
        struct.pack_into("<3d", velocity_pos, particle * 24, *values["velocity"][particle])
        struct.pack_into("<f", friction, particle * 4, values["friction"][particle])
    packed = (constraint_count << 20) if constraint_count else 0
    struct.pack_into("<I", index_array, 0, packed)
    for constraint_index, (neighbor, signed_rest) in enumerate(case["constraints"]):
        struct.pack_into("<H", data_array, constraint_index * 2, neighbor)
        struct.pack_into("<f", distance_array, constraint_index * 4, signed_rest)

    function(*(ctypes.addressof(buffer) for buffer in buffers), 0)
    return {
        "next": struct.unpack_from("<3d", next_pos, 0),
        "velocityPos": struct.unpack_from("<3d", velocity_pos, 0),
    }


def _validate_range_wrapper(pe: dict[str, Any]) -> dict[str, Any]:
    _, instructions = burst._exact_rva_span(
        pe, RANGE_WRAPPER_RVA, RANGE_WRAPPER_BYTES, RANGE_WRAPPER_SHA256
    )
    rows = {ins.address - pe["imageBase"]: ins for ins in instructions}
    pins = {
        0x322572: ("mov", "r15d, dword ptr [rax]"),
        0x3225A0: ("mov", "dword ptr [rsp + 0x70], r12d"),
        0x32261F: ("call", "0x180321ef0"),
        0x322624: ("inc", "r12d"),
    }
    for rva, expected in pins.items():
        row = rows.get(rva)
        actual = None if row is None else (row.mnemonic, row.op_str)
        if actual != expected:
            raise burst.ContractError(
                f"Distance range-wrapper ABI drift at 0x{rva:x}: {actual}"
            )
    return {
        "rva": f"0x{RANGE_WRAPPER_RVA:x}",
        "bytes": RANGE_WRAPPER_BYTES,
        "sha256": RANGE_WRAPPER_SHA256,
        "wrapperFinalArgument": "pointer to int32 range count",
        "coreArgument15": "int32 rangeIndex value",
        "evidence": [
            "wrapper loads the count through its final pointer argument",
            "wrapper stores the int32 loop counter in the core's fifteenth ABI slot",
            "core reads that slot with movsxd from a dword stack location",
        ],
    }


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    wrapper = _validate_range_wrapper(pe)
    burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    module, function = _make_native_function(dll)
    vectors = []
    for case in CASES:
        native = _run_native(function, case)
        port = source_port(case)
        if (
            _hex3(native["next"]) != _hex3(port["next"])
            or _hex3(native["velocityPos"]) != _hex3(port["velocityPos"])
        ):
            raise burst.ContractError(
                f"source DistanceConstraint transcription differs from native core: "
                f"{case['name']} native={native} source={port}"
            )
        values = _defaults(case)
        vectors.append({
            "name": case["name"],
            "input": {
                "next": [list(row) for row in case["next"]],
                "base": [list(row) for row in case["base"]],
                "velocity": [list(row) for row in values["velocity"]],
                "constraints": [
                    {"neighbor": neighbor, "signedRestFloat32": _f32(rest)}
                    for neighbor, rest in case["constraints"]
                ],
                "simulationPowerYFloat32": values["simulationPowerY"],
                "depthFloat32": values["depths"],
                "frictionFloat32": values["friction"],
                "attributes": values["attributes"],
                "stiffnessCurveFloat32": values["stiffnessCurve"],
                "velocityAttenuationFloat32": values["velocityAttenuation"],
                "animationPoseRatioFloat32": values["animationPoseRatio"],
                "initScaleXFloat32": values["initScaleX"],
                "scaleRatioFloat32": values["scaleRatio"],
                "teamFlag": values["teamFlag"],
                "rangeIndex": 0,
            },
            "output": {
                "next": list(native["next"]),
                "nextBinary64Le": _hex3(native["next"]),
                "velocityPos": list(native["velocityPos"]),
                "velocityPosBinary64Le": _hex3(native["velocityPos"]),
                "acceptedConstraintCount": port["acceptedCount"],
            },
        })
    del module
    return {
        "schema": "endfield.charinfo.secondary-dynamics-distance-golden-vectors.v1",
        "status": "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
        "nativeGate": gate,
        "rangeWrapperAbi": wrapper,
        "core": {
            "rva": f"0x{CORE_RVA:x}",
            "bytes": CORE_BYTES,
            "sha256": CORE_SHA256,
            "argument15": "int32 rangeIndex value",
        },
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": vectors,
        "boundary": {
            "nativeCoreExecuted": True,
            "sourceTranscriptionBinary64Matched": True,
            "rangeWrapperArgument15Confirmed": True,
            "caseCoverage": [
                "stretch", "compression", "negative signed rest and half stiffness",
                "fractional curve stiffness and asymmetric weights", "animation-pose blend",
                "multi-constraint averaging", "degenerate no-write", "empty packed range no-write",
            ],
            "unityPortExecuted": True,
            "unityVerifier": "EndfieldSecondaryDynamicsKernelGoldenVerifier.VerifyDistanceGoldenVectors",
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
            raise SystemExit("Distance golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
