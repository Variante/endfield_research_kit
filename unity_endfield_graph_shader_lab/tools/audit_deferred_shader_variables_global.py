#!/usr/bin/env python3
"""Scope the selected deferred resolver's actual ShaderVariablesGlobal reads."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ASSEMBLY = Path(r"D:/Program Files/Endfield Game/GameAssembly.dll")
SOURCES = {
    "selectedFragment": (
        LAB_ROOT
        / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
        "selected_fragment.hlsl"
    ),
    "selectedDxbcFragment": (
        LAB_ROOT
        / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
        "selected_fragment_dxbc.hlsl"
    ),
    "selectedMetadata": (
        LAB_ROOT
        / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
        "selected_fragment.enriched.metadata.json"
    ),
    "heightFogReset": (
        REPO_ROOT
        / "scratch/reverse_engineering/gacha_deferred_exact_binding_contents/"
        "native_height_fog_reset.json"
    ),
    "globalMipBias": (
        REPO_ROOT
        / "scratch/reverse_engineering/global_mip_bias_producer/"
        "global_mip_bias_producer_report.json"
    ),
    "inactiveIrradianceV2": (
        LAB_ROOT
        / "scratch/character_recovery/charinfo_pass0_resources/"
        "charinfo_v2_irradiance.json"
    ),
}
EXPECTED_HASHES = {
    "gameAssembly": (
        "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
    ),
    "selectedFragment": (
        "44dc5090af87a8f65ffca870f9e02b8525c4cfe14f84cf8feaa3ea6c49e4b9db"
    ),
    "selectedDxbcFragment": (
        "c748ee49a72794ef81f6795bee934775e42958ad74e9560c0730e8d83686906d"
    ),
    "selectedMetadata": (
        "c296317ff6e7aa8d5d35b1c6705117dbdee37ff4163b4b093e69262e85e3a826"
    ),
    "heightFogReset": (
        "44bb502de793304f3db0543602fb43afd022f247f320b52506e50bddff617740"
    ),
    "globalMipBias": (
        "bdd8901d5c5b89fa2105eb3425cd1807a6592ba1e21436986f31f1c84f62035f"
    ),
    "inactiveIrradianceV2": (
        "1f77756f536c394efcbfcd1d6d00fca9ed4b40e86f7cdad9c14cf7379af5a5b3"
    ),
}
OUTPUT = (
    LAB_ROOT
    / "scratch/character_recovery/deferred_shader_variables_global/audit.json"
)

SETTING_TEXT_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/b35_settings/text_export/TextAsset"
)
SETTING_FILES = {
    "CinematicSettings.ini": {
        "file": "CinematicSettings_p02A48AAA604195BF.json",
        "jsonSha256": "ae62d265d65b00c6cb7668d784616f13bdd8de1a16b4921893382d1225077dfc",
        "payloadSha256": "c0cd749dd829222aab2a2761e0ca7e61ed0d72e87dd2d294a3c65e2bc9358c73",
    },
    "CloudDesktopOverride.ini": {
        "file": "CloudDesktopOverride_p4CDB7A1FBABEC323.json",
        "jsonSha256": "dc463379b4ba195124e457d8f9c53bf3d48a2c38eaca49cb73bfcc4b914b35b2",
        "payloadSha256": "439af33ecca9b7b400a6b92b17ca279b488d47652b04296d95d868b85a7be7f4",
    },
    "CommonSettings.ini": {
        "file": "CommonSettings_p2936E10EDCE2C9E4.json",
        "jsonSha256": "f52077b159108fa369faaeb9f8b42dcb50f0df145f34bf4374c0ccf38e4fb6c3",
        "payloadSha256": "aed529949a67769c9066ead730aea1f4144cc8f9ecd63d5debf6e59670649049",
    },
    "ConsoleSettings.ini": {
        "file": "ConsoleSettings_p6DB117C9F26E1FCE.json",
        "jsonSha256": "115b5a3cbab70ccee1b6366ca41f7dd9c4fc8f61ea523522799ee7880209e5a1",
        "payloadSha256": "0d077462addf6478a90abf6584f6e0844c8b3ef0ff929465dc6c04c6b2e3ea69",
    },
    "DesktopSettings.ini": {
        "file": "DesktopSettings_p99C7C961A15A8994.json",
        "jsonSha256": "73b5a1579aec9439e604906af5be6b9f4fc4ca10cb5be4855e1ee2c3ccd2e4ad",
        "payloadSha256": "a4a0b652162a13e5c5cad39e7c290641dd83116b984d884e246cacf7991f1f10",
    },
    "HGRenderPipelineSettings.ini": {
        "file": "HGRenderPipelineSettings_p0EA7FF83EAC093AD.json",
        "jsonSha256": "0629f1b85befe3c2e400491b78c2a3de1afe14472b7201006a228d5281140317",
        "payloadSha256": "05a4fb96d13a4766757c965df6c5c2a478964ab40d8d2df31659a39e6b710abf",
    },
    "MobileSettings.ini": {
        "file": "MobileSettings_p883CA7EF83FC2F7C.json",
        "jsonSha256": "f50102f24addcb36f05181b559d050d7fd560196a284158ec2b4f88d3390a07a",
        "payloadSha256": "f9f3388bf3ddb6c0dfbecdac952244044589acb4bb6d7231f0e41a968e463a72",
    },
}
SETTING_MANIFEST = {
    "file": "SettingFiles_pA5D65C734C247CA7.json",
    "jsonSha256": "4b2bfc1d5b626288d7d8b7b13f784e88f999a1f0e8884d5a02781f72d924ab34",
    "payloadSha256": "6031cb98e345cd347830658d3661067af0a6b34ca58f92bc5f9ee6f0ed75d14c",
}
VOLUME_PROFILES = {
    "CharInfo_Volume": {
        "path": (
            LAB_ROOT
            / "scratch/character_recovery/charinfo_volume_state/export/MonoBehaviour/"
            "CharInfo_Volume_p8B672C2D300FB560.json"
        ),
        "sha256": "7e1fa59a6924952519c1672abdb159b036a209dd347e7533a5c0c3e6152a4f4c",
        "components": [
            "Bloom",
            "Tonemapping",
            "ColorAdjustments",
            "Vignette",
            "HGSharpen",
            "ColorLookup",
            "HGAutoExposure",
            "HGShadowSettings",
            "HGCharacterVolume",
            "ShadowsMidtonesHighlights",
            "HGDisableDirectionalShadowComponent",
            "HGChromaticAbberation",
        ],
    },
    "CharOverrideVolumeProfile": {
        "path": (
            LAB_ROOT
            / "scratch/character_recovery/charinfo_volume_state/export/MonoBehaviour/"
            "CharOverrideVolumeProfile_p1F791EC790728B5D.json"
        ),
        "sha256": "d103e65b492bd2ae402efaa086c34817c7df03f35dba7820f4f31e0fd944cebf",
        "components": ["HGCharacterVolume"],
    },
    "DefaultSettingsVolumeProfile": {
        "path": (
            REPO_ROOT
            / "scratch/animestudio/b35_settings/export/MonoBehaviour/"
            "DefaultSettingsVolumeProfile_p9275573295A68224.json"
        ),
        "sha256": "61685beb4e17487fd0f315889782e4a8ab24f29784e471c6128b54577a112115",
        "components": [],
    },
    "DefaultLookDevProfile": {
        "path": (
            REPO_ROOT
            / "scratch/animestudio/b35_settings/export/MonoBehaviour/"
            "DefaultLookDevProfile_p156F70A47D3CD82F.json"
        ),
        "sha256": "593f7818a33cfc4b118f0406921f817a630140bb4ace7186afa157b76ef7542e",
        "components": ["Tonemapping", "HGShadowSettings", "Bloom"],
    },
}

# These methods are the current installed non-IFix reset producers. Hashing the
# complete method bodies makes the decoded vectors below fail closed on drift.
NATIVE_METHODS = {
    "atmosphereFogReset": {
        "method": (
            "HG.Rendering.Runtime.HGAtmosphereRenderer."
            "ResetShaderVariablesGlobalAtmosphereFog"
        ),
        "methodIndex": 284536,
        "va": "0x189cdf408",
        "fileOffset": 0x9CDDA08,
        "size": 0x1A0,
        "sha256": (
            "40e8d04110fb803de8e3559f07169a643c44e42b39723b4fc96929e14dac6a8c"
        ),
        "vectors": {
            "c71": [0.0, 0.0, 0.0, 0.0],
            "c72": [0.0, 0.0, 1.0, 0.0010000000474974513],
            "c73": [9.999999747378752e-06] * 3 + [0.0],
            "c74": [0.0, 0.0, 0.0, -1.0],
            "c75": [0.0, 0.0, 0.0, 0.0],
            "c76": [0.0, 0.0, 0.0, -65535.0],
        },
    },
    "heightFogReset": {
        "method": (
            "HG.Rendering.Runtime.HGAtmosphereRenderer."
            "ResetShaderVariablesGlobalHeightFog"
        ),
        "methodIndex": 284538,
        "va": "0x189cdf664",
        "fileOffset": 0x9CDDC64,
        "size": 0x128,
        "sha256": (
            "e3c3397a936002165d66bc6f61f9ff7b7acb0730cd09fa0938644f587bb156ea"
        ),
        "vectors": {
            "c77": [0.0, 0.0, 0.0, 0.0],
            "c78": [0.0, 0.0, 0.0, 0.0],
            "c79": [0.0, 0.0, 0.0, 1.0],
            "c80": [0.0, 0.0, 0.0, 0.0],
            "c81": [0.0, 1.0, 0.0, 0.0],
            "c82": [0.0, 0.0, 0.0, 1.0],
        },
    },
    "volumetricFogReset": {
        "method": (
            "HG.Rendering.Runtime.HGVolumetricFogRenderer."
            "ResetShaderVariablesGlobalVolumetricFog"
        ),
        "methodIndex": 284730,
        "va": "0x189cee4bc",
        "fileOffset": 0x9CECABC,
        "size": 0xB8,
        "sha256": (
            "310ada3d2bdc604c4bd60fabeda47bebc76a577f9e9255e73a8609beb6be072b"
        ),
        "vectors": {
            f"c{row}": [0.0, 0.0, 0.0, 0.0]
            for row in range(83, 88)
        },
    },
}

# The selected c31.x path is deliberately pinned separately from reset
# producers: the writer reads SettingParameter<int> at HGSettingParameters
# +0x608 through op_Implicit, while the constructor creates that parameter
# with default value 7. Installed SettingFiles are audited below so every
# shipped override either also says 7 or leaves the code default untouched.
NATIVE_GRAPHICS_FEATURE_METHODS = {
    "graphicsFeatureWriter": {
        "method": (
            "HG.Rendering.Runtime.HGRenderPathScene."
            "UpdateShaderVariablesGraphFeaturesGlobalParam0"
        ),
        "methodIndex": 288044,
        "va": "0x189c04298",
        "fileOffset": 0x9C02898,
        "size": 0xF4,
        "sha256": (
            "251b339f8eab8844065a8fb6844b1fea606ffd5037b065270dcbc72aac52bb51"
        ),
        "writes": {
            "c30.x": "float(HGCamera.aoEnable)",
            "c30.y": "float(HGCamera.ssrEnable)",
            "c30.zw": [1.0, 1.0],
            "c31.x": (
                "float(SettingParameter<int>.op_Implicit("
                "HGSettingParameters[+0x608]))"
            ),
        },
    },
    "settingParametersConstructor": {
        "method": "HG.Rendering.Runtime.HGSettingParameters..ctor",
        "methodIndex": 288533,
        "va": "0x1836590a0",
        "fileOffset": 0x36576A0,
        "size": 0x35C0,
        "sha256": (
            "88def7f7f433864001f970bab9d4911e86b5a12bdf20d649798a5f0a3a7afe28"
        ),
        "field": "<reflectionProbeMaxSampleMip>k__BackingField",
        "fieldOffset": "0x608",
        "fieldType": "SettingParameter<int>",
        "defaultValue": 7,
        "parameterName": "reflectionProbeMaxSampleMip",
    },
    "aoGetter": {
        "method": "HG.Rendering.Runtime.HGCamera.get_aoEnable",
        "methodIndex": 286658,
        "va": "0x183c2f060",
        "fileOffset": 0x3C2D660,
        "size": 0x2C0,
        "sha256": "c6c21ef2818d11043fc69d0b6b58ebb72e8d37ef18e96a26f8de08d8a30f3f0d",
        "componentField": "VolumeComponentsData.m_GTAmbientOcclusion",
        "componentFieldOffset": "0xa0",
        "result": "component exists and GTAmbientOcclusion.IsActive()",
    },
    "ssrGetter": {
        "method": "HG.Rendering.Runtime.HGCamera.get_ssrEnable",
        "methodIndex": 286657,
        "va": "0x1831cb6d0",
        "fileOffset": 0x31C9CD0,
        "size": 0x370,
        "sha256": "0f49673e8a247cade7e25eea4975210fe2c3c1b17f894b1253498de841a2d8f5",
        "componentField": "VolumeComponentsData.m_hgssrVolume",
        "componentFieldOffset": "0x80",
        "result": (
            "component exists and ScreenSpaceReflectionVolume.IsActive() and "
            "pipeline HiZ/SSR capability and compute-shader gates pass"
        ),
    },
    "gtaoIsActive": {
        "method": "HG.Rendering.Runtime.GTAmbientOcclusion.IsActive",
        "methodIndex": 286355,
        "va": "0x183c2f320",
        "fileOffset": 0x3C2D920,
        "size": 0x110,
        "sha256": "a1559d52220b9a23f74b768d645e90ec62c6505cde962c8dbfc5cd01ec347856",
        "result": "bool(enable.value)",
    },
    "ssrIsActive": {
        "method": "HG.Rendering.Runtime.ScreenSpaceReflectionVolume.IsActive",
        "methodIndex": 286449,
        "va": "0x1831cba40",
        "fileOffset": 0x31CA040,
        "size": 0x110,
        "sha256": "e9ff34d8d5f78ad88712f6352a2ba3fece9fee90df92d8ab9439e83bef6cae05",
        "result": "bool(enable.value)",
    },
    "gtaoConstructor": {
        "method": "HG.Rendering.Runtime.GTAmbientOcclusion..ctor",
        "methodIndex": 286356,
        "va": "0x184405a20",
        "fileOffset": 0x4404020,
        "size": 0xD30,
        "sha256": "6527f74df8c3e4823a73bf95b4017c10d46c9b968718cd233ccd23b5f1541c04",
        "enableFieldOffset": "0x30",
        "enableDefault": False,
    },
    "ssrConstructor": {
        "method": "HG.Rendering.Runtime.ScreenSpaceReflectionVolume..ctor",
        "methodIndex": 286450,
        "va": "0x1845d07d0",
        "fileOffset": 0x45CEDD0,
        "size": 0x190,
        "sha256": "012f0039bb4da97b9ca81e23bbcd90c15371c810d689be05caf8e35a8f5dc91b",
        "enableFieldOffset": "0x30",
        "enableDefault": False,
    },
}

EXPECTED_USED_FIELDS = {
    "AtmosphereFogParams0",
    "AtmosphereFogParams1",
    "AtmosphereFogParams2",
    "AtmosphereFogParams3",
    "AtmosphereFogParams4",
    "AtmosphereFogParams5",
    "BinningBufferOffsets",
    "EnvironmentGlobalParams0",
    "ExponentialFogParams0",
    "ExponentialFogParams1",
    "ExponentialFogParams2",
    "ExponentialFogParams3",
    "ExponentialFogParams4",
    "ExponentialFogParams5",
    "f_48",
    "FrameCount",
    "GlobalMipBias",
    "GraphicsFeaturesGlobalParam0",
    "GraphicsFeaturesGlobalParam1",
    "IVDefaultSHAb",
    "IVDefaultSHAg",
    "IVDefaultSHAr",
    "IVParam0",
    "IVParam1",
    "IVParam2",
    "ScreenSize",
    "unity_OrthoParams",
    "VolumetricFogParams0",
    "VolumetricFogParams1",
    "VolumetricFogParams2",
    "VolumetricFogParams3",
    "VolumetricFogParams4",
    "WaterWetnessMaskParam0",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred ShaderVariablesGlobal audit failed: "
            f"check={check}; expected={expected!r}; actual={actual!r}"
        )


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def decode_text_asset(path: Path) -> bytes:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(f"{path.name}_m_Script", isinstance(payload.get("m_Script"), str), True)
    return base64.b64decode(payload["m_Script"], validate=True)


def parse_layout(source: str) -> dict[str, dict[str, object]]:
    match = re.search(
        r"cbuffer type_ShaderVariablesGlobal.*?\n\{(.*?)\n\};",
        source,
        re.DOTALL,
    )
    require("b35_declaration", match is not None, True)
    pattern = re.compile(
        r"\b(?:column_major\s+)?(?:float|int|uint)(?:[1-4](?:x[1-4])?)?\s+"
        r"ShaderVariablesGlobal_([A-Za-z0-9_]+)(?:\[(\d+)\])?\s*:\s*"
        r"packoffset\(c(\d+)(?:\.([xyzw]))?\);"
    )
    layout: dict[str, dict[str, object]] = {}
    for row in pattern.finditer(match.group(1)):
        layout[row.group(1)] = {
            "row": int(row.group(3)),
            "lane": row.group(4) or "xyzw",
            "arrayCount": int(row.group(2) or "1"),
        }
    return layout


def parse_body_uses(source: str, layout: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    body_offset = source.find("void frag_main")
    if body_offset < 0:
        body_offset = source.find("void main")
    require("fragment_body", body_offset >= 0, True)
    body = source[body_offset:]
    uses: list[dict[str, object]] = []
    pattern = re.compile(
        r"ShaderVariablesGlobal_([A-Za-z0-9_]+)(?:\[[^\]]+\])?"
        r"(?:\.([xyzw]+))?"
    )
    for match in pattern.finditer(body):
        field = match.group(1)
        require(f"layout_for_{field}", field in layout, True)
        line = source.count("\n", 0, body_offset + match.start()) + 1
        uses.append(
            {
                "field": field,
                "row": layout[field]["row"],
                "lanes": match.group(2) or layout[field]["lane"],
                "line": line,
            }
        )
    return uses


def build_audit() -> dict[str, object]:
    hashes = {name: sha256(path) for name, path in SOURCES.items()}
    game_hash = sha256(GAME_ASSEMBLY)
    require("gameAssembly_sha256", game_hash, EXPECTED_HASHES["gameAssembly"])
    for name, expected in EXPECTED_HASHES.items():
        if name == "gameAssembly":
            continue
        require(f"{name}_sha256", hashes[name], expected)

    game_bytes = GAME_ASSEMBLY.read_bytes()
    for name, method in NATIVE_METHODS.items():
        start = method["fileOffset"]
        body = game_bytes[start : start + method["size"]]
        require(f"{name}_size", len(body), method["size"])
        require(
            f"{name}_sha256",
            hashlib.sha256(body).hexdigest(),
            method["sha256"],
        )
    for name, method in NATIVE_GRAPHICS_FEATURE_METHODS.items():
        start = method["fileOffset"]
        body = game_bytes[start : start + method["size"]]
        require(f"{name}_size", len(body), method["size"])
        require(
            f"{name}_sha256",
            hashlib.sha256(body).hexdigest(),
            method["sha256"],
        )

    manifest_path = SETTING_TEXT_ROOT / SETTING_MANIFEST["file"]
    require(
        "setting_manifest_json_sha256",
        sha256(manifest_path),
        SETTING_MANIFEST["jsonSha256"],
    )
    manifest_payload = decode_text_asset(manifest_path)
    require(
        "setting_manifest_payload_sha256",
        hashlib.sha256(manifest_payload).hexdigest(),
        SETTING_MANIFEST["payloadSha256"],
    )
    manifest_names = [
        row.strip()
        for row in manifest_payload.decode("utf-8-sig").splitlines()
        if row.strip()
    ]
    require("setting_manifest_names", set(manifest_names), set(SETTING_FILES))
    expected_exports = {
        value["file"] for value in SETTING_FILES.values()
    } | {SETTING_MANIFEST["file"]}
    actual_exports = {path.name for path in SETTING_TEXT_ROOT.glob("*.json")}
    require("setting_export_file_set", actual_exports, expected_exports)

    setting_matrix: dict[str, dict[str, object]] = {}
    explicit_mip_values: list[int] = []
    for setting_name in manifest_names:
        expected = SETTING_FILES[setting_name]
        path = SETTING_TEXT_ROOT / expected["file"]
        require(f"{setting_name}_json_sha256", sha256(path), expected["jsonSha256"])
        payload = decode_text_asset(path)
        require(
            f"{setting_name}_payload_sha256",
            hashlib.sha256(payload).hexdigest(),
            expected["payloadSha256"],
        )
        text = payload.decode("utf-8-sig")
        matches = re.findall(
            r"^reflectionProbeMaxSampleMip\s*=\s*(-?\d+)\s*$",
            text,
            re.MULTILINE,
        )
        values = [int(value) for value in matches]
        require(f"{setting_name}_single_override", len(values) <= 1, True)
        explicit_mip_values.extend(values)
        setting_matrix[setting_name] = {
            "source": relative(path),
            "jsonSha256": expected["jsonSha256"],
            "payloadSha256": expected["payloadSha256"],
            "reflectionProbeMaxSampleMip": values[0] if values else None,
            "behavior": "explicit override" if values else "uses code/default inheritance",
        }
    require("reflection_probe_explicit_override_count", len(explicit_mip_values), 4)
    require("reflection_probe_explicit_override_values", set(explicit_mip_values), {7})

    volume_profiles: dict[str, dict[str, object]] = {}
    forbidden_components = {"GTAmbientOcclusion", "ScreenSpaceReflectionVolume"}
    for profile_name, expected in VOLUME_PROFILES.items():
        path = expected["path"]
        require(f"{profile_name}_sha256", sha256(path), expected["sha256"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual_name = payload["$animestudio"]["name"]
        require(f"{profile_name}_name", actual_name, profile_name)
        component_names = [
            row["targetName"]
            for row in payload["$animestudio"]["pptrReferences"]
            if row.get("path", "").startswith("$.components[")
        ]
        require(
            f"{profile_name}_components",
            component_names,
            expected["components"],
        )
        require(
            f"{profile_name}_no_ao_ssr_override",
            forbidden_components.isdisjoint(component_names),
            True,
        )
        volume_profiles[profile_name] = {
            "source": relative(path),
            "sha256": expected["sha256"],
            "components": component_names,
            "aoSsrOverrideAbsent": True,
        }

    source = SOURCES["selectedFragment"].read_text(encoding="utf-8")
    dxbc = SOURCES["selectedDxbcFragment"].read_text(encoding="utf-8")
    layout = parse_layout(source)
    uses = parse_body_uses(source, layout)
    used_fields = {row["field"] for row in uses}
    require("used_fields", used_fields, EXPECTED_USED_FIELDS)
    require(
        "spirv_b35_vector_count",
        max(v["row"] + v["arrayCount"] for v in layout.values()),
        200,
    )
    require("d3d11_b1_prefix", "float4 _57_m0[157]" in dxbc, True)
    require("d3d11_b1_alias_prefix", "float4 _62_m0[157]" in dxbc, True)

    mip = json.loads(SOURCES["globalMipBias"].read_text(encoding="utf-8"))
    require("selected_mip_bias", mip["labPublishedPair"]["_GlobalMipBias"], 0.0)
    iv = json.loads(SOURCES["inactiveIrradianceV2"].read_text(encoding="utf-8"))
    inactive = iv["activeClipmaps"]["installedMissingMapState"]["parameters"]
    for index in range(3):
        require(f"inactive_iv_param{index}", inactive[f"param{index}"], [0.0] * 4)

    compact_uses: dict[str, dict[str, object]] = {}
    for row in uses:
        entry = compact_uses.setdefault(
            row["field"],
            {"row": row["row"], "lanes": set(), "lines": []},
        )
        entry["lanes"].update(row["lanes"])
        entry["lines"].append(row["line"])
    lane_order = "xyzw"
    rendered_uses = [
        {
            "field": field,
            "row": value["row"],
            "lanes": "".join(lane for lane in lane_order if lane in value["lanes"]),
            "lines": sorted(set(value["lines"])),
        }
        for field, value in sorted(compact_uses.items(), key=lambda item: (item[1]["row"], item[0]))
    ]

    return {
        "schema": "endfield.deferred-shader-variables-global-audit.v1",
        "status": "selected_consumer_exactly_scoped_but_not_fully_source_closed",
        "binding": {
            "canonicalName": "ShaderVariablesGlobal",
            "spirvSet": 3,
            "spirvBinding": 35,
            "spirvBytes": 3200,
            "spirvVectors": 200,
            "d3d11Register": "b1",
            "d3d11BridgeName": "EndfieldCB1",
            "d3d11SelectedBytes": 2512,
            "d3d11SelectedVectors": 157,
        },
        "actualSelectedBodyUses": rendered_uses,
        "nativeResetProducers": {
            name: {
                key: value
                for key, value in method.items()
                if key not in {"fileOffset"}
            }
            | {"fileOffset": hex(method["fileOffset"])}
            for name, method in NATIVE_METHODS.items()
        },
        "graphicsFeatureProducer": {
            name: {
                key: value
                for key, value in method.items()
                if key not in {"fileOffset"}
            }
            | {"fileOffset": hex(method["fileOffset"])}
            for name, method in NATIVE_GRAPHICS_FEATURE_METHODS.items()
        },
        "reflectionProbeMaxSampleMip": {
            "selectedValue": 7,
            "selectedRow": "c31.x",
            "codeDefault": 7,
            "settingManifest": {
                "source": relative(manifest_path),
                "jsonSha256": SETTING_MANIFEST["jsonSha256"],
                "payloadSha256": SETTING_MANIFEST["payloadSha256"],
            },
            "installedSettingMatrix": setting_matrix,
            "closure": (
                "All four shipped platform/tier overrides are 7; the other "
                "three listed setting files do not override the constructor "
                "default 7. Device/profile selection therefore cannot change "
                "the selected installed value."
            ),
        },
        "graphicsFeatureSelectedState": {
            "c30": [0.0, 0.0, 1.0, 1.0],
            "aoEnable": False,
            "ssrEnable": False,
            "volumeProfiles": volume_profiles,
            "closure": (
                "The exact component constructors default both enable "
                "parameters to false, both IsActive methods return that "
                "parameter, and none of the installed global/lookdev or two "
                "selected CharInfo profiles contains an AO/SSR component "
                "override. The SSR capability gates are therefore not reached."
            ),
        },
        "closedSelectedRows": {
            "c4.w": "perspective ExternalCamera => unity_OrthoParams.w=0",
            "c26.x": "selected HGAdditionalCameraData materialMipBias=0",
            "c28": "same-frame recovered light/reflection binning offsets",
            "c29": "serialized CharInfo environment exposure/reflection scale",
            "c30": "exact selected AO/SSR booleans are 0/0 and writer constants are 1/1",
            "c71..c76": "exact installed atmosphere-fog reset producer",
            "c77..c82": "exact installed height-fog reset producer",
            "c83..c87": "exact installed disabled-volumetric reset producer; c83.z gates the branch off",
            "c132..c134": "installed no-reload V2 irradiance result parameters are all zero",
            "c31.x": "exact installed reflectionProbeMaxSampleMip code default and every shipped override are 7",
            "c156.x": "serialized CharInfo wetness is disabled/zero",
        },
        "branchDeadSelectedReads": {
            "c26.w": "FrameCount is read only inside the c83.z > 0 volumetric branch",
            "c84..c87": "volumetric parameters are zero and downstream reads are gated by c83.z=0",
        },
        "remainingSelectedRows": {
            "c0.zw": "same-target inverse screen dimensions; producer formula is known but target-frame dimensions remain dynamic",
            "c3.y": "depth/z-bin projection term; exact HGCamera producer expression/value remains open",
            "c135..c137": "IVDefaultSHAr/Ag/Ab remain live and exact selected-scene values are not yet recovered",
        },
        "decision": (
            "Do not publish EndfieldCB1 or enable pass 0 yet. The reset producers "
            "close fog rows exactly, c30 is exact (0,0,1,1), and c31.x is exact 7, "
            "but c3.y and c135..c137 "
            "still affect the selected resolver outside dead branches."
        ),
        "sources": {
            "gameAssembly": {
                "path": str(GAME_ASSEMBLY),
                "sha256": game_hash,
            }
        }
        | {
            name: {"path": relative(path), "sha256": hashes[name]}
            for name, path in SOURCES.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_audit(), indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file():
            raise AssertionError(f"missing generated audit: {OUTPUT}")
        require("generated_audit", OUTPUT.read_text(encoding="utf-8"), rendered)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "Deferred ShaderVariablesGlobal audit passed: 33 selected fields; "
        "fog resets plus c30/c31 exact; b1 remains blocked by c3/c135..c137."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
