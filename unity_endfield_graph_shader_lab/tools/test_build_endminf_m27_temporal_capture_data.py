#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("build_endminf_m27_temporal_capture_data.py")
SPEC = importlib.util.spec_from_file_location("m27_temporal_builder", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class M27TemporalBuilderTests(unittest.TestCase):
    def test_current_capture_generates_current_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cs = Path(directory) / "payload.cs"
            cpp = Path(directory) / "payload.h"
            generated = MODULE.build(MODULE.CAPTURE, MODULE.REPORT, cs, cpp)
            generated_cpp = cpp.read_text(encoding="utf-8")
        self.assertEqual(generated, MODULE.CS_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(generated_cpp, MODULE.CPP_OUTPUT.read_text(encoding="utf-8"))
        self.assertIn("PacketCount = 16", generated)
        self.assertIn("TotalDrawCount = 39", generated)
        self.assertIn("g_EndfieldM27TemporalDrawCount = 39u", generated_cpp)
        self.assertIn("g_EndfieldM27TemporalFrameCount", generated_cpp)

    def test_preserves_both_ia_layouts_and_zero_draw_transition(self) -> None:
        frames, textures = MODULE.collect(MODULE.CAPTURE, MODULE.REPORT)
        self.assertEqual(len(frames), 16)
        self.assertEqual(len(textures), 6)
        self.assertEqual({draw["vertex_stride"] for frame in frames
                          for draw in frame["draws"]}, {60, 68})
        transition = next(frame for frame in frames if frame["frame"] == 2970)
        self.assertEqual(transition["draws"], [])
        self.assertEqual([texture["format"] for texture in textures],
                         [99, 83, 83, 99, 29, 29])

    def test_native_loader_admits_captured_srgb_bc7(self) -> None:
        plugin = (MODULE.CPP_OUTPUT.parent / "OriginalDxbcSwapPlugin.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("format == DXGI_FORMAT_BC7_UNORM_SRGB", plugin)
        self.assertIn("EndfieldOriginalDxbcGetM27DrawFailureStage", plugin)


if __name__ == "__main__":
    unittest.main()
