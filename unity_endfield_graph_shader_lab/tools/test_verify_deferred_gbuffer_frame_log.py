import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_deferred_gbuffer_frame_log.py")
SPEC = importlib.util.spec_from_file_location(
    "verify_deferred_gbuffer_frame_log", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def ready_log() -> str:
    lines = [
        "Forcing GfxDevice: Direct3D 12",
        MODULE.PREREQUISITE_TOKEN,
        (
            "Recovered SphereOutside same-frame HGBuffer sidecar active: "
            "camera=MainCamera, size=640x720, "
            "attachments=B10G11R11/A2B10G10R10/A2B10G10R10/"
            "A2B10G10R10/R8G8B8A8_SRGB+D32S8, "
            "sourceRendererDisabled=True, "
            "resolverGBufferBindings=t23:C,t24:B,t25:A, "
            "pass0ConsumerEnabled=false."
        ),
    ]
    for role, expected in MODULE.EXPECTED_READBACKS.items():
        lines.append(
            "Recovered deferred HGBuffer GPU readback: "
            f"role={role}, camera=MainCamera, size=640x720, "
            f"format={expected['format']}, bytes=1843200, "
            f"nonzeroBytes={expected['nonzeroBytes']}, "
            f"sha256={expected['sha256']}."
        )
    lines.append("Exiting batchmode successfully now!")
    return "\n".join(lines)


class DeferredGBufferFrameLogTests(unittest.TestCase):
    def test_producer_publishes_source_closed_resolver_gbuffer_aliases(self):
        producer = (
            Path(__file__).resolve().parents[1]
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
            "EndfieldRecoveredDeferredGBufferFrame.cs"
        )
        source = producer.read_text(encoding="utf-8")
        self.assertIn(
            "command.SetGlobalTexture(ResolverGBufferT23Id, gBufferC)",
            source,
        )
        self.assertIn(
            "command.SetGlobalTexture(ResolverGBufferT24Id, gBufferB)",
            source,
        )
        self.assertIn(
            "command.SetGlobalTexture(ResolverGBufferT25Id, gBufferA)",
            source,
        )

    def test_ready_frame_passes(self):
        report = MODULE.validate_log(
            ready_log(), "d3d12", Path("ready.log")
        )
        self.assertTrue(report["valid"], report["failures"])

    def test_changed_payload_is_actionable(self):
        text = ready_log().replace(
            MODULE.EXPECTED_READBACKS["GBufferB"]["sha256"], "0" * 64
        )
        report = MODULE.validate_log(text, "d3d12", Path("changed.log"))
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("GBufferB.sha256" in value for value in report["failures"])
        )

    def test_missing_readback_is_actionable(self):
        text = "\n".join(
            line for line in ready_log().splitlines() if "role=GBufferC," not in line
        )
        report = MODULE.validate_log(text, "d3d12", Path("missing.log"))
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("readback_count" in value for value in report["failures"])
        )

    def test_fail_closed_without_prerequisites_passes(self):
        text = "\n".join(
            (
                "Forcing GfxDevice: Direct3D 12",
                MODULE.FAIL_CLOSED_TOKEN,
                "Exiting batchmode successfully now!",
            )
        )
        report = MODULE.validate_log(
            text,
            "d3d12",
            Path("fail-closed.log"),
            expect_fail_closed=True,
        )
        self.assertTrue(report["valid"], report["failures"])


if __name__ == "__main__":
    unittest.main()
