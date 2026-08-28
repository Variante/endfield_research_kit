#!/usr/bin/env python3
"""Build the exact Endminf M18 amber diffusion-shell packet from Full capture."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

import build_endminf_m21_peak_exact_capture_data as m21
import build_endminf_m30_exact_capture_data as shared


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260828T004942Z"
FRAME = 2775
DRAW_ORDINAL = 82
PHASE_SECONDS = (273 - 3) / 60.0
FRAME_METADATA_SHA256 = m21.FRAME_METADATA_SHA256
FRAME_RESOURCES_SHA256 = m21.FRAME_RESOURCES_SHA256
VS_SHA256 = "7d1953e7b7d5310f8ade70348901d48da1b882e6387814464f053d8c8a84cf85"
PS_SHA256 = "601242f701cb4380dd4383069ca1ad167a4ed55ba1800c1002998835490db88e"
VERTEX_SHA256 = "c798b3374ff03684ec536db43d6261377de03b40eddeb0c00e36a8b8ddde8c2c"
INDEX_SHA256 = "df1ffa56baa56e8ed36e6fa78b12ff76bdbf801dc8ce3c4496633b81138eb57c"
EXPECTED_VS_IDENTITY = 9014328383845511439
EXPECTED_PS_IDENTITY = 6922669205876327296
EXPECTED_INDEX_COUNT = 900
EXPECTED_START_INDEX = 4002
EXPECTED_BASE_VERTEX = 2045
EXPECTED_VERTEX_STRIDE = 76
VS_DECLARED = (2, 82, 104, 4094, 49)
PS_DECLARED = (28, 105, 4085, 43)
SHADER_ROOT = m21.SHADER_ROOT
VS_DXBC = SHADER_ROOT / "4152_endfield_dxbc_0.dxbc"
PS_DXBC = SHADER_ROOT / "4153_endfield_dxbc_1.dxbc"
CS_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM18PeakCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M18PeakCapturePayload.generated.h"
)


def collect_constants(draw: dict[str, Any]) -> dict[int, list[bytes]]:
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage, declared in ((0, VS_DECLARED), (4, PS_DECLARED)):
        for slot, declared_count in enumerate(declared):
            payload = shared.constant(draw, stage, slot)
            shared.require(len(payload) >= 16,
                           f"M18 stage {stage} b{slot} has no retained vectors")
            result[stage].append(payload[:declared_count * 16])
    return result


def collect_geometry(frame_root: Path, metadata: dict[str, Any],
                     draw: dict[str, Any]) -> tuple[bytes, bytes, bytes]:
    ia = draw["inputAssembler"]
    vertex_binding = next(row for row in ia["vertexBuffers"]
                          if int(row["slot"]) == 0)
    secondary_binding = next(row for row in ia["vertexBuffers"]
                             if int(row["slot"]) == 1)
    index_binding = ia["indexBuffer"]
    shared.require(int(vertex_binding["stride"]) == EXPECTED_VERTEX_STRIDE,
                   "M18 vertex stride drifted")
    shared.require(int(index_binding["format"]) == 57,
                   "M18 index format is not R16_UINT")
    vertex_record = m21.selected_record(
        metadata, 0, 0, int(vertex_binding["objectId"]))
    index_record = m21.selected_record(
        metadata, 1, 0, int(index_binding["objectId"]))
    secondary_record = m21.selected_record(
        metadata, 0, 1, int(secondary_binding["objectId"]))
    blob = (frame_root / "resources.bin").read_bytes()
    index_start = (int(index_record["blobOffset"])
                   + int(index_binding["offset"])
                   + int(draw["start"]) * 2)
    indices_bytes = blob[index_start:index_start + EXPECTED_INDEX_COUNT * 2]
    shared.require(len(indices_bytes) == EXPECTED_INDEX_COUNT * 2,
                   "M18 index slice is truncated")
    indices = struct.unpack("<" + "H" * EXPECTED_INDEX_COUNT, indices_bytes)
    shared.require(min(indices) == 0, "M18 draw-local indices no longer start at zero")
    vertex_count = max(indices) + 1
    vertex_start = (int(vertex_record["blobOffset"])
                    + int(vertex_binding["offset"])
                    + int(draw["baseVertex"]) * EXPECTED_VERTEX_STRIDE)
    vertices = blob[
        vertex_start:vertex_start + vertex_count * EXPECTED_VERTEX_STRIDE]
    secondary_start = int(secondary_record["blobOffset"])
    secondary = blob[secondary_start:secondary_start + 20]
    shared.require(m21.sha256(vertices) == VERTEX_SHA256,
                   "M18 vertex slice hash drifted")
    shared.require(m21.sha256(indices_bytes) == INDEX_SHA256,
                   "M18 index slice hash drifted")
    shared.require(len(secondary) == 20, "M18 secondary stream is truncated")
    return vertices, indices_bytes, secondary


def collect(capture: Path) -> dict[str, Any]:
    shared.require(capture.name == "20260828T004942Z", "M18 session drifted")
    frame_root = capture / "graphics/frames" / str(FRAME)
    metadata_path = frame_root / "metadata.json"
    resources_path = frame_root / "resources.bin"
    shared.require(m21.sha256(metadata_path.read_bytes()) == FRAME_METADATA_SHA256,
                   "M18 metadata hash drifted")
    shared.require(m21.sha256(resources_path.read_bytes()) == FRAME_RESOURCES_SHA256,
                   "M18 resources hash drifted")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = [row for row in metadata.get("drawRecords", [])
            if int(row.get("drawOrdinal", -1)) == DRAW_ORDINAL]
    shared.require(len(rows) == 1, "M18 draw ordinal is not unique")
    draw = rows[0]
    ids = m21.shader_ids(draw)
    shared.require((ids.get(0), ids.get(4)) ==
                   (EXPECTED_VS_IDENTITY, EXPECTED_PS_IDENTITY),
                   "M18 shader pair drifted")
    shared.require((int(draw["count"]), int(draw["start"]),
                    int(draw["baseVertex"])) ==
                   (EXPECTED_INDEX_COUNT, EXPECTED_START_INDEX,
                    EXPECTED_BASE_VERTEX), "M18 draw geometry contract drifted")
    vs = VS_DXBC.read_bytes()
    ps = PS_DXBC.read_bytes()
    shared.require(m21.sha256(vs) == VS_SHA256, "M18 vertex DXBC hash drifted")
    shared.require(m21.sha256(ps) == PS_SHA256, "M18 pixel DXBC hash drifted")
    vertices, indices, secondary = collect_geometry(frame_root, metadata, draw)
    return {"vs": vs, "ps": ps, "vertices": vertices, "indices": indices,
            "secondary": secondary, "constants": collect_constants(draw)}


def render_cpp(packet: dict[str, Any]) -> str:
    arrays = [
        shared.cpp_array("g_EndfieldM18PeakVertexDxbc", packet["vs"]),
        shared.cpp_array("g_EndfieldM18PeakPixelDxbc", packet["ps"]),
        shared.cpp_array("g_EndfieldM18PeakVertices", packet["vertices"]),
        shared.cpp_array("g_EndfieldM18PeakIndices", packet["indices"]),
        shared.cpp_array("g_EndfieldM18PeakSecondary", packet["secondary"]),
    ]
    for stage, label in ((0, "VS"), (4, "PS")):
        for slot, payload in enumerate(packet["constants"][stage]):
            arrays.append(shared.cpp_array(
                f"g_EndfieldM18Peak{label}CB{slot}", payload))
    return ((
        "// Generated by tools/build_endminf_m18_peak_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM18PeakPayloadPrepared = true;\n"
        f"inline constexpr float g_EndfieldM18PeakPhaseSeconds = {PHASE_SECONDS:.6f}f;\n"
        f"inline constexpr std::uint32_t g_EndfieldM18PeakVertexStride = {EXPECTED_VERTEX_STRIDE}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldM18PeakIndexCount = {EXPECTED_INDEX_COUNT}u;\n"
        "inline constexpr std::uint32_t g_EndfieldM18PeakVSDeclaredFloat4Counts[] = {2, 82, 104, 4094, 49};\n"
        "inline constexpr std::uint32_t g_EndfieldM18PeakPSDeclaredFloat4Counts[] = {28, 105, 4085, 43};\n\n"
        + "\n".join(arrays)).rstrip() + "\n")


def render_cs() -> str:
    return f'''// Generated by tools/build_endminf_m18_peak_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM18PeakCaptureData
    {{
        internal const string SourceSession = "20260828T004942Z";
        internal const int SourceFrame = {FRAME};
        internal const int DrawOrdinal = {DRAW_ORDINAL};
        internal const float PhaseSeconds = {PHASE_SECONDS:.6f}f;
        internal const int DrawCount = 1;
        internal const bool PayloadPrepared = true;
        internal const string MetadataSha256 = "{FRAME_METADATA_SHA256}";
        internal const string ResourcesSha256 = "{FRAME_RESOURCES_SHA256}";
        internal const string VertexSha256 = "{VERTEX_SHA256}";
        internal const string IndexSha256 = "{INDEX_SHA256}";
    }}
}}
'''


def build(capture: Path, cs_output: Path, cpp_output: Path) -> None:
    packet = collect(capture)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(render_cs(), encoding="utf-8", newline="\n")
    cpp_output.write_text(render_cpp(packet), encoding="utf-8", newline="\n")


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
