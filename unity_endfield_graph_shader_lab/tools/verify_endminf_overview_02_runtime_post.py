#!/usr/bin/env python3
"""Fail-closed contract check for Endminf overview-02 runtime post state."""
from __future__ import annotations

import json
import re
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
AUDIT = REPO / "reports/assets/endminf_overview_02_post_curve_native_audit.json"
CLOCK = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
    / "EndfieldEndminfVisualCompatibilityClock.cs"
)
PIPELINE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
)
SHADER = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Shaders/HGRPCompat"
    / "EndfieldHGRPExposureTonemap.shader"
)

EXPECTED_CLIP_SHA256 = (
    "9814b9de92d5af7902b1967c295f98d29327824bdd7b478984527c5ccccd076c"
)
EXPECTED_KEYS = (
    ((0.0, 0.12700000405311584), (0.1666666716337204, 0.0),
     (4.400000095367432, 0.0), (4.433333396911621, 0.10100000351667404),
     (4.599999904632568, 0.0)),
    ((0.0, 0.15199999511241913), (0.1666666716337204, 0.0),
     (4.400000095367432, 0.0), (4.433333396911621, 0.10899999737739563),
     (4.599999904632568, 0.0)),
    ((0.0, 1.0),),
)


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(f"{label} contract missing tokens: {missing}")


def verify() -> dict[str, object]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit["inputs"]["clipSha256"] != EXPECTED_CLIP_SHA256:
        raise RuntimeError("overview-02 clip hash mismatch")
    if audit["targetPath"] != {"name": "post (1)", "crc32": 669740077}:
        raise RuntimeError("overview-02 animated target path mismatch")
    bindings = audit["bindings"]
    if len(bindings) != 3:
        raise RuntimeError(f"expected three overview-02 scalar curves, got {len(bindings)}")
    for index, (binding, expected) in enumerate(zip(bindings, EXPECTED_KEYS)):
        actual = tuple((row["time"], row["value"]) for row in binding["keys"])
        if actual != expected:
            raise RuntimeError(f"overview-02 curve {index} key mismatch: {actual!r}")

    clock = CLOCK.read_text(encoding="utf-8")
    require_tokens(clock, (
        "ClearOverview02(Transform effectRoot)",
        "overview02Root != null",
        "EvaluateSourceCurve(elapsed, 0.127f, 0.101f)",
        "EvaluateSourceCurve(elapsed, 0.152f, 0.109f)",
        "const float animatedRadialPower = 1.0f",
        "Mathf.Lerp(",
        "1.0f,",
        "Mathf.Clamp01(radial / chromatic)",
        "(chromaticActive && radial > 0.01f ? 6 : 3)",
        "camera.WorldToViewportPoint(",
        "overview02Root.TransformPoint(RecoveredPostCenterLocal)",
        "viewport.x * 2.0f - 1.0f",
        "viewport.y * 2.0f - 1.0f",
        "packed.magnitude > 1.414f",
        "(packed.normalized + Vector2.one) * 0.5f",
        "Mathf.Clamp01(packed.x)",
        "Mathf.Clamp01(packed.y)",
        "time <= 0.16666667f",
        "time < 4.4f",
        "time <= 4.4333334f",
        "time <= 4.6f",
    ), "runtime clock")

    pipeline = PIPELINE.read_text(encoding="utf-8")
    require_tokens(pipeline, (
        "TryEvaluateRecoveredPost(",
        "endminfPost.radialIntensity",
        "endminfPost.chromaticIntensity",
        "endminfPost.mode",
        "endminfPost.effectivePower",
        "endminfPost.centerViewport",
    ), "render-pipeline packing")
    if "EvaluateEndminfVisualCompatibility(" in pipeline:
        raise RuntimeError("retired empirical Effect-02 evaluator is still present")

    spawner = (
        LAB
        / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
        / "EndfieldRecoveredCharEffectSpawner.cs"
    ).read_text(encoding="utf-8")
    require_tokens(spawner, (
        "PlayRecoveredParticleSystems(instance, systems)",
        "EndfieldEndminfVisualCompatibilityClock.ConfiguredPreRollSeconds",
        "const float sourceTickSeconds = 1.0f / 60.0f",
        "system.Simulate(step, false, restart, false)",
        "system.Play(false)",
    ), "overview-02 particle pre-roll")

    shader = SHADER.read_text(encoding="utf-8")
    require_tokens(shader, (
        "float4 SampleEndminfSceneLod0(float2 uv)",
        "float effectivePower)",
        "if (_EndminfVisualCompatibilityParams.z > 3.0)",
        "_EndminfVisualCompatibilityParams.w",
        "float3 bloom = max(tex2D(_BloomTex, presentUv).rgb, 0.0)",
        "source.rgb + bloom * bloomIntensity",
    ), "presentation shader")
    helper = re.search(
        r"float3 SampleEndminfRecoveredRadialChromatic\(.*?\n\s*}\n\n\s*float4 Frag",
        shader,
        re.DOTALL,
    )
    if helper is None:
        raise RuntimeError("could not isolate Effect-02 scene-warp helper")
    if "_BloomTex" in helper.group(0):
        raise RuntimeError("Effect-02 warped taps incorrectly resample bloom")

    return {
        "status": "verified_source_state_and_combination_order_full_uber_unresolved",
        "clipSha256": EXPECTED_CLIP_SHA256,
        "curveCount": len(bindings),
        "runtime": {
            "radialPower": 1.0,
            "combinedPowerBase": 1.0,
            "combinedMode": 6,
            "singleMode": 3,
            "averageSteps": [0, 0],
            "particlePreRollClock": "same nine discrete 60 Hz ticks as post owner",
        },
        "boundary": (
            "The animated values, native center/mode/power packing, source-only "
            "warp, and separate bloom sampling order are verified. The combined "
            "shipped Uber bloom merge and exact D3D12 presentation bindings remain "
            "unresolved."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
