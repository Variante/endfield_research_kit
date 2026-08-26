#!/usr/bin/env python3
"""Build the Unity runtime payload for the captured Endminf M14 draw."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
FRAME = (
    REPO
    / "scratch/reverse_engineering/endfield_capture/20260826T000901Z"
    / "graphics/frames/13175"
)
REPORT = (
    REPO
    / "reports/assets/character_recovery/endminf_m14_graphics_capture_latest.json"
)
OUTPUT = (
    REPO
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM14ExactCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO
    / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M14CapturePayload.generated.h"
)

EXPECTED_FRAME = 13175
EXPECTED_VS = 0x62A5CE6C09171DE9
EXPECTED_PS = 0x5558DEDDB1EE6188
VERTEX_STRIDE = 36
QUAD_COUNT = 285
VERTEX_COUNT = QUAD_COUNT * 4
INDEX_COUNT = QUAD_COUNT * 6
DECLARED_COUNTS = {
    0: (2, 82, 104, 4094, 10),
    4: (28, 105, 4085, 22),
}
CAPTURED_COUNTS = {
    0: (2, 82, 104, 16, 10),
    4: (28, 105, 5, 22),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def select_draw(metadata: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in metadata.get("drawRecords", [])
        if row.get("count") == INDEX_COUNT
        and row.get("start") == 4902
        and row.get("baseVertex") == 3227
        and row.get("instanceCount") == 1
        and row.get("priorityShaderPair") is True
    ]
    require(len(rows) == 1, "capture must contain one exact M14 draw")
    shaders = {row.get("stage"): row for row in rows[0].get("shaders", [])}
    require(shaders.get(0, {}).get("identityHash") == EXPECTED_VS,
            "M14 vertex shader identity drifted")
    require(shaders.get(4, {}).get("identityHash") == EXPECTED_PS,
            "M14 pixel shader identity drifted")
    return rows[0]


def collect_constants(draw: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    captured = {
        (row.get("stage"), row.get("slot")): row
        for row in draw.get("constantBuffers", [])
    }
    result: dict[int, list[dict[str, Any]]] = {}
    for stage, declared_counts in DECLARED_COUNTS.items():
        rows = []
        for slot, declared_count in enumerate(declared_counts):
            source = captured.get((stage, slot))
            require(source is not None,
                    f"captured M14 stage {stage} b{slot} is absent")
            require(source.get("rangeValid") is True and
                    source.get("metadataValid") is True,
                    f"captured M14 stage {stage} b{slot} range is invalid")
            payload = bytes.fromhex(source.get("dataHex", ""))
            require(len(payload) % 16 == 0,
                    f"captured M14 stage {stage} b{slot} is not float4-aligned")
            captured_count = len(payload) // 16
            require(captured_count == CAPTURED_COUNTS[stage][slot],
                    f"captured M14 stage {stage} b{slot} length drifted: "
                    f"{captured_count}")
            require(captured_count <= declared_count,
                    f"captured M14 stage {stage} b{slot} exceeds declaration")
            rows.append({
                "slot": slot,
                "declared_count": declared_count,
                "captured_count": captured_count,
                "payload": payload,
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
        result[stage] = rows
    return result


def collect_geometry(frame: Path, report: dict[str, Any]) -> dict[str, Any]:
    require(report.get("status") == "validated", "M14 verifier report is not valid")
    require(report.get("sessionId") == "20260826T000901Z",
            "M14 verifier session drifted")
    frames = report.get("frames", [])
    require(len(frames) == 1 and frames[0].get("frame") == EXPECTED_FRAME,
            "M14 verifier frame drifted")
    draws = frames[0].get("m14Draws", [])
    require(len(draws) == 1, "M14 verifier report must contain one draw")
    geometry = draws[0].get("rawParticleGeometry")
    require(isinstance(geometry, dict), "M14 verifier has no raw geometry")
    require(geometry.get("vertexStride") == VERTEX_STRIDE and
            geometry.get("consumedQuadCount") == QUAD_COUNT,
            "M14 raw geometry contract drifted")

    resources_path = frame / "resources.bin"
    resources = resources_path.read_bytes()
    start = int(geometry["blobOffset"]) + int(geometry["streamByteOffset"])
    size = VERTEX_COUNT * VERTEX_STRIDE
    require(start >= 0 and start + size <= len(resources),
            "M14 vertex stream exceeds resources.bin")
    vertices = resources[start:start + size]
    indices = []
    for quad in range(QUAD_COUNT):
        base = quad * 4
        indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))
    index_payload = struct.pack("<" + "H" * len(indices), *indices)
    return {
        "capture_kind": int(geometry["captureKind"]),
        "resource_index": int(geometry["resourceIndex"]),
        "blob_offset": int(geometry["blobOffset"]),
        "stream_offset": int(geometry["streamByteOffset"]),
        "vertices": vertices,
        "indices": index_payload,
        "vertex_sha256": hashlib.sha256(vertices).hexdigest(),
        "index_sha256": hashlib.sha256(index_payload).hexdigest(),
    }


def render_payload_rows(rows: list[dict[str, Any]]) -> tuple[str, str, str]:
    declared = ", ".join(str(row["declared_count"]) for row in rows)
    payloads = "\n".join(
        f'            "{base64.b64encode(row["payload"]).decode("ascii")}",'
        for row in rows
    )
    hashes = "\n".join(f'            "{row["sha256"]}",' for row in rows)
    return declared, payloads, hashes


def render_cpp_array(name: str, payload: bytes) -> str:
    lines = []
    for start in range(0, len(payload), 16):
        chunk = payload[start:start + 16]
        lines.append("    " + ", ".join(f"0x{value:02x}" for value in chunk) + ",")
    return (
        f"inline constexpr std::uint8_t {name}[] = {{\n" +
        "\n".join(lines) + "\n};\n" +
        f"inline constexpr std::size_t {name}Size = sizeof({name});\n"
    )


def render_cpp(constants: dict[int, list[dict[str, Any]]],
               geometry: dict[str, Any]) -> str:
    arrays = [
        render_cpp_array("g_EndfieldM14Vertices", geometry["vertices"]),
        render_cpp_array("g_EndfieldM14Indices", geometry["indices"]),
    ]
    for stage, prefix in ((0, "VS"), (4, "PS")):
        for row in constants[stage]:
            arrays.append(render_cpp_array(
                f"g_EndfieldM14{prefix}CB{row['slot']}", row["payload"]))
    return (
        "// Generated by tools/build_endminf_m14_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr std::uint32_t g_EndfieldM14VertexStride = 36;\n"
        "inline constexpr std::uint32_t g_EndfieldM14VertexCount = 1140;\n"
        "inline constexpr std::uint32_t g_EndfieldM14IndexCount = 1710;\n"
        "inline constexpr std::uint32_t g_EndfieldM14VSDeclaredFloat4Counts[] = "
        "{2, 82, 104, 4094, 10};\n"
        "inline constexpr std::uint32_t g_EndfieldM14PSDeclaredFloat4Counts[] = "
        "{28, 105, 4085, 22};\n\n" + "\n".join(arrays)
    )


def render(frame: Path, metadata: dict[str, Any], report: dict[str, Any],
           constants: dict[int, list[dict[str, Any]]],
           geometry: dict[str, Any]) -> str:
    vs_declared, vs_payloads, vs_hashes = render_payload_rows(constants[0])
    ps_declared, ps_payloads, ps_hashes = render_payload_rows(constants[4])
    metadata_path = frame / "metadata.json"
    metadata_hash = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
    report_hash = hashlib.sha256(REPORT.read_bytes()).hexdigest()
    relative_metadata = metadata_path.relative_to(REPO).as_posix()
    return f'''// Generated by tools/build_endminf_m14_exact_capture_data.py. Do not edit.
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM14ExactCaptureData
    {{
        internal const string SourceCapture = "{relative_metadata}";
        internal const string SourceCaptureSha256 = "{metadata_hash}";
        internal const string SourceReportSha256 = "{report_hash}";
        internal const int SourceFrame = {metadata.get("frame", EXPECTED_FRAME)};
        internal const int QuadCount = {QUAD_COUNT};
        internal const int VertexCount = {VERTEX_COUNT};
        internal const int IndexCount = {INDEX_COUNT};
        internal const int VertexStride = {VERTEX_STRIDE};
        internal const int CapturedResourceKind = {geometry["capture_kind"]};
        internal const int CapturedResourceIndex = {geometry["resource_index"]};
        internal const int CapturedResourceBlobOffset = {geometry["blob_offset"]};
        internal const int CapturedVertexByteOffset = {geometry["stream_offset"]};
        internal const string VertexSha256 = "{geometry["vertex_sha256"]}";
        internal const string IndexSha256 = "{geometry["index_sha256"]}";

        private const string VertexBase64 =
            "{base64.b64encode(geometry["vertices"]).decode("ascii")}";
        private const string IndexBase64 =
            "{base64.b64encode(geometry["indices"]).decode("ascii")}";

        private static readonly int[] VertexDeclaredFloat4Counts =
            {{ {vs_declared} }};
        private static readonly string[] VertexPayloadBase64 =
        {{
{vs_payloads}
        }};
        internal static readonly string[] VertexPayloadSha256 =
        {{
{vs_hashes}
        }};

        private static readonly int[] PixelDeclaredFloat4Counts =
            {{ {ps_declared} }};
        private static readonly string[] PixelPayloadBase64 =
        {{
{ps_payloads}
        }};
        internal static readonly string[] PixelPayloadSha256 =
        {{
{ps_hashes}
        }};

        internal static Vector4[][] CreateVertexConstantBufferValues()
        {{
            return CreateConstantBufferValues(
                VertexDeclaredFloat4Counts, VertexPayloadBase64, "VS");
        }}

        internal static Vector4[][] CreatePixelConstantBufferValues()
        {{
            return CreateConstantBufferValues(
                PixelDeclaredFloat4Counts, PixelPayloadBase64, "PS");
        }}

        private static Vector4[][] CreateConstantBufferValues(
            int[] declaredCounts, string[] payloadBase64, string stage)
        {{
            var result = new Vector4[declaredCounts.Length][];
            for (int slot = 0; slot < result.Length; ++slot)
            {{
                byte[] payload = Convert.FromBase64String(payloadBase64[slot]);
                if ((payload.Length & 15) != 0 ||
                    payload.Length > declaredCounts[slot] * 16)
                {{
                    throw new InvalidOperationException(
                        "Captured M14 " + stage + " b" + slot +
                        " payload length is invalid.");
                }}
                var values = new Vector4[declaredCounts[slot]];
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
            byte[] vertices = Convert.FromBase64String(VertexBase64);
            byte[] indices = Convert.FromBase64String(IndexBase64);
            if (vertices.Length != VertexCount * VertexStride ||
                indices.Length != IndexCount * 2)
            {{
                throw new InvalidOperationException(
                    "Captured M14 geometry payload length drifted.");
            }}

            var positions = new Vector3[VertexCount];
            var normals = new Vector3[VertexCount];
            var colors = new Color32[VertexCount];
            var uv0 = new Vector2[VertexCount];
            var uv1 = new List<Vector4>(VertexCount);
            var previousPositions = new List<Vector3>(VertexCount);
            for (int index = 0; index < VertexCount; ++index)
            {{
                int offset = index * VertexStride;
                positions[index] = new Vector3(
                    BitConverter.ToSingle(vertices, offset),
                    BitConverter.ToSingle(vertices, offset + 4),
                    BitConverter.ToSingle(vertices, offset + 8));
                normals[index] = new Vector3(
                    BitConverter.ToSingle(vertices, offset + 12),
                    BitConverter.ToSingle(vertices, offset + 16),
                    BitConverter.ToSingle(vertices, offset + 20));
                colors[index] = new Color32(
                    vertices[offset + 24], vertices[offset + 25],
                    vertices[offset + 26], vertices[offset + 27]);
                uv0[index] = new Vector2(
                    BitConverter.ToSingle(vertices, offset + 28),
                    BitConverter.ToSingle(vertices, offset + 32));
                uv1.Add(Vector4.zero);
                previousPositions.Add(positions[index]);
            }}
            var triangles = new int[IndexCount];
            for (int index = 0; index < IndexCount; ++index)
                triangles[index] = BitConverter.ToUInt16(indices, index * 2);

            var mesh = new Mesh
            {{
                name = "Captured Endminf M14 expanded draw",
                indexFormat = IndexFormat.UInt16,
                vertices = positions,
                normals = normals,
                colors32 = colors,
                uv = uv0,
            }};
            mesh.SetUVs(1, uv1);
            mesh.SetUVs(4, previousPositions);
            mesh.triangles = triangles;
            mesh.RecalculateBounds();
            return mesh;
        }}
    }}
}}
'''


def build(frame: Path, report_path: Path, output: Path,
          cpp_output: Path = CPP_OUTPUT) -> str:
    metadata_path = frame / "metadata.json"
    metadata = load_json(metadata_path)
    require(metadata.get("frame") == EXPECTED_FRAME, "M14 capture frame drifted")
    report = load_json(report_path)
    constants = collect_constants(select_draw(metadata))
    geometry = collect_geometry(frame, report)
    text = render(frame, metadata, report, constants, geometry)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    cpp_text = render_cpp(constants, geometry)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.write_text(cpp_text, encoding="utf-8", newline="\n")
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=Path, default=FRAME)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.frame, args.report, args.output, args.cpp_output)
    print(args.output)
    print(args.cpp_output)
