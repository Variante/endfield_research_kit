#!/usr/bin/env python3
"""Build the exact Endminf M28 peak refractive-sphere packet from Full capture."""

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
DRAW_ORDINAL = 87
PHASE_SECONDS = (273 - 3) / 60.0
FRAME_METADATA_SHA256 = m21.FRAME_METADATA_SHA256
FRAME_RESOURCES_SHA256 = m21.FRAME_RESOURCES_SHA256
VS_SHA256 = "7f5111cf80387beeac8aacb30aa7298d58af6d26a62c981a3e15ba9a1d7468ab"
PS_SHA256 = "a3c9bfc94f0caea930c20bd61ee49fdb95ab58ef1f2e7c64f0f19a74c7e1ea92"
VERTEX_SHA256 = "d0330e2efed3c8916d85f3ed6c4cce71720c63980fcb4e09c1607e9a0954a8c3"
INDEX_SHA256 = "321f2046a4b0fda3555920d5bf8e92fd530d9a28fd1819959516b9f726194583"
EXPECTED_VS_IDENTITY = 9174133498837498862
EXPECTED_PS_IDENTITY = 11802175169836658345
EXPECTED_INDEX_COUNT = 1764
EXPECTED_START_INDEX = 1080
EXPECTED_BASE_VERTEX = 603
EXPECTED_VERTEX_COUNT = 344
EXPECTED_VERTEX_STRIDE = 60
VS_DECLARED = (2, 82, 20, 4094, 5)
PS_DECLARED = (28, 104, 4085, 11)
SHADER_ROOT = (
    REPO / "scratch/character_recovery/vfx_shader_variants/shader_export/Shader"
    / "HGRP_Effect_VFXRefract_p6BC753C54B47D1ED.shader.bytecode"
)
VS_DXBC = SHADER_ROOT / "0624_endfield_dxbc_0.dxbc"
PS_DXBC = SHADER_ROOT / "0625_endfield_dxbc_1.dxbc"
CS_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM28PeakCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M28PeakCapturePayload.generated.h"
)


def collect_constants(draw: dict[str, Any]) -> dict[int, list[bytes]]:
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage, declared in ((0, VS_DECLARED), (4, PS_DECLARED)):
        for slot, declared_count in enumerate(declared):
            payload = shared.constant(draw, stage, slot)
            shared.require(len(payload) >= 16,
                           f"M28 stage {stage} b{slot} has no retained vectors")
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
                   "M28 vertex stride drifted")
    shared.require(int(secondary_binding["stride"]) == 0,
                   "M28 secondary stride drifted")
    shared.require(int(index_binding["format"]) == 57,
                   "M28 index format is not R16_UINT")
    shared.require(int(vertex_binding["objectId"]) == int(index_binding["objectId"]),
                   "M28 vertex/index arena identity drifted")

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
                   "M28 index slice is truncated")
    indices = struct.unpack("<" + "H" * EXPECTED_INDEX_COUNT, indices_bytes)
    shared.require(min(indices) == 0 and max(indices) + 1 == EXPECTED_VERTEX_COUNT,
                   "M28 draw-local vertex range drifted")
    vertex_start = (int(vertex_record["blobOffset"])
                    + int(vertex_binding["offset"])
                    + int(draw["baseVertex"]) * EXPECTED_VERTEX_STRIDE)
    vertices = blob[
        vertex_start:vertex_start + EXPECTED_VERTEX_COUNT * EXPECTED_VERTEX_STRIDE]
    secondary_start = int(secondary_record["blobOffset"])
    secondary = blob[secondary_start:secondary_start + 20]
    shared.require(len(vertices) == EXPECTED_VERTEX_COUNT * EXPECTED_VERTEX_STRIDE,
                   "M28 vertex slice is truncated")
    shared.require(len(secondary) == 20, "M28 secondary stream is truncated")
    shared.require(m21.sha256(vertices) == VERTEX_SHA256,
                   "M28 vertex slice hash drifted")
    shared.require(m21.sha256(indices_bytes) == INDEX_SHA256,
                   "M28 index slice hash drifted")
    return vertices, indices_bytes, secondary


