#!/usr/bin/env python3
"""Fail-closed validation of Endminf's captured Streamline DLAA boundary.

This tool validates evidence only.  It deliberately does not decode the four
surfaces or generate Unity assets.  A capture is admitted only when the Full
graphics summary, Streamline call chronology, exposure texel, surface-pair
metadata, files, sizes, and hashes all agree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_streamline_surface_capture_latest.json"
)

WIDTH = 3840
HEIGHT = 2160
PACKET_BYTES = 199_065_600
PAIR_BYTES = 398_131_200
EXPECTED_SURFACES = (
    ("input_color.bin", 0, 3, 26, 33_177_600),
    ("output_color.bin", 1, 4, 10, 66_355_200),
    ("depth.bin", 2, 0, 19, 66_355_200),
    ("motion.bin", 3, 1, 34, 33_177_600),
)
EXPOSURE_FORMAT_BYTES = {
    2: 16,   # R32G32B32A32_FLOAT
    6: 12,   # R32G32B32_FLOAT
    10: 8,   # R16G16B16A16_FLOAT
    16: 8,   # R32G32_FLOAT
    24: 4,   # R10G10B10A2_UNORM
    26: 4,   # R11G11B10_FLOAT
    28: 4,   # R8G8B8A8_UNORM
    29: 4,   # R8G8B8A8_UNORM_SRGB
    34: 4,   # R16G16_FLOAT
    41: 4,   # R32_FLOAT
    54: 2,   # R16_FLOAT
    61: 1,   # R8_UNORM
}


class VerificationError(RuntimeError):
    pass


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"{label}: missing {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label}: cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"{label}: root must be a JSON object: {path}")
    return value


def integer(value: Any, default: int = -1) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def require_equal(
    errors: list[str], label: str, actual: Any, expected: Any
) -> None:
    if actual != expected:
        errors.append(f"{label}: expected {expected!r}, found {actual!r}")


def require_true(errors: list[str], label: str, actual: Any) -> None:
    require_equal(errors, label, actual, True)


def unique_order(
    rows: Any, order: int, label: str, errors: list[str]
) -> dict[str, Any] | None:
    if not isinstance(rows, list):
        errors.append(f"{label}: call collection is not an array")
        return None
    matches = [row for row in rows if isinstance(row, dict)
               and integer(row.get("order")) == order]
    if len(matches) != 1:
        errors.append(
            f"{label}: order {order} must resolve once, found {len(matches)}")
        return None
    return matches[0]


def audit_session(capture: Path, errors: list[str]) -> dict[str, Any]:
    session = load_json(capture / "session.json", "session")
    summary = load_json(capture / "graphics/summary.json", "graphics summary")
    status = load_json(capture / "runtime.status.json", "runtime status")
    collected = load_json(capture / "collected/summary.json", "collection summary")

    require_equal(errors, "session.schema", session.get("schema"),
                  "endfieldCapture.session.v1")
    require_equal(errors, "session.graphicsProfile",
                  session.get("graphicsProfile"), "full")
    require_equal(errors, "graphics summary.schema", summary.get("schema"),
                  "endfieldCapture.graphicsSummary.v1")
    require_equal(errors, "graphics summary.graphicsProfile",
                  summary.get("graphicsProfile"), "full")
    require_true(errors, "graphics summary.hooksInstalled",
                 summary.get("hooksInstalled"))
    require_true(errors, "graphics summary.attached", summary.get("attached"))
    require_true(errors, "graphics summary.quiescentCleanup",
                 summary.get("quiescentCleanup"))
    require_true(errors, "graphics summary.complete", summary.get("complete"))
    require_equal(errors, "graphics summary.dropped",
                  integer(summary.get("dropped")), 0)
    require_true(errors, "graphics summary.sequenceAutomatic",
                 summary.get("sequenceAutomatic"))
    require_equal(errors, "graphics summary.sequenceFrames",
                  integer(summary.get("sequenceFrames")), 72)
    require_equal(errors, "graphics summary.sequenceLimit",
                  integer(summary.get("sequenceLimit")), 72)
    if summary.get("runtimeMode") != "d3d11-proxy":
        require_true(errors, "graphics summary.animatorSequenceTriggerGateMatched",
                     summary.get("animatorSequenceTriggerGateMatched"))
    require_true(errors, "graphics summary.cadenceValid",
                 summary.get("cadenceValid"))
    require_equal(errors, "runtime status.schema", status.get("schema"),
                  "endfieldCapture.runtimeStatus.v1")
    require_equal(errors, "runtime status.graphicsProfile",
                  status.get("graphicsProfile"), "full")
    require_true(errors, "runtime status.graphicsSelected",
                 status.get("graphicsSelected"))
    require_true(errors, "runtime status.graphicsHooksInstalled",
                 status.get("graphicsHooksInstalled"))
    require_true(errors, "runtime status.graphicsAttached",
                 status.get("graphicsAttached"))
    require_equal(errors, "runtime status.graphicsDropped",
                  integer(status.get("graphicsDropped")), 0)
    require_equal(errors, "runtime status.graphicsSequenceFrames",
                  integer(status.get("graphicsSequenceFrames")), 72)
    require_true(errors, "runtime status.graphicsSequenceAutomatic",
                 status.get("graphicsSequenceAutomatic"))
    require_equal(errors, "runtime status.graphicsSequenceActive",
                  status.get("graphicsSequenceActive"), False)
    require_equal(errors, "runtime status.graphicsSequenceCapturePending",
                  status.get("graphicsSequenceCapturePending"), False)
    require_equal(errors, "runtime status.framePending",
                  status.get("framePending"), False)
    require_true(errors, "runtime status.frameCompleted",
                 status.get("frameCompleted"))
    require_equal(errors, "runtime status.frameIncomplete",
                  status.get("frameIncomplete"), False)
    require_equal(errors, "runtime status.frameFailed",
                  status.get("frameFailed"), False)
    require_equal(errors, "collection summary.schema", collected.get("schema"),
                  "endfieldCapture.summary.v1")
    require_true(errors, "collection summary.complete", collected.get("complete"))
    require_equal(errors, "collection summary.dropped",
                  integer(collected.get("dropped")), 0)
    require_equal(errors, "collection summary.invalidRecords",
                  integer(collected.get("invalidRecords")), 0)
    require_equal(errors, "collection summary.writerError",
                  collected.get("writerError"), False)
    return {"session": session, "graphicsSummary": summary,
            "runtimeStatus": status, "collectionSummary": collected}


def audit_streamline_global(
    streamline: dict[str, Any], summary: dict[str, Any], errors: list[str]
) -> None:
    require_equal(errors, "Streamline.schema", streamline.get("schema"),
                  "endfieldCapture.streamlineDlss.v4")
    for key in (
        "observationOnly", "requested", "configured", "exactBuildValidated",
        "coreModuleLoaded", "coreModuleValidated", "dlssModuleLoaded",
        "dlssModuleValidated", "coreHooksInstalled",
        "initHookInstalled", "initObserved",
        "dlssOptionsHookInstalled", "dlssOptionsDirectHookInstalled",
        "presentClockConfigured", "callbacksQuiescent",
        "exposureCaptureRequested", "exposureCaptureComplete",
        "sequenceComplete",
    ):
        require_true(errors, f"Streamline.{key}", streamline.get(key))
    for key in ("recordsTruncated", "recordsUnreadable", "apiCallFailed",
                "exposureCaptureFailed", "failed"):
        require_equal(errors, f"Streamline.{key}", streamline.get(key), False)
    for key in (
        "presentClockFailures", "droppedFrameTokenCalls", "droppedOptionsCalls",
        "droppedInitCalls",
        "droppedTagCalls", "droppedConstantsCalls", "droppedEvaluateCalls",
        "truncatedTagPayloads", "truncatedEvaluatePayloads",
        "rejectedTargetViewportDlssSequences", "pendingDlssSequences",
        "droppedExposureSamples",
    ):
        require_equal(errors, f"Streamline.{key}", integer(streamline.get(key)), 0)
    require_equal(errors, "Streamline.initCalls",
                  integer(streamline.get("initCalls")), 1)
    initialization_value = streamline.get("initialization")
    initialization = (initialization_value
                      if isinstance(initialization_value, dict) else {})
    require_equal(errors, "Streamline.initialization.result",
                  integer(initialization.get("result")), 0)
    require_true(errors, "Streamline.initialization.readable",
                 initialization.get("readable"))
    require_equal(errors, "Streamline.initialization.truncated",
                  initialization.get("truncated"), False)
    features = initialization.get("features")
    if not isinstance(features, list) or 0 not in features:
        errors.append("Streamline.initialization.features: expected DLSS feature 0")
    samples = integer(streamline.get("exposureSamples"))
    require_equal(errors, "Streamline.matchedExposureSamples",
                  integer(streamline.get("matchedExposureSamples")), samples)
    if samples <= 0:
        errors.append(f"Streamline.exposureSamples: expected > 0, found {samples}")
    if integer(streamline.get("matchedTargetViewportDlssSequences")) <= 0:
        errors.append("Streamline.matchedTargetViewportDlssSequences: expected > 0")
    require_true(errors, "graphics summary.streamlineDlssObservationComplete",
                 summary.get("streamlineDlssObservationComplete"))
    require_true(errors, "graphics summary.streamlineDlssInitHookInstalled",
                 summary.get("streamlineDlssInitHookInstalled"))
    require_true(errors, "graphics summary.streamlineDlssInitObserved",
                 summary.get("streamlineDlssInitObserved"))
    require_equal(errors, "graphics summary.streamlineDlssInitCalls",
                  integer(summary.get("streamlineDlssInitCalls")), 1)
    require_equal(errors, "graphics summary.streamlineDlssDroppedInitCalls",
                  integer(summary.get("streamlineDlssDroppedInitCalls")), 0)
    for key in (
        "streamlineSurfacesRequested", "streamlineSurfacesTriggered",
        "streamlineSurfacesPairStaged", "streamlineSurfacesGpuComplete",
        "streamlineSurfacesPublished", "streamlineSurfacesSummaryWritten",
        "streamlineSurfacesPublishedBeforeDeferredSequence",
    ):
        require_true(errors, f"graphics summary.{key}", summary.get(key))
    require_equal(errors, "graphics summary.streamlineSurfacesFailed",
                  summary.get("streamlineSurfacesFailed"), False)
    for key in ("streamlineSurfacesStagedPackets",
                "streamlineSurfacesMappedPackets",
                "streamlineSurfacesPublishedPackets"):
        require_equal(errors, f"graphics summary.{key}",
                      integer(summary.get(key)), 2)
    require_equal(errors, "graphics summary.streamlineSurfacesCopyResourceCalls",
                  integer(summary.get("streamlineSurfacesCopyResourceCalls")), 8)
    require_equal(errors, "graphics summary.streamlineSurfacesPeakStagingBytes",
                  integer(summary.get("streamlineSurfacesPeakStagingBytes")),
                  PAIR_BYTES)
    require_equal(errors, "graphics summary Streamline trigger",
                  integer(summary.get("streamlineSurfacesTriggerPresent")),
                  integer(summary.get("graphicsSequenceTriggerPresent")))


def validate_exposure(
    streamline: dict[str, Any], packet: dict[str, Any], tag: dict[str, Any],
    errors: list[str], label: str,
) -> None:
    rows = streamline.get("exposureSampleRecords")
    if not isinstance(rows, list):
        errors.append("exposure: exposureSampleRecords is not an array")
        return
    matches = [row for row in rows if isinstance(row, dict)
               and integer(row.get("evaluateOrder"))
               == integer(packet.get("evaluateOrder"))]
    if len(matches) != 1:
        errors.append(
            f"{label} exposure: evaluate order {packet.get('evaluateOrder')} "
            f"must resolve once, found {len(matches)}")
        return
    row = matches[0]
    require_equal(errors, f"{label} exposure.viewport",
                  integer(row.get("viewport")), 3)
    if integer(row.get("frameToken")) == 0:
        errors.append(f"{label} exposure.frameToken: expected a retained nonzero reference address")
    require_equal(errors, f"{label} exposure.commandBuffer",
                  integer(row.get("commandBuffer")),
                  integer(packet.get("commandBuffer")))
    require_equal(errors, f"{label} exposure.evaluateTimestampQpc",
                  integer(row.get("evaluateTimestampQpc")),
                  integer(packet.get("evaluateEntryTimestampQpc")))
    require_equal(errors, f"{label} exposure.tagOrder",
                  integer(row.get("tagOrder")), integer(tag.get("order")))
    for key in ("descriptorReadable", "stagingCopyEnqueued",
                "evaluationAssociated", "payloadReadable"):
        require_true(errors, f"{label} exposure.{key}", row.get(key))
    require_equal(errors, f"{label} exposure.producerCompletionBoundary",
                  row.get("producerCompletionBoundary"),
                  "same-command-buffer-before-tagged-staging-copy")
    descriptor = row.get("descriptor")
    if not isinstance(descriptor, dict):
        errors.append(f"{label} exposure.descriptor: expected object")
        return
    for key, expected in (("width", 1), ("height", 1), ("mipLevels", 1),
                          ("arraySize", 1), ("sampleCount", 1)):
        require_equal(errors, f"{label} exposure.descriptor.{key}",
                      integer(descriptor.get(key)), expected)
    payload_size = integer(row.get("payloadSize"))
    payload_hex = row.get("payloadHex")
    format_id = integer(descriptor.get("format"))
    expected_payload_size = EXPOSURE_FORMAT_BYTES.get(format_id)
    if expected_payload_size is None:
        errors.append(
            f"{label} exposure.descriptor.format: unsupported DXGI format {format_id}")
    else:
        require_equal(errors, f"{label} exposure.payloadSize",
                      payload_size, expected_payload_size)
    if not isinstance(payload_hex, str) or len(payload_hex) != payload_size * 2:
        errors.append(
            f"{label} exposure.payloadHex: expected {payload_size * 2} hex digits")
    else:
        try:
            bytes.fromhex(payload_hex)
        except ValueError:
            errors.append(f"{label} exposure.payloadHex: contains non-hex data")
    tag_rows = tag.get("tags") if isinstance(tag.get("tags"), list) else []
    exposure_tags = [item for item in tag_rows if isinstance(item, dict)
                     and integer(item.get("bufferType")) == 13]
    if len(exposure_tags) != 1:
        errors.append(f"{label} exposure tag: expected one type-13 row, found {len(exposure_tags)}")
        return
    exposure_tag = exposure_tags[0]
    require_true(errors, f"{label} exposure tag.resourcePresent",
                 exposure_tag.get("resourcePresent"))
    resource = exposure_tag.get("resource")
    if not isinstance(resource, dict):
        errors.append(f"{label} exposure tag.resource: expected object")
        return
    require_equal(errors, f"{label} exposure.nativeResource",
                  integer(row.get("nativeResource")), integer(resource.get("native")))
    require_equal(errors, f"{label} exposure tag.resource.width",
                  integer(resource.get("width")), 1)
    require_equal(errors, f"{label} exposure tag.resource.height",
                  integer(resource.get("height")), 1)
    require_equal(errors, f"{label} exposure tag.resource.nativeFormat",
                  integer(resource.get("nativeFormat")), format_id)
    require_equal(errors, f"{label} exposure tag extent",
                  exposure_tag.get("extent"), [0, 0, 1, 1])
    first_order = integer(row.get("firstResourceTagOrder"))
    tag_order = integer(row.get("tagOrder"))
    first_qpc = integer(row.get("firstResourceTagTimestampQpc"))
    tag_qpc = integer(row.get("tagTimestampQpc"))
    copy_qpc = integer(row.get("stagingCopyTimestampQpc"))
    evaluate_qpc = integer(row.get("evaluateTimestampQpc"))
    ready_qpc = integer(row.get("payloadReadyTimestampQpc"))
    if not (0 < first_order <= tag_order < integer(row.get("evaluateOrder"))):
        errors.append(
            f"{label} exposure order: need first-resource <= tag < evaluate, "
            f"found {first_order}, {tag_order}, {row.get('evaluateOrder')}")
    if integer(row.get("resourceBindingOrdinal")) < 0:
        errors.append(f"{label} exposure.resourceBindingOrdinal: expected nonnegative")
    if not (0 < first_qpc <= tag_qpc <= copy_qpc <= evaluate_qpc <= ready_qpc):
        errors.append(
            f"{label} exposure QPC chronology: need first-resource <= tag <= "
            f"copy <= evaluate <= ready, found {first_qpc}, {tag_qpc}, "
            f"{copy_qpc}, {evaluate_qpc}, {ready_qpc}")


def validate_packet(
    packet: dict[str, Any], packet_index: int, streamline: dict[str, Any],
    errors: list[str], packet_root: Path,
) -> dict[str, Any]:
    label = f"frame{packet_index}"
    require_equal(errors, f"{label}.schema", packet.get("schema"),
                  "endfieldCapture.streamlineSurfacePacket.v1")
    require_true(errors, f"{label}.observationOnly", packet.get("observationOnly"))
    require_true(errors, f"{label}.originalEvaluateForwardedExactlyOnce",
                 packet.get("originalEvaluateForwardedExactlyOnce"))
    require_true(errors, f"{label}.complete", packet.get("complete"))
    require_equal(errors, f"{label}.packetIndex",
                  integer(packet.get("packetIndex")), packet_index)
    require_equal(errors, f"{label}.viewport", integer(packet.get("viewport")), 3)

    prior = integer(packet.get("priorPresentOrdinal"))
    closing = integer(packet.get("closingPresentOrdinal"))
    require_equal(errors, f"{label} closing Present", closing, prior + 1)
    entry = integer(packet.get("evaluateEntryTimestampQpc"))
    exit_qpc = integer(packet.get("evaluateExitTimestampQpc"))
    prior_qpc = integer(packet.get("priorPresentTimestampQpc"))
    closing_qpc = integer(packet.get("closingPresentTimestampQpc"))
    if not (0 < prior_qpc <= entry <= exit_qpc <= closing_qpc):
        errors.append(
            f"{label} QPC chronology: need prior <= entry <= exit <= closing, "
            f"found {prior_qpc}, {entry}, {exit_qpc}, {closing_qpc}")

    option = unique_order(streamline.get("optionsCalls"),
                          integer(packet.get("optionsOrder")),
                          f"{label} options", errors)
    token = unique_order(streamline.get("frameTokenCalls"),
                         integer(packet.get("frameTokenOrder")),
                         f"{label} frame token", errors)
    constants = unique_order(streamline.get("constantsCalls"),
                             integer(packet.get("constantsOrder")),
                             f"{label} constants", errors)
    evaluate = unique_order(streamline.get("evaluateCalls"),
                            integer(packet.get("evaluateOrder")),
                            f"{label} evaluate", errors)
    tag_orders = {integer(item.get("binding", {}).get("tagOrder"))
                  for item in packet.get("surfaces", [])
                  if isinstance(item, dict) and isinstance(item.get("binding"), dict)}
    if len(tag_orders) != 1:
        errors.append(f"{label} tag order: expected one shared order, found {sorted(tag_orders)}")
        tag = None
    else:
        tag = unique_order(streamline.get("tagCalls"), next(iter(tag_orders)),
                           f"{label} tags", errors)
        order_chain = [integer(packet.get(key)) for key in (
            "optionsOrder", "frameTokenOrder", "constantsOrder")]
        order_chain.extend((next(iter(tag_orders)),
                            integer(packet.get("evaluateOrder"))))
        if not all(left < right for left, right in zip(order_chain, order_chain[1:])):
            errors.append(
                f"{label} call order: need options < token < constants < tags < "
                f"evaluate, found {order_chain}")

    if option:
        expected_options = {
            "viewport": 3, "result": 0, "mode": 6,
            "outputWidth": WIDTH, "outputHeight": HEIGHT,
            "sharpness": 0, "preExposure": 1, "exposureScale": 1,
            "colorBuffersHDR": 1, "indicatorInvertAxisX": 0,
            "indicatorInvertAxisY": 1, "useAutoExposure": 0,
            "alphaUpscalingEnabled": 0,
        }
        for key, expected in expected_options.items():
            require_equal(errors, f"{label} options.{key}", option.get(key), expected)
        require_equal(errors, f"{label} options.presets",
                      option.get("presets"), [0, 0, 0, 0, 0, 0])
        require_true(errors, f"{label} options.readable", option.get("readable"))
        require_true(errors, f"{label} options.presentClockReadable",
                     option.get("presentClockReadable"))
        require_equal(errors, f"{label} options prior Present",
                      integer(option.get("priorPresentOrdinal")), prior)
    if token:
        for key in ("readable", "frameIndexSupplied", "presentClockReadable"):
            require_true(errors, f"{label} frame token.{key}", token.get(key))
        require_equal(errors, f"{label} frame token.result",
                      integer(token.get("result")), 0)
        require_equal(errors, f"{label} frame token.requestedFrameIndex",
                      integer(token.get("requestedFrameIndex")),
                      integer(packet.get("requestedFrameIndex")))
        require_equal(errors, f"{label} frame token.returnedToken",
                      integer(token.get("returnedToken")),
                      integer(packet.get("frameToken")))
        require_equal(errors, f"{label} frame token prior Present",
                      integer(token.get("priorPresentOrdinal")), prior)
    if constants:
        for key in ("readable", "presentClockReadable"):
            require_true(errors, f"{label} constants.{key}", constants.get(key))
        for key, expected in (("viewport", 3), ("result", 0), ("reset", 0)):
            require_equal(errors, f"{label} constants.{key}",
                          integer(constants.get(key)), expected)
        require_equal(errors, f"{label} constants.frameToken",
                      integer(constants.get("frameToken")),
                      integer(packet.get("frameToken")))
        require_equal(errors, f"{label} constants prior Present",
                      integer(constants.get("priorPresentOrdinal")), prior)
    if evaluate:
        for key in ("readable", "presentClockReadable", "chronologyCandidate",
                    "chronologyComplete"):
            require_true(errors, f"{label} evaluate.{key}", evaluate.get(key))
        for key, expected in (("viewport", 3), ("feature", 0), ("result", 0)):
            require_equal(errors, f"{label} evaluate.{key}",
                          integer(evaluate.get(key)), expected)
        for evaluate_key, packet_key in (
            ("frameToken", "frameToken"), ("commandBuffer", "commandBuffer"),
            ("matchedOptionsOrder", "optionsOrder"),
            ("matchedFrameTokenOrder", "frameTokenOrder"),
            ("matchedConstantsOrder", "constantsOrder"),
            ("priorPresentOrdinal", "priorPresentOrdinal"),
            ("nextPresentOrdinal", "closingPresentOrdinal"),
            ("nextPresentTimestampQpc", "closingPresentTimestampQpc"),
        ):
            require_equal(errors, f"{label} evaluate.{evaluate_key}",
                          integer(evaluate.get(evaluate_key)),
                          integer(packet.get(packet_key)))

    surfaces = packet.get("surfaces")
    if not isinstance(surfaces, list) or len(surfaces) != 4:
        errors.append(f"{label}.surfaces: expected 4 rows, found "
                      f"{len(surfaces) if isinstance(surfaces, list) else 'non-array'}")
        surfaces = []
    native_resources: set[int] = set()
    total_bytes = 0
    for index, contract in enumerate(EXPECTED_SURFACES):
        file_name, kind, buffer_type, format_id, expected_bytes = contract
        if index >= len(surfaces) or not isinstance(surfaces[index], dict):
            errors.append(f"{label} surface[{index}]: missing metadata row")
            continue
        row = surfaces[index]
        require_equal(errors, f"{label} surface[{index}].file",
                      row.get("file"), file_name)
        binding = row.get("binding")
        descriptor = row.get("descriptor")
        if not isinstance(binding, dict) or not isinstance(descriptor, dict):
            errors.append(f"{label} surface[{index}]: binding/descriptor must be objects")
            continue
        require_equal(errors, f"{label} surface[{index}].kind",
                      integer(binding.get("kind")), kind)
        require_equal(errors, f"{label} surface[{index}].bufferType",
                      integer(binding.get("bufferType")), buffer_type)
        require_equal(errors, f"{label} surface[{index}].lifecycle",
                      integer(binding.get("lifecycle")), 0)
        require_equal(errors, f"{label} surface[{index}].extent",
                      binding.get("extent"), [0, 0, WIDTH, HEIGHT])
        native = integer(binding.get("nativeResource"))
        if native <= 0:
            errors.append(f"{label} surface[{index}].nativeResource: expected nonzero")
        elif native in native_resources:
            errors.append(f"{label} surface[{index}].nativeResource: aliases another surface")
        native_resources.add(native)
        require_equal(errors, f"{label} surface[{index}].descriptor.resourceId",
                      integer(descriptor.get("resourceId")), native)
        for key, expected in (("width", WIDTH), ("height", HEIGHT),
                              ("mipLevels", 1), ("arraySize", 1),
                              ("format", format_id), ("sampleCount", 1),
                              ("sampleQuality", 0), ("rowBytes", expected_bytes // HEIGHT),
                              ("byteCount", expected_bytes)):
            require_equal(errors, f"{label} surface[{index}].descriptor.{key}",
                          integer(descriptor.get(key)), expected)
        path = packet_root / file_name
        try:
            actual_size = path.stat().st_size
        except OSError as exc:
            errors.append(f"{label} surface[{index}] file: cannot stat {path}: {exc}")
            continue
        require_equal(errors, f"{label} surface[{index}] file size",
                      actual_size, expected_bytes)
        expected_hash = row.get("sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            errors.append(f"{label} surface[{index}].sha256: expected 64 hex digits")
        else:
            try:
                int(expected_hash, 16)
            except ValueError:
                errors.append(f"{label} surface[{index}].sha256: contains non-hex data")
            else:
                try:
                    actual_hash = sha256_file(path)
                except OSError as exc:
                    errors.append(f"{label} surface[{index}] hash: cannot read {path}: {exc}")
                else:
                    require_equal(errors, f"{label} surface[{index}] SHA-256",
                                  actual_hash, expected_hash.lower())
        total_bytes += expected_bytes
    require_equal(errors, f"{label} packet bytes", total_bytes, PACKET_BYTES)
    if tag:
        require_true(errors, f"{label} tags.frameBased", tag.get("frameBased"))
        require_true(errors, f"{label} tags.readable", tag.get("readable"))
        require_true(errors, f"{label} tags.presentClockReadable",
                     tag.get("presentClockReadable"))
        for key, expected in (("viewport", 3), ("result", 0)):
            require_equal(errors, f"{label} tags.{key}", integer(tag.get(key)), expected)
        for tag_key, packet_key in (("frameToken", "frameToken"),
                                    ("commandBuffer", "commandBuffer"),
                                    ("priorPresentOrdinal", "priorPresentOrdinal")):
            require_equal(errors, f"{label} tags.{tag_key}",
                          integer(tag.get(tag_key)), integer(packet.get(packet_key)))
        tag_rows = tag.get("tags") if isinstance(tag.get("tags"), list) else []
        for index, contract in enumerate(EXPECTED_SURFACES):
            _, _, buffer_type, _, _ = contract
            matches = [item for item in tag_rows if isinstance(item, dict)
                       and integer(item.get("bufferType")) == buffer_type]
            if len(matches) != 1:
                errors.append(
                    f"{label} tags buffer type {buffer_type}: expected one row, "
                    f"found {len(matches)}")
                continue
            item = matches[0]
            require_equal(errors, f"{label} tags buffer type {buffer_type}.lifecycle",
                          integer(item.get("lifecycle")), 0)
            require_true(errors,
                         f"{label} tags buffer type {buffer_type}.resourcePresent",
                         item.get("resourcePresent"))
            require_equal(errors, f"{label} tags buffer type {buffer_type}.extent",
                          item.get("extent"), [0, 0, WIDTH, HEIGHT])
            resource = item.get("resource")
            packet_surfaces = packet.get("surfaces")
            if (not isinstance(resource, dict) or
                    not isinstance(packet_surfaces, list) or
                    index >= len(packet_surfaces) or
                    not isinstance(packet_surfaces[index], dict) or
                    not isinstance(packet_surfaces[index].get("binding"), dict)):
                errors.append(
                    f"{label} tags buffer type {buffer_type}: resource association "
                    "is not readable")
                continue
            require_equal(
                errors, f"{label} tags buffer type {buffer_type}.nativeResource",
                integer(resource.get("native")),
                integer(packet_surfaces[index]["binding"].get("nativeResource")))
        validate_exposure(streamline, packet, tag, errors, label)
    return {"packetIndex": packet_index,
            "requestedFrameIndex": integer(packet.get("requestedFrameIndex")),
            "priorPresentOrdinal": prior, "closingPresentOrdinal": closing,
            "packetBytes": total_bytes}


def build_report(capture: Path) -> dict[str, Any]:
    capture = capture.resolve()
    errors: list[str] = []
    session_audit = audit_session(capture, errors)
    summary = session_audit["graphicsSummary"]
    streamline = load_json(capture / "graphics/streamline_dlss.json", "Streamline")
    pair = load_json(capture / "graphics/streamline_surfaces/metadata.json",
                     "surface pair")
    audit_streamline_global(streamline, summary, errors)

    require_equal(errors, "surface pair.schema", pair.get("schema"),
                  "endfieldCapture.streamlineSurfacePair.v1")
    require_true(errors, "surface pair.observationOnly", pair.get("observationOnly"))
    require_true(errors, "surface pair.complete", pair.get("complete"))
    require_equal(errors, "surface pair.packetCount", integer(pair.get("packetCount")), 2)
    require_equal(errors, "surface pair.surfaceCountPerPacket",
                  integer(pair.get("surfaceCountPerPacket")), 4)
    require_equal(errors, "surface pair.copyResourceCalls",
                  integer(pair.get("copyResourceCalls")), 8)
    require_equal(errors, "surface pair.packetBytes",
                  integer(pair.get("packetBytes")), PACKET_BYTES)
    require_equal(errors, "surface pair.pairBytes",
                  integer(pair.get("pairBytes")), PAIR_BYTES)
    require_equal(errors, "surface pair.peakStagingBytes",
                  integer(pair.get("peakStagingBytes")), PAIR_BYTES)
    require_equal(errors, "surface pair trigger Present",
                  integer(pair.get("triggerPresentOrdinal")),
                  integer(summary.get("graphicsSequenceTriggerPresent")))

    packet_reports = []
    packets = []
    for index in range(2):
        root = capture / "graphics/streamline_surfaces" / f"frame{index}"
        packet = load_json(root / "metadata.json", f"frame{index}")
        packets.append(packet)
        packet_reports.append(validate_packet(
            packet, index, streamline, errors, root))

    first, second = packets
    require_equal(errors, "surface pair consecutive frame index",
                  integer(second.get("requestedFrameIndex")),
                  integer(first.get("requestedFrameIndex")) + 1)
    require_equal(errors, "surface pair consecutive prior Present",
                  integer(second.get("priorPresentOrdinal")),
                  integer(first.get("priorPresentOrdinal")) + 1)
    require_equal(errors, "surface pair shared Present boundary",
                  integer(first.get("closingPresentOrdinal")),
                  integer(second.get("priorPresentOrdinal")))
    require_equal(errors, "surface pair first trigger Present",
                  integer(first.get("priorPresentOrdinal")),
                  integer(pair.get("triggerPresentOrdinal")))
    frames = pair.get("frames")
    if not isinstance(frames, list) or len(frames) != 2:
        errors.append("surface pair.frames: expected exactly 2 rows")
    else:
        for index, packet in enumerate(packets):
            frame = frames[index]
            if not isinstance(frame, dict):
                errors.append(f"surface pair.frames[{index}]: expected object")
                continue
            for key in ("packetIndex", "requestedFrameIndex",
                        "priorPresentOrdinal", "closingPresentOrdinal"):
                require_equal(errors, f"surface pair.frames[{index}].{key}",
                              integer(frame.get(key)), integer(packet.get(key)))

    return {
        "schema": "endfield.endminf-streamline-surface-capture.v1",
        "status": "validated" if not errors else "rejected",
        "capture": str(capture),
        "sessionId": session_audit["session"].get("sessionId"),
        "surfaceContract": {
            "width": WIDTH, "height": HEIGHT,
            "formats": [row[3] for row in EXPECTED_SURFACES],
            "sizes": [row[4] for row in EXPECTED_SURFACES],
            "packetBytes": PACKET_BYTES, "pairBytes": PAIR_BYTES,
            "copyResourceCalls": 8,
        },
        "packets": packet_reports,
        "exposureSampleCount": integer(streamline.get("exposureSamples")),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture)
    except VerificationError as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    if report["status"] != "validated":
        for error in report["errors"]:
            print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
