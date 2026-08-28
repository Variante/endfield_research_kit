#!/usr/bin/env python3
"""Build the exact M31 payload plus its source-backed temporal envelope."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_endminf_m30_exact_capture_data as shared


REPO = Path(__file__).resolve().parents[2]
TEMPORAL_CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260828T121603Z"
PAYLOAD_CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260827T183054Z"
CAPTURE = TEMPORAL_CAPTURE
FRAME = 1818
PHASE_SECONDS = 4.35
ANCHOR_FRAME = 1977
QPC_FREQUENCY = 10_000_000
TEMPORAL_FRAMES = (1896, 1907, 1918, 1929, 1941, 1954, 1965, 1977, 1989)
EXPECTED_TEMPORAL_DRAWS = {
    1896: ((68, 4974, 2123), (77, 4974, 330)),
    1907: ((68, 4974, 2200), (79, 4974, 330)),
    1918: ((68, 3978, 2036), (79, 3978, 330)),
    1929: ((77, 3978, 2245), (89, 3978, 475)),
    1941: ((77, 3210, 1946), (89, 3210, 507)),
    1954: ((68, 2442, 1600), (80, 2442, 192)),
    1965: ((77, 2442, 522), (89, 2442, 96)),
    1977: ((66, 4542, 1082), (74, 4542, 443), (89, 4542, 32)),
    1989: ((67, 4830, 1785),),
}
EXPECTED_TEMPORAL_METADATA_SHA256 = {
    1896: "0b3e01b79571ffefea96f8e85003175c5d84e19b13e6f36ada8ae732f63a0a3d",
    1907: "670e3bb377b0543bd41ada162658b271de65126e9eeb3fc61353f87c5a99056f",
    1918: "a11b69b7c272962d9fd520e669067ed85aa3a487d90681dca0bbd61e9d71b1f9",
    1929: "2febf2b8d695a875e47a703bf257b41e40c839c01014353fdd85e7bd33a1359a",
    1941: "80a27368912493b3174d16da456b886d21d40a26cc411a2961f24ca61fe15feb",
    1954: "1b679b6812dd900601658215ded73a93b508e92fe59ee73874ef61fbf82745e9",
    1965: "d5e2befceb977423b0f70cf54e1e8164f91a178f71dc928dd8c5b576026dd21e",
    1977: "b5029723d017bb9a558eff0df96c58fedae7ffeeac6a92c03ffaae4ee32604e2",
    1989: "65989294287f6c09b7f81257a55bda950c55acee089151cb294fd10b03412665",
}
CS_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Runtime/Rendering/EndfieldRecoveredM31PeakCaptureData.generated.cs"
)
CPP_OUTPUT = (
    REPO / "unity_endfield_graph_shader_lab/tools/original_dxbc_exact"
    / "M31PeakCapturePayload.generated.h"
)
EXPECTED_SESSION = "20260827T183054Z"
EXPECTED_TEMPORAL_SESSION = "20260828T121603Z"
EXPECTED_VS = 0x62A5CE6C09171DE9
EXPECTED_PS = 0x5558DEDDB1EE6188
EXPECTED_C1 = (1.0, 0.0, 1.4, 1.35)
EXPECTED_C4 = (
    (1.0, 0.5607878, 0.0976956, 1.0),
    (1.0, 1.0, 1.0, 1.0),
)
EXPECTED_TEXTURE_SHA256 = "faa8e27acd0e887456212f4f281b5cc897442ad7ebf8415db2fe3f164d381bc0"
M29_VS = 0xCE755059DEDDC2E0
M29_PS = 0xF2AD2A14856044AC
M30_C1 = (1.0, 0.0, 3.0, 0.5)
EXPECTED_INTERLEAVED_M29_M30_COUNTS = (2, 2, 2, 2, 2, 2, 2, 0, 0)
EXPECTED_SPLIT_ORDER_COMPATIBLE = (
    True, True, True, True, True, True, True, False, False)


def is_m31(draw: dict[str, Any]) -> bool:
    pair = {int(row.get("stage", -1)): int(row.get("identityHash", 0))
            for row in draw.get("shaders", []) if isinstance(row, dict)}
    if (int(draw.get("count", -1)) != 6 or
            pair.get(0) != EXPECTED_VS or pair.get(4) != EXPECTED_PS):
        return False
    try:
        b3 = shared.constant(draw, 4, 3)
    except ValueError:
        return False
    return (shared.close(shared.vector(b3, 1), EXPECTED_C1) and
            any(shared.close(shared.vector(b3, 4), value)
                for value in EXPECTED_C4))


def is_m29_or_m30(draw: dict[str, Any]) -> bool:
    pair = {int(row.get("stage", -1)): int(row.get("identityHash", 0))
            for row in draw.get("shaders", []) if isinstance(row, dict)}
    if pair.get(0) == M29_VS and pair.get(4) == M29_PS:
        return True
    if pair.get(0) != EXPECTED_VS or pair.get(4) != EXPECTED_PS:
        return False
    try:
        return shared.close(shared.vector(shared.constant(draw, 4, 3), 1),
                            M30_C1)
    except ValueError:
        return False


def selected_resource(metadata: dict[str, Any], *, capture_kind: int,
                      stage: int, slot: int, object_id: int) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict) and
            int(row.get("captureKind", -1)) == capture_kind and
            int(row.get("stage", -1)) == stage and
            int(row.get("slot", -1)) == slot and
            int(row.get("objectId", 0)) == object_id]
    shared.require(len(rows) == 1 and rows[0].get("completed") is True,
                   f"M31 resource kind={capture_kind} stage={stage} "
                   f"slot={slot} object={object_id} is not uniquely complete")
    return rows[0]


def validate_temporal_resources(frame_root: Path, metadata: dict[str, Any],
                                draw: dict[str, Any]) -> str:
    ia = draw.get("inputAssembler", {})
    vertex_buffers = ia.get("vertexBuffers", [])
    shared.require(len(vertex_buffers) == 2,
                   "M31 does not bind exactly two IA vertex streams")
    vb0, vb1 = vertex_buffers
    index = ia.get("indexBuffer", {})
    shared.require((int(vb0.get("slot", -1)), int(vb0.get("stride", -1)),
                    int(vb0.get("offset", -1))) == (0, 36, 951184),
                   "M31 primary IA stream identity drifted")
    shared.require((int(vb1.get("slot", -1)), int(vb1.get("stride", -1)),
                    int(vb1.get("offset", -1))) == (1, 0, 0),
                   "M31 secondary IA stream identity drifted")
    shared.require(int(index.get("objectId", 0)) == int(vb0["objectId"]) and
                   int(index.get("format", -1)) == 57 and
                   int(index.get("offset", -1)) >= 0,
                   "M31 R16 index-ring identity drifted")

    resources = {(int(row.get("stage", -1)), int(row.get("slot", -1))): row
                 for row in draw.get("resources", []) if isinstance(row, dict)}
    shared.require(set(resources) == {(0, 0), (0, 1), (4, 0), (4, 1)},
                   "M31 draw resource-slot closure drifted")
    shared.require(int(resources[(0, 0)]["objectId"]) == int(vb0["objectId"]) and
                   int(resources[(0, 1)]["objectId"]) == int(vb1["objectId"]),
                   "M31 IA draw/resource ownership drifted")

    vertex = selected_resource(metadata, capture_kind=0, stage=0, slot=0,
                               object_id=int(vb0["objectId"]))
    secondary = selected_resource(metadata, capture_kind=0, stage=0, slot=1,
                                  object_id=int(vb1["objectId"]))
    indices = selected_resource(metadata, capture_kind=1, stage=0, slot=0,
                                object_id=int(index["objectId"]))
    scene = selected_resource(metadata, capture_kind=3, stage=4, slot=0,
                              object_id=int(resources[(4, 0)]["objectId"]))
    texture = selected_resource(metadata, capture_kind=3, stage=4, slot=1,
                                object_id=int(resources[(4, 1)]["objectId"]))
    # EndfieldCapture retains the shared ring once and may annotate that one
    # selected row with a different owner's stride. The draw-level IA binding
    # above is authoritative for M31; object, byte offset and payload identity
    # are the valid selected-resource closure keys.
    shared.require((int(vertex.get("blobBytes", 0)),
                    int(vertex.get("byteOffset", -1))) == (4194304, 951184),
                   "M31 retained primary IA descriptor drifted")
    shared.require(int(secondary.get("blobBytes", 0)) == 20,
                   "M31 retained secondary IA descriptor drifted")
    shared.require((int(indices.get("blobBytes", 0)), int(indices.get("stride", -1)),
                    int(indices.get("format", -1)),
                    int(indices.get("byteOffset", -1))) ==
                   (4194304, 2, 57, int(index["offset"])),
                   "M31 retained index descriptor drifted")
    shared.require((int(scene.get("width", 0)), int(scene.get("height", 0)),
                    int(scene.get("format", -1)), int(scene.get("viewFormat", -1)),
                    int(scene.get("blobBytes", 0))) ==
                   (3840, 2160, 41, 41, 33177600),
                   "M31 retained SceneColor descriptor drifted")
    shared.require((int(texture.get("width", 0)), int(texture.get("height", 0)),
                    int(texture.get("format", -1)),
                    int(texture.get("viewFormat", -1)),
                    int(texture.get("blobBytes", 0))) ==
                   (256, 256, 99, 99, 65536),
                   "M31 retained PS t1 descriptor drifted")
    blob = (frame_root / "resources.bin").read_bytes()
    start = int(texture["blobOffset"])
    payload = blob[start:start + int(texture["blobBytes"])]
    digest = shared.sha256_bytes(payload)
    shared.require(digest == EXPECTED_TEXTURE_SHA256,
                   "M31 retained PS t1 identity drifted")
    return digest


def validate_temporal_draw(draw: dict[str, Any], frame: int, draw_index: int,
                           start: int, base_vertex: int) -> None:
    shared.require(is_m31(draw),
                   f"M31 frame {frame} draw {draw_index} identity drifted")
    shared.require((int(draw.get("count", -1)), int(draw.get("start", -1)),
                    int(draw.get("baseVertex", -1)),
                    int(draw.get("instanceCount", -1)),
                    int(draw.get("startInstance", -1)),
                    int(draw.get("topology", -1))) ==
                   (6, start, base_vertex, 1, 0, 4),
                   f"M31 frame {frame} draw {draw_index} args drifted")
    shared.collect_constants(draw)


def collect_temporal(capture: Path) -> list[dict[str, Any]]:
    shared.require(capture.name == EXPECTED_TEMPORAL_SESSION,
                   "M31 temporal source session drifted")
    session = shared.load_json(capture / "session.json")
    shared.require(int(session.get("qpcFrequency", 0)) == QPC_FREQUENCY,
                   "M31 temporal QPC frequency drifted")
    anchor_metadata = shared.load_json(
        capture / "graphics/frames" / str(ANCHOR_FRAME) / "metadata.json")
    anchor_qpc = int(anchor_metadata.get("timestampQpc", 0))
    shared.require(anchor_qpc > 0, "M31 temporal anchor QPC is absent")

    packets: list[dict[str, Any]] = []
    for frame in TEMPORAL_FRAMES:
        frame_root = capture / "graphics/frames" / str(frame)
        metadata_path = frame_root / "metadata.json"
        metadata_bytes = metadata_path.read_bytes()
        shared.require(shared.sha256_bytes(metadata_bytes) ==
                       EXPECTED_TEMPORAL_METADATA_SHA256[frame],
                       f"M31 temporal frame {frame} metadata hash drifted")
        metadata = shared.load_json(metadata_path)
        shared.require(metadata.get("captureIncomplete") is False and
                       metadata.get("drawRecordsTruncated") is False,
                       f"M31 temporal frame {frame} is incomplete")
        expected = EXPECTED_TEMPORAL_DRAWS[frame]
        draws = []
        for draw_index, start, base_vertex in expected:
            rows = metadata.get("drawRecords", [])
            shared.require(0 <= draw_index < len(rows),
                           f"M31 frame {frame} draw {draw_index} is absent")
            draw = rows[draw_index]
            shared.require(isinstance(draw, dict),
                           f"M31 frame {frame} draw {draw_index} is malformed")
            validate_temporal_draw(draw, frame, draw_index, start, base_vertex)
            validate_temporal_resources(frame_root, metadata, draw)
            draws.append(draw_index)
        all_m31 = [index for index, row in enumerate(metadata.get("drawRecords", []))
                   if isinstance(row, dict) and is_m31(row)]
        shared.require(all_m31 == draws,
                       f"M31 frame {frame} owner draw set drifted")
        qpc = int(metadata.get("timestampQpc", 0))
        interleaved_m29_m30 = [
            index for index in range(draws[0] + 1, draws[-1])
            if is_m29_or_m30(metadata["drawRecords"][index])
        ]
        packets.append({
            "frame": frame,
            "phase": PHASE_SECONDS + (qpc - anchor_qpc) / QPC_FREQUENCY,
            "draw_indices": draws,
            "draw_count": len(draws),
            # The current native event submits one contiguous packet. Retail
            # interleaves every retained multi-draw M31 packet with other
            # owners, so those packets cannot be replayed at one pipeline
            # insertion point without changing blend/depth chronology.
            "native_order_compatible": all(
                right == left + 1 for left, right in zip(draws, draws[1:])),
            "interleaved_m29_m30": interleaved_m29_m30,
            "split_order_compatible": (
                len(draws) == 2 and len(interleaved_m29_m30) == 2),
            "metadata_sha256": EXPECTED_TEMPORAL_METADATA_SHA256[frame],
        })
    shared.require(abs(packets[TEMPORAL_FRAMES.index(ANCHOR_FRAME)]["phase"] -
                       PHASE_SECONDS) <= 1.0e-9,
                   "M31 temporal phase anchor drifted")
    shared.require(
        tuple(len(row["interleaved_m29_m30"]) for row in packets) ==
        EXPECTED_INTERLEAVED_M29_M30_COUNTS,
        "M31/M29/M30 retained owner chronology drifted")
    shared.require(
        tuple(row["split_order_compatible"] for row in packets) ==
        EXPECTED_SPLIT_ORDER_COMPATIBLE,
        "M31 split owner chronology drifted")
    return packets


def texture_payload(frame_root: Path, metadata: dict[str, Any],
                    draws: list[dict[str, Any]]) -> dict[str, Any]:
    object_ids: set[int] = set()
    for draw in draws:
        rows = [row for row in draw.get("resources", [])
                if int(row.get("stage", -1)) == 4 and
                int(row.get("slot", -1)) == 1]
        shared.require(len(rows) == 1, "M31 draw does not own one PS t1")
        object_ids.add(int(rows[0]["objectId"]))
    shared.require(len(object_ids) == 1,
                   "the two M31 peak draws do not share one main texture")
    object_id = next(iter(object_ids))
    selected = [row for row in metadata.get("selectedResourceRecords", [])
                if int(row.get("objectId", 0)) == object_id and
                int(row.get("stage", -1)) == 4 and
                int(row.get("slot", -1)) == 1]
    shared.require(len(selected) == 1 and selected[0].get("completed") is True,
                   "M31 PS t1 payload is not uniquely complete")
    row = selected[0]
    shared.require((int(row.get("format", -1)),
                    int(row.get("viewFormat", -1)),
                    int(row.get("width", 0)), int(row.get("height", 0))) ==
                   (99, 99, 256, 256), "M31 PS t1 descriptor drifted")
    blob = (frame_root / "resources.bin").read_bytes()
    start = int(row["blobOffset"])
    size = int(row["blobBytes"])
    payload = blob[start:start + size]
    shared.require(len(payload) == 65536, "M31 PS t1 byte count drifted")
    return {"payload": payload, "sha256": shared.sha256_bytes(payload)}


def collect(capture: Path) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    shared.require(capture.name == EXPECTED_SESSION,
                   "M31 source session drifted")
    frame_root = capture / "graphics/frames" / str(FRAME)
    metadata_path = frame_root / "metadata.json"
    metadata = shared.load_json(metadata_path)
    draws = [row for row in metadata.get("drawRecords", [])
             if isinstance(row, dict) and is_m31(row)]
    shared.require(len(draws) == 2,
                   f"M31 peak draw count drifted: {len(draws)}")
    secondary = shared.collect_secondary_stream(frame_root, metadata)
    packets: list[dict[str, Any]] = []
    for draw in draws:
        packets.append({
            "drawIndex": metadata["drawRecords"].index(draw),
            "constants": shared.collect_constants(draw),
            "geometry": shared.collect_geometry(frame_root, metadata, draw),
            "secondary": secondary,
        })
    texture = texture_payload(frame_root, metadata, draws)
    return packets, texture, shared.sha256_bytes(metadata_path.read_bytes())


def render_cpp(packets: list[dict[str, Any]], texture: dict[str, Any],
               metadata_sha256: str) -> str:
    arrays = [shared.cpp_array("g_EndfieldM31PeakTextureT1", texture["payload"])]
    descriptors: list[str] = []
    for index, packet in enumerate(packets):
        prefix = f"g_EndfieldM31PeakP{index}"
        arrays.extend((
            shared.cpp_array(prefix + "Vertices", packet["geometry"]["vertices"]),
            shared.cpp_array(prefix + "Indices", packet["geometry"]["indices"]),
            shared.cpp_array(prefix + "Secondary", packet["secondary"]),
        ))
        for stage, label in ((0, "VS"), (4, "PS")):
            for slot, payload in enumerate(packet["constants"][stage]):
                arrays.append(shared.cpp_array(
                    f"{prefix}{label}CB{slot}", payload))
        descriptors.append(
            f"    {{{packet['drawIndex']}u, {prefix}Vertices, "
            f"{prefix}VerticesSize, {prefix}Indices, {prefix}IndicesSize, "
            f"{packet['geometry']['index_count']}u, {prefix}Secondary, "
            f"{prefix}SecondarySize, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
            f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
    return (
        "// Generated by tools/build_endminf_m31_peak_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM31PeakPayloadPrepared = true;\n"
        "inline constexpr bool g_EndfieldM31PeakDepthContractReady = true;\n"
        f'inline constexpr char g_EndfieldM31PeakSession[] = "{EXPECTED_SESSION}";\n'
        f'inline constexpr char g_EndfieldM31PeakMetadataSha256[] = "{metadata_sha256}";\n'
        f"inline constexpr std::uint32_t g_EndfieldM31PeakFrame = {FRAME}u;\n"
        f"inline constexpr float g_EndfieldM31PeakPhaseSeconds = {PHASE_SECONDS:.6f}f;\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakVertexStride = 36u;\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakVSDeclaredFloat4Counts[] = {2, 82, 104, 4094, 10};\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakPSDeclaredFloat4Counts[] = {28, 105, 4085, 22};\n\n" +
        "\n".join(arrays) + "\n"
        "struct EndfieldM31PeakPacketPayload { std::uint32_t drawIndex; "
        "const std::uint8_t* vertices; std::size_t vertexBytes; "
        "const std::uint8_t* indices; std::size_t indexBytes; "
        "std::uint32_t indexCount; const std::uint8_t* secondary; "
        "std::size_t secondaryBytes; const std::uint8_t* vs[5]; "
        "std::size_t vsBytes[5]; const std::uint8_t* ps[4]; "
        "std::size_t psBytes[4]; };\n"
        "inline constexpr EndfieldM31PeakPacketPayload g_EndfieldM31PeakPackets[] = {\n" +
        "\n".join(descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakPacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM31PeakPackets) / "
        "sizeof(g_EndfieldM31PeakPackets[0]));\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakSplitEventCount = 2u;\n"
        f'inline constexpr char g_EndfieldM31PeakTextureT1Sha256[] = "{texture["sha256"]}";\n'
    )


def render_cs(temporal: list[dict[str, Any]], texture: dict[str, Any],
              metadata_sha256: str) -> str:
    frames = ", ".join(str(row["frame"]) for row in temporal)
    phases = ", ".join(f'{row["phase"]:.6f}f' for row in temporal)
    draw_counts = ", ".join(str(row["draw_count"]) for row in temporal)
    first_draw_ordinals = ", ".join(
        str(row["draw_indices"][0]) for row in temporal)
    last_draw_ordinals = ", ".join(
        str(row["draw_indices"][-1]) for row in temporal)
    native_order_compatible = ", ".join(
        "true" if row["native_order_compatible"] else "false"
        for row in temporal)
    split_order_compatible = ", ".join(
        "true" if row["split_order_compatible"] else "false"
        for row in temporal)
    interleaved_m29_m30_counts = ", ".join(
        str(len(row["interleaved_m29_m30"])) for row in temporal)
    hashes = ", ".join(f'"{row["metadata_sha256"]}"' for row in temporal)
    return f'''// Generated by tools/build_endminf_m31_peak_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM31PeakCaptureData
    {{
        internal const string TemporalSourceSession = "{EXPECTED_TEMPORAL_SESSION}";
        internal const string PayloadSourceSession = "{EXPECTED_SESSION}";
        internal const int PayloadSourceFrame = {FRAME};
        internal const int AnchorFrame = {ANCHOR_FRAME};
        internal const float AnchorPhaseSeconds = {PHASE_SECONDS:.6f}f;
        internal const int QpcFrequency = {QPC_FREQUENCY};
        internal const int PacketCount = {len(temporal)};
        internal const int NativePayloadDrawCount = 2;
        internal const bool PayloadPrepared = true;
        internal const bool DepthContractReady = true;
        internal const string PayloadMetadataSha256 = "{metadata_sha256}";
        internal const string TextureT1Sha256 = "{texture['sha256']}";
        internal static readonly int[] SourceFrames = {{ {frames} }};
        internal static readonly float[] PhaseSeconds = {{ {phases} }};
        internal static readonly int[] DrawCounts = {{ {draw_counts} }};
        internal static readonly int[] FirstDrawOrdinals = {{ {first_draw_ordinals} }};
        internal static readonly int[] LastDrawOrdinals = {{ {last_draw_ordinals} }};
        internal static readonly bool[] NativeOrderCompatible = {{ {native_order_compatible} }};
        internal static readonly bool[] SplitOrderCompatible = {{ {split_order_compatible} }};
        internal static readonly int[] InterleavedM29M30Counts = {{ {interleaved_m29_m30_counts} }};
        internal static readonly string[] TemporalMetadataSha256 = {{ {hashes} }};
    }}
}}
'''


def build(temporal_capture: Path, payload_capture: Path, cs_output: Path,
          cpp_output: Path) -> None:
    temporal = collect_temporal(temporal_capture)
    packets, texture, metadata_sha256 = collect(payload_capture)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(render_cs(temporal, texture, metadata_sha256),
                         encoding="utf-8", newline="\n")
    cpp_output.write_text(render_cpp(packets, texture, metadata_sha256),
                          encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temporal-capture", type=Path, default=TEMPORAL_CAPTURE)
    parser.add_argument("--payload-capture", type=Path, default=PAYLOAD_CAPTURE)
    parser.add_argument("--cs-output", type=Path, default=CS_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.temporal_capture.resolve(), args.payload_capture.resolve(),
          args.cs_output.resolve(),
          args.cpp_output.resolve())
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
