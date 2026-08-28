#!/usr/bin/env python3
"""Source contract for the measured Endminf late Uber pulse phase."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOCK = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldEndminfVisualCompatibilityClock.cs"
)


class EndminfLateUberPulseTimingContractTests(unittest.TestCase):
    def test_late_pulse_is_registered_to_retail_frame_1818(self) -> None:
        source = CLOCK.read_text(encoding="utf-8")
        values = {
            name: float(value)
            for name, value in re.findall(
                r"late(Start|Peak|End)Seconds = ([0-9.]+)f;", source
            )
        }
        self.assertAlmostEqual(values["Start"], 4.4 - 5.0 / 60.0, places=6)
        self.assertAlmostEqual(values["Peak"], 4.4333333 - 5.0 / 60.0, places=6)
        self.assertAlmostEqual(values["End"], 4.6 - 5.0 / 60.0, places=6)
        self.assertIn("Retail frame 1818", source)
        self.assertIn("latePeakSeconds - lateStartSeconds", source)
        self.assertIn("lateEndSeconds - latePeakSeconds", source)


if __name__ == "__main__":
    unittest.main()
