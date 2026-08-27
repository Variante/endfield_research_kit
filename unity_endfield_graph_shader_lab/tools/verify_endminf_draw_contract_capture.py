#!/usr/bin/env python3
"""Validate draw-local IA, fixed state, samplers, and chronology for Endminf VFX."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_OUTPUT = (REPO / "reports/assets/character_recovery"
                  / "endminf_draw_contract_capture_latest.json")
SPEC = importlib.util.spec_from_file_location(
    "endminf_capture_closure",
    HERE / "verify_endminf_m29_m30_capture_completeness.py")
assert SPEC and SPEC.loader
CLOSURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLOSURE)


class ContractError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def integer(value: Any, label: str, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool) and
            value >= minimum, f"{label} is not an integer >= {minimum}")
    return value


def owner_resource_ids(draw: dict[str, Any]) -> set[int]:
    return {int(row.get("objectId", 0)) for row in draw.get("resources", [])
            if isinstance(row, dict) and int(row.get("objectId", 0)) != 0}


def validate_ia(frame: int, draw_index: int, owner: str,
                draw: dict[str, Any]) -> dict[str, Any]:
    label = f"{owner} frame {frame} draw {draw_index}"
    ia = draw.get("inputAssembler")
    require(isinstance(ia, dict), f"{label} has no draw-local inputAssembler")
    vertices = ia.get("vertexBuffers")
    require(isinstance(vertices, list) and len(vertices) >= 2,
            f"{label} does not record two IA vertex slots")
    by_slot = {integer(row.get("slot"), f"{label} IA vertex slot"): row
               for row in vertices if isinstance(row, dict)}
    require(0 in by_slot and 1 in by_slot,
            f"{label} is missing IA vertex slot 0 or 1")
    primary = by_slot[0]
    secondary = by_slot[1]
    primary_id = integer(primary.get("objectId"),
                         f"{label} IA v0 objectId", 1)
    secondary_id = integer(secondary.get("objectId"),
                           f"{label} IA v1 objectId", 1)
    primary_stride = integer(primary.get("stride"),
                             f"{label} IA v0 stride", 1)
    secondary_stride = integer(secondary.get("stride"),
                               f"{label} IA v1 stride")
    primary_offset = integer(primary.get("offset"),
                             f"{label} IA v0 offset")
    secondary_offset = integer(secondary.get("offset"),
                               f"{label} IA v1 offset")
    index = ia.get("indexBuffer")
    require(isinstance(index, dict), f"{label} has no IA indexBuffer")
    index_id = integer(index.get("objectId"),
                       f"{label} IA index objectId", 1)
    index_format = integer(index.get("format"),
                           f"{label} IA index format", 1)
    index_offset = integer(index.get("offset"),
                           f"{label} IA index offset")
    owned = owner_resource_ids(draw)
    require({primary_id, secondary_id, index_id}.issubset(owned),
            f"{label} draw-local IA objects do not match owner resources")
    require(integer(draw.get("topology"), f"{label} topology", 1) == 4,
            f"{label} topology is not triangle-list")
    require(index_format == 57, f"{label} index format is not R16_UINT")
    if owner == "M29":
        require(primary_stride in (60, 68),
                f"{label} M29 primary stride is not 60 or 68")
        require(primary_id == index_id,
                f"{label} M29 vertex/index ring object differs")
    elif owner in ("M30", "M31"):
        require(primary_stride == 36,
                f"{label} particle primary stride is not 36")
    return {
        "vertexBuffers": [
            {"slot": 0, "objectId": primary_id, "stride": primary_stride,
             "offset": primary_offset},
            {"slot": 1, "objectId": secondary_id, "stride": secondary_stride,
             "offset": secondary_offset},
        ],
        "indexBuffer": {"objectId": index_id, "format": index_format,
                        "offset": index_offset},
        "topology": 4,
    }


def validate_pipeline(frame: int, draw_index: int, owner: str,
                      draw: dict[str, Any]) -> dict[str, Any]:
    label = f"{owner} frame {frame} draw {draw_index}"
    state = draw.get("pipelineState")
    require(isinstance(state, dict) and state.get("valid") is True,
            f"{label} pipelineState is absent or invalid")
    target = state.get("target")
    depth_target = state.get("depthTarget")
    viewport = state.get("viewport")
    scissor = state.get("scissor")
    require(isinstance(target, dict) and
            integer(target.get("width"), f"{label} target width", 1) > 0 and
            integer(target.get("height"), f"{label} target height", 1) > 0 and
            integer(target.get("renderTargetCount"),
                    f"{label} render target count", 1) > 0,
            f"{label} render target descriptor is incomplete")
    require(target.get("depthBound") is True and isinstance(depth_target, dict),
            f"{label} depth attachment is not recorded")
    require(isinstance(viewport, dict) and
            integer(viewport.get("count"), f"{label} viewport count", 1) > 0,
            f"{label} viewport is absent")
    require(isinstance(scissor, dict) and
            integer(scissor.get("count"), f"{label} scissor count", 1) > 0,
            f"{label} scissor is absent")
    samplers = state.get("samplers")
    require(isinstance(samplers, list) and len(samplers) >= 3,
            f"{label} does not record PS samplers 0-2")
    by_slot = {integer(row.get("slot"), f"{label} sampler slot"): row
               for row in samplers if isinstance(row, dict)}
    for slot in range(3):
        row = by_slot.get(slot)
        require(row is not None, f"{label} PS sampler {slot} is absent")
        # M29's shader reads s0-s2. M30/M31 read only s0-s1, but s2's
        # explicit bound/unbound state must still be serialized.
        if owner == "M29" or slot < 2:
            require(row.get("bound") is True,
                    f"{label} required PS sampler {slot} is unbound")
        else:
            require(isinstance(row.get("bound"), bool),
                    f"{label} PS sampler {slot} bound state is absent")
        for field in ("filter", "addressU", "addressV", "addressW",
                      "comparison", "maxAnisotropy"):
            integer(row.get(field), f"{label} sampler {slot} {field}")
    for field in ("blend", "depthStencil", "rasterizer"):
        require(isinstance(state.get(field), dict),
                f"{label} {field} descriptor is absent")
    return {
        "target": target,
        "depthTarget": depth_target,
        "viewport": viewport,
        "scissor": scissor,
        "samplers": [by_slot[index] for index in range(3)],
        "blend": state["blend"],
        "depthStencil": state["depthStencil"],
        "rasterizer": state["rasterizer"],
    }


def build_report(capture: Path) -> dict[str, Any]:
    frame_root = capture / "graphics/frames"
    require(frame_root.is_dir(), f"graphics frame directory is absent: {frame_root}")
    paths = sorted(frame_root.glob("*/metadata.json"),
                   key=lambda path: int(path.parent.name))
    require(paths, "capture has no graphics metadata")
    owners: dict[str, list[dict[str, Any]]] = {
        name: [] for name in ("M29", "M30", "M31")}
    chronological_frames: list[dict[str, Any]] = []
    for path in paths:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        frame = int(metadata.get("frame", path.parent.name))
        frame_rows = []
        ordinals: set[int] = set()
        for draw_index, draw in enumerate(metadata.get("drawRecords", [])):
            if not isinstance(draw, dict):
                continue
            ordinal = integer(draw.get("drawOrdinal"),
                              f"frame {frame} draw {draw_index} drawOrdinal")
            require(ordinal not in ordinals,
                    f"frame {frame} repeats drawOrdinal {ordinal}")
            ordinals.add(ordinal)
            owner = CLOSURE.owner_name(draw)
            if owner not in owners:
                continue
            row = {
                "frame": frame,
                "drawIndex": draw_index,
                "drawOrdinal": ordinal,
                "indexCount": int(draw.get("count", -1)),
                "startIndex": int(draw.get("start", -1)),
                "baseVertex": int(draw.get("baseVertex", -1)),
                "inputAssembler": validate_ia(frame, draw_index, owner, draw),
                "pipelineState": validate_pipeline(
                    frame, draw_index, owner, draw),
            }
            owners[owner].append(row)
            frame_rows.append({"owner": owner, "drawOrdinal": ordinal,
                               "drawIndex": draw_index})
        if frame_rows:
            chronological_frames.append({
                "frame": frame,
                "draws": sorted(frame_rows, key=lambda row: row["drawOrdinal"]),
            })
    for owner, rows in owners.items():
        require(rows, f"capture contains no state-complete exact {owner} draw")
    return {
        "schema": "endfield.endminf-draw-contract-capture.v1",
        "status": "validated_draw_local_ia_state_and_chronology",
        "capture": str(capture.resolve()),
        "frameCount": len(paths),
        "owners": {owner: {"drawCount": len(rows), "draws": rows}
                   for owner, rows in owners.items()},
        "chronology": chronological_frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture.resolve())
    except (OSError, ValueError, ContractError,
            CLOSURE.VerificationError) as exc:
        report = {
            "schema": "endfield.endminf-draw-contract-capture.v1",
            "status": "validation_failed",
            "capture": str(args.capture.resolve()),
            "diagnostic": str(exc),
        }
        exit_code = 1
    else:
        exit_code = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if exit_code:
        print("ERROR: " + report["diagnostic"])
    print(args.output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
