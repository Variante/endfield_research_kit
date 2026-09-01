#!/usr/bin/env python3
"""Verify the draw-local Endminf screen-shadow producer/consumer handoff.

The maintained deferred presentation may consume the retail t11 attachment only
after one joined M27+Default packet proves this exact same-frame chain:

* ordinary producer 1 after-draw (scene-shadow R);
* ordinary producer 2 after-draw (preserved R plus character-shadow G); and
* Default Deferred consumer-before t11.

This verifier intentionally repeats the native observer's admission checks and
adds byte-content checks.  A telemetry boolean alone is not publication
authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_screen_shadow_capture_latest.json"
)

SCHEMA = "endfieldCapture.graphicsFrame.v2"
JOINED_LANE = "joined-m27-default"
EXPECTED_GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
WIDTH = 3840
HEIGHT = 2160
BYTES_PER_PIXEL = 2
TEXTURE_FORMATS = {48, 49}  # R8G8_Typeless/R8G8_UNorm
VIEW_FORMAT = 49  # R8G8_UNorm
PS_STAGE = 4
SRV_CAPTURE_KIND = 3
SCREEN_SHADOW_SLOT = 11
OUTPUT_SLOT_BASE = 0x100
DEFAULT_OWNER = 4
SCREEN_SHADOW_OUTPUT_OWNER = 5
COPY_BEFORE_OWNER = 1
COPY_AFTER_OWNER = 2


class VerificationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise VerificationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"{path} must contain one JSON object")
    return value


def _int(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise VerificationError(f"{key} must be an integer, got {value!r}")
    return value


def _shader_pair_complete(resolver: dict[str, Any]) -> bool:
    identities = {
        row.get("stage"): row.get("identityHash")
        for row in resolver.get("shaders", [])
        if isinstance(row, dict)
    }
    return all(isinstance(identities.get(stage), int) and identities[stage] > 0
               for stage in (0, PS_STAGE))


def _pipeline_target(
    resolver: dict[str, Any], target: dict[str, Any]
) -> dict[str, Any] | None:
    state = resolver.get("pipelineState")
    if not isinstance(state, dict) or state.get("valid") is not True:
        return None
    slot = target.get("slot")
    targets = state.get("renderTargets")
    if (not isinstance(slot, int) or not isinstance(targets, list)
            or slot < 0 or slot >= len(targets)
            or not isinstance(targets[slot], dict)):
        return None
    return targets[slot]


def _matching_target(
    resolver: dict[str, Any], object_id: int
) -> dict[str, Any] | None:
    rows = [
        row for row in resolver.get("resourceChain", {}).get("renderTargets", [])
        if isinstance(row, dict) and row.get("objectId") == object_id
    ]
    return rows[0] if len(rows) == 1 else None


def _consumer_t11(
    resolver: dict[str, Any], object_id: int
) -> dict[str, Any] | None:
    rows = [
        row for row in resolver.get("resourceChain", {}).get("psInputs", [])
        if isinstance(row, dict)
        and row.get("slot") == SCREEN_SHADOW_SLOT
        and row.get("objectId") == object_id
    ]
    return rows[0] if len(rows) == 1 else None


def _descriptor_valid(row: dict[str, Any], width: int, height: int) -> bool:
    return (
        row.get("width") == width
        and row.get("height") == height
        and row.get("format") in TEXTURE_FORMATS
        and row.get("viewFormat") == VIEW_FORMAT
    )


def _selected_descriptor_valid(
    row: dict[str, Any], width: int, height: int
) -> bool:
    expected_bytes = width * height * BYTES_PER_PIXEL
    return (
        row.get("captureKind") == SRV_CAPTURE_KIND
        and row.get("resourceKind") == 1
        and row.get("stage") == PS_STAGE
        and _descriptor_valid(row, width, height)
        and row.get("subresource") == 0
        and row.get("requestedBytes") == expected_bytes
        and row.get("byteSize") == expected_bytes
        and row.get("blobBytes") == expected_bytes
        and row.get("attempted") is True
        and row.get("completed") is True
        and row.get("failure") == 0
        and row.get("hresult") == 0
    )


def _payload(blob: bytes, row: dict[str, Any]) -> bytes:
    start = _int(row, "blobOffset")
    size = _int(row, "blobBytes")
    end = start + size
    if start < 0 or size <= 0 or end > len(blob):
        raise VerificationError(
            f"invalid payload range [{start}, {end}) for {len(blob)} bytes"
        )
    return blob[start:end]


def _channel_summary(payload: bytes, channel: int) -> dict[str, Any]:
    values = payload[channel::BYTES_PER_PIXEL]
    histogram = [0] * 256
    for value in values:
        histogram[value] += 1
    nonzero_bins = [index for index, count in enumerate(histogram) if count]
    return {
        "minimum": nonzero_bins[0],
        "maximum": nonzero_bins[-1],
        "distinctValues": len(nonzero_bins),
        "neutral255Pixels": histogram[255],
        "zeroPixels": histogram[0],
    }


def _record_report(
    name: str, row: dict[str, Any], payload: bytes
) -> dict[str, Any]:
    return {
        "name": name,
        "objectId": row["objectId"],
        "slot": row["slot"],
        "deferredOwner": row["deferredOwner"],
        "deferredCopyPhase": row["deferredCopyPhase"],
        "deferredOwnerOccurrence": row["deferredOwnerOccurrence"],
        "deferredUnifiedCallOrdinal": row["deferredUnifiedCallOrdinal"],
        "deferredPresentEpoch": row["deferredPresentEpoch"],
        "blobOffset": row["blobOffset"],
        "blobBytes": row["blobBytes"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "channels": {
            "r": _channel_summary(payload, 0),
            "g": _channel_summary(payload, 1),
        },
    }


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _write_grayscale_png(
    path: Path, width: int, height: int, values: bytes
) -> dict[str, Any]:
    expected = width * height
    if len(values) != expected:
        raise VerificationError(
            f"PNG source has {len(values)} bytes, expected {expected}"
        )
    rows = b"".join(
        b"\x00" + values[y * width:(y + 1) * width]
        for y in range(height)
    )
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0),
        )
        + _png_chunk(b"IDAT", zlib.compress(rows, 9))
        + _png_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": str(path.resolve()),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "rowOrder": "captured-native-no-flip",
    }


def _write_channel_artifacts(
    artifact_dir: Path,
    width: int,
    height: int,
    p1: bytes,
    p2: bytes,
    consumer: bytes,
) -> dict[str, Any]:
    channels = {
        "producer1AfterR": p1[0::2],
        "producer1AfterG": p1[1::2],
        "producer2AfterR": p2[0::2],
        "producer2AfterG": p2[1::2],
        "consumerBeforeR": consumer[0::2],
        "consumerBeforeG": consumer[1::2],
        "producerRDelta": bytes(
            abs(left - right) for left, right in zip(p1[0::2], p2[0::2])
        ),
        "producerGDelta": bytes(
            abs(left - right) for left, right in zip(p1[1::2], p2[1::2])
        ),
    }
    output: dict[str, Any] = {}
    for name, values in channels.items():
        output[name] = _write_grayscale_png(
            artifact_dir / f"{name}.png", width, height, values
        )
    return output


def verify_frame(
    frame_dir: Path, *, width: int = WIDTH, height: int = HEIGHT,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    metadata = load_json(frame_dir / "metadata.json")
    failures: list[str] = []

    if metadata.get("schema") != SCHEMA:
        failures.append(f"unsupported schema {metadata.get('schema')!r}")
    if metadata.get("captureLane") != JOINED_LANE:
        failures.append(f"capture lane is {metadata.get('captureLane')!r}")
    if metadata.get("resourcePayloadTiming") != "draw-local":
        failures.append("resource payload timing is not draw-local")
    if metadata.get("resourcePayloadDrawLocal") is not True:
        failures.append("resourcePayloadDrawLocal is not true")
    if metadata.get("joinedM27SiblingAuthenticated") is not True:
        failures.append("joined M27 sibling is not authenticated")
    for key in (
        "drawRecordsTruncated", "dispatchRecordsTruncated",
        "resourceSelectionTruncated", "captureIncomplete", "captureFailed",
        "resourceCaptureIncomplete", "resourceCaptureFailed",
    ):
        if metadata.get(key) is not False:
            failures.append(f"{key} is not false")
    if metadata.get("droppedEvents") != 0:
        failures.append(f"droppedEvents is {metadata.get('droppedEvents')!r}")

    telemetry = {
        "required": metadata.get("exactEndminfScreenShadowAdmissionRequired"),
        "passed": metadata.get("exactEndminfScreenShadowAdmissionPassed"),
        "failure": metadata.get("exactEndminfScreenShadowAdmissionFailure"),
        "objectId": metadata.get("exactEndminfScreenShadowObjectId"),
        "producerRecords": metadata.get("exactEndminfScreenShadowProducerRecords"),
        "consumerRecords": metadata.get("exactEndminfScreenShadowConsumerRecords"),
        "selectedRecords": metadata.get("exactEndminfScreenShadowSelectedRecords"),
        "payloadComparisonAvailable": metadata.get(
            "exactEndminfScreenShadowPayloadComparisonAvailable"
        ),
        "payloadsEqual": metadata.get("exactEndminfScreenShadowPayloadsEqual"),
    }
    expected_telemetry = {
        "required": True,
        "passed": True,
        "failure": "none",
        "producerRecords": 2,
        "consumerRecords": 1,
        "selectedRecords": 3,
        "payloadComparisonAvailable": True,
        "payloadsEqual": True,
    }
    for key, expected in expected_telemetry.items():
        if telemetry[key] != expected:
            failures.append(
                f"admission {key} is {telemetry[key]!r}, expected {expected!r}"
            )
    object_id = telemetry["objectId"]
    if isinstance(object_id, bool) or not isinstance(object_id, int) or object_id <= 0:
        failures.append(f"admission objectId is invalid: {object_id!r}")
        object_id = -1

    resolvers = [
        row for row in metadata.get("fullscreenResolvers", [])
        if isinstance(row, dict)
    ]
    producers = [
        row for row in resolvers
        if row.get("priorityScreenShadowOutput") is True
        and row.get("instanced") is False
        and _matching_target(row, object_id) is not None
    ]
    consumers = [
        row for row in resolvers
        if row.get("priorityScreenShadowConsumer") is True
        and _consumer_t11(row, object_id) is not None
    ]
    if len(producers) != 2:
        failures.append(f"found {len(producers)} matching producer resolvers, expected 2")
    if len(consumers) != 1:
        failures.append(f"found {len(consumers)} matching consumer resolvers, expected 1")

    producer_ordinals: list[int] = []
    producer_slots: list[int] = []
    for index, resolver in enumerate(producers):
        target = _matching_target(resolver, object_id)
        assert target is not None
        if not _shader_pair_complete(resolver):
            failures.append(f"producer {index + 1} shader pair is incomplete")
        if not _descriptor_valid(target, width, height):
            failures.append(f"producer {index + 1} target descriptor is invalid")
        pipeline_target = _pipeline_target(resolver, target)
        if (pipeline_target is None or pipeline_target.get("bound") is not True
                or not _descriptor_valid(pipeline_target, width, height)):
            failures.append(f"producer {index + 1} pipeline target is invalid")
        ordinal = resolver.get("unifiedCallOrdinal")
        slot = target.get("slot")
        if not isinstance(ordinal, int) or ordinal <= 0:
            failures.append(f"producer {index + 1} call ordinal is invalid")
        else:
            producer_ordinals.append(ordinal)
        if not isinstance(slot, int) or slot < 0:
            failures.append(f"producer {index + 1} target slot is invalid")
        else:
            producer_slots.append(slot)

    consumer_ordinal: int | None = None
    if len(consumers) == 1:
        consumer = consumers[0]
        resource = _consumer_t11(consumer, object_id)
        assert resource is not None
        if not _shader_pair_complete(consumer):
            failures.append("consumer shader pair is incomplete")
        if not _descriptor_valid(resource, width, height):
            failures.append("consumer t11 descriptor is invalid")
        state = consumer.get("pipelineState")
        samplers = state.get("samplers", []) if isinstance(state, dict) else []
        sampler1 = next(
            (row for row in samplers if isinstance(row, dict) and row.get("slot") == 1),
            None,
        )
        if (not isinstance(state, dict) or state.get("valid") is not True
                or not isinstance(sampler1, dict) or sampler1.get("bound") is not True):
            failures.append("consumer pipeline or s1 sampler is invalid")
        value = consumer.get("unifiedCallOrdinal")
        if not isinstance(value, int) or value <= 0:
            failures.append("consumer call ordinal is invalid")
        else:
            consumer_ordinal = value

    if len(producer_ordinals) == 2:
        producer_ordinals.sort()
        if producer_ordinals[0] >= producer_ordinals[1]:
            failures.append("producer call ordinals are not strictly increasing")
        if consumer_ordinal is not None and producer_ordinals[1] >= consumer_ordinal:
            failures.append("producer-to-consumer chronology is invalid")
    if len(set(producer_slots)) > 1:
        failures.append(f"producer render-target slots differ: {producer_slots}")

    selected = [
        row for row in metadata.get("selectedResourceRecords", [])
        if isinstance(row, dict)
        and row.get("objectId") == object_id
        and row.get("captureKind") == SRV_CAPTURE_KIND
        and row.get("stage") == PS_STAGE
    ]
    output_rows = sorted(
        (row for row in selected
         if row.get("deferredOwner") == SCREEN_SHADOW_OUTPUT_OWNER
         and row.get("deferredCopyPhase") == COPY_AFTER_OWNER),
        key=lambda row: row.get("deferredOwnerOccurrence", -1),
    )
    consumer_rows = [
        row for row in selected
        if row.get("slot") == SCREEN_SHADOW_SLOT
        and row.get("deferredOwner") == DEFAULT_OWNER
        and row.get("deferredCopyPhase") == COPY_BEFORE_OWNER
    ]
    if len(output_rows) != 2:
        failures.append(f"found {len(output_rows)} producer-after payloads, expected 2")
    if len(consumer_rows) != 1:
        failures.append(f"found {len(consumer_rows)} consumer-before t11 payloads, expected 1")

    if len(output_rows) == 2:
        occurrences = [row.get("deferredOwnerOccurrence") for row in output_rows]
        if occurrences != [1, 2]:
            failures.append(f"producer owner occurrences are {occurrences}, expected [1, 2]")
        expected_slot = OUTPUT_SLOT_BASE + (producer_slots[0] if producer_slots else 0)
        if any(row.get("slot") != expected_slot for row in output_rows):
            failures.append(f"producer payload slot is not {expected_slot}")
    for name, rows in (("producer", output_rows), ("consumer", consumer_rows)):
        for index, row in enumerate(rows):
            if not _selected_descriptor_valid(row, width, height):
                failures.append(f"{name} payload {index + 1} descriptor/readback is invalid")

    record_reports: list[dict[str, Any]] = []
    artifacts: dict[str, Any] = {}
    content = {
        "producer1ToProducer2Changed": False,
        "sceneRPreserved": False,
        "characterGChanged": False,
        "producer2EqualsConsumer": False,
    }
    if len(output_rows) == 2 and len(consumer_rows) == 1:
        resource_name = metadata.get("resourcesFile")
        if not isinstance(resource_name, str):
            failures.append("resourcesFile is missing")
        else:
            try:
                blob = (frame_dir / resource_name).read_bytes()
                p1 = _payload(blob, output_rows[0])
                p2 = _payload(blob, output_rows[1])
                consumer_payload = _payload(blob, consumer_rows[0])
                record_reports = [
                    _record_report("producer1After", output_rows[0], p1),
                    _record_report("producer2After", output_rows[1], p2),
                    _record_report("consumerT11Before", consumer_rows[0], consumer_payload),
                ]
                content = {
                    "producer1ToProducer2Changed": p1 != p2,
                    "sceneRPreserved": p1[0::2] == p2[0::2],
                    "characterGChanged": p1[1::2] != p2[1::2],
                    "producer2EqualsConsumer": p2 == consumer_payload,
                }
                for key, passed in content.items():
                    if not passed:
                        failures.append(f"content gate failed: {key}")
                if record_reports[0]["channels"]["r"]["distinctValues"] < 2:
                    failures.append("content gate failed: producer-1 scene R is constant")
                if record_reports[1]["channels"]["g"]["distinctValues"] < 2:
                    failures.append("content gate failed: producer-2 character G is constant")
                if artifact_dir is not None:
                    artifacts = _write_channel_artifacts(
                        artifact_dir, width, height, p1, p2, consumer_payload
                    )
            except (OSError, VerificationError) as exc:
                failures.append(str(exc))

    epochs = {
        row.get("deferredPresentEpoch") for row in [*output_rows, *consumer_rows]
    }
    if len(epochs) != 1 or None in epochs or 0 in epochs:
        failures.append(f"selected payload present epochs are invalid: {sorted(epochs, key=str)}")
    if len(output_rows) == 2 and consumer_rows:
        record_ordinals = [
            output_rows[0].get("deferredUnifiedCallOrdinal"),
            output_rows[1].get("deferredUnifiedCallOrdinal"),
            consumer_rows[0].get("deferredUnifiedCallOrdinal"),
        ]
        if not all(isinstance(value, int) for value in record_ordinals):
            failures.append("selected payload call ordinals are missing")
        elif not (record_ordinals[0] < record_ordinals[1] < record_ordinals[2]):
            failures.append(f"selected payload chronology is invalid: {record_ordinals}")

    return {
        "frame": metadata.get("frame"),
        "frameDirectory": str(frame_dir.resolve()),
        "valid": not failures,
        "admission": telemetry,
        "producerCallOrdinals": sorted(producer_ordinals),
        "consumerCallOrdinal": consumer_ordinal,
        "content": content,
        "records": record_reports,
        "artifacts": artifacts,
        "failures": failures,
    }


def _frame_sort_key(path: Path) -> tuple[int, str]:
    match = re.match(r"(\d+)", path.parent.name)
    return (int(match.group(1)) if match else 2**63 - 1, path.parent.name)


def authenticate_collection(capture: Path) -> dict[str, Any]:
    """Authenticate the collector inventory and the pinned client identity."""
    inventory_path = capture / "collected/inventory.json"
    inventory = load_json(inventory_path)
    if inventory.get("schema") != "endfieldCapture.collection.v1":
        raise VerificationError("collector inventory schema is invalid")
    rows = inventory.get("artifacts")
    if not isinstance(rows, list):
        raise VerificationError("collector inventory artifacts are missing")

    indexed: dict[str, dict[str, Any]] = {}
    declared_bytes = 0
    for raw in rows:
        if not isinstance(raw, dict):
            raise VerificationError("collector inventory artifact is not an object")
        relative = raw.get("path")
        size = raw.get("bytes")
        digest = raw.get("sha256")
        if (not isinstance(relative, str) or not relative
                or "\\" in relative or relative.startswith("/")
                or any(part in ("", ".", "..") for part in relative.split("/"))
                or relative == "collected/inventory.json"):
            raise VerificationError(
                f"collector inventory path is not normalized: {relative!r}"
            )
        if relative in indexed:
            raise VerificationError(f"collector inventory duplicates {relative}")
        if (isinstance(size, bool) or not isinstance(size, int) or size < 0
                or not isinstance(digest, str) or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise VerificationError(
                f"collector inventory metadata is invalid for {relative}"
            )
        indexed[relative] = raw
        declared_bytes += size

    if inventory.get("files") != len(indexed):
        raise VerificationError("collector inventory file count is inconsistent")
    if inventory.get("bytes") != declared_bytes:
        raise VerificationError("collector inventory byte count is inconsistent")

    actual = {
        path.relative_to(capture).as_posix()
        for path in capture.rglob("*")
        if path.is_file() and path != inventory_path
    }
    declared = set(indexed)
    if actual != declared:
        missing = sorted(declared - actual)
        extra = sorted(actual - declared)
        raise VerificationError(
            "collector inventory file set differs: "
            f"missing={missing[:3]}, extra={extra[:3]}"
        )
    for relative, row in indexed.items():
        path = capture / Path(relative)
        if path.is_symlink():
            raise VerificationError(f"collector artifact is a symlink: {relative}")
        if path.stat().st_size != row["bytes"]:
            raise VerificationError(f"collector byte count differs for {relative}")
        if _sha256(path) != row["sha256"]:
            raise VerificationError(f"collector SHA-256 differs for {relative}")

    for required in (
        "session.json", "runtime.status.json", "collected/summary.json",
        "graphics/summary.json",
    ):
        if required not in indexed:
            raise VerificationError(f"collector inventory lacks {required}")

    session = load_json(capture / "session.json")
    collected = load_json(capture / "collected/summary.json")
    if session.get("schema") != "endfieldCapture.session.v1":
        raise VerificationError("session descriptor schema is invalid")
    if session.get("gameBuild") != EXPECTED_GAME_BUILD:
        raise VerificationError(
            f"session game build is {session.get('gameBuild')!r}, "
            f"expected {EXPECTED_GAME_BUILD!r}"
        )
    if session.get("graphicsProfile") != "full":
        raise VerificationError(
            f"screen-shadow publication requires Full graphics, got "
            f"{session.get('graphicsProfile')!r}"
        )
    if (collected.get("schema") != "endfieldCapture.summary.v1"
            or collected.get("complete") is not True
            or collected.get("dropped") != 0
            or collected.get("invalidRecords") != 0
            or collected.get("writerError") is not False):
        raise VerificationError("collector summary is incomplete or reports loss")
    return {
        "inventorySha256": _sha256(inventory_path),
        "artifactCount": len(indexed),
        "artifactBytes": declared_bytes,
        "gameBuild": session["gameBuild"],
        "graphicsProfile": session["graphicsProfile"],
        "runtimeSha256": session.get("runtimeSha256"),
        "targetSha256": session.get("targetSha256"),
    }


def verify_session(
    capture: Path, artifact_dir: Path | None = None
) -> dict[str, Any]:
    authentication = authenticate_collection(capture)
    frame_paths = sorted(
        (capture / "graphics/frames").glob("*/metadata.json"),
        key=_frame_sort_key,
    )
    if not frame_paths:
        raise VerificationError(
            f"capture has no graphics metadata under {capture / 'graphics/frames'}"
        )

    candidates: list[dict[str, Any]] = []
    for path in frame_paths:
        metadata = load_json(path)
        if (metadata.get("captureLane") == JOINED_LANE
                or metadata.get("exactEndminfScreenShadowAdmissionRequired") is True):
            frame_artifact_dir = None
            if artifact_dir is not None:
                frame_artifact_dir = artifact_dir / path.parent.name
            candidates.append(verify_frame(
                path.parent, artifact_dir=frame_artifact_dir
            ))

    summary_failures: list[str] = []
    summary_path = capture / "graphics/summary.json"
    summary: dict[str, Any] = {}
    if not summary_path.is_file():
        summary_failures.append("graphics/summary.json is missing")
    else:
        summary = load_json(summary_path)
        if summary.get("complete") is not True:
            summary_failures.append("graphics summary is not complete")
        if summary.get("automaticCollectionReady") is not True:
            summary_failures.append("automatic graphics collection is not ready")
        if summary.get("exactEndminfPublishable") is not True:
            summary_failures.append("exact Endminf packet set is not publishable")
        if summary.get("exactScreenShadowAdmissionPassed") is not True:
            summary_failures.append("graphics summary did not publish screen-shadow admission")
        expected_counts = {
            "exactScreenShadowAdmissionRequiredPackets": 1,
            "exactScreenShadowAdmissionPassedPackets": 1,
            "exactScreenShadowAdmissionFailedPackets": 0,
        }
        for key, expected in expected_counts.items():
            if summary.get(key) != expected:
                summary_failures.append(
                    f"graphics summary {key} is {summary.get(key)!r}, "
                    f"expected {expected}"
                )

    valid_candidates = [row for row in candidates if row["valid"]]
    failures = list(summary_failures)
    if len(valid_candidates) != 1:
        failures.append(
            f"found {len(valid_candidates)} valid joined screen-shadow packets, expected 1"
        )
    if not candidates:
        failures.append("no joined screen-shadow candidate packet was captured")
    for row in candidates:
        if not row["valid"]:
            failures.extend(
                f"frame {row['frame']}: {failure}" for failure in row["failures"]
            )

    return {
        "schema": "endfield.endminf-screen-shadow-capture.v1",
        "status": "validated" if not failures else "rejected",
        "capture": str(capture.resolve()),
        "authentication": authentication,
        "framesScanned": len(frame_paths),
        "candidateCount": len(candidates),
        "validCandidateCount": len(valid_candidates),
        "summary": {
            "path": str(summary_path.resolve()),
            "complete": summary.get("complete"),
            "automaticCollectionReady": summary.get("automaticCollectionReady"),
            "exactEndminfPublishable": summary.get("exactEndminfPublishable"),
            "exactScreenShadowAdmissionPassed": summary.get(
                "exactScreenShadowAdmissionPassed"
            ),
            "exactScreenShadowAdmissionRequiredPackets": summary.get(
                "exactScreenShadowAdmissionRequiredPackets"
            ),
            "exactScreenShadowAdmissionPassedPackets": summary.get(
                "exactScreenShadowAdmissionPassedPackets"
            ),
            "exactScreenShadowAdmissionFailedPackets": summary.get(
                "exactScreenShadowAdmissionFailedPackets"
            ),
        },
        "candidates": candidates,
        "failures": failures,
    }


def build_report(
    capture: Path, artifact_dir: Path | None = None
) -> dict[str, Any]:
    try:
        return verify_session(capture, artifact_dir)
    except (OSError, ValueError, VerificationError) as exc:
        return {
            "schema": "endfield.endminf-screen-shadow-capture.v1",
            "status": "rejected",
            "capture": str(capture.resolve()),
            "authentication": None,
            "framesScanned": 0,
            "candidateCount": 0,
            "validCandidateCount": 0,
            "summary": None,
            "candidates": [],
            "failures": [str(exc)],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--artifact-dir", type=Path,
        help="write lossless native-row-order R/G evidence PNGs",
    )
    args = parser.parse_args()
    report = build_report(args.capture.resolve(), args.artifact_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    for failure in report["failures"]:
        print(f"ERROR: {failure}")
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
