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
    samplers = [{"slot": slot, "bound": True, "filter": 21,
                 "addressU": 1, "addressV": 1, "addressW": 1,
                 "comparison": 1, "maxAnisotropy": 1}
                for slot in range(3)]
    return {
        "valid": True,
        "target": {"width": 1920, "height": 1080,
                   "renderTargetCount": 2, "depthBound": True},
        "depthTarget": {"width": 1920, "height": 1080},
        "viewport": {"count": 1},
        "scissor": {"count": 1},
        "samplers": samplers,
        "blend": {"enabled": True},
        "depthStencil": {"depthEnabled": False},
        "rasterizer": {"fillMode": 3},
    }


class DrawContractCaptureTests(unittest.TestCase):
    def build(self, metadata: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            frame = capture / "graphics/frames/1"
            frame.mkdir(parents=True)
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

    def test_repeated_ordinal_fails_closed(self) -> None:
        payload = self.payload()
        payload["drawRecords"][1]["drawOrdinal"] = 20
        with self.assertRaisesRegex(MODULE.ContractError,
                                    "repeats drawOrdinal"):
            self.build(payload)


if __name__ == "__main__":
    unittest.main()
