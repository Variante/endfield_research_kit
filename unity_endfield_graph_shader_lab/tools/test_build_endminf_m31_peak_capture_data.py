from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNTIME = (HERE.parent / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
           / "EndfieldRecoveredEndminfM31PeakExactRuntime.cs")
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_m31_peak_capture_data",
    HERE / "build_endminf_m31_peak_capture_data.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BuildEndminfM31PeakCaptureDataTests(unittest.TestCase):
    def test_builds_qpc_anchored_temporal_manifest_and_exact_payload(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cs_path = Path(folder) / "payload.cs"
            cpp_path = Path(folder) / "payload.h"
            MODULE.build(MODULE.TEMPORAL_CAPTURE, MODULE.PAYLOAD_CAPTURE,
                         cs_path, cpp_path)
            cs = cs_path.read_text(encoding="utf-8")
            cpp = cpp_path.read_text(encoding="utf-8")
            self.assertEqual(cs, MODULE.CS_OUTPUT.read_text(encoding="utf-8"))
            self.assertEqual(cpp, MODULE.CPP_OUTPUT.read_text(encoding="utf-8"))
            self.assertIn('TemporalSourceSession = "20260828T121603Z"', cs)
            self.assertIn("PayloadSourceFrame = 1818", cs)
            self.assertIn("AnchorFrame = 1977", cs)
            self.assertIn("AnchorPhaseSeconds = 4.350000f", cs)
            self.assertIn("PacketCount = 9", cs)
            self.assertIn("NativePayloadDrawCount = 2", cs)
            self.assertIn(
                "DrawCounts = { 2, 2, 2, 2, 2, 2, 2, 3, 1 }", cs)
            self.assertIn(
                "FirstDrawOrdinals = { 68, 68, 68, 77, 77, 68, 77, 66, 67 }",
                cs)
            self.assertIn(
                "LastDrawOrdinals = { 77, 79, 79, 89, 89, 80, 89, 89, 67 }",
                cs)
            self.assertIn(
                "NativeOrderCompatible = { false, false, false, false, false, false, false, false, true }",
                cs)
            self.assertIn(
                "SplitOrderCompatible = { true, true, true, true, true, true, true, false, false }",
                cs)
            self.assertIn(
                "InterleavedM29M30Counts = { 2, 2, 2, 2, 2, 2, 2, 0, 0 }",
                cs)
            self.assertIn("2.863329f", cs)
            self.assertIn("4.564017f", cs)
            self.assertIn("DepthContractReady = true", cs)
            self.assertIn("g_EndfieldM31PeakPacketCount", cpp)
            self.assertIn("g_EndfieldM31PeakSplitEventCount = 2u", cpp)
            self.assertIn("g_EndfieldM31PeakTextureT1", cpp)

    def test_temporal_capture_has_exact_owner_resource_closure(self) -> None:
        packets = MODULE.collect_temporal(MODULE.TEMPORAL_CAPTURE)
        self.assertEqual(list(MODULE.TEMPORAL_FRAMES),
                         [row["frame"] for row in packets])
        self.assertEqual([2, 2, 2, 2, 2, 2, 2, 3, 1],
                         [row["draw_count"] for row in packets])
        anchor = packets[list(MODULE.TEMPORAL_FRAMES).index(
            MODULE.ANCHOR_FRAME)]
        self.assertAlmostEqual(4.35, anchor["phase"], places=9)
        self.assertTrue(all(
            row["phase"] < packets[index + 1]["phase"]
            for index, row in enumerate(packets[:-1])))
        self.assertEqual([False] * 8 + [True],
                         [row["native_order_compatible"] for row in packets])
        self.assertEqual([True] * 7 + [False, False],
                         [row["split_order_compatible"] for row in packets])
        self.assertEqual([2, 2, 2, 2, 2, 2, 2, 0, 0],
                         [len(row["interleaved_m29_m30"])
                          for row in packets])

    def test_owner_constant_drift_is_rejected(self) -> None:
        metadata_path = (MODULE.PAYLOAD_CAPTURE /
                         "graphics/frames/1818/metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        draw = next(row for row in metadata["drawRecords"]
                    if MODULE.is_m31(row))
        changed = copy.deepcopy(draw)
        b3 = next(row for row in changed["constantBuffers"]
                  if row["stage"] == 4 and row["slot"] == 3)
        payload = bytearray.fromhex(b3["dataHex"])
        payload[16:20] = b"\x00\x00\x00\x00"
        b3["dataHex"] = payload.hex()
        self.assertFalse(MODULE.is_m31(changed))

    def test_capture_session_is_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            wrong = Path(folder) / "wrong-session"
            with self.assertRaisesRegex(ValueError,
                                        "temporal source session drifted"):
                MODULE.collect_temporal(wrong)

    def test_temporal_draw_args_are_pinned(self) -> None:
        metadata_path = (MODULE.TEMPORAL_CAPTURE /
                         "graphics/frames/1977/metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        draw = copy.deepcopy(metadata["drawRecords"][66])
        draw["baseVertex"] += 1
        draw_index, start, base_vertex = MODULE.EXPECTED_TEMPORAL_DRAWS[1977][0]
        with self.assertRaisesRegex(ValueError, "draw 66 args drifted"):
            MODULE.validate_temporal_draw(
                draw, 1977, draw_index, start, base_vertex)

    def test_runtime_admits_only_split_compatible_temporal_packets(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("ResolveNearestPacket", runtime)
        self.assertIn(
            "EndfieldRecoveredM31PeakCaptureData.DrawCounts[selectedPacket] ==",
            runtime)
        self.assertIn(
            "EndfieldRecoveredM31PeakCaptureData.NativePayloadDrawCount",
            runtime)
        self.assertIn(".SplitOrderCompatible[selectedPacket]", runtime)
        self.assertIn("transport-order gate drifted", runtime)
        self.assertIn("M31/M29/M30 owner order drifted", runtime)
        self.assertIn("SetRendererSuppression(active)", runtime)
        self.assertIn("submittedDraws !=", runtime)

    def test_pipeline_preserves_retail_split_owner_order(self) -> None:
        pipeline = (HERE.parent / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
                    / "HGCompatRenderPipeline.cs").read_text(encoding="utf-8")
        first = pipeline.index(
            "EndfieldRecoveredEndminfM31PeakExactRuntime.RenderFirst(")
        pre_m29 = pipeline.index(
            "EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime\n"
            "                        .RenderPreM29(")
        m30 = pipeline.index("EndfieldRecoveredEndminfM30ExactRuntime.Render(")
        queue3000 = pipeline.index(".CompositeMainTransparentQueue3000(")
        m29 = pipeline.index("EndfieldRecoveredEndminfM29ExactRuntime.Render(")
        second = pipeline.index(
            "EndfieldRecoveredEndminfM31PeakExactRuntime.RenderSecond(")
        post_m29 = pipeline.index(
            "EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime\n"
            "                        .RenderPostM29(")
        self.assertLess(first, pre_m29)
        self.assertLess(pre_m29, m30)
        self.assertLess(m30, queue3000)
        self.assertLess(queue3000, m29)
        self.assertLess(m29, second)
        self.assertLess(second, post_m29)

    def test_native_callback_submits_one_payload_per_split_event(self) -> None:
        plugin = (HERE / "original_dxbc_exact"
                  / "OriginalDxbcSwapPlugin.cpp").read_text(encoding="utf-8")
        self.assertIn(
            "g_EndfieldM31PeakSplitEventCount ==\n"
            "    g_EndfieldM31PeakPacketCount",
            plugin)
        callback_start = plugin.index(
            "void UNITY_INTERFACE_API DrawM31PeakExactRuntime(int eventId)")
        callback_end = plugin.index(
            "void UNITY_INTERFACE_API DrawVFXBaseV2PeakCohortRuntime",
            callback_start)
        callback = plugin[callback_start:callback_end]
        self.assertIn(
            "const std::uint32_t packetIndex = static_cast<std::uint32_t>(eventId);",
            callback)
        self.assertIn("g_EndfieldM31PeakPackets[packetIndex]", callback)
        self.assertIn("g_m31PeakDrawCount.fetch_add(1u", callback)
        self.assertNotIn(
            "packetIndex < g_EndfieldM31PeakPacketCount", callback)

    def test_runtime_submits_both_split_event_ids(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        first = runtime.index("internal static bool RenderFirst(")
        second = runtime.index("internal static bool RenderSecond(")
        split = runtime.index("private static bool RenderSplitEvent(")
        self.assertLess(first, second)
        self.assertLess(second, split)
        self.assertIn(
            "context, camera, sceneColor, sceneMV, sceneDepth, 0)",
            runtime[first:second])
        self.assertIn(
            "context, camera, sceneColor, sceneMV, sceneDepth, 1)",
            runtime[second:split])
        self.assertIn("command.IssuePluginEvent(renderEvent, eventId)", runtime)

    def test_runtime_publishes_frame_local_submission_evidence(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        prepare = runtime.index("PrepareBeforeCulling")
        first = runtime.index("internal static bool RenderFirst(", prepare)
        second = runtime.index("internal static bool RenderSecond(", first)
        validation = runtime.index(
            "ValidatePendingAfterSynchronizedRender", second)
        self.assertIn("submittedThisFrame = false", runtime[prepare:first])
        self.assertIn("validatedThisFrame = false", runtime[prepare:first])
        self.assertIn("selectedPacketThisFrame = selectedPacket", runtime[prepare:first])
        self.assertIn("submittedThisFrame = true", runtime[second:validation])
        self.assertIn("validatedThisFrame = true", runtime[validation:])
        for member in (
            "ActiveThisFrame",
            "SubmittedThisFrame",
            "ValidatedThisFrame",
            "SelectedPacketThisFrame",
            "SourceFrameThisFrame",
        ):
            self.assertIn(member, runtime)


if __name__ == "__main__":
    unittest.main()
