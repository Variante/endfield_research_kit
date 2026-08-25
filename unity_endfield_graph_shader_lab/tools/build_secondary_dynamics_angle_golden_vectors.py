#!/usr/bin/env python3
"""Execute the pinned Burst AngleConstraint core and publish golden vectors."""

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
    "secondary_dynamics_angle_golden_vectors.json"
)
PAYLOAD_DECODE = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_payload_decode.json"
)
CORE_RVA = 0x303D40
CORE_BYTES = 6480
CORE_SHA256 = "d3d5d8f685a57d0495d39a5068d8bae97db9fae0b247235a734293264edd2666"
RANGE_WRAPPER_RVA = 0x3108B0
RANGE_WRAPPER_BYTES = 334
RANGE_WRAPPER_SHA256 = "362a8deabacb21f171f513ee892cabccfc47c1bd6a565d2b0d8ffd67dbaafc34"
SINCOS_RVA = 0x1E5D30
SINCOS_BYTES = 521
SINCOS_SHA256 = "3021151e64547f2cc7e4266b846da35bbb8eef05f00d864a357f9757e730f0a6"
_SINCOS: Any | None = None
_MCW_DN = 0x03000000
_DN_FLUSH = 0x01000000


CONTROLLED_CASES: tuple[dict[str, Any], ...] = (
    {"name": "restoration_only_aligned", "next": [(0, 0, 0), (1, 0, 0)],
     "restoration": True},
    {"name": "restoration_only_bent", "next": [(0, 0, 0), (0, 1, 0)],
     "restoration": True, "restorationStrength": 0.35},
    {"name": "hair_limit_inside_cone", "next": [(0, 0, 0), (1, 0.08, 0)],
     "limit": True, "limitDegrees": 10.0, "limitStiffness": 1.0},
    {"name": "hair_limit_outside_cone", "next": [(0, 0, 0), (0, 1, 0)],
     "limit": True, "limitDegrees": 10.0, "limitStiffness": 1.0},
    {"name": "combined_limit_then_restoration", "next": [(0, 0, 0), (0, 1, 0)],
     "limit": True, "limitDegrees": 10.0, "limitStiffness": 1.0,
     "restoration": True, "restorationStrength": 0.125,
     "restorationVelocityAttenuation": 0.6},
    {"name": "active_parent_writeback", "next": [(0, 0, 0), (0, 1, 0)],
     "restoration": True, "restorationStrength": 0.125,
     "restorationVelocityAttenuation": 0.0, "attributes": [2, 2]},
    {"name": "friction_mobility", "next": [(0, 0, 0), (0, 1, 0)],
     "restoration": True, "restorationStrength": 0.35,
     "friction": [0.25, 0.75], "restorationVelocityAttenuation": 0.0},
)


def _array_values(value: Any) -> list[Any]:
    if isinstance(value, dict) and "values" in value:
        return value["values"]
    if isinstance(value, list):
        return value
    raise burst.ContractError(f"decoded payload array has unexpected shape: {type(value).__name__}")


def _vector_values(value: Any) -> tuple[float, ...]:
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    return tuple(map(float, value))


