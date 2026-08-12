#!/usr/bin/env python3
"""Verify the current original ScreenSpaceShadowResolve export boundary.

This audit pins the installed AssetMap identity, the exported pass layout, and
the character-pass SPIR-V decompilation.  It records the retail G-channel
producer semantics without claiming that the Unity recovery lab has full frame
parity or a validated runtime atlas upload.
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
SHADER_EXPORT = (
    REPO_ROOT
    / "scratch/animestudio/screen_shadow_resolve_refresh/shader_export/Shader"
    / "HGRP_ScreenSpaceShadowResolve_pE36AF612B2CE3978.shader"
)
BYTECODE_ROOT = Path(str(SHADER_EXPORT) + ".bytecode")
CHARACTER_METADATA = BYTECODE_ROOT / "0011_endfield_spirv_1.spv.metadata.json"
CHARACTER_DECOMP = (
    REPO_ROOT
    / "scratch/animestudio/screen_shadow_resolve_refresh/decomp/character1.glsl"
)

EXPECTED_MAP = {
    "name": "HGRP/ScreenSpaceShadowResolve",
    "type": "Shader",
    "path_id": -2059563319398876808,
    "source_name": "19F0903A12BA87C0D43E67E64889B525.chk",
    "asset_map_hash": "2ab5774404c4efeb",
    "offset": 9650600,
}
EXPECTED_SHADER = {
    "size": 346835,
    "sha256": "0ae2d7d48a23e1a74c37a5f645620e270176aa67acdb9522391d0425473dbe55",
}
EXPECTED_DECOMP = {
    "size": 30975,
    "sha256": "b6fe68647e91533efbce43a1bf92f06f120f679a1d5578a549ba59b1941dc724",
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


def verify_source_identity(entries: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [
        entry
        for entry in entries
        if entry.get("Name") == EXPECTED_MAP["name"]
        and entry.get("Type") == EXPECTED_MAP["type"]
        and int(entry.get("PathID", 0)) == EXPECTED_MAP["path_id"]
    ]
    if len(matches) != 1:
        raise AssertionError(
            "current ScreenSpaceShadowResolve AssetMap identity mismatch: "
            f"expected one row, actual={len(matches)}"
        )
    entry = matches[0]
    actual_source = Path(str(entry.get("Source") or "")).name
    checks = {
        "asset_map_hash": entry.get("Hash"),
        "offset": entry.get("Offset"),
        "source_name": actual_source,
    }
    for key, actual in checks.items():
        if actual != EXPECTED_MAP[key]:
            raise AssertionError(
                f"current ScreenSpaceShadowResolve AssetMap {key} mismatch: "
                f"expected={EXPECTED_MAP[key]} actual={actual}"
            )
    return {
        "name": entry["Name"],
        "type": entry["Type"],
        "path_id": int(entry["PathID"]),
        "source_name": actual_source,
        "asset_map_hash": entry["Hash"],
        "offset": int(entry["Offset"]),
    }


def verify_shader_passes() -> dict[str, Any]:
    require_file(
        SHADER_EXPORT,
        EXPECTED_SHADER["size"],
        EXPECTED_SHADER["sha256"],
        "current ScreenSpaceShadowResolve shader export",
    )
    text = SHADER_EXPORT.read_text(encoding="utf-8")
    required = (
        'Shader "HGRP/ScreenSpaceShadowResolve"',
        'Name "ScreenSpaceShadowResolve"',
        'Name "ScreenSpaceShadowResolve_Character"',
        'Name "HDPLSScreenSpaceShadowResolve"',
        'Ref 4',
        'ReadMask 7',
    )
    for needle in required:
        if needle not in text:
            raise AssertionError(f"current resolve shader export missing {needle!r}")
    return {
        "path": str(SHADER_EXPORT.relative_to(REPO_ROOT)).replace("\\", "/"),
        **EXPECTED_SHADER,
        "passes": [
            "ScreenSpaceShadowResolve",
            "ScreenSpaceShadowResolve_Character",
            "HDPLSScreenSpaceShadowResolve",
        ],
        "character_stencil": {"ref": 4, "read_mask": 7, "comp": "Equal"},
    }


def verify_character_metadata() -> dict[str, Any]:
    if not CHARACTER_METADATA.is_file():
        raise AssertionError(f"missing character resolve metadata: {CHARACTER_METADATA}")
    metadata = json.loads(CHARACTER_METADATA.read_text(encoding="utf-8"))
    if metadata.get("SourcePassName") != "ScreenSpaceShadowResolve_Character":
        raise AssertionError(
            "character resolve metadata pass mismatch: "
            f"{metadata.get('SourcePassName')}"
        )
    if metadata.get("SourceSubShaderIndex") != 0 or metadata.get("SourcePassIndex") != 1:
        raise AssertionError(
            "character resolve metadata index mismatch: "
            f"subshader={metadata.get('SourceSubShaderIndex')} pass={metadata.get('SourcePassIndex')}"
        )
    textures = [item.get("Name") for item in metadata.get("TextureParameters", [])]
    expected_textures = [
        "_CameraDepthTexture",
        "_CSMShadowmapTex",
        "_CharacterShadowmapTex",
        "_CloudShadowTex",
        "_ASMShadowmapTex",
        "_GBufferTexture0",
        "_GBufferTexture1",
    ]
    if textures != expected_textures:
        raise AssertionError(
            f"character resolve texture bindings mismatch: expected={expected_textures} actual={textures}"
        )
    return {
        "path": str(CHARACTER_METADATA.relative_to(REPO_ROOT)).replace("\\", "/"),
        "pass": metadata["SourcePassName"],
        "source_pass_index": int(metadata["SourcePassIndex"]),
        "texture_bindings": textures,
        "character_shadow_texture_index": 7,
    }


def verify_character_g_producer() -> dict[str, Any]:
    require_file(
        CHARACTER_DECOMP,
        EXPECTED_DECOMP["size"],
        EXPECTED_DECOMP["sha256"],
        "current character resolve SPIR-V decompilation",
    )
    text = CHARACTER_DECOMP.read_text(encoding="utf-8")
    required = {
        "character_shadow_resource": "Texture2D<float4> _CharacterShadowmapTex : register(t7, space3);",
        "character_shadow_data": "column_major float4x4 ShadowData_CharacterWorldToShadow[15]",
        "character_shadow_biases": "float4 ShadowData_CharacterShadowBiases[15]",
        "character_shadow_light_direction": "float4 ShadowData_CharacterShadowLightDir[15]",
        "character_shadow_atlas": "float4 ShadowData_CharacterShadowAtlasParams[15]",
        "character_shadow_texel_size": "float4 ShadowData_CharacterShadowTexelSize",
        "character_index_decode": "float _829 = log2(float((((uint((_262.w * 3.0f)",
        "character_shadow_transform": "mul(ShadowData_CharacterWorldToShadow[_837],",
        "character_shadow_gather": "_CharacterShadowmapTex.GatherRed(sampler_LinearMirror,",
        "character_shadow_taps": "_908 < 16u",
        "character_shadow_output": "_4 = float3(lerp(1.0f, min(1.0f, _797.x), ShadowData_DirectionalShadowParams.x), _947, 0.0f);",
    }
    for label, needle in required.items():
        if needle not in text:
            raise AssertionError(
                f"current character resolve producer anchor missing: label={label} needle={needle!r}"
            )
    return {
        "path": str(CHARACTER_DECOMP.relative_to(REPO_ROOT)).replace("\\", "/"),
        **EXPECTED_DECOMP,
        "g_channel": {
            "source": "character shadow atlas",
            "index": "log2(packed GBufferTexture0 identity)",
            "projection": "CharacterWorldToShadow[index] with light-facing bias",
            "filter": "16 GatherRed taps with depth comparison",
            "output": "float3(scene_directional_shadow, character_shadow, 0)",
        },
        "retail_frame_parity": "not asserted",
    }


def verify_current_boundary() -> dict[str, Any]:
    entries = load_map_entries()
    return {
        "ok": True,
        "source_identity": verify_source_identity(entries),
        "shader_export": verify_shader_passes(),
        "character_metadata": verify_character_metadata(),
        "character_g_producer": verify_character_g_producer(),
        "interpretation": {
            "screen_shadow_mask_layout": "R scene directional shadow, G character shadow, B unused",
            "current_lab_content_gate": "remains disabled until runtime character atlas upload is validated",
            "retail_frame_parity": "not asserted",
        },
    }


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
