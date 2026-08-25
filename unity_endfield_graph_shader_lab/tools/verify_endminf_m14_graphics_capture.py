#!/usr/bin/env python3
"""Validate and decode exact Endminf M14 draw constants from EndfieldCapture.

The verifier is intentionally tied to the pinned retail build and the exact
VS4914/PS4915 bytecode pair. It rejects pre-M14 recorder output, incomplete
GPU copies, truncated shader-addressable ranges, and shader/count lookalikes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
TARGET_SHA256 = "a9726459d9ab90cf01d7536a4250315e85ebfe12da493ac16f7bad3b68e7df99"
M14_INDEX_COUNT = 1_098
VS_IDENTITY = 0x62A5CE6C09171DE9
PS_IDENTITY = 0x5558DEDDB1EE6188
VS_BYTECODE_SIZE = 6_148
PS_BYTECODE_SIZE = 5_072

# (stage, slot): (highest addressable vector count, recorder vector limit).
# The limits exactly cover every constant index read by VS4914/PS4915.
REQUIRED_BINDINGS = {
    (0, 0): (2, 2),
    (0, 1): (82, 82),
    (0, 2): (104, 104),
    (0, 3): (16, 16),
    (0, 4): (10, 10),
    (4, 0): (28, 28),
    (4, 1): (105, 105),
    (4, 2): (5, 5),
    (4, 3): (22, 22),
}


class CaptureError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CaptureError(f"{path} must contain one JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def decode_binding(row: dict, stage: int, slot: int,
                   required_count: int, capture_limit: int) -> dict:
    label = f"stage {stage} b{slot}"
    require(row.get("rangeValid") is True, f"{label} range is not valid")
    require(row.get("metadataValid") is True, f"{label} GPU snapshot is not valid")
    first = int(row.get("firstConstant", -1))
    count = int(row.get("numConstants", -1))
    captured = int(row.get("capturedConstants", -1))
    require(first >= 0, f"{label} has an invalid firstConstant")
    require(count >= required_count,
            f"{label} exposes {count} vectors; shader requires {required_count}")
    require(captured == capture_limit,
            f"{label} captured {captured} vectors; expected {capture_limit}")
    require(row.get("truncated") is (count > capture_limit),
            f"{label} truncation flag does not match its declared range")
    data_hex = row.get("dataHex")
    require(isinstance(data_hex, str), f"{label} has no dataHex payload")
    try:
        data = bytes.fromhex(data_hex)
    except ValueError as exc:
        raise CaptureError(f"{label} dataHex is malformed: {exc}") from exc
    require(len(data) == captured * 16,
            f"{label} payload has {len(data)} bytes; expected {captured * 16}")
    vectors = [list(struct.unpack_from("<4f", data, index * 16))
               for index in range(captured)]
    uint_vectors = [list(struct.unpack_from("<4I", data, index * 16))
                    for index in range(captured)]
    return {
        "stage": stage,
        "slot": slot,
        "bufferId": int(row.get("bufferId", 0)),
        "firstConstant": first,
        "numConstants": count,
        "capturedConstants": captured,
        "truncated": bool(row["truncated"]),
        "float4": vectors,
        "uint4": uint_vectors,
    }


def decode_m14_draw(draw: dict) -> dict:
    require(draw.get("indexedInstanced") is True, "M14 draw is not indexed-instanced")
    require(int(draw.get("count", -1)) == M14_INDEX_COUNT,
            f"M14 draw count is not {M14_INDEX_COUNT}")
    require(int(draw.get("instanceCount", -1)) == 1, "M14 instanceCount is not one")
    require(int(draw.get("startInstance", -1)) == 0, "M14 startInstance is not zero")
    require(draw.get("priorityShaderPair") is True,
            "M14 priority marker is absent; capture predates the exact recorder")

    shader_rows = draw.get("shaders")
    require(isinstance(shader_rows, list), "M14 draw has no shader records")
    shaders = {int(row.get("stage", -1)): row for row in shader_rows
               if isinstance(row, dict)}
    for stage, identity, size, name in (
        (0, VS_IDENTITY, VS_BYTECODE_SIZE, "VS4914"),
        (4, PS_IDENTITY, PS_BYTECODE_SIZE, "PS4915"),
    ):
        row = shaders.get(stage)
        require(row is not None, f"M14 draw has no {name} record")
        require(int(row.get("identityHash", -1)) == identity,
                f"M14 {name} SHA-256 identity does not match")
        require(int(row.get("bytecodeSize", -1)) == size,
                f"M14 {name} bytecode size does not match")

    rows = draw.get("constantBuffers")
    require(isinstance(rows, list),
            "M14 draw has no constantBuffers; capture with the current proxy")
    indexed: dict[tuple[int, int], dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise CaptureError("M14 constantBuffers contains a non-object row")
        key = (int(row.get("stage", -1)), int(row.get("slot", -1)))
        if key in indexed:
            raise CaptureError(f"M14 draw repeats stage {key[0]} b{key[1]}")
        indexed[key] = row
    missing = sorted(set(REQUIRED_BINDINGS) - set(indexed))
    require(not missing, f"M14 draw is missing constant ranges: {missing}")
    bindings = {
        f"{stage}:b{slot}": decode_binding(
            indexed[(stage, slot)], stage, slot, required, limit
        )
        for (stage, slot), (required, limit) in REQUIRED_BINDINGS.items()
    }

    c13 = bindings["0:b3"]["float4"][13]
    require(all(math.isfinite(value) for value in c13),
            "M14 VS b3/c13 contains a non-finite color carrier")
    return {
        "indexCount": M14_INDEX_COUNT,
        "instanceCount": 1,
        "startInstance": 0,
        "vertexShader": {
            "name": "4914_endfield_dxbc_0.dxbc",
            "identitySha256Prefix": f"{VS_IDENTITY:016x}",
            "bytecodeSize": VS_BYTECODE_SIZE,
        },
        "pixelShader": {
            "name": "4915_endfield_dxbc_1.dxbc",
            "identitySha256Prefix": f"{PS_IDENTITY:016x}",
            "bytecodeSize": PS_BYTECODE_SIZE,
        },
        "vsPerDrawC13": c13,
        "vertexColorMultiplier": [1.0 - value for value in c13],
        "bindings": bindings,
    }


def decode_frame(frame_dir: Path) -> dict | None:
    metadata_path = frame_dir / "metadata.json"
    metadata = load_json(metadata_path)
    require(metadata.get("schema") == "endfieldCapture.graphicsFrame.v1",
            f"{frame_dir} has an unsupported graphics schema")
    require(metadata.get("runtimeMode") == "d3d11-proxy",
            f"{frame_dir} was not captured by the graphics-only proxy")
    require(metadata.get("evidenceLabel") == "forced-d3d11",
            f"{frame_dir} is not forced-D3D11 evidence")
    require(metadata.get("graphicsProfile") in ("targeted", "full"),
            f"{frame_dir} does not use a range-bearing graphics profile")
    require(metadata.get("captureIncomplete") is False and
            metadata.get("captureFailed") is False,
            f"{frame_dir} is incomplete or failed")
    draws = metadata.get("drawRecords")
    require(isinstance(draws, list), f"{frame_dir} has no drawRecords")
    candidates = [row for row in draws if isinstance(row, dict) and
                  int(row.get("count", -1)) == M14_INDEX_COUNT and
                  row.get("priorityShaderPair") is True]
    if not candidates:
        return None
    return {
        "frame": int(metadata.get("frame", frame_dir.name)),
        "frameDirectory": str(frame_dir.resolve()),
        "metadataSha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        "m14DrawCount": len(candidates),
        "m14Draws": [decode_m14_draw(row) for row in candidates],
    }


def decode_session(session_root: Path) -> dict:
    session = load_json(session_root / "session.json")
    require(session.get("schema") == "endfieldCapture.session.v1",
            "session schema is unsupported")
    require(session.get("gameBuild") == GAME_BUILD, "session game build is not pinned")
    require(session.get("targetSha256") == TARGET_SHA256,
            "session Endfield.exe hash is not pinned")
    require(int(session.get("providers", 0)) == 1,
            "session must use the dedicated graphics-only provider")
    require(session.get("evidenceLabel") == "forced-d3d11",
            "session is not forced-D3D11 evidence")
    require(session.get("graphicsProfile") in ("targeted", "full"),
            "session does not use a range-bearing profile")

    frames_root = session_root / "graphics" / "frames"
    try:
        frame_dirs = sorted(
            (path for path in frames_root.iterdir() if path.is_dir()),
            key=lambda path: int(path.name),
        )
    except (OSError, ValueError) as exc:
        raise CaptureError(f"cannot enumerate graphics frames under {frames_root}: {exc}") from exc
    require(bool(frame_dirs), f"no graphics frames found under {frames_root}")
    decoded = [decode_frame(path) for path in frame_dirs]
    target_frames = [row for row in decoded if row is not None]
    require(bool(target_frames),
            "session contains no priority-retained VS4914/PS4915 M14 draw")
    return {
        "schema": "endfield.charinfo.endminf-m14-graphics-capture.v1",
        "status": "validated",
        "sessionRoot": str(session_root.resolve()),
        "sessionId": session.get("sessionId"),
        "gameBuild": GAME_BUILD,
        "capturedFrameCount": len(frame_dirs),
        "m14FrameCount": len(target_frames),
        "framesWithoutM14": len(frame_dirs) - len(target_frames),
        "frames": target_frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = decode_session(args.session_root.resolve())
    except (CaptureError, OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
