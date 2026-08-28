from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


VERIFY = load("verify_uber_for_payload_test",
              HERE / "verify_endminf_uber_capture.py")
BUILD = load("build_uber_payload_test",
             HERE / "build_endminf_uber_capture_payload.py")


def range_row(constants: int, seed: int) -> dict[str, object]:
    payload = bytes((seed + index) & 0xFF for index in range(constants * 16))
    import hashlib
    return {
        "declaredConstants": constants,
        "declaredRangeHex": payload.hex(),
        "declaredRangeSha256": hashlib.sha256(payload).hexdigest(),
    }


def report() -> dict[str, object]:
    return {
        "status": BUILD.EXPECTED_STATUS,
        "capture": "D:/capture/session",
        "compiledKeywords": ["BLOOM", "RADIAL_BLUR", "VIGNETTE"],
        "packets": [{
            "frame": 42,
            "fullscreenOrdinal": 9,
            "vertexSha256": BUILD.EXPECTED_VERTEX_SHA256,
            "pixelSha256": BUILD.EXPECTED_PIXEL_SHA256,
            "vsB0": range_row(1, 1),
            "b0": range_row(28, 2),
            "b1": range_row(26, 3),
        }],
    }


class PayloadBuilderTests(unittest.TestCase):
    def test_valid_report_builds_exact_arrays(self) -> None:
        header = BUILD.build_header(report())
        self.assertIn("g_EndfieldUberCapturePayloadAvailable = true", header)
        self.assertIn("g_EndfieldUberVsB0Size = sizeof", header)
        self.assertIn("g_EndfieldUberPsB0Size = sizeof", header)
        self.assertIn("g_EndfieldUberPsB1Size = sizeof", header)
        self.assertIn("g_EndfieldUberCaptureFrame = 42u", header)

    def test_ambiguous_packets_fail_closed(self) -> None:
        value = report()
        value["packets"].append(dict(value["packets"][0]))
        with self.assertRaisesRegex(BUILD.ContractError, "one unambiguous"):
            BUILD.build_header(value)

    def test_byte_hash_drift_fails_closed(self) -> None:
        value = report()
        value["packets"][0]["b1"]["declaredRangeSha256"] = "0" * 64
        with self.assertRaisesRegex(BUILD.ContractError, "hash drifted"):
            BUILD.build_header(value)


if __name__ == "__main__":
    unittest.main()
