from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_m27_fixed_state_capture",
    HERE / "verify_endminf_m27_fixed_state_capture.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def pipeline_state() -> dict[str, object]:
    return {
        "valid": True,
        "target": {"width": 3840, "height": 2160,
                   "renderTargetCount": 5, "depthBound": True},
        "viewport": {"count": 1, "x": 0.0, "y": 0.0,
                     "width": 3840.0, "height": 2160.0,
                     "minDepth": 0.0, "maxDepth": 1.0},
        "scissor": {"count": 1, "left": 0, "top": 0,
                    "right": 3840, "bottom": 2160},
        "samplers": [
            {"slot": slot, "bound": True, "filter": 20,
             "addressU": 1, "addressV": 1, "addressW": 1,
             "comparison": 1, "mipBias": 0.0, "maxAnisotropy": 0,
             "minLod": 0.0, "maxLod": 1000.0,
             "borderColor": [0.0, 0.0, 0.0, 0.0]}
            for slot in range(3)
        ],
        "blend": {"enabled": False, "source": 2, "destination": 1,
                  "operation": 1, "sourceAlpha": 2,
                  "destinationAlpha": 1, "operationAlpha": 1,
                  "writeMask": 15, "factor": [1.0, 1.0, 1.0, 1.0],
                  "sampleMask": 0xffffffff},
        "depthStencil": {"depthEnabled": True, "writeMask": 1,
                         "function": 7, "stencilEnabled": True,
                         "stencilReference": 0},
        "rasterizer": {"fillMode": 3, "cullMode": 3,
                       "frontCounterClockwise": True,
                       "depthClipEnabled": True, "scissorEnabled": True,
                       "multisampleEnabled": False,
                       "antialiasedLineEnabled": False},
    }


def draw() -> dict[str, object]:
    return {
        "drawOrdinal": 38, "count": 72, "start": 0,
        "indexedInstanced": True, "topology": 4,
        "priorityShaderPair": True, "instanceCount": 1,
        "baseVertex": 0, "startInstance": 0,
        "shaders": [
            {"stage": 0, "identityHash": MODULE.VERTEX_IDENTITY},
            {"stage": 4, "identityHash": MODULE.PIXEL_IDENTITY},
        ],
        "inputAssembler": {
            "vertexBuffers": [
                {"slot": 0, "objectId": 100, "stride": 68, "offset": 0},
                {"slot": 1, "objectId": 101, "stride": 0, "offset": 0},
            ],
            "indexBuffer": {"objectId": 100, "format": 57, "offset": 0},
        },
        "pipelineState": pipeline_state(),
    }


class M27FixedStateCaptureTests(unittest.TestCase):
    def build(self, mutate=None) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            frame_root = capture / "graphics/frames/2723"
            frame_root.mkdir(parents=True)
            session = {
                "schema": "endfieldCapture.session.v1",
                "sessionId": MODULE.EXPECTED_SESSION,
                "providers": 1,
                "graphicsProfile": "targeted",
                "evidenceLabel": "forced-d3d11",
                "gameBuild": MODULE.EXPECTED_GAME_BUILD,
                "targetSha256": MODULE.EXPECTED_TARGET_SHA256,
            }
            runtime = {
                "schema": "endfieldCapture.runtimeStatus.v1",
                "runtimeMode": "d3d11-proxy", "graphicsSelected": True,
                "graphicsHooksInstalled": True, "graphicsAttached": True,
                "graphicsRequests": 1, "graphicsRequestsIgnored": 0,
                "graphicsDropped": 0, "framePending": False,
                "frameCompleted": True, "frameIncomplete": False,
                "frameFailed": False,
            }
            collected = {
                "schema": "endfieldCapture.summary.v1", "records": 3,
                "dropped": 0, "invalidRecords": 0, "writerError": False,
                "complete": True,
            }
            graphics = {
                "schema": "endfieldCapture.graphicsSummary.v1",
                "runtimeMode": "d3d11-proxy", "evidenceLabel": "forced-d3d11",
                "graphicsProfile": "targeted", "hooksInstalled": True,
                "attached": True, "dropped": 0, "pendingRequest": False,
                "quiescentCleanup": True, "complete": True,
            }
            metadata = {
                "frame": 2723, "captureIncomplete": False,
                "captureFailed": False, "droppedEvents": 0,
                "drawRecordsTruncated": False, "drawRecords": [draw()],
            }
            payload = {
                "session": session, "runtime": runtime,
                "collected": collected, "graphics": graphics,
                "metadata": metadata,
            }
            if mutate is not None:
                mutate(payload)
            (capture / "session.json").write_text(
                json.dumps(session), encoding="utf-8")
            (capture / "runtime.status.json").write_text(
                json.dumps(runtime), encoding="utf-8")
            (capture / "collected").mkdir()
            (capture / "collected/summary.json").write_text(
                json.dumps(collected), encoding="utf-8")
            (capture / "graphics/summary.json").write_text(
                json.dumps(graphics), encoding="utf-8")
            (frame_root / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8")
            return MODULE.build_report(capture)

    def test_complete_exact_state_passes(self) -> None:
        report = self.build()
        self.assertEqual(
            report["status"], "validated_exact_m27_liteffect_fixed_state")
        self.assertEqual(report["drawCount"], 1)
        self.assertEqual(report["closedReplayState"]["depthFunction"], 7)
        self.assertEqual(report["closedReplayState"]["cullMode"], 3)

    def test_incomplete_graphics_summary_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "graphics summary complete"):
            self.build(lambda value: value["graphics"].update(complete=False))

    def test_depth_function_drift_fails_closed(self) -> None:
        def mutate(value):
            value["metadata"]["drawRecords"][0]["pipelineState"] \
                ["depthStencil"]["function"] = 8

        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "GREATER_EQUAL"):
            self.build(mutate)

    def test_cull_mode_drift_fails_closed(self) -> None:
        def mutate(value):
            value["metadata"]["drawRecords"][0]["pipelineState"] \
                ["rasterizer"]["cullMode"] = 1

        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "cullMode drifted"):
            self.build(mutate)

    def test_scissor_state_drift_fails_closed(self) -> None:
        def mutate(value):
            value["metadata"]["drawRecords"][0]["pipelineState"] \
                ["rasterizer"]["scissorEnabled"] = False

        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "scissorEnabled drifted"):
            self.build(mutate)


if __name__ == "__main__":
    unittest.main()
