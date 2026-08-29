import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "HGCompatRenderPipeline.cs"
)
NGX_PROXY = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredUnityPublicNgxProxy.cs"
)


class EndminfTemporalPostSourceContractTests(unittest.TestCase):
    def test_resolve_and_history_keep_the_source_r16g16b16a16_format(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        method = source[source.index("EnqueueRecoveredEndminfTemporalResolve(") :]
        method = method[: method.index("ReleaseRecoveredTemporalHistory(")]
        self.assertGreaterEqual(
            method.count("GraphicsFormat.R16G16B16A16_SFloat"),
            3,
        )
        self.assertIn("state.history.graphicsFormat", method)

    def test_resolve_is_returned_directly_as_the_bloom_and_uber_source(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        self.assertIn("hasRecoveredTemporalPostSource", source)
        self.assertIn("recoveredTemporalPostSourceId", source)
        self.assertIn(
            "temporalPostSourceId = RecoveredTemporalResolveId",
            source,
        )
        self.assertIn(
            "releaseRecoveredTemporalPostSource",
            source,
        )
        self.assertIn(
            "commandBuffer.ReleaseTemporaryRT(\n"
            "                    recoveredTemporalPostSourceId)",
            source,
        )

    def test_resolve_does_not_round_trip_through_packed_camera_color(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        start = source.index("private bool EnqueueRecoveredEndminfTemporalResolve")
        end = source.index("private static void ReleaseRecoveredTemporalHistory", start)
        method = source[start:end]
        self.assertNotIn(
            "new RenderTargetIdentifier(RecoveredTemporalResolveId),\n"
            "                        new RenderTargetIdentifier(CameraColorId)",
            method,
        )

    def test_after_temporal_diagnostic_precedes_opening_strip(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        start = source.index("bool hasRecoveredTemporalPostSource")
        end = source.index("if (!useRecoveredPostSemantics)", start)
        post = source[start:end]
        self.assertLess(
            post.index("EndfieldRecoveredPostStageDiagnostic.AfterTemporal"),
            post.index("TryEvaluateOpeningStrip"),
        )

    def test_public_ngx_proxy_preserves_the_observed_format_handoff(self) -> None:
        source = NGX_PROXY.read_text(encoding="utf-8")
        self.assertIn("GraphicsFormat.B10G11R11_UFloatPack32", source)
        self.assertIn("GraphicsFormat.R16G16B16A16_SFloat", source)
        self.assertIn("SetGlobalTexture(OutputTextureId, outputColor)", source)
        self.assertNotIn("commandBuffer.Blit(outputColor, sourceColor)", source)

    def test_public_ngx_proxy_validates_each_synchronized_output(self) -> None:
        proxy = NGX_PROXY.read_text(encoding="utf-8")
        pipeline = PIPELINE.read_text(encoding="utf-8")
        capture = (
            ROOT
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
            "EndfieldEndminfViewerPlayModeCapture.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("pendingExecutionValidation = true", proxy)
        self.assertIn("ValidatePendingAfterSynchronizedRender", proxy)
        self.assertIn(
            "ValidateRecoveredUnityPublicNgxProxyAfterSynchronizedRender",
            pipeline,
        )
        validation = capture.index(
            "ValidateRecoveredUnityPublicNgxProxyAfterSynchronizedRender"
        )
        frame_row = capture.index("Frames.Add(new FrameRow", validation)
        self.assertLess(validation, frame_row)
        self.assertIn(".All(value => value.unityPublicNgxProxyValidated)", capture)

    def test_public_ngx_proxy_fail_closes_actual_resource_descriptors(self) -> None:
        source = NGX_PROXY.read_text(encoding="utf-8")
        self.assertIn("sceneDepth.depthStencilFormat", source)
        self.assertIn("GraphicsFormat.D32_SFloat_S8_UInt", source)
        self.assertIn("texture.graphicsFormat != expectedFormat", source)
        self.assertIn("texture.enableRandomWrite != expectedRandomWrite", source)
        pipeline = PIPELINE.read_text(encoding="utf-8")
        self.assertIn("TryGetOutputDescriptor", pipeline)

    def test_public_ngx_proxy_telemetry_resets_before_early_exit_gates(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        start = source.index("private bool EnqueueRecoveredEndminfTemporalResolve")
        method = source[start : source.index(
            "private static void ReleaseRecoveredTemporalHistory", start
        )]
        reset = method.index("LastRecoveredUnityPublicNgxProxySubmitted = false")
        early_gate = method.index("if (recoveredTemporalMaterial == null")
        self.assertLess(reset, early_gate)

    def test_public_ngx_proxy_declares_the_builtin_nvidia_module(self) -> None:
        manifest = json.loads((ROOT / "Packages/manifest.json").read_text())
        lock = json.loads((ROOT / "Packages/packages-lock.json").read_text())
        self.assertEqual(
            manifest["dependencies"].get("com.unity.modules.nvidia"),
            "1.0.0",
        )
        self.assertEqual(
            lock["dependencies"]["com.unity.modules.nvidia"]["source"],
            "builtin",
        )


if __name__ == "__main__":
    unittest.main()
