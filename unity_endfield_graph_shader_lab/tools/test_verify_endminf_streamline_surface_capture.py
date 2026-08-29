#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify_endminf_streamline_surface_capture as subject


TEST_SURFACES = (
    ("input_color.bin", 0, 3, 26, 1),
    ("output_color.bin", 1, 4, 10, 2),
    ("depth.bin", 2, 0, 19, 2),
    ("motion.bin", 3, 1, 34, 1),
)


class StreamlineSurfaceCaptureTests(unittest.TestCase):
    def make_capture(self, root: Path) -> None:
        graphics = root / "graphics"
        surfaces_root = graphics / "streamline_surfaces"
        surfaces_root.mkdir(parents=True)
        (root / "session.json").write_text(json.dumps({
            "schema": "endfieldCapture.session.v1",
            "sessionId": "fixture",
            "graphicsProfile": "full",
        }), encoding="utf-8")
        (root / "runtime.status.json").write_text(json.dumps({
            "schema": "endfieldCapture.runtimeStatus.v1",
            "graphicsProfile": "full",
            "graphicsSelected": True,
            "graphicsHooksInstalled": True,
            "graphicsAttached": True,
            "graphicsDropped": 0,
            "graphicsSequenceFrames": 72,
            "graphicsSequenceAutomatic": True,
            "graphicsSequenceActive": False,
            "graphicsSequenceCapturePending": False,
            "framePending": False,
            "frameCompleted": True,
            "frameIncomplete": False,
            "frameFailed": False,
        }), encoding="utf-8")
        collected = root / "collected"
        collected.mkdir()
        (collected / "summary.json").write_text(json.dumps({
            "schema": "endfieldCapture.summary.v1", "records": 74,
            "dropped": 0, "invalidRecords": 0, "writerError": False,
            "complete": True,
        }), encoding="utf-8")
        summary = {
            "schema": "endfieldCapture.graphicsSummary.v1",
            "graphicsProfile": "full",
            "hooksInstalled": True,
            "attached": True,
            "quiescentCleanup": True,
            "complete": True,
            "dropped": 0,
            "sequenceAutomatic": True,
            "sequenceFrames": 72,
            "sequenceLimit": 72,
            "animatorSequenceTriggerGateMatched": True,
            "cadenceValid": True,
            "graphicsSequenceTriggerPresent": 100,
            "streamlineDlssObservationComplete": True,
            "streamlineDlssInitHookInstalled": True,
            "streamlineDlssInitObserved": True,
            "streamlineDlssInitCalls": 1,
            "streamlineDlssDroppedInitCalls": 0,
            "streamlineSurfacesRequested": True,
            "streamlineSurfacesTriggered": True,
            "streamlineSurfacesPairStaged": True,
            "streamlineSurfacesGpuComplete": True,
            "streamlineSurfacesPublished": True,
            "streamlineSurfacesFailed": False,
            "streamlineSurfacesStagedPackets": 2,
            "streamlineSurfacesMappedPackets": 2,
            "streamlineSurfacesPublishedPackets": 2,
            "streamlineSurfacesCopyResourceCalls": 8,
            "streamlineSurfacesTriggerPresent": 100,
            "streamlineSurfacesPeakStagingBytes": 12,
            "streamlineSurfacesSummaryWritten": True,
        }
        (graphics / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

        options, tokens, constants, tags, evaluates, exposures = [], [], [], [], [], []
        pair_frames = []
        for index in range(2):
            prior = 100 + index
            closing = prior + 1
            frame_index = 700 + index
            base_order = 10 + index * 10
            option_order, token_order = base_order, base_order + 1
            constants_order, tag_order, evaluate_order = base_order + 2, base_order + 3, base_order + 4
            token_value, command_buffer = 500 + index, 900
            options.append({
                "order": option_order, "viewport": 3, "result": 0, "mode": 6,
                "outputWidth": subject.WIDTH, "outputHeight": subject.HEIGHT,
                "sharpness": 0, "preExposure": 1, "exposureScale": 1,
                "colorBuffersHDR": 1, "indicatorInvertAxisX": 0,
                "indicatorInvertAxisY": 1, "useAutoExposure": 0,
                "alphaUpscalingEnabled": 0, "readable": True,
                "presets": [0, 0, 0, 0, 0, 0],
                "presentClockReadable": True, "priorPresentOrdinal": prior,
            })
            tokens.append({
                "order": token_order, "returnedToken": token_value,
                "frameIndexSupplied": True, "requestedFrameIndex": frame_index,
                "result": 0, "readable": True, "presentClockReadable": True,
                "priorPresentOrdinal": prior,
            })
            constants.append({
                "order": constants_order, "frameToken": token_value,
                "viewport": 3, "result": 0, "reset": 0, "readable": True,
                "presentClockReadable": True, "priorPresentOrdinal": prior,
            })
            tag_items = []
            surface_rows = []
            frame_root = surfaces_root / f"frame{index}"
            frame_root.mkdir()
            for surface_index, contract in enumerate(TEST_SURFACES):
                file_name, kind, buffer_type, format_id, size = contract
                payload = bytes([index * 8 + surface_index + 1]) * size
                (frame_root / file_name).write_bytes(payload)
                native = 1000 + index * 10 + surface_index
                tag_items.append({
                    "bufferType": buffer_type, "lifecycle": 0,
                    "extent": [0, 0, subject.WIDTH, subject.HEIGHT],
                    "resourcePresent": True,
                    "resource": {"native": native},
                })
                surface_rows.append({
                    "file": file_name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "binding": {
                        "kind": kind, "bufferType": buffer_type, "lifecycle": 0,
                        "tagOrder": tag_order, "nativeResource": native,
                        "extent": [0, 0, subject.WIDTH, subject.HEIGHT],
                    },
                    "descriptor": {
                        "resourceId": native, "width": subject.WIDTH,
                        "height": subject.HEIGHT, "mipLevels": 1,
                        "arraySize": 1, "format": format_id, "sampleCount": 1,
                        "sampleQuality": 0, "rowBytes": size // subject.HEIGHT,
                        "byteCount": size,
                    },
                })
            exposure_native = 2000 + index
            tag_items.append({
                "bufferType": 13, "lifecycle": 0, "extent": [0, 0, 1, 1],
                "resourcePresent": True,
                "resource": {"native": exposure_native, "width": 1,
                             "height": 1, "nativeFormat": 41},
            })
            tags.append({
                "order": tag_order, "frameBased": True, "frameToken": token_value,
                "viewport": 3, "commandBuffer": command_buffer, "result": 0,
                "readable": True, "presentClockReadable": True,
                "priorPresentOrdinal": prior, "tags": tag_items,
            })
            evaluates.append({
                "order": evaluate_order, "feature": 0, "frameToken": token_value,
                "commandBuffer": command_buffer, "result": 0, "viewport": 3,
                "matchedOptionsOrder": option_order,
                "matchedFrameTokenOrder": token_order,
                "matchedConstantsOrder": constants_order,
                "priorPresentOrdinal": prior,
                "nextPresentOrdinal": closing,
                "nextPresentTimestampQpc": 400 + index * 100,
                "chronologyCandidate": True, "chronologyComplete": True,
                "readable": True, "presentClockReadable": True,
            })
            exposures.append({
                "tagOrder": tag_order, "tagTimestampQpc": 170 + index * 100,
                "firstResourceTagOrder": tag_order,
                "firstResourceTagTimestampQpc": 160 + index * 100,
                "resourceBindingOrdinal": 4,
                "evaluateOrder": evaluate_order,
                "evaluateTimestampQpc": 200 + index * 100,
                "stagingCopyTimestampQpc": 180 + index * 100,
                "payloadReadyTimestampQpc": 450 + index * 100,
                "frameToken": token_value, "viewport": 3,
                "commandBuffer": command_buffer, "nativeResource": exposure_native,
                "descriptor": {"width": 1, "height": 1, "mipLevels": 1,
                               "arraySize": 1, "sampleCount": 1, "format": 41},
                "payloadSize": 4, "payloadHex": "0000803f",
                "descriptorReadable": True, "stagingCopyEnqueued": True,
                "evaluationAssociated": True, "payloadReadable": True,
                "producerCompletionBoundary":
                    "same-command-buffer-before-tagged-staging-copy",
            })
            packet = {
                "schema": "endfieldCapture.streamlineSurfacePacket.v1",
                "observationOnly": True,
                "originalEvaluateForwardedExactlyOnce": True,
                "packetIndex": index, "requestedFrameIndex": frame_index,
                "viewport": 3, "optionsOrder": option_order,
                "frameTokenOrder": token_order, "constantsOrder": constants_order,
                "evaluateOrder": evaluate_order,
                "evaluateEntryTimestampQpc": 200 + index * 100,
                "evaluateExitTimestampQpc": 300 + index * 100,
                "priorPresentOrdinal": prior,
                "priorPresentTimestampQpc": 100 + index * 100,
                "closingPresentOrdinal": closing,
                "closingPresentTimestampQpc": 400 + index * 100,
                "frameToken": token_value, "commandBuffer": command_buffer,
                "surfaces": surface_rows, "complete": True,
            }
            (frame_root / "metadata.json").write_text(json.dumps(packet), encoding="utf-8")
            pair_frames.append({key: packet[key] for key in (
                "packetIndex", "requestedFrameIndex", "priorPresentOrdinal",
                "closingPresentOrdinal")})

        streamline = {
            "schema": "endfieldCapture.streamlineDlss.v4",
            "observationOnly": True, "requested": True, "configured": True,
            "exactBuildValidated": True, "coreModuleLoaded": True,
            "coreModuleValidated": True, "dlssModuleLoaded": True,
            "dlssModuleValidated": True, "coreHooksInstalled": True,
            "initHookInstalled": True, "initObserved": True,
            "initCalls": 1, "droppedInitCalls": 0,
            "initialization": {
                "result": 0, "readable": True, "truncated": False,
                "features": [0],
            },
            "dlssOptionsHookInstalled": True,
            "dlssOptionsDirectHookInstalled": True,
            "presentClockConfigured": True, "callbacksQuiescent": True,
            "recordsTruncated": False, "recordsUnreadable": False,
            "apiCallFailed": False, "exposureCaptureRequested": True,
            "exposureCaptureComplete": True, "exposureCaptureFailed": False,
            "exposureSamples": 2, "matchedExposureSamples": 2,
            "droppedExposureSamples": 0, "failed": False,
            "presentClockFailures": 0, "droppedFrameTokenCalls": 0,
            "droppedOptionsCalls": 0, "droppedTagCalls": 0,
            "droppedConstantsCalls": 0, "droppedEvaluateCalls": 0,
            "truncatedTagPayloads": 0, "truncatedEvaluatePayloads": 0,
            "matchedTargetViewportDlssSequences": 2,
            "rejectedTargetViewportDlssSequences": 0,
            "pendingDlssSequences": 0, "sequenceComplete": True,
            "optionsCalls": options, "frameTokenCalls": tokens,
            "constantsCalls": constants, "tagCalls": tags,
            "evaluateCalls": evaluates, "exposureSampleRecords": exposures,
        }
        (graphics / "streamline_dlss.json").write_text(
            json.dumps(streamline), encoding="utf-8")
        (surfaces_root / "metadata.json").write_text(json.dumps({
            "schema": "endfieldCapture.streamlineSurfacePair.v1",
            "observationOnly": True, "packetCount": 2,
            "surfaceCountPerPacket": 4, "copyResourceCalls": 8,
            "packetBytes": 6, "pairBytes": 12,
            "triggerPresentOrdinal": 100, "peakStagingBytes": 12,
            "frames": pair_frames, "complete": True,
        }), encoding="utf-8")

    def build(self, root: Path) -> dict:
        with mock.patch.object(subject, "EXPECTED_SURFACES", TEST_SURFACES), \
             mock.patch.object(subject, "PACKET_BYTES", 6), \
             mock.patch.object(subject, "PAIR_BYTES", 12):
            return subject.build_report(root)

    def test_exact_production_contract_is_pinned(self) -> None:
        self.assertEqual([26, 10, 19, 34],
                         [row[3] for row in subject.EXPECTED_SURFACES])
        self.assertEqual([33_177_600, 66_355_200, 66_355_200, 33_177_600],
                         [row[4] for row in subject.EXPECTED_SURFACES])
        self.assertEqual(199_065_600, subject.PACKET_BYTES)
        self.assertEqual(398_131_200, subject.PAIR_BYTES)

    def test_complete_capture_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_capture(root)
            report = self.build(root)
            self.assertEqual("validated", report["status"], report["errors"])
            self.assertEqual([], report["errors"])

    def test_hash_mismatch_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_capture(root)
            path = root / "graphics/streamline_surfaces/frame0/input_color.bin"
            path.write_bytes(b"x")
            report = self.build(root)
            self.assertEqual("rejected", report["status"])
            self.assertIn(
                "frame0 surface[0] SHA-256: expected",
                "\n".join(report["errors"]),
            )

    def test_nonconsecutive_frame_index_and_present_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_capture(root)
            path = root / "graphics/streamline_surfaces/frame1/metadata.json"
            packet = json.loads(path.read_text(encoding="utf-8"))
            packet["requestedFrameIndex"] += 1
            packet["priorPresentOrdinal"] += 1
            path.write_text(json.dumps(packet), encoding="utf-8")
            report = self.build(root)
            text = "\n".join(report["errors"])
            self.assertIn("surface pair consecutive frame index", text)
            self.assertIn("surface pair consecutive prior Present", text)

    def test_exposure_descriptor_and_association_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_capture(root)
            path = root / "graphics/streamline_dlss.json"
            streamline = json.loads(path.read_text(encoding="utf-8"))
            row = streamline["exposureSampleRecords"][0]
            row["descriptor"]["width"] = 2
            row["commandBuffer"] = 901
            path.write_text(json.dumps(streamline), encoding="utf-8")
            report = self.build(root)
            text = "\n".join(report["errors"])
            self.assertIn("frame0 exposure.descriptor.width", text)
            self.assertIn("frame0 exposure.commandBuffer", text)

    def test_missing_initialization_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_capture(root)
            path = root / "graphics/streamline_dlss.json"
            streamline = json.loads(path.read_text(encoding="utf-8"))
            streamline["initObserved"] = False
            streamline["initCalls"] = 0
            streamline["initialization"] = {}
            path.write_text(json.dumps(streamline), encoding="utf-8")
            report = self.build(root)
            text = "\n".join(report["errors"])
            self.assertIn("Streamline.initObserved", text)
            self.assertIn("Streamline.initCalls", text)
            self.assertIn("Streamline.initialization.features", text)

    def test_incomplete_graphics_summary_is_rejected_first(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_capture(root)
            path = root / "graphics/summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["complete"] = False
            path.write_text(json.dumps(summary), encoding="utf-8")
            report = self.build(root)
            self.assertEqual(
                "graphics summary.complete: expected True, found False",
                report["errors"][0],
            )

    def test_incomplete_collection_summary_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_capture(root)
            path = root / "collected/summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["invalidRecords"] = 2
            summary["complete"] = False
            path.write_text(json.dumps(summary), encoding="utf-8")
            report = self.build(root)
            text = "\n".join(report["errors"])
            self.assertIn("collection summary.complete", text)
            self.assertIn("collection summary.invalidRecords", text)


if __name__ == "__main__":
    unittest.main()
