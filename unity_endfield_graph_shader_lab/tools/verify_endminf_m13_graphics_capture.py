#!/usr/bin/env python3
"""Fail-closed verifier for the exact Endminf M13 graphics capture profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


VS_IDENTITY = 0x96A93DCB3965CBED
PS_IDENTITY = 0x0265C7A6806A095F
EXPECTED_COUNT = 6
EXPECTED_INSTANCE_COUNT = 1
PIXEL_STAGE = 4
SRV_TEXTURE_KIND = 3
REQUIRED_TEXTURE_SLOTS = frozenset(range(5))


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


def is_exact_draw(draw: object) -> bool:
    if not isinstance(draw, dict):
        return False
    shaders = {
        row.get("stage"): row
        for row in draw.get("shaders", [])
        if isinstance(row, dict)
    }
    return (
        draw.get("indexedInstanced") is True
        and draw.get("count") == EXPECTED_COUNT
        and draw.get("instanceCount") == EXPECTED_INSTANCE_COUNT
        and draw.get("priorityShaderPair") is True
        and shaders.get(0, {}).get("identityHash") == VS_IDENTITY
        and shaders.get(4, {}).get("identityHash") == PS_IDENTITY
    )


def validate_textures(metadata: dict) -> list[dict]:
    require(metadata.get("resourceSelectionTruncated") is not True,
            "M13 selected-resource list was truncated")
    rows = metadata.get("selectedResourceRecords")
    require(isinstance(rows, list), "M13 frame has no selectedResourceRecords")
    by_slot = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if (row.get("captureKind") == SRV_TEXTURE_KIND and
                row.get("stage") == PIXEL_STAGE and
                row.get("slot") in REQUIRED_TEXTURE_SLOTS):
            slot = row["slot"]
            require(slot not in by_slot, f"M13 repeats selected texture slot t{slot}")
            by_slot[slot] = row
    missing = sorted(REQUIRED_TEXTURE_SLOTS - set(by_slot))
    require(not missing, f"M13 selected textures are missing slots: {missing}")
    for slot in sorted(REQUIRED_TEXTURE_SLOTS):
        row = by_slot[slot]
        require(row.get("completed") is True,
                f"M13 selected texture t{slot} did not complete")
        require(row.get("failure") == 0,
                f"M13 selected texture t{slot} failed with code {row.get('failure')}")
        require(isinstance(row.get("blobOffset"), int) and row["blobOffset"] >= 0,
                f"M13 selected texture t{slot} has no valid blob offset")
        require(isinstance(row.get("blobBytes"), int) and row["blobBytes"] > 0,
                f"M13 selected texture t{slot} has no captured bytes")
    return [by_slot[slot] for slot in sorted(REQUIRED_TEXTURE_SLOTS)]


def verify_session(session_root: Path) -> dict:
    frames_root = session_root / "graphics" / "frames"
    require(frames_root.is_dir(), f"graphics frame directory is missing: {frames_root}")
    matches = []
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
        exact_draws = [draw for draw in metadata.get("drawRecords", [])
                       if is_exact_draw(draw)]
        if not exact_draws:
            continue
        require(len(exact_draws) == 1,
                f"frame {frame_dir.name} repeats the exact M13 draw")
        textures = validate_textures(metadata)
        resources_path = frame_dir / metadata.get("resourcesFile", "resources.bin")
        require(resources_path.is_file(),
                f"M13 resource blob is missing: {resources_path}")
        try:
            resource_bytes = resources_path.stat().st_size
        except OSError as exc:
            raise CaptureError(f"cannot stat {resources_path}: {exc}") from exc
        for slot, row in enumerate(textures):
            require(row["blobOffset"] + row["blobBytes"] <= resource_bytes,
                    f"M13 selected texture t{slot} exceeds resources.bin")
        matches.append({
            "frame": frame_dir.name,
            "count": EXPECTED_COUNT,
            "instanceCount": EXPECTED_INSTANCE_COUNT,
            "vertexShaderIdentity": f"{VS_IDENTITY:016x}",
            "pixelShaderIdentity": f"{PS_IDENTITY:016x}",
            "textures": [
                {
                    "slot": slot,
                    "byteSize": row.get("byteSize"),
                    "blobOffset": row["blobOffset"],
                    "blobBytes": row["blobBytes"],
                }
                for slot, row in enumerate(textures)
            ],
        })
    require(inspected > 0, "session contains no complete graphics metadata")
    require(matches, "session contains no exact M13 draw with textures t0-t4")
    return {
        "schema": "endfield.endminf-m13-graphics-capture.v1",
        "status": "exact_m13_draw_textures_captured",
        "sessionRoot": str(session_root.resolve()),
        "inspectedFrames": inspected,
        "matchedDraws": matches,
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
