#!/usr/bin/env python3
"""Execute the pinned Burst UpdateStepBasicPosture core and publish vectors."""

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
    "secondary_dynamics_basic_posture_golden_vectors.json"
)
CORE_RVA = 0x241AA0
CORE_BYTES = 1804
CORE_SHA256 = "1a83498696a2e50778d1aed396decdafacbae129c3ae4196daa9391497eaae98"
ENTRY_RVA = 0x241910
ENTRY_BYTES = 58
ENTRY_SHA256 = "f5d035f3bfc4f52f9740b9011d068f34792ad437e4fb2049de09457be818888d"
RANGE_RVA = 0x2421B0
RANGE_BYTES = 209
RANGE_SHA256 = "d9700e11acecd958bc1dd4bc35c0738431166df99c1d0411b9bfb461fa969939"
SIN_RVA = 0x1DE610
SIN_BYTES = 557
SIN_SHA256 = "d11fc448307689e5bf1c981bf1cae17af4604d6fa0105aa2196b162048a1c6ac"


CASES: tuple[dict[str, Any], ...] = (
    {
        "name": "root_identity_ratio_zero",
        "parents": [-1],
        "localPositions": [(0.0, 0.0, 0.0)],
        "localRotations": [(0.0, 0.0, 0.0, 1.0)],
        "basePositions": [(8.0, 9.0, 10.0)],
        "baseRotations": [(0.0, 0.0, 0.0, 1.0)],
        "stepPositions": [(1.25, -2.5, 3.75)],
        "stepRotations": [(0.0, 0.0, 0.0, 1.0)],
        "animationPoseRatio": 0.0,
    },
    {
        "name": "child_positive_scale_ratio_zero",
        "parents": [-1, 0],
        "localPositions": [(0.0, 0.0, 0.0), (1.0, 0.5, -0.25)],
        "localRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.70710677, 0.70710677)],
        "basePositions": [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
        "baseRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "stepPositions": [(10.0, -1.0, 2.0), (99.0, 99.0, 99.0)],
        "stepRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "initScale": (2.0, 3.0, 4.0),
        "scaleRatio": 0.5,
        "animationPoseRatio": 0.0,
    },
    {
        "name": "child_negative_scale_ratio_zero",
        "parents": [-1, 0],
        "localPositions": [(0.0, 0.0, 0.0), (1.0, -0.5, 0.25)],
        "localRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "basePositions": [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
        "baseRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "stepPositions": [(-3.0, 4.0, 1.0), (50.0, 50.0, 50.0)],
        "stepRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "negativeScaleDirection": (-1.0, 1.0, 1.0),
        "animationPoseRatio": 0.0,
    },
    {
        "name": "partial_pose_position_and_nlerp",
        "parents": [-1, 0],
        "localPositions": [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
        "localRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "basePositions": [(2.0, 4.0, 6.0), (6.0, 4.0, 6.0)],
        "baseRotations": [(0.0, 0.0, 0.043619387, 0.99904823), (0.0, 0.0, 0.043619387, 0.99904823)],
        "stepPositions": [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
        "stepRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "animationPoseRatio": 0.25,
    },
    {
        "name": "partial_pose_representative_slerp",
        "parents": [-1],
        "localPositions": [(0.0, 0.0, 0.0)],
        "localRotations": [(0.0, 0.0, 0.0, 1.0)],
        "basePositions": [(3.0, -2.0, 1.0)],
        "baseRotations": [(0.0, 0.70710677, 0.0, 0.70710677)],
        "stepPositions": [(1.0, 2.0, 3.0)],
        "stepRotations": [(0.0, 0.0, 0.0, 1.0)],
        "animationPoseRatio": 0.375,
    },
    {
        "name": "pose_ratio_one_early_exit",
        "parents": [-1, 0],
        "localPositions": [(0.0, 0.0, 0.0), (9.0, 9.0, 9.0)],
        "localRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "basePositions": [(7.0, 8.0, 9.0), (10.0, 11.0, 12.0)],
        "baseRotations": [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)],
        "stepPositions": [(-1.0, -2.0, -3.0), (-4.0, -5.0, -6.0)],
        "stepRotations": [(0.0, 0.0, 0.0, 1.0), (0.2, 0.3, 0.4, 0.5)],
        "animationPoseRatio": 1.0,
    },
)


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _fadd(a: float, b: float) -> float:
    return _f32(_f32(a) + _f32(b))


def _fsub(a: float, b: float) -> float:
    return _f32(_f32(a) - _f32(b))


def _fmul(a: float, b: float) -> float:
    return _f32(_f32(a) * _f32(b))


def _fdiv(a: float, b: float) -> float:
    return _f32(_f32(a) / _f32(b))


def _sqrt(value: float) -> float:
    return _f32(math.sqrt(_f32(value)))


def _sin_burst(value: float) -> float:
    """Transcribe the bounded |x| < 125 path of the pinned scalar helper."""
    value = _f32(value)
    if not math.isfinite(value) or abs(value) >= _f32(125.0):
        raise burst.ContractError("Basic Posture sine transcription left its pinned bounded path")
    quotient = _fmul(value, _f32(0.31830987334251404))
    rounded = math.trunc(_fadd(quotient, _f32(-0.5 if quotient < 0.0 else 0.5)))
    rounded_float = _f32(float(rounded))
    reduced = _fadd(value, _fmul(rounded_float, _f32(-3.1414794921875)))
    reduced = _fadd(reduced, _fmul(rounded_float, _f32(-0.0001131594181060791)))
    reduced = _fadd(reduced, _fmul(rounded_float, _f32(-1.984187258941006e-09)))
    signed = _f32(-reduced) if rounded & 1 else reduced
    square = _fmul(reduced, reduced)
    polynomial = _fadd(_fmul(square, _f32(2.6083159809786594e-06)),
                       _f32(-0.00019810690719168633))
    polynomial = _fadd(_fmul(square, polynomial), _f32(0.00833307858556509))
    polynomial = _fadd(_fmul(square, polynomial), _f32(-0.16666659712791443))
    return _fadd(signed, _fmul(square, _fmul(signed, polynomial)))


def _acos_burst(value: float) -> float:
    """Transcribe the scalar float acos sequence in the pinned core."""
    value = _f32(value)
    absolute = _f32(abs(value))
    if absolute < _f32(0.5):
        polynomial_input = _fmul(value, value)
        root = absolute
    else:
        polynomial_input = _fmul(_f32(0.5), _fsub(1.0, absolute))
        root = 0.0 if absolute == _f32(1.0) else _sqrt(polynomial_input)
    polynomial = _fadd(_fmul(polynomial_input, _f32(0.04197454825043678)),
                       _f32(0.024240460246801376))
    polynomial = _fadd(_fmul(polynomial_input, polynomial), _f32(0.04547423869371414))
    polynomial = _fadd(_fmul(polynomial_input, polynomial), _f32(0.07495029270648956))
    polynomial = _fadd(_fmul(polynomial_input, polynomial), _f32(0.16666772961616516))
    signed_root = _f32(-root) if value < 0.0 else root
    asin_value = _fadd(signed_root, _fmul(polynomial_input, _fmul(signed_root, polynomial)))
    if absolute < _f32(0.5):
        return _fsub(_f32(1.5707963705062866), asin_value)
    doubled = _fadd(root, _fmul(polynomial_input, _fmul(root, polynomial)))
    doubled = _fadd(doubled, doubled)
    return _fsub(_f32(3.1415927410125732), doubled) if value < 0.0 else doubled


def _dot4(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return _fadd(_fadd(_fmul(a[0], b[0]), _fmul(a[1], b[1])),
                 _fadd(_fmul(a[2], b[2]), _fmul(a[3], b[3])))


def _normalize4(q: tuple[float, ...]) -> tuple[float, ...]:
    inverse = _fdiv(1.0, _sqrt(_dot4(q, q)))
    return tuple(_fmul(value, inverse) for value in q)


def _quat_mul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        _fadd(_fadd(_fmul(aw, bx), _fmul(ax, bw)), _fsub(_fmul(ay, bz), _fmul(az, by))),
        _fadd(_fadd(_fmul(aw, by), _fmul(ay, bw)), _fsub(_fmul(az, bx), _fmul(ax, bz))),
        _fadd(_fadd(_fmul(aw, bz), _fmul(az, bw)), _fsub(_fmul(ax, by), _fmul(ay, bx))),
        _fsub(_fsub(_fsub(_fmul(aw, bw), _fmul(ax, bx)), _fmul(ay, by)), _fmul(az, bz)),
    )


def _rotate(q: tuple[float, ...], v: tuple[float, ...]) -> tuple[float, ...]:
    qv = q[:3]
    cross1 = (
        _fsub(_fmul(qv[1], v[2]), _fmul(qv[2], v[1])),
        _fsub(_fmul(qv[2], v[0]), _fmul(qv[0], v[2])),
        _fsub(_fmul(qv[0], v[1]), _fmul(qv[1], v[0])),
    )
    twice = tuple(_fadd(value, value) for value in cross1)
    cross2 = (
        _fsub(_fmul(qv[1], twice[2]), _fmul(qv[2], twice[1])),
        _fsub(_fmul(qv[2], twice[0]), _fmul(qv[0], twice[2])),
        _fsub(_fmul(qv[0], twice[1]), _fmul(qv[1], twice[0])),
    )
    return tuple(_fadd(_fadd(v[i], _fmul(q[3], twice[i])), cross2[i]) for i in range(3))


def _slerp(a: tuple[float, ...], b: tuple[float, ...], t: float) -> tuple[float, ...]:
    dot = _dot4(a, b)
    if dot < 0.0:
        b = tuple(_f32(-value) for value in b)
        dot = _f32(-dot)
    if dot >= _f32(0.9995):
        mixed = tuple(_fadd(a[i], _fmul(t, _fsub(b[i], a[i]))) for i in range(4))
        return _normalize4(mixed)
    theta = _acos_burst(dot)
    inverse_sin = _fdiv(1.0, _sqrt(_fsub(1.0, _fmul(dot, dot))))
    wa = _fmul(inverse_sin, _sin_burst(_fmul(_fsub(1.0, t), theta)))
    wb = _fmul(inverse_sin, _sin_burst(_fmul(t, theta)))
    return tuple(_fadd(_fmul(a[i], wa), _fmul(b[i], wb)) for i in range(4))


def _values(case: dict[str, Any]) -> dict[str, Any]:
    count = len(case["parents"])
    return {
        "attributes": list(case.get("attributes", [2] * count)),
        "initScale": tuple(_f32(v) for v in case.get("initScale", (1.0, 1.0, 1.0))),
        "scaleRatio": _f32(case.get("scaleRatio", 1.0)),
        "negativeScaleDirection": tuple(_f32(v) for v in case.get("negativeScaleDirection", (1.0, 1.0, 1.0))),
        "negativeScaleQuaternion": tuple(_f32(v) for v in case.get("negativeScaleQuaternion", (1.0, 1.0, 1.0, 1.0))),
        "animationPoseRatio": _f32(case["animationPoseRatio"]),
    }


def source_port(case: dict[str, Any]) -> dict[str, Any]:
    values = _values(case)
    positions = [tuple(_f32(v) for v in row) for row in case["stepPositions"]]
    rotations = [tuple(_f32(v) for v in row) for row in case["stepRotations"]]
    ratio = values["animationPoseRatio"]
    if ratio > _f32(0.99):
        return {"stepPositions": positions, "stepRotations": rotations}
    for vertex, parent in enumerate(case["parents"]):
        if values["attributes"][vertex] & 2 and parent >= 0:
            scaled = tuple(
                _fmul(_fmul(_fmul(case["localPositions"][vertex][axis], values["negativeScaleDirection"][axis]),
                             values["initScale"][axis]), values["scaleRatio"])
                for axis in range(3)
            )
            rotated = _rotate(rotations[parent], scaled)
            positions[vertex] = tuple(_fadd(positions[parent][axis], rotated[axis]) for axis in range(3))
            adjusted = tuple(_fmul(values["negativeScaleQuaternion"][axis], case["localRotations"][vertex][axis]) for axis in range(4))
            rotations[vertex] = _quat_mul(rotations[parent], adjusted)
        else:
            rotations[vertex] = _normalize4(rotations[vertex])
    if ratio > _f32(1e-8):
        for vertex in range(len(positions)):
            base_position = tuple(_f32(v) for v in case["basePositions"][vertex])
            positions[vertex] = tuple(_fadd(positions[vertex][axis], _fmul(ratio, _fsub(base_position[axis], positions[vertex][axis]))) for axis in range(3))
            base_rotation = tuple(_f32(v) for v in case["baseRotations"][vertex])
            rotations[vertex] = _slerp(rotations[vertex], base_rotation, ratio)
    return {"stepPositions": positions, "stepRotations": rotations}


def _hex_rows(rows: list[tuple[float, ...]]) -> list[list[str]]:
    return [[struct.pack("<f", value).hex() for value in row] for row in rows]


def _make_native_function(dll: Path) -> tuple[Any, Any]:
    module = ctypes.WinDLL(str(dll))
    signature = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 13), ctypes.c_int32)
    return module, signature(module._handle + CORE_RVA)


