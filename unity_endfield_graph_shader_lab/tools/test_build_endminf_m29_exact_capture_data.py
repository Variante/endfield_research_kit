#!/usr/bin/env python3
"""Focused tests for the exact M29 capture payload builder."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_m29_exact_capture_data",
    HERE / "build_endminf_m29_exact_capture_data.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class M29ExactCaptureDataTests(unittest.TestCase):
    def test_authoritative_captures_build_nine_packets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cs, cpp = MODULE.build(
                MODULE.CAPTURE, MODULE.REPORT, MODULE.VS_PATH, MODULE.PS_PATH,
                root / "data.cs", root / "data.h")
        self.assertIn("PacketCount = 9", cs)
        self.assertIn("PacketPhases", cs)
        self.assertIn("GeometryContractReady = true", cs)
        self.assertIn('DrawContractSession = "20260827T225644Z"', cs)
        self.assertIn(
            "GeometrySourceFrames = { 1732, 1743, 1753, 1764, 2723, 2723, 2723, 2723, 2723 }",
            cs)
        self.assertIn(
            "SourceFrames = { 1732, 1743, 1753, 1764, 1775, 2723, 1785, 1796, 1807 }",
            cs)
        self.assertIn(
            "PacketPhases = { 2.550000f, 2.733333f, 2.983333f, 3.200000f, 3.450000f, 3.600000f, 3.683333f, 3.916667f, 4.133333f }",
            cs)
        self.assertIn("g_EndfieldM29PacketCount", cpp)
        self.assertIn("g_EndfieldM29GeometryContractReady = true", cpp)
        self.assertIn("g_EndfieldM29VertexShaderBytecode", cpp)
        self.assertIn("g_EndfieldM29TextureT0", cpp)
        self.assertIn("g_EndfieldM29TextureT1", cpp)
        self.assertIn("60u", cpp)

    def test_draw_contract_report_hash_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "report.json"
            report.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError,
                                        "draw-contract report hash drifted"):
                MODULE.collect_contract_packet(
                    MODULE.CONTRACT_CAPTURE, report)

    def test_report_hash_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "report.json"
            report.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "report hash drifted"):
                MODULE.collect(MODULE.CAPTURE, report,
                               MODULE.VS_PATH, MODULE.PS_PATH)


if __name__ == "__main__":
    unittest.main()
