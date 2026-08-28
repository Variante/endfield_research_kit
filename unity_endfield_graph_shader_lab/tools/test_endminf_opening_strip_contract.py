#!/usr/bin/env python3
"""Focused source contract for the bounded Endminf opening-strip pass."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOCK = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldEndminfVisualCompatibilityClock.cs"
PIPELINE = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
SHADER = ROOT / "Assets/EndfieldGraphShaderLab/Shaders/HGRPCompat/EndfieldEndminfOpeningStrip.shader"


class EndminfOpeningStripContractTests(unittest.TestCase):
    def test_window_is_bounded_to_opening(self) -> None:
        source = CLOCK.read_text(encoding="utf-8")
        values = {
            name: float(value)
            for name, value in re.findall(
                r"OpeningStrip(Start|Peak|End)Seconds = ([0-9.]+)f;", source
            )
        }
        self.assertAlmostEqual(values["Start"], 1.0 / 30.0, places=6)
        self.assertAlmostEqual(values["Peak"], 1.0 / 15.0, places=6)
        self.assertAlmostEqual(values["End"], 0.35, places=6)
        self.assertIn("elapsed >= OpeningStripEndSeconds", source)
        self.assertIn("if (!TryGetElapsed(out float elapsed))", source)

    def test_pass_is_opt_in_and_pre_uber(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        gate = source.index("bool useRecoveredEndminfOpeningStrip")
        blit = source.index("RecoveredEndminfOpeningStripSourceId,\n                    recoveredEndminfOpeningStripMaterial", gate)
        bloom = source.index("BuildRecoveredSceneBloomPyramid", blit)
        uber = source.index("recoveredEndminfUberExactRuntime.Enqueue", bloom)
        self.assertLess(gate, blit)
        self.assertLess(blit, bloom)
        self.assertLess(bloom, uber)
        gate_text = source[gate:blit]
        self.assertIn("useRecoveredPostSemantics", gate_text)
        self.assertIn("recoveredEndminfOpeningStripMaterial != null", gate_text)
        self.assertIn("TryEvaluateOpeningStrip", gate_text)

    def test_shader_keeps_constant_band_x_and_restrained_rgb_split(self) -> None:
        source = SHADER.read_text(encoding="utf-8")
        self.assertIn("float band = floor", source)
        self.assertIn("float displacementPixels = signedOffset * sparse", source)
        self.assertIn("float chromaUv", source)
        self.assertIn("shiftedUv + float2(chromaUv, 0.0)", source)
        self.assertIn("shiftedUv - float2(chromaUv, 0.0)", source)
        self.assertNotIn("uv.y + displacement", source)


if __name__ == "__main__":
    unittest.main()
