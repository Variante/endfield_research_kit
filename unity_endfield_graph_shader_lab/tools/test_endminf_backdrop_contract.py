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


class EndminfBackdropContractTests(unittest.TestCase):
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
        ):
            self.assertIn(token, launcher)


if __name__ == "__main__":
    unittest.main()
