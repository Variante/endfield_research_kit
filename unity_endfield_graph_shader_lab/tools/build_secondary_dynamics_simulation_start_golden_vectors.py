#!/usr/bin/env python3
"""Execute controlled Simulation Start cases in the pinned AVX2 core."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Callable

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_simulation_start_golden_vectors.json"
)
CORE_RVA = 0x25E830
CORE_BYTES = 5074
CORE_SHA256 = "19b635fc37d878779e286408bcb58ea5abd3746f2f508f90fe634028d6bae9cc"
SIN_RVA = 0x23C490
SIN_BYTES = 720
SIN_SHA256 = "4b74ab7e0a799b053d616b14cf3380c3124a112d3756786a6df6c17f3d0521e4"
COS_RVA = 0x23C1C0
COS_BYTES = 718
COS_SHA256 = "6dd6e6504c6daed91f592c93fb0c0a6716787a20d2214fd83d4ed6e845ca0b8f"
SLERP_SIN_RVA = 0x1DE610
SLERP_SIN_BYTES = 557
SLERP_SIN_SHA256 = "d11fc448307689e5bf1c981bf1cae17af4604d6fa0105aa2196b162048a1c6ac"


DEFAULTS: dict[str, Any] = {
    "simulationPower": (0.0, 0.0, 1.0, 0.0),
    "dt": 0.5,
    "attribute": 2,
    "depth": 0.0,
    "position": (0.0, 0.0, 0.0),
    "rotation": (0.0, 0.0, 0.0, 1.0),
    "oldTransformPosition": (0.0, 0.0, 0.0),
    "oldTransformRotation": (0.0, 0.0, 0.0, 1.0),
    "oldPos": (0.0, 0.0, 0.0),
    "velocity": (0.0, 0.0, 0.0),
    "friction": 0.0,
    "frameInterpolation": 1.0,
    "teamTime": 0.0,
    "teamFlag": 0,
    "gravityRatio": 1.0,
    "scaleRatio": 1.0,
    "velocityWeight": 1.0,
    "forceMode": 0,
    "impactForce": (0.0, 0.0, 0.0),
    "gravity": 0.0,
    "gravityDirection": (0.0, -1.0, 0.0),
    "dampingCurve": (0.0,) * 16,
    "normalAxis": 0,
    "inertiaDepth": 0.0,
    "centerOldWorldPosition": (0.0, 0.0, 0.0),
    "centerStepVector": (0.0, 0.0, 0.0),
    "centerStepRotation": (0.0, 0.0, 0.0, 1.0),
    "centerInertiaVector": (0.0, 0.0, 0.0),
    "centerInertiaRotation": (0.0, 0.0, 0.0, 1.0),
    "springPower": 0.0,
    "springLimitDistance": 1.0,
    "springNormalLimitRatio": 1.0,
    "springNoise": 0.0,
}

CASES: tuple[dict[str, Any], ...] = (
    {"name": "inactive_bypass", "attribute": 0,
     "position": (3.0, -2.0, 1.0), "oldTransformPosition": (1.0, 2.0, -1.0),
     "frameInterpolation": 0.25},
    {"name": "base_transform_interpolation", "attribute": 0,
     "position": (4.0, -2.0, 2.0), "oldTransformPosition": (0.0, 2.0, -2.0),
     "frameInterpolation": 0.25},
    {"name": "base_transform_rotation_slerp", "attribute": 0,
     "rotation": (0.0, 0.0, 0.7071067811865476, 0.7071067811865476),
     "oldTransformRotation": (0.7071067811865476, 0.0, 0.0, 0.7071067811865476),
     "frameInterpolation": 0.35},
    {"name": "base_transform_rotation_nlerp", "attribute": 0,
     "rotation": (0.0, 0.009999499987500624, 0.0, 0.9999499987499375),
     "oldTransformRotation": (0.0, 0.0, 0.0, 1.0),
     "frameInterpolation": 0.4},
    {"name": "base_transform_rotation_shortest_arc_sign_flip", "attribute": 0,
     "rotation": (0.0, 0.0, -0.7071067811865476, -0.7071067811865476),
     "oldTransformRotation": (0.7071067811865476, 0.0, 0.0, 0.7071067811865476),
     "frameInterpolation": 0.35},
    {"name": "inertia_translation_and_velocity", "depth": 0.5,
     "inertiaDepth": 1.0, "oldPos": (1.0, 0.0, 0.0),
     "velocity": (2.0, 4.0, 0.0), "velocityWeight": 0.5,
     "centerStepVector": (2.0, 0.0, 0.0), "centerInertiaVector": (0.0, 2.0, 0.0)},
    {"name": "inertia_position_and_velocity_rotation", "depth": 0.5,
     "inertiaDepth": 0.8, "oldPos": (2.0, -1.0, 3.0),
     "velocity": (1.5, -2.0, 0.75), "velocityWeight": 0.65,
     "centerOldWorldPosition": (0.5, -0.25, 1.0),
     "centerStepVector": (0.75, -0.5, 0.25),
     "centerInertiaVector": (-0.25, 0.5, -0.75),
     "centerStepRotation": (0.0, 0.0, 0.7071067811865476, 0.7071067811865476),
     "centerInertiaRotation": (0.0, 0.7071067811865476, 0.0, 0.7071067811865476)},
    {"name": "damping_and_gravity_prediction", "dt": 0.25,
     "simulationPower": (0.0, 0.0, 0.8, 0.0), "velocity": (4.0, 0.0, 0.0),
     "dampingCurve": (0.25,) * 16, "gravity": 2.0, "gravityRatio": 0.5,
     "scaleRatio": 2.0},
    {"name": "force_mode_1_depth_attenuated", "dt": 0.25, "depth": 0.5,
     "forceMode": 1, "impactForce": (6.0, -3.0, 0.0)},
    {"name": "force_mode_10_unattenuated", "dt": 0.25, "depth": 0.5,
     "forceMode": 10, "impactForce": (6.0, -3.0, 0.0)},
    {"name": "spring_distance_clamp", "dt": 1.0, "attribute": 3,
     "teamFlag": 0x2000, "velocity": (2.0, 0.0, 0.0),
     "springLimitDistance": 1.0},
    {"name": "spring_noise", "dt": 1.0, "attribute": 3, "teamFlag": 0x2000,
     "velocity": (0.5, 0.0, 0.0), "teamTime": 0.25,
     "springPower": 0.25, "springLimitDistance": 2.0, "springNoise": 0.5},
    {"name": "normal_cone_restriction", "dt": 1.0, "attribute": 3,
     "teamFlag": 0x2000, "velocity": (0.8, 0.8, 0.0),
     "springLimitDistance": 1.0, "springNormalLimitRatio": 0.25,
     "normalAxis": 0},
)


def _case(raw: dict[str, Any]) -> dict[str, Any]:
    return DEFAULTS | raw


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
    """Transcribe the bounded path of Simulation Start's float sine helper."""
    value = _f32(value)
    if not math.isfinite(value) or abs(value) >= _f32(125.0):
        raise burst.ContractError("Simulation Start quaternion sine left its pinned bounded path")
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


