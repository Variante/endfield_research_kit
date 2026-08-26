#!/usr/bin/env python3
"""Build phase-addressable native payloads for captured Endminf LitEffect draws."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260826T162514Z"
REPORT = (REPO / "reports/assets/character_recovery"
          / "endminf_liteffect_temporal_capture_latest.json")
CS_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM27TemporalCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M27TemporalCapturePayload.generated.h"
)
EXPECTED_SESSION = "20260826T162514Z"
VS_IDENTITY = 0xC0266E7FAC0046C1
PS_IDENTITY = 0x92D80A93ADD9C714
VS_DECLARED = (82, 20, 4091)
PS_DECLARED = (45, 106, 4085, 31, 1)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain one JSON object")
    return value


def is_m27_draw(draw: dict[str, Any]) -> bool:
    shaders = {row.get("stage"): row for row in draw.get("shaders", [])}
    return (
        draw.get("priorityShaderPair") is True
        and shaders.get(0, {}).get("identityHash") == VS_IDENTITY
        and shaders.get(4, {}).get("identityHash") == PS_IDENTITY
    )


def select_resource(metadata: dict[str, Any], kind: int, slot: int) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if row.get("captureKind") == kind and row.get("slot") == slot]
    require(len(rows) == 1, f"expected one capture kind {kind} slot {slot}")
    row = rows[0]
    require(row.get("completed") is True and row.get("failure") == 0,
            f"capture kind {kind} slot {slot} is incomplete")
    return row


def collect_constants(draw: dict[str, Any]) -> dict[int, list[bytes]]:
    captured = {(row.get("stage"), row.get("slot")): row
                for row in draw.get("constantBuffers", [])}
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage, declared in ((0, VS_DECLARED), (4, PS_DECLARED)):
        for slot, declared_count in enumerate(declared):
            row = captured.get((stage, slot))
            require(row is not None, f"M27 stage {stage} b{slot} is absent")
            require(row.get("rangeValid") is True and row.get("metadataValid") is True,
                    f"M27 stage {stage} b{slot} is invalid")
            payload = bytes.fromhex(row.get("dataHex", ""))
            require(payload and len(payload) % 16 == 0,
                    f"M27 stage {stage} b{slot} is not float4-aligned")
            result[stage].append(payload[:declared_count * 16])
    return result


def collect_frame(capture: Path, report_frame: dict[str, Any]) -> dict[str, Any]:
    frame = int(report_frame["frame"])
    root = capture / "graphics" / "frames" / str(frame)
    metadata = load_json(root / "metadata.json")
    metadata_hash = hashlib.sha256((root / "metadata.json").read_bytes()).hexdigest()
    require(metadata_hash == report_frame["metadataSha256"],
            f"frame {frame} metadata hash drifted")
    draws = [row for row in metadata.get("drawRecords", [])
             if isinstance(row, dict) and is_m27_draw(row)]
    require(len(draws) == report_frame["drawCount"],
            f"frame {frame} draw count drifted")
    if not draws:
        return {"frame": frame, "phase": float(report_frame["phaseSeconds"]),
                "draws": []}
    resources = (root / metadata.get("resourcesFile", "resources.bin")).read_bytes()
    vertex = select_resource(metadata, 0, 0)
    index = select_resource(metadata, 1, 0)
    default_vertex = select_resource(metadata, 0, 1)
    blob_start = int(vertex["blobOffset"])
    ring = resources[blob_start:blob_start + int(vertex["blobBytes"])]
    result_draws = []
    for draw, report_draw in zip(draws, report_frame["draws"]):
        require((draw["count"], draw["start"], draw["baseVertex"]) ==
                (report_draw["indexCount"], report_draw["startIndex"],
                 report_draw["baseVertex"]),
                f"frame {frame} report/draw identity drifted")
        vertex_start = int(vertex["byteOffset"]) + int(draw["baseVertex"]) * int(vertex["stride"])
        index_start = int(index["byteOffset"]) + int(draw["start"]) * 2
        vertex_count = int(report_draw["vertexCount"])
        vertex_size = vertex_count * int(vertex["stride"])
        index_size = int(draw["count"]) * 2
        vertices = ring[vertex_start:vertex_start + vertex_size]
        indices = ring[index_start:index_start + index_size]
        require(hashlib.sha256(vertices).hexdigest() == report_draw["vertexSha256"],
                f"frame {frame} vertex slice hash drifted")
        require(hashlib.sha256(indices).hexdigest() == report_draw["indexSha256"],
                f"frame {frame} index slice hash drifted")
        result_draws.append({
            "vertices": vertices,
            "indices": indices,
            "vertex_stride": int(vertex["stride"]),
            "vertex_count": vertex_count,
            "index_count": int(draw["count"]),
            "constants": collect_constants(draw),
        })
    default_start = int(default_vertex["blobOffset"])
    return {
        "frame": frame,
        "phase": float(report_frame["phaseSeconds"]),
        "draws": result_draws,
        "default_vertex": resources[default_start:default_start + 20],
    }


def collect_textures(capture: Path, frame: int = 2905) -> list[dict[str, Any]]:
    root = capture / "graphics" / "frames" / str(frame)
    metadata = load_json(root / "metadata.json")
    resources = (root / metadata.get("resourcesFile", "resources.bin")).read_bytes()
    textures = []
    rows = metadata.get("selectedResourceRecords", [])
    for slot in range(4):
        matches = [row for row in rows if row.get("captureKind") == 3 and
                   row.get("stage") == 4 and row.get("slot") == slot and
                   row.get("completed") is True and row.get("failure") == 0]
        require(len(matches) == 1, f"frame {frame} PS t{slot} is not uniquely retained")
        row = matches[0]
        start = int(row["blobOffset"])
        payload = resources[start:start + int(row["blobBytes"])]
        require(payload, f"frame {frame} PS t{slot} payload is empty")
        textures.append({
            "slot": slot,
            "width": int(row["width"]),
            "height": int(row["height"]),
            "format": int(row["format"]),
            "payload": payload,
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    # Retail binds the same 4x4 black SRGB fallback to t4 and t5.
    for slot in (4, 5):
        payload = bytes(4 * 4 * 4)
        textures.append({"slot": slot, "width": 4, "height": 4, "format": 29,
                         "payload": payload,
                         "sha256": hashlib.sha256(payload).hexdigest()})
    return textures


def collect(capture: Path, report_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    report = load_json(report_path)
    require(report.get("status") == "validated",
            "LitEffect temporal report is not valid")
    require(report.get("sessionId") == EXPECTED_SESSION,
            "LitEffect temporal report session drifted")
    frames = [collect_frame(capture, row) for row in report.get("frames", [])]
    require(len(frames) == report.get("sampleCount"), "M27 packet count drifted")
    defaults = {frame.get("default_vertex") for frame in frames if frame["draws"]}
    require(len(defaults) == 1, "M27 slot-1 carrier changes across packets")
    for frame in frames:
        frame["default_vertex"] = next(iter(defaults))
    return frames, collect_textures(capture)


def cpp_array(name: str, payload: bytes) -> str:
    lines = ["    " + ", ".join(f"0x{value:02x}" for value in payload[i:i + 16]) + ","
             for i in range(0, len(payload), 16)]
    return (f"inline constexpr std::uint8_t {name}[] = {{\n" + "\n".join(lines) +
            f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n")


def render_cpp(frames: list[dict[str, Any]], textures: list[dict[str, Any]]) -> str:
    arrays: list[str] = []
    draw_descriptors: list[str] = []
    frame_descriptors: list[str] = []
    draw_offset = 0
    maximum_draws = max(len(frame["draws"]) for frame in frames)
    default_vertex = next(frame["default_vertex"] for frame in frames if frame["draws"])
    arrays.append(cpp_array("g_EndfieldM27TemporalDefaultVertex", default_vertex))
    for texture in textures:
        arrays.append(cpp_array(
            f"g_EndfieldM27TemporalTexture{texture['slot']}", texture["payload"]))
    for frame_index, frame in enumerate(frames):
        for draw_index, draw in enumerate(frame["draws"]):
            prefix = f"g_EndfieldM27F{frame_index}D{draw_index}"
            arrays.append(cpp_array(prefix + "Vertices", draw["vertices"]))
            arrays.append(cpp_array(prefix + "Indices", draw["indices"]))
            for stage, label in ((0, "VS"), (4, "PS")):
                for slot, payload in enumerate(draw["constants"][stage]):
                    arrays.append(cpp_array(f"{prefix}{label}CB{slot}", payload))
            vs_ptr = ", ".join(f"{prefix}VSCB{i}" for i in range(3))
            vs_size = ", ".join(f"{prefix}VSCB{i}Size" for i in range(3))
            ps_ptr = ", ".join(f"{prefix}PSCB{i}" for i in range(5))
            ps_size = ", ".join(f"{prefix}PSCB{i}Size" for i in range(5))
            draw_descriptors.append(
                f"    {{{prefix}Vertices, {prefix}VerticesSize, {draw['vertex_stride']}u, "
                f"{prefix}Indices, {prefix}IndicesSize, {draw['index_count']}u, "
                f"{{{vs_ptr}}}, {{{vs_size}}}, {{{ps_ptr}}}, {{{ps_size}}}}},")
        pointer = "nullptr" if not frame["draws"] else f"g_EndfieldM27TemporalDraws + {draw_offset}"
        frame_descriptors.append(
            f"    {{{frame['frame']}u, {frame['phase']:.6f}f, {pointer}, "
            f"{len(frame['draws'])}u}},")
        draw_offset += len(frame["draws"])
    texture_descriptors = "\n".join(
        f"    {{g_EndfieldM27TemporalTexture{row['slot']}, "
        f"g_EndfieldM27TemporalTexture{row['slot']}Size, {row['width']}u, "
        f"{row['height']}u, {row['format']}u}}," for row in textures)
    return (
        "// Generated by tools/build_endminf_m27_temporal_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n" +
        "\n".join(arrays) + "\n"
        "inline constexpr std::uint32_t g_EndfieldM27TemporalVSDeclaredFloat4Counts[] = "
        "{82, 20, 4091};\n"
        "inline constexpr std::uint32_t g_EndfieldM27TemporalPSDeclaredFloat4Counts[] = "
        "{45, 106, 4085, 31, 1};\n"
        "struct EndfieldM27TemporalTexturePayload { const std::uint8_t* data; "
        "std::size_t bytes; std::uint32_t width; std::uint32_t height; "
        "std::uint32_t format; };\n"
        "inline constexpr EndfieldM27TemporalTexturePayload "
        "g_EndfieldM27TemporalTextures[] = {\n" + texture_descriptors + "\n};\n"
        "struct EndfieldM27TemporalDrawPayload { const std::uint8_t* vertices; "
        "std::size_t vertexBytes; std::uint32_t vertexStride; "
        "const std::uint8_t* indices; std::size_t indexBytes; "
        "std::uint32_t indexCount; const std::uint8_t* vs[3]; "
        "std::size_t vsBytes[3]; const std::uint8_t* ps[5]; "
        "std::size_t psBytes[5]; };\n"
        "inline constexpr EndfieldM27TemporalDrawPayload g_EndfieldM27TemporalDraws[] = {\n" +
        "\n".join(draw_descriptors) + "\n};\n"
        "struct EndfieldM27TemporalFramePayload { std::uint32_t frame; "
        "float phaseSeconds; const EndfieldM27TemporalDrawPayload* draws; "
        "std::uint32_t drawCount; };\n"
        "inline constexpr EndfieldM27TemporalFramePayload g_EndfieldM27TemporalFrames[] = {\n" +
        "\n".join(frame_descriptors) + "\n};\n"
        f"inline constexpr std::uint32_t g_EndfieldM27TemporalDrawCount = {draw_offset}u;\n"
        f"inline constexpr std::uint32_t g_EndfieldM27TemporalMaximumDrawsPerFrame = "
        f"{maximum_draws}u;\n"
        "inline constexpr std::uint32_t g_EndfieldM27TemporalFrameCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM27TemporalFrames) / "
        "sizeof(g_EndfieldM27TemporalFrames[0]));\n")


def render_cs(frames: list[dict[str, Any]], report_path: Path) -> str:
    phases = ", ".join(f"{row['phase']:.6f}f" for row in frames)
    source_frames = ", ".join(str(row["frame"]) for row in frames)
    draw_counts = ", ".join(str(len(row["draws"])) for row in frames)
    total = sum(len(row["draws"]) for row in frames)
    report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
    return f'''// Generated by tools/build_endminf_m27_temporal_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM27TemporalCaptureData
    {{
        internal const string SourceSession = "{EXPECTED_SESSION}";
        internal const string SourceReportSha256 = "{report_hash}";
        internal const int PacketCount = {len(frames)};
        internal const int TotalDrawCount = {total};
        internal static readonly int[] SourceFrames = {{ {source_frames} }};
        internal static readonly float[] PhaseSeconds = {{ {phases} }};
        internal static readonly int[] DrawCounts = {{ {draw_counts} }};
    }}
}}
'''


def build(capture: Path, report_path: Path, cs_output: Path,
          cpp_output: Path) -> str:
    frames, textures = collect(capture, report_path)
    cs_text = render_cs(frames, report_path)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(cs_text, encoding="utf-8", newline="\n")
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.write_text(render_cpp(frames, textures), encoding="utf-8", newline="\n")
    return cs_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--cs-output", type=Path, default=CS_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.capture, args.report, args.cs_output, args.cpp_output)
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
