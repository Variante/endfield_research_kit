from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_m29_m30_temporal_capture.py"
SPEC = importlib.util.spec_from_file_location("verify_endminf_m29_m30_temporal_capture", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class M29M30TemporalCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = MODULE.build_report()

    def test_capture_is_source_assisted_not_exact(self) -> None:
        self.assertEqual(self.report["status"], "validated_source_assisted_only")
        self.assertFalse(self.report["exactReplayReady"])
        self.assertIn("owner-specific", self.report["exactReplayGap"])

    def test_owner_sequences_are_complete(self) -> None:
        self.assertEqual(self.report["owners"]["M29"]["packetCount"], 13)
        self.assertEqual(self.report["owners"]["M29"]["indexCounts"], [1386])
        self.assertEqual(self.report["owners"]["M30"]["packetCount"], 11)
        self.assertEqual(self.report["owners"]["M30"]["indexCounts"], [6, 12])

    def test_corrected_phase_anchor_is_applied(self) -> None:
        anchor = self.report["phaseAnchor"]
        self.assertAlmostEqual(
            MODULE.phase_seconds(anchor["timestampQpc"], anchor["timestampQpc"],
                                 self.report["captureClock"]["qpcFrequency"]),
            4.433333, places=6)
        self.assertAlmostEqual(
            self.report["owners"]["M29"]["frames"][0]["phaseSeconds"],
            2.483322,
            places=6,
        )

    def test_capture_clock_is_explicit_about_legacy_fallback(self) -> None:
        self.assertEqual(self.report["captureClock"]["qpcFrequency"], 10_000_000)
        self.assertIn("legacy", self.report["captureClock"]["basis"])

    def test_material_colors_match_captured_linear_uploads(self) -> None:
        for owner_name in ("M29", "M30"):
            material = self.report["owners"][owner_name]["material"]
            expected = MODULE.OWNERS[owner_name]["c4"]
            self.assertTrue(MODULE.close(tuple(material["linearTint"]), expected))

    def test_discontinuous_manual_frames_are_separate_bursts(self) -> None:
        rows = [{"frame": frame, "timestampQpc": qpc}
                for frame, qpc in ((100, 0), (108, 1_333_333),
                                   (116, 2_666_667), (500, 20_000_000),
                                   (900, 40_000_000))]
        bursts = MODULE.frame_bursts(rows, 10_000_000)
        self.assertEqual([row["packetCount"] for row in bursts], [3, 1, 1])
        self.assertEqual(bursts[0]["sampledSpanSeconds"], 0.266667)

    def test_tint_fingerprint_attack_fails_closed(self) -> None:
        original = MODULE.OWNERS["M30"]["c4"]
        MODULE.OWNERS["M30"]["c4"] = (0.0, 0.0, 0.0, 1.0)
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "M30 frame 2880"):
                MODULE.build_report()
        finally:
            MODULE.OWNERS["M30"]["c4"] = original


if __name__ == "__main__":
    unittest.main()