def _endminf_baseline_cases() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload_bytes = PAYLOAD_DECODE.read_bytes()
    payload = json.loads(payload_bytes)
    cases: list[dict[str, Any]] = []
    expected_shapes = {
        "MC_Ribbon2": [6],
        "MC_Hair": [4, 4, 4, 4, 3, 3, 4, 3],
        "MC_Ribbon": [4, 5, 4, 5],
        "MC_Coat": [9, 4, 6, 9, 4],
    }
    for cloth in payload["actors"]["endminf"]["cloths"]:
        cloth_name = cloth["game_object_path"]
        if cloth_name not in expected_shapes:
            continue
        arrays = cloth["proxy_mesh_arrays"]
        starts = list(map(int, _array_values(arrays["baseLineStartDataIndices"])))
        counts = list(map(int, _array_values(arrays["baseLineDataCounts"])))
        data = list(map(int, _array_values(arrays["baseLineData"])))
        attributes = list(map(int, _array_values(arrays["attributes"])))
        depths = list(map(float, _array_values(arrays["vertexDepths"])))
        parents = list(map(int, _array_values(arrays["vertexParentIndices"])))
        positions = [_vector_values(row) for row in _array_values(arrays["vertexBindPosePositions"])]
        rotations = [_vector_values(row) for row in _array_values(arrays["vertexBindPoseRotations"])]
        if counts != expected_shapes[cloth_name]:
            raise burst.ContractError(
                f"Endminf {cloth_name} baseline shape drift: {counts} != {expected_shapes[cloth_name]}")
        for baseline_index, (start, count) in enumerate(zip(starts, counts)):
            source_vertices = data[start:start + count]
            local_index = {vertex: index for index, vertex in enumerate(source_vertices)}
            local_parents = [-1]
            for vertex in source_vertices[1:]:
                parent = parents[vertex]
                if parent not in local_index:
                    raise burst.ContractError(
                        f"Endminf {cloth_name} baseline {baseline_index} parent {parent} "
                        f"is outside ordered data {source_vertices}")
                local_parents.append(local_index[parent])
            basic = [positions[vertex] for vertex in source_vertices]
            # The decoded rest positions produce a non-axis-aligned restoration
            # vector on every edge. Starting at that exact pose keeps this a
            # source-exact native vector while still exposing the immediate
            # parent/child writes made by each of the three ordered sweeps.
            next_positions = list(basic)
            velocity = [
                (1.0 + ordinal, -2.0 - ordinal, 0.5 + ordinal * 0.25)
                for ordinal in range(count)
            ]
            friction = []
            for ordinal in range(count):
                friction.append(_f32((ordinal % 4) * 0.125))
            slug = cloth_name.removeprefix("MC_").lower()
            cases.append({
                "name": f"endminf_{slug}_baseline_{baseline_index}_n{count}",
                "source": {"actor": "endminf", "cloth": cloth_name,
                           "baselineIndex": baseline_index,
                           "sourceVertexIndices": source_vertices},
                "next": next_positions,
                "velocity": velocity,
                "friction": friction,
                "basic": basic,
                "basicRotation": [rotations[vertex] for vertex in source_vertices],
                "attributes": [attributes[vertex] for vertex in source_vertices],
                "depths": [depths[vertex] for vertex in source_vertices],
                "parents": local_parents,
                "limit": False,
                "restoration": True,
                "restorationStrength": 0.3125,
                "restorationVelocityAttenuation": 0.45,
                "restorationGravityFalloff": 0.2,
                "simulationPowerW": 0.8,
                "gravityDot": 0.35,
            })
    return cases, {
        "path": PAYLOAD_DECODE.relative_to(LAB_ROOT.parent).as_posix(),
        "bytes": len(payload_bytes),
        "sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "actor": "endminf",
        "clothBaselineShapes": expected_shapes,
    }


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


def _fclamp(value: float, lo: float, hi: float) -> float:
    return min(max(_f32(value), _f32(lo)), _f32(hi))


def _d3_add(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float]:
    return tuple(a[i] + b[i] for i in range(3))  # type: ignore[return-value]


def _d3_sub(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float]:
    return tuple(a[i] - b[i] for i in range(3))  # type: ignore[return-value]


def _d3_mul(a: tuple[float, ...], scalar: float) -> tuple[float, float, float]:
    return tuple(a[i] * scalar for i in range(3))  # type: ignore[return-value]


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _length(a: tuple[float, ...]) -> float:
    return math.sqrt(_dot(a, a))


def _normalize(a: tuple[float, ...]) -> tuple[float, float, float]:
    length = _length(a)
    return _d3_mul(a, 1.0 / length)


def _curve(depth: float, values: list[float]) -> float:
    clamped = _fclamp(depth, 0.0, 1.0)
    scaled = _fmul(clamped, 15.0)
    index = math.trunc(scaled)
    step = _f32(0.06666667014360428)
    fraction = _fdiv(_fsub(depth, _fmul(float(index), step)), step)
    i0, i1 = min(max(index, 0), 15), min(max(index + 1, 0), 15)
    return _fadd(values[i0], _fmul(fraction, _fsub(values[i1], values[i0])))


