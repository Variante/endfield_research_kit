#!/usr/bin/env python3
"""Build the fail-closed exact M29 crystal packet payload from retail capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import math
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260827T183054Z"
REPORT = (REPO / "reports/assets/character_recovery"
          / "endminf_m29_m30_capture_completeness_latest.json")
CONTRACT_CAPTURE = (
    REPO / "scratch/reverse_engineering/endfield_capture/20260827T225644Z")
CONTRACT_REPORT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_m29_m30_capture_completeness_20260827T225644Z.json")
SHADER_ROOT = (REPO / "scratch/character_recovery/vfx_shader_variants/shader_export"
               / "Shader/HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode")
VS_PATH = SHADER_ROOT / "4110_endfield_dxbc_0.dxbc"
PS_PATH = SHADER_ROOT / "4111_endfield_dxbc_1.dxbc"
CS_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
             / "Runtime/Rendering/EndfieldRecoveredM29ExactCaptureData.generated.cs")
CPP_OUTPUT = (REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
              / "M29CapturePayload.generated.h")

EXPECTED_SESSION = "20260827T183054Z"
EXPECTED_REPORT_SHA256 = "25f3cadc7ca27f18e4c420925cbf70a7566fb546966cbd8d5a541310ec5ccf20"
EXPECTED_CONTRACT_SESSION = "20260827T225644Z"
EXPECTED_CONTRACT_REPORT_SHA256 = (
    "c13a5d79cacadae35c151b76da8aa74f1191c2ebb155a616a17d723ba49b81e0")
EXPECTED_CONTRACT_FRAME = 2723
EXPECTED_CONTRACT_DRAW_INDEX = 7
EXPECTED_CONTRACT_METADATA_SHA256 = (
    "23b8256ca23339dd77cfea103caef13520744c96fcba47add8b4d00eddd4bffe")
EXPECTED_METADATA_SHA256 = {
    1732: "aa6dcb358fb30db9213ee864b2a1a6158742192b2a2313d9f1a5b7511b0d6782",
    1743: "4ec782cb8c8d680615b9ed7a4c904fd03a2ac312d95128b235dd0f4776921baf",
    1753: "b3ee04abff99125d0ec9dbbcc8c333a10f3f1a50e6bb17e3b776bd1a912f2aec",
    1764: "aafde22806286d42e98517a0d01a19fb57c213b3a392a80b44d08aafdb8bf4a9",
    1775: "51156b61aaf7735b3996cf490e433e31b5864a76f84b8c3243dbd7101a1a251d",
    1785: "9944c0f286f0a4f3fc7f4568f82926dc177314958bd32493ca6634dfaf360da4",
    1796: "968ba927d70065ccf4fcd427ea73e3bad314c29ab2c59d9de9eaaf4666033db8",
    1807: "aea0bc35f7b9412968c6f9668168217291f023826b66afb76971321e49b88a46",
}
EXPECTED_VS_SHA256 = "ce755059deddc2e005111633763b9f7f9f7263ccd80321e70eeb9164096f6093"
EXPECTED_PS_SHA256 = "f2ad2a14856044acae0e7de2699678e65af2e91a949404cc71a6d35a692ba62e"
EXPECTED_VS = 0xCE755059DEDDC2E0
EXPECTED_PS = 0xF2AD2A14856044AC
VS_DECLARED = (2, 82, 104, 4094, 39)
PS_DECLARED = (28, 105, 4085, 33)
CAPTURE_FPS = 60.0
# Direct backbuffer-to-clean-reference matches. Capture frame deltas are not a
# valid animation clock because synchronous readback stalls changed the number
# of presented frames between samples. In the clean extracted sequence,
# reference frame 269 is the established 4.433333-second body-phase anchor,
# hence phase = (referenceFrame - 3) / 60.
REFERENCE_FRAMES = {
    1732: 156,
    1743: 167,
    1753: 182,
    1764: 195,
    1775: 210,
    1785: 224,
    1796: 238,
    1807: 251,
}
CONTRACT_REFERENCE_FRAME = 219
INDEX_COUNT = 1386
VERTEX_COUNT = 300
INDEX_FORMAT = 57
TEXTURE_FORMAT = 99


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def is_m29(draw: dict[str, Any]) -> bool:
    pair = {row.get("stage"): int(row.get("identityHash", 0))
            for row in draw.get("shaders", []) if isinstance(row, dict)}
    return (draw.get("priorityM29Geometry") is True and
            int(draw.get("count", -1)) == INDEX_COUNT and
            int(draw.get("instanceCount", -1)) == 1 and
            pair.get(0) == EXPECTED_VS and pair.get(4) == EXPECTED_PS)


def selected(metadata: dict[str, Any], *, kind: int, object_id: int,
             stage: int | None = None, slot: int | None = None) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict) and row.get("captureKind") == kind
            and int(row.get("objectId", 0)) == object_id
            and row.get("completed") is True]
    if stage is not None:
        rows = [row for row in rows if row.get("stage") == stage]
    if slot is not None:
        rows = [row for row in rows if row.get("slot") == slot]
    require(len(rows) == 1,
            f"captureKind {kind} object {object_id} stage {stage} slot {slot} is not unique")
    return rows[0]


def blob(resources: bytes, row: dict[str, Any]) -> bytes:
    start = int(row["blobOffset"])
    size = int(row["blobBytes"])
    require(start >= 0 and size > 0 and start + size <= len(resources),
            "selected resource exceeds resources.bin")
    return resources[start:start + size]


def collect_constants(metadata: dict[str, Any], draw: dict[str, Any],
                      resources: bytes) -> dict[int, list[bytes]]:
    result: dict[int, list[bytes]] = {0: [], 4: []}
    for stage, declared in ((0, VS_DECLARED), (4, PS_DECLARED)):
        for slot, count in enumerate(declared):
            bindings = [row for row in draw.get("constantBuffers", [])
                        if row.get("stage") == stage and row.get("slot") == slot]
            require(len(bindings) == 1, f"M29 stage {stage} b{slot} is not unique")
            binding = bindings[0]
            require(binding.get("rangeValid") is True and
                    binding.get("metadataValid") is True,
                    f"M29 stage {stage} b{slot} range is invalid")
            backing = selected(metadata, kind=2,
                               object_id=int(binding["bufferId"]))
            allocation = blob(resources, backing)
            start = int(binding["firstConstant"]) * 16
            end = start + count * 16
            require(end <= len(allocation),
                    f"M29 stage {stage} b{slot} declared range exceeds backing allocation")
            result[stage].append(allocation[start:end])
    return result


def collect_geometry(metadata: dict[str, Any], draw: dict[str, Any],
                     resources: bytes, *, draw_local: bool = False
                     ) -> dict[str, Any]:
    owned = [row for row in draw.get("resources", [])
             if row.get("stage") == 0 and row.get("slot") in (0, 1)]
    primary = [row for row in owned if row.get("slot") == 0]
    secondary = [row for row in owned if row.get("slot") == 1]
    require(len(primary) == len(secondary) == 1, "M29 IA ownership is incomplete")
    primary_id = int(primary[0]["objectId"])
    vb = selected(metadata, kind=0, object_id=primary_id, stage=0, slot=0)
    ib = selected(metadata, kind=1, object_id=primary_id, stage=0, slot=0)
    skin = selected(metadata, kind=0, object_id=int(secondary[0]["objectId"]),
                    stage=0, slot=1)
    vertex_offset = int(vb["byteOffset"])
    index_offset = int(ib["byteOffset"])
    stride = int(vb["stride"])
    if draw_local:
        assembler = draw.get("inputAssembler")
        require(isinstance(assembler, dict),
                "M29 draw-local IA descriptor is unavailable")
        vertex_bindings = [row for row in assembler.get("vertexBuffers", [])
                           if isinstance(row, dict) and row.get("slot") == 0]
        index_binding = assembler.get("indexBuffer")
        require(len(vertex_bindings) == 1 and isinstance(index_binding, dict),
                "M29 draw-local IA slot 0/index binding is incomplete")
        vertex_binding = vertex_bindings[0]
        require(int(vertex_binding.get("objectId", 0)) == primary_id and
                int(index_binding.get("objectId", 0)) == primary_id,
                "M29 draw-local IA ownership drifted")
        stride = int(vertex_binding.get("stride", 0))
        vertex_offset = int(vertex_binding.get("offset", -1))
        index_offset = int(index_binding.get("offset", -1))
        require(int(index_binding.get("format", -1)) == INDEX_FORMAT and
                int(draw.get("topology", -1)) == 4,
                "M29 draw-local index format/topology drifted")
    require(stride in (60, 68), f"M29 unsupported vertex stride {stride}")
    require(int(ib["stride"]) == 2 and int(ib["format"]) == INDEX_FORMAT,
            "M29 index binding is not R16_UINT")
    primary_blob = blob(resources, vb)
    require(int(vb["blobOffset"]) == int(ib["blobOffset"]) and
            int(vb["blobBytes"]) == int(ib["blobBytes"]),
            "M29 vertex/index ring alias drifted")
    vertex_start = vertex_offset + int(draw["baseVertex"]) * stride
    index_start = index_offset + int(draw["start"]) * 2
    vertices = primary_blob[vertex_start:vertex_start + VERTEX_COUNT * stride]
    indices = primary_blob[index_start:index_start + INDEX_COUNT * 2]
    require(len(vertices) == VERTEX_COUNT * stride and
            len(indices) == INDEX_COUNT * 2, "M29 IA slice is truncated")
    values = struct.unpack("<" + "H" * INDEX_COUNT, indices)
    require(min(values) == 0 and max(values) == VERTEX_COUNT - 1 and
            len(set(values)) == VERTEX_COUNT,
            "M29 index slice does not close the 300-vertex mesh")
    secondary_bytes = blob(resources, skin)
    require(len(secondary_bytes) == 20, "M29 secondary IA stream is not 20 bytes")
    positions = [struct.unpack_from("<3f", vertices, index * stride)
                 for index in range(VERTEX_COUNT)]
    geometry_contract_ready = all(
        math.isfinite(component) and abs(component) < 10000.0
        for position in positions for component in position)
    if geometry_contract_ready:
        extents = [max(position[axis] for position in positions) -
                   min(position[axis] for position in positions)
                   for axis in range(3)]
        geometry_contract_ready = max(extents) < 10.0 and max(extents) > 1.0e-4
    return {"stride": stride, "vertices": vertices, "indices": indices,
            "secondary": secondary_bytes,
            "geometry_contract_ready": geometry_contract_ready}


def collect_contract_packet(capture: Path, report_path: Path) -> dict[str, Any]:
    require(capture.name == EXPECTED_CONTRACT_SESSION,
            "M29 draw-contract capture session drifted")
    report_bytes = report_path.read_bytes()
    require(sha256(report_bytes) == EXPECTED_CONTRACT_REPORT_SHA256,
            "M29 draw-contract report hash drifted")
    report = json.loads(report_bytes)
    owner = report.get("owners", {}).get("M29", {})
    packets = owner.get("packets", [])
    require(report.get("status") == "validated_exact_owner_resource_closure" and
            owner.get("packetCount") == len(packets) == 1 and
            int(packets[0].get("frame", -1)) == EXPECTED_CONTRACT_FRAME and
            int(packets[0].get("drawIndex", -1)) == EXPECTED_CONTRACT_DRAW_INDEX,
            "M29 draw-contract resource closure drifted")
    frame_root = capture / "graphics/frames" / str(EXPECTED_CONTRACT_FRAME)
    metadata_bytes = (frame_root / "metadata.json").read_bytes()
    require(sha256(metadata_bytes) == EXPECTED_CONTRACT_METADATA_SHA256,
            "M29 draw-contract metadata hash drifted")
    metadata = json.loads(metadata_bytes)
    rows = metadata.get("drawRecords", [])
    require(EXPECTED_CONTRACT_DRAW_INDEX < len(rows),
            "M29 draw-contract draw is unavailable")
    draw = rows[EXPECTED_CONTRACT_DRAW_INDEX]
    require(is_m29(draw) and int(draw.get("drawOrdinal", -1)) == 73,
            "M29 draw-contract owner/chronology drifted")
    state = draw.get("pipelineState", {})
    samplers = state.get("samplers", [])
    require([(row.get("slot"), row.get("bound"), row.get("filter"),
              row.get("addressU"), row.get("addressV"), row.get("addressW"))
             for row in samplers] ==
            [(0, True, 20, 1, 1, 1), (1, True, 20, 1, 1, 1),
             (2, True, 20, 1, 1, 1)],
            "M29 draw-contract sampler state drifted")
    blend = state.get("blend", {})
    depth = state.get("depthStencil", {})
    rasterizer = state.get("rasterizer", {})
    require((blend.get("enabled"), blend.get("source"),
             blend.get("destination"), blend.get("operation"),
             blend.get("sourceAlpha"), blend.get("destinationAlpha"),
             blend.get("operationAlpha"), blend.get("writeMask")) ==
            (True, 2, 6, 1, 2, 6, 1, 15),
            "M29 draw-contract blend state drifted")
    require((depth.get("depthEnabled"), depth.get("writeMask"),
             depth.get("function"), depth.get("stencilEnabled"),
             depth.get("stencilReference")) == (True, 0, 8, True, 0),
            "M29 draw-contract depth/stencil state drifted")
    require((rasterizer.get("fillMode"), rasterizer.get("cullMode"),
             rasterizer.get("frontCounterClockwise"),
             rasterizer.get("depthClipEnabled"),
             rasterizer.get("scissorEnabled")) == (3, 1, True, True, True),
            "M29 draw-contract rasterizer state drifted")
    resources = (frame_root / "resources.bin").read_bytes()
    geometry = collect_geometry(metadata, draw, resources, draw_local=True)
    require(geometry["geometry_contract_ready"],
            "M29 draw-contract geometry is not replay-safe")
    geometry["source_frame"] = EXPECTED_CONTRACT_FRAME
    return {
        "frame": EXPECTED_CONTRACT_FRAME,
        "phase": (CONTRACT_REFERENCE_FRAME - 3) / CAPTURE_FPS,
        "geometry": geometry,
        "constants": collect_constants(metadata, draw, resources),
        "textures": collect_textures(metadata, draw, resources),
    }


def collect_textures(metadata: dict[str, Any], draw: dict[str, Any],
                     resources: bytes) -> tuple[bytes, bytes]:
    payloads: dict[int, bytes] = {}
    for slot, dimensions, size in ((0, (256, 256), 65536),
                                   (1, (512, 512), 262144),
                                   (2, (512, 512), 262144)):
        owned = [row for row in draw.get("resources", [])
                 if row.get("stage") == 4 and row.get("slot") == slot]
        require(len(owned) == 1, f"M29 PS t{slot} ownership is incomplete")
        row = selected(metadata, kind=3, object_id=int(owned[0]["objectId"]),
                       stage=4, slot=slot)
        require((int(row.get("format", -1)), int(row.get("viewFormat", -1)),
                 int(row.get("width", -1)), int(row.get("height", -1))) ==
                (TEXTURE_FORMAT, TEXTURE_FORMAT, *dimensions),
                f"M29 PS t{slot} descriptor drifted")
        payloads[slot] = blob(resources, row)
        require(len(payloads[slot]) == size, f"M29 PS t{slot} payload size drifted")
    require(payloads[1] == payloads[2], "M29 PS t1/t2 alias payload drifted")
    return payloads[0], payloads[1]


def collect(capture: Path, report_path: Path, vs_path: Path,
            ps_path: Path, contract_capture: Path = CONTRACT_CAPTURE,
            contract_report: Path = CONTRACT_REPORT
            ) -> tuple[list[dict[str, Any]], bytes, bytes, bytes, bytes]:
    require(capture.name == EXPECTED_SESSION, "M29 capture session drifted")
    report_bytes = report_path.read_bytes()
    require(sha256(report_bytes) == EXPECTED_REPORT_SHA256,
            "M29 completeness report hash drifted")
    report = json.loads(report_bytes)
    owner = report.get("owners", {}).get("M29", {})
    expected_packets = owner.get("packets", [])
    require(report.get("status") == "validated_exact_owner_resource_closure" and
            owner.get("packetCount") == len(expected_packets) == 8,
            "M29 completeness report is not an eight-packet closure")
    vs = vs_path.read_bytes()
    ps = ps_path.read_bytes()
    require(sha256(vs) == EXPECTED_VS_SHA256 and len(vs) == 7172,
            "M29 vertex bytecode drifted")
    require(sha256(ps) == EXPECTED_PS_SHA256 and len(ps) == 6520,
            "M29 pixel bytecode drifted")
    require(int(sha256(vs)[:16], 16) == EXPECTED_VS and
            int(sha256(ps)[:16], 16) == EXPECTED_PS,
            "M29 capture shader identity is not the sidecar SHA-256 prefix")
    contract_packet = collect_contract_packet(
        contract_capture, contract_report)
    contract_geometry = contract_packet["geometry"]
    packets: list[dict[str, Any]] = []
    texture_hashes: tuple[str, str] | None = None
    texture_payloads: tuple[bytes, bytes] | None = None
    secondary_hash: str | None = None
    for expected in expected_packets:
        frame = int(expected["frame"])
        frame_root = capture / "graphics/frames" / str(frame)
        metadata_bytes = (frame_root / "metadata.json").read_bytes()
        require(sha256(metadata_bytes) == EXPECTED_METADATA_SHA256.get(frame),
                f"M29 frame {frame} metadata hash drifted")
        metadata = json.loads(metadata_bytes)
        rows = metadata.get("drawRecords", [])
        draw_index = int(expected["drawIndex"])
        require(0 <= draw_index < len(rows) and is_m29(rows[draw_index]),
                f"M29 frame {frame} report owner identity drifted")
        draw = rows[draw_index]
        resources = (frame_root / "resources.bin").read_bytes()
        geometry = collect_geometry(metadata, draw, resources)
        constants = collect_constants(metadata, draw, resources)
        textures = collect_textures(metadata, draw, resources)
        hashes = (sha256(textures[0]), sha256(textures[1]))
        if texture_hashes is None:
            texture_hashes, texture_payloads = hashes, textures
        require(hashes == texture_hashes, "M29 textures changed across temporal packets")
        current_secondary = sha256(geometry["secondary"])
        if secondary_hash is None:
            secondary_hash = current_secondary
        require(current_secondary == secondary_hash,
                "M29 secondary IA stream changed across temporal packets")
        if geometry["geometry_contract_ready"]:
            geometry["source_frame"] = frame
        else:
            geometry = dict(contract_geometry)
        require(frame in REFERENCE_FRAMES,
                f"M29 frame {frame} has no clean-reference phase match")
        packets.append({"frame": frame,
                        "phase": (REFERENCE_FRAMES[frame] - 3) / CAPTURE_FPS,
                        "geometry": geometry, "constants": constants})
    assert texture_payloads is not None
    contract_textures = contract_packet.pop("textures")
    require((sha256(contract_textures[0]), sha256(contract_textures[1])) ==
            texture_hashes,
            "M29 draw-contract textures changed from the temporal capture")
    require(sha256(contract_geometry["secondary"]) == secondary_hash,
            "M29 draw-contract secondary IA stream changed")
    packets.append(contract_packet)
    packets.sort(key=lambda packet: packet["phase"])
    return packets, texture_payloads[0], texture_payloads[1], vs, ps


def cpp_array(name: str, payload: bytes) -> str:
    rows = ["    " + ", ".join(f"0x{x:02x}" for x in payload[i:i + 16]) + ","
            for i in range(0, len(payload), 16)]
    return (f"inline constexpr std::uint8_t {name}[] = {{\n" + "\n".join(rows) +
            f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n")


def render_cpp(packets: list[dict[str, Any]], t0: bytes, t1: bytes,
               vs: bytes, ps: bytes) -> str:
    arrays = [cpp_array("g_EndfieldM29VertexShaderBytecode", vs),
              cpp_array("g_EndfieldM29PixelShaderBytecode", ps),
              cpp_array("g_EndfieldM29TextureT0", t0),
              cpp_array("g_EndfieldM29TextureT1", t1)]
    descriptors = []
    for index, packet in enumerate(packets):
        prefix = f"g_EndfieldM29P{index}"
        geometry = packet["geometry"]
        arrays.extend((cpp_array(prefix + "Vertices", geometry["vertices"]),
                       cpp_array(prefix + "Indices", geometry["indices"]),
                       cpp_array(prefix + "Secondary", geometry["secondary"])))
        for stage, label in ((0, "VS"), (4, "PS")):
            for slot, payload in enumerate(packet["constants"][stage]):
                arrays.append(cpp_array(f"{prefix}{label}CB{slot}", payload))
        descriptors.append(
            f"    {{{packet['frame']}u, {packet['phase']:.6f}f, "
            f"{geometry['source_frame']}u, {geometry['stride']}u, "
            f"{prefix}Vertices, {prefix}VerticesSize, {prefix}Indices, "
            f"{prefix}IndicesSize, {INDEX_COUNT}u, {prefix}Secondary, "
            f"{prefix}SecondarySize, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
    geometry_ready = all(packet["geometry"]["geometry_contract_ready"]
                         for packet in packets)
    return (
        "// Generated by tools/build_endminf_m29_exact_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM29PayloadPrepared = true;\n"
        f"inline constexpr bool g_EndfieldM29GeometryContractReady = {'true' if geometry_ready else 'false'};\n"
        "inline constexpr std::uint32_t g_EndfieldM29TextureFormat = 99;\n"
        "inline constexpr std::uint32_t g_EndfieldM29TextureT0Width = 256;\n"
        "inline constexpr std::uint32_t g_EndfieldM29TextureT0Height = 256;\n"
        "inline constexpr std::uint32_t g_EndfieldM29TextureT1Width = 512;\n"
        "inline constexpr std::uint32_t g_EndfieldM29TextureT1Height = 512;\n"
        "inline constexpr std::uint32_t g_EndfieldM29VSDeclaredFloat4Counts[] = {2, 82, 104, 4094, 39};\n"
        "inline constexpr std::uint32_t g_EndfieldM29PSDeclaredFloat4Counts[] = {28, 105, 4085, 33};\n\n" +
        "\n".join(arrays) + "\n"
        "struct EndfieldM29PacketPayload { std::uint32_t frame; float phaseSeconds; "
        "std::uint32_t geometrySourceFrame; std::uint32_t vertexStride; "
        "const std::uint8_t* vertices; "
        "std::size_t vertexBytes; const std::uint8_t* indices; "
        "std::size_t indexBytes; std::uint32_t indexCount; "
        "const std::uint8_t* secondary; std::size_t secondaryBytes; "
        "const std::uint8_t* vs[5]; std::size_t vsBytes[5]; "
        "const std::uint8_t* ps[4]; std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldM29PacketPayload g_EndfieldM29Packets[] = {\n" +
        "\n".join(descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM29PacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM29Packets) / "
        "sizeof(g_EndfieldM29Packets[0]));\n")


def render_cs(packets: list[dict[str, Any]], t0: bytes, t1: bytes) -> str:
    frames = ", ".join(str(row["frame"]) for row in packets)
    phases = ", ".join(f"{row['phase']:.6f}f" for row in packets)
    strides = ", ".join(str(row["geometry"]["stride"]) for row in packets)
    geometry_frames = ", ".join(
        str(row["geometry"]["source_frame"]) for row in packets)
    geometry_ready = all(row["geometry"]["geometry_contract_ready"]
                         for row in packets)
    return f'''// Generated by tools/build_endminf_m29_exact_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM29ExactCaptureData
    {{
        internal const string SourceSession = "{EXPECTED_SESSION}";
        internal const string DrawContractSession = "{EXPECTED_CONTRACT_SESSION}";
        internal const string ReportSha256 = "{EXPECTED_REPORT_SHA256}";
        internal const string DrawContractReportSha256 = "{EXPECTED_CONTRACT_REPORT_SHA256}";
        internal const string TextureT0Sha256 = "{sha256(t0)}";
        internal const string TextureT1Sha256 = "{sha256(t1)}";
        internal const bool PayloadPrepared = true;
        internal const bool GeometryContractReady = {str(geometry_ready).lower()};
        internal const int PacketCount = {len(packets)};
        internal static readonly int[] SourceFrames = {{ {frames} }};
        internal static readonly int[] GeometrySourceFrames = {{ {geometry_frames} }};
        internal static readonly float[] PacketPhases = {{ {phases} }};
        internal static readonly int[] VertexStrides = {{ {strides} }};
    }}
}}
'''


def build(capture: Path, report: Path, vs_path: Path, ps_path: Path,
          cs_output: Path, cpp_output: Path,
          contract_capture: Path = CONTRACT_CAPTURE,
          contract_report: Path = CONTRACT_REPORT) -> tuple[str, str]:
    packets, t0, t1, vs, ps = collect(
        capture, report, vs_path, ps_path, contract_capture, contract_report)
    cs = render_cs(packets, t0, t1)
    cpp = render_cpp(packets, t0, t1, vs, ps)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(cs, encoding="utf-8", newline="\n")
    cpp_output.write_text(cpp, encoding="utf-8", newline="\n")
    return cs, cpp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--contract-capture", type=Path,
                        default=CONTRACT_CAPTURE)
    parser.add_argument("--contract-report", type=Path,
                        default=CONTRACT_REPORT)
    parser.add_argument("--vs", type=Path, default=VS_PATH)
    parser.add_argument("--ps", type=Path, default=PS_PATH)
    parser.add_argument("--cs-output", type=Path, default=CS_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.capture.resolve(), args.report.resolve(), args.vs.resolve(),
          args.ps.resolve(), args.cs_output.resolve(), args.cpp_output.resolve(),
          args.contract_capture.resolve(), args.contract_report.resolve())
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
