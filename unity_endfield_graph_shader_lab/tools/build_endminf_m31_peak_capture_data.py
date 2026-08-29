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
CAPTURE = TEMPORAL_CAPTURE
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
M18_VS = 0x7D1953E7B7D5310F
M18_PS = 0x601242F701CB4380
EXPECTED_INTERLEAVED_M29_M30_COUNTS = (2, 2, 2, 2, 2, 2, 2, 0, 0)
SCHEDULE_UNSUPPORTED = 0
SCHEDULE_QUEUE3000_INTERVAL_2 = 1
SCHEDULE_QUEUE3000_THEN_POST_M18_3 = 2
EXPECTED_SCHEDULE_PROFILES = (
    SCHEDULE_QUEUE3000_INTERVAL_2,) * 7 + (
    SCHEDULE_QUEUE3000_THEN_POST_M18_3, SCHEDULE_UNSUPPORTED)
EXPECTED_CHRONOLOGY_VALIDATED = (
    True, True, True, True, True, True, True, False, False)
EXPECTED_THIRD_EVENT_AFTER_M18 = (
    False, False, False, False, False, False, False, True, False)


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


def is_m18_third_event_boundary(draw: dict[str, Any]) -> bool:
    """Identify the exact frame-1977 M18 draw immediately before M31 #3."""
    pair = {int(row.get("stage", -1)): int(row.get("identityHash", 0))
            for row in draw.get("shaders", []) if isinstance(row, dict)}
    return (
        pair.get(0) == M18_VS and pair.get(4) == M18_PS and
        int(draw.get("count", -1)) == 900 and
        int(draw.get("start", -1)) == 3642 and
        int(draw.get("baseVertex", -1)) == 1615 and
        int(draw.get("instanceCount", -1)) == 1 and
        int(draw.get("startInstance", -1)) == 0 and
        int(draw.get("topology", -1)) == 4)


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


