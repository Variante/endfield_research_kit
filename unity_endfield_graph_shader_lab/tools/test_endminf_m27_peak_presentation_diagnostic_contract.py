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

    def test_visible_scene_color_not_full_carrier_gbuffer_owns_presentation(self) -> None:
        frame = GBUFFER_FRAME.read_text(encoding="utf-8")
        method = frame.split(
            "internal bool TryGetEndminfM27PresentationInputs(", 1
        )[1].split("internal bool TryGetSphereOutsidePresentationInputs(", 1)[0]
        self.assertIn("sourceSceneColor = sceneColor;", method)
        self.assertIn("mask = sceneColor;", method)
        self.assertNotIn("mask = gBufferC;", method)

    def test_native_resolver_is_joined_with_its_proven_mirrored_y_orientation(self) -> None:
        shader = PRESENTATION_SHADER.read_text(encoding="utf-8")
        self.assertIn("_EndfieldM27ResolvedColor.GetDimensions", shader)
        self.assertIn("int(resolvedHeight) - 1 - pixel.y", shader)
        self.assertIn(
            "_EndfieldM27ResolvedColor.Load(int3(resolvedPixel, 0))",
            shader,
        )

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
