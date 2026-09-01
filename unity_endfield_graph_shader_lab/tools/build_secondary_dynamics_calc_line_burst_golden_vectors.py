#!/usr/bin/env python3
"""Execute and source-transcribe the pinned CalcLine SSE2/AVX2 cores.

The cases are synthetic character-neutral values.  They carry no captured
positions, curves, frame timing, or Endminf-specific constants.
"""

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
import build_secondary_dynamics_float_sincos_golden_vectors as sincos


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_calc_line_burst_golden_vectors.json"
)

CORE_VARIANTS = (
    ("x64_sse2", 0xF4100, 3742,
     "d2981125e4685061134d4e7c1048efc84c33ecc9053f09d3dc9d104756282824",
     0x6E860),
    ("avx2", 0x284C50, 2901,
     "fd0fd8d14052cccdcf137f7e90391faadd0bae6c88c5e199fc908f0b8fe5b07c",
     0x1E5D30),
)

PARALLEL_EPSILON = 9.999999974752427e-07
SOURCE_PI = 3.1415927410125732
ABS64 = 0x7FFFFFFFFFFFFFFF

# Exact double polynomial table used twice by both pinned CalcLine cores.
ACOS64_COEFFICIENTS = (
    0.031615876506539346,
    0.012153605255773773,
    -0.015819182433299966,
    0.013887151845016092,
    0.019290454772679107,
    0.017359569912236146,
    0.006606077476277171,
    0.022371761819320483,
    0.030381959280381322,
    0.044642856813771024,
    0.07500000000378582,
    0.16666666666664975,
)

