from __future__ import annotations

import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_draw_contract_capture",
    HERE / "verify_endminf_draw_contract_capture.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def draw(owner_name: str, ordinal: int) -> dict[str, object]:
    owner = MODULE.CLOSURE.OWNERS[owner_name]
    values = [0.0] * 20
    values[4:8] = owner["c1"]
    values[16:20] = owner["c4"]
    stride = 60 if owner_name == "M29" else 36
    return {
        "drawOrdinal": ordinal,
        "count": min(owner["counts"]),
        "start": 10,
        "baseVertex": 20,
        "topology": 4,
        "shaders": [
            {"stage": 0, "identityHash": owner["vertex"]},
            {"stage": 4, "identityHash": owner["pixel"]},
        ],
        "constantBuffers": [{"stage": 4, "slot": 3,
                             "rangeValid": True, "metadataValid": True,
                             "dataHex": struct.pack("<20f", *values).hex()}],
        "resources": [
            {"objectId": 100, "stage": 0, "slot": 0},
            {"objectId": 101, "stage": 0, "slot": 1},
            {"objectId": 100, "stage": 0, "slot": 0},
        ],
        "inputAssembler": {
            "vertexBuffers": [
                {"slot": 0, "objectId": 100, "stride": stride,
                 "offset": 4096},
                {"slot": 1, "objectId": 101, "stride": 0, "offset": 0},
            ],
            "indexBuffer": {"objectId": 100, "format": 57,
                            "offset": 8192},
        },
        "pipelineState": pipeline_state(),
    }


def pipeline_state() -> dict[str, object]:
    samplers = [{"slot": slot, "bound": True,
                 "filter": (0, 20, 21)[slot],
                 "addressU": 3 if slot == 0 else 1,
                 "addressV": 3 if slot == 0 else 1,
                 "addressW": 3 if slot == 0 else 1,
                 "comparison": 1, "maxAnisotropy": 1,
                 "mipBias": 0.0, "minLod": 0.0, "maxLod": 1000.0,
                 "borderColor": [0.0, 0.0, 0.0, 0.0]}
                for slot in range(3)]
    render_targets = [
        {"slot": slot, "bound": slot < 2,
         "width": 3840 if slot < 2 else 0,
         "height": 2160 if slot < 2 else 0,
         "textureFormat": 26 if slot < 2 else 0,
         "viewFormat": 26 if slot < 2 else 0,
         "viewDimension": 4 if slot < 2 else 0,
         "sampleCount": 1 if slot < 2 else 0}
        for slot in range(8)]
    blend_targets = [
        {"slot": slot, "enabled": slot < 2, "source": 2,
         "destination": 6 if slot < 2 else 1, "operation": 1,
         "sourceAlpha": 2,
         "destinationAlpha": 6 if slot < 2 else 1,
         "operationAlpha": 1, "writeMask": 15}
        for slot in range(8)]
    blend_targets[1].update({
        "source": 3, "destination": 4,
        "sourceAlpha": 2, "destinationAlpha": 2,
    })
    return {
        "valid": True,
        "target": {"width": 3840, "height": 2160,
                   "renderTargetCount": 2, "depthBound": True},
        "renderTargets": render_targets,
        "depthTarget": {"width": 3840, "height": 2160,
                        "textureFormat": 19, "viewFormat": 20,
                        "viewDimension": 3, "viewFlags": 3,
                        "sampleCount": 1},
        "viewport": {"count": 1, "x": 0.0, "y": 0.0,
                     "width": 3840.0, "height": 2160.0,
                     "minDepth": 0.0, "maxDepth": 1.0},
        "scissor": {"count": 1, "left": 0, "top": 0,
                    "right": 3840, "bottom": 2160},
        "samplers": samplers,
        "blend": {"alphaToCoverageEnabled": False,
                  "independentBlendEnabled": True,
                  "factor": [1.0, 1.0, 1.0, 1.0],
                  "sampleMask": 0xffffffff, "targets": blend_targets},
        "depthStencil": {"depthEnabled": True, "writeMask": 0,
                         "function": 7, "stencilEnabled": True,
                         "stencilReference": 0, "stencilReadMask": 255,
                         "stencilWriteMask": 255,
                         "frontFace": {"failOperation": 1,
                                       "depthFailOperation": 1,
                                       "passOperation": 1, "function": 8},
                         "backFace": {"failOperation": 1,
                                      "depthFailOperation": 1,
                                      "passOperation": 1, "function": 8}},
        "rasterizer": {"fillMode": 3, "cullMode": 1,
                       "frontCounterClockwise": True,
                       "depthClipEnabled": True, "scissorEnabled": True,
                       "multisampleEnabled": False,
                       "antialiasedLineEnabled": False, "depthBias": 0,
                       "depthBiasClamp": 0.0,
                       "slopeScaledDepthBias": 0.0,
                       "forcedSampleCount": 0},
    }


