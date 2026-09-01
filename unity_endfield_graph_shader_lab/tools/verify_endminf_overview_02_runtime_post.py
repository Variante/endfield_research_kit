#!/usr/bin/env python3
"""Fail-closed contract check for Endminf overview-02 runtime post state."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
AUDIT = REPO / "reports/assets/endminf_overview_02_post_curve_native_audit.json"
UBER_AUDIT = REPO / "reports/assets/endminf_overview_02_uber_post_native_audit.json"
CLOCK = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
    / "EndfieldEndminfVisualCompatibilityClock.cs"
)
SOURCE_CURVES = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Resources/EndfieldEndminfSourcePost"
    / "endminf_overview_02_source_post_curves.json"
)
SOURCE_CURVE_RUNTIME = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
    / "EndfieldRecoveredEndminfSourcePostCurves.cs"
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
CAPTURE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldEndminfViewerPlayModeCapture.cs"
)
OPEN_WRAPPER = LAB / "open_character_recovery_lab.bat"

EXPECTED_CLIP_SHA256 = (
    "9814b9de92d5af7902b1967c295f98d29327824bdd7b478984527c5ccccd076c"
)
EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256 = (
    "0919ae4aab01e7772fb0c3987ad16f2885ad6374ff6c88a4adc065e4ba19353c"
)
EXPECTED_COMBINED_FRAGMENT_DXBC_SHA256 = (
    "3f490e1504c435541769ee03e881583df554e652df155e5b942a3a410d8e086b"
)
EXPECTED_ACTIVE_FRAGMENT_DXBC_SHA256 = (
    "86a732cef7eedb150cbcafb35a994c1e3f7b1ef837dc618131a95e9dfe030c97"
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
    uber_audit = json.loads(UBER_AUDIT.read_text(encoding="utf-8"))
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
    combined_variant = uber_audit["recovered_shader"]["endminf_combined_variant"]
    if combined_variant["keywords"] != [
        "BLOOM",
        "RADIAL_BLUR_CHROMATIC_ABERRATION",
    ]:
        raise RuntimeError("Endminf combined Uber keyword pair mismatch")
    if (
        combined_variant["fragment_dxbc_sha256"]
        != EXPECTED_COMBINED_FRAGMENT_DXBC_SHA256
    ):
        raise RuntimeError("Endminf combined Uber fragment hash mismatch")

    source_curve_text = SOURCE_CURVES.read_text(encoding="utf-8")
    normalized_source_curve_text = source_curve_text.replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    source_curve_payload_hash = hashlib.sha256(
        normalized_source_curve_text.encode("utf-8")
    ).hexdigest()
    if source_curve_payload_hash != EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256:
        raise RuntimeError(
            "generated overview-02 source-curve payload hash mismatch: "
            f"{source_curve_payload_hash}"
        )
    source_curves = json.loads(normalized_source_curve_text)
    if source_curves["schema"] != "endfield.endminf-overview-02-source-post-curves.v1":
        raise RuntimeError("generated overview-02 source-curve schema mismatch")
    if source_curves["sourceClip"]["sha256"] != EXPECTED_CLIP_SHA256:
        raise RuntimeError("generated overview-02 source-curve clip hash mismatch")
    if source_curves["target"] != {"name": "post (1)", "pathCrc32": 669740077}:
        raise RuntimeError("generated overview-02 source-curve target mismatch")
    if [row["role"] for row in source_curves["curves"]] != [
        "chromaticIntensity",
        "radialIntensity",
        "radialPower",
    ]:
        raise RuntimeError("generated overview-02 source-curve role order mismatch")

    source_curve_runtime = SOURCE_CURVE_RUNTIME.read_text(encoding="utf-8")
    require_tokens(source_curve_runtime, (
        'ExpectedSchema =\n            "endfield.endminf-overview-02-source-post-curves.v1"',
        EXPECTED_CLIP_SHA256,
        EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256,
        'Resources.Load<TextAsset>(ResourceName)',
        '.Replace("\\r\\n", "\\n")',
        'sha.ComputeHash(Encoding.UTF8.GetBytes(normalizedPayload))',
        'JsonUtility.FromJson<SourcePostContract>(normalizedPayload)',
        'Mathf.Clamp(',
        'contract.sourceClip.startSeconds',
        'contract.sourceClip.stopSeconds',
        'return ((key.a * delta + key.b) * delta + key.c) * delta + key.d;',
        'curve.keys.Length != keyCount',
        'curve.pathCrc32 != 669740077L',
        'curve.attributeCrc32 != attributeCrc32',
    ), "exact source-curve runtime")

    clock = CLOCK.read_text(encoding="utf-8")
    require_tokens(clock, (
        "ClearOverview02(Transform effectRoot)",
        "overview02Root != null",
        "public static bool SourcePostClockAuthenticated => false;",
        "!TryGetAuthenticatedSourcePostElapsed(out float elapsed)",
        "private static bool TryGetAuthenticatedSourcePostElapsed(",
        "elapsed = 0.0f;\n            return false;",
        "EndfieldRecoveredEndminfSourcePostCurves.TryEvaluate(",
        "out float animatedRadialPower",
        '"Recovered Endminf source post failed closed: "',
        "Mathf.Lerp(",
        "1.0f,",
        "Mathf.Clamp01(radial / chromatic)",
        "(chromaticActive && radial > 0.01f ? 6 : 3)",
        "camera.WorldToViewportPoint(",
        "overview02Root.TransformPoint(RecoveredPostCenterLocal)",
        "Vector2 center = new Vector2(viewport.x, viewport.y)",
        "viewport.x * 2.0f - 1.0f",
        "viewport.y * 2.0f - 1.0f",
        "signedCenter.magnitude > 1.414f",
        "(signedCenter.normalized + Vector2.one) * 0.5f",
        "Mathf.Clamp01(center.x)",
        "Mathf.Clamp01(center.y)",
    ), "runtime clock")
    forbidden_clock_tokens = (
        "EvaluateSourceCurve(",
        "initialPeak * 0.45f",
        "lateStartSeconds = 4.3166667f",
        "latePeakSeconds = 4.35f",
        "lateEndSeconds = 4.5166667f",
    )
    leaked = [token for token in forbidden_clock_tokens if token in clock]
    if leaked:
        raise RuntimeError(f"video-fitted source-curve substitute remains: {leaked}")
    evaluator = clock[
        clock.index("public static bool TryEvaluateRecoveredPost("):
        clock.index("private static bool TryGetAuthenticatedSourcePostElapsed(")
    ]
    if "TryGetElapsed(" in evaluator:
        raise RuntimeError("source post still consumes the unauthenticated compatibility clock")

    pipeline = PIPELINE.read_text(encoding="utf-8")
    require_tokens(pipeline, (
        "TryEvaluateRecoveredPost(",
        "endminfPost.radialIntensity",
        "endminfPost.chromaticIntensity",
        "endminfPost.mode",
        "endminfPost.effectivePower",
        "endminfPost.centerViewport",
        "GraphicsFormat.R16G16B16A16_SFloat",
        "LastRecoveredEndminfPostSourceGraphicsFormat",
        "LastRecoveredEndminfBloomGraphicsFormat",
        "RecoveredEndminfPostSourceId",
        "? new Vector4(\n                        endminfPost.radialIntensity,",
        "endminfPost.chromaticIntensity,",
    ), "render-pipeline packing")
    if "EvaluateEndminfVisualCompatibility(" in pipeline:
        raise RuntimeError("retired empirical Effect-02 evaluator is still present")
    if "EndminfCompatibilityUberIntensityScale" in pipeline:
        raise RuntimeError("video-fitted Endminf Uber intensity scale remains")

    require_tokens(CAPTURE.read_text(encoding="utf-8"), (
        'private const string RecordingVisualPostPreRollSeconds = "0";',
        "IncludeCharInfoBackground = true",
        "IncludeBackgroundPortrait = true",
        "charInfoBackgroundRequested = IncludeCharInfoBackground",
        "backgroundPortraitRequested = IncludeBackgroundPortrait",
        "public Vector2 endminfPostCenterViewport",
        "endminfPostCenterViewport = endminfPostState.centerViewport",
        "public string endminfPostSourceGraphicsFormat",
        "observedEndminfPostSourceRgba16",
        "observedEndminfBloomR11",
        "retail R16G16B16A16_FLOAT Uber source handoff",
        "retail R11G11B10_FLOAT Uber bloom handoff",
        "IsCharInfoBackgroundActive()",
        "IsBackgroundPortraitActive()",
        "if (!requiredCaptureContractReady)",
        "foregroundUiOverlayIncluded = false",
    ), "August 24 capture scope and phase")
    require_tokens(OPEN_WRAPPER.read_text(encoding="utf-8"), (
        'set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY_PREROLL_SECONDS=0"',
        'set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=1"',
    ), "August 24 interactive reproduction profile")

    spawner = (
        LAB
        / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
        / "EndfieldRecoveredCharEffectSpawner.cs"
    ).read_text(encoding="utf-8")
    require_tokens(spawner, (
        "PlayRecoveredParticleSystems(instance, systems)",
        "Keep particle delays on the selection/body timeline",
        "system.Play(true)",
        "private const float EndminfSmoke20PresentationAdvanceSeconds = 2f / 60f;",
        'private const string EndminfSmoke20MaterialName = "M_fx_endminm_gfx_20";',
        "if (IsEndminfSmoke20(instance, system))",
        "EndminfSmoke20PresentationAdvanceSeconds,",
        "system.Play(false);",
        '"P_fxui_endminm003_overview_02"',
        '"smoke (2)"',
    ), "overview-02 split post/particle clocks")
    if spawner.count("system.Simulate(") != 1:
        raise RuntimeError(
            "overview-02 must retain exactly one source-identified smoke correction"
        )
    smoke_gate = re.search(
        r"if \(IsEndminfSmoke20\(instance, system\)\).*?"
        r"system\.Simulate\(.*?EndminfSmoke20PresentationAdvanceSeconds,.*?"
        r"system\.Play\(false\);",
        spawner,
        re.DOTALL,
    )
    if smoke_gate is None:
        raise RuntimeError(
            "M20 smoke correction escaped its source-identified owner gate"
        )

    shader = SHADER.read_text(encoding="utf-8")
    require_tokens(shader, (
        EXPECTED_ACTIVE_FRAGMENT_DXBC_SHA256,
        "float4 SampleEndminfSceneLod0(float2 uv)",
        "float effectivePower)",
        "radialIntensity * 0.5",
        "radialIntensity * 1.5",
        "radialIntensity * 2.0",
        "radialIntensity * 2.5",
        "accumulated * 0.166666672",
        "_EndminfVisualCompatibilityParams.w",
        "float3 bloom = max(tex2D(_BloomTex, presentUv).rgb, 0.0)",
        "source.rgb + bloom * bloomIntensity",
    ), "presentation shader")
    helper = re.search(
        r"float3 SampleEndminfRecoveredRadial\(.*?\n\s*}\n\n\s*float3 DecodeEndminfUberBloomInput",
        shader,
        re.DOTALL,
    )
    if helper is None:
        raise RuntimeError("could not isolate Effect-02 scene-warp helper")
    if "_BloomTex" in helper.group(0):
        raise RuntimeError("Effect-02 warped taps incorrectly resample bloom")
    if "chromaticIntensity" in helper.group(0):
        raise RuntimeError("active radial-only Uber helper still splits RGB taps")

    return {
        "status": (
            "verified_exact_serialized_source_curves_native_apply_center_"
            "and_active_radial_uber_kernel_clock_fail_closed"
        ),
        "clipSha256": EXPECTED_CLIP_SHA256,
        "sourceCurvePayloadSha256": EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256,
        "combinedFragmentDxbcSha256": EXPECTED_COMBINED_FRAGMENT_DXBC_SHA256,
        "activeFragmentDxbcSha256": EXPECTED_ACTIVE_FRAGMENT_DXBC_SHA256,
        "curveCount": len(bindings),
        "runtime": {
            "radialPower": "serialized_constant_curve_1.0",
            "combinedPowerBase": 1.0,
            "combinedMode": 6,
            "singleMode": 3,
            "ordinaryCenterSpace": "viewport_0_to_1",
            "farOffscreenCenterTestSpace": "signed_viewport",
            "postSourceGraphicsFormat": "R16G16B16A16_SFloat",
            "bloomGraphicsFormat": "B10G11R11_UFloatPack32",
            "averageSteps": [0, 0],
            "publicUnityCurveTransport": "unscaled_serialized_values",
            "sourcePostClockAuthenticated": False,
            "presentationAdmitted": False,
            "particleClock": (
                "selection/body timeline; only source-identified M20 smoke is "
                "presentation-advanced by two ticks"
            ),
        },
        "boundary": (
            "The exact serialized cubic scalar curves, constant radial-power "
            "curve, native MonoBehaviour field/apply identities, ordinary/"
            "far-offscreen native center packing, "
            "native mode/power packing, the captured active radial-only Uber "
            "kernel, source-only warp, and separate bloom sampling order are "
            "verified. The older combined radial/chromatic variant remains "
            "asset evidence, not the active peak presentation. The outer "
            "effect-start timestamp, SceneColor chronology, and public-Unity "
            "presentation/binding ABI remain unresolved, so the runtime "
            "publisher is explicitly fail-closed."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
