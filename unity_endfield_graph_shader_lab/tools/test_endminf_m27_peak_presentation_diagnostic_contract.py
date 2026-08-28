from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredEndminfM27ExactRuntime.cs"
)
PRESENTATION = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredEndminfM27DeferredPresentation.cs"
)
PRESENTATION_SHADER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Shaders/Recovered/"
    "EndfieldEndminfM27DeferredPresentation.shader"
)
GBUFFER_FRAME = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredDeferredGBufferFrame.cs"
)
PIPELINE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
)
DEFERRED_CONSUMER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredDeferredExactConsumer.cs"
)


class EndminfM27PeakPresentationDiagnosticContractTests(unittest.TestCase):
    def test_one_shot_readback_waits_for_the_source_peak_stone_packet(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        presentation = PRESENTATION.read_text(encoding="utf-8")
        self.assertIn("internal static bool PeakStonePacketSelected", runtime)
        self.assertIn("internal static bool HandCrystalPacketSelected", runtime)
        self.assertIn("SourceFrames[selectedPacket] >= 2978", runtime)
        self.assertIn("SourceFrames[selectedPacket] == 2978", runtime)
        self.assertIn(
            "!EndfieldRecoveredEndminfM27ExactRuntime.PeakStonePacketSelected",
            presentation,
        )
        self.assertEqual(
            presentation.count(
                "!EndfieldRecoveredEndminfM27ExactRuntime.HandCrystalPacketSelected"
            ),
            2,
        )

    def test_private_depth_owns_deferred_lit_stone_presentation(self) -> None:
        frame = GBUFFER_FRAME.read_text(encoding="utf-8")
        method = frame.split(
            "internal bool TryGetEndminfM27PresentationInputs(", 1
        )[1].split("internal bool TryGetSphereOutsidePresentationInputs(", 1)[0]
        shader = PRESENTATION_SHADER.read_text(encoding="utf-8")
        self.assertIn("sourceSceneColor = sceneColor;", method)
        self.assertIn("private reversed-Z", method)
        self.assertEqual(
            shader.count(
                "_EndfieldM27PrivateDepth.Load(int3(pixel, 0))"
            ),
            2,
        )
        self.assertIn("if (privateDepth <= 0.0)", shader)
        self.assertIn(
            "if (_EndfieldM27PrivateDepth.Load(int3(pixel, 0)) <= 0.0)",
            shader,
        )
        self.assertNotIn("float3 ownership", shader)

    def test_native_resolver_is_joined_with_its_proven_mirrored_y_orientation(self) -> None:
        shader = PRESENTATION_SHADER.read_text(encoding="utf-8")
        self.assertIn("_EndfieldM27ResolvedColor.GetDimensions", shader)
        self.assertIn("int(resolvedHeight) - 1 - pixel.y", shader)
        self.assertIn(
            "_EndfieldM27ResolvedColor.Load(int3(resolvedPixel, 0))",
            shader,
        )

    def test_diagnostic_reports_direct_and_mirrored_resolver_ranges(self) -> None:
        presentation = PRESENTATION.read_text(encoding="utf-8")
        self.assertIn("resolvedDirectRgbRange=", presentation)
        self.assertIn("resolvedMirrorYRgbRange=", presentation)
        self.assertIn(
            "diagnosticResolvedBytes,\n"
            "                        mirroredPixel * 16 + lane * 4",
            presentation,
        )

    def test_final_transfer_is_linear_scene_emission_plus_resolve(self) -> None:
        shader = PRESENTATION_SHADER.read_text(encoding="utf-8")
        self.assertIn(
            "return _EndfieldM27SourceSceneColor.Load(int3(pixel, 0)) +",
            shader,
        )
        self.assertNotIn("LinearToSRGB", shader)
        self.assertNotIn("SRGBToLinear", shader)

    def test_exact_resolver_keeps_unclosed_lighting_inputs_explicit(self) -> None:
        consumer = DEFERRED_CONSUMER.read_text(encoding="utf-8")
        for token in (
            "b6=HDPLS:zero-local-fallback",
            "t12=LightCookie:black-zero-cookie",
            "t13=IntegratedFog:black-disabled-1x1-ASTC",
            "t16-t21=IrradianceV2:zero-inactive-fallback",
        ):
            self.assertIn(token, consumer)

    def test_depth_precedes_forward_and_color_follows_opaque_owner(self) -> None:
        pipeline = PIPELINE.read_text(encoding="utf-8")
        depth = pipeline.index(
            "recoveredEndminfM27DeferredPresentation.PublishDepth("
        )
        opaque = pipeline.index("recoveredSceneMVCompositor.DrawOpaqueOwner(")
        color = pipeline.index("recoveredEndminfM27DeferredPresentation.Render(")
        transparent = pipeline.index("PrepareRecoveredPreTransparentSceneColor(")
        self.assertLess(depth, opaque)
        self.assertLess(opaque, color)
        self.assertLess(color, transparent)


if __name__ == "__main__":
    unittest.main()
