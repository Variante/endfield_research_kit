#!/usr/bin/env python3
"""Build the exact Endminf Uber constant payload from a validated capture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_uber_capture_latest.json"
)
DEFAULT_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "EndminfUberCapturePayload.generated.h"
)
EXPECTED_STATUS = "validated_exact_uber_constant_payload_only"
EXPECTED_VERTEX_SHA256 = (
    "a8c084c37eba0ecc78f26d984a2b8c658f8d743002048c84431807d9dee0ce4e"
)
EXPECTED_PIXEL_SHA256 = (
    "86a732cef7eedb150cbcafb35a994c1e3f7b1ef837dc618131a95e9dfe030c97"
)


class ContractError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def exact_range(packet: dict[str, Any], key: str,
                constants: int) -> bytes:
    row = packet.get(key)
    require(isinstance(row, dict), f"capture packet has no {key} range")
    require(int(row.get("declaredConstants", 0)) == constants,
            f"capture packet {key} declaration drifted")
    encoded = row.get("declaredRangeHex")
    require(isinstance(encoded, str),
            f"capture packet {key} has no exact byte encoding")
    try:
        payload = bytes.fromhex(encoded)
    except ValueError as exc:
        raise ContractError(
            f"capture packet {key} has invalid exact bytes") from exc
    require(len(payload) == constants * 16,
            f"capture packet {key} has {len(payload)} bytes; "
            f"expected {constants * 16}")
    require(hashlib.sha256(payload).hexdigest() ==
            row.get("declaredRangeSha256"),
            f"capture packet {key} exact-byte hash drifted")
    return payload


def render_bytes(name: str, payload: bytes) -> str:
    rows = []
    for start in range(0, len(payload), 16):
        chunk = payload[start:start + 16]
        rows.append("    " + ", ".join(f"0x{value:02x}" for value in chunk) + ",")
    return (
        f"inline constexpr std::uint8_t {name}[] = {{\n"
        + "\n".join(rows)
        + "\n};\n"
        + f"inline constexpr std::size_t {name}Size = sizeof({name});\n"
    )


def build_header(report: dict[str, Any]) -> str:
    require(report.get("status") == EXPECTED_STATUS,
            "Uber report is not a validated exact constant-only payload")
    require(report.get("compiledKeywords") ==
            ["BLOOM", "RADIAL_BLUR", "VIGNETTE"],
            "exact Uber keyword set drifted")
    packets = report.get("packets")
    require(isinstance(packets, list) and len(packets) == 1,
            "exact Uber payload requires one unambiguous captured packet")
    packet = packets[0]
    require(isinstance(packet, dict), "exact Uber packet is invalid")
    require(packet.get("vertexSha256") == EXPECTED_VERTEX_SHA256,
            "exact Uber vertex shader identity drifted")
    require(packet.get("pixelSha256") == EXPECTED_PIXEL_SHA256,
            "exact Uber pixel shader identity drifted")
    vs_b0 = exact_range(packet, "vsB0", 1)
    ps_b0 = exact_range(packet, "b0", 28)
    ps_b1 = exact_range(packet, "b1", 26)
    capture = str(report.get("capture", "")).replace("\\", "/")
    frame = int(packet.get("frame", -1))
    ordinal = int(packet.get("fullscreenOrdinal", -1))
    require(frame >= 0 and ordinal >= 0,
            "exact Uber packet has no frame/ordinal provenance")
    return (
        "#pragma once\n"
        "#include <cstddef>\n"
        "#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldUberCapturePayloadAvailable = true;\n"
        f'inline constexpr char g_EndfieldUberCapture[] = "{capture}";\n'
        f"inline constexpr std::uint32_t g_EndfieldUberCaptureFrame = {frame}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldUberFullscreenOrdinal = {ordinal}u;\n\n"
        + render_bytes("g_EndfieldUberVsB0", vs_b0)
        + "\n"
        + render_bytes("g_EndfieldUberPsB0", ps_b0)
        + "\n"
        + render_bytes("g_EndfieldUberPsB1", ps_b1)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        header = build_header(report)
    except (OSError, ValueError, ContractError) as exc:
        print(f"ERROR: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
