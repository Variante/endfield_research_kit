import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfViewerPlayModeCapture.cs"
)
RUNTIME_ROOT = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
OPEN_WRAPPER = ROOT / "open_character_recovery_lab.bat"


class EndminfPeakExactCaptureTelemetryContractTests(unittest.TestCase):
    def test_report_schema_and_rows_publish_each_exact_packet_state(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endminf-viewer-playmode-sequence.v8", source)
        for material in ("M18", "M21", "M28"):
            for state in ("Requested", "Active", "Submitted", "Validated", "Failure"):
                field = f"endminf{material}Exact{state}"
                self.assertGreaterEqual(source.count(field), 2, field)

    def test_runtimes_reset_and_publish_per_frame_submission_state(self) -> None:
        for material in ("M18", "M21", "M28"):
            path = RUNTIME_ROOT / (
                f"EndfieldRecoveredEndminf{material}PeakExactRuntime.cs"
            )
            source = path.read_text(encoding="utf-8")
            prepare = source.index("PrepareBeforeCulling")
            render = source.index("Render(", prepare)
            self.assertIn("submittedThisFrame = false", source[prepare:render])
            self.assertIn("validatedThisFrame = false", source[prepare:render])
            self.assertIn("submittedThisFrame = true", source[render:])
            self.assertIn("validatedThisFrame = true", source[render:])

    def test_normal_reproduction_enables_only_the_complete_peak_stone_packet(
        self,
    ) -> None:
        source = OPEN_WRAPPER.read_text(encoding="utf-8")
        self.assertIn(
            'set "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT=1"',
            source,
        )
        self.assertNotIn(
            'set "ENDFIELD_RECOVERED_ENDMINF_M18_PEAK_EXACT=1"',
            source,
        )
        self.assertNotIn(
            'set "ENDFIELD_RECOVERED_ENDMINF_M28_PEAK_EXACT=1"',
            source,
        )

    def test_canonical_video_defaults_to_the_interactive_exact_profile_but_retains_overrides(
        self,
    ) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        wrapper = OPEN_WRAPPER.read_text(encoding="utf-8")
        expected = (
            "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME",
            "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_PRESENTATION",
            "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER",
            "ENDFIELD_RECOVERED_ENDMINF_M13_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M14_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER",
            "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC",
            "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION",
            "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER",
            "ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW",
            "ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW",
            "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC",
        )
        self.assertIn("CanonicalVideoDefaultFlags", source)
        self.assertIn("if (videoExportRequested)", source)
        self.assertIn("Environment.GetEnvironmentVariable(flag)", source)
        self.assertIn('Environment.SetEnvironmentVariable(flag, "1")', source)
        for flag in expected:
            self.assertIn(flag, source, flag)
            self.assertIn(f'set "{flag}=1"', wrapper, flag)


if __name__ == "__main__":
    unittest.main()
