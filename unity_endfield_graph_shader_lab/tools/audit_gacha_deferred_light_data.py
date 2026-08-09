#!/usr/bin/env python3
"""Audit the native b31 punctual-row schema and selected Gacha room inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
UNITY_PLAYER = GAME_ROOT / "UnityPlayer.dll"
GLOBAL_METADATA = GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
GLOBAL_GAME_MANAGERS = GAME_ROOT / "Endfield_Data/globalgamemanagers"
SELECTED_FRAGMENT = (
    LAB_ROOT
    / "scratch/reverse_engineering/sphereoutside_deferred_variant/selected_fragment.hlsl"
)
GACHA_POPULATION = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_light_population_recovery.json"
)
ROOM_HIERARCHY = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_room_lights/room_light_hierarchy.json"
)
ROOM_LIGHT_ROOT = (
    REPO_ROOT / "scratch/animestudio/zhuangfy_gacha_room_lights/json/Light"
)
ROOM_RAW_DUMP_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_start_order/gacharoom_raw_dump"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_deferred_light_data_recovery.json"
)

VALIDATOR = "gacha_deferred_light_data"
PREPARE_CPU_DATA_VA = 0x189D0C7BC
PREPARE_CPU_DATA_FILE_OFFSET = 0x9D0ADBC
PREPARE_CPU_DATA_SIZE = 0x1838
GET_LIGHT_NPR_DATA_VA = 0x1832025A0
GET_LIGHT_NPR_DATA_FILE_OFFSET = 0x3200BA0
GET_LIGHT_NPR_DATA_SIZE = 0x100
GET_LIGHT_ADDITIONAL_DATA_VA = 0x1832040F0
GET_LIGHT_ADDITIONAL_DATA_FILE_OFFSET = 0x32026F0
GET_LIGHT_ADDITIONAL_DATA_SIZE = 0x440
GET_LIGHT_FALLOFF_VA = 0x189D03E58
GET_LIGHT_FALLOFF_FILE_OFFSET = 0x9D02458
GET_LIGHT_FALLOFF_SIZE = 0x187
GET_LIGHT_FALLOFF_DEFAULT_FILE_OFFSET = 0xB957600
PACK_TWO_HALF_VA = 0x189C0F0A4
PACK_TWO_HALF_FILE_OFFSET = 0x9C0D6A4
PACK_TWO_HALF_SIZE = 0x7C
F32_TO_F16_VA = 0x185F0CFFC
F32_TO_F16_FILE_OFFSET = 0x5F0B5FC
F32_TO_F16_BODY_SIZE = 0x5A
F32_TO_F16_MAGIC_FILE_OFFSET = 0xDC7F17C
F32_TO_F16_SCALE_FILE_OFFSET = 0xDC7EA3C
F32_TO_F16_MAGIC_BITS = 0x4D77FF00
F32_TO_F16_SCALE_BITS = 0x07800000
DEGREES_TO_RADIANS_FILE_OFFSET = 0xB9576A0
DEGREES_TO_RADIANS_BITS = 0x3C8EFA35
HG_ADDITIONAL_LIGHT_DATA_SCRIPT_PATH_ID = 4098216658219718577

PLAYER_SETTINGS_FILE_OFFSET = 0x1000
PLAYER_SETTINGS_SIZE = 728
PLAYER_SETTINGS_COLOR_SPACE_OFFSET = 240
GRAPHICS_SETTINGS_FILE_OFFSET = 0xD8B28
GRAPHICS_SETTINGS_SIZE = 826
GRAPHICS_SETTINGS_LINEAR_INTENSITY_OFFSET = 736
GRAPHICS_SETTINGS_COLOR_TEMPERATURE_OFFSET = 737

UNITY_ICALL_NAME_TABLE_OFFSET = 0x20D27B0
UNITY_ICALL_FUNCTION_TABLE_OFFSET = 0x20CAA00
UNITY_ICALL_COUNT = 3962
UNITY_ICALLS = {
    1752: (
        0x181CC2158,
        0x1CC0D58,
        "UnityEngine.Light::set_enableLightAnimation",
        0x1800D4B40,
    ),
    1940: (
        0x181CC4A70,
        0x1CC3670,
        "UnityEngine.HGSharedLightData::get_finalColor_Injected",
        0x18011FE60,
    ),
    1982: (
        0x181CC55C0,
        0x1CC41C0,
        "UnityEngine.HGSharedLightData::get_flickerScale_Injected",
        0x180123330,
    ),
}
UNITY_GET_FINAL_COLOR_STUB_VA = 0x18011FE60
UNITY_GET_FINAL_COLOR_STUB_FILE_OFFSET = 0x11F460
UNITY_GET_FINAL_COLOR_STUB_SIZE = 0x33
UNITY_GET_FLICKER_STUB_VA = 0x180123330
UNITY_GET_FLICKER_STUB_FILE_OFFSET = 0x122930
UNITY_GET_FLICKER_STUB_SIZE = 5
UNITY_SET_LIGHT_ANIMATION_STUB_VA = 0x1800D4B40
UNITY_SET_LIGHT_ANIMATION_STUB_FILE_OFFSET = 0xD4140
UNITY_SET_LIGHT_ANIMATION_STUB_SIZE = 0x106
UNITY_FLICKER_GETTER_VA = 0x18036D480
UNITY_FLICKER_GETTER_FILE_OFFSET = 0x36CA80
UNITY_FLICKER_GETTER_SIZE = 0x190
UNITY_SET_LIGHT_ANIMATION_VA = 0x1803569F0
UNITY_SET_LIGHT_ANIMATION_FILE_OFFSET = 0x355FF0
UNITY_SET_LIGHT_ANIMATION_SIZE = 0xC1
UNITY_FINAL_COLOR_UPDATE_VA = 0x1803844E0
UNITY_FINAL_COLOR_UPDATE_FILE_OFFSET = 0x383AE0
UNITY_FINAL_COLOR_UPDATE_SIZE = 0x169
UNITY_COLOR_LINEAR_VA = 0x18034C690
UNITY_COLOR_LINEAR_FILE_OFFSET = 0x34BC90
UNITY_COLOR_LINEAR_SIZE = 0x180

EXPECTED_HASHES = {
    "gameAssembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "unityPlayer": "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2",
    "globalMetadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "globalGameManagers": "191619377ff312b785aae10faec8a75e39caf1ba60016ad08eff040b8c54f20d",
    "selectedFragment": "44dc5090af87a8f65ffca870f9e02b8525c4cfe14f84cf8feaa3ea6c49e4b9db",
    "gachaPopulation": "02e15c70197bcd96f804007fe042fcb46577c0014d956d78a28f2d96162e189a",
    "roomHierarchy": "bf26b44919a7563bd6c7ee137346d7f8880bb1a32911a8972c586b2bb0c87db9",
    "prepareCpuDataBody": "c55bd6dc86c971123c433a5dd29b446b557f8713f73b132da25c257369e9bd0b",
    "getLightNprDataBody": "49eeca70b72791b2ad58f8b77cf3fbc3f27149766dcc0510a00b9d129e6698c8",
    "getLightAdditionalDataBody": "071061feb7f3c76044273efe703f9bdf78288703516b863c10c592b263f73e00",
    "packTwoHalfBody": "dad4b266316d3ba37f5c20fd92f2db90da363f7b65b3467bf313342c1a8814ce",
    "f32ToF16Body": "dc4fa0754a86aed4b2d58a5a978fe6028d83257aa5fc8e0a06e8fa6b9b5dae62",
    "getLightFalloffBody": "dbb121bbf91f191001755e9290988f4f287fb9fcc1c65cd09254452474a2509d",
    "playerSettingsObject": "bb2752bf4f4dd43d7885e01520c992289330ea8efdf7321ea926cb7cb149b3d6",
    "graphicsSettingsObject": "8bbfff1de820c06fb150aa4093391bff3ad080eba65f4230d83496ed84b94563",
    "unityFlickerGetterBody": "622b04cd8adaf7bc219e4d56c9dc574f89f324e55128c2ca2c96c624254d3f1b",
    "unitySetLightAnimationBody": "911725357c454b8224102d6b34d32f12d912f9cadbbfcc26aa64dda8b3bb83c6",
    "unityFinalColorUpdateBody": "39cbb35b17202949963e8cb4ed54a9d1e31067ae1c26c766c191c80e004b5e1d",
    "unityColorLinearBody": "83785743304ef92949c2b53f43ba6b1fd9e30655b389f61a1f56a334babd608f",
}

# Golden Color.linear results were executed against the pinned UnityPlayer body.
# Keeping their IEEE-754 payloads avoids substituting Python libm for Unity's powf.
EXPECTED_LINEAR_COLOR_BITS = {
    (0x3F800000, 0x3F4DCDCE, 0x3F008081, 0x3F800000): (
        0x3F800000,
        0x3F1C4971,
        0x3E5D0A8B,
        0x3F800000,
    ),
    (0x3F800000, 0x3F43870E, 0x3ECCCCCC, 0x3F800000): (
        0x3F800000,
        0x3F0B53AD,
        0x3E080EA2,
        0x3F800000,
    ),
    (0x3F800000, 0x3F43186D, 0x3E99999A, 0x3F800000): (
        0x3F800000,
        0x3F0AA371,
        0x3D95FE50,
        0x3F800000,
    ),
    (0x3F800000, 0x3F2FAFB0, 0x3E4CCCCC, 0x3F800000): (
        0x3F800000,
        0x3EDB7D54,
        0x3D0798DC,
        0x3F800000,
    ),
}

EXPECTED_RECORD0_RGB_BITS = {
    ((0x3F800000, 0x3F4DCDCE, 0x3F008081, 0x3F800000), 0x42C80000): (0x42C80000, 0x427432C1, 0x41ACB03D),
    ((0x3F800000, 0x3F43870E, 0x3ECCCCCC, 0x3F800000), 0x40800000): (0x40800000, 0x400B53AD, 0x3F080EA2),
    ((0x3F800000, 0x3F43870E, 0x3ECCCCCC, 0x3F800000), 0x42700000): (0x42700000, 0x42029E72, 0x40FF1B70),
    ((0x3F800000, 0x3F43870E, 0x3ECCCCCC, 0x3F800000), 0x42C80000): (0x42C80000, 0x4259B2BE, 0x415496DD),
    ((0x3F800000, 0x3F4DCDCE, 0x3F008081, 0x3F800000), 0x40800000): (0x40800000, 0x401C4971, 0x3F5D0A8B),
    ((0x3F800000, 0x3F43186D, 0x3E99999A, 0x3F800000), 0x42700000): (0x42700000, 0x4201F93A, 0x408C9E6B),
    ((0x3F800000, 0x3F2FAFB0, 0x3E4CCCCC, 0x3F800000), 0x41F00000): (0x41F00000, 0x414DC57F, 0x3F7E3E9C),
    ((0x3F800000, 0x3F4DCDCE, 0x3F008081, 0x3F800000), 0x430C0000): (0x430C0000, 0x42AAF054, 0x41F1C388),
}

EXPECTED_ROOM_ORDER = [
    "Spot Light (12)",
    "Spot Light (19)",
    "Linear Light (12)",
    "Linear Light (13)",
    "Linear Light (14)",
    "Spot Light (17)",
    "Linear Light (15)",
    "Spot Light (18)",
    "Spot Light (9)",
    "Spot Light (11)",
    "Spot Light (10)",
]

# Each tuple is (instruction offset, record index, expected add-rcx immediate).
SPOT_RECORD_WRITES = [
    (0x0DF7, 0, 6),
    (0x0E6D, 1, 7),
    (0x0ED6, 2, 8),
    (0x0F21, 3, 9),
    (0x0F5D, 4, 10),
    (0x0FDE, 5, 11),
    (0x1024, 6, 12),
]
POINT_RECORD_WRITES = [
    (0x136A, 0, 6),
    (0x13C5, 1, 7),
    (0x1441, 2, 8),
    (0x148C, 3, 9),
    (0x14BC, 4, 10),
    (0x153E, 5, 11),
    (0x158C, 6, 12),
]
COMMON_RECORD_WRITE = (0x15F8, 7, 13)

NATIVE_CALLS = {
    0x064C: (GET_LIGHT_FALLOFF_VA, "LightExtensions.GetLightFalloff"),
    0x066B: (0x183A1D9B0, "UnityEngine.Color.op_Implicit"),
    0x0683: (0x183796500, "UnityEngine.Color.op_Multiply color by falloff"),
    0x0693: (0x18B3BDEF0, "HGSharedLightData.get_flickerScale_Injected"),
    0x06AB: (0x183796500, "UnityEngine.Color.op_Multiply color by flickerScale"),
    0x06C6: (0x18328FB00, "Unity.Mathematics.float4.op_Implicit"),
    0x08DB: (0x1832040F0, "LightExtensions.GetLightAdditionalData"),
    0x0979: (0x18B3BDCA8, "HGSharedLightData.get_cullingBoxRelativePosition_Injected"),
    0x09C2: (0x18B3BDBC8, "HGSharedLightData.get_cullingBoxHalfExtents_Injected"),
    0x0A0C: (0x18B3BDC38, "HGSharedLightData.get_cullingBoxOrientation_Injected"),
    0x0A68: (0x18B3BDD4C, "HGSharedLightData.get_enableOBBCullingBox_Injected"),
    0x0A77: (0x18B3BDD88, "HGSharedLightData.get_enableOverrideShadowLight_Injected"),
    0x0A91: (0x18B3BDD4C, "HGSharedLightData.get_enableOBBCullingBox_Injected"),
    0x0B17: (0x182FA5910, "UnityEngine.Quaternion.Euler"),
    0x0B91: (0x182FA4BB0, "UnityEngine.Matrix4x4.TRS"),
    0x0BCF: (0x182FA2B80, "UnityEngine.Matrix4x4.get_inverse"),
    0x0C2E: (PACK_TWO_HALF_VA, "HGUtils.PackTwoHalfValuesAsFloat row0.xy"),
    0x0C43: (PACK_TWO_HALF_VA, "HGUtils.PackTwoHalfValuesAsFloat row0.zw"),
    0x0C62: (PACK_TWO_HALF_VA, "HGUtils.PackTwoHalfValuesAsFloat row1.xy"),
    0x0C81: (PACK_TWO_HALF_VA, "HGUtils.PackTwoHalfValuesAsFloat row1.zw"),
    0x0CA0: (PACK_TWO_HALF_VA, "HGUtils.PackTwoHalfValuesAsFloat row2.xy"),
    0x0CBE: (PACK_TWO_HALF_VA, "HGUtils.PackTwoHalfValuesAsFloat row2.zw"),
    0x0CF8: (0x18B3BDF2C, "HGSharedLightData.get_innerSpotAngle_Injected"),
    0x0D1C: (0x18B3BE5FC, "HGSharedLightData.get_spotAngle_Injected"),
    0x0DD9: (0x18B3BE4D0, "HGSharedLightData.get_shadowOnly_Injected"),
    0x1046: (0x18B3BDB48, "HGSharedLightData.get_cullingBoxFalloffThreshold_Injected"),
    0x105A: (0x18B3BE584, "HGSharedLightData.get_softSourceRadius_Injected"),
    0x106E: (0x18B3BE5C0, "HGSharedLightData.get_specularIntensity_Injected"),
    0x13F4: (0x18B3BE030, "HGSharedLightData.get_length_Injected"),
    0x15AE: (0x18B3BDB48, "HGSharedLightData.get_cullingBoxFalloffThreshold_Injected"),
    0x15BF: (0x18B3BE584, "HGSharedLightData.get_softSourceRadius_Injected"),
    0x15D0: (0x18B3BE5C0, "HGSharedLightData.get_specularIntensity_Injected"),
}


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def float32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f32(value)))[0]


def float32_from_bits(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def f32_to_f16_bits(value: float) -> int:
    """Mirror installed Unity.Mathematics.math.f32tof16 through its first ret."""
    bits = float32_bits(value)
    magnitude = bits & 0x7FFFF000
    scaled = f32(
        float32_from_bits(magnitude)
        * float32_from_bits(F32_TO_F16_SCALE_BITS)
    )
    if scaled < float32_from_bits(F32_TO_F16_MAGIC_BITS):
        packed_magnitude = (float32_bits(scaled) + 0x1000) >> 13
    else:
        packed_magnitude = 0x7C00 if magnitude <= 0x7F800000 else 0x7E00
    return ((bits >> 16) & 0x8000) | packed_magnitude


def f16_bits_to_float(bits: int) -> float:
    return struct.unpack("<e", struct.pack("<H", bits))[0]


def pack_two_half_words(x: float, y: float) -> int:
    return f32_to_f16_bits(x) | (f32_to_f16_bits(y) << 16)


def is_f32_to_f16_one_ulp_sensitive(value: float) -> bool:
    if value == 0.0 or not math.isfinite(value):
        return False
    bits = float32_bits(value)
    packed = f32_to_f16_bits(value)
    return (
        f32_to_f16_bits(float32_from_bits(bits - 1)) != packed
        or f32_to_f16_bits(float32_from_bits(bits + 1)) != packed
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object, source: Path | str) -> None:
    if actual != expected:
        raise AssertionError(
            f"validator={VALIDATOR}; check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verified_hash(name: str, path: Path) -> str:
    actual = sha256(path)
    require(f"{name}_sha256", actual, EXPECTED_HASHES[name], path)
    return actual


def relative_call_target(body: bytes, base_va: int, offset: int) -> int:
    require(f"native_call_{offset:04x}_opcode", body[offset], 0xE8, GAME_ASSEMBLY)
    displacement = struct.unpack_from("<i", body, offset + 1)[0]
    return base_va + offset + 5 + displacement


def call_target(body: bytes, offset: int) -> int:
    return relative_call_target(body, PREPARE_CPU_DATA_VA, offset)


def relative_branch_target(
    body: bytes,
    base_va: int,
    offset: int,
    opcode: int,
    source: Path,
    check: str,
) -> int:
    require(f"{check}_opcode", body[offset], opcode, source)
    displacement = struct.unpack_from("<i", body, offset + 1)[0]
    return base_va + offset + 5 + displacement


def validate_global_lighting_settings(data: bytes) -> dict[str, Any]:
    player = data[
        PLAYER_SETTINGS_FILE_OFFSET : PLAYER_SETTINGS_FILE_OFFSET + PLAYER_SETTINGS_SIZE
    ]
    graphics = data[
        GRAPHICS_SETTINGS_FILE_OFFSET : GRAPHICS_SETTINGS_FILE_OFFSET
        + GRAPHICS_SETTINGS_SIZE
    ]
    player_hash = hashlib.sha256(player).hexdigest()
    graphics_hash = hashlib.sha256(graphics).hexdigest()
    require(
        "player_settings_object_sha256",
        player_hash,
        EXPECTED_HASHES["playerSettingsObject"],
        GLOBAL_GAME_MANAGERS,
    )
    require(
        "graphics_settings_object_sha256",
        graphics_hash,
        EXPECTED_HASHES["graphicsSettingsObject"],
        GLOBAL_GAME_MANAGERS,
    )
    active_color_space = struct.unpack_from(
        "<i", player, PLAYER_SETTINGS_COLOR_SPACE_OFFSET
    )[0]
    linear_intensity = bool(graphics[GRAPHICS_SETTINGS_LINEAR_INTENSITY_OFFSET])
    color_temperature = bool(graphics[GRAPHICS_SETTINGS_COLOR_TEMPERATURE_OFFSET])
    require("player_settings_active_color_space", active_color_space, 1, GLOBAL_GAME_MANAGERS)
    require("graphics_settings_linear_intensity", linear_intensity, True, GLOBAL_GAME_MANAGERS)
    require(
        "graphics_settings_color_temperature",
        color_temperature,
        True,
        GLOBAL_GAME_MANAGERS,
    )
    return {
        "sourcePath": GLOBAL_GAME_MANAGERS.relative_to(GAME_ROOT).as_posix(),
        "playerSettings": {
            "pathId": 1,
            "fileOffset": f"0x{PLAYER_SETTINGS_FILE_OFFSET:X}",
            "sizeBytes": PLAYER_SETTINGS_SIZE,
            "rawObjectSha256": player_hash,
            "activeColorSpace": "Linear",
            "activeColorSpaceValue": active_color_space,
        },
        "graphicsSettings": {
            "pathId": 7,
            "fileOffset": f"0x{GRAPHICS_SETTINGS_FILE_OFFSET:X}",
            "sizeBytes": GRAPHICS_SETTINGS_SIZE,
            "rawObjectSha256": graphics_hash,
            "lightsUseLinearIntensity": linear_intensity,
            "lightsUseColorTemperature": color_temperature,
        },
    }


def validate_light_falloff_native(body: bytes, default_bytes: bytes) -> dict[str, Any]:
    require("get_light_falloff_size", len(body), GET_LIGHT_FALLOFF_SIZE, GAME_ASSEMBLY)
    body_hash = hashlib.sha256(body).hexdigest()
    require(
        "get_light_falloff_body_sha256",
        body_hash,
        EXPECTED_HASHES["getLightFalloffBody"],
        GAME_ASSEMBLY,
    )
    require(
        "get_light_falloff_use_culling_call",
        relative_call_target(body, GET_LIGHT_FALLOFF_VA, 0xD3),
        0x18B3BE674,
        GAME_ASSEMBLY,
    )
    require(
        "get_light_falloff_use_far_show_call",
        relative_call_target(body, GET_LIGHT_FALLOFF_VA, 0x102),
        0x18B3BE6B0,
        GAME_ASSEMBLY,
    )
    require(
        "get_light_falloff_default_load",
        body[0x12B:0x133],
        bytes.fromhex("f30f10057552c501"),
        GAME_ASSEMBLY,
    )
    require(
        "get_light_falloff_default_bits",
        struct.unpack("<I", default_bytes)[0],
        0x3F800000,
        GAME_ASSEMBLY,
    )
    return {
        "method": "HG.Rendering.Runtime.LightExtensions.GetLightFalloff",
        "methodIndex": 285215,
        "virtualAddress": f"0x{GET_LIGHT_FALLOFF_VA:X}",
        "fileOffset": f"0x{GET_LIGHT_FALLOFF_FILE_OFFSET:X}",
        "sizeBytes": GET_LIGHT_FALLOFF_SIZE,
        "bodySha256": body_hash,
        "selectedRowsResult": 1.0,
        "reason": "useCullingDistance=false and useFarDistanceShow=false",
    }


def validate_unity_light_color_native(data: bytes) -> dict[str, Any]:
    icalls = []
    for index, (name_pointer, name_offset, name, function_pointer) in UNITY_ICALLS.items():
        actual_name_pointer = struct.unpack_from(
            "<Q", data, UNITY_ICALL_NAME_TABLE_OFFSET + index * 8
        )[0]
        actual_function_pointer = struct.unpack_from(
            "<Q", data, UNITY_ICALL_FUNCTION_TABLE_OFFSET + index * 8
        )[0]
        require(f"unity_icall_{index}_name_pointer", actual_name_pointer, name_pointer, UNITY_PLAYER)
        require(
            f"unity_icall_{index}_function_pointer",
            actual_function_pointer,
            function_pointer,
            UNITY_PLAYER,
        )
        actual_name = data[name_offset : name_offset + len(name)].decode("ascii")
        require(f"unity_icall_{index}_name", actual_name, name, UNITY_PLAYER)
        require(
            f"unity_icall_{index}_name_terminator",
            data[name_offset + len(name)],
            0,
            UNITY_PLAYER,
        )
        icalls.append(
            {
                "index": index,
                "name": name,
                "namePointer": f"0x{name_pointer:X}",
                "functionPointer": f"0x{function_pointer:X}",
            }
        )

    final_stub = data[
        UNITY_GET_FINAL_COLOR_STUB_FILE_OFFSET : UNITY_GET_FINAL_COLOR_STUB_FILE_OFFSET
        + UNITY_GET_FINAL_COLOR_STUB_SIZE
    ]
    flicker_stub = data[
        UNITY_GET_FLICKER_STUB_FILE_OFFSET : UNITY_GET_FLICKER_STUB_FILE_OFFSET
        + UNITY_GET_FLICKER_STUB_SIZE
    ]
    animation_stub = data[
        UNITY_SET_LIGHT_ANIMATION_STUB_FILE_OFFSET : UNITY_SET_LIGHT_ANIMATION_STUB_FILE_OFFSET
        + UNITY_SET_LIGHT_ANIMATION_STUB_SIZE
    ]
    require(
        "unity_get_final_color_shared_offset",
        final_stub[0x26:0x2D],
        bytes.fromhex("0f1040440f1107"),
        UNITY_PLAYER,
    )
    require(
        "unity_get_flicker_native_target",
        relative_branch_target(
            flicker_stub,
            UNITY_GET_FLICKER_STUB_VA,
            0,
            0xE9,
            UNITY_PLAYER,
            "unity_get_flicker_stub_jump",
        ),
        UNITY_FLICKER_GETTER_VA,
        UNITY_PLAYER,
    )
    require(
        "unity_set_light_animation_native_target",
        relative_branch_target(
            animation_stub,
            UNITY_SET_LIGHT_ANIMATION_STUB_VA,
            0xEE,
            0xE8,
            UNITY_PLAYER,
            "unity_set_light_animation_stub_call",
        ),
        UNITY_SET_LIGHT_ANIMATION_VA,
        UNITY_PLAYER,
    )

    bodies = {
        "flicker": data[
            UNITY_FLICKER_GETTER_FILE_OFFSET : UNITY_FLICKER_GETTER_FILE_OFFSET
            + UNITY_FLICKER_GETTER_SIZE
        ],
        "animation": data[
            UNITY_SET_LIGHT_ANIMATION_FILE_OFFSET : UNITY_SET_LIGHT_ANIMATION_FILE_OFFSET
            + UNITY_SET_LIGHT_ANIMATION_SIZE
        ],
        "finalColor": data[
            UNITY_FINAL_COLOR_UPDATE_FILE_OFFSET : UNITY_FINAL_COLOR_UPDATE_FILE_OFFSET
            + UNITY_FINAL_COLOR_UPDATE_SIZE
        ],
        "colorLinear": data[
            UNITY_COLOR_LINEAR_FILE_OFFSET : UNITY_COLOR_LINEAR_FILE_OFFSET
            + UNITY_COLOR_LINEAR_SIZE
        ],
    }
    for key, expected_key in (
        ("flicker", "unityFlickerGetterBody"),
        ("animation", "unitySetLightAnimationBody"),
        ("finalColor", "unityFinalColorUpdateBody"),
        ("colorLinear", "unityColorLinearBody"),
    ):
        require(
            f"unity_{key}_body_sha256",
            hashlib.sha256(bodies[key]).hexdigest(),
            EXPECTED_HASHES[expected_key],
            UNITY_PLAYER,
        )

    require(
        "unity_flicker_runtime_value_or_one",
        bodies["flicker"][0x156:0x17F],
        bytes.fromhex(
            "741f807939007419f30f1081f0000000488b9c24e80000004881c4d00000005fc3"
            "f30f1005e54c9801"
        ),
        UNITY_PLAYER,
    )
    require(
        "unity_flicker_default_one_bits",
        struct.unpack_from("<I", data, 0x1CF0EE4)[0],
        0x3F800000,
        UNITY_PLAYER,
    )
    require(
        "unity_animation_store_enable_flag",
        bodies["animation"][0x1A:0x25],
        bytes.fromhex("488b43504088b828030000"),
        UNITY_PLAYER,
    )
    require(
        "unity_animation_disable_remove_calls",
        (
            relative_branch_target(
                bodies["animation"], UNITY_SET_LIGHT_ANIMATION_VA, 0xA3, 0xE8,
                UNITY_PLAYER, "unity_animation_remove_component"
            ),
            relative_branch_target(
                bodies["animation"], UNITY_SET_LIGHT_ANIMATION_VA, 0xAB, 0xE8,
                UNITY_PLAYER, "unity_animation_remove_followup"
            ),
        ),
        (0x18033C350, 0x180350E60),
        UNITY_PLAYER,
    )
    require(
        "unity_final_color_graphics_settings_call",
        relative_branch_target(
            bodies["finalColor"], UNITY_FINAL_COLOR_UPDATE_VA, 0x13, 0xE8,
            UNITY_PLAYER, "unity_final_color_graphics_settings"
        ),
        0x18039E490,
        UNITY_PLAYER,
    )
    require(
        "unity_final_color_linear_intensity_flag",
        bodies["finalColor"][0x18:0x1F],
        bytes.fromhex("80b85401000000"),
        UNITY_PLAYER,
    )
    require(
        "unity_final_color_temperature_flag",
        bodies["finalColor"][0x4D:0x54],
        bytes.fromhex("80bbc000000000"),
        UNITY_PLAYER,
    )
    require(
        "unity_final_color_color_linear_call",
        relative_branch_target(
            bodies["finalColor"], UNITY_FINAL_COLOR_UPDATE_VA, 0x88, 0xE8,
            UNITY_PLAYER, "unity_final_color_color_linear"
        ),
        UNITY_COLOR_LINEAR_VA,
        UNITY_PLAYER,
    )
    require(
        "unity_final_color_store",
        bodies["finalColor"][0xEB:0xF9],
        bytes.fromhex("488d93b80100000f118300020000"),
        UNITY_PLAYER,
    )
    return {
        "internalCallTable": {
            "entryCount": UNITY_ICALL_COUNT,
            "nameTableFileOffset": f"0x{UNITY_ICALL_NAME_TABLE_OFFSET:X}",
            "functionTableFileOffset": f"0x{UNITY_ICALL_FUNCTION_TABLE_OFFSET:X}",
            "resolvedEntries": icalls,
        },
        "finalColor": {
            "updateVirtualAddress": f"0x{UNITY_FINAL_COLOR_UPDATE_VA:X}",
            "updateBodySha256": hashlib.sha256(bodies["finalColor"]).hexdigest(),
            "colorLinearVirtualAddress": f"0x{UNITY_COLOR_LINEAR_VA:X}",
            "colorLinearBodySha256": hashlib.sha256(bodies["colorLinear"]).hexdigest(),
            "selectedRowsFormula": "UnityPlayer Color.linear(serialized color) * intensity",
            "selectedRowsUseColorTemperature": False,
        },
        "flickerScale": {
            "nativeVirtualAddress": f"0x{UNITY_FLICKER_GETTER_VA:X}",
            "nativeBodySha256": hashlib.sha256(bodies["flicker"]).hexdigest(),
            "disabledAnimationResult": 1.0,
        },
        "lightAnimation": {
            "nativeVirtualAddress": f"0x{UNITY_SET_LIGHT_ANIMATION_VA:X}",
            "nativeBodySha256": hashlib.sha256(bodies["animation"]).hexdigest(),
            "disabledPath": "stores false and removes an existing runtime animation component",
        },
    }


def validate_record_writes(body: bytes) -> dict[str, Any]:
    store_opcode = bytes.fromhex("f30f7f04c8")
    branches = {"spot": SPOT_RECORD_WRITES, "point_or_linear": POINT_RECORD_WRITES}
    result: dict[str, Any] = {}
    for branch, rows in branches.items():
        validated = []
        for add_offset, record, immediate in rows:
            require(
                f"{branch}_record{record}_address",
                body[add_offset : add_offset + 4],
                bytes((0x48, 0x83, 0xC1, immediate)),
                GAME_ASSEMBLY,
            )
            store_matches = [
                index
                for index in range(add_offset + 4, min(add_offset + 48, len(body) - 4))
                if body[index : index + 5] == store_opcode
            ]
            require(
                f"{branch}_record{record}_single_store",
                len(store_matches),
                1,
                GAME_ASSEMBLY,
            )
            validated.append(
                {
                    "record": record,
                    "absoluteVectorOffset": immediate,
                    "addressInstructionOffset": f"0x{add_offset:04X}",
                    "storeInstructionOffset": f"0x{store_matches[0]:04X}",
                }
            )
        result[branch] = validated

    add_offset, record, immediate = COMMON_RECORD_WRITE
    require(
        "common_record7_address",
        body[add_offset : add_offset + 4],
        bytes((0x48, 0x83, 0xC1, immediate)),
        GAME_ASSEMBLY,
    )
    require(
        "common_record7_store",
        body[0x15FF : 0x1604],
        store_opcode,
        GAME_ASSEMBLY,
    )
    result["common"] = [
        {
            "record": record,
            "absoluteVectorOffset": immediate,
            "addressInstructionOffset": f"0x{add_offset:04X}",
            "storeInstructionOffset": "0x15FF",
        }
    ]
    return result


def validate_native_body(body: bytes) -> dict[str, Any]:
    require("prepare_cpu_data_size", len(body), PREPARE_CPU_DATA_SIZE, GAME_ASSEMBLY)
    body_hash = hashlib.sha256(body).hexdigest()
    require(
        "prepare_cpu_data_body_sha256",
        body_hash,
        EXPECTED_HASHES["prepareCpuDataBody"],
        GAME_ASSEMBLY,
    )
    calls = []
    for offset, (target, name) in NATIVE_CALLS.items():
        require(f"native_call_{offset:04x}_target", call_target(body, offset), target, GAME_ASSEMBLY)
        calls.append({"offset": f"0x{offset:04X}", "target": f"0x{target:X}", "method": name})
    return {
        "method": "HG.Rendering.Runtime.LightCulling.PrepareCPUData",
        "methodIndex": 285282,
        "virtualAddress": f"0x{PREPARE_CPU_DATA_VA:X}",
        "fileOffset": f"0x{PREPARE_CPU_DATA_FILE_OFFSET:X}",
        "sizeBytes": PREPARE_CPU_DATA_SIZE,
        "bodySha256": body_hash,
        "recordWrites": validate_record_writes(body),
        "resolvedCalls": calls,
    }


def validate_additional_data_native(
    npr_body: bytes, additional_body: bytes
) -> dict[str, Any]:
    require(
        "get_light_npr_data_size",
        len(npr_body),
        GET_LIGHT_NPR_DATA_SIZE,
        GAME_ASSEMBLY,
    )
    npr_hash = hashlib.sha256(npr_body).hexdigest()
    require(
        "get_light_npr_data_body_sha256",
        npr_hash,
        EXPECTED_HASHES["getLightNprDataBody"],
        GAME_ASSEMBLY,
    )
    # Selected room rows all use NPR type 0. This branch reads the type at
    # +0x3c, the bool auto-limit carrier at +0x48, and contrast at +0x44,
    # then materializes (contrast, bool-as-float, 0, 0) at +0x2c.
    npr_checks = {
        "type_zero_dispatch": (0x44, "8b4b3c85c97537"),
        "type_zero_auto_limit": (0x4B, "384b480f849a000000"),
        "type_zero_contrast": (0x5C, "8b434489432c"),
        "type_zero_true_store": (0x64, "f30f11433048894334"),
        "type_zero_false_scalar": (0xEE, "0f57c0e966ffffff"),
    }
    for check, (offset, expected_hex) in npr_checks.items():
        expected = bytes.fromhex(expected_hex)
        require(
            f"get_light_npr_data_{check}",
            npr_body[offset : offset + len(expected)],
            expected,
            GAME_ASSEMBLY,
        )

    require(
        "get_light_additional_data_size",
        len(additional_body),
        GET_LIGHT_ADDITIONAL_DATA_SIZE,
        GAME_ASSEMBLY,
    )
    additional_hash = hashlib.sha256(additional_body).hexdigest()
    require(
        "get_light_additional_data_body_sha256",
        additional_hash,
        EXPECTED_HASHES["getLightAdditionalDataBody"],
        GAME_ASSEMBLY,
    )
    require(
        "get_light_additional_data_npr_call",
        relative_call_target(additional_body, GET_LIGHT_ADDITIONAL_DATA_VA, 0x286),
        GET_LIGHT_NPR_DATA_VA,
        GAME_ASSEMBLY,
    )
    # The successful HGAdditionalLightData path copies the returned NPR vector,
    # then packs type, CharacterOnly, volumetric intensity, and falloff into
    # the second 16-byte half of UnityEngine.HGLightAdditionalData.
    pack_checks = {
        "falloff_load": (0x28B, "f30f108384000000"),
        "volumetric_load": (0x293, "f30f108b80000000"),
        "npr_vector_load": (0x29B, "0f1018"),
        "npr_type_load": (0x29E, "8b433c"),
        "character_only_load": (0x2A4, "0fb6437d"),
        "result_stores": (0x2C3, "0f111f0f115710"),
    }
    for check, (offset, expected_hex) in pack_checks.items():
        expected = bytes.fromhex(expected_hex)
        require(
            f"get_light_additional_data_{check}",
            additional_body[offset : offset + len(expected)],
            expected,
            GAME_ASSEMBLY,
        )
    return {
        "getLightNprData": {
            "method": "HG.Rendering.Runtime.HGAdditionalLightData.GetLightNPRData",
            "methodIndex": 285199,
            "virtualAddress": f"0x{GET_LIGHT_NPR_DATA_VA:X}",
            "fileOffset": f"0x{GET_LIGHT_NPR_DATA_FILE_OFFSET:X}",
            "sizeBytes": GET_LIGHT_NPR_DATA_SIZE,
            "bodySha256": npr_hash,
            "selectedTypeZeroPacking": "(defaultContrast, defaultAutoLimit ? 1.0 : 0.0, 0, 0)",
        },
        "getLightAdditionalData": {
            "method": "HG.Rendering.Runtime.LightExtensions.GetLightAdditionalData",
            "methodIndex": 285217,
            "virtualAddress": f"0x{GET_LIGHT_ADDITIONAL_DATA_VA:X}",
            "fileOffset": f"0x{GET_LIGHT_ADDITIONAL_DATA_FILE_OFFSET:X}",
            "sizeBytes": GET_LIGHT_ADDITIONAL_DATA_SIZE,
            "bodySha256": additional_hash,
            "returnLayout": {
                "0x00": "float4 lightNPRData",
                "0x10": "int lightNPRType",
                "0x14": "bool LightCharacterOnly plus padding",
                "0x18": "float volumetricScatteringIntensity",
                "0x1C": "float falloffExponent",
            },
        },
    }


def validate_obb_pack_native(
    pack_body: bytes,
    f32_to_f16_body: bytes,
    magic_bytes: bytes,
    scale_bytes: bytes,
    degrees_to_radians_bytes: bytes,
) -> dict[str, Any]:
    require("pack_two_half_size", len(pack_body), PACK_TWO_HALF_SIZE, GAME_ASSEMBLY)
    pack_hash = hashlib.sha256(pack_body).hexdigest()
    require(
        "pack_two_half_body_sha256",
        pack_hash,
        EXPECTED_HASHES["packTwoHalfBody"],
        GAME_ASSEMBLY,
    )
    require(
        "pack_two_half_y_call",
        relative_call_target(pack_body, PACK_TWO_HALF_VA, 0x27),
        F32_TO_F16_VA,
        GAME_ASSEMBLY,
    )
    require(
        "pack_two_half_x_call",
        relative_call_target(pack_body, PACK_TWO_HALF_VA, 0x36),
        F32_TO_F16_VA,
        GAME_ASSEMBLY,
    )
    require(
        "pack_two_half_shift_or",
        pack_body[0x2C:0x3E],
        bytes.fromhex("448bd00f28c741c1e210e81ddf2ffc440bd0"),
        GAME_ASSEMBLY,
    )

    require(
        "f32_to_f16_body_size",
        len(f32_to_f16_body),
        F32_TO_F16_BODY_SIZE,
        GAME_ASSEMBLY,
    )
    helper_hash = hashlib.sha256(f32_to_f16_body).hexdigest()
    require(
        "f32_to_f16_body_sha256",
        helper_hash,
        EXPECTED_HASHES["f32ToF16Body"],
        GAME_ASSEMBLY,
    )
    require(
        "f32_to_f16_magic_bits",
        struct.unpack("<I", magic_bytes)[0],
        F32_TO_F16_MAGIC_BITS,
        GAME_ASSEMBLY,
    )
    require(
        "f32_to_f16_scale_bits",
        struct.unpack("<I", scale_bytes)[0],
        F32_TO_F16_SCALE_BITS,
        GAME_ASSEMBLY,
    )
    require(
        "quaternion_euler_degrees_to_radians_bits",
        struct.unpack("<I", degrees_to_radians_bytes)[0],
        DEGREES_TO_RADIANS_BITS,
        GAME_ASSEMBLY,
    )
    require(
        "f32_to_f16_round_and_sign",
        f32_to_f16_body[0x42:0x59],
        bytes.fromhex("660f7ec181c100100000c1e90dc1e81025008000000bc1"),
        GAME_ASSEMBLY,
    )
    return {
        "packTwoHalfValuesAsFloat": {
            "method": "HG.Rendering.Runtime.HGUtils.PackTwoHalfValuesAsFloat",
            "methodIndex": 288325,
            "virtualAddress": f"0x{PACK_TWO_HALF_VA:X}",
            "fileOffset": f"0x{PACK_TWO_HALF_FILE_OFFSET:X}",
            "sizeBytesToNextManagedEntry": PACK_TWO_HALF_SIZE,
            "bodySha256": pack_hash,
            "layout": "x occupies low 16 bits; y occupies high 16 bits",
        },
        "f32ToF16": {
            "method": "Unity.Mathematics.math.f32tof16",
            "methodIndex": 451057,
            "virtualAddress": f"0x{F32_TO_F16_VA:X}",
            "fileOffset": f"0x{F32_TO_F16_FILE_OFFSET:X}",
            "sizeBytesThroughFirstReturn": F32_TO_F16_BODY_SIZE,
            "bodySha256": helper_hash,
            "magicBits": f"0x{F32_TO_F16_MAGIC_BITS:08X}",
            "scaleBits": f"0x{F32_TO_F16_SCALE_BITS:08X}",
            "quaternionEulerDegreesToRadiansBits": f"0x{DEGREES_TO_RADIANS_BITS:08X}",
            "rounding": "installed IEEE binary16 conversion including signed zero, infinity, and canonical NaN",
        },
        "prepareCpuDataPackOrder": [
            "inverse row0 xy -> record5.x",
            "inverse row0 zw -> record5.y",
            "inverse row1 xy -> record5.z",
            "inverse row1 zw -> record6.x",
            "inverse row2 xy -> record6.y",
            "inverse row2 zw -> record6.z",
        ],
    }


def recovered_y_rotation_inverse_rows(row: dict[str, Any]) -> tuple[list[list[float]], list[list[float]]]:
    """Model the selected rows' Y-only inverse TRS with explicit float32 steps."""
    orientation = row["cullingBoxOrientationZxyDegrees"]
    require(
        f"room_{row['lightPathId']}_obb_orientation_x_zero",
        float(orientation["x"]) == 0.0,
        True,
        REPO_ROOT / row["sourcePath"],
    )
    require(
        f"room_{row['lightPathId']}_obb_orientation_z_zero",
        float(orientation["z"]) == 0.0,
        True,
        REPO_ROOT / row["sourcePath"],
    )
    position = [f32(float(row["cullingBoxRelativePosition"][key])) for key in "xyz"]
    scale = [f32(float(row["cullingBoxHalfExtents"][key])) for key in "xyz"]
    require(
        f"room_{row['lightPathId']}_obb_positive_half_extents",
        all(value > 0.0 for value in scale),
        True,
        REPO_ROOT / row["sourcePath"],
    )

    radians = f32(
        f32(float(orientation["y"]))
        * float32_from_bits(DEGREES_TO_RADIANS_BITS)
    )
    half_angle = f32(radians * f32(0.5))
    quaternion_y = f32(math.sin(half_angle))
    quaternion_w = f32(math.cos(half_angle))
    doubled_y = f32(quaternion_y + quaternion_y)
    cosine = f32(f32(1.0) - f32(quaternion_y * doubled_y))
    sine = f32(quaternion_w * doubled_y)
    rotation = [
        [cosine, 0.0, sine],
        [0.0, 1.0, 0.0],
        [f32(-sine), 0.0, cosine],
    ]

    # Invert the only non-trivial XZ block. The installed UnityPlayer internal
    # call remains opaque, so the resulting nonzero half payloads are reported
    # with a quantization boundary rather than mislabeled as captured runtime bits.
    matrix_xx = f32(rotation[0][0] * scale[0])
    matrix_xz = f32(rotation[0][2] * scale[2])
    matrix_zx = f32(rotation[2][0] * scale[0])
    matrix_zz = f32(rotation[2][2] * scale[2])
    determinant = f32(
        f32(matrix_xx * matrix_zz) - f32(matrix_xz * matrix_zx)
    )
    inverse = [
        [f32(matrix_zz / determinant), 0.0, f32(-matrix_xz / determinant), 0.0],
        [0.0, f32(1.0 / scale[1]), 0.0, 0.0],
        [f32(-matrix_zx / determinant), 0.0, f32(matrix_xx / determinant), 0.0],
    ]
    for output_row in inverse:
        translated = f32(
            f32(output_row[0] * position[0])
            + f32(output_row[1] * position[1])
            + f32(output_row[2] * position[2])
        )
        output_row[3] = f32(-translated)
    return rotation, inverse