def collect_temporal(
        capture: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
    shared_texture: dict[str, Any] | None = None
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
        draw_indices: list[int] = []
        draw_records: list[dict[str, Any]] = []
        secondary = shared.collect_secondary_stream(frame_root, metadata)
        payloads: list[dict[str, Any]] = []
        for draw_index, start, base_vertex in expected:
            rows = metadata.get("drawRecords", [])
            shared.require(0 <= draw_index < len(rows),
                           f"M31 frame {frame} draw {draw_index} is absent")
            draw = rows[draw_index]
            shared.require(isinstance(draw, dict),
                           f"M31 frame {frame} draw {draw_index} is malformed")
            validate_temporal_draw(draw, frame, draw_index, start, base_vertex)
            validate_temporal_resources(frame_root, metadata, draw)
            draw_indices.append(draw_index)
            draw_records.append(draw)
            payloads.append({
                "drawIndex": draw_index,
                "constants": shared.collect_constants(draw),
                "geometry": shared.collect_geometry(frame_root, metadata, draw),
                "secondary": secondary,
            })
        all_m31 = [index for index, row in enumerate(metadata.get("drawRecords", []))
                   if isinstance(row, dict) and is_m31(row)]
        shared.require(all_m31 == draw_indices,
                       f"M31 frame {frame} owner draw set drifted")
        frame_texture = texture_payload(frame_root, metadata, draw_records)
        if shared_texture is None:
            shared_texture = frame_texture
        shared.require(
            frame_texture["sha256"] == EXPECTED_TEXTURE_SHA256 and
            frame_texture["payload"] == shared_texture["payload"],
            f"M31 frame {frame} shared PS t1 payload drifted")
        qpc = int(metadata.get("timestampQpc", 0))
        interleaved_m29_m30 = [
            index for index in range(draw_indices[0] + 1, draw_indices[-1])
            if is_m29_or_m30(metadata["drawRecords"][index])
        ]
        third_event_after_m18 = False
        if len(draw_indices) == 3:
            third_draw = draw_indices[2]
            shared.require(
                frame == ANCHOR_FRAME and third_draw > 0 and
                is_m18_third_event_boundary(
                    metadata["drawRecords"][third_draw - 1]),
                f"M31 frame {frame} third-event M18 boundary drifted")
            third_event_after_m18 = True
        packets.append({
            "frame": frame,
            "phase": PHASE_SECONDS + (qpc - anchor_qpc) / QPC_FREQUENCY,
            "draw_indices": draw_indices,
            "draw_count": len(draw_indices),
            "payloads": payloads,
            # Contiguous order remains diagnostic. The native split route has
            # exactly two event slots around the recovered M29/M30 interval,
            # so only the independently proven two-draw/two-owner-gap shape
            # is admissible without changing blend/depth chronology.
            "native_order_compatible": all(
                right == left + 1
                for left, right in zip(draw_indices, draw_indices[1:])),
            "interleaved_m29_m30": interleaved_m29_m30,
            "schedule_profile": (
                SCHEDULE_QUEUE3000_INTERVAL_2
                if len(draw_indices) == 2 and len(interleaved_m29_m30) == 2
                else SCHEDULE_QUEUE3000_THEN_POST_M18_3
                if len(draw_indices) == 3 and third_event_after_m18
                else SCHEDULE_UNSUPPORTED),
            # The seven two-event packets have their complete retained owner
            # interval. Packet 7's three owner draws are retained, but the old
            # capture does not prove which SceneColor version each event saw.
            "chronology_validated": (
                len(draw_indices) == 2 and len(interleaved_m29_m30) == 2),
            # This is an observed owner-order fact only. It does not establish
            # that the three callbacks see the required SceneColor versions;
            # the corrected chronology observer owns that separate gate.
            "third_event_after_m18": third_event_after_m18,
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
        tuple(row["schedule_profile"] for row in packets) ==
        EXPECTED_SCHEDULE_PROFILES,
        "M31 schedule profile chronology drifted")
    shared.require(
        tuple(row["chronology_validated"] for row in packets) ==
        EXPECTED_CHRONOLOGY_VALIDATED,
        "M31 chronology validation gate drifted")
    shared.require(
        tuple(row["third_event_after_m18"] for row in packets) ==
        EXPECTED_THIRD_EVENT_AFTER_M18,
        "M31 third-event M18 placement drifted")
    shared.require(shared_texture is not None,
                   "M31 temporal capture has no shared PS t1 payload")
    return packets, shared_texture


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
                   "the M31 packet draws do not share one main texture")
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


def render_cpp(temporal: list[dict[str, Any]], texture: dict[str, Any]) -> str:
    arrays = [shared.cpp_array("g_EndfieldM31PeakTextureT1", texture["payload"])]
    draw_descriptors: list[str] = []
    temporal_descriptors: list[str] = []
    first_draw_payload = 0
    for temporal_index, packet in enumerate(temporal):
        for draw_index, payload in enumerate(packet["payloads"]):
            prefix = f"g_EndfieldM31PeakT{temporal_index}D{draw_index}"
            arrays.extend((
                shared.cpp_array(
                    prefix + "Vertices", payload["geometry"]["vertices"]),
                shared.cpp_array(
                    prefix + "Indices", payload["geometry"]["indices"]),
                shared.cpp_array(prefix + "Secondary", payload["secondary"]),
            ))
            for stage, label in ((0, "VS"), (4, "PS")):
                for slot, constant in enumerate(payload["constants"][stage]):
                    arrays.append(shared.cpp_array(
                        f"{prefix}{label}CB{slot}", constant))
            draw_descriptors.append(
                f"    {{{payload['drawIndex']}u, {prefix}Vertices, "
                f"{prefix}VerticesSize, {prefix}Indices, {prefix}IndicesSize, "
                f"{payload['geometry']['index_count']}u, {prefix}Secondary, "
                f"{prefix}SecondarySize, "
                f"{{{', '.join(prefix + 'VSCB' + str(i) for i in range(5))}}}, "
                f"{{{', '.join(prefix + 'VSCB' + str(i) + 'Size' for i in range(5))}}}, "
                f"{{{', '.join(prefix + 'PSCB' + str(i) for i in range(4))}}}, "
                f"{{{', '.join(prefix + 'PSCB' + str(i) + 'Size' for i in range(4))}}}}},")
        validated = "true" if packet["chronology_validated"] else "false"
        temporal_descriptors.append(
            f"    {{{packet['frame']}u, {packet['phase']:.6f}f, "
            f"{first_draw_payload}u, {packet['draw_count']}u, "
            f"{packet['schedule_profile']}u, {validated}}},")
        first_draw_payload += packet["draw_count"]
    return (
        "// Generated by tools/build_endminf_m31_peak_capture_data.py. Do not edit.\n"
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n\n"
        "inline constexpr bool g_EndfieldM31PeakPayloadPrepared = true;\n"
        "inline constexpr bool g_EndfieldM31PeakDepthContractReady = true;\n"
        f'inline constexpr char g_EndfieldM31PeakSession[] = "{EXPECTED_TEMPORAL_SESSION}";\n'
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
        "inline constexpr EndfieldM31PeakPacketPayload g_EndfieldM31PeakDrawPayloads[] = {\n" +
        "\n".join(draw_descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakDrawPayloadCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM31PeakDrawPayloads) / "
        "sizeof(g_EndfieldM31PeakDrawPayloads[0]));\n"
        "struct EndfieldM31PeakTemporalPacket { std::uint32_t frame; "
        "float phaseSeconds; std::uint32_t firstDrawPayload; "
        "std::uint32_t drawCount; std::uint32_t scheduleProfile; "
        "bool chronologyValidated; };\n"
        "inline constexpr EndfieldM31PeakTemporalPacket g_EndfieldM31PeakTemporalPackets[] = {\n" +
        "\n".join(temporal_descriptors) + "\n};\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakTemporalPacketCount = "
        "static_cast<std::uint32_t>(sizeof(g_EndfieldM31PeakTemporalPackets) / "
        "sizeof(g_EndfieldM31PeakTemporalPackets[0]));\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakScheduleUnsupported = 0u;\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakScheduleQueue3000Interval2 = 1u;\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakScheduleQueue3000ThenPostM18_3 = 2u;\n"
        "inline constexpr std::uint32_t g_EndfieldM31PeakMaxEventCount = 3u;\n"
        f'inline constexpr char g_EndfieldM31PeakTextureT1Sha256[] = "{texture["sha256"]}";\n'
    )


def render_cs(temporal: list[dict[str, Any]], texture: dict[str, Any]) -> str:
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
    schedule_profiles = ", ".join(
        str(row["schedule_profile"])
        for row in temporal)
    chronology_validated = ", ".join(
        "true" if row["chronology_validated"] else "false"
        for row in temporal)
    interleaved_m29_m30_counts = ", ".join(
        str(len(row["interleaved_m29_m30"])) for row in temporal)
    third_event_after_m18 = ", ".join(
        "true" if row["third_event_after_m18"] else "false"
        for row in temporal)
    hashes = ", ".join(f'"{row["metadata_sha256"]}"' for row in temporal)
    return f'''// Generated by tools/build_endminf_m31_peak_capture_data.py. Do not edit.
namespace EndfieldGraphShaderLab
{{
    internal static class EndfieldRecoveredM31PeakCaptureData
    {{
        internal const string TemporalSourceSession = "{EXPECTED_TEMPORAL_SESSION}";
        internal const string PayloadSourceSession = "{EXPECTED_TEMPORAL_SESSION}";
        internal const int AnchorFrame = {ANCHOR_FRAME};
        internal const float AnchorPhaseSeconds = {PHASE_SECONDS:.6f}f;
        internal const int QpcFrequency = {QPC_FREQUENCY};
        internal const int PacketCount = {len(temporal)};
        internal const int ScheduleUnsupported = {SCHEDULE_UNSUPPORTED};
        internal const int ScheduleQueue3000Interval2 = {SCHEDULE_QUEUE3000_INTERVAL_2};
        internal const int ScheduleQueue3000ThenPostM18_3 = {SCHEDULE_QUEUE3000_THEN_POST_M18_3};
        internal const int MaxEventCount = 3;
        internal const bool PayloadPrepared = true;
        internal const bool DepthContractReady = true;
        // The retained frame metadata proves the owner boundary below, but
        // not the SceneColor version seen by each event. A corrected observer
        // capture must explicitly replace this fail-closed gate.
        internal const string TextureT1Sha256 = "{texture['sha256']}";
        internal static readonly int[] SourceFrames = {{ {frames} }};
        internal static readonly float[] PhaseSeconds = {{ {phases} }};
        internal static readonly int[] DrawCounts = {{ {draw_counts} }};
        internal static readonly int[] FirstDrawOrdinals = {{ {first_draw_ordinals} }};
        internal static readonly int[] LastDrawOrdinals = {{ {last_draw_ordinals} }};
        internal static readonly bool[] NativeOrderCompatible = {{ {native_order_compatible} }};
        internal static readonly int[] ScheduleProfiles = {{ {schedule_profiles} }};
        internal static readonly bool[] ChronologyValidated = {{ {chronology_validated} }};
        internal static readonly int[] InterleavedM29M30Counts = {{ {interleaved_m29_m30_counts} }};
        internal static readonly bool[] ThirdEventAfterM18Observed = {{ {third_event_after_m18} }};
        internal static readonly string[] TemporalMetadataSha256 = {{ {hashes} }};
    }}
}}
'''


def build(temporal_capture: Path, cs_output: Path, cpp_output: Path) -> None:
    temporal, texture = collect_temporal(temporal_capture)
    cs_output.parent.mkdir(parents=True, exist_ok=True)
    cpp_output.parent.mkdir(parents=True, exist_ok=True)
    cs_output.write_text(render_cs(temporal, texture),
                         encoding="utf-8", newline="\n")
    cpp_output.write_text(render_cpp(temporal, texture),
                          encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temporal-capture", type=Path, default=TEMPORAL_CAPTURE)
    parser.add_argument("--cs-output", type=Path, default=CS_OUTPUT)
    parser.add_argument("--cpp-output", type=Path, default=CPP_OUTPUT)
    args = parser.parse_args()
    build(args.temporal_capture.resolve(), args.cs_output.resolve(),
          args.cpp_output.resolve())
    print(args.cs_output)
    print(args.cpp_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