def _run_native(function: Any, case: dict[str, Any]) -> dict[str, Any]:
    values = _values(case)
    count = len(case["parents"])
    buffers = [
        ctypes.create_string_buffer(4), ctypes.create_string_buffer(464),
        ctypes.create_string_buffer(count), ctypes.create_string_buffer(count * 4),
        ctypes.create_string_buffer(count * 12), ctypes.create_string_buffer(count * 16),
        ctypes.create_string_buffer(2), ctypes.create_string_buffer(2),
        ctypes.create_string_buffer(count * 2), ctypes.create_string_buffer(count * 12),
        ctypes.create_string_buffer(count * 16), ctypes.create_string_buffer(count * 12),
        ctypes.create_string_buffer(count * 16),
    ]
    (step, team, attributes, parents, local_positions, local_rotations,
     starts, counts, data, base_positions, base_rotations, step_positions,
     step_rotations) = buffers
    struct.pack_into("<I", step, 0, 0)
    struct.pack_into("<3f", team, 0x54, *values["initScale"])
    struct.pack_into("<f", team, 0x60, values["scaleRatio"])
    struct.pack_into("<3f", team, 0x68, *values["negativeScaleDirection"])
    struct.pack_into("<4f", team, 0x88, *values["negativeScaleQuaternion"])
    struct.pack_into("<f", team, 0xE8, values["animationPoseRatio"])
    struct.pack_into("<i", team, 0x124, 0)
    struct.pack_into("<i", team, 0x164, 0)
    struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<H", starts, 0, 0)
    struct.pack_into("<H", counts, 0, count)
    for vertex in range(count):
        struct.pack_into("<B", attributes, vertex, values["attributes"][vertex])
        struct.pack_into("<i", parents, vertex * 4, case["parents"][vertex])
        struct.pack_into("<3f", local_positions, vertex * 12, *case["localPositions"][vertex])
        struct.pack_into("<4f", local_rotations, vertex * 16, *case["localRotations"][vertex])
        struct.pack_into("<H", data, vertex * 2, vertex)
        struct.pack_into("<3f", base_positions, vertex * 12, *case["basePositions"][vertex])
        struct.pack_into("<4f", base_rotations, vertex * 16, *case["baseRotations"][vertex])
        struct.pack_into("<3f", step_positions, vertex * 12, *case["stepPositions"][vertex])
        struct.pack_into("<4f", step_rotations, vertex * 16, *case["stepRotations"][vertex])
    function(*(ctypes.addressof(buffer) for buffer in buffers), 0)
    return {
        "stepPositions": [struct.unpack_from("<3f", step_positions, vertex * 12) for vertex in range(count)],
        "stepRotations": [struct.unpack_from("<4f", step_rotations, vertex * 16) for vertex in range(count)],
    }


