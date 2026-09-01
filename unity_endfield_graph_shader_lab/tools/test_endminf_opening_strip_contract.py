#!/usr/bin/env python3
"""Focused source contract for the bounded Endminf opening-strip pass."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOCK = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldEndminfVisualCompatibilityClock.cs"
PIPELINE = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
CAPTURE = (
    ROOT / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldEndminfViewerPlayModeCapture.cs"
)
SHADER = ROOT / "Assets/EndfieldGraphShaderLab/Shaders/HGRPCompat/EndfieldEndminfOpeningStrip.shader"
PLUGIN = ROOT / "tools/original_dxbc_exact/OriginalDxbcSwapPlugin.cpp"
OPENING_STRIP_DIAGNOSTIC = (
    "ENDFIELD_ENDMINF_MEASURED_OPENING_STRIP_DIAGNOSTIC"
)


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
        self.assertIn(OPENING_STRIP_DIAGNOSTIC, source)
        self.assertIn("MeasuredOpeningStripDiagnosticRequested", source)
        self.assertIn(
            "if (!MeasuredOpeningStripDiagnosticRequested ||", source
        )
        self.assertIn("!TryGetElapsed(out float elapsed)", source)

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

    def test_compatibility_pass_is_explicit_diagnostic_and_pre_temporal(self) -> None:
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
        self.assertIn("MeasuredOpeningStripDiagnosticRequested", gate_text)
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

    def test_presentation_profiles_do_not_enable_measured_strip(self) -> None:
        wrapper = (ROOT / "open_character_recovery_lab.bat").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(f'{OPENING_STRIP_DIAGNOSTIC}=1', wrapper)
        self.assertIn(f'{OPENING_STRIP_DIAGNOSTIC}=0', wrapper)
        capture = CAPTURE.read_text(encoding="utf-8")
        default_start = capture.index("CanonicalVideoDefaultFlags")
        default_end = capture.index("};", default_start)
        self.assertNotIn(
            OPENING_STRIP_DIAGNOSTIC,
            capture[default_start:default_end],
        )
        forced_start = capture.index("CanonicalVideoForcedOffFlags")
        forced_end = capture.index("};", forced_start)
        self.assertIn(
            OPENING_STRIP_DIAGNOSTIC,
            capture[forced_start:forced_end],
        )

    def test_compatibility_publishes_retail_target1_scene_mv_marker(self) -> None:
        pipeline = PIPELINE.read_text(encoding="utf-8")
        shader = SHADER.read_text(encoding="utf-8")
        self.assertIn("RecoveredEndminfOpeningStripSceneMVId", pipeline)
        self.assertIn("recoveredSceneMV.descriptor", pipeline)
        self.assertIn("ENDFIELD_ENDMINF_OPENING_STRIP_SCENEMV", pipeline)
        selector = pipeline.index("ENDFIELD_ENDMINF_OPENING_STRIP_SCENEMV")
        selector_end = pipeline.index("System.StringComparison.Ordinal", selector)
        self.assertIn('"1"', pipeline[selector:selector_end])
        self.assertIn("LastRecoveredEndminfOpeningStripSceneMVApplied = true", pipeline)
        self.assertIn("#pragma fragment FragSceneMV", shader)
        self.assertIn("original.b = max(original.b, coverage)", shader)
        self.assertIn("preserve XY/A and set B=1", shader)

    def test_exact_transport_uses_independent_target1_blend(self) -> None:
        source = PLUGIN.read_text(encoding="utf-8")
        start = source.index("D3D11_BLEND_DESC blend = {};")
        end = source.index(
            "device->CreateBlendState(&blend, &g_openingStripBlendState)",
            start,
        )
        block = source[start:end]
        self.assertIn(
            "blend.RenderTarget[1].SrcBlend = D3D11_BLEND_SRC_COLOR", block
        )
        self.assertIn(
            "blend.RenderTarget[1].DestBlend = D3D11_BLEND_INV_SRC_COLOR", block
        )
        self.assertIn(
            "blend.RenderTarget[1].DestBlendAlpha = D3D11_BLEND_ONE", block
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
        self.assertIn("openingStripSceneMVBeforeTemporal", capture)
        self.assertIn("observedOpeningStripSceneMVBeforeTemporal", capture)

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

    def test_exact_packet_forces_its_required_scene_mv_transport(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        collect = source.index(
            "EndfieldRecoveredSceneMVRequest recoveredSceneMVRequest ="
        )
        reset = source.index("ResetRecoveredSceneMVDiagnostic", collect)
        request_gate = source[collect:reset]
        self.assertIn("exactEndminfOpeningStripPrepared", request_gate)
        self.assertIn(
            "recoveredSceneMVRequest = new EndfieldRecoveredSceneMVRequest(",
            request_gate,
        )

    def test_requested_exact_packets_must_submit_and_validate(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endminfOpeningStripExactRequirementReady", source)
        self.assertIn("endminfOpeningStripExactRangeIncluded", source)
        self.assertIn("observedEndminfOpeningStripExactActive &&", source)
        self.assertIn(
            "observedEndminfOpeningStripExactSubmitted &&", source
        )
        self.assertIn("observedEndminfOpeningStripExactValidated", source)
        required = source[source.index("bool requiredCaptureContractReady") :]
        self.assertIn("endminfOpeningStripExactRequirementReady", required)

    def test_exact_transport_refreshes_and_guards_optional_source_renderer(self) -> None:
        runtime = (
            ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredEndminfOpeningStripExactRuntime.cs"
        ).read_text(encoding="utf-8")
        prepare = runtime[
            runtime.index("internal static bool PrepareBeforeCulling") :
            runtime.index("internal static bool Render(")
        ]
        self.assertIn(
            "RefreshOptionalSourceRendererAndInitializeTransport()", prepare
        )
        self.assertIn("if (sourceRenderer != null)", prepare)
        self.assertIn("sourceRenderer.enabled = false;", prepare)
        refresh = runtime[
            runtime.index(
                "private static bool "
                "RefreshOptionalSourceRendererAndInitializeTransport"
            ) :
            runtime.index("private static int ResolvePacket")
        ]
        self.assertIn("if (sourceRenderer == null)", refresh)
        self.assertIn("if (initialized)", refresh)

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
