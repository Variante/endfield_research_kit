#!/usr/bin/env python3
"""Convert one collected EndfieldCapture M27 draw into partial live evidence.

The converter authenticates the collector inventory and every packaged file,
then selects exactly one synchronized retail M27 draw.  It emits only values
proved by raw D3D11 metadata or authenticated sidecar bytes.  Unity-only
renderer, compiler-substitution, and publisher facts remain explicitly
unresolved; captured VB/IB/CB arrays are never copied into the output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Any, Callable


LIVE_SCHEMA = "endfield.endminf-m27-live-exact-particle-draw.v1"
AUTH_SCHEMA = (
    "endfield.endminf-m27-live-exact-particle-draw-authentication.v1")
CONVERTER_SCHEMA = "endfield.endminf-m27-capture-conversion.v1"

VS_SHA256 = "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c"
PS_SHA256 = "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e"
VS_IDENTITY = 0xC0266E7FAC0046C1
PS_IDENTITY = 0x92D80A93ADD9C714
VS_BYTES = 8148
PS_BYTES = 8200

M27_INDEX_COUNT = 1080
SOURCE_MESH_INDEX_COUNT = 72
SOURCE_BURST_COUNT = 15
TRIANGLE_LIST = 4
R16_UINT = 57
SKIN_FLAG_MASK = 32
SKIN_FLAG_REGISTER_OFFSET = 4
SKIN_FLAG_LANE = "w"
SKIN_RECORD_STRIDE_FLOAT4 = 16
TERRAIN_SELECTED_FRAME_SCHEMA = (
    "endfield.endminf-m27-terrain-profile-selected-frame.v1")
TERRAIN_PROFILE_CB_SLOT = 4
TERRAIN_PROFILE_REGISTER = 0
TERRAIN_PROFILE_LANE = "w"
TERRAIN_PROFILE_LANE_BYTE_OFFSET = 12
# RegisterFromTerrain/UpdateTerrainProfile publish index + 1 through a float.
# 2^24 is the first integer that cannot distinguish every adjacent uint in
# IEEE-754 binary32, so the source publisher admits 0..2^24-1 only.
TERRAIN_PROFILE_MAX_EXACT_PUBLISHED = 16_777_215
VERTEX_SKIN_BUFFER_BYTES = 8_413_184
VERTEX_SKIN_BUFFER_ELEMENTS = 525_824
VERTEX_SKIN_VIEW_DIMENSION = 1
VERTEX_SKIN_BIND_FLAGS = 136
VERTEX_SKIN_MISC_FLAGS = 64
EXPECTED_TEXTURES = {
    0: (1024, 1024, 99),
    1: (1024, 1024, 83),
    2: (1024, 1024, 83),
    3: (128, 128, 99),
}
FRAME_METADATA_RE = re.compile(r"^graphics/frames/([^/]+)/metadata\.json$")
FRAME_SCHEMA = "endfieldCapture.graphicsFrame.v2"
BINDINGS_FILE = "bindings.v3.bin"
BINDINGS_SCHEMA = "endfieldCapture.graphicsFrame.bindings.v3\n"
BINDINGS_WIRE_SCHEMA = (
    "header:u64(layout,frame,siblingEpoch,siblingCall);"
    "u32(headerSize,resourceSize,drawSize,resolverSize,siblingSlot,resources,draws,resolvers);"
    "u8(lane,drawLocal,siblingAuth,siblingLane);"
    "resource:u64(object,view,requested,blobOffset,blobBytes,call,epoch);"
    "u32(hresult,occurrence,slot);"
    "u8(captureKind,failure,owner,phase,stage,resourceKind,attempted,completed);"
    "draw:u64(call,epoch);u32(occurrence,indexCount,instanceCount,startIndex,baseVertex,startInstance);"
    "u8(owner,indexedInstanced,renderTargetCount,depthBound);"
    "resolver:u64(call,epoch);u32(occurrence,vertexCount,instanceCount,startVertex,startInstance);"
    "u8(owner,default,shadowOutput,shadowConsumer,renderTargetCount,depthBound,reserved0,reserved1);"
)


def _fnv1a64(text: str) -> int:
    value = 14695981039346656037
    for byte in text.encode("ascii"):
        value ^= byte
        value = (value * 1099511628211) & 0xffffffffffffffff
    return value


BINDINGS_LAYOUT_HASH = _fnv1a64(BINDINGS_WIRE_SCHEMA)
BINDINGS_HEADER = struct.Struct("<4Q8I4B")
BINDINGS_RESOURCE = struct.Struct("<7Q3I8B")
BINDINGS_DRAW = struct.Struct("<2Q4IiI4B")
BINDINGS_RESOLVER = struct.Struct("<2Q5I8B")
M27_CAPTURE_LANE = "priority-m27"
M27_CAPTURE_LANE_WIRE = 5
M27_DEFERRED_OWNER = 3
BEFORE_OWNER_PHASE = 1
AFTER_OWNER_PHASE = 2
EXACT_PACKET_COUNTERS = (
    "publishableM20Packets",
    "publishableM21Packets",
    "publishableM27Packets",
    "publishableDefaultDeferredPackets",
    "publishableM27DefaultDeferredJoinedPackets",
)
SCREEN_SHADOW_PACKET_COUNTERS = {
    "exactScreenShadowAdmissionRequiredPackets": 1,
    "exactScreenShadowAdmissionPassedPackets": 1,
    "exactScreenShadowAdmissionFailedPackets": 0,
}


class ConversionError(RuntimeError):
    """The raw package cannot support an authenticated observation."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConversionError(message)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _read_json(path: Path, schema: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConversionError(f"cannot read JSON {path}: {exc}") from exc
    _require(isinstance(value, dict), f"expected JSON object at {path}")
    _require(value.get("schema") == schema,
             f"{path} schema {value.get('schema')!r} != {schema!r}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ConversionError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _sha256_slice(path: Path, offset: int, length: int) -> str:
    _require(offset >= 0 and length >= 0,
             f"invalid sidecar slice offset={offset}, length={length}")
    digest = hashlib.sha256()
    remaining = length
    try:
        with path.open("rb") as stream:
            stream.seek(offset)
            while remaining:
                block = stream.read(min(1024 * 1024, remaining))
                _require(bool(block),
                         f"sidecar {path} ended inside authenticated slice")
                digest.update(block)
                remaining -= len(block)
    except OSError as exc:
        raise ConversionError(f"cannot hash sidecar slice in {path}: {exc}") from exc
    return digest.hexdigest()


def _read_slice(path: Path, offset: int, length: int) -> bytes:
    _require(offset >= 0 and length >= 0,
             f"invalid sidecar slice offset={offset}, length={length}")
    try:
        with path.open("rb") as stream:
            stream.seek(offset)
            value = stream.read(length)
    except OSError as exc:
        raise ConversionError(f"cannot read sidecar slice in {path}: {exc}") from exc
    _require(len(value) == length,
             f"sidecar {path} ended inside authenticated slice")
    return value


def _normalized_artifact_path(value: Any) -> str:
    _require(isinstance(value, str) and value,
             "collector inventory has an empty artifact path")
    text = value.replace("\\", "/")
    parts = text.split("/")
    _require(not text.startswith("/") and
             all(part not in ("", ".", "..") for part in parts),
             f"collector inventory path is not normalized: {value!r}")
    _require(text != "collected/inventory.json",
             "collector inventory must not include itself")
    return text


def _authenticate_inventory(
        root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    inventory_path = root / "collected" / "inventory.json"
    _require(inventory_path.is_file(),
             "collector inventory is missing: collected/inventory.json")
    inventory = _read_json(inventory_path, "endfieldCapture.collection.v1")
    rows = inventory.get("artifacts")
    _require(isinstance(rows, list), "collector inventory artifacts are missing")
    indexed: dict[str, dict[str, Any]] = {}
    declared_bytes = 0
    for raw in rows:
        _require(isinstance(raw, dict), "collector inventory artifact is not an object")
        relative = _normalized_artifact_path(raw.get("path"))
        _require(relative not in indexed,
                 f"collector inventory has duplicate artifact {relative}")
        size = raw.get("bytes")
        digest = str(raw.get("sha256", "")).lower()
        _require(_is_int(size) and size >= 0,
                 f"collector inventory size is invalid for {relative}")
        _require(len(digest) == 64 and
                 all(character in "0123456789abcdef" for character in digest),
                 f"collector inventory SHA-256 is invalid for {relative}")
        indexed[relative] = {"path": relative, "bytes": size, "sha256": digest}
        declared_bytes += size

    _require(inventory.get("files") == len(indexed),
             "collector inventory file count does not match artifacts")
    _require(inventory.get("bytes") == declared_bytes,
             "collector inventory byte count does not match artifacts")

    actual: set[str] = set()
    for path in root.rglob("*"):
        if path == inventory_path:
            continue
        _require(not path.is_symlink(),
                 f"collected package contains unsupported symlink: {path}")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    declared = set(indexed)
    missing = sorted(declared - actual)
    extra = sorted(actual - declared)
    _require(not missing and not extra,
             "collector inventory file set mismatch: "
             f"missing={missing[:3]}, extra={extra[:3]}")

    for relative in sorted(indexed):
        row = indexed[relative]
        path = root / Path(relative)
        _require(path.stat().st_size == row["bytes"],
                 f"collector inventory byte mismatch for {relative}")
        _require(_sha256(path) == row["sha256"],
                 f"collector inventory SHA-256 mismatch for {relative}")

    canonical = json.dumps(
        [indexed[key] for key in sorted(indexed)],
        sort_keys=True, separators=(",", ":")).encode("utf-8")
    authentication = {
        "inventorySha256": _sha256(inventory_path),
        "artifactSetSha256": hashlib.sha256(canonical).hexdigest(),
        "artifactCount": len(indexed),
        "artifactBytes": declared_bytes,
    }
    return indexed, authentication


def _artifact(
        artifacts: dict[str, dict[str, Any]], relative: str) -> dict[str, Any]:
    _require(relative in artifacts,
             f"collector inventory lacks required artifact {relative}")
    return artifacts[relative]


def _validate_summaries(
        root: Path, artifacts: dict[str, dict[str, Any]]) -> tuple[
            dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    for relative in (
            "session.json", "runtime.status.json", "collected/summary.json",
            "graphics/summary.json"):
        _artifact(artifacts, relative)
    session = _read_json(root / "session.json", "endfieldCapture.session.v1")
    runtime = _read_json(
        root / "runtime.status.json", "endfieldCapture.runtimeStatus.v1")
    collected = _read_json(
        root / "collected" / "summary.json", "endfieldCapture.summary.v1")
    graphics = _read_json(
        root / "graphics" / "summary.json",
        "endfieldCapture.graphicsSummary.v1")

    _require(session.get("sessionId") == root.name,
             "session descriptor identity does not match package directory")
    _require(_is_int(session.get("providers")) and
             session["providers"] & 1,
             "session descriptor did not select graphics")
    profile = session.get("graphicsProfile")
    label = session.get("evidenceLabel")
    _require(profile in ("targeted", "full"),
             f"M27 converter requires targeted/full graphics, got {profile!r}")
    _require(runtime.get("graphicsProfile") == profile and
             graphics.get("graphicsProfile") == profile,
             "graphics profile differs across authenticated summaries")
    _require(graphics.get("evidenceLabel") == label,
             "graphics evidence label differs from session descriptor")

    _require(collected.get("complete") is True and
             collected.get("dropped") == 0 and
             collected.get("invalidRecords") == 0 and
             collected.get("writerError") is False,
             "collector summary is incomplete or reports writer loss")
    _require(runtime.get("graphicsSelected") is True and
             runtime.get("graphicsHooksInstalled") is True and
             runtime.get("graphicsAttached") is True and
             runtime.get("graphicsDropped") == 0 and
             runtime.get("framePending") is False and
             runtime.get("frameCompleted") is True and
             runtime.get("frameIncomplete") is False and
             runtime.get("frameFailed") is False,
             "runtime graphics summary is incomplete or reports loss")
    _require(graphics.get("hooksInstalled") is True and
             graphics.get("attached") is True and
             graphics.get("dropped") == 0 and
             graphics.get("deferredFailed") is False and
             graphics.get("quiescentCleanup") is True and
             graphics.get("shaderBytecodeArchiveComplete") is True and
             graphics.get("complete") is True,
             "graphics summary is incomplete or reports capture loss")
    _require(graphics.get("exactOwnerResourcePayloadTiming") == "draw-local" and
             graphics.get("exactOwnerResourcePayloadDrawLocal") is True,
             "graphics summary lacks exact draw-local resource-payload proof")
    for counter in EXACT_PACKET_COUNTERS:
        _require(_is_int(graphics.get(counter)) and graphics[counter] == 1,
                 f"graphics summary exact packet counter {counter} != 1")
    for counter, expected in SCREEN_SHADOW_PACKET_COUNTERS.items():
        _require(_is_int(graphics.get(counter)) and
                 graphics[counter] == expected,
                 f"graphics summary screen-shadow counter {counter} != "
                 f"{expected}")
    _require(graphics.get("exactScreenShadowAdmissionPassed") is True,
             "graphics summary lacks exact screen-shadow admission")
    _require(graphics.get("exactEndminfPublishable") is True,
             "graphics summary does not authenticate exact Endminf publication")
    return session, runtime, collected, graphics


def _draw_shader(draw: dict[str, Any], stage: int) -> dict[str, Any] | None:
    rows = [row for row in draw.get("shaders", [])
            if isinstance(row, dict) and row.get("stage") == stage]
    return rows[0] if len(rows) == 1 else None


def _is_exact_m27_draw(draw: dict[str, Any]) -> bool:
    vertex = _draw_shader(draw, 0)
    pixel = _draw_shader(draw, 4)
    return bool(
        vertex and pixel and
        vertex.get("identityHash") == VS_IDENTITY and
        pixel.get("identityHash") == PS_IDENTITY and
        draw.get("count") == M27_INDEX_COUNT and
        draw.get("instanceCount") == 1)


def _select_draw(
        root: Path, artifacts: dict[str, dict[str, Any]]) -> tuple[
            str, dict[str, Any], dict[str, Any]]:
    metadata_paths = sorted(
        path for path in artifacts if FRAME_METADATA_RE.match(path))
    _require(metadata_paths, "collected session has no graphics frame metadata")
    matches: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for relative in metadata_paths:
        frame = _read_json(root / Path(relative), FRAME_SCHEMA)
        _require(frame.get("drawRecordsTruncated") is False,
                 f"frame draw rows are truncated: {relative}")
        draws = frame.get("drawRecords")
        _require(isinstance(draws, list), f"frame draw rows are missing: {relative}")
        ordinals = [row.get("drawOrdinal") for row in draws
                    if isinstance(row, dict)]
        _require(len(ordinals) == len(draws) and len(set(ordinals)) == len(ordinals),
                 f"frame draw rows are malformed or ambiguous: {relative}")
        for draw in draws:
            if isinstance(draw, dict) and _is_exact_m27_draw(draw):
                matches.append((relative, frame, draw))
    _require(len(matches) == 1,
             f"expected exactly one synchronized M27 draw; found {len(matches)}")
    relative, frame, draw = matches[0]
    _require(draw.get("priorityShaderPair") is True and
             draw.get("priorityM27Geometry") is True,
             "exact M27 draw lacks producer priority authentication")
    _require(frame.get("captureLane") == M27_CAPTURE_LANE,
             "exact M27 draw is not in the priority-M27 capture lane")
    return relative, frame, draw


def _validate_frame(
        root: Path, relative: str, frame: dict[str, Any],
        draw: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> tuple[
            Path, list[dict[str, Any]], str]:
    for key in ("resourceSelectionTruncated", "dispatchRecordsTruncated",
                "fullscreenResolverRecordsTruncated", "captureIncomplete",
                "captureFailed", "resourceCaptureIncomplete",
                "resourceCaptureFailed"):
        _require(frame.get(key) is False,
                 f"selected M27 frame gate failed: {key}=true ({relative})")
    _require(frame.get("droppedEvents") == 0,
             f"selected M27 frame reports dropped events: {relative}")
    draws = frame["drawRecords"]
    _require(frame.get("draws") == len(draws) and
             frame.get("observedDraws") == len(draws),
             f"selected M27 frame draw counts are inconsistent: {relative}")
    records = frame.get("selectedResourceRecords")
    _require(isinstance(records, list) and
             records and frame.get("selectedResources") == len(records),
             f"selected M27 resource rows are missing or truncated: {relative}")
    _validate_draw_local_resource_evidence(frame, draw, records, relative)

    frame_root = (root / Path(relative)).parent
    bindings_file = frame.get("bindingsFile")
    _require(bindings_file == BINDINGS_FILE,
             f"selected M27 bindings sidecar declaration is invalid: {relative}")
    bindings_relative = (Path(relative).parent / bindings_file).as_posix()
    bindings_artifact = _artifact(artifacts, bindings_relative)
    _validate_bindings_sidecar(
        frame_root / bindings_file, frame, bindings_artifact, relative)
    _require(frame.get("resourcesFile") == "resources.bin",
             f"selected M27 resources sidecar declaration is invalid: {relative}")
    resources_relative = (Path(relative).parent / "resources.bin").as_posix()
    resource_artifact = _artifact(artifacts, resources_relative)
    _require(frame.get("resourceBlobBytes") == resource_artifact["bytes"],
             f"selected M27 resource blob byte count drifted: {relative}")
    for index, record in enumerate(records):
        offset = record.get("blobOffset")
        size = record.get("blobBytes")
        _require(_is_int(offset) and _is_int(size) and
                 offset >= 0 and size >= 0 and
                 offset + size <= resource_artifact["bytes"],
                 f"selected resource row {index} points outside resources.bin")
    return frame_root / "resources.bin", records, bindings_relative


def _positive_int(value: Any) -> bool:
    return _is_int(value) and value > 0


def _validate_bindings_sidecar(
        path: Path, frame: dict[str, Any], artifact: dict[str, Any],
        relative: str) -> None:
    """Authenticate and cross-check the explicit fixed-width v3 wire ABI."""
    declared = (
        frame.get("bindingsLayoutHash"), frame.get("bindingsHeaderSize"),
        frame.get("bindingsSelectedRecordSize"),
        frame.get("bindingsDrawTimingRecordSize"),
        frame.get("bindingsResolverTimingRecordSize"),
    )
    expected = (
        BINDINGS_LAYOUT_HASH, BINDINGS_HEADER.size, BINDINGS_RESOURCE.size,
        BINDINGS_DRAW.size, BINDINGS_RESOLVER.size,
    )
    _require(declared == expected,
             f"selected M27 bindings layout declaration is invalid: {relative}")
    prefix = BINDINGS_SCHEMA.encode("ascii")
    _require(_is_int(artifact.get("bytes")) and
             artifact["bytes"] >= len(prefix) + BINDINGS_HEADER.size,
             f"selected M27 bindings inventory size is invalid: {relative}")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ConversionError(f"cannot read bindings sidecar {path}: {exc}") from exc
    _require(len(payload) == artifact["bytes"],
             f"selected M27 bindings inventory/file size differs: {relative}")
    _require(payload[:len(prefix)] == prefix,
             f"selected M27 bindings schema/header is invalid: {relative}")
    offset = len(prefix)
    header = BINDINGS_HEADER.unpack_from(payload, offset)
    offset += BINDINGS_HEADER.size
    (layout_hash, frame_number, sibling_epoch, sibling_call,
     header_size, resource_size, draw_size, resolver_size, sibling_slot,
     resource_count, draw_count, resolver_count, lane, draw_local,
     sibling_authenticated, sibling_lane) = header
    _require((layout_hash, header_size, resource_size, draw_size,
              resolver_size) == expected,
             f"selected M27 bindings wire layout is invalid: {relative}")
    _require(lane == M27_CAPTURE_LANE_WIRE and draw_local == 1 and
             sibling_authenticated in (0, 1) and
             sibling_lane == M27_CAPTURE_LANE_WIRE,
             f"selected M27 bindings wire lane is invalid: {relative}")
    _require(frame_number == frame.get("frame") and
             sibling_epoch == frame.get("joinedM27SiblingPresentEpoch", 0) and
             sibling_call == frame.get("joinedM27SiblingCallOrdinal", 0) and
             sibling_slot == frame.get("joinedM27SiblingSequenceSlot") and
             bool(sibling_authenticated) is
                frame.get("joinedM27SiblingAuthenticated") and
             resource_count == frame.get("selectedResources") and
             draw_count == len(frame.get("drawRecords", [])) and
             resolver_count == len(frame.get("fullscreenResolvers", [])),
             f"selected M27 bindings header disagrees with JSON: {relative}")
    if sibling_authenticated == 0:
        _require(sibling_epoch == 0 and sibling_call == 0,
                 f"selected M27 bindings inactive sibling is nonzero: {relative}")

    expected_file_size = (
        len(prefix) + BINDINGS_HEADER.size +
        resource_count * BINDINGS_RESOURCE.size +
        draw_count * BINDINGS_DRAW.size +
        resolver_count * BINDINGS_RESOLVER.size)
    _require(expected_file_size == artifact["bytes"],
             f"selected M27 bindings exact file size is invalid: {relative}")

    records = frame["selectedResourceRecords"]
    for index, json_row in enumerate(records):
        wire = BINDINGS_RESOURCE.unpack_from(payload, offset)
        offset += BINDINGS_RESOURCE.size
        (object_id, view_id, requested_bytes, blob_offset, blob_bytes,
         call_ordinal, present_epoch, hresult, occurrence, slot,
         capture_kind, failure, owner, phase, stage, resource_kind,
         attempted, completed) = wire
        _require(attempted in (0, 1) and completed in (0, 1),
                 f"bindings resource {index} has non-boolean wire flags: {relative}")
        json_values = (
            json_row.get("objectId"), json_row.get("viewId"),
            json_row.get("requestedBytes"), json_row.get("blobOffset"),
            json_row.get("blobBytes"),
            json_row.get("deferredUnifiedCallOrdinal"),
            json_row.get("deferredPresentEpoch"), json_row.get("hresult"),
            json_row.get("deferredOwnerOccurrence"), json_row.get("slot"),
            json_row.get("captureKind"), json_row.get("failure"),
            json_row.get("deferredOwner"),
            json_row.get("deferredCopyPhase"), json_row.get("stage"),
            json_row.get("resourceKind"),
            1 if json_row.get("attempted") is True else 0,
            1 if json_row.get("completed") is True else 0,
        )
        _require(wire == json_values,
                 f"bindings resource {index} disagrees with JSON: {relative}")

    for index, json_draw in enumerate(frame["drawRecords"]):
        wire = BINDINGS_DRAW.unpack_from(payload, offset)
        offset += BINDINGS_DRAW.size
        (call_ordinal, present_epoch, occurrence, index_count, instance_count,
         start_index, base_vertex, start_instance, owner,
         indexed_instanced, render_target_count, depth_bound) = wire
        _require(indexed_instanced in (0, 1) and depth_bound in (0, 1),
                 f"bindings draw {index} has non-boolean wire flags: {relative}")
        pipeline_target = json_draw.get("pipelineState", {}).get("target", {})
        json_values = (
            json_draw.get("unifiedCallOrdinal"), json_draw.get("presentEpoch"),
            json_draw.get("deferredOwnerOccurrence"), json_draw.get("count"),
            json_draw.get("instanceCount"), json_draw.get("start"),
            json_draw.get("baseVertex"), json_draw.get("startInstance"),
            json_draw.get("deferredOwner"),
            1 if json_draw.get("indexedInstanced") is True else 0,
            pipeline_target.get("renderTargetCount"),
            1 if pipeline_target.get("depthBound") is True else 0,
        )
        _require(wire == json_values,
                 f"bindings draw {index} disagrees with JSON: {relative}")

    for index, json_resolver in enumerate(frame.get("fullscreenResolvers", [])):
        wire = BINDINGS_RESOLVER.unpack_from(payload, offset)
        offset += BINDINGS_RESOLVER.size
        (call_ordinal, present_epoch, occurrence, vertex_count, instance_count,
         start_vertex, start_instance, owner, priority_default,
         priority_shadow_output, priority_shadow_consumer,
         render_target_count, depth_bound, reserved0, reserved1) = wire
        _require(priority_default in (0, 1) and
                 priority_shadow_output in (0, 1) and
                 priority_shadow_consumer in (0, 1) and
                 depth_bound in (0, 1) and reserved0 == 0 and reserved1 == 0,
                 f"bindings resolver {index} flags/reserved bytes are invalid: "
                 f"{relative}")
        chain = json_resolver.get("resourceChain", {})
        json_values = (
            json_resolver.get("unifiedCallOrdinal"),
            json_resolver.get("presentEpoch"),
            json_resolver.get("deferredOwnerOccurrence"),
            json_resolver.get("vertexCountPerInstance"),
            json_resolver.get("instanceCount"),
            json_resolver.get("startVertex"),
            json_resolver.get("startInstance"),
            json_resolver.get("deferredOwner"),
            1 if json_resolver.get("priorityDefaultDeferred") is True else 0,
            1 if json_resolver.get("priorityScreenShadowOutput") is True else 0,
            1 if json_resolver.get("priorityScreenShadowConsumer") is True else 0,
            len(chain.get("renderTargets", [])),
            1 if chain.get("depthTarget", {}).get("objectId") else 0,
            0, 0,
        )
        _require(wire == json_values,
                 f"bindings resolver {index} disagrees with JSON: {relative}")
    _require(offset == len(payload),
             f"selected M27 bindings parser did not consume exact extent: {relative}")


def _matching_selected_resource(
        records: list[dict[str, Any]], *, object_id: int, stage: int,
        slot: int, capture_kinds: tuple[int, ...]) -> bool:
    return any(
        row.get("objectId") == object_id and row.get("stage") == stage and
        row.get("slot") == slot and row.get("captureKind") in capture_kinds and
        row.get("deferredCopyPhase") == BEFORE_OWNER_PHASE
        for row in records)


def _validate_draw_local_resource_evidence(
        frame: dict[str, Any], draw: dict[str, Any],
        records: list[dict[str, Any]], relative: str) -> None:
    _require(frame.get("resourcePayloadTiming") == "draw-local" and
             frame.get("resourcePayloadDrawLocal") is True,
             f"selected M27 frame lacks draw-local payload proof: {relative}")

    owner = draw.get("deferredOwner")
    occurrence = draw.get("deferredOwnerOccurrence")
    call_ordinal = draw.get("unifiedCallOrdinal")
    present_epoch = draw.get("presentEpoch")
    _require(owner == M27_DEFERRED_OWNER and
             _positive_int(occurrence) and _positive_int(call_ordinal) and
             _positive_int(present_epoch),
             f"exact M27 draw owner chronology is invalid: {relative}")

    phases: set[int] = set()
    for index, record in enumerate(records):
        phase = record.get("deferredCopyPhase")
        slot = record.get("slot")
        output_slot = _is_int(slot) and (
            0x100 <= slot < 0x108 or slot == 0x200)
        _require(isinstance(record, dict) and
                 record.get("attempted") is True and
                 record.get("completed") is True and
                 _is_int(record.get("failure")) and
                 record.get("failure") == 0 and
                 _is_int(record.get("hresult")) and
                 record.get("hresult") == 0 and
                 _positive_int(record.get("requestedBytes")) and
                 _positive_int(record.get("blobBytes")) and
                 record.get("blobBytes") == record.get("requestedBytes") and
                 _is_int(record.get("deferredOwner")) and
                 record.get("deferredOwner") == owner and
                 _is_int(record.get("deferredOwnerOccurrence")) and
                 record.get("deferredOwnerOccurrence") == occurrence and
                 _is_int(record.get("deferredUnifiedCallOrdinal")) and
                 record.get("deferredUnifiedCallOrdinal") == call_ordinal and
                 _is_int(record.get("deferredPresentEpoch")) and
                 record.get("deferredPresentEpoch") == present_epoch and
                 _is_int(phase) and
                 phase in
                    (BEFORE_OWNER_PHASE, AFTER_OWNER_PHASE),
                 f"selected resource row {index} lacks exact owner-local proof: "
                 f"{relative}")
        _require((phase == AFTER_OWNER_PHASE) == output_slot and
                 (phase != AFTER_OWNER_PHASE or
                  (record.get("captureKind") == 3 and
                   record.get("stage") == 4)),
                 f"selected resource row {index} has the wrong owner phase: "
                 f"{relative}")
        phases.add(phase)
    _require(phases == {BEFORE_OWNER_PHASE, AFTER_OWNER_PHASE},
             f"selected M27 resources lack before/after owner phases: {relative}")

    ia = draw.get("inputAssembler")
    _require(isinstance(ia, dict),
             f"exact M27 input-assembler evidence is missing: {relative}")
    vertex_rows = ia.get("vertexBuffers")
    index_row = ia.get("indexBuffer")
    _require(isinstance(vertex_rows, list) and isinstance(index_row, dict),
             f"exact M27 input-assembler bindings are missing: {relative}")
    for binding in vertex_rows:
        if not isinstance(binding, dict) or not _positive_int(binding.get("objectId")):
            continue
        _require(_matching_selected_resource(
            records, object_id=binding["objectId"], stage=0,
            slot=binding.get("slot"), capture_kinds=(0,)),
            f"exact M27 IA vertex binding lacks before-owner payload: {relative}")
    _require(_positive_int(index_row.get("objectId")) and
             _matching_selected_resource(
                 records, object_id=index_row["objectId"], stage=0, slot=0,
                 capture_kinds=(1,)),
             f"exact M27 IA index binding lacks before-owner payload: {relative}")

    constants = draw.get("constantBuffers")
    _require(isinstance(constants, list) and constants,
             f"exact M27 constant-buffer bindings are missing: {relative}")
    for binding in constants:
        _require(isinstance(binding, dict) and
                 _positive_int(binding.get("bufferId")) and
                 _matching_selected_resource(
                     records, object_id=binding["bufferId"],
                     stage=binding.get("stage"), slot=binding.get("slot"),
                     capture_kinds=(2,)),
                 f"exact M27 constant-buffer binding lacks before-owner payload: "
                 f"{relative}")

    shader_resources = draw.get("resources")
    _require(isinstance(shader_resources, list) and shader_resources,
             f"exact M27 shader-resource bindings are missing: {relative}")
    for binding in shader_resources:
        if (not isinstance(binding, dict) or binding.get("bound") is not True or
                not _positive_int(binding.get("objectId"))):
            continue
        kind = binding.get("kind")
        capture_kinds = (4,) if kind == 1 else (3,) if kind in (2, 3, 4) else ()
        _require(bool(capture_kinds) and _matching_selected_resource(
            records, object_id=binding["objectId"],
            stage=binding.get("stage"), slot=binding.get("slot"),
            capture_kinds=capture_kinds),
            f"exact M27 shader-resource binding lacks before-owner payload: "
            f"{relative}")

    pipeline = draw.get("pipelineState")
    _require(isinstance(pipeline, dict),
             f"exact M27 pipeline state is missing: {relative}")
    render_targets = pipeline.get("renderTargets")
    _require(isinstance(render_targets, list),
             f"exact M27 render targets are missing: {relative}")
    for target in render_targets:
        if not isinstance(target, dict) or target.get("bound") is not True:
            continue
        slot = target.get("slot")
        _require(_is_int(slot) and any(
            row.get("captureKind") == 3 and row.get("stage") == 4 and
            row.get("slot") == 0x100 + slot and
            row.get("deferredCopyPhase") == AFTER_OWNER_PHASE and
            row.get("width") == target.get("width") and
            row.get("height") == target.get("height") and
            row.get("format") == target.get("textureFormat") and
            row.get("viewFormat") == target.get("viewFormat")
            for row in records),
            f"exact M27 render target {slot} lacks after-owner payload: "
            f"{relative}")
    target_summary = pipeline.get("target")
    depth = pipeline.get("depthTarget")
    _require(isinstance(target_summary, dict) and isinstance(depth, dict),
             f"exact M27 depth state is missing: {relative}")
    if target_summary.get("depthBound") is True:
        _require(any(
            row.get("captureKind") == 3 and row.get("stage") == 4 and
            row.get("slot") == 0x200 and
            row.get("deferredCopyPhase") == AFTER_OWNER_PHASE and
            row.get("width") == depth.get("width") and
            row.get("height") == depth.get("height") and
            row.get("format") == depth.get("textureFormat") and
            row.get("viewFormat") == depth.get("viewFormat")
            for row in records),
            f"exact M27 depth target lacks after-owner payload: {relative}")


def _one(
        rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool],
        label: str) -> dict[str, Any]:
    matches = [row for row in rows if predicate(row)]
    _require(len(matches) == 1, f"expected one {label}; found {len(matches)}")
    return matches[0]


def _constant_bytes(row: dict[str, Any], label: str) -> bytes:
    count = row.get("capturedConstants")
    data = row.get("dataHex")
    _require(_is_int(count) and count >= 0 and isinstance(data, str),
             f"{label} constant prefix metadata is invalid")
    try:
        value = bytes.fromhex(data)
    except ValueError as exc:
        raise ConversionError(f"{label} constant prefix is not hexadecimal") from exc
    _require(len(value) == count * 16,
             f"{label} constant prefix byte count does not match metadata")
    return value


def _extract_b2(
        draw: dict[str, Any], synchronized_draw_id: str) -> tuple[
            dict[str, Any], dict[str, Any]]:
    rows = draw.get("constantBuffers")
    _require(isinstance(rows, list), "exact M27 constant-buffer rows are missing")
    vertex = _one(rows, lambda row: row.get("stage") == 0 and row.get("slot") == 2,
                  "VS b2 row")
    pixel = _one(rows, lambda row: row.get("stage") == 4 and row.get("slot") == 2,
                 "PS b2 row")
    for label, row, minimum in (("VS b2", vertex, 11), ("PS b2", pixel, 5)):
        _require(row.get("rangeValid") is True and
                 row.get("metadataValid") is True and
                 row.get("numConstants") == 4096 and
                 _is_int(row.get("bufferId")) and row["bufferId"] != 0 and
                 _is_int(row.get("capturedConstants")) and
                 row["capturedConstants"] >= minimum,
                 f"{label} range/prefix is incomplete")
    _require(vertex["bufferId"] == pixel["bufferId"] and
             vertex.get("firstConstant") == pixel.get("firstConstant"),
             "VS/PS b2 rows do not identify one synchronized record range")
    _require(draw.get("vsCb2RangeValid") is True and
             draw.get("vsCb2MetadataValid") is True and
             draw.get("vsCb2BufferId") == vertex["bufferId"] and
             draw.get("vsCb2FirstConstant") == vertex.get("firstConstant") and
             draw.get("vsCb2NumConstants") == 4096,
             "draw-level VS b2 metadata disagrees with captured row")

    vertex_bytes = _constant_bytes(vertex, "VS b2")
    pixel_bytes = _constant_bytes(pixel, "PS b2")
    _require(vertex_bytes[:5 * 16] == pixel_bytes[:5 * 16],
             "VS/PS b2 record-0 prefixes disagree")
    flag_offset = SKIN_FLAG_REGISTER_OFFSET * 16 + 12
    skin_flag = struct.unpack_from("<I", vertex_bytes, flag_offset)[0]
    _require((skin_flag & SKIN_FLAG_MASK) == 0,
             f"M27 b2 c4.w activates unsupported skin branch: 0x{skin_flag:08x}")
    control = {
        "observedFromActualDraw": True,
        "synchronizedDrawId": synchronized_draw_id,
        "constantBufferSlot": 2,
        "recordIndex": 0,
        "recordStrideFloat4": SKIN_RECORD_STRIDE_FLOAT4,
        "flagRegisterOffset": SKIN_FLAG_REGISTER_OFFSET,
        "flagLane": SKIN_FLAG_LANE,
        "flagMask": SKIN_FLAG_MASK,
        "flagRaw": skin_flag,
        "skinBranchActive": False,
    }
    row = {
        "slot": 2,
        "observedStages": ["vertex", "pixel"],
        "objectId": vertex["bufferId"],
        "firstConstant": vertex["firstConstant"],
        "numConstants": 4096,
        "recordIndex": 0,
        "authenticatedPrefixBytes": 256,
        "record0Sha256": hashlib.sha256(vertex_bytes[:256]).hexdigest(),
        "vertexCapturedPrefixSha256": hashlib.sha256(vertex_bytes).hexdigest(),
        "pixelCapturedPrefixSha256": hashlib.sha256(pixel_bytes).hexdigest(),
        "observedFromActualDraw": True,
        "synchronizedDrawId": synchronized_draw_id,
    }
    return control, row


def _extract_terrain_profile_b4(
        draw: dict[str, Any], records: list[dict[str, Any]],
        resources_path: Path, resources_artifact_sha256: str,
        synchronized_draw_id: str) -> dict[str, Any]:
    """Authenticate retail PS b4 c0.w without exporting its captured buffer."""
    rows = draw.get("constantBuffers")
    _require(isinstance(rows, list),
             "exact M27 constant-buffer rows are missing")
    binding = _one(
        rows,
        lambda row: row.get("stage") == 4 and
        row.get("slot") == TERRAIN_PROFILE_CB_SLOT,
        "PS b4 row")
    buffer_id = binding.get("bufferId")
    first_constant = binding.get("firstConstant")
    num_constants = binding.get("numConstants")
    captured_constants = binding.get("capturedConstants")
    _require(_positive_int(buffer_id) and
             _is_int(first_constant) and first_constant >= 0 and
             _positive_int(num_constants) and
             _positive_int(captured_constants) and
             binding.get("rangeValid") is True and
             binding.get("metadataValid") is True,
             "exact M27 PS b4 buffer/range metadata is invalid")
    prefix = _constant_bytes(binding, "PS b4")
    _require(captured_constants >= 1 and len(prefix) >= 16,
             "exact M27 PS b4 captured prefix is incomplete")

    capture = _one(
        records,
        lambda row: row.get("captureKind") == 2 and
        row.get("stage") == 4 and
        row.get("slot") == TERRAIN_PROFILE_CB_SLOT and
        row.get("objectId") == buffer_id,
        "captured PS b4 buffer")
    _require(capture.get("deferredCopyPhase") == BEFORE_OWNER_PHASE and
             capture.get("deferredOwner") == draw.get("deferredOwner") and
             capture.get("deferredOwnerOccurrence") ==
                draw.get("deferredOwnerOccurrence") and
             capture.get("deferredUnifiedCallOrdinal") ==
                draw.get("unifiedCallOrdinal") and
             capture.get("deferredPresentEpoch") == draw.get("presentEpoch"),
             "exact M27 PS b4 capture is not from the selected owner call")
    _require(capture.get("bindingFirstConstant") == first_constant and
             capture.get("bindingNumConstants") == num_constants,
             "exact M27 PS b4 selected range disagrees with the draw")
    byte_size = capture.get("byteSize")
    blob_offset = capture.get("blobOffset")
    blob_bytes = capture.get("blobBytes")
    _require(_positive_int(byte_size) and byte_size % 16 == 0 and
             _is_int(blob_offset) and blob_offset >= 0 and
             blob_bytes == byte_size and
             capture.get("requestedBytes") == byte_size,
             "exact M27 PS b4 staged buffer is incomplete")
    range_offset_in_buffer = first_constant * 16
    range_bytes = num_constants * 16
    _require(range_offset_in_buffer <= byte_size and
             range_bytes <= byte_size - range_offset_in_buffer,
             "exact M27 PS b4 selected range exceeds its staged buffer")

    word_offset = (blob_offset + range_offset_in_buffer +
                   TERRAIN_PROFILE_LANE_BYTE_OFFSET)
    staged_word = _read_slice(resources_path, word_offset, 4)
    prefix_word = prefix[
        TERRAIN_PROFILE_LANE_BYTE_OFFSET:
        TERRAIN_PROFILE_LANE_BYTE_OFFSET + 4]
    _require(staged_word == prefix_word,
             "exact M27 PS b4 c0.w draw prefix and staged buffer disagree")
    raw_word = struct.unpack("<I", staged_word)[0]
    exact_float = struct.unpack("<f", staged_word)[0]
    _require(math.isfinite(exact_float),
             "exact M27 PS b4 terrain profile scalar is non-finite")
    _require(exact_float.is_integer(),
             "exact M27 PS b4 terrain profile scalar is non-integral")
    published_scalar = int(exact_float)
    _require(0 <= published_scalar <= TERRAIN_PROFILE_MAX_EXACT_PUBLISHED,
             "exact M27 PS b4 terrain profile scalar is outside the source "
             "publisher range")
    canonical_word = struct.unpack(
        "<I", struct.pack("<f", float(published_scalar)))[0]
    _require(raw_word == canonical_word,
             "exact M27 PS b4 terrain profile scalar is not a canonical exact "
             "published uint")

    buffer_sha256 = _sha256_slice(resources_path, blob_offset, blob_bytes)
    selected_range_sha256 = _sha256_slice(
        resources_path, blob_offset + range_offset_in_buffer, range_bytes)
    provenance = {
        "schema": TERRAIN_SELECTED_FRAME_SCHEMA,
        "synchronizedDrawId": synchronized_draw_id,
        "stage": 4,
        "slot": TERRAIN_PROFILE_CB_SLOT,
        "firstConstant": first_constant,
        "numConstants": num_constants,
        "rawWord": raw_word,
        "resourcesArtifactSha256": resources_artifact_sha256,
        "bufferPayloadSha256": buffer_sha256,
        "selectedRangeSha256": selected_range_sha256,
    }
    provenance_sha256 = hashlib.sha256(json.dumps(
        provenance, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")).hexdigest()
    return {
        "schema": TERRAIN_SELECTED_FRAME_SCHEMA,
        "status": "draw_local_selected_frame_value_authenticated",
        "constantBufferSlot": TERRAIN_PROFILE_CB_SLOT,
        "constantRegister": TERRAIN_PROFILE_REGISTER,
        "lane": TERRAIN_PROFILE_LANE,
        "c0wRawWord": raw_word,
        "exactFloat": exact_float,
        "publishedScalar": published_scalar,
        "resourcesArtifactSha256": resources_artifact_sha256,
        "bufferPayloadSha256": buffer_sha256,
        "selectedRangeSha256": selected_range_sha256,
        "provenanceSha256": provenance_sha256,
        "observedFromActualDraw": True,
        "synchronizedDrawId": synchronized_draw_id,
    }


def _extract_ia(
        draw: dict[str, Any], records: list[dict[str, Any]], resources_path: Path,
        synchronized_draw_id: str) -> dict[str, Any]:
    _require(draw.get("indexedInstanced") is True and
             draw.get("topology") == TRIANGLE_LIST and
             draw.get("count") == M27_INDEX_COUNT and
             draw.get("instanceCount") == 1 and
             draw.get("startInstance") == 0,
             "exact M27 indexed draw shape is invalid")
    ia = draw.get("inputAssembler")
    _require(isinstance(ia, dict), "exact M27 input-assembler row is missing")
    vertex_rows = ia.get("vertexBuffers")
    index_row = ia.get("indexBuffer")
    _require(isinstance(vertex_rows, list) and isinstance(index_row, dict),
             "exact M27 IA vertex/index rows are missing")
    primary = _one(vertex_rows, lambda row: row.get("slot") == 0,
                   "IA vertex slot 0")
    stride = primary.get("stride")
    _require(stride in (60, 68) and _is_int(primary.get("offset")) and
             _is_int(primary.get("objectId")) and primary["objectId"] != 0,
             "exact M27 IA vertex slot 0 descriptor is invalid")
    _require(index_row.get("format") == R16_UINT and
             _is_int(index_row.get("offset")) and
             _is_int(index_row.get("objectId")) and index_row["objectId"] != 0,
             "exact M27 IA index descriptor is invalid")

    vertex_capture = _one(
        records,
        lambda row: row.get("captureKind") == 0 and row.get("stage") == 0 and
        row.get("slot") == 0 and row.get("objectId") == primary["objectId"] and
        row.get("stride") == stride and row.get("byteOffset") == primary["offset"],
        "captured IA vertex slot 0")
    index_capture = _one(
        records,
        lambda row: row.get("captureKind") == 1 and row.get("stage") == 0 and
        row.get("slot") == 0 and row.get("objectId") == index_row["objectId"] and
        row.get("format") == R16_UINT and row.get("stride") == 2 and
        row.get("byteOffset") == index_row["offset"],
        "captured IA index buffer")
    index_start = index_capture["blobOffset"] + index_row["offset"] + draw["start"] * 2
    index_bytes = _read_slice(resources_path, index_start, M27_INDEX_COUNT * 2)
    indices = struct.unpack("<" + "H" * M27_INDEX_COUNT, index_bytes)
    base_vertex = draw.get("baseVertex")
    _require(_is_int(base_vertex), "exact M27 base vertex is invalid")
    effective_min = min(indices) + base_vertex
    effective_max = max(indices) + base_vertex
    _require(effective_min >= 0,
             "exact M27 index range underflows its base vertex")
    vertex_end = primary["offset"] + (effective_max + 1) * stride
    _require(vertex_end <= vertex_capture["blobBytes"],
             "exact M27 index range exceeds captured vertex buffer")
    return {
        "vertexStride": stride,
        "actualParticleRecordRangeObserved": True,
        "indexCount": M27_INDEX_COUNT,
        "sourceMeshIndexCount": SOURCE_MESH_INDEX_COUNT,
        "expandedParticleCount": SOURCE_BURST_COUNT,
        "particleExpansionEquation": "1080=15*72",
        "topology": TRIANGLE_LIST,
        "baseVertex": base_vertex,
        "startIndex": draw["start"],
        "instanceCount": 1,
        "startInstance": 0,
        "effectiveVertexIndexMin": effective_min,
        "effectiveVertexIndexMax": effective_max,
        "uniqueIndexCount": len(set(indices)),
        "indexRangeSha256": hashlib.sha256(index_bytes).hexdigest(),
        "vertexBufferObjectId": primary["objectId"],
        "indexBufferObjectId": index_row["objectId"],
        "observedFromActualDraw": True,
        "synchronizedDrawId": synchronized_draw_id,
    }


def _extract_vertex_t0(
        draw: dict[str, Any], records: list[dict[str, Any]], resources_path: Path,
        synchronized_draw_id: str) -> dict[str, Any]:
    ia_ids = {
        row.get("objectId")
        for row in draw.get("inputAssembler", {}).get("vertexBuffers", [])
        if isinstance(row, dict)
    }
    resource_rows = draw.get("resources")
    _require(isinstance(resource_rows, list), "exact M27 draw resources are missing")
    candidates = [
        row for row in resource_rows
        if isinstance(row, dict) and row.get("stage") == 0 and
        row.get("slot") == 0 and
        (row.get("bound") is False or
         (row.get("bound") is True and row.get("kind") == 1 and
          _is_int(row.get("viewId")) and row.get("viewId") != 0 and
          row.get("objectId") not in ia_ids))
    ]
    _require(len(candidates) == 1,
             f"expected one explicit draw-local VS t0 outcome; found {len(candidates)}")
    resource = candidates[0]
    if resource.get("bound") is False:
        _require(resource.get("objectId") == 0 and resource.get("viewId") in (None, 0),
                 "unbound VS t0 outcome retains a non-null object/view")
        return {
            "slot": 0,
            "bound": False,
            "objectId": 0,
            "viewId": 0,
            "observedFromActualDraw": True,
            "synchronizedDrawId": synchronized_draw_id,
        }

    required_descriptor = {
        "objectId": lambda value: _is_int(value) and value != 0,
        "viewId": lambda value: _is_int(value) and value != 0,
        "descriptorHash": lambda value: _is_int(value) and value != 0,
        "byteSize": lambda value: _is_int(value) and value > 0,
        "viewDimension": lambda value: value == VERTEX_SKIN_VIEW_DIMENSION,
        "bindFlags": lambda value: value == VERTEX_SKIN_BIND_FLAGS,
        "miscFlags": lambda value: value == VERTEX_SKIN_MISC_FLAGS,
        "structureByteStride": lambda value: value == 16,
        "viewFirstElement": lambda value: value == 0,
        "viewNumElements": lambda value: _is_int(value) and value > 0,
    }
    for field, predicate in required_descriptor.items():
        _require(predicate(resource.get(field)),
                 f"bound VS t0 descriptor field {field} is missing/invalid")
    _require(resource["viewNumElements"] * resource["structureByteStride"] ==
             resource["byteSize"],
             "bound VS t0 view extent does not cover the structured buffer")
    _require(resource["byteSize"] == VERTEX_SKIN_BUFFER_BYTES and
             resource["viewNumElements"] == VERTEX_SKIN_BUFFER_ELEMENTS,
             "bound VS t0 does not match the authenticated retail palette extent")
    capture = _one(
        records,
        lambda row: row.get("captureKind") == 4 and row.get("stage") == 0 and
        row.get("slot") == 0 and row.get("objectId") == resource["objectId"] and
        row.get("byteSize") == resource["byteSize"] and
        row.get("blobBytes") == resource["byteSize"],
        "captured VS t0 structured buffer")
    payload_sha = _sha256_slice(
        resources_path, capture["blobOffset"], capture["blobBytes"])
    return {
        "slot": 0,
        "bound": True,
        "kind": "StructuredBuffer",
        "logicalName": "_VertexSkinMatrices",
        "objectId": resource["objectId"],
        "viewId": resource["viewId"],
        "descriptorHash": resource["descriptorHash"],
        "byteSize": resource["byteSize"],
        "viewDimension": resource["viewDimension"],
        "bindFlags": resource["bindFlags"],
        "miscFlags": resource["miscFlags"],
        "stride": resource["structureByteStride"],
        "viewFirstElement": resource["viewFirstElement"],
        "viewNumElements": resource["viewNumElements"],
        "payloadSha256": payload_sha,
        "payloadBytes": capture["blobBytes"],
        "observedFromActualDraw": True,
        "synchronizedDrawId": synchronized_draw_id,
    }


def _extract_pipeline(draw: dict[str, Any]) -> dict[str, Any]:
    pipeline = draw.get("pipelineState")
    _require(isinstance(pipeline, dict) and pipeline.get("valid") is True,
             "exact M27 draw-local pipeline state is missing")
    target = pipeline.get("target")
    viewport = pipeline.get("viewport")
    depth = pipeline.get("depthTarget")
    _require(isinstance(target, dict) and isinstance(viewport, dict) and
             isinstance(depth, dict),
             "exact M27 target/viewport/depth metadata is missing")
    _require(viewport.get("count") == 1,
             "exact M27 viewport is missing or ambiguous")
    viewport_row = [viewport.get("x"), viewport.get("y"),
                    viewport.get("width"), viewport.get("height")]
    live_target = {**target, "viewport": viewport_row}
    render_targets = pipeline.get("renderTargets")
    _require(isinstance(render_targets, list),
             "exact M27 render-target rows are missing")
    bound_targets = [row for row in render_targets
                     if isinstance(row, dict) and row.get("bound") is True]
    _require(sorted(row.get("slot") for row in bound_targets) == [0, 1, 2, 3, 4],
             "exact M27 bound render-target slots are missing or ambiguous")
    live_targets = [{**row, "viewport": viewport_row} for row in bound_targets]

    depth_stencil = pipeline.get("depthStencil")
    rasterizer = pipeline.get("rasterizer")
    _require(isinstance(depth_stencil, dict) and isinstance(rasterizer, dict),
             "exact M27 fixed-state metadata is missing")
    fixed = {
        "depthWriteMask": depth_stencil.get("writeMask"),
        "depthFunction": depth_stencil.get("function"),
        "cullMode": rasterizer.get("cullMode"),
        "frontCounterClockwise": rasterizer.get("frontCounterClockwise"),
        "scissorEnabled": rasterizer.get("scissorEnabled"),
    }
    samplers = pipeline.get("samplers")
    _require(isinstance(samplers, list), "exact M27 sampler rows are missing")
    slots = [row.get("slot") for row in samplers if isinstance(row, dict)]
    _require(len(slots) == len(set(slots)), "exact M27 sampler rows are ambiguous")
    live_samplers = [
        {**row, "active": row.get("bound") is True,
         "observedFromActualDraw": True}
        for row in samplers if isinstance(row, dict)
    ]
    return {
        "target": live_target,
        "renderTargets": live_targets,
        "depthTarget": depth,
        "fixedState": fixed,
        "samplers": live_samplers,
    }


def _extract_textures(
        draw: dict[str, Any], records: list[dict[str, Any]],
        resources_path: Path) -> list[dict[str, Any]]:
    resource_rows = draw.get("resources")
    _require(isinstance(resource_rows, list), "exact M27 draw resources are missing")
    textures: list[dict[str, Any]] = []
    for slot in range(6):
        resource = _one(
            resource_rows,
            lambda row, wanted=slot: row.get("kind") == 3 and
            row.get("stage") == 4 and row.get("slot") == wanted and
            row.get("bound") is True,
            f"PS texture t{slot}")
        output = {
            "slot": slot,
            "objectId": resource.get("objectId"),
            "viewId": resource.get("viewId"),
            "descriptorHash": resource.get("descriptorHash"),
            "byteSize": resource.get("byteSize"),
            "dxgiFormat": resource.get("viewFormat"),
            "observedFromActualDraw": True,
        }
        if slot < 4:
            capture = _one(
                records,
                lambda row, wanted=slot, object_id=resource.get("objectId"):
                row.get("captureKind") == 3 and row.get("stage") == 4 and
                row.get("slot") == wanted and row.get("objectId") == object_id,
                f"captured PS texture t{slot}")
            width, height, texture_format = EXPECTED_TEXTURES[slot]
            _require(capture.get("width") == width and
                     capture.get("height") == height and
                     capture.get("viewFormat") == texture_format,
                     f"captured PS texture t{slot} descriptor drifted")
            output.update({
                "width": capture["width"],
                "height": capture["height"],
                "capturedSubresource": capture.get("subresource"),
                "capturedSubresourceBytes": capture["blobBytes"],
                "capturedSubresourceSha256": _sha256_slice(
                    resources_path, capture["blobOffset"], capture["blobBytes"]),
            })
        textures.append(output)
    _require(textures[4]["objectId"] != 0 and
             textures[4]["objectId"] == textures[5]["objectId"] and
             textures[4]["viewId"] == textures[5]["viewId"],
             "PS t4/t5 do not identify one shared bound default resource")
    return textures


def _authenticate_shaders(
        root: Path, artifacts: dict[str, dict[str, Any]],
        draw: dict[str, Any]) -> dict[str, Any]:
    rows = {
        0: (VS_SHA256, VS_BYTES),
        4: (PS_SHA256, PS_BYTES),
    }
    output: dict[str, Any] = {}
    for stage, (digest, expected_bytes) in rows.items():
        shader = _draw_shader(draw, stage)
        _require(shader is not None and shader.get("bytecodeSize") == expected_bytes,
                 f"exact M27 stage {stage} shader metadata is incomplete")
        relative = f"graphics/shaders/{digest}-s{stage}.dxbc"
        artifact = _artifact(artifacts, relative)
        _require(artifact["sha256"] == digest and artifact["bytes"] == expected_bytes,
                 f"exact M27 stage {stage} shader archive is not authenticated")
        output["vertex" if stage == 0 else "pixel"] = {
            "sha256": digest,
            "identity": f"0x{shader['identityHash']:016X}",
            "bytes": expected_bytes,
            "artifact": relative,
        }
    return output


def build_observation(session_root: Path) -> dict[str, Any]:
    root = session_root.resolve()
    _require(root.is_dir(), f"session root does not exist: {root}")
    artifacts, package_auth = _authenticate_inventory(root)
    session, _runtime, _collected, graphics = _validate_summaries(root, artifacts)
    relative, frame, draw = _select_draw(root, artifacts)
    resources_path, resource_records, bindings_relative = _validate_frame(
        root, relative, frame, draw, artifacts)
    frame_number = frame.get("frame")
    timestamp_qpc = frame.get("timestampQpc")
    draw_ordinal = draw.get("drawOrdinal")
    _require(_is_int(frame_number) and _is_int(timestamp_qpc) and
             _is_int(draw_ordinal),
             "selected M27 synchronization identity is incomplete")
    synchronized_draw_id = (
        f"{session['sessionId']}:frame:{frame_number}:"
        f"qpc:{timestamp_qpc}:draw:{draw_ordinal}")

    shader = _authenticate_shaders(root, artifacts, draw)
    ia = _extract_ia(draw, resource_records, resources_path, synchronized_draw_id)
    skin_control, b2 = _extract_b2(draw, synchronized_draw_id)
    resources_relative = (Path(relative).parent / "resources.bin").as_posix()
    terrain_profile = _extract_terrain_profile_b4(
        draw, resource_records, resources_path,
        artifacts[resources_relative]["sha256"], synchronized_draw_id)
    vertex_t0 = _extract_vertex_t0(
        draw, resource_records, resources_path, synchronized_draw_id)
    pipeline = _extract_pipeline(draw)
    textures = _extract_textures(draw, resource_records, resources_path)

    frame_artifact = _artifact(artifacts, relative)
    unresolved = [
        {
            "fields": [
                "authentication.actualDrawRendererObserved",
                "renderer",
                "inputAssembler.fromParticleSystemRenderer",
                "inputAssembler.geometryRendererPathId",
            ],
            "reason": "raw D3D11 capture cannot authenticate Unity object ownership",
        },
        {
            "fields": ["compilerSubstitution"],
            "reason": "requires the Unity post-baseline shell callback report",
        },
        {
            "fields": [
                "textures[*].property", "textures[*].mipCount",
                "textures[*].fullMipChain", "textures[4:6].serializedNull",
            ],
            "reason": "raw draw proves bindings/subresources, not serialized Material semantics",
        },
        {
            "fields": [
                "constantBuffers[0]", "constantBuffers[1]",
                "constantBuffers[3]",
                "constantBuffers[*].logicalName",
                "constantBuffers[*].producer", "publishers",
            ],
            "reason": "requires Unity source publishers and selected-frame provenance",
        },
        {
            "fields": ["vertexSkinningControl.sourceMeshSkinRows"],
            "reason": "requires the authenticated Unity source-mesh probe",
        },
    ]
    return {
        "schema": LIVE_SCHEMA,
        "status": "raw_capture_authenticated_unity_fields_unresolved",
        "observationOnly": True,
        "presentationEnabled": False,
        "capturedPacketArraysUsed": False,
        "authentication": {
            "schema": AUTH_SCHEMA,
            "staticContractFieldsSynthesized": False,
            "synchronizedDrawId": synchronized_draw_id,
            "producerReportSha256": package_auth["inventorySha256"],
            "converterSchema": CONVERTER_SCHEMA,
            "sessionId": session["sessionId"],
            "frame": frame_number,
            "timestampQpc": timestamp_qpc,
            "drawOrdinal": draw_ordinal,
            "captureLane": frame["captureLane"],
            "resourcePayloadTiming": frame["resourcePayloadTiming"],
            "resourcePayloadDrawLocal": True,
            "deferredOwner": draw["deferredOwner"],
            "deferredOwnerOccurrence": draw["deferredOwnerOccurrence"],
            "unifiedCallOrdinal": draw["unifiedCallOrdinal"],
            "presentEpoch": draw["presentEpoch"],
            "bindingsSchema": BINDINGS_SCHEMA.rstrip("\n"),
            "bindingsLayoutHash": f"0x{BINDINGS_LAYOUT_HASH:016x}",
            "bindingsBytes": artifacts[bindings_relative]["bytes"],
            "exactPacketCounters": {
                key: graphics[key] for key in EXACT_PACKET_COUNTERS
            },
            **package_auth,
            "sessionDescriptorSha256": artifacts["session.json"]["sha256"],
            "collectorSummarySha256":
                artifacts["collected/summary.json"]["sha256"],
            "graphicsSummarySha256": artifacts["graphics/summary.json"]["sha256"],
            "frameMetadataSha256": frame_artifact["sha256"],
            "bindingsFileSha256": artifacts[bindings_relative]["sha256"],
            "resourcesFileSha256": artifacts[resources_relative]["sha256"],
        },
        "shader": {
            "vertexSha256": shader["vertex"]["sha256"],
            "pixelSha256": shader["pixel"]["sha256"],
            "vertexIdentity": shader["vertex"]["identity"],
            "pixelIdentity": shader["pixel"]["identity"],
            "authenticatedArtifacts": [shader["vertex"], shader["pixel"]],
        },
        "inputAssembler": ia,
        "vertexSkinningControl": skin_control,
        "vertexResources": [vertex_t0],
        "constantBuffers": [b2],
        "terrainSubsurfaceSelectedFrame": terrain_profile,
        "textures": textures,
        **pipeline,
        "unresolved": unresolved,
        "boundary": (
            "Captured VB/IB/CB arrays were inspected only to derive bounded "
            "hashes, index extents, and selected b2 lanes. They are not emitted "
            "or authorized for Unity/runtime replay."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path, help="Collected session root")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    try:
        observation = build_observation(args.session)
    except ConversionError as exc:
        print(f"M27 capture conversion failed: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(observation, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
