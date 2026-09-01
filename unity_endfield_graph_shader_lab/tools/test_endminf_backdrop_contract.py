import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredCharInfoPresentation.cs"
)
SHADER = ROOT / "Assets/EndfieldGraphShaderLab/Shaders/ReferenceBackdrop.shader"
BUILDER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldRecoveredCharInfoPresentationBuilder.cs"
)
CAPTURE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfViewerPlayModeCapture.cs"
)
LAUNCHER = ROOT / "open_character_recovery_lab.bat"
PROFILE_BUILDER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldPlayableCharInfoProfileBuilder.cs"
)
PORTRAIT_SHADER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Shaders/Recovered/"
    "EndfieldCharInfoBackgroundPortraitRecovered.shader"
)
PIPELINE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
)


class EndminfBackdropContractTests(unittest.TestCase):
    def test_endminf_portrait_requires_unrotated_source_packing_and_upright_uv(self):
        builder = PROFILE_BUILDER.read_text(encoding="utf-8")
        self.assertGreaterEqual(
            builder.count("ValidatePortraitPackingForUnflippedUv("),
            3,
        )
        for token in (
            'Str(Get(packing, "meshType"))',
            'Str(Get(packing, "packingMode"))',
            'Str(Get(packing, "packingRotation"))',
            'Int(Get(packing, "packed")) != 0',
            '"Tight"',
            '"None"',
            "new Vector2(textureRect.xMin / SourceTextureSize, textureRect.yMin / SourceTextureSize)",
            "new Vector2(textureRect.xMax / SourceTextureSize, textureRect.yMax / SourceTextureSize)",
            "vertices[0].y < vertices[2].y && uv[0].y < uv[2].y",
        ):
            self.assertIn(token, builder)
        shader = PORTRAIT_SHADER.read_text(encoding="utf-8")
        self.assertIn("output.uv = input.uv;", shader)
        self.assertNotIn("1.0 - input.uv.y", shader)
        self.assertNotIn("1.0 - input.uv", shader)

    def test_portrait_only_flip_and_invalid_body_mask_stay_fail_closed(self):
        pipeline = PIPELINE.read_text(encoding="utf-8")
        draw_start = pipeline.index("private void DrawRecoveredPostUberWorldUi(")
        draw_end = pipeline.index(
            "private int BuildRecoveredSceneBloomPyramid", draw_start
        )
        portrait_draw = pipeline[draw_start:draw_end]
        self.assertIn(
            "commandBuffer.SetGlobalFloat(HGFlipYId, 0.0f);",
            portrait_draw,
        )
        self.assertNotIn(
            "camera.targetTexture == null ? 1.0f : 0.0f",
            portrait_draw,
        )
        self.assertGreaterEqual(
            pipeline.count("recoveredDeferredExactConsumer.PresentationReady"),
            4,
        )

        capture = CAPTURE.read_text(encoding="utf-8")
        defaults_start = capture.index("CanonicalVideoDefaultFlags")
        defaults_end = capture.index("};", defaults_start)
        defaults = capture[defaults_start:defaults_end]
        self.assertNotIn(
            "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC",
            defaults,
        )
        self.assertNotIn(
            "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_PRESENTATION",
            defaults,
        )
        self.assertIn("content-invalid screen-shadow attachment", defaults)
        self.assertIn("upside-down body mask over the portrait", defaults)

        forced_start = capture.index("CanonicalVideoForcedOffFlags")
        forced_end = capture.index("};", forced_start)
        forced_off = capture[forced_start:forced_end]
        self.assertIn(
            "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC",
            forced_off,
        )
        self.assertIn("SphereOutsidePresentationEnvironment", forced_off)
        self.assertIn(
            'Environment.SetEnvironmentVariable(flag, "0");',
            capture,
        )

    def test_diagnostic_plate_retains_measured_neutral_grade(self):
        source = PRESENTATION.read_text(encoding="utf-8")
        for token in (
            "new Color(0.61f, 0.61f, 0.605f, 1.0f)",
            "new Color(0.85f, 0.85f, 0.845f, 1.0f)",
            '"_BottomVignette", 0.58f',
            '"_BottomVignetteFloor", 0.13f',
            '"_BottomVignetteHeight", 0.27f',
        ):
            self.assertIn(token, source)

    def test_bottom_rolloff_is_screen_space_not_actor_bounds_uv(self):
        source = SHADER.read_text(encoding="utf-8")
        self.assertIn("o.screenPos = ComputeScreenPos(o.pos);", source)
        self.assertIn(
            "float2 screenUv = i.screenPos.xy / max(i.screenPos.w, 1.0e-6);",
            source,
        )
        self.assertIn("screenUv.y)) *", source)
        self.assertNotIn("0.02, max(_BottomVignetteHeight", source)

    def test_source_background_is_independent_and_excludes_plate(self):
        source = PRESENTATION.read_text(encoding="utf-8")
        self.assertIn(
            '"ENDFIELD_ENDMINF_SOURCE_BACKGROUND"',
            source,
        )
        start = source.index("private void ApplyEndminfSourceBackground()")
        end = source.index("private void ApplyReadySubsetDiagnostic()", start)
        source_path = source[start:end]
        self.assertIn(
            "SetRendererEnabledStates(false, false, false, true, true);",
            source_path,
        )
        self.assertIn("ApplySettledOpenState(openState, false);", source_path)
        self.assertIn("appliedBackdropRenderer.enabled = false;", source_path)
        self.assertIn("source-backed partial ShadowPlane", source_path)
        self.assertNotIn("0.125f", source_path)
        self.assertNotIn('"_TopColor"', source_path)

        validation_start = source.index(
            "private bool ValidateEndminfSourceBackgroundReadiness("
        )
        validation_end = source.index(
            "private bool ValidateReadySubsetReadiness(", validation_start
        )
        validation = source[validation_start:validation_end]
        for token in (
            "ValidateReadySubsetReadiness(out openState, out failure)",
            "shadowPlaneRenderer",
            '"ShadowPlane"',
            '"Plane"',
            "ShadowReceiverShaderName",
            "claim that its final presented pixels match retail ownership",
        ):
            self.assertIn(token, validation)

    def test_capture_fits_remain_compatibility_only(self):
        source = PRESENTATION.read_text(encoding="utf-8")
        compatibility_start = source.index(
            "private bool ApplyEndminfBackdropCompatibility("
        )
        compatibility_end = source.index(
            "public bool ValidateSourceReadiness", compatibility_start
        )
        compatibility_path = source[compatibility_start:compatibility_end]
        self.assertIn("ApplySettledOpenState(openState, true);", compatibility_path)
        self.assertIn('"_TopColor"', compatibility_path)
        self.assertEqual(source.count("gridTint.a *= 0.125f;"), 1)
        self.assertEqual(source.count("ApplySettledOpenState(openState, true);"), 1)

    def test_generated_source_selector_remains_default_off(self):
        source = BUILDER.read_text(encoding="utf-8")
        self.assertGreaterEqual(
            source.count("controller.enableEndminfSourceBackground = false;"),
            3,
        )

    def test_canonical_capture_and_launcher_exclude_fitted_backgrounds(self):
        capture = CAPTURE.read_text(encoding="utf-8")
        for token in (
            ".EndminfSourceBackgroundEnvironmentVariable",
            ".EndminfBackdropVisualCompatibilityEnvironmentVariable,",
            ".ReadySubsetEnvironmentVariable,",
            "IsEndminfSourceBackgroundActive()",
            "IsFittedCompatibilityPlateActive()",
            "public bool fittedCompatibilityPlateActive;",
        ):
            self.assertIn(token, capture)
        self.assertGreaterEqual(capture.count('"0");'), 2)

        launcher = LAUNCHER.read_text(encoding="utf-8")
        for token in (
            'set "ENDFIELD_ENDMINF_SOURCE_BACKGROUND=1"',
            'set "ENDFIELD_ENDMINF_BACKDROP_VISUAL_COMPATIBILITY=0"',
            'set "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC=0"',
            'set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=1"',
            'set "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC=0"',
            'set "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_PRESENTATION=0"',
        ):
            self.assertIn(token, launcher)


if __name__ == "__main__":
    unittest.main()
