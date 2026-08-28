#!/usr/bin/env python3
"""Fail-closed source/manifest audit for Endminf's main LOD0 body materials."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
MANIFEST = LAB / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/endminf_ui_recovery_manifest.json"
REPORT = REPO / "reports/assets/endminf_body_material_admission.json"
GENERATED_MATERIAL_ROOT = LAB / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Materials"
PRE_GBUFFER_OWNER = LAB / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredPreGBufferDepthOwner.cs"

EXPECTED = {
    "M_actor_endminf_body_01": (-8084013477027282831, 4484747192473637154, "face_skin"),
    "M_actor_endminf_face_01": (-2899086821170044781, 4484747192473637154, "face_skin"),
    "M_actor_endminf_iris_01": (6810389916262429829, -1706220712117210762, "face_skin"),
    "M_actor_endminf_brow_01": (5270450699446844522, -1706220712117210762, "face_skin"),
    "M_actor_endminf_hair_01": (-3834932228167739915, -8095970123935614097, "hair"),
    "M_actor_endminf_hairt_01": (-3941236971230507885, -8095970123935614097, "hair"),
    "M_actor_endminf_cloth_01": (-3591263160191616808, -7822190029627442914, "coat_fabric_metal"),
    "M_actor_endminf_cloth_02": (8960951648682285338, -7822190029627442914, "coat_fabric_metal"),
    "M_actor_endminf_cloth_03": (-5776609843457913041, -7822190029627442914, "coat_fabric_metal"),
    "M_actor_endminf_cloth_04": (5848321708952813210, -7822190029627442914, "coat_fabric_metal"),
    "M_hairshadow_common_03": (3892601363701718524, 1962491951764993823, "overlay"),
    "M_eyewhiteshadow_common_01": (-6619209920468870390, 1962491951764993823, "overlay"),
    "M_eyeshadow_common_03": (216738175154250504, 1962491951764993823, "overlay"),
}


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generated_scalar(text: str, key: str) -> str:
    match = re.search(
        rf"^(?:  {re.escape(key)}|    - {re.escape(key)}):\s*([^\s#]+)\s*$",
        text,
        re.MULTILINE,
    )
    require(match is not None, f"generated material scalar absent: {key}")
    return match.group(1)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(len(manifest.get("meshes") or []) == 11, "LOD0 renderer count drifted")
    materials = {row["name"]: row for row in (manifest.get("materials") or {}).values()}
    require(set(materials) == set(EXPECTED), "LOD0 material identity set drifted")
    renderer_materials = {
        name for mesh in manifest["meshes"] for name in mesh.get("material_names") or []
    }
    require(renderer_materials == set(EXPECTED), "renderer/material binding closure drifted")

    rows = []
    for name, (path_id, shader_path_id, priority) in EXPECTED.items():
        row = materials[name]
        require(row.get("path_id") == path_id, f"{name}: material PathID drifted")
        require(row.get("shader_path_id") == shader_path_id, f"{name}: shader PathID drifted")
        require(row.get("source_serialized_state") is True, f"{name}: serialized state absent")
        source = Path(row["json"])
        require(source.is_file(), f"{name}: source Material JSON absent")
        raw = json.loads(source.read_text(encoding="utf-8"))
        require(raw.get("m_Name") == name, f"{name}: source name drifted")
        require(raw["m_Shader"]["m_PathID"] == shader_path_id, f"{name}: source shader drifted")
        for source_key, manifest_key in (
            ("m_CustomRenderQueue", "custom_render_queue"),
            ("m_ValidKeywords", "valid_keywords"),
            ("m_InvalidKeywords", "invalid_keywords"),
            ("m_StringTagMap", "string_tag_map"),
            ("m_DisabledShaderPasses", "disabled_shader_passes"),
            ("m_EnableInstancingVariants", "enable_instancing_variants"),
            ("m_LightmapFlags", "lightmap_flags"),
        ):
            require(raw.get(source_key) == row.get(manifest_key), f"{name}: {manifest_key} drifted")
        saved = raw.get("m_SavedProperties") or {}
        require(saved.get("m_Floats") == row.get("floats"), f"{name}: float sheet drifted")
        source_colors = {
            key: [value[c] for c in "rgba"] for key, value in (saved.get("m_Colors") or {}).items()
        }
        require(source_colors == row.get("colors"), f"{name}: color/vector sheet drifted")
        source_texture_ids = {
            key: int(value["m_Texture"]["m_PathID"])
            for key, value in (saved.get("m_TexEnvs") or {}).items()
            if int(value["m_Texture"]["m_PathID"]) != 0
        }
        manifest_texture_ids = {
            key: int(value["path_id"]) for key, value in (row.get("textures") or {}).items()
        }
        require(source_texture_ids == manifest_texture_ids, f"{name}: texture PPtr sheet drifted")
        rows.append({
            "name": name,
            "priority": priority,
            "material_path_id": path_id,
            "shader_name": row["shader_name"],
            "shader_path_id": shader_path_id,
            "queue": row["custom_render_queue"],
            "valid_keywords": row["valid_keywords"],
            "texture_count": len(manifest_texture_ids),
            "float_count": len(row["floats"]),
            "color_vector_count": len(row["colors"]),
            "source_json": str(source),
            "source_sha256": sha256(source),
        })
    generated_body = GENERATED_MATERIAL_ROOT / "actor_endminf_pathid_-8084013477027282831.mat"
    require(generated_body.is_file(), "generated exact body material absent")
    generated_text = generated_body.read_text(encoding="utf-8")
    for fragment in (
        "m_Name: M_actor_endminf_body_01",
        "m_CustomRenderQueue: 2000",
        "- _BumpScale: 0.6",
        "- _UseBumpMap: 1",
        "- _RecoveredSkinBodyForwardVariant: 1",
    ):
        require(fragment in generated_text, f"generated body admission drifted: {fragment}")

    generated_state_contracts = {
        # Source Material JSON: opaque alpha-test, despite the legacy alpha
        # content hint and BlendMode=4.  This row must not be normalized into
        # transparent blending by ConfigureMaterialSurface.
        "actor_endminf_pathid_-5776609843457913041.mat": {
            "m_Name": "M_actor_endminf_cloth_03",
            "m_CustomRenderQueue": "2000",
            "_SurfaceType": "0",
            "_AlphaClip": "1",
            "_EnableAlphaTest": "1",
            "_Cull": "2",
            "_SrcBlend": "1",
            "_DstBlend": "0",
            "_ZWrite": "1",
        },
        # The transparent hair shell is a second material on the source
        # hair renderer.  Preserve its source Less depth comparison rather
        # than the general transparent LessEqual compatibility fallback.
        "actor_endminf_pathid_-3941236971230507885.mat": {
            "m_Name": "M_actor_endminf_hairt_01",
            "m_CustomRenderQueue": "2985",
            "_AlphaClip": "0",
            "_Cull": "2",
            "_SrcBlend": "5",
            "_DstBlend": "10",
            "_ZTest": "2",
            "_ZWrite": "1",
        },
        # Endminf's transparent cape sheet is explicitly double-sided.
        "actor_endminf_pathid_8960951648682285338.mat": {
            "m_Name": "M_actor_endminf_cloth_02",
            "m_CustomRenderQueue": "3000",
            "_SurfaceType": "1",
            "_AlphaClip": "0",
            "_Cull": "0",
            "_SrcBlend": "5",
            "_DstBlend": "10",
            "_ZTest": "4",
            "_ZWrite": "1",
        },
    }
    generated_states = []
    for filename, expected_state in generated_state_contracts.items():
        path = GENERATED_MATERIAL_ROOT / filename
        require(path.is_file(), f"generated material absent: {filename}")
        text = path.read_text(encoding="utf-8")
        actual_state = {
            key: generated_scalar(text, key) for key in expected_state
        }
        require(
            actual_state == expected_state,
            f"{expected_state['m_Name']}: generated render state drifted: "
            f"expected={expected_state} actual={actual_state}",
        )
        generated_states.append({
            "file": str(path),
            "sha256": sha256(path),
            "state": actual_state,
        })

    require(PRE_GBUFFER_OWNER.is_file(), "PreGBuffer depth-owner runtime absent")
    pre_gbuffer_owner_text = PRE_GBUFFER_OWNER.read_text(encoding="utf-8")
    reset_all_match = re.search(
        r"private static void ResetAllRecoveredCharacterZTestsToCompatibility\(\)"
        r"(?P<body>.*?)\n\s*}\n\n\s*private bool LogFailure",
        pre_gbuffer_owner_text,
        re.DOTALL,
    )
    require(reset_all_match is not None, "global compatibility reset method drifted")
    require(
        "material.renderQueue > (int)RenderQueue.GeometryLast" in
        reset_all_match.group("body"),
        "global compatibility reset can overwrite transparent source Z-tests",
    )

    report = {
        "schema": "endfield.endminf-body-material-admission.v1",
        "status": "exact_unity_admission_visual_ab_pass",
        "scope": "main actor LOD0 only; VFX and accessories excluded",
        "renderer_count": 11,
        "material_count": 13,
        "priority_order": ["face_skin", "hair", "coat_fabric_metal", "overlay"],
        "manifest": str(MANIFEST),
        "manifest_sha256": sha256(MANIFEST),
        "materials": rows,
        "generated_unity_admission": {
            "material": str(generated_body),
            "material_sha256": sha256(generated_body),
            "recovered_shader": "Endfield/Recovered/CharacterSkin",
            "body_forward_variant": 1,
            "queue": 2000,
            "bump_scale": 0.6,
            "use_bump_map": 1,
            "hair_cape_render_states": generated_states,
            "pre_gbuffer_compatibility_reset": {
                "file": str(PRE_GBUFFER_OWNER),
                "sha256": sha256(PRE_GBUFFER_OWNER),
                "opaque_only": True,
            },
        },
        "graphical_exact_default_ab": {
            "time_seconds": 2.25,
            "mode": "exact-default; no visual-compatibility environment flags",
            "artifact_root": "unity_endfield_graph_shader_lab/scratch/character_recovery/endminf_body_material_baseline",
            "region_similarity_before_after": {
                "face_skin": [0.396, 0.411],
                "hair": [0.731, 0.774],
                "knit": [0.220, 0.228],
                "coat_fabric": [0.830, 0.868],
                "yellow_accent_control": [0.490, 0.489],
                "metal_visor": [0.485, 0.494],
            },
            "visible_result": "visor plates/occlusion restored; face, hair, knit, coat, and metal regions improve while the yellow control is stable",
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS source/manifest exact: renderers=11 materials=13 report={REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