class DrawContractCaptureTests(unittest.TestCase):
    def build(self, metadata: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            frame = capture / "graphics/frames/1"
            frame.mkdir(parents=True)
            (capture / "graphics/summary.json").write_text(json.dumps({
                "complete": True, "cadenceValid": True, "dropped": 0,
                "deferredFailed": False, "deferredStagedSlots": 72,
                "deferredDrainedSlots": 72,
                "deferredPublishedSlots": 72,
            }), encoding="utf-8")
            (frame / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8")
            return MODULE.build_report(capture)

    def payload(self) -> dict[str, object]:
        return {"frame": 1, "drawRecords": [
            draw("M31", 20), draw("M29", 30), draw("M30", 40)]}

    def test_complete_contract_passes_and_sorts_chronology(self) -> None:
        report = self.build(self.payload())
        self.assertEqual(
            report["status"],
            "validated_draw_local_ia_state_and_chronology")
        self.assertEqual(
            [row["owner"] for row in report["chronology"][0]["draws"]],
            ["M31", "M29", "M30"])
        self.assertEqual(
            report["owners"]["M29"]["draws"][0]
                  ["inputAssembler"]["vertexBuffers"][0]["offset"], 4096)

    def test_missing_draw_local_ia_fails_closed(self) -> None:
        payload = self.payload()
        del payload["drawRecords"][1]["inputAssembler"]
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "draw-local inputAssembler"):
            self.build(payload)

    def test_missing_sampler_two_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][1]["pipelineState"]["samplers"] = \
            payload["drawRecords"][1]["pipelineState"]["samplers"][:2]
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "PS samplers 0-2"):
            self.build(payload)

    def test_missing_dsv_flags_fails_closed(self) -> None:
        payload = self.payload()
        del payload["drawRecords"][0]["pipelineState"]["depthTarget"]["viewFlags"]
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "depthTarget viewFlags"):
            self.build(payload)

    def test_missing_blend_target_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["blend"]["targets"].pop()
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "all eight blend targets"):
            self.build(payload)

    def test_m31_non_keep_stencil_face_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["depthStencil"] \
            ["frontFace"]["passOperation"] = 2
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "frontFace differs from serialized M31"):
            self.build(payload)

    def test_m31_rtv1_blend_fails_closed_on_serialized_state_drift(self) -> None:
        payload = self.payload()
        target = payload["drawRecords"][0]["pipelineState"]["blend"] \
            ["targets"][1]
        target["enabled"] = False
        target["source"] = 1
        target["destination"] = 1
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "blend target 1 is not enabled"):
            self.build(payload)

    def test_m31_rtv1_descriptor_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["renderTargets"][1] \
            ["viewDimension"] = 99
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "RTV 1 viewDimension"):
            self.build(payload)

    def test_m31_dsv_dimension_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["depthTarget"] \
            ["viewDimension"] = 99
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "depthTarget viewDimension"):
            self.build(payload)

    def test_m31_dsv_must_be_read_only_depth(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["depthTarget"] \
            ["viewFlags"] = 0
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "must make depth read-only"):
            self.build(payload)

    def test_m31_read_only_depth_without_stencil_is_recorded(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["depthTarget"] \
            ["viewFlags"] = 1
        report = self.build(payload)
        observed = report["owners"]["M31"]["draws"][0] \
            ["pipelineState"]["depthTarget"]["viewFlags"]
        self.assertEqual(observed, 1)

    def test_m31_disabled_blend_slot_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["blend"]["targets"][2] \
            ["destination"] = 6
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "blend target 2 destination"):
            self.build(payload)

    def test_m31_alpha_to_coverage_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["blend"] \
            ["alphaToCoverageEnabled"] = True
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "alpha-to-coverage/independent blend"):
            self.build(payload)

    def test_m31_raster_bias_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][0]["pipelineState"]["rasterizer"] \
            ["depthBias"] = 1
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "bias/forced-sample state"):
            self.build(payload)

    def test_repeated_ordinal_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][1]["drawOrdinal"] = 20
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "repeats drawOrdinal"):
            self.build(payload)


if __name__ == "__main__":
    unittest.main()
