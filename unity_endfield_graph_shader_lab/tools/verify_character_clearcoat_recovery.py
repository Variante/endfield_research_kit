#!/usr/bin/env python3
"""Strict original-data verifier for the CharacterNPR clear-coat recovery."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
GAME_CHUNK = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS"
    r"\0CE8FA57\19F0903A12BA87C0D43E67E64889B525.chk"
)
SOURCE_MAP = (
    REPO
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps"
    / "endfield_streamingassets_assets.json"
)
EVIDENCE = PROJECT / "scratch/character_recovery/ruri_character_npr"
EXPORTED_SHADER = (
    EVIDENCE
    / "shader_export_sidecars/Shader/HGRP_CharacterNPR_p9371FF9C9E74391E.shader"
)
BYTECODE = EXPORTED_SHADER.with_name(EXPORTED_SHADER.name + ".bytecode")
RECOVERED_SHADER = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Shaders/Recovered"
    / "EndfieldCharacterClothRecovered.shader"
)
PLAYABLE = (
    PROJECT / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable"
)

CHARACTER_NPR_PATH_ID = -7822190029627442914

PINNED_FILES = {
    GAME_CHUNK: (
        211_831_350,
        "cbc87c7d8f41d90da25af7758cf77ced7321d19c52c067f6f77a75aa5dabc380",
    ),
    SOURCE_MAP: (
        759_252_292,
        "148415835f911fc94a634925c50c2d8b9a1cd4f5f141412f956cbb143805b6f3",
    ),
    EXPORTED_SHADER: (
        36_654_652,
        "a05d0c3bf09e3bd66b7662874d09a3a1d4b02d2d1094bfe56acdcae758c072bd",
    ),
    BYTECODE / "0025_endfield_dxbc_1.dxbc": (
        64_996,
        "9f607bbca3e27d20f8c1bd930adb607f2325d983b8167b107818b21af2f61979",
    ),
    BYTECODE / "0025_endfield_dxbc_1.dxbc.metadata.json": (
        28_739,
        "0cc03217e7839ae0a185a820ce50a1278c92b04fd9d028d4b779e697c69ac844",
    ),
    BYTECODE / "0193_endfield_dxbc_1.dxbc": (
        68_572,
        "33fcf3078381560f50cc3766fa8bcda34742ad968d659fbb600c87c6b4ead13a",
    ),
    BYTECODE / "0193_endfield_dxbc_1.dxbc.metadata.json": (
        28_758,
        "9c1996c4613e9dad6f059dcd258df03754efc74bdf2628f7e679201c76766b02",
    ),
    EVIDENCE / "metal_normal_forward_fragment.hlsl": (
        125_160,
        "3a4d5704a39bfce25b4889393426abe84c3754677cc125459c5f5ad75ffb319e",
    ),
    EVIDENCE / "clearcoat_metal_normal_forward_fragment.hlsl": (
        130_762,
        "4d5464334d464fdf7a52f3b42dff3da0f23bfed2c9a5d8eade566bec09c7e7a9",
    ),
    EVIDENCE / "metal_normal_forward_fragment.asm": (
        86_204,
        "14361178d7fa1ec90dbdc62003faefa3695b1cb686d658ef21521d0b9f3ed42f",
    ),
    EVIDENCE / "clearcoat_metal_normal_forward_fragment.asm": (
        90_835,
        "0c10e7a717431dd0bb7f7b15774ed4dbe465931065cd4cc8a140daae806a9d9b",
    ),
}

BASE_KEYWORDS = [
    "HG_ENABLE_PER_OBJECT_MV",
    "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK",
    "SRP_INSTANCING_ON",
    "_METALLICSPECGLOSSMAP",
    "_NORMALMAP",
]

EXPECTED_VARIANTS = {
    "0025": {
        "debug_name": "subshader0/pass0:ForwardLit/vertex/blob364/33",
        "keywords": BASE_KEYWORDS,
    },
    "0193": {
        "debug_name": "subshader0/pass0:ForwardLit/vertex/blob392/33",
        "keywords": BASE_KEYWORDS[:3] + ["_CLEARCOAT"] + BASE_KEYWORDS[3:],
    },
}

EXPECTED_MATERIALS = {
    "ardelia": {
        "name": "M_actor_ardelia_cloth_05",
        "path_id": 8240211286960059696,
        "json": "M_actor_ardelia_cloth_05_p725B1C81C96B3530.json",
        "size": 21_613,
        "sha256": "5154a9da641ffe58b12a992e32f47e65af5e773c13c11b7facea00f7c7a23d20",
        "metallic": 1.0,
        "normal_mode": 1.0,
        "smoothness": 0.908,
        "color": [0.6579857, 0.552125, 0.875, 1.0],
        "mask_path_id": 0,
    },
    "camille": {
        "name": "M_actor_camille_cloth_02",
        "path_id": -5523271509383216623,
        "json": "M_actor_camille_cloth_02_pB35965D3652D8211.json",
        "size": 21_742,
        "sha256": "a6a1d1c78f6fdad7940f2a54bd7bd9ffd4df4a67b8204c7533b7342f5588c93f",
        "metallic": 0.357,
        "normal_mode": 1.0,
        "smoothness": 1.0,
        "color": [0.7738768, 0.9066203, 0.90943396, 1.0],
        "mask_path_id": 0,
    },
    "chen": {
        "name": "M_wpn_misc_0002_01",
        "path_id": 7421457765546635011,
        "json": "M_wpn_misc_0002_01_p66FE508466F8AF03.json",
        "size": 21_451,
        "sha256": "f372ed86ab53c46eea844d686882c4204d6beed758cb62a46437a0ace3addf2a",
        "metallic": 0.0,
        "normal_mode": 0.0,
        "smoothness": 0.95,
        "color": [0.89100003, 0.91394734, 1.0, 1.0],
        "mask_path_id": 7023808903529468216,
    },
    "lastrite": {
        "name": "M_actor_lastrite_cloth_02",
        "path_id": 4627707172404591078,
        "json": "M_actor_lastrite_cloth_02_p4038EB2797B3F9E6.json",
        "size": 21_687,
        "sha256": "949865d15610636946a5e29e9b7065653e278dc1964dd9f044fdedfbebcc0bd5",
        "metallic": 0.47,
        "normal_mode": 1.0,
        "smoothness": 0.943,
        "color": [0.6627451, 0.8444607, 0.9764706, 1.0],
        "mask_path_id": 0,
    },
    "lizhiyan": {
        "name": "M_actor_lizhiyan_cloth_03",
        "path_id": 7258541699582035621,
        "json": "M_actor_lizhiyan_cloth_03_p64BB8537E6F286A5.json",
        "size": 35_660,
        "sha256": "6cbd926a0b0c31bbc077817db511bdfa0a114d063b08322735cad4a38033af81",
        "metallic": 0.3,
        "normal_mode": 1.0,
        "smoothness": 0.9,
        "color": [0.0, 0.91296387, 1.0, 1.0],
        "mask_path_id": 7786430986205329491,
    },
    "mifu": {
        "name": "M_actor_mifu_cloth_03",
        "path_id": -8381521011435758088,
        "json": "M_actor_mifu_cloth_03_p8BAEDB0C1BE61DF8.json",
        "size": 21_678,
        "sha256": "02c6770a892507cefad9c2a9d175bccbd0332388fd3a2982bb4297ee6df25343",
        "metallic": 0.424,
        "normal_mode": 1.0,
        "smoothness": 1.0,
        "color": [1.0, 1.0, 1.0, 1.0],
        "mask_path_id": -305539405380476928,
    },
    "tangtang": {
        "name": "M_actor_tangtang_cloth_03",
        "path_id": -698422753149858780,
        "json": "M_actor_tangtang_cloth_03_pF64EB434D773CC24.json",
        "size": 21_712,
        "sha256": "dfdfa5bf23c9286947b39c7e602f9fc13c0f145d313aceb58532823a433b29c4",
        "metallic": 0.75,
        "normal_mode": 1.0,
        "smoothness": 0.7,
        "color": [0.4594196, 0.71781015, 0.8784314, 1.0],
        "mask_path_id": -6769624548349941593,
    },
    "yvonne": {
        "name": "M_actor_yvonne_cloth_03",
        "path_id": -4604803984280465497,
        "json": "M_actor_yvonne_cloth_03_pC018732C70A8CFA7.json",
        "size": 21_570,
        "sha256": "6f4252a41d79d21de79473a162efc2ce208830ab49ba3d74fb71da577600bc67",
        "metallic": 0.517,
        "normal_mode": 1.0,
        "smoothness": 0.85,
        "color": [1.0, 1.0, 1.0, 1.0],
        "mask_path_id": -2339335844287429574,
    },
}

# Most of the original playable manifests expose one clear-coat material per
# actor.  Liino is an intentional exception: the post-model contains a
# clothing material plus a skill material and its LOD copy.  Keep these as
# separate source-authored rows instead of collapsing them by actor token (or
# silently accepting whichever manifest happens to be visited first).
EXPECTED_MATERIAL_VARIANTS = {
    actor: [expected] for actor, expected in EXPECTED_MATERIALS.items()
}
EXPECTED_MATERIAL_VARIANTS["liino"] = [
    {
        "name": "M_actor_liino_cloth_04",
        "path_id": 2821061305164868905,
        "json": "M_actor_liino_cloth_04_p27266C4F77F3AD29.json",
        "size": 21_669,
        "sha256": "547f7376dc362fda62d688936f78f5a016f314cb5a341afd74275c265d5b1397",
        "metallic": 0.75,
        "normal_mode": 1.0,
        "smoothness": 0.384,
        "color": [1.0, 1.0, 1.0, 1.0],
        "mask_path_id": 0,
    },
    {
        "name": "M_actor_liino_skill_01",
        "path_id": 2046064906034311838,
        "json": "M_actor_liino_skill_01_p1C6515310791729E.json",
        "size": 21_659,
        "sha256": "788e7ce229159f172968548b2cfb0224c0f33bf3d711eeb9d20b193967134088",
        "metallic": 0.363,
        "normal_mode": 1.0,
        "smoothness": 0.938,
        "color": [0.8951385, 1.0, 0.8660377, 1.0],
        "mask_path_id": -3864852781857798233,
    },
    {
        "name": "M_actor_lod_liino_skill_01",
        "path_id": -6953818256598606552,
        "json": "M_actor_lod_liino_skill_01_p9F7F132376D05D28.json",
        "size": 21_667,
        "sha256": "6bdbc4d96e065717c516cc3204a7cad2dcc6f5a3ffb48f469573b5011f5994e1",
        "metallic": 0.363,
        "normal_mode": 1.0,
        "smoothness": 0.938,
        "color": [0.8951385, 1.0, 0.8660377, 1.0],
        "mask_path_id": -3864852781857798233,
    },
]

DIRECT_BLOCK_SHA256 = "adc855c5e353deabda8f24b281735ce3cad10e38f6f25e3714327f711df23e18"
ENVIRONMENT_BLOCK_SHA256 = "3e8ee002e028f1cbff89c5e030af581c62336173016af0b7d56b56e30e890614"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def path_id(reference: object) -> int:
    if not isinstance(reference, dict):
        return 0
    return int(reference.get("m_PathID") or 0)


def verify_pinned_files() -> None:
    for path, (expected_size, expected_hash) in PINNED_FILES.items():
        require(path.is_file(), f"missing pinned source: {path}")
        require(path.stat().st_size == expected_size, f"source size drift: {path}")
        require(sha256(path) == expected_hash, f"source SHA-256 drift: {path}")


def verify_shader_identity() -> None:
    # The map is 759 MiB. Scan its pretty-printed flat AssetEntries one object
    # at a time so verification remains bounded even while Unity is using most
    # of the machine's memory; the complete file is still size/hash-gated.
    matches: list[dict] = []
    in_entries = False
    entry_lines: list[str] | None = None
    with SOURCE_MAP.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not in_entries:
                if line.strip() == '"AssetEntries": [':
                    in_entries = True
                continue
            stripped = line.rstrip("\r\n")
            if entry_lines is None:
                if stripped == "    {":
                    entry_lines = [line]
                elif stripped == "  ]":
                    break
                continue
            entry_lines.append(line)
            if stripped in {"    },", "    }"}:
                entry_text = "".join(entry_lines).rstrip()
                if entry_text.endswith(","):
                    entry_text = entry_text[:-1]
                item = json.loads(entry_text)
                if item.get("Name") == "HGRP/CharacterNPR":
                    matches.append(item)
                entry_lines = None
    require(entry_lines is None, "truncated source-map AssetEntry")
    require(len(matches) == 1, "CharacterNPR source-map identity drift")
    item = matches[0]
    require(int(item.get("PathID") or 0) == CHARACTER_NPR_PATH_ID, "CharacterNPR PathID drift")
    require(
        str(item.get("Container") or "").lower()
        == "packages/com.hg.render-pipelines/runtime/shaders/materials/characternpr/characternpr.shader",
        "CharacterNPR container drift",
    )
    require(str(item.get("Source") or "").endswith("19F0903A12BA87C0D43E67E64889B525.chk"), "CharacterNPR CHK source drift")
    require(int(item.get("Offset") or -1) == 185_104_054, "CharacterNPR CHK offset drift")
    require(str(item.get("Hash") or "").lower() == "6e1e996a72074e02", "CharacterNPR logical hash drift")


def verify_variants() -> None:
    for stem, expected in EXPECTED_VARIANTS.items():
        path = BYTECODE / f"{stem}_endfield_dxbc_1.dxbc.metadata.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("DebugName") == expected["debug_name"], f"{stem}: debug carrier drift")
        require(payload.get("SourceSubShaderIndex") == 0, f"{stem}: subshader drift")
        require(payload.get("SourcePassIndex") == 0, f"{stem}: pass drift")
        require(payload.get("SourcePassName") == "ForwardLit", f"{stem}: pass-name drift")
        require(payload.get("SourceCompilerPlatform") == "d3d11", f"{stem}: compiler platform drift")
        require(payload.get("DecodedProgramStage") == "fragment", f"{stem}: decoded stage drift")
        require(payload.get("DecodedProgramEncoding") == "DXBC", f"{stem}: encoding drift")
        require(payload.get("SourceCompiledKeywords") == expected["keywords"], f"{stem}: keyword drift")
        require(payload.get("SourceLocalKeywords") == [], f"{stem}: local keyword drift")
        # AnimeStudio still reports the serialized stage carrier as vertex;
        # the decoded DXBC program itself is conclusively a fragment program.
        require(payload.get("SourceSerializedProgramStage") == "vertex", f"{stem}: serialized-stage boundary drift")


def verify_materials() -> None:
    recovered: dict[str, list[dict]] = {}
    for manifest_path in sorted(PLAYABLE.glob("*/*_ui_recovery_manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actor = str(manifest.get("actor_token") or "")
        for material in (manifest.get("materials") or {}).values():
            if not isinstance(material, dict):
                continue
            source_path = Path(str(material.get("json") or ""))
            if not source_path.is_file():
                continue
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            floats = payload.get("m_SavedProperties", {}).get("m_Floats", {})
            if (
                path_id(payload.get("m_Shader")) == CHARACTER_NPR_PATH_ID
                and floats.get("_ClearCoat") == 1.0
            ):
                recovered.setdefault(actor, []).append(
                    {"manifest": material, "source": source_path, "payload": payload}
                )

    require(
        set(recovered) == set(EXPECTED_MATERIAL_VARIANTS),
        "playable clear-coat census drift",
    )
    for actor, expected_variants in EXPECTED_MATERIAL_VARIANTS.items():
        rows = sorted(
            recovered[actor], key=lambda row: int(row["manifest"].get("path_id") or 0)
        )
        expected_rows = sorted(expected_variants, key=lambda row: row["path_id"])
        require(
            len(rows) == len(expected_rows),
            f"{actor}: clear-coat material count drift",
        )
        for row, expected in zip(rows, expected_rows):
            material = row["manifest"]
            source_path = row["source"]
            payload = row["payload"]
            properties = payload["m_SavedProperties"]
            floats = properties["m_Floats"]
            colors = properties["m_Colors"]
            mask_texture = properties["m_TexEnvs"]["_ClearCoatMask"]["m_Texture"]
            color = colors["_ClearCoatColor"]

            require(material.get("name") == expected["name"], f"{actor}: material-name drift")
            require(int(material.get("path_id") or 0) == expected["path_id"], f"{actor}: material PathID drift")
            require(source_path.name == expected["json"], f"{actor}: material source-path drift")
            require(source_path.stat().st_size == expected["size"], f"{actor}: material source-size drift")
            require(sha256(source_path) == expected["sha256"], f"{actor}: material source-hash drift")
            require(path_id(payload.get("m_Shader")) == CHARACTER_NPR_PATH_ID, f"{actor}: shader PPtr drift")
            require(floats.get("_ClearCoat") == 1.0, f"{actor}: clear-coat toggle drift")
            require("_ClearCoatMask" not in floats, f"{actor}: unexpected scalar clear-coat mask")
            require(floats.get("_ClearCoatMetallic") == expected["metallic"], f"{actor}: metallic drift")
            require(floats.get("_ClearCoatNormalMode") == expected["normal_mode"], f"{actor}: normal-mode drift")
            require(floats.get("_ClearCoatSmoothness") == expected["smoothness"], f"{actor}: smoothness drift")
            require(
                [color[channel] for channel in "rgba"] == expected["color"],
                f"{actor}: authored clear-coat color drift",
            )
            require(path_id(mask_texture) == expected["mask_path_id"], f"{actor}: clear-coat mask PPtr drift")


def verify_generated_materials() -> None:
    """Prove Unity retained every newly exposed authored clear-coat field."""

    def verify_one(actor: str, expected: dict) -> None:
        filename = f"actor_{actor}_pathid_{expected['path_id']}.mat"
        matches = list(PLAYABLE.glob(f"*/Materials/{filename}"))
        require(len(matches) == 1, f"{actor}: generated clear-coat material missing")
        source = matches[0].read_text(encoding="utf-8").replace("\r\n", "\n")

        def float_value(name: str) -> float:
            match = re.search(
                rf"^\s+- {re.escape(name)}: ([-+0-9.eE]+)\s*$",
                source,
                re.MULTILINE,
            )
            require(match is not None, f"{actor}: generated {name} missing")
            return float(match.group(1))

        require(float_value("_ClearCoat") == 1.0, f"{actor}: generated toggle drift")
        require(float_value("_ClearCoatMetallic") == expected["metallic"], f"{actor}: generated metallic drift")
        require(float_value("_ClearCoatNormalMode") == expected["normal_mode"], f"{actor}: generated normal-mode drift")
        require(float_value("_ClearCoatSmoothness") == expected["smoothness"], f"{actor}: generated smoothness drift")

        color_match = re.search(
            r"^\s+- _ClearCoatColor: \{r: ([-+0-9.eE]+), g: ([-+0-9.eE]+), "
            r"b: ([-+0-9.eE]+), a: ([-+0-9.eE]+)\}\s*$",
            source,
            re.MULTILINE,
        )
        require(color_match is not None, f"{actor}: generated authored clear-coat color missing")
        require(
            [float(value) for value in color_match.groups()] == expected["color"],
            f"{actor}: generated authored clear-coat color drift",
        )

        mask_match = re.search(
            r"^\s+- _ClearCoatMask:\n\s+m_Texture: \{fileID: (\d+)(?:, [^}]*)?\}",
            source,
            re.MULTILINE,
        )
        require(mask_match is not None, f"{actor}: generated clear-coat mask binding missing")
        generated_mask_is_null = int(mask_match.group(1)) == 0
        require(
            generated_mask_is_null == (expected["mask_path_id"] == 0),
            f"{actor}: generated clear-coat mask nullability drift",
        )

    for actor, expected_variants in EXPECTED_MATERIAL_VARIANTS.items():
        for expected in expected_variants:
            verify_one(actor, expected)


def verify_recovered_shader() -> None:
    source = RECOVERED_SHADER.read_text(encoding="utf-8").replace("\r\n", "\n")
    direct_start = source.index("// Exact `_CLEARCOAT` ForwardLit carrier")
    direct_end = source.index("if (clothSpecularMode > 1.5)", direct_start)
    direct = source[direct_start:direct_end].encode("utf-8")
    require(hashlib.sha256(direct).hexdigest() == DIRECT_BLOCK_SHA256, "recovered direct clear-coat block drift")

    environment_start = source.index("if (recoveredClearCoatActive)", direct_end)
    environment_end = source.index("#if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)", environment_start)
    environment = source[environment_start:environment_end].rstrip().encode("utf-8")
    require(
        hashlib.sha256(environment).hexdigest() == ENVIRONMENT_BLOCK_SHA256,
        "recovered environment clear-coat block drift",
    )

    required = [
        '_ClearCoatNormalMode ("Clear Coat Normal Mode", Range(0,1)) = 0',
        '[HDR] _ClearCoatColor ("Clear Coat Color", Color) = (1,1,1,1)',
        "tex2Dbias(\n                    _ClearCoatMask,\n                    float4(uv, 0.0, _GlobalMipBias)).r",
        "recoveredClearCoatMask > 0.001",
        "recoveredClearCoatRoughnessRaw *\n                    recoveredClearCoatRoughnessRaw,\n                    0.0078125",
        "recoveredClearCoatMask * recoveredClearCoatFresnel",
        "recoveredClearCoatBaseSpecAttenuation *\n                         recoveredClearCoatBaseSpecAttenuation",
        "1.0 - recoveredClearCoatMask *\n                        recoveredClearCoatMaskedFresnel",
        "recoveredClearCoatF0 * recoveredClearCoatDfgX +\n                            recoveredClearCoatDfgY",
        "recoveredClearCoatCubemapReflection *\n                            recoveredClearCoatMask",
        "(float3)color * recoveredClearCoatDiffuseAttenuation",
    ]
    for marker in required:
        require(marker in source, f"recovered shader semantic missing: {marker!r}")


def main() -> int:
    verify_pinned_files()
    verify_shader_identity()
    verify_variants()
    verify_materials()
    verify_generated_materials()
    verify_recovered_shader()
    print("CharacterNPR clear-coat original-data verification passed")
    print(f"  shader PathID: {CHARACTER_NPR_PATH_ID}")
    print("  selected fragments: blob364/33 control, blob392/33 _CLEARCOAT")
    print(
        "  playable clear-coat materials: "
        f"{sum(len(rows) for rows in EXPECTED_MATERIAL_VARIANTS.values())}"
    )
    print(f"  recovered shader SHA-256: {sha256(RECOVERED_SHADER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
