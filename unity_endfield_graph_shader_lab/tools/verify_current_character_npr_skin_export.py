#!/usr/bin/env python3
"""Verify the current installed CharacterNPR_Skin export boundary.

This audit deliberately proves source/export identity and compiled-variant
metadata only.  It does not claim that the recovered Unity shader has retail
frame parity, nor does it treat the older no-screen sidecars as evidence for
the current game data.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
ASSET_MAP = (
    REPO_ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps"
    / "endfield_streamingassets_assets.json"
)
MATERIAL_ROOT = (
    REPO_ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material"
)
SHADER_EXPORT = (
    REPO_ROOT
    / "scratch/animestudio/body_skin_sidecar_refresh/shader_export/Shader"
    / "HGRP_CharacterNPR_Skin_p3E3D05CF72D25122.shader"
)
BYTECODE_ROOT = Path(str(SHADER_EXPORT) + ".bytecode")
PREGBUFFER_RUNTIME = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    / "EndfieldRecoveredPreGBufferDiagnostic.cs"
)
DECOMPILED_SPV_GLSL = (
    REPO_ROOT / "scratch/animestudio/body_skin_sidecar_refresh/skin_body_forward.spv.glsl"
)
PREG_BUFFER_DECOMPILED_HLSL = (
    REPO_ROOT / "scratch/character_recovery/pregbuffer_decomp/skin_1261.hlsl"
)
PREG_BUFFER_SIDECAR = BYTECODE_ROOT / "1261_endfield_dxbc_1.dxbc"
PREG_BUFFER_VERTEX_DECOMPILED_HLSL = (
    REPO_ROOT / "scratch/character_recovery/pregbuffer_decomp/skin_1260_vertex.hlsl"
)
PREG_BUFFER_VERTEX_SIDECAR = BYTECODE_ROOT / "1260_endfield_dxbc_0.dxbc"
EYE_PREGBUFFER_VERTEX_DECOMPILED_HLSL = (
    REPO_ROOT / "scratch/character_recovery/pregbuffer_decomp/eye_0216_vertex.hlsl"
)
EYE_PREGBUFFER_VERTEX_SIDECAR = (
    REPO_ROOT
    / "scratch/animestudio/body_skin_sidecar_refresh/shader_export/Shader"
    / "HGRP_CharacterNPR_Eye_pE852494D61D6F176.shader.bytecode"
    / "0216_endfield_dxbc_0.dxbc"
)
EYE_PREGBUFFER_FRAGMENT_DECOMPILED_HLSL = (
    REPO_ROOT / "scratch/character_recovery/pregbuffer_decomp/eye_0217.hlsl"
)
EYE_PREGBUFFER_FRAGMENT_SIDECAR = (
    REPO_ROOT
    / "scratch/animestudio/body_skin_sidecar_refresh/shader_export/Shader"
    / "HGRP_CharacterNPR_Eye_pE852494D61D6F176.shader.bytecode"
    / "0217_endfield_dxbc_1.dxbc"
)

EXPECTED_SHADER_MAP = {
    "name": "HGRP/CharacterNPR_Skin",
    "type": "Shader",
    "path_id": 4484747192473637154,
    "source_name": "19F0903A12BA87C0D43E67E64889B525.chk",
    "asset_map_hash": "82daad1fdebff692",
    "offset": 112899433,
}
EXPECTED_SHADER_EXPORT = {
    "size": 34275574,
    "sha256": "91f3255a631b067f7942756ce96857c5f5d4a3f65f648faa2ccf11b61b75c0b8",
}
EXPECTED_DECOMPILED_SPV_GLSL = {
    "size": 97085,
    "sha256": "70022f422f83b698b28f30bed89c08502d25e26dd9c30e6d9372cd92c77040a1",
}
EXPECTED_PREG_BUFFER_SIDECAR = {
    "size": 2816,
    "sha256": "4d081d6dc8f5bd141d69ecb4a9c0b33ac48c6fddc1e544bca1af7a7a35370c13",
}
EXPECTED_PREG_BUFFER_DECOMPILED_HLSL = {
    "size": 7299,
    "sha256": "597b675391e99509c443c327460e9f55b414f1d460d1278ce823905568ceb4c8",
}
EXPECTED_PREG_BUFFER_VERTEX_SIDECAR = {
    "size": 6044,
    "sha256": "bee21d747a5ee3abea06b5db3535165471eea079222993a339377fe5e28b2a8e",
}
EXPECTED_PREG_BUFFER_VERTEX_DECOMPILED_HLSL = {
    "size": 19906,
    "sha256": "c0eda911850f70be443f8de0642f102bf9426d7dde1d7748ac83ffeeee0331e7",
}
EXPECTED_EYE_PREGBUFFER_VERTEX_SIDECAR = {
    "size": 6044,
    "sha256": "bee21d747a5ee3abea06b5db3535165471eea079222993a339377fe5e28b2a8e",
    "pass_index": 1,
}
EXPECTED_EYE_PREGBUFFER_FRAGMENT_SIDECAR = {
    "size": 2316,
    "sha256": "207e55c4830c804557a1e732cea6f8e5573c0c231ef0f55964f56771f4d09a5f",
    "pass_index": 1,
}
EXPECTED_EYE_PREGBUFFER_FRAGMENT_DECOMPILED_HLSL = {
    "size": 6266,
    "sha256": "7e8566d7486f0a5257c56ff58091de30eb4414e18981805868e8885c78f9820c",
}

EXPECTED_MATERIALS = {
    "M_actor_wulfa_body_01": {
        "file": "M_actor_wulfa_body_01_p6341AD44D709F517.json",
        "path_id": 7152188194418193687,
        "size": 16224,
        "sha256": "e5c28101e3ddf74b45e3c74973cfc0700ae657f90740bf65e2959ada4e4d3bc0",
    },
    "M_actor_zhuangfy_body_01": {
        "file": "M_actor_zhuangfy_body_01_pA98FECEDBCC64D62.json",
        "path_id": -6228499253811589790,
        "size": 11477,
        "sha256": "775db3b4ad09fd51084f4ad4cd868a819d9a93f0ec886edc2db000818bfa85c9",
    },
}

BODY_KEYWORDS = ["_DIFF_RAMP_ON", "_NORMALMAP", "_SHADOW_LUT_TEX"]
SCREEN_KEYWORD = "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK"
SELECTED_SIDECARS = {
    "0120_endfield_dxbc_0.dxbc": {
        "size": 9380,
        "sha256": "1a9f4b149e6089aabdfd0c50de721914d2fce72ff12c7063ae3200be97f9ce02",
        "stage": "vertex",
        "encoding": "DXBC",
    },
    "0121_endfield_dxbc_1.dxbc": {
        "size": 64064,
        "sha256": "f7ffb8f0e6d128edd94773a9a09e3dfe62d056999ba34b336e6b6a1f4848d028",
        "stage": "fragment",
        "encoding": "DXBC",
    },
    "0122_endfield_smolv_0.smolv": {
        "size": 5232,
        "sha256": "3c5df8a42057000715d3ae2da859e8750317be6b88c41b93e9efd1fac7f020c4",
        "stage": None,
        "encoding": None,
    },
    "0123_endfield_spirv_0.spv": {
        "size": 19196,
        "sha256": "0aa6ca19fab1ebf5a8a295f7ee4670ec3f56c524866db3bcc32526b3516124f3",
        "stage": None,
        "encoding": None,
    },
    "0124_endfield_smolv_1.smolv": {
        "size": 28411,
        "sha256": "9ccfc28ff806539046f52fa5acb32f053c940ba93fbddae4efcf1311e332c57d",
        "stage": None,
        "encoding": None,
    },
    "0125_endfield_spirv_1.spv": {
        "size": 90280,
        "sha256": "98e19ceef84f50255c1fffd6bac4e61c9220a59c15deebd83f9771e8ff049292",
        "stage": None,
        "encoding": None,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_file(path: Path, expected_size: int, expected_hash: str, label: str) -> None:
    if not path.is_file():
        raise AssertionError(f"missing {label}: {path}")
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise AssertionError(
            f"{label} size mismatch: path={path} expected={expected_size} actual={actual_size}"
        )
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise AssertionError(
            f"{label} sha256 mismatch: path={path} expected={expected_hash} actual={actual_hash}"
        )


def load_map_entries() -> list[dict[str, Any]]:
    if not ASSET_MAP.is_file():
        raise AssertionError(f"missing current AssetMap: {ASSET_MAP}")
    payload = json.loads(ASSET_MAP.read_text(encoding="utf-8"))
    entries = payload.get("AssetEntries")
    if not isinstance(entries, list):
        raise AssertionError("current AssetMap has no AssetEntries list")
    return [entry for entry in entries if isinstance(entry, dict)]


def verify_shader_map(entries: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [
        entry
        for entry in entries
        if entry.get("Name") == EXPECTED_SHADER_MAP["name"]
        and entry.get("Type") == EXPECTED_SHADER_MAP["type"]
        and int(entry.get("PathID", 0)) == EXPECTED_SHADER_MAP["path_id"]
    ]
    if len(matches) != 1:
        raise AssertionError(
            "current CharacterNPR_Skin AssetMap identity mismatch: "
            f"expected one row, actual={len(matches)}"
        )
    entry = matches[0]
    actual_source = Path(str(entry.get("Source") or "")).name
    for key in ("asset_map_hash", "offset"):
        if entry.get("Hash" if key == "asset_map_hash" else "Offset") != EXPECTED_SHADER_MAP[key]:
            raise AssertionError(
                f"current CharacterNPR_Skin AssetMap {key} mismatch: "
                f"expected={EXPECTED_SHADER_MAP[key]} actual="
                f"{entry.get('Hash' if key == 'asset_map_hash' else 'Offset')}"
            )
    if actual_source != EXPECTED_SHADER_MAP["source_name"]:
        raise AssertionError(
            "current CharacterNPR_Skin source mismatch: "
            f"expected={EXPECTED_SHADER_MAP['source_name']} actual={actual_source}"
        )
    return {
        "name": entry["Name"],
        "type": entry["Type"],
        "path_id": int(entry["PathID"]),
        "source_name": actual_source,
        "asset_map_hash": entry["Hash"],
        "offset": int(entry["Offset"]),
    }


def verify_materials(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for name, expected in EXPECTED_MATERIALS.items():
        path = MATERIAL_ROOT / expected["file"]
        require_file(path, expected["size"], expected["sha256"], f"{name} JSON")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("m_Name") != name:
            raise AssertionError(f"{name} material name mismatch: {payload.get('m_Name')}")
        shader = payload.get("m_Shader") or {}
        if int(shader.get("m_PathID", 0)) != EXPECTED_SHADER_MAP["path_id"]:
            raise AssertionError(f"{name} shader PathID mismatch: {shader.get('m_PathID')}")
        floats = (payload.get("m_SavedProperties") or {}).get("m_Floats") or {}
        # Material feature floats use _Use* names; the keyword list below is
        # the authoritative serialized feature state for this source tranche.
        feature_state = {
            "_DIFF_RAMP_ON": float(floats.get("_UseDiffRampMap", 0.0)),
            "_NORMALMAP": float(floats.get("_UseBumpMap", 0.0)),
            "_SHADOW_LUT_TEX": float(floats.get("_UseShadowLutTex", 0.0)),
        }
        missing = [key for key, value in feature_state.items() if abs(value - 1.0) > 1e-6]
        if missing:
            raise AssertionError(f"{name} body feature state mismatch: missing={missing}")
        valid_keywords = payload.get("m_ValidKeywords") or []
        if list(valid_keywords) != BODY_KEYWORDS:
            raise AssertionError(
                f"{name} serialized keyword mismatch: expected={BODY_KEYWORDS} actual={valid_keywords}"
            )
        verified.append(
            {
                "name": name,
                "path_id": int(expected["path_id"]),
                "size": expected["size"],
                "sha256": expected["sha256"],
                "valid_keywords": valid_keywords,
                "feature_state": feature_state,
            }
        )
    return verified


def verify_sidecars() -> dict[str, Any]:
    require_file(
        SHADER_EXPORT,
        EXPECTED_SHADER_EXPORT["size"],
        EXPECTED_SHADER_EXPORT["sha256"],
        "current CharacterNPR_Skin shader export",
    )
    shader_text = SHADER_EXPORT.read_text(encoding="utf-8")
    for needle in ('Shader "HGRP/CharacterNPR_Skin"', 'Name "ForwardLit"'):
        if needle not in shader_text:
            raise AssertionError(f"current shader export missing {needle!r}")

    selected: list[str] = []
    expected_keywords = [
        "HG_ENABLE_PER_OBJECT_MV",
        SCREEN_KEYWORD,
        "SRP_INSTANCING_ON",
        "_DIFF_RAMP_ON",
        "_NORMALMAP",
        "_SHADOW_LUT_TEX",
    ]
    for filename, expected in SELECTED_SIDECARS.items():
        path = BYTECODE_ROOT / filename
        require_file(path, expected["size"], expected["sha256"], f"current sidecar {filename}")
        metadata_path = Path(str(path) + ".metadata.json")
        if not metadata_path.is_file():
            raise AssertionError(f"missing sidecar metadata: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("SourceCompiledKeywords") != expected_keywords:
            raise AssertionError(
                f"current sidecar keyword mismatch: path={path} "
                f"expected={expected_keywords} actual={metadata.get('SourceCompiledKeywords')}"
            )
        if metadata.get("SourceSubShaderIndex") != 0 or metadata.get("SourcePassIndex") != 0:
            raise AssertionError(f"current sidecar pass identity mismatch: {metadata_path}")
        if metadata.get("SourcePassName") != "ForwardLit":
            raise AssertionError(f"current sidecar pass name mismatch: {metadata_path}")
        if metadata.get("SourceSerializedProgramStage") != "vertex":
            raise AssertionError(f"current sidecar serialized stage mismatch: {metadata_path}")
        if metadata.get("DecodedProgramStage") != expected["stage"]:
            raise AssertionError(f"current sidecar decoded stage mismatch: {metadata_path}")
        if metadata.get("DecodedProgramEncoding") != expected["encoding"]:
            raise AssertionError(f"current sidecar decoded encoding mismatch: {metadata_path}")
        selected.append(filename)

    forward_metadata = []
    for metadata_path in BYTECODE_ROOT.glob("*.metadata.json"):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("SourcePassName") == "ForwardLit":
            forward_metadata.append(metadata)
    keyword_sets = {
        tuple(metadata.get("SourceCompiledKeywords") or [])
        for metadata in forward_metadata
    }
    with_screen = sum(SCREEN_KEYWORD in keyword_set for keyword_set in keyword_sets)
    without_screen = len(keyword_sets) - with_screen
    if len(forward_metadata) != 846 or len(keyword_sets) != 141:
        raise AssertionError(
            "current ForwardLit metadata census mismatch: "
            f"expected_records=846 actual_records={len(forward_metadata)} "
            f"expected_sets=141 actual_sets={len(keyword_sets)}"
        )
    if without_screen != 0:
        raise AssertionError(
            "current ForwardLit no-screen boundary changed: "
            f"expected=0 actual={without_screen}"
        )
    return {
        "shader_export": {
            "path": str(SHADER_EXPORT.relative_to(REPO_ROOT)).replace("\\", "/"),
            **EXPECTED_SHADER_EXPORT,
        },
        "selected_sidecars": selected,
        "forward_lit_metadata_records": len(forward_metadata),
        "forward_lit_unique_keyword_sets": len(keyword_sets),
        "forward_lit_sets_with_screen_shadow_mask": with_screen,
        "forward_lit_sets_without_screen_shadow_mask": without_screen,
    }


def verify_decompiled_consumer() -> dict[str, Any]:
    """Pin the current SPIR-V consumer semantics without claiming parity."""

    require_file(
        DECOMPILED_SPV_GLSL,
        EXPECTED_DECOMPILED_SPV_GLSL["size"],
        EXPECTED_DECOMPILED_SPV_GLSL["sha256"],
        "current CharacterNPR_Skin SPIR-V decompilation",
    )
    text = DECOMPILED_SPV_GLSL.read_text(encoding="utf-8")
    required = {
        "screen_mask_resource": "Texture2D<float4> _ScreenSpaceShadowMask",
        "integer_pixel_load": "_ScreenSpaceShadowMask.Load(int3(int3(_2162, _2163, 0).xy, 0))",
        "character_shadow_g_channel": "float _2172 = _2167.y;",
        "scene_shadow_r_channel": "float _2175 = lerp(lerp(1.0f, _2167.x",
        "scene_shadow_ignore_main_gate": "ShaderVariablesGlobal_CharacterParams1.z);",
        "character_shadow_alpha_product": "float _2215 = _472 * _2172;",
        "character_shadow_minimum": "float _2221 = min(min(_2172, _472), _2205);",
        "scene_shadow_lighting_selector": "float3 _2250 = _2175.xxx;",
        "clustered_light_bit_scan": "uint _2516 = firstbitlow(_2511);",
        "punctual_shadow_basis": "float3 _3045 =",
        "punctual_rim_dispatch": "float _3274 = 0.0f;",
    }
    for label, needle in required.items():
        if needle not in text:
            raise AssertionError(
                f"current SPIR-V consumer anchor missing: label={label} needle={needle!r}"
            )
    return {
        "path": str(DECOMPILED_SPV_GLSL.relative_to(REPO_ROOT)).replace("\\", "/"),
        **EXPECTED_DECOMPILED_SPV_GLSL,
        "screen_mask_load": "integer pixel Load",
        "screen_mask_channels": {"r": "directional scene shadow", "g": "character shadow"},
        "shadow_equations": {
            "directional_scene": (
                "lerp(lerp(1, R, DirectionalShadowParams.x), "
                "1, CharacterParams1.z)"
            ),
            "character_shadow": "G",
            "character_shadow_material_alpha": "alpha * G",
            "character_shadow_minimum": "min(G, alpha, material-shadow-sample)",
        },
        "clustered_punctual_consumer": True,
        "retail_frame_parity": "not asserted",
    }


def verify_pregbuffer_contract() -> dict[str, Any]:
    """Pin the current Skin PreGBuffer pass without claiming full GBuffer parity.

    The source pass writes five MRT lanes.  The maintained lab deliberately
    consumes only the selector/normal pair for its default-off screen-shadow
    diagnostic; motion vectors remain open while the material/color lane has a
    source-shaped diagnostic sidecar.
    """

    require_file(
        PREG_BUFFER_SIDECAR,
        EXPECTED_PREG_BUFFER_SIDECAR["size"],
        EXPECTED_PREG_BUFFER_SIDECAR["sha256"],
        "current Skin PreGBuffer DXBC sidecar",
    )
    metadata_path = Path(str(PREG_BUFFER_SIDECAR) + ".metadata.json")
    if not metadata_path.is_file():
        raise AssertionError(f"missing PreGBuffer metadata: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_keywords = ["HG_ENABLE_PER_OBJECT_MV", "SRP_INSTANCING_ON"]
    if metadata.get("SourcePassName") != "PreGBuffer":
        raise AssertionError(
            "current Skin PreGBuffer pass mismatch: "
            f"expected=PreGBuffer actual={metadata.get('SourcePassName')}"
        )
    if metadata.get("SourcePassIndex") != 3:
        raise AssertionError(
            "current Skin PreGBuffer pass index mismatch: "
            f"expected=3 actual={metadata.get('SourcePassIndex')}"
        )
    if metadata.get("SourceCompiledKeywords") != expected_keywords:
        raise AssertionError(
            "current Skin PreGBuffer keyword mismatch: "
            f"expected={expected_keywords} actual={metadata.get('SourceCompiledKeywords')}"
        )
    if metadata.get("SourceSerializedProgramStage") != "vertex":
        raise AssertionError(
            "current Skin PreGBuffer serialized stage mismatch: "
            f"expected=vertex actual={metadata.get('SourceSerializedProgramStage')}"
        )
    if metadata.get("DecodedProgramStage") != "fragment":
        raise AssertionError(
            "current Skin PreGBuffer decoded stage mismatch: "
            f"expected=fragment actual={metadata.get('DecodedProgramStage')}"
        )
    if metadata.get("DecodedProgramEncoding") != "DXBC":
        raise AssertionError(
            "current Skin PreGBuffer encoding mismatch: "
            f"expected=DXBC actual={metadata.get('DecodedProgramEncoding')}"
        )

    require_file(
        PREG_BUFFER_DECOMPILED_HLSL,
        EXPECTED_PREG_BUFFER_DECOMPILED_HLSL["size"],
        EXPECTED_PREG_BUFFER_DECOMPILED_HLSL["sha256"],
        "current Skin PreGBuffer decompilation",
    )
    text = PREG_BUFFER_DECOMPILED_HLSL.read_text(encoding="utf-8")
    required = {
        "five_mrt_outputs": "float4 SV_Target_4 : SV_Target4;",
        "target0_zero": "SV_Target.x = 0.0f;",
        "target1_motion_vector": "SV_Target_1.z = 1.0f;",
        "target1_motion_confidence": "SV_Target_1.w = 0.4000000059604644775390625f;",
        "target2_selector": "SV_Target_2.x = _65(_168 & 1023u)",
        "target3_oct_normal": "SV_Target_3.x = mad(_229 ?",
        "target4_material_color": "SV_Target_4.x = mad(asfloat(_308.x), _301, _302)",
        "motion_current_ndc_y": "float _105 = TEXCOORD_3.y / _98;",
        "motion_previous_ndc_y": "float _114 = TEXCOORD_4.y / _108;",
        "motion_delta_x": "float _115 = (TEXCOORD_3.x / _98) - (TEXCOORD_4.x / _108);",
        "motion_delta_y": "float _117 = _114 - _105;",
        "motion_x_encoding": "SV_Target_1.x = mad(_61(((_115 < 0.0f)",
        "motion_y_encoding": "SV_Target_1.y = mad(_61(uint(_117 > 0.0f)",
    }
    for label, needle in required.items():
        if needle not in text:
            raise AssertionError(
                f"current Skin PreGBuffer decompilation anchor missing: "
                f"label={label} needle={needle!r}"
            )

    require_file(
        PREG_BUFFER_VERTEX_SIDECAR,
        EXPECTED_PREG_BUFFER_VERTEX_SIDECAR["size"],
        EXPECTED_PREG_BUFFER_VERTEX_SIDECAR["sha256"],
        "current Skin PreGBuffer vertex DXBC sidecar",
    )
    vertex_metadata_path = Path(str(PREG_BUFFER_VERTEX_SIDECAR) + ".metadata.json")
    if not vertex_metadata_path.is_file():
        raise AssertionError(
            f"missing PreGBuffer vertex metadata: {vertex_metadata_path}"
        )
    vertex_metadata = json.loads(vertex_metadata_path.read_text(encoding="utf-8"))
    if vertex_metadata.get("SourcePassName") != "PreGBuffer":
        raise AssertionError(
            "current Skin PreGBuffer vertex pass mismatch: "
            f"expected=PreGBuffer actual={vertex_metadata.get('SourcePassName')}"
        )
    if vertex_metadata.get("SourcePassIndex") != 3:
        raise AssertionError(
            "current Skin PreGBuffer vertex pass index mismatch: "
            f"expected=3 actual={vertex_metadata.get('SourcePassIndex')}"
        )
    if vertex_metadata.get("SourceCompiledKeywords") != expected_keywords:
        raise AssertionError(
            "current Skin PreGBuffer vertex keyword mismatch: "
            f"expected={expected_keywords} actual="
            f"{vertex_metadata.get('SourceCompiledKeywords')}"
        )
    if vertex_metadata.get("SourceSerializedProgramStage") != "vertex":
        raise AssertionError(
            "current Skin PreGBuffer vertex serialized stage mismatch: "
            f"expected=vertex actual={vertex_metadata.get('SourceSerializedProgramStage')}"
        )
    if vertex_metadata.get("DecodedProgramStage") != "vertex":
        raise AssertionError(
            "current Skin PreGBuffer vertex decoded stage mismatch: "
            f"expected=vertex actual={vertex_metadata.get('DecodedProgramStage')}"
        )
    if vertex_metadata.get("DecodedProgramEncoding") != "DXBC":
        raise AssertionError(
            "current Skin PreGBuffer vertex encoding mismatch: "
            f"expected=DXBC actual={vertex_metadata.get('DecodedProgramEncoding')}"
        )
    vertex_parameters = vertex_metadata.get("ConstantBufferParameters") or []
    parameter_names = {
        str(parameter.get("Name"))
        for buffer in vertex_parameters
        if isinstance(buffer, dict)
        for parameter in (buffer.get("MatrixParameters") or [])
        + (buffer.get("VectorParameters") or [])
        if isinstance(parameter, dict)
    }
    if not {
        "_NonJitteredViewNoTransProjMatrix",
        "_PrevNonJitteredViewNoTransProjMatrix",
        "_PrevCamPosRWS_Internal",
    }.issubset(parameter_names):
        raise AssertionError(
            "current Skin PreGBuffer vertex history parameter boundary mismatch: "
            f"actual={sorted(parameter_names)}"
        )
    per_draw_members = {
        str(member.get("Name"))
        for buffer in vertex_parameters
        if isinstance(buffer, dict)
        for struct in (buffer.get("StructParameters") or [])
        if isinstance(struct, dict)
        for member in (struct.get("MatrixMembers") or [])
        + (struct.get("VectorMembers") or [])
        if isinstance(member, dict)
    }
    if "unity_MatrixPreviousM" not in per_draw_members:
        raise AssertionError(
            "current Skin PreGBuffer vertex previous-object matrix boundary missing"
        )
    require_file(
        PREG_BUFFER_VERTEX_DECOMPILED_HLSL,
        EXPECTED_PREG_BUFFER_VERTEX_DECOMPILED_HLSL["size"],
        EXPECTED_PREG_BUFFER_VERTEX_DECOMPILED_HLSL["sha256"],
        "current Skin PreGBuffer vertex decompilation",
    )
    vertex_text = PREG_BUFFER_VERTEX_DECOMPILED_HLSL.read_text(encoding="utf-8")
    vertex_required = {
        "current_clip_varying": "float3 TEXCOORD_3 : TEXCOORD4;",
        "previous_clip_varying": "float3 TEXCOORD_4_1 : TEXCOORD5;",
        "current_clip_assignment": "TEXCOORD_3.x = _612;",
        "current_clip_w_assignment": "TEXCOORD_3.z = _615;",
        "previous_clip_assignment": "TEXCOORD_4_1.x = mad(",
        "previous_clip_w_assignment": "TEXCOORD_4_1.z = mad(",
    }
    for label, needle in vertex_required.items():
        if needle not in vertex_text:
            raise AssertionError(
                f"current Skin PreGBuffer vertex decompilation anchor missing: "
                f"label={label} needle={needle!r}"
            )

    # Eye's authored PreGBuffer uses a different pass index but the exact same
    # vertex DXBC blob. This closes the shared current/previous deformation
    # ABI across two CharacterNPR families instead of assuming Skin-only
    # behavior.
    require_file(
        EYE_PREGBUFFER_VERTEX_SIDECAR,
        EXPECTED_EYE_PREGBUFFER_VERTEX_SIDECAR["size"],
        EXPECTED_EYE_PREGBUFFER_VERTEX_SIDECAR["sha256"],
        "current Eye PreGBuffer vertex DXBC sidecar",
    )
    eye_metadata_path = Path(str(EYE_PREGBUFFER_VERTEX_SIDECAR) + ".metadata.json")
    if not eye_metadata_path.is_file():
        raise AssertionError(f"missing Eye PreGBuffer vertex metadata: {eye_metadata_path}")
    eye_metadata = json.loads(eye_metadata_path.read_text(encoding="utf-8"))
    for key, expected in {
        "SourcePassName": "PreGBuffer",
        "SourcePassIndex": EXPECTED_EYE_PREGBUFFER_VERTEX_SIDECAR["pass_index"],
        "SourceSerializedProgramStage": "vertex",
        "DecodedProgramStage": "vertex",
        "DecodedProgramEncoding": "DXBC",
    }.items():
        if eye_metadata.get(key) != expected:
            raise AssertionError(
                "current Eye PreGBuffer vertex metadata mismatch: "
                f"field={key} expected={expected!r} actual={eye_metadata.get(key)!r}"
            )
    if eye_metadata.get("SourceCompiledKeywords") != expected_keywords:
        raise AssertionError(
            "current Eye PreGBuffer vertex keyword mismatch: "
            f"expected={expected_keywords} actual={eye_metadata.get('SourceCompiledKeywords')}"
        )
    require_file(
        EYE_PREGBUFFER_VERTEX_DECOMPILED_HLSL,
        EXPECTED_PREG_BUFFER_VERTEX_DECOMPILED_HLSL["size"],
        EXPECTED_PREG_BUFFER_VERTEX_DECOMPILED_HLSL["sha256"],
        "current Eye PreGBuffer vertex decompilation",
    )
    eye_vertex_text = EYE_PREGBUFFER_VERTEX_DECOMPILED_HLSL.read_text(encoding="utf-8")
    if eye_vertex_text != vertex_text:
        raise AssertionError(
            "current Eye/Skin PreGBuffer vertex decompilations differ despite "
            "the expected shared DXBC hash"
        )

    require_file(
        EYE_PREGBUFFER_FRAGMENT_SIDECAR,
        EXPECTED_EYE_PREGBUFFER_FRAGMENT_SIDECAR["size"],
        EXPECTED_EYE_PREGBUFFER_FRAGMENT_SIDECAR["sha256"],
        "current Eye PreGBuffer fragment DXBC sidecar",
    )
    eye_fragment_metadata_path = Path(
        str(EYE_PREGBUFFER_FRAGMENT_SIDECAR) + ".metadata.json"
    )
    if not eye_fragment_metadata_path.is_file():
        raise AssertionError(
            "missing Eye PreGBuffer fragment metadata: "
            f"{eye_fragment_metadata_path}"
        )
    eye_fragment_metadata = json.loads(
        eye_fragment_metadata_path.read_text(encoding="utf-8")
    )
    for key, expected in {
        "SourcePassName": "PreGBuffer",
        "SourcePassIndex": EXPECTED_EYE_PREGBUFFER_FRAGMENT_SIDECAR["pass_index"],
        "SourceSerializedProgramStage": "vertex",
        "DecodedProgramStage": "fragment",
        "DecodedProgramEncoding": "DXBC",
    }.items():
        if eye_fragment_metadata.get(key) != expected:
            raise AssertionError(
                "current Eye PreGBuffer fragment metadata mismatch: "
                f"field={key} expected={expected!r} "
                f"actual={eye_fragment_metadata.get(key)!r}"
            )
    if eye_fragment_metadata.get("SourceCompiledKeywords") != expected_keywords:
        raise AssertionError(
            "current Eye PreGBuffer fragment keyword mismatch: "
            f"expected={expected_keywords} "
            f"actual={eye_fragment_metadata.get('SourceCompiledKeywords')}"
        )
    require_file(
        EYE_PREGBUFFER_FRAGMENT_DECOMPILED_HLSL,
        EXPECTED_EYE_PREGBUFFER_FRAGMENT_DECOMPILED_HLSL["size"],
        EXPECTED_EYE_PREGBUFFER_FRAGMENT_DECOMPILED_HLSL["sha256"],
        "current Eye PreGBuffer fragment decompilation",
    )
    eye_fragment_text = EYE_PREGBUFFER_FRAGMENT_DECOMPILED_HLSL.read_text(
        encoding="utf-8"
    )
    for label, needle in {
        "five_mrt_outputs": "float4 SV_Target_4 : SV_Target4;",
        "target0_zero": "SV_Target.z = 0.0f;",
        "target1_motion": "SV_Target_1.z = 1.0f;",
        "target2_selector": "SV_Target_2.x = _59(_162 & 1023u)",
        "target3_eye_normal_alpha": "SV_Target_3.w = 0.699999988079071044921875f;",
        "target4_color": "SV_Target_4.w = 1.0f;",
    }.items():
        if needle not in eye_fragment_text:
            raise AssertionError(
                "current Eye PreGBuffer fragment decompilation anchor missing: "
                f"label={label} needle={needle!r}"
            )
    runtime = PREGBUFFER_RUNTIME.read_text(encoding="utf-8")
    runtime_required = {
        "g_buffer_c_property": 'Shader.PropertyToID("_EndfieldRecoveredPreGBufferC")',
        "g_buffer_c_attachment": "new RenderTargetIdentifier(resources.gBufferC)",
        "g_buffer_c_format": "GraphicsFormat.R8G8B8A8_SRGB",
        "g_buffer_c_readback": "CompleteMaterialReadback",
        "five_readbacks": "internal int remaining = 5;",
        "motion_vector_gap": "does not publish motion vectors",
    }
    for label, needle in runtime_required.items():
        if needle not in runtime:
            raise AssertionError(
                f"current PreGBuffer runtime anchor missing: "
                f"label={label} needle={needle!r}"
            )
    return {
        "pass": "PreGBuffer",
        "light_mode": "DepthCharacterOnly",
        "stencil": {"ref": 36, "comp": "Always", "pass": "Replace"},
        "compiled_keywords": expected_keywords,
        "mrt_count": 5,
        "outputs": {
            "target0": "zero/unused scene lane",
            "target1": "motion-vector payload (xy), z=1, w=0.4",
            "target2": "packed 10-bit selector bits",
            "target3": "octahedral world normal, z=0, w=0.4",
            "target4": "material/color payload",
        },
        "vertex_motion_inputs": {
            "current_clip": "TEXCOORD_3 = current clip x/y/w",
            "previous_clip": "TEXCOORD_4_1 = previous skinned/world clip x/y/w",
            "history_parameters": [
                "_NonJitteredViewNoTransProjMatrix",
                "_PrevNonJitteredViewNoTransProjMatrix",
                "_PrevCamPosRWS_Internal",
                "unity_MatrixPreviousM",
            ],
            "source_deformation": "previous clip is generated from a separate previous skinned/object path; previous camera matrix alone is insufficient",
            "encoding": "Target1.xy = 0.5 + sign(sqrt(sqrt(abs(delta * 0.5))) * 0.5), Target1.z=1, Target1.w=0.4",
            "eye_shared_vertex": "exact same 6044-byte DXBC and decompilation; Eye pass index is 1",
            "eye_fragment": "same five MRT topology; Eye Target3.w=0.7",
        },
        "lab_consumption": {
            "selector_normal_pair": "diagnostic A/B only",
            "motion_vector": "not published",
            "material_color": "source-shaped diagnostic C sidecar, not consumed by retail resolver",
        },
        "retail_frame_parity": "not asserted",
    }


def verify_current_boundary() -> dict[str, Any]:
    entries = load_map_entries()
    result = {
        "ok": True,
        "source_identity": verify_shader_map(entries),
        "materials": verify_materials(entries),
        "compiled_variants": verify_sidecars(),
        "binary_consumer": verify_decompiled_consumer(),
        "pregbuffer": verify_pregbuffer_contract(),
        "interpretation": {
            "current_forward_lit_policy": "all current ForwardLit keyword sets include HG_ENABLE_SCREEN_SPACE_SHADOW_MASK",
            "older_no_screen_sidecars": "not evidence for this export",
            "retail_frame_parity": "not asserted",
        },
    }
    return result


def main() -> int:
    try:
        result = verify_current_boundary()
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "diagnostic": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
