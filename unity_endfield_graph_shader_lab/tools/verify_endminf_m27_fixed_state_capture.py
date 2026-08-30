#!/usr/bin/env python3
"""Publish only globally-gated fixed state for the exact M27 LitEffect pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_m27_fixed_state_capture_latest.json"
)
EXPECTED_SESSION = "20260827T225644Z"
EXPECTED_GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
EXPECTED_TARGET_SHA256 = (
    "a9726459d9ab90cf01d7536a4250315e85ebfe12da493ac16f7bad3b68e7df99"
)
VERTEX_IDENTITY = 0xC0266E7FAC0046C1
PIXEL_IDENTITY = 0x92D80A93ADD9C714


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def integer(value: Any, label: str, minimum: int = 0) -> int:
    require(
        isinstance(value, int) and not isinstance(value, bool)
        and value >= minimum,
        f"{label} is not an integer >= {minimum}",
    )
    return value


def number(value: Any, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(float(value)),
        f"{label} is not a finite number",
    )
    return float(value)


def boolean(value: Any, label: str) -> bool:
    require(isinstance(value, bool), f"{label} is not a boolean")
    return value


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"required capture file is absent: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"capture file is not an object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_session(capture: Path) -> dict[str, Any]:
    session_path = capture / "session.json"
    runtime_path = capture / "runtime.status.json"
    collected_path = capture / "collected/summary.json"
    graphics_path = capture / "graphics/summary.json"
    session = read_json(session_path)
    runtime = read_json(runtime_path)
    collected = read_json(collected_path)
    graphics = read_json(graphics_path)

    require(session.get("schema") == "endfieldCapture.session.v1",
            "session schema drifted")
    require(session.get("sessionId") == EXPECTED_SESSION,
            "capture sessionId is not the pinned fixed-state session")
    require(session.get("gameBuild") == EXPECTED_GAME_BUILD,
            "capture game build drifted")
    require(session.get("targetSha256") == EXPECTED_TARGET_SHA256,
            "capture target hash drifted")
    require(session.get("graphicsProfile") == "targeted" and
            session.get("evidenceLabel") == "forced-d3d11",
            "capture session is not targeted forced-D3D11 evidence")
    require(integer(session.get("providers"), "session providers") == 1,
            "capture session provider count drifted")

    require(runtime.get("schema") == "endfieldCapture.runtimeStatus.v1",
            "runtime status schema drifted")
    require(runtime.get("runtimeMode") == "d3d11-proxy",
            "runtime mode is not d3d11-proxy")
    for field in ("graphicsSelected", "graphicsHooksInstalled",
                  "graphicsAttached", "frameCompleted"):
        require(runtime.get(field) is True,
                f"runtime status {field} gate is false")
    for field in ("framePending", "frameIncomplete", "frameFailed"):
        require(runtime.get(field) is False,
                f"runtime status {field} gate is true")
    require(integer(runtime.get("graphicsRequests"),
                    "runtime graphicsRequests") == 1,
            "runtime did not complete exactly one graphics request")
    require(integer(runtime.get("graphicsRequestsIgnored"),
                    "runtime graphicsRequestsIgnored") == 0,
            "runtime ignored a graphics request")
    require(integer(runtime.get("graphicsDropped"),
                    "runtime graphicsDropped") == 0,
            "runtime dropped graphics events")

    require(collected.get("schema") == "endfieldCapture.summary.v1",
            "collector summary schema drifted")
    require(collected.get("complete") is True,
            "collector complete gate is false")
    require(integer(collected.get("dropped"), "collector dropped") == 0,
            "collector reports dropped records")
    require(integer(collected.get("invalidRecords"),
                    "collector invalidRecords") == 0,
            "collector reports invalid records")
    require(collected.get("writerError") is False,
            "collector writerError gate is true")

    require(graphics.get("schema") == "endfieldCapture.graphicsSummary.v1",
            "graphics summary schema drifted")
    require(graphics.get("runtimeMode") == "d3d11-proxy" and
            graphics.get("graphicsProfile") == "targeted" and
            graphics.get("evidenceLabel") == "forced-d3d11",
            "graphics summary identity drifted")
    for field in ("hooksInstalled", "attached", "quiescentCleanup",
                  "complete"):
        require(graphics.get(field) is True,
                f"graphics summary {field} gate is false")
    require(graphics.get("pendingRequest") is False,
            "graphics summary pendingRequest gate is true")
    require(integer(graphics.get("dropped"), "graphics dropped") == 0,
            "graphics summary reports dropped events")

    return {
        "sessionId": EXPECTED_SESSION,
        "gameBuild": EXPECTED_GAME_BUILD,
        "targetSha256": EXPECTED_TARGET_SHA256,
        "runtimeMode": "d3d11-proxy",
        "graphicsProfile": "targeted",
        "evidenceLabel": "forced-d3d11",
        "complete": True,
        "dropped": 0,
        "pendingRequest": False,
        "quiescentCleanup": True,
        "sourceFiles": {
            "session": {"path": str(session_path.resolve()),
                        "sha256": sha256(session_path)},
            "runtimeStatus": {"path": str(runtime_path.resolve()),
                              "sha256": sha256(runtime_path)},
            "collectorSummary": {"path": str(collected_path.resolve()),
                                 "sha256": sha256(collected_path)},
            "graphicsSummary": {"path": str(graphics_path.resolve()),
                                "sha256": sha256(graphics_path)},
        },
    }


def shader_pair(draw: dict[str, Any]) -> dict[int, int]:
    return {
        integer(row.get("stage"), "shader stage"):
            integer(row.get("identityHash"), "shader identityHash")
        for row in draw.get("shaders", []) if isinstance(row, dict)
    }


def exact_draw(draw: dict[str, Any]) -> bool:
    shaders = shader_pair(draw)
    return (shaders.get(0) == VERTEX_IDENTITY and
            shaders.get(4) == PIXEL_IDENTITY)


def validate_sampler(label: str, row: dict[str, Any], slot: int) -> dict[str, Any]:
    require(integer(row.get("slot"), f"{label} sampler slot") == slot,
            f"{label} sampler slot {slot} is malformed")
    require(row.get("bound") is True,
            f"{label} sampler slot {slot} is unbound")
    expected = {
        "filter": 20,
        "addressU": 1,
        "addressV": 1,
        "addressW": 1,
        "comparison": 1,
        "maxAnisotropy": 0,
    }
    for field, value in expected.items():
        require(integer(row.get(field), f"{label} sampler {slot} {field}") ==
                value, f"{label} sampler {slot} {field} drifted")
    expected_float = {"mipBias": 0.0, "minLod": 0.0, "maxLod": 1000.0}
    for field, value in expected_float.items():
        require(number(row.get(field), f"{label} sampler {slot} {field}") ==
                value, f"{label} sampler {slot} {field} drifted")
    return dict(row)


def validate_draw(frame: int, draw_index: int,
                  draw: dict[str, Any]) -> dict[str, Any]:
    label = f"M27 pair frame {frame} draw {draw_index}"
    require(draw.get("priorityShaderPair") is True,
            f"{label} priorityShaderPair gate is false")
    require(draw.get("indexedInstanced") is True,
            f"{label} is not indexed-instanced")
    require(integer(draw.get("topology"), f"{label} topology") == 4,
            f"{label} topology is not triangle-list")
    require(integer(draw.get("instanceCount"),
                    f"{label} instanceCount") == 1,
            f"{label} instanceCount is not one")
    require(integer(draw.get("startInstance"),
                    f"{label} startInstance") == 0,
            f"{label} startInstance is not zero")

    ia = draw.get("inputAssembler")
    require(isinstance(ia, dict), f"{label} inputAssembler is absent")
    vertices = ia.get("vertexBuffers")
    require(isinstance(vertices, list),
            f"{label} vertex buffers are absent")
    by_slot = {integer(row.get("slot"), f"{label} vertex slot"): row
               for row in vertices if isinstance(row, dict)}
    require(0 in by_slot and 1 in by_slot,
            f"{label} vertex slots 0/1 are incomplete")
    stride = integer(by_slot[0].get("stride"), f"{label} vertex stride")
    require(stride in (60, 68), f"{label} vertex stride is not 60 or 68")
    index = ia.get("indexBuffer")
    require(isinstance(index, dict), f"{label} index buffer is absent")
    require(integer(index.get("format"), f"{label} index format") == 57,
            f"{label} index format is not R16_UINT")

    state = draw.get("pipelineState")
    require(isinstance(state, dict) and state.get("valid") is True,
            f"{label} pipelineState is absent or invalid")
    target = state.get("target")
    require(isinstance(target, dict), f"{label} target is absent")
    require(integer(target.get("renderTargetCount"),
                    f"{label} renderTargetCount") == 5,
            f"{label} does not bind five render targets")
    require(target.get("depthBound") is True,
            f"{label} depth attachment is absent")

    viewport = state.get("viewport")
    scissor = state.get("scissor")
    require(isinstance(viewport, dict) and
            integer(viewport.get("count"), f"{label} viewport count") == 1,
            f"{label} viewport is absent")
    require(isinstance(scissor, dict) and
            integer(scissor.get("count"), f"{label} scissor count") == 1,
            f"{label} scissor is absent")
    expected_rect = {
        "left": 0,
        "top": 0,
        "right": integer(target.get("width"), f"{label} target width", 1),
        "bottom": integer(target.get("height"), f"{label} target height", 1),
    }
    for field, value in expected_rect.items():
        require(integer(scissor.get(field), f"{label} scissor {field}") == value,
                f"{label} scissor {field} differs from the target extent")

    samplers = state.get("samplers")
    require(isinstance(samplers, list) and len(samplers) == 3,
            f"{label} does not record exactly captured samplers s0-s2")
    sampler_by_slot = {
        integer(row.get("slot"), f"{label} sampler slot"): row
        for row in samplers if isinstance(row, dict)
    }
    captured_samplers = [
        validate_sampler(label, sampler_by_slot[slot], slot)
        for slot in range(3)
    ]

    blend = state.get("blend")
    require(isinstance(blend, dict), f"{label} blend state is absent")
    require(blend.get("enabled") is False,
            f"{label} blend must be disabled")
    for field, value in {
        "source": 2, "destination": 1, "operation": 1,
        "sourceAlpha": 2, "destinationAlpha": 1,
        "operationAlpha": 1, "writeMask": 15,
        "sampleMask": 0xffffffff,
    }.items():
        require(integer(blend.get(field), f"{label} blend {field}") == value,
                f"{label} blend {field} drifted")

    depth = state.get("depthStencil")
    require(isinstance(depth, dict), f"{label} depthStencil is absent")
    require(depth.get("depthEnabled") is True and
            integer(depth.get("writeMask"), f"{label} depth writeMask") == 1 and
            integer(depth.get("function"), f"{label} depth function") == 7,
            f"{label} depth state is not writable reversed-Z GREATER_EQUAL")
    require(depth.get("stencilEnabled") is True and
            integer(depth.get("stencilReference"),
                    f"{label} stencil reference") == 0,
            f"{label} stencil enable/reference drifted")

    rasterizer = state.get("rasterizer")
    require(isinstance(rasterizer, dict), f"{label} rasterizer is absent")
    expected_raster = {
        "fillMode": 3,
        "cullMode": 3,
        "frontCounterClockwise": True,
        "depthClipEnabled": True,
        "scissorEnabled": True,
        "multisampleEnabled": False,
        "antialiasedLineEnabled": False,
    }
    for field, value in expected_raster.items():
        actual = rasterizer.get(field)
        if isinstance(value, bool):
            boolean(actual, f"{label} rasterizer {field}")
        else:
            integer(actual, f"{label} rasterizer {field}")
        require(actual == value, f"{label} rasterizer {field} drifted")

    return {
        "frame": frame,
        "drawIndex": draw_index,
        "drawOrdinal": integer(draw.get("drawOrdinal"),
                               f"{label} drawOrdinal"),
        "indexCount": integer(draw.get("count"), f"{label} indexCount", 1),
        "instanceCount": 1,
        "startInstance": 0,
        "vertexStride": stride,
        "renderTargetCount": 5,
        "viewport": viewport,
        "scissor": scissor,
        "samplersS0ThroughS2": captured_samplers,
        "blend": blend,
        "depthStencil": depth,
        "rasterizer": rasterizer,
    }


def build_report(capture: Path) -> dict[str, Any]:
    session = validate_session(capture)
    frame_root = capture / "graphics/frames"
    require(frame_root.is_dir(),
            f"graphics frame directory is absent: {frame_root}")
    paths = sorted(frame_root.glob("*/metadata.json"),
                   key=lambda path: int(path.parent.name))
    require(paths, "capture contains no graphics frame metadata")
    rows: list[dict[str, Any]] = []
    frame_sources = []
    for path in paths:
        metadata = read_json(path)
        frame = integer(metadata.get("frame"), "graphics frame")
        require(metadata.get("captureIncomplete") is False,
                f"frame {frame} captureIncomplete gate is true")
        require(metadata.get("captureFailed") is False,
                f"frame {frame} captureFailed gate is true")
        require(integer(metadata.get("droppedEvents"),
                        f"frame {frame} droppedEvents") == 0,
                f"frame {frame} reports dropped events")
        require(metadata.get("drawRecordsTruncated") is False,
                f"frame {frame} drawRecordsTruncated gate is true")
        frame_rows = []
        for draw_index, draw in enumerate(metadata.get("drawRecords", [])):
            if isinstance(draw, dict) and exact_draw(draw):
                row = validate_draw(frame, draw_index, draw)
                rows.append(row)
                frame_rows.append(row["drawOrdinal"])
        if frame_rows:
            frame_sources.append({
                "frame": frame,
                "path": str(path.resolve()),
                "sha256": sha256(path),
                "drawOrdinals": frame_rows,
            })
    require(rows, "capture contains no exact M27 LitEffect shader-pair draw")
    return {
        "schema": "endfield.endminf-m27-fixed-state-capture.v1",
        "status": "validated_exact_m27_liteffect_fixed_state",
        "capture": str(capture.resolve()),
        "session": session,
        "shaderPair": {
            "vertexIdentity": f"0x{VERTEX_IDENTITY:016X}",
            "pixelIdentity": f"0x{PIXEL_IDENTITY:016X}",
            "pass": "HGRP/LitEffect HGBuffer subprogram 113",
        },
        "scopeBoundary": (
            "The captured pair is shared by M01/M38/M27. These rows close the "
            "pair's fixed D3D11 state; they do not claim material identity, "
            "particle chronology, or presentation parity."
        ),
        "frameSources": frame_sources,
        "drawCount": len(rows),
        "draws": rows,
        "closedReplayState": {
            "depthEnabled": True,
            "depthWriteMask": 1,
            "depthFunction": 7,
            "depthFunctionName": "D3D11_COMPARISON_GREATER_EQUAL",
            "fillMode": 3,
            "cullMode": 3,
            "cullModeName": "D3D11_CULL_BACK",
            "frontCounterClockwise": True,
            "depthClipEnabled": True,
            "scissorEnabled": True,
        },
        "unresolvedBoundary": (
            "The observer retained PS samplers s0-s2 only. This report does not "
            "infer s3-s5 and does not authorize texture, mip, constant-buffer, "
            "geometry, chronology, or presentation changes."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture.resolve())
    except (OSError, ValueError, json.JSONDecodeError,
            VerificationError) as exc:
        report = {
            "schema": "endfield.endminf-m27-fixed-state-capture.v1",
            "status": "validation_failed",
            "capture": str(args.capture.resolve()),
            "diagnostic": str(exc),
        }
        exit_code = 1
    else:
        exit_code = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    if exit_code:
        print("ERROR: " + report["diagnostic"])
    print(args.output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
