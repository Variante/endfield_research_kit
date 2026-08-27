#!/usr/bin/env python3
"""Build fail-closed M30 temporal payloads while retail scene depth is pending."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
TEMPORAL_CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260826T162514Z"
TEMPORAL_REPORT = (REPO / "reports/assets/character_recovery"
                   / "endminf_m29_m30_temporal_capture_latest.json")
RESOURCE_CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260827T081152Z"
CS_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
             / "Runtime/Rendering/EndfieldRecoveredM30ExactCaptureData.generated.cs")
CPP_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
              / "M30CapturePayload.generated.h")
EXPECTED_TEMPORAL_SESSION = "20260826T162514Z"
EXPECTED_RESOURCE_SESSION = "20260827T081152Z"
EXPECTED_RESOURCE_FRAME = 1845
EXPECTED_VS = 0x62A5CE6C09171DE9
EXPECTED_PS = 0x5558DEDDB1EE6188
EXPECTED_C1 = (1.0, 0.0, 3.0, 0.5)
EXPECTED_C4 = (0.93269453, 0.52442606, 0.09170079, 1.0)
VERTEX_STRIDE = 36
INDEX_FORMAT = 57
TEXTURE_FORMAT = 99
TEXTURE_WIDTH = 256
TEXTURE_HEIGHT = 256
VS_DECLARED = (2, 82, 104, 4094, 10)
PS_DECLARED = (28, 105, 4085, 22)
VS_MINIMUM = (2, 82, 104, 16, 10)
PS_MINIMUM = (28, 105, 16, 22)
PARTICLE_UVS = ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def shader_pair_matches(draw: dict[str, Any]) -> bool:
    pair = {row.get("stage"): row.get("identityHash")
            for row in draw.get("shaders", []) if isinstance(row, dict)}
    return (draw.get("priorityShaderPair") is True and
            pair.get(0) == EXPECTED_VS and pair.get(4) == EXPECTED_PS)


def constant(draw: dict[str, Any], stage: int, slot: int) -> bytes:
    rows = [row for row in draw.get("constantBuffers", [])
            if row.get("stage") == stage and row.get("slot") == slot]
    require(len(rows) == 1, f"M30 stage {stage} b{slot} is not unique")
    row = rows[0]
    require(row.get("rangeValid") is True and row.get("metadataValid") is True,
            f"M30 stage {stage} b{slot} range is invalid")
    payload = bytes.fromhex(row.get("dataHex", ""))
    require(payload and len(payload) % 16 == 0,
            f"M30 stage {stage} b{slot} is not float4-aligned")
    return payload


def vector(payload: bytes, index: int) -> tuple[float, float, float, float]:
    require((index + 1) * 16 <= len(payload), f"M30 c{index} is absent")
    return struct.unpack_from("<4f", payload, index * 16)


def close(actual: tuple[float, ...], expected: tuple[float, ...]) -> bool:
    return all(math.isclose(a, b, rel_tol=0.0, abs_tol=2.0e-6)
               for a, b in zip(actual, expected))


def is_m30(draw: dict[str, Any]) -> bool:
    if not shader_pair_matches(draw):
        return False
    try:
        b3 = constant(draw, 4, 3)
    except ValueError:
        return False
    return close(vector(b3, 1), EXPECTED_C1) and close(vector(b3, 4), EXPECTED_C4)


def select_draw(metadata: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in metadata.get("drawRecords", [])
            if isinstance(row, dict) and is_m30(row)]
    rows = [row for row in rows
            if int(row.get("count", -1)) == int(expected["indexCount"])
            and int(row.get("start", -1)) == int(expected["startIndex"])
            and int(row.get("baseVertex", -1)) == int(expected["baseVertex"])
            and int(row.get("instanceCount", -1)) == 1]
    require(len(rows) == 1,
            f"M30 frame {expected['frame']} draw is not uniquely report-matched")
    return rows[0]


def collect_constants(draw: dict[str, Any]) -> dict[int, list[bytes]]:
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage, declared, minimum in ((0, VS_DECLARED, VS_MINIMUM),
                                      (4, PS_DECLARED, PS_MINIMUM)):
        for slot, (declared_count, minimum_count) in enumerate(zip(declared, minimum)):
            payload = constant(draw, stage, slot)
            require(len(payload) // 16 >= minimum_count,
                    f"M30 stage {stage} b{slot} retained only {len(payload) // 16} vectors")
            result[stage].append(payload[:declared_count * 16])
    return result


def one_binding(metadata: dict[str, Any], kind: int, object_id: int | None = None
                ) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict) and row.get("captureKind") == kind
            and row.get("slot") == 0 and row.get("completed") is True]
    if object_id is not None:
        rows = [row for row in rows if int(row.get("objectId", 0)) == object_id]
    if kind == 0:
        rows = [row for row in rows if int(row.get("blobBytes", 0)) == 4194304]
    require(len(rows) == 1, f"M30 IA captureKind {kind} is not unique")
    return rows[0]


def canonical_indices(quad_count: int) -> bytes:
    values: list[int] = []
    for quad in range(quad_count):
        base = quad * 4
        values.extend((base, base + 1, base + 2, base, base + 2, base + 3))
    return struct.pack("<" + "H" * len(values), *values)


def quad_is_canonical(data: bytes, offset: int) -> bool:
    if offset < 0 or offset + 4 * VERTEX_STRIDE > len(data):
        return False
    for vertex, expected_uv in enumerate(PARTICLE_UVS):
        values = struct.unpack_from("<6fI2f", data, offset + vertex * VERTEX_STRIDE)
        if not all(math.isfinite(value) for value in values[:6] + values[7:9]):
            return False
        if values[7:9] != expected_uv:
            return False
    return True


def collect_geometry(frame_root: Path, metadata: dict[str, Any],
                     draw: dict[str, Any]) -> dict[str, Any]:
    vertex = one_binding(metadata, 0)
    index = one_binding(metadata, 1, int(vertex["objectId"]))
    require(index.get("stride") == 2 and index.get("format") == INDEX_FORMAT,
            "M30 index binding is not R16_UINT")
    require(vertex.get("blobOffset") == index.get("blobOffset") and
            vertex.get("blobBytes") == index.get("blobBytes"),
            "M30 IA vertex/index ring alias drifted")
    resources = (frame_root / "resources.bin").read_bytes()
    blob_offset = int(vertex["blobOffset"])
    blob_bytes = int(vertex["blobBytes"])
    require(blob_offset >= 0 and blob_offset + blob_bytes <= len(resources),
            "M30 IA ring exceeds resources.bin")
    ring = resources[blob_offset:blob_offset + blob_bytes]
    quad_count = int(draw["count"]) // 6
    require(quad_count in (1, 2), "M30 draw is not the captured one/two-quad topology")
    vertex_offset = int(vertex["byteOffset"]) + int(draw["baseVertex"]) * VERTEX_STRIDE
    index_offset = int(index["byteOffset"]) + int(draw["start"]) * 2
    vertex_bytes = quad_count * 4 * VERTEX_STRIDE
    expected_indices = canonical_indices(quad_count)
    require(vertex_offset + vertex_bytes <= len(ring), "M30 vertex slice exceeds IA ring")
    require(index_offset + len(expected_indices) <= len(ring),
            "M30 index slice exceeds IA ring")
    for quad in range(quad_count):
        require(quad_is_canonical(ring, vertex_offset + quad * 4 * VERTEX_STRIDE),
                "M30 expanded quad is not canonical 36-byte particle data")
    require(ring[index_offset:index_offset + len(expected_indices)] == expected_indices,
            "M30 index slice is not canonical quad topology")
    return {
        "vertices": ring[vertex_offset:vertex_offset + vertex_bytes],
        "indices": expected_indices,
        "index_count": len(expected_indices) // 2,
        "vertex_offset": vertex_offset,
        "index_offset": index_offset,
    }


def collect_secondary_stream(frame_root: Path, metadata: dict[str, Any]) -> bytes:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict) and row.get("captureKind") == 0
            and row.get("slot") == 1 and row.get("completed") is True
            and int(row.get("blobBytes", 0)) == 20]
    require(len(rows) == 1, "M30 secondary IA stream is not unique")
    row = rows[0]
    resources = (frame_root / "resources.bin").read_bytes()
    start = int(row["blobOffset"])
    payload = resources[start:start + 20]
    require(len(payload) == 20, "M30 secondary IA stream is truncated")
    return payload


def collect_texture(capture: Path) -> dict[str, Any]:
    frame_root = capture / "graphics/frames" / str(EXPECTED_RESOURCE_FRAME)
    metadata = load_json(frame_root / "metadata.json")
    matches = [row for row in metadata.get("drawRecords", [])
               if isinstance(row, dict) and is_m30(row)]
    require(len(matches) == 1, "resource capture must contain one exact M30 draw")
    draw = matches[0]
    resources_by_key = {(int(row.get("objectId", 0)), int(row.get("stage", -1)),
                         int(row.get("slot", -1))): row
                        for row in metadata.get("selectedResourceRecords", [])
                        if isinstance(row, dict)}
    owned = [row for row in draw.get("resources", [])
             if row.get("stage") == 4 and row.get("slot") == 1]
    require(len(owned) == 1, "M30 draw does not own one PS t1")
    selected = resources_by_key.get((int(owned[0]["objectId"]), 4, 1))
    require(selected is not None and selected.get("completed") is True,
            "M30 PS t1 was not retained")
    require((selected.get("format"), selected.get("viewFormat"),
             selected.get("width"), selected.get("height")) ==
            (TEXTURE_FORMAT, TEXTURE_FORMAT, TEXTURE_WIDTH, TEXTURE_HEIGHT),
            "M30 PS t1 descriptor drifted")
    resources = (frame_root / "resources.bin").read_bytes()
    start = int(selected["blobOffset"])
    size = int(selected["blobBytes"])
    payload = resources[start:start + size]
    require(len(payload) == 65536, "M30 PS t1 payload size drifted")
    return {"payload": payload, "sha256": sha256_bytes(payload),
            "metadata_sha256": sha256_bytes((frame_root / "metadata.json").read_bytes())}


def collect_packets(capture: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    require(report.get("sessionId") == EXPECTED_TEMPORAL_SESSION,
            "M30 temporal report session drifted")
    owner = report.get("owners", {}).get("M30", {})
    frames = owner.get("frames", [])
    require(owner.get("packetCount") == len(frames) == 11,
            "M30 temporal packet count drifted")
    packets = []
    secondary_hash: str | None = None
    for expected in frames:
        frame_root = capture / "graphics/frames" / str(expected["frame"])
        metadata_path = frame_root / "metadata.json"
        require(sha256_bytes(metadata_path.read_bytes()) == expected["metadataSha256"],
                f"M30 frame {expected['frame']} metadata hash drifted")
        metadata = load_json(metadata_path)
        draw = select_draw(metadata, expected)
        secondary = collect_secondary_stream(frame_root, metadata)
        current_secondary_hash = sha256_bytes(secondary)
        if secondary_hash is None:
            secondary_hash = current_secondary_hash
        require(current_secondary_hash == secondary_hash,
                "M30 secondary IA stream changed across temporal packets")
        packets.append({
            "frame": int(expected["frame"]),
            "phase": float(expected["phaseSeconds"]),
            "constants": collect_constants(draw),
            "geometry": collect_geometry(frame_root, metadata, draw),
            "secondary": secondary,
        })
    return packets


def cpp_array(name: str, payload: bytes) -> str:
    rows = ["    " + ", ".join(f"0x{x:02x}" for x in payload[i:i + 16]) + ","
            for i in range(0, len(payload), 16)]
    return (f"inline constexpr std::uint8_t {name}[] = {{\n" + "\n".join(rows) +
            f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n")


def render_cpp(packets: list[dict[str, Any]], texture: dict[str, Any]) -> str:
    arrays = [cpp_array("g_EndfieldM30TextureT1", texture["payload"])]
    descriptors = []
    for index, packet in enumerate(packets):
        prefix = f"g_EndfieldM30P{index}"
        arrays.extend((cpp_array(prefix + "Vertices", packet["geometry"]["vertices"]),
                       cpp_array(prefix + "Indices", packet["geometry"]["indices"]),
                       cpp_array(prefix + "Secondary", packet["secondary"])))
        for stage, label in ((0, "VS"), (4, "PS")):
            for slot, payload in enumerate(packet["constants"][stage]):
                arrays.append(cpp_array(f"{prefix}{label}CB{slot}", payload))
        descriptors.append(
            f"    {{{packet['frame']}u, {packet['phase']:.6f}f, "
            f"{prefix}Vertices, {prefix}VerticesSize, {prefix}Indices, "
            f"{prefix}IndicesSize, {packet['geometry']['index_count']}u, "
            f"{prefix}Secondary, {prefix}SecondarySize, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
    return (
        "// Generated by tools/build_endminf_m30_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM30PayloadPrepared = true;\n"
        "inline constexpr bool g_EndfieldM30DepthContractReady = false;\n"
        "inline constexpr std::uint32_t g_EndfieldM30VertexStride = 36;\n"
        "inline constexpr std::uint32_t g_EndfieldM30TextureFormat = 99;\n"
        "inline constexpr std::uint32_t g_EndfieldM30TextureWidth = 256;\n"
        "inline constexpr std::uint32_t g_EndfieldM30TextureHeight = 256;\n"
        "inline constexpr std::uint32_t g_EndfieldM30VSDeclaredFloat4Counts[] = {2, 82, 104, 4094, 10};\n"
        "inline constexpr std::uint32_t g_EndfieldM30PSDeclaredFloat4Counts[] = {28, 105, 4085, 22};\n\n" +
        "\n".join(arrays) + "\n"
        "struct EndfieldM30PacketPayload { std::uint32_t frame; float phaseSeconds; "
        "const std::uint8_t* vertices; std::size_t vertexBytes; "
        "const std::uint8_t* indices; std::size_t indexBytes; std::uint32_t indexCount; "
        "const std::uint8_t* secondary; std::size_t secondaryBytes; "
        "const std::uint8_t* vs[5]; std::size_t vsBytes[5]; "
        "const std::uint8_t* ps[4]; std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldM30PacketPayload g_EndfieldM30Packets[] = {\n" +
        "\n".join(descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM30PacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM30Packets) / "
        "sizeof(g_EndfieldM30Packets[0]));\n")


def render_cs(packets: list[dict[str, Any]], texture: dict[str, Any],
              report_path: Path) -> str:
    frames = ", ".join(str(row["frame"]) for row in packets)
    phases = ", ".join(f"{row['phase']:.6f}f" for row in packets)
    counts = ", ".join(str(row["geometry"]["index_count"]) for row in packets)
    return f'''// Generated by tools/build_endminf_m30_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM30ExactCaptureData
    {{
        internal const string TemporalSourceSession = "{EXPECTED_TEMPORAL_SESSION}";
        internal const string ResourceSourceSession = "{EXPECTED_RESOURCE_SESSION}";
        internal const string TemporalReportSha256 = "{sha256_bytes(report_path.read_bytes())}";
        internal const string TextureT1Sha256 = "{texture['sha256']}";
        internal const bool PayloadPrepared = true;
        internal const bool DepthContractReady = false;
        internal const int PacketCount = {len(packets)};
        internal static readonly int[] SourceFrames = {{ {frames} }};
        internal static readonly float[] PhaseSeconds = {{ {phases} }};
        internal static readonly int[] IndexCounts = {{ {counts} }};
    }}
}}
'''


def build(temporal_capture: Path, report_path: Path, resource_capture: Path,
          cs_output: Path, cpp_output: Path) -> tuple[str, str]:
    require(temporal_capture.name == EXPECTED_TEMPORAL_SESSION,
            "temporal capture session drifted")
    require(resource_capture.name == EXPECTED_RESOURCE_SESSION,
            "resource capture session drifted")
    report = load_json(report_path)
    packets = collect_packets(temporal_capture, report)
    texture = collect_texture(resource_capture)
    cs = render_cs(packets, texture, report_path)
    cpp = render_cpp(packets, texture)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(cs, encoding="utf-8", newline="\n")
    cpp_output.write_text(cpp, encoding="utf-8", newline="\n")
    return cs, cpp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temporal-capture", type=Path, default=TEMPORAL_CAPTURE)
    parser.add_argument("--report", type=Path, default=TEMPORAL_REPORT)
    parser.add_argument("--resource-capture", type=Path, default=RESOURCE_CAPTURE)
    parser.add_argument("--cs-output", type=Path, default=CS_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.temporal_capture.resolve(), args.report.resolve(),
          args.resource_capture.resolve(), args.cs_output.resolve(),
          args.cpp_output.resolve())
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
