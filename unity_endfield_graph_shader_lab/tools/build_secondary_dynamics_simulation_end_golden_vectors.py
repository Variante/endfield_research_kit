#!/usr/bin/env python3
"""Execute bounded Simulation End paths in the pinned AVX2 core."""

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
    "secondary_dynamics_simulation_end_golden_vectors.json"
)
CORE_RVA = 0x24FA60
CORE_BYTES = 1745
CORE_SHA256 = "f623b3ca9c367210ca74998645797c72cefa6d393d708f8665788b85aba41780"
CASES = (
    {"name": "inactive_bypass", "active": False, "limit": -1.0},
    {"name": "active_unlimited", "active": True, "limit": -1.0},
    {"name": "active_speed_limit", "active": True, "limit": 2.0},
)


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _hex(values: tuple[float, ...], code: str) -> list[str]:
    return [struct.pack("<" + code, value).hex() for value in values]


def source_port(case: dict[str, Any]) -> dict[str, tuple[float, ...]]:
    next_pos = (2.0, 3.0, 4.0)
    old_pos = (1.0, 1.0, 1.0)
    velocity_pos = (1.0, 1.0, 1.0)
    dt = float(_f32(0.5))
    real_velocity = tuple(_f32((p - old) / dt) for p, old in zip(next_pos, old_pos))
    if not case["active"]:
        velocity = (0.0, 0.0, 0.0)
    else:
        candidate = tuple((p - vp) / dt for p, vp in zip(next_pos, velocity_pos))
        limit = float(_f32(case["limit"]))
        length = math.sqrt(sum(component * component for component in candidate))
        if limit >= 0.0 and length > limit and length > 9.999999717180685e-10:
            candidate = tuple(component * (limit / length) for component in candidate)
        velocity = tuple(_f32(component) for component in candidate)
    return {"velocity": velocity, "realVelocity": real_velocity, "oldPos": next_pos}


def _run_native(dll: Path, case: dict[str, Any]) -> dict[str, tuple[float, ...]]:
    module = ctypes.WinDLL(str(dll))
    function = ctypes.CFUNCTYPE(
        None, ctypes.c_float, *([ctypes.c_void_p] * 15), ctypes.c_int
    )(module._handle + CORE_RVA)
    # The range wrapper reorders the three state arrays after oldPos to the
    # core's float3 velocity, float3 realVelocity, double3 velocityPos ABI.
    sizes = [4, 464, 808, 696, 1, 4, 2, 24, 24, 12, 12, 24, 4, 4, 12]
    buffers = [ctypes.create_string_buffer(size) for size in sizes]
    (step, team, parameters, _center, attributes, _depth, team_ids,
     next_pos, old_pos, velocity, real_velocity, velocity_pos,
     _friction, _static_friction, _normal) = buffers
    struct.pack_into("<i", step, 0, 0)
    struct.pack_into("<i", team, 0x124, 0)
    struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<f", team, 0x60, 1.0)
    struct.pack_into("<f", team, 0xFC, 1.0)
    struct.pack_into("<f", parameters, 0xDC, case["limit"])
    struct.pack_into("<B", attributes, 0, 2 if case["active"] else 0)
    struct.pack_into("<h", team_ids, 0, 0)
    struct.pack_into("<3d", next_pos, 0, 2.0, 3.0, 4.0)
    struct.pack_into("<3d", old_pos, 0, 1.0, 1.0, 1.0)
    struct.pack_into("<3d", velocity_pos, 0, 1.0, 1.0, 1.0)
    function(
        ctypes.c_float(0.5),
        *(ctypes.addressof(buffer) for buffer in buffers),
        ctypes.c_int(0),
    )
    return {
        "velocity": struct.unpack_from("<3f", velocity),
        "realVelocity": struct.unpack_from("<3f", real_velocity),
        "oldPos": struct.unpack_from("<3d", old_pos),
    }


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    vectors = []
    for case in CASES:
        native = _run_native(dll, case)
        port = source_port(case)
        if (_hex(native["velocity"], "f") != _hex(port["velocity"], "f") or
                _hex(native["realVelocity"], "f") != _hex(port["realVelocity"], "f") or
                _hex(native["oldPos"], "d") != _hex(port["oldPos"], "d")):
            raise burst.ContractError(f"source Simulation End transcription differs: {case['name']}")
        vectors.append({
            "name": case["name"],
            "input": {"active": case["active"], "particleSpeedLimitFloat32": _f32(case["limit"])},
            "output": {
                "velocity": list(native["velocity"]),
                "velocityBinary32Le": _hex(native["velocity"], "f"),
                "realVelocity": list(native["realVelocity"]),
                "realVelocityBinary32Le": _hex(native["realVelocity"], "f"),
                "oldPos": list(native["oldPos"]),
                "oldPosBinary64Le": _hex(native["oldPos"], "d"),
            },
        })
    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-end-golden-vectors.v1",
        "status": "native_avx2_bypass_base_velocity_and_speed_limit_vectors_exact",
        "nativeGate": gate,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES, "sha256": CORE_SHA256},
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": vectors,
        "boundary": {
            "nativeCoreExecuted": True,
            "sourceTranscriptionMatched": True,
            "covered": ["inactive bypass", "active base velocity", "particle speed limit"],
            "notCovered": ["static friction", "dynamic friction", "centrifugal response"],
            "completeKernelGoldenCoverage": False,
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
            raise SystemExit("Simulation End golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
