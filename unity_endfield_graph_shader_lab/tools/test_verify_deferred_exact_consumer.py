import unittest
import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("verify_deferred_exact_consumer.py")
LAB_ROOT = MODULE_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_deferred_exact_consumer", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
validate_log = MODULE.validate_log


GOOD_LOG = """
Exiting batchmode successfully now!
Recovered exact deferred resolver consumer submitted: camera=MainCamera, size=640x720, publicationSerial=1, exactBound=1, resourceMask=0x3ffffff, resourceFailureMask=0x0, resourceFailureResults=none, constantBufferMask=0x1ff, failureCount=0, presented=false, retailPass0=false, screenContentValid=false.
Recovered exact deferred resolver consumer readback: camera=MainCamera, size=640x720, bytes=7372800, nonzeroBytes=6430845, exactBound=1, resourceMask=0x3ffffff, resourceFailureMask=0x0, resourceFailureResults=none, constantBufferMask=0x1ff, rgbaFloatSha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef, finiteFloats=1843200, nonFiniteFloats=0, nonzeroRgbFloats=123456, screenContentValid=true, min=0, max=1, failureCount=0, presented=false, retailPass0=false.
Recovered deferred pass-0 HLSL vs exact DXBC comparison: camera=MainCamera, size=640x720, floatCount=1843200, maxAbs=1.1920929E-07, rmse=4.8E-09, over1e-6=0, over1e-4=0, over1e-3=0, presented=false.
"""


