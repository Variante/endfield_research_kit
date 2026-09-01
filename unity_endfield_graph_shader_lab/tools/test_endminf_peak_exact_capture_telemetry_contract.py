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
MANIFEST_SETUP = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldManifestCharacterSetup.cs"
)
PACKET_RUNTIME_NAMES = (
    "EndfieldRecoveredEndminfM13ExactRuntime.cs",
    "EndfieldRecoveredEndminfM14ExactRuntime.cs",
    "EndfieldRecoveredEndminfM18PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM20PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM21PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM27ExactRuntime.cs",
    "EndfieldRecoveredEndminfM28PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM29ExactRuntime.cs",
    "EndfieldRecoveredEndminfM31PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfOpeningStripExactRuntime.cs",
    "EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime.cs",
)
PACKET_REPLAY_FLAGS = (
    "ENDFIELD_RECOVERED_ENDMINF_M13_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M14_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M18_PEAK_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M20_PEAK_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC",
    "ENDFIELD_RECOVERED_ENDMINF_M28_PEAK_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M29_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M30_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_M31_PEAK_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_OPENING_STRIP_EXACT",
    "ENDFIELD_RECOVERED_ENDMINF_VFXBASEV2_PEAK_COHORT_EXACT",
)


class EndminfPeakExactCaptureTelemetryContractTests(unittest.TestCase):
    def test_cached_viewer_rebuild_preserves_enriched_actor_prefabs(self) -> None:
        source = MANIFEST_SETUP.read_text(encoding="utf-8")
        rebuild = source.split(
            "public static void RebuildSharedViewerSceneFromCachedAssets()", 1
        )[1].split(
            "public static void RebuildSharedViewerSceneFromOriginalMeshes()", 1
        )[0]
        self.assertIn("BuildCharacterViewer(", rebuild)
        self.assertIn("preserveExistingGeneratedAssets: true", rebuild)
        self.assertNotIn("RebuildSharedViewerScene(rebuildMeshAssets: false)", rebuild)

    def test_targeted_exact_probe_fails_when_source_fixture_is_missing(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("bool exactConsumerSourceFixtureReady", source)
        for gate in (
            "observedEntranceVfx",
            "observedPrimaryRockCompatibilityBinding",
            "observedDeferredLightDataReady",
            "observedDeferredShadowDataReady",
            "observedDeferredPass0InputSubsetReady",
            "observedDeferredGBufferFrameReady",
            "observedEndminfM27HGBufferReady",
        ):
            self.assertIn(gate, source)
        self.assertIn(
            "requiredCaptureContractReady &&\n"
            "                exactConsumerSourceFixtureReady",
            source,
        )

    def test_report_schema_and_rows_publish_each_exact_packet_state(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endminf-viewer-playmode-sequence.v21", source)
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
        for material in ("M18", "M21", "M28", "M31"):
            for state in ("Requested", "Active", "Submitted", "Validated", "Failure"):
                field = f"endminf{material}Exact{state}"
                self.assertGreaterEqual(source.count(field), 2, field)

    def test_runtimes_reset_and_publish_per_frame_submission_state(self) -> None:
        for material in ("M18", "M21", "M28", "M31"):
            path = RUNTIME_ROOT / (
                f"EndfieldRecoveredEndminf{material}PeakExactRuntime.cs"
            )
            source = path.read_text(encoding="utf-8")
            prepare = source.index("PrepareBeforeCulling")
            render = source.index(
                "RenderSecond(" if material == "M31" else "Render(",
                prepare,
            )
            self.assertIn("submittedThisFrame = false", source[prepare:render])
            self.assertIn("validatedThisFrame = false", source[prepare:render])
            self.assertIn("submittedThisFrame = true", source[render:])
            self.assertIn("validatedThisFrame = true", source[render:])

    def test_m31_expected_phase_is_fail_closed_in_the_report(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        runtime = (
            RUNTIME_ROOT / "EndfieldRecoveredEndminfM31PeakExactRuntime.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("IsCapturedPhase(activeBodyClipTime)", source)
        self.assertIn("expectedEndminfM31Frames.All", source)
        self.assertIn("endminfM31ExactRequirementReady", source)
        self.assertIn("IsCapturedPhase(float overviewSeconds)", runtime)

    def test_normal_reproduction_keeps_captured_packet_replays_diagnostic_only(
        self,
    ) -> None:
        source = OPEN_WRAPPER.read_text(encoding="utf-8")
        for flag in PACKET_REPLAY_FLAGS:
            self.assertNotIn(f'set "{flag}=1"', source, flag)
        self.assertNotIn(
            'set "ENDFIELD_RECOVERED_ENDMINF_UBER_EXACT=1"',
            source,
        )
        self.assertIn("fixed geometry", source)
        self.assertIn("source runtime", source)

    def test_canonical_video_keeps_packet_replays_opt_in_and_retains_overrides(
        self,
    ) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        wrapper = OPEN_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("CanonicalVideoDefaultFlags", source)
        self.assertIn("if (videoExportRequested)", source)
        self.assertIn("Environment.GetEnvironmentVariable(flag)", source)
        self.assertIn('Environment.SetEnvironmentVariable(flag, "1")', source)
        start = source.index("CanonicalVideoDefaultFlags")
        defaults = source[start:source.index("};", start)]
        for flag in PACKET_REPLAY_FLAGS:
            self.assertNotIn(flag, defaults, flag)
            self.assertNotIn(f'set "{flag}=1"', wrapper, flag)

    def test_packet_replays_use_only_authenticated_source_effect_time(
        self,
    ) -> None:
        for path in sorted(RUNTIME_ROOT.glob("EndfieldRecoveredEndminf*Runtime.cs")):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("ViewerLeadSeconds", source, path.name)
        for name in PACKET_RUNTIME_NAMES:
            source = (RUNTIME_ROOT / name).read_text(encoding="utf-8")
            self.assertIn(
                "TryGetAuthenticatedSourceEffectElapsed",
                source,
                name,
            )
            self.assertNotIn("GetCurrentAnimatorStateInfo", source, name)
            self.assertNotIn('animation["ui_overview_start"]', source, name)

    def test_obsolete_untracked_m30_runtime_has_no_tracked_consumers(self) -> None:
        obsolete_runtime = "EndfieldRecoveredEndminfM" + "30ExactRuntime"
        for path in (
            RUNTIME_ROOT / "HGCompatRenderPipeline.cs",
            CAPTURE,
        ):
            self.assertNotIn(
                obsolete_runtime,
                path.read_text(encoding="utf-8"),
                path.name,
            )

    def test_canonical_video_rejects_unclosed_uber_input_chronology(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        start = source.index("CanonicalVideoDefaultFlags")
        defaults = source[start:source.index("};", start)]
        self.assertNotIn("ENDFIELD_RECOVERED_ENDMINF_UBER_EXACT", defaults)
        self.assertIn("input chronology is not source-closed", defaults)

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
