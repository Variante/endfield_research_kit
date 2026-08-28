import tempfile
import unittest
from pathlib import Path

import build_endminf_opening_strip_exact_capture_data as builder


class OpeningStripExactCaptureDataTests(unittest.TestCase):
    def test_retained_packets_build_deterministically(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "capture.cs"
            header = Path(root) / "capture.h"
            text = builder.build(output, header)
            self.assertEqual(text, output.read_text(encoding="utf-8"))
            self.assertIn("PacketCount = 4", text)
            self.assertIn("1034, 1035, 1036, 1037", text)
            self.assertIn("11610, 7998, 4176, 420", text)
            generated = header.read_text(encoding="utf-8")
            self.assertIn("g_EndfieldOpeningStripPacketCount", generated)
            self.assertIn("g_EndfieldOpeningStripVertexDxbc", generated)
            self.assertIn("g_EndfieldOpeningStripPixelDxbc", generated)

    def test_runtime_owns_mask_and_accepts_only_live_scene_color(self):
        plugin = (builder.REPO / "unity_endfield_graph_shader_lab/tools/"
                  "original_dxbc_exact/OriginalDxbcSwapPlugin.cpp").read_text(
                      encoding="utf-8")
        runtime = (builder.REPO / "unity_endfield_graph_shader_lab/Assets/"
                   "EndfieldGraphShaderLab/Runtime/Rendering/"
                   "EndfieldRecoveredEndminfOpeningStripExactRuntime.cs").read_text(
                       encoding="utf-8")
        self.assertIn("g_openingStripMaskView", plugin)
        self.assertIn("void* sceneColorTexture)", plugin)
        self.assertNotIn("void* refractTexture, void* sceneColorTexture", plugin)
        self.assertIn("SetTextureResources(IntPtr sceneColor)", runtime)
        self.assertNotIn("source-closed opening-strip material binding is absent",
                         runtime)


if __name__ == "__main__":
    unittest.main()