def recover_obb_pack(row: dict[str, Any]) -> dict[str, Any]:
    rotation, inverse = recovered_y_rotation_inverse_rows(row)
    pairs = [
        (inverse[output_row][lane], inverse[output_row][lane + 1])
        for output_row in range(3)
        for lane in (0, 2)
    ]
    words = [pack_two_half_words(x, y) for x, y in pairs]
    masks = []
    zero_lanes = []
    one_ulp_sensitive_lanes = []
    for pair_index, (x, y) in enumerate(pairs):
        mask = 0xFFFFFFFF
        if x == 0.0:
            mask &= ~0x00008000
            zero_lanes.append(pair_index * 2)
        if y == 0.0:
            mask &= ~0x80000000
            zero_lanes.append(pair_index * 2 + 1)
        if is_f32_to_f16_one_ulp_sensitive(x):
            one_ulp_sensitive_lanes.append(pair_index * 2)
        if is_f32_to_f16_one_ulp_sensitive(y):
            one_ulp_sensitive_lanes.append(pair_index * 2 + 1)
        masks.append(mask)

    decoded = [
        [
            f16_bits_to_float(f32_to_f16_bits(inverse[output_row][lane]))
            for lane in range(4)
        ]
        for output_row in range(3)
    ]
    position = [f32(float(row["cullingBoxRelativePosition"][key])) for key in "xyz"]
    half_extents = [f32(float(row["cullingBoxHalfExtents"][key])) for key in "xyz"]
    maximum_corner_error = 0.0
    for sign_x in (-1.0, 1.0):
        for sign_y in (-1.0, 1.0):
            for sign_z in (-1.0, 1.0):
                authored_local = [
                    sign_x * half_extents[0],
                    sign_y * half_extents[1],
                    sign_z * half_extents[2],
                ]
                relative_corner = [
                    position[axis]
                    + sum(
                        rotation[axis][lane] * authored_local[lane]
                        for lane in range(3)
                    )
                    for axis in range(3)
                ]
                decoded_corner = [
                    sum(decoded[axis][lane] * relative_corner[lane] for lane in range(3))
                    + decoded[axis][3]
                    for axis in range(3)
                ]
                maximum_corner_error = max(
                    maximum_corner_error,
                    max(abs(abs(value) - 1.0) for value in decoded_corner),
                )
    require(
        f"room_{row['lightPathId']}_obb_half_round_trip_corner_error",
        maximum_corner_error < 0.003,
        True,
        REPO_ROOT / row["sourcePath"],
    )
    return {
        "producerFormula": "inverse(TRS(relativePosition, Quaternion.Euler(ZXY degrees), halfExtents))",
        "inverseRowsFloat32Model": inverse,
        "analyticCandidateWordHex": [f"0x{word:08X}" for word in words],
        "signedZeroNormalizedCandidateWordHex": [
            f"0x{word & mask:08X}" for word, mask in zip(words, masks)
        ],
        "consumerComparisonMaskHex": [f"0x{mask:08X}" for mask in masks],
        "unresolvedSignedZeroHalfLanes": zero_lanes,
        "oneFloat32UlpSensitiveHalfLanes": one_ulp_sensitive_lanes,
        "decodedHalfInverseRows": decoded,
        "maximumAuthoredCornerBoundaryError": maximum_corner_error,
        "recordPlacement": {
            "record5.xyz": "word 0, 1, 2",
            "record6.xyz": "word 3, 4, 5",
        },
        "precisionBoundary": (
            "the pack layout and analytic candidate are exact through the installed managed helpers; "
            "signed-zero bits and any one-float32-ULP-sensitive half boundary remain conditional on the opaque UnityPlayer "
            "inverse result and require its internal-call body or a retail buffer capture"
        ),
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_index(folder: Path) -> dict[int, tuple[Path, dict[str, Any]]]:
    result: dict[int, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(folder.glob("*.json")):
        data = load_json(path)
        metadata_path_id = (data.get("$animestudio") or {}).get("pathId")
        embedded_path_id = (
            ((data.get("m_Transform") or {}).get("m_GameObject") or {}).get(
                "m_PathID"
            )
        )
        path_id = int(
            metadata_path_id if metadata_path_id is not None else embedded_path_id
        )
        require(f"dump_unique_path_id_{path_id}", path_id in result, False, folder)
        result[path_id] = (path, data)
    return result


def attach_room_additional_data(
    rows: list[dict[str, Any]],
    game_objects: dict[int, tuple[Path, dict[str, Any]]] | None = None,
    behaviours: dict[int, tuple[Path, dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    game_objects = game_objects or dump_index(ROOM_RAW_DUMP_ROOT / "GameObject")
    behaviours = behaviours or dump_index(ROOM_RAW_DUMP_ROOT / "MonoBehaviour")
    required_fields = {
        "m_lightNPRData:Vector4f",
        "m_lightNPRType:int",
        "m_lightNPRAdvancedParamMode:UInt8",
        "m_lightNPRDefaultContrast:float",
        "m_lightNPRDefaultAutoLimit:UInt8",
        "m_LightCharacterOnly:UInt8",
        "m_volumetricScatteringIntensity:float",
        "m_falloffExponent:float",
    }
    enriched = []
    for source_row in rows:
        row = dict(source_row)
        light = load_json(REPO_ROOT / row["sourcePath"])
        game_object_id = int(light["m_GameObject"]["m_PathID"])
        require(
            f"room_{row['lightPathId']}_game_object_present",
            game_object_id in game_objects,
            True,
            ROOM_RAW_DUMP_ROOT / "GameObject",
        )
        game_object_path, game_object = game_objects[game_object_id]
        components = game_object.get("m_Components") or []
        require(
            f"room_{row['lightPathId']}_component_count",
            len(components),
            3,
            game_object_path,
        )
        require(
            f"room_{row['lightPathId']}_light_component",
            int(components[1]["m_PathID"]),
            int(row["lightPathId"]),
            game_object_path,
        )
        behaviour_id = int(components[2]["m_PathID"])
        require(
            f"room_{row['lightPathId']}_additional_component_present",
            behaviour_id in behaviours,
            True,
            ROOM_RAW_DUMP_ROOT / "MonoBehaviour",
        )
        behaviour_path, data = behaviours[behaviour_id]
        metadata = data["$animestudio"]
        raw_sidecar = behaviour_path.with_name(metadata["rawDataSidecar"])
        require(
            f"room_{row['lightPathId']}_additional_raw_sidecar_present",
            raw_sidecar.is_file(),
            True,
            raw_sidecar,
        )
        require(
            f"room_{row['lightPathId']}_additional_raw_sha256",
            sha256(raw_sidecar),
            metadata["rawDataSha256"],
            raw_sidecar,
        )
        require(
            f"room_{row['lightPathId']}_additional_component_owner",
            int(data["m_GameObject"]["m_PathID"]),
            game_object_id,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_additional_component_enabled",
            bool(data["m_Enabled"]),
            True,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_additional_script_file_id",
            int(data["m_Script"]["m_FileID"]),
            1,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_additional_script_path_id",
            int(data["m_Script"]["m_PathID"]),
            HG_ADDITIONAL_LIGHT_DATA_SCRIPT_PATH_ID,
            behaviour_path,
        )
        field_paths = set(metadata["typeTreeFieldPaths"])
        require(
            f"room_{row['lightPathId']}_additional_type_tree_fields",
            required_fields.issubset(field_paths),
            True,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_npr_type",
            int(data["m_lightNPRType"]),
            0,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_npr_advanced",
            bool(data["m_lightNPRAdvancedParamMode"]),
            False,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_npr_contrast",
            float(data["m_lightNPRDefaultContrast"]),
            1.0,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_npr_auto_limit",
            bool(data["m_lightNPRDefaultAutoLimit"]),
            True,
            behaviour_path,
        )
        serialized_npr = [
            float(data["m_lightNPRData"][key]) for key in ("x", "y", "z", "w")
        ]
        require(
            f"room_{row['lightPathId']}_npr_serialized_carrier",
            serialized_npr,
            [1.0, 1.0, 0.0, 0.0],
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_character_only",
            bool(data["m_LightCharacterOnly"]),
            False,
            behaviour_path,
        )
        require(
            f"room_{row['lightPathId']}_falloff_exponent",
            float(data["m_falloffExponent"]),
            -1.0,
            behaviour_path,
        )
        volumetric = float(data["m_volumetricScatteringIntensity"])
        require(
            f"room_{row['lightPathId']}_volumetric_value",
            volumetric in (0.0, 1.0, 10.0),
            True,
            behaviour_path,
        )
        row["gameObjectPathId"] = game_object_id
        row["additionalLightData"] = {
            "componentPathId": behaviour_id,
            "sourcePath": behaviour_path.relative_to(REPO_ROOT).as_posix(),
            "rawSidecarPath": raw_sidecar.relative_to(REPO_ROOT).as_posix(),
            "sourceRawDataSha256": metadata["rawDataSha256"],
            "scriptFileId": 1,
            "scriptPathId": HG_ADDITIONAL_LIGHT_DATA_SCRIPT_PATH_ID,
            "typeTreeSource": metadata["typeTreeSource"],
            "nprType": 0,
            "nprDataSerialized": serialized_npr,
            "nprDataNativePacked": [1.0, 1.0, 0.0, 0.0],
            "characterOnly": False,
            "volumetricScatteringIntensity": volumetric,
            "falloffExponent": -1.0,
        }
        enriched.append(row)
    return enriched


def room_light_rows(population: dict[str, Any], hierarchy: dict[str, Any]) -> list[dict[str, Any]]:
    known = population["exactKnownAuthoredSelectedAspectSurvivors"]
    ordered = [row["name"] for row in known["rows"] if row["source"] == "SceneLight6Rarity"]
    require("selected_room_order", ordered, EXPECTED_ROOM_ORDER, GACHA_POPULATION)

    hierarchy_rows = {
        row["name"]: row
        for row in hierarchy["lights"]
        if row["rarityGroup"] == "SceneLight6Rarity"
    }
    require("rarity6_unique_names", len(hierarchy_rows), 12, ROOM_HIERARCHY)

    result = []
    for name in ordered:
        source = hierarchy_rows[name]
        path_id = int(source["lightPathId"])
        path_hex = f"{path_id & ((1 << 64) - 1):016X}"
        matches = list(ROOM_LIGHT_ROOT.glob(f"*p{path_hex}.json"))
        require(f"{name}_source_file_count", len(matches), 1, ROOM_LIGHT_ROOT)
        path = matches[0]
        data = json.loads(path.read_text(encoding="utf-8"))
        require(f"{name}_source_path_id", int(data["$animestudio"]["pathId"]), path_id, path)
        require(f"{name}_enabled", bool(data["m_Enabled"]), True, path)
        require(f"{name}_obb", bool(data["m_EnableOBBCullingBox"]), True, path)
        require(f"{name}_shadow_only", bool(data["m_ShadowOnly"]), False, path)
        require(
            f"room_{path_id}_use_color_temperature",
            bool(data["m_UseColorTemperature"]),
            False,
            path,
        )
        require(
            f"room_{path_id}_use_culling_distance",
            bool(data["m_UseCullingDistance"]),
            False,
            path,
        )
        require(f"room_{path_id}_culling_distance", float(data["m_CullingDistance"]), 100.0, path)
        require(f"room_{path_id}_falloff_distance", float(data["m_FalloffDistance"]), 100.0, path)
        require(
            f"room_{path_id}_use_far_distance_show",
            bool(data["m_UseFarDistanceShow"]),
            False,
            path,
        )
        require(
            f"room_{path_id}_far_distance_show_distance",
            float(data["m_FarDistanceShowDistance"]),
            10.0,
            path,
        )
        require(
            f"room_{path_id}_far_distance_show_falloff_distance",
            float(data["m_FarDistanceShowFalloffDistance"]),
            12.0,
            path,
        )
        animation = data["m_LightAnimationSetting"]
        flicker = animation["lightAnimatedData"]["flickerData"]
        require(
            f"room_{path_id}_light_animation_enabled",
            bool(animation["enableLightAnimation"]),
            False,
            path,
        )
        require(
            f"room_{path_id}_light_multi_state_enabled",
            bool(animation["enableMultiState"]),
            False,
            path,
        )
        require(
            f"room_{path_id}_light_flicker_enabled",
            bool(flicker["enableFlicker"]),
            False,
            path,
        )
        require(
            f"room_{path_id}_light_flicker_style_file_id",
            int(flicker["flickerStyle"]["m_FileID"]),
            0,
            path,
        )
        require(
            f"room_{path_id}_light_flicker_style_path_id",
            int(flicker["flickerStyle"]["m_PathID"]),
            0,
            path,
        )
        require(f"room_{path_id}_light_state_count", len(animation["lightState"]), 0, path)
        require(
            f"room_{path_id}_light_state_transition_count",
            len(animation["lightStateTransition"]),
            0,
            path,
        )
        require(
            f"{name}_override_shadow",
            bool(data["m_Shadows"]["m_EnableOverrideShadowLight"]),
            False,
            path,
        )
        require(f"{name}_cookie", int(data["m_Cookie"]["m_PathID"]), 0, path)
        require(
            f"{name}_shadow_type",
            int(data["m_Shadows"]["m_PlatformSpecificType"]["defaultParam"]),
            0,
            path,
        )
        result.append(
            {
                "name": name,
                "lightPathId": path_id,
                "sourcePath": path.relative_to(REPO_ROOT).as_posix(),
                "sourceRawDataSha256": data["$animestudio"]["rawDataSha256"],
                "unityLightType": int(data["m_Type"]),
                "color": [float(data["m_Color"][key]) for key in ("r", "g", "b", "a")],
                "intensity": float(data["m_Intensity"]),
                "useColorTemperature": False,
                "colorTemperature": float(data["m_ColorTemperature"]),
                "useCullingDistance": False,
                "cullingDistance": 100.0,
                "falloffDistance": 100.0,
                "useFarDistanceShow": False,
                "farDistanceShowDistance": 10.0,
                "farDistanceShowFalloffDistance": 12.0,
                "lightAnimation": {
                    "enabled": False,
                    "multiStateEnabled": False,
                    "flickerEnabled": False,
                    "flickerStylePathId": 0,
                    "stateCount": 0,
                    "transitionCount": 0,
                },
                "range": float(data["m_Range"]),
                "innerSpotAngleDegrees": float(data["m_InnerSpotAngle"]),
                "outerSpotAngleDegrees": float(data["m_SpotAngle"]),
                "linearLightLength": float(data["m_LinearLightLength"]),
                "softSourceRadius": float(data["m_SoftSourceRadius"]),
                "specularIntensity": float(data["m_SpecularIntensity"]),
                "cullingBoxRelativePosition": data["m_CullingBoxRelativePosition"],
                "cullingBoxHalfExtents": data["m_CullingBoxHalfExtents"],
                "cullingBoxOrientationZxyDegrees": data["m_CullingBoxOrientation"],
                "cullingBoxFalloffThreshold": float(data["m_CullingBoxFalloffThreshold"]),
                "shadowOnly": False,
                "overrideShadowLight": False,
                "cookiePathId": 0,
                "shadowType": 0,
            }
        )

    require("selected_room_type_counts", Counter(row["unityLightType"] for row in result), Counter({2: 10, 0: 1}), ROOM_LIGHT_ROOT)
    require(
        "selected_linear_extension_count",
        sum(row["unityLightType"] == 2 and row["linearLightLength"] > 0 for row in result),
        4,
        ROOM_LIGHT_ROOT,
    )
    return result


def recover_record0_color(row: dict[str, Any]) -> dict[str, Any]:
    source = REPO_ROOT / row["sourcePath"]
    color_bits = tuple(float32_bits(value) for value in row["color"])
    require(
        f"room_{row['lightPathId']}_record0_authored_color_known",
        color_bits in EXPECTED_LINEAR_COLOR_BITS,
        True,
        source,
    )
    linear_bits = EXPECTED_LINEAR_COLOR_BITS[color_bits]
    intensity_bits = float32_bits(row["intensity"])
    key = (color_bits, intensity_bits)
    require(
        f"room_{row['lightPathId']}_record0_color_intensity_known",
        key in EXPECTED_RECORD0_RGB_BITS,
        True,
        source,
    )
    expected_bits = EXPECTED_RECORD0_RGB_BITS[key]
    calculated_bits = tuple(
        float32_bits(f32(float32_from_bits(bits) * row["intensity"]))
        for bits in linear_bits[:3]
    )
    require(
        f"room_{row['lightPathId']}_record0_rgb_bits",
        calculated_bits,
        expected_bits,
        source,
    )
    return {
        "producerFormula": "VisibleLight.finalColor.rgb * GetLightFalloff * flickerScale",
        "serializedColorBits": [f"0x{bits:08X}" for bits in color_bits],
        "unityPlayerLinearColorBits": [f"0x{bits:08X}" for bits in linear_bits],
        "unityPlayerLinearColor": [float32_from_bits(bits) for bits in linear_bits],
        "intensity": row["intensity"],
        "intensityBits": f"0x{intensity_bits:08X}",
        "falloff": 1.0,
        "flickerScale": 1.0,
        "record0RgbBits": [f"0x{bits:08X}" for bits in expected_bits],
        "record0Rgb": [float32_from_bits(bits) for bits in expected_bits],
    }


def validate_consumer(text: str) -> dict[str, Any]:
    checks = {
        "recordStride": "int((32u * _747) + _758) * 8",
        "record0Type": "_LightDataBuffer_f_96[_764].w < 1.5f",
        "record1Position": "_LightDataBuffer_f_96[_767].xyz - _448",
        "record1InverseRange": "_LightDataBuffer_f_96[_767].w * _LightDataBuffer_f_96[_767].w",
        "record2Direction": "_LightDataBuffer_f_96[_770].y",
        "record3CharacterOnly": "_LightDataBuffer_f_96[_773].z > 0.5f",
        "record5ObbFlags": "uint(_LightDataBuffer_f_96[_776].w)",
        "record5ObbWord0": "asuint(_LightDataBuffer_f_96[_776].x)",
        "record5ObbWord1": "asuint(_LightDataBuffer_f_96[_776].y)",
        "record5ObbWord2": "asuint(_LightDataBuffer_f_96[_776].z)",
        "record6ObbWord3": "asuint(_LightDataBuffer_f_96[_779].x)",
        "record6ObbWord4": "asuint(_LightDataBuffer_f_96[_779].y)",
        "record6ObbWord5": "asuint(_LightDataBuffer_f_96[_779].z)",
        "obbRowTranspose": "spvUnpackHalf2x16(_792).x, spvUnpackHalf2x16(_806).x, spvUnpackHalf2x16(_820).x",
        "record6Falloff": "_LightDataBuffer_f_96[_779].w < 0.0f",
        "record7ObbThreshold": "_LightDataBuffer_f_96[_782].x * 0.5f",
        "record7SoftRadius": "_LightDataBuffer_f_96[_782].y * _1397",
        "record7CookieSlot": "int(_LightDataBuffer_f_96[_782].w)",
        "record7Specular": "_LightDataBuffer_f_96[_782].z",
    }
    for check, token in checks.items():
        require(f"consumer_{check}", token in text, True, SELECTED_FRAGMENT)
    return {
        "strideVectors": 8,
        "records": {
            "0": "final color xyz; packed light-kind/shadow-only discriminator w",
            "1": "world position xyz; inverse range w",
            "2": "octahedral direction xy; spot cone or linear-area terms zw",
            "3": "shadow/cookie address x; volumetric intensity y; CharacterOnly z; NPR type w",
            "4": "HGLightAdditionalData.lightNPRData",
            "5": "first packed OBB transform words; OBB/override bit field w",
            "6": "remaining packed OBB transform words; falloff exponent/mode w",
            "7": "OBB falloff threshold, soft-source radius, specular intensity, cookie slot",
        },
    }


def build_audit() -> dict[str, Any]:
    hashes = {
        "gameAssemblySha256": verified_hash("gameAssembly", GAME_ASSEMBLY),
        "unityPlayerSha256": verified_hash("unityPlayer", UNITY_PLAYER),
        "globalMetadataSha256": verified_hash("globalMetadata", GLOBAL_METADATA),
        "globalGameManagersSha256": verified_hash(
            "globalGameManagers", GLOBAL_GAME_MANAGERS
        ),
        "selectedFragmentSha256": verified_hash("selectedFragment", SELECTED_FRAGMENT),
        "gachaPopulationSha256": verified_hash("gachaPopulation", GACHA_POPULATION),
        "roomHierarchySha256": verified_hash("roomHierarchy", ROOM_HIERARCHY),
    }
    with GAME_ASSEMBLY.open("rb") as stream:
        stream.seek(PREPARE_CPU_DATA_FILE_OFFSET)
        body = stream.read(PREPARE_CPU_DATA_SIZE)
        stream.seek(GET_LIGHT_NPR_DATA_FILE_OFFSET)
        npr_body = stream.read(GET_LIGHT_NPR_DATA_SIZE)
        stream.seek(GET_LIGHT_ADDITIONAL_DATA_FILE_OFFSET)
        additional_body = stream.read(GET_LIGHT_ADDITIONAL_DATA_SIZE)
        stream.seek(GET_LIGHT_FALLOFF_FILE_OFFSET)
        falloff_body = stream.read(GET_LIGHT_FALLOFF_SIZE)
        stream.seek(GET_LIGHT_FALLOFF_DEFAULT_FILE_OFFSET)
        falloff_default = stream.read(4)
        stream.seek(PACK_TWO_HALF_FILE_OFFSET)
        pack_body = stream.read(PACK_TWO_HALF_SIZE)
        stream.seek(F32_TO_F16_FILE_OFFSET)
        f32_to_f16_body = stream.read(F32_TO_F16_BODY_SIZE)
        stream.seek(F32_TO_F16_MAGIC_FILE_OFFSET)
        magic_bytes = stream.read(4)
        stream.seek(F32_TO_F16_SCALE_FILE_OFFSET)
        scale_bytes = stream.read(4)
        stream.seek(DEGREES_TO_RADIANS_FILE_OFFSET)
        degrees_to_radians_bytes = stream.read(4)
    global_game_managers_data = GLOBAL_GAME_MANAGERS.read_bytes()
    unity_player_data = UNITY_PLAYER.read_bytes()
    population = json.loads(GACHA_POPULATION.read_text(encoding="utf-8"))
    hierarchy = json.loads(ROOM_HIERARCHY.read_text(encoding="utf-8"))
    rows = attach_room_additional_data(room_light_rows(population, hierarchy))
    for row in rows:
        row["record0Color"] = recover_record0_color(row)
        row["obbPackedTransform"] = recover_obb_pack(row)
    consumer = validate_consumer(SELECTED_FRAGMENT.read_text(encoding="utf-8"))
    native = validate_native_body(body)
    native["additionalLightData"] = validate_additional_data_native(
        npr_body, additional_body
    )
    native["lightFalloff"] = validate_light_falloff_native(
        falloff_body, falloff_default
    )
    native["unityPlayerLightColor"] = validate_unity_light_color_native(
        unity_player_data
    )
    native["obbHalfPacking"] = validate_obb_pack_native(
        pack_body,
        f32_to_f16_body,
        magic_bytes,
        scale_bytes,
        degrees_to_radians_bytes,
    )
    volumetric_counts = Counter(
        row["additionalLightData"]["volumetricScatteringIntensity"] for row in rows
    )
    obb_boundaries = [
        {
            "name": row["name"],
            "halfLanes": row["obbPackedTransform"]["oneFloat32UlpSensitiveHalfLanes"],
        }
        for row in rows
        if row["obbPackedTransform"]["oneFloat32UlpSensitiveHalfLanes"]
    ]
    require(
        "selected_room_obb_one_ulp_boundaries",
        obb_boundaries,
        [{"name": "Spot Light (12)", "halfLanes": [0]}],
        ROOM_LIGHT_ROOT,
    )
    maximum_obb_corner_error = max(
        row["obbPackedTransform"]["maximumAuthoredCornerBoundaryError"]
        for row in rows
    )
    return {
        "schema": "endfield.gacha-deferred-light-data-recovery.v4",
        "status": "room_record0_color_and_obb_candidates_closed",
        "installedInputs": hashes,
        "originalGlobalLightingSettings": validate_global_lighting_settings(
            global_game_managers_data
        ),
        "nativeProducer": native,
        "selectedConsumer": {
            "path": SELECTED_FRAGMENT.relative_to(LAB_ROOT).as_posix(),
            "binding": 31,
            **consumer,
        },
        "selectedAuthoredRoomRows": {
            "count": len(rows),
            "typeCounts": {"Spot": 1, "PointOrLinearExtension": 10},
            "linearExtensionPointCount": 4,
            "ordinaryPointCount": 6,
            "allObbEnabled": True,
            "allUnshadowed": True,
            "allCookieFree": True,
            "allAdditionalComponentsResolved": True,
            "allColorTemperatureDisabled": True,
            "allDistanceFalloffDisabled": True,
            "allFarDistanceShowDisabled": True,
            "allLightAnimationDisabled": True,
            "record0ColorSummary": {
                "globalColorSpace": "Linear",
                "lightsUseLinearIntensity": True,
                "allUseColorTemperature": False,
                "allFalloff": 1.0,
                "allFlickerScale": 1.0,
                "exactCandidateCount": len(rows),
                "closedLanes": ["record0.x", "record0.y", "record0.z"],
            },
            "obbHalfPackingSummary": {
                "producerFormula": "inverse TRS of authored relative position, ZXY Euler orientation, and half extents",
                "wordPlacement": "six row-major half2 words in record5.xyz then record6.xyz",
                "installedPackingMethodClosed": True,
                "analyticCandidateCount": len(rows),
                "oneFloat32UlpSensitiveLocations": obb_boundaries,
                "signedZeroBitsCaptured": False,
                "maximumAuthoredCornerBoundaryError": maximum_obb_corner_error,
            },
            "additionalLightDataSummary": {
                "scriptPathId": HG_ADDITIONAL_LIGHT_DATA_SCRIPT_PATH_ID,
                "nprType": 0,
                "nprDataNativePacked": [1.0, 1.0, 0.0, 0.0],
                "allCharacterOnly": False,
                "allFalloffExponent": -1.0,
                "volumetricScatteringIntensityCounts": {
                    "0": volumetric_counts[0.0],
                    "1": volumetric_counts[1.0],
                    "10": volumetric_counts[10.0],
                },
                "b31ProducerLanesClosed": [
                    "record3.y volumetricScatteringIntensity",
                    "record3.z LightCharacterOnly",
                    "record3.w lightNPRType",
                    "record4.xyzw lightNPRData",
                    "record6.w falloffExponent",
                ],
            },
            "rows": rows,
        },
        "evidenceBoundary": {
            "closed": [
                "PrepareCPUData owns all eight float4 writes for both native Spot and Point/linear-extension branches",
                "the selected deferred consumer's record offsets and observed lane semantics",
                "the exact selected-aspect 11-row authored room membership and raw Unity Light inputs",
                "one Spot, six ordinary Point, and four positive-length linear-extension Point rows",
                "all eleven selected room rows enable OBB culling and have no cookie, shadow, shadow-only, or override-shadow state",
                "all eleven room HGAdditionalLightData components, their exact source PathIDs/hashes, and the native 32-byte return layout",
                "all rows use NPR type 0 with (1,1,0,0), CharacterOnly false, and falloff exponent -1; volumetric values split 2/5/4 across 0/1/10",
                "the corresponding producer lanes record3.yzw, record4.xyzw, and record6.w",
                "the OBB producer call chain: relative position, half extents, ZXY Euler orientation, inverse TRS, and six row-major half pairs",
                "the installed HGUtils/math.f32tof16 method bodies, x-low/y-high word layout, and record5.xyz/record6.xyz placement",
                "six-word analytic OBB candidates for all eleven rows and every non-boundary half payload; decoded candidates return every authored corner to the unit-box boundary within 0.003",
                "the installed PlayerSettings Linear color space and GraphicsSettings linear-light-intensity/color-temperature flags from pinned globalgamemanagers objects",
                "the UnityPlayer finalColor producer, Color.linear body, light-animation disable path, and flickerScale inactive fallback of exactly 1.0",
                "all eleven rows disable per-light color temperature, culling-distance/far-show falloff, animation, multistate, and flicker; their state tables and flicker references are empty",
                "exact UnityPlayer-derived record0.xyz IEEE-754 candidates for all eleven rows: linearized serialized RGB times intensity, with falloff and flickerScale both 1",
            ],
            "open": [
                "camera-relative position/direction values at the target frame and the exact record0.w kind/shadow discriminator payload",
                "exact IEEE signed-zero bits in the packed OBB lanes, the UnityPlayer internal inverse result for one reciprocal at a one-float32-ULP half boundary, and shadow/cookie cache indices",
                "the complete retail survivor array, runtime/custom carry-in, and final lightCount",
            ],
            "decision": (
                "Treat the eight-record native schema and the eleven serialized room inputs as source-closed, "
                "including their record0.xyz color, additional-light lanes, and bounded OBB transform candidates. Do not publish "
                "a byte-exact Gacha b31 fixture or enable deferred pass 0 until the remaining UnityPlayer/boundary "
                "bits, target-frame transforms, record0.w, and runtime list boundary are closed."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_audit(), indent=2) + "\n"
    if args.check:
        require("generated_output", OUTPUT.read_text(encoding="utf-8"), rendered, OUTPUT)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "Gacha deferred LightData audit passed: native Spot/Point 8-float4 schema, "
        "all 11 record0.xyz colors/additional-light components, and bounded OBB half candidates closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
