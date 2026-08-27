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
PIXEL_IDENTITY = 0x3F490E1504C43554
VERTEX_IDENTITY = 0xA8C084C37EBA0ECC
VERTEX_SHA256 = (
    "a8c084c37eba0ecc78f26d984a2b8c658f8d743002048c84431807d9dee0ce4e"
)
PIXEL_SHA256 = (
    "3f490e1504c435541769ee03e881583df554e652df155e5b942a3a410d8e086b"
)
MINIMUM_RESOURCE_BUDGET = 128 * 1024 * 1024


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
    viewport = state.get("viewport")
    scissor = state.get("scissor")
    sampler = state.get("sampler")
    blend = state.get("blend")
    depth = state.get("depthStencil")
    raster = state.get("rasterizer")
    require(all(isinstance(value, dict) for value in
                (target, viewport, scissor, sampler, blend, depth, raster)),
            f"frame {frame} exact Uber pipeline state is incomplete")
    assert isinstance(target, dict) and isinstance(viewport, dict)
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
            target.get("depthBound") is False,
            f"frame {frame} exact Uber output target contract drifted")
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
                     resource_blob: bytes) -> dict[str, Any]:
    require(resolver.get("priorityEndminfUber") is True,
            f"frame {frame} resolver {resolver_index} lost Uber priority tagging")
    require(shader_identity(resolver, 0) == VERTEX_IDENTITY,
            f"frame {frame} resolver {resolver_index} has the wrong Uber VS")
    vs_b0 = constant_range(
        resolver, "vsConstantBuffers", "VS", 0)
    b0 = constant_range(resolver, "psConstantBuffers", "PS", 0)
    b1 = constant_range(resolver, "psConstantBuffers", "PS", 1)
    require(int(vs_b0.get("numConstants", 0)) >= 1,
            f"frame {frame} exact Uber VS b0 does not expose c0")
    require(int(b0.get("numConstants", 0)) >= 28,
            f"frame {frame} exact Uber PS b0 does not expose c27")
    require(int(b1.get("numConstants", 0)) >= 26,
            f"frame {frame} exact Uber PS b1 does not expose c25")
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
    radial = vector(b1_payload, int(b1["firstConstant"]), 0)
    radial2 = vector(b1_payload, int(b1["firstConstant"]), 25)
    vs_b0_values = declared_vectors(
        vs_b0_payload, int(vs_b0["firstConstant"]), 1)
    b0_values = declared_vectors(
        b0_payload, int(b0["firstConstant"]), 28)
    b1_values = declared_vectors(
        b1_payload, int(b1["firstConstant"]), 26)
    require(finite(vertex_params + exposure + radial + radial2),
            f"frame {frame} exact Uber constants are non-finite")
    require(0.0 <= radial[0] <= 1.0 and 0.0 <= radial[1] <= 1.0,
            f"frame {frame} exact Uber center is outside viewport space")
    require(radial[2] >= 0.0 and radial[3] > 0.0 and radial2[1] >= 0.0,
            f"frame {frame} exact Uber intensity/power lanes are invalid")
    require(radial2[0] in (3.0, 6.0),
            f"frame {frame} exact Uber mode is unexpected: {radial2[0]}")
    require(radial2[2] in (0.0, 1.0) and radial2[3] in (0.0, 1.0),
            f"frame {frame} exact Uber average-step flags are invalid")
    draw_pipeline_state = pipeline_state(resolver, frame)
    return {
        "frame": frame,
        "resolverIndex": resolver_index,
        "fullscreenOrdinal": int(resolver.get("fullscreenOrdinal", -1)),
        "pixelIdentity": f"{PIXEL_IDENTITY:016x}",
        "pixelSha256": PIXEL_SHA256,
        "vertexIdentity": f"{VERTEX_IDENTITY:016x}",
        "vertexSha256": VERTEX_SHA256,
        "pipelineState": draw_pipeline_state,
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
            "c0RadialBlurParams": list(radial),
            "c25RadialBlurParams2": list(radial2),
            "declaredConstants": 26,
            "declaredRangeSha256": range_sha256(b1_values),
            "declaredRangeHex": range_hex(b1_values),
            "values": b1_values,
        },
    }


def build_report(capture: Path) -> dict[str, Any]:
    session_path = capture / "session.json"
    require(session_path.is_file(), f"session manifest is absent: {session_path}")
    session = json.loads(session_path.read_text(encoding="utf-8"))
    require(session.get("graphicsProfile") == "targeted",
            "capture is not the targeted graphics profile")
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
                frame, resolver_index, resolver, metadata, resource_blob))
    require(packets,
            "capture contains no exact Endminf combined Uber pulse resolver")
    return {
        "schema": "endfield.endminf-uber-capture.v1",
        "status": "validated_exact_live_uber_binding",
        "capture": str(capture.resolve()),
        "frameCount": len(paths),
        "resourceBudgetBytes": int(session["graphicsResourceBudgetBytes"]),
        "qpcFrequency": int(session["qpcFrequency"]),
        "packetCount": len(packets),
        "packets": packets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture.resolve())
    except (OSError, ValueError, VerificationError) as exc:
        report = {
            "schema": "endfield.endminf-uber-capture.v1",
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
