#!/usr/bin/env python3
"""Fail-closed verifier for the aggregate Endminf LitEffect capture sequence."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import verify_endminf_m27_temporal_capture as m27


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260826T162514Z"
OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_liteffect_temporal_capture_latest.json"
)
EXPECTED_SESSION = "20260826T162514Z"
VS_IDENTITY = 0xC0266E7FAC0046C1
PS_IDENTITY = 0x92D80A93ADD9C714
FRAME_MIN = 2721
FRAME_MAX = 3027
PHASE_ANCHOR_FRAME = 2978
PHASE_ANCHOR_SECONDS = 4.433333
EXPECTED_FRAMES = (
    2721, 2729, 2737, 2746, 2754, 2762, 2771, 2780, 2788, 2797,
    2805, 2813, 2822, 2831, 2839, 2847, 2855, 2864, 2872, 2880,
    2888, 2896, 2905, 2913, 2921, 2929, 2937, 2945, 2953, 2962,
    2970, 2978, 2987, 2995, 3003, 3011, 3019, 3027,
)
EXPECTED_FINGERPRINT_COUNTS = {
    2721: (3, 0), 2729: (2, 1), 2737: (2, 2),
    2746: (3, 3), 2754: (3, 3), 2762: (3, 3),
    2771: (3, 3), 2780: (3, 3), 2788: (3, 3),
    2797: (3, 3), 2805: (3, 3), 2813: (3, 3),
    2822: (3, 3), 2831: (3, 3), 2839: (3, 3),
    2847: (3, 3), 2855: (3, 3), 2864: (3, 2),
    2872: (3, 2), 2880: (3, 2), 2888: (4, 1),
    2896: (4, 0), 2905: (4, 0), 2913: (4, 0),
    2921: (4, 0), 2929: (4, 0), 2937: (4, 0),
    2945: (4, 0), 2953: (4, 0), 2962: (4, 0),
    2970: (0, 0), 2978: (1, 0), 2987: (1, 0),
    2995: (1, 0), 3003: (1, 0), 3011: (1, 0),
    3019: (1, 0), 3027: (1, 0),
}
R16_UINT = m27.R16_UINT
SOURCE_VERTEX_COUNT = m27.SOURCE_VERTEX_COUNT
SOURCE_INDEX_COUNT = m27.SOURCE_INDEX_COUNT
REQUIRED_CONSTANTS = m27.REQUIRED_CONSTANTS
MESH = m27.MESH
CaptureError = m27.CaptureError
require = m27.require
load_json = m27.load_json

BRIGHT_NAME = "bright_m01_or_m27"
LOW_NAME = "low_m38"
BRIGHT_VECTOR = (964.7226, 330.88165, 85.55083, 1.0)
LOW_VECTOR = (135.58704, 46.852066, 12.777836, 1.0)
BRIGHT_BYTES = struct.pack("<4f", *BRIGHT_VECTOR)
LOW_BYTES = struct.pack("<4f", *LOW_VECTOR)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc


def exact_pair(draw: dict[str, Any]) -> bool:
    shaders = draw.get("shaders", [])
    vs = [row for row in shaders if row.get("stage") == 0]
    ps = [row for row in shaders if row.get("stage") == 4]
    return (
        len(vs) == 1 and len(ps) == 1
        and vs[0].get("identityHash") == VS_IDENTITY
        and ps[0].get("identityHash") == PS_IDENTITY
    )


def classify_fingerprint(payload: bytes, frame: int, draw_index: int) -> str:
    if payload == BRIGHT_BYTES:
        return BRIGHT_NAME
    if payload == LOW_BYTES:
        return LOW_NAME
    raise CaptureError(
        f"frame {frame} draw {draw_index} PS b3 c29 has rejected fingerprint "
        f"{payload.hex()}"
    )


def validate_constants(
    draw: dict[str, Any], frame: int, draw_index: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_rows = draw.get("constantBuffers", [])
    require(isinstance(raw_rows, list) and len(raw_rows) == 8,
            f"frame {frame} draw {draw_index} requires exactly 8 constant buffers")
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    for row in raw_rows:
        key = (row.get("stage"), row.get("slot"))
        require(key not in rows,
                f"frame {frame} draw {draw_index} duplicates constant buffer {key}")
        rows[key] = row
    require(set(rows) == set(REQUIRED_CONSTANTS),
            f"frame {frame} draw {draw_index} constant-buffer set drifted: "
            f"{sorted(rows)}")

    result = []
    payloads: dict[tuple[int, int], bytes] = {}
    for key in sorted(REQUIRED_CONSTANTS):
        row = rows[key]
        require(row.get("rangeValid") is True and row.get("metadataValid") is True,
                f"frame {frame} draw {draw_index} constant buffer {key} is invalid")
        try:
            payload = bytes.fromhex(row.get("dataHex", ""))
        except (TypeError, ValueError) as exc:
            raise CaptureError(
                f"frame {frame} draw {draw_index} constant buffer {key} has invalid hex"
            ) from exc
        minimum = REQUIRED_CONSTANTS[key]
        require(len(payload) % 16 == 0 and len(payload) // 16 >= minimum,
                f"frame {frame} draw {draw_index} constant buffer {key} is incomplete")
        payloads[key] = payload
        result.append({
            "stage": key[0],
            "slot": key[1],
            "firstConstant": row.get("firstConstant"),
            "numConstants": row.get("numConstants"),
            "capturedConstants": len(payload) // 16,
            "sha256": sha256(payload),
        })

    b3 = payloads[(4, 3)]
    c29 = b3[29 * 16:30 * 16]
    require(len(c29) == 16,
            f"frame {frame} draw {draw_index} PS b3 c29 was not captured")
    fingerprint = classify_fingerprint(c29, frame, draw_index)
    return result, {
        "classification": fingerprint,
        "constants": list(struct.unpack("<4f", c29)),
        "dataHex": c29.hex(),
        "sha256": sha256(c29),
    }


def one_resource(
    rows: list[dict[str, Any]], kind: int, slot: int, frame: int,
) -> dict[str, Any]:
    return m27.one_resource(rows, kind, slot, frame)


def blob_slice(resources: bytes, row: dict[str, Any], label: str, frame: int) -> bytes:
    start = int(row.get("blobOffset", -1))
    size = int(row.get("blobBytes", -1))
    require(start >= 0 and size >= 0 and start + size <= len(resources),
            f"frame {frame} {label} blob exceeds resources.bin")
    return resources[start:start + size]


def uv_signature_matches(
    ring: bytes, vertex_start: int, copies: int, stride: int,
    mesh: dict[str, Any],
) -> bool:
    uv_offset = 28 if stride == 60 else 44
    uv0 = [struct.pack("<2f", *mesh["m_UV0"][offset:offset + 2])
           for offset in range(0, SOURCE_VERTEX_COUNT * 2, 2)]
    uv1 = [struct.pack("<2f", *mesh["m_UV1"][offset:offset + 2])
           for offset in range(0, SOURCE_VERTEX_COUNT * 2, 2)]
    for copy in range(copies):
        for source_vertex in range(SOURCE_VERTEX_COUNT):
            offset = (
                vertex_start
                + (copy * SOURCE_VERTEX_COUNT + source_vertex) * stride
                + uv_offset
            )
            if (ring[offset:offset + 8] != uv0[source_vertex]
                    or ring[offset + 8:offset + 16] != uv1[source_vertex]):
                return False
    return True


def validate_geometry(
    metadata: dict[str, Any], resources: bytes, draws: list[dict[str, Any]],
    mesh: dict[str, Any], frame: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = metadata.get("selectedResourceRecords", [])
    require(isinstance(rows, list), f"frame {frame} selected resources are missing")
    vertex = one_resource(rows, 0, 0, frame)
    slot1 = one_resource(rows, 0, 1, frame)
    index = one_resource(rows, 1, 0, frame)
    stride = int(vertex.get("stride", -1))
    require(stride in (60, 68),
            f"frame {frame} IA slot 0 vertex stride {stride} is unsupported")
    require(slot1.get("stride") == 0 and slot1.get("blobBytes") == 20,
            f"frame {frame} IA slot 1 carrier is incomplete")
    require(index.get("stride") == 2 and index.get("format") == R16_UINT,
            f"frame {frame} index binding is not R16_UINT")
    require(vertex.get("objectId") == index.get("objectId")
            and vertex.get("blobOffset") == index.get("blobOffset")
            and vertex.get("blobBytes") == index.get("blobBytes"),
            f"frame {frame} retained IA slot 0/index ring alias drifted")

    ring = blob_slice(resources, vertex, "IA ring", frame)
    slot1_payload = blob_slice(resources, slot1, "IA slot 1", frame)
    slices = []
    source_indices = mesh["m_Indices"]
    for draw_index, draw in enumerate(draws):
        count = int(draw.get("count", -1))
        require(count > 0 and count % SOURCE_INDEX_COUNT == 0,
                f"frame {frame} draw {draw_index} index count {count} is not divisible by 72")
        copies = count // SOURCE_INDEX_COUNT
        vertex_count = copies * SOURCE_VERTEX_COUNT
        index_start = int(index.get("byteOffset", -1)) + int(draw.get("start", -1)) * 2
        vertex_start = (
            int(vertex.get("byteOffset", -1))
            + int(draw.get("baseVertex", -1)) * stride
        )
        expected_indices = m27.expanded_indices(source_indices, copies)
        vertex_size = vertex_count * stride
        require(index_start >= 0 and index_start + len(expected_indices) <= len(ring),
                f"frame {frame} draw {draw_index} index slice exceeds IA ring")
        require(vertex_start >= 0 and vertex_start + vertex_size <= len(ring),
                f"frame {frame} draw {draw_index} exact vertex slice exceeds IA ring")
        actual_indices = ring[index_start:index_start + len(expected_indices)]
        require(actual_indices == expected_indices,
                f"frame {frame} draw {draw_index} indices do not repeat source topology")
        vertex_payload = ring[vertex_start:vertex_start + vertex_size]
        constant_buffers, fingerprint = validate_constants(draw, frame, draw_index)
        slices.append({
            "drawIndex": draw_index,
            "indexCount": count,
            "startIndex": draw.get("start"),
            "baseVertex": draw.get("baseVertex"),
            "copies": copies,
            "vertexCount": vertex_count,
            "vertexByteOffset": vertex_start,
            "vertexBytes": vertex_size,
            "vertexSha256": sha256(vertex_payload),
            "indexByteOffset": index_start,
            "indexBytes": len(actual_indices),
            "indexSha256": sha256(actual_indices),
            "sourceUvSignature": uv_signature_matches(
                ring, vertex_start, copies, stride, mesh),
            "psB3C29": fingerprint,
            "constantBuffers": constant_buffers,
        })
    return ({
        "vertexStride": stride,
        "vertexBufferByteOffset": vertex.get("byteOffset"),
        "indexBufferByteOffset": index.get("byteOffset"),
        "ringBlobOffset": vertex.get("blobOffset"),
        "ringBlobBytes": len(ring),
        "ringSha256": sha256(ring),
        "slot1BlobOffset": slot1.get("blobOffset"),
        "slot1Bytes": len(slot1_payload),
        "slot1Sha256": sha256(slot1_payload),
        "indexFormat": R16_UINT,
    }, slices)


def discover_frames(capture: Path) -> tuple[int, ...]:
    root = capture / "graphics" / "frames"
    try:
        frames = tuple(sorted(
            int(path.name) for path in root.iterdir()
            if path.is_dir() and path.name.isdecimal()
            and FRAME_MIN <= int(path.name) <= FRAME_MAX
        ))
    except OSError as exc:
        raise CaptureError(f"cannot scan captured frame directories in {root}: {exc}") from exc
    require(frames == EXPECTED_FRAMES,
            f"captured frame directory set drifted: expected {EXPECTED_FRAMES}, got {frames}")
    return frames


def phase_name(frame: int) -> str:
    if frame < 2970:
        return "early_m01_m38_aggregate"
    if frame == 2970:
        return "zero_transition"
    return "late_m27_single_draw"


def enforce_phase_structure(frames: list[dict[str, Any]]) -> None:
    require(tuple(row["frame"] for row in frames) == EXPECTED_FRAMES,
            "reported temporal frame order drifted")
    for row in frames:
        frame = row["frame"]
        counts = row["fingerprintCounts"]
        actual = (counts[BRIGHT_NAME], counts[LOW_NAME])
        require(actual == EXPECTED_FINGERPRINT_COUNTS[frame],
                f"frame {frame} aggregate fingerprint counts drifted: {actual}")
        require(row["phase"] == phase_name(frame),
                f"frame {frame} phase label drifted")
        if frame < 2970:
            require(row["drawCount"] > 1,
                    f"frame {frame} is not an aggregate M01/M38 packet")
        elif frame == 2970:
            require(row["drawCount"] == 0,
                    "frame 2970 must contain zero exact-pair draws")
        else:
            require(row["drawCount"] == 1 and actual == (1, 0),
                    f"frame {frame} must contain one bright M27 draw")


def verify_session(capture: Path) -> dict[str, Any]:
    session = load_json(capture / "session.json")
    require(session.get("sessionId") == EXPECTED_SESSION,
            "LitEffect temporal session identity drifted")
    mesh, source_index_payload = m27.source_payloads()
    source_mesh_payload = read_bytes(MESH)
    frames = []

    for frame in discover_frames(capture):
        frame_root = capture / "graphics" / "frames" / str(frame)
        metadata_path = frame_root / "metadata.json"
        metadata_payload = read_bytes(metadata_path)
        metadata = load_json(metadata_path)
        require(metadata.get("captureIncomplete") is not True
                and metadata.get("captureFailed") is not True,
                f"frame {frame} capture is incomplete or failed")
        draw_records = metadata.get("drawRecords", [])
        require(isinstance(draw_records, list), f"frame {frame} draw records are missing")
        draws = [draw for draw in draw_records
                 if isinstance(draw, dict) and exact_pair(draw)]
        row: dict[str, Any] = {
            "frame": frame,
            "phaseSeconds": round(
                PHASE_ANCHOR_SECONDS + (frame - PHASE_ANCHOR_FRAME) / 60.0, 6),
            "phase": phase_name(frame),
            "drawCount": len(draws),
            "fingerprintCounts": {BRIGHT_NAME: 0, LOW_NAME: 0},
            "metadataSha256": sha256(metadata_payload),
            "binding": None,
            "draws": [],
        }
        if draws:
            resources_path = frame_root / metadata.get("resourcesFile", "resources.bin")
            resources = read_bytes(resources_path)
            binding, slices = validate_geometry(metadata, resources, draws, mesh, frame)
            for draw in slices:
                row["fingerprintCounts"][draw["psB3C29"]["classification"]] += 1
            row["resourcesFile"] = resources_path.name
            row["resourcesBytes"] = len(resources)
            row["resourcesSha256"] = sha256(resources)
            row["binding"] = binding
            row["draws"] = slices
        frames.append(row)

    enforce_phase_structure(frames)
    all_draws = [draw for frame in frames for draw in frame["draws"]]
    bright_count = sum(
        frame["fingerprintCounts"][BRIGHT_NAME] for frame in frames)
    low_count = sum(frame["fingerprintCounts"][LOW_NAME] for frame in frames)
    uv_true = sum(draw["sourceUvSignature"] is True for draw in all_draws)
    return {
        "schema": "endfield.endminf-liteffect-temporal-capture.v1",
        "status": "validated",
        "sessionId": EXPECTED_SESSION,
        "captureRoot": str(capture.resolve()),
        "sampleCount": len(frames),
        "drawCount": len(all_draws),
        "frameRange": {"first": FRAME_MIN, "last": FRAME_MAX},
        "shaderPair": {
            "vertexIdentity": f"0x{VS_IDENTITY:016X}",
            "pixelIdentity": f"0x{PS_IDENTITY:016X}",
        },
        "sourceMesh": {
            "path": str(MESH.resolve()),
            "sha256": sha256(source_mesh_payload),
            "vertexCount": SOURCE_VERTEX_COUNT,
            "indexCount": SOURCE_INDEX_COUNT,
            "indexFormat": "R16_UINT",
            "indexDataHex": source_index_payload.hex(),
            "indexSha256": sha256(source_index_payload),
        },
        "psB3C29Fingerprints": {
            BRIGHT_NAME: {
                "constants": list(struct.unpack("<4f", BRIGHT_BYTES)),
                "dataHex": BRIGHT_BYTES.hex(),
                "sha256": sha256(BRIGHT_BYTES),
            },
            LOW_NAME: {
                "constants": list(struct.unpack("<4f", LOW_BYTES)),
                "dataHex": LOW_BYTES.hex(),
                "sha256": sha256(LOW_BYTES),
            },
        },
        "requiredConstantBuffers": [
            {"stage": key[0], "slot": key[1], "minimumConstants": minimum}
            for key, minimum in sorted(REQUIRED_CONSTANTS.items())
        ],
        "counts": {
            "frames": len(frames),
            "draws": len(all_draws),
            "brightM01OrM27Draws": bright_count,
            "lowM38Draws": low_count,
            "sourceUvSignatureTrue": uv_true,
            "sourceUvSignatureFalse": len(all_draws) - uv_true,
            "sourceMeshCopies": sum(draw["copies"] for draw in all_draws),
            "indices": sum(draw["indexCount"] for draw in all_draws),
            "vertices": sum(draw["vertexCount"] for draw in all_draws),
        },
        "phases": {
            "earlyM01M38Aggregate": {"firstFrame": 2721, "lastFrame": 2962},
            "zeroTransition": {"frame": 2970},
            "lateBrightM27SingleDraw": {"firstFrame": 2978, "lastFrame": 3027},
        },
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
        "schema": report["schema"],
        "counts": report["counts"],
        "output": str(args.output),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
