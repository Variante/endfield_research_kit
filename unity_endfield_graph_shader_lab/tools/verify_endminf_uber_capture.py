#!/usr/bin/env python3
"""Fail closed unless a capture closes Endminf's exact late Uber pulse ABI."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_uber_capture_latest.json"
)
PIXEL_IDENTITY = 0x86A732CEF7EEDB15
VERTEX_IDENTITY = 0xA8C084C37EBA0ECC
VERTEX_SHA256 = (
    "a8c084c37eba0ecc78f26d984a2b8c658f8d743002048c84431807d9dee0ce4e"
)
PIXEL_SHA256 = (
    "86a732cef7eedb150cbcafb35a994c1e3f7b1ef837dc618131a95e9dfe030c97"
)
NORMAL_PIXEL_IDENTITY = 0xDE96A55F118305EA
NORMAL_PIXEL_SHA256 = (
    "de96a55f118305ea6145db7aae1789640b1f5b3355cfae87b342e05adaee80dd"
)
VARIANTS = {
    "normal": {
        "identity": NORMAL_PIXEL_IDENTITY,
        "sha256": NORMAL_PIXEL_SHA256,
        "b1Constants": 12,
        "keywords": ["BLOOM", "VIGNETTE"],
    },
    "peak": {
        "identity": PIXEL_IDENTITY,
        "sha256": PIXEL_SHA256,
        "b1Constants": 26,
        "keywords": ["BLOOM", "RADIAL_BLUR", "VIGNETTE"],
    },
}
MINIMUM_RESOURCE_BUDGET = 128 * 1024 * 1024
EXACT_CHARINFO_LUT_SHA256 = (
    "717c1d483662c00abe55e1c56a9d024f45e5c84c430ed9dd2854cb386f372482"
)


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def shader_identity(resolver: dict[str, Any], stage: int) -> int | None:
    rows = [row for row in resolver.get("shaders", [])
            if isinstance(row, dict) and int(row.get("stage", -1)) == stage]
    require(len(rows) <= 1, f"fullscreen stage {stage} shader is ambiguous")
    return int(rows[0]["identityHash"]) if rows else None


def constant_range(resolver: dict[str, Any], key: str, stage: str,
                   slot: int) -> dict[str, Any]:
    rows = [row for row in resolver.get(key, [])
            if isinstance(row, dict) and int(row.get("slot", -1)) == slot]
    require(len(rows) == 1,
            f"exact Uber {stage} b{slot} range is not unique")
    row = rows[0]
    require(row.get("rangeValid") is True,
            f"exact Uber {stage} b{slot} range is invalid")
    require(int(row.get("bufferId", 0)) != 0,
            f"exact Uber {stage} b{slot} has no buffer identity")
    return row


def selected_payload(metadata: dict[str, Any], object_id: int,
                     resource_blob: bytes) -> bytes:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict)
            and int(row.get("objectId", 0)) == object_id
            and int(row.get("captureKind", -1)) == 2]
    require(len(rows) == 1,
            f"constant buffer {object_id} selected payload is not unique")
    row = rows[0]
    require(row.get("completed") is True and int(row.get("failure", -1)) == 0,
            f"constant buffer {object_id} payload is incomplete")
    offset = int(row.get("blobOffset", -1))
    size = int(row.get("blobBytes", 0))
    require(offset >= 0 and size > 0 and offset + size <= len(resource_blob),
            f"constant buffer {object_id} payload bounds are invalid")
    return resource_blob[offset:offset + size]


def texture_binding(resolver: dict[str, Any], slot: int) -> int:
    chain = resolver.get("resourceChain")
    require(isinstance(chain, dict), "exact Uber resource chain is absent")
    rows = [row for row in chain.get("psInputs", [])
            if isinstance(row, dict) and int(row.get("slot", -1)) == slot]
    require(len(rows) == 1,
            f"exact Uber PS t{slot} binding is not unique")
    object_id = int(rows[0].get("objectId", 0))
    require(object_id != 0, f"exact Uber PS t{slot} has no texture identity")
    return object_id


def selected_texture(metadata: dict[str, Any], object_id: int,
                     resource_blob: bytes, label: str, width: int,
                     height: int, format_value: int,
                     bytes_per_pixel: int) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if isinstance(row, dict)
            and int(row.get("objectId", 0)) == object_id
            and int(row.get("captureKind", -1)) == 3]
    require(len(rows) == 1,
            f"exact Uber {label} selected texture payload is not unique")
    row = rows[0]
    require(row.get("completed") is True and int(row.get("failure", -1)) == 0,
            f"exact Uber {label} texture payload is incomplete")
    require(int(row.get("width", 0)) == width and
            int(row.get("height", 0)) == height and
            int(row.get("format", -1)) == format_value and
            int(row.get("viewFormat", -1)) == format_value,
            f"exact Uber {label} descriptor drifted: expected "
            f"{width}x{height} format {format_value}, got "
            f"{row.get('width')}x{row.get('height')} "
            f"format {row.get('format')}/{row.get('viewFormat')}")
    expected_bytes = width * height * bytes_per_pixel
    require(int(row.get("requestedBytes", 0)) == expected_bytes and
            int(row.get("blobBytes", 0)) == expected_bytes,
            f"exact Uber {label} byte count drifted: expected "
            f"{expected_bytes}, got requested={row.get('requestedBytes')} "
            f"blob={row.get('blobBytes')}")
    offset = int(row.get("blobOffset", -1))
    require(offset >= 0 and offset + expected_bytes <= len(resource_blob),
            f"exact Uber {label} payload bounds are invalid")
    payload = resource_blob[offset:offset + expected_bytes]
    return {
        "objectId": object_id,
        "width": width,
        "height": height,
        "format": format_value,
        "byteLength": expected_bytes,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def vector(payload: bytes, first_constant: int,
           index: int) -> tuple[float, float, float, float]:
    offset = (first_constant + index) * 16
    require(offset >= 0 and offset + 16 <= len(payload),
            f"constant c{index} is outside the captured buffer")
    return struct.unpack_from("<4f", payload, offset)


def declared_vectors(payload: bytes, first_constant: int,
                     count: int) -> list[list[float]]:
    require(count > 0, "declared constant range is empty")
    return [list(vector(payload, first_constant, index))
            for index in range(count)]


def range_sha256(values: list[list[float]]) -> str:
    flattened = [lane for value in values for lane in value]
    return hashlib.sha256(
        struct.pack(f"<{len(flattened)}f", *flattened)).hexdigest()


def range_hex(values: list[list[float]]) -> str:
    flattened = [lane for value in values for lane in value]
    return struct.pack(f"<{len(flattened)}f", *flattened).hex()


def finite(values: tuple[float, ...]) -> bool:
    return all(math.isfinite(value) for value in values)


def pipeline_state(resolver: dict[str, Any], frame: int) -> dict[str, Any]:
    state = resolver.get("pipelineState")
    require(isinstance(state, dict) and state.get("valid") is True,
            f"frame {frame} exact Uber draw-bound pipeline state is absent")
    target = state.get("target")
    depth_target = state.get("depthTarget")
    viewport = state.get("viewport")
    scissor = state.get("scissor")
    sampler = state.get("sampler")
    blend = state.get("blend")
    depth = state.get("depthStencil")
    raster = state.get("rasterizer")
    require(all(isinstance(value, dict) for value in
                (target, depth_target, viewport, scissor, sampler, blend,
                 depth, raster)),
            f"frame {frame} exact Uber pipeline state is incomplete")
    assert isinstance(target, dict) and isinstance(viewport, dict)
    assert isinstance(depth_target, dict)
    assert isinstance(scissor, dict) and isinstance(sampler, dict)
    assert isinstance(blend, dict) and isinstance(depth, dict)
    assert isinstance(raster, dict)
    width = int(target.get("width", 0))
    height = int(target.get("height", 0))
    require(width > 0 and height > 0,
            f"frame {frame} exact Uber target dimensions are invalid")
    require(int(target.get("textureFormat", -1)) == 28 and
            int(target.get("viewFormat", -1)) == 28 and
            int(target.get("sampleCount", 0)) == 1 and
            int(target.get("renderTargetCount", 0)) == 1 and
            target.get("depthBound") is True,
            f"frame {frame} exact Uber output target contract drifted")
    require(int(depth_target.get("width", 0)) == width and
            int(depth_target.get("height", 0)) == height and
            int(depth_target.get("textureFormat", -1)) == 44 and
            int(depth_target.get("viewFormat", -1)) == 45 and
            int(depth_target.get("sampleCount", 0)) == 1,
            f"frame {frame} exact Uber D24S8 attachment contract drifted")
    require(int(viewport.get("count", 0)) == 1 and
            abs(float(viewport.get("x", math.nan))) <= 1e-6 and
            abs(float(viewport.get("y", math.nan))) <= 1e-6 and
            abs(float(viewport.get("width", math.nan)) - width) <= 1e-3 and
            abs(float(viewport.get("height", math.nan)) - height) <= 1e-3 and
            abs(float(viewport.get("minDepth", math.nan))) <= 1e-6 and
            abs(float(viewport.get("maxDepth", math.nan)) - 1.0) <= 1e-6,
            f"frame {frame} exact Uber viewport contract drifted")
    require(int(scissor.get("count", 0)) == 1,
            f"frame {frame} exact Uber scissor state is absent")
    require(int(sampler.get("filter", -1)) == 21 and
            int(sampler.get("addressU", -1)) == 3 and
            int(sampler.get("addressV", -1)) == 3 and
            int(sampler.get("addressW", -1)) == 3,
            f"frame {frame} exact Uber sampler contract drifted")
    require(blend.get("enabled") is False and
            int(blend.get("writeMask", 0)) == 15,
            f"frame {frame} exact Uber blend contract drifted")
    require(depth.get("depthEnabled") is False and
            depth.get("stencilEnabled") is False,
            f"frame {frame} exact Uber depth/stencil contract drifted")
    require(int(raster.get("fillMode", -1)) == 3 and
            int(raster.get("cullMode", -1)) == 1 and
            raster.get("depthClipEnabled") is True,
            f"frame {frame} exact Uber rasterizer contract drifted")
    return state


def inspect_resolver(frame: int, resolver_index: int,
                     resolver: dict[str, Any], metadata: dict[str, Any],
                     resource_blob: bytes,
                     require_draw_pipeline: bool = True,
                     variant: str = "peak") -> dict[str, Any]:
    require(variant in VARIANTS, f"unknown exact Uber variant: {variant}")
    variant_contract = VARIANTS[variant]
    if require_draw_pipeline:
        require(resolver.get("priorityEndminfUber") is True,
                f"frame {frame} resolver {resolver_index} lost Uber priority tagging")
    require(shader_identity(resolver, 0) == VERTEX_IDENTITY,
            f"frame {frame} resolver {resolver_index} has the wrong Uber VS")
    require(shader_identity(resolver, 4) == variant_contract["identity"],
            f"frame {frame} resolver {resolver_index} has the wrong "
            f"{variant} Uber PS")
    vs_b0 = constant_range(
        resolver, "vsConstantBuffers", "VS", 0)
    b0 = constant_range(resolver, "psConstantBuffers", "PS", 0)
    b1 = constant_range(resolver, "psConstantBuffers", "PS", 1)
    require(int(vs_b0.get("numConstants", 0)) >= 1,
            f"frame {frame} exact Uber VS b0 does not expose c0")
    require(int(b0.get("numConstants", 0)) >= 28,
            f"frame {frame} exact Uber PS b0 does not expose c27")
    b1_constants = int(variant_contract["b1Constants"])
    require(int(b1.get("numConstants", 0)) >= b1_constants,
            f"frame {frame} {variant} Uber PS b1 does not expose "
            f"{b1_constants} constants")
    vs_b0_payload = selected_payload(
        metadata, int(vs_b0["bufferId"]), resource_blob)
    b0_payload = (vs_b0_payload
                  if int(b0["bufferId"]) == int(vs_b0["bufferId"])
                  else selected_payload(
                      metadata, int(b0["bufferId"]), resource_blob))
    b1_payload = (b0_payload if int(b1["bufferId"]) == int(b0["bufferId"])
                  else selected_payload(
                      metadata, int(b1["bufferId"]), resource_blob))
    vertex_params = vector(
        vs_b0_payload, int(vs_b0["firstConstant"]), 0)
    exposure = vector(b0_payload, int(b0["firstConstant"]), 27)
    radial = (vector(b1_payload, int(b1["firstConstant"]), 0)
              if variant == "peak" else None)
    radial2 = (vector(b1_payload, int(b1["firstConstant"]), 25)
               if variant == "peak" else None)
    vs_b0_values = declared_vectors(
        vs_b0_payload, int(vs_b0["firstConstant"]), 1)
    b0_values = declared_vectors(
        b0_payload, int(b0["firstConstant"]), 28)
    b1_values = declared_vectors(
        b1_payload, int(b1["firstConstant"]), b1_constants)
    finite_values = tuple(
        lane for row in (vs_b0_values + b0_values + b1_values)
        for lane in row
    )
    require(finite(finite_values),
            f"frame {frame} exact Uber constants are non-finite")
    if variant == "peak":
        assert radial is not None and radial2 is not None
        require(0.0 <= radial[0] <= 1.0 and 0.0 <= radial[1] <= 1.0,
                f"frame {frame} exact Uber center is outside viewport space")
        require(radial[2] >= 0.0 and radial[3] > 0.0 and radial2[1] >= 0.0,
                f"frame {frame} exact Uber intensity/power lanes are invalid")
        require(radial2[0] in (3.0, 6.0),
                f"frame {frame} exact Uber mode is unexpected: {radial2[0]}")
        require(radial2[2] in (0.0, 1.0) and radial2[3] in (0.0, 1.0),
                f"frame {frame} exact Uber average-step flags are invalid")
    draw_pipeline_state = (
        pipeline_state(resolver, frame) if require_draw_pipeline else None
    )
    textures = None
    if draw_pipeline_state is not None:
        target = draw_pipeline_state["target"]
        target_width = int(target["width"])
        target_height = int(target["height"])
        textures = {
            "sourceT0": selected_texture(
                metadata, texture_binding(resolver, 0), resource_blob,
                "t0 source", target_width, target_height, 10, 8),
            "bloomT1": selected_texture(
                metadata, texture_binding(resolver, 1), resource_blob,
                "t1 bloom", (target_width + 1) // 2,
                (target_height + 1) // 2, 26, 4),
            "charInfoLutT2": selected_texture(
                metadata, texture_binding(resolver, 2), resource_blob,
                "t2 CharInfo LUT", 1024, 32, 10, 8),
        }
        require(
            textures["charInfoLutT2"]["sha256"] ==
            EXACT_CHARINFO_LUT_SHA256,
            "exact Uber t2 CharInfo LUT hash drifted",
        )
    result = {
        "frame": frame,
        "variant": variant,
        "resolverIndex": resolver_index,
        "fullscreenOrdinal": int(resolver.get("fullscreenOrdinal", -1)),
        "pixelIdentity": f"{int(variant_contract['identity']):016x}",
        "pixelSha256": variant_contract["sha256"],
        "compiledKeywords": variant_contract["keywords"],
        "vertexIdentity": f"{VERTEX_IDENTITY:016x}",
        "vertexSha256": VERTEX_SHA256,
        "vsB0": {
            "bufferId": int(vs_b0["bufferId"]),
            "firstConstant": int(vs_b0["firstConstant"]),
            "numConstants": int(vs_b0["numConstants"]),
            "c0": list(vertex_params),
            "declaredConstants": 1,
            "declaredRangeSha256": range_sha256(vs_b0_values),
            "declaredRangeHex": range_hex(vs_b0_values),
            "values": vs_b0_values,
        },
        "b0": {
            "bufferId": int(b0["bufferId"]),
            "firstConstant": int(b0["firstConstant"]),
            "numConstants": int(b0["numConstants"]),
            "c27ExposureWithMiscParams": list(exposure),
            "declaredConstants": 28,
            "declaredRangeSha256": range_sha256(b0_values),
            "declaredRangeHex": range_hex(b0_values),
            "values": b0_values,
        },
        "b1": {
            "bufferId": int(b1["bufferId"]),
            "firstConstant": int(b1["firstConstant"]),
            "numConstants": int(b1["numConstants"]),
            "declaredConstants": b1_constants,
            "declaredRangeSha256": range_sha256(b1_values),
            "declaredRangeHex": range_hex(b1_values),
            "values": b1_values,
        },
    }
    if radial is not None and radial2 is not None:
        result["b1"]["c0RadialBlurParams"] = list(radial)
        result["b1"]["c25RadialBlurParams2"] = list(radial2)
    if draw_pipeline_state is not None:
        result["pipelineState"] = draw_pipeline_state
        result["textures"] = textures
    return result


def build_report(capture: Path, constant_payload_only: bool = False,
                 frame_filter: int | None = None) -> dict[str, Any]:
    session_path = capture / "session.json"
    require(session_path.is_file(), f"session manifest is absent: {session_path}")
    session = json.loads(session_path.read_text(encoding="utf-8"))
    graphics_profile = session.get("graphicsProfile")
    require(
        graphics_profile in {"targeted", "full"},
        "capture graphics profile is unsupported: "
        f"expected targeted or full, got {graphics_profile!r}",
    )
    if not constant_payload_only:
        require(int(session.get("graphicsResourceBudgetBytes", 0)) >=
                MINIMUM_RESOURCE_BUDGET,
                "capture predates the 128-MiB exact resource policy")
    require(int(session.get("qpcFrequency", 0)) > 0,
            "capture has no recorded QPC frequency")

    frame_root = capture / "graphics/frames"
    paths = sorted(frame_root.glob("*/metadata.json"),
                   key=lambda path: int(path.parent.name))
    require(paths, "capture has no graphics metadata")
    packets = []
    for path in paths:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        frame = int(metadata.get("frame", path.parent.name))
        if frame_filter is not None and frame != frame_filter:
            continue
        resources_path = path.parent / "resources.bin"
        resource_blob = (resources_path.read_bytes()
                         if resources_path.is_file() else b"")
        for resolver_index, resolver in enumerate(
                metadata.get("fullscreenResolvers", [])):
            if not isinstance(resolver, dict):
                continue
            if shader_identity(resolver, 4) != PIXEL_IDENTITY:
                continue
            packets.append(inspect_resolver(
                frame, resolver_index, resolver, metadata, resource_blob,
                require_draw_pipeline=not constant_payload_only))
    require(packets,
            "capture contains no exact Endminf combined Uber pulse resolver")
    return {
        "schema": "endfield.endminf-uber-capture.v2",
        "status": (
            "validated_exact_uber_constant_payload_only"
            if constant_payload_only
            else "validated_exact_live_uber_binding"
        ),
        "capture": str(capture.resolve()),
        "graphicsProfile": graphics_profile,
        "frameCount": len(paths),
        "resourceBudgetBytes": int(session["graphicsResourceBudgetBytes"]),
        "qpcFrequency": int(session["qpcFrequency"]),
        "packetCount": len(packets),
        "compiledKeywords": ["BLOOM", "RADIAL_BLUR", "VIGNETTE"],
        "pipelineEvidenceBoundary": (
            "draw-bound pipeline state retained"
            if not constant_payload_only
            else "constant ranges only; active shader predates priority tagging"
        ),
        "packets": packets,
    }


def archived_shader(capture: Path, sha256: str, stage: int,
                    expected_size: int) -> dict[str, Any]:
    path = capture / "graphics/shaders" / f"{sha256}-s{stage}.dxbc"
    require(path.is_file(), f"exact Uber archived shader is absent: {path}")
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    require(len(payload) == expected_size and actual == sha256,
            f"exact Uber archived shader drifted: stage={stage} "
            f"size={len(payload)}/{expected_size} sha256={actual}/{sha256}")
    return {
        "stage": stage,
        "path": str(path.relative_to(capture)).replace("\\", "/"),
        "byteLength": len(payload),
        "sha256": actual,
    }


def packet_lane_bits(packet: dict[str, Any], buffer_name: str,
                     register: int, lane: int) -> str:
    values = packet[buffer_name]["values"]
    require(register < len(values) and lane < len(values[register]),
            f"frame {packet['frame']} {buffer_name}.c{register}."
            f"{'xyzw'[lane]} is outside the retained range")
    return struct.pack("<f", float(values[register][lane])).hex()


def build_sequence_report(capture: Path) -> dict[str, Any]:
    session_path = capture / "session.json"
    summary_path = capture / "graphics/summary.json"
    require(session_path.is_file(), f"session manifest is absent: {session_path}")
    require(summary_path.is_file(),
            f"graphics completion summary is absent: {summary_path}")
    session = json.loads(session_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    require(session.get("graphicsProfile") == "full",
            "exact Uber sequence requires graphicsProfile=full")
    require(int(session.get("graphicsResourceBudgetBytes", 0)) >=
            MINIMUM_RESOURCE_BUDGET,
            "capture predates the 128-MiB exact resource policy")
    require(summary.get("complete") is True,
            "graphics summary is incomplete")
    require(summary.get("cadenceValid") is True,
            "graphics cadence is invalid")
    require(summary.get("deferredFailed") is False,
            "deferred readback reported failure")
    require(summary.get("shaderBytecodeArchiveComplete") is True,
            "shader bytecode archive is incomplete")
    require(int(summary.get("deferredStagedSlots", -1)) ==
            int(summary.get("deferredPublishedSlots", -2)),
            "staged/published deferred slot counts differ")

    frame_root = capture / "graphics/frames"
    paths = sorted(frame_root.glob("*/metadata.json"),
                   key=lambda path: int(path.parent.name))
    require(paths, "capture has no graphics metadata")
    require(int(summary.get("sequenceFrames", 0)) == len(paths),
            f"graphics sequence/frame-directory count drifted: "
            f"summary={summary.get('sequenceFrames')} directories={len(paths)}")

    packets: list[dict[str, Any]] = []
    for path in paths:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        frame = int(metadata.get("frame", path.parent.name))
        resolvers = [
            (index, resolver)
            for index, resolver in enumerate(
                metadata.get("fullscreenResolvers", []))
            if isinstance(resolver, dict) and
            resolver.get("priorityEndminfUber") is True
        ]
        require(len(resolvers) == 1,
                f"frame {frame} exact Uber priority resolver is not unique")
        resolver_index, resolver = resolvers[0]
        pixel = shader_identity(resolver, 4)
        variants = [name for name, contract in VARIANTS.items()
                    if int(contract["identity"]) == pixel]
        require(len(variants) == 1,
                f"frame {frame} exact Uber pixel identity is unsupported: "
                f"{pixel!r}")
        resources_path = path.parent / "resources.bin"
        require(resources_path.is_file(),
                f"frame {frame} resources.bin is absent")
        packets.append(inspect_resolver(
            frame, resolver_index, resolver, metadata,
            resources_path.read_bytes(), variant=variants[0]))

    variant_counts = {
        name: sum(packet["variant"] == name for packet in packets)
        for name in VARIANTS
    }
    require(variant_counts["peak"] == 1,
            f"exact Uber sequence requires one peak packet, got "
            f"{variant_counts['peak']}")
    require(variant_counts["normal"] == len(packets) - 1,
            "every non-peak sequence packet must use the ordinary shader")
    peak_index = next(index for index, packet in enumerate(packets)
                      if packet["variant"] == "peak")
    require(0 < peak_index < len(packets) - 1,
            "peak packet is not bracketed by ordinary packets")
    require(packets[peak_index - 1]["variant"] == "normal" and
            packets[peak_index + 1]["variant"] == "normal",
            "peak packet lacks immediate ordinary neighbors")

    shared_lanes = [
        ("b0", 0, 0), ("b0", 0, 1),
        ("b0", 27, 0), ("b0", 27, 2),
    ] + [
        ("b1", register, lane)
        for register in (1, 2, 4, 7, 9, 10, 11)
        for lane in range(4)
    ]
    shared_signatures = {}
    for buffer_name, register, lane in shared_lanes:
        label = f"{buffer_name}.c{register}.{'xyzw'[lane]}"
        values = [packet_lane_bits(packet, buffer_name, register, lane)
                  for packet in packets]
        require(len(set(values)) == 1,
                f"shader-read ordinary Uber lane varies: {label}")
        shared_signatures[label] = values[0]
    vs_signatures = {packet["vsB0"]["declaredRangeSha256"]
                     for packet in packets}
    require(len(vs_signatures) == 1,
            "exact Uber VS b0 varies across the sequence")

    shaders = {
        "vertex": archived_shader(capture, VERTEX_SHA256, 0, 608),
        "normalPixel": archived_shader(
            capture, NORMAL_PIXEL_SHA256, 4, 3416),
        "peakPixel": archived_shader(capture, PIXEL_SHA256, 4, 4216),
    }
    return {
        "schema": "endfield.endminf-uber-sequence-capture.v1",
        "status": "validated_exact_live_uber_sequence",
        "capture": str(capture.resolve()),
        "graphicsProfile": session["graphicsProfile"],
        "resourceBudgetBytes": int(session["graphicsResourceBudgetBytes"]),
        "frameCount": len(paths),
        "variantCounts": variant_counts,
        "peakFrame": packets[peak_index]["frame"],
        "peakPreviousFrame": packets[peak_index - 1]["frame"],
        "peakNextFrame": packets[peak_index + 1]["frame"],
        "vsB0Sha256": next(iter(vs_signatures)),
        "sharedOrdinaryReadLaneBits": shared_signatures,
        "shaders": shaders,
        "packets": packets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--constant-payload-only",
        action="store_true",
        help=(
            "validate only retained Uber constant ranges; does not claim "
            "the 128-MiB resource or draw-state contract"
        ),
    )
    parser.add_argument(
        "--sequence-contract",
        action="store_true",
        help=(
            "require one complete ordinary/peak/ordinary Full sequence, "
            "valid cadence, exact t0/t1/t2, and archived shader payloads"
        ),
    )
    parser.add_argument(
        "--frame",
        type=int,
        help="restrict validation to one retained presented frame",
    )
    args = parser.parse_args()
    if args.sequence_contract and (args.constant_payload_only or
                                   args.frame is not None):
        parser.error(
            "--sequence-contract cannot be combined with "
            "--constant-payload-only or --frame")
    try:
        report = (build_sequence_report(args.capture.resolve())
                  if args.sequence_contract else build_report(
                      args.capture.resolve(),
                      constant_payload_only=args.constant_payload_only,
                      frame_filter=args.frame,
                  ))
    except (OSError, ValueError, VerificationError) as exc:
        report = {
            "schema": ("endfield.endminf-uber-sequence-capture.v1"
                       if args.sequence_contract
                       else "endfield.endminf-uber-capture.v2"),
            "status": "validation_failed",
            "capture": str(args.capture.resolve()),
            "diagnostic": str(exc),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n",
                               encoding="utf-8")
        print(f"ERROR: {exc}")
        print(args.output)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
