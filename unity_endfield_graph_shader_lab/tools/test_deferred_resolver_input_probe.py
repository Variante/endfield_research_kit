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
        self.assertIn("Texture2D<float4> _62 : register(t23)", shader)
        self.assertIn("Texture2D<float4> _61 : register(t24)", shader)
        self.assertIn("Texture2D<float4> _60 : register(t25)", shader)

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
