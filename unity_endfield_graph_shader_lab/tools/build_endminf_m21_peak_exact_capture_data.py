#!/usr/bin/env python3
"""Build the exact Endminf M21 peak stone-shell packet from Full capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import build_endminf_m30_exact_capture_data as shared


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260828T004942Z"
FRAME = 2775
DRAW_ORDINAL = 74
PHASE_SECONDS = (273 - 3) / 60.0
FRAME_METADATA_SHA256 = "6038aec199ba5493cbadbed94594fad39c943e9215bc653b756facf0d2f3982e"
FRAME_RESOURCES_SHA256 = "0d6127cd7a89935d352000326b6253445bd9fcee504462ec2679e859e26413e9"
VS_SHA256 = "e7f5568d34fd467b63652eeef414e1506f41915f7296bb999226aa84e8ae4e00"
PS_SHA256 = "c5b21fee8e9936a6a37a5254dda91103a7be129e558fed4cdf02314058de6ab9"
VERTEX_SHA256 = "463aa8a3d7956663a3384848b76ee4239ad1bb21a9126010d4c166cbbb2bca92"
INDEX_SHA256 = "b68918aa41db6e3cea9b23bd95a5053525e56089931dab3a5d6c711bbefcb61c"
EXPECTED_VS_IDENTITY = 16714360756534855291
EXPECTED_PS_IDENTITY = 14245483680781383334
EXPECTED_INDEX_COUNT = 1110
EXPECTED_START_INDEX = 2844
EXPECTED_BASE_VERTEX = 1105
EXPECTED_VERTEX_STRIDE = 52
VS_DECLARED = (2, 82, 104, 4094, 10)
PS_DECLARED = (45, 105, 4085, 1, 22)
SHADER_ROOT = (
    REPO / "scratch/character_recovery/vfx_shader_variants/shader_export/Shader"
    / "HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode"
)
VS_DXBC = SHADER_ROOT / "4176_endfield_dxbc_0.dxbc"
PS_DXBC = SHADER_ROOT / "4177_endfield_dxbc_1.dxbc"
CS_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM21PeakCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M21PeakCapturePayload.generated.h"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def shader_ids(draw: dict[str, Any]) -> dict[int, int]:
    return {int(row["stage"]): int(row["identityHash"])
            for row in draw.get("shaders", [])}


def selected_record(metadata: dict[str, Any], kind: int, slot: int,
                    object_id: int) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict)
            and int(row.get("captureKind", -1)) == kind
            and int(row.get("slot", -1)) == slot
            and int(row.get("objectId", 0)) == object_id
            and row.get("completed") is True]
    shared.require(len(rows) == 1,
                   f"M21 capture kind {kind} slot {slot} is not uniquely complete")
    return rows[0]


def collect_constants(draw: dict[str, Any]) -> dict[int, list[bytes]]:
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage, declared in ((0, VS_DECLARED), (4, PS_DECLARED)):
        for slot, declared_count in enumerate(declared):
            payload = shared.constant(draw, stage, slot)
            shared.require(len(payload) >= 16,
                           f"M21 stage {stage} b{slot} has no retained vectors")
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
                   "M21 vertex stride drifted")
    shared.require(int(index_binding["format"]) == 57,
                   "M21 index format is not R16_UINT")
    shared.require(int(vertex_binding["objectId"]) == int(index_binding["objectId"]),
                   "M21 vertex/index arena identity drifted")

    vertex_record = selected_record(
        metadata, 0, 0, int(vertex_binding["objectId"]))
    index_record = selected_record(
        metadata, 1, 0, int(index_binding["objectId"]))
    secondary_record = selected_record(
        metadata, 0, 1, int(secondary_binding["objectId"]))
    blob = (frame_root / "resources.bin").read_bytes()

    index_start = (int(index_record.get("blobOffset", 0))
                   + int(index_binding["offset"])
                   + int(draw["start"]) * 2)
    index_bytes = blob[index_start:index_start + EXPECTED_INDEX_COUNT * 2]
    shared.require(len(index_bytes) == EXPECTED_INDEX_COUNT * 2,
                   "M21 index slice is truncated")
    indices = struct.unpack("<" + "H" * EXPECTED_INDEX_COUNT, index_bytes)
    shared.require(min(indices) == 0, "M21 draw-local indices no longer start at zero")
    vertex_count = max(indices) + 1
    vertex_start = (int(vertex_record.get("blobOffset", 0))
                    + int(vertex_binding["offset"])
                    + int(draw["baseVertex"]) * EXPECTED_VERTEX_STRIDE)
    vertex_bytes = blob[
        vertex_start:vertex_start + vertex_count * EXPECTED_VERTEX_STRIDE]
    shared.require(len(vertex_bytes) == vertex_count * EXPECTED_VERTEX_STRIDE,
                   "M21 vertex slice is truncated")

    secondary_start = int(secondary_record["blobOffset"])
    secondary = blob[secondary_start:secondary_start + 20]
    shared.require(len(secondary) == 20, "M21 secondary stream is truncated")
    shared.require(sha256(vertex_bytes) == VERTEX_SHA256,
                   "M21 vertex slice hash drifted")
    shared.require(sha256(index_bytes) == INDEX_SHA256,
                   "M21 index slice hash drifted")
    return vertex_bytes, index_bytes, secondary


def collect(capture: Path) -> dict[str, Any]:
    shared.require(capture.name == "20260828T004942Z", "M21 session drifted")
    frame_root = capture / "graphics/frames" / str(FRAME)
    metadata_path = frame_root / "metadata.json"
    resources_path = frame_root / "resources.bin"
    shared.require(sha256(metadata_path.read_bytes()) == FRAME_METADATA_SHA256,
                   "M21 metadata hash drifted")
    shared.require(sha256(resources_path.read_bytes()) == FRAME_RESOURCES_SHA256,
                   "M21 resources hash drifted")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = [row for row in metadata.get("drawRecords", [])
            if int(row.get("drawOrdinal", -1)) == DRAW_ORDINAL]
    shared.require(len(rows) == 1, "M21 draw ordinal is not unique")
    draw = rows[0]
    ids = shader_ids(draw)
    shared.require((ids.get(0), ids.get(4)) ==
                   (EXPECTED_VS_IDENTITY, EXPECTED_PS_IDENTITY),
                   "M21 shader pair drifted")
    shared.require((int(draw["count"]), int(draw["start"]),
                    int(draw["baseVertex"])) ==
                   (EXPECTED_INDEX_COUNT, EXPECTED_START_INDEX,
                    EXPECTED_BASE_VERTEX), "M21 draw geometry contract drifted")
    vs = VS_DXBC.read_bytes()
    ps = PS_DXBC.read_bytes()
    shared.require(sha256(vs) == VS_SHA256, "M21 vertex DXBC hash drifted")
    shared.require(sha256(ps) == PS_SHA256, "M21 pixel DXBC hash drifted")
    vertices, indices, secondary = collect_geometry(frame_root, metadata, draw)
    return {"vs": vs, "ps": ps, "vertices": vertices, "indices": indices,
            "secondary": secondary, "constants": collect_constants(draw)}


def render_cpp(packet: dict[str, Any]) -> str:
    arrays = [
        shared.cpp_array("g_EndfieldM21PeakVertexDxbc", packet["vs"]),
        shared.cpp_array("g_EndfieldM21PeakPixelDxbc", packet["ps"]),
        shared.cpp_array("g_EndfieldM21PeakVertices", packet["vertices"]),
        shared.cpp_array("g_EndfieldM21PeakIndices", packet["indices"]),
        shared.cpp_array("g_EndfieldM21PeakSecondary", packet["secondary"]),
    ]
    for stage, label in ((0, "VS"), (4, "PS")):
        for slot, payload in enumerate(packet["constants"][stage]):
            arrays.append(shared.cpp_array(
                f"g_EndfieldM21Peak{label}CB{slot}", payload))
    return (
        "// Generated by tools/build_endminf_m21_peak_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM21PeakPayloadPrepared = true;\n"
        f"inline constexpr float g_EndfieldM21PeakPhaseSeconds = {PHASE_SECONDS:.6f}f;\n"
        f"inline constexpr std::uint32_t g_EndfieldM21PeakVertexStride = {EXPECTED_VERTEX_STRIDE}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldM21PeakIndexCount = {EXPECTED_INDEX_COUNT}u;\n"
        "inline constexpr std::uint32_t g_EndfieldM21PeakVSDeclaredFloat4Counts[] = {2, 82, 104, 4094, 10};\n"
        "inline constexpr std::uint32_t g_EndfieldM21PeakPSDeclaredFloat4Counts[] = {45, 105, 4085, 1, 22};\n\n"
        + "\n".join(arrays)).rstrip() + "\n"


def render_cs() -> str:
    return f'''// Generated by tools/build_endminf_m21_peak_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM21PeakCaptureData
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
