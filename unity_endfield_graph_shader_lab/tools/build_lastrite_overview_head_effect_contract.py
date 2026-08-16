#!/usr/bin/env python3
"""Build the exact serialized contract for Last Rite's head Overview effect."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_SOURCE = REPO_ROOT / "scratch/character_recovery/lastrite_effect_materialization"
DEFAULT_OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "lastrite_overview_head_effect.json"
)
EFFECT_NAME = "P_fxui_lastrite_ui_overview_start_01_01"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def path_id(path: Path, data: dict[str, Any]) -> int:
    metadata = data.get("$animestudio") or {}
    if "pathId" in metadata:
        return int(metadata["pathId"])
    match = re.search(r"_p([0-9A-Fa-f]{16})", path.name)
    require(match is not None, f"PathID is absent from {path}")
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def pptr(value: Any) -> int:
    return int(value.get("m_PathID") or 0) if isinstance(value, dict) else 0


def artifact(path: Path, object_type: str) -> dict[str, Any]:
    data = load(path)
    metadata = data.get("$animestudio") or {}
    return {
        "path": path.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "objectType": object_type,
        "pathID": path_id(path, data),
        "sourceFile": metadata.get("sourceFile"),
        "sourceOffset": metadata.get("sourceOffset"),
        "rawDataLength": metadata.get("rawDataLength"),
        "rawDataSha256": str(metadata.get("rawDataSha256") or "").upper() or None,
        "typeTreeSource": metadata.get("typeTreeSource"),
    }


def load_type(root: Path, name: str) -> dict[int, tuple[Path, dict[str, Any]]]:
    result: dict[int, tuple[Path, dict[str, Any]]] = {}
    for path in sorted((root / name).glob("*.json")):
        data = load(path)
        identity = path_id(path, data)
        require(identity not in result, f"duplicate {name} PathID {identity}")
        result[identity] = (path, data)
    return result


def source_payload(data: dict[str, Any]) -> dict[str, Any]:
    # `Name` is AnimeStudio's convenience identity field, not a serialized
    # Unity member. The authoritative serialized name remains `m_Name`.
    return {
        key: value
        for key, value in data.items()
        if key not in {"$animestudio", "Name"}
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    prefab_root = args.source_root / "export2"
    mesh_component_root = args.source_root / "mesh_components"
    material_root = args.source_root / "materials"
    mesh_root = args.source_root / "mesh"
    game_objects = load_type(prefab_root, "GameObject")
    transforms = load_type(prefab_root, "Transform")
    systems = load_type(prefab_root, "ParticleSystem")
    renderers = load_type(prefab_root, "ParticleSystemRenderer")
    behaviours = load_type(prefab_root, "MonoBehaviour")
    mesh_renderers = load_type(mesh_component_root, "MeshRenderer")
    mesh_filters = load_type(mesh_component_root, "MeshFilter")
    materials = load_type(material_root, "Material")
    meshes = load_type(mesh_root, "Mesh")

    require(len(game_objects) == 8 and len(transforms) == 8, "expected 8 hierarchy nodes")
    require(len(systems) == 5 and len(renderers) == 5, "expected 5 particle pairs")
    require(len(behaviours) == 2, "expected animation-switch plus EffectSetting behaviours")
    require(len(mesh_renderers) == 1 and len(mesh_filters) == 1, "expected one head mesh pair")
    require(len(materials) == 6 and len(meshes) == 1, "dependency census drifted")

    transform_by_go: dict[int, int] = {}
    for transform_id, (_, transform) in transforms.items():
        go_id = pptr(transform.get("m_GameObject"))
        require(go_id in game_objects and go_id not in transform_by_go, "invalid Transform owner")
        transform_by_go[go_id] = transform_id

    hierarchy_cache: dict[int, str] = {}

    def hierarchy(go_id: int, seen: frozenset[int] = frozenset()) -> str:
        if go_id in hierarchy_cache:
            return hierarchy_cache[go_id]
        require(go_id not in seen and go_id in transform_by_go, "hierarchy cycle or missing node")
        transform_id = transform_by_go[go_id]
        transform = transforms[transform_id][1]
        father_id = pptr(transform.get("m_Father"))
        name = str(game_objects[go_id][1].get("m_Name") or f"GameObject#{go_id}")
        if father_id and father_id in transforms:
            parent_go = pptr(transforms[father_id][1].get("m_GameObject"))
            value = hierarchy(parent_go, seen | {go_id}) + "/" + name
        else:
            value = name
        hierarchy_cache[go_id] = value
        return value

    roots = [go_id for go_id in game_objects if hierarchy(go_id) == EFFECT_NAME]
    require(len(roots) == 1, "exact effect root is not unique")

    hierarchy_nodes = []
    artifact_paths: list[Path] = []
    for go_id in sorted(game_objects, key=hierarchy):
        go_path, game_object = game_objects[go_id]
        transform_id = transform_by_go[go_id]
        transform_path, transform = transforms[transform_id]
        hierarchy_nodes.append(
            {
                "hierarchy": hierarchy(go_id),
                "gameObjectPathID": go_id,
                "transformPathID": transform_id,
                "gameObject": source_payload(game_object),
                "transform": source_payload(transform),
                "gameObjectSource": artifact(go_path, "GameObject"),
                "transformSource": artifact(transform_path, "Transform"),
            }
        )
        artifact_paths.extend((go_path, transform_path))

    systems_by_go = {pptr(data.get("m_GameObject")): (path, data) for path, data in systems.values()}
    renderers_by_go = {pptr(data.get("m_GameObject")): (path, data) for path, data in renderers.values()}
    require(set(systems_by_go) == set(renderers_by_go), "particle/renderer owners differ")
    particle_pairs = []
    referenced_materials: set[int] = set()
    for go_id in sorted(systems_by_go, key=hierarchy):
        system_path, system = systems_by_go[go_id]
        renderer_path, renderer = renderers_by_go[go_id]
        enabled_modules = {
            key: value
            for key, value in system.items()
            if key.endswith("Module") and isinstance(value, dict) and bool(value.get("enabled"))
        }
        fields = {
            key: value
            for key, value in system.items()
            if key != "$animestudio" and not key.endswith("Module")
        }
        renderer_fields = source_payload(renderer)
        referenced_materials.update(
            pptr(value) for value in renderer.get("m_Materials") or [] if pptr(value)
        )
        particle_pairs.append(
            {
                "hierarchy": hierarchy(go_id),
                "gameObjectPathID": go_id,
                "particleSystem": {
                    "source": artifact(system_path, "ParticleSystem"),
                    "fields": fields,
                    "enabledModules": enabled_modules,
                },
                "renderer": {
                    "source": artifact(renderer_path, "ParticleSystemRenderer"),
                    "fields": renderer_fields,
                },
            }
        )
        artifact_paths.extend((system_path, renderer_path))

    effect_settings = []
    animation_switches = []
    for behaviour_path, behaviour in behaviours.values():
        if "effectLogicCfg" in behaviour:
            effect_settings.append((behaviour_path, behaviour))
        else:
            animation_switches.append((behaviour_path, behaviour))
    require(len(effect_settings) == 1 and len(animation_switches) == 1, "behaviour classification drifted")
    setting_path, setting = effect_settings[0]
    timing = setting["effectLogicCfg"]
    require(timing == {
        "isLoop": 0,
        "duration": 13.5,
        "randomDelay": 0,
        "delay": 3.5,
        "range": {"x": 0.0, "y": 0.0},
        "fadeoutTime": 0.0,
        "timeScaleMode": 0,
        "autoFade": 0,
        "startFadeTime": 0.0,
        "endFadeTime": 0.0,
    }, "EffectSetting timing drifted")
    artifact_paths.extend(path for path, _ in effect_settings + animation_switches)

    mesh_renderer_path, mesh_renderer = next(iter(mesh_renderers.values()))
    mesh_filter_path, mesh_filter = next(iter(mesh_filters.values()))
    referenced_materials.update(
        pptr(value) for value in mesh_renderer.get("m_Materials") or [] if pptr(value)
    )
    referenced_mesh = pptr(mesh_filter.get("m_Mesh"))
    require(referenced_materials == set(materials), "material dependency set drifted")
    require(referenced_mesh in meshes and len(meshes) == 1, "head mesh dependency drifted")
    artifact_paths.extend((mesh_renderer_path, mesh_filter_path))

    material_rows = []
    for identity in sorted(materials):
        path, data = materials[identity]
        material_rows.append(
            {
                "pathID": identity,
                "name": data.get("m_Name"),
                "shaderPathID": pptr(data.get("m_Shader")),
                "validKeywords": data.get("m_ValidKeywords") or [],
                "invalidKeywords": data.get("m_InvalidKeywords") or [],
                "customRenderQueue": int(data.get("m_CustomRenderQueue") or 0),
                "source": artifact(path, "Material"),
            }
        )
        artifact_paths.append(path)
    require({row["shaderPathID"] for row in material_rows} == {-1430105248647086886}, "shader identity drifted")

    mesh_path, mesh = meshes[referenced_mesh]
    artifact_paths.append(mesh_path)
    aggregate = hashlib.sha256()
    for path in sorted(set(artifact_paths), key=lambda value: value.as_posix().casefold()):
        aggregate.update(path.resolve().relative_to(REPO_ROOT.resolve()).as_posix().encode())
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(sha256(path)))

    output = {
        "schema": "endfield.lastrite-overview-head-effect.v1",
        "status": "source_serialized_payload_closed_visual_shaders_fail_closed",
        "effectName": EFFECT_NAME,
        "summary": {
            "hierarchyNodes": len(hierarchy_nodes),
            "particlePairs": len(particle_pairs),
            "materials": len(material_rows),
            "meshRenderers": 1,
            "sourceAggregateSha256": aggregate.hexdigest().upper(),
        },
        "effectSetting": {
            "source": artifact(setting_path, "EffectSetting"),
            "fields": source_payload(setting),
            "timing": timing,
        },
        "animationSwitch": {
            "source": artifact(animation_switches[0][0], "EffectAnimationSwitch"),
            "fields": source_payload(animation_switches[0][1]),
        },
        "hierarchyNodes": hierarchy_nodes,
        "particlePairs": particle_pairs,
        "meshRenderer": {
            "hierarchy": hierarchy(pptr(mesh_renderer.get("m_GameObject"))),
            "rendererSource": artifact(mesh_renderer_path, "MeshRenderer"),
            "rendererFields": source_payload(mesh_renderer),
            "filterSource": artifact(mesh_filter_path, "MeshFilter"),
            "filterFields": source_payload(mesh_filter),
            "mesh": {
                "pathID": referenced_mesh,
                "name": mesh.get("m_Name"),
                "source": artifact(mesh_path, "Mesh"),
                "payload": source_payload(mesh),
            },
        },
        "materials": material_rows,
        "executionBoundary": (
            "Hierarchy, local transforms, EffectSetting timing, ParticleSystem and renderer payloads, "
            "head mesh, and material/shader identities are source-closed. All six materials remain "
            "ColorMask-0 fail-closed until each exact HGRP/Effect/VFXBaseV2 specialization and texture "
            "dependency is admitted; no visual approximation is generated."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output}: nodes={len(hierarchy_nodes)} particles={len(particle_pairs)} "
        f"materials={len(material_rows)} aggregate={output['summary']['sourceAggregateSha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