def _rotate(q: tuple[float, ...], v: tuple[float, ...]) -> tuple[float, float, float]:
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
    return tuple(_fadd(_fadd(v[i], _fmul(q[3], twice[i])), cross2[i]) for i in range(3))  # type: ignore[return-value]


def _f3(values: tuple[float, ...]) -> tuple[float, float, float]:
    return tuple(_f32(v) for v in values)  # type: ignore[return-value]


def _f4(values: tuple[float, ...]) -> tuple[float, float, float, float]:
    return tuple(_f32(v) for v in values)  # type: ignore[return-value]


def _f3_add(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float]:
    return tuple(_fadd(x, y) for x, y in zip(a, b))  # type: ignore[return-value]


def _f3_mul(a: tuple[float, ...], scalar: float) -> tuple[float, float, float]:
    return tuple(_fmul(x, scalar) for x in a)  # type: ignore[return-value]


def _sample16(curve: tuple[float, ...], depth: float) -> float:
    clamped = max(min(_f32(depth), _f32(1.0)), _f32(0.0))
    scaled = _fmul(clamped, 15.0)
    index = math.trunc(scaled)
    fraction = _fdiv(_fsub(depth, _fmul(float(index), _f32(0.06666667014360428))),
                     _f32(0.06666667014360428))
    i0 = max(0, min(15, index))
    i1 = max(0, min(15, index + 1))
    return _fadd(curve[i0], _fmul(fraction, _fsub(curve[i1], curve[i0])))


