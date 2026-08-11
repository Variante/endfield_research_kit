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


def verify_current_boundary() -> dict[str, Any]:
    entries = load_map_entries()
    result = {
        "ok": True,
        "source_identity": verify_shader_map(entries),
        "materials": verify_materials(entries),
        "compiled_variants": verify_sidecars(),
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
