#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import build_endminf_m20_peak_exact_capture_data as subject


class M20PeakCaptureDataTests(unittest.TestCase):
    def test_exact_live_packet_is_source_closed(self) -> None:
        packet = subject.collect(subject.CAPTURE)
        self.assertEqual(subject.VS_SHA256, subject.m21.sha256(packet["vs"]))
        self.assertEqual(subject.PS_SHA256, subject.m21.sha256(packet["ps"]))
        self.assertEqual(subject.VERTEX_SHA256,
                         subject.m21.sha256(packet["vertices"]))
        self.assertEqual(subject.INDEX_SHA256,
                         subject.m21.sha256(packet["indices"]))
        self.assertEqual(subject.ATLAS_SHA256,
                         subject.m21.sha256(packet["atlas"]))
        self.assertEqual(subject.VERTEX_RESOURCE_SHA256,
                         subject.m21.sha256(packet["vertex_resource"]))

    def test_generated_contract_retains_retail_atlas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cs = root / "payload.cs"
            cpp = root / "payload.h"
            subject.build(subject.CAPTURE, cs, cpp)
            self.assertIn("20260828T224210Z", cs.read_text(encoding="utf-8"))
            generated = cpp.read_text(encoding="utf-8")
            self.assertIn("g_EndfieldM20PeakAtlasBc7", generated)
            self.assertIn("g_EndfieldM20PeakPixelDxbc", generated)
            self.assertIn("g_EndfieldM20PeakVertexResource", generated)
            self.assertIn("g_EndfieldM20PeakIndexCount = 36u", generated)

    def test_native_and_pipeline_transport_is_wired(self) -> None:
        project = subject.REPO / "unity_endfield_graph_shader_lab"
        plugin = (project / "tools/original_dxbc_exact/OriginalDxbcSwapPlugin.cpp").read_text(
            encoding="utf-8")
        runtime = (project / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
                   / "EndfieldRecoveredEndminfM20PeakExactRuntime.cs").read_text(
                       encoding="utf-8")
        pipeline = (project / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
                    / "HGCompatRenderPipeline.cs").read_text(encoding="utf-8")
        validator = (project / "tools/original_dxbc_exact/ValidateEmbeddedDxbc.cpp").read_text(
            encoding="utf-8")
        self.assertIn("g_m20PeakVertexView", plugin)
        self.assertIn("g_m20PeakAtlasView", plugin)
        self.assertIn("DrawIndexedInstanced(g_EndfieldM20PeakIndexCount", plugin)
        self.assertIn("EndfieldOriginalDxbcSetM20PeakDepthResource", plugin)
        self.assertIn("EndfieldOriginalDxbcGetM20PeakRenderEventFunc", runtime)
        self.assertIn("new RenderTargetIdentifier(sceneDepth)", runtime)
        self.assertIn("EndfieldRecoveredEndminfM20PeakExactRuntime.Render", pipeline)
        self.assertIn("m20InputLayoutResult", validator)


if __name__ == "__main__":
    unittest.main()