def _asin_poly(s: float, y: float) -> float:
    a0, a1 = 0.031615876506539346, 0.012153605255773773
    a2, a3 = 0.019290454772679107, 0.017359569912236146
    b0, b1 = -0.015819182433299966, 0.013887151845016092
    b2, b3 = 0.006606077476277171, 0.022371761819320483
    c0, c1 = 0.07500000000378582, 0.16666666666664975
    d0, d1 = 0.030381959280381322, 0.044642856813771024
    y2 = y * y
    t0 = b2 + a2 * y + y2 * (b0 + a0 * y)
    t1 = b3 + a3 * y + y2 * (b1 + a1 * y)
    p = c1 + c0 * y + y2 * (d1 + d0 * y) + y2 * y2 * t1 + y2 ** 4 * t0
    return s + s * y * p


def _acos_burst(value: float) -> float:
    x = min(max(value, -1.0), 1.0)
    ax = abs(x)
    if ax < 0.5:
        asin = _asin_poly(ax, ax * ax)
    else:
        y = (1.0 - ax) * 0.5
        asin = math.pi * 0.5 - 2.0 * _asin_poly(math.sqrt(y), y)
    if x < 0.0:
        asin = -asin
    return math.pi * 0.5 - asin


def _qmul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    ax, ay, az, aw = (_f32(v) for v in a)
    bx, by, bz, bw = (_f32(v) for v in b)
    return (
        _fadd(_fadd(_fmul(aw, bx), _fmul(ax, bw)), _fsub(_fmul(ay, bz), _fmul(az, by))),
        _fadd(_fadd(_fmul(aw, by), _fmul(ay, bw)), _fsub(_fmul(az, bx), _fmul(ax, bz))),
        _fadd(_fadd(_fmul(aw, bz), _fmul(az, bw)), _fsub(_fmul(ax, by), _fmul(ay, bx))),
        _fsub(_fsub(_fsub(_fmul(aw, bw), _fmul(ax, bx)), _fmul(ay, by)), _fmul(az, bz)),
    )


def _qrotate(q: tuple[float, ...], v: tuple[float, ...]) -> tuple[float, float, float]:
    xyz = (float(q[0]), float(q[1]), float(q[2]))
    t = _d3_mul(_cross(xyz, v), 2.0)
    return _d3_add(v, _d3_add(_d3_mul(t, float(q[3])), _cross(xyz, t)))


def _qinverse(q: tuple[float, ...]) -> tuple[float, float, float, float]:
    return (_f32(-q[0]), _f32(-q[1]), _f32(-q[2]), _f32(q[3]))


def _axis_angle(axis: tuple[float, ...], angle: float) -> tuple[float, float, float, float]:
    af = tuple(_f32(v) for v in axis)
    half = _fmul(_f32(angle), 0.5)
    if _SINCOS is None:
        raise burst.ContractError("pinned Burst sincos helper is not initialized")
    sine, cosine = _SINCOS(half)
    return (_fmul(af[0], sine), _fmul(af[1], sine), _fmul(af[2], sine), cosine)


def _rotation_between(source: tuple[float, ...], target: tuple[float, ...],
                      requested_angle: float | None = None) -> tuple[float, float, float, float]:
    sn, tn = _normalize(source), _normalize(target)
    cosine = min(max(_dot(sn, tn), -1.0), 1.0)
    angle = _acos_burst(cosine) if requested_angle is None else requested_angle
    if abs(1.0 - cosine) < 9.999999974752427e-7:
        return (0.0, 0.0, 0.0, 1.0)
    if abs(1.0 + cosine) < 9.999999974752427e-7:
        helper = (1.0, 1.0, 1.0) if abs(sn[0]) > abs(sn[1]) else (1.0, 0.0, 0.0)
        axis = _normalize(_cross(sn, helper))
        angle = 3.1415927410125732 if requested_angle is None else requested_angle
    else:
        axis = _normalize(_cross(sn, tn))
    return _axis_angle(axis, angle)


