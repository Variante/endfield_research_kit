from __future__ import annotations

import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_uber_capture.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_uber_capture", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def fixture(mode: float = 3.0, priority: bool = True,
            budget: int = MODULE.MINIMUM_RESOURCE_BUDGET) -> tuple[
                dict[str, object], dict[str, object], bytes]:
    values = [0.0] * (256 * 4)
    b0_first = 4
    b1_first = 64
    values[(b0_first + 27) * 4:(b0_first + 28) * 4] = [1.0, 1.0, 0.0, 0.0]
    values[b1_first * 4:(b1_first + 1) * 4] = [0.51, 0.53, 0.10, 1.0]
    values[(b1_first + 25) * 4:(b1_first + 26) * 4] = [mode, 0.09, 0.0, 0.0]
    blob = struct.pack(f"<{len(values)}f", *values)
    session = {
        "graphicsProfile": "targeted",
        "graphicsResourceBudgetBytes": budget,
        "qpcFrequency": 10_000_000,
    }
    metadata = {
        "frame": 7,
        "selectedResourceRecords": [{
            "captureKind": 2, "objectId": 100,
            "blobOffset": 0, "blobBytes": len(blob),
            "completed": True, "failure": 0,
        }],
        "fullscreenResolvers": [{
            "fullscreenOrdinal": 24,
            "priorityEndminfUber": priority,
            "shaders": [{
                "stage": 4, "identityHash": MODULE.PIXEL_IDENTITY,
                "bytecodeSize": 4836,
            }],
            "psConstantBuffers": [
                {"slot": 0, "bufferId": 100, "firstConstant": b0_first,
                 "numConstants": 28, "rangeValid": True},
                {"slot": 1, "bufferId": 100, "firstConstant": b1_first,
                 "numConstants": 32, "rangeValid": True},
            ],
        }],
    }
    return session, metadata, blob


class UberCaptureTests(unittest.TestCase):
    def build(self, session: dict[str, object], metadata: dict[str, object],
              blob: bytes) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / "session.json").write_text(
                json.dumps(session), encoding="utf-8")
            frame = capture / "graphics/frames/7"
            frame.mkdir(parents=True)
            (frame / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8")
            (frame / "resources.bin").write_bytes(blob)
            return MODULE.build_report(capture)

    def test_exact_live_binding_passes(self) -> None:
        report = self.build(*fixture())
        self.assertEqual(report["status"], "validated_exact_live_uber_binding")
        self.assertEqual(report["packets"][0]["b1"]["c25RadialBlurParams2"][0],
                         3.0)

    def test_old_budget_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "128-MiB"):
            self.build(*fixture(budget=96 * 1024 * 1024))

    def test_missing_priority_tag_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "priority tagging"):
            self.build(*fixture(priority=False))

    def test_unexpected_mode_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "mode is unexpected"):
            self.build(*fixture(mode=4.0))


if __name__ == "__main__":
    unittest.main()
