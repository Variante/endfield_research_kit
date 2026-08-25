#!/usr/bin/env python3
"""Execute and transcribe the pinned Collider Start AVX2 capsule core."""

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
    "secondary_dynamics_collider_start_golden_vectors.json"
)
SEMANTICS = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_collider_start_semantics_contract.json"
)
SOLVER_INPUTS = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_solver_inputs.json"
)

EXPORT_NAME = "8b3d2761aaaac71a35d4a2557d570456"
EXPORT_RVA = 0x357AD0
EXPORT_BODY_BYTES = 205
EXPORT_BODY_SHA256 = "bad4ef19af75f491d1a97a73428af34b9e983eb2b5c543dace2ca3fd64bbcf83"
ENTRY_RVA = 0x243660
ENTRY_BYTES = 83
ENTRY_SHA256 = "0601c7e78f544793564164d2ecbd6bbb7f28824c8f279d64ed565ef17bbe790d"
CORE_RVA = 0x243810
CORE_BYTES = 2732
CORE_SHA256 = "a69539c847d5f68e7a1c155058f8299a6953c79004ef28e14282ccdec26d0615"
SIN_RVA = 0x1DE610
SIN_BYTES = 557
SIN_SHA256 = "d11fc448307689e5bf1c981bf1cae17af4604d6fa0105aa2196b162048a1c6ac"

OUTPUT_SIZES = {
    "nowPositions": 12,
    "nowRotations": 16,
    "oldPositions": 12,
    "oldRotations": 16,
    "workData": 184,
}


