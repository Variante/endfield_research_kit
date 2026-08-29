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
                r"OpeningStrip(Start|End)Seconds = ([0-9.]+)f;", source
            )
        }
        self.assertAlmostEqual(values["Start"], 4.0 / 60.0, places=6)
        self.assertAlmostEqual(values["End"], 0.35, places=6)
        self.assertIn("IsMeasuredOpeningStripFrame(frame)", source)
        self.assertNotIn("OPENING_STRIP_DIAGNOSTIC", source)
        self.assertIn("if (!TryGetElapsed(out float elapsed))", source)

    def test_runtime_admits_exactly_shader_backed_frames(self) -> None:
        clock_source = CLOCK.read_text(encoding="utf-8")
        shader_source = SHADER.read_text(encoding="utf-8")
        runtime_frames = {
            int(frame)
            for frame in re.findall(r"case ([0-9]+):", clock_source)
        }
        shader_frames = {
            int(frame)
            for frame in re.findall(r"frame == ([0-9]+)", shader_source)
        }
        self.assertEqual(runtime_frames, shader_frames)
        self.assertEqual(
            runtime_frames,
            {4, 6, 7, 8, 9, 10, 11, 12, 18, 19, 20},
        )

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
        self.assertIn("hasOpeningStripSelector", gate_text)
        self.assertIn("TryEvaluateOpeningStrip", gate_text)

    def test_shader_uses_measured_rightward_bands_and_restrained_rgb_split(self) -> None:
        source = SHADER.read_text(encoding="utf-8")
        self.assertIn("TryGetMeasuredBand", source)
        self.assertIn("frame == 4", source)
        self.assertIn("frame == 20", source)
        self.assertIn("uv.x - displacementUv", source)
        self.assertIn("float chromaUv", source)
        self.assertIn("shiftedUv + float2(chromaUv, 0.0)", source)
        self.assertIn("shiftedUv - float2(chromaUv, 0.0)", source)
        self.assertIn("OpeningStripHash", source)
        self.assertIn("floor(retailPixel.y / 8.0)", source)
        self.assertIn("rowSelector > 0.88", source)
        self.assertIn("lerp(110.0, 420.0, shiftSelector)", source)
        self.assertNotIn("Hash11", source)

    def test_shader_uses_shifted_character_selector_ownership(self) -> None:
        source = SHADER.read_text(encoding="utf-8")
        self.assertIn("sampler2D _EndminfOpeningStripSelector", source)
        selector = source.index("float4 selector = tex2Dlod")
        shifted_uv = source.index("float4(shiftedUv, 0.0, 0.0)", selector)
        owner = source.index("float shiftedOwner = step", shifted_uv)
        destination = source.index("float destinationOwner = step", owner)
        composite = source.index("activeBand * shiftedOwner * (1.0 - destinationOwner)", destination)
        self.assertLess(selector, shifted_uv)
        self.assertLess(shifted_uv, owner)
        self.assertLess(owner, destination)
        self.assertLess(destination, composite)
        self.assertNotIn("uv.y + displacement", source)


if __name__ == "__main__":
    unittest.main()
