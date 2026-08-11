#!/usr/bin/env python3
"""Audit the current screen-shadow producer/consumer fail-closed boundary.

This intentionally does not use the older capture contract: that contract pins
an earlier export and is not a valid freshness check after an installed-data
refresh.  The audit reports what the current lab wires today and refuses to
claim retail parity while Skin is still on the diagnostic consumer branch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
LAB_ROOT = REPO_ROOT / "unity_endfield_graph_shader_lab"
PRODUCER = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    / "EndfieldRecoveredScreenShadowMaskProducer.cs"
)
LIGHTING_INCLUDE = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Shaders/HGRPCompat/"
    / "EndfieldHGRPCharacterLighting.cginc"
)
SKIN_SHADER = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/"
    / "EndfieldCharacterSkinRecovered.shader"
)


def read_source(path: Path, label: str) -> str:
    if not path.is_file():
        raise AssertionError(f"{label} source is missing: {path}")
    return path.read_text(encoding="utf-8")


def require(source: str, needle: str, label: str) -> None:
    if needle not in source:
        raise AssertionError(
            f"{label} is missing required source anchor {needle!r}"
        )


def verify_current_boundary() -> dict[str, Any]:
    producer = read_source(PRODUCER, "screen-shadow producer")
    include = read_source(LIGHTING_INCLUDE, "HGRP lighting include")
    skin = read_source(SKIN_SHADER, "recovered Skin shader")

    for needle in (
        'Shader.PropertyToID("_ScreenSpaceShadowMask")',
        "GraphicsFormat.R8G8_UNorm",
        "commandBuffer.SetRenderTarget(resources.mask, sceneDepth);",
        "bool contentValid = false;",
        "if (contentValid)",
        "commandBuffer.EnableShaderKeyword(EyeConsumerKeyword);",
    ):
        require(producer, needle, "current screen-shadow producer")
    if "SkinConsumerKeyword" in producer:
        raise AssertionError(
            "current producer unexpectedly publishes a Skin consumer keyword "
            "without a refreshed source contract"
        )

    for needle in (
        "Texture2D<float2> _ScreenSpaceShadowMask;",
        "_ScreenSpaceShadowMask.Load(",
        "defined(ENDFIELD_RECOVERED_EYE_SCREEN_SHADOW_MASK_R)",
        "_EndfieldRecoveredScreenSpaceShadowMaskReady",
        "Texture2D<float2> _EndfieldRecoveredScreenShadowMaskDiagnostic;",
    ):
        require(include, needle, "current HGRP screen-shadow include")

    for needle in (
        "#if defined(ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER)",
        "EndfieldHGRPLoadRecoveredScreenShadowMask(i.pos.xy);",
        "#pragma multi_compile __ ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER",
    ):
        require( skin, needle, "current Skin diagnostic consumer")

    retail_skin_keyword = "ENDFIELD_RECOVERED_RETAIL_SCREEN_SHADOW_MASK" in skin
    direct_skin_global_load = "EndfieldHGRPLoadScreenSpaceShadowMaskRG" in skin
    content_valid = "bool contentValid = true;" in producer
    producer_skin_gate = "SkinConsumerKeyword" in producer
    if retail_skin_keyword != direct_skin_global_load:
        raise AssertionError(
            "Skin retail screen-shadow keyword and direct global load disagree"
        )
    if retail_skin_keyword and not producer_skin_gate:
        raise AssertionError(
            "Skin retail consumer exists without a producer keyword gate"
        )
    if content_valid:
        raise AssertionError(
            "screen-shadow producer was promoted to content-valid without a "
            "new retail publication contract"
        )

    return {
        "ok": True,
        "producer": {
            "resource": "_ScreenSpaceShadowMask",
            "format": "R8G8_UNorm",
            "content_valid": content_valid,
            "eye_keyword_gate": "EyeConsumerKeyword" in producer,
            "skin_keyword_gate": producer_skin_gate,
        },
        "skin_consumer": {
            "diagnostic_branch": True,
            "retail_global_keyword": retail_skin_keyword,
            "direct_global_load": direct_skin_global_load,
        },
        "binary_evidence": {
            "retail_skin_load": True,
            "channels": {"r": "directional scene shadow", "g": "character shadow"},
        },
        "interpretation": {
            "current_boundary": (
                "producer binds the retail-named resource but content is invalid; "
                "Skin remains on the diagnostic texture branch"
            ),
            "retail_frame_parity": "not asserted",
        },
    }


def main() -> int:
    try:
        result = verify_current_boundary()
    except (AssertionError, OSError) as exc:
        print(
            json.dumps(
                {"ok": False, "diagnostic": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
