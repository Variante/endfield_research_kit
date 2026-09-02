#!/usr/bin/env python3
"""Execute and source-transcribe the pinned CalcLine SSE2/AVX2 cores.

The branch cases are synthetic character-neutral values.  The detached
Endminf topology cases join hash-pinned serialized proxy topology to three
deterministic finite states; they carry no capture, frame timing, route
selection, scene writeback, or visual-equivalence claim.
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
DATA_ROOT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
)
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_calc_line_burst_golden_vectors.json"
)
PAYLOAD_DECODE = DATA_ROOT / "secondary_dynamics_payload_decode.json"
SOLVER_INPUTS = DATA_ROOT / "secondary_dynamics_solver_inputs.json"
EXPECTED_PAYLOAD_DECODE_SHA256 = (
    "6c8eed435f2acd645d3fb3560acf7c993b5ef34c8ff2336de1a9fa87a1cbff1a"
)
EXPECTED_SOLVER_INPUTS_SHA256 = (
    "fe91726b102a1104ed223be0aeb9138a76d58887a79851cc70736fd0d4ed6251"
)
EXPECTED_ENDMINF_OWNERS = ("MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat")
TOPOLOGY_ARRAY_KEYS = (
    "attributes",
    "vertexParentIndices",
    "vertexChildIndexArray",
    "vertexChildDataArray",
    "vertexLocalPositions",
    "vertexLocalRotations",
    "vertexBindPosePositions",
    "vertexBindPoseRotations",
    "baseLineFlags",
    "baseLineStartDataIndices",
    "baseLineDataCounts",
    "baseLineData",
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


def _quat_mul_burst(
    a: tuple[float, ...],
    b: tuple[float, ...],
) -> tuple[float, float, float, float]:
    """Pinned Unity.Mathematics float4 grouping used by both Burst cores."""
    first = tuple(_fmul(a[3], b[index]) for index in range(4))
    positive = (
        _fadd(_fmul(a[0], b[3]), _fmul(a[1], b[2])),
        _fadd(_fmul(a[1], b[3]), _fmul(a[2], b[0])),
        _fadd(_fmul(a[2], b[3]), _fmul(a[0], b[1])),
        _fsub(0.0, _fadd(_fmul(a[0], b[0]), _fmul(a[1], b[1]))),
    )
    last = (
        _fmul(a[2], b[1]),
        _fmul(a[0], b[2]),
        _fmul(a[1], b[0]),
        _fmul(a[2], b[2]),
    )
    return tuple(_fsub(_fadd(first[index], positive[index]), last[index])
                 for index in range(4))


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
        child_moves = bool(int(child["attribute"]) & 2)
        if child_moves:
            child_direction = tuple(float(child["position"][axis]) - parent_position[axis]
                                    for axis in range(3))
        else:
            child_direction = rest
        direction = tuple(direction[axis] + child_direction[axis] for axis in range(3))
        child_from_to = _from_to(rest, child_direction, 1.0)
        local_rotation = tuple(_fmul(child["localRotation"][axis], signed_quaternion[axis])
                               for axis in range(4))
        if child_moves:
            rotations[child_index] = _quat_mul_burst(
                child_from_to,
                _quat_mul_burst(parent_rotation, local_rotation),
            )
    if case["children"]:
        interpolation = (float(case["rotationalInterpolation"])
                         if int(case["parentAttribute"]) & 2
                         else float(case["rootRotation"]))
        rotations[0] = _quat_mul_burst(
            _from_to(rest_sum, direction, interpolation),
            parent_rotation,
        )
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


def _position_bits(rows: list[tuple[float, ...]]) -> list[list[str]]:
    return [[struct.pack("<d", value).hex() for value in row] for row in rows]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_pinned_json(path: Path, expected_sha256: str, schema: str) -> dict[str, Any]:
    actual_sha256 = _sha256(path)
    if actual_sha256 != expected_sha256:
        raise burst.ContractError(
            f"{path.name} hash drift: expected {expected_sha256}, got {actual_sha256}"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise burst.ContractError(f"unable to read {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise burst.ContractError(f"{path.name} schema drift")
    return value


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise burst.ContractError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise burst.ContractError(f"{label} must be an array")
    return value


def _array_field(arrays: dict[str, Any], key: str) -> dict[str, Any]:
    row = _object(arrays.get(key), key)
    values = _array(row.get("values"), f"{key}.values")
    count = row.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(values):
        raise burst.ContractError(f"{key} count differs from values")
    digest = row.get("array_bytes_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise burst.ContractError(f"{key} has no pinned array byte hash")
    return row


def _integer_values(arrays: dict[str, Any], key: str) -> list[int]:
    values = _array_field(arrays, key)["values"]
    result: list[int] = []
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, int):
            raise burst.ContractError(f"{key}[{index}] is not an integer")
        result.append(value)
    return result


def _vector_values(arrays: dict[str, Any], key: str, width: int) -> list[tuple[float, ...]]:
    values = _array_field(arrays, key)["values"]
    result: list[tuple[float, ...]] = []
    for index, value in enumerate(values):
        lanes = _array(value, f"{key}[{index}]")
        if len(lanes) != width:
            raise burst.ContractError(f"{key}[{index}] width differs from {width}")
        converted = tuple(float(lane) for lane in lanes)
        if not all(math.isfinite(lane) for lane in converted):
            raise burst.ContractError(f"{key}[{index}] is not finite")
        result.append(converted)
    return result


def _topology_hash(topology: dict[str, Any]) -> str:
    keys = (
        "ownerPath", "attributes", "parentIndices", "childIndices", "childData",
        "localPositions", "localRotations", "bindPositions", "bindRotations",
        "baselineFlags", "baselineStarts", "baselineCounts", "baselineData",
        "rotationalInterpolation", "rootRotation",
    )
    payload = json.dumps(
        {key: topology[key] for key in keys},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _decode_endminf_topologies(
    payload_decode: dict[str, Any],
    solver_inputs: dict[str, Any],
) -> list[dict[str, Any]]:
    payload_actor = _object(_object(payload_decode.get("actors"), "payload actors").get(
        "endminf"), "payload endminf")
    solver_actor = _object(_object(solver_inputs.get("actors"), "solver actors").get(
        "endminf"), "solver endminf")
    payload_cloths = _array(payload_actor.get("cloths"), "payload endminf cloths")
    solver_cloths = _array(solver_actor.get("cloths"), "solver endminf cloths")
    solver_by_owner = {
        str(_object(row, "solver cloth").get("game_object_path")): _object(row, "solver cloth")
        for row in solver_cloths
    }
    owners: list[dict[str, Any]] = []
    for cloth_value in payload_cloths:
        cloth = _object(cloth_value, "payload cloth")
        owner_path = cloth.get("game_object_path")
        if not isinstance(owner_path, str) or owner_path not in solver_by_owner:
            raise burst.ContractError(f"unjoined Endminf owner {owner_path!r}")
        arrays = _object(cloth.get("proxy_mesh_arrays"), f"{owner_path}.proxy_mesh_arrays")
        solver_cloth = solver_by_owner[owner_path]
        serialized = _object(solver_cloth.get("serialized_data"), f"{owner_path}.serialized_data")
        rotational_interpolation = float(serialized.get("rotationalInterpolation"))
        root_rotation = float(serialized.get("rootRotation"))
        if not math.isfinite(rotational_interpolation) or not math.isfinite(root_rotation):
            raise burst.ContractError(f"{owner_path} interpolation scalars are not finite")
        topology = {
            "ownerPath": owner_path,
            "attributes": _integer_values(arrays, "attributes"),
            "parentIndices": _integer_values(arrays, "vertexParentIndices"),
            "childIndices": _integer_values(arrays, "vertexChildIndexArray"),
            "childData": _integer_values(arrays, "vertexChildDataArray"),
            "localPositions": _vector_values(arrays, "vertexLocalPositions", 3),
            "localRotations": _vector_values(arrays, "vertexLocalRotations", 4),
            "bindPositions": _vector_values(arrays, "vertexBindPosePositions", 3),
            "bindRotations": _vector_values(arrays, "vertexBindPoseRotations", 4),
            "baselineFlags": _integer_values(arrays, "baseLineFlags"),
            "baselineStarts": _integer_values(arrays, "baseLineStartDataIndices"),
            "baselineCounts": _integer_values(arrays, "baseLineDataCounts"),
            "baselineData": _integer_values(arrays, "baseLineData"),
            "rotationalInterpolation": rotational_interpolation,
            "rootRotation": root_rotation,
            "lineCount": int(_array_field(arrays, "lines")["count"]),
            "sourceArraySha256": {
                key: str(_array_field(arrays, key)["array_bytes_sha256"])
                for key in TOPOLOGY_ARRAY_KEYS
            },
        }
        vertex_count = len(topology["attributes"])
        vertex_fields = (
            "parentIndices", "childIndices", "localPositions", "localRotations",
            "bindPositions", "bindRotations",
        )
        if vertex_count == 0 or any(len(topology[key]) != vertex_count for key in vertex_fields):
            raise burst.ContractError(f"{owner_path} vertex cardinalities drift")
        baseline_count = len(topology["baselineFlags"])
        if any(len(topology[key]) != baseline_count
               for key in ("baselineStarts", "baselineCounts")):
            raise burst.ContractError(f"{owner_path} baseline cardinalities drift")
        cursor = 0
        seen_children: set[int] = set()
        for parent, packed in enumerate(topology["childIndices"]):
            local_start = packed & 0xFFFFF
            child_count = packed >> 20
            if local_start != cursor or cursor + child_count > len(topology["childData"]):
                raise burst.ContractError(f"{owner_path} packed child slice drift at {parent}")
            for child in topology["childData"][cursor:cursor + child_count]:
                if (child < 0 or child >= vertex_count or child in seen_children or
                        topology["parentIndices"][child] != parent):
                    raise burst.ContractError(f"{owner_path} child membership drift at {parent}")
                seen_children.add(child)
            cursor += child_count
        if cursor != len(topology["childData"]):
            raise burst.ContractError(f"{owner_path} child data has trailing values")
        for baseline, (start, count) in enumerate(zip(
                topology["baselineStarts"], topology["baselineCounts"])):
            if start < 0 or count < 0 or start + count > len(topology["baselineData"]):
                raise burst.ContractError(f"{owner_path} baseline slice drift at {baseline}")
            for parent in topology["baselineData"][start:start + count]:
                if parent < 0 or parent >= vertex_count:
                    raise burst.ContractError(f"{owner_path} baseline parent out of range")
        topology["topologySha256"] = _topology_hash(topology)
        owners.append(topology)
    if tuple(owner["ownerPath"] for owner in owners) != EXPECTED_ENDMINF_OWNERS:
        raise burst.ContractError("Endminf owner order drift")
    return owners


def _perturbed_state(
    topology: dict[str, Any],
    owner_index: int,
    state_index: int,
) -> tuple[list[tuple[float, ...]], list[tuple[float, ...]]]:
    positions = [tuple(float(lane) for lane in row) for row in topology["bindPositions"]]
    rotations = [tuple(_f32(lane) for lane in row) for row in topology["bindRotations"]]
    if state_index == 0:
        return positions, rotations
    position_scale = 0.00035 if state_index == 1 else -0.00055
    rotation_scale = 0.00125 if state_index == 1 else -0.00175
    for vertex in range(len(positions)):
        seed = (owner_index + 1) * 97 + (vertex + 1) * 31 + state_index * 17
        offset = tuple(
            position_scale * (((seed >> (axis * 3)) % 7) - 3)
            for axis in range(3)
        )
        positions[vertex] = tuple(positions[vertex][axis] + offset[axis] for axis in range(3))
        x = _f32(rotation_scale * (((seed >> 1) % 5) - 2))
        y = _f32(rotation_scale * (((seed >> 4) % 5) - 2))
        z = _f32(rotation_scale * (((seed >> 7) % 5) - 2))
        magnitude = float(x) * x + float(y) * y + float(z) * z
        if magnitude >= 1.0:
            raise burst.ContractError("deterministic rotation perturbation is not bounded")
        delta = (x, y, z, _f32(math.sqrt(1.0 - magnitude)))
        rotations[vertex] = _quat_mul(rotations[vertex], delta)
    if not all(math.isfinite(lane) for row in positions + rotations for lane in row):
        raise burst.ContractError("deterministic topology state is not finite")
    return positions, rotations


def _source_topology_state(
    topology: dict[str, Any],
    positions: list[tuple[float, ...]],
    input_rotations: list[tuple[float, ...]],
) -> list[tuple[float, ...]]:
    rotations = list(input_rotations)
    for baseline, flag in enumerate(topology["baselineFlags"]):
        if not flag & 1:
            continue
        start = topology["baselineStarts"][baseline]
        count = topology["baselineCounts"][baseline]
        for parent in topology["baselineData"][start:start + count]:
            packed = topology["childIndices"][parent]
            child_start = packed & 0xFFFFF
            child_count = packed >> 20
            children_indices = topology["childData"][child_start:child_start + child_count]
            if not children_indices:
                continue
            parent_position = positions[parent]
            parent_rotation = rotations[parent]
            rest_sum = (0.0, 0.0, 0.0)
            direction_sum = (0.0, 0.0, 0.0)
            for child in children_indices:
                local = topology["localPositions"][child]
                rest = tuple(float(value) for value in _rotate(parent_rotation, local))
                rest_sum = tuple(rest_sum[axis] + rest[axis] for axis in range(3))
                child_moves = bool(topology["attributes"][child] & 2)
                direction = (
                    tuple(positions[child][axis] - parent_position[axis] for axis in range(3))
                    if child_moves else rest
                )
                direction_sum = tuple(
                    direction_sum[axis] + direction[axis] for axis in range(3)
                )
                if child_moves:
                    child_from_to = _from_to(rest, direction, 1.0)
                    signed_local = topology["localRotations"][child]
                    rotations[child] = _quat_mul_burst(
                        child_from_to,
                        _quat_mul_burst(parent_rotation, signed_local),
                    )
            interpolation = (
                topology["rotationalInterpolation"]
                if topology["attributes"][parent] & 2
                else topology["rootRotation"]
            )
            rotations[parent] = _quat_mul_burst(
                _from_to(rest_sum, direction_sum, interpolation),
                parent_rotation,
            )
    return rotations


def _ctypes_bytes(value: Any) -> bytes:
    return ctypes.string_at(ctypes.addressof(value), ctypes.sizeof(value))


def _buffer_sha256(value: Any) -> str:
    return hashlib.sha256(_ctypes_bytes(value)).hexdigest()


def _immutable_sha256(buffers: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for name in sorted(buffers):
        if name == "rotations":
            continue
        digest.update(name.encode("ascii"))
        digest.update(b"\0")
        digest.update(_ctypes_bytes(buffers[name]))
    return digest.hexdigest()


def _native_topology_state(
    module: Any,
    core_rva: int,
    topology: dict[str, Any],
    positions_values: list[tuple[float, ...]],
    rotation_values: list[tuple[float, ...]],
) -> tuple[list[tuple[float, ...]], dict[str, Any]]:
    vertex_count = len(topology["attributes"])
    baseline_count = len(topology["baselineFlags"])
    child_data_count = len(topology["childData"])
    baseline_data_count = len(topology["baselineData"])
    team_data = ctypes.create_string_buffer(2 * 0x1D0)
    team = 0x1D0
    struct.pack_into("<Q", team_data, team, 2)
    struct.pack_into("<3f", team_data, team + 0x68, 1.0, 1.0, 1.0)
    struct.pack_into("<4f", team_data, team + 0x88, 1.0, 1.0, 1.0, 1.0)
    struct.pack_into("<ii", team_data, team + 0x124, 0, vertex_count)
    struct.pack_into("<ii", team_data, team + 0x12C, 0, child_data_count)
    struct.pack_into("<ii", team_data, team + 0x164, 0, baseline_count)
    parameters = ctypes.create_string_buffer(2 * 0x328)
    struct.pack_into("<f", parameters, 0x328 + 0xA0, topology["rotationalInterpolation"])
    struct.pack_into("<f", parameters, 0x328 + 0xA4, topology["rootRotation"])
    job_baselines = (ctypes.c_int32 * baseline_count)(*range(baseline_count))
    attributes = (ctypes.c_uint8 * vertex_count)(*topology["attributes"])
    positions = (ctypes.c_double * (vertex_count * 3))(
        *(lane for row in positions_values for lane in row)
    )
    rotations = (ctypes.c_float * (vertex_count * 4))(
        *(lane for row in rotation_values for lane in row)
    )
    local_positions = (ctypes.c_float * (vertex_count * 3))(
        *(lane for row in topology["localPositions"] for lane in row)
    )
    local_rotations = (ctypes.c_float * (vertex_count * 4))(
        *(lane for row in topology["localRotations"] for lane in row)
    )
    parent_indices = (ctypes.c_int32 * vertex_count)(*topology["parentIndices"])
    child_indices = (ctypes.c_uint32 * vertex_count)(*topology["childIndices"])
    child_data = (ctypes.c_uint16 * child_data_count)(*topology["childData"])
    baseline_flags = (ctypes.c_uint8 * baseline_count)(*topology["baselineFlags"])
    baseline_team_ids = (ctypes.c_int16 * baseline_count)(*([1] * baseline_count))
    baseline_starts = (ctypes.c_uint16 * baseline_count)(*topology["baselineStarts"])
    baseline_counts = (ctypes.c_uint16 * baseline_count)(*topology["baselineCounts"])
    baseline_data = (ctypes.c_uint16 * baseline_data_count)(*topology["baselineData"])
    buffers = {
        "jobBaselines": job_baselines,
        "teamData": team_data,
        "parameters": parameters,
        "attributes": attributes,
        "positions": positions,
        "rotations": rotations,
        "localPositions": local_positions,
        "localRotations": local_rotations,
        "parentIndices": parent_indices,
        "childIndices": child_indices,
        "childData": child_data,
        "baselineFlags": baseline_flags,
        "baselineTeamIds": baseline_team_ids,
        "baselineStarts": baseline_starts,
        "baselineCounts": baseline_counts,
        "baselineData": baseline_data,
    }
    before = {name: _buffer_sha256(value) for name, value in buffers.items()}
    immutable_before = _immutable_sha256(buffers)
    signature = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 16), ctypes.c_int32)
    function = signature(module._handle + core_rva)
    ordered = tuple(buffers[name] for name in (
        "jobBaselines", "teamData", "parameters", "attributes", "positions", "rotations",
        "localPositions", "localRotations", "parentIndices", "childIndices", "childData",
        "baselineFlags", "baselineTeamIds", "baselineStarts", "baselineCounts", "baselineData",
    ))
    for job_index in range(baseline_count):
        function(*(ctypes.cast(value, ctypes.c_void_p) for value in ordered), job_index)
    after = {name: _buffer_sha256(value) for name, value in buffers.items()}
    changed = [name for name in buffers if before[name] != after[name]]
    if changed != ["rotations"]:
        raise burst.ContractError(
            f"CalcLine native mutation boundary differs for {topology['ownerPath']}: {changed!r}"
        )
    immutable_after = _immutable_sha256(buffers)
    if immutable_before != immutable_after:
        raise burst.ContractError(f"CalcLine immutable aggregate changed for {topology['ownerPath']}")
    result = [tuple(float(rotations[vertex * 4 + axis]) for axis in range(4))
              for vertex in range(vertex_count)]
    return result, {
        "declaredMutableBuffers": ["rotations"],
        "changedBuffers": changed,
        "rotationBeforeSha256": before["rotations"],
        "rotationAfterSha256": after["rotations"],
        "immutableBuffers": sorted(name for name in buffers if name != "rotations"),
        "immutableBeforeSha256": immutable_before,
        "immutableAfterSha256": immutable_after,
    }


def _coverage(topology: dict[str, Any]) -> dict[str, int]:
    child_counts = [packed >> 20 for packed in topology["childIndices"]]
    return {
        "vertexCount": len(topology["attributes"]),
        "lineCount": topology["lineCount"],
        "baselineCount": len(topology["baselineFlags"]),
        "baselineParentVisitCount": sum(topology["baselineCounts"]),
        "rootCount": sum(1 for parent in topology["parentIndices"] if parent < 0),
        "leafCount": sum(1 for count in child_counts if count == 0),
        "multiChildParentCount": sum(1 for count in child_counts if count > 1),
        "fixedVertexCount": sum(1 for value in topology["attributes"] if not value & 2),
        "movableVertexCount": sum(1 for value in topology["attributes"] if value & 2),
    }


def _topology_fixture(
    module: Any,
    topologies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    owners: list[dict[str, Any]] = []
    state_names = ("bind_rest", "seeded_perturbation_a", "seeded_perturbation_b")
    for owner_index, topology in enumerate(topologies):
        states = []
        for state_index, state_name in enumerate(state_names):
            positions, input_rotations = _perturbed_state(topology, owner_index, state_index)
            source = _source_topology_state(topology, positions, input_rotations)
            source_bits = _rotation_bits(source)
            native_mutation: dict[str, Any] = {}
            for variant, rva, _size, _sha256, _helper in CORE_VARIANTS:
                native, mutation = _native_topology_state(
                    module, rva, topology, positions, input_rotations
                )
                native_bits = _rotation_bits(native)
                if native_bits != source_bits:
                    first = next(
                        index for index, (native_row, source_row) in enumerate(
                            zip(native_bits, source_bits)
                        ) if native_row != source_row
                    )
                    raise burst.ContractError(
                        f"CalcLine topology transcription differs for "
                        f"{variant}/{topology['ownerPath']}/{state_name} at vertex {first}: "
                        f"native={native_bits[first]!r} source={source_bits[first]!r}"
                    )
                native_mutation[variant] = mutation
            states.append({
                "name": state_name,
                "positionBitsLe": _position_bits(positions),
                "inputRotationBitsLe": _rotation_bits(input_rotations),
                "outputRotationBitsLe": source_bits,
                "nativeMutation": native_mutation,
            })
        owners.append({
            "ownerPath": topology["ownerPath"],
            "topologySha256": topology["topologySha256"],
            "sourceArraySha256": topology["sourceArraySha256"],
            "coverage": _coverage(topology),
            "attributes": topology["attributes"],
            "parentIndices": topology["parentIndices"],
            "childIndices": topology["childIndices"],
            "childData": topology["childData"],
            "localPositionBitsLe": [
                [struct.pack("<f", lane).hex() for lane in row]
                for row in topology["localPositions"]
            ],
            "localRotationBitsLe": _rotation_bits(topology["localRotations"]),
            "baselineFlags": topology["baselineFlags"],
            "baselineStarts": topology["baselineStarts"],
            "baselineCounts": topology["baselineCounts"],
            "baselineData": topology["baselineData"],
            "negativeScaleDirectionBitsLe": [struct.pack("<f", 1.0).hex()] * 3,
            "negativeScaleQuaternionBitsLe": [struct.pack("<f", 1.0).hex()] * 4,
            "rotationalInterpolationBitsLe": struct.pack(
                "<f", topology["rotationalInterpolation"]
            ).hex(),
            "rootRotationBitsLe": struct.pack("<f", topology["rootRotation"]).hex(),
            "states": states,
        })
    return owners


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
    payload_decode = _load_pinned_json(
        PAYLOAD_DECODE,
        EXPECTED_PAYLOAD_DECODE_SHA256,
        "endfield.charinfo.secondary-dynamics-payload-decoder.v2",
    )
    solver_inputs = _load_pinned_json(
        SOLVER_INPUTS,
        EXPECTED_SOLVER_INPUTS_SHA256,
        "endfield.charinfo.secondary-dynamics-solver-inputs.v1",
    )
    topologies = _decode_endminf_topologies(payload_decode, solver_inputs)
    topology_cases = _topology_fixture(module, topologies)
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
        "schema": "endfield.charinfo.secondary-dynamics-calc-line-burst-golden-vectors.v2",
        "status": "dual_cpu_core_source_and_endminf_topology_exact",
        "nativeGate": gate,
        "sourceFiles": {
            "payloadDecode": {
                "repoPath": str(PAYLOAD_DECODE.relative_to(LAB_ROOT.parent)).replace("\\", "/"),
                "size": PAYLOAD_DECODE.stat().st_size,
                "sha256": EXPECTED_PAYLOAD_DECODE_SHA256,
                "schema": payload_decode["schema"],
            },
            "solverInputs": {
                "repoPath": str(SOLVER_INPUTS.relative_to(LAB_ROOT.parent)).replace("\\", "/"),
                "size": SOLVER_INPUTS.stat().st_size,
                "sha256": EXPECTED_SOLVER_INPUTS_SHA256,
                "schema": solver_inputs["schema"],
            },
        },
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
                "mulBurstBinary32(fromTo(rest,direction,1), "
                "mulBurstBinary32(parentRotation, "
                "localRotation*negativeScaleQuaternion))"
            ),
            "childWriteGate": (
                "only children with attributes & Flag_Move (0x02) write rotations; "
                "fixed children contribute rest direction but preserve their incoming lane"
            ),
            "parentRotation": (
                "mulBurstBinary32(fromTo(restSum,direction,selectedInterpolation), "
                "incomingParentRotation)"
            ),
            "quaternionGrouping": (
                "Unity.Mathematics packed float4 grouping: "
                "(left.wwww*right + (left.xyzx*right.wwwx + "
                "left.yzxy*right.zxyy)*float4(1,1,1,-1)) - "
                "left.zxyz*right.yzxz"
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
        "endminfTopologyCases": topology_cases,
        "boundary": {
            "nativeCpuVariantsExecuted": [variant for variant, *_rest in CORE_VARIANTS],
            "sourceOnlyTranscriptionMatchedBitForBit": True,
            "caseCount": len(rows),
            "endminfOwnerCount": len(topology_cases),
            "endminfStateCountPerOwner": 3,
            "endminfTopologyCaseCount": sum(len(owner["states"]) for owner in topology_cases),
            "fullBaselinePackedChildTraversalExecuted": True,
            "rotationOnlyMutationProven": True,
            "captureUsed": False,
            "runtimeRouteSelected": False,
            "writebackConnected": False,
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
