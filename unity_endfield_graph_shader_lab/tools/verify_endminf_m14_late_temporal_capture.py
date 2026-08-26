#!/usr/bin/env python3
"""Fail-closed verifier for Endminf's nine late exact M14 IA packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260826T162514Z"
OUTPUT = (
    REPO
    / "reports/assets/character_recovery/endminf_m14_late_temporal_capture_latest.json"
)
EXPECTED_SESSION = "20260826T162514Z"
EXPECTED_GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
EXPECTED_TARGET_SHA256 = (
    "a9726459d9ab90cf01d7536a4250315e85ebfe12da493ac16f7bad3b68e7df99"
)
VS_IDENTITY = 0x62A5CE6C09171DE9
PS_IDENTITY = 0x5558DEDDB1EE6188
EXPECTED_TINT = (0.2927562, 0.1786134, 0.04641925, 1.0)
TINT_TOLERANCE = 1.0e-6
VERTEX_STRIDE = 36
R16_UINT = 57
SEQUENCE = (
    (2978, 1872),
    (2987, 2898),
    (2995, 2898),
    (3003, 2874),
    (3011, 2628),
    (3019, 2328),
    (3027, 2058),
    (3035, 1782),
    (3043, 1584),
)
PHASE_ANCHOR_FRAME = 2978
PHASE_ANCHOR_SECONDS = 4.433333
LATE_TEXTURE_OMISSION_FRAMES = frozenset((3035, 3043))
TEXTURE_REUSE_FRAME = 2978
PINNED_VERTEX_RING_BYTE_OFFSET = 930320
LATE_INDEX_SLICE_OFFSETS = {3035: 975644, 3043: 968336}
REQUIRED_CONSTANTS = {
    (0, 0): 16,
    (0, 1): 82,
    (0, 2): 104,
    (0, 3): 16,
    (0, 4): 10,
    (4, 0): 28,
    (4, 1): 106,
    (4, 2): 16,
    (4, 3): 32,
}
TEXTURE_DESCRIPTORS = {
    0: (99, 1024, 1024),
    1: (83, 1024, 1024),
    2: (83, 1024, 1024),
    3: (99, 128, 128),
}
PARTICLE_UVS = ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))


class CaptureError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain one JSON object")
    return value


def shader_pair_matches(draw: dict[str, Any]) -> bool:
    shaders = {row.get("stage"): row for row in draw.get("shaders", [])
               if isinstance(row, dict)}
    return (
        draw.get("priorityShaderPair") is True
        and shaders.get(0, {}).get("identityHash") == VS_IDENTITY
        and shaders.get(4, {}).get("identityHash") == PS_IDENTITY
    )


def constant_rows(draw: dict[str, Any], frame: int) -> dict[tuple[int, int], dict[str, Any]]:
    source = draw.get("constantBuffers")
    require(isinstance(source, list), f"frame {frame} M14 has no constantBuffers")
    require(len(source) == len(REQUIRED_CONSTANTS),
            f"frame {frame} M14 must retain exactly all nine constant buffers")
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    for row in source:
        require(isinstance(row, dict),
                f"frame {frame} M14 constantBuffers contains a non-object")
        key = (int(row.get("stage", -1)), int(row.get("slot", -1)))
        require(key not in rows, f"frame {frame} M14 repeats constant buffer {key}")
        rows[key] = row
    missing = sorted(set(REQUIRED_CONSTANTS) - set(rows))
    extra = sorted(set(rows) - set(REQUIRED_CONSTANTS))
    require(not missing and not extra,
            f"frame {frame} M14 constant-buffer set drifted; missing={missing}, extra={extra}")
    return rows


def decode_payload(row: dict[str, Any], key: tuple[int, int], frame: int) -> bytes:
    label = f"frame {frame} M14 stage {key[0]} b{key[1]}"
    require(row.get("rangeValid") is True and row.get("metadataValid") is True,
            f"{label} range is invalid")
    try:
        payload = bytes.fromhex(row.get("dataHex", ""))
    except ValueError as exc:
        raise CaptureError(f"{label} payload is malformed: {exc}") from exc
    require(len(payload) % 16 == 0, f"{label} payload is not float4-aligned")
    captured = len(payload) // 16
    require(captured >= REQUIRED_CONSTANTS[key],
            f"{label} retained {captured} vectors; requires {REQUIRED_CONSTANTS[key]}")
    require(int(row.get("capturedConstants", captured)) == captured,
            f"{label} capturedConstants disagrees with dataHex")
    require(int(row.get("numConstants", -1)) >= captured,
            f"{label} declared range is shorter than its payload")
    return payload


def draw_tint(draw: dict[str, Any], frame: int) -> tuple[float, float, float, float]:
    rows = constant_rows(draw, frame)
    payload = decode_payload(rows[(4, 3)], (4, 3), frame)
    return struct.unpack_from("<4f", payload, 4 * 16)


def select_draw(metadata: dict[str, Any], frame: int, expected_count: int) -> dict[str, Any]:
    pair = [row for row in metadata.get("drawRecords", [])
            if isinstance(row, dict) and shader_pair_matches(row)]
    tinted = []
    for draw in pair:
        tint = draw_tint(draw, frame)
        if math.dist(tint, EXPECTED_TINT) <= TINT_TOLERANCE:
            tinted.append(draw)
    large = [row for row in tinted if int(row.get("count", -1)) >= min(
        count for _, count in SEQUENCE)]
    require(len(large) == 1,
            f"frame {frame} must contain one uniquely large tint-pinned M14 draw; "
            f"found {len(large)}")
    draw = large[0]
    require(int(draw.get("count", -1)) == expected_count,
            f"frame {frame} M14 index count is {draw.get('count')}; expected {expected_count}")
    require(draw.get("indexedInstanced") is True and
            int(draw.get("instanceCount", -1)) == 1 and
            int(draw.get("startInstance", -1)) == 0,
            f"frame {frame} M14 draw ABI drifted")
    require(expected_count % 6 == 0, f"frame {frame} M14 index count is not quad-aligned")
    return draw


def validate_constants(draw: dict[str, Any], frame: int) -> list[dict[str, Any]]:
    rows = constant_rows(draw, frame)
    result = []
    for key in REQUIRED_CONSTANTS:
        payload = decode_payload(rows[key], key, frame)
        result.append({
            "stage": key[0],
            "slot": key[1],
            "firstConstant": rows[key].get("firstConstant"),
            "numConstants": rows[key].get("numConstants"),
            "capturedConstants": len(payload) // 16,
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return result


def one_resource(rows: list[dict[str, Any]], kind: int, slot: int,
                 frame: int) -> dict[str, Any]:
    matches = [row for row in rows
               if isinstance(row, dict) and row.get("captureKind") == kind
               and row.get("slot") == slot]
    require(len(matches) == 1,
            f"frame {frame} requires one IA kind {kind} slot {slot}; found {len(matches)}")
    row = matches[0]
    require(row.get("completed") is True and int(row.get("failure", -1)) == 0,
            f"frame {frame} IA kind {kind} slot {slot} was not read back")
    return row


def one_backing_resource(rows: list[dict[str, Any]], frame: int) -> dict[str, Any]:
    matches = [row for row in rows if isinstance(row, dict)
               and row.get("captureKind") == 4 and row.get("slot") == 0]
    require(len(matches) == 1,
            f"frame {frame} requires one retained IA backing ring; found {len(matches)}")
    row = matches[0]
    require(row.get("completed") is True and int(row.get("failure", -1)) == 0,
            f"frame {frame} retained IA backing ring was not read back")
    return row


def canonical_indices(quad_count: int) -> bytes:
    values: list[int] = []
    for quad in range(quad_count):
        base = quad * 4
        values.extend((base, base + 1, base + 2, base, base + 2, base + 3))
    return struct.pack("<" + "H" * len(values), *values)


def quad_is_canonical(data: bytes, offset: int) -> bool:
    if offset < 0 or offset + VERTEX_STRIDE * 4 > len(data):
        return False
    for vertex, expected_uv in enumerate(PARTICLE_UVS):
        row = offset + vertex * VERTEX_STRIDE
        values = struct.unpack_from("<6fI2f", data, row)
        if not all(math.isfinite(value) for value in values[:6] + values[7:9]):
            return False
        if values[7:9] != expected_uv:
            return False
    return True


def large_stream_starts(ring: bytes, minimum_quads: int) -> list[tuple[int, int]]:
    """Find canonical runs efficiently from their first packed UV pair."""
    needle = struct.pack("<2f", 0.0, 1.0)
    starts: set[int] = set()
    cursor = 0
    while True:
        found = ring.find(needle, cursor)
        if found < 0:
            break
        offset = found - 28
        if quad_is_canonical(ring, offset):
            starts.add(offset)
        cursor = found + 1
    runs = []
    quad_bytes = VERTEX_STRIDE * 4
    for offset in sorted(starts):
        if offset - quad_bytes in starts:
            continue
        count = 1
        while offset + count * quad_bytes in starts:
            count += 1
        if count >= minimum_quads:
            runs.append((offset, count))
    return runs


def validate_geometry(metadata: dict[str, Any], resources: bytes,
                      draw: dict[str, Any], frame: int) -> dict[str, Any]:
    rows = metadata.get("selectedResourceRecords")
    require(isinstance(rows, list), f"frame {frame} has no selectedResourceRecords")
    vertex_rows = [row for row in rows if isinstance(row, dict)
                   and row.get("captureKind") == 0 and row.get("slot") == 0]
    index_rows = [row for row in rows if isinstance(row, dict)
                  and row.get("captureKind") == 1 and row.get("slot") == 0]
    binding_metadata_status = "captured_complete"
    if vertex_rows or index_rows:
        vertex = one_resource(rows, 0, 0, frame)
        index = one_resource(rows, 1, 0, frame)
        require(index.get("stride") == 2 and index.get("format") == R16_UINT,
                f"frame {frame} M14 index binding is not R16_UINT")
        require(vertex.get("objectId") == index.get("objectId") and
                vertex.get("blobOffset") == index.get("blobOffset") and
                vertex.get("blobBytes") == index.get("blobBytes"),
                f"frame {frame} M14 IA vertex/index ring alias was not retained")
        vertex_binding_offset = int(vertex.get("byteOffset", -1))
        index_binding_offset = int(index.get("byteOffset", -1))
    else:
        require(frame in LATE_TEXTURE_OMISSION_FRAMES,
                f"frame {frame} unexpectedly omits IA binding records")
        vertex = one_backing_resource(rows, frame)
        index = vertex
        require(int(draw.get("start", -1)) == 0,
                f"frame {frame} omitted IA metadata with a nonzero startIndex")
        vertex_binding_offset = PINNED_VERTEX_RING_BYTE_OFFSET
        index_binding_offset = LATE_INDEX_SLICE_OFFSETS[frame]
        binding_metadata_status = "omitted_exact_slices_content_pinned"
    blob_offset = int(vertex.get("blobOffset", -1))
    blob_bytes = int(vertex.get("blobBytes", -1))
    require(blob_offset >= 0 and blob_bytes > 0 and
            blob_offset + blob_bytes <= len(resources),
            f"frame {frame} M14 IA ring exceeds resources.bin")
    ring = resources[blob_offset:blob_offset + blob_bytes]
    quad_count = int(draw["count"]) // 6
    vertex_offset = vertex_binding_offset + int(draw.get("baseVertex", -1)) * VERTEX_STRIDE
    vertex_bytes = quad_count * 4 * VERTEX_STRIDE
    index_offset = index_binding_offset + int(draw.get("start", -1)) * 2
    expected_indices = canonical_indices(quad_count)
    require(vertex_offset >= 0 and vertex_offset + vertex_bytes <= len(ring),
            f"frame {frame} M14 effective vertex slice exceeds the retained IA ring")
    require(index_offset >= 0 and index_offset + len(expected_indices) <= len(ring),
            f"frame {frame} M14 effective index slice exceeds the retained IA ring")
    for quad in range(quad_count):
        require(quad_is_canonical(ring, vertex_offset + quad * 4 * VERTEX_STRIDE),
                f"frame {frame} M14 expanded quad {quad} is not canonical 36-byte IA data")
    require(ring[index_offset:index_offset + len(expected_indices)] == expected_indices,
            f"frame {frame} M14 effective index slice is not the canonical quad topology")
    large_runs = large_stream_starts(ring, quad_count)
    require(len(large_runs) == 1 and large_runs[0][0] == vertex_offset and
            large_runs[0][1] >= quad_count,
            f"frame {frame} M14 stream is not uniquely large at the effective "
            f"IA offset: {large_runs}")
    vertex_payload = ring[vertex_offset:vertex_offset + vertex_bytes]
    return {
        "vertexStride": VERTEX_STRIDE,
        "quadCount": quad_count,
        "vertexCount": quad_count * 4,
        "indexCount": int(draw["count"]),
        "ringBlobOffset": blob_offset,
        "ringBlobBytes": blob_bytes,
        "bindingMetadataStatus": binding_metadata_status,
        "vertexBindingByteOffset": vertex_binding_offset,
        "indexBindingByteOffset": index_binding_offset,
        "effectiveVertexByteOffset": vertex_offset,
        "effectiveIndexByteOffset": index_offset,
        "vertexByteLength": len(vertex_payload),
        "indexByteLength": len(expected_indices),
        "vertexSha256": hashlib.sha256(vertex_payload).hexdigest(),
        "indexSha256": hashlib.sha256(expected_indices).hexdigest(),
        "uniqueLargeExpandedQuadStream": True,
        "contiguousExpandedQuadCount": large_runs[0][1],
    }


def texture_rows(metadata: dict[str, Any], frame: int) -> dict[int, dict[str, Any]]:
    selected = metadata.get("selectedResourceRecords", [])
    require(isinstance(selected, list), f"frame {frame} has no selected resources")
    result: dict[int, dict[str, Any]] = {}
    for slot, descriptor in TEXTURE_DESCRIPTORS.items():
        fmt, width, height = descriptor
        matches = [row for row in selected if isinstance(row, dict)
                   and row.get("captureKind") == 3 and row.get("slot") == slot
                   and row.get("format") == fmt and row.get("width") == width
                   and row.get("height") == height]
        require(len(matches) <= 1,
                f"frame {frame} M14 texture t{slot} descriptor is ambiguous")
        if matches:
            result[slot] = matches[0]
    return result


def validate_textures(metadata: dict[str, Any], resources: bytes, frame: int,
                      expected_hashes: dict[int, str] | None) -> tuple[dict[str, Any], dict[int, str] | None]:
    rows = texture_rows(metadata, frame)
    expected_slots = set(TEXTURE_DESCRIPTORS)
    missing = sorted(expected_slots - set(rows))
    if frame in LATE_TEXTURE_OMISSION_FRAMES:
        require(missing == sorted(expected_slots),
                f"frame {frame} has a partial/unexpected M14 texture omission: {missing}")
        require(expected_hashes is not None,
                f"frame {frame} cannot reuse textures before a complete source frame")
        return ({
            "status": "omitted_reuse_immutable",
            "omittedSlots": missing,
            "reuseFromFrame": TEXTURE_REUSE_FRAME,
            "reusedSha256BySlot": {str(k): v for k, v in expected_hashes.items()},
        }, expected_hashes)
    require(not missing, f"frame {frame} is missing M14 texture slots {missing}")
    hashes: dict[int, str] = {}
    records = []
    for slot in sorted(rows):
        row = rows[slot]
        require(row.get("completed") is True and int(row.get("failure", -1)) == 0,
                f"frame {frame} M14 texture t{slot} was not read back")
        offset = int(row.get("blobOffset", -1))
        size = int(row.get("blobBytes", -1))
        require(offset >= 0 and size > 0 and offset + size <= len(resources),
                f"frame {frame} M14 texture t{slot} exceeds resources.bin")
        digest = hashlib.sha256(resources[offset:offset + size]).hexdigest()
        hashes[slot] = digest
        records.append({
            "slot": slot,
            "format": row["format"],
            "width": row["width"],
            "height": row["height"],
            "blobBytes": size,
            "sha256": digest,
        })
    if expected_hashes is not None:
        require(hashes == expected_hashes,
                f"frame {frame} M14 immutable texture payloads drifted")
    return ({"status": "captured_complete", "records": records}, hashes)


def verify_session(capture: Path) -> dict[str, Any]:
    session = load_json(capture / "session.json")
    require(session.get("schema") == "endfieldCapture.session.v1",
            "M14 temporal session schema is unsupported")
    require(session.get("sessionId") == EXPECTED_SESSION,
            "M14 temporal session identity drifted")
    require(session.get("gameBuild") == EXPECTED_GAME_BUILD,
            "M14 temporal game build drifted")
    require(session.get("targetSha256") == EXPECTED_TARGET_SHA256,
            "M14 temporal Endfield.exe hash drifted")
    require(session.get("evidenceLabel") == "forced-d3d11" and
            session.get("graphicsProfile") in ("targeted", "full"),
            "M14 temporal session is not range-bearing forced-D3D11 evidence")

    frames = []
    texture_hashes: dict[int, str] | None = None
    for frame, expected_count in SEQUENCE:
        frame_root = capture / "graphics" / "frames" / str(frame)
        metadata_path = frame_root / "metadata.json"
        metadata = load_json(metadata_path)
        require(metadata.get("schema") == "endfieldCapture.graphicsFrame.v1",
                f"frame {frame} graphics schema is unsupported")
        require(metadata.get("captureIncomplete") is False and
                metadata.get("captureFailed") is False,
                f"frame {frame} is incomplete or failed")
        draw = select_draw(metadata, frame, expected_count)
        resources_path = frame_root / metadata.get("resourcesFile", "resources.bin")
        try:
            resources = resources_path.read_bytes()
        except OSError as exc:
            raise CaptureError(f"cannot read {resources_path}: {exc}") from exc
        textures, current_hashes = validate_textures(
            metadata, resources, frame, texture_hashes)
        if frame == TEXTURE_REUSE_FRAME:
            texture_hashes = current_hashes
        geometry = validate_geometry(metadata, resources, draw, frame)
        tint = draw_tint(draw, frame)
        frames.append({
            "frame": frame,
            "phaseSeconds": round(
                PHASE_ANCHOR_SECONDS + (frame - PHASE_ANCHOR_FRAME) / 60.0, 6),
            "metadataSha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
            "shaderPair": {
                "vertex": f"0x{VS_IDENTITY:016X}",
                "pixel": f"0x{PS_IDENTITY:016X}",
            },
            "psB3C4Tint": list(tint),
            "constantBuffers": validate_constants(draw, frame),
            "geometry": geometry,
            "textures": textures,
        })
    require(texture_hashes is not None, "M14 immutable texture source was not retained")
    return {
        "schema": "endfield.endminf-m14-late-temporal-capture.v1",
        "status": "validated",
        "sessionId": EXPECTED_SESSION,
        "captureRoot": str(capture.resolve()),
        "sampleCount": len(frames),
        "packetCount": len(frames),
        "totalIndexCount": sum(row["geometry"]["indexCount"] for row in frames),
        "totalQuadCount": sum(row["geometry"]["quadCount"] for row in frames),
        "constantBufferCountPerPacket": len(REQUIRED_CONSTANTS),
        "textureReuseSourceFrame": TEXTURE_REUSE_FRAME,
        "textureOmissionFrames": sorted(LATE_TEXTURE_OMISSION_FRAMES),
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        report = verify_session(args.capture.resolve())
    except (CaptureError, OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "packetCount": report["packetCount"],
        "totalIndexCount": report["totalIndexCount"],
        "output": str(args.output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
