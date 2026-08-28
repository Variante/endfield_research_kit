#!/usr/bin/env python3
"""Build a fail-closed native payload for the captured Endminf M13 draw."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
SESSION = REPO / "scratch/reverse_engineering/endfield_capture/20260826T144934Z"
FRAME = SESSION / "graphics/frames/5404"
OUTPUT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
          / "Runtime/Rendering/EndfieldRecoveredM13ExactCaptureData.generated.cs")
CPP_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
              / "M13CapturePayload.generated.h")

PACKET_CONTRACTS = (
    {
        "frame": 5395,
        "reference_frame": 266,
        "metadata_sha256": "03886baf52e226a48ef9694ca98382eccc745f29479e9b0507f1ef969cc749e5",
        "resources_sha256": "ba5575eaa39efd4407aa71157b79050549a729fc14585d4d95c87ff1a541611e",
    },
    {
        "frame": 5404,
        "reference_frame": 275,
        "metadata_sha256": "1a67e671ad25f61fc9e9ee069515406fa61bb7a77478efa39fe85e43a34804b2",
        "resources_sha256": "8f80561c565eb007f3eafa1d0002717ae8633c5d0b01f35f62da0aa3e177ce5a",
    },
)
EXPECTED_VS = 0x96A93DCB3965CBED
EXPECTED_PS = 0x0265C7A6806A095F
EXPECTED_DRAW = (6, 1, 0)
VERTEX_STRIDE = 60
VERTEX_COUNT = 4
INDEX_PAYLOAD = struct.pack("<6H", 0, 1, 2, 0, 2, 3)
DECLARED_COUNTS = {0: (2, 82, 20, 4094, 4), 4: (28, 105, 4085, 50)}
TEXTURE_SHAPES = ((256, 256), (512, 512), (512, 512), (256, 256), (256, 256))
BC7_SRGB = 99
CAPTURE_FPS = 60.0
# Both frames use the same shared-ring IA binding. EndfieldCapture predates
# draw-local IA descriptors here, so the exact draw baseVertex resolves the
# owned quad within the selected ring allocation.
RING_VERTEX_BINDING_OFFSET = 930320


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def select_draw(metadata: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in metadata.get("drawRecords", []):
        shaders = {item.get("stage"): item for item in row.get("shaders", [])}
        draw_key = (row.get("count"), row.get("instanceCount"),
                    row.get("startInstance"))
        if (draw_key == EXPECTED_DRAW and row.get("indexedInstanced") is True and
                row.get("priorityShaderPair") is True and
                shaders.get(0, {}).get("identityHash") == EXPECTED_VS and
                shaders.get(4, {}).get("identityHash") == EXPECTED_PS):
            rows.append(row)
    require(len(rows) == 1, "capture must contain exactly one pinned M13 draw")
    return rows[0]


def selected_record(metadata: dict[str, Any], kind: int, stage: int,
                    slot: int) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if row.get("captureKind") == kind and row.get("stage") == stage and
            row.get("slot") == slot]
    require(len(rows) == 1,
            f"capture must contain one selected kind {kind} stage {stage} slot {slot}")
    row = rows[0]
    require(row.get("completed") is True and row.get("failure") == 0,
            f"selected kind {kind} stage {stage} slot {slot} did not complete")
    return row


def slice_record(resources: bytes, row: dict[str, Any]) -> bytes:
    start = int(row["blobOffset"])
    size = int(row["blobBytes"])
    require(start >= 0 and size > 0 and start + size <= len(resources),
            "selected resource exceeds resources.bin")
    return resources[start:start + size]


def collect_constants(draw: dict[str, Any], metadata: dict[str, Any],
                      resources: bytes) -> dict[int, list[dict[str, Any]]]:
    # EndfieldCapture selects every distinct allocation bound by the exact M13
    # draw. This closes ranges that the bounded per-draw preview may truncate.
    full_rows = {int(row["objectId"]): row
                 for row in metadata.get("selectedResourceRecords", [])
                 if row.get("captureKind") == 2 and row.get("completed") is True and
                 row.get("failure") == 0 and isinstance(row.get("objectId"), int)}
    captured = {(row.get("stage"), row.get("slot")): row
                for row in draw.get("constantBuffers", [])}
    result: dict[int, list[dict[str, Any]]] = {}
    for stage, counts in DECLARED_COUNTS.items():
        stage_rows = []
        for slot, count in enumerate(counts):
            row = captured.get((stage, slot))
            require(row is not None and row.get("rangeValid") is True and
                    row.get("metadataValid") is True,
                    f"M13 stage {stage} b{slot} range is absent or invalid")
            buffer_id = int(row["bufferId"])
            require(buffer_id in full_rows,
                    f"M13 stage {stage} b{slot} backing allocation was not selected")
            full = slice_record(resources, full_rows[buffer_id])
            start = int(row["firstConstant"]) * 16
            size = count * 16
            require(start >= 0 and start + size <= len(full),
                    f"M13 stage {stage} b{slot} exceeds the selected allocation")
            payload = full[start:start + size]
            preview = bytes.fromhex(row.get("dataHex", ""))
            overlap = min(len(payload), len(preview))
            require(payload[:overlap] == preview[:overlap],
                    f"M13 stage {stage} b{slot} full-buffer bytes disagree with preview")
            stage_rows.append({"slot": slot, "declared_count": count,
                               "payload": payload, "sha256": sha256(payload)})
        result[stage] = stage_rows
    return result


def is_geometry_candidate(ring: bytes, offset: int) -> bool:
    expected_uv = ((0.0, 1.0, 0.0, 1.0), (1.0, 1.0, 1.0, 1.0),
                   (1.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 0.0))
    custom = None
    color = None
    for vertex, uv in enumerate(expected_uv):
        start = offset + vertex * VERTEX_STRIDE
        position = struct.unpack_from("<3f", ring, start)
        if not all(math.isfinite(value) and -1000.0 < value < 1000.0 for value in position):
            return False
        current_color = ring[start + 24:start + 28]
        if color is None:
            color = current_color
        elif current_color != color:
            return False
        if struct.unpack_from("<4f", ring, start + 28) != uv:
            return False
        current_custom = struct.unpack_from("<4f", ring, start + 44)
        if struct.pack("<f", current_custom[1]) != struct.pack("<f", 0.516995132):
            return False
        if current_custom[3] != 0.0:
            return False
        if custom is None:
            custom = current_custom
        elif current_custom != custom:
            return False
    return True


def collect_geometry(draw: dict[str, Any], metadata: dict[str, Any],
                     resources: bytes) -> dict[str, Any]:
    ring = slice_record(resources, selected_record(metadata, 4, 5, 0))
    size = VERTEX_STRIDE * VERTEX_COUNT
    offset = RING_VERTEX_BINDING_OFFSET + int(draw["baseVertex"]) * VERTEX_STRIDE
    require(offset >= 0 and offset + size <= len(ring) and
            is_geometry_candidate(ring, offset),
            "M13 draw-local baseVertex does not resolve a valid shared-ring quad")
    payload = ring[offset:offset + size]
    return {"vertices": payload, "indices": INDEX_PAYLOAD, "ring_offset": offset,
            "vertex_sha256": sha256(payload), "index_sha256": sha256(INDEX_PAYLOAD)}


def collect_textures(metadata: dict[str, Any], resources: bytes) -> list[dict[str, Any]]:
    result = []
    for slot, (width, height) in enumerate(TEXTURE_SHAPES):
        row = selected_record(metadata, 3, 4, slot)
        expected_bytes = width * height
        require(row.get("width") == width and row.get("height") == height and
                row.get("format") == BC7_SRGB and row.get("viewFormat") == BC7_SRGB and
                row.get("subresource") == 0 and row.get("blobBytes") == expected_bytes,
                f"M13 t{slot} BC7 mip-0 contract drifted")
        payload = slice_record(resources, row)
        result.append({"slot": slot, "width": width, "height": height,
                       "payload": payload, "sha256": sha256(payload)})
    return result


def render_cpp_array(name: str, payload: bytes) -> str:
    rows = ["    " + ", ".join(f"0x{value:02x}" for value in payload[start:start + 16]) + ","
            for start in range(0, len(payload), 16)]
    return (f"inline constexpr std::uint8_t {name}[] = {{\n" + "\n".join(rows) +
            f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n")


def render_cpp(packets: list[dict[str, Any]]) -> str:
    arrays = [render_cpp_array("g_EndfieldM13Indices", INDEX_PAYLOAD)]
    descriptors = []
    for index, packet in enumerate(packets):
        prefix = f"g_EndfieldM13P{index}"
        arrays.append(render_cpp_array(prefix + "Vertices",
                                       packet["geometry"]["vertices"]))
        for stage, label in ((0, "VS"), (4, "PS")):
            arrays.extend(render_cpp_array(
                f"{prefix}{label}CB{row['slot']}", row["payload"])
                for row in packet["constants"][stage])
        descriptors.append(
            f"    {{{packet['frame']}u, {packet['phase']:.6f}f, "
            f"{prefix}Vertices, {prefix}VerticesSize, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
    arrays.extend(render_cpp_array(f"g_EndfieldM13Texture{row['slot']}", row["payload"])
                  for row in packets[0]["textures"])
    texture_desc = ",\n".join(
        f"    {{g_EndfieldM13Texture{row['slot']}, g_EndfieldM13Texture{row['slot']}Size, "
        f"{row['width']}u, {row['height']}u}}" for row in packets[0]["textures"])
    return (
        "// Generated by tools/build_endminf_m13_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr std::uint32_t g_EndfieldM13VertexStride = 60;\n"
        "inline constexpr std::uint32_t g_EndfieldM13VSDeclaredFloat4Counts[] = "
        "{2, 82, 20, 4094, 4};\n"
        "inline constexpr std::uint32_t g_EndfieldM13PSDeclaredFloat4Counts[] = "
        "{28, 105, 4085, 50};\n\n" + "\n".join(arrays) + "\n"
        "struct EndfieldM13PacketPayload { std::uint32_t frame; float phaseSeconds; "
        "const std::uint8_t* vertices; std::size_t vertexBytes; "
        "const std::uint8_t* vs[5]; std::size_t vsBytes[5]; "
        "const std::uint8_t* ps[4]; std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldM13PacketPayload g_EndfieldM13Packets[] = {\n" +
        "\n".join(descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM13PacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM13Packets) / "
        "sizeof(g_EndfieldM13Packets[0]));\n"
        "struct EndfieldM13TexturePayload { const std::uint8_t* bytes; std::size_t size; "
        "std::uint32_t width; std::uint32_t height; };\n"
        "inline constexpr EndfieldM13TexturePayload g_EndfieldM13Textures[] = {\n" +
        texture_desc + "\n};\n")


def render_cs(packets: list[dict[str, Any]]) -> str:
    texture_hashes = ", ".join(
        f'"{row["sha256"]}"' for row in packets[0]["textures"])
    frames = ", ".join(str(packet["frame"]) for packet in packets)
    phases = ", ".join(f'{packet["phase"]:.6f}f' for packet in packets)
    offsets = ", ".join(
        str(packet["geometry"]["ring_offset"]) for packet in packets)
    vertex_hashes = ", ".join(
        f'"{packet["geometry"]["vertex_sha256"]}"' for packet in packets)
    return f'''// Generated by tools/build_endminf_m13_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM13ExactCaptureData
    {{
        internal const string SourceSession = "20260826T144934Z";
        internal const int PacketCount = {len(packets)};
        internal static readonly int[] SourceFrames = {{ {frames} }};
        internal static readonly float[] PhaseSeconds = {{ {phases} }};
        internal static readonly int[] RingByteOffsets = {{ {offsets} }};
        internal static readonly string[] VertexSha256 = {{ {vertex_hashes} }};
        internal static readonly string[] TextureSha256 = {{ {texture_hashes} }};
    }}
}}
'''


def build(output: Path = OUTPUT, cpp_output: Path = CPP_OUTPUT) -> str:
    packets = []
    texture_hashes: list[str] | None = None
    for contract in PACKET_CONTRACTS:
        frame_id = int(contract["frame"])
        frame = SESSION / "graphics/frames" / str(frame_id)
        metadata_bytes = (frame / "metadata.json").read_bytes()
        resources = (frame / "resources.bin").read_bytes()
        require(sha256(metadata_bytes) == contract["metadata_sha256"],
                f"M13 frame {frame_id} metadata hash drifted")
        require(sha256(resources) == contract["resources_sha256"],
                f"M13 frame {frame_id} resources hash drifted")
        metadata = json.loads(metadata_bytes)
        require(metadata.get("captureIncomplete") is not True and
                metadata.get("captureFailed") is not True,
                f"M13 frame {frame_id} is incomplete")
        draw = select_draw(metadata)
        textures = collect_textures(metadata, resources)
        current_hashes = [row["sha256"] for row in textures]
        if texture_hashes is None:
            texture_hashes = current_hashes
        require(current_hashes == texture_hashes,
                "M13 textures changed across temporal packets")
        packets.append({
            "frame": frame_id,
            "phase": (int(contract["reference_frame"]) - 3) / CAPTURE_FPS,
            "constants": collect_constants(draw, metadata, resources),
            "geometry": collect_geometry(draw, metadata, resources),
            "textures": textures,
        })
    text = render_cs(packets)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.write_text(render_cpp(packets), encoding="utf-8", newline="\n")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.output, args.cpp_output)
    print(args.output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