def _mobility(friction: float) -> float:
    return _fdiv(1.0, _fadd(1.0, _fmul(3.0, friction)))


def _defaults(case: dict[str, Any]) -> dict[str, Any]:
    count = len(case["next"])
    return {
        "attributes": list(case.get("attributes", [0] + [2] * (count - 1))),
        "depths": [_f32(v) for v in case.get(
            "depths", [0.0] + [index / (count - 1) for index in range(1, count)])],
        "friction": [_f32(v) for v in case.get("friction", [0.0] * count)],
        "velocity": [tuple(map(float, v)) for v in case.get("velocity", [(0, 0, 0)] * count)],
        "basic": [tuple(map(float, v)) for v in case.get(
            "basic", [(float(index), 0.0, 0.0) for index in range(count)])],
        "basicRotation": [tuple(map(float, v)) for v in case.get(
            "basicRotation", [(0.0, 0.0, 0.0, 1.0)] * count)],
        "parents": list(map(int, case.get("parents", [-1] + list(range(count - 1))))),
        "restoration": bool(case.get("restoration", False)),
        "restorationCurve": [_f32(case.get("restorationStrength", 1.0))] * 16,
        "restorationVelocityAttenuation": _f32(case.get("restorationVelocityAttenuation", 0.6)),
        "restorationGravityFalloff": _f32(case.get("restorationGravityFalloff", 0.0)),
        "limit": bool(case.get("limit", False)),
        "limitCurve": [_f32(case.get("limitDegrees", 10.0))] * 16,
        "limitStiffness": _f32(case.get("limitStiffness", 1.0)),
        "simulationPowerW": _f32(case.get("simulationPowerW", 1.0)),
        "gravityDot": _f32(case.get("gravityDot", 1.0)),
    }