def collect(capture: Path) -> dict[str, Any]:
    shared.require(capture.name == "20260828T004942Z", "M28 session drifted")
    frame_root = capture / "graphics/frames" / str(FRAME)
    metadata_path = frame_root / "metadata.json"
    resources_path = frame_root / "resources.bin"
    shared.require(m21.sha256(metadata_path.read_bytes()) == FRAME_METADATA_SHA256,
                   "M28 metadata hash drifted")
    shared.require(m21.sha256(resources_path.read_bytes()) == FRAME_RESOURCES_SHA256,
                   "M28 resources hash drifted")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = [row for row in metadata.get("drawRecords", [])
            if int(row.get("drawOrdinal", -1)) == DRAW_ORDINAL]
    shared.require(len(rows) == 1, "M28 draw ordinal is not unique")
    draw = rows[0]
    ids = m21.shader_ids(draw)
    shared.require((ids.get(0), ids.get(4)) ==
                   (EXPECTED_VS_IDENTITY, EXPECTED_PS_IDENTITY),
                   "M28 shader pair drifted")
    shared.require(draw.get("indexedInstanced") is True and
                   int(draw.get("instanceCount", 0)) == 1 and
                   int(draw.get("startInstance", -1)) == 0,
                   "M28 instanced draw contract drifted")
    shared.require((int(draw["count"]), int(draw["start"]),
                    int(draw["baseVertex"])) ==
                   (EXPECTED_INDEX_COUNT, EXPECTED_START_INDEX,
                    EXPECTED_BASE_VERTEX), "M28 draw geometry contract drifted")
    vs = VS_DXBC.read_bytes()
    ps = PS_DXBC.read_bytes()
    shared.require(m21.sha256(vs) == VS_SHA256, "M28 vertex DXBC hash drifted")
    shared.require(m21.sha256(ps) == PS_SHA256, "M28 pixel DXBC hash drifted")
    vertices, indices, secondary = collect_geometry(frame_root, metadata, draw)
    return {"vs": vs, "ps": ps, "vertices": vertices, "indices": indices,
            "secondary": secondary, "constants": collect_constants(draw)}


def render_cpp(packet: dict[str, Any]) -> str:
    arrays = [
        shared.cpp_array("g_EndfieldM28PeakVertexDxbc", packet["vs"]),
        shared.cpp_array("g_EndfieldM28PeakPixelDxbc", packet["ps"]),
        shared.cpp_array("g_EndfieldM28PeakVertices", packet["vertices"]),
        shared.cpp_array("g_EndfieldM28PeakIndices", packet["indices"]),
        shared.cpp_array("g_EndfieldM28PeakSecondary", packet["secondary"]),
    ]
    for stage, label in ((0, "VS"), (4, "PS")):
        for slot, payload in enumerate(packet["constants"][stage]):
            arrays.append(shared.cpp_array(
                f"g_EndfieldM28Peak{label}CB{slot}", payload))
    return ((
        "// Generated by tools/build_endminf_m28_peak_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM28PeakPayloadPrepared = true;\n"
        f"inline constexpr float g_EndfieldM28PeakPhaseSeconds = {PHASE_SECONDS:.6f}f;\n"
        f"inline constexpr std::uint32_t g_EndfieldM28PeakVertexStride = {EXPECTED_VERTEX_STRIDE}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldM28PeakVertexCount = {EXPECTED_VERTEX_COUNT}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldM28PeakIndexCount = {EXPECTED_INDEX_COUNT}u;\n"
        "inline constexpr std::uint32_t g_EndfieldM28PeakVSDeclaredFloat4Counts[] = {2, 82, 20, 4094, 5};\n"
        "inline constexpr std::uint32_t g_EndfieldM28PeakPSDeclaredFloat4Counts[] = {28, 104, 4085, 11};\n\n"
        + "\n".join(arrays)).rstrip() + "\n")


def render_cs() -> str:
    return f'''// Generated by tools/build_endminf_m28_peak_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM28PeakCaptureData
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
