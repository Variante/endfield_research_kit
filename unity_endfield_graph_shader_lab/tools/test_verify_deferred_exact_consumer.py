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
Recovered exact deferred resolver consumer readback: camera=MainCamera, size=640x720, bytes=7372800, nonzeroBytes=6430845, exactBound=1, resourceMask=0x3ffffff, resourceFailureMask=0x0, resourceFailureResults=none, constantBufferMask=0x1ff, rgbaFloatSha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef, finiteFloats=1843200, nonFiniteFloats=0, min=0, max=1, failureCount=0, presented=false, retailPass0=false.
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
        self.assertIn("case 12: return Texture2D.blackTexture;", source)
        self.assertIn("case 13: return integratedFogFallback;", source)
        self.assertIn("TextureFormat.ASTC_4x4", source)
        self.assertIn("t12=LightCookie:black-zero-cookie", source)
        self.assertIn("t13=IntegratedFog:black-disabled-1x1-ASTC", source)

    def test_accepts_exact_non_presented_frame(self):
        report = validate_log(GOOD_LOG, Path("fixture.log"))
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
            GOOD_LOG.replace("resourceMask=0x3ffffff", "resourceMask=0x3fff5f"),
            Path("fixture.log"),
        )
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("readback_resource_mask_all_t0_t25" in failure
                for failure in report["failures"])
        )


if __name__ == "__main__":
    unittest.main()
