#!/usr/bin/env python3
"""Build fail-closed source contracts for Li Zhiyan Overview start_02/_03."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build_lastrite_overview_head_effect_contract import (
    REPO_ROOT,
    artifact,
    file_artifact,
    path_id,
    pptr,
    require,
    resolve_textures,
    sha256,
    source_payload,
)


LAB = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "scratch/character_recovery/next_effect_candidates/prefabs"
EXPORT = REPO_ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets"
MATERIAL_ROOT = EXPORT / "json_by_type/Material"
MESH_ROOT = EXPORT / "convert_by_type/Mesh"
SHARED_ANIMATION = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "A_fxui__lizhiyan_overview_start_01.anim"
)
SHARED_CONTRACT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "lizhiyan_overview_start_01_effect.json"
)
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "lizhiyan_overview_start_02_03_effects.json"
)
ANIMATION_CLIP_PATH_ID = 7360398354216100382
SHADER_PATH_ID = -1430105248647086886


@dataclass(frozen=True)
class EffectSpec:
    name: str
    suffix: str
    duration: float
    mesh_paths: dict[int, Path]
    material_paths: dict[int, Path]


SPECS = (
    EffectSpec(
        "P_fxui_lizhiyan_overview_start_02",
        "D0A1.json",
        5.0,
        {7032717393607757449: MESH_ROOT / "Plane009_p61993B3563B38E89.obj"},
        {
            -481371258366057841: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_12_pF951D3641402228F.json",
            2540816063756981481: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_13_p2342CABF87D754E9.json",
            -2434886401441015548: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_14_pDE358BB7EDADD904.json",
        },
    ),
    EffectSpec(
        "P_fxui_lizhiyan_overview_start_03",
        "B53C.json",
        7.0,
        {
            -4003364140602261775: MESH_ROOT / "S_fx_shoutiaodai_01_pC87131865CDD7EF1.obj",
            3893791131891476371: MESH_ROOT / "S_fx_tuoweidisan_01_p360986677DF52793.obj",
        },
        {
            -7438264461631060117: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_15_p98C5F9E1BB11876B.json",
            9120706159938786131: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_16_p7E9341EDCBDE5353.json",
            -6772801081383272744: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_17_pA2022D4CE1C4BED8.json",
        },
    ),
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_type(name: str, suffix: str) -> dict[int, tuple[Path, dict[str, Any]]]:
    result: dict[int, tuple[Path, dict[str, Any]]] = {}
    for path in sorted((SOURCE / name).glob(f"*{suffix}")):
        data = load(path)
        identity = path_id(path, data)
        require(identity not in result, f"duplicate {name} PathID {identity}")
        result[identity] = (path, data)
    return result


def build_effect(spec: EffectSpec) -> tuple[dict[str, Any], list[Path], set[int]]:
    game_objects = load_type("GameObject", spec.suffix)
    transforms = load_type("Transform", spec.suffix)
    animators = load_type("Animator", spec.suffix)
    filters = load_type("MeshFilter", spec.suffix)
    renderers = load_type("MeshRenderer", spec.suffix)
    behaviours = load_type("MonoBehaviour", spec.suffix)
    require(len(game_objects) == 4 and len(transforms) == 4,
            f"{spec.name} hierarchy census drifted")
    require(len(animators) == 1 and len(filters) == len(renderers) == 3,
            f"{spec.name} static component census drifted")
    require(len(behaviours) == 2, f"{spec.name} behaviour census drifted")

    transform_by_go = {pptr(row.get("m_GameObject")): identity
                       for identity, (_, row) in transforms.items()}
    require(set(transform_by_go) == set(game_objects), f"{spec.name} Transform owners drifted")
    hierarchy_cache: dict[int, str] = {}

    def hierarchy(go_id: int) -> str:
        if go_id in hierarchy_cache:
            return hierarchy_cache[go_id]
        transform = transforms[transform_by_go[go_id]][1]
        father = pptr(transform.get("m_Father"))
        name = str(game_objects[go_id][1].get("m_Name") or go_id)
        if father:
            require(father in transforms, f"{spec.name} parent Transform missing")
            parent_go = pptr(transforms[father][1].get("m_GameObject"))
            value = hierarchy(parent_go) + "/" + name
        else:
            value = name
        hierarchy_cache[go_id] = value
        return value

    roots = [identity for identity in game_objects if hierarchy(identity) == spec.name]
    require(len(roots) == 1, f"{spec.name} root drifted")
    root_id = roots[0]
    artifacts: list[Path] = []
    hierarchy_rows = []
    for go_id in sorted(game_objects, key=hierarchy):
        go_path, go = game_objects[go_id]
        transform_id = transform_by_go[go_id]
        transform_path, transform = transforms[transform_id]
        hierarchy_rows.append({
            "hierarchy": hierarchy(go_id),
            "gameObjectPathID": go_id,
            "transformPathID": transform_id,
            "gameObject": source_payload(go),
            "transform": source_payload(transform),
            "gameObjectSource": artifact(go_path, "GameObject"),
            "transformSource": artifact(transform_path, "Transform"),
        })
        artifacts.extend((go_path, transform_path))

    setting_path, setting = next((path, row) for path, row in behaviours.values()
                                 if "effectLogicCfg" in row)
    helper_path, helper = next((path, row) for path, row in behaviours.values()
                               if "startAnimationClip" in row)
    timing = setting["effectLogicCfg"]
    require(float(timing["duration"]) == spec.duration and
            float(timing["delay"]) == 0.0 and int(timing["isLoop"]) == 0,
            f"{spec.name} timing drifted")
    require(pptr(helper["startAnimationClip"]) == ANIMATION_CLIP_PATH_ID and
            pptr(helper["loopAnimationClip"]) == 0 and
            pptr(helper["endAnimationClip"]) == 0,
            f"{spec.name} animation helper drifted")
    artifacts.extend((setting_path, helper_path))

    filters_by_go = {pptr(row.get("m_GameObject")): (identity, path, row)
                     for identity, (path, row) in filters.items()}
    renderers_by_go = {pptr(row.get("m_GameObject")): (identity, path, row)
                       for identity, (path, row) in renderers.items()}
    require(set(filters_by_go) == set(renderers_by_go) == set(game_objects) - {root_id},
            f"{spec.name} static owners drifted")
    static_nodes = []
    referenced_meshes: set[int] = set()
    referenced_materials: set[int] = set()
    for go_id in sorted(filters_by_go, key=hierarchy):
        filter_id, filter_path, mesh_filter = filters_by_go[go_id]
        renderer_id, renderer_path, renderer = renderers_by_go[go_id]
        mesh_id = pptr(mesh_filter.get("m_Mesh"))
        material_ids = [pptr(value) for value in renderer.get("m_Materials") or []]
        require(mesh_id in spec.mesh_paths and len(material_ids) == 1 and
                material_ids[0] in spec.material_paths,
                f"{spec.name} mesh/material identity drifted")
        referenced_meshes.add(mesh_id)
        referenced_materials.update(material_ids)
        static_nodes.append({
            "hierarchy": hierarchy(go_id),
            "gameObjectPathID": go_id,
            "meshFilterPathID": filter_id,
            "meshRendererPathID": renderer_id,
            "mesh": {"fileID": int(mesh_filter["m_Mesh"]["m_FileID"]), "pathID": mesh_id},
            "materials": [{"fileID": 4, "pathID": material_ids[0]}],
            "sourceRendererEnabled": bool(renderer.get("m_Enabled")),
            "meshFilterSource": artifact(filter_path, "MeshFilter"),
            "meshRendererSource": artifact(renderer_path, "MeshRenderer"),
            "meshFilter": source_payload(mesh_filter),
            "meshRenderer": source_payload(renderer),
        })
        artifacts.extend((filter_path, renderer_path))
    require(referenced_meshes == set(spec.mesh_paths) and
            referenced_materials == set(spec.material_paths),
            f"{spec.name} dependency set drifted")

    mesh_rows = []
    for identity, path in sorted(spec.mesh_paths.items()):
        require(path.is_file(), f"{spec.name} converted mesh missing: {path}")
        mesh_rows.append({"pathID": identity, "convertedObj": file_artifact(path, "MeshObj")})
        artifacts.append(path)

    material_rows = []
    texture_ids: set[int] = set()
    for identity, path in sorted(spec.material_paths.items()):
        require(path.is_file(), f"{spec.name} material missing: {path}")
        data = load(path)
        require(path_id(path, data) == identity and pptr(data.get("m_Shader")) == SHADER_PATH_ID and
                int(data.get("m_CustomRenderQueue") or 0) == 3704,
                f"{spec.name} material ABI drifted: {identity}")
        refs = []
        for property_name, environment in sorted(
            ((data.get("m_SavedProperties") or {}).get("m_TexEnvs") or {}).items()
        ):
            texture = (environment or {}).get("m_Texture") or {}
            texture_id = pptr(texture)
            if not texture_id:
                continue
            texture_ids.add(texture_id)
            refs.append({"property": property_name, "fileID": int(texture.get("m_FileID") or 0),
                         "pathID": texture_id, "scale": environment.get("m_Scale"),
                         "offset": environment.get("m_Offset")})
        material_rows.append({
            "pathID": identity,
            "name": data.get("m_Name"),
            "shaderPathID": SHADER_PATH_ID,
            "customRenderQueue": 3704,
            "validKeywords": data.get("m_ValidKeywords") or [],
            "textureReferences": refs,
            "payload": source_payload(data),
            "source": artifact(path, "Material"),
        })
        artifacts.append(path)

    animator_id, (animator_path, animator) = next(iter(animators.items()))
    require(pptr(animator.get("m_GameObject")) == root_id, f"{spec.name} Animator owner drifted")
    artifacts.append(animator_path)
    return ({
        "effectName": spec.name,
        "mountPoint": "",
        "summary": {
            "hierarchyNodes": 4,
            "staticMeshNodes": 3,
            "particleSystems": 0,
            "materials": len(material_rows),
            "uniqueMeshes": len(mesh_rows),
            "uniqueTextureReferences": len(texture_ids),
        },
        "effectSetting": {"pathID": path_id(setting_path, setting),
                          "timing": timing, "fields": source_payload(setting),
                          "source": artifact(setting_path, "EffectSetting")},
        "animation": {
            "animatorPathID": animator_id,
            "animator": source_payload(animator),
            "animatorSource": artifact(animator_path, "Animator"),
            "helperPathID": path_id(helper_path, helper),
            "helper": source_payload(helper),
            "helperSource": artifact(helper_path, "EffectAnimationHelper"),
            "startAnimationClip": {"fileID": int(helper["startAnimationClip"]["m_FileID"]),
                                   "pathID": ANIMATION_CLIP_PATH_ID,
                                   "sharedResolvedClip": file_artifact(
                                       SHARED_ANIMATION, "ResolvedAnimationClipYaml")},
        },
        "hierarchyNodes": hierarchy_rows,
        "staticMeshNodes": static_nodes,
        "meshDependencies": mesh_rows,
        "materials": material_rows,
        "executionBoundary": {
            "bindingKind": "static_mesh_animated",
            "sourcePayloadApplied": False,
            "sourceAnimationPayloadApplied": False,
            "rendererFailClosedForUnrecoveredShader": True,
            "visibleAdmission": False,
            "blockedBy": [
                "native Mesh payload and Unity import parity are not pinned",
                "native Texture2D mip payloads and Unity import parity are not pinned",
                "VFXBaseV2 material variants lack exact selected DXBC/descriptor/draw admission",
                "static-mesh effect prefab/import binding is not implemented",
            ],
        },
    }, artifacts, texture_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    require(SHARED_ANIMATION.is_file() and SHARED_CONTRACT.is_file(),
            "shared resolved start animation contract is missing")
    effects = []
    artifacts: list[Path] = [SHARED_ANIMATION, SHARED_CONTRACT]
    texture_ids: set[int] = set()
    for spec in SPECS:
        effect, effect_artifacts, effect_textures = build_effect(spec)
        effects.append(effect)
        artifacts.extend(effect_artifacts)
        texture_ids.update(effect_textures)
    textures = resolve_textures(texture_ids)
    artifacts.extend(REPO_ROOT / row["convertedPng"]["path"] for row in textures)
    aggregate = hashlib.sha256()
    for path in sorted(set(artifacts), key=lambda value: value.as_posix().casefold()):
        aggregate.update(path.resolve().relative_to(REPO_ROOT.resolve()).as_posix().encode())
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(sha256(path)))
    output = {
        "schema": "endfield.lizhiyan-overview-static-sibling-effects.v1",
        "status": "start02_start03_serialized_sources_closed_visible_fail_closed",
        "summary": {"effects": 2, "staticMeshNodes": 6,
                    "uniqueTextureReferences": len(texture_ids),
                    "sourceAggregateSha256": aggregate.hexdigest().upper()},
        "sharedAnimation": {
            "pathID": ANIMATION_CLIP_PATH_ID,
            "sourceContract": file_artifact(SHARED_CONTRACT, "Start01EffectContract"),
            "resolvedUnityAnim": file_artifact(SHARED_ANIMATION, "ResolvedAnimationClipYaml"),
            "bindingStatus": "all_hashes_resolved_shared_start01_start02_start03_clip",
        },
        "effects": effects,
        "textureDependencies": textures,
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file() and args.output.read_text(encoding="utf-8") == rendered,
                "Li Zhiyan sibling static-effect contract drifted")
        print("Li Zhiyan start_02/_03 contracts verified: static nodes=6, visibleAdmission=false")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: effects=2, static nodes=6, visibleAdmission=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