def _validate_abi(pe: dict[str, Any]) -> dict[str, Any]:
    burst._exact_rva_span(pe, ENTRY_RVA, ENTRY_BYTES, ENTRY_SHA256)
    _, instructions = burst._exact_rva_span(pe, RANGE_RVA, RANGE_BYTES, RANGE_SHA256)
    rows = {ins.address - pe["imageBase"]: (ins.mnemonic, ins.op_str) for ins in instructions}
    pins = {
        0x2421C5: ("mov", "rax, qword ptr [rbp + 0xb8]"),
        0x2421CC: ("mov", "r15d, dword ptr [rax]"),
        0x2421F0: ("mov", "dword ptr [rsp + 0x68], r13d"),
        0x242263: ("call", "0x180241aa0"),
    }
    for rva, expected in pins.items():
        if rows.get(rva) != expected:
            raise burst.ContractError(f"Basic Posture range ABI drift at 0x{rva:x}: {rows.get(rva)}")
    return {
        "entry": {"rva": f"0x{ENTRY_RVA:x}", "bytes": ENTRY_BYTES, "sha256": ENTRY_SHA256},
        "range": {"rva": f"0x{RANGE_RVA:x}", "bytes": RANGE_BYTES, "sha256": RANGE_SHA256},
        "rangeFinalArgument": "pointer to int32 range count",
        "coreArgument14": "int32 rangeIndex value",
        "parameterOrder": [
            "stepBaseLineIndexArray", "teamDataArray", "attributes", "vertexParentIndices",
            "vertexLocalPositions", "vertexLocalRotations", "baseLineStartDataIndices",
            "baseLineDataCounts", "baseLineData", "basePosArray", "baseRotArray",
            "stepBasicPositionArray", "stepBasicRotationArray", "rangeIndex",
        ],
    }


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    abi = _validate_abi(pe)
    burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    burst._exact_rva_span(pe, SIN_RVA, SIN_BYTES, SIN_SHA256)
    module, function = _make_native_function(dll)
    vectors = []
    for case in CASES:
        native = _run_native(function, case)
        source = source_port(case)
        if (_hex_rows(native["stepPositions"]) != _hex_rows(source["stepPositions"]) or
                _hex_rows(native["stepRotations"]) != _hex_rows(source["stepRotations"])):
            raise burst.ContractError(
                f"source Basic Posture transcription differs from native core for {case['name']}: "
                f"native={native} source={source}"
            )
        values = _values(case)
        vectors.append({
            "name": case["name"],
            "input": {
                "parents": case["parents"], "attributes": values["attributes"],
                "localPositionsFloat32": case["localPositions"],
                "localRotationsFloat32": case["localRotations"],
                "basePositionsFloat32": case["basePositions"],
                "baseRotationsFloat32": case["baseRotations"],
                "stepPositionsFloat32": case["stepPositions"],
                "stepRotationsFloat32": case["stepRotations"],
                "initScaleFloat32": list(values["initScale"]),
                "scaleRatioFloat32": values["scaleRatio"],
                "negativeScaleDirectionFloat32": list(values["negativeScaleDirection"]),
                "negativeScaleQuaternionFloat32": list(values["negativeScaleQuaternion"]),
                "animationPoseRatioFloat32": values["animationPoseRatio"],
                "rangeIndex": 0,
            },
            "output": {
                "stepPositionsFloat32": [list(row) for row in native["stepPositions"]],
                "stepPositionsBinary32Le": _hex_rows(native["stepPositions"]),
                "stepRotationsFloat32": [list(row) for row in native["stepRotations"]],
                "stepRotationsBinary32Le": _hex_rows(native["stepRotations"]),
            },
        })
    del module
    return {
        "schema": "endfield.charinfo.secondary-dynamics-basic-posture-golden-vectors.v1",
        "status": "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
        "nativeGate": gate,
        "abi": abi,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES, "sha256": CORE_SHA256},
        "sineHelper": {"rva": f"0x{SIN_RVA:x}", "bytes": SIN_BYTES, "sha256": SIN_SHA256},
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": vectors,
        "boundary": {
            "nativeCoreExecuted": True,
            "sourceTranscriptionBinary32Matched": True,
            "unityPortExecuted": True,
            "unityVerifier": "EndfieldGraphShaderLabEditor.EndfieldSecondaryDynamicsKernelGoldenVerifier.VerifyMenu",
            "caseCoverage": [
                "root hierarchy", "non-root hierarchy", "positive scale", "negative scale",
                "animation-pose ratio zero", "animation-pose ratio partial",
                "animation-pose ratio one early exit", "quaternion nlerp", "quaternion slerp",
            ],
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
            raise SystemExit("Basic Posture golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
