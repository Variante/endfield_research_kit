#!/usr/bin/env python3
"""Build the fail-closed exact payload for Endminf's opening strip owner."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
SESSION = REPO / "scratch/reverse_engineering/endfield_capture/20260828T181119Z"
OUTPUT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
          / "Runtime/Rendering/EndfieldRecoveredOpeningStripCaptureData.generated.cs")
CPP_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
              / "OpeningStripCapturePayload.generated.h")
SHADER_ROOT = (REPO / "scratch/character_recovery/vfx_shader_variants/shader_export"
               / "Shader/HGRP_Effect_VFXRefract_p6BC753C54B47D1ED.shader.bytecode")

VS_PATH = SHADER_ROOT / "0546_endfield_dxbc_0.dxbc"
PS_PATH = SHADER_ROOT / "0547_endfield_dxbc_1.dxbc"
VS_SHA256 = "297e7323cb0a7c42f4e80ad4d5fbacc89ac2c278e549b0fa0e69af190736eccf"
PS_SHA256 = "76db04f0bc22dd3e8b297e213f44bd0331fc699522adaaab8f0d082e7e0d1d0e"
VS_IDENTITY = 2989953800188099650
PS_IDENTITY = 8564444548370193726
VERTEX_STRIDE = 60
VS_COUNTS = (2, 82, 20, 4094, 5)
PS_COUNTS = (28, 104, 4085, 12)

# The four automatic tail packets bracket the source particle simulation at
# these 60 Hz phases. This is the narrow evidence window; it must not be
# extrapolated into the rest of overview_start.
PACKETS = (
    (1034, 0.150000,
     "1dcc1dbf181f13e396c5c4dc020644a3e68f98ca4dd440e1cfce99d25aee5b98",
     "626ee9cf02d40fbea226e8fd2634789b7ec5055424b598c0188fb179ec22bf58"),
    (1035, 0.183333,
     "f8f8371c70bea13daf359b97ed87792a4ebe9116e5a991ff163577028ef0e7a8",
     "5240d8fd72444978f8f07494d62331246dfb8aceff2f54a6cced980d2858143b"),
    (1036, 0.216667,
     "f4f8aecfeadbe5548c2de6c1ec908bd4c50863608d8ea6a766e7238f55a19fb5",
     "e989ee1b514f82e2f326258503780e9ff00ab088cccc459f319ce30da1db59d0"),
    (1037, 0.250000,
     "bf61c3fa1be96aca386ebf43bdeb84861c1e1dbf77078bb6eaad576fc9a3213a",
     "dd62336e75a73db4db226f1d065ce5c2cb964c517a5737b8dcb52beef3da7c5f"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def shader_pair(draw: dict[str, Any]) -> tuple[int, int] | None:
    rows = {int(row.get("stage", -1)): int(row.get("identityHash", -1))
            for row in draw.get("shaders", [])}
    return (rows[0], rows[4]) if 0 in rows and 4 in rows else None


def selected_record(metadata: dict[str, Any], kind: int,
                    object_id: int) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if int(row.get("captureKind", -1)) == kind
            and int(row.get("objectId", -1)) == object_id
            and row.get("completed") is True and int(row.get("failure", 0)) == 0]
    # Selected vertex rows may be duplicated by independent priority owners;
    # they refer to the same retained allocation and byte range.
    require(rows, f"selected kind {kind} object {object_id} is absent")
    first = rows[0]
    require(all(int(row["blobOffset"]) == int(first["blobOffset"])
                and int(row["blobBytes"]) == int(first["blobBytes"])
                for row in rows),
            f"selected kind {kind} object {object_id} is ambiguous")
    return first


def slice_record(resources: bytes, row: dict[str, Any]) -> bytes:
    offset = int(row["blobOffset"])
    size = int(row["blobBytes"])
    result = resources[offset:offset + size]
    require(len(result) == size, "selected resource exceeds resources.bin")
    return result


def collect_geometry(draw: dict[str, Any], metadata: dict[str, Any],
                     resources: bytes) -> tuple[bytes, bytes]:
    ia = draw.get("inputAssembler", {})
    vertices = [row for row in ia.get("vertexBuffers", [])
                if int(row.get("slot", -1)) == 0]
    index = ia.get("indexBuffer", {})
    require(len(vertices) == 1 and isinstance(index, dict),
            "opening IA descriptor is incomplete")
    vertex = vertices[0]
    require(int(vertex.get("stride", -1)) == VERTEX_STRIDE,
            "opening vertex stride drifted")
    require(int(index.get("format", -1)) == 57,
            "opening index format is not R16_UINT")
    count = int(draw["count"])
    require(count > 0 and count % 6 == 0, "opening indices are not quad-aligned")
    vertex_backing = slice_record(
        resources, selected_record(metadata, 0, int(vertex["objectId"])))
    index_backing = slice_record(
        resources, selected_record(metadata, 1, int(index["objectId"])))
    base_vertex = int(draw["baseVertex"])
    vertex_count = count // 6 * 4
    vertex_offset = int(vertex.get("offset", 0)) + base_vertex * VERTEX_STRIDE
    vertex_bytes = vertex_backing[
        vertex_offset:vertex_offset + vertex_count * VERTEX_STRIDE]
    index_offset = int(index.get("offset", 0)) + int(draw["start"]) * 2
    index_bytes = index_backing[index_offset:index_offset + count * 2]
    require(len(vertex_bytes) == vertex_count * VERTEX_STRIDE
            and len(index_bytes) == count * 2, "opening geometry is truncated")
    indices = struct.unpack(f"<{count}H", index_bytes)
    for quad in range(vertex_count // 4):
        first = quad * 4
        require(indices[quad * 6:quad * 6 + 6] ==
                (first, first + 1, first + 2, first, first + 2, first + 3),
                "opening topology is not independent quads")
    return vertex_bytes, index_bytes


def collect_constants(draw: dict[str, Any], metadata: dict[str, Any],
                      resources: bytes, stage: int,
                      counts: tuple[int, ...]) -> list[bytes]:
    rows = {(int(row.get("stage", -1)), int(row.get("slot", -1))): row
            for row in draw.get("constantBuffers", [])}
    result = []
    for slot, count in enumerate(counts):
        row = rows.get((stage, slot))
        require(row is not None and row.get("rangeValid") is True
                and row.get("metadataValid") is True,
                f"opening stage {stage} b{slot} range is invalid")
        preview = bytes.fromhex(str(row.get("dataHex", "")))
        selected = [value for value in metadata.get("selectedResourceRecords", [])
                    if int(value.get("captureKind", -1)) == 2
                    and int(value.get("objectId", -1)) == int(row["bufferId"])
                    and value.get("completed") is True
                    and int(value.get("failure", 0)) == 0]
        if selected:
            backing = slice_record(
                resources, selected_record(metadata, 2, int(row["bufferId"])))
            offset = int(row["firstConstant"]) * 16
            payload = backing[offset:offset + count * 16]
        else:
            # The automatic full capture selected the shared 4 MiB global
            # allocation, while the small per-material allocation remains in
            # the draw-local preview. Its retained preview is longer than the
            # exact DXBC declaration and therefore closes the used range.
            payload = preview[:count * 16]
        require(len(payload) == count * 16,
                f"opening stage {stage} b{slot} is truncated")
        require(payload[:min(len(payload), len(preview))] ==
                preview[:min(len(payload), len(preview))],
                f"opening stage {stage} b{slot} disagrees with preview")
        result.append(payload)
    return result


def cpp_array(name: str, payload: bytes) -> str:
    rows = ["    " + ", ".join(f"0x{value:02x}" for value in payload[i:i + 16]) + ","
            for i in range(0, len(payload), 16)]
    return (f"inline constexpr std::uint8_t {name}[] = {{\n" + "\n".join(rows)
            + f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n")


def render_cpp(packets: list[dict[str, Any]], vs: bytes, ps: bytes) -> str:
    arrays = [cpp_array("g_EndfieldOpeningStripVertexDxbc", vs),
              cpp_array("g_EndfieldOpeningStripPixelDxbc", ps)]
    descriptors = []
    for index, packet in enumerate(packets):
        prefix = f"g_EndfieldOpeningStripP{index}"
        arrays.append(cpp_array(prefix + "Vertices", packet["vertices"]))
        arrays.append(cpp_array(prefix + "Indices", packet["indices"]))
        for stage, label in (("vs", "VS"), ("ps", "PS")):
            arrays.extend(cpp_array(f"{prefix}{label}CB{slot}", payload)
                          for slot, payload in enumerate(packet[stage]))
        descriptors.append(
            f"    {{{packet['frame']}u, {packet['phase']:.6f}f, "
            f"{len(packet['indices']) // 2}u, {prefix}Vertices, {prefix}VerticesSize, "
            f"{prefix}Indices, {prefix}IndicesSize, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
    return (
        "// Generated by tools/build_endminf_opening_strip_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr std::uint32_t g_EndfieldOpeningStripVertexStride = 60u;\n"
        "inline constexpr std::uint32_t g_EndfieldOpeningStripVSCounts[] = {2,82,20,4094,5};\n"
        "inline constexpr std::uint32_t g_EndfieldOpeningStripPSCounts[] = {28,104,4085,12};\n\n"
        + "\n".join(arrays) + "\n"
        "struct EndfieldOpeningStripPacket { std::uint32_t frame; float phaseSeconds; "
        "std::uint32_t indexCount; const std::uint8_t* vertices; std::size_t vertexBytes; "
        "const std::uint8_t* indices; std::size_t indexBytes; const std::uint8_t* vs[5]; "
        "std::size_t vsBytes[5]; const std::uint8_t* ps[4]; std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldOpeningStripPacket g_EndfieldOpeningStripPackets[] = {\n"
        + "\n".join(descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldOpeningStripPacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldOpeningStripPackets) / "
        "sizeof(g_EndfieldOpeningStripPackets[0]));\n")


def render_cs(packets: list[dict[str, Any]]) -> str:
    frames = ", ".join(str(row["frame"]) for row in packets)
    phases = ", ".join(f'{row["phase"]:.6f}f' for row in packets)
    counts = ", ".join(str(len(row["indices"]) // 2) for row in packets)
    return f'''// Generated by tools/build_endminf_opening_strip_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredOpeningStripCaptureData
    {{
        internal const string SourceSession = "20260828T181119Z";
        internal const int PacketCount = {len(packets)};
        internal static readonly int[] SourceFrames = {{ {frames} }};
        internal static readonly float[] PhaseSeconds = {{ {phases} }};
        internal static readonly int[] IndexCounts = {{ {counts} }};
    }}
}}
'''


def build(output: Path = OUTPUT, cpp_output: Path = CPP_OUTPUT) -> str:
    vs = VS_PATH.read_bytes()
    ps = PS_PATH.read_bytes()
    require(sha256(vs) == VS_SHA256 and sha256(ps) == PS_SHA256,
            "opening-strip shader bytecode drifted")
    packets = []
    for frame_id, phase, metadata_hash, resources_hash in PACKETS:
        frame = SESSION / "graphics/frames" / str(frame_id)
        metadata_bytes = (frame / "metadata.json").read_bytes()
        resources = (frame / "resources.bin").read_bytes()
        require(sha256(metadata_bytes) == metadata_hash,
                f"opening frame {frame_id} metadata hash drifted")
        require(sha256(resources) == resources_hash,
                f"opening frame {frame_id} resource hash drifted")
        metadata = json.loads(metadata_bytes)
        draws = [row for row in metadata.get("drawRecords", [])
                 if shader_pair(row) == (VS_IDENTITY, PS_IDENTITY)]
        require(len(draws) == 1, f"opening frame {frame_id} owner is not unique")
        vertices, indices = collect_geometry(draws[0], metadata, resources)
        packets.append({"frame": frame_id, "phase": phase,
                        "vertices": vertices, "indices": indices,
                        "vs": collect_constants(draws[0], metadata, resources, 0, VS_COUNTS),
                        "ps": collect_constants(draws[0], metadata, resources, 4, PS_COUNTS)})
    text = render_cs(packets)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.write_text(render_cpp(packets, vs, ps), encoding="utf-8", newline="\n")
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
