#!/usr/bin/env python3
"""Build phase-addressable Unity/native payloads for captured Endminf M14 draws."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260826T091023Z"
REPORT = REPO / "reports/assets/character_recovery/endminf_m14_graphics_capture_latest.json"
LATE_CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260826T162514Z"
LATE_REPORT = (REPO / "reports/assets/character_recovery"
               / "endminf_m14_late_temporal_capture_latest.json")
OUTPUT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
          / "Runtime/Rendering/EndfieldRecoveredM14ExactCaptureData.generated.cs")
CPP_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
              / "M14CapturePayload.generated.h")
EXPECTED_SESSION = "20260826T091023Z"
EXPECTED_LATE_SESSION = "20260826T162514Z"
EXPECTED_FRAMES = (1405, 1413, 1421, 1429, 1437, 1445, 1453)
PACKET_PHASE_SECONDS = (4.50, 4.75, 5.00, 5.25, 5.50, 5.75, 6.00)
EXPECTED_VS = 0x62A5CE6C09171DE9
EXPECTED_PS = 0x5558DEDDB1EE6188
VERTEX_STRIDE = 36
DECLARED_COUNTS = {0: (2, 82, 104, 4094, 10), 4: (28, 105, 4085, 22)}
MINIMUM_COUNTS = {0: (2, 82, 104, 16, 10), 4: (28, 105, 5, 22)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def is_m14_draw(row: dict[str, Any]) -> bool:
    shaders = {item.get("stage"): item for item in row.get("shaders", [])}
    return (row.get("priorityShaderPair") is True and
            shaders.get(0, {}).get("identityHash") == EXPECTED_VS and
            shaders.get(4, {}).get("identityHash") == EXPECTED_PS)


def select_draw(metadata: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in metadata.get("drawRecords", []) if is_m14_draw(row)]
    rows = [row for row in rows
            if int(row.get("count", -1)) == int(expected["indexCount"])
            and int(row.get("start", -1)) == int(expected["startIndex"])
            and int(row.get("baseVertex", -1)) == int(expected["baseVertex"])
            and row.get("instanceCount") == 1]
    require(len(rows) == 1, "capture must contain one report-matched M14 draw")
    return rows[0]


def collect_constants(draw: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    captured = {(row.get("stage"), row.get("slot")): row
                for row in draw.get("constantBuffers", [])}
    result: dict[int, list[dict[str, Any]]] = {}
    for stage, declared_counts in DECLARED_COUNTS.items():
        rows = []
        for slot, declared_count in enumerate(declared_counts):
            source = captured.get((stage, slot))
            require(source is not None, f"captured M14 stage {stage} b{slot} is absent")
            require(source.get("rangeValid") is True and source.get("metadataValid") is True,
                    f"captured M14 stage {stage} b{slot} range is invalid")
            payload = bytes.fromhex(source.get("dataHex", ""))
            require(len(payload) % 16 == 0,
                    f"captured M14 stage {stage} b{slot} is not float4-aligned")
            captured_count = len(payload) // 16
            require(captured_count >= MINIMUM_COUNTS[stage][slot],
                    f"captured M14 stage {stage} b{slot} is too short: {captured_count}")
            payload = payload[:declared_count * 16]
            rows.append({"slot": slot, "declared_count": declared_count,
                         "captured_count": len(payload) // 16, "payload": payload,
                         "sha256": hashlib.sha256(payload).hexdigest()})
        result[stage] = rows
    return result


def collect_geometry(frame: Path, report_draw: dict[str, Any]) -> dict[str, Any]:
    geometry = report_draw.get("rawParticleGeometry")
    require(isinstance(geometry, dict), "M14 verifier has no raw geometry")
    quad_count = int(report_draw["quadCount"])
    require(geometry.get("vertexStride") == VERTEX_STRIDE and
            geometry.get("consumedQuadCount") == quad_count,
            "M14 raw geometry contract drifted")
    resources = (frame / "resources.bin").read_bytes()
    start = int(geometry["blobOffset"]) + int(geometry["streamByteOffset"])
    size = quad_count * 4 * VERTEX_STRIDE
    require(start >= 0 and start + size <= len(resources),
            "M14 vertex stream exceeds resources.bin")
    vertices = resources[start:start + size]
    indices: list[int] = []
    for quad in range(quad_count):
        base = quad * 4
        indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))
    return {"quad_count": quad_count, "vertex_count": quad_count * 4,
            "index_count": quad_count * 6, "vertices": vertices,
            "indices": struct.pack("<" + "H" * len(indices), *indices),
            "stream_offset": int(geometry["streamByteOffset"])}


def collect_packets(capture: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    require(report.get("status") == "validated", "M14 verifier report is not valid")
    require(report.get("sessionId") == EXPECTED_SESSION, "M14 verifier session drifted")
    report_frames = {int(row["frame"]): row for row in report.get("frames", [])}
    require(tuple(report_frames) == EXPECTED_FRAMES, "M14 verifier frame set drifted")
    packets = []
    for frame_id, phase in zip(EXPECTED_FRAMES, PACKET_PHASE_SECONDS):
        frame = capture / "graphics/frames" / str(frame_id)
        metadata = load_json(frame / "metadata.json")
        report_draws = report_frames[frame_id].get("m14Draws", [])
        require(len(report_draws) == 1, f"frame {frame_id} must contain one M14 draw")
        report_draw = report_draws[0]
        draw = select_draw(metadata, report_draw)
        packets.append({"frame": frame_id, "phase": phase,
                        "constants": collect_constants(draw),
                        "geometry": collect_geometry(frame, report_draw),
                        "metadata_sha256": hashlib.sha256(
                            (frame / "metadata.json").read_bytes()).hexdigest()})
    return packets


def collect_late_geometry(frame: Path, report_draw: dict[str, Any]) -> dict[str, Any]:
    geometry = report_draw.get("geometry")
    require(isinstance(geometry, dict), "late M14 verifier has no geometry")
    require(geometry.get("vertexStride") == VERTEX_STRIDE,
            "late M14 vertex stride drifted")
    resources = (frame / "resources.bin").read_bytes()
    ring_start = int(geometry["ringBlobOffset"])
    vertex_start = ring_start + int(geometry["effectiveVertexByteOffset"])
    vertex_size = int(geometry["vertexByteLength"])
    index_start = ring_start + int(geometry["effectiveIndexByteOffset"])
    index_size = int(geometry["indexByteLength"])
    require(vertex_start >= 0 and vertex_start + vertex_size <= len(resources),
            "late M14 vertex slice exceeds resources.bin")
    require(index_start >= 0 and index_start + index_size <= len(resources),
            "late M14 index slice exceeds resources.bin")
    vertices = resources[vertex_start:vertex_start + vertex_size]
    indices = resources[index_start:index_start + index_size]
    require(hashlib.sha256(vertices).hexdigest() == geometry["vertexSha256"],
            "late M14 vertex slice hash drifted")
    require(hashlib.sha256(indices).hexdigest() == geometry["indexSha256"],
            "late M14 index slice hash drifted")
    return {
        "quad_count": int(geometry["quadCount"]),
        "vertex_count": int(geometry["vertexCount"]),
        "index_count": int(geometry["indexCount"]),
        "vertices": vertices,
        "indices": indices,
        "stream_offset": int(geometry["effectiveVertexByteOffset"]),
    }


def select_late_draw(metadata: dict[str, Any], report_frame: dict[str, Any]) -> dict[str, Any]:
    expected_count = int(report_frame["geometry"]["indexCount"])
    expected_tint = struct.pack("<4f", *report_frame["psB3C4Tint"])
    matches = []
    for row in metadata.get("drawRecords", []):
        if not is_m14_draw(row) or int(row.get("count", -1)) != expected_count:
            continue
        b3_rows = [cb for cb in row.get("constantBuffers", [])
                   if cb.get("stage") == 4 and cb.get("slot") == 3]
        if len(b3_rows) != 1:
            continue
        payload = bytes.fromhex(b3_rows[0].get("dataHex", ""))
        if payload[64:80] == expected_tint:
            matches.append(row)
    require(len(matches) == 1,
            f"late M14 frame {report_frame['frame']} draw is not unique")
    return matches[0]


def collect_late_packets(capture: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    require(report.get("status") == "validated", "late M14 report is not valid")
    require(report.get("sessionId") == EXPECTED_LATE_SESSION,
            "late M14 report session drifted")
    packets = []
    for report_frame in report.get("frames", []):
        frame_id = int(report_frame["frame"])
        frame = capture / "graphics/frames" / str(frame_id)
        metadata_path = frame / "metadata.json"
        metadata = load_json(metadata_path)
        require(hashlib.sha256(metadata_path.read_bytes()).hexdigest() ==
                report_frame["metadataSha256"],
                f"late M14 frame {frame_id} metadata hash drifted")
        draw = select_late_draw(metadata, report_frame)
        packets.append({
            "frame": frame_id,
            "phase": float(report_frame["phaseSeconds"]),
            "constants": collect_constants(draw),
            "geometry": collect_late_geometry(frame, report_frame),
            "metadata_sha256": report_frame["metadataSha256"],
        })
    require(len(packets) == report.get("packetCount") == 9,
            "late M14 packet count drifted")
    return packets


def merge_packets(early: list[dict[str, Any]], late: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_phase = {round(packet["phase"], 6): packet for packet in early}
    by_phase.update({round(packet["phase"], 6): packet for packet in late})
    packets = [by_phase[key] for key in sorted(by_phase)]
    # The dense sequence owns the exact 5.25-second duplicate.
    require(len(packets) == 15, "combined M14 packet count drifted")
    return packets


def render_cpp_array(name: str, payload: bytes) -> str:
    lines = ["    " + ", ".join(f"0x{value:02x}" for value in payload[start:start + 16]) + ","
             for start in range(0, len(payload), 16)]
    return (f"inline constexpr std::uint8_t {name}[] = {{\n" + "\n".join(lines) +
            f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n")


def render_cpp(packets: list[dict[str, Any]]) -> str:
    arrays: list[str] = []
    descriptors: list[str] = []
    for packet_index, packet in enumerate(packets):
        prefix = f"g_EndfieldM14P{packet_index}"
        geometry = packet["geometry"]
        arrays.extend((render_cpp_array(prefix + "Vertices", geometry["vertices"]),
                       render_cpp_array(prefix + "Indices", geometry["indices"])))
        for stage, stage_name in ((0, "VS"), (4, "PS")):
            for row in packet["constants"][stage]:
                arrays.append(render_cpp_array(
                    f"{prefix}{stage_name}CB{row['slot']}", row["payload"]))
        vs_ptr = ", ".join(f"{prefix}VSCB{i}" for i in range(5))
        vs_size = ", ".join(f"{prefix}VSCB{i}Size" for i in range(5))
        ps_ptr = ", ".join(f"{prefix}PSCB{i}" for i in range(4))
        ps_size = ", ".join(f"{prefix}PSCB{i}Size" for i in range(4))
        descriptors.append(
            f"    {{{packet['frame']}u, {packet['phase']:.6f}f, {prefix}Vertices, "
            f"{prefix}VerticesSize, {prefix}Indices, {prefix}IndicesSize, "
            f"{geometry['index_count']}u, {{{vs_ptr}}}, {{{vs_size}}}, "
            f"{{{ps_ptr}}}, {{{ps_size}}}}},")
    return (
        "// Generated by tools/build_endminf_m14_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr std::uint32_t g_EndfieldM14VertexStride = 36;\n"
        "inline constexpr std::uint32_t g_EndfieldM14VSDeclaredFloat4Counts[] = "
        "{2, 82, 104, 4094, 10};\n"
        "inline constexpr std::uint32_t g_EndfieldM14PSDeclaredFloat4Counts[] = "
        "{28, 105, 4085, 22};\n\n" + "\n".join(arrays) + "\n"
        "struct EndfieldM14PacketPayload { std::uint32_t frame; float phaseSeconds; "
        "const std::uint8_t* vertices; std::size_t vertexBytes; "
        "const std::uint8_t* indices; std::size_t indexBytes; std::uint32_t indexCount; "
        "const std::uint8_t* vs[5]; std::size_t vsBytes[5]; "
        "const std::uint8_t* ps[4]; std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldM14PacketPayload g_EndfieldM14Packets[] = {\n" +
        "\n".join(descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM14PacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM14Packets) / "
        "sizeof(g_EndfieldM14Packets[0]));\n")


def render_cs(packets: list[dict[str, Any]], report_path: Path,
              late_report_path: Path) -> str:
    frames = ", ".join(str(row["frame"]) for row in packets)
    phases = ", ".join(f"{row['phase']:.6f}f" for row in packets)
    counts = ", ".join(str(row["geometry"]["index_count"]) for row in packets)
    report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
    late_report_hash = hashlib.sha256(late_report_path.read_bytes()).hexdigest()
    return f'''// Generated by tools/build_endminf_m14_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM14ExactCaptureData
    {{
        internal const string SourceSession = "{EXPECTED_SESSION}";
        internal const string LateSourceSession = "{EXPECTED_LATE_SESSION}";
        internal const string SourceReportSha256 = "{report_hash}";
        internal const string LateSourceReportSha256 = "{late_report_hash}";
        internal const int PacketCount = {len(packets)};
        internal static readonly int[] SourceFrames = {{ {frames} }};
        internal static readonly float[] PhaseSeconds = {{ {phases} }};
        internal static readonly int[] IndexCounts = {{ {counts} }};
    }}
}}
'''


def build(capture: Path, report_path: Path, output: Path,
          cpp_output: Path = CPP_OUTPUT, late_capture: Path = LATE_CAPTURE,
          late_report_path: Path = LATE_REPORT) -> str:
    report = load_json(report_path)
    late_report = load_json(late_report_path)
    packets = merge_packets(
        collect_packets(capture, report),
        collect_late_packets(late_capture, late_report))
    text = render_cs(packets, report_path, late_report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.write_text(render_cpp(packets), encoding="utf-8", newline="\n")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--late-capture", type=Path, default=LATE_CAPTURE)
    parser.add_argument("--late-report", type=Path, default=LATE_REPORT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.capture, args.report, args.output, args.cpp_output,
          args.late_capture, args.late_report)
    print(args.output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
