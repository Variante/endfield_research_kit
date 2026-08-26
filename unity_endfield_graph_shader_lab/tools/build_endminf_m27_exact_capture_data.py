#!/usr/bin/env python3
"""Build the Unity runtime payload for the exact captured Endminf M27 draw."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CAPTURE = (
    REPO
    / "scratch/reverse_engineering/endfield_capture/20260826T141208Z"
    / "graphics/frames/2529/metadata.json"
)
OUTPUT = (
    REPO
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM27ExactCaptureData.generated.cs"
)
NATIVE_OUTPUT = (
    REPO
    / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M27CapturePayload.generated.h"
)
SOURCE_MESH = (
    REPO
    / "scratch/animestudio/endminf_m27_source_contract/fc_json/Mesh"
    / "S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.json"
)

EXPECTED_SHADER_IDENTITIES = {
    0: 0xC0266E7FAC0046C1,
    4: 0x92D80A93ADD9C714,
}
SOURCE_ROWS = {
    0: (0, 0, 82),
    1: (4, 1, 106),
    2: (0, 2, 4091),
    3: (4, 3, 31),
    4: (4, 4, 1),
}
NATIVE_ROWS = (
    ("vs", 0, 0, 82),
    ("vs", 0, 1, 20),
    ("vs", 0, 2, 4091),
    ("ps", 4, 0, 45),
    ("ps", 4, 1, 106),
    ("ps", 4, 2, 4085),
    ("ps", 4, 3, 31),
    ("ps", 4, 4, 1),
)
EXPECTED_CAPTURED_FLOAT4S = {0: 82, 1: 106, 2: 104, 3: 36, 4: 1}
EXPECTED_FRAME = 2529
EXPANDED_COPY_COUNT = 15
SOURCE_VERTEX_COUNT = 29
SOURCE_INDEX_COUNT = 72
CAPTURED_VERTEX_STRIDE = 60


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_capture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_draw(capture: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in capture.get("drawRecords", [])
        if row.get("count") == 1080
        and row.get("instanceCount") == 1
        and row.get("priorityM27Geometry") is True
        and row.get("priorityShaderPair") is True
    ]
    require(len(rows) == 1, "capture must contain one priority M27 draw")
    draw = rows[0]
    shaders = {row.get("stage"): row for row in draw.get("shaders", [])}
    for stage, identity in EXPECTED_SHADER_IDENTITIES.items():
        require(
            shaders.get(stage, {}).get("identityHash") == identity,
            f"M27 stage {stage} identity drifted",
        )
    return draw


def collect_payloads(draw: dict[str, Any]) -> list[dict[str, Any]]:
    captured = {
        (row.get("stage"), row.get("slot")): row
        for row in draw.get("constantBuffers", [])
    }
    result = []
    for slot, (stage, source_slot, declared_float4s) in SOURCE_ROWS.items():
        row = captured.get((stage, source_slot))
        require(row is not None, f"captured M27 b{slot} is absent")
        require(row.get("rangeValid") is True, f"captured M27 b{slot} range is invalid")
        require(row.get("metadataValid") is True, f"captured M27 b{slot} metadata is invalid")
        payload = bytes.fromhex(row.get("dataHex", ""))
        captured_float4s = len(payload) // 16
        require(len(payload) % 16 == 0, f"captured M27 b{slot} is not float4-aligned")
        require(
            captured_float4s == EXPECTED_CAPTURED_FLOAT4S[slot],
            f"captured M27 b{slot} length drifted: {captured_float4s}",
        )
        require(
            captured_float4s >= min(declared_float4s, EXPECTED_CAPTURED_FLOAT4S[slot]),
            f"captured M27 b{slot} does not close its used range",
        )
        payload = payload[: declared_float4s * 16]
        result.append(
            {
                "slot": slot,
                "declared_float4s": declared_float4s,
                "captured_float4s": len(payload) // 16,
                "payload": payload,
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return result


def collect_native_payloads(draw: dict[str, Any]) -> list[dict[str, Any]]:
    captured = {
        (row.get("stage"), row.get("slot")): row
        for row in draw.get("constantBuffers", [])
    }
    result = []
    for stage_name, stage, slot, declared_float4s in NATIVE_ROWS:
        row = captured.get((stage, slot))
        require(row is not None,
                f"captured M27 {stage_name} b{slot} is absent")
        require(row.get("rangeValid") is True,
                f"captured M27 {stage_name} b{slot} range is invalid")
        require(row.get("metadataValid") is True,
                f"captured M27 {stage_name} b{slot} metadata is invalid")
        payload = bytes.fromhex(row.get("dataHex", ""))
        require(len(payload) % 16 == 0,
                f"captured M27 {stage_name} b{slot} is not float4-aligned")
        payload = payload[:declared_float4s * 16]
        require(payload,
                f"captured M27 {stage_name} b{slot} payload is empty")
        result.append({
            "stage_name": stage_name,
            "stage": stage,
            "slot": slot,
            "declared_float4s": declared_float4s,
            "captured_float4s": len(payload) // 16,
            "payload": payload,
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return result


def collect_geometry(capture_path: Path, capture: dict[str, Any]) -> dict[str, Any]:
    mesh = json.loads(SOURCE_MESH.read_text(encoding="utf-8"))
    source_indices = mesh.get("m_Indices", [])
    require(len(source_indices) == SOURCE_INDEX_COUNT, "M27 source index count drifted")
    require(mesh.get("m_VertexCount") == SOURCE_VERTEX_COUNT,
            "M27 source vertex count drifted")
    expanded_indices = [
        index + copy * SOURCE_VERTEX_COUNT
        for copy in range(EXPANDED_COPY_COUNT)
        for index in source_indices
    ]
    index_payload = struct.pack("<" + "H" * len(expanded_indices), *expanded_indices)

    resources_path = capture_path.with_name(capture.get("resourcesFile", "resources.bin"))
    resources = resources_path.read_bytes()
    complete_rows = [
        row for row in capture.get("selectedResourceRecords", [])
        if row.get("completed") is True and row.get("failure") == 0
    ]
    index_matches: list[tuple[dict[str, Any], int, bytes]] = []
    for row in complete_rows:
        start = int(row.get("blobOffset", -1))
        size = int(row.get("blobBytes", -1))
        require(start >= 0 and size >= 0 and start + size <= len(resources),
                "M27 selected resource range is invalid")
        payload = resources[start:start + size]
        offset = payload.find(index_payload)
        while offset >= 0:
            index_matches.append((row, offset, payload))
            offset = payload.find(index_payload, offset + 1)
    require(len(index_matches) == 1, "M27 expanded index stream is not unique")
    resource_row, index_offset, resource_payload = index_matches[0]

    uv0 = [struct.pack("<2f", *mesh["m_UV0"][i:i + 2])
           for i in range(0, SOURCE_VERTEX_COUNT * 2, 2)]
    uv1 = [struct.pack("<2f", *mesh["m_UV1"][i:i + 2])
           for i in range(0, SOURCE_VERTEX_COUNT * 2, 2)]
    first_uv = uv0[0]
    vertex_matches = []
    search = resource_payload.find(first_uv)
    expanded_vertex_count = SOURCE_VERTEX_COUNT * EXPANDED_COPY_COUNT
    vertex_bytes = expanded_vertex_count * CAPTURED_VERTEX_STRIDE
    while search >= 0:
        if search + vertex_bytes <= len(resource_payload):
            valid = True
            for copy in range(EXPANDED_COPY_COUNT):
                for vertex in range(SOURCE_VERTEX_COUNT):
                    offset = search + (copy * SOURCE_VERTEX_COUNT + vertex) * CAPTURED_VERTEX_STRIDE
                    captured_uv0 = resource_payload[offset:offset + 8]
                    captured_uv1 = resource_payload[offset + 8:offset + 16]
                    if captured_uv0 != uv0[vertex] or captured_uv1 != uv1[vertex]:
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                vertex_matches.append(search)
        search = resource_payload.find(first_uv, search + 1)
    require(len(vertex_matches) == 1, "M27 expanded vertex stream is not unique")
    vertex_offset = vertex_matches[0]
    vertex_payload = resource_payload[vertex_offset:vertex_offset + vertex_bytes]
    return {
        "resource_kind": int(resource_row["captureKind"]),
        "resource_blob_offset": int(resource_row["blobOffset"]),
        "vertex_offset": vertex_offset,
        "vertex_stride": CAPTURED_VERTEX_STRIDE,
        "vertex_count": expanded_vertex_count,
        "vertex_payload": vertex_payload,
        "vertex_sha256": hashlib.sha256(vertex_payload).hexdigest(),
        "index_offset": index_offset,
        "index_count": len(expanded_indices),
        "index_payload": index_payload,
        "index_sha256": hashlib.sha256(index_payload).hexdigest(),
    }


def render(capture_path: Path, capture: dict[str, Any], rows: list[dict[str, Any]],
           geometry: dict[str, Any]) -> str:
    capture_hash = hashlib.sha256(capture_path.read_bytes()).hexdigest()
    counts = ", ".join(str(row["declared_float4s"]) for row in rows)
    payloads = "\n".join(
        f'            "{base64.b64encode(row["payload"]).decode("ascii")}",'
        for row in rows
    )
    hashes = "\n".join(
        f'            "{row["sha256"]}",'
        for row in rows
    )
    relative_capture = capture_path.resolve().relative_to(REPO.resolve()).as_posix()
    return f'''// Generated by tools/build_endminf_m27_exact_capture_data.py. Do not edit.
using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM27ExactCaptureData
    {{
        internal const string SourceCapture = "{relative_capture}";
        internal const string SourceCaptureSha256 = "{capture_hash}";
        internal const int SourceFrame = {capture.get("frame", EXPECTED_FRAME)};
        internal const int CapturedB0Float4Count = {rows[0]["captured_float4s"]};
        internal const bool ExactVertexEnvelopeClosed =
            {str(rows[0]["captured_float4s"] >= 82).lower()};
        internal const int ExpandedVertexCount = {geometry["vertex_count"]};
        internal const int ExpandedIndexCount = {geometry["index_count"]};
        internal const int ExpandedVertexStride = {geometry["vertex_stride"]};
        internal const int CapturedResourceKind = {geometry["resource_kind"]};
        internal const int CapturedResourceBlobOffset = {geometry["resource_blob_offset"]};
        internal const int CapturedVertexByteOffset = {geometry["vertex_offset"]};
        internal const int CapturedIndexByteOffset = {geometry["index_offset"]};
        internal const string ExpandedVertexSha256 = "{geometry["vertex_sha256"]}";
        internal const string ExpandedIndexSha256 = "{geometry["index_sha256"]}";

        private const string ExpandedVertexBase64 =
            "{base64.b64encode(geometry["vertex_payload"]).decode("ascii")}";
        private const string ExpandedIndexBase64 =
            "{base64.b64encode(geometry["index_payload"]).decode("ascii")}";

        private static readonly int[] DeclaredFloat4Counts = {{ {counts} }};
        private static readonly string[] PayloadBase64 =
        {{
{payloads}
        }};
        internal static readonly string[] PayloadSha256 =
        {{
{hashes}
        }};

        internal static Vector4[][] CreateConstantBufferValues()
        {{
            var result = new Vector4[DeclaredFloat4Counts.Length][];
            for (int slot = 0; slot < result.Length; ++slot)
            {{
                byte[] payload = Convert.FromBase64String(PayloadBase64[slot]);
                if ((payload.Length & 15) != 0 ||
                    payload.Length > DeclaredFloat4Counts[slot] * 16)
                {{
                    throw new InvalidOperationException(
                        "Captured M27 b" + slot + " payload length is invalid.");
                }}
                var values = new Vector4[DeclaredFloat4Counts[slot]];
                for (int index = 0; index < payload.Length / 16; ++index)
                {{
                    int offset = index * 16;
                    values[index] = new Vector4(
                        BitConverter.ToSingle(payload, offset),
                        BitConverter.ToSingle(payload, offset + 4),
                        BitConverter.ToSingle(payload, offset + 8),
                        BitConverter.ToSingle(payload, offset + 12));
                }}
                result[slot] = values;
            }}
            return result;
        }}

        internal static Mesh CreateExpandedMesh()
        {{
            byte[] vertices = Convert.FromBase64String(ExpandedVertexBase64);
            byte[] indices = Convert.FromBase64String(ExpandedIndexBase64);
            if (vertices.Length != ExpandedVertexCount * ExpandedVertexStride ||
                indices.Length != ExpandedIndexCount * 2)
                throw new InvalidOperationException(
                    "Captured M27 expanded geometry payload length drifted.");

            var positions = new Vector3[ExpandedVertexCount];
            var normals = new Vector3[ExpandedVertexCount];
            var colors = new Color32[ExpandedVertexCount];
            var uv0 = new Vector2[ExpandedVertexCount];
            var uv1 = new Vector2[ExpandedVertexCount];
            var custom1 = new Vector4[ExpandedVertexCount];
            for (int index = 0; index < ExpandedVertexCount; ++index)
            {{
                int offset = index * ExpandedVertexStride;
                uv0[index] = new Vector2(
                    BitConverter.ToSingle(vertices, offset),
                    BitConverter.ToSingle(vertices, offset + 4));
                uv1[index] = new Vector2(
                    BitConverter.ToSingle(vertices, offset + 8),
                    BitConverter.ToSingle(vertices, offset + 12));
                custom1[index] = new Vector4(
                    BitConverter.ToSingle(vertices, offset + 16),
                    BitConverter.ToSingle(vertices, offset + 20),
                    BitConverter.ToSingle(vertices, offset + 24),
                    BitConverter.ToSingle(vertices, offset + 28));
                positions[index] = new Vector3(
                    BitConverter.ToSingle(vertices, offset + 32),
                    BitConverter.ToSingle(vertices, offset + 36),
                    BitConverter.ToSingle(vertices, offset + 40));
                normals[index] = new Vector3(
                    BitConverter.ToSingle(vertices, offset + 44),
                    BitConverter.ToSingle(vertices, offset + 48),
                    BitConverter.ToSingle(vertices, offset + 52));
                colors[index] = new Color32(
                    vertices[offset + 56], vertices[offset + 57],
                    vertices[offset + 58], vertices[offset + 59]);
            }}
            var triangles = new int[ExpandedIndexCount];
            for (int index = 0; index < ExpandedIndexCount; ++index)
                triangles[index] = BitConverter.ToUInt16(indices, index * 2);

            var mesh = new Mesh {{ name = "Captured Endminf M27 expanded draw" }};
            mesh.vertices = positions;
            mesh.normals = normals;
            mesh.colors32 = colors;
            mesh.uv = uv0;
            mesh.uv2 = uv1;
            mesh.SetUVs(4, custom1);
            mesh.triangles = triangles;
            mesh.RecalculateBounds();
            return mesh;
        }}
    }}
}}
'''


def render_native(capture_path: Path, capture: dict[str, Any],
                  rows: list[dict[str, Any]], geometry: dict[str, Any]) -> str:
    def array(name: str, payload: bytes) -> str:
        lines = []
        for offset in range(0, len(payload), 16):
            chunk = payload[offset:offset + 16]
            lines.append("    " + ", ".join(f"0x{value:02x}" for value in chunk) + ",")
        return (
            f"inline constexpr unsigned char {name}[] = {{\n" +
            "\n".join(lines) + "\n};\n" +
            f"inline constexpr std::size_t {name}Size = sizeof({name});\n"
        )

    row_arrays = []
    for row in rows:
        row_arrays.append(array(
            f"g_EndfieldM27{row['stage_name'].upper()}B{row['slot']}",
            row["payload"]))
    source = capture_path.resolve().relative_to(REPO.resolve()).as_posix()
    vertex_hash = hashlib.sha256(geometry["vertex_payload"]).hexdigest()
    index_hash = hashlib.sha256(geometry["index_payload"]).hexdigest()
    return f'''#pragma once
// Generated by tools/build_endminf_m27_exact_capture_data.py. Do not edit.
// Source: {source}
#include <cstddef>

{array("g_EndfieldM27Vertices", geometry["vertex_payload"])}
{array("g_EndfieldM27Indices", geometry["index_payload"])}
{''.join(row_arrays)}
inline constexpr const unsigned char* g_EndfieldM27VSCapturedData[] = {{
    g_EndfieldM27VSB0, g_EndfieldM27VSB1, g_EndfieldM27VSB2,
}};
inline constexpr std::size_t g_EndfieldM27VSCapturedSizes[] = {{
    g_EndfieldM27VSB0Size, g_EndfieldM27VSB1Size, g_EndfieldM27VSB2Size,
}};
inline constexpr std::size_t g_EndfieldM27VSDeclaredSizes[] = {{
    82u * 16u, 20u * 16u, 4091u * 16u,
}};
inline constexpr const unsigned char* g_EndfieldM27PSCapturedData[] = {{
    g_EndfieldM27PSB0, g_EndfieldM27PSB1, g_EndfieldM27PSB2,
    g_EndfieldM27PSB3, g_EndfieldM27PSB4,
}};
inline constexpr std::size_t g_EndfieldM27PSCapturedSizes[] = {{
    g_EndfieldM27PSB0Size, g_EndfieldM27PSB1Size, g_EndfieldM27PSB2Size,
    g_EndfieldM27PSB3Size, g_EndfieldM27PSB4Size,
}};
inline constexpr std::size_t g_EndfieldM27PSDeclaredSizes[] = {{
    45u * 16u, 106u * 16u, 4085u * 16u, 31u * 16u, 1u * 16u,
}};
inline constexpr char g_EndfieldM27VertexSha256[] = "{vertex_hash}";
inline constexpr char g_EndfieldM27IndexSha256[] = "{index_hash}";
'''


def build(capture_path: Path, output: Path,
          native_output: Path = NATIVE_OUTPUT) -> str:
    capture = load_capture(capture_path)
    require(capture.get("frame") == EXPECTED_FRAME, "M27 capture frame drifted")
    draw = select_draw(capture)
    rows = collect_payloads(draw)
    native_rows = collect_native_payloads(draw)
    geometry = collect_geometry(capture_path, capture)
    text = render(capture_path, capture, rows, geometry)
    native_text = render_native(capture_path, capture, native_rows, geometry)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    native_output.parent.mkdir(parents=True, exist_ok=True)
    native_output.write_text(native_text, encoding="utf-8", newline="\n")
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--native-output", type=Path, default=NATIVE_OUTPUT)
    args = parser.parse_args()
    build(args.capture, args.output, args.native_output)
    print(args.output)
    print(args.native_output)
