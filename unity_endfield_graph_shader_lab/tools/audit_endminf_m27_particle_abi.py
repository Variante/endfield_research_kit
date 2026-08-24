#!/usr/bin/env python3
"""Audit the exact M27 LitEffect particle/optional-skin vertex ABI.

This is intentionally fail closed.  It separates observations made by the
current Unity editor from the original Endfield shader dataflow, and never
equates ParticleSystemRenderer.enableGPUInstancing with a proven retail
BLENDWEIGHTS/BLENDINDICES publisher.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
UNITY = REPO / "unity_endfield_graph_shader_lab"
SOURCE_CONTRACT = REPO / "reports/assets/character_recovery/endminf_m27_suikuai_source_contract.json"
PROGRAM_CONTRACT = REPO / "reports/assets/character_recovery/endminf_m27_liteffect_program_recovery.json"
UNITY_PROBE = REPO / "reports/assets/character_recovery/endminf_m27_particle_abi_unity_probe.json"
RESOURCE_MAPPING = (
    UNITY
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/ExternalUiEffects/"
    "endminf_liteffect_resource_mapping.json"
)
VERTEX_HLSL = (
    REPO
    / "scratch/animestudio/endminf_liteffect_shader/sidecars/Shader/"
    "HGRP_LitEffect_p5936F49FA93F14DD.shader.bytecode/ruri_final/"
    "parallax_hgbuffer_vertex.hlsl"
)
FRAGMENT_HLSL = VERTEX_HLSL.with_name("parallax_hgbuffer_fragment.hlsl")
UNITY_PARTICLE_INCLUDE = Path(
    "D:/Program Files/2022.3.62f3/Editor/Data/CGIncludes/"
    "UnityStandardParticleInstancing.cginc"
)
OUTPUT = REPO / "reports/assets/character_recovery/endminf_m27_particle_abi.json"

EXPECTED = {
    "vertex_hlsl": "766bb181381150caf1e732abb67e885e3388f6a589e8685cc82b8435dd689d9c",
    "fragment_hlsl": "7783cc2a916242f273853b115b2b4b67dfb8736940d86220d1cdf91dfe459744",
    "unity_particle_include": "19ca894b59456951060791e3f79884aab16e4a7ffd64baf028a7389411c51c0f",
    "vertex_dxbc": "b38d5e7661abdcb0d56a1c349eb673d205547fef5a30ba7d10befbe78b638253",
    "mesh_json": "55dd5a73380a0b64b8fc173cb636f58b0178e377e7fd4445362a4a6c0de2f58d",
    "particle_raw": "8954241756066faa9de14c4d73da702c7adf07037346fd743ce5f6625730efd5",
    "renderer_raw": "9d782b66bb7bf6375ddf80ab9c776c35bb0718af154c41a574b1c29be98aae9c",
}


class AuditError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc


def sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AuditError(f"cannot hash {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def main(output: Path, unity_particle_include: Path) -> dict[str, Any]:
    source = load_json(SOURCE_CONTRACT)
    program = load_json(PROGRAM_CONTRACT)
    unity_probe = load_json(UNITY_PROBE)
    mapping = load_json(RESOURCE_MAPPING)

    vertex_hash = sha256(VERTEX_HLSL)
    fragment_hash = sha256(FRAGMENT_HLSL)
    include_hash = sha256(unity_particle_include)
    require(vertex_hash == EXPECTED["vertex_hlsl"], "selected Ruri vertex HLSL hash drifted")
    require(fragment_hash == EXPECTED["fragment_hlsl"], "selected Ruri fragment HLSL hash drifted")
    require(include_hash == EXPECTED["unity_particle_include"], "Unity particle include hash drifted")
    require(
        program["selectedProgram"]["vertex"]["sha256"] == EXPECTED["vertex_dxbc"],
        "selected M27 vertex DXBC hash drifted",
    )
    require(source["mesh"]["json"]["sha256"] == EXPECTED["mesh_json"], "M27 mesh JSON hash drifted")
    require(source["particleSystem"]["rawDataSha256"] == EXPECTED["particle_raw"], "M27 particle raw hash drifted")
    require(source["renderer"]["rawDataSha256"] == EXPECTED["renderer_raw"], "M27 renderer raw hash drifted")
    require(unity_probe["status"] == "ok", "current Unity M27 probe did not pass")
    require(unity_probe["unityVersion"] == "2022.3.62f3", "current Unity probe version drifted")

    expected_streams = ["Position", "Normal", "Color", "UV", "UV2", "Custom1XYZW"]
    require(source["renderer"]["customVertexStreams"]["names"] == expected_streams, "serialized M27 streams drifted")
    require(unity_probe["activeVertexStreams"] == expected_streams, "current Unity active M27 streams drifted")
    require(unity_probe["enableGPUInstancing"] is True, "current Unity lost the M27 GPU-instancing flag")
    require(unity_probe["rendererEnabled"] is False, "M27 must remain blocked")
    require(unity_probe["retainedMaterialCount"] == 0, "M27 unexpectedly has a retained material")
    require(unity_probe["retainedMeshAssigned"] is False, "M27 unexpectedly has a retained mesh")
    require(unity_probe["exactMeshVertexCount"] == 29, "current Unity M27 mesh vertex count drifted")
    require(unity_probe["exactMeshBoneWeightCount"] == 0, "current Unity M27 mesh has bone weights")
    require(unity_probe["exactMeshBindPoseCount"] == 0, "current Unity M27 mesh has bind poses")
    require(unity_probe["exactMeshBonesPerVertexInfluenceSum"] == 0, "current Unity M27 mesh has bone influences")

    vertex = VERTEX_HLSL.read_text(encoding="utf-8")
    fragment = FRAGMENT_HLSL.read_text(encoding="utf-8")
    unity_include = unity_particle_include.read_text(encoding="utf-8")
    skin_gate = "if (!(((_258 & 32u) == 0u) || (_261 == 0u)))"
    no_skin_marker = "_546 = TEXCOORD_4.z;"
    skin_start = vertex.find(skin_gate)
    no_skin_start = vertex.find(no_skin_marker)
    require(skin_start >= 0 and no_skin_start > skin_start, "selected vertex optional-skin branch drifted")
    require("_10.Load<uint4>" in vertex[skin_start:no_skin_start], "selected skin branch lost matrix-buffer reads")
    require("_10.Load<uint4>" not in vertex[no_skin_start:], "selected no-skin tail unexpectedly reads t0")
    for marker in (
        "BLENDINDICES.x * 3u",
        "BLENDINDICES.w * 3u",
        "BLENDWEIGHTS.x",
        "BLENDWEIGHTS.w",
        "_564 = POSITION.z;",
        "_566 = POSITION.x;",
        "_568 = POSITION.y;",
        "bool _795 = asfloat(_790.x) < 1.0f;",
        "bool _796 = asfloat(_790.y) < 1.0f;",
        "float _816 = _795 ? _566 : _550;",
    ):
        require(marker in vertex, f"selected vertex dataflow marker drifted: {marker}")

    require("TEXCOORD_4 : TEXCOORD6" in vertex, "Ruri logical TEXCOORD4 input declaration drifted")
    require("float4 TEXCOORD_4_1 : TEXCOORD4" in vertex, "selected color output signature drifted")
    require("TEXCOORD_4" not in fragment, "selected fragment unexpectedly consumes TEXCOORD4")
    require(mapping["bindChannels"]["status"] == "gap", "ParserBindChannels gap unexpectedly changed")

    selected_keywords = program["selectedProgram"]["compiledKeywords"]
    require(selected_keywords == ["HG_ENABLE_MV", "_PARALLAX_MAP"], "selected M27 keywords drifted")
    require("unity_ParticleInstanceData" not in vertex, "selected original vertex unexpectedly exposes Unity particle buffer")
    for marker in (
        "struct DefaultParticleInstanceData",
        "float3x4 transform;",
        "StructuredBuffer<UNITY_PARTICLE_INSTANCE_DATA> unity_ParticleInstanceData;",
        "UNITY_PROCEDURAL_INSTANCING_ENABLED",
    ):
        require(marker in unity_include, f"current Unity particle-instancing contract drifted: {marker}")

    report = {
        "schema": "endfield.endminf-m27-particle-abi.v1",
        "status": "fail_closed_physical_particle_instance_publisher_unresolved",
        "scope": "P_fxui_endminm003_overview_02/all/suikuai (2) only",
        "selectedProgram": {
            "vertexDxbcSha256": EXPECTED["vertex_dxbc"],
            "ruriVertexPath": relative(VERTEX_HLSL),
            "ruriVertexSha256": vertex_hash,
            "ruriFragmentPath": relative(FRAGMENT_HLSL),
            "ruriFragmentSha256": fragment_hash,
            "compiledKeywords": selected_keywords,
        },
        "exactSerializedConsumer": {
            "particlePathId": source["particleSystem"]["pathId"],
            "particleRawSha256": source["particleSystem"]["rawDataSha256"],
            "rendererPathId": source["renderer"]["pathId"],
            "rendererRawSha256": source["renderer"]["rawDataSha256"],
            "renderMode": source["renderer"]["renderMode"]["name"],
            "enableGPUInstancing": True,
            "activeVertexStreams": expected_streams,
            "meshPathId": source["mesh"]["pathId"],
            "meshJsonSha256": source["mesh"]["json"]["sha256"],
            "meshVertexCount": source["mesh"]["vertexCount"],
            "meshSkinRows": 0,
            "meshBindPoses": 0,
            "meshBoneNameHashes": 0,
        },
        "currentUnityProbe": {
            "path": relative(UNITY_PROBE),
            "unityVersion": unity_probe["unityVersion"],
            "result": "serialized streams and GPU-instancing flag retained; exact imported mesh remains unskinned; renderer remains disabled with no bindings",
            "activeVertexStreams": unity_probe["activeVertexStreams"],
            "meshBoneWeights": unity_probe["exactMeshBoneWeightCount"],
            "meshBindPoses": unity_probe["exactMeshBindPoseCount"],
            "meshInfluences": unity_probe["exactMeshBonesPerVertexInfluenceSum"],
            "standardParticleInstancingInclude": {
                "path": str(unity_particle_include.resolve()),
                "sha256": include_hash,
                "contract": "procedural instance buffer with float3x4 transform, packed color, and animation frame; it does not define BLENDWEIGHTS/BLENDINDICES as particle instance fields",
            },
        },
        "selectedVertexDataflow": {
            "optionalSkinGate": "UnityPerDraw c4.w bit 5 set and c4.w with bits 4/5 cleared nonzero",
            "skinBranch": "BLENDINDICES select three-float4 matrix rows from t0 _VertexSkinMatrices; BLENDWEIGHTS blend two or four current and previous matrices",
            "noSkinBranch": "t0, BLENDWEIGHTS, and BLENDINDICES are not read; current object position is POSITION and the alternate previous-position carrier is TEXCOORD4.xyz",
            "currentTransform": "UnityPerDraw c0-c3 object-to-world path",
            "previousTransform": "UnityPerDraw c6-c9 previous-object path, gated by c10.x/y motion parameters; current position is reused when those gates select no previous deformation/object motion",
            "fragmentUse": "the selected fragment consumes UV0/UV1, world normal/tangent, current clip position, and previous clip position; it does not consume the vertex TEXCOORD4/color output",
        },
        "validatedConclusions": [
            "The selected original program's BLEND inputs are matrix indices/weights for its optional t0 transform branch; they are not self-describing particle transforms.",
            "The exact authored rock mesh and its current Unity import have no skin data, so mesh-authored BLEND payload is excluded.",
            "The current Unity standard procedural particle path uses unity_ParticleInstanceData rather than BLEND semantics; the selected original program exposes no such resource and has no procedural-instancing keyword.",
            "The M27 renderer retains Custom1XYZW exactly, but the original Shader ParserBindChannels table is absent, so the stream cannot be equated to the DXBC TEXCOORD4 previous-position input.",
        ],
        "unresolvedPhysicalAbi": [
            {
                "input": "UnityPerDraw c4.w skin/transform flags",
                "gap": "no selected retail draw capture proves whether Endfield sets the optional transform branch for this ParticleSystemRenderer",
            },
            {
                "input": "BLENDWEIGHTS/BLENDINDICES and t0 _VertexSkinMatrices",
                "gap": "if Endfield repurposes the optional transform branch for particle mesh instancing, the engine-synthesized attributes, current/previous matrix-table bases, and contents remain uncaptured; current Unity public active streams do not expose internal generated attributes",
            },
            {
                "input": "TEXCOORD4",
                "gap": "DXBC uses it as alternate previous local position, while the renderer serializes Custom1XYZW; missing ParserBindChannels prevents a physical semantic assignment",
            },
        ],
        "implementationDecision": {
            "diagnosticShaderCreated": False,
            "reason": "A source-level shader could sample BLEND semantics in current Unity, but it could not recreate or observe Endfield's custom engine-side publisher and would risk turning missing attributes into an asserted retail ABI.",
            "admissionImpact": "Do not append guessed BLEND streams, bind an identity t0 buffer, or map Custom1XYZW to TEXCOORD4. Keep M27 blocked until a selected retail draw capture or equivalent source-proven publisher closes all three physical inputs.",
        },
        "protectedBoundary": "M21 overview_02/all/shitou (1) was not inspected, modified, disabled, resized, retimed, or used as an M27 substitute.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--unity-particle-include", type=Path, default=UNITY_PARTICLE_INCLUDE)
    args = parser.parse_args()
    result = main(args.output, args.unity_particle_include)
    print(f"validated Endminf M27 particle ABI boundary: {args.output}")
    print(result["status"])
