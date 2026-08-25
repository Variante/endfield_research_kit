#!/usr/bin/env python3
"""Execute all closed Simulation End branches in the pinned AVX2 core."""

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
OUTPUT = LAB_ROOT / ("Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
                     "secondary_dynamics_simulation_end_golden_vectors.json")
CORE_RVA = 0x24FA60
CORE_BYTES = 1745
CORE_SHA256 = "f623b3ca9c367210ca74998645797c72cefa6d393d708f8665788b85aba41780"
DEFAULTS = {
    "active": True, "dt": 0.5, "scaleRatio": 1.0, "velocityWeight": 1.0,
    "particleSpeedLimit": -1.0, "centrifugalAcceleration": 0.0,
    "dynamicFriction": 0.0, "staticFrictionParameter": 0.0, "depth": 0.25,
    "nextPos": (2.0, 3.0, 4.0), "oldPos": (1.0, 1.0, 1.0),
    "velocityPos": (1.0, 1.0, 1.0), "friction": 0.0, "staticFriction": 0.0,
    "collisionNormal": (0.0, 0.0, 0.0), "centerPosition": (0.0, 0.0, 0.0),
    "centerAngularVelocity": 0.0, "centerRotationAxis": (0.0, 1.0, 0.0),
}
CASES = (
    {"name": "inactive_bypass", "active": False},
    {"name": "active_unlimited"},
    {"name": "active_speed_limit", "particleSpeedLimit": 2.0},
    {"name": "static_friction_accumulation", "nextPos": (0.01, 0.0, 0.0),
     "oldPos": (0.0, 0.0, 0.0), "velocityPos": (-0.5, 0.0, 0.0),
     "friction": 0.75, "staticFriction": 0.25, "staticFrictionParameter": 0.5,
     "collisionNormal": (0.0, 1.0, 0.0)},
    {"name": "static_friction_release", "nextPos": (0.075, 0.0, 0.0),
     "oldPos": (0.0, 0.0, 0.0), "velocityPos": (-0.5, 0.0, 0.0),
     "friction": 0.75, "staticFriction": 0.7, "staticFrictionParameter": 0.1,
     "collisionNormal": (0.0, 1.0, 0.0)},
    {"name": "static_friction_no_contact_decay", "friction": 0.75,
     "staticFriction": 0.4, "staticFrictionParameter": 0.5,
     "collisionNormal": (0.0, 0.0, 0.0)},
    {"name": "dynamic_friction_attenuation", "nextPos": (1.0, 0.0, 0.0),
     "oldPos": (0.0, 0.0, 0.0), "velocityPos": (0.0, 0.0, 0.0),
     "friction": 0.5, "dynamicFriction": 0.8, "collisionNormal": (0.0, 1.0, 0.0)},
    {"name": "center_centrifugal_response", "nextPos": (2.0, 0.0, 0.0),
     "oldPos": (1.0, 0.0, 0.0), "velocityPos": (2.0, 0.0, 1.0),
     "centrifugalAcceleration": 0.5, "centerAngularVelocity": 2.0,
     "centerRotationAxis": (0.0, 1.0, 0.0)},
)


def _case(values: dict[str, Any]) -> dict[str, Any]:
    return DEFAULTS | values


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _fmul(a: float, b: float) -> float:
    return _f32(_f32(a) * _f32(b))


def _fadd(a: float, b: float) -> float:
    return _f32(_f32(a) + _f32(b))


