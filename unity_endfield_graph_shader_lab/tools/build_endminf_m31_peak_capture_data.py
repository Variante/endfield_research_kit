#!/usr/bin/env python3
"""Build the exact two-draw Endminf M31 crystal-peak payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_endminf_m30_exact_capture_data as shared


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260827T183054Z"
FRAME = 1818
# Capture frame 1818 directly matches clean extracted frame 264. The prior
# 4.433333 anchor incorrectly treated presented-frame deltas as animation time.
PHASE_SECONDS = (264 - 3) / 60.0
CS_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM31PeakCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M31PeakCapturePayload.generated.h"
)
EXPECTED_SESSION = "20260827T183054Z"
EXPECTED_VS = 0x62A5CE6C09171DE9
EXPECTED_PS = 0x5558DEDDB1EE6188
EXPECTED_C1 = (1.0, 0.0, 1.4, 1.35)
EXPECTED_C4 = (
    (1.0, 0.5607878, 0.0976956, 1.0),
    (1.0, 1.0, 1.0, 1.0),
)


def is_m31(draw: dict[str, Any]) -> bool:
    pair = {int(row.get("stage", -1)): int(row.get("identityHash", 0))
            for row in draw.get("shaders", []) if isinstance(row, dict)}
    if (int(draw.get("count", -1)) != 6 or
            pair.get(0) != EXPECTED_VS or pair.get(4) != EXPECTED_PS):
        return False
    try:
        b3 = shared.constant(draw, 4, 3)
    except ValueError:
        return False
    return (shared.close(shared.vector(b3, 1), EXPECTED_C1) and
            any(shared.close(shared.vector(b3, 4), value)
                for value in EXPECTED_C4))


def texture_payload(frame_root: Path, metadata: dict[str, Any],
                    draws: list[dict[str, Any]]) -> dict[str, Any]:
    object_ids: set[int] = set()
    for draw in draws:
        rows = [row for row in draw.get("resources", [])
                if int(row.get("stage", -1)) == 4 and
                int(row.get("slot", -1)) == 1]
        shared.require(len(rows) == 1, "M31 draw does not own one PS t1")
        object_ids.add(int(rows[0]["objectId"]))
    shared.require(len(object_ids) == 1,
                   "the two M31 peak draws do not share one main texture")
    object_id = next(iter(object_ids))
    selected = [row for row in metadata.get("selectedResourceRecords", [])
                if int(row.get("objectId", 0)) == object_id and
                int(row.get("stage", -1)) == 4 and
                int(row.get("slot", -1)) == 1]
    shared.require(len(selected) == 1 and selected[0].get("completed") is True,
                   "M31 PS t1 payload is not uniquely complete")
    row = selected[0]
    shared.require((int(row.get("format", -1)),
                    int(row.get("viewFormat", -1)),
                    int(row.get("width", 0)), int(row.get("height", 0))) ==
                   (99, 99, 256, 256), "M31 PS t1 descriptor drifted")
    blob = (frame_root / "resources.bin").read_bytes()
    start = int(row["blobOffset"])
    size = int(row["blobBytes"])
    payload = blob[start:start + size]
    shared.require(len(payload) == 65536, "M31 PS t1 byte count drifted")
    return {"payload": payload, "sha256": shared.sha256_bytes(payload)}


def collect(capture: Path) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    shared.require(capture.name == EXPECTED_SESSION,
                   "M31 source session drifted")
    frame_root = capture / "graphics/frames" / str(FRAME)
    metadata_path = frame_root / "metadata.json"
    metadata = shared.load_json(metadata_path)
    draws = [row for row in metadata.get("drawRecords", [])
             if isinstance(row, dict) and is_m31(row)]
    shared.require(len(draws) == 2,
                   f"M31 peak draw count drifted: {len(draws)}")
    secondary = shared.collect_secondary_stream(frame_root, metadata)
    packets: list[dict[str, Any]] = []
    for draw in draws:
        packets.append({
            "drawIndex": metadata["drawRecords"].index(draw),
            "constants": shared.collect_constants(draw),
            "geometry": shared.collect_geometry(frame_root, metadata, draw),
            "secondary": secondary,
        })
    texture = texture_payload(frame_root, metadata, draws)
    return packets, texture, shared.sha256_bytes(metadata_path.read_bytes())


def render_cpp(packets: list[dict[str, Any]], texture: dict[str, Any],
               metadata_sha256: str) -> str:
    arrays = [shared.cpp_array("g_EndfieldM31PeakTextureT1", texture["payload"])]
    descriptors: list[str] = []
    for index, packet in enumerate(packets):
        prefix = f"g_EndfieldM31PeakP{index}"
        arrays.extend((
            shared.cpp_array(prefix + "Vertices", packet["geometry"]["vertices"]),
            shared.cpp_array(prefix + "Indices", packet["geometry"]["indices"]),
            shared.cpp_array(prefix + "Secondary", packet["secondary"]),
        ))
        for stage, label in ((0, "VS"), (4, "PS")):
            for slot, payload in enumerate(packet["constants"][stage]):
                arrays.append(shared.cpp_array(
                    f"{prefix}{label}CB{slot}", payload))
        descriptors.append(
            f"    {{{packet['drawIndex']}u, {prefix}Vertices, "
            f"{prefix}VerticesSize, {prefix}Indices, {prefix}IndicesSize, "
            f"{packet['geometry']['index_count']}u, {prefix}Secondary, "
            f"{prefix}SecondarySize, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
    return (
        "// Generated by tools/build_endminf_m31_peak_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM31PeakPayloadPrepared = true;\n"
        "inline constexpr bool g_EndfieldM31PeakDepthContractReady = true;\n"
        f'inline constexpr char g_EndfieldM31PeakSession[] = "{EXPECTED_SESSION}";\n'
        f'inline constexpr char g_EndfieldM31PeakMetadataSha256[] = "{metadata_sha256}";\n'
        f"inline constexpr std::uint32_t g_EndfieldM31PeakFrame = {FRAME}u;\n"
        f"inline constexpr float g_EndfieldM31PeakPhaseSeconds = {PHASE_SECONDS:.6f}f;\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakVertexStride = 36u;\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakVSDeclaredFloat4Counts[] = {2, 82, 104, 4094, 10};\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakPSDeclaredFloat4Counts[] = {28, 105, 4085, 22};\n\n" +
        "\n".join(arrays) + "\n"
        "struct EndfieldM31PeakPacketPayload { std::uint32_t drawIndex; "
        "const std::uint8_t* vertices; std::size_t vertexBytes; "
        "const std::uint8_t* indices; std::size_t indexBytes; "
        "std::uint32_t indexCount; const std::uint8_t* secondary; "
        "std::size_t secondaryBytes; const std::uint8_t* vs[5]; "
        "std::size_t vsBytes[5]; const std::uint8_t* ps[4]; "
        "std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldM31PeakPacketPayload g_EndfieldM31PeakPackets[] = {\n" +
        "\n".join(descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakPacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM31PeakPackets) / "
        "sizeof(g_EndfieldM31PeakPackets[0]));\n"
        f'inline constexpr char g_EndfieldM31PeakTextureT1Sha256[] = "{texture["sha256"]}";\n'
    )


def render_cs(texture: dict[str, Any], metadata_sha256: str) -> str:
    return f'''// Generated by tools/build_endminf_m31_peak_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM31PeakCaptureData
    {{
        internal const string SourceSession = "{EXPECTED_SESSION}";
        internal const int SourceFrame = {FRAME};
        internal const float PhaseSeconds = {PHASE_SECONDS:.6f}f;
        internal const int DrawCount = 2;
        internal const bool PayloadPrepared = true;
        internal const bool DepthContractReady = true;
        internal const string MetadataSha256 = "{metadata_sha256}";
        internal const string TextureT1Sha256 = "{texture['sha256']}";
    }}
}}
'''


def build(capture: Path, cs_output: Path, cpp_output: Path) -> None:
    packets, texture, metadata_sha256 = collect(capture)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(render_cs(texture, metadata_sha256),
                         encoding="utf-8", newline="\n")
    cpp_output.write_text(render_cpp(packets, texture, metadata_sha256),
                          encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--cs-output", type=Path, default=CS_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.capture.resolve(), args.cs_output.resolve(),
          args.cpp_output.resolve())
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
