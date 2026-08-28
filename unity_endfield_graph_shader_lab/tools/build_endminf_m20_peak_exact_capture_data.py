#!/usr/bin/env python3
"""Build Endminf's exact retail M20 gas-plume packet from automatic capture."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

import build_endminf_m21_peak_exact_capture_data as m21
import build_endminf_m30_exact_capture_data as shared


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260828T224210Z"
FRAME = 1748
DRAW_ORDINAL = 77
PHASE_SECONDS = 4.433333
FRAME_METADATA_SHA256 = "ec785118b40e5da4b753118460f57759ee7de7c440df1fabf137e230a4b4752b"
FRAME_RESOURCES_SHA256 = "1ac5fe20944a6100ac4a8a3ede5c542272ce1755e90577222b81c44036dc9d07"
VS_SHA256 = "62a5ce6c09171de949ade143b0520cef5b6f899137c1d0190d4014b053eee698"
PS_SHA256 = "5558deddb1ee6188dfb530e5be89d86d67352362384fababc585e778b78b99e7"
VERTEX_SHA256 = "ed1f2340d6212fe064857717b9ea45ffd96951e7e4f6f1dda36d542bac03e20b"
INDEX_SHA256 = "111344a69a3f4c9c714bfdd23c3b16f9ad6beb430821bd310f33d9f795061012"
SECONDARY_SHA256 = "d60dbf57189e6a16e14dc8e8a5ff123ff163334a32857641daeee7d46966bb76"
ATLAS_SHA256 = "c7d830bcee33bbd31367d2c7d40eeb9f0d5d808f94d66925fb4fda619fcc8bdd"
EXPECTED_VS_IDENTITY = 0x62A5CE6C09171DE9
EXPECTED_PS_IDENTITY = 0x5558DEDDB1EE6188
EXPECTED_INDEX_COUNT = 36
EXPECTED_START_INDEX = 4542
EXPECTED_BASE_VERTEX = 48
EXPECTED_VERTEX_COUNT = 24
EXPECTED_VERTEX_STRIDE = 36
EXPECTED_ATLAS_WIDTH = 256
EXPECTED_ATLAS_HEIGHT = 128
BC7_UNORM_SRGB = 99
VS_DECLARED = (2, 82, 104, 4096, 10)
PS_DECLARED = (28, 105, 4096, 22)
SHADER_ROOT = CAPTURE / "graphics/shaders"
VS_DXBC = SHADER_ROOT / f"{VS_SHA256}-s0.dxbc"
PS_DXBC = SHADER_ROOT / f"{PS_SHA256}-s4.dxbc"
CS_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM20PeakCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M20PeakCapturePayload.generated.h"
)


def selected_record(metadata: dict[str, Any], kind: int, stage: int,
                    slot: int, object_id: int) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if int(row.get("captureKind", -1)) == kind
            and int(row.get("stage", -1)) == stage
            and int(row.get("slot", -1)) == slot
            and int(row.get("objectId", 0)) == object_id
            and row.get("completed") is True]
    shared.require(len(rows) == 1,
                   f"M20 resource kind={kind} stage={stage} slot={slot} is not unique")
    return rows[0]


def resource_bytes(blob: bytes, row: dict[str, Any]) -> bytes:
    start = int(row["blobOffset"])
    size = int(row["blobBytes"])
    result = blob[start:start + size]
    shared.require(len(result) == size, "M20 selected resource is truncated")
    return result


def collect_constants(draw: dict[str, Any]) -> dict[int, list[bytes]]:
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage, declared in ((0, VS_DECLARED), (4, PS_DECLARED)):
        for slot, declared_count in enumerate(declared):
            payload = shared.constant(draw, stage, slot)
            shared.require(len(payload) >= 16,
                           f"M20 stage {stage} b{slot} has no retained vectors")
            result[stage].append(payload[:declared_count * 16])
    return result


def collect_geometry(frame_root: Path, metadata: dict[str, Any],
                     draw: dict[str, Any]) -> tuple[bytes, bytes, bytes]:
    ia = draw["inputAssembler"]
    vertex = next(row for row in ia["vertexBuffers"] if int(row["slot"]) == 0)
    secondary = next(row for row in ia["vertexBuffers"] if int(row["slot"]) == 1)
    index = ia["indexBuffer"]
    shared.require(int(vertex["stride"]) == EXPECTED_VERTEX_STRIDE,
                   "M20 vertex stride drifted")
    shared.require(int(secondary["stride"]) == 0, "M20 secondary stride drifted")
    shared.require(int(index["format"]) == 57, "M20 index format is not R16_UINT")
    shared.require(int(vertex["objectId"]) == int(index["objectId"]),
                   "M20 vertex/index arena identity drifted")
    vertex_row = selected_record(metadata, 0, 0, 0, int(vertex["objectId"]))
    index_row = selected_record(metadata, 1, 0, 0, int(index["objectId"]))
    secondary_row = selected_record(metadata, 0, 0, 1,
                                    int(secondary["objectId"]))
    blob = (frame_root / "resources.bin").read_bytes()
    index_start = (int(index_row["blobOffset"]) + int(index["offset"])
                   + int(draw["start"]) * 2)
    indices = blob[index_start:index_start + EXPECTED_INDEX_COUNT * 2]
    shared.require(len(indices) == EXPECTED_INDEX_COUNT * 2,
                   "M20 index slice is truncated")
    values = struct.unpack("<" + "H" * EXPECTED_INDEX_COUNT, indices)
    shared.require(min(values) == 0 and max(values) == EXPECTED_VERTEX_COUNT - 1,
                   "M20 draw-local vertex range drifted")
    vertex_start = (int(vertex_row["blobOffset"]) + int(vertex["offset"])
                    + int(draw["baseVertex"]) * EXPECTED_VERTEX_STRIDE)
    vertices = blob[vertex_start:vertex_start
                    + EXPECTED_VERTEX_COUNT * EXPECTED_VERTEX_STRIDE]
    secondary_bytes = resource_bytes(blob, secondary_row)[:20]
    shared.require(m21.sha256(vertices) == VERTEX_SHA256,
                   "M20 vertex slice hash drifted")
    shared.require(m21.sha256(indices) == INDEX_SHA256,
                   "M20 index slice hash drifted")
    shared.require(m21.sha256(secondary_bytes) == SECONDARY_SHA256,
                   "M20 secondary stream hash drifted")
    return vertices, indices, secondary_bytes


def collect_atlas(frame_root: Path, metadata: dict[str, Any],
                  draw: dict[str, Any]) -> bytes:
    resources = [row for row in draw.get("resources", [])
                 if int(row.get("stage", -1)) == 4
                 and int(row.get("slot", -1)) == 1
                 and int(row.get("kind", -1)) == 3]
    shared.require(len(resources) == 1, "M20 PS t1 atlas binding is not unique")
    row = selected_record(metadata, 3, 4, 1, int(resources[0]["objectId"]))
    shared.require((int(row["width"]), int(row["height"]), int(row["format"]),
                    int(row["viewFormat"])) ==
                   (EXPECTED_ATLAS_WIDTH, EXPECTED_ATLAS_HEIGHT,
                    BC7_UNORM_SRGB, BC7_UNORM_SRGB),
                   "M20 PS t1 is not the measured 256x128 BC7 sRGB atlas")
    atlas = resource_bytes((frame_root / "resources.bin").read_bytes(), row)
    shared.require(m21.sha256(atlas) == ATLAS_SHA256, "M20 atlas hash drifted")
    return atlas


def collect(capture: Path) -> dict[str, Any]:
    shared.require(capture.name == "20260828T224210Z", "M20 session drifted")
    frame_root = capture / "graphics/frames" / str(FRAME)
    metadata_path = frame_root / "metadata.json"
    resources_path = frame_root / "resources.bin"
    shared.require(m21.sha256(metadata_path.read_bytes()) == FRAME_METADATA_SHA256,
                   "M20 metadata hash drifted")
    shared.require(m21.sha256(resources_path.read_bytes()) == FRAME_RESOURCES_SHA256,
                   "M20 resources hash drifted")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = [row for row in metadata.get("drawRecords", [])
            if int(row.get("drawOrdinal", -1)) == DRAW_ORDINAL]
    shared.require(len(rows) == 1, "M20 draw ordinal is not unique")
    draw = rows[0]
    shared.require(m21.shader_ids(draw) ==
                   {0: EXPECTED_VS_IDENTITY, 4: EXPECTED_PS_IDENTITY},
                   "M20 retail shader pair drifted")
    shared.require(draw.get("indexedInstanced") is True
                   and int(draw.get("instanceCount", 0)) == 1
                   and int(draw.get("startInstance", -1)) == 0,
                   "M20 instanced draw contract drifted")
    shared.require((int(draw["count"]), int(draw["start"]),
                    int(draw["baseVertex"])) ==
                   (EXPECTED_INDEX_COUNT, EXPECTED_START_INDEX,
                    EXPECTED_BASE_VERTEX), "M20 geometry contract drifted")
    vs = VS_DXBC.read_bytes()
    ps = PS_DXBC.read_bytes()
    shared.require(m21.sha256(vs) == VS_SHA256, "M20 vertex DXBC hash drifted")
    shared.require(m21.sha256(ps) == PS_SHA256, "M20 pixel DXBC hash drifted")
    vertices, indices, secondary = collect_geometry(frame_root, metadata, draw)
    return {"vs": vs, "ps": ps, "vertices": vertices, "indices": indices,
            "secondary": secondary, "atlas": collect_atlas(frame_root, metadata, draw),
            "constants": collect_constants(draw)}


def render_cpp(packet: dict[str, Any]) -> str:
    arrays = [
        shared.cpp_array("g_EndfieldM20PeakVertexDxbc", packet["vs"]),
        shared.cpp_array("g_EndfieldM20PeakPixelDxbc", packet["ps"]),
        shared.cpp_array("g_EndfieldM20PeakVertices", packet["vertices"]),
        shared.cpp_array("g_EndfieldM20PeakIndices", packet["indices"]),
        shared.cpp_array("g_EndfieldM20PeakSecondary", packet["secondary"]),
        shared.cpp_array("g_EndfieldM20PeakAtlasBc7", packet["atlas"]),
    ]
    for stage, label in ((0, "VS"), (4, "PS")):
        for slot, payload in enumerate(packet["constants"][stage]):
            arrays.append(shared.cpp_array(
                f"g_EndfieldM20Peak{label}CB{slot}", payload))
    return (("// Generated by tools/build_endminf_m20_peak_exact_capture_data.py. Do not edit.\n"
             "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
             "inline constexpr bool g_EndfieldM20PeakPayloadPrepared = true;\n"
             f"inline constexpr float g_EndfieldM20PeakPhaseSeconds = {PHASE_SECONDS:.6f}f;\n"
             f"inline constexpr std::uint32_t g_EndfieldM20PeakVertexStride = {EXPECTED_VERTEX_STRIDE}u;\n"
             f"inline constexpr std::uint32_t g_EndfieldM20PeakVertexCount = {EXPECTED_VERTEX_COUNT}u;\n"
             f"inline constexpr std::uint32_t g_EndfieldM20PeakIndexCount = {EXPECTED_INDEX_COUNT}u;\n"
             f"inline constexpr std::uint32_t g_EndfieldM20PeakAtlasWidth = {EXPECTED_ATLAS_WIDTH}u;\n"
             f"inline constexpr std::uint32_t g_EndfieldM20PeakAtlasHeight = {EXPECTED_ATLAS_HEIGHT}u;\n"
             "inline constexpr std::uint32_t g_EndfieldM20PeakVSDeclaredFloat4Counts[] = {2, 82, 104, 4096, 10};\n"
             "inline constexpr std::uint32_t g_EndfieldM20PeakPSDeclaredFloat4Counts[] = {28, 105, 4096, 22};\n\n"
             + "\n".join(arrays)).rstrip() + "\n")


def render_cs() -> str:
    return f'''// Generated by tools/build_endminf_m20_peak_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM20PeakCaptureData
    {{
        internal const string SourceSession = "20260828T224210Z";
        internal const int SourceFrame = {FRAME};
        internal const int DrawOrdinal = {DRAW_ORDINAL};
        internal const float PhaseSeconds = {PHASE_SECONDS:.6f}f;
        internal const bool PayloadPrepared = true;
        internal const string AtlasSha256 = "{ATLAS_SHA256}";
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
    build(args.capture.resolve(), args.cs_output.resolve(), args.cpp_output.resolve())
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