class VerifyDeferredExactConsumerTests(unittest.TestCase):
    def test_source_closed_cookie_and_disabled_fog_slots_are_explicit(self):
        source = (
            LAB_ROOT
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Runtime"
            / "Rendering"
            / "EndfieldRecoveredDeferredExactConsumer.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("case 11: return resources.t11ScreenShadow;", source)
        self.assertIn("case 12: return Texture2D.blackTexture;", source)
        self.assertIn("case 13: return integratedFogFallback;", source)
        self.assertIn("TextureFormat.ASTC_4x4", source)
        self.assertIn("t11=screenShadow:", source)
        self.assertIn("t12=LightCookie:black-zero-cookie", source)
        self.assertIn("t13=IntegratedFog:black-disabled-1x1-ASTC", source)
        self.assertIn("t16-t21=IrradianceV2:zero-inactive-fallback", source)
        self.assertIn("t23-t25=GBuffer:A/B/C", source)
        self.assertIn("fallbackTextureSlots=t2,t3,t4.", source)
        self.assertIn("legacy Gacha payload", source)

    def test_physical_diagnostic_t11_cannot_authorize_presentation(self):
        resource_probe = (
            LAB_ROOT
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Runtime"
            / "Rendering"
            / "EndfieldRecoveredDeferredResolverInputProbe.cs"
        ).read_text(encoding="utf-8")
        screen_shadow = (
            LAB_ROOT
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Runtime"
            / "Rendering"
            / "EndfieldRecoveredScreenShadowMaskProducer.cs"
        ).read_text(encoding="utf-8")
        consumer = (
            LAB_ROOT
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Runtime"
            / "Rendering"
            / "EndfieldRecoveredDeferredExactConsumer.cs"
        ).read_text(encoding="utf-8")

        # Keep the strict physical diagnostic gate intact. Content validity is
        # a separate same-frame publication property, not a relaxed AllPhysical.
        self.assertIn("T7Ready && T11Ready", resource_probe)
        self.assertIn("internal bool t11ContentValid;", resource_probe)
        self.assertIn("out frame.t11ContentValid", resource_probe)
        self.assertIn("publicationContentValid = contentValid;", screen_shadow)
        self.assertIn("bool contentValid = false;", screen_shadow)
        self.assertIn("contentValid = publicationContentValid;", screen_shadow)

        # A nonzero exact readback is necessary but insufficient: the invalid
        # diagnostic mask may execute the DXBC, but it cannot reach M27 display.
        self.assertIn(
            "exactContentValid = t11ContentValid && numericContentValid;",
            consumer,
        )
        self.assertIn("t11ContentValid={t11ContentValid}", consumer)
        presentation = consumer.split("internal bool PresentationReady =>", 1)[1]
        presentation = presentation.split("internal void SuppressInactiveFrame", 1)[0]
        self.assertIn("exactContentValid", presentation)

    def test_runtime_event_arm_owns_the_deferred_route(self):
        source = (
            LAB_ROOT / "tools" / "original_dxbc_exact" /
            "OriginalDxbcSwapPlugin.cpp"
        ).read_text(encoding="utf-8")
        arm = source.split("void ArmDiagnosticOnRenderThread()", 1)[1].split(
            "void UNITY_INTERFACE_API InspectPostDrawBindings", 1
        )[0]
        self.assertIn("SubstitutionRoute::DeferredDiagnostic", arm)
        cleanup = source.split(
            "void CompleteDiagnosticSubmissionOnRenderThread()", 1
        )[1].split(
            "void AbandonDiagnosticSubmission", 1
        )[0]
        self.assertIn("SubstitutionRoute::None", cleanup)

    def test_exact_consumer_submission_lifetime_uses_completion_serial(self):
        native = (
            LAB_ROOT / "tools" / "original_dxbc_exact" /
            "OriginalDxbcSwapPlugin.cpp"
        ).read_text(encoding="utf-8")
        consumer = (
            LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Runtime" /
            "Rendering" / "EndfieldRecoveredDeferredExactConsumer.cs"
        ).read_text(encoding="utf-8")

        begin = native.split(
            "EndfieldOriginalDxbcBeginDiagnosticSubmission", 1
        )[1].split(
            "EndfieldOriginalDxbcCancelDiagnosticSubmission", 1
        )[0]
        self.assertIn("g_configuredDiagnosticSubmissionSerial", begin)
        self.assertIn("resource->AddRef()", begin)
        self.assertIn("g_diagnosticSubmissionMutex", begin)
        self.assertIn(
            "retainedResourceCount != kDiagnosticRetainedResourceCapacity",
            begin,
        )
        exhaustion_check = (
            "g_nextDiagnosticSubmissionSerial ==\n"
            "        (std::numeric_limits<std::uint64_t>::max)()"
        )
        self.assertIn(exhaustion_check, begin)
        self.assertNotIn("g_nextDiagnosticSubmissionSerial == 0", begin)
        self.assertLess(
            begin.index(exhaustion_check),
            begin.index("ReleaseDiagnosticRetainedResourcesLocked()"),
            "serial exhaustion must reject before native resource state changes",
        )
        self.assertLess(
            begin.index(exhaustion_check),
            begin.index("resource->AddRef()"),
            "serial exhaustion must reject before retaining any resources",
        )
        completion = native.split(
            "void CompleteDiagnosticSubmissionOnRenderThread()", 1
        )[1].split(
            "void AbandonDiagnosticSubmission", 1
        )[0]
        self.assertIn("ClearDiagnosticSubmissionLocked(serial)", completion)
        self.assertIn("ReleaseRuntimeShaders()", completion)
        event = native.split(
            "void UNITY_INTERFACE_API InspectPostDrawBindings", 1
        )[1].split("extern \"C\"", 1)[0]
        self.assertLess(event.index("if (eventId == 2)"),
                        event.index("if (!g_armed.load"))

        self.assertIn("nativePendingSubmissionSerial", consumer)
        self.assertIn("GetCompletedDiagnosticSubmissionSerial", consumer)
        self.assertIn("BeginDiagnosticSubmission", consumer)
        self.assertIn("CancelDiagnosticSubmission", consumer)
        pending_gate = consumer.split(
            "if (nativePendingSubmissionSerial != 0)", 1
        )[1].split("if (SystemInfo.graphicsDeviceType", 1)[0]
        self.assertNotIn("GetDiagnosticArmed", pending_gate)

    def test_pipeline_disposes_exact_consumer_before_input_resources(self):
        pipeline = (
            LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Runtime" /
            "Rendering" / "HGCompatRenderPipeline.cs"
        ).read_text(encoding="utf-8")
        dispose = pipeline.split(
            "protected override void Dispose(bool disposing)", 1
        )[1].split("private void", 1)[0]
        exact = dispose.index("recoveredDeferredExactConsumer?.Dispose()")
        self.assertLess(exact, dispose.index("recoveredDeferredGBufferFrame?.Dispose()"))
        self.assertLess(exact, dispose.index("recoveredPunctualShadowProducer?.Dispose()"))
        self.assertLess(exact, dispose.index("recoveredDeferredShadowData?.Dispose()"))

    def test_canonical_capture_rejects_both_diagnostic_dynamics_owners(self):
        capture = (
            LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" /
            "CharacterRecovery" / "EndfieldEndminfViewerPlayModeCapture.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("videoExport && enableSecondaryDynamicsSolver", capture)
        self.assertIn("videoExport && enableCapturedSecondaryDynamicsReplay", capture)
        self.assertIn("cannot use the unverified", capture)
        self.assertIn("cannot use a captured hair/cape", capture)
        self.assertIn("observedCanonicalSecondaryDynamicsOwnership", capture)
        self.assertIn("!value.capturedSecondaryReplayEnabled", capture)
        self.assertIn("!value.capturedSecondaryReplayPoseAppliedThisFrame", capture)

    def test_exact_consumer_requires_current_cookie_publication_provenance(self):
        consumer = (
            LAB_ROOT
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Runtime"
            / "Rendering"
            / "EndfieldRecoveredDeferredExactConsumer.cs"
        ).read_text(encoding="utf-8")
        binning = (
            LAB_ROOT
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Runtime"
            / "Rendering"
            / "EndfieldRecoveredLightBinning.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("TryGetCurrentExactConstantBuffers", consumer)
        self.assertIn("lightCookiePublicationValid", binning)
        self.assertIn("retailConstantsPublicationValid", binning)
        self.assertIn("retailPublicationCameraInstanceId", binning)
        self.assertIn("retailPublicationFrame != Time.frameCount", binning)
        self.assertIn(
            "current-camera LightBinningConstants/zero-cookie publication is not provenance-valid",
            binning,
        )

    def test_exact_consumer_keeps_a_physical_depth_copy_with_world_ui(self):
        pipeline = (
            LAB_ROOT
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Runtime"
            / "Rendering"
            / "HGCompatRenderPipeline.cs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "((!useRecoveredPostUberWorldUi && !useRecoveredSceneMV) ||\n"
            "                 recoveredDeferredExactConsumer.Requested &&\n"
            "                 recoveredEndminfLitEffectOwnerActive)",
            pipeline,
        )

    def test_accepts_exact_non_presented_frame(self):
        report = validate_log(GOOD_LOG, Path("fixture.log"))
        self.assertTrue(report["valid"], report["failures"])

    def test_accepts_dynamic_full_hd_extent(self):
        full_hd = (GOOD_LOG.replace("640x720", "1920x1080")
                   .replace("7372800", "33177600")
                   .replace("1843200", "8294400"))
        report = validate_log(full_hd, Path("fixture-full-hd.log"))
        self.assertTrue(report["valid"], report["failures"])

    def test_reports_missing_exact_binding(self):
        report = validate_log(
            GOOD_LOG.replace("exactBound=1", "exactBound=0"),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(any("exact_shader_bound" in failure for failure in report["failures"]))

    def test_reports_incomplete_resource_mask(self):
        report = validate_log(
            GOOD_LOG.replace("resourceMask=0x3ffffff", "resourceMask=0x3ffff5f"),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("readback_resource_mask_all_t0_t25" in failure
                for failure in report["failures"])
        )

    def test_reports_zero_rgb_content(self):
        report = validate_log(
            GOOD_LOG.replace("nonzeroRgbFloats=123456", "nonzeroRgbFloats=0"),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("readback_nonzero_rgb" in failure
                for failure in report["failures"])
        )

    def test_reports_invalid_screen_content(self):
        report = validate_log(
            GOOD_LOG.replace("screenContentValid=true, min=", "screenContentValid=false, min="),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("readback_screen_content_valid" in failure
                for failure in report["failures"])
        )

    def test_missing_rgb_validity_fields_fails_closed(self):
        report = validate_log(
            GOOD_LOG.replace(
                "nonzeroRgbFloats=123456, screenContentValid=true, ",
                "",
            ),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("readback_record_count" in failure
                for failure in report["failures"])
        )

    def test_reports_hlsl_numeric_drift(self):
        report = validate_log(
            GOOD_LOG.replace("over1e-6=0", "over1e-6=7"),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("hlsl_comparison_over_1e6" in failure
                for failure in report["failures"])
        )


if __name__ == "__main__":
    unittest.main()
