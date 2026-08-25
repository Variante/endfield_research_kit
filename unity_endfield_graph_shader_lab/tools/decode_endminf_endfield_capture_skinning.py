#!/usr/bin/env python3
"""Decode Endminf skin palettes from focused EndfieldCapture frame packages.

The targeted capture preserves each retained draw's two skin-palette offsets
at draw time and stores the 8,413,184-byte skin-palette buffer at Present.
This decoder joins those facts using Endminf's exact LOD0 index counts and
fails closed when a mesh has no unique palette pair in a frame.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path


PALETTE_BYTES = 8_413_184
PALETTE_STRIDE = 16
ROWS_PER_MATRIX = 3

MESHES = {
    "body": (16_524, 44),
    "cloth_01": (101_994, 156),
    "cloth_03": (4_524, 1),
    "cloth_04": (20_577, 14),
    "hair": (27_615, 28),
}


class CaptureError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CaptureError(f"{path} must contain one JSON object")
    return value


def select_resource(metadata: dict, byte_size: int) -> dict:
    rows = [
        row for row in metadata.get("selectedResourceRecords", [])
        if row.get("completed") is True
        and int(row.get("byteSize", -1)) == byte_size
        and int(row.get("blobBytes", -1)) == byte_size
    ]
    if len(rows) != 1:
        raise CaptureError(
            f"expected one completed {byte_size}-byte resource, found {len(rows)}"
        )
    return rows[0]


def resource_bytes(blob: bytes, row: dict) -> bytes:
    start = int(row["blobOffset"])
    size = int(row["blobBytes"])
    end = start + size
    if start < 0 or end > len(blob):
        raise CaptureError(f"resource blob range [{start}, {end}) is out of bounds")
    return blob[start:end]


def unique_mesh_draw(metadata: dict, mesh: str) -> dict:
    index_count, _ = MESHES[mesh]
    matching_rows = [
        row for row in metadata.get("drawRecords", [])
        if row.get("indexedInstanced") is True
        and row.get("vsCb2RangeValid") is True
        and int(row.get("count", -1)) == index_count
    ]
    if not matching_rows:
        raise CaptureError(f"frame has no range-bearing {mesh} draw ({index_count} indices)")
    rows = [row for row in matching_rows if row.get("vsCb2MetadataValid") is True]
    if not rows:
        raise CaptureError(
            f"frame has {len(matching_rows)} range-bearing {mesh} draw(s), but no "
            "draw-time b2 metadata snapshot; capture again with the current EndfieldCapture build"
        )
    keys = {
        (
            int(row["vsCb2CurrentPaletteRaw"]),
            int(row["vsCb2PreviousPaletteRaw"]),
        )
        for row in rows
    }
    if len(keys) != 1:
        raise CaptureError(f"frame has ambiguous {mesh} palette pairs: {sorted(keys)}")
    current_raw, previous_raw = next(iter(keys))
    ranges = sorted({
        (
            int(row["vsCb2FirstConstant"]),
            int(row["vsCb2NumConstants"]),
            int(row.get("startInstance", 0)),
        )
        for row in rows
    })
    return {
        "indexCount": index_count,
        "matchingDrawRecords": len(rows),
        "matchingRanges": [
            {
                "firstConstant": first,
                "numConstants": count,
                "startInstance": start_instance,
            }
            for first, count, start_instance in ranges
        ],
        "currentBaseRaw": current_raw,
        "previousBaseRaw": previous_raw,
    }


def decode_mesh(palette: bytes, draw: dict, mesh: str) -> dict:
    _, matrix_count = MESHES[mesh]
    current_raw = draw["currentBaseRaw"]
    previous_raw = draw["previousBaseRaw"]
    current_base = current_raw + 3
    previous_base = previous_raw + 3
    palette_rows = len(palette) // PALETTE_STRIDE

    def matrices(base: int) -> list[list[list[float]]]:
        end = base + matrix_count * ROWS_PER_MATRIX
        if base < 0 or end > palette_rows:
            raise CaptureError(
                f"{mesh} palette range [{base}, {end}) exceeds {palette_rows} rows"
            )
        result = []
        for matrix in range(matrix_count):
            rows = []
            for row in range(ROWS_PER_MATRIX):
                offset = (base + matrix * ROWS_PER_MATRIX + row) * PALETTE_STRIDE
                values = struct.unpack_from("<4f", palette, offset)
                if not all(math.isfinite(value) for value in values):
                    raise CaptureError(f"{mesh} palette contains a non-finite value")
                rows.append(list(values))
            result.append(rows)
        return result

    return {
        **draw,
        "matrixCount": matrix_count,
        "currentEffectiveBaseRow": current_base,
        "previousEffectiveBaseRow": previous_base,
        "currentMatrices3x4": matrices(current_base),
        "previousMatrices3x4": matrices(previous_base),
    }


def decode_frame(frame_dir: Path, meshes: list[str]) -> dict:
    metadata = load_json(frame_dir / "metadata.json")
    if metadata.get("captureIncomplete") or metadata.get("captureFailed"):
        raise CaptureError(f"{frame_dir} is incomplete or failed")
    try:
        blob = (frame_dir / metadata.get("resourcesFile", "resources.bin")).read_bytes()
    except OSError as exc:
        raise CaptureError(f"cannot read resources for {frame_dir}: {exc}") from exc
    palette = resource_bytes(blob, select_resource(metadata, PALETTE_BYTES))
    return {
        "frame": int(metadata["frame"]),
        "frameDirectory": str(frame_dir.resolve()),
        "meshes": {
            mesh: decode_mesh(palette, unique_mesh_draw(metadata, mesh), mesh)
            for mesh in meshes
        },
    }


def decode_session(session_root: Path, meshes: list[str]) -> dict:
    frames_root = session_root / "graphics" / "frames"
    frame_dirs = sorted(
        (path for path in frames_root.iterdir() if path.is_dir()),
        key=lambda path: int(path.name),
    ) if frames_root.is_dir() else []
    if not frame_dirs:
        raise CaptureError(f"no graphics frames found under {frames_root}")
    frames = [decode_frame(path, meshes) for path in frame_dirs]
    return {
        "schema": "endfield.charinfo.endminf-captured-skin-palette-sequence.v1",
        "status": "decoded",
        "sessionRoot": str(session_root.resolve()),
        "meshContracts": {
            mesh: {"indexCount": MESHES[mesh][0], "matrixCount": MESHES[mesh][1]}
            for mesh in meshes
        },
        "frameCount": len(frames),
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_root", type=Path)
    parser.add_argument("--mesh", action="append", choices=sorted(MESHES))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    meshes = args.mesh or ["cloth_01", "cloth_04", "cloth_03", "hair", "body"]
    try:
        result = decode_session(args.session_root.resolve(), meshes)
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
