#!/usr/bin/env python3
"""Build the exact serialized contract for Li Zhiyan's mounted finger effect."""

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
    resolve_textures,
    sha256,
    source_payload,
)


LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "scratch/character_recovery/lizhiyan_trail_candidate"
DEFAULT_NATIVE_TEXTURE_ROOT = (
    REPO_ROOT / "scratch/character_recovery/lizhiyan_native_textures/export/Texture2D"
)
DEFAULT_OUTPUT = (
    LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "lizhiyan_overview_finger_effect.json"
)
EFFECT_NAME = "P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub"


def resolve_native_texture_payloads(root: Path, texture_ids: set[int]) -> list[dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for manifest_path in sorted(root.glob("*.texture2d.*.manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        path_id = int(manifest.get("pathId") or 0)
        if path_id not in texture_ids:
            continue
        require(path_id not in rows, f"duplicate native texture payload for {path_id}")
        require(manifest.get("schema") == "animestudio.texture2d-native-payload.v1", "native texture schema drifted")
        require(manifest.get("format") == "BC7", f"native texture {path_id} is not BC7")
        require(manifest.get("mipsStripped") == 0, f"native texture {path_id} has stripped mips")
        require(manifest.get("imageCount") == 1 and manifest.get("textureDimension") == 2,
                f"native texture {path_id} is not a single 2D image")
        payload_info = manifest.get("payload") or {}
        require(payload_info.get("layoutValidated") is True, f"native texture {path_id} layout is unvalidated")
        payload_path = manifest_path.with_name(str(payload_info.get("file") or ""))
        require(payload_path.is_file(), f"missing native texture payload for {path_id}")
        require(payload_path.stat().st_size == int(payload_info.get("bytes") or -1),
                f"native texture {path_id} byte count drifted")
        require(sha256(payload_path) == str(payload_info.get("sha256") or "").upper(),
                f"native texture {path_id} hash drifted")
        rows[path_id] = {
            "pathID": path_id,
            "name": manifest.get("name"),
            "format": manifest.get("format"),
            "width": manifest.get("width"),
            "height": manifest.get("height"),
            "mipCount": manifest.get("mipCount"),
            "colorSpace": manifest.get("colorSpace"),
            "textureSettings": manifest.get("textureSettings"),
            "payload": {
                "path": payload_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
                "bytes": payload_path.stat().st_size,
                "sha256": sha256(payload_path),
                "objectType": "Texture2DNativePayload",
                "pathID": path_id,
            },
            "manifest": artifact(manifest_path, "Texture2DNativePayloadManifest"),
            "mipDimensions": payload_info.get("mipDimensions"),
        }
    require(set(rows) == texture_ids, "native texture payload set does not match material references")
    return [rows[path_id] for path_id in sorted(rows)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--native-texture-root", type=Path, default=DEFAULT_NATIVE_TEXTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    prefab_root = args.source_root / "prefab"
    material_root = args.source_root / "materials"
    game_objects = load_type(prefab_root, "GameObject")
    transforms = load_type(prefab_root, "Transform")
    systems = load_type(prefab_root, "ParticleSystem")
    renderers = load_type(prefab_root, "ParticleSystemRenderer")
    behaviours = load_type(prefab_root, "MonoBehaviour")
    materials = load_type(material_root, "Material")
    require(len(game_objects) == 8 and len(transforms) == 8, "expected 8 hierarchy nodes")
    require(len(systems) == 7 and len(renderers) == 7, "expected 7 particle pairs")
    require(len(behaviours) == 1 and len(materials) == 6, "dependency census drifted")

    transform_by_go = {pptr(data.get("m_GameObject")): identity for identity, (_, data) in transforms.items()}
    require(len(transform_by_go) == 8, "Transform owner set drifted")
    hierarchy_cache: dict[int, str] = {}

    def hierarchy(go_id: int, seen: frozenset[int] = frozenset()) -> str:
        if go_id in hierarchy_cache:
            return hierarchy_cache[go_id]
        require(go_id not in seen and go_id in transform_by_go, "hierarchy cycle or missing node")
        transform = transforms[transform_by_go[go_id]][1]
        father_id = pptr(transform.get("m_Father"))
        name = str(game_objects[go_id][1].get("m_Name") or f"GameObject#{go_id}")
        if father_id and father_id in transforms:
            parent_go = pptr(transforms[father_id][1].get("m_GameObject"))
            value = hierarchy(parent_go, seen | {go_id}) + "/" + name
        else:
            value = name
        hierarchy_cache[go_id] = value
        return value

    require(sum(hierarchy(go_id) == EFFECT_NAME for go_id in game_objects) == 1, "root drifted")
    artifact_paths: list[Path] = []
    hierarchy_nodes = []
    for go_id in sorted(game_objects, key=hierarchy):
        go_path, game_object = game_objects[go_id]
        transform_id = transform_by_go[go_id]
        transform_path, transform = transforms[transform_id]
        hierarchy_nodes.append({
            "hierarchy": hierarchy(go_id),
            "gameObjectPathID": go_id,
            "transformPathID": transform_id,
            "gameObject": source_payload(game_object),
            "transform": source_payload(transform),
            "gameObjectSource": artifact(go_path, "GameObject"),
            "transformSource": artifact(transform_path, "Transform"),
        })
        artifact_paths.extend((go_path, transform_path))

    systems_by_go = {pptr(data.get("m_GameObject")): (path, data) for path, data in systems.values()}
    renderers_by_go = {pptr(data.get("m_GameObject")): (path, data) for path, data in renderers.values()}
    require(set(systems_by_go) == set(renderers_by_go), "particle renderer owners differ")
    particle_pairs = []
    referenced_materials: set[int] = set()
    for go_id in sorted(systems_by_go, key=hierarchy):
        system_path, system = systems_by_go[go_id]
        renderer_path, renderer = renderers_by_go[go_id]
        referenced_materials.update(pptr(value) for value in renderer.get("m_Materials") or [] if pptr(value))
        particle_pairs.append({
            "hierarchy": hierarchy(go_id),
            "gameObjectPathID": go_id,
            "particleSystem": {
                "source": artifact(system_path, "ParticleSystem"),
                "fields": {key: value for key, value in system.items() if key != "$animestudio" and not key.endswith("Module")},
                "enabledModules": {key: value for key, value in system.items() if key.endswith("Module") and isinstance(value, dict) and bool(value.get("enabled"))},
            },
            "renderer": {"source": artifact(renderer_path, "ParticleSystemRenderer"), "fields": source_payload(renderer)},
        })
        artifact_paths.extend((system_path, renderer_path))
    require(referenced_materials == set(materials), "material reference set drifted")

    setting_path, setting = next(iter(behaviours.values()))
    timing = setting.get("effectLogicCfg")
    require(timing == {
        "isLoop": 0, "duration": 2.33333, "randomDelay": 0, "delay": 0.83333,
        "range": {"x": 0.0, "y": 0.0}, "fadeoutTime": 0.0, "timeScaleMode": 0,
        "autoFade": 0, "startFadeTime": 0.0, "endFadeTime": 0.0,
    }, "EffectSetting timing drifted")
    artifact_paths.append(setting_path)

    texture_ids: set[int] = set()
    material_rows = []
    for identity in sorted(materials):
        path, data = materials[identity]
        refs = []
        for prop, environment in sorted(((data.get("m_SavedProperties") or {}).get("m_TexEnvs") or {}).items()):
            texture = (environment or {}).get("m_Texture") or {}
            texture_id = int(texture.get("m_PathID") or 0)
            if not texture_id:
                continue
            texture_ids.add(texture_id)
            refs.append({"property": prop, "fileID": int(texture.get("m_FileID") or 0), "pathID": texture_id,
                         "scale": environment.get("m_Scale"), "offset": environment.get("m_Offset")})
        material_rows.append({
            "pathID": identity, "name": data.get("m_Name"), "shaderPathID": pptr(data.get("m_Shader")),
            "validKeywords": data.get("m_ValidKeywords") or [], "invalidKeywords": data.get("m_InvalidKeywords") or [],
            "customRenderQueue": int(data.get("m_CustomRenderQueue") or 0), "textureReferences": refs,
            "payload": source_payload(data), "source": artifact(path, "Material"),
        })
        artifact_paths.append(path)
    require({row["shaderPathID"] for row in material_rows} == {-1430105248647086886}, "shader identity drifted")
    texture_dependencies = resolve_textures(texture_ids)
    artifact_paths.extend(REPO_ROOT / row["convertedPng"]["path"] for row in texture_dependencies)
    native_texture_payloads = resolve_native_texture_payloads(args.native_texture_root, texture_ids)
    for row in native_texture_payloads:
        artifact_paths.append(REPO_ROOT / row["payload"]["path"])
        artifact_paths.append(REPO_ROOT / row["manifest"]["path"])

    aggregate = hashlib.sha256()
    for path in sorted(set(artifact_paths), key=lambda value: value.as_posix().casefold()):
        aggregate.update(path.resolve().relative_to(REPO_ROOT.resolve()).as_posix().encode())
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(sha256(path)))

    output: dict[str, Any] = {
        "schema": "endfield.lizhiyan-overview-finger-effect.v2",
        "status": "source_serialized_payload_closed_visual_shaders_fail_closed",
        "effectName": EFFECT_NAME,
        "mountPoint": "Bip001_R_Finger2Nub",
        "summary": {"hierarchyNodes": 8, "particlePairs": 7, "materials": 6,
                    "uniqueTextureReferences": len(texture_ids), "sourceAggregateSha256": aggregate.hexdigest().upper()},
        "effectSetting": {"source": artifact(setting_path, "EffectSetting"), "fields": source_payload(setting), "timing": timing},
        "hierarchyNodes": hierarchy_nodes, "particlePairs": particle_pairs, "materials": material_rows,
        "textureDependencyBoundary": {"uniquePathIDs": sorted(texture_ids), "textures": texture_dependencies,
            "nativePayloads": native_texture_payloads,
            "status": "assetmap_converted_png_and_bc7_native_mip_sampling_metadata_closed"},
        "executionBoundary": "Hierarchy, transforms, timing, particle payloads, material payloads, converted texture identities, original BC7 mip chains, and serialized sampler settings are source-closed. Materials remain ColorMask-0 until the selected retail VFXBaseV2 variant, descriptors, draw/PSO/MRT, depth, and compositing contract is admitted.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}: nodes=8 particles=7 materials=6 textures={len(texture_ids)} aggregate={output['summary']['sourceAggregateSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
