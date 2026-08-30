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
    frame_runtime_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredDeferredGBufferFrame.cs")
    generative_runtime_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/"
        "Rendering/EndfieldRecoveredEndminfM27GenerativeExactRuntime.cs")

    paths = [
        particle_path, probe_path, state_path, frame_path, texture_path,
        mapping_path, registry_path, native_observer_path, generative_pin_path,
        packet_shell_path,
        shell_path,
        terrain_contract_path, terrain_publisher_path,
        compatibility_binding_path, shell_observer_path, material_json_path,
        transform_contract_path,
        transform_owner_path, global_contract_path, global_owner_path,
        frame_runtime_path, generative_runtime_path,
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
    full_publishers_connected = (
        "TransformVariablesId" in generative_text and
        "ShaderVariablesGlobalId" in generative_text and
        "EndfieldRecoveredDeferredTransformVariablesContract.SizeBytes" in generative_text and
        "EndfieldRecoveredShaderVariablesGlobalContract.SizeBytes" in generative_text)
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
        "b0SelectedReadsFullySourcePopulated": False,
        "b1SelectedReadsFullySourcePopulated": False,
        "b2ActualParticleRecordRangeAndGeometryObserved": False,
        "vertexSkinStructuredResourceAuthenticated": False,
        "b3AllSelectedWordsTiedToOriginalMaterialAndLayout": False,
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

    vertex_resources = observation.get("vertexResources", [])
    try:
        vertex_skin = _find(vertex_resources, slot=0)
    except VerificationError:
        vertex_skin = {}
    add("live.vertex.t0.kind", vertex_skin.get("kind"), "StructuredBuffer")
    add("live.vertex.t0.logicalName",
        vertex_skin.get("logicalName"), "_VertexSkinMatrices")
    add("live.vertex.t0.stride", vertex_skin.get("stride"), 16)
    add("live.vertex.t0.skinBranchActive",
        vertex_skin.get("skinBranchActive"), False)
    add("live.vertex.t0.sourceMeshSkinRows",
        vertex_skin.get("sourceMeshSkinRows"), 0)

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
        "vertexSkinStructuredResourceAuthenticated",
        "b3AllSelectedWordsTiedToOriginalMaterialAndLayout",
        "b4SelectedFrameProducerValueAuthenticated",
        "orderedMrtSlotsObserved",
        "activeSamplerSlotsObserved",
        "authenticatedObservationWriterAvailable",
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
            "The named generative shell and default-off ParticleSystemRenderer "
            "route now have independently pinned compiler identities and SetPass "
            "proof, but admission still requires source-complete selected b0/b1 "
            "reads, actual PSR b2 range/geometry and vertex structured-resource "
            "authentication, complete b3 word provenance, fresh selected-frame b4 "
            "value provenance, ordered MRT/sampler observation, and an "
            "authenticated synchronized writer."
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
                "range, and b4 selected-frame provenance. The route currently "
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
