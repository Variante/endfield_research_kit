from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_m30_exact_capture_data",
    HERE / "build_endminf_m30_exact_capture_data.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BuildEndminfM30ExactCaptureDataTests(unittest.TestCase):
    def test_builds_eleven_packets_but_keeps_depth_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cs_path = Path(folder) / "payload.cs"
            cpp_path = Path(folder) / "payload.h"
            cs, cpp = MODULE.build(
                MODULE.TEMPORAL_CAPTURE,
                MODULE.TEMPORAL_REPORT,
                MODULE.RESOURCE_CAPTURE,
                cs_path,
                cpp_path)
            self.assertIn("PacketCount = 11", cs)
            self.assertIn("DepthContractReady = false", cs)
            self.assertIn("g_EndfieldM30PacketCount", cpp)
            self.assertIn("g_EndfieldM30DepthContractReady = false", cpp)
            self.assertIn("g_EndfieldM30TextureT1", cpp)
            self.assertEqual(cs_path.read_text(encoding="utf-8"), cs)
            self.assertEqual(cpp_path.read_text(encoding="utf-8"), cpp)

    def test_report_hash_drift_fails_closed(self) -> None:
        report = json.loads(MODULE.TEMPORAL_REPORT.read_text(encoding="utf-8"))
        report["owners"]["M30"]["frames"][0]["metadataSha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report_path = root / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "metadata hash drifted"):
                MODULE.build(
                    MODULE.TEMPORAL_CAPTURE,
                    report_path,
                    MODULE.RESOURCE_CAPTURE,
                    root / "payload.cs",
                    root / "payload.h")

    def test_resource_session_is_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "resource capture session drifted"):
                MODULE.build(
                    MODULE.TEMPORAL_CAPTURE,
                    MODULE.TEMPORAL_REPORT,
                    Path(folder),
                    Path(folder) / "payload.cs",
                    Path(folder) / "payload.h")


if __name__ == "__main__":
    unittest.main()
