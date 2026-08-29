import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfViewerPlayModeCapture.cs"
)
RUNTIME_ROOT = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
OPEN_WRAPPER = ROOT / "open_character_recovery_lab.bat"
EXACT_LUT_RUNTIME = RUNTIME_ROOT / "EndfieldRecoveredCharInfoLut.cs"
EXACT_LUT_BYTES = ROOT / (
    "Assets/EndfieldGraphShaderLab/Resources/EndfieldCharInfo/"
    "EndminfCharInfoLut1024x32Rgba16f.bytes"
)
EXACT_LUT_CONTRACT = ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/"
    "endminf_charinfo_lut_contract.json"
)


class EndminfPeakExactCaptureTelemetryContractTests(unittest.TestCase):
    def test_report_schema_and_rows_publish_each_exact_packet_state(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endminf-viewer-playmode-sequence.v12", source)
        for field in (
            "exactEndminfUberRequested",
            "exactEndminfUberSubmitted",
            "exactEndminfUberValidated",
            "exactEndminfUberVariant",
            "exactEndminfUberFailure",
            "observedExactEndminfUberSubmitted",
            "observedExactEndminfUberValidated",
        ):
            self.assertGreaterEqual(source.count(field), 2, field)
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

    def test_canonical_video_admits_the_source_certified_uber_tick(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        start = source.index("CanonicalVideoDefaultFlags")
        defaults = source[start:source.index("};", start)]
        self.assertIn("ENDFIELD_RECOVERED_ENDMINF_UBER_EXACT", defaults)

    def test_public_ngx_proxy_is_reported_and_never_a_canonical_default(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        start = source.index("CanonicalVideoDefaultFlags")
        defaults = source[start:source.index("};", start)]
        self.assertNotIn("ENDFIELD_RECOVERED_UNITY_PUBLIC_NGX_PROXY", defaults)
        for field in (
            "unityPublicNgxProxyRequested",
            "unityPublicNgxProxySubmitted",
            "unityPublicNgxProxyValidated",
            "unityPublicNgxProxyFailure",
            "observedUnityPublicNgxProxySubmitted",
            "observedUnityPublicNgxProxyValidated",
        ):
            self.assertGreaterEqual(source.count(field), 2, field)

    def test_exact_uber_validates_after_readback_before_telemetry(self) -> None:
        capture = CAPTURE.read_text(encoding="utf-8")
        pipeline = (
            RUNTIME_ROOT / "HGCompatRenderPipeline.cs"
        ).read_text(encoding="utf-8")
        runtime = (
            RUNTIME_ROOT / "EndfieldRecoveredEndminfUberExactRuntime.cs"
        ).read_text(encoding="utf-8")
        render = capture.index("Color32[] pixels = Render(camera)")
        validation = capture.index(
            "ValidateRecoveredEndminfExactUberAfterSynchronizedRender",
            render,
        )
        frame_row = capture.index("Frames.Add(new FrameRow", validation)
        self.assertLess(render, validation)
        self.assertLess(validation, frame_row)
        self.assertIn("ValidatePendingAfterSynchronizedRender", runtime)
        self.assertIn(
            "LastRecoveredEndminfExactUberValidated = valid",
            pipeline,
        )
        self.assertIn(
            "observedExactEndminfUberSubmitted &&\n"
            "                 observedExactEndminfUberValidated",
            capture,
        )

    def test_exact_charinfo_lut_bytes_and_orientation_contract(self) -> None:
        payload = EXACT_LUT_BYTES.read_bytes()
        contract = json.loads(EXACT_LUT_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(len(payload), 1024 * 32 * 8)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "717c1d483662c00abe55e1c56a9d024f45e5c84c430ed9dd2854cb386f372482",
        )
        self.assertEqual(contract["graphicsFormat"], "R16G16B16A16_SFloat")
        self.assertEqual(
            contract["orientation"],
            "no flip; offset=((greenRow*1024)+(blueSlice*32)+redIndex)*8",
        )
        for sentinel in contract["sentinels"]:
            offset = (sentinel["y"] * 1024 + sentinel["x"]) * 8
            self.assertEqual(payload[offset : offset + 8].hex(), sentinel["hex"])

    def test_exact_uber_uses_captured_lut_and_compatibility_keeps_builder(self) -> None:
        runtime = EXACT_LUT_RUNTIME.read_text(encoding="utf-8")
        pipeline = (
            RUNTIME_ROOT / "HGCompatRenderPipeline.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("GraphicsFormat.R16G16B16A16_SFloat", runtime)
        self.assertIn("SetPixelData<byte>(payload, 0)", runtime)
        self.assertIn("Apply(false, true)", runtime)
        self.assertIn("HasSentinel(payload, 1023, 31", runtime)
        self.assertIn("recoveredColorGradingLut.EnqueueBuild(commandBuffer)", pipeline)
        self.assertIn("recoveredColorGradingLut.ExactEndminfTexture", pipeline)
        self.assertGreaterEqual(pipeline.count("exactEndminfLut,"), 2)


if __name__ == "__main__":
    unittest.main()
