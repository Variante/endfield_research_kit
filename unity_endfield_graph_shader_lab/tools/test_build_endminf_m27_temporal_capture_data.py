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
        self.assertIn("PacketCount = 38", generated)
        self.assertIn("TotalDrawCount = 157", generated)
        self.assertIn("g_EndfieldM27TemporalDrawCount = 157u", generated_cpp)
        self.assertIn(
            "g_EndfieldM27TemporalMaximumDrawsPerFrame = 6u", generated_cpp)
        self.assertIn("g_EndfieldM27TemporalFrameCount", generated_cpp)

    def test_preserves_both_ia_layouts_and_zero_draw_transition(self) -> None:
        frames, textures = MODULE.collect(MODULE.CAPTURE, MODULE.REPORT)
        self.assertEqual(len(frames), 38)
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

    def test_runtime_and_sequence_gate_share_the_capture_envelope(self) -> None:
        runtime = (
            MODULE.REPO / "unity_endfield_graph_shader_lab/Assets"
            / "EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredEndminfM27ExactRuntime.cs"
        ).read_text(encoding="utf-8")
        capture = (
            MODULE.REPO / "unity_endfield_graph_shader_lab/Assets"
            / "EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldEndminfViewerPlayModeCapture.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("public static bool IsCapturedPhase(float seconds)", runtime)
        self.assertIn("if (!IsCapturedPhase(seconds))", runtime)
        self.assertIn("submittedDraws != (uint)expectedPacketDraws", runtime)
        self.assertIn("validatedDrawCount = draws", runtime)
        self.assertIn(
            "EndfieldRecoveredEndminfM27ExactRuntime.IsCapturedPhase(",
            capture,
        )

    def test_runtime_uses_the_normalized_actor_clock_each_frame(self) -> None:
        runtime = (
            MODULE.REPO / "unity_endfield_graph_shader_lab/Assets"
            / "EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredEndminfM27ExactRuntime.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("private const float ViewerLeadSeconds = 2.0f / 60.0f;",
                      runtime)
        self.assertIn("seconds - ViewerLeadSeconds", runtime)
        self.assertNotIn("overviewEpoch", runtime)
        self.assertNotIn("Time.time -", runtime)

    def test_measured_450_viewer_clock_selects_the_15_stone_peak(self) -> None:
        frames, _ = MODULE.collect(MODULE.CAPTURE, MODULE.REPORT)
        # The current focused report measured 4.53425455 s on the actor clip
        # at requested 4.50000048 s. Normalizing the established two-tick
        # viewer lead must retain frame 2978, not advance to the four-stone
        # frame-2987 tail.
        source_seconds = 4.534254550933838 - 2.0 / 60.0
        selected = min(frames, key=lambda row: abs(row["phase"] - source_seconds))
        self.assertEqual(2978, selected["frame"])
        self.assertEqual(1, len(selected["draws"]))
        self.assertEqual(1080, selected["draws"][0]["index_count"])

    def test_exact_runtime_can_bootstrap_from_retained_inactive_binding(self) -> None:
        deferred = (
            MODULE.REPO / "unity_endfield_graph_shader_lab/Assets"
            / "EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredDeferredGBufferFrame.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("TryResolveRetainedEndminfM27Material(", deferred)
        self.assertIn(
            "row.particleRendererPathId == EndminfM27RendererPathId",
            deferred,
        )
        self.assertIn(
            "row.materialPathId != EndminfM27MaterialPathId ||",
            deferred,
        )
        self.assertIn("sourceMaterial = materials[0];", deferred)


if __name__ == "__main__":
    unittest.main()