def _dot64(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return (a[0] * b[0] + a[1] * b[1]) + a[2] * b[2]


def _dot32(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return _fadd(_fadd(_fmul(a[0], b[0]), _fmul(a[1], b[1])), _fmul(a[2], b[2]))


def _normalize32(value: tuple[float, ...]) -> tuple[float, ...]:
    value = tuple(_f32(v) for v in value)
    reciprocal = _f32(1.0 / _f32(math.sqrt(_dot32(value, value))))
    return tuple(_fmul(v, reciprocal) for v in value)


def _hex(values: tuple[float, ...], code: str) -> list[str]:
    return [struct.pack("<" + code, value).hex() for value in values]


def source_port(raw: dict[str, Any]) -> dict[str, Any]:
    c = _case(raw)
    dt = float(_f32(c["dt"]))
    scale = _f32(c["scaleRatio"])
    weight = _f32(c["velocityWeight"])
    friction = _f32(c["friction"])
    sf = float(_f32(c["staticFriction"]))
    normal32 = tuple(_f32(v) for v in c["collisionNormal"])
    normal = tuple(float(v) for v in normal32)
    pos = tuple(float(v) for v in c["nextPos"])
    old = tuple(float(v) for v in c["oldPos"])
    velocity_pos = tuple(float(v) for v in c["velocityPos"])
    corrected = pos

    if not c["active"]:
        velocity = (0.0, 0.0, 0.0)
    else:
        corrected_velocity_pos = velocity_pos
        normal_sq = _dot32(normal32, normal32)
        threshold = _fmul(scale, c["staticFrictionParameter"])
        if normal_sq > _f32(1e-8) and friction > 0.0 and threshold > 0.0:
            delta = tuple(p - o for p, o in zip(pos, old))
            normal_distance = _dot64(normal, delta)
            tangent = tuple(d - n * normal_distance for d, n in zip(delta, normal))
            tangent_speed = math.sqrt(_dot64(tangent, tangent)) / dt
            if float(threshold) > tangent_speed:
                sf += float(_f32(0.04))
            else:
                sf -= max(
                    (tangent_speed - float(threshold)) / float(_f32(0.2)),
                    float(_f32(0.05)),
                )
            sf = max(min(sf, 1.0), 0.0)
            correction = tuple(v * sf for v in tangent)
            corrected = tuple(p - v for p, v in zip(pos, correction))
            corrected_velocity_pos = tuple(p - v for p, v in zip(velocity_pos, correction))
        else:
            sf = max(min(sf - float(_f32(0.05)), 1.0), 0.0)

        velocity0 = tuple((p - v) / dt for p, v in zip(corrected, corrected_velocity_pos))
        speed0_sq = _dot64(velocity0, velocity0)
        direction0 = _normalize32(velocity0) if speed0_sq > 1e-8 else (0.0, 0.0, 0.0)
        velocity1 = velocity0
        dynamic = _f32(c["dynamicFriction"])
        if friction > _f32(1e-8) and normal_sq > _f32(1e-8) and dynamic > 0.0 and speed0_sq >= 1e-8:
            hemisphere = _fadd(_fmul(_dot32(normal32, direction0), 0.5), 0.5)
            directional_loss = _f32(1.0 - _fmul(hemisphere, hemisphere))
            strength = max(min(_fmul(dynamic, friction), 1.0), 0.0)
            attenuation = _fmul(strength, directional_loss)
            velocity1 = tuple(v - v * float(attenuation) for v in velocity0)

        velocity2 = velocity1
        limit = _f32(c["particleSpeedLimit"])
        if limit >= 0.0:
            scaled_limit = _fmul(limit, scale)
            speed = math.sqrt(_dot64(velocity1, velocity1))
            if not (speed <= float(scaled_limit) or speed <= 9.999999717180685e-10):
                velocity2 = tuple(v * (float(scaled_limit) / speed) for v in velocity1)

        velocity_final = velocity2
        angular = _f32(c["centerAngularVelocity"])
        centrifugal = _f32(c["centrifugalAcceleration"])
        if angular > _f32(1e-8) and centrifugal > _f32(1e-8) and speed0_sq >= 1e-8:
            center = tuple(float(v) for v in c["centerPosition"])
            radial_input = tuple(float(_f32(p - center_value)) for p, center_value in zip(corrected, center))
            axis = tuple(float(_f32(v)) for v in c["centerRotationAxis"])
            axial = _dot64(axis, radial_input)
            radial = tuple(v - a * axial for v, a in zip(radial_input, axis))
            radial_length = math.sqrt(_dot64(radial, radial))
            if radial_length > 1e-8:
                radial_direction = tuple(v / radial_length for v in radial)
                cross = (axis[1]*radial_direction[2]-axis[2]*radial_direction[1],
                         axis[2]*radial_direction[0]-axis[0]*radial_direction[2],
                         axis[0]*radial_direction[1]-axis[1]*radial_direction[0])
                cross_length = math.sqrt(_dot64(cross, cross))
                tangent = tuple(v / cross_length for v in cross)
                alignment = max(min(_dot64(tangent, tuple(float(v) for v in direction0)), 1.0), 0.0)
                depth_factor = _fadd(_f32(1.0 - _f32(c["depth"])), 1.0)
                angular_term = _fmul(_fmul(angular, depth_factor), angular)
                magnitude = radial_length * float(angular_term) * alignment
                magnitude *= float(centrifugal) * 0.019999999552965164
                velocity_final = tuple(v + r*magnitude for v, r in zip(velocity2, radial_direction))

        velocity = tuple(_f32(v * float(weight)) for v in velocity_final)
        friction = _fmul(friction, 0.6000000238418579)

    real_velocity = tuple(_f32((p - o) / dt) for p, o in zip(corrected, old))
    return {"velocity": velocity, "realVelocity": real_velocity, "oldPos": corrected,
            "friction": friction, "staticFriction": _f32(sf)}


def _run_native(dll: Path, raw: dict[str, Any]) -> dict[str, Any]:
    c = _case(raw)
    module = ctypes.WinDLL(str(dll))
    function = ctypes.CFUNCTYPE(None, ctypes.c_float, *([ctypes.c_void_p] * 15), ctypes.c_int)(
        module._handle + CORE_RVA)
    sizes = [4, 464, 808, 696, 1, 4, 2, 24, 24, 12, 12, 24, 4, 4, 12]
    buffers = [ctypes.create_string_buffer(size) for size in sizes]
    (step, team, parameters, center, attributes, depth, team_ids, next_pos, old_pos,
     velocity, real_velocity, velocity_pos, friction, static_friction, normal) = buffers
    struct.pack_into("<i", step, 0, 0)
    struct.pack_into("<i", team, 0x124, 0); struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<f", team, 0x60, c["scaleRatio"]); struct.pack_into("<f", team, 0xFC, c["velocityWeight"])
    struct.pack_into("<f", parameters, 0xD8, c["centrifugalAcceleration"])
    struct.pack_into("<f", parameters, 0xDC, c["particleSpeedLimit"])
    struct.pack_into("<f", parameters, 0x268, c["dynamicFriction"])
    struct.pack_into("<f", parameters, 0x26C, c["staticFrictionParameter"])
    struct.pack_into("<3d", center, 0x170, *c["centerPosition"])
    struct.pack_into("<f", center, 0x210, c["centerAngularVelocity"])
    struct.pack_into("<3f", center, 0x214, *c["centerRotationAxis"])
    struct.pack_into("<B", attributes, 0, 2 if c["active"] else 0)
    struct.pack_into("<f", depth, 0, c["depth"]); struct.pack_into("<h", team_ids, 0, 0)
    struct.pack_into("<3d", next_pos, 0, *c["nextPos"]); struct.pack_into("<3d", old_pos, 0, *c["oldPos"])
    struct.pack_into("<3d", velocity_pos, 0, *c["velocityPos"])
    struct.pack_into("<f", friction, 0, c["friction"]); struct.pack_into("<f", static_friction, 0, c["staticFriction"])
    struct.pack_into("<3f", normal, 0, *c["collisionNormal"])
    function(ctypes.c_float(c["dt"]), *(ctypes.addressof(b) for b in buffers), ctypes.c_int(0))
    return {"velocity": struct.unpack_from("<3f", velocity),
            "realVelocity": struct.unpack_from("<3f", real_velocity),
            "oldPos": struct.unpack_from("<3d", old_pos),
            "friction": struct.unpack_from("<f", friction)[0],
            "staticFriction": struct.unpack_from("<f", static_friction)[0]}


def _assert_exact(native: dict[str, Any], port: dict[str, Any], name: str) -> None:
    for field, code in (("velocity", "f"), ("realVelocity", "f"), ("oldPos", "d"),
                        ("friction", "f"), ("staticFriction", "f")):
        nv = native[field] if isinstance(native[field], tuple) else (native[field],)
        pv = port[field] if isinstance(port[field], tuple) else (port[field],)
        if _hex(nv, code) != _hex(pv, code):
            raise burst.ContractError(f"source Simulation End transcription differs: {name}.{field}: "
                                      f"native={_hex(nv, code)} source={_hex(pv, code)}")


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    burst._exact_rva_span(burst._pe_exports(dll), CORE_RVA, CORE_BYTES, CORE_SHA256)
    vectors = []
    for raw in CASES:
        c = _case(raw); native = _run_native(dll, raw); port = source_port(raw)
        _assert_exact(native, port, raw["name"])
        vectors.append({"name": raw["name"],
                        "input": {k: list(v) if isinstance(v, tuple) else v for k, v in c.items() if k != "name"},
                        "output": {"velocity": list(native["velocity"]), "velocityBinary32Le": _hex(native["velocity"], "f"),
                                   "realVelocity": list(native["realVelocity"]), "realVelocityBinary32Le": _hex(native["realVelocity"], "f"),
                                   "oldPos": list(native["oldPos"]), "oldPosBinary64Le": _hex(native["oldPos"], "d"),
                                   "friction": native["friction"], "frictionBinary32Le": _hex((native["friction"],), "f")[0],
                                   "staticFriction": native["staticFriction"],
                                   "staticFrictionBinary32Le": _hex((native["staticFriction"],), "f")[0]}})
    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-end-golden-vectors.v1",
        "status": "native_avx2_all_closed_branches_exact", "nativeGate": gate,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES, "sha256": CORE_SHA256},
        "abi": {"leadingValue": "dt float32", "pointerOrder": ["stepParticleIndexArray", "teamDataArray",
                "parameterArray", "centerDataArray", "attributes", "vertexDepths", "teamIdArray", "nextPosArray",
                "oldPosArray", "velocityArray", "realVelocityArray", "velocityPosArray", "frictionArray",
                "staticFrictionArray", "collisionNormalArray"], "trailingValue": "rangeIndex int32"},
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "vectors": vectors,
        "boundary": {"nativeCoreExecuted": True, "sourceTranscriptionMatched": True,
                     "covered": ["inactive bypass", "active base velocity", "particle speed limit",
                                 "static-friction accumulation", "static-friction release",
                                 "static-friction no-contact decay", "dynamic-friction attenuation",
                                 "center centrifugal response"],
                     "notCovered": [], "completeKernelGoldenCoverage": True, "unityPortExecuted": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT); parser.add_argument("--check", action="store_true")
    args = parser.parse_args(); payload = json.dumps(build_contract(), indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit("Simulation End golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n"); print(args.output); return 0


if __name__ == "__main__":
    raise SystemExit(main())
