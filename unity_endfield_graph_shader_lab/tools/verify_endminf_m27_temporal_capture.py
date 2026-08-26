#!/usr/bin/env python3
"""Fail-closed verifier for Endminf's captured M27 temporal IA packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CAPTURE = (
    REPO
    / "scratch/reverse_engineering/endfield_capture/20260826T162514Z"
)
OUTPUT = (
    REPO
    / "reports/assets/character_recovery/endminf_m27_temporal_capture_latest.json"
)
MESH = (
    REPO
    / "scratch/animestudio/endminf_m27_source_contract/fc_json/Mesh"
    / "S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.json"
)
EXPECTED_SESSION = "20260826T162514Z"
VS_IDENTITY = 0xC0266E7FAC0046C1
PS_IDENTITY = 0x92D80A93ADD9C714
R16_UINT = 57
SOURCE_VERTEX_COUNT = 29
SOURCE_INDEX_COUNT = 72
SEQUENCE_FRAMES = (
    2905, 2913, 2921, 2929, 2937, 2945, 2953, 2962,
    2970, 2978, 2987, 2995, 3003, 3011, 3019, 3027,
)
# The no-frame-generation dense comparison pins the 1,080-index burst peak to
# body phase 4.433333 s (source frame 381). Presented-frame deltas within this
# one capture session remain valid; the older frame-2905/4.50 assignment was a
# provisional owner-local label and shifted the whole replay 1.2167 s late.
PHASE_ANCHOR_FRAME = 2978
PHASE_ANCHOR_SECONDS = 4.433333
REQUIRED_CONSTANTS = {
    (0, 0): 82,
    (0, 1): 20,
    (0, 2): 16,
    (4, 0): 28,
    (4, 1): 106,
    (4, 2): 16,
    (4, 3): 31,
    (4, 4): 1,
}


class CaptureError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain one JSON object")
    return value


def is_m27_draw(draw: dict[str, Any]) -> bool:
    shaders = {row.get("stage"): row for row in draw.get("shaders", [])}
    return (
        draw.get("priorityShaderPair") is True
        and shaders.get(0, {}).get("identityHash") == VS_IDENTITY
        and shaders.get(4, {}).get("identityHash") == PS_IDENTITY
    )


def source_payloads() -> tuple[dict[str, Any], bytes]:
    mesh = load_json(MESH)
    require(mesh.get("m_VertexCount") == SOURCE_VERTEX_COUNT,
            "M27 source vertex count drifted")
    indices = mesh.get("m_Indices")
    require(isinstance(indices, list) and len(indices) == SOURCE_INDEX_COUNT,
            "M27 source index count drifted")
    return mesh, struct.pack("<" + "H" * len(indices), *indices)


def validate_constants(draw: dict[str, Any], frame: int) -> list[dict[str, Any]]:
    rows = {(row.get("stage"), row.get("slot")): row
            for row in draw.get("constantBuffers", [])}
    missing = sorted(set(REQUIRED_CONSTANTS) - set(rows))
    require(not missing, f"frame {frame} M27 draw is missing constants {missing}")
    result = []
    for key, minimum in REQUIRED_CONSTANTS.items():
        row = rows[key]
        require(row.get("rangeValid") is True and row.get("metadataValid") is True,
                f"frame {frame} M27 {key} range is invalid")
        payload = bytes.fromhex(row.get("dataHex", ""))
        require(len(payload) % 16 == 0 and len(payload) // 16 >= minimum,
                f"frame {frame} M27 {key} captured range is too short")
        result.append({
            "stage": key[0],
            "slot": key[1],
            "firstConstant": row.get("firstConstant"),
            "numConstants": row.get("numConstants"),
            "capturedConstants": len(payload) // 16,
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return result


def one_resource(rows: list[dict[str, Any]], kind: int, slot: int,
                 frame: int) -> dict[str, Any]:
    matches = [row for row in rows
               if row.get("captureKind") == kind and row.get("slot") == slot]
    require(len(matches) == 1,
            f"frame {frame} requires one IA kind {kind} slot {slot}; found {len(matches)}")
    row = matches[0]
    require(row.get("completed") is True and row.get("failure") == 0,
            f"frame {frame} IA kind {kind} slot {slot} was not read back")
    return row


def expanded_indices(source_indices: list[int], copies: int) -> bytes:
    values = [index + copy * SOURCE_VERTEX_COUNT
              for copy in range(copies) for index in source_indices]
    return struct.pack("<" + "H" * len(values), *values)


def validate_geometry(
    metadata: dict[str, Any], resources: bytes, draws: list[dict[str, Any]],
    mesh: dict[str, Any], frame: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = metadata.get("selectedResourceRecords", [])
    require(isinstance(rows, list), f"frame {frame} has no selected resources")
    vertex = one_resource(rows, 0, 0, frame)
    default_vertex = one_resource(rows, 0, 1, frame)
    index = one_resource(rows, 1, 0, frame)
    require(vertex.get("stride") in (60, 68),
            f"frame {frame} M27 vertex stride is unsupported")
    require(default_vertex.get("stride") == 0 and default_vertex.get("blobBytes") == 20,
            f"frame {frame} M27 slot-1 carrier drifted")
    require(index.get("stride") == 2 and index.get("format") == R16_UINT,
            f"frame {frame} M27 index binding is not R16_UINT")
    require(vertex.get("objectId") == index.get("objectId") and
            vertex.get("blobOffset") == index.get("blobOffset") and
            vertex.get("blobBytes") == index.get("blobBytes"),
            f"frame {frame} M27 vertex/index alias was not retained")
    blob_start = int(vertex["blobOffset"])
    blob_size = int(vertex["blobBytes"])
    require(blob_start >= 0 and blob_start + blob_size <= len(resources),
            f"frame {frame} M27 ring blob exceeds resources.bin")
    ring = resources[blob_start:blob_start + blob_size]
    uv0 = [struct.pack("<2f", *mesh["m_UV0"][offset:offset + 2])
           for offset in range(0, SOURCE_VERTEX_COUNT * 2, 2)]
    uv1 = [struct.pack("<2f", *mesh["m_UV1"][offset:offset + 2])
           for offset in range(0, SOURCE_VERTEX_COUNT * 2, 2)]
    stride = int(vertex["stride"])
    # Retail's two particle IA layouts retain the immutable source UV pairs at
    # different offsets.  The 60-byte expanded/instanced path stores them at
    # byte 28; the 68-byte mesh-particle path stores them at byte 44.
    uv_offset = 28 if stride == 60 else 44
    slices = []
    for draw in draws:
        count = int(draw.get("count", -1))
        require(count > 0 and count % SOURCE_INDEX_COUNT == 0,
                f"frame {frame} M27 index count {count} is not source-aligned")
        copies = count // SOURCE_INDEX_COUNT
        vertex_count = copies * SOURCE_VERTEX_COUNT
        index_start = int(index["byteOffset"]) + int(draw["start"]) * 2
        vertex_start = int(vertex["byteOffset"]) + int(draw["baseVertex"]) * stride
        index_payload = expanded_indices(mesh["m_Indices"], copies)
        vertex_size = vertex_count * stride
        require(index_start >= 0 and index_start + len(index_payload) <= len(ring),
                f"frame {frame} M27 index slice exceeds the retained ring")
        require(vertex_start >= 0 and vertex_start + vertex_size <= len(ring),
                f"frame {frame} M27 vertex slice exceeds the retained ring")
        require(ring[index_start:index_start + len(index_payload)] == index_payload,
                f"frame {frame} M27 index slice does not match the source mesh")
        for copy in range(copies):
            for source_vertex in range(SOURCE_VERTEX_COUNT):
                offset = (vertex_start +
                          (copy * SOURCE_VERTEX_COUNT + source_vertex) * stride +
                          uv_offset)
                require(ring[offset:offset + 8] == uv0[source_vertex] and
                        ring[offset + 8:offset + 16] == uv1[source_vertex],
                        f"frame {frame} M27 vertex UV signature drifted")
        vertex_payload = ring[vertex_start:vertex_start + vertex_size]
        slices.append({
            "indexCount": count,
            "startIndex": draw["start"],
            "baseVertex": draw["baseVertex"],
            "vertexCount": vertex_count,
            "vertexByteOffset": vertex_start,
            "indexByteOffset": index_start,
            "vertexSha256": hashlib.sha256(vertex_payload).hexdigest(),
            "indexSha256": hashlib.sha256(index_payload).hexdigest(),
            "constantBuffers": validate_constants(draw, frame),
        })
    return ({
        "vertexStride": stride,
        "vertexBufferByteOffset": vertex["byteOffset"],
        "indexBufferByteOffset": index["byteOffset"],
        "ringBlobOffset": blob_start,
        "ringBlobBytes": blob_size,
        "slot1Sha256": hashlib.sha256(
            resources[int(default_vertex["blobOffset"]):
                      int(default_vertex["blobOffset"]) + 20]).hexdigest(),
    }, slices)


def verify_session(capture: Path) -> dict[str, Any]:
    session = load_json(capture / "session.json")
    require(session.get("sessionId") == EXPECTED_SESSION,
            "M27 temporal session identity drifted")
    mesh, _ = source_payloads()
    frames = []
    total_draws = 0
    for frame in SEQUENCE_FRAMES:
        frame_root = capture / "graphics" / "frames" / str(frame)
        metadata_path = frame_root / "metadata.json"
        metadata = load_json(metadata_path)
        require(metadata.get("captureIncomplete") is not True and
                metadata.get("captureFailed") is not True,
                f"frame {frame} is incomplete or failed")
        draws = [row for row in metadata.get("drawRecords", [])
                 if isinstance(row, dict) and is_m27_draw(row)]
        row: dict[str, Any] = {
            "frame": frame,
            "phaseSeconds": round(
                PHASE_ANCHOR_SECONDS + (frame - PHASE_ANCHOR_FRAME) / 60.0, 6),
            "drawCount": len(draws),
            "metadataSha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        }
        if draws:
            resources_path = frame_root / metadata.get("resourcesFile", "resources.bin")
            resources = resources_path.read_bytes()
            binding, slices = validate_geometry(metadata, resources, draws, mesh, frame)
            row["binding"] = binding
            row["draws"] = slices
            total_draws += len(draws)
        else:
            require(frame == 2970,
                    f"frame {frame} unexpectedly has no exact M27 draw")
            row["binding"] = None
            row["draws"] = []
        frames.append(row)
    early = next(row for row in frames if row["frame"] == 2905)
    peak = next(row for row in frames if row["frame"] == 2978)
    require(early["drawCount"] == 4 and
            [row["indexCount"] for row in early["draws"]] == [72, 72, 72, 72] and
            early["binding"]["vertexStride"] == 68,
            "frame 2905 is not the exact four-crystal packet")
    require(peak["drawCount"] == 1 and peak["draws"][0]["indexCount"] == 1080 and
            peak["binding"]["vertexStride"] == 60,
            "frame 2978 is not the exact 15-crystal peak")
    return {
        "schema": "endfield.endminf-m27-temporal-capture.v1",
        "status": "validated",
        "sessionId": EXPECTED_SESSION,
        "captureRoot": str(capture.resolve()),
        "sourceMesh": str(MESH.resolve()),
        "sampleCount": len(frames),
        "drawCount": total_draws,
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = verify_session(args.capture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "sampleCount": report["sampleCount"],
        "drawCount": report["drawCount"],
        "output": str(args.output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
