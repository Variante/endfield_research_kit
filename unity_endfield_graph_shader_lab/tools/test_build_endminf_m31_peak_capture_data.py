from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNTIME = (HERE.parent / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
           / "EndfieldRecoveredEndminfM31PeakExactRuntime.cs")
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_m31_peak_capture_data",
    HERE / "build_endminf_m31_peak_capture_data.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BuildEndminfM31PeakCaptureDataTests(unittest.TestCase):
    def test_builds_qpc_anchored_temporal_manifest_and_exact_payload(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cs_path = Path(folder) / "payload.cs"
            cpp_path = Path(folder) / "payload.h"
            MODULE.build(MODULE.TEMPORAL_CAPTURE, MODULE.PAYLOAD_CAPTURE,
                         cs_path, cpp_path)
            cs = cs_path.read_text(encoding="utf-8")
            cpp = cpp_path.read_text(encoding="utf-8")
            self.assertIn('TemporalSourceSession = "20260828T121603Z"', cs)
            self.assertIn("PayloadSourceFrame = 1818", cs)
            self.assertIn("AnchorFrame = 1977", cs)
            self.assertIn("AnchorPhaseSeconds = 4.350000f", cs)
            self.assertIn("PacketCount = 9", cs)
            self.assertIn("NativePayloadDrawCount = 2", cs)
            self.assertIn(
                "DrawCounts = { 2, 2, 2, 2, 2, 2, 2, 3, 1 }", cs)
            self.assertIn("2.863329f", cs)
            self.assertIn("4.564017f", cs)
            self.assertIn("DepthContractReady = true", cs)
            self.assertIn("g_EndfieldM31PeakPacketCount", cpp)
            self.assertIn("g_EndfieldM31PeakTextureT1", cpp)

    def test_temporal_capture_has_exact_owner_resource_closure(self) -> None:
        packets = MODULE.collect_temporal(MODULE.TEMPORAL_CAPTURE)
        self.assertEqual(list(MODULE.TEMPORAL_FRAMES),
                         [row["frame"] for row in packets])
        self.assertEqual([2, 2, 2, 2, 2, 2, 2, 3, 1],
                         [row["draw_count"] for row in packets])
        anchor = packets[list(MODULE.TEMPORAL_FRAMES).index(
            MODULE.ANCHOR_FRAME)]
        self.assertAlmostEqual(4.35, anchor["phase"], places=9)
        self.assertTrue(all(
            row["phase"] < packets[index + 1]["phase"]
            for index, row in enumerate(packets[:-1])))

    def test_owner_constant_drift_is_rejected(self) -> None:
        metadata_path = (MODULE.PAYLOAD_CAPTURE /
                         "graphics/frames/1818/metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        draw = next(row for row in metadata["drawRecords"]
                    if MODULE.is_m31(row))
        changed = copy.deepcopy(draw)
        b3 = next(row for row in changed["constantBuffers"]
                  if row["stage"] == 4 and row["slot"] == 3)
        payload = bytearray.fromhex(b3["dataHex"])
        payload[16:20] = b"\x00\x00\x00\x00"
        b3["dataHex"] = payload.hex()
        self.assertFalse(MODULE.is_m31(changed))

    def test_capture_session_is_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            wrong = Path(folder) / "wrong-session"
            with self.assertRaisesRegex(ValueError,
                                        "temporal source session drifted"):
                MODULE.collect_temporal(wrong)

    def test_temporal_draw_args_are_pinned(self) -> None:
        metadata_path = (MODULE.TEMPORAL_CAPTURE /
                         "graphics/frames/1977/metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        draw = copy.deepcopy(metadata["drawRecords"][66])
        draw["baseVertex"] += 1
        draw_index, start, base_vertex = MODULE.EXPECTED_TEMPORAL_DRAWS[1977][0]
        with self.assertRaisesRegex(ValueError, "draw 66 args drifted"):
            MODULE.validate_temporal_draw(
                draw, 1977, draw_index, start, base_vertex)

    def test_runtime_admits_only_native_compatible_temporal_packets(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("ResolveNearestPacket", runtime)
        self.assertIn(
            "EndfieldRecoveredM31PeakCaptureData.DrawCounts[selectedPacket] ==",
            runtime)
        self.assertIn(
            "EndfieldRecoveredM31PeakCaptureData.NativePayloadDrawCount",
            runtime)
        self.assertIn("SetRendererSuppression(active)", runtime)
        self.assertIn("submittedDraws !=", runtime)


if __name__ == "__main__":
    unittest.main()
