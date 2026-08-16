#!/usr/bin/env python3
"""Build the fail-closed source contract for Li Zhiyan Overview start_01."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
MESH = EXPORT / "convert_by_type/Mesh/S_fx_lzy_tiaodaifenwei_01_pA111149ECDFB5C6C.obj"
ANIMATION_CLIP = (
    EXPORT / "convert_by_type/AnimationClip/"
    "A_fxui__lizhiyan_overview_start_01_p6625634E5C6BA21E.anim"
)
RESOLVED_ANIMATION_CLIP = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "A_fxui__lizhiyan_overview_start_01.anim"
)
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "lizhiyan_overview_start_01_effect.json"
)
SCHEMA = "endfield.lizhiyan-overview-start01-effect.v1"
EFFECT_NAME = "P_fxui_lizhiyan_overview_start_01"
SUFFIX = "76E5.json"
MATERIAL_PATHS = {
    2993445828574428557: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_09_p298ADB1F028DBD8D.json",
    3282333668994552481: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_10_p2D8D3114D6B992A1.json",
    -6912999194325832649: MATERIAL_ROOT / "M_fxui__lizhiyan_overview_11_pA01017DC01A5AC37.json",
}
MESH_PATH_ID = -6840663686705882004
ANIMATION_CLIP_PATH_ID = 7360398354216100382
ANIMATION_TARGET_PATHS = {
    100733734: ("P_fxui_lizhiyan_overview_start_03", "S_fx_shoutiaodai_01"),
    524802392: ("P_fxui_lizhiyan_overview_start_02", "S_fx_lzy_fenweiqiliu_02"),
    1182372393: (EFFECT_NAME, "S_fx_lzy_tiaodaifenwei_01 (4)"),
    1485209883: ("P_fxui_lizhiyan_overview_start_03", "S_fx_shoutiaodai_01 (1)"),
    1600299880: (EFFECT_NAME, "S_fx_lzy_tiaodaifenwei_01 (5)"),
    1834271210: (EFFECT_NAME, "S_fx_lzy_tiaodaifenwei_01 (7)"),
    1951396011: (EFFECT_NAME, "S_fx_lzy_tiaodaifenwei_01 (6)"),
    2367030625: ("P_fxui_lizhiyan_overview_start_02", "S_fx_lzy_fenweiqiliu_02 (1)"),
    2832407953: ("P_fxui_lizhiyan_overview_start_03", "S_fx_tuoweidisan_01"),
    3206572003: ("P_fxui_lizhiyan_overview_start_02", "S_fx_lzy_fenweiqiliu_02 (3)"),
}
ANIMATION_MATERIAL_PROPERTIES = {
    109495689: "_MainTex_ST.x",
    377931145: "_MainTex_ST.y",
    646366601: "_MainTex_ST.z",
    914802057: "_MainTex_ST.w",
    2250381253: "_DisturbUIntensity1",
    2292127880: "_TintColorAlpha",
    2316997392: "_DissolveScheduleOffset",
}


def animation_clip_contract(
    path: Path, resolved_path: Path = RESOLVED_ANIMATION_CLIP, check: bool = False
) -> dict[str, Any]:
    require(path.is_file(), f"start_01 converted AnimationClip missing: {path}")
    text = path.read_text(encoding="utf-8")
    name = re.search(r"(?m)^  m_Name: (.+)$", text)
    sample_rate = re.search(r"(?m)^  m_SampleRate: ([0-9.]+)$", text)
    stop_time = re.search(r"(?m)^    m_StopTime: ([0-9.]+)$", text)
    events = re.search(r"(?m)^  m_Events: \[\]$", text)
    bindings = re.findall(
        r"(?m)^    attribute: material\.(\d+)\r?\n"
        r"    path: path_(\d+)\r?\n"
        r"    classID: (\d+)$",
        text,
    )
    require(name and name.group(1) == "A_fxui__lizhiyan_overview_start_01",
            "start_01 AnimationClip name drifted")
    require(sample_rate and float(sample_rate.group(1)) == 30.0,
            "start_01 AnimationClip sample rate drifted")
    require(stop_time and abs(float(stop_time.group(1)) - 6.366667) < 1e-7,
            "start_01 AnimationClip stop time drifted")
    require(events is not None, "start_01 AnimationClip events drifted")
    require(len(bindings) == 53, "start_01 AnimationClip float-curve census drifted")
    require({int(row[2]) for row in bindings} == {23},
            "start_01 AnimationClip target class drifted")
    path_hashes = sorted({int(row[1]) for row in bindings})
    property_hashes = sorted({int(row[0]) for row in bindings})
    require(len(path_hashes) == 10 and len(property_hashes) == 7,
            "start_01 AnimationClip hashed binding census drifted")
    require(set(path_hashes) == set(ANIMATION_TARGET_PATHS),
            "start_01 AnimationClip target-path mapping drifted")
    require(set(property_hashes) == set(ANIMATION_MATERIAL_PROPERTIES),
            "start_01 AnimationClip material-property mapping drifted")
    resolved = text
    for value, (_, target_path) in ANIMATION_TARGET_PATHS.items():
        resolved = resolved.replace(f"path_{value}", target_path)
    for value, property_name in ANIMATION_MATERIAL_PROPERTIES.items():
        resolved = resolved.replace(f"material.{value}", f"material.{property_name}")
    require("path_" not in resolved and
            not re.search(r"attribute: material\.\d+", resolved),
            "start_01 AnimationClip resolved binding output is incomplete")
    if check:
        require(resolved_path.is_file() and
                resolved_path.read_text(encoding="utf-8") == resolved,
                "start_01 resolved AnimationClip drifted")
    else:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(resolved, encoding="utf-8")
    return {
        "name": name.group(1),
        "sampleRate": float(sample_rate.group(1)),
        "stopTime": float(stop_time.group(1)),
        "events": [],
        "floatCurveBindings": {
            "count": len(bindings),
            "targetClassID": 23,
            "targetPathHashes": path_hashes,
            "materialPropertyHashes": property_hashes,
            "targetPaths": [
                {"hash": value, "effectRoot": ANIMATION_TARGET_PATHS[value][0],
                 "path": ANIMATION_TARGET_PATHS[value][1]}
                for value in path_hashes
            ],
            "materialProperties": [
                {"hash": value, "property": ANIMATION_MATERIAL_PROPERTIES[value]}
                for value in property_hashes
            ],
            "currentEffectTargetPaths": 4,
            "siblingEffectTargetPaths": 6,
            "status": "all_hashes_resolved_shared_start01_start02_start03_clip",
        },
        "convertedAnim": file_artifact(path, "AnimationClipYaml"),
        "resolvedUnityAnim": file_artifact(resolved_path, "ResolvedAnimationClipYaml"),
    }


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_type(name: str) -> dict[int, tuple[Path, dict[str, Any]]]:
    result: dict[int, tuple[Path, dict[str, Any]]] = {}
    for path in sorted((SOURCE / name).glob(f"*{SUFFIX}")):
        data = load(path)
        identity = path_id(path, data)
        require(identity not in result, f"duplicate {name} PathID {identity}")
        result[identity] = (path, data)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    game_objects = load_type("GameObject")
    transforms = load_type("Transform")
    animators = load_type("Animator")
    filters = load_type("MeshFilter")
    renderers = load_type("MeshRenderer")
    behaviours = load_type("MonoBehaviour")
    require(len(game_objects) == 5 and len(transforms) == 5, "start_01 hierarchy census drifted")
    require(len(animators) == 1 and len(filters) == 4 and len(renderers) == 4,
            "start_01 static component census drifted")
    require(len(behaviours) == 2, "start_01 MonoBehaviour census drifted")

    transform_by_go = {pptr(row.get("m_GameObject")): identity for identity, (_, row) in transforms.items()}
    require(set(transform_by_go) == set(game_objects), "start_01 Transform owner set drifted")
    hierarchy_cache: dict[int, str] = {}

    def hierarchy(go_id: int, seen: frozenset[int] = frozenset()) -> str:
        if go_id in hierarchy_cache:
            return hierarchy_cache[go_id]
        require(go_id not in seen and go_id in transform_by_go, "hierarchy cycle or missing node")
        transform = transforms[transform_by_go[go_id]][1]
        father = pptr(transform.get("m_Father"))
        name = str(game_objects[go_id][1].get("m_Name") or go_id)
        if father:
            require(father in transforms, f"missing parent Transform {father}")
            parent_go = pptr(transforms[father][1].get("m_GameObject"))
            value = hierarchy(parent_go, seen | {go_id}) + "/" + name
        else:
            value = name
        hierarchy_cache[go_id] = value
        return value

    roots = [go_id for go_id in game_objects if hierarchy(go_id) == EFFECT_NAME]
    require(len(roots) == 1, "start_01 root drifted")
    root_id = roots[0]
    hierarchy_rows = []
    artifacts: list[Path] = []
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

    effect_path, effect_setting = next(
        (path, row) for path, row in behaviours.values() if "effectLogicCfg" in row
    )
    helper_path, animation_helper = next(
        (path, row) for path, row in behaviours.values() if "startAnimationClip" in row
    )
    timing = effect_setting["effectLogicCfg"]
    require(timing == {
        "isLoop": 0, "duration": 2.2, "randomDelay": 0, "delay": 0.0,
        "range": {"x": 0.0, "y": 0.0}, "fadeoutTime": 0.0,
        "timeScaleMode": 0, "autoFade": 0, "startFadeTime": 0.0,
        "endFadeTime": 0.0,
    }, "start_01 EffectSetting timing drifted")
    require(pptr(animation_helper["startAnimationClip"]) == ANIMATION_CLIP_PATH_ID and
            pptr(animation_helper["loopAnimationClip"]) == 0 and
            pptr(animation_helper["endAnimationClip"]) == 0 and
            int(animation_helper["isEnableChangeState"]) == 1,
            "start_01 animation helper drifted")
    artifacts.extend((effect_path, helper_path))

    filters_by_go = {pptr(row.get("m_GameObject")): (identity, path, row)
                     for identity, (path, row) in filters.items()}
    renderers_by_go = {pptr(row.get("m_GameObject")): (identity, path, row)
                       for identity, (path, row) in renderers.items()}
    require(set(filters_by_go) == set(renderers_by_go) == set(game_objects) - {root_id},
            "start_01 static renderer owner set drifted")
    material_ids: set[int] = set()
    static_nodes = []
    for go_id in sorted(filters_by_go, key=hierarchy):
        filter_id, filter_path, mesh_filter = filters_by_go[go_id]
        renderer_id, renderer_path, renderer = renderers_by_go[go_id]
        require(int(mesh_filter["m_Mesh"]["m_FileID"]) == 2 and
                pptr(mesh_filter["m_Mesh"]) == MESH_PATH_ID,
                "start_01 mesh identity drifted")
        ids = [pptr(row) for row in renderer.get("m_Materials") or []]
        require(len(ids) == 1 and ids[0] in MATERIAL_PATHS,
                "start_01 material identity drifted")
        material_ids.update(ids)
        static_nodes.append({
            "hierarchy": hierarchy(go_id),
            "gameObjectPathID": go_id,
            "meshFilterPathID": filter_id,
            "meshRendererPathID": renderer_id,
            "mesh": {"fileID": 2, "pathID": MESH_PATH_ID},
            "materials": [{"fileID": 4, "pathID": ids[0]}],
            "meshFilter": source_payload(mesh_filter),
            "meshRenderer": source_payload(renderer),
            "meshFilterSource": artifact(filter_path, "MeshFilter"),
            "meshRendererSource": artifact(renderer_path, "MeshRenderer"),
        })
        artifacts.extend((filter_path, renderer_path))
    require(material_ids == set(MATERIAL_PATHS), "start_01 material set drifted")
    require(MESH.is_file(), "start_01 converted mesh missing")
    artifacts.append(MESH)

    material_rows = []
    texture_reference_ids: set[int] = set()
    for identity, path in sorted(MATERIAL_PATHS.items()):
        require(path.is_file(), f"start_01 material {identity} missing")
        data = load(path)
        require(path_id(path, data) == identity and
                pptr(data.get("m_Shader")) == -1430105248647086886 and
                int(data.get("m_CustomRenderQueue") or 0) == 3704,
                f"start_01 material {identity} ABI drifted")
        texture_references = []
        texture_environments = ((data.get("m_SavedProperties") or {}).get("m_TexEnvs") or {})
        for property_name, environment in sorted(texture_environments.items()):
            texture = (environment or {}).get("m_Texture") or {}
            texture_id = int(texture.get("m_PathID") or 0)
            if not texture_id:
                continue
            texture_reference_ids.add(texture_id)
            texture_references.append({
                "property": property_name,
                "fileID": int(texture.get("m_FileID") or 0),
                "pathID": texture_id,
                "scale": environment.get("m_Scale"),
                "offset": environment.get("m_Offset"),
            })
        material_rows.append({
            "pathID": identity,
            "name": data.get("m_Name"),
            "shaderPathID": pptr(data.get("m_Shader")),
            "customRenderQueue": int(data.get("m_CustomRenderQueue") or 0),
            "validKeywords": data.get("m_ValidKeywords") or [],
            "textureReferences": texture_references,
            "payload": source_payload(data),
            "source": artifact(path, "Material"),
        })
        artifacts.append(path)

    require(len(texture_reference_ids) == 8, "start_01 texture dependency census drifted")
    texture_dependencies = resolve_textures(texture_reference_ids)
    artifacts.extend(REPO_ROOT / row["convertedPng"]["path"] for row in texture_dependencies)
    clip = animation_clip_contract(ANIMATION_CLIP, check=args.check)
    artifacts.append(ANIMATION_CLIP)

    animator_id, (animator_path, animator) = next(iter(animators.items()))
    require(pptr(animator.get("m_GameObject")) == root_id, "start_01 Animator owner drifted")
    artifacts.append(animator_path)
    aggregate = hashlib.sha256()
    for path in sorted(set(artifacts), key=lambda row: row.as_posix().casefold()):
        aggregate.update(path.resolve().relative_to(REPO_ROOT.resolve()).as_posix().encode())
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(sha256(path)))

    contract = {
        "schema": SCHEMA,
        "status": "static_mesh_animation_and_texture_sources_closed_visible_fail_closed",
        "effectName": EFFECT_NAME,
        "mountPoint": "",
        "summary": {
            "hierarchyNodes": 5,
            "staticMeshNodes": 4,
            "particleSystems": 0,
            "materials": 3,
            "uniqueMeshes": 1,
            "uniqueTextureReferences": 8,
            "sourceAggregateSha256": aggregate.hexdigest().upper(),
        },
        "effectSetting": {
            "pathID": path_id(effect_path, effect_setting),
            "source": artifact(effect_path, "EffectSetting"),
            "fields": source_payload(effect_setting),
            "timing": timing,
        },
        "animation": {
            "animatorPathID": animator_id,
            "animator": source_payload(animator),
            "animatorSource": artifact(animator_path, "Animator"),
            "helperPathID": path_id(helper_path, animation_helper),
            "helper": source_payload(animation_helper),
            "helperSource": artifact(helper_path, "EffectAnimationHelper"),
            "startAnimationClip": {
                "fileID": int(animation_helper["startAnimationClip"]["m_FileID"]),
                "pathID": ANIMATION_CLIP_PATH_ID,
                "status": "converted_source_payload_closed",
                **clip,
            },
            "loopAnimationClip": None,
            "endAnimationClip": None,
        },
        "hierarchyNodes": hierarchy_rows,
        "staticMeshNodes": static_nodes,
        "meshDependency": {
            "fileID": 2,
            "pathID": MESH_PATH_ID,
            "convertedObj": file_artifact(MESH, "MeshObj"),
            "nativePayloadStatus": "converted_obj_present_native_mesh_payload_not_pinned",
        },
        "materials": material_rows,
        "textureDependencies": texture_dependencies,
        "executionBoundary": {
            "bindingKind": "static_mesh_animated",
            "sourcePayloadApplied": False,
            "sourceAnimationPayloadApplied": False,
            "rendererFailClosedForUnrecoveredShader": True,
            "visibleAdmission": False,
            "blockedBy": [
                "native Mesh payload and Unity import parity are not pinned",
                "native Texture2D mip payloads and Unity import parity are not pinned",
                "three VFXBaseV2 material variants lack exact selected DXBC/descriptor/draw admission",
                "static-mesh effect runtime binding kind is not implemented",
            ],
        },
    }
    rendered = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file(), "start_01 output missing")
        require(args.output.read_text(encoding="utf-8") == rendered, "start_01 output drifted")
        print("Li Zhiyan start_01 contract verified: static nodes=4, visibleAdmission=false")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: static nodes=4, materials=3, visibleAdmission=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
