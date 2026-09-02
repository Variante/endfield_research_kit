#!/usr/bin/env python3
"""Fail-closed admission gate for a generative M27 exact PSR draw.

This tool deliberately does not replay captured vertex, index, or constant-
buffer bytes.  It joins source contracts that are already closed and admits a
draw only when a separate live observation proves that the compiler-substituted
subprogram-113 pair ran on the retained ParticleSystemRenderer path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any


SCHEMA = "endfield.endminf-m27-live-exact-abi-admission.v1"
LIVE_SCHEMA = "endfield.endminf-m27-live-exact-particle-draw.v1"
LIVE_AUTHENTICATION_SCHEMA = (
    "endfield.endminf-m27-live-exact-particle-draw-authentication.v1")
GENERATIVE_SHELL_PIN_SCHEMA = (
    "endfield.endminf-m27-generative-shell-pin.v1")
GENERATIVE_SHELL_OBSERVATION_SCHEMA = (
    "endfield.m27-generative-unity-shell-observation.v1")
TERRAIN_NATIVE_CONTRACT_SCHEMA = (
    "endfield.endminf-m27-terrain-profile-native-contract.v1")
TERRAIN_SELECTED_FRAME_SCHEMA = (
    "endfield.endminf-m27-terrain-profile-selected-frame.v1")
M27_MIP_BIAS_SOURCE_SCHEMA = (
    "endfield.endminf-m27-global-mip-bias-unity-source.v1")
M27_MIP_BIAS_RESOURCE_NAME = (
    "EndfieldRecoveredM27/endminf_m27_global_mip_bias_source")
M27_MIP_BIAS_STATIC_CONTRACT_SHA256 = (
    "01d703a635fa1b2f2cf463cc78c501bab2e1e97d93444605fb82be62f9f5d0d9")

VS_SHA256 = "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c"
PS_SHA256 = "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e"
VS_IDENTITY = "0xC0266E7FAC0046C1"
PS_IDENTITY = "0x92D80A93ADD9C714"
SHELL_VS_SHA256 = "b6ffa6a650c43fa86cfed1a146ecdfb046d6c92c7e866ff6f51ac79a6c7d4833"
SHELL_PS_SHA256 = "9a6803527679aa4d4822ca38a4257c2dafcbce2748a67c7e3387f63e3ee54707"
GENERATIVE_SHELL_VS_SHA256 = (
    "6b87d2cb5f1d92dd3209b104d52fb700dba578b12237468cbe9ea9082a9a1022")
GENERATIVE_SHELL_PS_SHA256 = (
    "0ad380949c0e8edaedc6ac76fa002017ff2476bff4a0ce9d2d52de0569e903ce")

RENDERER_PATH_ID = 59284134265994738
MATERIAL_PATH_ID = -6543263480174539080  # 0xA531A88850690EB8
MESH_PATH_ID = -8157825361227167527  # 0x8EC9950E5461C8D9
HIERARCHY = "all/suikuai (2)"
ACTIVE_STREAMS = [
    "Position", "Normal", "Color", "UV", "UV2", "Custom1XYZW"
]
ALLOWED_IA_STRIDES = [60, 68]

# The exact VS gates its optional t0 skin palette from UnityPerDraw record
# c4.w. The selected unskinned draw proves bit 5 clear, but retail may still
# retain the real global palette binding. Authenticate the explicit draw-local
# outcome; never manufacture an identity buffer for the inactive branch.
VERTEX_SKIN_CB_SLOT = 2
VERTEX_SKIN_RECORD_INDEX = 0
VERTEX_SKIN_RECORD_STRIDE_FLOAT4 = 16
VERTEX_SKIN_FLAG_REGISTER_OFFSET = 4
VERTEX_SKIN_FLAG_LANE = "w"
VERTEX_SKIN_FLAG_MASK = 32
VERTEX_SKIN_BUFFER_BYTES = 8_413_184
VERTEX_SKIN_BUFFER_ELEMENTS = 525_824
VERTEX_SKIN_VIEW_DIMENSION = 1
VERTEX_SKIN_BIND_FLAGS = 136
VERTEX_SKIN_MISC_FLAGS = 64

TARGET = {
    "textureFormat": 26,
    "viewFormat": 26,
    "sampleCount": 1,
    "renderTargetCount": 5,
    "depthBound": True,
}
DEPTH_TARGET = {
    "textureFormat": 19,
    "viewFormat": 20,
    "sampleCount": 1,
}

MRT_SLOTS = [
    (0, "SceneColor", 26, 26),
    (1, "SceneMV", 24, 24),
    (2, "GBufferA", 24, 24),
    (3, "GBufferB", 24, 24),
    (4, "GBufferC", 29, 29),
]

SAMPLER_SLOTS = [0, 1, 2, 3, 4, 5]

TEXTURE_SLOTS = [
    (0, "_BaseColorMap", 1024, 1024, 99, 11,
     "9f5255c1a12b2a17586362f864097453db9158288dafaf0b234ea81e964e88ba"),
    (1, "_NormalMap", 1024, 1024, 83, 11,
     "ee27e904469e3879349ac52a5e7eac9247c150914a7d9a940d0c0c16ec512af7"),
    (2, "_MROMap", 1024, 1024, 83, 11,
     "da6f07ae91303fe587f0e363e4f37f3df2631bac6a47c95ac55bbbedd9e4e434"),
    (3, "_ParallaxMap", 128, 128, 99, 8,
     "9bdc2187bbc5ee1c2c74c4b0486060fa46c3aba2a1860c3221693f77b00a27e8"),
]
SERIALIZED_NULL_TEXTURE_SLOTS = [
    (4, "_ParallaxMaskMap"),
    (5, "_ParallaxNoiseMap"),
]

CBUFFERS = [
    (0, "_TransformVariables", 1312, 1312,
     "EndfieldRecoveredDeferredTransformVariables"),
    (1, "ShaderVariablesGlobal", 3200, 1696,
     "EndfieldRecoveredShaderVariablesGlobal"),
    (2, "UnityPerDraw", 256, 256, "ParticleSystemRenderer"),
    (3, "UnityPerMaterial", 576, 496, "Material"),
    (4, "_TerrainSubsurfaceConstants", 16, 16,
     "EndfieldRecoveredTerrainSubsurfaceConstants"),
]

B3_READ_LANES = (
    (0, "xzw"), (1, "xw"), (2, "w"), (3, "xyw"),
    (4, "xyz"), (7, "xz"), (8, "xyzw"), (11, "xyzw"),
    (12, "xyzw"), (22, "x"), (24, "xyzw"), (25, "xyzw"),
    (26, "xyzw"), (27, "xyz"), (28, "yw"), (29, "xyz"),
    (30, "xyz"),
)
LANE_INDEX = {lane: index for index, lane in enumerate("xyzw")}


class VerificationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"could not read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"expected a JSON object at {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _is_sha256(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(character in "0123456789abcdef"
                                   for character in text)


def _source(path: Path, repo: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(repo).as_posix(),
        "sha256": _sha256(path),
    }


def _find(items: list[dict[str, Any]], **wanted: Any) -> dict[str, Any]:
    for item in items:
        if all(item.get(key) == value for key, value in wanted.items()):
            return item
    raise VerificationError(f"missing row {wanted}")


def _float_word(value: Any) -> int:
    return struct.unpack("<I", struct.pack("<f", float(value)))[0]


def _call_text(source: str, callee: str) -> str:
    """Return one balanced call expression, or an empty string if absent."""
    start = source.find(callee)
    if start < 0:
        return ""
    opening = source.find("(", start + len(callee))
    if opening < 0:
        return ""
    depth = 0
    for index in range(opening, len(source)):
        character = source[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    return ""


def _validate_runtime_source_connections(
        pipeline_text: str,
        frame_runtime_text: str) -> dict[str, bool]:
    """Prove that source readiness/material state reaches the exact draw."""
    pipeline_render = re.sub(
        r"\s+", "", _call_text(
            pipeline_text, "recoveredDeferredGBufferFrame.Render"))
    frame_render_signature = re.sub(
        r"\s+", "", _call_text(frame_runtime_text, "internal bool Render"))
    bind_draw = re.sub(
        r"\s+", "", _call_text(
            frame_runtime_text,
            "endminfM27GenerativeExactRuntime.TryBindDraw"))
    configure_material = re.sub(
        r"\s+", "", _call_text(
            frame_runtime_text,
            "endminfM27GenerativeExactRuntime.TryConfigureMaterial"))

    b0_pipeline_connection = (
        "recoveredDeferredTransformVariables.CurrentBuffer,"
        "recoveredDeferredTransformsReady,"
        "recoveredDeferredTransformVariables.CurrentM27SourceReady,"
        "recoveredShaderVariablesGlobal.CurrentBuffer,"
        "recoveredShaderVariablesGlobalReady,"
        "recoveredShaderVariablesGlobal.CurrentM27SourceReady" in
        pipeline_render)
    b0_frame_connection = (
        "ComputeBuffertransformVariables,"
        "booltransformVariablesReady,"
        "booltransformVariablesM27SourceReady,"
        "ComputeBuffershaderVariablesGlobal,"
        "boolshaderVariablesGlobalReady,"
        "boolshaderVariablesGlobalM27SourceReady" in
        frame_render_signature and
        "transformVariables,transformVariablesReady,"
        "transformVariablesM27SourceReady,shaderVariablesGlobal,"
        "shaderVariablesGlobalReady,shaderVariablesGlobalM27SourceReady" in
        bind_draw)
    b3_material_connection = (
        "TryConfigureMaterial(sourceMaterial,endminfM27Material,outfailure)" in
        configure_material)
    return {
        "b0ReadinessReachesExactDraw": (
            b0_pipeline_connection and b0_frame_connection),
        "b3RetainedMaterialReachesExactShell": b3_material_connection,
    }


def _call_argument_count(expression: str) -> int:
    opening = expression.find("(")
    if opening < 0:
        return 0
    depth = 0
    count = 1
    has_argument = False
    for character in expression[opening + 1:]:
        if character == "(":
            depth += 1
            has_argument = True
        elif character == ")":
            if depth == 0:
                return count if has_argument else 0
            depth -= 1
            has_argument = True
        elif character == "," and depth == 0:
            count += 1
        elif not character.isspace():
            has_argument = True
    return 0


def _call_arguments(expression: str) -> list[str]:
    """Return top-level call arguments, or an empty list if malformed."""
    opening = expression.find("(")
    if opening < 0:
        return []
    depth = 0
    start = opening + 1
    arguments: list[str] = []
    for index, character in enumerate(expression[start:], start=start):
        if character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                tail = expression[start:index].strip()
                if tail or arguments:
                    arguments.append(tail)
                return arguments
            depth -= 1
        elif character == "," and depth == 0:
            arguments.append(expression[start:index].strip())
            start = index + 1
    return []


def _assignment_expressions(
        source: str,
        variable: str) -> list[tuple[int, int, str]]:
    """Return simple statement assignments to one local variable.

    The audited publisher join deliberately uses statement-local values.  A
    unique-assignment requirement makes an inserted overwrite fail closed
    instead of letting token-presence checks bless an earlier good value.
    """
    pattern = re.compile(rf"\b{re.escape(variable)}\s*=(?!=)")
    assignments: list[tuple[int, int, str]] = []
    for match in pattern.finditer(source):
        depth = 0
        for index in range(match.end(), len(source)):
            character = source[index]
            if character in "([{":
                depth += 1
            elif character in ")]}":
                depth -= 1
            elif character == ";" and depth == 0:
                assignments.append((
                    match.start(),
                    index + 1,
                    source[match.end():index].strip(),
                ))
                break
    return assignments


def _unique_compact_assignment(
        source: str,
        variable: str) -> tuple[int, int, str] | None:
    assignments = _assignment_expressions(source, variable)
    if len(assignments) != 1:
        return None
    start, end, expression = assignments[0]
    return start, end, re.sub(r"\s+", "", expression)


def _method_body(source: str, signature: str) -> str:
    """Return a balanced C# method body for a unique audited signature."""
    start = source.find(signature)
    if start < 0 or source.find(signature, start + len(signature)) >= 0:
        return ""
    opening = source.find("{", start + len(signature))
    if opening < 0:
        return ""
    depth = 0
    for index in range(opening, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    return ""


def _validate_m27_global_mip_bias_source_contract(
        source_text: str,
        contract_text: str,
        pipeline_text: str) -> dict[str, Any]:
    """Audit the absent-by-default authenticated c26 Resource bridge."""
    compact_source = re.sub(r"\s+", "", source_text)
    compact_contract = re.sub(r"\s+", "", contract_text)
    ensure_loaded = re.sub(
        r"\s+", "", _method_body(source_text, "private void EnsureLoaded()"))
    validate_payload = re.sub(
        r"\s+", "", _method_body(
            source_text,
            "public static bool TryValidatePayloadJson("))
    overlay_method = re.sub(
        r"\s+", "", _method_body(
            contract_text,
            "public M27SourceInputs WithPhysicalCameraGlobalMipBias("))

    identity_and_resource_gate = all(marker in compact_source for marker in (
        "publicsealedclassEndfieldRecoveredM27GlobalMipBiasSource",
        f'publicconststringResourceName="{M27_MIP_BIAS_RESOURCE_NAME}";',
        f'publicconststringPayloadSchema="{M27_MIP_BIAS_SOURCE_SCHEMA}";',
        "publicconststringPayloadStatus=\"source_authenticated_for_c26_only\";",
        f'publicconststringStaticContractSha256="{M27_MIP_BIAS_STATIC_CONTRACT_SHA256}";',
        f'publicconststringRendererPathId="{RENDERER_PATH_ID}";',
    ))
    absent_resource_fails_closed = all(marker in ensure_loaded for marker in (
        "TextAssetsource=Resources.Load<TextAsset>(ResourceName);",
        "if(source==null)",
        'diagnostic="authenticatedEndminfM27global-mip-biasResourceisabsent";',
        "return;",
        "ready=TryValidatePayloadJson(source.text,outglobalMipBias,outdiagnostic);",
    ))
    schema_status_gate = all(marker in validate_payload for marker in (
        "string.Equals(payload.schema,PayloadSchema,StringComparison.Ordinal)",
        "string.Equals(payload.status,PayloadStatus,StringComparison.Ordinal)",
    ))
    hash_identity_gate = all(marker in validate_payload for marker in (
        "!IsLowerHex(payload.sourceReportSha256,64)",
        "!IsLowerHex(payload.receiptSha256,64)",
        "!IsLowerHex(payload.runtimePackageSha256,64)",
        "string.Equals(payload.staticContractSha256,StaticContractSha256,StringComparison.Ordinal)",
        "string.Equals(payload.rendererPathId,RendererPathId,StringComparison.Ordinal)",
    ))
    authority_gate = (
        "if(!payload.canPopulatePhysicalCameraMipBiasSource||"
        "payload.presentationAuthority)" in validate_payload)
    bit_and_equation_gate = all(marker in validate_payload for marker in (
        "TryParseBits(payload.materialMipBiasBits,outuintmaterialBits)",
        "TryParseBits(payload.dynamicTermBits,outuintdynamicBits)",
        "TryParseBits(payload.globalMipBiasBits,outuintglobalBits)",
        "TryParseBits(payload.publishedC26YBits,outuintpow2Bits)",
        "FloatBits(material+dynamicTerm)!=globalBits",
        "FloatBits(Mathf.Pow(2.0f,global))!=pow2Bits",
        "value=global;returntrue;",
    ))
    overlay_preserves_other_sources = (
        "if(!ready)returnthis;returnnewM27SourceInputs("
        "targetDimensionsReady,perspectiveCameraReady,taaJitterStrength,"
        "taaJitterReady,value,true,exposureAdaptation,exposureReady,"
        "vfxPlayerPosition,vfxClockSeconds,vfxParams0Ready,vfxParams2,"
        "vfxParams2Ready);" in overlay_method and
        "publicreadonlyfloatphysicalCameraGlobalMipBias;" in compact_contract and
        "publicreadonlyboolphysicalCameraGlobalMipBiasReady;" in compact_contract)

    compact_pipeline = re.sub(r"\s+", "", pipeline_text)
    owner_lifecycle = all(marker in compact_pipeline for marker in (
        "privatereadonlyEndfieldRecoveredM27GlobalMipBiasSource"
        "recoveredM27GlobalMipBiasSource;",
        "recoveredM27GlobalMipBiasSource="
        "newEndfieldRecoveredM27GlobalMipBiasSource();",
    ))
    try_get_call = _call_text(
        pipeline_text,
        "recoveredM27GlobalMipBiasSource.TryGetGlobalMipBias")
    try_get_arguments = _call_arguments(try_get_call)
    try_get_exact = try_get_arguments == [
        "out float recoveredM27GlobalMipBias", "out _"]
    source_assignments = _assignment_expressions(pipeline_text, "m27SourceInputs")
    source_assignment_expressions = [
        re.sub(r"\s+", "", row[2]) for row in source_assignments]
    expected_initial = (
        "EndfieldRecoveredShaderVariablesGlobalContract.M27SourceInputs."
        "CurrentTargetPerspectiveExposureAndVFXPlayer("
        "recoveredCurrentCameraExposure,recoveredCurrentCameraExposureReady,"
        "recoveredVFXPlayerPosition,recoveredVFXClockSeconds,"
        "recoveredVFXParams0Ready)")
    expected_overlay = (
        "m27SourceInputs.WithPhysicalCameraGlobalMipBias("
        "recoveredM27GlobalMipBias,true)")
    exact_two_stage_assignment = (
        source_assignment_expressions == [expected_initial, expected_overlay])
    publish_call = _call_text(
        pipeline_text, "recoveredShaderVariablesGlobal.PrepareAndPublish")
    publish_arguments = _call_arguments(publish_call)
    publish_position = pipeline_text.find(publish_call)
    try_get_position = pipeline_text.find(try_get_call)
    overlay_ordered_before_publish = (
        len(source_assignments) == 2 and
        source_assignments[0][1] < try_get_position <
        source_assignments[1][0] < source_assignments[1][1] < publish_position and
        len(publish_arguments) == 8 and
        publish_arguments[5] == "m27SourceInputs")

    checks = {
        "namedSourceOwner": identity_and_resource_gate,
        "absentResourceFailsClosed": absent_resource_fails_closed,
        "schemaStatusGate": schema_status_gate,
        "hashIdentityGate": hash_identity_gate,
        "authorityGate": authority_gate,
        "bitAndEquationGate": bit_and_equation_gate,
        "overlayPreservesOtherSources": overlay_preserves_other_sources,
        "pipelineOwnerLifecycle": owner_lifecycle,
        "pipelineTryGetExact": try_get_exact,
        "exactTwoStageAssignment": exact_two_stage_assignment,
        "overlayOrderedBeforePublisher": overlay_ordered_before_publish,
    }
    return {
        "resourceName": M27_MIP_BIAS_RESOURCE_NAME,
        "payloadSchema": M27_MIP_BIAS_SOURCE_SCHEMA,
        "resourceRequiredAtAuditTime": False,
        "checks": checks,
        "connectionAudited": all(checks.values()),
    }


def _validate_b1_source_contract(
        contract_text: str,
        owner_text: str,
        pipeline_text: str,
        m27_mip_bias_source_text: str) -> dict[str, Any]:
    """Audit source-owned M27 b1 equations separately from live owners."""
    compact_contract = re.sub(r"\s+", "", contract_text)
    compact_owner = re.sub(r"\s+", "", owner_text)
    default_inputs = re.sub(
        r"\s+", "", _call_text(
            contract_text, "return new M27SourceInputs"))
    pipeline_publish = _call_text(
        pipeline_text, "recoveredShaderVariablesGlobal.PrepareAndPublish")
    pipeline_publish_arguments = _call_arguments(pipeline_publish)

    readiness_fields = {
        "c0.zw": "public readonly bool targetDimensionsReady;",
        "c4.w": "public readonly bool perspectiveCameraReady;",
        "c19.zw": "public readonly bool taaJitterReady;",
        "c26.xy": (
            "public readonly bool physicalCameraGlobalMipBiasReady;"),
        "c27.y": "public readonly bool exposureReady;",
        "c103.xyzw": "public readonly bool vfxParams0Ready;",
        "c105.xyzw": "public readonly bool vfxParams2Ready;",
    }
    readiness = {
        register: declaration in contract_text
        for register, declaration in readiness_fields.items()
    }
    equations = {
        "currentTargetDimensionsAndReciprocals": (
            "destination[ScreenSizeVector]=newVector4(width,height,"
            "1.0f/width,1.0f/height);" in compact_contract),
        "currentPerspectiveFlag": (
            "camera.orthographic?1.0f:0.0f" in compact_contract),
        "haltonJitterInputGuarded": (
            "if(m27Inputs.taaJitterReady)" in compact_contract and
            "m27Inputs.taaJitterStrength" in compact_contract),
        "physicalCameraMipBiasInputGuarded": (
            "if(m27Inputs.physicalCameraGlobalMipBiasReady)" in
            compact_contract and
            "Mathf.Pow(2.0f,m27Inputs.physicalCameraGlobalMipBias)" in
            compact_contract),
        "exposureReciprocalInputGuarded": (
            "if(m27Inputs.exposureReady)" in compact_contract and
            "1.0f/m27Inputs.exposureAdaptation" in compact_contract),
        "playerCenterAndClockInputGuarded": (
            "if(m27Inputs.vfxParams0Ready)" in compact_contract and
            "m27Inputs.vfxClockSeconds%1024.0f" in compact_contract),
        "anchorStateInputGuarded": (
            "if(m27Inputs.vfxParams2Ready)" in compact_contract and
            "destination[VFXParams2Vector]=m27Inputs.vfxParams2" in
            compact_contract),
    }
    validation_mentions_all_reads = all(
        f'M27 b1 {register}' in contract_text for register in readiness)
    default_unresolved_inputs_are_not_ready = (
        default_inputs ==
        "returnnewM27SourceInputs(true,true,Vector4.zero,false,0.0f,"
        "false,0.0f,false,Vector3.zero,0.0f,false,Vector4.zero,false)" and
        "M27SourceInputs.CurrentTargetAndPerspectiveCameraOnly" in owner_text)
    owner_tracks_validated_readiness = (
        "currentM27SourceReady=EndfieldRecoveredShaderVariablesGlobalContract"
        ".TryValidateM27SourceReadiness(m27Inputs,out_);" in compact_owner and
        "internalboolCurrentM27SourceReady=>currentM27SourceReady;" in
        compact_owner and
        "currentM27SourceReady=false;" in compact_owner)
    complete = (
        all(readiness.values()) and all(equations.values()) and
        validation_mentions_all_reads and
        default_unresolved_inputs_are_not_ready and
        owner_tracks_validated_readiness)
    source_input_expression = (
        pipeline_publish_arguments[5]
        if len(pipeline_publish_arguments) == 8 else None)
    inline_default_input = bool(
        source_input_expression and re.search(
            r"\bdefault\s*(?:\(|$)", source_input_expression))
    inline_constructed_input = bool(
        source_input_expression and re.search(
            r"\bnew\s+(?:[A-Za-z_]\w*\.)*M27SourceInputs\s*\(",
            source_input_expression))
    named_source_owner_expression = bool(
        source_input_expression and re.fullmatch(
            r"[A-Za-z_]\w*\.CurrentM27SourceInputs",
            source_input_expression.strip()))
    named_source_input_expression = bool(
        source_input_expression and re.fullmatch(
            r"[A-Za-z_]\w*",
            source_input_expression.strip()))
    partial_factory_audited = (
        "CurrentTargetPerspectiveExposureAndVFXPlayer(" in contract_text and
        "returnnewM27SourceInputs(true,true,Vector4.zero,false,0.0f,false,"
        "exposureAdaptation,exposureReady,vfxPlayerPosition,vfxClockSeconds,"
        "vfxParams0Ready,Vector4.zero,false);" in compact_contract)
    prepare_method_body = _method_body(
        pipeline_text,
        "private EndfieldRecoveredCharInfoAutoExposureCameraState\n"
        "            PrepareRecoveredLiveCharInfoAutoExposure(")
    manual_selector_body = _method_body(
        prepare_method_body,
        "if (!recoveredLiveCharInfoAutoExposureRequested)")
    compact_manual_selector_body = re.sub(
        r"\s+", "", manual_selector_body)
    advance_manual = "state.AdvanceSourceClosedNeutralProfile(deltaTime);"
    source_closed_manual_exposure_return_audited = (
        bool(prepare_method_body) and
        bool(manual_selector_body) and
        "if(!useRecoveredGachaManualExposure)returnnull;" in
        compact_manual_selector_body and
        compact_manual_selector_body.count(advance_manual) == 1 and
        compact_manual_selector_body.endswith(advance_manual + "returnstate;") and
        "state.Advance(deltaTime,Time.frameCount);" not in
        compact_manual_selector_body and
        "state.AdvanceInactive(deltaTime);" not in
        compact_manual_selector_body and
        prepare_method_body.count(
            "state.AdvanceSourceClosedNeutralProfile(deltaTime);") == 1)

    expected_assignments = {
        "recoveredSourceClosedManualExposureRequested": (
            "(recoveredSceneMVRequest.requested||"
            "recoveredDeferredExactConsumer.Requested&&"
            "recoveredEndminfLitEffectOwnerActive)&&"
            "camera.GetComponent<EndfieldHGOperatorPresentation>()is"
            "EndfieldHGOperatorPresentationexposurePresentation&&"
            "exposurePresentation.environmentPhaseSnapshot!=null&&"
            "(exposurePresentation.environmentPhaseSnapshot."
            "IsGachaRoomSourceClosed||exposurePresentation."
            "environmentPhaseSnapshot.IsCharacterInfoSourceClosed)"),
        "recoveredCurrentCameraExposure": (
            "liveAutoExposureState!=null?"
            "liveAutoExposureState.CurrentExposure:0.0f"),
        "recoveredCurrentCameraExposureReady": (
            "recoveredSourceClosedManualExposureRequested&&"
            "!recoveredLiveCharInfoAutoExposureRequested&&"
            "liveAutoExposureState!=null&&"
            "recoveredCurrentCameraExposure>0.0f&&"
            "!float.IsNaN(recoveredCurrentCameraExposure)&&"
            "!float.IsInfinity(recoveredCurrentCameraExposure)"),
        "recoveredVFXPlayerSourceRequested": (
            "useRecoveredSceneMV||recoveredEndminfLitEffectOwnerActive&&"
            "EndfieldRecoveredShaderVariablesGlobal.IsRequested"),
        "recoveredVFXPlayerCenterReady": (
            "recoveredVFXPlayerSourceRequested&&"
            "TryResolveRecoveredVFXPlayerCenter(outrecoveredVFXPlayerCenter)"),
        "recoveredVFXPlayerPosition": (
            "recoveredVFXPlayerCenterReady?"
            "recoveredVFXPlayerCenter.position:Vector3.zero"),
        "recoveredVFXClockSeconds": (
            "recoveredVFXPlayerCenterReady?Time.time:0.0f"),
        "recoveredVFXParams0Ready": (
            "recoveredVFXPlayerCenterReady&&"
            "!float.IsNaN(recoveredVFXClockSeconds)&&"
            "!float.IsInfinity(recoveredVFXClockSeconds)&&"
            "recoveredVFXClockSeconds>=0.0f"),
        "m27SourceInputs": (
            "EndfieldRecoveredShaderVariablesGlobalContract.M27SourceInputs."
            "CurrentTargetPerspectiveExposureAndVFXPlayer("
            "recoveredCurrentCameraExposure,"
            "recoveredCurrentCameraExposureReady,"
            "recoveredVFXPlayerPosition,recoveredVFXClockSeconds,"
            "recoveredVFXParams0Ready)"),
    }
    assignments: dict[str, tuple[int, int, str] | None] = {
        variable: _unique_compact_assignment(pipeline_text, variable)
        for variable in expected_assignments if variable != "m27SourceInputs"
    }
    m27_assignments = _assignment_expressions(pipeline_text, "m27SourceInputs")
    assignments["m27SourceInputs"] = (
        (m27_assignments[0][0], m27_assignments[0][1],
         re.sub(r"\s+", "", m27_assignments[0][2]))
        if len(m27_assignments) == 2 else None)
    assignment_shapes_audited = {
        variable: assignment is not None and assignment[2] == expected
        for variable, expected in expected_assignments.items()
        for assignment in (assignments[variable],)
    }
    ordered_variables = list(expected_assignments)
    ordered_assignments = [assignments[variable] for variable in ordered_variables]
    assignment_order_audited = (
        all(assignment is not None for assignment in ordered_assignments) and
        all(
            ordered_assignments[index][1] < ordered_assignments[index + 1][0]
            for index in range(len(ordered_assignments) - 1)))
    manual_prepare = _call_text(
        pipeline_text, "PrepareRecoveredLiveCharInfoAutoExposure")
    manual_prepare_arguments = _call_arguments(manual_prepare)
    source_closed_manual_exposure_gate_audited = (
        assignment_shapes_audited[
            "recoveredSourceClosedManualExposureRequested"] and
        len(manual_prepare_arguments) == 4 and
        manual_prepare_arguments[3] ==
        "recoveredSourceClosedManualExposureRequested")
    exposure_lane_audited = (
        source_closed_manual_exposure_return_audited and
        source_closed_manual_exposure_gate_audited and
        assignment_shapes_audited["recoveredCurrentCameraExposure"] and
        assignment_shapes_audited["recoveredCurrentCameraExposureReady"])
    vfx_lab_carrier_lane_audited = all(
        assignment_shapes_audited[variable]
        for variable in (
            "recoveredVFXPlayerSourceRequested",
            "recoveredVFXPlayerCenterReady",
            "recoveredVFXPlayerPosition",
            "recoveredVFXClockSeconds",
            "recoveredVFXParams0Ready"))
    partial_pipeline_join_audited = (
        exposure_lane_audited and
        vfx_lab_carrier_lane_audited and
        assignment_shapes_audited["m27SourceInputs"] and
        assignment_order_audited)
    partial_source_join_audited = (
        source_input_expression == "m27SourceInputs" and
        partial_factory_audited and partial_pipeline_join_audited)
    mip_bias_source_contract = _validate_m27_global_mip_bias_source_contract(
        m27_mip_bias_source_text,
        contract_text,
        pipeline_text)
    c26_source_connection_audited = (
        partial_source_join_audited and
        mip_bias_source_contract["connectionAudited"])
    runtime_read_connections = {
        "c0.zw": partial_source_join_audited,
        "c4.w": partial_source_join_audited,
        "c19.zw": False,
        "c26.xy": c26_source_connection_audited,
        "c27.y": partial_source_join_audited,
        "c103.xyzw": partial_source_join_audited,
        "c105.xyzw": False,
    }
    # A named owner property is only a connection candidate. Its per-field
    # readiness/lifecycle still needs a separate audit. The current audited
    # connection is instead a local partial join with explicitly bounded lanes.
    named_source_owner_contract_audited = mip_bias_source_contract[
        "connectionAudited"]
    explicit_inputs_reach_runtime = (
        len(pipeline_publish_arguments) == 8 and
        (partial_source_join_audited or
         named_source_owner_expression and
         named_source_owner_contract_audited) and
        not inline_default_input and
        not inline_constructed_input)
    return {
        "selectedReads": list(readiness),
        "readinessBits": readiness,
        "sourceEquations": equations,
        "defaultRuntimeFailsClosed": (
            default_unresolved_inputs_are_not_ready and
            owner_tracks_validated_readiness),
        "sourceOwnedInputContractComplete": complete,
        "runtimeSourceInputConnection": {
            "argumentCount": len(pipeline_publish_arguments),
            "sourceInputExpression": source_input_expression,
            "inlineDefaultRejected": inline_default_input,
            "inlineConstructorRejected": inline_constructed_input,
            "namedSourceInputExpression": named_source_input_expression,
            "namedSourceOwnerExpression": named_source_owner_expression,
            "namedSourceOwnerContractAudited":
                named_source_owner_contract_audited,
            "partialFactoryAudited": partial_factory_audited,
            "sourceClosedManualExposureReturnAudited":
                source_closed_manual_exposure_return_audited,
            "sourceClosedManualExposureGateAudited":
                source_closed_manual_exposure_gate_audited,
            "exposureLaneAudited": exposure_lane_audited,
            "vfxLiveLabCarrierLaneAudited": vfx_lab_carrier_lane_audited,
            "uniqueAssignmentShapesAudited": assignment_shapes_audited,
            "assignmentOrderAudited": assignment_order_audited,
            "partialPipelineJoinAudited": partial_pipeline_join_audited,
            "partialSourceJoinAudited": partial_source_join_audited,
            "m27GlobalMipBiasSource": mip_bias_source_contract,
        },
        "runtimeReadConnections": runtime_read_connections,
        "populatedSelectedReads": [
            register for register, connected in runtime_read_connections.items()
            if connected
        ],
        "explicitInputsReachRuntimePublisher": explicit_inputs_reach_runtime,
        "allSelectedReadsRuntimeSourcePopulated": (
            complete and explicit_inputs_reach_runtime and
            all(runtime_read_connections.values())),
        "runtimeSourceSemantics": {
            "c27.y": "source_closed_manual_profile_only",
            "c103.xyzw": (
                "live_lab_actor_root_and_time_carrier; "
                "retail_selected_frame_HGVFX_player_identity_unproven"),
        },
        "capturedValuesAuthorized": False,
    }


def _validate_b3_material_contract(
        mapping: dict[str, Any],
        material_json: dict[str, Any],
        draw: dict[str, Any],
        shell_text: str) -> dict[str, Any]:
    """Join exact PS b3 reads to authored material values and live bytes.

    The captured constant buffer authenticates the join only. Runtime binding
    continues to use Material properties and texture scale/offset state.
    """
    fields = [
        row for row in mapping.get("constantBuffers", {})
        .get("fragmentFieldMapping", [])
        if row.get("buffer") == "UnityPerMaterial"
    ]
    saved = material_json.get("m_SavedProperties", {})
    floats = saved.get("m_Floats", {})
    colors = saved.get("m_Colors", {})
    tex_envs = saved.get("m_TexEnvs", {})
    b3 = _find(draw.get("constantBuffers", []), stage=4, slot=3)
    _require(b3.get("rangeValid") is True and
             b3.get("metadataValid") is True and
             b3.get("truncated") is False and
             b3.get("capturedConstants", 0) >= 31,
             "selected M27 PS b3 range is not fully captured")
    try:
        payload = bytes.fromhex(str(b3.get("dataHex", "")))
    except ValueError as exc:
        raise VerificationError("selected M27 PS b3 dataHex is invalid") from exc
    _require(len(payload) == b3.get("capturedConstants") * 16,
             "selected M27 PS b3 byte count drifted")

    used_words: list[dict[str, Any]] = []
    source_field_names: set[str] = set()
    unmapped: list[str] = []
    for register, lanes in B3_READ_LANES:
        for lane in lanes:
            lane_index = LANE_INDEX[lane]
            byte_offset = register * 16 + lane_index * 4
            matches = [
                row for row in fields
                if isinstance(row.get("offsetBytes"), int) and
                isinstance(row.get("sizeBytes"), int) and
                row["offsetBytes"] <= byte_offset <
                row["offsetBytes"] + row["sizeBytes"]
            ]
            if len(matches) != 1:
                unmapped.append(f"c{register}.{lane}")
                continue
            field = matches[0]
            name = str(field.get("name", ""))
            field_offset = int(field["offsetBytes"])
            size_bytes = int(field["sizeBytes"])
            _require(field_offset % 4 == 0 and size_bytes in (4, 16),
                     f"selected M27 b3 field layout drifted for {name}")
            component = (byte_offset - field_offset) // 4
            source_kind: str
            if name.endswith("_ST"):
                texture_name = name[:-3]
                tex_env = tex_envs.get(texture_name, {})
                scale = tex_env.get("m_Scale", {})
                offset = tex_env.get("m_Offset", {})
                values = [
                    scale.get("X"), scale.get("Y"),
                    offset.get("X"), offset.get("Y"),
                ]
                _require(all(value is not None for value in values),
                         f"authored texture ST is missing for {name}")
                expected_word = _float_word(values[component])
                source_kind = "material_texenv_st"
            elif name in colors:
                value = colors[name]
                components = [
                    value.get("r"), value.get("g"),
                    value.get("b"), value.get("a"),
                ]
                _require(all(item is not None for item in components),
                         f"authored color is incomplete for {name}")
                expected_word = _float_word(components[component])
                source_kind = "material_color"
            elif name == "_ParallaxMarchNum":
                value = floats.get(name)
                _require(value is not None and float(value).is_integer() and
                         0 <= int(value) <= 0xFFFFFFFF,
                         "authored _ParallaxMarchNum is not an exact uint")
                expected_word = int(value)
                source_kind = "material_float_to_uint"
            else:
                _require(name in floats and component == 0,
                         f"authored scalar is missing for {name}")
                expected_word = _float_word(floats[name])
                source_kind = "material_float"
            observed_word = struct.unpack_from("<I", payload, byte_offset)[0]
            _require(observed_word == expected_word,
                     f"selected M27 b3 word mismatch at c{register}.{lane} "
                     f"({name}): expected 0x{expected_word:08x}, "
                     f"observed 0x{observed_word:08x}")
            source_field_names.add(name)
            used_words.append({
                "register": register,
                "lane": lane,
                "byteOffset": byte_offset,
                "field": name,
                "fieldComponent": component,
                "sourceKind": source_kind,
                "expectedWord": f"0x{expected_word:08x}",
                "observedWord": f"0x{observed_word:08x}",
                "bitExact": True,
            })

    _require(not unmapped, "selected M27 b3 has unmapped used words: " +
             ", ".join(unmapped))
    _require(len(used_words) == 50 and len(source_field_names) == 37,
             "selected M27 b3 read/field coverage drifted")

    for name in sorted(source_field_names):
        field = _find(fields, name=name)
        offset = int(field["offsetBytes"])
        register = offset // 16
        lane = "xyzw"[(offset % 16) // 4]
        if int(field["sizeBytes"]) == 16:
            declaration = f"float4 {name} : packoffset(c{register});"
        else:
            scalar_type = "uint" if name == "_ParallaxMarchNum" else "float"
            declaration = (
                f"{scalar_type} {name} : packoffset(c{register}.{lane});")
        _require(declaration in shell_text,
                 f"generative shell b3 declaration drifted for {name}")

        if name.endswith("_ST"):
            texture_name = name[:-3]
            _require(f"{texture_name} (" in shell_text,
                     f"generative shell texture property is missing for {name}")
            continue
        if name in colors:
            match = re.search(
                rf"\b{re.escape(name)}\s+\(\"\",\s*Color\)\s*=\s*\(([^)]*)\)",
                shell_text)
            _require(match is not None,
                     f"generative shell color default is missing for {name}")
            shell_values = [float(value.strip())
                            for value in match.group(1).split(",")]
            authored = colors[name]
            authored_values = [
                authored["r"], authored["g"], authored["b"], authored["a"]]
            _require(len(shell_values) == 4 and all(
                _float_word(actual) == _float_word(expected)
                for actual, expected in zip(shell_values, authored_values)),
                f"generative shell color default drifted for {name}")
            continue
        match = re.search(
            rf"\b{re.escape(name)}\s+\(\"\",\s*(Float|Integer)\)\s*=\s*"
            rf"([-+0-9.eE]+)",
            shell_text)
        _require(match is not None,
                 f"generative shell scalar default is missing for {name}")
        expected_kind = "Integer" if name == "_ParallaxMarchNum" else "Float"
        _require(match.group(1) == expected_kind,
                 f"generative shell scalar type drifted for {name}")
        if expected_kind == "Integer":
            default_matches = int(float(match.group(2))) == int(floats[name])
        else:
            default_matches = (
                _float_word(match.group(2)) == _float_word(floats[name]))
        _require(default_matches,
                 f"generative shell scalar default drifted for {name}")

    return {
        "shaderStage": "pixel",
        "bufferSlot": 3,
        "logicalName": "UnityPerMaterial",
        "sourceMaterial": material_json.get("Name"),
        "usedWordCount": len(used_words),
        "mappedFieldCount": len(source_field_names),
        "bitExactMatches": sum(row["bitExact"] for row in used_words),
        "unmappedUsedWords": unmapped,
        "capturedPayloadUsedAtRuntime": False,
        "usedWords": used_words,
    }


def _validate_runtime_b3_material_source(
        mapping: dict[str, Any],
        material_json: dict[str, Any],
        runtime_material_text: str,
        compatibility_shader_text: str) -> dict[str, Any]:
    """Validate the generated Material values actually copied at runtime."""
    _require("m_Name: M_fx_endminm_gfx_27" in runtime_material_text,
             "runtime M27 material identity drifted")
    property_names = set(re.findall(
        r"^\s*(?:\[[^]]+\]\s*)?(_[A-Za-z0-9_]+)\s+\(",
        compatibility_shader_text,
        re.MULTILINE))
    fields = [
        row for row in mapping.get("constantBuffers", {})
        .get("fragmentFieldMapping", [])
        if row.get("buffer") == "UnityPerMaterial"
    ]
    field_names = {str(row.get("name", "")) for row in fields}
    saved = material_json.get("m_SavedProperties", {})
    floats = saved.get("m_Floats", {})
    colors = saved.get("m_Colors", {})
    tex_envs = saved.get("m_TexEnvs", {})
    yaml_scalars = {
        match.group(1): float(match.group(2))
        for match in re.finditer(
            r"^\s+- (_[A-Za-z0-9_]+):\s*([-+0-9.eE]+)\s*$",
            runtime_material_text,
            re.MULTILINE)
    }
    yaml_colors: dict[str, list[float]] = {}
    for match in re.finditer(
            r"^\s+- (_[A-Za-z0-9_]+):\s*\{r:\s*([-+0-9.eE]+),\s*"
            r"g:\s*([-+0-9.eE]+),\s*b:\s*([-+0-9.eE]+),\s*"
            r"a:\s*([-+0-9.eE]+)\}\s*$",
            runtime_material_text,
            re.MULTILINE):
        yaml_colors[match.group(1)] = [
            float(match.group(index)) for index in range(2, 6)]

    records: list[dict[str, Any]] = []
    for name in sorted(field_names):
        if name.endswith("_ST"):
            texture_name = name[:-3]
            if texture_name not in property_names:
                continue
            number = r"([-+0-9.eE]+)"
            match = re.search(
                rf"^\s+- {re.escape(texture_name)}:\s*\r?\n"
                rf"\s+m_Texture:.*\r?\n"
                rf"\s+m_Scale:\s*\{{x:\s*{number},\s*y:\s*{number}\}}\s*\r?\n"
                rf"\s+m_Offset:\s*\{{x:\s*{number},\s*y:\s*{number}\}}",
                runtime_material_text,
                re.MULTILINE)
            _require(match is not None,
                     f"runtime M27 material ST is missing for {texture_name}")
            actual = [float(match.group(index)) for index in range(1, 5)]
            tex_env = tex_envs.get(texture_name, {})
            expected = [
                tex_env.get("m_Scale", {}).get("X"),
                tex_env.get("m_Scale", {}).get("Y"),
                tex_env.get("m_Offset", {}).get("X"),
                tex_env.get("m_Offset", {}).get("Y"),
            ]
            _require(all(value is not None for value in expected) and all(
                _float_word(left) == _float_word(right)
                for left, right in zip(actual, expected)),
                f"runtime M27 material ST drifted for {texture_name}")
            records.append({"property": name, "source": "generated_mat_texenv"})
            continue
        if name not in property_names:
            continue
        if name in colors:
            actual = yaml_colors.get(name)
            if actual is None:
                default = re.search(
                    rf"\b{re.escape(name)}\s+\(\"[^\"]*\",\s*Color\)\s*=\s*"
                    rf"\(([^)]*)\)",
                    compatibility_shader_text)
                _require(default is not None,
                         f"runtime source shader color default is missing for {name}")
                actual = [float(value.strip())
                          for value in default.group(1).split(",")]
            authored = colors[name]
            expected = [
                authored["r"], authored["g"], authored["b"], authored["a"]]
            _require(len(actual) == 4 and all(
                _float_word(left) == _float_word(right)
                for left, right in zip(actual, expected)),
                f"runtime M27 material color drifted for {name}")
            records.append({"property": name, "source": "generated_mat_color"})
            continue
        if name in floats:
            actual_scalar = yaml_scalars.get(name)
            if actual_scalar is None:
                default = re.search(
                    rf"\b{re.escape(name)}\s+\(\"[^\"]*\",\s*"
                    rf"(?:Float|Integer)\)\s*=\s*([-+0-9.eE]+)",
                    compatibility_shader_text)
                _require(default is not None,
                         f"runtime source shader scalar default is missing for {name}")
                actual_scalar = float(default.group(1))
            _require(_float_word(actual_scalar) == _float_word(floats[name]),
                     f"runtime M27 material scalar drifted for {name}")
            if name == "_ParallaxMarchNum":
                _require(float(actual_scalar).is_integer() and
                         0 <= int(actual_scalar) <= 0x7FFFFFFF,
                         "runtime _ParallaxMarchNum is not an exact uint")
            records.append({"property": name, "source": "generated_mat_float"})

    _require({row["property"] for row in records} == {
        "_BaseColor", "_BaseColorMap_ST", "_NormalMap_ST",
        "_ParallaxColor", "_ParallaxIntensity", "_ParallaxMarchNum",
        "_ParallaxMinBrightness", "_ParallaxStrength", "_ParallaxTilling",
    }, "runtime M27 material selected b3 override coverage drifted")
    return {
        "name": "M_fx_endminm_gfx_27",
        "selectedB3OverrideCount": len(records),
        "allEffectiveOverridesMatchOriginalMaterial": True,
        "capturedPayloadUsedAtRuntime": False,
        "properties": records,
    }


def _validate_static(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    particle_path = repo / "reports/assets/character_recovery/endminf_m27_particle_abi.json"
    probe_path = repo / "reports/assets/character_recovery/endminf_m27_particle_abi_unity_probe.json"
    state_path = repo / "reports/assets/character_recovery/endminf_m27_fixed_state_capture_latest.json"
    frame_path = repo / (
        "scratch/reverse_engineering/endfield_capture/20260829T224523Z/"
        "graphics/frames/2344/metadata.json")
    texture_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
        "OriginalData/RenderParameters/endminf_liteffect_native_texture_payload_contract.json")
    mapping_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
        "Characters/Playable/Endminf/ExternalUiEffects/"
        "endminf_liteffect_resource_mapping.json")
    registry_path = repo / (
        "unity_endfield_graph_shader_lab/tools/original_dxbc_exact/"
        "M27SubstitutionRegistry.h")
    native_observer_path = repo / (
        "unity_endfield_graph_shader_lab/tools/original_dxbc_exact/"
        "OriginalDxbcSwapPlugin.cpp")
    generative_pin_path = repo / (
        "reports/assets/character_recovery/"
        "endminf_m27_generative_shell_pin.json")
    packet_shell_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/"
        "Diagnostics/EndfieldEndminfM27ExactAbiShell.shader")
    shell_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/"
        "Diagnostics/EndfieldEndminfM27GenerativeExactAbiShell.shader")
    terrain_contract_path = repo / (
        "reports/assets/character_recovery/"
        "endminf_m27_terrain_profile_native_contract.json")
    terrain_publisher_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredTerrainSubsurfaceConstants.cs")
    compatibility_binding_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldEndminfLitEffectCompatibilityBinding.cs")
    shell_observer_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/"
        "CharacterRecovery/EndfieldM27ShellHashCapture.cs")
    material_json_path = repo / (
        "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/"
        "Material/M_fx_endminm_gfx_27_pA531A88850690EB8.json")
    runtime_material_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
        "Characters/Playable/Endminf/Effects/Overview/Materials/"
        "M_fx_endminm_gfx_27_pA531A88850690EB8.mat")
    compatibility_shader_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/"
        "Recovered/EndfieldEndminfLitEffectVisualCompatibility.shader")
    compatibility_shader_meta_path = Path(str(compatibility_shader_path) + ".meta")
    b0_source_contract_path = repo / (
        "reports/assets/character_recovery/"
        "endminf_m27_b0_source_contract.json")
    transform_contract_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredDeferredTransformVariablesContract.cs")
    transform_owner_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredDeferredTransformVariables.cs")
    global_contract_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredShaderVariablesGlobalContract.cs")
    global_owner_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredShaderVariablesGlobal.cs")
    m27_mip_bias_source_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredM27GlobalMipBiasSource.cs")
    frame_runtime_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredDeferredGBufferFrame.cs")
    generative_runtime_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredEndminfM27GenerativeExactRuntime.cs")
    pipeline_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/HGCompatRenderPipeline.cs")
    binding_policy_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredDeferredResolverBindingPolicy.cs")

    paths = [
        particle_path, probe_path, state_path, frame_path, texture_path,
        mapping_path, registry_path, native_observer_path, generative_pin_path,
        packet_shell_path,
        shell_path,
        terrain_contract_path, terrain_publisher_path,
        compatibility_binding_path, shell_observer_path, material_json_path,
        runtime_material_path, compatibility_shader_path,
        compatibility_shader_meta_path, b0_source_contract_path,
        transform_contract_path,
        transform_owner_path, global_contract_path, global_owner_path,
        m27_mip_bias_source_path,
        frame_runtime_path, generative_runtime_path, pipeline_path,
        binding_policy_path,
    ]
    for path in paths:
        _require(path.is_file(), f"required source is missing: {path}")

    particle = _read_json(particle_path)
    selected = particle.get("selectedRetailProgram", {})
    _require(particle.get("schema") == "endfield.endminf-m27-particle-abi.v3",
             "particle ABI schema drifted")
    _require(selected.get("subProgramIndex") == 113,
             "selected retail subprogram is not 113")
    programs = selected.get("programs", [])
    _require(_find(programs, stage="vertex").get("sha256") == VS_SHA256,
             "exact M27 vertex DXBC identity drifted")
    _require(_find(programs, stage="fragment").get("sha256") == PS_SHA256,
             "exact M27 pixel DXBC identity drifted")

    probe = _read_json(probe_path)
    _require(probe.get("status") == "ok", "Unity PSR source probe is not ok")
    _require(probe.get("rendererPathId") == RENDERER_PATH_ID,
             "Unity PSR renderer PathID drifted")
    _require(probe.get("hierarchy") == HIERARCHY,
             "Unity PSR hierarchy drifted")
    _require(probe.get("renderMode") == "Mesh",
             "Unity source renderer is not a mesh ParticleSystemRenderer")
    _require(probe.get("activeVertexStreams") == ACTIVE_STREAMS,
             "Unity PSR active vertex streams drifted")
    _require(probe.get("exactMeshVertexCount") == 29,
             "source mesh vertex count drifted")

    state = _read_json(state_path)
    _require(state.get("status") == "validated_exact_m27_liteffect_fixed_state",
             "globally gated M27 fixed-state report is not validated")
    _require(state.get("shaderPair", {}).get("vertexIdentity") == VS_IDENTITY,
             "fixed-state VS identity drifted")
    _require(state.get("shaderPair", {}).get("pixelIdentity") == PS_IDENTITY,
             "fixed-state PS identity drifted")
    state_strides = sorted({row.get("vertexStride") for row in state.get("draws", [])})
    _require(state_strides and set(state_strides).issubset(set(ALLOWED_IA_STRIDES)),
             "retail IA stride is outside the recovered 60/68-byte set")

    frame = _read_json(frame_path)
    _require(frame.get("captureIncomplete") is False and
             frame.get("captureFailed") is False and
             frame.get("droppedEvents") == 0,
             "pinned graphics frame is incomplete")
    draw = _find(
        frame.get("drawRecords", []),
        priorityShaderPair=True,
        priorityM27Geometry=True)
    _require(draw.get("count") == 1080 and
             draw.get("instanceCount") == 1 and
             draw.get("startInstance") == 0,
             "selected M27 particle geometry/range drifted")
    shader_rows = draw.get("shaders", [])
    _require(_find(shader_rows, stage=0).get("identityHash") == int(VS_IDENTITY, 16),
             "pinned draw VS identity drifted")
    _require(_find(shader_rows, stage=4).get("identityHash") == int(PS_IDENTITY, 16),
             "pinned draw PS identity drifted")
    target = draw.get("pipelineState", {}).get("target", {})
    depth = draw.get("pipelineState", {}).get("depthTarget", {})
    for key, expected in TARGET.items():
        _require(target.get(key) == expected,
                 f"five-MRT descriptor drifted at {key}")
    for key, expected in DEPTH_TARGET.items():
        _require(depth.get(key) == expected,
                 f"depth descriptor drifted at {key}")

    texture = _read_json(texture_path)
    _require(texture.get("schema") == "endfield.native-texture-payload-contract.v2" and
             texture.get("status") == "source_closed_current_build",
             "native full-mip texture contract is not source-closed")
    texture_rows = texture.get("textures", [])
    selected_resources = frame.get("selectedResourceRecords", [])
    draw_resources = draw.get("resources", [])
    material_json = _read_json(material_json_path)
    tex_envs = (material_json.get("m_SavedProperties", {})
                .get("m_TexEnvs", {}))
    texture_contract: list[dict[str, Any]] = []
    for slot, prop, width, height, dxgi, mips, payload_sha in TEXTURE_SLOTS:
        row = _find(texture_rows, property=prop)
        payload_path = (repo / "unity_endfield_graph_shader_lab" /
                        row.get("payloadAssetPath", ""))
        _require(payload_path.is_file(), f"native payload missing for {prop}")
        _require(row.get("width") == width and row.get("height") == height and
                 row.get("dxgiFormat") == dxgi and row.get("mipCount") == mips,
                 f"native descriptor drifted for {prop}")
        _require(str(row.get("payloadSha256", "")).lower() == payload_sha and
                 _sha256(payload_path) == payload_sha,
                 f"native full-mip payload hash drifted for {prop}")
        resource = _find(draw_resources, kind=3, stage=4, slot=slot)
        selected_resource = _find(
            selected_resources, captureKind=3, stage=4, slot=slot,
            objectId=resource.get("objectId"))
        mip0 = row.get("mipLayout", [{}])[0]
        _require(selected_resource.get("width") == width and
                 selected_resource.get("height") == height and
                 selected_resource.get("format") == dxgi and
                 selected_resource.get("viewFormat") == dxgi and
                 selected_resource.get("byteSize") == mip0.get("byteSize"),
                 f"active subprogram-113 t{slot} descriptor does not match {prop}")
        texture_contract.append({
            "slot": slot,
            "property": prop,
            "width": width,
            "height": height,
            "dxgiFormat": dxgi,
            "mipCount": mips,
            "payloadSha256": payload_sha,
            "payloadBytes": row.get("payloadSize"),
            "fullMipChainRequired": True,
        })

    null_resource_ids: list[int] = []
    for slot, prop in SERIALIZED_NULL_TEXTURE_SLOTS:
        resource = _find(draw_resources, kind=3, stage=4, slot=slot)
        texture_value = tex_envs.get(prop, {}).get("m_Texture", {})
        _require(resource.get("objectId") and resource.get("byteSize") == 0,
                 f"selected M27 t{slot} is not the null/default resource")
        _require(texture_value.get("IsNull") is True and
                 texture_value.get("m_FileID") == 0 and
                 texture_value.get("m_PathID") == 0,
                 f"serialized M27 source texture {prop} is no longer null")
        null_resource_ids.append(resource.get("objectId"))
        texture_contract.append({
            "slot": slot,
            "property": prop,
            "serializedNull": True,
            "shaderDefault": "black",
            "selectedDrawObjectId": resource.get("objectId"),
        })
    _require(len(set(null_resource_ids)) == 1,
             "selected M27 t4/t5 no longer share one null/default resource")

    mapping = _read_json(mapping_path)
    _require(mapping.get("schema") == "endfield.endminf-liteffect-resource-mapping.v1",
             "LitEffect resource mapping schema drifted")
    fragment_mapping = mapping.get("constantBuffers", {}).get("fragment", [])
    b3 = _find(fragment_mapping, register=3)
    b4 = _find(fragment_mapping, register=4)
    _require(b3.get("logicalName") == "UnityPerMaterial" and
             b3.get("sizeBytes") == 496 and
             b3.get("status") == "resolved_cross_platform_register",
             "recovered b3 identity drifted")
    _require(b4.get("logicalName") == "_TerrainSubsurfaceConstants" and
             b4.get("sizeBytes") == 16 and
             b4.get("status") == "resolved_cross_platform_register",
             "recovered b4 identity drifted")
    b4_field = _find(
        mapping.get("constantBuffers", {}).get("fragmentFieldMapping", []),
        buffer="_TerrainSubsurfaceConstants",
        name="_TerrainSubsurfaceProfileInt")
    _require(b4_field.get("register") == 4 and
             b4_field.get("offsetBytes") == 12 and
             b4_field.get("registerOffsetBytes") == 12 and
             b4_field.get("sizeBytes") == 4,
             "recovered b4 c0.w field layout drifted")

    terrain_contract = _read_json(terrain_contract_path)
    _require(terrain_contract.get("schema") == TERRAIN_NATIVE_CONTRACT_SCHEMA and
             terrain_contract.get("status") ==
             "producer_semantics_closed_selected_charinfo_value_open",
             "terrain profile native producer contract drifted")
    terrain_publisher_text = terrain_publisher_path.read_text(encoding="utf-8")
    for marker in (
        TERRAIN_NATIVE_CONTRACT_SCHEMA,
        TERRAIN_SELECTED_FRAME_SCHEMA,
        'Shader.PropertyToID("_TerrainSubsurfaceProfileInt")',
        "command.SetGlobalFloat(",
        "incomplete captures and an empty lab registry",
    ):
        _require(marker in terrain_publisher_text,
                 f"terrain profile publisher drifted: {marker}")

    registry_text = registry_path.read_text(encoding="utf-8")
    registry_compact = "".join(registry_text.split())
    for digest in (
        SHELL_VS_SHA256,
        SHELL_PS_SHA256,
        GENERATIVE_SHELL_VS_SHA256,
        GENERATIVE_SHELL_PS_SHA256,
    ):
        byte_tokens = ",".join(f"0x{digest[i:i+2]}" for i in range(0, 64, 2))
        _require(byte_tokens in registry_compact,
                 f"compiler-substitution shell registry lost {digest}")
    packet_shell_text = packet_shell_path.read_text(encoding="utf-8")
    _require("float4 _M27CB0[82]" in packet_shell_text and
             "float4 _M27CB4[1]" in packet_shell_text,
             "immutable packet shell was not preserved")

    native_observer_text = native_observer_path.read_text(encoding="utf-8")
    for marker in (
        "SubstitutionRoute::M27ObserveOnly",
        "EndfieldOriginalDxbcSetM27ObservationArmed",
        "ObserveD3D11Declarations",
        "dcl_resource",
        "g_m27ObservationEpoch",
        "TryArmCompilerRouteLocked",
        "TryDisarmCompilerRouteLocked",
        "expectedRoute",
    ):
        _require(marker in native_observer_text,
                 f"native M27 observer contract drifted: {marker}")

    shell_text = shell_path.read_text(encoding="utf-8")
    for declaration in (
        "cbuffer _TransformVariables : register(b0)",
        "float4 _M27TransformValues[82]",
        "cbuffer ShaderVariablesGlobal : register(b1)",
        "float4 _M27GlobalValues[106]",
        "cbuffer UnityPerDraw : register(b2)",
        "float4 _M27UnityPerDrawValues[4091]",
        "cbuffer UnityPerMaterial : register(b3)",
        "cbuffer _TerrainSubsurfaceConstants : register(b4)",
        "Texture2D<float4> _BaseColorMap : register(t0)",
        "Texture2D<float4> _NormalMap : register(t1)",
        "Texture2D<float4> _MROMap : register(t2)",
        "Texture2D<float4> _ParallaxMap : register(t3)",
        "Texture2D<float4> _ParallaxMaskMap : register(t4)",
        "Texture2D<float4> _ParallaxNoiseMap : register(t5)",
        "SamplerState sampler_ParallaxMaskMap : register(s4)",
        "SamplerState sampler_ParallaxNoiseMap : register(s5)",
        "StructuredBuffer<float4> _VertexSkinMatrices : register(t0)",
        '"DisableBatching" = "True"',
        "ZTest GEqual", "ZWrite On", "Cull Back",
        "float4 target4 : SV_Target4",
    ):
        _require(declaration in shell_text,
                 f"M27 exact ABI shell drifted: {declaration}")
    _require("Retail PS DXBC declares and reads all six slots" in shell_text,
             "generative shell lost the retail six-texture source boundary")
    b3_material_contract = _validate_b3_material_contract(
        mapping,
        material_json,
        draw,
        shell_text)
    runtime_material_text = runtime_material_path.read_text(encoding="utf-8")
    compatibility_shader_text = compatibility_shader_path.read_text(
        encoding="utf-8")
    compatibility_shader_meta_text = compatibility_shader_meta_path.read_text(
        encoding="utf-8")
    shader_guid = re.search(
        r"^guid:\s*([0-9a-f]{32})\s*$",
        compatibility_shader_meta_text,
        re.MULTILINE)
    _require(shader_guid is not None and
             f"guid: {shader_guid.group(1)}" in runtime_material_text,
             "runtime M27 material compatibility shader identity drifted")
    runtime_b3_material_source = _validate_runtime_b3_material_source(
        mapping,
        material_json,
        runtime_material_text,
        compatibility_shader_text)
    runtime_b3_material_source["path"] = (
        runtime_material_path.relative_to(repo).as_posix())
    runtime_b3_material_source["sha256"] = _sha256(runtime_material_path)

    b0_source_contract = _read_json(b0_source_contract_path)
    _require(b0_source_contract.get("schema") ==
             "endfield.endminf-m27-b0-source-contract.v1" and
             b0_source_contract.get("status") ==
             "source_closed_runtime_values_not_captured" and
             b0_source_contract.get("selectedDrawValidation", {})
             .get("capturedPayloadUsedAtRuntime") is False,
             "M27 b0 source contract is not closed")
    b0_program = b0_source_contract.get("exactProgram", {})
    _require(b0_program.get("subProgramIndex") == 113 and
             b0_program.get("vertex", {}).get("sha256") == VS_SHA256 and
             b0_program.get("pixel", {}).get("sha256") == PS_SHA256 and
             b0_program.get("vertex", {}).get("b0Reads") == {
                 "32": "xyzw", "33": "xyzw", "34": "xyzw",
                 "35": "xyzw", "44": "xyz", "57": "xyw",
                 "58": "xyw", "59": "xyw", "60": "xyw", "81": "xyz",
             } and
             b0_program.get("pixel", {}).get("b0Reads") == {
                 "0": "z", "1": "z", "2": "z", "24": "xyzw",
                 "25": "xyzw", "26": "xyzw", "27": "xyzw",
                 "44": "xyz",
             } and
             b0_program.get("pixel", {}).get("b3Reads") == {
                 str(register): lanes for register, lanes in B3_READ_LANES
             },
             "M27 b0 exact DXBC read inventory drifted")
    b0_sources = b0_source_contract.get("sources", {})
    for key, path in (
            ("contract", transform_contract_path),
            ("owner", transform_owner_path),
            ("pipeline", pipeline_path)):
        _require(b0_sources.get(key, {}).get("sha256") == _sha256(path),
                 f"M27 b0 source contract is stale at {key}")
    _require(b0_source_contract.get("selectedDrawValidation", {})
             .get("source", {}).get("sha256") == _sha256(frame_path),
             "M27 b0 selected-draw validation source drifted")

    generative_pin = _read_json(generative_pin_path)
    _require(generative_pin.get("schema") == GENERATIVE_SHELL_PIN_SCHEMA and
             generative_pin.get("status") ==
             "independently_pinned_d3d11_callback",
             "generative M27 shell pin report is not validated")
    _require(generative_pin.get("shaderAsset") ==
             shell_path.relative_to(repo / "unity_endfield_graph_shader_lab")
             .as_posix() and
             generative_pin.get("shaderSourceSha256") == _sha256(shell_path),
             "generative M27 pin source identity drifted")
    shell_pin = generative_pin.get("shell", {})
    _require(shell_pin.get("vertexSha256") == GENERATIVE_SHELL_VS_SHA256 and
             shell_pin.get("pixelSha256") == GENERATIVE_SHELL_PS_SHA256,
             "generative M27 shell hashes drifted")
    raw_observations = generative_pin.get("rawObservations", [])
    _require(len(raw_observations) == 2 and
             len({row.get("source") for row in raw_observations}) == 2,
             "generative M27 shell requires two independent raw observations")
    for row in raw_observations:
        _require(row.get("schema") == GENERATIVE_SHELL_OBSERVATION_SCHEMA and
                 row.get("status") == "observed_unpinned_fail_closed" and
                 row.get("shaderSourceSha256") == _sha256(shell_path) and
                 row.get("vertexShellSha256") ==
                 GENERATIVE_SHELL_VS_SHA256 and
                 row.get("pixelShellSha256") ==
                 GENERATIVE_SHELL_PS_SHA256 and
                 row.get("vertexAbiMatchCount") == 1 and
                 row.get("pixelAbiMatchCount") == 1 and
                 row.get("setPassActivated") is True and
                 row.get("vertexSwapCount") == 0 and
                 row.get("pixelSwapCount") == 0 and
                 row.get("failureCount") == 0 and
                 _is_sha256(row.get("reportSha256")),
                 "generative M27 raw shell observation drifted")
        raw_source = repo / str(row.get("source", ""))
        if raw_source.is_file():
            _require(_sha256(raw_source) == row.get("reportSha256"),
                     "generative M27 raw observation file hash drifted")
    pin_validation = generative_pin.get("substitutionValidation", {})
    _require(pin_validation.get("schema") == GENERATIVE_SHELL_PIN_SCHEMA and
             pin_validation.get("status") ==
             "independently_pinned_d3d11_callback" and
             pin_validation.get("shaderSourceSha256") == _sha256(shell_path) and
             pin_validation.get("vertexShellSha256") ==
             GENERATIVE_SHELL_VS_SHA256 and
             pin_validation.get("pixelShellSha256") ==
             GENERATIVE_SHELL_PS_SHA256 and
             pin_validation.get("vertexAbiMatchCount") == 1 and
             pin_validation.get("pixelAbiMatchCount") == 1 and
             pin_validation.get("setPassActivated") is True and
             pin_validation.get("vertexSwapCount", 0) > 0 and
             pin_validation.get("pixelSwapCount", 0) > 0 and
             pin_validation.get("failureCount") == 0 and
             _is_sha256(pin_validation.get("reportSha256")),
             "generative M27 stage+SHA substitution validation drifted")
    pin_source = repo / str(pin_validation.get("source", ""))
    if pin_source.is_file():
        _require(_sha256(pin_source) == pin_validation.get("reportSha256"),
                 "generative M27 pin validation file hash drifted")

    transform_contract = transform_contract_path.read_text(encoding="utf-8")
    transform_owner = transform_owner_path.read_text(encoding="utf-8")
    global_contract = global_contract_path.read_text(encoding="utf-8")
    global_owner = global_owner_path.read_text(encoding="utf-8")
    m27_mip_bias_source = m27_mip_bias_source_path.read_text(encoding="utf-8")
    _require("public const int SizeBytes = 1312;" in transform_contract and
             "public const int VectorCount = 82;" in transform_contract and
             "EndfieldRecoveredDeferredTransformVariablesContract.SizeBytes" in transform_owner,
             "full _TransformVariables publisher contract drifted")
    _require("public const int SizeBytes = 3200;" in global_contract and
             "public const int VectorCount = 200;" in global_contract and
             "EndfieldRecoveredShaderVariablesGlobalContract.SizeBytes" in global_owner,
             "full ShaderVariablesGlobal publisher contract drifted")

    saved = material_json.get("m_SavedProperties", {})
    floats = saved.get("m_Floats", {})
    colors = saved.get("m_Colors", {})
    _require(material_json.get("Name") == "M_fx_endminm_gfx_27" and
             floats.get("_ParallaxMarchNum") == 5.0 and
             floats.get("_ParallaxStrength") == 0.096 and
             colors.get("_BaseColor", {}).get("a") == 1.0 and
             colors.get("_ParallaxColor", {}).get("r") == 964.7226,
             "original M27 material source values drifted")

    runtime_text = frame_runtime_path.read_text(encoding="utf-8")
    packet_texture_binding = (
        'destination.SetTexture("_M27T0", Texture2D.blackTexture);' in runtime_text and
        '"_ParallaxMap",\n                "_NormalMap",\n                "_MROMap",\n                "_BaseColorMap",' in runtime_text
    )
    packet_captured_arrays = "CreateConstantBufferValues()" in runtime_text
    packet_issue = "EndfieldRecoveredEndminfM27ExactRuntime.Issue(command)" in runtime_text
    generative_text = generative_runtime_path.read_text(encoding="utf-8")
    pipeline_text = pipeline_path.read_text(encoding="utf-8")
    binding_policy_text = binding_policy_path.read_text(encoding="utf-8")
    frame_runtime_text = frame_runtime_path.read_text(encoding="utf-8")
    runtime_source_connections = _validate_runtime_source_connections(
        pipeline_text,
        frame_runtime_text)
    b1_source_contract = _validate_b1_source_contract(
        global_contract,
        global_owner,
        pipeline_text,
        m27_mip_bias_source)
    compatibility_text = compatibility_binding_path.read_text(encoding="utf-8")
    shell_observer_text = shell_observer_path.read_text(encoding="utf-8")
    generative_forbidden_packet_data = (
        "CreateConstantBufferValues" in generative_text or
        "IssuePluginEvent" in generative_text or
        "EndfieldRecoveredM27ExactCaptureData" in generative_text)
    generative_texture_slots = all(
        f'"{name}"' in generative_text
        for name in (
            "_BaseColorMap", "_NormalMap", "_MROMap", "_ParallaxMap",
            "_ParallaxMaskMap", "_ParallaxNoiseMap"))
    generative_required_material_destination = (
        'if (!destination.HasProperty(property))' in generative_text and
        'destination.SetTextureScale(' in generative_text and
        'destination.SetTextureOffset(' in generative_text and
        'destination.SetInteger("_ParallaxMarchNum", marchCount)' in
        generative_text)
    full_publishers_connected = (
        "TransformVariablesId" in generative_text and
        "ShaderVariablesGlobalId" in generative_text and
        "EndfieldRecoveredDeferredTransformVariablesContract.SizeBytes" in generative_text and
        "EndfieldRecoveredShaderVariablesGlobalContract.SizeBytes" in generative_text)
    b0_publish_start = pipeline_text.find(
        "if (EndfieldRecoveredDeferredTransformVariables.IsRequested)")
    b0_owner_gate = pipeline_text.find(
        "if (recoveredEndminfLitEffectOwnerActive", b0_publish_start)
    b0_continuous_publish = (
        b0_publish_start >= 0 and b0_owner_gate > b0_publish_start and
        "PrepareAndPublish" in
        pipeline_text[b0_publish_start:b0_owner_gate])
    b0_source_closed = all(marker in transform_contract for marker in (
        "public static readonly int[] M27ReadVectors",
        "nonJitteredGpuProjection * viewNoTranslation",
        "viewProjection.inverse",
        "previousFrameHistoryReady",
        "previousProjection",
        "previousPosition",
        "public static bool TryEvaluateHistory(",
        "history.lastPublishedFrame == frame - 1",
        "public static void CommitHistory(",
    )) and all(marker in transform_owner for marker in (
        ".CameraHistoryState>",
        ".TryEvaluateHistory(",
        "CommitHistory(",
        "history.nonJitteredViewNoTranslationProjection",
        "history.cameraPosition",
        "currentM27SourceReady = true",
        "currentM27SourceReady = false",
    )) and b0_continuous_publish and runtime_source_connections[
        "b0ReadinessReachesExactDraw"] and (
        "EndfieldRecoveredEndminfM27GenerativeExactRuntime" in
        binding_policy_text) and all(marker in generative_text for marker in (
            "bool transformVariablesM27SourceReady",
            "if (!transformVariablesM27SourceReady",
        ))
    engine_per_draw = "cbuffer UnityPerDraw : register(b2)" in shell_text
    b4_fail_closed = (
        "fresh selected-frame value provenance" in generative_text and
        "EndfieldRecoveredTerrainSubsurfaceConstants.PublisherState" in
        generative_text and
        "false,\n                                        false,\n                                        -1," in
        runtime_text)
    generative_draw_renderer = (
        "endminfM27GenerativeExactRuntime.TryBindDraw" in runtime_text and
        "command.DrawRenderer(\n                            endminfM27Renderer" in runtime_text)
    generative_substitution_gate = (
        "bool compilerSubstitutionReady" in generative_text and
        "if (!compilerSubstitutionReady)" in generative_text and
        "endminfM27Material,\n                                    false," in
        runtime_text)
    raw_shell_observer = (
        "RunGenerativeObservation" in shell_observer_text and
        "GenerativeShaderAsset" in shell_observer_text and
        "Native.SetM27SubstitutionArmed(0)" in shell_observer_text and
        "newObservations" in shell_observer_text and
        "RunGenerativePinValidation" in shell_observer_text and
        "value.boundResources == 4u" in shell_observer_text and
        'value.textureSlotMask == "0x00000001"' in shell_observer_text and
        "value.boundResources == 17u" in shell_observer_text and
        'value.textureSlotMask == "0x0000003f"' in shell_observer_text and
        'value.samplerSlotMask == "0x0000003f"' in shell_observer_text)
    selector_enables_retained_renderer = (
        "GenerativeExactM27EnvironmentVariable" in compatibility_text and
        "generativeExactM27" in compatibility_text)

    sources = {path.relative_to(repo).as_posix(): _source(path, repo) for path in paths}
    contract = {
        "shader": {
            "subProgramIndex": 113,
            "vertexSha256": VS_SHA256,
            "pixelSha256": PS_SHA256,
            "vertexIdentity": VS_IDENTITY,
            "pixelIdentity": PS_IDENTITY,
            "immutablePacketShellVertexSha256": SHELL_VS_SHA256,
            "immutablePacketShellPixelSha256": SHELL_PS_SHA256,
            "generativeShellPinSchema": GENERATIVE_SHELL_PIN_SCHEMA,
            "generativeShellVertexSha256": GENERATIVE_SHELL_VS_SHA256,
            "generativeShellPixelSha256": GENERATIVE_SHELL_PS_SHA256,
            "generativeShellPinned": True,
            "generativeShellPinReportSha256": _sha256(generative_pin_path),
        },
        "renderer": {
            "type": "ParticleSystemRenderer",
            "hierarchy": HIERARCHY,
            "rendererPathId": RENDERER_PATH_ID,
            "materialPathId": MATERIAL_PATH_ID,
            "meshPathId": MESH_PATH_ID,
            "activeVertexStreams": ACTIVE_STREAMS,
        },
        "inputAssembler": {"allowedVertexStrides": ALLOWED_IA_STRIDES},
        "fiveMrtDescriptor": TARGET,
        "selectedMaterialB3": b3_material_contract,
        "runtimeMaterialB3Source": runtime_b3_material_source,
        "runtimeSourceConnections": runtime_source_connections,
        "selectedB0SourceContract": {
            "path": b0_source_contract_path.relative_to(repo).as_posix(),
            "sha256": _sha256(b0_source_contract_path),
            "schema": b0_source_contract.get("schema"),
            "status": b0_source_contract.get("status"),
        },
        "selectedB1SourceContract": b1_source_contract,
        "orderedMrtDescriptors": [
            {
                "slot": slot,
                "role": role,
                "textureFormat": texture_format,
                "viewFormat": view_format,
                "sampleCount": 1,
            }
            for slot, role, texture_format, view_format in MRT_SLOTS
        ],
        "depthDescriptor": DEPTH_TARGET,
        "textures": texture_contract,
        "constantBuffers": [
            {
                "slot": slot,
                "logicalName": name,
                "fullPublisherOrLogicalBytes": full_bytes,
                "exactUsedPrefixBytes": used_bytes,
                "producer": producer,
            }
            for slot, name, full_bytes, used_bytes, producer in CBUFFERS
        ],
        "sources": sources,
    }
    audit = {
        "immutablePacketReplayRetained": packet_issue,
        "immutablePacketReplayUsesCapturedConstantBufferArrays": packet_captured_arrays,
        "immutablePacketReplayUsesObsoleteRepresentativeTextureSlots": packet_texture_binding,
        "generativeRouteUsesCapturedPacketData": generative_forbidden_packet_data,
        "generativeRouteHasActiveT0ThroughT3SourceBindings": generative_texture_slots,
        "generativeRouteHasNamedFullB0B1Publishers": full_publishers_connected,
        "generativeRouteDeclaresEngineUnityPerDrawB2": engine_per_draw,
        "generativeRouteHasParticleSystemRendererDraw": generative_draw_renderer,
        "generativeRouteHasAuthenticatedCompilerSubstitutionGate":
            generative_substitution_gate,
        "staticTextureEvidenceUsesActualM27Geometry":
            draw.get("priorityM27Geometry") is True,
        "selectedM27VertexSkinBranchInactive":
            particle.get("liveActiveConstantRanges", {})
            .get("dynamicRecord0", {}).get("skinBranchActive") is False,
        "generativeRouteB4FailsClosedWithoutValidatedPublisher": b4_fail_closed,
        "generativeRouteHasUnarmedPostBaselineShellObserver": raw_shell_observer,
        "generativeSelectorEnablesRetainedRenderer":
            selector_enables_retained_renderer,
        "generativeShellIndependentlyPinnedFromD3D11Callback": True,
        "runtimePipelineTagCompileReflectionAndSetPassProven": True,
        "b0SelectedReadsFullySourcePopulated": b0_source_closed,
        "b1SourceOwnedInputContractComplete": b1_source_contract[
            "sourceOwnedInputContractComplete"],
        "b1SelectedReadsFullySourcePopulated": b1_source_contract[
            "allSelectedReadsRuntimeSourcePopulated"],
        "b2ActualParticleRecordRangeAndGeometryObserved": False,
        "vertexSkinDrawLocalT0OutcomeAuthenticated": False,
        "b3AllSelectedWordsTiedToOriginalMaterialAndLayout": (
            b3_material_contract["usedWordCount"] == 50 and
            b3_material_contract["bitExactMatches"] == 50 and
            b3_material_contract["unmappedUsedWords"] == [] and
            runtime_b3_material_source[
                "allEffectiveOverridesMatchOriginalMaterial"] is True and
            generative_required_material_destination and
            runtime_source_connections[
                "b3RetainedMaterialReachesExactShell"]),
        "b4SelectedFrameProducerValueAuthenticated": False,
        "orderedMrtSlotsObserved": False,
        "activeSamplerSlotsObserved": False,
        "authenticatedObservationWriterAvailable": False,
        "admissibleGenerativeParticleRendererPathExists": False,
        "boundary": (
            "These flags audit the current implementation only. They do not alter "
            "the packet replay, enable the shell, or promote it to presentation."
        ),
    }
    return contract, audit


