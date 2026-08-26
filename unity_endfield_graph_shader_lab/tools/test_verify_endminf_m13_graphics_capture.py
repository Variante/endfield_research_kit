#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("verify_endminf_m13_graphics_capture.py")
SPEC = importlib.util.spec_from_file_location("m13_capture", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def draw() -> dict:
    return {
        "count": 6,
        "indexedInstanced": True,
        "priorityShaderPair": True,
        "instanceCount": 1,
        "shaders": [
            {"stage": 0, "identityHash": MODULE.VS_IDENTITY},
            {"stage": 4, "identityHash": MODULE.PS_IDENTITY},
        ],
    }


def metadata() -> dict:
    return {
        "captureIncomplete": False,
        "captureFailed": False,
        "resourceSelectionTruncated": False,
        "resourcesFile": "resources.bin",
        "drawRecords": [draw()],
        "selectedResourceRecords": [
            {
                "captureKind": MODULE.SRV_TEXTURE_KIND,
                "stage": MODULE.PIXEL_STAGE,
                "slot": slot,
                "byteSize": MODULE.EXPECTED_TEXTURES[slot][2],
                "width": MODULE.EXPECTED_TEXTURES[slot][0],
                "height": MODULE.EXPECTED_TEXTURES[slot][1],
                "format": MODULE.BC7_UNORM_SRGB,
                "viewFormat": MODULE.BC7_UNORM_SRGB,
                "subresource": 0,
                "blobOffset": sum(MODULE.EXPECTED_TEXTURES[index][2]
                                  for index in range(slot)),
                "blobBytes": MODULE.EXPECTED_TEXTURES[slot][2],
                "failure": 0,
                "completed": True,
            }
            for slot in range(5)
        ],
    }


class M13CaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_session(self, value: dict, resource_bytes: int | None = None) -> Path:
        root = Path(self.temp.name)
        frame = root / "graphics" / "frames" / "123"
        frame.mkdir(parents=True)
        (frame / "metadata.json").write_text(json.dumps(value), encoding="utf-8")
        if resource_bytes is None:
            resource_bytes = sum(row[2] for row in MODULE.EXPECTED_TEXTURES.values())
        (frame / "resources.bin").write_bytes(bytes(resource_bytes))
        return root

    def test_accepts_exact_draw_and_five_complete_textures(self) -> None:
        report = MODULE.verify_session(self.make_session(metadata()))
        self.assertEqual(report["status"], "exact_m13_draw_textures_captured")
        self.assertEqual(len(report["matchedDraws"][0]["textures"]), 5)

    def test_rejects_missing_texture_slot(self) -> None:
        value = metadata()
        value["selectedResourceRecords"].pop()
        with self.assertRaisesRegex(MODULE.CaptureError, r"missing slots: \[4\]"):
            MODULE.verify_session(self.make_session(value))

    def test_rejects_incomplete_texture(self) -> None:
        value = metadata()
        value["selectedResourceRecords"][2]["completed"] = False
        with self.assertRaisesRegex(MODULE.CaptureError, "t2 did not complete"):
            MODULE.verify_session(self.make_session(value))

    def test_rejects_texture_outside_resource_blob(self) -> None:
        with self.assertRaisesRegex(MODULE.CaptureError, "t4 exceeds"):
            MODULE.verify_session(self.make_session(
                metadata(),
                resource_bytes=sum(row[2] for row in MODULE.EXPECTED_TEXTURES.values()) - 1,
            ))

    def test_rejects_non_bc7_texture_view(self) -> None:
        value = metadata()
        value["selectedResourceRecords"][1]["viewFormat"] = 28
        with self.assertRaisesRegex(MODULE.CaptureError, "t1 view is not BC7 sRGB"):
            MODULE.verify_session(self.make_session(value))


if __name__ == "__main__":
    unittest.main()
