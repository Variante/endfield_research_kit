#!/usr/bin/env python3
"""Verify the retained retail owner of Endminf's opening strip mosaic."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import struct
from pathlib import Path
from typing import Any


VS_IDENTITY = 2989953800188099650
PS_IDENTITY = 8564444548370193726
EXPECTED_INDEX_COUNTS = [11610, 7998, 4176, 420]
EXPECTED_VERTEX_STRIDE = 60
EXPECTED_TARGET = (3840, 2160)


class VerificationError(RuntimeError):
    pass


def _metadata(frame: Path) -> dict[str, Any]:
    path = frame / "metadata.json"
    if not path.is_file():
        raise VerificationError(f"frame metadata is absent: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _shader_pair(draw: dict[str, Any]) -> tuple[int, int] | None:
    rows = {int(row.get("stage", -1)): int(row.get("identityHash", -1))
            for row in draw.get("shaders", [])}
    if 0 not in rows or 4 not in rows:
        return None
    return rows[0], rows[4]


def _resource_row(
    metadata: dict[str, Any], object_id: int, capture_kind: int
) -> dict[str, Any]:
    rows = [row for row in metadata.get("selectedResourceRecords", [])
            if int(row.get("objectId", -1)) == object_id
            and int(row.get("captureKind", -1)) == capture_kind
            and row.get("completed") is True]
    if len(rows) != 1:
        raise VerificationError(
            f"resource {object_id} kind {capture_kind} has {len(rows)} retained rows"
        )
    return rows[0]


def _slice(payload: bytes, offset: int, size: int) -> bytes:
    result = payload[offset:offset + size]
    if len(result) != size:
        raise VerificationError(
            f"resource range is truncated at {offset}: expected {size}, got {len(result)}"
        )
    return result


def _decode_packet(
    frame: Path, metadata: dict[str, Any], draw: dict[str, Any]
) -> dict[str, Any]:
    ia = draw.get("inputAssembler", {})
    vertex_rows = ia.get("vertexBuffers", [])
    if not vertex_rows:
        raise VerificationError("opening owner has no vertex buffer")
    vertex = vertex_rows[0]
    index = ia.get("indexBuffer", {})
    stride = int(vertex.get("stride", -1))
    count = int(draw.get("count", -1))
    start = int(draw.get("start", -1))
    base_vertex = int(draw.get("baseVertex", -1))
    if stride != EXPECTED_VERTEX_STRIDE:
        raise VerificationError(f"opening vertex stride drifted: {stride}")
    if count <= 0 or count % 6:
        raise VerificationError(f"opening index count is not quad-aligned: {count}")
    if int(index.get("format", -1)) != 57:
        raise VerificationError("opening index format is not R16_UINT")

    vertex_row = _resource_row(metadata, int(vertex["objectId"]), 0)
    index_row = _resource_row(metadata, int(index["objectId"]), 1)
    resources = frame / str(metadata.get("resourcesFile", "resources.bin"))
    if not resources.is_file():
        raise VerificationError(f"frame resource blob is absent: {resources}")
    resource_payload = resources.read_bytes()
    index_offset = (int(index_row["blobOffset"]) + int(index.get("offset", 0))
                    + start * 2)
    raw_indices = _slice(resource_payload, index_offset, count * 2)
    indices = struct.unpack(f"<{count}H", raw_indices)
    quad_count = count // 6
    topology_errors = 0
    horizontal_ratios: list[float] = []
    mins = [math.inf, math.inf, math.inf]
    maxs = [-math.inf, -math.inf, -math.inf]
    vertex_blob = int(vertex_row["blobOffset"])
    vertex_offset = int(vertex.get("offset", 0))
    for quad in range(quad_count):
        first = quad * 4
        expected = (first, first + 1, first + 2, first, first + 2, first + 3)
        if indices[quad * 6:quad * 6 + 6] != expected:
            topology_errors += 1
            continue
        positions: list[tuple[float, float, float]] = []
        for local in range(4):
            address = (vertex_blob + vertex_offset
                       + (base_vertex + first + local) * stride)
            raw = _slice(resource_payload, address, 12)
            position = struct.unpack("<3f", raw)
            positions.append(position)
            for axis in range(3):
                mins[axis] = min(mins[axis], position[axis])
                maxs[axis] = max(maxs[axis], position[axis])
        width = max(row[0] for row in positions) - min(row[0] for row in positions)
        height = max(row[1] for row in positions) - min(row[1] for row in positions)
        horizontal_ratios.append(width / max(height, 1.0e-8))
    if topology_errors:
        raise VerificationError(
            f"opening owner has {topology_errors} non-independent quad packets"
        )
    horizontal_fraction = sum(ratio >= 4.0 for ratio in horizontal_ratios) / quad_count
    return {
        "frame": int(metadata.get("frame", frame.name)),
        "drawOrdinal": int(draw.get("drawOrdinal", -1)),
        "indexCount": count,
        "quadCount": quad_count,
        "vertexStride": stride,
        "startIndex": start,
        "baseVertex": base_vertex,
        "boundsMin": mins,
        "boundsMax": maxs,
        "medianWidthToHeight": statistics.median(horizontal_ratios),
        "horizontalQuadFraction": horizontal_fraction,
    }


def build_report(session: Path) -> dict[str, Any]:
    frames_root = session / "graphics" / "frames"
    if not frames_root.is_dir():
        raise VerificationError(f"graphics frame root is absent: {frames_root}")
    packets: list[dict[str, Any]] = []
    errors: list[str] = []
    frame_dirs = sorted(
        (path for path in frames_root.iterdir() if path.is_dir()),
        key=lambda path: int(path.name),
    )
    for frame in frame_dirs:
        metadata = _metadata(frame)
        for draw in metadata.get("drawRecords", []):
            if _shader_pair(draw) != (VS_IDENTITY, PS_IDENTITY):
                continue
            pipeline = draw.get("pipelineState", {})
            target = pipeline.get("target", {})
            blend = pipeline.get("blend", {})
            if (int(target.get("width", -1)), int(target.get("height", -1))) \
                    != EXPECTED_TARGET:
                errors.append(f"frame {frame.name} opening target is not 3840x2160")
            if not blend.get("enabled") or int(blend.get("source", -1)) != 5 \
                    or int(blend.get("destination", -1)) != 6:
                errors.append(
                    f"frame {frame.name} opening blend is not SrcAlpha/InvSrcAlpha"
                )
            try:
                packets.append(_decode_packet(frame, metadata, draw))
            except (KeyError, OSError, ValueError, VerificationError) as exc:
                errors.append(f"frame {frame.name}: {exc}")

    counts = [row["indexCount"] for row in packets]
    if counts != EXPECTED_INDEX_COUNTS:
        errors.append(
            f"opening temporal index counts drifted: expected {EXPECTED_INDEX_COUNTS}, "
            f"got {counts}"
        )
    if packets and min(row["horizontalQuadFraction"] for row in packets) < 0.95:
        errors.append("opening owner is no longer predominantly horizontal quads")
    return {
        "schema": "endfield.endminf-opening-strip-capture-verification.v1",
        "status": "validated" if not errors else "rejected",
        "session": str(session.resolve()),
        "shaderPair": {
            "vertexIdentityHash": VS_IDENTITY,
            "pixelIdentityHash": PS_IDENTITY,
            "vertexSha256Prefix": f"{VS_IDENTITY:016x}",
            "pixelSha256Prefix": f"{PS_IDENTITY:016x}",
        },
        "packetCount": len(packets),
        "indexCounts": counts,
        "packets": packets,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = build_report(args.session.resolve())
    except (OSError, ValueError, VerificationError) as exc:
        print(f"ERROR: {exc}")
        return 2
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text, end="")
    for error in report["errors"]:
        print(f"ERROR: {error}")
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
