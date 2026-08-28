#!/usr/bin/env python3
"""Build the complete ordered Endminf VFXBaseV2 peak cohort from retail."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260827T225644Z"
REPORT = (REPO / "reports/assets/character_recovery"
          / "endminf_m29_m30_capture_completeness_20260827T225644Z.json")
CS_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
             / "Runtime/Rendering/EndfieldRecoveredVFXBaseV2PeakCohortData.generated.cs")
CPP_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
              / "VFXBaseV2PeakCohortPayload.generated.h")

EXPECTED_SESSION = "20260827T225644Z"
EXPECTED_FRAME = 2723
EXPECTED_REPORT_SHA256 = (
    "c13a5d79cacadae35c151b76da8aa74f1191c2ebb155a616a17d723ba49b81e0")
EXPECTED_METADATA_SHA256 = (
    "23b8256ca23339dd77cfea103caef13520744c96fcba47add8b4d00eddd4bffe")
EXPECTED_VS = 0x62A5CE6C09171DE9
EXPECTED_PS = 0x5558DEDDB1EE6188
EXPECTED_ORDINALS = (68, 74, 75, 76, 77, 78, 79, 80, 81, 83, 84, 85,
                     86, 87, 88)
EXPECTED_DRAW_INDICES = (3, 12, 19, 20, 28, 29, 8, 9, 11, 15, 16, 17, 24,
                         25, 31)
VERTEX_STRIDE = 36
INDEX_FORMAT = 57
TEXTURE_FORMAT = 99
DECLARED_COUNTS = {0: (2, 82, 104, 4094, 10),
                   4: (28, 105, 4085, 22)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def selected(metadata: dict[str, Any], *, kind: int, object_id: int,
             stage: int | None = None, slot: int | None = None
             ) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict) and row.get("captureKind") == kind
            and int(row.get("objectId", 0)) == object_id
            and row.get("completed") is True]
    if stage is not None:
        rows = [row for row in rows if row.get("stage") == stage]
    if slot is not None:
        rows = [row for row in rows if row.get("slot") == slot]
    require(len(rows) == 1,
            f"resource kind {kind} object {object_id} stage {stage} slot {slot} "
            "is not unique")
    return rows[0]


def blob(resources: bytes, row: dict[str, Any]) -> bytes:
    start = int(row["blobOffset"])
    size = int(row["blobBytes"])
    require(start >= 0 and size > 0 and start + size <= len(resources),
            "selected resource exceeds resources.bin")
    return resources[start:start + size]


def shader_pair(draw: dict[str, Any]) -> tuple[int, int]:
    rows = {int(row.get("stage", -1)): int(row.get("identityHash", 0))
            for row in draw.get("shaders", []) if isinstance(row, dict)}
    return rows.get(0, 0), rows.get(4, 0)


def collect_constants(metadata: dict[str, Any], draw: dict[str, Any],
                      resources: bytes) -> dict[int, list[bytes]]:
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage in (0, 4):
        for slot, count in enumerate(DECLARED_COUNTS[stage]):
            rows = [row for row in draw.get("constantBuffers", [])
                    if row.get("stage") == stage and row.get("slot") == slot]
            require(len(rows) == 1,
                    f"ordinal {draw['drawOrdinal']} stage {stage} b{slot} "
                    "is not unique")
            binding = rows[0]
            require(binding.get("rangeValid") is True and
                    binding.get("metadataValid") is True,
                    f"ordinal {draw['drawOrdinal']} stage {stage} b{slot} is invalid")
            backing = selected(metadata, kind=2,
                               object_id=int(binding["bufferId"]))
            allocation = blob(resources, backing)
            start = int(binding["firstConstant"]) * 16
            end = start + count * 16
            require(end <= len(allocation),
                    f"ordinal {draw['drawOrdinal']} stage {stage} b{slot} "
                    "exceeds its backing allocation")
            result[stage].append(allocation[start:end])
    return result


def collect_geometry(metadata: dict[str, Any], draw: dict[str, Any],
                     resources: bytes) -> dict[str, Any]:
    assembler = draw.get("inputAssembler")
    require(isinstance(assembler, dict),
            f"ordinal {draw['drawOrdinal']} has no draw-local IA")
    vertex_rows = [row for row in assembler.get("vertexBuffers", [])
                   if row.get("slot") == 0]
    secondary_rows = [row for row in assembler.get("vertexBuffers", [])
                      if row.get("slot") == 1]
    index_binding = assembler.get("indexBuffer")
    require(len(vertex_rows) == len(secondary_rows) == 1 and
            isinstance(index_binding, dict),
            f"ordinal {draw['drawOrdinal']} has incomplete draw-local IA")
    vertex_binding = vertex_rows[0]
    secondary_binding = secondary_rows[0]
    primary_id = int(vertex_binding["objectId"])
    require(int(index_binding.get("objectId", 0)) == primary_id and
            int(vertex_binding.get("stride", 0)) == VERTEX_STRIDE and
            int(index_binding.get("format", -1)) == INDEX_FORMAT and
            int(draw.get("topology", -1)) == 4,
            f"ordinal {draw['drawOrdinal']} IA descriptor drifted")
    vertex_row = selected(metadata, kind=0, object_id=primary_id,
                          stage=0, slot=0)
    index_row = selected(metadata, kind=1, object_id=primary_id,
                         stage=0, slot=0)
    require(int(vertex_row["blobOffset"]) == int(index_row["blobOffset"]) and
            int(vertex_row["blobBytes"]) == int(index_row["blobBytes"]),
            f"ordinal {draw['drawOrdinal']} IA ring alias drifted")
    ring = blob(resources, vertex_row)
    index_count = int(draw["count"])
    index_start = int(index_binding["offset"]) + int(draw["start"]) * 2
    indices = ring[index_start:index_start + index_count * 2]
    require(len(indices) == index_count * 2,
            f"ordinal {draw['drawOrdinal']} index slice is truncated")
    index_values = struct.unpack("<" + "H" * index_count, indices)
    require(min(index_values) == 0,
            f"ordinal {draw['drawOrdinal']} indices do not start at zero")
    vertex_count = max(index_values) + 1
    require(vertex_count % 4 == 0 and len(set(index_values)) == vertex_count,
            f"ordinal {draw['drawOrdinal']} does not close expanded quads")
    vertex_start = (int(vertex_binding["offset"]) +
                    int(draw["baseVertex"]) * VERTEX_STRIDE)
    vertices = ring[vertex_start:vertex_start + vertex_count * VERTEX_STRIDE]
    require(len(vertices) == vertex_count * VERTEX_STRIDE,
            f"ordinal {draw['drawOrdinal']} vertex slice is truncated")
    for index in range(vertex_count):
        values = struct.unpack_from("<6fI2f", vertices,
                                    index * VERTEX_STRIDE)
        require(all(math.isfinite(value) for value in values[:6] + values[7:]),
                f"ordinal {draw['drawOrdinal']} has non-finite vertex data")
    secondary_row = selected(
        metadata, kind=0, object_id=int(secondary_binding["objectId"]),
        stage=0, slot=1)
    secondary = blob(resources, secondary_row)
    require(len(secondary) == 20,
            f"ordinal {draw['drawOrdinal']} secondary stream is not 20 bytes")
    return {"vertices": vertices, "indices": indices,
            "secondary": secondary, "index_count": index_count,
            "vertex_count": vertex_count}


def collect_texture(metadata: dict[str, Any], draw: dict[str, Any],
                    resources: bytes) -> dict[str, Any]:
    owned = [row for row in draw.get("resources", [])
             if row.get("stage") == 4 and row.get("slot") == 1]
    require(len(owned) == 1,
            f"ordinal {draw['drawOrdinal']} does not own one PS t1")
    row = selected(metadata, kind=3, object_id=int(owned[0]["objectId"]),
                   stage=4, slot=1)
    require(int(row.get("format", -1)) == TEXTURE_FORMAT and
            int(row.get("viewFormat", -1)) == TEXTURE_FORMAT,
            f"ordinal {draw['drawOrdinal']} texture is not BC7 sRGB")
    payload = blob(resources, row)
    width = int(row["width"])
    height = int(row["height"])
    require(len(payload) == ((width + 3) // 4) * ((height + 3) // 4) * 16,
            f"ordinal {draw['drawOrdinal']} BC7 payload size drifted")
    return {"object_id": int(row["objectId"]), "width": width,
            "height": height, "payload": payload, "sha256": sha256(payload)}


def validate_state(draw: dict[str, Any]) -> None:
    state = draw.get("pipelineState", {})
    samplers = state.get("samplers", [])
    require([(row.get("slot"), row.get("bound"), row.get("filter"),
              row.get("addressU"), row.get("addressV"), row.get("addressW"))
             for row in samplers] ==
            [(0, True, 0, 3, 3, 3), (1, True, 20, 1, 1, 1),
             (2, False, 0, 0, 0, 0)],
            f"ordinal {draw['drawOrdinal']} sampler state drifted")
    blend = state.get("blend", {})
    depth = state.get("depthStencil", {})
    rasterizer = state.get("rasterizer", {})
    require((blend.get("enabled"), blend.get("source"),
             blend.get("destination"), blend.get("operation"),
             blend.get("sourceAlpha"), blend.get("destinationAlpha"),
             blend.get("operationAlpha"), blend.get("writeMask")) ==
            (True, 2, 6, 1, 2, 6, 1, 15),
            f"ordinal {draw['drawOrdinal']} blend state drifted")
    require((depth.get("depthEnabled"), depth.get("writeMask"),
             depth.get("function"), depth.get("stencilEnabled"),
             depth.get("stencilReference")) == (True, 0, 7, True, 0),
            f"ordinal {draw['drawOrdinal']} depth/stencil state drifted")
    require((rasterizer.get("fillMode"), rasterizer.get("cullMode"),
             rasterizer.get("frontCounterClockwise"),
             rasterizer.get("depthClipEnabled"),
             rasterizer.get("scissorEnabled")) == (3, 1, True, True, True),
            f"ordinal {draw['drawOrdinal']} rasterizer state drifted")


def collect(capture: Path, report_path: Path
            ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    require(capture.name == EXPECTED_SESSION, "peak cohort session drifted")
    require(sha256(report_path.read_bytes()) == EXPECTED_REPORT_SHA256,
            "peak cohort report hash drifted")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    require(report.get("status") == "validated_exact_owner_resource_closure",
            "peak cohort report is not validated")
    frame_root = capture / "graphics/frames" / str(EXPECTED_FRAME)
    metadata_bytes = (frame_root / "metadata.json").read_bytes()
    require(sha256(metadata_bytes) == EXPECTED_METADATA_SHA256,
            "peak cohort metadata hash drifted")
    metadata = json.loads(metadata_bytes)
    resources = (frame_root / "resources.bin").read_bytes()
    candidates = [(index, draw)
                  for index, draw in enumerate(metadata.get("drawRecords", []))
                  if isinstance(draw, dict) and
                  shader_pair(draw) == (EXPECTED_VS, EXPECTED_PS)]
    candidates.sort(key=lambda row: int(row[1].get("drawOrdinal", -1)))
    require(tuple(int(draw["drawOrdinal"]) for _, draw in candidates) ==
            EXPECTED_ORDINALS and
            tuple(index for index, _ in candidates) == EXPECTED_DRAW_INDICES,
            "peak cohort draw identity/order drifted")
    textures_by_hash: dict[str, dict[str, Any]] = {}
    draws = []
    secondary_hash: str | None = None
    for draw_index, draw in candidates:
        validate_state(draw)
        geometry = collect_geometry(metadata, draw, resources)
        current_secondary_hash = sha256(geometry["secondary"])
        if secondary_hash is None:
            secondary_hash = current_secondary_hash
        require(current_secondary_hash == secondary_hash,
                "peak cohort secondary stream changed between draws")
        texture = collect_texture(metadata, draw, resources)
        textures_by_hash.setdefault(texture["sha256"], texture)
        draws.append({"draw_index": draw_index,
                      "ordinal": int(draw["drawOrdinal"]),
                      "geometry": geometry,
                      "constants": collect_constants(metadata, draw, resources),
                      "texture_hash": texture["sha256"]})
    textures = list(textures_by_hash.values())
    texture_indices = {row["sha256"]: index
                       for index, row in enumerate(textures)}
    for draw in draws:
        draw["texture_index"] = texture_indices[draw.pop("texture_hash")]
    require(len(draws) == 15 and len(textures) == 5,
            "peak cohort draw/texture closure drifted")
    return draws, textures


def cpp_array(name: str, payload: bytes) -> str:
    rows = ["    " + ", ".join(f"0x{x:02x}" for x in payload[i:i + 16]) + ","
            for i in range(0, len(payload), 16)]
    return (f"inline constexpr std::uint8_t {name}[] = {{\n" +
            "\n".join(rows) +
            f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n")


def render_cpp(draws: list[dict[str, Any]],
               textures: list[dict[str, Any]]) -> str:
    arrays: list[str] = [cpp_array(
        "g_EndfieldVFXPeakSecondary", draws[0]["geometry"]["secondary"])]
    texture_descriptors = []
    for index, texture in enumerate(textures):
        name = f"g_EndfieldVFXPeakTexture{index}"
        arrays.append(cpp_array(name, texture["payload"]))
        texture_descriptors.append(
            f"    {{{texture['width']}u, {texture['height']}u, {name}, {name}Size}},")
    draw_descriptors = []
    for index, draw in enumerate(draws):
        prefix = f"g_EndfieldVFXPeakD{index}"
        geometry = draw["geometry"]
        arrays.extend((cpp_array(prefix + "Vertices", geometry["vertices"]),
                       cpp_array(prefix + "Indices", geometry["indices"])))
        for stage, label in ((0, "VS"), (4, "PS")):
            for slot, payload in enumerate(draw["constants"][stage]):
                arrays.append(cpp_array(f"{prefix}{label}CB{slot}", payload))
        draw_descriptors.append(
            f"    {{{draw['ordinal']}u, {draw['draw_index']}u, "
            f"{geometry['index_count']}u, {draw['texture_index']}u, "
            f"{prefix}Vertices, {prefix}VerticesSize, {prefix}Indices, "
            f"{prefix}IndicesSize, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
    return (
        "// Generated by tools/build_endminf_vfxbasev2_peak_cohort.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldVFXPeakPayloadPrepared = true;\n"
        "inline constexpr std::uint32_t g_EndfieldVFXPeakFrame = 2723u;\n"
        "inline constexpr std::uint32_t g_EndfieldVFXPeakVertexStride = 36u;\n"
        "inline constexpr std::uint32_t g_EndfieldVFXPeakTextureFormat = 99u;\n"
        "inline constexpr std::uint32_t g_EndfieldVFXPeakVSDeclaredFloat4Counts[] = {2, 82, 104, 4094, 10};\n"
        "inline constexpr std::uint32_t g_EndfieldVFXPeakPSDeclaredFloat4Counts[] = {28, 105, 4085, 22};\n\n" +
        "\n".join(arrays) + "\n"
        "struct EndfieldVFXPeakTexturePayload { std::uint32_t width; "
        "std::uint32_t height; const std::uint8_t* data; std::size_t bytes; };\n"
        "inline constexpr EndfieldVFXPeakTexturePayload g_EndfieldVFXPeakTextures[] = {\n" +
        "\n".join(texture_descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldVFXPeakTextureCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldVFXPeakTextures) / "
        "sizeof(g_EndfieldVFXPeakTextures[0]));\n"
        "struct EndfieldVFXPeakDrawPayload { std::uint32_t ordinal; "
        "std::uint32_t drawIndex; std::uint32_t indexCount; "
        "std::uint32_t textureIndex; const std::uint8_t* vertices; "
        "std::size_t vertexBytes; const std::uint8_t* indices; "
        "std::size_t indexBytes; const std::uint8_t* vs[5]; "
        "std::size_t vsBytes[5]; const std::uint8_t* ps[4]; "
        "std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldVFXPeakDrawPayload g_EndfieldVFXPeakDraws[] = {\n" +
        "\n".join(draw_descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldVFXPeakDrawCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldVFXPeakDraws) / "
        "sizeof(g_EndfieldVFXPeakDraws[0]));\n")


def render_cs(draws: list[dict[str, Any]],
              textures: list[dict[str, Any]]) -> str:
    ordinals = ", ".join(str(row["ordinal"]) for row in draws)
    draw_indices = ", ".join(str(row["draw_index"]) for row in draws)
    counts = ", ".join(str(row["geometry"]["index_count"]) for row in draws)
    hashes = ", ".join(f'"{row["sha256"]}"' for row in textures)
    return f'''// Generated by tools/build_endminf_vfxbasev2_peak_cohort.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredVFXBaseV2PeakCohortData
    {{
        internal const string SourceSession = "{EXPECTED_SESSION}";
        internal const string ReportSha256 = "{EXPECTED_REPORT_SHA256}";
        internal const int SourceFrame = {EXPECTED_FRAME};
        internal const bool PayloadPrepared = true;
        internal const int DrawCount = {len(draws)};
        internal const int TextureCount = {len(textures)};
        internal static readonly int[] DrawOrdinals = {{ {ordinals} }};
        internal static readonly int[] DrawIndices = {{ {draw_indices} }};
        internal static readonly int[] IndexCounts = {{ {counts} }};
        internal static readonly string[] TextureSha256 = {{ {hashes} }};
    }}
}}
'''


def build(capture: Path, report: Path, cs_output: Path,
          cpp_output: Path) -> tuple[str, str]:
    draws, textures = collect(capture, report)
    cs = render_cs(draws, textures)
    cpp = render_cpp(draws, textures)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(cs, encoding="utf-8", newline="\n")
    cpp_output.write_text(cpp, encoding="utf-8", newline="\n")
    return cs, cpp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--cs-output", type=Path, default=CS_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.capture.resolve(), args.report.resolve(),
          args.cs_output.resolve(), args.cpp_output.resolve())
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
