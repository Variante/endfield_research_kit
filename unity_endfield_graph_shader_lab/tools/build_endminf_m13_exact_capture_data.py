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
FRAME_ID = 5404
FRAME = SESSION / "graphics/frames" / str(FRAME_ID)
OUTPUT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
          / "Runtime/Rendering/EndfieldRecoveredM13ExactCaptureData.generated.cs")
CPP_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
              / "M13CapturePayload.generated.h")

EXPECTED_METADATA_SHA256 = "1a67e671ad25f61fc9e9ee069515406fa61bb7a77478efa39fe85e43a34804b2"
EXPECTED_RESOURCES_SHA256 = "8f80561c565eb007f3eafa1d0002717ae8633c5d0b01f35f62da0aa3e177ce5a"
EXPECTED_VS = 0x96A93DCB3965CBED
EXPECTED_PS = 0x0265C7A6806A095F
EXPECTED_DRAW = (6, 1, 0)
VERTEX_STRIDE = 60
VERTEX_COUNT = 4
INDEX_PAYLOAD = struct.pack("<6H", 0, 1, 2, 0, 2, 3)
DECLARED_COUNTS = {0: (2, 82, 20, 4094, 4), 4: (28, 105, 4085, 50)}
TEXTURE_SHAPES = ((256, 256), (512, 512), (512, 512), (256, 256), (256, 256))
BC7_SRGB = 99


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
        if current_color[:3] != bytes((255, 73, 6)):
            return False
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


def collect_geometry(metadata: dict[str, Any], resources: bytes) -> dict[str, Any]:
    ring = slice_record(resources, selected_record(metadata, 4, 5, 0))
    size = VERTEX_STRIDE * VERTEX_COUNT
    offsets = [offset for offset in range(0, len(ring) - size + 1, 4)
               if is_geometry_candidate(ring, offset)]
    require(len(offsets) == 1,
            f"M13 particle-ring signature must be unique, found {len(offsets)} candidates")
    payload = ring[offsets[0]:offsets[0] + size]
    return {"vertices": payload, "indices": INDEX_PAYLOAD, "ring_offset": offsets[0],
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


def render_cpp(packet: dict[str, Any]) -> str:
    arrays = [render_cpp_array("g_EndfieldM13Vertices", packet["geometry"]["vertices"]),
              render_cpp_array("g_EndfieldM13Indices", packet["geometry"]["indices"])]
    for stage, label in ((0, "VS"), (4, "PS")):
        arrays.extend(render_cpp_array(f"g_EndfieldM13{label}CB{row['slot']}", row["payload"])
                      for row in packet["constants"][stage])
    arrays.extend(render_cpp_array(f"g_EndfieldM13Texture{row['slot']}", row["payload"])
                  for row in packet["textures"])
    texture_desc = ",\n".join(
        f"    {{g_EndfieldM13Texture{row['slot']}, g_EndfieldM13Texture{row['slot']}Size, "
        f"{row['width']}u, {row['height']}u}}" for row in packet["textures"])
    return (
        "// Generated by tools/build_endminf_m13_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr std::uint32_t g_EndfieldM13VertexStride = 60;\n"
        "inline constexpr std::uint32_t g_EndfieldM13VSDeclaredFloat4Counts[] = "
        "{2, 82, 20, 4094, 4};\n"
        "inline constexpr std::uint32_t g_EndfieldM13PSDeclaredFloat4Counts[] = "
        "{28, 105, 4085, 50};\n\n" + "\n".join(arrays) + "\n"
        "inline constexpr const std::uint8_t* g_EndfieldM13VSConstantPayloads[] = "
        "{g_EndfieldM13VSCB0, g_EndfieldM13VSCB1, g_EndfieldM13VSCB2, "
        "g_EndfieldM13VSCB3, g_EndfieldM13VSCB4};\n"
        "inline constexpr std::size_t g_EndfieldM13VSConstantPayloadSizes[] = "
        "{g_EndfieldM13VSCB0Size, g_EndfieldM13VSCB1Size, "
        "g_EndfieldM13VSCB2Size, g_EndfieldM13VSCB3Size, "
        "g_EndfieldM13VSCB4Size};\n"
        "inline constexpr const std::uint8_t* g_EndfieldM13PSConstantPayloads[] = "
        "{g_EndfieldM13PSCB0, g_EndfieldM13PSCB1, g_EndfieldM13PSCB2, "
        "g_EndfieldM13PSCB3};\n"
        "inline constexpr std::size_t g_EndfieldM13PSConstantPayloadSizes[] = "
        "{g_EndfieldM13PSCB0Size, g_EndfieldM13PSCB1Size, "
        "g_EndfieldM13PSCB2Size, g_EndfieldM13PSCB3Size};\n"
        "struct EndfieldM13TexturePayload { const std::uint8_t* bytes; std::size_t size; "
        "std::uint32_t width; std::uint32_t height; };\n"
        "inline constexpr EndfieldM13TexturePayload g_EndfieldM13Textures[] = {\n" +
        texture_desc + "\n};\n")


def render_cs(packet: dict[str, Any]) -> str:
    texture_hashes = ", ".join(f'"{row["sha256"]}"' for row in packet["textures"])
    return f'''// Generated by tools/build_endminf_m13_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM13ExactCaptureData
    {{
        internal const string SourceSession = "20260826T144934Z";
        internal const int SourceFrame = {FRAME_ID};
        internal const float PhaseSeconds = 4.50f;
        internal const float ActiveHalfWidthSeconds = 0.125f;
        internal const int RingByteOffset = {packet["geometry"]["ring_offset"]};
        internal const string VertexSha256 = "{packet["geometry"]["vertex_sha256"]}";
        internal static readonly string[] TextureSha256 = {{ {texture_hashes} }};
    }}
}}
'''


def build(frame: Path = FRAME, output: Path = OUTPUT,
          cpp_output: Path = CPP_OUTPUT) -> str:
    metadata_bytes = (frame / "metadata.json").read_bytes()
    resources = (frame / "resources.bin").read_bytes()
    require(sha256(metadata_bytes) == EXPECTED_METADATA_SHA256, "M13 metadata hash drifted")
    require(sha256(resources) == EXPECTED_RESOURCES_SHA256, "M13 resources hash drifted")
    metadata = json.loads(metadata_bytes)
    require(metadata.get("captureIncomplete") is not True and
            metadata.get("captureFailed") is not True, "M13 frame is incomplete")
    draw = select_draw(metadata)
    packet = {"constants": collect_constants(draw, metadata, resources),
              "geometry": collect_geometry(metadata, resources),
              "textures": collect_textures(metadata, resources)}
    text = render_cs(packet)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.write_text(render_cpp(packet), encoding="utf-8", newline="\n")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", type=Path, default=FRAME)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.frame, args.output, args.cpp_output)
    print(args.output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
