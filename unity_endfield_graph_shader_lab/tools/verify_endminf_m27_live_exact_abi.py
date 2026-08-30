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

VS_SHA256 = "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c"
PS_SHA256 = "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e"
VS_IDENTITY = "0xC0266E7FAC0046C1"
PS_IDENTITY = "0x92D80A93ADD9C714"
SHELL_VS_SHA256 = "b6ffa6a650c43fa86cfed1a146ecdfb046d6c92c7e866ff6f51ac79a6c7d4833"
SHELL_PS_SHA256 = "9a6803527679aa4d4822ca38a4257c2dafcbce2748a67c7e3387f63e3ee54707"

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

CBUFFERS = [
    (0, "_TransformVariables", 1312, 1312,
     "EndfieldRecoveredDeferredTransformVariables"),
    (1, "ShaderVariablesGlobal", 3200, 1696,
     "EndfieldRecoveredShaderVariablesGlobal"),
    (2, "UnityPerDraw", 256, 256, "ParticleSystemRenderer"),
    (3, "UnityPerMaterial", 576, 496, "Material"),
    (4, "_TerrainSubsurfaceConstants", 16, 16, "global"),
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
    frame_path = repo / "scratch/reverse_engineering/endfield_capture/20260827T225644Z/graphics/frames/2723/metadata.json"
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
    shell_path = repo / (
        "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/"
        "Diagnostics/EndfieldEndminfM27ExactAbiShell.shader")
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

    paths = [
        particle_path, probe_path, state_path, frame_path, texture_path,
        mapping_path, registry_path, shell_path, transform_contract_path,
        transform_owner_path, global_contract_path, global_owner_path,
        frame_runtime_path,
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
    draw = _find(frame.get("drawRecords", []), drawOrdinal=38)
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

    registry_text = registry_path.read_text(encoding="utf-8")
    registry_compact = "".join(registry_text.split())
    for digest in (SHELL_VS_SHA256, SHELL_PS_SHA256):
        byte_tokens = ",".join(f"0x{digest[i:i+2]}" for i in range(0, 64, 2))
        _require(byte_tokens in registry_compact,
                 f"compiler-substitution shell registry lost {digest}")

    shell_text = shell_path.read_text(encoding="utf-8")
    for declaration in (
        "float4 _M27CB0[82]", "float4 _M27CB1[106]",
        "float4 _M27CB2[4091]", "float4 _M27CB3[31]",
        "float4 _M27CB4[1]", "float4 target4 : SV_Target4",
    ):
        _require(declaration in shell_text,
                 f"M27 exact ABI shell drifted: {declaration}")

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

    runtime_text = frame_runtime_path.read_text(encoding="utf-8")
    old_texture_binding = (
        'destination.SetTexture("_M27T0", Texture2D.blackTexture);' in runtime_text and
        '"_ParallaxMap",\n                "_NormalMap",\n                "_MROMap",\n                "_BaseColorMap",' in runtime_text
    )
    captured_arrays = "CreateConstantBufferValues()" in runtime_text
    packet_issue = "EndfieldRecoveredEndminfM27ExactRuntime.Issue(command)" in runtime_text
    publisher_names_connected = (
        "EndfieldM27CB0" in transform_owner and "EndfieldM27CB1" in global_owner
    )

    sources = {path.relative_to(repo).as_posix(): _source(path, repo) for path in paths}
    contract = {
        "shader": {
            "subProgramIndex": 113,
            "vertexSha256": VS_SHA256,
            "pixelSha256": PS_SHA256,
            "vertexIdentity": VS_IDENTITY,
            "pixelIdentity": PS_IDENTITY,
            "shellVertexSha256": SHELL_VS_SHA256,
            "shellPixelSha256": SHELL_PS_SHA256,
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
        "activeExactRouteUsesCapturedConstantBufferArrays": captured_arrays,
        "activeExactRouteUsesCapturedPacketIssue": packet_issue,
        "activeExactMaterialUsesObsoleteRepresentativeTextureSlots": old_texture_binding,
        "fullPublishersConnectedToM27ShellCbufferNames": publisher_names_connected,
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

    renderer = observation.get("renderer", {})
    add("live.renderer.type", renderer.get("type"), "ParticleSystemRenderer")
    add("live.renderer.hierarchy", renderer.get("hierarchy"), HIERARCHY)
    add("live.renderer.pathId", renderer.get("rendererPathId"), RENDERER_PATH_ID)
    add("live.renderer.materialPathId", renderer.get("materialPathId"), MATERIAL_PATH_ID)
    add("live.renderer.meshPathId", renderer.get("meshPathId"), MESH_PATH_ID)
    add("live.renderer.activeVertexStreams", renderer.get("activeVertexStreams"), ACTIVE_STREAMS)

    substitution = observation.get("compilerSubstitution", {})
    add("live.substitution.registryReady", substitution.get("registryReady"), True)
    add("live.substitution.vertexSwapCount", substitution.get("vertexSwapCount"), 1)
    add("live.substitution.pixelSwapCount", substitution.get("pixelSwapCount"), 1)
    add("live.substitution.failureCount", substitution.get("failureCount"), 0)
    add("live.substitution.shellVertexSha256",
        str(substitution.get("shellVertexSha256", "")).lower(), SHELL_VS_SHA256)
    add("live.substitution.shellPixelSha256",
        str(substitution.get("shellPixelSha256", "")).lower(), SHELL_PS_SHA256)

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

    target = observation.get("target", {})
    for key, expected in TARGET.items():
        add(f"live.target.{key}", target.get(key), expected)
    depth = observation.get("depthTarget", {})
    for key, expected in DEPTH_TARGET.items():
        add(f"live.depthTarget.{key}", depth.get(key), expected)

    textures = observation.get("textures", [])
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
    return checks


def build_report(repo: Path, observation: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = repo.resolve()
    contract, audit = _validate_static(repo)
    checks = _live_checks(observation)
    failures = [row for row in checks if not row["passed"]]
    admitted = observation is not None and not failures
    if admitted:
        status = "admitted_live_exact_particle_renderer_abi"
        gap = None
    elif observation is None:
        status = "fail_closed_live_particle_renderer_observation_missing"
        gap = (
            "No generative live observation joins the compiler-substituted "
            "subprogram-113 pair to the actual M27 ParticleSystemRenderer draw. "
            "Before observing it, the diagnostic path must replace the old t2-t5 "
            "and captured _M27CB* bindings with source-driven t0-t3 bindings and "
            "a named bridge to the existing full b0/b1 publishers; UnityPerDraw "
            "b2 must remain engine-produced."
        )
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
        "liveObservation": {
            "provided": observation is not None,
            "schema": observation.get("schema") if observation else None,
            "checks": checks,
            "failureCount": len(failures),
            "firstFailure": failures[0]["name"] if failures else None,
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
