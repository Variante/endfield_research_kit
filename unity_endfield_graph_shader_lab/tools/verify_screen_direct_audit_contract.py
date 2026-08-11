#!/usr/bin/env python3
"""Static fail-closed audit of screen/direct and recovered tangent contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "Assets/EndfieldGraphShaderLab"
LIGHTING = ROOT / "Shaders/HGRPCompat/EndfieldHGRPCharacterLighting.cginc"
PIPELINE = ROOT / "Runtime/Rendering/HGCompatRenderPipeline.cs"
RUNTIME = ROOT / "Runtime/Rendering/EndfieldRecoveredScreenDirectAudit.cs"
PRE_G = ROOT / "Runtime/Rendering/EndfieldRecoveredPreGBufferDiagnostic.cs"
SCREEN = ROOT / "Runtime/Rendering/EndfieldRecoveredScreenShadowMaskDiagnostic.cs"
COMMON = ROOT / "Shaders/Recovered/EndfieldCharacterRecoveredCommon.cginc"
BATCH = (
    ROOT
    / "Editor/CharacterRecovery/EndfieldRecoveredScreenDirectAuditBatchVerifier.cs"
)
WRAPPER = PROJECT / "verify_recovered_screen_direct_audit.bat"
SAME_OWNER_WRAPPER = (
    PROJECT / "verify_recovered_screen_direct_same_owner_audit.bat"
)
SHADERS = {
    "Skin": ROOT / "Shaders/Recovered/EndfieldCharacterSkinRecovered.shader",
    "Cloth": ROOT / "Shaders/Recovered/EndfieldCharacterClothRecovered.shader",
    "Hair": ROOT / "Shaders/Recovered/EndfieldCharacterHairRecovered.shader",
}
EYE = ROOT / "Shaders/Recovered/EndfieldCharacterEyeRecovered.shader"
TANGENT_SHADERS = {**SHADERS, "Eye": EYE}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_tokens(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        require(token in text, f"{path.name}: missing token {token!r}")


def require_in_order(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    offset = 0
    for token in tokens:
        index = text.find(token, offset)
        require(index >= 0, f"{path.name}: missing/out-of-order {token!r}")
        offset = index + len(token)


def main() -> int:
    for path in (
        LIGHTING,
        PIPELINE,
        RUNTIME,
        PRE_G,
        SCREEN,
        COMMON,
        BATCH,
        WRAPPER,
        SAME_OWNER_WRAPPER,
        EYE,
        *SHADERS.values(),
    ):
        require(path.is_file(), f"missing {path}")

    require_tokens(
        LIGHTING,
        [
            "defined(ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT)",
            "EndfieldHGRPSampleCharacterShadowWithStrength(",
            "saturate(receiverStrength) * enabled",
            "uint2 pixel = uint2(screenPosition);",
            "_EndfieldRecoveredScreenShadowMaskDiagnostic.Load(",
            "_EndfieldRecoveredPreGBufferA.Load(int3(pixel, 0))",
            "selector == 256u",
            "_EndfieldRecoveredPreGBufferB.Load(int3(pixel, 0))",
            "EndfieldHGRPDecodeRecoveredYUpOct(",
            "(float2(pixel) + 0.5)",
            "clipPosition.y = -ndc.y;",
            "_EndfieldRecoveredScreenShadowMaskInverseGpuViewProjection",
            "actualWorldPosition,\n            signedGeometryNormal",
            "reconstructedWorldPosition,\n            preGNormal",
            "actualWorldPosition,\n                preGNormal",
            "reconstructedWorldPosition,\n                    signedGeometryNormal",
            "atlasCoordinateError = length(directAtlas - reconstructedAtlas);",
            "dot(normalize(preGNormal), normalize(signedGeometryNormal))",
            "primitiveFacing >= 0.0 ? 1.0 : -1.0",
        ],
    )
    audit_body = LIGHTING.read_text(encoding="utf-8").split(
        "inline void EndfieldHGRPWriteRecoveredScreenDirectAudit(", 1
    )[1].split("#else", 1)[0]
    require(
        audit_body.count("float2(pixel),\n        1.0") >= 2
        or audit_body.count("float2(pixel),\n            1.0") >= 2,
        "diagnostic solves no longer use explicit raw receiverStrength=1",
    )

    expected = {
        "Skin": ("1.0,\n                1.0 / 3.0", "faceGeometryNormal"),
        "Cloth": ("2.0,\n                0.0", "faceGeometryNormal"),
        "Hair": ("3.0,\n                1.0", "faceGeometryNormal"),
    }
    for family, path in SHADERS.items():
        family_tokens, signed_normal = expected[family]
        require_tokens(
            path,
            [
                "ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT_OUTPUTS",
                "ENDFIELD_WRITE_RECOVERED_SCREEN_DIRECT_AUDIT(",
                signed_normal,
                family_tokens,
                "Blend 0 [_SrcBlend] [_DstBlend]",
                "Blend 1 One Zero",
                "Blend 2 One Zero",
                "#pragma multi_compile __ ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT",
                "ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(facing)",
                "ENDFIELD_RECOVERED_SAME_OWNER_AUDIT_OUTPUTS",
                "ENDFIELD_WRITE_RECOVERED_SAME_OWNER_AUDIT(",
                "Blend 3 Off",
                "Blend 4 Off",
                "Blend 5 Off",
                "Blend 6 Off",
                "Blend 7 Off",
                "ColorMask RGBA 3",
                "ColorMask RGBA 4",
                "ColorMask RGBA 5",
                "ColorMask RGBA 6",
                "ColorMask RGBA 7",
                "ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(",
                "ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(",
                "endfieldSameOwnerNormalTS",
                "#pragma multi_compile __ ENDFIELD_RECOVERED_SAME_OWNER_AUDIT",
                '_EndfieldRecoveredForwardLogicalDrawId ("Diagnostic Forward Logical Draw ID", Integer) = 0',
                '_EndfieldRecoveredForwardRenderQueue ("Diagnostic Forward Render Queue", Integer) = 0',
            ],
        )

    expected_fragment_tbn_sites = {
        "Skin": 2,
        "Cloth": 2,
        "Hair": 2,
        "Eye": 1,
    }
    for family, path in TANGENT_SHADERS.items():
        text = path.read_text(encoding="utf-8")
        require_tokens(
            path,
            [
                "float4 tangent : TANGENT;",
                "float4 worldTangent : TEXCOORD3;",
                "o.worldTangent = float4(",
                "normalize(UnityObjectToWorldDir(v.tangent.xyz)),",
                "v.tangent.w);",
                "half3 tangentWS = normalize(i.worldTangent.xyz);",
                "cross(geometryNormal, tangentWS) * i.worldTangent.w;",
            ],
        )
        require(
            text.count(
                "cross(geometryNormal, tangentWS) * i.worldTangent.w;"
            )
            == expected_fragment_tbn_sites[family],
            f"{path.name}: Forward/PreG fragment TBN site count changed",
        )
        require(
            "worldBinormal" not in text,
            f"{path.name}: separately interpolated world binormal returned",
        )
        require(
            "unity_WorldTransformParams.w" not in text,
            f"{path.name}: tangent basis again depends on transform-sign ABI",
        )
        require(
            "half3 worldTangent" not in text,
            f"{path.name}: tangent varying no longer preserves source float4 W",
        )
    require_tokens(
        SHADERS["Hair"],
        ["float recoveredTangentSign = (float)i.worldTangent.w;"],
    )
    require(
        "recoveredUnsignedBinormal"
        not in SHADERS["Hair"].read_text(encoding="utf-8"),
        "Hair still infers tangent sign from a reconstructed binormal",
    )
    require(
        "ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT" not in EYE.read_text(encoding="utf-8"),
        "Eye unexpectedly participates in the character-G audit",
    )
    require_tokens(
        EYE,
        [
            "ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(",
            "ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT(",
        ],
    )

    require_tokens(
        COMMON,
        [
            "int _EndfieldRecoveredLogicalDrawId;",
            "int _EndfieldRecoveredForwardLogicalDrawId;",
            "int _EndfieldRecoveredForwardRenderQueue;",
            "ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(name)",
            "uint endfieldRecoveredPrimitiveId : SV_PrimitiveID",
            "bool name : SV_IsFrontFace",
            "fixed name : VFACE",
            "float4 owner : SV_Target2;",
            "ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_PARAMETER",
            "ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT",
            "primitiveId < 16777216u",
            "primitiveIdExact ? (float)primitiveId : -1.0",
            "output.owner = float4(",
            "normalTSXY);",
        ],
    )
    require_tokens(
        LIGHTING,
        [
            "Texture2D<float4> _EndfieldRecoveredPreGBufferOwner;",
            "out float4 endfieldSameOwnerAuditOwner : SV_Target3",
            "out float4 endfieldSameOwnerAuditShading : SV_Target4",
            "out float4 endfieldSameOwnerAuditGeometry : SV_Target5",
            "out float4 endfieldSameOwnerAuditPreG : SV_Target6",
            "out float4 endfieldSameOwnerAuditTangent : SV_Target7",
            "const uint exactFloatIntegerLimit = 16777216u;",
            "ownerMrt = float4(",
            "preGLogicalExact ? preGOwner.x : -1.0",
            "preGPrimitiveExact ? preGOwner.y : -1.0);",
            "familyCode << 12u",
            "classification |= 1u << 10u;",
            "classification |= 1u << 11u;",
            "shadingMrt.w = 1.0;",
            "primitiveId < exactFloatIntegerLimit",
            "shadingMrt = float4(normalize(signedShadingNormal), 1.0);",
            "geometryMrt = float4(",
            "preGMrt = float4(normalize(preGNormal), (float)classification);",
            "tangentMrt = float4(forwardNormalTS, preGOwner.zw);",
            "_EndfieldRecoveredForwardLogicalDrawId > 0",
            "_EndfieldRecoveredForwardRenderQueue <= 2500",
            "marker += 0.25;",
        ],
    )
    require_tokens(
        PRE_G,
        [
            "GraphicsFormat.R32G32B32A32_SFloat",
            "ExactFloatIntegerLimit = 1 << 24",
            "bool preGEligible =",
            "material.renderQueue <= (int)RenderQueue.GeometryLast",
            "? material.FindPass(CharacterPassName)",
            "if (!preGEligible)",
            "logicalDraws.Sort(",
            "logicalDraws.Count < ExactFloatIntegerLimit",
            "? (uint)(i + 1)",
            "commandBuffer.SetGlobalInt(",
            "new RenderTargetIdentifier(resources.sameOwner)",
            "CollectLogicalDrawsForSameOwner(Camera camera)",
            "without issuing graphics commands",
        ],
    )
    require_in_order(
        PRE_G,
        [
            "bool preGEligible =",
            "material.renderQueue <= (int)RenderQueue.GeometryLast",
            "? material.FindPass(CharacterPassName)",
            "if (!preGEligible)",
            "characterDraws.Add(logicalDraw)",
            "IsSourceBackedCharInfoPassAfterCharacterPreG(",
            'material.shader.name.StartsWith(\n                            "Endfield/Recovered/",',
            'material.shader.name + "/" + material.name + ": unsupported recovered family"',
        ],
    )
    require_tokens(
        PRE_G,
        [
            "renderer == presentation.floorRenderer",
            "renderer == presentation.wallRenderer",
            "renderer == presentation.farGridRenderer",
            "material.renderQueue == (int)RenderQueue.Geometry",
            "material.renderQueue == 2950",
            "EndfieldRecoveredCharInfoPresentation.FloorShaderName",
            "EndfieldRecoveredCharInfoPresentation.WallShaderName",
            "EndfieldRecoveredCharInfoPresentation.GridShaderName",
        ],
    )
    pre_g_text = PRE_G.read_text(encoding="utf-8")
    charinfo_exclusion = pre_g_text.find(
        "if (IsSourceBackedCharInfoPassAfterCharacterPreG("
    )
    unknown_recovered_blocker = pre_g_text.find(
        'material.shader.name.StartsWith(\n                            "Endfield/Recovered/",',
        charinfo_exclusion,
    )
    generic_depth = pre_g_text.find(
        "if (material.renderQueue <= (int)RenderQueue.GeometryLast)",
        unknown_recovered_blocker,
    )
    require(
        charinfo_exclusion >= 0
        and charinfo_exclusion < unknown_recovered_blocker < generic_depth,
        "PreG must exclude only the exact source-backed post-CharacterPrePass "
        "CharInfo passes before retaining the unknown recovered-family blocker "
        "and the non-recovered generic-depth fallback",
    )
    require_tokens(
        RUNTIME,
        [
            '"ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT"',
            '"ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT_USE_PREGBUFFER_DEPTH"',
            "Shader.DisableKeyword(Keyword);",
            "GraphicsFormat.R16G16B16A16_SFloat",
            "SystemInfo.supportedRenderTargetCount < 3",
            "preGBuffer.depthStencilFormat != GraphicsFormat.D32_SFloat_S8_UInt",
            "new[]\n                {\n                    canonicalColor,",
            "? new RenderTargetIdentifier(preGBuffer.depthStencil)\n                : canonicalColor",
            "commandBuffer.SetRenderTarget(canonicalColor);",
            "loadedVsRecomputedMismatchCount",
            "maximumLoadedVsRecomputedCodeDifference",
            '"screen_direct_audit_mrt0_rgba16f.raw"',
            '"screen_direct_audit_acceptance.png"',
            '"actual lab behavior: Forward depth-tests against the canonical CameraColor/TempBuffer forward depth/stencil, distinct from PreG sidecar ownership"',
            '"shipped CharInfo DefaultDeferred: generic deferred/forward ECS PreZ and "',
            '"ordinary opaque preDepthRendererList run in the earlier DepthPrepass; "',
            '"characterPrePassECSList and characterPrePassRendererList then run in "',
            '"GBuffer on the same sceneDepth"',
            '"generic opaque depth before the source-eligible opaque character PreG sidecar; "',
            '"draw counts are scene-dependent"',
            '"materials through GeometryLast only; observed eligible queues 2000/2015, observed "',
            '"2985/3000 Forward layers excluded"',
            '"Forward audit observes both opaque and transparent Skin/Cloth/Hair draws; family "',
            '"equality is not same draw or primitive identity, and transparent Forward may "',
            '"ENDFIELD_RECOVERED_SCREEN_DIRECT_SAME_OWNER_AUDIT"',
            '"ENDFIELD_RECOVERED_SAME_OWNER_AUDIT"',
            "GraphicsFormat.R32G32B32A32_SFloat",
            "SystemInfo.supportedRenderTargetCount < 8",
            "resources.sameOwnerShading",
            "resources.sameOwnerGeometry",
            "resources.sameOwnerPreG",
            "resources.sameOwnerTangent",
            "TangentClearSentinel",
            "request.GetData<float>()",
            "forwardShaderMarkerPixelCount",
            "exactFloatRenderTextureAllocationVerified",
            "exactFloatIntegerLimitExclusive = ExactFloatIntegerLimit",
            "floatIntegerPrecisionContract",
            "logicalIdRangeViolationPixelCount",
            "primitiveIdRangeViolationPixelCount",
            "TryDecodeExactFloatInteger(",
            "TryReadFiniteNormal(",
            "AccumulateTangentEvidence(",
            "sameOwnerTangentTargetWritePixelCount",
            "sameOwnerTangentMismatchPixelCount",
            "tangentFiniteWitnessMismatchPixelCount",
            "SameOwnerTangentDrawReport[] tangentByLogicalDraw",
            '"neutral-no-normal-map"',
            '"hair-split-rg-diffuse"',
            '"packed-ra-g"',
            "formatCapabilityContract",
            "carrierSynchronizationContract",
            "carriersPreparedBeforeCull",
            "PrepareSameOwnerBeforeCulling(",
            "PreparedLogicalDrawsMatch(",
            "RestoreAfterCamera(Camera camera)",
            "ApplyLogicalDrawPropertyBlocks(",
            "draw.material.HasInteger(ForwardLogicalDrawId)",
            "applied.SetInteger(",
            "applied.SetInteger(ForwardRenderQueue, draw.renderQueue);",
            "RestorePropertyBlocks(resources);",
            "originalWasEmpty ? null : restore.original",
            "draw.material.IsKeywordEnabled(",
            "draw.material.EnableKeyword(SameOwnerKeyword);",
            "restore.material.DisableKeyword(SameOwnerKeyword);",
            "Shader.IsKeywordEnabled(SameOwnerKeyword)",
            "commandBuffer.EnableShaderKeyword(SameOwnerKeyword);",
            "commandBuffer.DisableShaderKeyword(SameOwnerKeyword);",
            "CopySortedKeywords(",
            "sameOwnerVariantLegacyMarkerPixelCount",
            "keywordScopeContract",
            "materialKeywordDisabledAfterExplicitCount",
            '"screen_direct_same_owner_validation.json"',
            '"screen_direct_same_owner_draw_ids.json"',
            '"screen_direct_same_owner_ids_rgba32f.raw"',
            '"screen_direct_same_owner_shading_rgba32f.raw"',
            '"screen_direct_same_owner_geometry_rgba32f.raw"',
            '"screen_direct_same_owner_preg_rgba32f.raw"',
            '"screen_direct_same_owner_tangent_rgba32f.raw"',
            "sameDrawSamePrimitivePixelCount",
            "sameDrawDifferentPrimitivePixelCount",
            "crossDrawSameFamilyPixelCount",
            "crossDrawDifferentFamilyPixelCount",
            "transparentOverOpaquePreGPixelCount",
            "0.999991147",
            "const float minimumNormalAgreement = 0.999f;",
        ],
    )
    require_in_order(
        PIPELINE,
        [
            "new EndfieldRecoveredScreenDirectAudit()",
            "new EndfieldRecoveredScreenShadowMaskDiagnostic(\n                    recoveredScreenDirectAudit.Requested)",
            ".CollectLogicalDrawsForSameOwner(camera);",
            "recoveredScreenDirectAudit.PrepareSameOwnerBeforeCulling(",
            "context.Cull(ref cullingParameters);",
            "recoveredScreenDirectAudit.BeginForward(",
            # HGCompatRenderPipeline keeps this call multiline; anchor the
            # semantic DrawRenderers/opaque-range pair instead of one stale
            # single-line spelling.
            "DrawRenderers(\n                    context,\n                    camera,\n                    cullingResults,\n                    RenderQueueRange.opaque",
            "SortingCriteria.CommonTransparent | SortingCriteria.RendererPriority,",
            "recoveredScreenDirectAudit.EndForward(",
            "context.Submit();",
            "recoveredScreenDirectAudit.FinalizeKeywordAfterSubmit();",
        ],
    )
    require_in_order(
        RUNTIME,
        [
            "commandBuffer.EnableShaderKeyword(SameOwnerKeyword);",
            "context.ExecuteCommandBuffer(commandBuffer);",
            "EnqueueSameOwnerReadback(",
            "commandBuffer.DisableShaderKeyword(SameOwnerKeyword);",
            "context.ExecuteCommandBuffer(commandBuffer);",
        ],
    )
    require_tokens(
        PIPELINE,
        [
            "recoveredScreenDirectAudit.SameOwnerRequested",
            "recoveredScreenDirectAudit.RestoreAfterCamera(camera);",
        ],
    )
    require_tokens(
        SCREEN,
        [
            "bool forceProducerRequested = false",
            "requested = forceProducerRequested || consumerRequested || IsRequested(",
        ],
    )
    require_tokens(
        BATCH,
        [
            "EndfieldRecoveredScreenDirectAuditBatchVerifier",
            "GraphicsFormat.R16G16B16A16_SFloat",
            "report.loadedVsRecomputedMismatchCount != 0",
            "report.maximumLoadedVsRecomputedCodeDifference > 1",
            "report.recoveredRetailPreDepthChronology.IndexOf(",
            '"generic deferred/forward ECS PreZ"',
            '"DefaultDeferred"',
            '"through GeometryLast only"',
            '"both opaque and transparent"',
            "GraphicsFormat.R32G32B32A32_SFloat",
            "SystemInfo.supportedRenderTargetCount < 8",
            "exactFloatIntegerLimitExclusive != (1 << 24)",
            "report.carriersPreparedBeforeCull",
            "report.carrierSynchronizationContract.IndexOf(",
            '"before Cull"',
            '"after Submit"',
            "primitiveIdRangeViolationPixelCount",
            "AsyncGPUReadback<float>",
            "VerifySameOwner(cameraDirectory);",
            "report.sameOwnerVariantLegacyMarkerPixelCount <= 0",
            "report.globalKeywordEnabledAtBegin",
            "report.materialKeywordDisabledAfterExplicitCount != 0",
            "report.materialKeywordStates.Length != report.materialKeywordStateCount",
            '"#pragma multi_compile"',
            '"explicitly enables/restores"',
            '"screen_direct_same_owner_validation.json"',
            '"screen_direct_same_owner_draw_ids.json"',
            '"conservative diagnostic threshold"',
            '"component-exact"',
            '"screen_direct_same_owner_tangent_rgba32f.raw"',
            "report.tangentByLogicalDraw",
        ],
    )
    require(
        "GraphicsFormat.R32G32_UInt" not in RUNTIME.read_text(encoding="utf-8")
        and "GraphicsFormat.R32G32B32A32_UInt"
        not in RUNTIME.read_text(encoding="utf-8"),
        "runtime must never allocate the native-crashing UINT RenderTexture formats",
    )
    require(
        "GraphicsFormat.R32G32_UInt" not in PRE_G.read_text(encoding="utf-8"),
        "PreG must never allocate the native-crashing UINT owner RenderTexture",
    )
    require(
        "GraphicsFormat.R32G32_UInt" not in BATCH.read_text(encoding="utf-8")
        and "GraphicsFormat.R32G32B32A32_UInt"
        not in BATCH.read_text(encoding="utf-8"),
        "batch preflight must never probe the native-crashing UINT RenderTexture formats",
    )
    require_tokens(
        SAME_OWNER_WRAPPER,
        [
            "ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT=1",
            "ENDFIELD_RECOVERED_SCREEN_DIRECT_SAME_OWNER_AUDIT=1",
            "EndfieldRecoveredScreenDirectAuditBatchVerifier.Verify",
            "-force-d3d12",
        ],
    )

    require_tokens(
        WRAPPER,
        [
            "ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT=1",
            "EndfieldRecoveredScreenDirectAuditBatchVerifier.Verify",
            "-force-d3d12",
        ],
    )

    print(
        json.dumps(
            {
                "ok": True,
                "defaultOff": True,
                "families": list(SHADERS),
                "eyeExcluded": True,
                "auditTargets": [
                    "R16G16B16A16_SFloat",
                    "R16G16B16A16_SFloat",
                ],
                "ordinaryTarget": "SV_Target0 preserved",
                "tangentBasisContract": (
                    "float4 tangent varying; fragment "
                    "cross(normalized N, normalized T.xyz) * interpolated T.w"
                ),
                "sameOwnerTargets": [
                    "PreG RGBA32_SFloat numeric IDs + normalTS.xy",
                    "Forward RGBA32_SFloat numeric IDs",
                    "Forward 3x RGBA32_SFloat full XYZ normals/classes",
                    "Forward final RGBA32_SFloat exact-owner tangent pairs",
                ],
                "depthModes": ["canonical CameraColor forward depth/stencil", "explicit PreG D32S8"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, UnicodeError) as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
