import json
import re
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
PLUGIN = ROOT / "tools/original_dxbc_exact/OriginalDxbcSwapPlugin.cpp"
CAPTURE = (
    ROOT
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldEndminfViewerPlayModeCapture.cs"
)
SOURCE_POST = (
    ROOT
    / "Assets/EndfieldGraphShaderLab/Resources/EndfieldEndminfSourcePost"
    / "endminf_overview_02_source_post_curves.json"
)
UBER_PAYLOAD = ROOT / "tools/original_dxbc_exact/EndminfUberCapturePayload.generated.h"
RUNTIMES = (
    "EndfieldRecoveredEndminfM18PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM21PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM28PeakExactRuntime.cs",
)


class EndminfPeakExactCaptureWindowContractTests(unittest.TestCase):
    def test_single_frame_packets_are_not_replayed_across_adjacent_ticks(self) -> None:
        for name in RUNTIMES:
            with self.subTest(runtime=name):
                source = (RUNTIME_ROOT / name).read_text(encoding="utf-8")
                self.assertRegex(
                    source,
                    r"HalfWindowSeconds\s*=\s*1\.0f\s*/\s*120\.0f;",
                )
                self.assertIn("Mathf.Abs(", source)
                self.assertIn("<=\n                HalfWindowSeconds", source)

        uber = (RUNTIME_ROOT / "EndfieldRecoveredEndminfUberExactRuntime.cs").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            uber,
            r"HalfWindowSeconds\s*=\s*1\.0f\s*/\s*120\.0f;",
        )
        self.assertNotIn("if (!IsCapturedPhase(hasPost, post))", uber)
        self.assertIn("EarlyCapturePhaseSeconds = 0.02256267f", uber)
        self.assertIn(
            '"ENDFIELD_RECOVERED_ENDMINF_UBER_EARLY_DIAGNOSTIC"',
            uber,
        )
        self.assertIn("uint variant = EarlyDiagnosticRequested &&", uber)
        self.assertIn("? 2u", uber)
        self.assertIn("QueuePacketVariant(", uber)
        self.assertIn("post.mode == 6", uber)
        self.assertIn("Mathf.Abs(post.elapsed - CapturePhaseSeconds)", uber)
        self.assertIn("Mathf.Abs(post.elapsed - EarlyCapturePhaseSeconds)", uber)

    def test_peak_packet_uses_authenticated_source_effect_clock(self) -> None:
        uber = (RUNTIME_ROOT / "EndfieldRecoveredEndminfUberExactRuntime.cs").read_text(
            encoding="utf-8"
        )
        capture = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("CapturePhaseSeconds = 4.4333334f", uber)
        self.assertIn("capturedUberPhaseSeconds = 4.4333334f", capture)

        phase = 4.4333334
        half_window = 1.0 / 120.0
        self.assertGreater(abs(4.35 - phase), half_window)
        self.assertLessEqual(abs(4.4333334 - phase), half_window)

        payload = json.loads(SOURCE_POST.read_text(encoding="utf-8"))
        curve_peak = {}
        for curve in payload["curves"]:
            for key in curve["keys"]:
                if abs(key["time"] - phase) < 1.0e-6:
                    curve_peak[curve["role"]] = key["d"]
        self.assertAlmostEqual(curve_peak["radialIntensity"], 0.109, places=6)
        self.assertAlmostEqual(curve_peak["chromaticIntensity"], 0.101, places=6)

        retained = UBER_PAYLOAD.read_text(encoding="utf-8")
        block = re.search(
            r"g_EndfieldUberPsB1\[\]\s*=\s*\{(.*?)\};",
            retained,
            re.DOTALL,
        )
        self.assertIsNotNone(block)
        packed = bytes(
            int(value, 16)
            for value in re.findall(r"0x([0-9a-fA-F]{2})", block.group(1))
        )
        self.assertAlmostEqual(struct.unpack_from("<f", packed, 2 * 4)[0],
                               0.10884803, places=7)
        self.assertAlmostEqual(struct.unpack_from("<f", packed, (25 * 4 + 1) * 4)[0],
                               0.10085920, places=7)
        native = PLUGIN.read_text(encoding="utf-8")
        self.assertRegex(
            native,
            re.compile(
                r"PatchEndminfUberFloat\(\s*packet->psB1,\s*"
                r"sizeof\(packet->psB1\),\s*2u,\s*radialIntensity\);",
                re.DOTALL,
            ),
        )

    def test_inactive_exact_paths_restore_the_authored_renderer(self) -> None:
        for name in RUNTIMES[:2]:
            with self.subTest(runtime=name):
                source = (RUNTIME_ROOT / name).read_text(encoding="utf-8")
                self.assertIn("renderer.enabled = !active", source)

        m28 = (RUNTIME_ROOT / RUNTIMES[2]).read_text(encoding="utf-8")
        prepare = m28.index("internal bool PrepareBeforeCulling")
        restore = m28.index("RestoreSourceRenderers();", prepare)
        active = m28.index("active = !float.IsNaN", restore)
        suppress = m28.index("SuppressSourceRenderers();", active)
        self.assertLess(restore, active)
        self.assertLess(active, suppress)

    def test_shared_native_release_invalidates_m18_m28_screen_patches(self) -> None:
        source = PLUGIN.read_text(encoding="utf-8")
        release = source.split("void ReleaseM14RuntimeResources()", 1)[1].split(
            "HRESULT CreateM14RuntimeResources", 1
        )[0]
        for owner in ("m18Peak", "m28Peak"):
            with self.subTest(owner=owner):
                self.assertIn(
                    f"g_{owner}ScreenSizePatched.store(0, std::memory_order_release);",
                    release,
                )
                self.assertIn(f"g_{owner}ResourceWidth = 0;", release)
                self.assertIn(f"g_{owner}ResourceHeight = 0;", release)


if __name__ == "__main__":
    unittest.main()
