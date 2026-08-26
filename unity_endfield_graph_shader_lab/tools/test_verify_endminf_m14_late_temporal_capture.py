#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("verify_endminf_m14_late_temporal_capture.py")
SPEC = importlib.util.spec_from_file_location("m14_late_temporal_capture", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class M14LateTemporalCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = MODULE.verify_session(MODULE.CAPTURE)

    def test_current_capture_closes_all_nine_packets(self) -> None:
        self.assertEqual(self.report["status"], "validated")
        self.assertEqual(self.report["sampleCount"], 9)
        self.assertEqual(
            [row["geometry"]["indexCount"] for row in self.report["frames"]],
            [count for _, count in MODULE.SEQUENCE],
        )
        self.assertTrue(all(
            row["geometry"]["uniqueLargeExpandedQuadStream"]
            for row in self.report["frames"]
        ))
        self.assertAlmostEqual(
            self.report["frames"][0]["phaseSeconds"], 4.433333, places=6)
        self.assertAlmostEqual(
            self.report["frames"][-1]["phaseSeconds"], 5.516666, places=6)

    def test_every_packet_has_all_nine_constant_buffers_and_exact_ia_hashes(self) -> None:
        for row in self.report["frames"]:
            self.assertEqual(len(row["constantBuffers"]), 9)
            self.assertEqual(len(row["geometry"]["vertexSha256"]), 64)
            self.assertEqual(len(row["geometry"]["indexSha256"]), 64)
            self.assertEqual(row["geometry"]["vertexStride"], 36)

    def test_only_two_late_frames_reuse_the_immutable_texture_closure(self) -> None:
        statuses = {row["frame"]: row["textures"]["status"]
                    for row in self.report["frames"]}
        self.assertEqual(
            [frame for frame, status in statuses.items()
             if status == "omitted_reuse_immutable"],
            [3035, 3043],
        )
        for row in self.report["frames"][-2:]:
            self.assertEqual(row["textures"]["omittedSlots"], [0, 1, 2, 3])
            self.assertEqual(row["textures"]["reuseFromFrame"], 2978)

    def test_wrong_tint_and_missing_constant_buffer_fail_closed(self) -> None:
        frame = 2978
        metadata = MODULE.load_json(
            MODULE.CAPTURE / "graphics" / "frames" / str(frame) / "metadata.json")
        draw = MODULE.select_draw(metadata, frame, 1872)

        wrong_tint = copy.deepcopy(draw)
        row = next(item for item in wrong_tint["constantBuffers"]
                   if item["stage"] == 4 and item["slot"] == 3)
        payload = bytearray.fromhex(row["dataHex"])
        payload[4 * 16:4 * 16 + 16] = b"\0" * 16
        row["dataHex"] = payload.hex()
        changed = copy.deepcopy(metadata)
        changed["drawRecords"] = [wrong_tint]
        with self.assertRaises(MODULE.CaptureError):
            MODULE.select_draw(changed, frame, 1872)

        missing = copy.deepcopy(draw)
        missing["constantBuffers"].pop()
        with self.assertRaises(MODULE.CaptureError):
            MODULE.validate_constants(missing, frame)


if __name__ == "__main__":
    unittest.main()