def source_port(case: dict[str, Any]) -> dict[str, Any]:
    v = _defaults(case)
    count = len(case["next"])
    next_pos = [tuple(map(float, row)) for row in case["next"]]
    velocity = list(v["velocity"])
    rotations = list(v["basicRotation"])
    lengths = [0.0] * count
    local_pos = [(0.0, 0.0, 0.0)] * count
    local_rot = [(0.0, 0.0, 0.0, 0.0)] * count
    restoration_vectors = [(0.0, 0.0, 0.0)] * count
    for child in range(count):
        rotations[child] = v["basicRotation"][child]
        parent = v["parents"][child]
        if parent < 0:
            continue
        if v["limit"]:
            lengths[child] = _f32(_length(_d3_sub(next_pos[parent], next_pos[child])))
            basic_direction = _normalize(_d3_sub(v["basic"][child], v["basic"][parent]))
            local_pos[child] = tuple(_f32(x) for x in _qrotate(
                _qinverse(v["basicRotation"][parent]), basic_direction))
            local_rot[child] = _qmul(
                _qinverse(v["basicRotation"][parent]), v["basicRotation"][child])
        if v["restoration"]:
            restoration_vectors[child] = tuple(
                _f32(x) for x in _d3_sub(v["basic"][child], v["basic"][parent]))

    for sweep in range(3):
        t = _fadd(_fmul(_fmul(float(sweep), 0.5), 0.4), 0.1)
        one_minus_t = _fsub(1.0, t)
        for child in range(1, count):
            parent = v["parents"][child]
            p, q = next_pos[child], next_pos[parent]
            child_mobility = float(_mobility(v["friction"][child]))
            parent_mobility = float(_mobility(v["friction"][parent]))
            if v["limit"]:
                u = _qrotate(rotations[parent], tuple(float(x) for x in local_pos[child]))
                d = _d3_sub(p, q)
                current_length = _length(d)
                blend_length = current_length + 0.5 * (float(lengths[child]) - current_length)
                direction = _d3_mul(d, 1.0 / current_length)
                vv = _d3_mul(direction, blend_length)
                limit_radians = _fmul(_curve(v["depths"][child], v["limitCurve"]),
                                      _f32(0.01745329238474369))
                phi = _acos_burst(min(max(_dot(vv, u) / (_length(vv) * _length(u)), -1.0), 1.0))
                vlimit = vv
                if phi > float(limit_radians):
                    vn, un = _normalize(vv), _normalize(u)
                    psi = _acos_burst(min(max(_dot(vn, un), -1.0), 1.0))
                    beta = phi + float(v["limitStiffness"]) * (float(limit_radians) - phi)
                    if beta < psi:
                        theta = psi * ((psi - beta) / psi)
                        vlimit = _qrotate(_rotation_between(vn, un, theta), vv)
                child_target = _d3_add(q, _d3_add(
                    _d3_mul(vv, float(_f32(0.4000000059604645))),
                    _d3_mul(vlimit, float(_f32(0.6000000238418579)))))
                child_corr = _d3_mul(_d3_sub(child_target, p), child_mobility)
                next_pos[child] = _d3_add(p, child_corr)
                velocity[child] = _d3_add(
                    velocity[child], _d3_mul(child_corr, float(_f32(0.8999999761581421))))
                if v["attributes"][parent] & 2:
                    parent_corr = _d3_mul(_d3_sub(vv, vlimit),
                                          parent_mobility * float(_f32(0.4000000059604645)))
                    next_pos[parent] = _d3_add(q, parent_corr)
                    velocity[parent] = _d3_add(
                        velocity[parent], _d3_mul(parent_corr, float(_f32(0.8999999761581421))))
                dnew = _d3_sub(next_pos[child], next_pos[parent])
                qbase = _qmul(rotations[parent], local_rot[child])
                qdelta = _rotation_between(u, dnew)
                rotations[child] = _qmul(qdelta, qbase)

            if v["restoration"]:
                p, q = next_pos[child], next_pos[parent]
                d = _d3_sub(p, q)
                rest = tuple(float(x) for x in restoration_vectors[child])
                dn, rn = _normalize(d), _normalize(rest)
                angle = _acos_burst(min(max(_dot(dn, rn), -1.0), 1.0))
                strength = _fclamp(_curve(v["depths"][child], v["restorationCurve"]), 0.0, 1.0)
                strength = _fclamp(_fmul(strength, v["simulationPowerW"]), 0.0, 1.0)
                gravity_mix = _fadd(_fsub(1.0, v["restorationGravityFalloff"]),
                                    _fmul(v["gravityDot"], v["restorationGravityFalloff"]))
                strength = _fmul(strength, gravity_mix)
                drot = _qrotate(_rotation_between(dn, rn, angle * float(strength)), d)
                weighted_current = _d3_add(q, _d3_mul(d, float(t)))
                child_target = _d3_add(weighted_current, _d3_mul(drot, float(one_minus_t)))
                child_corr = _d3_mul(_d3_sub(child_target, p), parent_mobility)
                next_pos[child] = _d3_add(p, child_corr)
                velocity[child] = _d3_add(
                    velocity[child], _d3_mul(child_corr, float(v["restorationVelocityAttenuation"])))
                if v["attributes"][parent] & 2:
                    # The AVX2 body deliberately forms (Q+t*d)-t*dRot-Q before
                    # applying mobility; preserving those cancellation points is
                    # observable in the binary64 result.
                    parent_delta = _d3_sub(
                        _d3_sub(weighted_current, _d3_mul(drot, float(t))), q)
                    parent_corr = _d3_mul(parent_delta, child_mobility)
                    next_pos[parent] = _d3_add(q, parent_corr)
                    velocity[parent] = _d3_add(
                        velocity[parent],
                        _d3_mul(parent_corr, float(v["restorationVelocityAttenuation"])))
    return {"next": next_pos, "velocity": velocity, "rotation": rotations,
            "length": lengths, "localPos": local_pos, "localRot": local_rot,
            "restorationVector": restoration_vectors}


def _make_native_function(dll: Path) -> tuple[Any, Any]:
    module = ctypes.WinDLL(str(dll))
    signature = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 20), ctypes.c_int32)
    return module, signature(module._handle + CORE_RVA)


