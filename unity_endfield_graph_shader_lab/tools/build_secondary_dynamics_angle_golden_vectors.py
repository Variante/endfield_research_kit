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


CASES: tuple[dict[str, Any], ...] = (
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
    return {
        "attributes": list(case.get("attributes", [0, 2])),
        "depths": [_f32(v) for v in case.get("depths", [0.0, 0.37])],
        "friction": [_f32(v) for v in case.get("friction", [0.0, 0.0])],
        "velocity": [tuple(map(float, v)) for v in case.get("velocity", [(0, 0, 0), (0, 0, 0)])],
        "basic": [tuple(map(float, v)) for v in case.get("basic", [(0, 0, 0), (1, 0, 0)])],
        "basicRotation": [(0.0, 0.0, 0.0, 1.0)] * 2,
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
    next_pos = [tuple(map(float, row)) for row in case["next"]]
    velocity = list(v["velocity"])
    rotations = list(v["basicRotation"])
    lengths = [0.0, 0.0]
    local_pos = [(0.0, 0.0, 0.0)] * 2
    local_rot = [(0.0, 0.0, 0.0, 0.0)] * 2
    restoration_vectors = [(0.0, 0.0, 0.0)] * 2
    rotations[0] = v["basicRotation"][0]
    rotations[1] = v["basicRotation"][1]
    if v["limit"]:
        lengths[1] = _f32(_length(_d3_sub(next_pos[0], next_pos[1])))
        basic_direction = _normalize(_d3_sub(v["basic"][1], v["basic"][0]))
        local_pos[1] = tuple(_f32(x) for x in _qrotate(_qinverse(v["basicRotation"][0]), basic_direction))
        local_rot[1] = _qmul(_qinverse(v["basicRotation"][0]), v["basicRotation"][1])
    if v["restoration"]:
        restoration_vectors[1] = tuple(_f32(x) for x in _d3_sub(v["basic"][1], v["basic"][0]))

    for sweep in range(3):
        t = _fadd(_fmul(_fmul(float(sweep), 0.5), 0.4), 0.1)
        one_minus_t = _fsub(1.0, t)
        p, q = next_pos[1], next_pos[0]
        child_mobility = float(_mobility(v["friction"][1]))
        parent_mobility = float(_mobility(v["friction"][0]))
        if v["limit"]:
            u = _qrotate(rotations[0], tuple(float(x) for x in local_pos[1]))
            d = _d3_sub(p, q)
            current_length = _length(d)
            blend_length = current_length + 0.5 * (float(lengths[1]) - current_length)
            direction = _d3_mul(d, 1.0 / current_length)
            vv = _d3_mul(direction, blend_length)
            limit_radians = _fmul(_curve(v["depths"][1], v["limitCurve"]),
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
            next_pos[1] = _d3_add(p, child_corr)
            velocity[1] = _d3_add(velocity[1], _d3_mul(child_corr, float(_f32(0.8999999761581421))))
            if v["attributes"][0] & 2:
                parent_corr = _d3_mul(_d3_sub(vv, vlimit),
                                      parent_mobility * float(_f32(0.4000000059604645)))
                next_pos[0] = _d3_add(q, parent_corr)
                velocity[0] = _d3_add(velocity[0], _d3_mul(parent_corr, float(_f32(0.8999999761581421))))
            dnew = _d3_sub(next_pos[1], next_pos[0])
            qbase = _qmul(rotations[0], local_rot[1])
            qdelta = _rotation_between(u, dnew)
            rotations[1] = _qmul(qdelta, qbase)

        if v["restoration"]:
            p, q = next_pos[1], next_pos[0]
            d = _d3_sub(p, q)
            rest = tuple(float(x) for x in restoration_vectors[1])
            dn, rn = _normalize(d), _normalize(rest)
            angle = _acos_burst(min(max(_dot(dn, rn), -1.0), 1.0))
            strength = _fclamp(_curve(v["depths"][1], v["restorationCurve"]), 0.0, 1.0)
            strength = _fclamp(_fmul(strength, v["simulationPowerW"]), 0.0, 1.0)
            gravity_mix = _fadd(_fsub(1.0, v["restorationGravityFalloff"]),
                                _fmul(v["gravityDot"], v["restorationGravityFalloff"]))
            strength = _fmul(strength, gravity_mix)
            drot = _qrotate(_rotation_between(dn, rn, angle * float(strength)), d)
            weighted_current = _d3_add(q, _d3_mul(d, float(t)))
            child_target = _d3_add(weighted_current, _d3_mul(drot, float(one_minus_t)))
            child_corr = _d3_mul(_d3_sub(child_target, p), parent_mobility)
            next_pos[1] = _d3_add(p, child_corr)
            velocity[1] = _d3_add(velocity[1], _d3_mul(child_corr, float(v["restorationVelocityAttenuation"])))
            if v["attributes"][0] & 2:
                # The AVX2 body deliberately forms (Q+t*d)-t*dRot-Q before
                # applying mobility; preserving those cancellation points is
                # observable in the binary64 result.
                parent_delta = _d3_sub(
                    _d3_sub(weighted_current, _d3_mul(drot, float(t))), q)
                parent_corr = _d3_mul(parent_delta, child_mobility)
                next_pos[0] = _d3_add(q, parent_corr)
                velocity[0] = _d3_add(velocity[0], _d3_mul(parent_corr, float(v["restorationVelocityAttenuation"])))
    return {"next": next_pos, "velocity": velocity, "rotation": rotations,
            "length": lengths, "localPos": local_pos, "localRot": local_rot,
            "restorationVector": restoration_vectors}


def _make_native_function(dll: Path) -> tuple[Any, Any]:
    module = ctypes.WinDLL(str(dll))
    signature = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 20), ctypes.c_int32)
    return module, signature(module._handle + CORE_RVA)


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
    sizes = [16, 4, 464, 808, 2, 8, 8, 2, 2, 4, 48, 48, 8, 48, 32, 8, 24, 32, 32, 24]
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
    struct.pack_into("<2B", attrs, 0, *v["attributes"])
    struct.pack_into("<2f", depths, 0, *v["depths"])
    struct.pack_into("<2i", parents, 0, -1, 0)
    struct.pack_into("<H", starts, 0, 0)
    struct.pack_into("<H", counts, 0, 2)
    struct.pack_into("<2H", data, 0, 0, 1)
    for index in range(2):
        struct.pack_into("<3d", next_pos, index * 24, *case["next"][index])
        struct.pack_into("<3d", velocity, index * 24, *v["velocity"][index])
        struct.pack_into("<f", friction, index * 4, v["friction"][index])
        struct.pack_into("<3d", basic_pos, index * 24, *v["basic"][index])
        struct.pack_into("<4f", basic_rot, index * 16, *v["basicRotation"][index])
    function(*(ctypes.addressof(buffer) for buffer in buffers), 0)
    return {
        "next": [struct.unpack_from("<3d", next_pos, i * 24) for i in range(2)],
        "velocity": [struct.unpack_from("<3d", velocity, i * 24) for i in range(2)],
        "rotation": [struct.unpack_from("<4f", rotations, i * 16) for i in range(2)],
        "length": list(struct.unpack_from("<2f", lengths, 0)),
        "localPos": [struct.unpack_from("<3f", local_pos, i * 12) for i in range(2)],
        "localRot": [struct.unpack_from("<4f", local_rot, i * 16) for i in range(2)],
        "restorationVector": [struct.unpack_from("<3f", restoration, i * 12) for i in range(2)],
    }


def _bits(value: Any, fmt: str) -> Any:
    if isinstance(value, (list, tuple)):
        return [_bits(item, fmt) for item in value]
    return struct.pack(fmt, value).hex()


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
    burst._exact_rva_span(pe, SINCOS_RVA, SINCOS_BYTES, SINCOS_SHA256)
    _SINCOS, thunk_address = _make_sincos(module)
    vectors = []
    for case in CASES:
        native = _run_native(function, case)
        source = source_port(case)
        _assert_exact(case["name"], native, source)
        vectors.append({"name": case["name"], "input": case, "output": native,
                        "outputBits": {key: _bits(value, "<d" if key in {"next", "velocity"} else "<f")
                                       for key, value in native.items()}})
    del thunk_address
    return {
        "schema": "endfield.charinfo.secondary-dynamics-angle-golden-vectors.v1",
        "status": "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
        "nativeGate": gate, "rangeWrapperAbi": wrapper,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES,
                 "sha256": CORE_SHA256, "argument21": "int32 rangeIndex value"},
        "transcendentalHelper": {"role": "source transcription exact float sincos",
                                  "rva": f"0x{SINCOS_RVA:x}", "bytes": SINCOS_BYTES,
                                  "sha256": SINCOS_SHA256},
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": vectors,
        "boundary": {"nativeCoreExecuted": True, "sourceTranscriptionAllWrittenBitsMatched": True,
                     "rangeWrapperArgument21Confirmed": True,
                     "caseCoverage": [case["name"] for case in CASES],
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
