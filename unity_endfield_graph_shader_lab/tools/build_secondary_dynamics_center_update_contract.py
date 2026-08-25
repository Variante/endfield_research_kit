#!/usr/bin/env python3
"""Build the pinned, fail-closed no-wind CenterData/TeamData update contract."""

from __future__ import annotations

import argparse
import bisect
import ctypes
import hashlib
import importlib.util
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_center_update_contract.json"
ELEMENT_LAYOUT = SOURCE_ROOT / "secondary_dynamics_element_layout_contract.json"
CALLBACK_CONTRACT = SOURCE_ROOT / "secondary_dynamics_callback_contract.json"
SUBSTEP_CONTRACT = SOURCE_ROOT / "secondary_dynamics_substep_contract.json"
SOLVER_INPUTS = SOURCE_ROOT / "secondary_dynamics_solver_inputs.json"

EXPORT_NAME = "51ab4d19d63aa082d5346e023278645e"
EXPORT_RVA = 0x355FE0
EXPORT_BYTES = 171
EXPORT_SHA256 = "b266a8cbb0c27f5674ca71a2fcca85615073b3f78e5e11955dc58c9caab82caa"
SLOT_RVA = 0x3C51D0
AVX_ASSIGN_RVA = 0x35C2AF
AVX_ASSIGN_SHA256 = "90745f96923fec818c664b7decdebda2ab0afe997a7e42fd7fdc8aa15307f9db"
AVX_ENTRY_RVA = 0x28E960
AVX_ENTRY_BYTES = 84
AVX_ENTRY_SHA256 = "3803a59146214f0782b106edc230598320fea21ae938cd615b21a9d0da91687b"
AVX_RANGE_RVA = 0x292B50
AVX_RANGE_BYTES = 244
AVX_RANGE_SHA256 = "15cfda483ccbbd7a7aacd774815bcae9f17fd1b2039269921ffd687dad52093d"
AVX_CORE_RVA = 0x28EB60
AVX_CORE_BYTES = 16366
AVX_CORE_SHA256 = "20ccbda5b2cc0e710ff88fb83729bad8c4e31f006773d8b1fef736adcc559de4"

MANAGED_METHODS = (
    (384598, "BeyondDynamicBone.TeamManager", "CalcCenterAndInertiaAndWind", 0x1835BC3E0, 896,
     "0a6c8277ce4fc5ace672f530aed89710a5b75fc87d33daa8db8d8eccf6f36ed7"),
    (384713, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindKernels", "CalcCenterAndInertiaAndWindKernel", 0x18673AA38, 264,
     "5c7a6b8cc3ab1da43158ddd8bc8b18004370e3b00a6eb79851e6aa114bcc8759"),
    (384714, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindKernels", "CalcCenterAndInertiaAndWindRangeKernel", 0x18673AB40, 264,
     "59378c3d785c3fd5714c200bd92a8a2027fc0597b60e1505562bdae46736524c"),
    (384716, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindKernels", "CalcCenterAndInertiaAndWindKernel$BurstManaged", 0x18673854C, 9452,
     "64a0db2d9078e13d3196e93200ae91c9f8849abf7fd501ee5e1ca05c3af0b2a4"),
    (384717, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindKernels", "CalcCenterAndInertiaAndWindRangeKernel$BurstManaged", 0x18673149C, 5428,
     "d9f763de10e2ca12e23a6d99c1734e4d049514863192af5db43304b2c1438808"),
    (384749, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindJob", "SetIndexCount", 0x183D46500, 64,
     "5159fe66c28f5cf8da625f431dcdea3f3b0ed26d800985d9806e3ef4d233685e"),
    (384750, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindJob", "Execute", 0x1867375F8, 120,
     "a672fbeb7d29c642ddd41a07a496b5b762b6454163d4963655723b2adff730fb"),
    (384751, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindJob", "Execute", 0x186734FCC, 9772,
     "9e801c009a429048499417ef39dd6fd2ce10156e5a55f03b91ad6ab988b89105"),
    (384753, "BeyondDynamicBone.TeamManager+CalcCenterAndInertiaAndWindJob", "UnsafeDo", 0x186737670, 428,
     "8e63b42fb3030af1f7f7f30005e42c0b2c67f8bbf67abc88a0046122e48b9233"),
)

TEAM_STRIDE = 464
CENTER_STRIDE = 696
TEAM_WIND_STRIDE = 152
PARAMETER_STRIDE = 808
ACTIVE_GATE_MASK = 0x2000000000080812
ACTIVE_GATE_VALUE = 0x2

SELECTED_FIELDS = {
    "team.flag": ("team", 0x0, 8),
    "team.frameInterpolation": ("team", 0x3C, 4),
    "team.gravityRatio": ("team", 0x40, 4),
    "team.scaleRatio": ("team", 0x60, 4),
    "center.componentWorldPosition": ("center", 0x60, 24),
    "center.componentWorldRotation": ("center", 0x78, 16),
    "center.componentWorldScale": ("center", 0x88, 12),
    "center.oldComponentWorldPosition": ("center", 0x98, 24),
    "center.oldComponentWorldRotation": ("center", 0xB0, 16),
    "center.frameComponentShiftVector": ("center", 0xCC, 12),
    "center.frameComponentShiftRotation": ("center", 0xD8, 16),
    "center.frameMovingSpeed": ("center", 0xE8, 4),
    "center.frameMovingDirection": ("center", 0xEC, 12),
    "center.frameWorldPosition": ("center", 0xF8, 24),
    "center.frameWorldRotation": ("center", 0x110, 16),
    "center.oldFrameWorldPosition": ("center", 0x138, 24),
    "center.oldFrameWorldRotation": ("center", 0x150, 16),
    "center.nowWorldPosition": ("center", 0x170, 24),
    "center.nowWorldRotation": ("center", 0x188, 16),
    "center.oldWorldPosition": ("center", 0x198, 24),
    "center.oldWorldRotation": ("center", 0x1B0, 16),
    "center.stepMoveInertiaRatio": ("center", 0x1C0, 4),
    "center.stepRotationInertiaRatio": ("center", 0x1C4, 4),
    "center.stepVector": ("center", 0x1C8, 12),
    "center.stepRotation": ("center", 0x1D4, 16),
    "center.inertiaVector": ("center", 0x1E4, 12),
    "center.inertiaRotation": ("center", 0x1F0, 16),
    "center.stepMovingSpeed": ("center", 0x200, 4),
    "center.stepMovingDirection": ("center", 0x204, 12),
    "center.angularVelocity": ("center", 0x210, 4),
    "center.rotationAxis": ("center", 0x214, 12),
    "center.initLocalGravityDirection": ("center", 0x220, 12),
    "center.smoothingVelocity": ("center", 0x22C, 12),
}

FIXED_AGGREGATION_FIELDS = (
    "team.flag", "center.frameWorldPosition", "center.frameWorldRotation",
    "center.oldFrameWorldPosition", "center.oldFrameWorldRotation",
    "center.nowWorldPosition", "center.nowWorldRotation",
    "center.oldWorldPosition", "center.oldWorldRotation",
)
FIXED_POSITION_FIELDS = tuple(field for field in FIXED_AGGREGATION_FIELDS
                              if field == "team.flag" or field.endswith("Position"))
TARGET_FIXED_CERTIFIED_FIELDS = FIXED_AGGREGATION_FIELDS + ("team.gravityRatio", "team.scaleRatio")
PRESERVED_SIMULATION_FEED_FIELDS = (
    "center.stepMoveInertiaRatio", "center.stepRotationInertiaRatio", "center.stepVector",
    "center.stepRotation", "center.inertiaVector", "center.inertiaRotation",
    "center.stepMovingSpeed", "center.stepMovingDirection", "center.angularVelocity",
    "center.rotationAxis", "center.initLocalGravityDirection",
)

