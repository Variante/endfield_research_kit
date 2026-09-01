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
TEMPORAL_SHADER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Shaders/Recovered/"
    "EndfieldRecoveredTemporalResolve.shader"
)


class EndminfTemporalPostSourceContractTests(unittest.TestCase):
    def test_ordinary_history_bound_uses_direct_reprojected_history(self) -> None:
        source = TEMPORAL_SHADER.read_text(encoding="utf-8")
        start = source.index("float3 history = SampleRetailHistory(previousUv, texel);")
        end = source.index("float3 neighborhoodMean", start)
        ordinary = source[start:end]
        self.assertIn(
            "float3 ordinaryDirectHistory = tex2Dlod(\n"
            "                    _RecoveredTemporalHistory,\n"
            "                    float4(previousUv, 0.0, 0.0)).rgb;",
            ordinary,
        )
        self.assertIn("ordinaryDirectHistory * 0.2", ordinary)
        self.assertIn("ordinaryDirectHistory * 1.8", ordinary)
        self.assertNotIn("current * 0.2", ordinary)
        self.assertNotIn("current * 1.8", ordinary)

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

    def test_opening_strip_compatibility_precedes_temporal_resolve(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        render_start = source.index("private void RenderPreparedCamera")
        render_end = source.index("private void ApplyCharacterPostProcess", render_start)
        render = source[render_start:render_end]
        self.assertLess(
            render.index(
                "ApplyRecoveredEndminfOpeningStripCompatibilityBeforeTemporal("
            ),
            render.index("CaptureBeforeTemporalIfArmed"),
        )
        post_start = source.index("private void ApplyCharacterPostProcess")
        post_end = source.index(
            "private bool ApplyRecoveredEndminfOpeningStripCompatibilityBeforeTemporal",
            post_start,
        )
        post = source[post_start:post_end]
        self.assertNotIn("TryEvaluateOpeningStrip", post)
        self.assertLess(
            post.index("EnqueueRecoveredEndminfTemporalResolve("),
            post.index("EndfieldRecoveredPostStageDiagnostic.AfterTemporal"),
        )

    def test_public_ngx_proxy_preserves_the_observed_format_handoff(self) -> None:
        source = NGX_PROXY.read_text(encoding="utf-8")
        self.assertIn("GraphicsFormat.B10G11R11_UFloatPack32", source)
        self.assertIn("GraphicsFormat.R16G16B16A16_SFloat", source)
        self.assertIn("SetGlobalTexture(OutputTextureId, outputColor)", source)
        self.assertNotIn("commandBuffer.Blit(outputColor, sourceColor)", source)

    def test_public_ngx_proxy_uses_the_captured_pixel_jitter_and_axis_contract(
        self,
    ) -> None:
        source = NGX_PROXY.read_text(encoding="utf-8")
        expected_samples = (
            "new Vector2(-0.25f, 0.388888896f)",
            "new Vector2(0.375f, 0.0555555522f)",
            "new Vector2(-0.125f, -0.277777791f)",
            "new Vector2(0.125f, 0.277777791f)",
            "new Vector2(-0.375f, -0.055555582f)",
            "new Vector2(0.4375f, -0.388888896f)",
            "new Vector2(0.0f, 0.166666657f)",
            "new Vector2(0.25f, -0.166666687f)",
        )
        positions = [source.index(sample) for sample in expected_samples]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("CapturedPixelJitterSampleCount = 8", source)
        self.assertIn("CapturedIndicatorInvertAxisX = 0", source)
        self.assertIn("CapturedIndicatorInvertAxisY = 1", source)
        self.assertIn("executeData.jitterOffsetX = jitterOffset.x", source)
        self.assertIn("executeData.jitterOffsetY = jitterOffset.y", source)
        self.assertIn(
            "executeData.invertXAxis = CapturedIndicatorInvertAxisX",
            source,
        )
        self.assertIn(
            "executeData.invertYAxis = CapturedIndicatorInvertAxisY",
            source,
        )
        self.assertIn("jitterSampleIndex = 0", source)

    def test_public_ngx_proxy_reports_the_applied_temporal_constants(self) -> None:
        pipeline = PIPELINE.read_text(encoding="utf-8")
        capture = (
            ROOT
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
            "EndfieldEndminfViewerPlayModeCapture.cs"
        ).read_text(encoding="utf-8")
        for field in (
            "LastRecoveredUnityPublicNgxProxyJitterOffset",
            "LastRecoveredUnityPublicNgxProxyJitterPhase",
            "LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisX",
            "LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisY",
        ):
            self.assertGreaterEqual(pipeline.count(field), 2, field)
        for field in (
            "unityPublicNgxProxyJitterOffset",
            "unityPublicNgxProxyJitterPhase",
            "unityPublicNgxProxyIndicatorInvertAxisX",
            "unityPublicNgxProxyIndicatorInvertAxisY",
        ):
            self.assertGreaterEqual(capture.count(field), 2, field)

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