def _enable_unity_denormal_mode() -> dict[str, Any]:
    """Match Burst/Unity's flush-denormals execution mode in this process."""
    control = ctypes.c_uint32()
    result = ctypes.CDLL("msvcrt")._controlfp_s(
        ctypes.byref(control), _DN_FLUSH, _MCW_DN)
    if result != 0 or control.value & _MCW_DN != _DN_FLUSH:
        raise burst.ContractError(
            f"could not enable flush-denormals mode: result={result} control=0x{control.value:x}")
    return {"denormalControlMask": f"0x{_MCW_DN:x}",
            "denormalMode": "flush", "controlWord": f"0x{control.value:x}"}


def _make_sincos(module: Any) -> tuple[Any, int]:
    """Expose Burst's packed-XMM sincos through a tiny Windows-x64 ABI thunk."""
    # void thunk(void* target, float x, float* out): preserve out across the
    # call, move x from XMM1 to the helper's XMM0 input, then store both return
    # lanes. The thunk itself contains no numeric implementation.
    code = bytes.fromhex(
        "4883ec38"          # sub rsp,38h
        "4c89442420"        # mov [rsp+20h],r8
        "0f28c1"            # movaps xmm0,xmm1
        "ffd1"              # call rcx
        "4c8b442420"        # mov r8,[rsp+20h]
        "410f1300"          # movlps [r8],xmm0
        "4883c438"          # add rsp,38h
        "c3"                # ret
    )
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    address = kernel32.VirtualAlloc(None, len(code), 0x3000, 0x40)
    if not address:
        raise burst.ContractError(f"VirtualAlloc for sincos ABI thunk failed: {ctypes.get_last_error()}")
    ctypes.memmove(address, code, len(code))
    thunk_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float,
                                 ctypes.POINTER(ctypes.c_float))
    thunk = thunk_type(address)
    target = module._handle + SINCOS_RVA

    def invoke(value: float) -> tuple[float, float]:
        result = (ctypes.c_float * 2)()
        thunk(target, _f32(value), result)
        return float(result[0]), float(result[1])

    return invoke, int(address)


def _run_native(function: Any, case: dict[str, Any]) -> dict[str, Any]:
    v = _defaults(case)
    count = len(case["next"])
    sizes = [16, 4, 464, 808, count, count * 4, count * 4, 2, 2,
             count * 2, count * 24, count * 24, count * 4, count * 24,
             count * 16, count * 4, count * 12, count * 16, count * 16,
             count * 12]
    # Burst emits widened vector loads/stores around several float3/double3
    # arrays. Keep guard storage after every logical allocation so the native
    # probe cannot corrupt an adjacent ctypes object while preserving the
    # exact logical array addresses and strides.
    buffers = [ctypes.create_string_buffer(size + 256) for size in sizes]
    (sim, step, team, params, attrs, depths, parents, starts, counts, data,
     next_pos, velocity, friction, basic_pos, basic_rot, lengths, local_pos,
     local_rot, rotations, restoration) = buffers
    struct.pack_into("<f", sim, 12, v["simulationPowerW"])
    struct.pack_into("<I", step, 0, 0)
    struct.pack_into("<f", team, 0x44, v["gravityDot"])
    struct.pack_into("<i", team, 0x124, 0)
    struct.pack_into("<i", team, 0x164, 0)
    struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<B", params, 0x140, int(v["restoration"]))
    struct.pack_into("<16f", params, 0x144, *v["restorationCurve"])
    struct.pack_into("<f", params, 0x184, v["restorationVelocityAttenuation"])
    struct.pack_into("<f", params, 0x188, v["restorationGravityFalloff"])
    struct.pack_into("<B", params, 0x18C, int(v["limit"]))
    struct.pack_into("<16f", params, 0x190, *v["limitCurve"])
    struct.pack_into("<f", params, 0x1D0, v["limitStiffness"])
    struct.pack_into(f"<{count}B", attrs, 0, *v["attributes"])
    struct.pack_into(f"<{count}f", depths, 0, *v["depths"])
    struct.pack_into(f"<{count}i", parents, 0, *v["parents"])
    struct.pack_into("<H", starts, 0, 0)
    struct.pack_into("<H", counts, 0, count)
    struct.pack_into(f"<{count}H", data, 0, *range(count))
    for index in range(count):
        struct.pack_into("<3d", next_pos, index * 24, *case["next"][index])
        struct.pack_into("<3d", velocity, index * 24, *v["velocity"][index])
        struct.pack_into("<f", friction, index * 4, v["friction"][index])
        struct.pack_into("<3d", basic_pos, index * 24, *v["basic"][index])
        struct.pack_into("<4f", basic_rot, index * 16, *v["basicRotation"][index])
    function(*(ctypes.addressof(buffer) for buffer in buffers), 0)
    return {
        "next": [struct.unpack_from("<3d", next_pos, i * 24) for i in range(count)],
        "velocity": [struct.unpack_from("<3d", velocity, i * 24) for i in range(count)],
        "rotation": [struct.unpack_from("<4f", rotations, i * 16) for i in range(count)],
        "length": list(struct.unpack_from(f"<{count}f", lengths, 0)),
        "localPos": [struct.unpack_from("<3f", local_pos, i * 12) for i in range(count)],
        "localRot": [struct.unpack_from("<4f", local_rot, i * 16) for i in range(count)],
        "restorationVector": [struct.unpack_from("<3f", restoration, i * 12) for i in range(count)],
    }


