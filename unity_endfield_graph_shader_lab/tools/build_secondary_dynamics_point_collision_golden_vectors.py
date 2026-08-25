#!/usr/bin/env python3
"""Execute the pinned Burst Point-capsule core and publish golden vectors."""

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
    "secondary_dynamics_point_collision_golden_vectors.json"
)
EXPORT_NAME = "6a5470d135bde394bed7e7182cdf7c65"
EXPORT_RVA = 0x356D80
EXPORT_BYTES = 159
EXPORT_SHA256 = "75c85b4054080534f00540c55ad11def04b67afb2bf35d432e251f14e82d0a73"
CORE_RVA = 0x2FCDA0
CORE_BYTES = 3660
CORE_SHA256 = "bead77afdd711f8049af5b48df8eed513a7deeb74285be97dcd8cdf4c9a75b1d"


CASES: tuple[dict[str, Any], ...] = (
    {
        "name": "static_capsule_penetration",
        "particle": (0.2, 0.0, 0.0),
        "oldEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "newEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "radii": (0.3, 0.3),
    },
    {
        "name": "no_contact_normal_zero",
        "particle": (0.6, 0.0, 0.0),
        "oldEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "newEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "radii": (0.3, 0.3),
    },
    {
        "name": "translated_collider_transport",
        "particle": (0.2, 0.0, 0.0),
        "oldEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "newEndpoints": ((0.1, -1.0, 0.0), (0.1, 1.0, 0.0)),
        "radii": (0.3, 0.3),
    },
    {
        "name": "rotated_collider_transport",
        "particle": (0.2, 0.0, 0.0),
        "oldEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "newEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "radii": (0.3, 0.3),
        "rotation": (0.0, 0.0, 0.7071067690849304, 0.7071067690849304),
    },
    {
        "name": "tapered_capsule_radius",
        "particle": (0.2, 0.5, 0.0),
        "oldEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "newEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "radii": (0.2, 0.4),
    },
    {
        "name": "friction_near_contact",
        "particle": (0.45, 0.0, 0.0),
        "oldEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "newEndpoints": ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)),
        "radii": (0.3, 0.3),
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


def _fsqrt(value: float) -> float:
    return _f32(math.sqrt(_f32(value)))


def _dot3d(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return (a[0] * b[0] + a[1] * b[1]) + a[2] * b[2]


def _quat_rotate_f32(
    q: tuple[float, float, float, float],
    v: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Match Unity.Mathematics' SIMD q*v expansion with binary32 boundaries."""
    qx, qy, qz, qw = (_f32(value) for value in q)
    vx, vy, vz = (_f32(value) for value in v)
    tx = _fmul(2.0, _fsub(_fmul(qy, vz), _fmul(qz, vy)))
    ty = _fmul(2.0, _fsub(_fmul(qz, vx), _fmul(qx, vz)))
    tz = _fmul(2.0, _fsub(_fmul(qx, vy), _fmul(qy, vx)))
    cx = _fsub(_fmul(qy, tz), _fmul(qz, ty))
    cy = _fsub(_fmul(qz, tx), _fmul(qx, tz))
    cz = _fsub(_fmul(qx, ty), _fmul(qy, tx))
    return (
        _fadd(_fadd(vx, _fmul(qw, tx)), cx),
        _fadd(_fadd(vy, _fmul(qw, ty)), cy),
        _fadd(_fadd(vz, _fmul(qw, tz)), cz),
    )


def _normalize_float3(values: tuple[float, float, float]) -> tuple[float, float, float]:
    squares = tuple(_fmul(value, value) for value in values)
    length_sq = _fadd(_fadd(squares[0], squares[1]), squares[2])
    inverse = _f32(_f32(1.0) / _fsqrt(length_sq))
    return tuple(_fmul(value, inverse) for value in values)  # type: ignore[return-value]


def _hex(values: tuple[float, ...], fmt: str) -> list[str]:
    return [struct.pack(fmt, value).hex() for value in values]


def _inspect_abi(pe: dict[str, Any]) -> dict[str, Any]:
    export_body, export_instructions = burst._exact_rva_span(
        pe, EXPORT_RVA, EXPORT_BYTES, EXPORT_SHA256
    )
    core_body, core_instructions = burst._exact_rva_span(
        pe, CORE_RVA, CORE_BYTES, CORE_SHA256
    )
    del export_body, core_body
    export_text = [f"{ins.mnemonic} {ins.op_str}" for ins in export_instructions]
    core_text = [f"{ins.mnemonic} {ins.op_str}" for ins in core_instructions]
    required_export = {
        "mov qword ptr [rsp + 0x20], rax",
        "mov qword ptr [rsp + 0x68], r13",
        "call qword ptr [rip + 0x6e7f3]",
    }
    required_core = {
        "mov rax, qword ptr [rbp + 0x508]",
        "movsxd r10, dword ptr [rbp + 0x548]",
        "mov r12d, dword ptr [rdx + r11 + 0x18c]",
        "vmovss xmm0, dword ptr [rdx + r11 + 0x60]",
        "mov eax, dword ptr [rdx + r11 + 0x124]",
        "mov ecx, dword ptr [rdx + r11 + 0x174]",
        "mov r13d, dword ptr [rdx + r11 + 0x17c]",
        "cmp r10d, 1",
        "imul rax, rax, 0xb8",
    }
    if not required_export.issubset(export_text):
        raise burst.ContractError("Point export forwarding wrapper ABI drift")
    if not required_core.issubset(core_text):
        raise burst.ContractError("Point core argument/layout evidence drift")
    matching = [row for row in pe["exports"] if row["name"] == EXPORT_NAME]
    if len(matching) != 1 or matching[0]["rva"] != EXPORT_RVA:
        raise burst.ContractError("Point hashed export identity drift")
    return {
        "exportName": EXPORT_NAME,
        "exportRva": f"0x{EXPORT_RVA:x}",
        "exportBytes": EXPORT_BYTES,
        "exportSha256": EXPORT_SHA256,
        "forwardedPointerArguments": 13,
        "rangeIndexArgument": 14,
        "rangeIndexLoadedByValue": True,
        "teamDataStrideBytes": 464,
        "parameterStrideBytes": 808,
        "workDataStrideBytes": 184,
    }


def source_port(case: dict[str, Any]) -> dict[str, tuple[float, ...]]:
    p = tuple(case["particle"])
    a0, a1 = (tuple(row) for row in case["oldEndpoints"])
    b0, b1 = (tuple(row) for row in case["newEndpoints"])
    r0, r1 = (_f32(value) for value in case["radii"])
    inverse_old = tuple(case.get("inverseOldRotation", (0.0, 0.0, 0.0, 1.0)))
    rotation = tuple(case.get("rotation", (0.0, 0.0, 0.0, 1.0)))
    particle_radius_f = _f32(0.1)
    u = tuple(a1[i] - a0[i] for i in range(3))
    denominator = _dot3d(u, u)
    if denominator == 0.0:
        t = _f32(0.0)
    else:
        t = _f32(_dot3d(tuple(p[i] - a0[i] for i in range(3)), u) / denominator)
        t = _f32(min(max(t, _f32(0.0)), _f32(1.0)))
    collider_radius = _fadd(r0, _fmul(_fsub(r1, r0), t))
    td = float(t)
    old_center = tuple(a0[i] + (a1[i] - a0[i]) * td for i in range(3))
    old_offset_f = tuple(_f32(p[i] - old_center[i]) for i in range(3))
    local_offset = _quat_rotate_f32(inverse_old, old_offset_f)  # type: ignore[arg-type]
    transported_f = _quat_rotate_f32(rotation, local_offset)  # type: ignore[arg-type]
    transported = tuple(float(value) for value in transported_f)
    transported_length = math.sqrt(_dot3d(transported, transported))
    normal = tuple(value * (1.0 / transported_length) for value in transported)
    new_center = tuple(b0[i] + (b1[i] - b0[i]) * td for i in range(3))
    surface_radius = _fadd(collider_radius, particle_radius_f)
    surface = tuple(new_center[i] + normal[i] * float(surface_radius) for i in range(3))
    distance = _dot3d(tuple(p[i] - surface[i] for i in range(3)), normal)
    projected = p
    add_pos = (0.0, 0.0, 0.0)
    add_count = 0
    normal_f = tuple(_f32(value) for value in normal)
    if distance <= 0.0:
        projected = tuple(p[i] - normal[i] * distance for i in range(3))
        add_pos = tuple(projected[i] - p[i] for i in range(3))
        add_count = 1

    next_pos = p
    if add_count:
        average_normal = normal_f
        squares = tuple(_fmul(value, value) for value in average_normal)
        average_length = _fsqrt(_fadd(_fadd(squares[0], squares[1]), squares[2]))
        if average_length >= _f32(1.0e-8):
            weight = _f32(min(average_length, _f32(1.0)))
            next_pos = tuple(p[i] + add_pos[i] * float(weight) for i in range(3))

    friction = _f32(0.0)
    collision_normal = (0.0, 0.0, 0.0)
    if distance <= float(particle_radius_f):
        ratio = min(max(distance / float(particle_radius_f), 0.0), 1.0)
        friction = _f32(max(float(friction), 1.0 - ratio))
        squares = tuple(_fmul(value, value) for value in normal_f)
        normal_length_sq = _fadd(_fadd(squares[0], squares[1]), squares[2])
        if normal_length_sq > _f32(1.0e-6):
            collision_normal = _normalize_float3(normal_f)
    return {
        "next": tuple(next_pos),
        "friction": (friction,),
        "collisionNormal": tuple(collision_normal),
        "velocityPos": tuple(p),
    }


def _run_native(dll: Path, case: dict[str, Any]) -> dict[str, tuple[float, ...]]:
    module = ctypes.WinDLL(str(dll))
    function = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 14))(
        module._handle + CORE_RVA
    )
    buffers = [
        ctypes.create_string_buffer(4),
        ctypes.create_string_buffer(464),
        ctypes.create_string_buffer(808),
        ctypes.create_string_buffer(1),
        ctypes.create_string_buffer(4),
        ctypes.create_string_buffer(2),
        ctypes.create_string_buffer(24),
        ctypes.create_string_buffer(4),
        ctypes.create_string_buffer(12),
        ctypes.create_string_buffer(24),
        ctypes.create_string_buffer(24),
        ctypes.create_string_buffer(1),
        ctypes.create_string_buffer(184),
    ]
    (step, team, parameters, attributes, depths, team_ids, next_pos, friction,
     collision_normal, velocity_pos, base_pos, collider_flags, work) = buffers
    struct.pack_into("<i", step, 0, 0)
    struct.pack_into("<f", team, 0x60, 1.0)
    struct.pack_into("<i", team, 0x124, 0)
    struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<i", team, 0x17C, 0)
    struct.pack_into("<i", team, 0x18C, 1)
    struct.pack_into("<16f", parameters, 0x5C, *([0.1] * 16))
    struct.pack_into("<i", parameters, 0x264, 1)
    struct.pack_into("<B", attributes, 0, 2)
    struct.pack_into("<f", depths, 0, 0.0)
    struct.pack_into("<h", team_ids, 0, 0)
    particle = tuple(case["particle"])
    struct.pack_into("<3d", next_pos, 0, *particle)
    struct.pack_into("<3d", velocity_pos, 0, *particle)
    struct.pack_into("<3d", base_pos, 0, *particle)
    struct.pack_into("<B", collider_flags, 0, 0x32)
    struct.pack_into("<3d", work, 0x00, -100.0, -100.0, -100.0)
    struct.pack_into("<3d", work, 0x18, 100.0, 100.0, 100.0)
    struct.pack_into("<2f", work, 0x30, *case["radii"])
    struct.pack_into("<3d", work, 0x38, *case["oldEndpoints"][0])
    struct.pack_into("<3d", work, 0x50, *case["oldEndpoints"][1])
    struct.pack_into("<3d", work, 0x68, *case["newEndpoints"][0])
    struct.pack_into("<3d", work, 0x80, *case["newEndpoints"][1])
    struct.pack_into("<4f", work, 0x98, *case.get("inverseOldRotation", (0.0, 0.0, 0.0, 1.0)))
    struct.pack_into("<4f", work, 0xA8, *case.get("rotation", (0.0, 0.0, 0.0, 1.0)))
    function(
        *(ctypes.addressof(buffer) for buffer in buffers),
        ctypes.c_void_p(0),
    )
    return {
        "next": struct.unpack_from("<3d", next_pos),
        "friction": struct.unpack_from("<f", friction),
        "collisionNormal": struct.unpack_from("<3f", collision_normal),
        "velocityPos": struct.unpack_from("<3d", velocity_pos),
    }


def _exact_outputs(output: dict[str, tuple[float, ...]]) -> dict[str, list[str]]:
    return {
        "next": _hex(output["next"], "<d"),
        "friction": _hex(output["friction"], "<f"),
        "collisionNormal": _hex(output["collisionNormal"], "<f"),
        "velocityPos": _hex(output["velocityPos"], "<d"),
    }


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    abi = _inspect_abi(pe)
    rows = []
    for case in CASES:
        native = _run_native(dll, case)
        port = source_port(case)
        native_bits = _exact_outputs(native)
        port_bits = _exact_outputs(port)
        if native_bits != port_bits:
            differences = {
                key: {"native": native_bits[key], "source": port_bits[key]}
                for key in native_bits if native_bits[key] != port_bits[key]
            }
            raise burst.ContractError(
                f"source Point-capsule transcription differs from native core "
                f"for {case['name']}: {differences}"
            )
        rows.append({
            "name": case["name"],
            "input": {
                "particle": list(case["particle"]),
                "particleRadiusCurveFloat32": _f32(0.1),
                "oldEndpoints": [list(row) for row in case["oldEndpoints"]],
                "newEndpoints": [list(row) for row in case["newEndpoints"]],
                "capsuleRadiiFloat32": [_f32(value) for value in case["radii"]],
                "inverseOldRotationFloat32": list(case.get("inverseOldRotation", (0.0, 0.0, 0.0, 1.0))),
                "rotationFloat32": list(case.get("rotation", (0.0, 0.0, 0.0, 1.0))),
            },
            "output": {
                "next": list(native["next"]),
                "nextBinary64Le": native_bits["next"],
                "friction": native["friction"][0],
                "frictionBinary32Le": native_bits["friction"][0],
                "collisionNormal": list(native["collisionNormal"]),
                "collisionNormalBinary32Le": native_bits["collisionNormal"],
                "velocityPos": list(native["velocityPos"]),
                "velocityPosBinary64Le": native_bits["velocityPos"],
            },
        })
    return {
        "schema": "endfield.charinfo.secondary-dynamics-point-collision-golden-vectors.v1",
        "status": "native_avx2_vectors_and_source_transcription_exact_for_bounded_point_capsule_cases",
        "nativeGate": gate,
        "abiInspection": abi,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES, "sha256": CORE_SHA256},
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": rows,
        "boundary": {
            "nativeCoreExecuted": True,
            "sourceTranscriptionExactBitsMatched": True,
            "rangeIndexPassedByValue": True,
            "caseCoverage": [
                "static capsule penetration",
                "no contact and zero normal",
                "translated collider transport",
                "rotated collider transport",
                "tapered capsule radius",
                "friction near contact",
            ],
            "unityPortExecuted": False,
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
            raise SystemExit("Point collision golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
