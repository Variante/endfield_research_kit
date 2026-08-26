#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("verify_endminf_m27_graphics_capture.py")
SPEC = importlib.util.spec_from_file_location("m27_capture", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def draw() -> dict:
    return {
        "count": MODULE.EXPECTED_COUNT,
        "indexedInstanced": True,
        "priorityShaderPair": True,
        "priorityM27Geometry": True,
        "instanceCount": 1,
        "startInstance": 0,
        "shaders": [
            {"stage": 0, "identityHash": MODULE.VS_IDENTITY,
             "bytecodeSize": MODULE.VS_BYTES},
            {"stage": 4, "identityHash": MODULE.PS_IDENTITY,
             "bytecodeSize": MODULE.PS_BYTES},
        ],
        "constantBuffers": [
            {
                "stage": stage,
                "slot": slot,
                "firstConstant": 100,
                "numConstants": 4096,
                "capturedConstants": count,
                "rangeValid": True,
                "metadataValid": True,
                "truncated": True,
                "dataHex": "00" * count * 16,
            }
            for (stage, slot), count in MODULE.REQUIRED_CONSTANTS.items()
        ],
    }


class M27CaptureTests(unittest.TestCase):
    def make_session(self, value: dict) -> Path:
        root = Path(self.temp.name)
        frame = root / "graphics" / "frames" / "123"
        frame.mkdir(parents=True)
        (frame / "metadata.json").write_text(json.dumps(value), encoding="utf-8")
        return root

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_accepts_complete_exact_draw(self) -> None:
        report = MODULE.verify_session(self.make_session({
            "captureIncomplete": False,
            "captureFailed": False,
            "drawRecords": [draw()],
        }))
        self.assertEqual(report["status"], "exact_m27_draw_ranges_captured")
        self.assertEqual(len(report["matchedDraws"]), 1)

    def test_rejects_missing_c105(self) -> None:
        value = draw()
        next(row for row in value["constantBuffers"]
             if row["stage"] == 4 and row["slot"] == 1)["capturedConstants"] = 105
        with self.assertRaisesRegex(MODULE.CaptureError, "need 106"):
            MODULE.verify_session(self.make_session({"drawRecords": [value]}))

    def test_rejects_old_profile_without_geometry_marker(self) -> None:
        value = draw()
        value.pop("priorityM27Geometry")
        with self.assertRaisesRegex(MODULE.CaptureError, "predates this profile"):
            MODULE.verify_session(self.make_session({"drawRecords": [value]}))


if __name__ == "__main__":
    unittest.main()