def _hex(values: tuple[float, ...], code: str) -> list[str]:
    return [struct.pack("<" + code, value).hex() for value in values]


def _asin_burst64(value: float) -> float:
    absolute = abs(value)
    if absolute < 0.5:
        y = value * value
        root = absolute
    else:
        y = (1.0 - absolute) * 0.5
        root = math.sqrt(y)
    a0, a1 = 0.031615876506539346, 0.012153605255773773
    a2, a3 = 0.019290454772679107, 0.017359569912236146
    b0, b1 = -0.015819182433299966, 0.013887151845016092
    b2, b3 = 0.006606077476277171, 0.022371761819320483
    c0, c1 = 0.07500000000378582, 0.16666666666664975
    d0, d1 = 0.030381959280381322, 0.044642856813771024
    y2 = y * y
    t0 = b2 + a2*y + y2*(b0 + a0*y)
    t1 = b3 + a3*y + y2*(b1 + a1*y)
    polynomial = c1 + c0*y + y2*(d1 + d0*y) + (y2*y2)*t1 + (y2*y2*y2*y2)*t0
    result = root + root*y*polynomial
    if absolute >= 0.5:
        result = math.pi / 2.0 - 2.0*result if value >= 0.0 else -math.pi / 2.0 + 2.0*result
    return math.copysign(result, value) if absolute < 0.5 else result


