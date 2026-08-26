#!/usr/bin/env python3
"""Fail-closed verifier for the exact Endminf M27 graphics capture profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


VS_IDENTITY = 0xC0266E7FAC0046C1
PS_IDENTITY = 0x92D80A93ADD9C714
VS_BYTES = 8148
PS_BYTES = 8200
EXPECTED_COUNT = 1080
EXPECTED_INSTANCE_COUNT = 1
REQUIRED_CONSTANTS = {
    (0, 0): 1,
    (0, 1): 28,
    (0, 2): 16,
    (4, 0): 1,
    (4, 1): 106,
    (4, 2): 16,
    (4, 3): 36,
    (4, 4): 1,
}


class CaptureError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain one JSON object")
    return value


def shader_map(draw: dict) -> dict[int, dict]:
    rows = draw.get("shaders")
    require(isinstance(rows, list), "M27 draw has no shader records")
    result = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("stage"), int):
            result[row["stage"]] = row
    return result


def validate_draw(draw: dict) -> dict:
    require(draw.get("indexedInstanced") is True, "M27 draw is not indexed-instanced")
    require(draw.get("count") == EXPECTED_COUNT, "M27 draw is not the 1,080-index burst")
    require(draw.get("instanceCount") == EXPECTED_INSTANCE_COUNT,
            "M27 draw instance count drifted")
    require(draw.get("startInstance") == 0, "M27 startInstance is not zero")
    require(draw.get("priorityM27Geometry") is True,
            "M27 geometry-priority marker is absent; capture predates this profile")
    require(draw.get("priorityShaderPair") is True,
            "M27 shader pair was not priority-retained")

    shaders = shader_map(draw)
    for stage, identity, size, name in (
        (0, VS_IDENTITY, VS_BYTES, "vertex"),
        (4, PS_IDENTITY, PS_BYTES, "pixel"),
    ):
        row = shaders.get(stage)
        require(row is not None, f"M27 draw has no {name} shader record")
        require(row.get("identityHash") == identity,
                f"M27 {name} shader identity drifted")
        require(row.get("bytecodeSize") == size,
                f"M27 {name} shader byte size drifted")

    rows = draw.get("constantBuffers")
    require(isinstance(rows, list), "M27 draw has no constantBuffers")
    bindings = {}
    for row in rows:
        require(isinstance(row, dict), "M27 constantBuffers has a non-object row")
        key = (row.get("stage"), row.get("slot"))
        require(key not in bindings, f"M27 draw repeats constant binding {key}")
        bindings[key] = row
    missing = sorted(set(REQUIRED_CONSTANTS) - set(bindings))
    require(not missing, f"M27 draw is missing constant bindings: {missing}")
    for key, minimum in REQUIRED_CONSTANTS.items():
        row = bindings[key]
        require(row.get("rangeValid") is True, f"M27 {key} range is invalid")
        require(row.get("metadataValid") is True, f"M27 {key} bytes are invalid")
        require(isinstance(row.get("firstConstant"), int),
                f"M27 {key} has no numeric firstConstant")
        require(isinstance(row.get("numConstants"), int),
                f"M27 {key} has no numeric numConstants")
        require(row.get("capturedConstants", 0) >= minimum,
                f"M27 {key} captured {row.get('capturedConstants')} constants; need {minimum}")
        require(len(row.get("dataHex", "")) >= minimum * 32,
                f"M27 {key} dataHex is incomplete")

    return {
        "count": draw["count"],
        "instanceCount": draw["instanceCount"],
        "startInstance": draw["startInstance"],
        "vertexShaderIdentity": f"{VS_IDENTITY:016x}",
        "pixelShaderIdentity": f"{PS_IDENTITY:016x}",
        "constantRanges": [
            {
                "stage": key[0],
                "slot": key[1],
                "firstConstant": bindings[key]["firstConstant"],
                "numConstants": bindings[key]["numConstants"],
                "capturedConstants": bindings[key]["capturedConstants"],
                "truncated": bindings[key].get("truncated"),
            }
            for key in sorted(REQUIRED_CONSTANTS)
        ],
    }


def verify_session(session_root: Path) -> dict:
    frames_root = session_root / "graphics" / "frames"
    require(frames_root.is_dir(), f"graphics frame directory is missing: {frames_root}")
    candidates = []
    inspected = 0
    for frame_dir in sorted(path for path in frames_root.iterdir() if path.is_dir()):
        metadata_path = frame_dir / "metadata.json"
        if not metadata_path.is_file():
            continue
        inspected += 1
        metadata = load_json(metadata_path)
        require(metadata.get("captureIncomplete") is not True,
                f"frame {frame_dir.name} is incomplete")
        require(metadata.get("captureFailed") is not True,
                f"frame {frame_dir.name} failed")
        for draw in metadata.get("drawRecords", []):
            if (isinstance(draw, dict) and draw.get("count") == EXPECTED_COUNT and
                    draw.get("instanceCount") == EXPECTED_INSTANCE_COUNT):
                candidates.append({
                    "frame": frame_dir.name,
                    "evidence": validate_draw(draw),
                })
    require(inspected > 0, "session contains no complete graphics metadata")
    require(candidates, "session contains no exact M27 1,080-index shader draw")
    return {
        "schema": "endfield.endminf-m27-graphics-capture.v1",
        "status": "exact_m27_draw_ranges_captured",
        "sessionRoot": str(session_root.resolve()),
        "inspectedFrames": inspected,
        "matchedDraws": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("session_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify_session(args.session_root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "inspectedFrames": report["inspectedFrames"],
        "matchedDrawCount": len(report["matchedDraws"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