CASES = (
    {
        "name": "parallel_move",
        "parentPosition": (0.0, 0.0, 0.0),
        "parentRotation": (0.0, 0.0, 0.0, 1.0),
        "parentAttribute": 2,
        "rotationalInterpolation": 1.0,
        "rootRotation": 0.25,
        "children": ({"position": (1.0, 0.0, 0.0),
                      "localPosition": (1.0, 0.0, 0.0),
                      "localRotation": (0.0, 0.0, 0.0, 1.0),
                      "attribute": 2},),
    },
    {
        "name": "quarter_turn_move",
        "parentPosition": (0.25, -0.5, 0.75),
        "parentRotation": (0.0, 0.0, 0.0, 1.0),
        "parentAttribute": 2,
        "rotationalInterpolation": 0.625,
        "rootRotation": 0.25,
        "children": ({"position": (0.25, 0.5, 0.75),
                      "localPosition": (1.0, 0.0, 0.0),
                      "localRotation": (0.0, 0.0, 0.0, 1.0),
                      "attribute": 2},),
    },
    {
        "name": "antiparallel_positive_x",
        "parentPosition": (0.0, 0.0, 0.0),
        "parentRotation": (0.0, 0.0, 0.0, 1.0),
        "parentAttribute": 0,
        "rotationalInterpolation": 1.0,
        "rootRotation": 0.5,
        "children": ({"position": (-1.0, 0.0, 0.0),
                      "localPosition": (1.0, 0.0, 0.0),
                      "localRotation": (0.0, 0.0, 0.0, 1.0),
                      "attribute": 2},),
    },
    {
        "name": "non_move_assignment",
        "parentPosition": (10.0, 20.0, 30.0),
        "parentRotation": (0.0, 0.0, 0.0, 1.0),
        "parentAttribute": 0,
        "rotationalInterpolation": 0.75,
        "rootRotation": 0.375,
        "children": ({"position": (-100.0, 50.0, 80.0),
                      "localPosition": (0.25, -0.5, 0.75),
                      "localRotation": (0.0, 0.0, 0.0, 1.0),
                      "attribute": 0},),
    },
    {
        "name": "two_child_parent_direction_sum",
        "parentPosition": (0.0, 0.0, 0.0),
        "parentRotation": (0.0, 0.0, 0.0, 1.0),
        "parentAttribute": 2,
        "rotationalInterpolation": 0.4,
        "rootRotation": 0.9,
        "children": (
            {"position": (0.0, 1.0, 0.0), "localPosition": (1.0, 0.0, 0.0),
             "localRotation": (0.0, 0.0, 0.0, 1.0), "attribute": 2},
            {"position": (0.0, 0.0, 1.0), "localPosition": (0.0, 1.0, 0.0),
             "localRotation": (0.0, 0.0, 0.0, 1.0), "attribute": 2},
        ),
    },
    {
        "name": "empty_child_no_write",
        "parentPosition": (1.0, 2.0, 3.0),
        "parentRotation": (0.125, -0.25, 0.375, 0.5),
        "parentAttribute": 2,
        "rotationalInterpolation": 1.0,
        "rootRotation": 1.0,
        "children": (),
    },
    {
        "name": "negative_x_antiparallel_zero_axis",
        "parentPosition": (0.0, 0.0, 0.0),
        "parentRotation": (0.0, 0.0, 0.0, 1.0),
        "parentAttribute": 2,
        "rotationalInterpolation": 1.0,
        "rootRotation": 1.0,
        "negativeScaleDirection": (-1.0, 1.0, 1.0),
        "children": ({"position": (1.0, 0.0, 0.0),
                      "localPosition": (1.0, 0.0, 0.0),
                      "localRotation": (0.0, 0.0, 0.0, 1.0),
                      "attribute": 2},),
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


def _bits32(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", _f32(value)))[0]


def _from_bits32(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value & 0xFFFFFFFF))[0]


def _bits64(value: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def _from_bits64(value: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF))[0]


def _abs64(value: float) -> float:
    return _from_bits64(_bits64(value) & ABS64)


def _ddiv(a: float, b: float) -> float:
    if math.isnan(a) or math.isnan(b):
        return float("nan")
    if b == 0.0:
        if a == 0.0:
            return float("nan")
        return math.copysign(float("inf"), a * b if b else a)
    return a / b


def _dsqrt(value: float) -> float:
    if math.isnan(value) or value < 0.0:
        return float("nan")
    return math.sqrt(value)


def _normalize3(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _dsqrt((value[0] * value[0] + value[1] * value[1]) + value[2] * value[2])
    inverse = _ddiv(1.0, length)
    return (value[0] * inverse, value[1] * inverse, value[2] * inverse)


def _dot3(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return (a[0] * b[0] + a[1] * b[1]) + a[2] * b[2]


def _cross3(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _acos64(value: float) -> float:
    """Instruction-grouped scalar double acos in both pinned CalcLine cores."""
    absolute = _abs64(value)
    if absolute < 0.5:
        z = value * value
        root = absolute
    else:
        z = 0.5 * (1.0 - absolute)
        root = 0.0 if absolute == 1.0 else _dsqrt(z)
    c = ACOS64_COEFFICIENTS
    z2 = z * z
    even0 = z2 * (z * c[0] + c[2]) + (z * c[4] + c[6])
    even1 = z2 * (z * c[1] + c[3]) + (z * c[5] + c[7])
    base = z2 * (z * c[8] + c[9]) + (z * c[10] + c[11])
    z4 = z2 * z2
    polynomial = (base + z4 * even1) + (z4 * z4) * even0
    term = (z * root) * polynomial
    signed_root = _from_bits64(_bits64(root) ^ (_bits64(value) & ~ABS64))
    signed_term = _from_bits64(_bits64(term) ^ (_bits64(value) & ~ABS64))
    asin_value = signed_root + signed_term
    if absolute < 0.5:
        return math.pi * 0.5 - asin_value
    doubled = (root + term) + (root + term)
    return math.pi - doubled if value < 0.0 else doubled


def _from_to(
    source: tuple[float, float, float],
    target: tuple[float, float, float],
    interpolation: float,
) -> tuple[float, float, float, float]:
    u = _normalize3(source)
    v = _normalize3(target)
    dot = max(-1.0, min(1.0, _dot3(u, v)))
    angle = _acos64(dot)
    axis = _cross3(u, v)
    if _abs64(dot + 1.0) < PARALLEL_EPSILON:
        angle = SOURCE_PI
        reference = (0.0, 1.0, 0.0) if u[0] > u[1] and u[0] > u[2] else (1.0, 0.0, 0.0)
        axis = _cross3(u, reference)
    elif _abs64(1.0 - dot) < PARALLEL_EPSILON:
        return (0.0, 0.0, 0.0, 1.0)
    axis = _normalize3(axis)
    scaled = _f32(angle * interpolation)
    half = _fmul(scaled, 0.5)
    sin_bits, cos_bits, _path = sincos.source_sincos(_bits32(half))
    sine = _from_bits32(sin_bits)
    return (_fmul(_f32(axis[0]), sine),
            _fmul(_f32(axis[1]), sine),
            _fmul(_f32(axis[2]), sine),
            _from_bits32(cos_bits))


def _quat_mul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    x_first = _fadd(_fmul(a[3], b[0]), _fmul(a[0], b[3]))
    x_cross = _fsub(_fmul(a[1], b[2]), _fmul(a[2], b[1]))
    y_first = _fadd(_fmul(a[3], b[1]), _fmul(a[1], b[3]))
    y_cross = _fsub(_fmul(a[2], b[0]), _fmul(a[0], b[2]))
    z_first = _fadd(_fmul(a[3], b[2]), _fmul(a[2], b[3]))
    z_cross = _fsub(_fmul(a[0], b[1]), _fmul(a[1], b[0]))
    w = _fsub(_fsub(_fsub(_fmul(a[3], b[3]), _fmul(a[0], b[0])),
                    _fmul(a[1], b[1])), _fmul(a[2], b[2]))
    return (_fadd(x_first, x_cross), _fadd(y_first, y_cross),
            _fadd(z_first, z_cross), w)


def _rotate(q: tuple[float, ...], v: tuple[float, ...]) -> tuple[float, float, float]:
    tx = _fmul(2.0, _fsub(_fmul(q[1], v[2]), _fmul(q[2], v[1])))
    ty = _fmul(2.0, _fsub(_fmul(q[2], v[0]), _fmul(q[0], v[2])))
    tz = _fmul(2.0, _fsub(_fmul(q[0], v[1]), _fmul(q[1], v[0])))
    cx = _fsub(_fmul(q[1], tz), _fmul(q[2], ty))
    cy = _fsub(_fmul(q[2], tx), _fmul(q[0], tz))
    cz = _fsub(_fmul(q[0], ty), _fmul(q[1], tx))
    return (_fadd(_fadd(v[0], _fmul(q[3], tx)), cx),
            _fadd(_fadd(v[1], _fmul(q[3], ty)), cy),
            _fadd(_fadd(v[2], _fmul(q[3], tz)), cz))


def source_port(case: dict[str, Any]) -> list[tuple[float, float, float, float]]:
    parent_position = tuple(float(v) for v in case["parentPosition"])
    parent_rotation = tuple(_f32(v) for v in case["parentRotation"])
    scale = tuple(_f32(v) for v in case.get("negativeScaleDirection", (1.0, 1.0, 1.0)))
    signed_quaternion = tuple(_f32(v) for v in case.get("negativeScaleQuaternion", (1.0, 1.0, 1.0, 1.0)))
    rotations = [parent_rotation] + [tuple(_f32(v) for v in child["localRotation"])
                                     for child in case["children"]]
    rest_sum = (0.0, 0.0, 0.0)
    direction = (0.0, 0.0, 0.0)
    for child_index, child in enumerate(case["children"], 1):
        local = tuple(_fmul(child["localPosition"][axis], scale[axis]) for axis in range(3))
        rest32 = _rotate(parent_rotation, local)
        rest = tuple(float(value) for value in rest32)
        rest_sum = tuple(rest_sum[axis] + rest[axis] for axis in range(3))
        if int(child["attribute"]) & 2:
            child_direction = tuple(float(child["position"][axis]) - parent_position[axis]
                                    for axis in range(3))
        else:
            child_direction = rest
        direction = tuple(direction[axis] + child_direction[axis] for axis in range(3))
        child_from_to = _from_to(rest, child_direction, 1.0)
        local_rotation = tuple(_fmul(child["localRotation"][axis], signed_quaternion[axis])
                               for axis in range(4))
        rotations[child_index] = _quat_mul(
            _quat_mul(parent_rotation, local_rotation), child_from_to
        )
    if case["children"]:
        interpolation = (float(case["rotationalInterpolation"])
                         if int(case["parentAttribute"]) & 2
                         else float(case["rootRotation"]))
        rotations[0] = _quat_mul(_from_to(rest_sum, direction, interpolation), parent_rotation)
    return rotations


def _native_case(module: Any, core_rva: int, case: dict[str, Any]) -> list[tuple[float, ...]]:
    children = tuple(case["children"])
    vertex_count = 1 + len(children)
    team_data = ctypes.create_string_buffer(2 * 0x1D0)
    team = 0x1D0
    struct.pack_into("<Q", team_data, team, 2)
    struct.pack_into("<3f", team_data, team + 0x68,
                     *case.get("negativeScaleDirection", (1.0, 1.0, 1.0)))
    struct.pack_into("<4f", team_data, team + 0x88,
                     *case.get("negativeScaleQuaternion", (1.0, 1.0, 1.0, 1.0)))
    struct.pack_into("<ii", team_data, team + 0x124, 0, vertex_count)
    struct.pack_into("<ii", team_data, team + 0x12C, 0, len(children))
    struct.pack_into("<ii", team_data, team + 0x164, 0, 1)

    parameters = ctypes.create_string_buffer(2 * 0x328)
    struct.pack_into("<f", parameters, 0x328 + 0xA0, case["rotationalInterpolation"])
    struct.pack_into("<f", parameters, 0x328 + 0xA4, case["rootRotation"])
    job_baselines = (ctypes.c_int32 * 1)(0)
    attributes = (ctypes.c_uint8 * vertex_count)(
        int(case["parentAttribute"]), *(int(row["attribute"]) for row in children)
    )
    positions = (ctypes.c_double * (vertex_count * 3))()
    for axis, value in enumerate(case["parentPosition"]):
        positions[axis] = value
    for child_index, child in enumerate(children, 1):
        for axis, value in enumerate(child["position"]):
            positions[child_index * 3 + axis] = value
    rotations = (ctypes.c_float * (vertex_count * 4))()
    initial_rotations = [case["parentRotation"]] + [row["localRotation"] for row in children]
    for vertex, rotation in enumerate(initial_rotations):
        for axis, value in enumerate(rotation):
            rotations[vertex * 4 + axis] = value
    local_positions = (ctypes.c_float * (vertex_count * 3))()
    local_rotations = (ctypes.c_float * (vertex_count * 4))()
    for child_index, child in enumerate(children, 1):
        for axis, value in enumerate(child["localPosition"]):
            local_positions[child_index * 3 + axis] = value
        for axis, value in enumerate(child["localRotation"]):
            local_rotations[child_index * 4 + axis] = value
    parent_indices = (ctypes.c_int32 * max(1, vertex_count))()
    child_indices = (ctypes.c_uint32 * max(1, vertex_count))()
    child_indices[0] = len(children) << 20
    child_data = (ctypes.c_uint16 * max(1, len(children)))(
        *(range(1, vertex_count)) if children else (0,)
    )
    baseline_flags = (ctypes.c_uint8 * 1)(1)
    baseline_team_ids = (ctypes.c_int16 * 1)(1)
    baseline_starts = (ctypes.c_uint16 * 1)(0)
    baseline_counts = (ctypes.c_uint16 * 1)(1)
    baseline_data = (ctypes.c_uint16 * 1)(0)

    arrays = (
        job_baselines, team_data, parameters, attributes, positions, rotations,
        local_positions, local_rotations, parent_indices, child_indices,
        child_data, baseline_flags, baseline_team_ids, baseline_starts,
        baseline_counts, baseline_data,
    )
    signature = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 16), ctypes.c_int32)
    function = signature(module._handle + core_rva)
    function(*(ctypes.cast(value, ctypes.c_void_p) for value in arrays), 0)
    return [tuple(float(rotations[vertex * 4 + axis]) for axis in range(4))
            for vertex in range(vertex_count)]


def _rotation_bits(rows: list[tuple[float, ...]]) -> list[list[str]]:
    return [[struct.pack("<f", value).hex() for value in row] for row in rows]


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    for _variant, rva, size, sha256, helper_rva in CORE_VARIANTS:
        _body, instructions = burst._exact_rva_span(pe, rva, size, sha256)
        calls = [burst._direct_target(ins, pe["imageBase"])
                 for ins in instructions if ins.mnemonic == "call"]
        if calls != [helper_rva, helper_rva]:
            raise burst.ContractError(f"CalcLine helper call graph drift at 0x{rva:x}")
    module = ctypes.WinDLL(str(dll))
    rows = []
    for case in CASES:
        source = source_port(case)
        native = {
            variant: _native_case(module, rva, case)
            for variant, rva, _size, _sha256, _helper in CORE_VARIANTS
        }
        source_bits = _rotation_bits(source)
        native_bits = {variant: _rotation_bits(value) for variant, value in native.items()}
        for variant, bits in native_bits.items():
            if bits != source_bits:
                raise burst.ContractError(
                    f"CalcLine source transcription differs for {variant}/{case['name']}: "
                    f"native={bits!r} source={source_bits!r}"
                )
        rows.append({
            "name": case["name"],
            "childCount": len(case["children"]),
            "rotationBitsLe": source_bits,
        })
    return {
        "schema": "endfield.charinfo.secondary-dynamics-calc-line-burst-golden-vectors.v1",
        "status": "dual_cpu_core_and_source_transcription_exact_for_branch_golden_cases",
        "nativeGate": gate,
        "cores": [
            {"cpuVariant": variant, "rva": f"0x{rva:x}", "bytes": size,
             "sha256": sha256, "sincosHelperRva": f"0x{helper_rva:x}"}
            for variant, rva, size, sha256, helper_rva in CORE_VARIANTS
        ],
        "equations": {
            "traversal": (
                "baseline list -> bit-0/team gates -> baseline parents -> packed "
                "child list; select one per-child direction, add it to the parent "
                "direction sum, and pass that per-child direction to child FromTo"
            ),
            "rest": (
                "double3(float3(rotateBinary32(parentRotation, "
                "localPosition*negativeScaleDirection)))"
            ),
            "childRotation": (
                "mulBinary32(mulBinary32(parentRotation, "
                "localRotation*negativeScaleQuaternion), fromTo(rest,direction,1))"
            ),
            "parentRotation": (
                "mulBinary32(fromTo(restSum,direction,selectedInterpolation), "
                "incomingParentRotation)"
            ),
            "acos64PolynomialCoefficients": list(ACOS64_COEFFICIENTS),
            "acos64Grouping": (
                "z2=z*z; even0=z2*(z*c0+c2)+(z*c4+c6); "
                "even1=z2*(z*c1+c3)+(z*c5+c7); "
                "base=z2*(z*c8+c9)+(z*c10+c11); "
                "poly=(base+(z2*z2)*even1)+((z2*z2)^2)*even0"
            ),
            "axisAngle": (
                "normalize double3 axis; cast components and angle*t to float32; "
                "multiply half angle in float32; use the CPU-local pinned sincos helper"
            ),
        },
        "degeneracy": {
            "parallel": "abs(1-dot)<epsilon returns identity before axis normalization",
            "antiparallel": (
                "abs(dot+1)<epsilon uses float-pi promoted to double and reference "
                "Y only when u.x>u.y and u.x>u.z, otherwise X"
            ),
            "negativeXAxis": (
                "the authored reference rule produces a zero cross axis for exact "
                "negative X; normalization propagates canonical NaN quaternion lanes"
            ),
            "zeroOrNonFinite": (
                "there is no explicit normalization guard; IEEE infinity/NaN values "
                "propagate through the exact polynomial and sincos special cases"
            ),
            "emptyChild": "no parent or child rotation write occurs",
        },
        "vectors": rows,
        "boundary": {
            "nativeCpuVariantsExecuted": [variant for variant, *_rest in CORE_VARIANTS],
            "sourceOnlyTranscriptionMatchedBitForBit": True,
            "caseCount": len(rows),
            "captureUsed": False,
            "runtimeRouteSelected": False,
            "managedIfixPatchStateClosed": False,
            "solverImplemented": False,
            "retailEquivalent": False,
        },
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_contract(), indent=2, allow_nan=True) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit("CalcLine Burst golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
