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
        self.assertAlmostEqual(MODULE.phase_seconds(2978), 4.433333, places=6)
        self.assertAlmostEqual(
            self.report["owners"]["M29"]["frames"][0]["phaseSeconds"],
            2.533333,
            places=6,
        )

    def test_material_colors_match_captured_linear_uploads(self) -> None:
        for owner_name in ("M29", "M30"):
            material = self.report["owners"][owner_name]["material"]
            expected = MODULE.OWNERS[owner_name]["c4"]
            self.assertTrue(MODULE.close(tuple(material["linearTint"]), expected))

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
