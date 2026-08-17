#!/usr/bin/env python3
"""Build source contracts for Li Zhiyan's start_04 particle effect family."""

from __future__ import annotations

import argparse
import hashlib
import json
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