def source_port(raw: dict[str, Any], sin_helper: Callable[[float], float],
                cos_helper: Callable[[float], float]) -> dict[str, Any]:
    c = _case(raw)
    interpolation = _f32(c["frameInterpolation"])
    base = tuple(float(old + float(interpolation)*(now-old))
                 for old, now in zip(c["oldTransformPosition"], c["position"]))
    base_rotation = _normalize4(_slerp(_f4(c["oldTransformRotation"]),
                                       _f4(c["rotation"]), interpolation))
    if not (c["attribute"] & 2) and not (c["teamFlag"] & 0x2000):
        return {"basePos": base, "baseRot": base_rotation, "stepBasicPosition": base,
                "stepBasicRotation": base_rotation, "velocityPos": base, "nextPos": base}

    depth = _f32(c["depth"])
    k = _fmul(_fsub(1.0, _fmul(depth, depth)), c["inertiaDepth"])
    inertia_vector = _f3(c["centerInertiaVector"])
    step_vector = _f3(c["centerStepVector"])
    translation = tuple(_fadd(a, _fmul(k, _fsub(b, a)))
                        for a, b in zip(inertia_vector, step_vector))
    center = tuple(float(v) for v in c["centerOldWorldPosition"])
    relative = _f3(tuple(old-center_value for old, center_value in zip(c["oldPos"], center)))
    inertia_rotation = _slerp(_f4(c["centerInertiaRotation"]),
                              _f4(c["centerStepRotation"]), k)
    rotated_relative = _rotate(inertia_rotation, relative)
    inertia_position = tuple(center_value + float(r) + float(t)
                             for center_value, r, t in zip(center, rotated_relative, translation))
    inertia_velocity = _f3_mul(_rotate(inertia_rotation, _f3(c["velocity"])), c["velocityWeight"])

    curve = _sample16(tuple(_f32(v) for v in c["dampingCurve"]), depth)
    damping = max(min(_fsub(1.0, _fmul(curve, c["simulationPower"][2])), 1.0), 0.0)
    damped = _f3_mul(inertia_velocity, damping)
    gravity = _f3_mul(_f3(c["gravityDirection"]), _fmul(c["gravity"], c["gravityRatio"]))
    impact = (0.0, 0.0, 0.0)
    mode = int(c["forceMode"])
    if mode in (1, 2):
        denominator = _fadd(1.0, _fmul(5.0, _fmul(_fsub(1.0, depth), _fsub(1.0, depth))))
        impact = tuple(_fdiv(v, denominator) for v in _f3(c["impactForce"]))
    elif mode in (10, 11):
        impact = _f3(c["impactForce"])
    acceleration = _f3_add(gravity, impact)
    dt = _f32(c["dt"])
    scaled_acceleration = _f3_mul(acceleration, _fmul(dt, c["scaleRatio"]))
    new_velocity = _f3_add(damped, scaled_acceleration)
    displacement = _f3_mul(new_velocity, dt)
    predicted = tuple(p + float(d) for p, d in zip(inertia_position, displacement))
    final = predicted

    if (c["teamFlag"] & 0x2000) and (c["attribute"] & 1):
        limit = float(_fmul(c["scaleRatio"], c["springLimitDistance"]))
        delta = tuple(p-b for p, b in zip(predicted, base))
        length = math.sqrt(sum(v*v for v in delta))
        constrained = tuple(v*(limit/length) for v in delta) if length > limit else delta
        ratio = _f32(c["springNormalLimitRatio"])
        if ratio < _f32(1.0):
            axes = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
                    (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
            normal = axes[int(c["normalAxis"])]
            parallel = sum(v*n for v, n in zip(constrained, normal))
            tangent = tuple(v-parallel*n for v, n in zip(constrained, normal))
            tangent_length = math.sqrt(sum(v*v for v in tangent))
            angle = _asin_burst64(tangent_length/limit)
            threshold = limit * float(ratio) * cos_helper(angle)
            if abs(parallel) > threshold:
                excess = math.copysign(abs(parallel)-threshold, parallel)
                constrained = tuple(v-excess*n for v, n in zip(constrained, normal))
        phase = sum(predicted) + float(_f32(2.451200008392334))*float(
            _fadd(c["teamTime"], _fmul(49.61980056762695, 0.0)))
        spring_power = float(_f32(c["springPower"]))
        spring_noise = float(_fmul(c["springNoise"], 0.6000000238418579))
        spring_factor = max(0.0, spring_power + spring_power*spring_noise*sin_helper(phase))
        final = tuple(b + v*(1.0-spring_factor) for b, v in zip(base, constrained))

    return {"basePos": base, "baseRot": base_rotation, "stepBasicPosition": base,
            "stepBasicRotation": base_rotation, "velocityPos": inertia_position, "nextPos": final}


def _run_native(module: Any, raw: dict[str, Any]) -> dict[str, Any]:
    c = _case(raw)
    signature = ctypes.CFUNCTYPE(None, *([ctypes.c_float] * 5),
                                *([ctypes.c_void_p] * 23), ctypes.c_int)
    target = module._handle + CORE_RVA
    # Burst passes its fifth scalar in xmm4. A public Win64 FFI places argument
    # five at [rsp+0x28], so use a tiny tail-call shim to restore Burst's
    # internal convention without disturbing any stack argument.
    code = b"\xf3\x0f\x10\x64\x24\x28\x48\xb8" + struct.pack("<Q", target) + b"\xff\xe0"
    kernel32 = ctypes.windll.kernel32
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    address = kernel32.VirtualAlloc(None, len(code), 0x3000, 0x40)
    if not address:
        raise burst.ContractError("VirtualAlloc failed for Simulation Start ABI shim")
    ctypes.memmove(address, code, len(code))
    function = signature(address)
    sizes = (4, 1, 4, 24, 16, 4, 464, 808, 696, 152, 212, 2,
             24, 24, 24, 12, 16, 24, 16, 24, 4, 24, 16)
    buffers = [ctypes.create_string_buffer(size) for size in sizes]
    (step, attributes, depth, positions, rotations, roots, team, parameters, center,
     team_wind, wind, team_ids, old_pos, next_pos, base_pos, velocity, base_rot,
     old_transform_pos, old_transform_rot, velocity_pos, friction, step_pos, step_rot) = buffers
    struct.pack_into("<i", step, 0, 0); struct.pack_into("<B", attributes, 0, c["attribute"])
    struct.pack_into("<f", depth, 0, c["depth"]); struct.pack_into("<3d", positions, 0, *c["position"])
    struct.pack_into("<4f", rotations, 0, *c["rotation"]); struct.pack_into("<i", roots, 0, 0)
    struct.pack_into("<H", team, 0, c["teamFlag"]); struct.pack_into("<f", team, 0x14, c["teamTime"])
    struct.pack_into("<f", team, 0x3C, c["frameInterpolation"]); struct.pack_into("<f", team, 0x40, c["gravityRatio"])
    struct.pack_into("<f", team, 0x60, c["scaleRatio"]); struct.pack_into("<f", team, 0xFC, c["velocityWeight"])
    struct.pack_into("<i", team, 0x108, c["forceMode"]); struct.pack_into("<3f", team, 0x10C, *c["impactForce"])
    struct.pack_into("<i", team, 0x124, 0); struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<f", parameters, 0, c["gravity"]); struct.pack_into("<3f", parameters, 4, *c["gravityDirection"])
    struct.pack_into("<16f", parameters, 0x1C, *c["dampingCurve"])
    struct.pack_into("<i", parameters, 0x9C, c["normalAxis"]); struct.pack_into("<f", parameters, 0xD4, c["inertiaDepth"])
    struct.pack_into("<4f", parameters, 0x318, c["springPower"], c["springLimitDistance"],
                     c["springNormalLimitRatio"], c["springNoise"])
    struct.pack_into("<3d", center, 0x198, *c["centerOldWorldPosition"])
    struct.pack_into("<3f", center, 0x1C8, *c["centerStepVector"]); struct.pack_into("<4f", center, 0x1D4, *c["centerStepRotation"])
    struct.pack_into("<3f", center, 0x1E4, *c["centerInertiaVector"]); struct.pack_into("<4f", center, 0x1F0, *c["centerInertiaRotation"])
    struct.pack_into("<h", team_ids, 0, 0); struct.pack_into("<3d", old_pos, 0, *c["oldPos"])
    struct.pack_into("<3f", velocity, 0, *c["velocity"]); struct.pack_into("<3d", old_transform_pos, 0, *c["oldTransformPosition"])
    struct.pack_into("<4f", old_transform_rot, 0, *c["oldTransformRotation"]); struct.pack_into("<f", friction, 0, c["friction"])
    scalars = [ctypes.c_float(v) for v in (*c["simulationPower"], c["dt"])]
    # The range wrapper lowers the managed container order to this physical core
    # order: velocity is moved ahead of next/base position.
    physical = buffers[:13] + [velocity, next_pos, base_pos, base_rot,
                               old_transform_pos, old_transform_rot, velocity_pos,
                               friction, step_pos, step_rot]
    function(*scalars, *(ctypes.addressof(b) for b in physical), ctypes.c_int(0))
    return {"basePos": struct.unpack_from("<3d", base_pos), "baseRot": struct.unpack_from("<4f", base_rot),
            "stepBasicPosition": struct.unpack_from("<3d", step_pos),
            "stepBasicRotation": struct.unpack_from("<4f", step_rot),
            "velocityPos": struct.unpack_from("<3d", velocity_pos), "nextPos": struct.unpack_from("<3d", next_pos)}


def _assert_exact(native: dict[str, Any], source: dict[str, Any], name: str) -> None:
    for field in ("basePos", "stepBasicPosition", "velocityPos", "nextPos"):
        if _hex(native[field], "d") != _hex(source[field], "d"):
            raise burst.ContractError(f"Simulation Start differs: {name}.{field}: native={_hex(native[field], 'd')} source={_hex(source[field], 'd')}")
    for field in ("baseRot", "stepBasicRotation"):
        if _hex(native[field], "f") != _hex(source[field], "f"):
            raise burst.ContractError(f"Simulation Start differs: {name}.{field}: native={_hex(native[field], 'f')} source={_hex(source[field], 'f')}")


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    burst._exact_rva_span(pe, SIN_RVA, SIN_BYTES, SIN_SHA256)
    burst._exact_rva_span(pe, COS_RVA, COS_BYTES, COS_SHA256)
    burst._exact_rva_span(pe, SLERP_SIN_RVA, SLERP_SIN_BYTES, SLERP_SIN_SHA256)
    module = ctypes.WinDLL(str(dll))
    sin_helper = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)(module._handle + SIN_RVA)
    cos_helper = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)(module._handle + COS_RVA)
    vectors = []
    for raw in CASES:
        native = _run_native(module, raw)
        source = source_port(raw, sin_helper, cos_helper)
        _assert_exact(native, source, raw["name"])
        output: dict[str, Any] = {}
        for field, values in native.items():
            code = "f" if "Rot" in field else "d"
            output[field] = list(values)
            output[field + ("Binary32Le" if code == "f" else "Binary64Le")] = _hex(values, code)
        inputs = {k: list(v) if isinstance(v, tuple) else v for k, v in _case(raw).items() if k != "name"}
        vectors.append({"name": raw["name"], "input": inputs, "output": output})
    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-start-golden-vectors.v1",
        "status": "native_avx2_controlled_domain_exact",
        "nativeGate": gate,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES, "sha256": CORE_SHA256},
        "abi": {"leadingValues": ["simulationPower.x float32", "simulationPower.y float32",
                "simulationPower.z float32", "simulationPower.w float32", "simulationDeltaTime float32"],
                "pointerOrder": ["stepParticleIndexArray", "attributes", "depthArray", "positions", "rotations",
                "vertexRootIndices", "teamDataArray", "parameterArray", "centerDataArray", "teamWindArray",
                "windDataArray", "teamIdArray", "oldPosArray", "velocityArray", "nextPosArray", "basePosArray",
                "baseRotArray", "oldPositionArray", "oldRotationArray", "velocityPosArray", "frictionArray",
                "stepBasicPositionArray", "stepBasicRotationArray"], "trailingValue": "rangeIndex int32",
                "internalRegisterConvention": "simulationDeltaTime is live in xmm4; all 23 pointers are stack arguments",
                "ffiShim": "movss xmm4,[rsp+0x28]; mov rax,core; jmp rax"},
        "directHelpers": {
            "quaternionSlerpSin": {"rva": f"0x{SLERP_SIN_RVA:x}", "bytes": SLERP_SIN_BYTES,
                                    "sha256": SLERP_SIN_SHA256,
                                    "abi": "float32 -> float32", "usedBySourceTranscription": False,
                                    "sourceBoundary": "standalone bounded-path transcription"},
            "springNoiseSin": {"rva": f"0x{SIN_RVA:x}", "bytes": SIN_BYTES, "sha256": SIN_SHA256,
                               "abi": "double -> double", "usedBySourceTranscription": True},
            "normalConeCos": {"rva": f"0x{COS_RVA:x}", "bytes": COS_BYTES, "sha256": COS_SHA256,
                              "abi": "double -> double", "usedBySourceTranscription": True}},
        "windIsolation": {"teamWindDataZeroed": True, "movingWindZeroed": True,
                          "result": "zero; inlined wind blend/noise helpers not entered"},
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": vectors,
        "boundary": {"nativeCoreExecuted": True, "sourceTranscriptionMatched": True,
                     "covered": ["inactive bypass", "base transform position interpolation",
                                 "base transform shortest-arc quaternion nlerp and slerp interpolation",
                                 "center step/inertia quaternion interpolation and rotated position/velocity", "inertia",
                                 "damping and gravity prediction", "force mode 1 attenuation",
                                 "force mode 10 preservation", "spring distance clamp", "spring noise",
                                 "normal cone restriction"],
                     "nonStandaloneHelperBoundary": ["spring noise uses the directly pinned scalar sine helper",
                                                     "normal-cone threshold uses the directly pinned scalar cosine helper"],
                     "notCovered": ["nonzero wind"],
                     "controlledDomain": "zero wind; representative normalized base and center quaternions cover all base/inertia position and rotation equations; valid quaternion slerp arguments remain inside the standalone float-sine transcription's bounded path",
                     "completeKernelGoldenCoverage": False, "unityPortExecuted": True,
                     "unityVerifier": "EndfieldGraphShaderLabEditor.EndfieldSecondaryDynamicsKernelGoldenVerifier.VerifyMenu",
                     "unityPortDomain": "StartSimulationParticleZeroWind; all 13 controlled vectors bit-exact"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_contract(), indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit("Simulation Start golden vectors differ from regenerated output")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
