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
Recovered exact deferred resolver consumer submitted: camera=MainCamera, size=640x720, publicationSerial=1, exactBound=1, resourceMask=0xfffffff, resourceFailureMask=0x0, resourceFailureResults=none, constantBufferMask=0x3ff, failureCount=0, presented=false, retailPass0=false, screenContentValid=false.
Recovered exact deferred resolver consumer readback: camera=MainCamera, size=640x720, bytes=7372800, nonzeroBytes=6430845, exactBound=1, resourceMask=0xfffffff, resourceFailureMask=0x0, resourceFailureResults=none, constantBufferMask=0x3ff, rgbaFloatSha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef, finiteFloats=1843200, nonFiniteFloats=0, min=0, max=1, failureCount=0, presented=false, retailPass0=false.
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
        self.assertIn("case 12: return fallbackArray;", source)
        self.assertIn("case 15: return integratedFogFallback;", source)
        self.assertIn("TextureFormat.ASTC_4x4", source)
        self.assertIn("t12=LightCookie:black-zero-cookie", source)
        self.assertIn("t15=IntegratedFog:black-disabled-1x1-ASTC", source)
        self.assertIn("t18-t23=IrradianceV2:zero-inactive-fallback", source)
        self.assertIn("t25-t27=GBuffer:A/B/C", source)
        self.assertIn("fallbackTextureSlots=t2,t3,t4.", source)
        self.assertIn("legacy Gacha payload", source)

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
            "                 recoveredDeferredExactConsumer.Requested)",
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
            GOOD_LOG.replace("resourceMask=0xfffffff", "resourceMask=0xfffff5f"),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("readback_resource_mask_all_t0_t27" in failure
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
