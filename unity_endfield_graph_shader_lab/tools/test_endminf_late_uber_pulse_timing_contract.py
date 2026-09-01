#!/usr/bin/env python3
"""Source contract for the authored Endminf late Uber pulse phase."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOCK = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldEndminfVisualCompatibilityClock.cs"
)
SOURCE_CURVES = ROOT / (
    "Assets/EndfieldGraphShaderLab/Resources/EndfieldEndminfSourcePost/"
    "endminf_overview_02_source_post_curves.json"
)


class EndminfLateUberPulseTimingContractTests(unittest.TestCase):
    def test_late_pulse_preserves_serialized_clip_phase(self) -> None:
        payload = json.loads(SOURCE_CURVES.read_text(encoding="utf-8"))
        chromatic, radial, power = payload["curves"]
        expected_times = [
            0.0,
            0.1666666716337204,
            4.400000095367432,
            4.433333396911621,
            4.599999904632568,
        ]
        self.assertEqual([key["time"] for key in chromatic["keys"]], expected_times)
        self.assertEqual([key["time"] for key in radial["keys"]], expected_times)
        self.assertEqual(chromatic["keys"][3]["d"], 0.10100000351667404)
        self.assertEqual(radial["keys"][3]["d"], 0.10899999737739563)
        self.assertEqual(power["keys"], [
            {"time": 0.0, "a": 0.0, "b": 0.0, "c": 0.0, "d": 1.0}
        ])

    def test_runtime_rejects_the_retired_video_registered_substitute(self) -> None:
        source = CLOCK.read_text(encoding="utf-8")
        self.assertIn("EndfieldRecoveredEndminfSourcePostCurves.TryEvaluate(", source)
        for token in (
            "EvaluateSourceCurve(",
            "initialPeak * 0.45f",
            "4.3166667f",
            "4.35f",
            "4.5166667f",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