ENDMINF_FIXED = {
    "MC_Ribbon2": {"fixed": [0], "centerTransformIndex": 6},
    "MC_Hair": {"fixed": [0, 3, 7, 10, 13, 17, 22, 26], "centerTransformIndex": 30},
    "MC_Ribbon": {"fixed": [0, 6, 10, 16], "centerTransformIndex": 20},
    "MC_Coat": {"fixed": [2, 4, 12, 26, 28, 33, 45, 47, 55], "centerTransformIndex": 70},
}


class ContractError(RuntimeError):
    pass


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": _repo_path(path), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _qmul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    # Keep every multiply/add at binary32: this matches the AVX2 scalar lanes.
    return (
        _f32(_f32(_f32(aw * bx) + _f32(ax * bw)) + _f32(_f32(ay * bz) - _f32(az * by))),
        _f32(_f32(_f32(aw * by) - _f32(ax * bz)) + _f32(_f32(ay * bw) + _f32(az * bx))),
        _f32(_f32(_f32(aw * bz) + _f32(ax * by)) + _f32(_f32(az * bw) - _f32(ay * bx))),
        _f32(_f32(_f32(aw * bw) - _f32(ax * bx)) - _f32(_f32(ay * by) + _f32(az * bz))),
    )


def _qnormalize(q: tuple[float, ...]) -> tuple[float, float, float, float]:
    d = _f32(sum(_f32(value * value) for value in q))
    if not d > 0.0:
        return (0.0, 0.0, 0.0, 1.0)
    inv = _f32(1.0 / _f32(d ** 0.5))
    return tuple(_f32(value * inv) for value in q)  # type: ignore[return-value]


