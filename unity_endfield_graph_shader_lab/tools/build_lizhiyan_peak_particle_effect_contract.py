#!/usr/bin/env python3
"""Build source contracts for Li Zhiyan's start_04 particle effect family."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from build_lastrite_overview_head_effect_contract import (
    REPO_ROOT,
    artifact,
    load_type,
    pptr,
    require,
    sha256,
    source_payload,
)


LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "scratch/animestudio/lizhiyan_peak_particles"
DEFAULT_OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "lizhiyan_overview_peak_particle_effects.json"
)
EFFECTS = {
    255466609: "P_fxui_lizhiyan_overview_start_04",
    262069547: "P_fxui_lizhiyan_overview_start_04_1",
    264787144: "P_fxui_lizhiyan_overview_start_04_2",
}
SHADER_PATH_ID = -1430105248647086886
M23_PATH_ID = -430604955415889784
M23_MATERIAL_SHA256 = "81B920BE11D13B3662A97851C97C8A41EF98333478578EACD2A164D4BEFE98FA"
M23_VARIANT_KEYWORDS = [
    "HG_ENABLE_MV",
    "_SAMPLE_TEX0",
    "_SAMPLE_TEX1",
    "_SAMPLE_TEX2",
    "_SAMPLE_TEX3",
    "_USE_FRESNEL",
]
M23_VARIANT_PASS = "ForwardOnly"
M23_VARIANT_ROOT = (
    REPO_ROOT
    / "scratch/character_recovery/vfx_shader_variants/shader_export/Shader"
    / "HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode"
)
M23_SHADER_JSON = (
    REPO_ROOT
    / "scratch/animestudio/m23_shader_json_probe/out/Shader"
    / "HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.json"
)
M23_SHADER_JSON_BYTES = 17166809
M23_SHADER_JSON_SHA256 = "B77939FDD44FF3684C61F4CF4464514535F43530DF6BCDC68E08DC20F1BB160E"
M23_SHADER_PROPERTY_COUNT = 296
M23_UNITY_PER_MATERIAL_SIZE = 432
M23_UNITY_PER_MATERIAL_VECTOR_COUNT = 20
M23_UNITY_PER_MATERIAL_MAX_NAMED_INDEX = 144
M23_VARIANT_FILES = {
    "vertex": {
        "blob": "0138_endfield_dxbc_0.dxbc",
        "metadata": "0138_endfield_dxbc_0.dxbc.metadata.json",
        "bytes": 10720,
        "sha256": "7D0A508F7B1E5C9AEF0B89489FEAE97F8669A8CDDABA1DE0CCC0E26FD0EB2CA0",
    },
    "fragment": {
        "blob": "0139_endfield_dxbc_1.dxbc",
        "metadata": "0139_endfield_dxbc_1.dxbc.metadata.json",
        "bytes": 8100,
        "sha256": "0FF508AA08112122C14A3ECE17D12F15778EAF39AD0C639C946512DC996B6F83",
    },
}
M23_TEXCOORD_PACKING = {
    "vertexInputs": {"v4": "TEXCOORD0", "v5": "TEXCOORD1"},
    "vertexOutputs": {
        "o1.xy": "mainUV",
        "o2.xy": "sample0UV",
        "o2.zw": "sample1UV",
        "o3.xy": "sample2UV",
        "o3.zw": "sample3UV",
    },
    "fragmentInputs": {
        "v1": "TEXCOORD0/mainUV",
        "v2": "TEXCOORD1/sample0.xy+sample1.zw",
        "v3": "TEXCOORD2/sample2.xy+sample3.zw",
    },
    "secondaryUV": "lerp(v5.xy, v4.zw, _InParticle [cb4[1].x])",
    "motionLanes": {"main": "v5.x", "samples": "v5.y"},
}
M23_LOW_CBUFFER_MAPPINGS = {
    "cb4[0].x": "_SurfaceType",
    "cb4[0].y": "_BlendMode",
    "cb4[0].z": "_Responsive",
    "cb4[0].w": "_EnableTransparentMV",
    "cb4[1].x": "_InParticle",
    "cb4[1].y": "_DisableVertColor",
    "cb4[1].z": "_TintColorIntensity",
    "cb4[1].w": "_TintColorAlpha",
    "cb4[2].y": "_ExpThreshold",
    "cb4[2].z": "_ExpIntensity",
    "cb4[2].w": "_IsSceneEffect",
    "cb4[3].x": "_IgnorePostExposure",
    "cb4[3].y": "_VertCameraOffset",
    "cb4[4]": "_TintColor",
    "cb4[5].x": "_MainTexUseDisturb",
    "cb4[5].y": "_UseMainTexAsAlpha",
    "cb4[5].z": "_MainTexMipmapBias",
    "cb4[6]": "_MainTexUVSpeed",
    "cb4[7]": "_MainTexUVRotateMat",
    "cb4[8]": "_MainTexUVWeights",
    "cb4[9]": "_MainTex_ST",
}
M23_UNRESOLVED_CBUFFER_SLOTS = [
    "cb4[11..12]", "cb4[16..18]", "cb4[17..18]",
    "cb4[23..24]", "cb4[28..29]", "cb4[33..43]",
]
M23_FRAGMENT_CONTAINER = {
    "bytes": 8100,
    "chunks": [
        {"fourCC": "ISGN", "offset": "0x2C", "bytes": 248},
        {"fourCC": "OSGN", "offset": "0x12C", "bytes": 68},
        {"fourCC": "SHEX", "offset": "0x178", "bytes": 7716},
    ],
    "hasRdef": False,
    "b4Float4Registers": 44,
    "b4Bytes": 704,
    "highestDirectlyAccessedB4Index": 43,
    "reflectionBoundary": {
        "isPartial": True,
        "bytes": 432,
        "namedSlots": "cb4[0..9] with gaps recorded by lowCbufferMappings",
    },
    "unresolvedNameBoundary": "cb4[10..43]",
}


def metadata(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("$animestudio")
    require(isinstance(value, dict), "missing $animestudio provenance")
    return value


def source_offset(data: dict[str, Any]) -> int:
    return int(metadata(data).get("sourceOffset") or -1)


def locate_by_path_id(root: Path, path_id: int, suffix: str) -> Path:
    token = f"_P{path_id & ((1 << 64) - 1):016X}"
    matches = sorted(path for path in root.rglob(f"*{suffix}") if token in path.stem.upper())
    require(len(matches) == 1, f"expected one {suffix} artifact for PathID {path_id}, got {len(matches)}")
    return matches[0]


def derived_artifact(path: Path, object_type: str, path_id: int) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "objectType": object_type,
        "pathID": path_id,
    }


def _pack_shader_properties(properties: list[dict[str, Any]]) -> tuple[dict[str, int], int]:
    """Pack serialized numeric properties using ordinary HLSL cbuffer rules."""
    offset = 0
    packed: dict[str, int] = {}
    for prop in properties:
        name = str(prop.get("m_Name") or "")
        prop_type = str(prop.get("m_Type") or "")
        if prop_type == "Texture":
            continue
        if prop_type in {"Vector", "Color"}:
            offset = (offset + 15) // 16 * 16
            packed[name] = offset
            offset += 16
        elif prop_type in {"Float", "Range"}:
            if offset % 16 > 12:
                offset = (offset + 15) // 16 * 16
            packed[name] = offset
            offset += 4
        else:
            raise RuntimeError(f"unsupported serialized shader property type: {prop_type!r}")
    return packed, (offset + 15) // 16 * 16


def _first_packing_divergence(packed: dict[str, int], known: dict[str, int]) -> dict[str, Any] | None:
    for name, offset in packed.items():
        if name in known and offset != known[name]:
            return {"property": name, "candidateOffset": offset, "knownOffset": known[name]}
    return None


def _packing_candidate(
    name: str,
    properties: list[dict[str, Any]],
    known: dict[str, int],
    reflection_size: int,
    shex_size: int,
    add_main_tex_st: bool = False,
) -> dict[str, Any]:
    source_properties = properties
    if add_main_tex_st:
        source_properties = []
        for prop in properties:
            if prop.get("m_Name") in known:
                source_properties.append(prop)
            if prop.get("m_Name") == "_MainTex":
                source_properties.append({"m_Name": "_MainTex_ST", "m_Type": "Vector"})
    packed, total = _pack_shader_properties(source_properties)
    divergence = _first_packing_divergence(packed, known)
    return {
        "name": name,
        "propertyCount": len(packed),
        "totalBytes": total,
        "firstDivergence": divergence,
        "matchesKnownLowLayout": divergence is None,
        "matchesUnityPerMaterialSize": total == reflection_size,
        "matchesShexB4Bytes": total == shex_size,
        "passesGates": divergence is None and total == reflection_size and total == shex_size,
        "mainTexSTOffset": packed.get("_MainTex_ST"),
    }


def m23_shader_json_evidence() -> dict[str, Any]:
    require(M23_SHADER_JSON.is_file(), f"M23 targeted Shader JSON is missing: {M23_SHADER_JSON}")
    require(M23_SHADER_JSON.stat().st_size == M23_SHADER_JSON_BYTES,
            "M23 targeted Shader JSON size drifted")
    require(sha256(M23_SHADER_JSON) == M23_SHADER_JSON_SHA256,
            "M23 targeted Shader JSON SHA-256 drifted")
    shader = json.loads(M23_SHADER_JSON.read_text(encoding="utf-8"))
    parsed = shader.get("m_ParsedForm")
    require(isinstance(parsed, dict), "M23 Shader JSON is missing m_ParsedForm")
    prop_info = parsed.get("m_PropInfo")
    properties = prop_info.get("m_Props") if isinstance(prop_info, dict) else None
    require(isinstance(properties, list) and len(properties) == M23_SHADER_PROPERTY_COUNT,
            "M23 serialized Shader property count drifted")
    subshaders = parsed.get("m_SubShaders")
    require(isinstance(subshaders, list) and subshaders, "M23 Shader JSON has no subshaders")
    passes = subshaders[0].get("m_Passes")
    require(isinstance(passes, list) and passes, "M23 Shader JSON has no first pass")
    first_pass = passes[0]
    name_indices = first_pass.get("m_NameIndices")
    require(isinstance(name_indices, list), "M23 Shader JSON is missing m_NameIndices")
    names = {str(row.get("Key")): int(row.get("Value")) for row in name_indices
             if isinstance(row, dict) and row.get("Key") is not None and row.get("Value") is not None}
    material_name_index = names.get("UnityPerMaterial")
    require(material_name_index is not None, "M23 UnityPerMaterial name index is missing")
    common = ((first_pass.get("progVertex") or {}).get("m_CommonParameters"))
    require(isinstance(common, dict), "M23 Shader JSON is missing vertex common parameters")
    constant_buffers = common.get("m_ConstantBuffers")
    require(isinstance(constant_buffers, list), "M23 Shader JSON is missing constant buffers")
    matching = [row for row in constant_buffers
                if isinstance(row, dict) and row.get("m_NameIndex") == material_name_index]
    require(len(matching) == 1, "M23 UnityPerMaterial constant buffer is ambiguous")
    material_cb = matching[0]
    vectors = material_cb.get("m_VectorParams")
    require(isinstance(vectors, list) and len(vectors) == M23_UNITY_PER_MATERIAL_VECTOR_COUNT,
            "M23 UnityPerMaterial named vector count drifted")
    known = {}
    for row in vectors:
        require(isinstance(row, dict) and isinstance(row.get("m_NameIndex"), int)
                and isinstance(row.get("m_Index"), int),
                "M23 UnityPerMaterial parameter row is malformed")
        name = next((key for key, value in names.items() if value == row["m_NameIndex"]), None)
        require(name is not None, "M23 UnityPerMaterial parameter name index is unresolved")
        known[name] = row["m_Index"]
    require(max(known.values()) == M23_UNITY_PER_MATERIAL_MAX_NAMED_INDEX,
            "M23 UnityPerMaterial maximum named offset drifted")
    require(material_cb.get("m_Size") == M23_UNITY_PER_MATERIAL_SIZE,
            "M23 UnityPerMaterial size drifted")
    require(material_cb.get("m_IsPartialCB") is True,
            "M23 UnityPerMaterial partial-reflection gate changed")
    active_properties = [prop for prop in properties if prop.get("m_Name") in known]
    candidates = [
        _packing_candidate("activeSerializedProperties", active_properties, known,
                           M23_UNITY_PER_MATERIAL_SIZE, M23_FRAGMENT_CONTAINER["b4Bytes"]),
        _packing_candidate("activeSerializedPropertiesPlusMainTexST", properties, known,
                           M23_UNITY_PER_MATERIAL_SIZE, M23_FRAGMENT_CONTAINER["b4Bytes"],
                           add_main_tex_st=True),
        _packing_candidate("allNonTextureSerializedProperties", properties, known,
                           M23_UNITY_PER_MATERIAL_SIZE, M23_FRAGMENT_CONTAINER["b4Bytes"]),
    ]
    require(candidates[0]["firstDivergence"] == {
        "property": "_VertCameraOffset", "candidateOffset": 8, "knownOffset": 52,
    }, "M23 active-property packing divergence drifted")
    require(candidates[1]["firstDivergence"] == candidates[0]["firstDivergence"],
            "M23 implicit MainTex_ST packing divergence drifted")
    require(candidates[1]["mainTexSTOffset"] == 48,
            "M23 implicit MainTex_ST candidate offset drifted")
    require(candidates[2]["firstDivergence"] == {
        "property": "_SurfaceType", "candidateOffset": 4, "knownOffset": 0,
    }, "M23 all-property packing divergence drifted")
    require(all(not candidate["passesGates"] for candidate in candidates),
            "M23 unresolved packing unexpectedly passed")
    return {
        "source": derived_artifact(M23_SHADER_JSON, "ShaderSerializedJSON", SHADER_PATH_ID),
        "propertyCount": len(properties),
        "unityPerMaterial": {
            "size": material_cb["m_Size"],
            "isPartial": material_cb["m_IsPartialCB"],
            "namedVectorCount": len(vectors),
            "maxNamedIndex": max(known.values()),
        },
        "packingCandidates": candidates,
    }


def hierarchy_for_group(
    game_objects: dict[int, tuple[Path, dict[str, Any]]],
    transforms: dict[int, tuple[Path, dict[str, Any]]],
) -> tuple[dict[int, str], dict[int, int]]:
    transform_by_go = {pptr(data.get("m_GameObject")): identity for identity, (_, data) in transforms.items()}
    require(len(transform_by_go) == len(game_objects), "Transform owner set drifted")
    cache: dict[int, str] = {}

    def hierarchy(go_id: int, seen: frozenset[int] = frozenset()) -> str:
        if go_id in cache:
            return cache[go_id]
        require(go_id not in seen and go_id in transform_by_go, "hierarchy cycle or missing node")
        transform = transforms[transform_by_go[go_id]][1]
        father = pptr(transform.get("m_Father"))
        name = str(game_objects[go_id][1].get("m_Name") or f"GameObject#{go_id}")
        if father and father in transforms:
            parent_go = pptr(transforms[father][1].get("m_GameObject"))
            value = hierarchy(parent_go, seen | {go_id}) + "/" + name
        else:
            value = name
        cache[go_id] = value
        return value

    for identity in game_objects:
        hierarchy(identity)
    return cache, transform_by_go


def m23_shader_abi(materials: dict[int, tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    require(M23_PATH_ID in materials, "M23 material is missing")
    material_path, material = materials[M23_PATH_ID]
    require(sha256(material_path) == M23_MATERIAL_SHA256, "M23 material SHA-256 drifted")
    require(pptr(material.get("m_Shader")) == SHADER_PATH_ID, "M23 shader identity drifted")
    require(material.get("m_ValidKeywords") == M23_VARIANT_KEYWORDS[1:],
            "M23 serialized keyword signature drifted")
    variants: dict[str, Any] = {}
    for stage, expected in M23_VARIANT_FILES.items():
        blob = M23_VARIANT_ROOT / expected["blob"]
        metadata_path = M23_VARIANT_ROOT / expected["metadata"]
        require(blob.is_file() and metadata_path.is_file(),
                f"M23 {stage} DXBC artifacts are missing")
        require(blob.stat().st_size == expected["bytes"],
                f"M23 {stage} DXBC size drifted")
        require(sha256(blob) == expected["sha256"],
                f"M23 {stage} DXBC SHA-256 drifted")
        if stage == "fragment":
            payload = blob.read_bytes()
            require(payload[:4] == b"DXBC", "M23 fragment is not a DXBC container")
            chunk_count = struct.unpack_from("<I", payload, 28)[0]
            offsets = struct.unpack_from(f"<{chunk_count}I", payload, 32)
            chunks = []
            for offset in offsets:
                fourcc = payload[offset:offset + 4].decode("ascii")
                size = struct.unpack_from("<I", payload, offset + 4)[0]
                chunks.append({"fourCC": fourcc, "offset": f"0x{offset:X}", "bytes": size})
            require(chunks == M23_FRAGMENT_CONTAINER["chunks"],
                    "M23 fragment DXBC chunk table drifted")
            require(all(row["fourCC"] != "RDEF" for row in chunks),
                    "M23 fragment unexpectedly gained an RDEF chunk")
        compiled = json.loads(metadata_path.read_text(encoding="utf-8"))
        require(compiled.get("SourcePassName") == M23_VARIANT_PASS,
                f"M23 {stage} pass drifted")
        require(compiled.get("SourceCompiledKeywords") == M23_VARIANT_KEYWORDS,
                f"M23 {stage} keyword signature drifted")
        require(compiled.get("DecodedProgramStage") == stage,
                f"M23 {stage} decoded stage drifted")
        variants[stage] = {
            "blob": derived_artifact(blob, "ShaderDXBC", SHADER_PATH_ID),
            "metadata": derived_artifact(metadata_path, "ShaderDXBCMetadata", SHADER_PATH_ID),
            "pass": M23_VARIANT_PASS,
            "keywords": M23_VARIANT_KEYWORDS,
        }
    return {
        "material": {
            "pathID": M23_PATH_ID,
            "source": artifact(material_path, "Material"),
            "validKeywords": M23_VARIANT_KEYWORDS[1:],
        },
        "shader": {"pathID": SHADER_PATH_ID, "name": "HGRP/Effect/VFXBaseV2",
                   "pass": M23_VARIANT_PASS, "keywords": M23_VARIANT_KEYWORDS},
        "variants": variants,
        "texcoordPacking": M23_TEXCOORD_PACKING,
        "lowCbufferMappings": M23_LOW_CBUFFER_MAPPINGS,
        "unresolvedCbufferSlots": M23_UNRESOLVED_CBUFFER_SLOTS,
        "fragmentContainer": M23_FRAGMENT_CONTAINER,
        "shaderJsonEvidence": m23_shader_json_evidence(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    prefab_root = args.source_root / "prefab_json"
    material_root = args.source_root / "dependency_json"
    mesh_root = args.source_root / "dependency_convert" / "Mesh"
    texture_root = args.source_root / "texture_shader_convert" / "Texture2D"
    shader_root = args.source_root / "texture_shader_convert" / "Shader"
    all_game_objects = load_type(prefab_root, "GameObject")
    all_transforms = load_type(prefab_root, "Transform")
    all_systems = load_type(prefab_root, "ParticleSystem")
    all_renderers = load_type(prefab_root, "ParticleSystemRenderer")
    all_behaviours = load_type(prefab_root, "MonoBehaviour")
    materials = load_type(material_root, "Material")
    require((len(all_game_objects), len(all_transforms), len(all_systems), len(all_renderers), len(all_behaviours)) ==
            (17, 17, 14, 14, 3), "peak particle source census drifted")
    require(len(materials) == 8, "peak particle material census drifted")

    artifact_paths: list[Path] = []
    referenced_materials: set[int] = set()
    referenced_meshes: set[int] = set()
    effects: list[dict[str, Any]] = []
    global_hierarchy, global_transform_by_go = hierarchy_for_group(all_game_objects, all_transforms)
    for offset, effect_name in EFFECTS.items():
        member_go_ids = {identity for identity, value in global_hierarchy.items()
                         if value == effect_name or value.startswith(effect_name + "/")}
        game_objects = {identity: row for identity, row in all_game_objects.items() if identity in member_go_ids}
        member_transform_ids = {global_transform_by_go[identity] for identity in member_go_ids}
        transforms = {identity: row for identity, row in all_transforms.items() if identity in member_transform_ids}
        systems = {identity: row for identity, row in all_systems.items()
                   if pptr(row[1].get("m_GameObject")) in member_go_ids}
        renderers = {identity: row for identity, row in all_renderers.items()
                     if pptr(row[1].get("m_GameObject")) in member_go_ids}
        behaviours = {identity: row for identity, row in all_behaviours.items()
                      if pptr(row[1].get("m_GameObject")) in member_go_ids}
        require(len(behaviours) == 1 and len(systems) == len(renderers), f"{effect_name} component census drifted")
        hierarchy, transform_by_go = hierarchy_for_group(game_objects, transforms)
        roots = [identity for identity, value in hierarchy.items() if value == effect_name]
        require(len(roots) == 1, f"{effect_name} root drifted")
        nodes = []
        for go_id in sorted(game_objects, key=hierarchy.get):
            go_path, game_object = game_objects[go_id]
            transform_id = transform_by_go[go_id]
            transform_path, transform = transforms[transform_id]
            nodes.append({
                "hierarchy": hierarchy[go_id],
                "gameObjectPathID": go_id,
                "transformPathID": transform_id,
                "gameObject": source_payload(game_object),
                "transform": source_payload(transform),
                "gameObjectSource": artifact(go_path, "GameObject"),
                "transformSource": artifact(transform_path, "Transform"),
            })
            artifact_paths.extend((go_path, transform_path))
        systems_by_go = {pptr(data.get("m_GameObject")): (identity, path, data)
                         for identity, (path, data) in systems.items()}
        renderers_by_go = {pptr(data.get("m_GameObject")): (identity, path, data)
                           for identity, (path, data) in renderers.items()}
        require(set(systems_by_go) == set(renderers_by_go), f"{effect_name} particle owners differ")
        pairs = []
        for go_id in sorted(systems_by_go, key=hierarchy.get):
            system_id, system_path, system = systems_by_go[go_id]
            renderer_id, renderer_path, renderer = renderers_by_go[go_id]
            material_ids = [pptr(value) for value in renderer.get("m_Materials") or [] if pptr(value)]
            mesh_id = pptr(renderer.get("m_Mesh"))
            referenced_materials.update(material_ids)
            if mesh_id:
                referenced_meshes.add(mesh_id)
            pairs.append({
                "hierarchy": hierarchy[go_id],
                "gameObjectPathID": go_id,
                "particleSystem": {
                    "pathID": system_id,
                    "source": artifact(system_path, "ParticleSystem"),
                    "fields": {key: value for key, value in system.items()
                               if key != "$animestudio" and not key.endswith("Module")},
                    "enabledModules": {key: value for key, value in system.items()
                                       if key.endswith("Module") and isinstance(value, dict) and bool(value.get("enabled"))},
                },
                "renderer": {"pathID": renderer_id, "source": artifact(renderer_path, "ParticleSystemRenderer"),
                             "fields": source_payload(renderer)},
                "materialPathIDs": material_ids,
                "meshPathID": mesh_id,
            })
            artifact_paths.extend((system_path, renderer_path))
        behaviour_id, (behaviour_path, behaviour) = next(iter(behaviours.items()))
        artifact_paths.append(behaviour_path)
        effects.append({
            "effectName": effect_name,
            "sourceOffset": offset,
            "rootGameObjectPathID": roots[0],
            "lodComponentPathID": behaviour_id,
            "lodComponent": source_payload(behaviour),
            "lodComponentSource": artifact(behaviour_path, "MonoBehaviour"),
            "hierarchyNodes": nodes,
            "particlePairs": pairs,
        })

    require(referenced_materials == set(materials), "referenced material set drifted")
    material_rows = []
    texture_ids: set[int] = set()
    for identity in sorted(materials):
        path, data = materials[identity]
        require(pptr(data.get("m_Shader")) == SHADER_PATH_ID, "material shader identity drifted")
        refs = []
        for prop, environment in sorted(((data.get("m_SavedProperties") or {}).get("m_TexEnvs") or {}).items()):
            texture = (environment or {}).get("m_Texture") or {}
            texture_id = int(texture.get("m_PathID") or 0)
            if texture_id:
                texture_ids.add(texture_id)
                refs.append({"property": prop, "fileID": int(texture.get("m_FileID") or 0),
                             "pathID": texture_id, "scale": environment.get("m_Scale"),
                             "offset": environment.get("m_Offset")})
        material_rows.append({"pathID": identity, "name": data.get("m_Name"),
                              "shaderPathID": SHADER_PATH_ID,
                              "customRenderQueue": int(data.get("m_CustomRenderQueue") or 0),
                              "textureReferences": refs, "payload": source_payload(data),
                              "source": artifact(path, "Material")})
        artifact_paths.append(path)
    m23_abi = m23_shader_abi(materials)
    artifact_paths.append(M23_SHADER_JSON)
    for expected in M23_VARIANT_FILES.values():
        artifact_paths.extend((M23_VARIANT_ROOT / expected["blob"],
                               M23_VARIANT_ROOT / expected["metadata"]))
    texture_rows = []
    for identity in sorted(texture_ids):
        path = locate_by_path_id(texture_root, identity, ".png")
        texture_rows.append({"pathID": identity, "convertedPng": derived_artifact(path, "Texture2DConvertedPNG", identity)})
        artifact_paths.append(path)
    mesh_rows = []
    for identity in sorted(referenced_meshes):
        path = locate_by_path_id(mesh_root, identity, ".obj")
        mesh_rows.append({"pathID": identity, "convertedObj": derived_artifact(path, "MeshConvertedOBJ", identity)})
        artifact_paths.append(path)
    shader_files = sorted(shader_root.glob("*.shader"))
    require(len(shader_files) == 1, "expected one converted VFXBaseV2 shader")
    artifact_paths.append(shader_files[0])

    aggregate = hashlib.sha256()
    for path in sorted(set(artifact_paths), key=lambda value: value.as_posix().casefold()):
        relative = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        aggregate.update(relative.encode())
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(sha256(path)))
    output = {
        "schema": "endfield.lizhiyan-overview-peak-particle-effects.v1",
        "status": "serialized_hierarchy_particle_material_texture_mesh_closed_visual_shader_fail_closed",
        "summary": {"effects": 3, "hierarchyNodes": 17, "particlePairs": 14, "materials": 8,
                    "uniqueTextures": len(texture_ids), "meshes": len(referenced_meshes),
                    "sourceAggregateSha256": aggregate.hexdigest().upper()},
        "effects": effects,
        "materials": material_rows,
        "textures": texture_rows,
        "meshes": mesh_rows,
        "shader": {"pathID": SHADER_PATH_ID, "name": "HGRP/Effect/VFXBaseV2",
                   "convertedSource": derived_artifact(shader_files[0], "ShaderConvertedSource", SHADER_PATH_ID)},
        "m23ShaderAbi": m23_abi,
        "executionBoundary": "Serialized hierarchy/TRS, particle modules, renderer/material/mesh ownership, material payloads, converted textures, converted mesh geometry, shader identity, and M23's exact ForwardOnly vertex/fragment DXBC variant are source-closed. M23 TEXCOORD packing and the named low UnityPerMaterial slots are instruction/metadata-closed; high sample/mask/blend/dissolve/Fresnel cbuffer property names remain explicitly unresolved. Filtered GameObject convenience JSON omits m_IsActive; manual diagnostics default those nodes active while retail activation remains owned by unrecovered EffectSetting/EffectLodCfg execution. Converted PNG/OBJ payloads are diagnostic derivatives. Retail EffectSetting execution, descriptor binding, draw/PSO/MRT/depth, after-DOF survivor ownership, and final compositing remain unproven; visibleAdmission stays false.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}: effects=3 nodes=17 particles=14 materials=8 textures={len(texture_ids)} meshes={len(referenced_meshes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
