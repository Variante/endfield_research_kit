from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_visibility_sh_frame_log.py")
MODULE_SPEC = importlib.util.spec_from_file_location(
    "verify_visibility_sh_frame_log",
    MODULE_PATH,
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"cannot load verifier module: {MODULE_PATH}")
verifier = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(verifier)


GOOD_LOG = """
-force-d3d12
Forcing GfxDevice: Direct3D 12
Recovered canonical CharInfo binning + reflection oct/global + exact VisibilitySHConstData frame resources are active
Recovered VisibilitySH CPU capsule fixture: actor=Wulfa, count=10, stride=48, order=[0,1,2,3,4,5,6,7,8,9], sha256=687ab01a054e6ef9d07e982de605489de181da089e221e14b450b108161bd5c1.
Recovered VisibilitySH producer active: Wulfa, 10/10 retail-cull survivors, order=[0,1,2,3,4,5,6,7,8,9], 320x360 RGBAHalf, retail defaults interval=0.8/range=5/half-resolution, canonicalPublication=ready.
Recovered VisibilitySH GPU readback: actor=Wulfa, size=320x360, bytes=921600, nonzeroPixels=20006, sha256=ceaa3f173c90ffbdffa6062f9b046863ebd16fb554101856b8e0126a9d0cdb52.
Exiting batchmode successfully now!
"""


class VisibilitySHFrameLogTests(unittest.TestCase):
    def test_good_log_passes(self) -> None:
        report = verifier.validate_log(
            GOOD_LOG,
            "d3d12",
            Path("fixture.log"),
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["activeFrame"]["canonicalPublication"], "ready")

    def test_missing_canonical_gate_is_actionable(self) -> None:
        changed = GOOD_LOG.replace(
            "Recovered canonical CharInfo binning + reflection oct/global + exact VisibilitySHConstData frame resources are active\n",
            "",
        )
        report = verifier.validate_log(changed, "d3d12", Path("fixture.log"))
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "check=canonical_prerequisites; source=fixture.log; "
                "expected=True; actual=False" in failure
                for failure in report["failures"]
            )
        )

    def test_zero_gpu_output_is_actionable(self) -> None:
        changed = GOOD_LOG.replace("nonzeroPixels=20006", "nonzeroPixels=0")
        report = verifier.validate_log(changed, "d3d12", Path("fixture.log"))
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "check=readback_nonzero; source=fixture.log; "
                "expected=True; actual=False" in failure
                for failure in report["failures"]
            )
        )

    def test_fail_closed_gate_passes_without_canonical_prerequisites(self) -> None:
        changed = GOOD_LOG.replace(
            "Recovered canonical CharInfo binning + reflection oct/global + exact VisibilitySHConstData frame resources are active\n",
            "",
        ).replace(
            "canonicalPublication=ready",
            "canonicalPublication=fail-closed",
        )
        report = verifier.validate_log(
            changed,
            "d3d12",
            Path("fixture.log"),
            "fail-closed",
        )
        self.assertTrue(report["valid"])


if __name__ == "__main__":
    unittest.main()