def _live_checks(observation: dict[str, Any] | None) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, actual: Any, expected: Any) -> None:
        checks.append({
            "name": name,
            "passed": actual == expected,
            "expected": expected,
            "actual": actual,
        })

    if observation is None:
        add("live.observation", None, LIVE_SCHEMA)
        return checks

    add("live.schema", observation.get("schema"), LIVE_SCHEMA)
    add("live.status", observation.get("status"), "complete")
    add("live.observationOnly", observation.get("observationOnly"), True)
    add("live.presentationEnabled", observation.get("presentationEnabled"), False)
    add("live.capturedPacketArraysUsed",
        observation.get("capturedPacketArraysUsed"), False)

    authentication = observation.get("authentication", {})
    add("live.authentication.schema", authentication.get("schema"),
        LIVE_AUTHENTICATION_SCHEMA)
    add("live.authentication.actualDrawRendererObserved",
        authentication.get("actualDrawRendererObserved"), True)
    add("live.authentication.staticContractFieldsSynthesized",
        authentication.get("staticContractFieldsSynthesized"), False)
    add("live.authentication.synchronizedDrawIdPresent",
        bool(authentication.get("synchronizedDrawId")), True)
    add("live.authentication.producerReportSha256",
        _is_sha256(authentication.get("producerReportSha256")), True)

    renderer = observation.get("renderer", {})
    add("live.renderer.type", renderer.get("type"), "ParticleSystemRenderer")
    add("live.renderer.hierarchy", renderer.get("hierarchy"), HIERARCHY)
    add("live.renderer.pathId", renderer.get("rendererPathId"), RENDERER_PATH_ID)
    add("live.renderer.materialPathId", renderer.get("materialPathId"), MATERIAL_PATH_ID)
    add("live.renderer.meshPathId", renderer.get("meshPathId"), MESH_PATH_ID)
    add("live.renderer.activeVertexStreams", renderer.get("activeVertexStreams"), ACTIVE_STREAMS)
    add("live.renderer.drawRendererSubmissionCount",
        renderer.get("drawRendererSubmissionCount"), 1)

    substitution = observation.get("compilerSubstitution", {})
    add("live.substitution.registryReady", substitution.get("registryReady"), True)
    add("live.substitution.generativeShellPinSchema",
        substitution.get("generativeShellPinSchema"),
        GENERATIVE_SHELL_PIN_SCHEMA)
    add("live.substitution.generativeShellPinStatus",
        substitution.get("generativeShellPinStatus"),
        "independently_pinned_d3d11_callback")
    add("live.substitution.generativeShellPinReportSha256",
        _is_sha256(substitution.get("generativeShellPinReportSha256")), True)
    add("live.substitution.vertexSwapCount", substitution.get("vertexSwapCount"), 1)
    add("live.substitution.pixelSwapCount", substitution.get("pixelSwapCount"), 1)
    add("live.substitution.failureCount", substitution.get("failureCount"), 0)
    add("live.substitution.shellVertexSha256Present",
        _is_sha256(substitution.get("shellVertexSha256")), True)
    add("live.substitution.shellPixelSha256Present",
        _is_sha256(substitution.get("shellPixelSha256")), True)

    shader = observation.get("shader", {})
    add("live.shader.vertexSha256", str(shader.get("vertexSha256", "")).lower(), VS_SHA256)
    add("live.shader.pixelSha256", str(shader.get("pixelSha256", "")).lower(), PS_SHA256)
    add("live.shader.vertexIdentity", shader.get("vertexIdentity"), VS_IDENTITY)
    add("live.shader.pixelIdentity", shader.get("pixelIdentity"), PS_IDENTITY)

    ia = observation.get("inputAssembler", {})
    stride = ia.get("vertexStride")
    checks.append({
        "name": "live.inputAssembler.vertexStride",
        "passed": stride in ALLOWED_IA_STRIDES,
        "expected": ALLOWED_IA_STRIDES,
        "actual": stride,
    })
    add("live.inputAssembler.fromParticleSystemRenderer",
        ia.get("fromParticleSystemRenderer"), True)
    add("live.inputAssembler.actualParticleRecordRangeObserved",
        ia.get("actualParticleRecordRangeObserved"), True)
    add("live.inputAssembler.geometryRendererPathId",
        ia.get("geometryRendererPathId"), RENDERER_PATH_ID)

    target = observation.get("target", {})
    for key, expected in TARGET.items():
        add(f"live.target.{key}", target.get(key), expected)
    depth = observation.get("depthTarget", {})
    for key, expected in DEPTH_TARGET.items():
        add(f"live.depthTarget.{key}", depth.get(key), expected)

    width = target.get("width")
    height = target.get("height")
    viewport = target.get("viewport")
    add("live.target.positiveDimensions",
        isinstance(width, int) and width > 0 and
        isinstance(height, int) and height > 0, True)
    add("live.target.fullViewport", viewport, [0, 0, width, height])
    render_targets = observation.get("renderTargets", [])
    for slot, role, texture_format, view_format in MRT_SLOTS:
        try:
            row = _find(render_targets, slot=slot)
        except VerificationError:
            row = {}
        add(f"live.rtv{slot}.role", row.get("role"), role)
        add(f"live.rtv{slot}.textureFormat",
            row.get("textureFormat"), texture_format)
        add(f"live.rtv{slot}.viewFormat", row.get("viewFormat"), view_format)
        add(f"live.rtv{slot}.sampleCount", row.get("sampleCount"), 1)
        add(f"live.rtv{slot}.width", row.get("width"), width)
        add(f"live.rtv{slot}.height", row.get("height"), height)
        add(f"live.rtv{slot}.viewport", row.get("viewport"), viewport)
    add("live.depthTarget.width", depth.get("width"), width)
    add("live.depthTarget.height", depth.get("height"), height)

    fixed = observation.get("fixedState", {})
    add("live.fixedState.depthWriteMask", fixed.get("depthWriteMask"), 1)
    add("live.fixedState.depthFunction", fixed.get("depthFunction"), 7)
    add("live.fixedState.cullMode", fixed.get("cullMode"), 3)
    add("live.fixedState.frontCounterClockwise",
        fixed.get("frontCounterClockwise"), True)
    add("live.fixedState.scissorEnabled", fixed.get("scissorEnabled"), True)

    textures = observation.get("textures", [])
    add("live.textureSlots.exact",
        sorted(row.get("slot") for row in textures
               if isinstance(row.get("slot"), int)),
        list(range(6)))
    for slot, prop, width, height, dxgi, mips, payload_sha in TEXTURE_SLOTS:
        try:
            row = _find(textures, slot=slot)
        except VerificationError:
            row = {}
        add(f"live.t{slot}.property", row.get("property"), prop)
        add(f"live.t{slot}.width", row.get("width"), width)
        add(f"live.t{slot}.height", row.get("height"), height)
        add(f"live.t{slot}.dxgiFormat", row.get("dxgiFormat"), dxgi)
        add(f"live.t{slot}.mipCount", row.get("mipCount"), mips)
        add(f"live.t{slot}.fullMipChain", row.get("fullMipChain"), True)
        add(f"live.t{slot}.payloadSha256",
            str(row.get("payloadSha256", "")).lower(), payload_sha)
    null_resource_ids: list[Any] = []
    for slot, prop in SERIALIZED_NULL_TEXTURE_SLOTS:
        try:
            row = _find(textures, slot=slot)
        except VerificationError:
            row = {}
        add(f"live.t{slot}.property", row.get("property"), prop)
        add(f"live.t{slot}.serializedNull", row.get("serializedNull"), True)
        add(f"live.t{slot}.shaderDefault", row.get("shaderDefault"), "black")
        add(f"live.t{slot}.observedFromActualDraw",
            row.get("observedFromActualDraw"), True)
        null_resource_ids.append(row.get("objectId"))
    add("live.t4t5.sharedNullResource",
        len(null_resource_ids) == 2 and
        null_resource_ids[0] not in (None, 0) and
        null_resource_ids[0] == null_resource_ids[1], True)

    samplers = observation.get("samplers", [])
    add("live.samplerSlots.exact",
        sorted(row.get("slot") for row in samplers
               if isinstance(row.get("slot"), int)),
        SAMPLER_SLOTS)
    for slot in SAMPLER_SLOTS:
        try:
            row = _find(samplers, slot=slot)
        except VerificationError:
            row = {}
        add(f"live.s{slot}.active", row.get("active"), True)
        add(f"live.s{slot}.observedFromActualDraw",
            row.get("observedFromActualDraw"), True)

    vertex_skin_control = observation.get("vertexSkinningControl", {})
    add("live.vertexSkinningControl.observedFromActualDraw",
        vertex_skin_control.get("observedFromActualDraw"), True)
    add("live.vertexSkinningControl.synchronizedDrawId",
        vertex_skin_control.get("synchronizedDrawId"),
        authentication.get("synchronizedDrawId"))
    add("live.vertexSkinningControl.constantBufferSlot",
        vertex_skin_control.get("constantBufferSlot"), VERTEX_SKIN_CB_SLOT)
    add("live.vertexSkinningControl.recordIndex",
        vertex_skin_control.get("recordIndex"), VERTEX_SKIN_RECORD_INDEX)
    add("live.vertexSkinningControl.recordStrideFloat4",
        vertex_skin_control.get("recordStrideFloat4"),
        VERTEX_SKIN_RECORD_STRIDE_FLOAT4)
    add("live.vertexSkinningControl.flagRegisterOffset",
        vertex_skin_control.get("flagRegisterOffset"),
        VERTEX_SKIN_FLAG_REGISTER_OFFSET)
    add("live.vertexSkinningControl.flagLane",
        vertex_skin_control.get("flagLane"), VERTEX_SKIN_FLAG_LANE)
    add("live.vertexSkinningControl.flagMask",
        vertex_skin_control.get("flagMask"), VERTEX_SKIN_FLAG_MASK)
    skin_flag_raw = vertex_skin_control.get("flagRaw")
    skin_flag_raw_is_uint = (
        isinstance(skin_flag_raw, int) and
        not isinstance(skin_flag_raw, bool) and
        0 <= skin_flag_raw <= 0xFFFFFFFF)
    add("live.vertexSkinningControl.flagRawPresent",
        skin_flag_raw_is_uint, True)
    add("live.vertexSkinningControl.skinFlagClear",
        skin_flag_raw_is_uint and
        (skin_flag_raw & VERTEX_SKIN_FLAG_MASK) == 0, True)
    add("live.vertexSkinningControl.skinBranchActive",
        vertex_skin_control.get("skinBranchActive"), False)
    add("live.vertexSkinningControl.sourceMeshSkinRows",
        vertex_skin_control.get("sourceMeshSkinRows"), 0)

    vertex_resources = observation.get("vertexResources", [])
    add("live.vertex.resourceSlots.exact",
        sorted(row.get("slot") for row in vertex_resources
               if isinstance(row.get("slot"), int)), [0])
    try:
        vertex_skin = _find(vertex_resources, slot=0)
    except VerificationError:
        vertex_skin = {}
    add("live.vertex.t0.observedFromActualDraw",
        vertex_skin.get("observedFromActualDraw"), True)
    add("live.vertex.t0.synchronizedDrawId",
        vertex_skin.get("synchronizedDrawId"),
        authentication.get("synchronizedDrawId"))
    vertex_t0_bound = vertex_skin.get("bound")
    add("live.vertex.t0.boundStatePresent",
        isinstance(vertex_t0_bound, bool), True)
    if vertex_t0_bound is True:
        add("live.vertex.t0.kind", vertex_skin.get("kind"), "StructuredBuffer")
        add("live.vertex.t0.logicalName",
            vertex_skin.get("logicalName"), "_VertexSkinMatrices")
        add("live.vertex.t0.objectIdPresent",
            isinstance(vertex_skin.get("objectId"), int) and
            not isinstance(vertex_skin.get("objectId"), bool) and
            vertex_skin.get("objectId") != 0, True)
        add("live.vertex.t0.viewIdPresent",
            isinstance(vertex_skin.get("viewId"), int) and
            not isinstance(vertex_skin.get("viewId"), bool) and
            vertex_skin.get("viewId") != 0, True)
        add("live.vertex.t0.descriptorHashPresent",
            isinstance(vertex_skin.get("descriptorHash"), int) and
            not isinstance(vertex_skin.get("descriptorHash"), bool) and
            vertex_skin.get("descriptorHash") != 0, True)
        add("live.vertex.t0.byteSize",
            vertex_skin.get("byteSize"), VERTEX_SKIN_BUFFER_BYTES)
        add("live.vertex.t0.viewDimension",
            vertex_skin.get("viewDimension"), VERTEX_SKIN_VIEW_DIMENSION)
        add("live.vertex.t0.bindFlags",
            vertex_skin.get("bindFlags"), VERTEX_SKIN_BIND_FLAGS)
        add("live.vertex.t0.miscFlags",
            vertex_skin.get("miscFlags"), VERTEX_SKIN_MISC_FLAGS)
        add("live.vertex.t0.stride", vertex_skin.get("stride"), 16)
        add("live.vertex.t0.viewFirstElement",
            vertex_skin.get("viewFirstElement"), 0)
        add("live.vertex.t0.viewNumElements",
            vertex_skin.get("viewNumElements"), VERTEX_SKIN_BUFFER_ELEMENTS)
        add("live.vertex.t0.payloadBytes",
            vertex_skin.get("payloadBytes"), VERTEX_SKIN_BUFFER_BYTES)
        add("live.vertex.t0.payloadSha256",
            _is_sha256(vertex_skin.get("payloadSha256")), True)
    elif vertex_t0_bound is False:
        add("live.vertex.t0.objectId", vertex_skin.get("objectId"), 0)
        add("live.vertex.t0.viewId", vertex_skin.get("viewId"), 0)

    cbuffers = observation.get("constantBuffers", [])
    for slot, name, full_bytes, used_bytes, producer in CBUFFERS:
        try:
            row = _find(cbuffers, slot=slot)
        except VerificationError:
            row = {}
        add(f"live.b{slot}.logicalName", row.get("logicalName"), name)
        add(f"live.b{slot}.fullPublisherOrLogicalBytes",
            row.get("fullPublisherOrLogicalBytes"), full_bytes)
        add(f"live.b{slot}.exactUsedPrefixBytes",
            row.get("exactUsedPrefixBytes"), used_bytes)
        add(f"live.b{slot}.producer", row.get("producer"), producer)

    publishers = observation.get("publishers", {})
    add("live.publishers.transformVariablesReady",
        publishers.get("transformVariablesReady"), True)
    add("live.publishers.transformVariablesBytes",
        publishers.get("transformVariablesBytes"), 1312)
    add("live.publishers.shaderVariablesGlobalReady",
        publishers.get("shaderVariablesGlobalReady"), True)
    add("live.publishers.shaderVariablesGlobalBytes",
        publishers.get("shaderVariablesGlobalBytes"), 3200)
    add("live.publishers.b0SelectedReadsAuthenticated",
        publishers.get("b0SelectedReadsAuthenticated"), True)
    add("live.publishers.b1SelectedReadsAuthenticated",
        publishers.get("b1SelectedReadsAuthenticated"), True)
    add("live.publishers.terrainSubsurfaceReady",
        publishers.get("terrainSubsurfaceReady"), True)
    add("live.publishers.terrainSubsurfacePublisher",
        publishers.get("terrainSubsurfacePublisher"),
        "EndfieldRecoveredTerrainSubsurfaceConstants")
    add("live.publishers.terrainSubsurfaceNativeContractSchema",
        publishers.get("terrainSubsurfaceNativeContractSchema"),
        TERRAIN_NATIVE_CONTRACT_SCHEMA)
    add("live.publishers.terrainSubsurfaceSelectedFrameSchema",
        publishers.get("terrainSubsurfaceSelectedFrameSchema"),
        TERRAIN_SELECTED_FRAME_SCHEMA)
    add("live.publishers.terrainSubsurfaceProvenanceSha256",
        _is_sha256(
            publishers.get("terrainSubsurfaceProvenanceSha256")), True)
    published_terrain = publishers.get("terrainSubsurfacePublishedValue")
    observed_terrain = publishers.get("terrainSubsurfaceObservedRetailValue")
    add("live.publishers.terrainSubsurfacePublishedValuePresent",
        isinstance(published_terrain, int) and published_terrain >= 0, True)
    add("live.publishers.terrainSubsurfaceObservedRetailValuePresent",
        isinstance(observed_terrain, int) and observed_terrain >= 0, True)
    add("live.publishers.terrainSubsurfacePublishedMatchesObserved",
        isinstance(published_terrain, int) and
        isinstance(observed_terrain, int) and
        published_terrain == observed_terrain, True)
    return checks


