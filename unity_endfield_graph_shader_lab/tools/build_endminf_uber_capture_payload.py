#!/usr/bin/env python3
"""Build the exact Endminf Uber constant payload from a validated capture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_EARLY_REPORT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_uber_early_constant_payload_20260827T183054Z.json"
)
DEFAULT_LATE_REPORT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_uber_late_constant_payload_20260827T183054Z.json"
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


def packet_from_report(report: dict[str, Any], expected_frame: int) -> dict[str, Any]:
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
    require(int(packet.get("frame", -1)) == expected_frame,
            f"exact Uber packet frame drifted from {expected_frame}")
    require(packet.get("vertexSha256") == EXPECTED_VERTEX_SHA256,
            "exact Uber vertex shader identity drifted")
    require(packet.get("pixelSha256") == EXPECTED_PIXEL_SHA256,
            "exact Uber pixel shader identity drifted")
    return packet


def build_header(early_report: dict[str, Any],
                 late_report: dict[str, Any] | None = None) -> str:
    # Preserve the one-report API for focused unit tests; production generation
    # always supplies independently validated early and late packets.
    if late_report is None:
        late_report = early_report
        expected_early_frame = int(early_report["packets"][0]["frame"])
        expected_late_frame = expected_early_frame
    else:
        expected_early_frame = 1600
        expected_late_frame = 1818
    early = packet_from_report(early_report, expected_early_frame)
    late = packet_from_report(late_report, expected_late_frame)
    early_vs_b0 = exact_range(early, "vsB0", 1)
    early_ps_b0 = exact_range(early, "b0", 28)
    early_ps_b1 = exact_range(early, "b1", 26)
    late_vs_b0 = exact_range(late, "vsB0", 1)
    late_ps_b0 = exact_range(late, "b0", 28)
    late_ps_b1 = exact_range(late, "b1", 26)
    early_capture = str(early_report.get("capture", "")).replace("\\", "/")
    late_capture = str(late_report.get("capture", "")).replace("\\", "/")
    early_frame = int(early.get("frame", -1))
    late_frame = int(late.get("frame", -1))
    early_ordinal = int(early.get("fullscreenOrdinal", -1))
    late_ordinal = int(late.get("fullscreenOrdinal", -1))
    require(min(early_frame, late_frame, early_ordinal, late_ordinal) >= 0,
            "exact Uber packet has no frame/ordinal provenance")
    return (
        "#pragma once\n"
        "#include <cstddef>\n"
        "#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldUberCapturePayloadAvailable = true;\n"
        f'inline constexpr char g_EndfieldUberEarlyCapture[] = "{early_capture}";\n'
        f"inline constexpr std::uint32_t g_EndfieldUberEarlyCaptureFrame = {early_frame}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldUberEarlyFullscreenOrdinal = {early_ordinal}u;\n"
        f'inline constexpr char g_EndfieldUberCapture[] = "{late_capture}";\n'
        f"inline constexpr std::uint32_t g_EndfieldUberCaptureFrame = {late_frame}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldUberFullscreenOrdinal = {late_ordinal}u;\n\n"
        + render_bytes("g_EndfieldUberEarlyVsB0", early_vs_b0)
        + "\n"
        + render_bytes("g_EndfieldUberEarlyPsB0", early_ps_b0)
        + "\n"
        + render_bytes("g_EndfieldUberEarlyPsB1", early_ps_b1)
        + "\n"
        + render_bytes("g_EndfieldUberVsB0", late_vs_b0)
        + "\n"
        + render_bytes("g_EndfieldUberPsB0", late_ps_b0)
        + "\n"
        + render_bytes("g_EndfieldUberPsB1", late_ps_b1)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--early-report", type=Path, default=DEFAULT_EARLY_REPORT)
    parser.add_argument("--late-report", type=Path, default=DEFAULT_LATE_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        early_report = json.loads(args.early_report.read_text(encoding="utf-8"))
        late_report = json.loads(args.late_report.read_text(encoding="utf-8"))
        header = build_header(early_report, late_report)
    except (OSError, ValueError, ContractError) as exc:
        print(f"ERROR: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
