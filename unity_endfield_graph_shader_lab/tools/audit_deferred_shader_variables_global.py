#!/usr/bin/env python3
"""Scope the selected deferred resolver's actual ShaderVariablesGlobal reads."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ASSEMBLY = Path(r"D:/Program Files/Endfield Game/GameAssembly.dll")
GLOBAL_METADATA = Path(
    r"D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/"
    r"global-metadata.dat"
)
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
    "selectedCameraProfiles": (
        LAB_ROOT
        / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
        "CharInfoPlayableProfiles/source_profiles.json"
    ),
    "selectedCameraLens": (
        REPO_ROOT
        / "scratch/charinfo_playable_profiles/dependencies_json/MonoBehaviour/"
        "MonoBehaviour#1116_p2FDBEDA931885FC8.json"
    ),
    "selectedEnvironmentVolume": (
        LAB_ROOT
        / "scratch/character_recovery/charinfo_volume_state/prefab_export/"
        "MonoBehaviour/MonoBehaviour#263_pD07FBA9DF34A6703.json"
    ),
    "selectedEnvironmentPhase": (
        REPO_ROOT
        / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/"
        "MonoBehaviour/CharInfo_Env_p10AB447A9F33D0F3.json"
    ),
}
EXPECTED_HASHES = {
    "gameAssembly": (
        "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
    ),
    "globalMetadata": (
        "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
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
    "selectedCameraProfiles": (
        "09867b8a1263ffaec1457e2390e51d1333b01861900f9a9d87f2db5d6bfe8566"
    ),
    "selectedCameraLens": (
        "f7c053539d3abbd40aff2dd51ea450a869ee78409220163267ef9445362c26fb"
    ),
    "selectedEnvironmentVolume": (
        "0c10d9772a6256187c0d4682b5826d6a3c298d8b7fa2949f095da44dad89a627"
    ),
    "selectedEnvironmentPhase": (
        "33bb9d19d4a7c1e0dfb5e82117821c908108059f76b7103c2c0ed5e8ba7f873c"
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

# UnityEngine.Camera getter wrappers and HGCamera.UpdateFrustum prove the two
# indirect scalar inputs are nearClipPlane and farClipPlane. UpdateFrustum
# constructs projectionParams as
# (-1, nearClipPlane, farClipPlane, 1/farClipPlane) at object offset 0x798.
# The four-argument UpdateShaderVariablesGlobalCB overload then copies that
# exact vector to ShaderVariablesGlobal c3. Complete body hashes plus the
# bounded instruction bytes make both the field route and lane order fail
# closed on an installed-binary change.
NATIVE_PROJECTION_METHODS = {
    "updateFrustum": {
        "method": "HG.Rendering.Runtime.HGCamera.UpdateFrustum",
        "methodIndex": 286759,
        "token": "0x06000ea3",
        "va": "0x183252130",
        "fileOffset": 0x3250730,
        "size": 0x6B0,
        "sha256": "3b93667a1deb3b76e8ddff63b5ae25fe68c6790218df395bbc1558aabedb0f0c",
        "byteChecks": [
            {
                "offset": 0x133,
                "hex": (
                    "488b0546ce110c4885c00f84d21ddb01488bcbffd0488b5f60"
                    "440f28d04885db0f840f050000488b0530ce110c4885c00f84"
                    "e01ddb01488bcbffd0440f28c8"
                ),
                "meaning": (
                    "call Camera nearClipPlane slot 0x18f36f0b0 into xmm10, "
                    "then farClipPlane slot 0x18f36f0c0 into xmm9"
                ),
            },
            {
                "offset": 0x29A,
                "hex": (
                    "b8ffffffff0f57c0f30f2ac0f3410f5ee90fc6c0e1f3410f10c2"
                    "0fc6c0c6f3410f10c10fc6c027f30f10c50fc6c0390f118798070000"
                ),
                "meaning": (
                    "assemble (-1, nearClipPlane, farClipPlane, "
                    "1/farClipPlane) and store HGCamera.projectionParams@0x798"
                ),
            }
        ],
    },
    "cameraNearClipGetter": {
        "method": "UnityEngine.Camera.get_nearClipPlane",
        "methodIndex": 402327,
        "token": "0x0600021e",
        "va": "0x18324d130",
        "fileOffset": 0x324B730,
        "size": 0x40,
        "sha256": "78e1415719b357fd11b027f7e1c1b074268a68de25e0c7de5f289f93c84eb1f9",
        "byteChecks": [
            {
                "offset": 0x6,
                "hex": "488b05731f120c",
                "meaning": "load native getter slot 0x18f36f0b0",
            }
        ],
    },
    "cameraFarClipGetter": {
        "method": "UnityEngine.Camera.get_farClipPlane",
        "methodIndex": 402329,
        "token": "0x06000220",
        "va": "0x18324dc80",
        "fileOffset": 0x324C280,
        "size": 0x40,
        "sha256": "6288d419cb7211384bfad831f5e2c27d1642c148f227d04401c024a2dcee79ce",
        "byteChecks": [
            {
                "offset": 0x6,
                "hex": "488b053314120c",
                "meaning": "load native getter slot 0x18f36f0c0",
            }
        ],
    },
    "updateGlobalWrapper": {
        "method": "HG.Rendering.Runtime.HGCamera.UpdateShaderVariablesGlobalCB",
        "overload": "(cb, basicTransformConstants, preTransform)",
        "methodIndex": 286747,
        "token": "0x06000e97",
        "va": "0x1832de2d0",
        "fileOffset": 0x32DC8D0,
        "size": 0xC0,
        "sha256": "8cbdcffa1dc69ea1bfd36508d32f21b8153d234ff4a86893da19b237a435d377",
        "byteChecks": [],
    },
    "updateGlobalBody": {
        "method": "HG.Rendering.Runtime.HGCamera.UpdateShaderVariablesGlobalCB",
        "overload": "(basicTransformConstants, cb, preTransform, frameCount)",
        "methodIndex": 286748,
        "token": "0x06000e98",
        "va": "0x1832e0020",
        "fileOffset": 0x32DE620,
        "size": 0xB40,
        "sha256": "31937f3310ede8f299b5387a85b35bb290973c0e049d1baa5de99356a0d17539",
        "byteChecks": [
            {
                "offset": 0x211,
                "hex": (
                    "0f1083780700000f1147200f108b980700000f114f30"
                    "0f1083880700000f114740"
                ),
                "meaning": (
                    "copy zBufferParams@0x778 to c2, projectionParams@0x798 "
                    "to c3, and unity_OrthoParams@0x788 to c4"
                ),
            }
        ],
    },
}

# The legacy/default irradiance path reads the interpolated HGSkyConfig,
# selects skyAmbientSH when useCustomIVDefaultSH is false, converts each color's
# coefficients to (L1x, L1y, L1z, L0), scales by skyDirectIntensity, and writes
# ShaderVariablesGlobal c135..c137. Metadata-derived field offsets are recorded
# with the exact installed method bodies so this route fails closed on drift.
NATIVE_DEFAULT_SH_METHODS = {
    "updateIrradianceVolume": {
        "method": (
            "HG.Rendering.Runtime.HGRenderPathBase."
            "UpdateShaderVariablesIrradianceVolume"
        ),
        "methodIndex": 287936,
        "token": "0x0600133c",
        "va": "0x189bdeb2c",
        "fileOffset": 0x9BDD12C,
        "size": 0x570,
        "sha256": "409b4efb4118dbdba601a9705db762f0a7968cf6b02c2f2ef0408ec1bf56e349",
        "fieldOffsets": {
            "interpolatedPhaseSkyConfig": "0x190",
            "skyDirectIntensity": "0x20 object / 0x10 embedded",
            "useCustomIVDefaultSH": "0x24 object / 0x14 embedded",
            "customIVDefaultSH": "0x28 object / 0x18 embedded",
            "skyAmbientSH": "0xec object / 0xdc embedded",
            "destinationIVDefaultSHAr": "this+0xdf0 / ShaderVariablesGlobal+0x880 / c135",
            "destinationIVDefaultSHAg": "this+0xe00 / ShaderVariablesGlobal+0x890 / c136",
            "destinationIVDefaultSHAb": "this+0xe10 / ShaderVariablesGlobal+0x8a0 / c137",
        },
        "byteChecks": [
            {
                "offset": 0x1C0,
                "hex": (
                    "33d2498bcee8ca7852f94885c07506e860954ff6cc41b802000000"
                    "488d8890010000488bc1488d9590010000"
                ),
                "meaning": (
                    "GetInterpolatedPhase(0), require a result, then address "
                    "the embedded HGSkyConfig at phase+0x190"
                ),
            },
            {
                "offset": 0x2ED,
                "hex": "488b454048c1e820488d553084c00f84a9000000",
                "meaning": (
                    "test embedded HGSkyConfig.useCustomIVDefaultSH and branch "
                    "to skyAmbientSH when false"
                ),
            },
            {
                "offset": 0x422,
                "hex": (
                    "0f10850c0100008b85740100000f108d1c0100000f10952c010000"
                    "0f109d3c0100000f10a54c0100000f10ad5c010000f20f10b56c"
                    "0100004533c00f2945c0488d55c00f294dd0488d4c24500f2955"
                    "e00f295df00f2965000f296d10f20f117520894528e819fed2f9"
                ),
                "meaning": (
                    "load skyAmbientSH from embedded offset 0xdc and call "
                    "HGEnvironmentUtils.GetCoefficientsL1"
                ),
            },
            {
                "offset": 0x48B,
                "hex": (
                    "f30f10ada0010000488d5424400f28d5488d4d800f10000f107010"
                    "0f107820660f7f442440e81f75bbf90f28d5660f7f742440488d"
                    "542440488d4d80f30f6f20f30f7fa6f00d0000e8fc74bbf90f28"
                    "d5660f7f7c2440488d542440488d4d80f30f6f20f30f7fa6000e"
                    "0000e8d974bbf9f30f6f20f30f7fa6100e0000"
                ),
                "meaning": (
                    "scale all three L1 vectors by skyDirectIntensity and "
                    "write c135, c136, and c137"
                ),
            },
        ],
    },
    "getCoefficientsL1": {
        "method": "HG.Rendering.Runtime.HGEnvironmentUtils.GetCoefficientsL1",
        "methodIndex": 284574,
        "token": "0x0600061a",
        "va": "0x18390edd0",
        "fileOffset": 0x390D3D0,
        "size": 0x290,
        "sha256": "acc6c2d1d74a42179b31d138d0aeaf5fcf0cb29c8f25fcf15aa311fc0d7f1db4",
        "formula": {
            "red": ["sh[0,3]", "sh[0,1]", "sh[0,2]", "sh[0,0]"],
            "green": ["sh[1,3]", "sh[1,1]", "sh[1,2]", "sh[1,0]"],
            "blue": ["sh[2,3]", "sh[2,1]", "sh[2,2]", "sh[2,0]"],
        },
        "byteChecks": [
            {
                "offset": 0x8E,
                "hex": (
                    "4533c933d241b803000000488bcbe8ef0100004533c933d241b801"
                    "000000488bcb440f28e8e8d80100004533c933d241b80200000048"
                    "8bcb440f28e0e8c10100004533c94533c033d2488bcb440f28d8"
                    "e8ad010000"
                ),
                "meaning": "read red SH coefficients in 3,1,2,0 order",
            },
            {
                "offset": 0x1C2,
                "hex": (
                    "450fc6ede1f3450f10ec450fc6edc6f3450f10eb440f28a424e0"
                    "000000488bc7440f289c24f0000000450fc6c0e1f3440f10c745"
                    "0fc6ed270f28bc2430010000f3450f10e9440f288c2410010000"
                    "450fc6c0c6f3440f10c6450fc6ed390f28b42440010000450fc6"
                    "c027440f112f440f28ac24d0000000f3440f10c0450fc6c03944"
                    "0f115710440f28942400010000440f114720"
                ),
                "meaning": (
                    "pack the three (coefficient 3,1,2,0) vectors and store "
                    "red/green/blue at result+0x0/+0x10/+0x20"
                ),
            },
        ],
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


def f32_bits(value: float) -> str:
    return f"0x{struct.unpack('<I', struct.pack('<f', value))[0]:08x}"


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
    metadata_hash = sha256(GLOBAL_METADATA)
    require("gameAssembly_sha256", game_hash, EXPECTED_HASHES["gameAssembly"])
    require(
        "globalMetadata_sha256",
        metadata_hash,
        EXPECTED_HASHES["globalMetadata"],
    )
    for name, expected in EXPECTED_HASHES.items():
        if name in {"gameAssembly", "globalMetadata"}:
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
    for name, method in NATIVE_PROJECTION_METHODS.items():
        start = method["fileOffset"]
        body = game_bytes[start : start + method["size"]]
        require(f"{name}_size", len(body), method["size"])
        require(
            f"{name}_sha256",
            hashlib.sha256(body).hexdigest(),
            method["sha256"],
        )
        for index, check in enumerate(method["byteChecks"]):
            expected_bytes = bytes.fromhex(check["hex"])
            offset = check["offset"]
            require(
                f"{name}_byte_check_{index}",
                body[offset : offset + len(expected_bytes)],
                expected_bytes,
            )
    for name, method in NATIVE_DEFAULT_SH_METHODS.items():
        start = method["fileOffset"]
        body = game_bytes[start : start + method["size"]]
        require(f"{name}_size", len(body), method["size"])
        require(
            f"{name}_sha256",
            hashlib.sha256(body).hexdigest(),
            method["sha256"],
        )
        for index, check in enumerate(method["byteChecks"]):
            expected_bytes = bytes.fromhex(check["hex"])
            offset = check["offset"]
            require(
                f"{name}_byte_check_{index}",
                body[offset : offset + len(expected_bytes)],
                expected_bytes,
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

    profile_source = json.loads(
        SOURCES["selectedCameraProfiles"].read_text(encoding="utf-8")
    )
    require(
        "camera_profile_source_policy",
        profile_source["policy"]["production_parameter_source"],
        "serialized_original_game_data_only",
    )
    require(
        "camera_profile_visual_fitting",
        profile_source["policy"]["visual_fitting_allowed"],
        False,
    )
    selected_profiles = [
        row
        for row in profile_source["characters"]
        if row["character_id"] == "chr_0030_zhuangfy"
    ]
    require("selected_camera_profile_count", len(selected_profiles), 1)
    selected_camera = selected_profiles[0]["camera"]
    require("selected_camera_track", selected_camera["track_root"], "track_chr_0030_zhuangfy")
    require(
        "selected_camera_vcam",
        selected_camera["vcam_path"],
        "track_chr_0030_zhuangfy/DollyCart/vcam_overview",
    )
    require("selected_camera_near_clip", selected_camera["near_clip"], 0.1)
    require("selected_camera_far_clip", selected_camera["far_clip"], 50.0)
    selected_lens_source = selected_camera["sources"]["lens"]
    require(
        "selected_camera_lens_path",
        selected_lens_source["path"],
        relative(SOURCES["selectedCameraLens"]),
    )
    require(
        "selected_camera_lens_sha256",
        selected_lens_source["sha256"],
        EXPECTED_HASHES["selectedCameraLens"],
    )
    require(
        "selected_camera_lens_raw_sha256",
        selected_lens_source["raw_data_sha256"],
        "fa79069273ac59573dc8f103566122dc27f5a46b95c1adfeedf324993b5cad55",
    )
    lens_payload = json.loads(
        SOURCES["selectedCameraLens"].read_text(encoding="utf-8")
    )
    require("selected_camera_lens_path_id", lens_payload["$animestudio"]["pathId"], 3448611250618523592)
    require("selected_camera_lens_raw_length", lens_payload["$animestudio"]["rawDataLength"], 164)
    require(
        "selected_camera_lens_payload_raw_sha256",
        lens_payload["$animestudio"]["rawDataSha256"],
        selected_lens_source["raw_data_sha256"],
    )
    require("selected_camera_lens_near_clip", lens_payload["m_Lens"]["NearClipPlane"], 0.1)
    require("selected_camera_lens_far_clip", lens_payload["m_Lens"]["FarClipPlane"], 50.0)

    environment_volume = json.loads(
        SOURCES["selectedEnvironmentVolume"].read_text(encoding="utf-8")
    )
    require("environment_volume_enabled", environment_volume["m_Enabled"], 1)
    require("environment_volume_type", environment_volume["_volumeType"], 0)
    require("environment_volume_blend_mode", environment_volume["_blendMode"], 0)
    require("environment_volume_priority", environment_volume["_priority"], 600)
    require(
        "environment_volume_manual_blend_factor",
        environment_volume["_manualBlendFactor"],
        1.0,
    )
    environment_path_id = environment_volume["_envPhase"]["m_PathID"]
    require("environment_volume_phase_path_id", environment_path_id, 1201129019072041203)
    require(
        "environment_volume_raw_sha256",
        environment_volume["$animestudio"]["rawDataSha256"],
        "be70748fe214daad8a45450dd095a5f984a29f427d3c30ebcff231ffa5440a76",
    )

    environment_phase = json.loads(
        SOURCES["selectedEnvironmentPhase"].read_text(encoding="utf-8")
    )
    require(
        "environment_phase_path_id",
        environment_phase["$animestudio"]["pathId"],
        environment_path_id,
    )
    require("environment_phase_name", environment_phase["$animestudio"]["name"], "CharInfo_Env")
    require(
        "environment_phase_raw_sha256",
        environment_phase["$animestudio"]["rawDataSha256"],
        "f9d1384c29f1e54599cd55e5f9c5c6d7eb9bd6f678d9fd104c7c329e6f1a66f9",
    )
    sky = environment_phase["skyConfig"]
    require("environment_sky_active", sky["m_active"], 1)
    require("environment_use_custom_default_sh", sky["useCustomIVDefaultSH"], 0)
    require("environment_sky_direct_intensity_bits", f32_bits(sky["skyDirectIntensity"]), "0x3f800000")
    custom_sh = [sky["customIVDefaultSH"][f"sh[{index:2d}]"] for index in range(27)]
    require("environment_custom_default_sh", custom_sh, [0.0] * 27)
    ambient_sh = [sky["skyAmbientSH"][f"sh[{index:2d}]"] for index in range(27)]
    ambient_bits = [f32_bits(value) for value in ambient_sh]
    expected_channel_bits = [
        "0x3f8c53be",
        "0x3ef1c917",
        "0x3c476813",
        "0xbbf76c60",
        "0x3ab9bcf1",
        "0xbb92cc26",
        "0xbd4352ee",
        "0x3b71ed4d",
        "0xbe0ee977",
    ]
    require(
        "environment_ambient_sh_bits",
        ambient_bits,
        expected_channel_bits * 3,
    )
    selected_default_sh: dict[str, dict[str, object]] = {}
    for channel_index, (channel, row) in enumerate(
        (("red", "c135"), ("green", "c136"), ("blue", "c137"))
    ):
        source_indices = [channel_index * 9 + index for index in (3, 1, 2, 0)]
        values = [ambient_sh[index] * sky["skyDirectIntensity"] for index in source_indices]
        selected_default_sh[channel] = {
            "row": row,
            "sourceCoefficientIndices": source_indices,
            "value": [struct.unpack("<f", struct.pack("<f", value))[0] for value in values],
            "float32Bits": [f32_bits(value) for value in values],
        }
    expected_default_sh_bits = [
        "0xbbf76c60",
        "0x3ef1c917",
        "0x3c476813",
        "0x3f8c53be",
    ]
    for channel, value in selected_default_sh.items():
        require(
            f"environment_{channel}_default_sh_bits",
            value["float32Bits"],
            expected_default_sh_bits,
        )

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
        "status": "selected_consumer_exactly_scoped_and_value_source_closed",
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
        "projectionParamsProducer": {
            "selectedRow": "c3.y",
            "hgCameraField": "projectionParams",
            "hgCameraFieldOffset": "0x798",
            "shaderVariablesGlobalDestination": "c3",
            "formula": ["-1", "nearClipPlane", "farClipPlane", "1/farClipPlane"],
            "nativeMethods": {
                name: {
                    key: value
                    for key, value in method.items()
                    if key not in {"fileOffset"}
                }
                | {"fileOffset": hex(method["fileOffset"])}
                for name, method in NATIVE_PROJECTION_METHODS.items()
            },
            "selectedCamera": {
                "characterId": "chr_0030_zhuangfy",
                "trackRoot": selected_camera["track_root"],
                "vcamPath": selected_camera["vcam_path"],
                "nearClipPlane": selected_camera["near_clip"],
                "farClipPlane": selected_camera["far_clip"],
                "projectionParams": [-1.0, 0.1, 50.0, 0.02],
                "lensPathId": selected_lens_source["path_id"],
                "lensRawDataLength": selected_lens_source["raw_data_length"],
                "lensRawDataSha256": selected_lens_source["raw_data_sha256"],
                "lensSourceFile": selected_lens_source["source_file"],
            },
            "closure": (
                "The installed native producer constructs c3 as "
                "(-1, near, far, 1/far), and the selected serialized original "
                "Overview lens supplies near=0.1 and far=50. Therefore the live "
                "selected c3.y value is exactly 0.1."
            ),
        },
        "defaultIrradianceSHProducer": {
            "selectedRows": ["c135", "c136", "c137"],
            "environmentVolume": {
                "source": relative(SOURCES["selectedEnvironmentVolume"]),
                "enabled": True,
                "volumeType": environment_volume["_volumeType"],
                "blendMode": environment_volume["_blendMode"],
                "priority": environment_volume["_priority"],
                "manualBlendFactor": environment_volume["_manualBlendFactor"],
                "environmentPhasePathId": environment_path_id,
                "rawDataSha256": environment_volume["$animestudio"]["rawDataSha256"],
            },
            "environmentPhase": {
                "source": relative(SOURCES["selectedEnvironmentPhase"]),
                "pathId": environment_path_id,
                "name": environment_phase["$animestudio"]["name"],
                "rawDataSha256": environment_phase["$animestudio"]["rawDataSha256"],
                "skyActive": bool(sky["m_active"]),
                "useCustomIVDefaultSH": bool(sky["useCustomIVDefaultSH"]),
                "selectedSH": "skyAmbientSH",
                "skyDirectIntensity": sky["skyDirectIntensity"],
                "skyDirectIntensityFloat32Bits": f32_bits(sky["skyDirectIntensity"]),
                "ambientSHFloat32Bits": ambient_bits,
            },
            "nativeMethods": {
                name: {
                    key: value
                    for key, value in method.items()
                    if key not in {"fileOffset"}
                }
                | {"fileOffset": hex(method["fileOffset"])}
                for name, method in NATIVE_DEFAULT_SH_METHODS.items()
            },
            "formula": (
                "for each RGB channel, "
                "float4(sh[channel,3], sh[channel,1], sh[channel,2], "
                "sh[channel,0]) * skyDirectIntensity"
            ),
            "selectedValues": selected_default_sh,
            "closure": (
                "The enabled weight-1 CharInfo Global Env Volume selects the "
                "serialized CharInfo_Env phase. Its custom-default selector is "
                "false, so the installed native producer chooses skyAmbientSH, "
                "reorders coefficients 3/1/2/0, multiplies by the exact 1.0 "
                "skyDirectIntensity, and writes c135/c136/c137."
            ),
        },
        "closedSelectedRows": {
            "c3.y": "selected serialized Overview nearClipPlane=0.1 through exact HGCamera projectionParams producer",
            "c4.w": "perspective ExternalCamera => unity_OrthoParams.w=0",
            "c26.x": "selected HGAdditionalCameraData materialMipBias=0",
            "c28": "same-frame recovered light/reflection binning offsets",
            "c29": "serialized CharInfo environment exposure/reflection scale",
            "c30": "exact selected AO/SSR booleans are 0/0 and writer constants are 1/1",
            "c71..c76": "exact installed atmosphere-fog reset producer",
            "c77..c82": "exact installed height-fog reset producer",
            "c83..c87": "exact installed disabled-volumetric reset producer; c83.z gates the branch off",
            "c132..c134": "installed no-reload V2 irradiance result parameters are all zero",
            "c135..c137": "selected CharInfo skyAmbientSH reordered 3/1/2/0 and scaled by exact skyDirectIntensity=1",
            "c31.x": "exact installed reflectionProbeMaxSampleMip code default and every shipped override are 7",
            "c156.x": "serialized CharInfo wetness is disabled/zero",
        },
        "branchDeadSelectedReads": {
            "c26.w": "FrameCount is read only inside the c83.z > 0 volumetric branch",
            "c84..c87": "volumetric parameters are zero and downstream reads are gated by c83.z=0",
        },
        "remainingSelectedRows": {
            "c0.zw": "same-target inverse screen dimensions; producer formula is known but target-frame dimensions remain dynamic",
        },
        "decision": (
            "The selected ShaderVariablesGlobal value contract is now source-closed; "
            "c0.zw remains a known same-target runtime formula rather than an unknown "
            "constant. EndfieldCB1 is still deliberately unpublished and pass 0 "
            "disabled until a default-off runtime publisher and GPU binding verifier "
            "are implemented."
        ),
        "sources": {
            "gameAssembly": {
                "path": str(GAME_ASSEMBLY),
                "sha256": game_hash,
            },
            "globalMetadata": {
                "path": str(GLOBAL_METADATA),
                "sha256": metadata_hash,
            },
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
        "fog resets, c3/c30/c31, and c135..c137 exact; selected values closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
