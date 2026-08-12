from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_deferred_resolver_input_probe.py")
SPEC = importlib.util.spec_from_file_location(
    "verify_deferred_resolver_input_probe", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def ready_log() -> str:
    return "\n".join(
        (
            "Forcing GfxDevice: Direct3D 12",
            MODULE.G_BUFFER_TOKEN,
            MODULE.SHADOW_DATA_TOKEN,
            (
                "Recovered deferred resolver input consumer probe active: "
                "camera=MainCamera, size=640x720, publicationSerial=1, "
                "sourceIdentifiers=t23:_60,t24:_61,t25:_62, "
                "registerBridges=b0..b8, b6=zero-fallback, "
                "presented=false, retailPass0=false."
            ),
            (
                "Recovered deferred resolver input probe readback: "
                "camera=MainCamera, size=640x720, bytes=7372800, "
                "nonzeroBytes=5524150."
            ),
            (
                "Recovered deferred resolver target-resource snapshot: "
                "t0=ready,t1=ready,t5=ready,t6=ready,t7=absent,t11=absent, "
                "t1=640x720,t5=576x576x32,t6=6144x4096,t7=none,t11=none, "
                "allPhysical=false, screenContentValid=false."
            ),
            "Exiting batchmode successfully now!",
        )
    )


class DeferredResolverInputProbeLogTests(unittest.TestCase):
    def test_ready_same_frame_probe_passes(self) -> None:
        report = MODULE.validate_log(ready_log(), Path("ready.log"))
        self.assertTrue(report["valid"], report["failures"])
        self.assertEqual(report["active"]["publicationSerial"], 1)
        self.assertFalse(report["resources"]["allPhysical"])

    def test_strict_resource_probe_requires_target_resources(self) -> None:
        text = ready_log().replace(
            "t7=absent,t11=absent, t1=640x720,t5=576x576x32,t6=6144x4096,t7=none,t11=none, "
            "allPhysical=false",
            "t7=ready,t11=allocated, t1=640x720,t5=576x576x32,t6=6144x4096,t7=160x180,t11=640x720, "
            "allPhysical=true",
        )
        report = MODULE.validate_log(
            text,
            Path("strict-ready.log"),
            expect_resource_probe=True,
        )
        self.assertTrue(report["valid"], report["failures"])
        self.assertTrue(report["resources"]["allPhysical"])

    def test_missing_publication_is_actionable(self) -> None:
        text = ready_log().replace("publicationSerial=1", "publicationSerial=0")
        report = MODULE.validate_log(text, Path("missing-publication.log"))
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("publication_serial" in failure for failure in report["failures"])
        )

    def test_fail_closed_b34_is_actionable(self) -> None:
        text = "\n".join(
            (
                "Forcing GfxDevice: Direct3D 12",
                "Recovered deferred resolver input probe failed closed: "
                "selected b30/b35/b31/b34 inputs are not all ready: "
                "b30=True, b35=True, b31=True, b34=False.",
                "Exiting batchmode successfully now!",
            )
        )
        report = MODULE.validate_log(
            text,
            Path("fail-closed.log"),
            expect_fail_closed=True,
        )
        self.assertTrue(report["valid"], report["failures"])

    def test_strict_resource_probe_failure_keeps_upstream_evidence(self) -> None:
        text = "\n".join(
            (
                "Forcing GfxDevice: Direct3D 12",
                MODULE.G_BUFFER_TOKEN,
                MODULE.SHADOW_DATA_TOKEN,
                "Recovered deferred resolver input probe failed closed: "
                "strict resolver target-resource probe requires physical "
                "t0/t1/t5/t6/t7/t11 resources: "
                "t0=ready,t1=ready,t5=ready,t6=ready,t7=absent,t11=absent.",
                "Exiting batchmode successfully now!",
            )
        )
        report = MODULE.validate_log(
            text,
            Path("strict-fail-closed.log"),
            expect_fail_closed=True,
            expect_resource_probe=True,
        )
        self.assertTrue(report["valid"], report["failures"])


if __name__ == "__main__":
    unittest.main()
