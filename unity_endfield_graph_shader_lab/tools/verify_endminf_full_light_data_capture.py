#!/usr/bin/env python3
"""Verify the bounded active Endminf LightData prefix in a clean capture.

The retail constant-buffer allocation is reused.  Bytes after the six headers
and twelve active punctual records are therefore deliberately outside this
oracle; they are neither required to be zero nor included in any digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


FRAME = 1758
METADATA_SHA256 = "91f0d0bcac11b1123083e895c6bd9c6edb3620051dc389d60dbcad9c729ced9d"
ACTIVE_SHA256 = "50b6df32ad75ee88ceda711d7092b92ba909b35e09679195f4f213fe6767ef92"
INVARIANT_SHA256 = "7b50fb8b2af8658d1b853e9271b087e0899e1913036d9f639bb1ea84dcae5765"
VERTEX_SHADER = 12011068085959802841
PIXEL_SHADER = 12224473953367385681
FULLSCREEN_ORDINAL = 17
BUFFER_ID = 5304604128
FIRST_CONSTANT = 1344
BOUND_CONSTANTS = 2064
BUFFER_BYTES = 4 * 1024 * 1024
BLOB_OFFSET = 12_607_488
HEADER_VECTORS = 6
LIGHT_COUNT = 12
VECTORS_PER_LIGHT = 8
ACTIVE_BYTES = (HEADER_VECTORS + LIGHT_COUNT * VECTORS_PER_LIGHT) * 16
EXPECTED_SOURCE_ORDER = [7, 4, 2, 6, 10, 3, 9, 5, 8, 0, 11, 1]


class VerificationError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VerificationError(f"expected JSON object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def validate_summaries(session: Path) -> None:
    graphics = read_json(session / "graphics" / "summary.json")
    require(graphics.get("schema") == "endfieldCapture.graphicsSummary.v1",
            "graphics summary schema drift")
    require(graphics.get("runtimeMode") == "d3d11-proxy",
            "graphics runtime mode is not the admitted proxy observer")
    require(graphics.get("complete") is True, "graphics summary is incomplete")
    require(graphics.get("hooksInstalled") is True, "graphics hooks were not installed")
    require(graphics.get("attached") is True, "graphics provider was not attached")
    require(graphics.get("graphicsProfile") == "full", "graphics profile is not full")
    require(graphics.get("dropped") == 0, "graphics provider dropped events")
    require(graphics.get("sequenceAutomatic") is True, "graphics sequence was not automatic")
    require(graphics.get("quiescentCleanup") is True, "graphics cleanup was not quiescent")

    collected = read_json(session / "collected" / "summary.json")
    require(collected.get("schema") == "endfieldCapture.summary.v1",
            "collection summary schema drift")
    require(collected.get("complete") is True, "collection summary is incomplete")
    require(collected.get("dropped") == 0, "collector dropped records")
    require(collected.get("invalidRecords") == 0, "collector saw invalid records")
    require(collected.get("writerError") is False, "collector writer failed")


def select_binding(metadata: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    require(metadata.get("frame") == FRAME, f"expected frame {FRAME}")
    for key in (
        "drawRecordsTruncated",
        "dispatchRecordsTruncated",
        "resourceSelectionTruncated",
        "captureIncomplete",
        "captureFailed",
        "fullscreenResolverRecordsTruncated",
    ):
        require(metadata.get(key) is False, f"frame gate {key} is not false")
    require(metadata.get("droppedEvents") == 0, "frame dropped events")

    resolvers = [
        row
        for row in metadata.get("fullscreenResolvers", [])
        if isinstance(row, dict) and row.get("priorityDeferredRangeShape") is True
    ]
    require(len(resolvers) == 1, "expected one priority DeferredRangeShape resolver")
    resolver = resolvers[0]
    require(resolver.get("fullscreenOrdinal") == FULLSCREEN_ORDINAL, "resolver ordinal drift")
    shader_rows = [
        row for row in resolver.get("shaders", []) if isinstance(row, dict)
    ]
    require(len(shader_rows) == 2, "resolver shader record count drift")
    shaders = {
        row.get("stage"): row.get("identityHash")
        for row in shader_rows
    }
    require(len(shaders) == 2, "resolver shader stages are not unique")
    require(shaders == {0: VERTEX_SHADER, 4: PIXEL_SHADER}, "resolver shader identity drift")
    bindings = [
        row
        for row in resolver.get("psConstantBuffers", [])
        if isinstance(row, dict) and row.get("slot") == 5
    ]
    require(len(bindings) == 1, "expected one PS b5 binding")
    binding = bindings[0]
    require(binding.get("bufferId") == BUFFER_ID, "PS b5 buffer identity drift")
    require(binding.get("firstConstant") == FIRST_CONSTANT, "PS b5 range offset drift")
    require(binding.get("numConstants") == BOUND_CONSTANTS, "PS b5 range length drift")
    require(binding.get("byteWidth") == BUFFER_BYTES, "PS b5 allocation size drift")
    require(binding.get("rangeValid") is True, "PS b5 range is invalid")

    resources = [
        row
        for row in metadata.get("selectedResourceRecords", [])
        if isinstance(row, dict)
        and row.get("captureKind") == 2
        and row.get("objectId") == BUFFER_ID
        and row.get("stage") == 4
        and row.get("slot") == 0
    ]
    require(len(resources) == 1, "expected one retained PS b5 constant-buffer resource")
    resource = resources[0]
    require(resource.get("completed") is True, "constant-buffer readback is incomplete")
    require(resource.get("failure") == 0, "constant-buffer readback failed")
    require(resource.get("blobOffset") == BLOB_OFFSET, "constant-buffer blob offset drift")
    require(resource.get("blobBytes") == BUFFER_BYTES, "constant-buffer blob length drift")
    require(resource.get("byteSize") == BUFFER_BYTES, "constant-buffer byte size drift")
    return binding, resource


def extract_active_prefix(
    metadata: dict[str, Any], resources_path: Path, expected_sha256: str = ACTIVE_SHA256
) -> bytes:
    binding, resource = select_binding(metadata)
    active_offset = int(resource["blobOffset"]) + int(binding["firstConstant"]) * 16
    resource_end = int(resource["blobOffset"]) + int(resource["blobBytes"])
    require(active_offset + ACTIVE_BYTES <= resource_end, "active prefix exceeds retained resource")
    require(resources_path.stat().st_size >= active_offset + ACTIVE_BYTES, "resources.bin is truncated")
    with resources_path.open("rb") as stream:
        stream.seek(active_offset)
        active = stream.read(ACTIVE_BYTES)
    require(len(active) == ACTIVE_BYTES, "active prefix read was short")
    actual = sha256_bytes(active)
    require(actual == expected_sha256, f"active prefix hash mismatch: {actual}")
    return active


def invariant_bytes(active: bytes) -> bytes:
    words = struct.unpack(f"<{len(active) // 4}I", active)
    selected: list[int] = list(words[: HEADER_VECTORS * 4])
    for packed in range(LIGHT_COUNT):
        base = (HEADER_VECTORS + packed * VECTORS_PER_LIGHT) * 4
        selected.extend(words[base + 0 : base + 4])
        selected.append(words[base + 7])
        # Packed rows 0..2 are the only follower-mode-1 lights whose forward
        # depends on the live pose. Retain exact oct lanes for every
        # source-stable row so an encoder regression cannot pass the oracle.
        if packed >= 3:
            selected.extend(words[base + 8 : base + 10])
        selected.extend(words[base + 10 : base + 12])
        selected.extend(words[base + 12 : base + 32])
    return struct.pack(f"<{len(selected)}I", *selected)


def validate_source_identity(active: bytes, operator_lights_path: Path) -> None:
    payload = read_json(operator_lights_path)
    require(
        payload.get("schema") == "endfield.original-operator-lights.v1",
        "operator-light source schema drift",
    )
    validation = payload.get("validation")
    require(isinstance(validation, dict) and validation.get("ok") is True,
            "operator-light source validation is not successful")
    require(
        validation.get("actor_counts", {}).get("endminf") == LIGHT_COUNT,
        "operator-light validation does not admit 12 Endminf rows",
    )
    actors = payload.get("actors")
    require(isinstance(actors, dict), "operator-light actor table is malformed")
    actor = actors.get("endminf")
    require(isinstance(actor, dict), "Endminf operator-light actor entry is malformed")
    require(actor.get("count") == LIGHT_COUNT, "Endminf actor count drift")
    require(actor.get("group_name") == "light_overview", "Endminf light group identity drift")
    rows = actor.get("lights", [])
    require(len(rows) == LIGHT_COUNT, "operator-light source does not contain 12 Endminf rows")
    inverse_range_to_source: dict[int, int] = {}
    shadow_sources: set[int] = set()
    for source_index, row in enumerate(rows):
        require(isinstance(row, dict), f"operator-light source row {source_index} is malformed")
        require(row.get("index") == source_index, f"operator-light source row {source_index} index drift")
        require(row.get("light_type") in (0, 2), f"operator-light source row {source_index} has unsupported light type")
        require(row.get("shadow_type") in (0, 2), f"operator-light source row {source_index} has unsupported shadow type")
        if row.get("shadow_type") == 2:
            shadow_sources.add(source_index)
        source_range = struct.unpack(
            "<f", struct.pack("<f", float(row["range"]))
        )[0]
        inverse_bits = struct.unpack("<I", struct.pack("<f", 1.0 / source_range))[0]
        require(inverse_bits not in inverse_range_to_source, "source inverse ranges are not unique")
        inverse_range_to_source[inverse_bits] = source_index
    require(shadow_sources == {3, 11}, f"operator-light shadow source set drift: {sorted(shadow_sources)}")

    words = struct.unpack(f"<{len(active) // 4}I", active)
    source_order: list[int] = []
    for packed in range(LIGHT_COUNT):
        base = (HEADER_VECTORS + packed * VECTORS_PER_LIGHT) * 4
        inverse_bits = words[base + 7]
        require(inverse_bits in inverse_range_to_source, f"packed row {packed} has unknown inverse range")
        source_index = inverse_range_to_source[inverse_bits]
        source_order.append(source_index)
        row = rows[source_index]
        if int(row["light_type"]) == 0:
            expected_shadow = 40.0 if source_index == 3 else 41.0 if source_index == 11 else -1.0
            actual_shadow = struct.unpack("<f", struct.pack("<I", words[base + 12]))[0]
            require(actual_shadow == expected_shadow, f"source row {source_index} shadow slot mismatch")
        else:
            require(words[base + 11] == 0xFFFFFFFF, f"source row {source_index} point face0123 sentinel drift")
            require(words[base + 12] == 0x0000FFFF, f"source row {source_index} point face45 sentinel drift")
    require(source_order == EXPECTED_SOURCE_ORDER, f"packed source order drift: {source_order}")


def verify(session: Path, operator_lights_path: Path) -> dict[str, Any]:
    validate_summaries(session)
    frame_root = session / "graphics" / "frames" / str(FRAME)
    metadata_path = frame_root / "metadata.json"
    require(sha256_file(metadata_path) == METADATA_SHA256, "frame metadata hash drift")
    metadata = read_json(metadata_path)
    active = extract_active_prefix(metadata, frame_root / "resources.bin")
    invariant = invariant_bytes(active)
    require(len(invariant) == 1464, "invariant lane selection length drift")
    require(sha256_bytes(invariant) == INVARIANT_SHA256, "invariant lane digest drift")
    validate_source_identity(active, operator_lights_path)
    return {
        "schema": "endfield.endminf-full-light-data-capture.v1",
        "valid": True,
        "session": str(session),
        "frame": FRAME,
        "ownedBytes": ACTIVE_BYTES,
        "activeSha256": sha256_bytes(active),
        "invariantSha256": sha256_bytes(invariant),
        "packedSourceOrder": EXPECTED_SOURCE_ORDER,
        "captureTailOwned": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path)
    parser.add_argument("--operator-lights", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    session = (args.session or repo / "scratch/reverse_engineering/endfield_capture/20260828T121603Z").resolve()
    operator_lights = (args.operator_lights or repo / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/operator_lights.json").resolve()
    report = verify(session, operator_lights)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
