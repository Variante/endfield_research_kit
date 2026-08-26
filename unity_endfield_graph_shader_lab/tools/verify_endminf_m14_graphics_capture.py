#!/usr/bin/env python3
"""Validate and decode exact Endminf M14 draw constants from EndfieldCapture.

The verifier is intentionally tied to the pinned retail build and the exact
VS4914/PS4915 bytecode pair. It rejects pre-M14 recorder output, incomplete
GPU copies, truncated shader-addressable ranges, and implausible particle
draws. Particle index counts are dynamic: FrameAnalysis observed 1,098 indices
while the phase-matched peak capture observed 1,710.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import struct
from pathlib import Path


GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
TARGET_SHA256 = "a9726459d9ab90cf01d7536a4250315e85ebfe12da493ac16f7bad3b68e7df99"
M14_REFERENCE_INDEX_COUNT = 1_098
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

PARTICLE_VERTEX_STRIDE = 36
PARTICLE_UVS = ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))

# Base vertices distinguish every exact-pair emitter retained in frame 13175.
# The expected vectors are the PS b3/c4 uploads matched against the generated
# material closure. M31 has two one-quad draws with the same material state.
CAPTURED_BASEV2_TINT_WITNESSES = {
    4908: ("M_fx_endminm_gfx_22", "EC97B180E0A82AB7",
           (1.0, 0.4251311, 0.0975873, 1.0)),
    86: ("M_fx_endminm_gfx_43", "73D80B62F5BA886F",
         (1.0, 1.0, 1.0, 1.0)),
    1450: ("M_fx_endminm_gfx_31", "602883BD6BB1831B",
           (1.0, 0.5607878, 0.0976956, 1.0)),
    844: ("M_fx_endminm_gfx_40", "26EC2259AEC716E7",
          (0.7615293, 0.3865187, 0.2021150, 1.0)),
    1466: ("M_fx_endminm_gfx_39", "BF692EC36800069D",
           (0.7605246, 0.5119022, 0.2015562, 1.0)),
    54: ("M_fx_endminm_gfx_31", "602883BD6BB1831B",
         (1.0, 0.5607878, 0.0976956, 1.0)),
    3227: ("M_fx_endminm_gfx_14", "F6DCA5E6B2122169",
           (0.29275623, 0.17861338, 0.04641925, 1.0)),
    1482: ("M_fx_endminm_gfx_26", "364397B467C89F2E",
           (0.29275623, 0.17861338, 0.04641925, 1.0)),
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
    index_count = int(draw.get("count", -1))
    require(index_count >= M14_REFERENCE_INDEX_COUNT and index_count % 6 == 0,
            "M14 draw does not contain a plausible dynamic quad index count")
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
        "indexCount": index_count,
        "quadCount": index_count // 6,
        "referenceIndexCount": M14_REFERENCE_INDEX_COUNT,
        "startIndex": int(draw.get("start", -1)),
        "baseVertex": int(draw.get("baseVertex", -1)),
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


def decode_priority_pair_tint(draw: dict) -> dict:
    """Decode PS b3/c1 and c4 for any retained VS4914/PS4915 draw."""
    require(draw.get("priorityShaderPair") is True,
            "exact-pair tint draw is not priority retained")
    shaders = {int(row.get("stage", -1)): row for row in draw.get("shaders", [])
               if isinstance(row, dict)}
    require(int(shaders.get(0, {}).get("identityHash", -1)) == VS_IDENTITY and
            int(shaders.get(4, {}).get("identityHash", -1)) == PS_IDENTITY,
            "priority marker does not identify VS4914/PS4915")
    rows = [row for row in draw.get("constantBuffers", [])
            if isinstance(row, dict) and int(row.get("stage", -1)) == 4 and
            int(row.get("slot", -1)) == 3]
    require(len(rows) == 1, "exact-pair draw does not have one PS b3 range")
    binding = decode_binding(rows[0], 4, 3, 22, 22)
    base_vertex = int(draw.get("baseVertex", -1))
    result = {
        "indexCount": int(draw.get("count", -1)),
        "startIndex": int(draw.get("start", -1)),
        "baseVertex": base_vertex,
        "psPerMaterialC1": binding["float4"][1],
        "psTintColorC4": binding["float4"][4],
    }
    witness = CAPTURED_BASEV2_TINT_WITNESSES.get(base_vertex)
    if witness is not None:
        material_name, path_id, expected = witness
        actual = result["psTintColorC4"]
        require(math.dist(actual, expected) <= 1.0e-6,
                f"{material_name} PS b3/c4 no longer matches the captured tint")
        result.update({
            "material": material_name,
            "materialPathIdHex": path_id,
            "materialMatch": "generated-authored-Color-linear-upload",
        })
    return result


def _particle_quad(data: bytes, offset: int) -> tuple[float, float] | None:
    positions = []
    for vertex, expected_uv in enumerate(PARTICLE_UVS):
        row = offset + vertex * PARTICLE_VERTEX_STRIDE
        values = struct.unpack_from("<6fI2f", data, row)
        position = values[:3]
        normal = values[3:6]
        uv = values[7:9]
        if not all(math.isfinite(value) for value in position + normal + uv):
            return None
        # Stretch billboards can publish a shortened direction carrier as
        # their velocity approaches zero; finiteness plus canonical UV order
        # identifies the stream without incorrectly rejecting those rows.
        if uv != expected_uv:
            return None
        positions.append(position)
    width = math.dist(positions[0], positions[1])
    height = math.dist(positions[1], positions[2])
    return width, height


def decode_particle_geometry(frame_dir: Path, metadata: dict,
                             quad_count: int) -> dict | None:
    """Recover the expanded stock-Unity particle stream from resources.bin.

    The current recorder deduplicates a D3D11 buffer first observed through an
    SRV/UAV binding, so the shared IA resource is labelled kind 4/5 rather than
    kind 0. Its raw bytes remain complete. Locate the stream by its exact
    36-byte Position/Normal/packed-Color/UV ABI and canonical quad UV order.
    """
    rows = metadata.get("selectedResourceRecords")
    if rows is None:
        return None
    require(isinstance(rows, list), "selectedResourceRecords is not an array")
    resources_path = frame_dir / "resources.bin"
    try:
        resources = resources_path.read_bytes()
    except OSError as exc:
        raise CaptureError(f"cannot read {resources_path}: {exc}") from exc

    candidates = []
    for resource_index, row in enumerate(rows):
        if not isinstance(row, dict) or int(row.get("captureKind", -1)) not in (0, 4, 5):
            continue
        if row.get("completed") is not True or int(row.get("failure", -1)) != 0:
            continue
        blob_offset = int(row.get("blobOffset", -1))
        blob_bytes = int(row.get("blobBytes", -1))
        require(blob_offset >= 0 and blob_bytes >= 0 and
                blob_offset + blob_bytes <= len(resources),
                f"selected resource {resource_index} exceeds resources.bin")
        data = resources[blob_offset:blob_offset + blob_bytes]
        starts = {}
        limit = len(data) - PARTICLE_VERTEX_STRIDE * 4
        for offset in range(0, max(0, limit + 1), 4):
            dimensions = _particle_quad(data, offset)
            if dimensions is not None:
                starts[offset] = dimensions
        for offset in sorted(starts):
            if offset - PARTICLE_VERTEX_STRIDE * 4 in starts:
                continue
            run = 1
            while offset + run * PARTICLE_VERTEX_STRIDE * 4 in starts:
                run += 1
            if run >= quad_count:
                candidates.append((run - quad_count, resource_index, offset,
                                   run, starts, row))
    require(bool(candidates),
            "resources.bin contains no complete M14 36-byte particle-quad stream")
    _, resource_index, offset, run, starts, resource_row = min(candidates)
    widths = []
    heights = []
    ratios = []
    for index in range(quad_count):
        width, height = starts[offset + index * PARTICLE_VERTEX_STRIDE * 4]
        widths.append(width)
        heights.append(height)
        if width > 1.0e-8 and height > 1.0e-8:
            ratios.append(width / height)
    require(len(ratios) >= quad_count * 0.7,
            "M14 raw stream has too few non-degenerate expanded quads")
    median_ratio = statistics.median(ratios)
    require(1.85 <= median_ratio <= 2.15,
            f"M14 median expanded-quad aspect ratio {median_ratio:.6g} is not 2:1")
    return {
        "resourceIndex": resource_index,
        "captureKind": int(resource_row["captureKind"]),
        "blobOffset": int(resource_row["blobOffset"]),
        "streamByteOffset": offset,
        "vertexStride": PARTICLE_VERTEX_STRIDE,
        "contiguousQuadCount": run,
        "consumedQuadCount": quad_count,
        "nonDegenerateQuadCount": len(ratios),
        "medianRawWidth": statistics.median(widths),
        "medianRawHeight": statistics.median(heights),
        "medianAspectRatio": median_ratio,
        "minimumRawWidth": min(widths),
        "maximumRawWidth": max(widths),
        "minimumRawHeight": min(heights),
        "maximumRawHeight": max(heights),
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
    # The exact shader pair is shared by several particle emitters in this
    # frame. M14 is the largest priority-retained quad draw during its bounded
    # live window: 1,098 indices in FrameAnalysis and 1,710 at the captured
    # peak. Do not hardcode one instantaneous alive-particle count.
    priority_draws = [row for row in draws if isinstance(row, dict) and
                      row.get("priorityShaderPair") is True]
    plausible = [row for row in priority_draws
                 if int(row.get("count", -1)) >= M14_REFERENCE_INDEX_COUNT and
                 int(row.get("count", -1)) % 6 == 0]
    candidates = [] if not plausible else [max(
        plausible, key=lambda row: int(row.get("count", -1))
    )]
    if not candidates:
        return None
    decoded_draws = [decode_m14_draw(row) for row in candidates]
    priority_pair_tints = [decode_priority_pair_tint(row)
                           for row in priority_draws]
    for decoded_draw in decoded_draws:
        decoded_draw["rawParticleGeometry"] = decode_particle_geometry(
            frame_dir, metadata, decoded_draw["quadCount"]
        )
    return {
        "frame": int(metadata.get("frame", frame_dir.name)),
        "frameDirectory": str(frame_dir.resolve()),
        "metadataSha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        "priorityPairDrawCount": len(priority_pair_tints),
        "capturedLinearTintWitnessCount": sum(
            "material" in row for row in priority_pair_tints
        ),
        "priorityPairDraws": priority_pair_tints,
        "m14DrawCount": len(candidates),
        "m14Draws": decoded_draws,
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
