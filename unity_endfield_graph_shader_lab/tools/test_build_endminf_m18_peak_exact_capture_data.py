import tempfile
import unittest
from pathlib import Path

import build_endminf_m18_peak_exact_capture_data as build


class M18PeakCaptureDataTests(unittest.TestCase):
    def test_collect_pins_exact_diffusion_shell(self) -> None:
        packet = build.collect(build.CAPTURE)
        self.assertEqual(len(packet["vertices"]), 204 * 76)
        self.assertEqual(len(packet["indices"]), 900 * 2)
        self.assertEqual(len(packet["secondary"]), 20)
        self.assertEqual(build.m21.sha256(packet["vertices"]), build.VERTEX_SHA256)
        self.assertEqual(build.m21.sha256(packet["indices"]), build.INDEX_SHA256)
        self.assertEqual(len(packet["constants"][0]), 5)
        self.assertEqual(len(packet["constants"][4]), 4)

    def test_build_emits_native_and_managed_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            cs = Path(root) / "capture.cs"
            cpp = Path(root) / "capture.h"
            build.build(build.CAPTURE, cs, cpp)
            self.assertIn("DrawOrdinal = 82", cs.read_text(encoding="utf-8"))
            text = cpp.read_text(encoding="utf-8")
            self.assertIn("g_EndfieldM18PeakVertexDxbc", text)
            self.assertIn("g_EndfieldM18PeakPSDeclaredFloat4Counts", text)


if __name__ == "__main__":
    unittest.main()
