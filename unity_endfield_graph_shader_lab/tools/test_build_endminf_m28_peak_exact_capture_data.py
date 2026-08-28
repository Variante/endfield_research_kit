import tempfile
import unittest
from pathlib import Path

import build_endminf_m28_peak_exact_capture_data as build


class M28PeakCaptureDataTests(unittest.TestCase):
    def test_collect_pins_exact_refractive_sphere_packet(self) -> None:
        packet = build.collect(build.CAPTURE)
        self.assertEqual(len(packet["vertices"]), 344 * 60)
        self.assertEqual(len(packet["indices"]), 1764 * 2)
        self.assertEqual(len(packet["secondary"]), 20)
        self.assertEqual(build.m21.sha256(packet["vertices"]), build.VERTEX_SHA256)
        self.assertEqual(build.m21.sha256(packet["indices"]), build.INDEX_SHA256)
        self.assertEqual([len(value) for value in packet["constants"][0]],
                         [2 * 16, 82 * 16, 20 * 16, 16 * 16, 5 * 16])
        self.assertEqual([len(value) for value in packet["constants"][4]],
                         [28 * 16, 104 * 16, 16 * 16, 11 * 16])

    def test_build_emits_native_and_managed_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            cs = Path(root) / "capture.cs"
            cpp = Path(root) / "capture.h"
            build.build(build.CAPTURE, cs, cpp)
            self.assertIn("SourceFrame = 2775", cs.read_text(encoding="utf-8"))
            text = cpp.read_text(encoding="utf-8")
            self.assertIn("g_EndfieldM28PeakVertexDxbc", text)
            self.assertIn("g_EndfieldM28PeakPSDeclaredFloat4Counts", text)


if __name__ == "__main__":
    unittest.main()