def build_report(repo: Path, observation: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = repo.resolve()
    contract, audit = _validate_static(repo)
    checks = _live_checks(observation)
    failures = [row for row in checks if not row["passed"]]
    blocker_keys = [
        "generativeShellIndependentlyPinnedFromD3D11Callback",
        "runtimePipelineTagCompileReflectionAndSetPassProven",
        "b0SelectedReadsFullySourcePopulated",
        "b1SelectedReadsFullySourcePopulated",
        "b2ActualParticleRecordRangeAndGeometryObserved",
        "vertexSkinDrawLocalT0OutcomeAuthenticated",
        "b3AllSelectedWordsTiedToOriginalMaterialAndLayout",
        "b4SelectedFrameProducerValueAuthenticated",
        "orderedMrtSlotsObserved",
        "activeSamplerSlotsObserved",
        "authenticatedObservationWriterAvailable",
        "admissibleGenerativeParticleRendererPathExists",
    ]
    static_blockers = [key for key in blocker_keys if not audit.get(key)]
    admitted = (observation is not None and not failures and
                not static_blockers)
    if admitted:
        status = "admitted_live_exact_particle_renderer_abi"
        gap = None
    elif observation is None:
        status = "fail_closed_generative_route_not_source_complete"
        gap = (
            "Static admission remains fail-closed at: " +
            ", ".join(static_blockers) + ". A synchronized live observation "
            "is also required before any diagnostic draw can be admitted."
        )
    elif not failures and static_blockers:
        status = "fail_closed_static_admission_blockers"
        gap = "Static admission remains blocked at " + static_blockers[0] + "."
    else:
        status = "fail_closed_live_particle_renderer_abi_mismatch"
        gap = f"Live observation failed at {failures[0]['name']}."
    return {
        "schema": SCHEMA,
        "status": status,
        "admitted": admitted,
        "presentationEnabled": False,
        "capturedPacketDataAuthorized": False,
        "staticContractsValidated": True,
        "contract": contract,
        "currentImplementationAudit": audit,
        "staticAdmissionBlockers": static_blockers,
        "liveObservation": {
            "provided": observation is not None,
            "schema": observation.get("schema") if observation else None,
            "checks": checks,
            "failureCount": len(failures),
            "firstFailure": failures[0]["name"] if failures else None,
        },
        "observationProducer": {
            "status": "blocked_before_draw_submission",
            "reason": (
                "A complete live observation must follow an actual synchronized "
                "DrawRenderer submission and authenticate the post-baseline shell "
                "callback/pin, substitution counters, IA/PSO, ordered MRT/depth, "
                "samplers/resources, full publisher readiness, PSR b2 geometry/"
                "range, inactive b2 skin gate/explicit draw-local VS t0 outcome, and b4 "
                "selected-frame provenance. The route currently "
                "fails before submission, so no observation fields are synthesized."
            ),
        },
        "smallestRemainingSourceGap": gap,
        "boundary": (
            "Admission is diagnostic only. It never enables canonical presentation, "
            "never consumes captured VB/IB/CB arrays, and never tunes transforms, "
            "positions, curves, lighting, or texture sampling."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root (defaults to the root containing the Unity lab).")
    parser.add_argument("--live-observation", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    try:
        observation = (_read_json(args.live_observation)
                       if args.live_observation else None)
        report = build_report(args.repo, observation)
    except VerificationError as exc:
        report = {
            "schema": SCHEMA,
            "status": "fail_closed_static_contract_error",
            "admitted": False,
            "presentationEnabled": False,
            "capturedPacketDataAuthorized": False,
            "error": str(exc),
        }
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0 if report.get("admitted") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