def _bits(value: Any, fmt: str) -> Any:
    if isinstance(value, (list, tuple)):
        return [_bits(item, fmt) for item in value]
    return struct.pack(fmt, value).hex()


def _flatten(rows: list[Any]) -> list[Any]:
    return [value for row in rows for value in row]


def _unity_baseline_vector(case: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    v = _defaults(case)
    return {
        "name": case["name"],
        "cloth": case["source"]["cloth"],
        "baselineIndex": case["source"]["baselineIndex"],
        "sourceVertexIndices": case["source"]["sourceVertexIndices"],
        "attributes": v["attributes"],
        "parents": v["parents"],
        "depths": v["depths"],
        "frictions": v["friction"],
        "basicPositions": _flatten(v["basic"]),
        "basicPositionBits": _flatten(_bits(v["basic"], "<d")),
        "basicRotations": _flatten(v["basicRotation"]),
        "basicRotationBits": _flatten(_bits(v["basicRotation"], "<f")),
        "nextPositions": _flatten(case["next"]),
        "nextInputBits": _flatten(_bits(case["next"], "<d")),
        "velocityPositions": _flatten(v["velocity"]),
        "velocityInputBits": _flatten(_bits(v["velocity"], "<d")),
        "restorationCurve": v["restorationCurve"],
        "restorationVelocityAttenuation": v["restorationVelocityAttenuation"],
        "restorationGravityFalloff": v["restorationGravityFalloff"],
        "simulationPowerW": v["simulationPowerW"],
        "gravityDot": v["gravityDot"],
        "nextBits": _flatten(_bits(output["next"], "<d")),
        "velocityBits": _flatten(_bits(output["velocity"], "<d")),
        "rotationBits": _flatten(_bits(output["rotation"], "<f")),
        "lengthBits": _bits(output["length"], "<f"),
        "localPositionBits": _flatten(_bits(output["localPos"], "<f")),
        "localRotationBits": _flatten(_bits(output["localRot"], "<f")),
        "restorationVectorBits": _flatten(_bits(output["restorationVector"], "<f")),
    }


def _validate_range_wrapper(pe: dict[str, Any]) -> dict[str, Any]:
    _, instructions = burst._exact_rva_span(
        pe, RANGE_WRAPPER_RVA, RANGE_WRAPPER_BYTES, RANGE_WRAPPER_SHA256)
    rows = {ins.address - pe["imageBase"]: (ins.mnemonic, ins.op_str) for ins in instructions}
    pins = {
        0x3108D2: ("mov", "r15d, dword ptr [rax]"),
        0x310900: ("mov", "dword ptr [rsp + 0xa0], r12d"),
        0x3109D9: ("call", "0x180303d40"),
        0x3109DE: ("inc", "r12d"),
    }
    for rva, expected in pins.items():
        if rows.get(rva) != expected:
            raise burst.ContractError(
                f"Angle range-wrapper ABI drift at 0x{rva:x}: {rows.get(rva)}")
    return {"rva": f"0x{RANGE_WRAPPER_RVA:x}", "bytes": RANGE_WRAPPER_BYTES,
            "sha256": RANGE_WRAPPER_SHA256,
            "wrapperFinalArgument": "pointer to int32 range count",
            "coreArgument21": "int32 rangeIndex value"}


def _assert_exact(case_name: str, native: dict[str, Any], source: dict[str, Any]) -> None:
    formats = {"next": "<d", "velocity": "<d", "rotation": "<f", "length": "<f",
               "localPos": "<f", "localRot": "<f", "restorationVector": "<f"}
    for key, fmt in formats.items():
        if _bits(native[key], fmt) != _bits(source[key], fmt):
            raise burst.ContractError(
                f"source AngleConstraint transcription differs from native core: "
                f"{case_name} {key} native={native[key]} source={source[key]}")


def build_contract() -> dict[str, Any]:
    global _SINCOS
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    wrapper = _validate_range_wrapper(pe)
    burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    module, function = _make_native_function(dll)
    float_mode = _enable_unity_denormal_mode()
    burst._exact_rva_span(pe, SINCOS_RVA, SINCOS_BYTES, SINCOS_SHA256)
    _SINCOS, thunk_address = _make_sincos(module)
    baseline_cases, payload_source = _endminf_baseline_cases()
    cases = list(CONTROLLED_CASES) + baseline_cases
    vectors = []
    unity_baseline_vectors = []
    for case in cases:
        native = _run_native(function, case)
        source = source_port(case)
        _assert_exact(case["name"], native, source)
        vectors.append({"name": case["name"], "input": case, "output": native,
                        "outputBits": {key: _bits(value, "<d" if key in {"next", "velocity"} else "<f")
                                       for key, value in native.items()}})
        if "source" in case:
            unity_baseline_vectors.append(_unity_baseline_vector(case, native))
    del thunk_address
    return {
        "schema": "endfield.charinfo.secondary-dynamics-angle-golden-vectors.v1",
        "status": "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
        "nativeGate": gate, "rangeWrapperAbi": wrapper,
        "nativeFloatMode": float_mode,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES,
                 "sha256": CORE_SHA256, "argument21": "int32 rangeIndex value"},
        "transcendentalHelper": {"role": "source transcription exact float sincos",
                                  "rva": f"0x{SINCOS_RVA:x}", "bytes": SINCOS_BYTES,
                                  "sha256": SINCOS_SHA256},
        "endminfPayloadSource": payload_source,
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": vectors,
        "unityBaselineVectors": unity_baseline_vectors,
        "boundary": {"nativeCoreExecuted": True, "sourceTranscriptionAllWrittenBitsMatched": True,
                     "rangeWrapperArgument21Confirmed": True,
                     "caseCoverage": [case["name"] for case in cases],
                     "controlledTwoParticleVectorCount": len(CONTROLLED_CASES),
                     "endminfFullBaselineVectorCount": len(baseline_cases),
                     "endminfBaselineParticleCountRange": [3, 9],
                     "orderedSweepCount": 3,
                     "orderedInterParticleWritesPreserved": True,
                     "sourceTranscriptionCallsPinnedNativeSincos": True,
                     "standaloneSincosTranscriptionComplete": True,
                     "standaloneSincosContract": "secondary_dynamics_float_sincos_golden_vectors.json",
                     "unityPortExecuted": True,
                     "unityVerifier": "EndfieldGraphShaderLabEditor.EndfieldSecondaryDynamicsKernelGoldenVerifier.VerifyMenu"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_contract(), indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit("Angle golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
