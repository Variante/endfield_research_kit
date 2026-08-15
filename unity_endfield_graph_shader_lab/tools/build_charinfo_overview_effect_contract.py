#!/usr/bin/env python3
"""Build the exact shared Character Info CharEffect particle contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = (
    REPO_ROOT
    / "scratch/character_recovery/charinfo_generic_entry_effect/json_filtered"
)
MATERIAL_PATH = (
    REPO_ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material"
    / "M_UI_charChoose_12_p3CE8306B7872A127.json"
)
TEXTURE_PATH = (
    REPO_ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D"
    / "T_fx_mask_01_M_p9E34304E227EA66A.png"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "char_effect_particle_contract.json"
)

SCHEMA = "endfield.charinfo-char-effect-particle.v1"
SOURCE_FILE = "CAB-45edfbd38d2a68534810c905ce39aff4"
PREFAB_CONTAINER = (
    "assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfochar.prefab"
)

OBJECTS = (
    {
        "hierarchy": "CharEffect",
        "game_object": ("GameObject/CharEffect_p0B2704F0A2976703.json", 803616490075416323),
        "transform": ("Transform/Transform#753_p56B221180B806703.json", 6247092020272195331),
        "particle_system": ("ParticleSystem/ParticleSystem#521_p149F8BEA81526703.json", 1486060241363822339),
        "particle_renderer": ("ParticleSystemRenderer/ParticleSystemRenderer#440_pFE71EA7C768D6703.json", -112050695421729021),
    },
    {
        "hierarchy": "CharEffect/trail",
        "game_object": ("GameObject/trail_p29D31B6D060E6703.json", 3013782730707986179),
        "transform": ("Transform/Transform#691_p458D38C3439E6703.json", 5011724371637462787),
        "particle_system": ("ParticleSystem/ParticleSystem#831_p70998C93AB686703.json", 8113670769548486403),
        "particle_renderer": ("ParticleSystemRenderer/ParticleSystemRenderer#719_p4FE5DB2B7CA56703.json", 5757248678484338435),
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def load_source(relative: str, expected_path_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    path = SOURCE_ROOT / relative
    require(path.is_file(), f"missing source JSON: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = data.get("$animestudio") or {}
    encoded_path_id = f"{expected_path_id & ((1 << 64) - 1):016X}"
    require(
        int(metadata.get("pathId") or expected_path_id) == expected_path_id
        and f"_p{encoded_path_id}.json" in path.name,
        f"PathID drift: {path}",
    )
    require(
        not metadata or metadata.get("sourceFile") == SOURCE_FILE,
        f"source CAB drift: {path}",
    )
    return (
        {key: value for key, value in data.items() if key != "$animestudio"},
        {
            "path": repo_path(path),
            "jsonBytes": path.stat().st_size,
            "jsonSha256": sha256(path),
            "pathID": expected_path_id,
            "rawDataLength": int(metadata.get("rawDataLength") or 0),
            "rawDataSha256": str(metadata.get("rawDataSha256") or "").upper(),
            "sourceFile": metadata.get("sourceFile"),
            "sourceOffset": int(metadata.get("sourceOffset") or 0),
            "typeTreeSource": metadata.get("typeTreeSource"),
        },
    )


def build() -> dict[str, Any]:
    nodes = []
    for spec in OBJECTS:
        row: dict[str, Any] = {"hierarchy": spec["hierarchy"]}
        for key in ("game_object", "transform", "particle_system", "particle_renderer"):
            relative, expected = spec[key]
            fields, source = load_source(relative, expected)
            row[key] = fields
            row[key + "_source"] = source
        nodes.append(row)

    material = json.loads(MATERIAL_PATH.read_text(encoding="utf-8"))
    material_meta = material.get("$animestudio") or {}
    require(
        int(material_meta.get("pathId") or 4388811075012960551) == 4388811075012960551
        and "_p3CE8306B7872A127.json" in MATERIAL_PATH.name,
        "material PathID drift",
    )
    require(material.get("m_Name") == "M_UI_charChoose_12", "material name drift")
    require(material.get("m_ValidKeywords") == ["_USE_RBOFFSET"], "keyword drift")
    require(int(material.get("m_CustomRenderQueue")) == 3000, "queue drift")
    require(TEXTURE_PATH.is_file(), f"missing exact texture: {TEXTURE_PATH}")

    single_effects, single_effects_source = load_source(
        "GameObject/SingleEffects_p7A53C6AFBBE86703.json",
        8814607353768339203,
    )
    single_effects_transform, single_effects_transform_source = load_source(
        "Transform/Transform#306_pDC8E3F3C0A6B6703.json",
        -2554034411567094013,
    )
    mount_position = single_effects_transform["m_LocalPosition"]
    mount_scale = single_effects_transform["m_LocalScale"]
    require(mount_position == {"X": -0.3, "Y": 0.0, "Z": 0.05}, "SingleEffects position drift")
    require(mount_scale == {"X": 0.5, "Y": 1.0, "Z": 0.5}, "SingleEffects scale drift")

    return {
        "schema": SCHEMA,
        "source_prefab": PREFAB_CONTAINER,
        "source_serialized_file": SOURCE_FILE,
        "effect_root": "CharEffect",
        "mount_owner": "sceneObject.view.singleEffects/effect<height>",
        "play_owner": "PhaseCharInfo._PlayModelEffect -> effect:Play()",
        "scene_mount": {
            "gameObjectPathID": 8814607353768339203,
            "transformPathID": -2554034411567094013,
            "localPosition": mount_position,
            "localRotation": single_effects_transform["m_LocalRotation"],
            "localScale": mount_scale,
            "heightBuckets": {
                "effect1": {"name": "GirlFlattie", "transformPathID": -2372154738899982589},
                "effect2": {"name": "GirlHighHeel", "transformPathID": -7077363634982000893},
                "effect3": {"name": "Female", "transformPathID": -3136265006245255421},
                "effect4": {"name": "Male", "transformPathID": -3173405536942987517},
            },
            "gameObject": single_effects,
            "gameObjectSource": single_effects_source,
            "transformSource": single_effects_transform_source,
            "boundary": "Height choice is table-owned; all four serialized bucket transforms are local identity.",
        },
        "nodes": nodes,
        "material": {
            "pathID": 4388811075012960551,
            "name": "M_UI_charChoose_12",
            "shaderPathID": 7766268189260370413,
            "shaderName": "HGRP/Effect/VFXRefract",
            "recoveredShaderName": "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT",
            "fields": {key: value for key, value in material.items() if key != "$animestudio"},
            "source": {
                "path": repo_path(MATERIAL_PATH),
                "jsonBytes": MATERIAL_PATH.stat().st_size,
                "jsonSha256": sha256(MATERIAL_PATH),
            },
        },
        "texture": {
            "pathID": -7046954404783675798,
            "name": "T_fx_mask_01_M",
            "property": "_RefractTex",
            "path": repo_path(TEXTURE_PATH),
            "bytes": TEXTURE_PATH.stat().st_size,
            "sha256": sha256(TEXTURE_PATH),
        },
        "execution_gate": {
            "queue": 3000,
            "lightMode": "Distortion",
            "keywords": ["HG_ENABLE_MV", "_USE_RBOFFSET"],
            "fragmentDxbcHash": "f905de094d0261d5",
            "sceneMvFormat": "A2B10G10R10_UNormPack32",
            "selectedTarget1": [0.0, 0.0, 1.0, 0.0],
        },
        "boundary": (
            "Exact serialized hierarchy, ParticleSystem/renderer payloads, material, texture, "
            "and selected MRT shader branch. Runtime culling/sorting and live VFX globals "
            "remain validation requirements."
        ),
    }


def main() -> int:
    contract = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes, sha256={sha256(OUTPUT)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
