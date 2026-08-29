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

    def test_compatibility_pass_is_opt_in_and_pre_temporal(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        method_start = source.index(
            "private bool ApplyRecoveredEndminfOpeningStripCompatibilityBeforeTemporal"
        )
        method_end = source.index(
            "private bool EnqueueRecoveredEndminfTemporalResolve", method_start
        )
        method = source[method_start:method_end]
        gate = method.index("bool useRecoveredEndminfOpeningStripCompatibility")
        blit = method.index(
            "commandBuffer.Blit(\n                CameraColorId", gate
        )
        publish = method.index(
            "commandBuffer.CopyTexture(\n                "
            "RecoveredEndminfOpeningStripSourceId", blit
        )
        release = method.index("commandBuffer.ReleaseTemporaryRT", publish)
        self.assertLess(gate, blit)
        self.assertLess(blit, publish)
        self.assertLess(publish, release)
        gate_text = method[gate:blit]
        self.assertIn("useRecoveredPostSemantics", gate_text)
        self.assertIn(
            "!EndfieldRecoveredEndminfOpeningStripExactRuntime.ActiveThisFrame",
            gate_text,
        )
        self.assertIn("recoveredEndminfOpeningStripMaterial != null", gate_text)
        self.assertIn("hasOpeningStripSelector", gate_text)
        self.assertIn("TryEvaluateOpeningStrip", gate_text)
        self.assertIn("compatibility before temporal", method)
        self.assertIn(
            "LastRecoveredEndminfOpeningStripCompatibilityApplied = true",
            method,
        )

    def test_capture_reports_pre_temporal_compatibility_submission(self) -> None:
        pipeline = PIPELINE.read_text(encoding="utf-8")
        capture = (
            ROOT
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldEndminfViewerPlayModeCapture.cs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "LastRecoveredEndminfOpeningStripCompatibilityApplied",
            pipeline,
        )
        self.assertIn(
            "openingStripCompatibilityBeforeTemporal = HGCompatRenderPipeline",
            capture,
        )
        self.assertIn(
            "observedOpeningStripCompatibilityBeforeTemporal",
            capture,
        )

    def test_compatibility_call_precedes_temporal_input_diagnostics(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        render_start = source.index("private void RenderPreparedCamera")
        render_end = source.index("private void ApplyCharacterPostProcess", render_start)
        render = source[render_start:render_end]
        compatibility = render.index(
            "ApplyRecoveredEndminfOpeningStripCompatibilityBeforeTemporal("
        )
        before_temporal = render.index("CaptureBeforeTemporalIfArmed", compatibility)
        post = render.index("ApplyCharacterPostProcess(", before_temporal)
        self.assertLess(compatibility, before_temporal)
        self.assertLess(before_temporal, post)

    def test_exact_packet_path_remains_in_scene_render_before_compatibility(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        render_start = source.index("private void RenderPreparedCamera")
        render_end = source.index("private void ApplyCharacterPostProcess", render_start)
        render = source[render_start:render_end]
        exact = render.index(
            "EndfieldRecoveredEndminfOpeningStripExactRuntime.Render("
        )
        compatibility = render.index(
            "ApplyRecoveredEndminfOpeningStripCompatibilityBeforeTemporal("
        )
        self.assertLess(exact, compatibility)

    def test_shader_uses_measured_rightward_bands_and_restrained_rgb_split(self) -> None:
        source = SHADER.read_text(encoding="utf-8")
        self.assertIn("TryGetMeasuredBand", source)
        self.assertIn("frame == 4", source)
        self.assertIn("frame == 20", source)
        self.assertIn("uv.x - displacementUv", source)
        self.assertIn("float chromaUv", source)
        self.assertIn("shiftedUv + float2(chromaUv, 0.0)", source)
        self.assertIn("shiftedUv - float2(chromaUv, 0.0)", source)
        self.assertNotIn("OpeningStripHash", source)
        self.assertNotIn("floor(retailPixel.y / 8.0)", source)
        self.assertNotIn("rowSelector > 0.88", source)
        self.assertNotIn("lerp(110.0, 420.0, shiftSelector)", source)
        self.assertIn("saturate(_EndminfOpeningStripParams.x)", source)
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
