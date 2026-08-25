#!/usr/bin/env python3
"""Execute the pinned Burst tether core and publish deterministic golden vectors."""

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
    "secondary_dynamics_tether_golden_vectors.json"
)
CORE_RVA = 0x29F7D0
CORE_BYTES = 648
CORE_SHA256 = "39f9eb3cd9771cbd921c9091d3821fedd510b1efc9b86161713a9010fd2c7b4a"
CASES = (
    ("stretch_full_axis", (2.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.1, 0.1),
    ("compression_full_axis", (0.5, 0.0, 0.0), (1.0, 0.0, 0.0), 0.1, 0.1),
    ("dead_zone", (1.05, 0.0, 0.0), (1.0, 0.0, 0.0), 0.1, 0.1),
    ("stretch_partial", (1.2, 0.0, 0.0), (1.0, 0.0, 0.0), 0.1, 0.1),
    ("stretch_full_oblique", (2.0, 1.0, -0.5), (1.0, 0.5, -0.25), 0.1, 0.1),
)


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _hex3(values: tuple[float, float, float]) -> list[str]:
    return [struct.pack("<d", value).hex() for value in values]


def source_port(case: tuple[str, tuple[float, float, float], tuple[float, float, float], float, float]) -> dict[str, Any]:
    _, current, basic, compression, stretch = case
    current_length = math.sqrt(sum(value * value for value in current))
    basic_length = math.sqrt(sum(value * value for value in basic))
    next_result = list(current)
    velocity_result = list(current)
    if current_length >= 9.99999993922529e-9 and basic_length != 0.0:
        ratio = current_length / basic_length
        compression_threshold = float(_f32(_f32(1.0) - _f32(compression)))
        stretch_threshold = float(_f32(_f32(1.0) + _f32(stretch)))
        if compression_threshold > ratio:
            target = compression_threshold
            activation = min(max((target - ratio) / 0.30000001192092896, 0.0), 1.0)
        elif ratio > stretch_threshold:
            target = stretch_threshold
            activation = min(max((ratio - target) / 0.30000001192092896, 0.0), 1.0)
        else:
            target = ratio
            activation = 0.0
        if activation != 0.0:
            signed_error = current_length - basic_length * target
            correction_scale = signed_error * activation / current_length
            correction = tuple(-value * correction_scale for value in current)
            next_result = [value + delta for value, delta in zip(current, correction)]
            velocity_result = [
                value + delta * 0.699999988079071
                for value, delta in zip(current, correction)
            ]
    return {
        "next": tuple(next_result),
        "velocityPos": tuple(velocity_result),
    }


def _run_native(dll: Path, case: tuple[str, tuple[float, float, float], tuple[float, float, float], float, float]) -> dict[str, Any]:
    _, current, basic, compression, stretch = case
    module = ctypes.WinDLL(str(dll))
    function = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 13))(module._handle + CORE_RVA)
    buffers = [
        ctypes.create_string_buffer(4), ctypes.create_string_buffer(464),
        ctypes.create_string_buffer(808), ctypes.create_string_buffer(696),
        ctypes.create_string_buffer(bytes([1, 2])), ctypes.create_string_buffer(8),
        ctypes.create_string_buffer(8), ctypes.create_string_buffer(4),
        ctypes.create_string_buffer(48), ctypes.create_string_buffer(48),
        ctypes.create_string_buffer(8), ctypes.create_string_buffer(48),
        ctypes.create_string_buffer(4),
    ]
    step, team, parameters, _, _, _, roots, team_ids, next_pos, velocity_pos, _, basic_pos, count = buffers
    struct.pack_into("<i", step, 0, 1)
    struct.pack_into("<i", team, 0x124, 0)
    struct.pack_into("<i", team, 0x174, 0)
    struct.pack_into("<f", parameters, 0xEC, compression)
    struct.pack_into("<f", parameters, 0xF0, stretch)
    struct.pack_into("<2i", roots, 0, -1, 0)
    struct.pack_into("<2h", team_ids, 0, 0, 0)
    struct.pack_into("<6d", next_pos, 0, 0, 0, 0, *current)
    struct.pack_into("<6d", velocity_pos, 0, 0, 0, 0, *current)
    struct.pack_into("<6d", basic_pos, 0, 0, 0, 0, *basic)
    struct.pack_into("<i", count, 0, 1)
    function(*(ctypes.addressof(buffer) for buffer in buffers))
    return {
        "next": struct.unpack_from("<3d", next_pos, 24),
        "velocityPos": struct.unpack_from("<3d", velocity_pos, 24),
    }


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    burst._exact_rva_span(pe, CORE_RVA, CORE_BYTES, CORE_SHA256)
    rows = []
    for case in CASES:
        name, current, basic, compression, stretch = case
        native = _run_native(dll, case)
        port = source_port(case)
        if _hex3(native["next"]) != _hex3(port["next"]) or _hex3(native["velocityPos"]) != _hex3(port["velocityPos"]):
            raise burst.ContractError(f"source tether transcription differs from native core: {name}")
        rows.append({
            "name": name,
            "input": {
                "currentChild": list(current),
                "basicChild": list(basic),
                "compressionLimitFloat32": _f32(compression),
                "stretchLimitFloat32": _f32(stretch),
            },
            "output": {
                "next": list(native["next"]),
                "nextBinary64Le": _hex3(native["next"]),
                "velocityPos": list(native["velocityPos"]),
                "velocityPosBinary64Le": _hex3(native["velocityPos"]),
            },
        })
    return {
        "schema": "endfield.charinfo.secondary-dynamics-tether-golden-vectors.v1",
        "status": "native_avx2_vectors_and_source_transcription_exact_for_bounded_cases",
        "nativeGate": gate,
        "core": {"rva": f"0x{CORE_RVA:x}", "bytes": CORE_BYTES, "sha256": CORE_SHA256},
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": rows,
        "boundary": {
            "nativeCoreExecuted": True,
            "sourceTranscriptionBinary64Matched": True,
            "caseCoverage": ["full stretch", "full compression", "dead zone", "partial activation", "oblique normalization"],
            "unityPortExecuted": True,
            "unityVerifier": "EndfieldSecondaryDynamicsKernelGoldenVerifier.VerifyTetherGoldenVectors",
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
            raise SystemExit("Tether golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
