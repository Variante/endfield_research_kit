#!/usr/bin/env python3
"""Static source gates for the default-off deferred resolver input probe."""

from __future__ import annotations

import unittest
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
SHADER = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldDeferredResolverInputProbe.shader"


class DeferredResolverInputProbeTests(unittest.TestCase):
    def test_probe_is_explicit_and_non_presented(self) -> None:
        policy = (RUNTIME / "EndfieldRecoveredDeferredResolverBindingPolicy.cs").read_text(
            encoding="utf-8"
        )
        probe = (RUNTIME / "EndfieldRecoveredDeferredResolverInputProbe.cs").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"ENDFIELD_RECOVERED_DEFERRED_RESOLVER_INPUT_PROBE"', policy
        )
        self.assertIn("presented=false, retailPass0=false.", probe)
        self.assertIn("Shader.SetGlobalFloat(ReadyId, 0.0f)", probe)
        self.assertIn("FailClosed(context, failure)", probe)
        self.assertIn("SetRenderTarget(canonicalColorTarget, canonicalDepthTarget)", probe)

    def test_m27_presentation_transitively_requests_exact_consumer(self) -> None:
        policy = (RUNTIME / "EndfieldRecoveredDeferredResolverBindingPolicy.cs").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "EndfieldRecoveredEndminfM27DeferredPresentation\n"
            "                        .EnvironmentVariable",
            policy,
        )
        self.assertGreaterEqual(
            policy.count("EndfieldRecoveredEndminfM27DeferredPresentation"),
            2,
        )

    def test_probe_consumes_source_gbuffer_order_and_all_bridge_slots(self) -> None:
        probe = (RUNTIME / "EndfieldRecoveredDeferredResolverInputProbe.cs").read_text(
            encoding="utf-8"
        )
        shader = SHADER.read_text(encoding="utf-8")
        for token in (
            "ResolverSourceTextureT23Id",
            "ResolverSourceTextureT24Id",
            "ResolverSourceTextureT25Id",
            'Shader.PropertyToID("EndfieldCB6")',
        ):
            self.assertIn(token, probe)
        self.assertIn("_62.Load", shader)
        self.assertIn("_61.Load", shader)
        self.assertIn("_60.Load", shader)
        for slot in range(9):
            self.assertIn(f"cbuffer EndfieldCB{slot} : register(b{slot})", shader)
        for slot in (0, 1, 5, 6, 7, 11):
            self.assertIn(f": register(t{slot})", shader)
        self.assertIn("Texture2D<float4> _60 : register(t23)", shader)
        self.assertIn("Texture2D<float4> _61 : register(t24)", shader)
        self.assertIn("Texture2D<float4> _62 : register(t25)", shader)

    def test_probe_requires_current_camera_frame_publication(self) -> None:
        producer = (
            RUNTIME / "EndfieldRecoveredDeferredGBufferFrame.cs"
        ).read_text(encoding="utf-8")
        probe = (
            RUNTIME / "EndfieldRecoveredDeferredResolverInputProbe.cs"
        ).read_text(encoding="utf-8")
        for token in (
            "publicationValid",
            "publishedFrame",
            "publishedCameraInstanceId",
            "publishedWidth",
            "publishedHeight",
            "PublishFrame(camera, width, height)",
            "InvalidatePublication();",
            "publication stamp mismatch",
            "camera,\n            int width,\n            int height",
        ):
            self.assertIn(token, producer, token)
        self.assertIn(
            "out resolverPublicationSerial",
            probe,
        )
        self.assertIn("publicationSerial=", probe)

    def test_probe_captures_target_resource_ownership(self) -> None:
        policy = (
            RUNTIME / "EndfieldRecoveredDeferredResolverBindingPolicy.cs"
        ).read_text(encoding="utf-8")
        probe = (
            RUNTIME / "EndfieldRecoveredDeferredResolverInputProbe.cs"
        ).read_text(encoding="utf-8")
        pipeline = (RUNTIME / "HGCompatRenderPipeline.cs").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"ENDFIELD_RECOVERED_DEFERRED_RESOLVER_RESOURCE_PROBE"',
            policy,
        )
        for token in (
            "ResourceFrame",
            "CaptureResources",
            "TryGetCurrentCanonicalPublication",
            "TryGetCurrentPublication",
            "resolver target-resource snapshot",
            "allPhysical=",
        ):
            self.assertIn(token, probe, token)
        self.assertIn("CaptureResources(", pipeline)
        self.assertIn("recoveredDeferredResolverResources", pipeline)

    def test_pregbuffer_preserves_srgb_material_lane(self) -> None:
        preg = (RUNTIME / "EndfieldRecoveredPreGBufferDiagnostic.cs").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "sRGB = GraphicsFormatUtility.IsSRGBFormat(format)",
            preg,
        )
        self.assertIn(
            "gBufferC={resources.gBufferC.graphicsFormat}",
            preg,
        )

    def test_existing_publishers_opt_into_probe_policy(self) -> None:
        paths = (
            "EndfieldRecoveredLightBinning.cs",
            "EndfieldRecoveredDeferredTransformVariables.cs",
            "EndfieldRecoveredShaderVariablesGlobal.cs",
            "EndfieldRecoveredDeferredLightData.cs",
            "EndfieldRecoveredDeferredShadowData.cs",
            "EndfieldRecoveredDeferredGBufferFrame.cs",
        )
        for name in paths:
            source = (RUNTIME / name).read_text(encoding="utf-8")
            self.assertIn(
                "EndfieldRecoveredDeferredResolverBindingPolicy.IsRequested",
                source,
                name,
            )

    def test_punctual_shadow_admits_recovered_desktop_proxy_material(self) -> None:
        producer = (
            RUNTIME / "EndfieldRecoveredPunctualShadowProducer.cs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'CharacterShadowProxyShaderName =',
            producer,
        )
        self.assertIn(
            '"Hidden/Endfield/Recovered/CharacterShadowProxy"',
            producer,
        )
        self.assertIn(
            "CharacterShadowProxyShaderName\n            }",
            producer,
        )

    def test_exact_constant_aliases_are_published(self) -> None:
        binning = (RUNTIME / "EndfieldRecoveredLightBinning.cs").read_text(
            encoding="utf-8"
        )
        visibility = (
            RUNTIME / "EndfieldRecoveredVisibilitySHConstants.cs"
        ).read_text(encoding="utf-8")
        for token in (
            'Shader.PropertyToID("EndfieldCB3")',
            'Shader.PropertyToID("EndfieldCB7")',
            "ExactDxbcBridgeConstantsId",
            "ExactDxbcBridgeLightCookieDataId",
        ):
            self.assertIn(token, binning)
        self.assertIn('Shader.PropertyToID("EndfieldCB8")', visibility)
        self.assertIn("ExactDxbcBridgeConstantsId", visibility)


if __name__ == "__main__":
    unittest.main()