CASES: tuple[dict[str, Any], ...] = (
    {
        "name": "disabled_flag_bypass",
        "flag": 0x00,
        "typeBranch": "bypass",
    },
    {
        "name": "incomplete_active_bits_bypass",
        "flag": 0x22,
        "typeBranch": "bypass",
    },
    {
        "name": "static_aligned_x_separated_radii",
        "flag": 0x32,
        "typeBranch": "aligned_x",
        "position": (0.25, 1.0, -0.5),
        "size": (0.08, 0.12, 0.65),
    },
    {
        "name": "static_aligned_z_endminf_direction_2",
        "flag": 0x34,
        "typeBranch": "aligned_z",
        "position": (-0.1, 0.8, 0.2),
        "size": (0.105, 0.106, 0.297),
    },
    {
        "name": "translated_rotated_scaled_moving_y",
        "flag": 0x33,
        "typeBranch": "aligned_y",
        "framePosition": (1.4, -0.25, 2.1),
        "oldFramePosition": (0.8, -0.7, 1.6),
        "frameRotation": (0.19866933, 0.0, 0.0, 0.9800666),
        "oldFrameRotation": (0.0, 0.0, -0.1305262, 0.9914449),
        "frameScale": (1.25, 0.75, 1.5),
        "size": (0.077, 0.031, 0.489),
        "frameInterpolation": 0.625,
        "oldPosition": (0.55, -0.9, 1.3),
        "oldRotation": (0.0, 0.25881904, 0.0, 0.9659258),
        "centerMoveRatio": 0.45,
        "centerRotationRatio": 0.55,
    },
    {
        "name": "reverse_direction_x",
        "flag": 0xB2,
        "typeBranch": "aligned_x_reverse",
        "position": (0.0, 0.0, 0.0),
        "rotation": (0.0, 0.38268343, 0.0, 0.9238795),
        "size": (0.06, 0.11, 0.5),
    },
    {
        "name": "negative_scale_direction_y",
        "flag": 0x33,
        "typeBranch": "aligned_y_negative_scale",
        "position": (0.5, -0.25, 0.75),
        "rotation": (0.0, 0.0, 0.25881904, 0.9659258),
        "frameScale": (1.0, -1.6, 0.8),
        "size": (0.09, 0.04, 0.42),
    },
    {
        "name": "aligned_radius_overlap_clamps_both_separations",
        "flag": 0x32,
        "typeBranch": "aligned_x_radius_overlap",
        "position": (-0.5, 0.25, 1.0),
        "size": (0.31, 0.29, 0.4),
    },
    {
        "name": "unaligned_x_radius_separation",
        "flag": 0x35,
        "typeBranch": "unaligned_x",
        "position": (0.1, -0.2, 0.3),
        "rotation": (0.0, 0.0, 0.5, 0.8660254),
        "size": (0.08, 0.12, 0.7),
    },
    {
        "name": "unaligned_y_radius_overlap",
        "flag": 0x36,
        "typeBranch": "unaligned_y_radius_overlap",
        "position": (0.2, 0.4, -0.6),
        "size": (0.25, 0.22, 0.35),
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


def _fsqrt(value: float) -> float:
    return _f32(math.sqrt(_f32(value)))


def _dot4(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return _fadd(
        _fadd(_fmul(a[0], b[0]), _fmul(a[1], b[1])),
        _fadd(_fmul(a[2], b[2]), _fmul(a[3], b[3])),
    )


def _normalize4(q: tuple[float, ...]) -> tuple[float, ...]:
    inverse = _fdiv(1.0, _fsqrt(_dot4(q, q)))
    return tuple(_fmul(value, inverse) for value in q)


def _sin_burst(value: float) -> float:
    """Standalone bounded transcription of the core's scalar sine helper."""
    value = _f32(value)
    if not math.isfinite(value) or abs(value) >= _f32(125.0):
        raise burst.ContractError("Collider Start sine left its bounded source path")
    quotient = _fmul(value, _f32(0.31830987334251404))
    rounded = math.trunc(_fadd(quotient, _f32(-0.5 if quotient < 0.0 else 0.5)))
    rf = _f32(float(rounded))
    reduced = _fadd(value, _fmul(rf, _f32(-3.1414794921875)))
    reduced = _fadd(reduced, _fmul(rf, _f32(-0.0001131594181060791)))
    reduced = _fadd(reduced, _fmul(rf, _f32(-1.984187258941006e-09)))
    signed = _f32(-reduced) if rounded & 1 else reduced
    square = _fmul(reduced, reduced)
    polynomial = _fadd(_fmul(square, _f32(2.6083159809786594e-06)), _f32(-0.00019810690719168633))
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
        polynomial_input = _fmul(0.5, _fsub(1.0, absolute))
        root = 0.0 if absolute == _f32(1.0) else _fsqrt(polynomial_input)
    polynomial = _fadd(_fmul(polynomial_input, _f32(0.04197454825043678)), _f32(0.024240460246801376))
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


def _slerp(a: tuple[float, ...], b: tuple[float, ...], t: float) -> tuple[float, ...]:
    dot = _dot4(a, b)
    if dot < 0.0:
        b = tuple(_f32(-value) for value in b)
        dot = _f32(-dot)
    if dot >= _f32(0.9995):
        return _normalize4(tuple(_fadd(a[i], _fmul(t, _fsub(b[i], a[i]))) for i in range(4)))
    theta = _acos_burst(dot)
    inverse_sin = _fdiv(1.0, _fsqrt(_fsub(1.0, _fmul(dot, dot))))
    wa = _fmul(inverse_sin, _sin_burst(_fmul(_fsub(1.0, t), theta)))
    wb = _fmul(inverse_sin, _sin_burst(_fmul(t, theta)))
    return tuple(_fadd(_fmul(a[i], wa), _fmul(b[i], wb)) for i in range(4))


def _rotate(q: tuple[float, ...], v: tuple[float, ...]) -> tuple[float, float, float]:
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = _fadd(_fsub(_fmul(qy, vz), _fmul(qz, vy)), _fsub(_fmul(qy, vz), _fmul(qz, vy)))
    ty = _fadd(_fsub(_fmul(qz, vx), _fmul(qx, vz)), _fsub(_fmul(qz, vx), _fmul(qx, vz)))
    tz = _fadd(_fsub(_fmul(qx, vy), _fmul(qy, vx)), _fsub(_fmul(qx, vy), _fmul(qy, vx)))
    cx = _fsub(_fmul(qy, tz), _fmul(qz, ty))
    cy = _fsub(_fmul(qz, tx), _fmul(qx, tz))
    cz = _fsub(_fmul(qx, ty), _fmul(qy, tx))
    return (
        _fadd(_fadd(vx, _fmul(qw, tx)), cx),
        _fadd(_fadd(vy, _fmul(qw, ty)), cy),
        _fadd(_fadd(vz, _fmul(qw, tz)), cz),
    )


def _lerp3(a: tuple[float, ...], b: tuple[float, ...], t: float) -> tuple[float, float, float]:
    return tuple(_fadd(a[i], _fmul(t, _fsub(b[i], a[i]))) for i in range(3))  # type: ignore[return-value]


def _case_values(case: dict[str, Any]) -> dict[str, Any]:
    position = tuple(case.get("position", (0.0, 0.0, 0.0)))
    rotation = tuple(case.get("rotation", (0.0, 0.0, 0.0, 1.0)))
    return {
        "flag": int(case["flag"]),
        "size": tuple(_f32(v) for v in case.get("size", (0.08, 0.1, 0.5))),
        "framePosition": tuple(_f32(v) for v in case.get("framePosition", position)),
        "frameRotation": tuple(_f32(v) for v in case.get("frameRotation", rotation)),
        "frameScale": tuple(_f32(v) for v in case.get("frameScale", (1.0, 1.0, 1.0))),
        "oldFramePosition": tuple(_f32(v) for v in case.get("oldFramePosition", position)),
        "oldFrameRotation": tuple(_f32(v) for v in case.get("oldFrameRotation", rotation)),
        "oldPosition": tuple(_f32(v) for v in case.get("oldPosition", position)),
        "oldRotation": tuple(_f32(v) for v in case.get("oldRotation", rotation)),
        "frameInterpolation": _f32(case.get("frameInterpolation", 1.0)),
        "centerMoveRatio": _f32(case.get("centerMoveRatio", 1.0)),
        "centerRotationRatio": _f32(case.get("centerRotationRatio", 1.0)),
    }


def _initial_outputs(values: dict[str, Any]) -> dict[str, bytearray]:
    outputs = {name: bytearray([0xA5] * size) for name, size in OUTPUT_SIZES.items()}
    struct.pack_into("<3f", outputs["oldPositions"], 0, *values["oldPosition"])
    struct.pack_into("<4f", outputs["oldRotations"], 0, *values["oldRotation"])
    return outputs


def source_port(case: dict[str, Any]) -> dict[str, bytes]:
    """Standalone source transcription; this function never invokes native code."""
    values = _case_values(case)
    outputs = _initial_outputs(values)
    flag = values["flag"]
    if ((~flag) & 0x30) != 0:
        return {name: bytes(data) for name, data in outputs.items()}

    now_position = _lerp3(values["oldFramePosition"], values["framePosition"], values["frameInterpolation"])
    now_rotation = _normalize4(_slerp(values["oldFrameRotation"], values["frameRotation"], values["frameInterpolation"]))
    old_position = _lerp3(values["oldPosition"], now_position, values["centerMoveRatio"])
    old_rotation_raw = _slerp(values["oldRotation"], now_rotation, values["centerRotationRatio"])
    old_rotation = _normalize4(old_rotation_raw)
    struct.pack_into("<3f", outputs["nowPositions"], 0, *now_position)
    struct.pack_into("<4f", outputs["nowRotations"], 0, *now_rotation)
    struct.pack_into("<3f", outputs["oldPositions"], 0, *old_position)
    struct.pack_into("<4f", outputs["oldRotations"], 0, *old_rotation)

    collider_type = flag & 0x0F
    axes = {2: (1.0, 0.0, 0.0), 3: (0.0, 1.0, 0.0), 4: (0.0, 0.0, 1.0),
            5: (1.0, 0.0, 0.0), 6: (0.0, 1.0, 0.0)}
    if collider_type not in axes:
        raise burst.ContractError(f"case {case['name']} left the selected capsule branch set")
    axis = axes[collider_type]
    scale_parts = tuple(_fmul(values["frameScale"][i], axis[i]) for i in range(3))
    axis_scale = _fadd(_fadd(scale_parts[0], scale_parts[1]), scale_parts[2])
    if axis_scale == 0.0:
        direction = (0.0, 0.0, 0.0)
    else:
        sign = _f32(-1.0 if axis_scale < 0.0 else 1.0)
        direction = tuple(_fmul(value, sign) for value in axis)
    if flag & 0x80:
        direction = tuple(_f32(-value) for value in direction)
    absolute_scale = _f32(abs(axis_scale))
    radius0, radius1, length = tuple(_fmul(value, absolute_scale) for value in values["size"])
    if collider_type < 5:
        half = _fmul(length, 0.5)
        separation0 = _f32(max(_fsub(half, radius0), 0.0))
        separation1 = _f32(max(_fsub(half, radius1), 0.0))
    else:
        separation0 = _f32(0.0)
        separation1 = _f32(max(_fsub(_fsub(length, radius0), radius1), 0.0))

    # The core publishes the normalized old rotation but deliberately keeps
    # the pre-normalized interpolation result live for old endpoint rotation
    # and quaternion inversion.
    old_offset0 = _rotate(old_rotation_raw, tuple(_fmul(v, separation0) for v in direction))
    old_offset1 = _rotate(old_rotation_raw, tuple(_fmul(v, separation1) for v in direction))
    next_offset0 = _rotate(now_rotation, tuple(_fmul(v, separation0) for v in direction))
    next_offset1 = _rotate(now_rotation, tuple(_fmul(v, separation1) for v in direction))
    old0 = tuple(_fadd(old_position[i], old_offset0[i]) for i in range(3))
    old1 = tuple(_fsub(old_position[i], old_offset1[i]) for i in range(3))
    next0 = tuple(_fadd(now_position[i], next_offset0[i]) for i in range(3))
    next1 = tuple(_fsub(now_position[i], next_offset1[i]) for i in range(3))
    lower = tuple(float(min(_fsub(old0[i], radius0), _fsub(next0[i], radius0),
                            _fsub(old1[i], radius1), _fsub(next1[i], radius1))) for i in range(3))
    upper = tuple(float(max(_fadd(old0[i], radius0), _fadd(next0[i], radius0),
                            _fadd(old1[i], radius1), _fadd(next1[i], radius1))) for i in range(3))
    norm_sq = _dot4(old_rotation_raw, old_rotation_raw)
    inverse_old = tuple(_fmul(old_rotation_raw[i], _fdiv(1.0, norm_sq)) for i in range(4))
    inverse_old = (_f32(-inverse_old[0]), _f32(-inverse_old[1]), _f32(-inverse_old[2]), inverse_old[3])

    work = outputs["workData"]
    struct.pack_into("<3d", work, 0x00, *lower)
    struct.pack_into("<3d", work, 0x18, *upper)
    struct.pack_into("<2f", work, 0x30, radius0, radius1)
    struct.pack_into("<3d", work, 0x38, *(float(value) for value in old0))
    struct.pack_into("<3d", work, 0x50, *(float(value) for value in old1))
    struct.pack_into("<3d", work, 0x68, *(float(value) for value in next0))
    struct.pack_into("<3d", work, 0x80, *(float(value) for value in next1))
    struct.pack_into("<4f", work, 0x98, *inverse_old)
    struct.pack_into("<4f", work, 0xA8, *now_rotation)
    return {name: bytes(data) for name, data in outputs.items()}


def _run_native(dll: Path, case: dict[str, Any]) -> dict[str, bytes]:
    values = _case_values(case)
    outputs = _initial_outputs(values)
    module = ctypes.WinDLL(str(dll))
    function = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 16), ctypes.c_int)(module._handle + CORE_RVA)
    buffers = [
        ctypes.create_string_buffer(4), ctypes.create_string_buffer(464), ctypes.create_string_buffer(696),
        ctypes.create_string_buffer(2), ctypes.create_string_buffer(1), ctypes.create_string_buffer(12),
        ctypes.create_string_buffer(12), ctypes.create_string_buffer(16), ctypes.create_string_buffer(12),
        ctypes.create_string_buffer(12), ctypes.create_string_buffer(16), ctypes.create_string_buffer(12),
        ctypes.create_string_buffer(16), ctypes.create_string_buffer(12), ctypes.create_string_buffer(16),
        ctypes.create_string_buffer(184),
    ]
    (indices, team, center, team_ids, flags, size, frame_pos, frame_rot, frame_scale,
     old_frame_pos, old_frame_rot, now_pos, now_rot, old_pos, old_rot, work) = buffers
    struct.pack_into("<i", indices, 0, 0)
    struct.pack_into("<f", team, 0x3C, values["frameInterpolation"])
    struct.pack_into("<f", center, 0x1C0, values["centerMoveRatio"])
    struct.pack_into("<f", center, 0x1C4, values["centerRotationRatio"])
    struct.pack_into("<h", team_ids, 0, 0)
    struct.pack_into("<B", flags, 0, values["flag"])
    struct.pack_into("<3f", size, 0, *values["size"])
    struct.pack_into("<3f", frame_pos, 0, *values["framePosition"])
    struct.pack_into("<4f", frame_rot, 0, *values["frameRotation"])
    struct.pack_into("<3f", frame_scale, 0, *values["frameScale"])
    struct.pack_into("<3f", old_frame_pos, 0, *values["oldFramePosition"])
    struct.pack_into("<4f", old_frame_rot, 0, *values["oldFrameRotation"])
    ctypes.memmove(now_pos, bytes(outputs["nowPositions"]), 12)
    ctypes.memmove(now_rot, bytes(outputs["nowRotations"]), 16)
    ctypes.memmove(old_pos, bytes(outputs["oldPositions"]), 12)
    ctypes.memmove(old_rot, bytes(outputs["oldRotations"]), 16)
    ctypes.memmove(work, bytes(outputs["workData"]), 184)
    function(*(ctypes.addressof(buffer) for buffer in buffers), 0)
    return {
        "nowPositions": ctypes.string_at(now_pos, 12),
        "nowRotations": ctypes.string_at(now_rot, 16),
        "oldPositions": ctypes.string_at(old_pos, 12),
        "oldRotations": ctypes.string_at(old_rot, 16),
        "workData": ctypes.string_at(work, 184),
    }


def _file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": path.relative_to(LAB_ROOT).as_posix(), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _inspect_identity(pe: dict[str, Any]) -> dict[str, Any]:
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    selected = [row for row in semantics["targets"] if row["hash"] == EXPORT_NAME]
    if len(selected) != 1:
        raise burst.ContractError("Collider Start semantic candidate identity drift")
    row = selected[0]
    avx = [item for item in row["initializerAssignments"] if item["cpuVariant"] == "avx2"]
    if (semantics["semanticDecision"]["semanticCandidateHash"] != EXPORT_NAME or
            not row["semanticMatch"]["allRequiredChecksPass"] or len(avx) != 1):
        raise burst.ContractError("Collider Start unique semantic selection drift")
    if row["callMapping"]["callArgumentSources"] != [f"param{i}" for i in range(1, 18)]:
        raise burst.ContractError("Collider Start canonical forwarding order drift")
    burst._exact_rva_span(pe, EXPORT_RVA, EXPORT_BODY_BYTES, EXPORT_BODY_SHA256)
    burst._exact_rva_span(pe, ENTRY_RVA, ENTRY_BYTES, ENTRY_SHA256)
    _, instructions = burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    burst._exact_rva_span(pe, SIN_RVA, SIN_BYTES, SIN_SHA256)
    exports = [item for item in pe["exports"] if item["name"] == EXPORT_NAME]
    if len(exports) != 1 or exports[0]["rva"] != EXPORT_RVA:
        raise burst.ContractError("Collider Start hashed export table identity drift")
    text = {f"{ins.mnemonic} {ins.op_str}" for ins in instructions}
    required = {
        "movsxd rsi, dword ptr [rcx + r10*4]",
        "movzx edi, byte ptr [rax + rsi]",
        "imul r9, r13, 0x1d0",
        "imul rax, r13, 0x2b8",
        "imul rcx, rsi, 0xb8",
        "movsxd r10, dword ptr [rbp + 0x120]",
    }
    if not required.issubset(text):
        raise burst.ContractError("Collider Start physical ABI/layout evidence drift")
    return {
        "selectionBasis": "unique canonical 17-argument semantic candidate in the pinned source-metadata contract",
        "exportName": EXPORT_NAME, "exportRva": f"0x{EXPORT_RVA:x}",
        "exportBodyBytes": EXPORT_BODY_BYTES, "exportBodySha256": EXPORT_BODY_SHA256,
        "entryRva": f"0x{ENTRY_RVA:x}", "entryBytes": ENTRY_BYTES, "entrySha256": ENTRY_SHA256,
        "coreRva": f"0x{CORE_RVA:x}", "coreBytes": CORE_BYTES, "coreSha256": CORE_SHA256,
        "sineHelperRva": f"0x{SIN_RVA:x}", "sineHelperBytes": SIN_BYTES, "sineHelperSha256": SIN_SHA256,
        "physicalAbi": {
            "pointerArguments": 16, "rangeIndexArgument": 17, "rangeIndexByValue": True,
            "teamDataStrideBytes": 464, "centerDataStrideBytes": 696,
            "transformPositionStrideBytes": 12, "quaternionStrideBytes": 16,
            "workDataStrideBytes": 184,
        },
    }


def _endminf_scope() -> dict[str, Any]:
    payload = json.loads(SOLVER_INPUTS.read_text(encoding="utf-8"))
    colliders = payload["actors"]["endminf"]["colliders"]
    capsules = [row for row in colliders if row["type"] == "BeyondDynamicBone.BeyondBoneCapsuleCollider"]
    if not capsules:
        raise burst.ContractError("Endminf capsule source set is empty")
    return {
        "source": _file(SOLVER_INPUTS),
        "capsuleCount": len(capsules),
        "directions": sorted({int(row["direction"]) for row in capsules}),
        "reverseDirections": sorted({int(row["reverse_direction"]) for row in capsules}),
        "radiusSeparations": sorted({float(row["radius_separation"]) for row in capsules}),
        "alignedOnCenter": sorted({int(row["aligned_on_center"]) for row in capsules}),
    }


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    identity = _inspect_identity(pe)
    vectors = []
    for case in CASES:
        native = _run_native(dll, case)
        source = source_port(case)
        matches = {name: native[name] == source[name] for name in OUTPUT_SIZES}
        if not all(matches.values()):
            bad = [name for name, value in matches.items() if not value]
            raise burst.ContractError(f"Collider Start native/source mismatch for {case['name']}: {bad}")
        vectors.append({
            "name": case["name"], "flag": f"0x{int(case['flag']):02x}",
            "typeBranch": case["typeBranch"], "inputs": _case_values(case),
            "outputs": {name: native[name].hex() for name in OUTPUT_SIZES},
            "outputByteCounts": dict(OUTPUT_SIZES), "nativeSourceBitExact": matches,
        })
    return {
        "schema": "endfield.charinfo.secondary-dynamics-collider-start-golden-v1",
        "status": "native_source_bit_exact",
        "nativeGate": gate,
        "identity": identity,
        "sourceContracts": {"semantics": _file(SEMANTICS)},
        "endminfScope": _endminf_scope(),
        "coverage": {
            "disabledBypass": True, "staticCapsule": True, "translatedMovingCapsule": True,
            "rotatedMovingCapsule": True, "scaledMovingCapsule": True,
            "directionBranches": ["x", "y", "z"], "reverseDirection": True,
            "alignedBranches": ["centered", "one_sided"],
            "radiusSeparationBranches": ["positive", "clamped_zero"],
        },
        "vectors": vectors,
        "verification": {
            "vectorCount": len(vectors), "allOutputBuffersComparedAsRawBytes": True,
            "comparedOutputs": dict(OUTPUT_SIZES), "nativeCoreExecuted": True,
            "sourceInvokesNativeHelpers": False,
        },
        "boundary": [
            "Export selection is the unique static canonical-signature and managed-fallback semantic match in the pinned contract; no retail runtime resolver telemetry is claimed.",
            "The native audit executes the pinned AVX2 core and its in-module sine dependency; source_port is standalone and executes no native helper.",
            "Capsule branches 2 through 6 are covered. Sphere and plane branches are outside Endminf's serialized collider requirement.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_contract()
        serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
            print(json.dumps({"status": payload["status"], "matches": matches, "vectors": len(payload["vectors"])}))
            return 0 if matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(json.dumps({"status": payload["status"], "output": str(args.output), "vectors": len(payload["vectors"])}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, burst.ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