def _dot3(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return _f32(_f32(_f32(a[0] * b[0]) + _f32(a[1] * b[1])) + _f32(a[2] * b[2]))


def _cross(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float]:
    return (
        _f32(_f32(a[1] * b[2]) - _f32(a[2] * b[1])),
        _f32(_f32(a[2] * b[0]) - _f32(a[0] * b[2])),
        _f32(_f32(a[0] * b[1]) - _f32(a[1] * b[0])),
    )


def _normalize3(value: tuple[float, ...]) -> tuple[float, float, float]:
    length = _f32(math.sqrt(_dot3(value, value)))
    reciprocal = _f32(1.0 / length)
    return tuple(_f32(lane * reciprocal) for lane in value)  # type: ignore[return-value]


def _qrotate(q: tuple[float, ...], value: tuple[float, ...]) -> tuple[float, float, float]:
    xyz = q[:3]
    twice_cross = tuple(_f32(2.0 * lane) for lane in _cross(xyz, value))
    second_cross = _cross(xyz, twice_cross)
    return tuple(_f32(_f32(value[i] + _f32(q[3] * twice_cross[i])) + second_cross[i])
                 for i in range(3))  # type: ignore[return-value]


def _shuffle4(value: tuple[float, ...], immediate: int) -> tuple[float, float, float, float]:
    return tuple(value[(immediate >> (lane * 2)) & 3] for lane in range(4))  # type: ignore[return-value]


def _mul4(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    return tuple(_f32(a[i] * b[i]) for i in range(4))  # type: ignore[return-value]


def _sub4(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    return tuple(_f32(a[i] - b[i]) for i in range(4))  # type: ignore[return-value]


def _add4(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    return tuple(_f32(a[i] + b[i]) for i in range(4))  # type: ignore[return-value]


def _burst_qmul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    aw_b = _mul4((a[3],) * 4, b)
    bw_a = _mul4(_shuffle4(a, 0x24), _shuffle4(b, 0x3F))
    cross_a = _mul4(_shuffle4(a, 0x49), _shuffle4(b, 0x52))
    signed = _mul4(_add4(bw_a, cross_a), (1.0, 1.0, 1.0, -1.0))
    tail = _mul4(_shuffle4(a, 0x92), _shuffle4(b, 0x89))
    return _sub4(_add4(aw_b, signed), tail)


def _burst_rotated_basis_pair(q: tuple[float, ...]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    # Literal transcription of AVX2 0x28fbbd..0x28fc3f.
    one_xw = (0.0, 1.0, 0.0, 1.0)
    one_z = (0.0, 0.0, 1.0, 0.0)
    one_x = (1.0, 0.0, 0.0, 0.0)
    q_c9 = _shuffle4(q, 0xC9)
    q_w = (q[3],) * 4

    twice = tuple(_f32(2.0 * lane) for lane in _sub4(_mul4(q, one_x), _mul4(q_c9, one_xw)))
    twice_c9 = _shuffle4(twice, 0xC9)
    first = _add4(_mul4(q_w, twice_c9), one_xw)
    first = _add4(first, _shuffle4(_sub4(_mul4(q, _shuffle4(twice, 0xD2)),
                                                   _mul4(twice_c9, q_c9)), 0xC9))

    twice = tuple(_f32(2.0 * lane) for lane in _sub4(_mul4(q, one_xw), _mul4(one_z, q_c9)))
    twice_c9 = _shuffle4(twice, 0xC9)
    second = _add4(_mul4(q_w, twice_c9), one_z)
    second = _add4(second, _shuffle4(_sub4(_mul4(_shuffle4(twice, 0xD2), q),
                                                     _mul4(twice_c9, q_c9)), 0xC9))
    return first, second


def _u32(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _from_u32(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value & 0xFFFFFFFF))[0]


def _quaternion_from_matrix(columns: tuple[tuple[float, ...], ...]) -> tuple[float, float, float, float]:
    u, v, w = columns
    u_sign = _u32(u[0]) & 0x80000000
    t = _f32(v[1] + _from_u32(_u32(w[2]) ^ u_sign))
    u_mask = 0xFFFFFFFF if u_sign else 0
    t_mask = 0xFFFFFFFF if _u32(t) & 0x80000000 else 0
    sign_flips = [0, 0x80000000, 0x80000000, 0x80000000]
    u_flips = [0, 0x80000000, 0, 0x80000000]
    t_flips = [0x80000000, 0x80000000, 0x80000000, 0]
    signs = [sign_flips[i] ^ (u_mask & u_flips[i]) ^ (t_mask & t_flips[i])
             for i in range(4)]
    left = (_f32(1.0 + abs(u[0])), u[1], w[0], v[2])
    right = (t, v[0], u[2], w[1])
    value = tuple(_f32(left[i] + _from_u32(_u32(right[i]) ^ signs[i])) for i in range(4))
    if u_mask:
        value = (value[2], value[3], value[0], value[1])
    if not t_mask:
        value = (value[3], value[2], value[1], value[0])
    products = tuple(_f32(lane * lane) for lane in value)
    length_sq = _f32(_f32(products[0] + products[1]) + _f32(products[2] + products[3]))
    reciprocal = _f32(1.0 / _f32(math.sqrt(length_sq)))
    return tuple(_f32(lane * reciprocal) for lane in value)  # type: ignore[return-value]


def _look_rotation(forward: tuple[float, ...], up: tuple[float, ...]) -> tuple[float, float, float, float]:
    forward = _normalize3(forward)
    up = _normalize3(up)
    right = _normalize3(_cross(up, forward))
    corrected_up = _cross(forward, right)
    return _quaternion_from_matrix((right, corrected_up, forward))


def _aggregate_fixed(positions: list[tuple[float, float, float]],
                     rotations: list[tuple[float, float, float, float]],
                     binds: list[tuple[float, float, float, float]],
                     fixed: list[int]) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
    if not fixed:
        raise ContractError("fixed-center aggregation requires a nonempty UInt16 range")
    ps = [0.0, 0.0, 0.0]
    forward_sum = [0.0, 0.0, 0.0]
    up_sum = [0.0, 0.0, 0.0]
    for index in fixed:
        for lane in range(3):
            ps[lane] += positions[index][lane]
        bind = binds[index]
        relative = _burst_qmul(rotations[index], bind)
        up4, forward4 = _burst_rotated_basis_pair(relative)
        forward, up = forward4[:3], up4[:3]
        for lane in range(3):
            forward_sum[lane] = _f32(forward_sum[lane] + forward[lane])
            up_sum[lane] = _f32(up_sum[lane] + up[lane])
    count = len(fixed)
    return (tuple(value / count for value in ps),
            _look_rotation(tuple(forward_sum), tuple(up_sum)))  # type: ignore[return-value]


def _source_payload(path: Path, schema: str, status: str | None = None) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != schema:
        raise ContractError(f"source schema drift: {path}")
    if status is not None and payload.get("status") != status:
        raise ContractError(f"source status drift: {path}")
    return payload


def _managed_rows(game_path: Path, metadata_path: Path) -> list[dict[str, Any]]:
    catalog = _load("center_update_metadata", REPO_ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py")
    native = _load("center_update_native", REPO_ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py")
    md = catalog.Metadata(metadata_path)
    pe = native.PeImage(game_path)
    code_registration = native.find_code_registration(pe, {md.string(row.name_index) for row in md.images})
    modules = native.parse_codegen_modules(pe, code_registration)
    _, by_pointer = native.build_pointer_indexes(pe, md, modules, native.image_method_ranges(md))
    pointers = sorted(pointer for pointer in by_pointer if pointer)
    result = []
    for method_index, type_name, method_name, va, size, digest in MANAGED_METHODS:
        matches = [(pointer, row) for pointer, rows in by_pointer.items() for row in rows
                   if int(row.get("methodIndex", -1)) == method_index]
        if len(matches) != 1:
            raise ContractError(f"managed method {method_index} pointer count drift")
        pointer, identity = matches[0]
        end = pointers[bisect.bisect_right(pointers, pointer)]
        body = pe.bytes_at_va(pointer, end - pointer)
        if ((identity.get("type"), identity.get("method")) != (type_name, method_name)
                or (pointer, len(body), hashlib.sha256(body).hexdigest()) != (va, size, digest)):
            raise ContractError(f"managed method identity drift: {method_index}")
        result.append({"methodIndex": method_index, "token": identity["token"], "type": type_name,
                       "method": method_name, "startVa": f"0x{va:x}", "spanBytes": size,
                       "sha256": digest})
    return result


def _burst_identity(pe: dict[str, Any]) -> dict[str, Any]:
    export = next((row for row in pe["exports"] if row["name"] == EXPORT_NAME), None)
    if export is None or export["rva"] != EXPORT_RVA:
        raise ContractError("center range hashed export drift")
    body, instructions = burst._exact_rva_span(pe, EXPORT_RVA, EXPORT_BYTES, EXPORT_SHA256)
    calls = burst._rip_call_rows(pe, pe["imageBase"] + EXPORT_RVA, instructions)
    if len(calls) != 1 or int(calls[0]["targetVa"], 16) - pe["imageBase"] != SLOT_RVA:
        raise ContractError("center range function-pointer slot drift")
    assign, assign_instructions = burst._exact_rva_span(
        pe, AVX_ASSIGN_RVA, 14, AVX_ASSIGN_SHA256,
    )
    if [row.mnemonic for row in assign_instructions] != ["lea", "mov"]:
        raise ContractError("center AVX2 assignment shape drift")
    if [burst._rip_memory_target(pe, row) for row in assign_instructions] != [
            pe["imageBase"] + AVX_ENTRY_RVA, pe["imageBase"] + SLOT_RVA]:
        raise ContractError("center AVX2 assignment edge drift")
    _, entry = burst._exact_rva_span(pe, AVX_ENTRY_RVA, AVX_ENTRY_BYTES, AVX_ENTRY_SHA256)
    _, range_loop = burst._exact_rva_span(pe, AVX_RANGE_RVA, AVX_RANGE_BYTES, AVX_RANGE_SHA256)
    _, core = burst._exact_rva_span(pe, AVX_CORE_RVA, AVX_CORE_BYTES, AVX_CORE_SHA256)
    if [burst._direct_target(row, pe["imageBase"]) for row in entry if row.mnemonic == "call"] != [AVX_RANGE_RVA]:
        raise ContractError("center entry-to-range edge drift")
    if [burst._direct_target(row, pe["imageBase"]) for row in range_loop if row.mnemonic == "call"] != [AVX_CORE_RVA]:
        raise ContractError("center range-to-core edge drift")
    text = [f"{row.mnemonic} {row.op_str}" for row in core]
    for marker in ("0x1d0", "0x2b8", "0x328"):
        if not any(marker in row for row in text):
            raise ContractError(f"center core stride marker missing: {marker}")
    return {
        "selectionBasis": "unique 15-argument wrapper with float, eleven pointers, int windZoneCount, pointer windDataArray, and int range length; core has all three canonical structure strides",
        "export": {"name": EXPORT_NAME, "rva": f"0x{EXPORT_RVA:x}", "bytes": len(body), "sha256": EXPORT_SHA256,
                   "functionPointerSlotRva": f"0x{SLOT_RVA:x}"},
        "avx2": {
            "burstInitializeAssignment": {"rva": f"0x{AVX_ASSIGN_RVA:x}", "bytes": len(assign),
                                          "sha256": hashlib.sha256(assign).hexdigest()},
            "entry": {"rva": f"0x{AVX_ENTRY_RVA:x}", "bytes": AVX_ENTRY_BYTES, "sha256": AVX_ENTRY_SHA256},
            "rangeLoop": {"rva": f"0x{AVX_RANGE_RVA:x}", "bytes": AVX_RANGE_BYTES, "sha256": AVX_RANGE_SHA256},
            "core": {"rva": f"0x{AVX_CORE_RVA:x}", "bytes": AVX_CORE_BYTES, "sha256": AVX_CORE_SHA256},
        },
        "abi": ["simulationDeltaTime:f32", "teamDataArray:ptr", "centerDataArray:ptr", "teamWindArray:ptr",
                "parameterArray:ptr", "positions:ptr", "rotations:ptr", "vertexBindPoseRotations:ptr",
                "fixedArray:ptr", "transformPositionArray:ptr", "transformRotationArray:ptr",
                "transformScaleArray:ptr", "windZoneCount:i32", "windDataArray:ptr", "length:i32"],
    }


def _simulation_feed_write_ownership(pe: dict[str, Any]) -> dict[str, Any]:
    _, core = burst._exact_rva_span(pe, AVX_CORE_RVA, AVX_CORE_BYTES, AVX_CORE_SHA256)
    by_rva = {row.address - pe["imageBase"]: row for row in core}
    edges = (
        (0x28F1A1, "[rdi + r12 + 0x1c0]", 0x28F1AB, "[rsp + 0x868]", 0x29282E, 0x292837, "[rdi + 0x1c0]"),
        (0x28F1B4, "[rdi + r12 + 0x1e0]", 0x28F1BE, "[rsp + 0x888]", 0x29283F, 0x292848, "[rdi + 0x1e0]"),
        (0x28F1C7, "[rdi + r12 + 0x200]", 0x28F1D1, "[rsp + 0x8a8]", 0x292850, 0x292859, "[rdi + 0x200]"),
        (0x28F1E1, "[rdi + r12 + 0x220]", 0x28F1E9, "[rsp + 0x8c8]", 0x292861, 0x292869, "[rdi + 0x220]"),
        (0x28F1F1, "[rdi + r12 + 0x228]", 0x28F1F9, "[rsp + 0x8d0]", 0x292870, 0x292877, "[rdi + 0x228]"),
    )
    rows = []
    for load_rva, source, stack_write_rva, stack, stack_read_rva, store_rva, destination in edges:
        load = by_rva.get(load_rva)
        stack_write = by_rva.get(stack_write_rva)
        stack_read = by_rva.get(stack_read_rva)
        store = by_rva.get(store_rva)
        references = [row for row in core if stack in row.op_str]
        if (load is None or stack_write is None or stack_read is None or store is None
                or source not in load.op_str or stack not in stack_write.op_str
                or stack not in stack_read.op_str or destination not in store.op_str
                or [row.address - pe["imageBase"] for row in references] != [stack_write_rva, stack_read_rva]):
            raise ContractError(f"CalcCenter preserved-feed edge drift: {stack}")
        rows.append({"sourceCenterOffset": source.split("+")[-1].strip(" ]"),
                     "stackSlot": stack, "destinationCenterOffset": destination.split("+")[-1].strip(" ]"),
                     "loadRvas": [f"0x{load_rva:x}", f"0x{stack_write_rva:x}"],
                     "storeRvas": [f"0x{stack_read_rva:x}", f"0x{store_rva:x}"],
                     "stackReferenceCount": len(references)})
    smoothing_markers = {
        0x28F2B8: "[rdi + r12 + 0x22c]", 0x28F407: "[rdi + r10 + 0x234]",
        0x2913F8: "[rsp + 0xc0]", 0x29287D: "[rsp + 0xc0]",
    }
    for rva, marker in smoothing_markers.items():
        if rva not in by_rva or marker not in by_rva[rva].op_str:
            raise ContractError(f"CalcCenter smoothing write marker drift: 0x{rva:x}")
    return {
        "preservedRange": "CenterData+0x1c0..0x22b",
        "loadStoreOnlyChunks": rows,
        "proof": "Each private stack slot has exactly its one input load and one output store reference in the pinned 16,366-byte core, so no intervening CalcCenter instruction can alter these bytes.",
        "smoothingVelocityWrite": {"centerRange": "0x22c..0x237",
                                   "inputLoadRvas": ["0x28f2b8", "0x28f407"],
                                   "updatedStackStoreRva": "0x2913f8", "centerStoreRva": "0x29287d"},
    }


def _initial_buffers(flag: int, current: tuple[float, float, float], previous_component: tuple[float, float, float],
                     interpolation: float) -> list[Any]:
    sizes = [TEAM_STRIDE * 2, CENTER_STRIDE * 2, TEAM_WIND_STRIDE * 2, PARAMETER_STRIDE * 2,
             96, 64, 64, 16, 96, 64, 48, 212]
    buffers = [ctypes.create_string_buffer(size) for size in sizes]
    team, center, _wind, _parameters, _positions, rotations, bind_rotations, _fixed, transform_positions, transform_rotations, transform_scales, _wind_data = buffers
    to, co = TEAM_STRIDE, CENTER_STRIDE
    struct.pack_into("<Q", team, to, flag)
    struct.pack_into("<f", team, to + 0x3C, _f32(interpolation))
    struct.pack_into("<f", team, to + 0x40, 1.0)
    struct.pack_into("<3f", team, to + 0x54, 1.0, 1.0, 1.0)
    struct.pack_into("<f", team, to + 0x60, 1.0)
    for offset in (0x18, 0x40, 0x78, 0xB0, 0xD8, 0x110, 0x150, 0x188, 0x1B0, 0x1D4, 0x1F0):
        struct.pack_into("<4f", center, co + offset, 0.0, 0.0, 0.0, 1.0)
    for offset in (0x88, 0xC0, 0x120, 0x160):
        struct.pack_into("<3f", center, co + offset, 1.0, 1.0, 1.0)
    struct.pack_into("<3d", center, co + 0x98, *previous_component)
    for index in range(4):
        struct.pack_into("<d", center, co + 0x238 + (index * 4 + index) * 8, 1.0)
    struct.pack_into("<3d", transform_positions, 0, *current)
    struct.pack_into("<4f", transform_rotations, 0, 0.0, 0.0, 0.0, 1.0)
    struct.pack_into("<3f", transform_scales, 0, 1.0, 1.0, 1.0)
    struct.pack_into("<4f", rotations, 0, 0.0, 0.0, 0.0, 1.0)
    struct.pack_into("<4f", bind_rotations, 0, 0.0, 0.0, 0.0, 1.0)
    return buffers


def _selected(buffers: list[Any]) -> dict[str, str]:
    payload = {"team": bytes(buffers[0])[TEAM_STRIDE:TEAM_STRIDE * 2],
               "center": bytes(buffers[1])[CENTER_STRIDE:CENTER_STRIDE * 2]}
    return {name: payload[source][offset:offset + size].hex()
            for name, (source, offset, size) in SELECTED_FIELDS.items()}


def _source_vector(flag: int, current: tuple[float, float, float], previous_component: tuple[float, float, float],
                   interpolation: float) -> dict[str, str]:
    buffers = _initial_buffers(flag, current, previous_component, interpolation)
    team, center = buffers[0], buffers[1]
    to, co = TEAM_STRIDE, CENTER_STRIDE
    if (flag & ACTIVE_GATE_MASK) != ACTIVE_GATE_VALUE:
        return _selected(buffers)
    reset = bool(flag & 0x4)
    result_flag = flag | 0x40000
    if not reset:
        result_flag |= 0x400
    struct.pack_into("<Q", team, to, result_flag)
    bootstrap = not bool(flag & 0x400)
    if reset or bootstrap:
        struct.pack_into("<3d", center, co + 0x98, *current)
    shift = ((0.0, 0.0, 0.0) if reset or bootstrap else
             tuple(_f32(float(current[i]) - float(previous_component[i])) for i in range(3)))
    predicted = tuple(float(current[i]) + float(shift[i]) for i in range(3))
    for offset in (0x60, 0xF8, 0x198):
        struct.pack_into("<3d", center, co + offset, *current)
    struct.pack_into("<3f", center, co + 0xCC, *shift)
    target = current if reset or bootstrap else predicted
    struct.pack_into("<3d", center, co + 0x138, *target)
    struct.pack_into("<3d", center, co + 0x170, *target)
    return _selected(buffers)


def _native_vector(dll: Path, flag: int, current: tuple[float, float, float],
                   previous_component: tuple[float, float, float], interpolation: float) -> tuple[dict[str, str], bool]:
    buffers = _initial_buffers(flag, current, previous_component, interpolation)
    before_wind = bytes(buffers[2])
    module = ctypes.WinDLL(str(dll))
    fn = ctypes.CFUNCTYPE(None, ctypes.c_float, *([ctypes.c_void_p] * 11), ctypes.c_int,
                          ctypes.c_void_p, ctypes.c_int)(module._handle + AVX_CORE_RVA)
    fn(ctypes.c_float(_f32(1.0 / 90.0)), *(ctypes.addressof(row) for row in buffers[:11]),
       0, ctypes.addressof(buffers[11]), 1)
    return _selected(buffers), bytes(buffers[2]) == before_wind


def _fixed_buffers(fixed: list[int], rotation_mode: str = "planar") -> tuple[list[Any], list[tuple[float, float, float]],
                                                list[tuple[float, float, float, float]],
                                                list[tuple[float, float, float, float]]]:
    buffers = _initial_buffers(0x22, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0)
    length = max(fixed) + 1
    positions = [(float(i + 1), float(2 * i), float(-i)) for i in range(length)]
    rotations = []
    binds = []
    for i in range(length):
        angle = _f32((30.0 + (i % 12) * 5.0) * 0.008726646259971648)
        planar = (0.0, 0.0, _f32(math.sin(angle)), _f32(math.cos(angle)))
        bind_angle = _f32(10.0 * 0.008726646259971648)
        planar_bind = (0.0, 0.0, _f32(math.sin(bind_angle)), _f32(math.cos(bind_angle)))
        if rotation_mode == "planar":
            rotations.append(planar)
            binds.append(planar_bind)
        elif rotation_mode == "spatial":
            x_angle = _f32((7.0 + (i % 5) * 3.0) * 0.008726646259971648)
            y_angle = _f32((-11.0 + (i % 7) * 2.0) * 0.008726646259971648)
            qx = (_f32(math.sin(x_angle)), 0.0, 0.0, _f32(math.cos(x_angle)))
            qy = (0.0, _f32(math.sin(y_angle)), 0.0, _f32(math.cos(y_angle)))
            rotations.append(_qmul(_qmul(planar, qy), qx))
            binds.append(_qmul(planar_bind, qx))
        else:
            raise ContractError(f"unsupported fixed rotation mode: {rotation_mode}")
    buffers[4] = ctypes.create_string_buffer(24 * length)
    buffers[5] = ctypes.create_string_buffer(16 * length)
    buffers[6] = ctypes.create_string_buffer(16 * length)
    buffers[7] = ctypes.create_string_buffer(2 * len(fixed))
    for i in range(length):
        struct.pack_into("<3d", buffers[4], i * 24, *positions[i])
        struct.pack_into("<4f", buffers[5], i * 16, *rotations[i])
        struct.pack_into("<4f", buffers[6], i * 16, *binds[i])
    for i, index in enumerate(fixed):
        struct.pack_into("<H", buffers[7], i * 2, index)
    struct.pack_into("<ii", buffers[0], TEAM_STRIDE + 0x16C, 0, len(fixed))
    return buffers, positions, rotations, binds


def _fixed_source_selected(fixed: list[int], rotation_mode: str = "planar") -> dict[str, str]:
    buffers, positions, rotations, binds = _fixed_buffers(fixed, rotation_mode)
    center_position, center_rotation = _aggregate_fixed(positions, rotations, binds, fixed)
    team, center = buffers[0], buffers[1]
    struct.pack_into("<Q", team, TEAM_STRIDE, 0x40422)
    for offset in (0xF8, 0x138, 0x170, 0x198):
        struct.pack_into("<3d", center, CENTER_STRIDE + offset, *center_position)
    for offset in (0x110, 0x150, 0x188, 0x1B0):
        struct.pack_into("<4f", center, CENTER_STRIDE + offset, *center_rotation)
    selected = _selected(buffers)
    return {field: selected[field] for field in TARGET_FIXED_CERTIFIED_FIELDS}


def _fixed_native_selected(dll: Path, fixed: list[int], rotation_mode: str = "planar") -> tuple[dict[str, str], bool]:
    buffers, _positions, _rotations, _binds = _fixed_buffers(fixed, rotation_mode)
    before_wind = bytes(buffers[2])
    module = ctypes.WinDLL(str(dll))
    fn = ctypes.CFUNCTYPE(None, ctypes.c_float, *([ctypes.c_void_p] * 11), ctypes.c_int,
                          ctypes.c_void_p, ctypes.c_int)(module._handle + AVX_CORE_RVA)
    fn(ctypes.c_float(_f32(1.0 / 90.0)), *(ctypes.addressof(row) for row in buffers[:11]),
       0, ctypes.addressof(buffers[11]), 1)
    selected = _selected(buffers)
    observed = dict.fromkeys(FIXED_AGGREGATION_FIELDS + ("team.gravityRatio", "team.scaleRatio"))
    return ({field: selected[field] for field in observed},
            bytes(buffers[2]) == before_wind)


def _write_inertia_parameters(buffer: Any, *, world: float, smoothing: float,
                              local: float, depth: float) -> None:
    offset = PARAMETER_STRIDE + 0xB4
    values = (0.0, world, smoothing, -1.0, -1.0, local, -1.0, -1.0,
              depth, 0.0, -1.0, 0, 1000.0, 1000.0)
    struct.pack_into("<11fI2f", buffer, offset, *values)


def _write_feed_sentinels(center: Any) -> None:
    offset = CENTER_STRIDE
    struct.pack_into("<2f", center, offset + 0x1C0, 0.125, 0.25)
    struct.pack_into("<3f", center, offset + 0x1C8, 1.25, -2.5, 3.75)
    struct.pack_into("<4f", center, offset + 0x1D4, 0.1, -0.2, 0.3, 0.9)
    struct.pack_into("<3f", center, offset + 0x1E4, -4.5, 5.25, -6.0)
    struct.pack_into("<4f", center, offset + 0x1F0, -0.4, 0.5, -0.6, 0.7)
    struct.pack_into("<f3ff3f", center, offset + 0x200,
                     7.5, 0.25, -0.5, 0.75, 8.25, -0.125, 0.375, -0.625)
    struct.pack_into("<3f", center, offset + 0x220, 0.2, -0.3, 0.4)
    struct.pack_into("<3f", center, offset + 0x22C, 9.0, -10.0, 11.0)


def _zero_target_smoothing_step(old: tuple[float, float, float], smoothing: float) -> tuple[float, float, float]:
    base = _f32(1.0 - _f32(smoothing))
    blend = _f32(_f32(_f32(math.pow(base, _f32(3.0))) * _f32(0.99)) + _f32(0.01))
    blend = min(1.0, max(0.0, blend))
    return tuple(_f32(old[i] + _f32(blend * _f32(0.0 - old[i]))) for i in range(3))  # type: ignore[return-value]


def _native_target_motion_vector(dll: Path, owner: str, second_flag: int = 0x8022) -> dict[str, Any]:
    facts = ENDMINF_FIXED[owner]
    fixed = facts["fixed"]
    buffers, positions, rotations, _binds = _fixed_buffers(fixed)
    cloth = next(row for row in json.loads(SOLVER_INPUTS.read_text(encoding="utf-8"))["actors"]["endminf"]["cloths"]
                 if row["game_object_path"] == owner)
    inertia = cloth["serialized_data"]["inertiaConstraint"]
    struct.pack_into("<Q", buffers[0], TEAM_STRIDE, 0x8022)
    struct.pack_into("<f", buffers[0], TEAM_STRIDE + 0x10, _f32(1.0 / 60.0))
    struct.pack_into("<2fI", buffers[0], TEAM_STRIDE + 0x2C, 1.0, 1.0, 1)
    _write_inertia_parameters(buffers[3], world=float(inertia["worldInertia"]),
                              smoothing=float(inertia["movementInertiaSmoothing"]),
                              local=float(inertia["localInertia"]), depth=float(inertia["depthInertia"]))
    _write_feed_sentinels(buffers[1])
    sentinels = {field: _selected(buffers)[field] for field in PRESERVED_SIMULATION_FEED_FIELDS}
    before_wind = bytes(buffers[2])
    module = ctypes.WinDLL(str(dll))
    fn = ctypes.CFUNCTYPE(None, ctypes.c_float, *([ctypes.c_void_p] * 11), ctypes.c_int,
                          ctypes.c_void_p, ctypes.c_int)(module._handle + AVX_CORE_RVA)
    args = lambda: (*(ctypes.addressof(row) for row in buffers[:11]),
                    0, ctypes.addressof(buffers[11]), 1)
    fn(ctypes.c_float(_f32(1.0 / 90.0)), *args())
    before = _selected(buffers)
    first_expected_smoothing = _zero_target_smoothing_step((9.0, -10.0, 11.0),
                                                            float(inertia["movementInertiaSmoothing"]))
    struct.pack_into("<Q", buffers[0], TEAM_STRIDE, second_flag)
    for ordinal, index in enumerate(fixed):
        p = positions[index]
        moved = (p[0] + 0.004 * (ordinal + 1), p[1] - 0.002 * ordinal,
                 p[2] + 0.001 * (ordinal & 1))
        struct.pack_into("<3d", buffers[4], index * 24, *moved)
        angle = _f32((34.0 + (index % 12) * 5.0 + ordinal * 1.25) * 0.008726646259971648)
        struct.pack_into("<4f", buffers[5], index * 16, 0.0, 0.0,
                         _f32(math.sin(angle)), _f32(math.cos(angle)))
    fn(ctypes.c_float(_f32(1.0 / 90.0)), *args())
    after = _selected(buffers)
    second_expected_smoothing = _zero_target_smoothing_step(first_expected_smoothing,
                                                             float(inertia["movementInertiaSmoothing"]))
    smoothing_matches = {
        "bootstrap": before["center.smoothingVelocity"] == struct.pack("<3f", *first_expected_smoothing).hex(),
        "animatedStep": after["center.smoothingVelocity"] == struct.pack("<3f", *second_expected_smoothing).hex(),
    }
    if not all(smoothing_matches.values()):
        raise ContractError(f"zero-root smoothing mismatch: {owner}: {smoothing_matches}")
    preserved = {field: before[field] == sentinels[field] == after[field]
                 for field in PRESERVED_SIMULATION_FEED_FIELDS}
    if not all(preserved.values()):
        raise ContractError(f"CalcCenter feed preservation drift: {owner}: "
                            f"{[field for field, matched in preserved.items() if not matched]}")
    if before["center.frameWorldPosition"] == after["center.frameWorldPosition"]:
        raise ContractError(f"animated fixed-center control did not move: {owner}")
    if bytes(buffers[2]) != before_wind:
        raise ContractError(f"zero-wind TeamWindData changed: {owner}")
    return {
        "name": f"endminf_{owner.lower()}_animated_fixed_step",
        "owner": owner,
        "inputs": {"simulationDeltaTimeF32": _f32(1.0 / 90.0), "fixedArrayUInt16": fixed,
                   "worldInertiaF32": _f32(float(inertia["worldInertia"])),
                   "movementInertiaSmoothingF32": _f32(float(inertia["movementInertiaSmoothing"])),
                   "localInertiaF32": _f32(float(inertia["localInertia"])),
                   "depthInertiaF32": _f32(float(inertia["depthInertia"])),
                   "centrifugalAccelerationF32": 0.0, "windZoneCount": 0},
        "bootstrapOutputs": before,
        "animatedStepOutputs": after,
        "preservedSimulationFeedFields": preserved,
        "zeroRootSmoothingNativeSourceBitExact": smoothing_matches,
        "teamWindElementUnchanged": True,
    }


def _fixed_golden_vectors(dll: Path) -> list[dict[str, Any]]:
    vectors = []
    cases = [(owner, facts, "planar") for owner, facts in ENDMINF_FIXED.items()]
    cases += [(owner, ENDMINF_FIXED[owner], "spatial")
              for owner in ("MC_Hair", "MC_Ribbon", "MC_Coat")]
    for owner, facts, rotation_mode in cases:
        fixed = facts["fixed"]
        native, wind_unchanged = _fixed_native_selected(dll, fixed, rotation_mode)
        source = _fixed_source_selected(fixed, rotation_mode)
        compared = TARGET_FIXED_CERTIFIED_FIELDS
        matches = {field: native[field] == source[field] for field in compared}
        if not all(matches.values()) or not wind_unchanged:
            bad = [field for field, matched in matches.items() if not matched]
            raise ContractError(f"fixed-center vector mismatch: {owner}: {bad}; windUnchanged={wind_unchanged}")
        vectors.append({
            "name": f"endminf_{owner.lower()}_fixed_center_{rotation_mode}_bootstrap",
            "owner": owner,
            "inputs": {"fixedDataChunk": {"startIndexI32": 0, "dataLengthI32": len(fixed)},
                       "fixedArrayUInt16": fixed, "windZoneCount": 0,
                       "syntheticPositionFormulaF64": "position[i] = (i+1, 2*i, -i)",
                       "syntheticRotationFormulaF32": ("rotation[i] = qz(30 + 5*(i mod 12) degrees)" if rotation_mode == "planar"
                                                        else "rotation[i] = (qz * qy) * qx with index-varying axes"),
                       "bindPoseRotations": ("qz(10 degrees)" if rotation_mode == "planar"
                                             else "qz(10 degrees) * index-varying qx")},
            "selectedNativeOutputs": native, "nativeSourceBitExact": matches,
            "rotationComparisonBoundary": "all published center quaternions are source-certified raw-byte exact",
            "teamWindElementUnchanged": wind_unchanged,
        })
    return vectors


def _endminf_fixed_facts(cloths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    by_owner = {row["game_object_path"]: row for row in cloths}
    if set(by_owner) != set(ENDMINF_FIXED):
        raise ContractError("Endminf cloth owner set drift")
    for owner, expected in ENDMINF_FIXED.items():
        cloth = by_owner[owner]
        proxy = cloth["solver_input"]["prebuild_data"]["preBuildData"]["proxyMesh"]
        actual = {"fixed": proxy["centerFixedList"], "centerTransformIndex": proxy["centerTransformIndex"]}
        if actual != expected:
            raise ContractError(f"Endminf fixed-center source drift: {owner}: {actual}")
        inertia = cloth["serialized_data"]["inertiaConstraint"]
        rows.append({"owner": owner, "fixedArrayUInt16": actual["fixed"],
                     "fixedCount": len(actual["fixed"]),
                     "centerTransformIndex": actual["centerTransformIndex"],
                     "centerTransformRelationship": "identity child of actor root (capture target fact)",
                     "authoredInertia": {key: inertia[key] for key in (
                         "anchorInertia", "worldInertia", "movementInertiaSmoothing", "localInertia",
                         "depthInertia", "teleportMode", "teleportDistance", "teleportRotation")},
                     "gravity": cloth["serialized_data"]["gravity"],
                     "gravityFalloff": cloth["serialized_data"]["gravityFalloff"]})
    return rows


def _golden_vectors(dll: Path) -> list[dict[str, Any]]:
    cases = (
        ("disabled_bypass", 0x0, (1.0, 2.0, 3.0), (0.25, 0.5, 0.75), 0.5),
        ("active_steady_identity", 0x22, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0),
        ("active_bootstrap_translation_half_phase", 0x22, (0.01, -0.02, 0.03), (0.0, 0.0, 0.0), 0.5),
        ("active_reset_direct_translation", 0x26, (1.0, -2.0, 3.0), (0.25, 0.5, -0.75), 0.25),
    )
    vectors = []
    for name, flag, current, previous, interpolation in cases:
        native, wind_unchanged = _native_vector(dll, flag, current, previous, interpolation)
        source = _source_vector(flag, current, previous, interpolation)
        matches = {field: native[field] == source[field] for field in SELECTED_FIELDS}
        if not all(matches.values()) or not wind_unchanged:
            bad = [field for field, value in matches.items() if not value]
            raise ContractError(f"no-wind center vector mismatch: {name}: {bad}; windUnchanged={wind_unchanged}")
        vectors.append({"name": name, "inputs": {"flag": f"0x{flag:x}", "currentComponentPositionF64": list(current),
                                                   "oldComponentPositionF64": list(previous),
                                                   "frameInterpolationF32": _f32(interpolation), "windZoneCount": 0},
                        "selectedOutputs": native, "nativeSourceBitExact": matches,
                        "teamWindElementUnchanged": wind_unchanged})
    return vectors


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    game_path = Path(gate["gameAssembly"]["path"])
    metadata_path = Path(gate["globalMetadata"]["path"])
    dll_path = Path(gate["libBurstGenerated"]["path"])
    layout = _source_payload(ELEMENT_LAYOUT, "endfield.charinfo.secondary-dynamics-element-layout.v1")
    callback = _source_payload(CALLBACK_CONTRACT, "endfield.charinfo.secondary-dynamics-callback-writeback.v1")
    substep = _source_payload(SUBSTEP_CONTRACT, "endfield.charinfo.secondary-dynamics-substep.v1",
                              "pinned_unpatched_substep_accumulator_count_and_solver_loop_closed")
    if "SimulationStepTeamUpdate" not in json.dumps(substep, separators=(",", ":")):
        raise ContractError("substep contract no longer identifies SimulationStepTeamUpdate")
    solver = json.loads(SOLVER_INPUTS.read_text(encoding="utf-8"))
    center_layout = next(row for row in layout["elements"] if row["name"].endswith("+CenterData"))
    team_layout = next(row for row in layout["elements"] if row["name"].endswith("+TeamData"))
    if (center_layout["nativeSizeBytes"], team_layout["nativeSizeBytes"]) != (CENTER_STRIDE, TEAM_STRIDE):
        raise ContractError("CenterData/TeamData stride drift")
    calls = callback.get("writeback", {}).get("criticalCalls", [])
    names = [row.get("method") for row in calls]
    required = ["PreProxyMeshUpdate", "CalcCenterAndInertiaAndWind", "PreSimulationUpdate"]
    positions = [names.index(name) for name in required]
    if positions != sorted(positions):
        raise ContractError("pre-simulation center scheduling order drift")
    cloths = solver["actors"]["endminf"]["cloths"]
    fixed_facts = _endminf_fixed_facts(cloths)
    moving_wind = sorted({float(row["serialized_data"]["wind"]["movingWind"]) for row in cloths})
    if moving_wind != [0.0]:
        raise ContractError(f"Endminf moving-wind source drift: {moving_wind}")
    pe = burst._pe_exports(dll_path)
    vectors = _golden_vectors(dll_path)
    fixed_vectors = _fixed_golden_vectors(dll_path)
    target_motion_vectors = [_native_target_motion_vector(dll_path, owner)
                             for owner in ("MC_Hair", "MC_Coat")]
    return {
        "schema": "endfield.charinfo.secondary-dynamics-center-update.v1",
        "status": "no_wind_fixed_center_rotation_and_zero_root_smoothing_closed_downstream_step_inertia_fail_closed",
        "nativeGate": gate,
        "sources": [_file(ELEMENT_LAYOUT), _file(CALLBACK_CONTRACT), _file(SUBSTEP_CONTRACT), _file(SOLVER_INPUTS)],
        "managedMethods": _managed_rows(game_path, metadata_path),
        "burstIdentity": _burst_identity(pe),
        "simulationFeedWriteOwnership": _simulation_feed_write_ownership(pe),
        "schedule": {
            "order": ["VirtualMeshManager.PreProxyMeshUpdate", "TeamManager.CalcCenterAndInertiaAndWind",
                      "SimulationManager.PreSimulationUpdate", "SimulationManager.SimulationStepUpdate"],
            "job": "CalcCenterAndInertiaAndWindJob is populated once and scheduled over team ids; its range path calls the pinned Burst range kernel.",
            "jobPayloadOffsets": {"simulationDeltaTime": "0x0", "teamDataArray": "0x8", "centerDataArray": "0x18",
                                  "teamWindArray": "0x28", "parameterArray": "0x38", "positions": "0x48",
                                  "rotations": "0x58", "vertexBindPoseRotations": "0x68", "fixedArray": "0x78",
                                  "transformPositionArray": "0x88", "transformRotationArray": "0x98",
                                  "transformScaleArray": "0xa8", "windZoneCount": "0xb8",
                                  "windDataArray": "0xc0", "_indexCount": "0xd0"},
        },
        "fieldAndArrayProvenance": {
            "teamManagerFields": {"teamDataArray": "manager+0x10", "teamWindArray": "manager+0x18",
                                  "parameterArray": "manager+0x40", "centerDataArray": "manager+0x48"},
            "elementStridesBytes": {"TeamData": TEAM_STRIDE, "CenterData": CENTER_STRIDE,
                                    "TeamWindData": TEAM_WIND_STRIDE, "ClothParameters": PARAMETER_STRIDE},
            "transformInputs": "current transform position/rotation/scale arrays produced by the transform-read phase; CenterData.centerTransformIndex selects the center transform",
            "fixedCenterInputs": {"fixedDataChunk": {"TeamData.startIndex": "team+0x16c:i32",
                                                       "TeamData.dataLength": "team+0x170:i32"},
                                  "fixedArray": "UInt16 proxy-common vertex indices",
                                  "positions": "float64 x3 proxy-common positions",
                                  "rotations": "float32 x4 proxy-common rotations",
                                  "vertexBindPoseRotations": "float32 x4 proxy-common bind rotations"},
            "teamClock": substep["perTeamAccumulator"],
            "solverInterpolation": substep["solverLoop"]["perExecutedTeamStep"],
            "simulationFeedOwnership": "The pinned CalcCenter AVX2 core copies CenterData 0x1c0..0x22b from input to output without an intervening write. The pinned substep contract separately schedules TeamManager.SimulationStepTeamUpdate before each solver step; its equations are the remaining owner-recovery target.",
        },
        "exactClosedEquations": {
            "activeGate": "execute iff (TeamData.flag & 0x2000000000080812) == 0x2; otherwise no selected TeamData, CenterData, or TeamWindData byte changes",
            "selectedTranslationDomain": [
                "componentWorldPosition_f64 = transformPositionArray[centerTransformIndex]",
                "after InertiaShift bootstrap: frameComponentShiftVector_f32 = f32(componentWorldPosition - oldComponentWorldPosition); bootstrap/reset instead copy current to oldComponentWorldPosition and publish zero shift",
                "frameWorldPosition_f64 = componentWorldPosition",
                "without reset: predicted_f64 = componentWorldPosition + f64(frameComponentShiftVector_f32); oldFrameWorldPosition = nowWorldPosition = predicted_f64; oldWorldPosition = componentWorldPosition",
                "with Flag_Reset (0x4): frameComponentShiftVector = float3(0); oldFrameWorldPosition = nowWorldPosition = oldWorldPosition = componentWorldPosition",
                "this stage preserves TeamData.frameInterpolation; per-step interpolation is performed later by SimulationStepTeamUpdate as pinned in the substep contract",
            ],
            "fixedCenterAggregation": [
                "iterate fixedArray[fixedDataChunk.startIndex .. startIndex+dataLength) in stored UInt16 order",
                "frameWorldPosition_f64 = sequential sum(positions[fixedIndex]) / f64(dataLength)",
                "relativeRotation = the AVX2 lane-ordered Hamilton product rotations[fixedIndex] * vertexBindPoseRotations[fixedIndex] (not conjugate(bind))",
                "for every relativeRotation, accumulate its rotated up=(0,1,0) and forward=(0,0,1) vectors in fixed UInt16 order with binary32 adds",
                "normalize forward and up independently; right = normalize(cross(up, forward)); correctedUp = cross(forward, right)",
                "frameWorldRotation = Unity.Mathematics quaternion(float3x3(right, correctedUp, forward)): apply the u_sign/t_sign mask/select construction, then normalize the selected float4 with AVX binary32 horizontal order",
                "the transcription is raw-byte exact for planar 1/8/4/9 vectors and independent spatial 8/4/9 vectors, covering all target multi-fixed cardinalities",
                "on bootstrap, oldFrameWorld/nowWorld/oldWorld position receive the aggregated frame position",
            ],
            "calcCenterSimulationFeedPreservation": [
                "CalcCenterAndInertiaAndWind preserves CenterData byte range 0x1c0..0x22b: stepMoveInertiaRatio, stepRotationInertiaRatio, stepVector, stepRotation, inertiaVector, inertiaRotation, stepMovingSpeed, stepMovingDirection, angularVelocity, rotationAxis, and initLocalGravityDirection",
                "Hair(depthInertia=1.0, worldInertia=1.0, localInertia=1.0, smoothing=0.4) and Coat(depthInertia=0.7, worldInertia=0.5, localInertia=0.8, smoothing=0.4) controlled vectors move and rotate the fixed center while distinct finite sentinels in every named preserved field remain raw-byte unchanged",
                "smoothingVelocity at 0x22c..0x237 is updated by this core and is treated separately; direct production of step/inertia/angular fields by CalcCenter is rejected",
            ],
            "zeroRootMovementSmoothing": [
                "target component velocity is float3(0) because the actor/component root is stationary and frameComponentShiftVector is exactly zero in both overview clips",
                "base = f32(1 - movementInertiaSmoothing)",
                "blend = saturate(f32(f32(pow_f32(base, 3.0f) * 0.99f) + 0.01f))",
                "smoothingVelocity_next = f32(smoothingVelocity_old + f32(blend * f32(float3(0) - smoothingVelocity_old))) lane-wise",
                "for Endminf movementInertiaSmoothing=0.4f, blend=0.22384002804756165 and the retained old-velocity factor is 0.7761599719524384",
                "Hair and Coat two-step sentinel vectors match native bytes exactly; depthInertia does not enter this root-velocity smoothing branch",
            ],
            "generalRotationPublication": [
                "frameComponentShiftRotation is the normalized component delta from oldComponentWorldRotation to componentWorldRotation",
                "non-bootstrap predicted center rotation multiplication order is frameComponentShiftRotation * frameWorldRotation (Hamilton xyzw); a native cross-axis qx(30 degree) actor delta and qy(40 degree) fixed center produced xyzw (0.2432103008,0.3303660452,0.08852131665,0.9076731801)",
                "oldFrameWorldRotation and nowWorldRotation receive that predicted rotation; oldWorldRotation receives the unpredicted aggregated frameWorldRotation",
                "the exact AVX2 normalization/rounding sequence for component delta remains outside the source-bit-exact boundary",
            ],
            "endminfTargetRatios": [
                "actor root world transform and all identity-child MC_* center transforms have unit scale, so scaleRatio_f32 remains 1.0",
                "actor/component rotation is identity and the target gravity direction remains aligned with its initialized direction, so gravityRatio_f32 remains 1.0",
                "both constants are compared as raw native/source bytes in every fixed-center cardinality vector; rotated-gravity and nonuniform/negative-scale equations are not generalized",
            ],
            "widths": {"transform and center world positions": "float64 x3", "component shift and scale": "float32",
                       "quaternions": "float32 x4", "team time/ratios/interpolation": "float32", "flags": "uint64"},
            "stageFlagsInSelectedDomain": "the stage sets NegativeScaleTeleport (0x40000); non-reset selected vectors also set InertiaShift (0x400)",
        },
        "endminfNoWindDomain": {
            "clothOwners": [row["game_object_path"] for row in cloths],
            "authoredMovingWindValues": moving_wind,
            "requiredRuntimeWindZoneCount": 0,
            "teamWindExpectation": "the complete 152-byte selected TeamWindData element is unchanged",
            "fixedCenters": fixed_facts,
            "centerTransformCaptureFact": "MC_Ribbon2, MC_Hair, MC_Ribbon, and MC_Coat are identity children of the actor root; generally they inherit actor-root translation/rotation, but the pinned target proof below makes that inherited delta a no-op for this segment.",
            "overviewRootMotionTargetProof": {
                "recoveredClipCount": 2,
                "bothClips": {"hasRootCurves": False, "hasMotionCurves": False,
                              "averageSpeed": [0.0, 0.0, 0.0], "averageAngularSpeed": 0.0},
                "actorRootWorldTransform": "identity and stationary for the target lab segment",
                "centerTransforms": "all four MC_* transforms are identity children of actor root",
                "classification": "target-closed no-op: component translation delta is float3(0), component rotation delta is identity, and root-motion contributions to center linear/angular velocity are zero",
                "boundary": "internally animated fixed vertices remain live and may move/rotate the aggregated frame center; this proof does not zero resulting center inertia",
                "provenance": "target proof supplied from the two recovered Animator clip reports and lab hierarchy; this contract does not generalize it beyond Endminf ui_overview_start/loop",
            },
        },
        "goldenVectors": vectors,
        "fixedCenterGoldenVectors": fixed_vectors,
        "targetMotionGoldenVectors": target_motion_vectors,
        "verification": {"nativeAvx2CoreExecuted": True, "sourceInvokesNativeHelpers": False,
                         "selectedFieldCount": len(SELECTED_FIELDS),
                         "vectorCount": len(vectors) + len(fixed_vectors) + len(target_motion_vectors),
                         "fixedCenterVectorCounts": [len(row["fixedArrayUInt16"]) for row in fixed_facts],
                         "multiFixedSpatialVectorCounts": [8, 4, 9],
                         "allCertifiedOutputsComparedAsRawBytes": True,
                         "calcPreservedFeedFieldCount": len(PRESERVED_SIMULATION_FEED_FIELDS),
                         "zeroRootSmoothingVectorOwners": ["MC_Hair", "MC_Coat"],
                         "observedButUncertifiedOutputsPresent": True},
        "failClosedBoundary": {
            "runtimeFeedReady": False,
            "closed": ["native schedule and ABI", "active/bypass gate", "array/field provenance",
                       "team clock and per-step frame interpolation ownership", "zero-wind proof",
                       "identity quaternion and translational bootstrap/reset/prediction publication subset",
                       "Endminf fixed UInt16 lists/counts and fixed-center float64 position mean",
                       "fixed-center quaternion reduction, operation order, basis normalization, and matrix-to-quaternion conversion for target counts 1/8/4/9",
                       "general noncommutative actor-delta * fixed-center rotation multiplication order",
                       "Endminf overview root-motion/component delta as target no-op",
                       "Endminf target gravityRatio=1.0f and scaleRatio=1.0f under identity rotation/unit scale",
                       "CalcCenter raw-byte preservation (not production) of CenterData step/inertia/angular feed fields through initLocalGravityDirection",
                       "target zero-root smoothingVelocity update for Hair and Coat"],
            "unresolved": [
                "target-active center angularVelocity/rotationAxis and step/inertiaVector/inertiaRotation smoothing equations belong to the separately scheduled SimulationStepTeamUpdate kernel, not this CalcCenter core, and remain unrecovered",
                "the exact TeamData/CenterData inputs and flag lifecycle presented to SimulationStepTeamUpdate for the 1/2-step 90 Hz-on-60 Hz target cadence",
                "off-target anchor/world/local inertia speed clamps, teleport-keep, and negative-scale matrix branches",
                "off-target gravityRatio/gravityDot updates for rotated gravity and nonuniform/negative scaleRatio equations",
                "empty fixed-center range behavior and any nonzero wind-zone or moving-wind state",
                "the IFix-patched route and retail runtime resolver telemetry",
            ],
            "rule": "Consumers must reject this contract as a complete Simulation Start feed until SimulationStepTeamUpdate is separately recovered. CalcCenter's proven behavior for those fields is preservation, not production.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_contract()
        encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == encoded
            print(json.dumps({"status": payload["status"], "matches": matches,
                              "validationFailures": [] if matches else ["generated contract drift"]}))
            return 0 if matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
        print(json.dumps({"status": payload["status"], "output": str(args.output),
                          "vectors": payload["verification"]["vectorCount"]}))
        return 0
    except (OSError, ValueError, KeyError, IndexError, struct.error, ContractError, burst.ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
