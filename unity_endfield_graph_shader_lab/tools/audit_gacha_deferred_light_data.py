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
GACHA_CULL_VIEW_AUDIT = (
    REPO_ROOT / "scratch/reverse_engineering/gacha_light_cull_view/audit.json"
)
ROTATEHOUSE = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_start_order/gacharoom_raw_dump/"
    "GameObject/rotatehouse_pB2306755E2A9ADE0.json"
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
PUNCTUAL_SHADOW_CACHE_INDEX_VA = 0x189B486D4
PUNCTUAL_SHADOW_CACHE_INDEX_FILE_OFFSET = 0x9B46CD4
PUNCTUAL_SHADOW_CACHE_INDEX_SIZE = 0x134
GET_SHADOW_RENDER_TYPE_VA = 0x189B48808
GET_SHADOW_RENDER_TYPE_FILE_OFFSET = 0x9B46E08
GET_SHADOW_RENDER_TYPE_SIZE = 0x104
GET_SHADOW_RENDER_TYPE_PATCH_ID = 0x886
WRAPPERS_MANAGER_IS_PATCHED_VA = 0x1831068E0
WRAPPERS_MANAGER_IS_PATCHED_FILE_OFFSET = 0x3104EE0
WRAPPERS_MANAGER_IS_PATCHED_SIZE = 0x4D
WRAPPERS_MANAGER_IS_PATCHED_COLD_VA = 0x184E35008
WRAPPERS_MANAGER_IS_PATCHED_COLD_FILE_OFFSET = 0x4E33608
WRAPPERS_MANAGER_IS_PATCHED_COLD_SIZE = 0x46
WRAPPERS_MANAGER_GET_PATCH_VA = 0x189CDC2C0
WRAPPERS_MANAGER_GET_PATCH_FILE_OFFSET = 0x9CDA8C0
WRAPPERS_MANAGER_GET_PATCH_SIZE = 0x53
WRAPPERS_MANAGER_TABLE_GLOBAL_VA = 0x18E28EC48
ILFIX_DYNAMIC_METHOD_WRAPPER_874_VA = 0x189CD140C
FAIL_FAST_VA = 0x1800D8260
GET_RENDERER_CONFIG_VA = 0x189B4861C
GET_RENDERER_CONFIG_FILE_OFFSET = 0x9B46C1C
GET_RENDERER_CONFIG_SIZE = 0xB8
GET_RENDERER_CONFIG_PATCH_ID = 0x887
ILFIX_DYNAMIC_METHOD_WRAPPER_875_VA = 0x189CD1564
GET_ECS_RENDER_FLAGS_VA = 0x189B48344
GET_ECS_RENDER_FLAGS_FILE_OFFSET = 0x9B46944
GET_ECS_RENDER_FLAGS_SIZE = 0x178
GET_ECS_RENDER_FLAGS_PATCH_ID = 0x888
HG_SHARED_LIGHT_ENABLE_HD_CHARACTER_SHADOW_VA = 0x18B3BDD10
HG_HDPLS_GET_ACTIVE_VA = 0x189B42908
HG_SHARED_LIGHT_EXTENSION_GET_ENTITY_VA = 0x189D08BE8
HG_HDPLS_IS_LIGHT_VA = 0x189B46C38
ILFIX_DYNAMIC_METHOD_WRAPPER_876_VA = 0x189CD1664
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
HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_VA = 0x18B3BDFA4
HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_FILE_OFFSET = 0xB3BC5A4
HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_SIZE = 0x12
HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_VA = 0x18B3BDA84
HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_FILE_OFFSET = 0xB3BC084
HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_SIZE = 0x15
HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_VA = 0x18B3BDA6C
HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_FILE_OFFSET = 0xB3BC06C
HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_SIZE = 0x15
VISIBLE_LIGHT_GET_RANGE_VA = 0x184DBCCB0
VISIBLE_LIGHT_GET_RANGE_FILE_OFFSET = 0x4DBB2B0
VISIBLE_LIGHT_GET_RANGE_SIZE = 8
SCALAR_COS_VA = 0x180334EA0
SCALAR_COS_FILE_OFFSET = 0x3342A0
SCALAR_COS_SIZE = 0x21F
SPOT_ANGLE_DIVISOR_FILE_OFFSET = 0xB9576AC
SPOT_ANGLE_PI_FILE_OFFSET = 0xB957C80
SPOT_ANGLE_DIVISOR_BITS = 0x43B40000
SPOT_ANGLE_PI_BITS = 0x40490FDB
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
# ``Matrix4x4::Inverse`` is the UnityPlayer half of the managed
# ``UnityEngine.Matrix4x4.get_inverse`` call used by b31's OBB producer.  Keep
# the complete lookup chain pinned: a managed wrapper address alone does not
# prove which UnityPlayer implementation is active.
MATRIX4X4_INVERSE_ICALL_INDEX = 2471
MATRIX4X4_INVERSE_NAME_FILE_OFFSET = 0x1CC9BD8
MATRIX4X4_INVERSE_NAME_POINTER = 0x181CCAFD8
MATRIX4X4_INVERSE_NAME = "UnityEngine.Matrix4x4::Inverse3DAffine_Injected"
MATRIX4X4_INVERSE_FUNCTION_POINTER = 0x1800A2020
MATRIX4X4_INVERSE_STUB_FILE_OFFSET = 0xA1620
MATRIX4X4_INVERSE_STUB_VA = 0x1800A2020
MATRIX4X4_INVERSE_NATIVE_VA = 0x180569BD0
MATRIX4X4_INVERSE_NATIVE_FILE_OFFSET = 0x5691D0
MATRIX4X4_INVERSE_NATIVE_SIZE = 0x2C4
MATRIX4X4_INVERSE_NATIVE_BODY_SHA256 = (
    "71e600ecd556110747f8fb572abb1ab41343b3f0b3154b7bd5187696922fd20d"
)
MATRIX4X4_INVERSE_SIGN_MASK_FILE_OFFSET = 0x1CF1410
MATRIX4X4_INVERSE_SIGN_MASK_BITS = 0x80000000
MATRIX4X4_INVERSE_DETERMINANT_THRESHOLD_FILE_OFFSET = 0x1D7DA00
MATRIX4X4_INVERSE_DETERMINANT_THRESHOLD = 1e-25
# ``Matrix4x4::TRS_Injected`` is the UnityPlayer half of the managed
# ``Matrix4x4.TRS`` call used immediately before the authored OBB inverse.
# Keep both the icall-table lookup and the native quaternion-to-matrix helper
# pinned: the native body applies scale/translation to the helper's exact
# column-major float32 result.
MATRIX4X4_TRS_ICALL_INDEX = 2470
MATRIX4X4_TRS_NAME_FILE_OFFSET = 0x1CC9BB0
MATRIX4X4_TRS_NAME_POINTER = 0x181CCAFB0
MATRIX4X4_TRS_NAME = "UnityEngine.Matrix4x4::TRS_Injected"
MATRIX4X4_TRS_FUNCTION_POINTER = 0x1800A1BB0
MATRIX4X4_TRS_WRAPPER_FILE_OFFSET = 0xA11B0
MATRIX4X4_TRS_WRAPPER_VA = 0x1800A1BB0
MATRIX4X4_TRS_WRAPPER_SIZE = 0x45
MATRIX4X4_TRS_WRAPPER_BODY_SHA256 = (
    "3edd178a3e30e9d27b133e50983ed473f223584eb229b1a435d45e82d006a8de"
)
MATRIX4X4_TRS_NATIVE_VA = 0x18056CB40
MATRIX4X4_TRS_NATIVE_FILE_OFFSET = 0x56C140
MATRIX4X4_TRS_NATIVE_SIZE = 0xC6
MATRIX4X4_TRS_NATIVE_BODY_SHA256 = (
    "ed2c20824bf8944a67566c874df429a53f6ca1c25f51f0eaf39259a16105b980"
)
MATRIX4X4_TRS_QUATERNION_HELPER_VA = 0x18056B8A0
MATRIX4X4_TRS_QUATERNION_HELPER_FILE_OFFSET = 0x56AEA0
MATRIX4X4_TRS_QUATERNION_HELPER_SIZE = 0x142
MATRIX4X4_TRS_QUATERNION_HELPER_BODY_SHA256 = (
    "415e200d056300c292a580b888e8604f1f2f01a98afc830de6691461f3d3e285"
)
MATRIX4X4_TRS_HELPER_CALL_OFFSET = 0x1E
# ``Quaternion.Euler(Vector3)`` first converts degrees to radians in the
# GameAssembly wrapper, then dispatches ``Internal_FromEulerRad_Injected``.
# Pin both sides of that boundary: the managed wrapper/helper proves the
# float32 degree-to-radian input, while UnityPlayer proves the half-angle and
# native sin/cos call sequence. The IFix function-pointer slot remains a
# runtime boundary and is intentionally reported rather than guessed.
QUATERNION_EULER_MANAGED_VA = 0x182FA5910
QUATERNION_EULER_MANAGED_FILE_OFFSET = 0x2FA3F10
QUATERNION_EULER_MANAGED_SIZE = 0x7D
QUATERNION_EULER_MANAGED_BODY_SHA256 = (
    "f121f5fab7dc03bec3bf2bdc9397d7464ee1b5df96f87c0e00979a67e2a68c01"
)
QUATERNION_EULER_SCALE_HELPER_VA = 0x184DBBC80
QUATERNION_EULER_SCALE_HELPER_FILE_OFFSET = 0x4DBA280
QUATERNION_EULER_SCALE_HELPER_SIZE = 0x24
QUATERNION_EULER_SCALE_HELPER_BODY_SHA256 = (
    "6d8f004cb69175ca921b4eb758db8344af753c24039c85a4a76579f838886f83"
)
QUATERNION_EULER_MANAGED_SCALE_CALL_OFFSET = 0x32
QUATERNION_EULER_MANAGED_DEGREES_TO_RADIANS_FILE_OFFSET = 0xB9576A0
QUATERNION_EULER_ICALL_INDEX = 2489
QUATERNION_EULER_NAME_FILE_OFFSET = 0x1CC9EF0
QUATERNION_EULER_NAME_POINTER = 0x181CCB2F0
QUATERNION_EULER_NAME = "UnityEngine.Quaternion::Internal_FromEulerRad_Injected"
QUATERNION_EULER_FUNCTION_POINTER = 0x1800A5010
QUATERNION_EULER_STUB_FILE_OFFSET = 0xA4610
QUATERNION_EULER_STUB_VA = 0x1800A5010
QUATERNION_EULER_STUB_SIZE = 0x28
QUATERNION_EULER_STUB_BODY_SHA256 = (
    "4a07f22965618b8620cf0f5f7e5bacef4a731f3f6a7ebe656e7b9a9092f9bbff"
)
QUATERNION_EULER_NATIVE_VA = 0x180567590
QUATERNION_EULER_NATIVE_FILE_OFFSET = 0x566B90
QUATERNION_EULER_NATIVE_SIZE = 0x88B
QUATERNION_EULER_NATIVE_BODY_SHA256 = (
    "ef6c901cf98d6c2658be06abe98eb7747837b6794fb94063c3d2a1f9804b3130"
)
QUATERNION_EULER_HALF_ANGLE_FILE_OFFSET = 0x1CF0EDC
QUATERNION_EULER_HALF_ANGLE_BITS = 0x3F000000
QUATERNION_EULER_SIN_VA = 0x181C634F0
QUATERNION_EULER_COS_VA = 0x181C620A0
QUATERNION_EULER_MATH_CALLS = (
    (0x58, QUATERNION_EULER_SIN_VA, "sin(float32 half-angle)"),
    (0x69, QUATERNION_EULER_COS_VA, "cos(float32 half-angle)"),
    (0x7B, QUATERNION_EULER_SIN_VA, "sin(float32 half-angle)"),
    (0x8D, QUATERNION_EULER_COS_VA, "cos(float32 half-angle)"),
    (0x9F, QUATERNION_EULER_SIN_VA, "sin(float32 half-angle)"),
    (0xB1, QUATERNION_EULER_COS_VA, "cos(float32 half-angle)"),
)
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
    "gachaCullViewAudit": "4717ddd564f0eee2e1742024660e233e09865b4a301a4b7566aaca6844011dc4",
    "rotatehouse": "3cac5172e91bb3cddf1a8c6db8e8550620abbfb0c957905f39538b8c97baded4",
    "prepareCpuDataBody": "c55bd6dc86c971123c433a5dd29b446b557f8713f73b132da25c257369e9bd0b",
    "getShadowRenderTypeBody": "bfb6730d6907e208480291489117015ee10293e8489a3735b868ab0fde517233",
    "wrappersManagerIsPatchedBody": "48678146c1cbf1cef4ef7bed4718b73df3e74df0f9cf1c827b5dcd4e5fe85692",
    "wrappersManagerIsPatchedColdBody": "fefa55918137436af9357f114d7eab2296608ddabc34af7ce8a79d57120493d0",
    "wrappersManagerGetPatchBody": "026cc13020ea55d8ca602768e0764e672d004b50509eea615e448b8db7fc91fd",
    "getRendererConfigBody": "07df57dc9a61647510d55da24a8cdd309fab5957d87195946a05e94b3ede4a07",
    "getEcsRenderFlagsBody": "2ad75354fa81b3958de4783f247c8e0993a6986b4c7ff244ce8f36e04615075d",
    "getLightNprDataBody": "49eeca70b72791b2ad58f8b77cf3fbc3f27149766dcc0510a00b9d129e6698c8",
    "getLightAdditionalDataBody": "071061feb7f3c76044273efe703f9bdf78288703516b863c10c592b263f73e00",
    "packTwoHalfBody": "dad4b266316d3ba37f5c20fd92f2db90da363f7b65b3467bf313342c1a8814ce",
    "f32ToF16Body": "dc4fa0754a86aed4b2d58a5a978fe6028d83257aa5fc8e0a06e8fa6b9b5dae62",
    "getLightFalloffBody": "dbb121bbf91f191001755e9290988f4f287fb9fcc1c65cd09254452474a2509d",
    "visibleLightGetRangeBody": "6ef4776b9933e7529c578b48a5fbc7322a242c1f05b8b8ec30b715a199d8a822",
    "scalarCosBody": "02ced20a0867a29f34e8f6e9060bbbea89d8475e154834c57ee2036f63a93bee",
    "playerSettingsObject": "bb2752bf4f4dd43d7885e01520c992289330ea8efdf7321ea926cb7cb149b3d6",
    "graphicsSettingsObject": "8bbfff1de820c06fb150aa4093391bff3ad080eba65f4230d83496ed84b94563",
    "unityFlickerGetterBody": "622b04cd8adaf7bc219e4d56c9dc574f89f324e55128c2ca2c96c624254d3f1b",
    "unitySetLightAnimationBody": "911725357c454b8224102d6b34d32f12d912f9cadbbfcc26aa64dda8b3bb83c6",
    "unityFinalColorUpdateBody": "39cbb35b17202949963e8cb4ed54a9d1e31067ae1c26c766c191c80e004b5e1d",
    "unityColorLinearBody": "83785743304ef92949c2b53f43ba6b1fd9e30655b389f61a1f56a334babd608f",
    "visibleLightGetForwardBody": "ed742d362644817a4275490ffadf42fc0843340060584150e4b8f1f017bb29d1",
    "visibleLightGetPositionBody": "9bf253dbd8822df91b50cc9de46c2aecce39c88fa1b4d9da361639cb02e7dba1",
    "packNormalOctRectEncodeBody": "9b3353f0544568e35e2bc5317515f22207c58ad3efa889e2e336f0c2670b2a2c",
}

EXPECTED_INVERSE_RANGE_BITS = {
    0x41200000: 0x3DCCCCCD,
    0x40E17F92: 0x3E115050,
    0x41600000: 0x3D924925,
    0x40A00000: 0x3E4CCCCD,
    0x40DDB186: 0x3E13CEC6,
    0x41A00000: 0x3D4CCCCD,
    0x41700000: 0x3D888889,
}

EXPECTED_SPOT_RECORD2_BITS = {
    "innerAngleDegrees": 0x42B40000,
    "outerAngleDegrees": 0x430C0000,
    "innerRadians": 0x3F490FDB,
    "outerRadians": 0x3F9C61AB,
    "innerCos": 0x3F3504F3,
    "outerCos": 0x3EAF1D40,
    "cosDifference": 0x3EBAECA6,
    "inverseCosDifference": 0x402F4D02,
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

# Point/linear-extension record2.w is not an opaque float.  The native
# producer constructs six LightCaster face requests in order, queries the
# punctual-shadow cache for each face, maps an unavailable cache slot (-1) to
# the shader sentinel 255, and packs the six byte values into record2.w plus
# the low two byte lanes of record3.x.
# The target-frame cache indices are still runtime state; these offsets pin the
# original producer contract without inventing those values offline.
LIGHT_CASTER_CONSTRUCTOR_VA = 0x189B52B0C
POINT_SHADOW_FACE_CONSTRUCTOR_CALLS = (
    (0x10D4, 0),
    (0x1120, 1),
    (0x1163, 2),
    (0x11A5, 3),
    (0x11E7, 4),
    (0x122A, 5),
)
POINT_SHADOW_CACHE_INDEX_CALLS = (
    (0x10F7, 0),
    (0x113A, 1),
    (0x117D, 2),
    (0x11BF, 3),
    (0x1202, 4),
    (0x1245, 5),
)
POINT_SHADOW_FALLBACK_SEQUENCE = bytes.fromhex(
    "83c9ffbaff000000443bf9440f44fa443bf1440f44f23bf10f44f23bf90f44fa3bd90f44da3bc10f44c2"
)
POINT_SHADOW_PACK_SEQUENCE = bytes.fromhex(
    "41c1e708450bfec1e3084c8bb59000000041c1e708440bfe8b75c041c1e708440bff0bd86641"
)

# The first two dynamic rows in every punctual record are produced from the
# original VisibleLight transform helpers.  The shader later subtracts the
# camera position from record1.xyz, so the native producer stores world-space
# position; record2.xy is the helper's octahedral encoding of light forward.
VISIBLE_LIGHT_GET_FORWARD_VA = 0x189D14F34
HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_VA = 0x189C0EF4C
VISIBLE_LIGHT_GET_POSITION_VA = 0x189D15168
VISIBLE_LIGHT_GET_FORWARD_FILE_OFFSET = 0x9D13534
VISIBLE_LIGHT_GET_FORWARD_SIZE = 0x130
VISIBLE_LIGHT_GET_POSITION_FILE_OFFSET = 0x9D13768
VISIBLE_LIGHT_GET_POSITION_SIZE = 0x130
HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_FILE_OFFSET = 0x9C0D54C
HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_SIZE = 0x158
VISIBLE_LIGHT_GET_FORWARD_IFIX_METHOD_ID = 0x77A
VISIBLE_LIGHT_GET_POSITION_IFIX_METHOD_ID = 0x77D
HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_IFIX_METHOD_ID = 0x77B
VISIBLE_LIGHT_LOCAL_TO_WORLD_MATRIX_FIELD_OFFSET = 0x24
MATRIX4X4_GET_COLUMN_VA = 0x182FA64C0
VECTOR4_IMPLICIT_VECTOR3_VA = 0x184DBBDE0
PACK_NORMAL_ABS_CALL_OFFSET = 0x5D
PACK_NORMAL_ABS_VA = 0x183B0AD90
PACK_NORMAL_DOT_CALL_OFFSET = 0x88
PACK_NORMAL_DOT_VA = 0x184D8B7C0
PACK_NORMAL_FLOAT3_MULTIPLY_CALL_OFFSET = 0x9C
PACK_NORMAL_FLOAT3_MULTIPLY_VA = 0x1830E7A60
PACK_NORMAL_CLAMP_CALL_OFFSET = 0xE7
PACK_NORMAL_CLAMP_VA = 0x182EE75E0
PACK_NORMAL_COPY_SIGN_CALL_OFFSET = 0xF6
PACK_NORMAL_COPY_SIGN_VA = 0x189C0C2F0
PACK_NORMAL_ONE_CONSTANT_FILE_OFFSET = 0xB957600
PACK_NORMAL_HALF_CONSTANT_FILE_OFFSET = 0xB9575E0
POINT_RECORD_TRANSFORM_CALLS = (
    (0x073E, VISIBLE_LIGHT_GET_FORWARD_VA, "VisibleLightExtensionMethods.GetForward"),
    (0x0798, HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_VA, "HGUtils.PackNormalOctRectEncode"),
    (0x083C, VISIBLE_LIGHT_GET_POSITION_VA, "VisibleLightExtensionMethods.GetPosition"),
)

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
    0x0D0D: (SCALAR_COS_VA, "installed scalar cosine for inner half-angle"),
    0x0D1C: (0x18B3BE5FC, "HGSharedLightData.get_spotAngle_Injected"),
    0x0D31: (SCALAR_COS_VA, "installed scalar cosine for outer half-angle"),
    0x0DD9: (0x18B3BE4D0, "HGSharedLightData.get_shadowOnly_Injected Spot"),
    0x1046: (0x18B3BDB48, "HGSharedLightData.get_cullingBoxFalloffThreshold_Injected"),
    0x105A: (0x18B3BE584, "HGSharedLightData.get_softSourceRadius_Injected"),
    0x106E: (0x18B3BE5C0, "HGSharedLightData.get_specularIntensity_Injected"),
    0x1347: (0x18B3BE4D0, "HGSharedLightData.get_shadowOnly_Injected Point"),
    0x13F4: (0x18B3BE030, "HGSharedLightData.get_length_Injected"),
    0x15AE: (0x18B3BDB48, "HGSharedLightData.get_cullingBoxFalloffThreshold_Injected"),
    0x15BF: (0x18B3BE584, "HGSharedLightData.get_softSourceRadius_Injected"),
    0x15D0: (0x18B3BE5C0, "HGSharedLightData.get_specularIntensity_Injected"),
}


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def quaternion_multiply(a: list[float], b: list[float]) -> list[float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [
        f32(aw * bx + ax * bw + ay * bz - az * by),
        f32(aw * by - ax * bz + ay * bw + az * bx),
        f32(aw * bz + ax * by - ay * bx + az * bw),
        f32(aw * bw - ax * bx - ay * by - az * bz),
    ]


def quaternion_rotate(q: list[float], value: list[float]) -> list[float]:
    x, y, z, w = q
    vx, vy, vz = value
    mul = lambda a, b: f32(a * b)
    add = lambda a, b: f32(a + b)
    sub = lambda a, b: f32(a - b)
    tx, ty, tz = mul(2.0, x), mul(2.0, y), mul(2.0, z)
    xx = sub(1.0, add(mul(ty, y), mul(tz, z)))
    xy = sub(mul(tx, y), mul(mul(2.0, w), z))
    xz = add(mul(tx, z), mul(mul(2.0, w), y))
    yx = add(mul(tx, y), mul(mul(2.0, w), z))
    yy = sub(1.0, add(mul(tx, x), mul(tz, z)))
    yz = sub(mul(ty, z), mul(mul(2.0, w), x))
    zx = sub(mul(tx, z), mul(mul(2.0, w), y))
    zy = add(mul(ty, z), mul(mul(2.0, w), x))
    zz = sub(1.0, add(mul(tx, x), mul(ty, y)))
    return [
        add(add(mul(xx, vx), mul(xy, vy)), mul(xz, vz)),
        add(add(mul(yx, vx), mul(yy, vy)), mul(yz, vz)),
        add(add(mul(zx, vx), mul(zy, vy)), mul(zz, vz)),
    ]


def pack_normal_oct_rect_encode_candidate(direction: list[float]) -> list[float]:
    """Mirror the installed unpatched PackNormalOctRectEncode arithmetic."""

    x, y, z = (f32(value) for value in direction)
    absolute = [f32(abs(value)) for value in (x, y, z)]
    # Unity.Mathematics.math.dot(abs(n), float3(1, 1, 1)) executes y+x+z
    # in the pinned scalar body, with an f32 round after each multiply/add.
    y_term = f32(absolute[1] * 1.0)
    x_term = f32(absolute[0] * 1.0)
    z_term = f32(absolute[2] * 1.0)
    l1 = f32(f32(y_term + x_term) + z_term)
    inverse_l1 = f32(1.0 / l1)
    normalized = [f32(value * inverse_l1) for value in (x, y, z)]

    half_x = f32(normalized[0] * 0.5)
    first = f32(0.5 - half_x)
    half_y = f32(normalized[1] * 0.5)
    first = f32(first + half_y)
    first = f32(max(min(first, 1.0), 0.0))
    if normalized[2] < 0.0:
        first = f32(-first)
    second = f32(normalized[1] + normalized[0])
    return [first, second]


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


def cache_index_call_target(body: bytes, offset: int) -> int:
    return relative_call_target(body, PUNCTUAL_SHADOW_CACHE_INDEX_VA, offset)


def shadow_render_type_call_target(body: bytes, offset: int) -> int:
    return relative_call_target(body, GET_SHADOW_RENDER_TYPE_VA, offset)


def renderer_config_call_target(body: bytes, offset: int) -> int:
    return relative_call_target(body, GET_RENDERER_CONFIG_VA, offset)


def ecs_render_flags_call_target(body: bytes, offset: int) -> int:
    return relative_call_target(body, GET_ECS_RENDER_FLAGS_VA, offset)


def relative_short_branch_target(
    body: bytes,
    base_va: int,
    offset: int,
    opcode: int,
    source: Path,
    check: str,
) -> int:
    require(f"{check}_opcode", body[offset], opcode, source)
    displacement = struct.unpack_from("<b", body, offset + 1)[0]
    return base_va + offset + 2 + displacement


def relative_near_branch_target(
    body: bytes,
    base_va: int,
    offset: int,
    opcode: bytes,
    source: Path,
    check: str,
) -> int:
    require(f"{check}_opcode", body[offset : offset + len(opcode)], opcode, source)
    displacement = struct.unpack_from("<i", body, offset + len(opcode))[0]
    return base_va + offset + len(opcode) + 4 + displacement


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


def validate_ifix_wrapper_table_native(
    is_patched_body: bytes,
    is_patched_cold_body: bytes,
    get_patch_body: bytes,
) -> dict[str, Any]:
    """Pin the native IFix wrapper-table lookup ABI.

    The three punctual methods only expose a live table lookup: the manager
    singleton's ``+0xB8`` points at a table whose first pointer is the active
    table, ``+0x18`` is its entry count, and ``+0x20 + 8 * methodId`` stores
    the wrapper pointer. The installed binary does not serialize the active
    entry values, so this validator closes lookup semantics while keeping
    membership and patched return values runtime-boundary evidence.
    """

    expected_bodies = (
        (
            "wrappers_manager_is_patched_body",
            is_patched_body,
            WRAPPERS_MANAGER_IS_PATCHED_SIZE,
            EXPECTED_HASHES["wrappersManagerIsPatchedBody"],
        ),
        (
            "wrappers_manager_is_patched_cold_body",
            is_patched_cold_body,
            WRAPPERS_MANAGER_IS_PATCHED_COLD_SIZE,
            EXPECTED_HASHES["wrappersManagerIsPatchedColdBody"],
        ),
        (
            "wrappers_manager_get_patch_body",
            get_patch_body,
            WRAPPERS_MANAGER_GET_PATCH_SIZE,
            EXPECTED_HASHES["wrappersManagerGetPatchBody"],
        ),
    )
    body_hashes: dict[str, str] = {}
    for check, body, size, expected_hash in expected_bodies:
        require(f"{check}_size", len(body), size, GAME_ASSEMBLY)
        actual_hash = hashlib.sha256(body).hexdigest()
        require(f"{check}_sha256", actual_hash, expected_hash, GAME_ASSEMBLY)
        body_hashes[check] = actual_hash

    require(
        "wrappers_manager_is_patched_global_slot",
        is_patched_body[0x09:0x10],
        bytes.fromhex("488b0d5883180b"),
        GAME_ASSEMBLY,
    )
    require(
        "wrappers_manager_is_patched_table_fields",
        is_patched_body[0x19:0x2B],
        bytes.fromhex("488b81b8000000488b104885d274113b5a18"),
        GAME_ASSEMBLY,
    )
    require(
        "wrappers_manager_is_patched_cold_table_fields",
        is_patched_cold_body[0x15:0x2B],
        bytes.fromhex("488b81b8000000488b084885c90f84e9182dfe3b5918"),
        GAME_ASSEMBLY,
    )
    require(
        "wrappers_manager_get_patch_table_fields",
        get_patch_body[0x21:0x35],
        bytes.fromhex("488b0560295b04488b80b8000000488b104885d2"),
        GAME_ASSEMBLY,
    )
    require(
        "wrappers_manager_get_patch_count_check",
        get_patch_body[0x3D:0x42],
        bytes.fromhex("3b5a187206"),
        GAME_ASSEMBLY,
    )
    require(
        "wrappers_manager_get_patch_entry_load",
        get_patch_body[0x48:0x4D],
        bytes.fromhex("488b44da20"),
        GAME_ASSEMBLY,
    )

    branches = []
    for body, base_va, offset, opcode, target, name in (
        (
            is_patched_body,
            WRAPPERS_MANAGER_IS_PATCHED_VA,
            0x17,
            0x74,
            WRAPPERS_MANAGER_IS_PATCHED_VA + 0x3F,
            "is_patched_init_fallback",
        ),
        (
            is_patched_body,
            WRAPPERS_MANAGER_IS_PATCHED_VA,
            0x26,
            0x74,
            WRAPPERS_MANAGER_IS_PATCHED_VA + 0x39,
            "is_patched_null_table_fail_fast",
        ),
        (
            is_patched_cold_body,
            WRAPPERS_MANAGER_IS_PATCHED_COLD_VA,
            0x07,
            0x75,
            WRAPPERS_MANAGER_IS_PATCHED_COLD_VA + 0x15,
            "is_patched_cold_initialized",
        ),
        (
            is_patched_cold_body,
            WRAPPERS_MANAGER_IS_PATCHED_COLD_VA,
            0x2B,
            0x72,
            WRAPPERS_MANAGER_IS_PATCHED_COLD_VA + 0x33,
            "is_patched_bounds_ok",
        ),
        (
            get_patch_body,
            WRAPPERS_MANAGER_GET_PATCH_VA,
            0x17,
            0x75,
            WRAPPERS_MANAGER_GET_PATCH_VA + 0x28,
            "get_patch_initialized",
        ),
        (
            get_patch_body,
            WRAPPERS_MANAGER_GET_PATCH_VA,
            0x35,
            0x75,
            WRAPPERS_MANAGER_GET_PATCH_VA + 0x3D,
            "get_patch_nonnull_table",
        ),
        (
            get_patch_body,
            WRAPPERS_MANAGER_GET_PATCH_VA,
            0x40,
            0x72,
            WRAPPERS_MANAGER_GET_PATCH_VA + 0x48,
            "get_patch_bounds_ok",
        ),
    ):
        resolved = relative_short_branch_target(
            body,
            base_va,
            offset,
            opcode,
            GAME_ASSEMBLY,
            name,
        )
        require(f"{name}_target", resolved, target, GAME_ASSEMBLY)
        branches.append(
            {
                "name": name,
                "offset": f"0x{offset:X}",
                "target": f"0x{resolved:X}",
            }
        )

    for body, base_va, offset, opcode, target, name in (
        (
            is_patched_body,
            WRAPPERS_MANAGER_IS_PATCHED_VA,
            0x2B,
            bytes.fromhex("0f8c"),
            WRAPPERS_MANAGER_IS_PATCHED_COLD_VA,
            "is_patched_signed_id_gate",
        ),
        (
            is_patched_cold_body,
            WRAPPERS_MANAGER_IS_PATCHED_COLD_VA,
            0x22,
            bytes.fromhex("0f84"),
            WRAPPERS_MANAGER_IS_PATCHED_VA + 0x39,
            "is_patched_cold_null_table_fail_fast",
        ),
        (
            is_patched_cold_body,
            WRAPPERS_MANAGER_IS_PATCHED_COLD_VA,
            0x39,
            bytes.fromhex("0f84"),
            WRAPPERS_MANAGER_IS_PATCHED_VA + 0x31,
            "is_patched_entry_null",
        ),
    ):
        resolved = relative_near_branch_target(
            body,
            base_va,
            offset,
            opcode,
            GAME_ASSEMBLY,
            name,
        )
        require(f"{name}_target", resolved, target, GAME_ASSEMBLY)
        branches.append(
            {
                "name": name,
                "offset": f"0x{offset:X}",
                "target": f"0x{resolved:X}",
            }
        )

    return {
        "managerGlobalSlot": f"0x{WRAPPERS_MANAGER_TABLE_GLOBAL_VA:X}",
        "managerInitializationField": "+0xE0",
        "managerTablePointerField": "+0xB8",
        "tableLayout": {
            "activeTablePointer": "+0x00 of manager[+0xB8]",
            "entryCount": "+0x18",
            "entryArray": "+0x20 + 8 * methodId",
            "entrySizeBytes": 8,
        },
        "isPatched": {
            "virtualAddress": f"0x{WRAPPERS_MANAGER_IS_PATCHED_VA:X}",
            "fileOffset": f"0x{WRAPPERS_MANAGER_IS_PATCHED_FILE_OFFSET:X}",
            "sizeBytes": WRAPPERS_MANAGER_IS_PATCHED_SIZE,
            "bodySha256": body_hashes["wrappers_manager_is_patched_body"],
            "coldVirtualAddress": f"0x{WRAPPERS_MANAGER_IS_PATCHED_COLD_VA:X}",
            "coldFileOffset": f"0x{WRAPPERS_MANAGER_IS_PATCHED_COLD_FILE_OFFSET:X}",
            "coldSizeBytes": WRAPPERS_MANAGER_IS_PATCHED_COLD_SIZE,
            "coldBodySha256": body_hashes["wrappers_manager_is_patched_cold_body"],
            "input": "signed int32 methodId in ecx",
            "outcome": "non-null table entry => true; null/out-of-range/uninitialized => false or fail-fast according to native branch",
        },
        "getPatch": {
            "virtualAddress": f"0x{WRAPPERS_MANAGER_GET_PATCH_VA:X}",
            "fileOffset": f"0x{WRAPPERS_MANAGER_GET_PATCH_FILE_OFFSET:X}",
            "sizeBytes": WRAPPERS_MANAGER_GET_PATCH_SIZE,
            "bodySha256": body_hashes["wrappers_manager_get_patch_body"],
            "input": "signed int32 methodId in ecx",
            "outcome": "returns table entry pointer after unsigned count check; invalid bounds fail-fast",
        },
        "resolvedBranches": branches,
        "runtimeMembershipStillOpen": True,
        "runtimeWrapperPointersStillOpen": True,
        "lookupContractClosed": True,
    }


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


def validate_matrix4x4_inverse_native(data: bytes) -> dict[str, Any]:
    """Pin the UnityPlayer affine inverse used by the authored OBB path.

    The managed ``Matrix4x4.get_inverse`` wrapper only forwards to an
    internal-call table entry.  The target body is therefore validated
    independently of the GameAssembly wrapper.  Its scalar SSE instructions
    compute the determinant, cofactors, translation, and sign-bit flips that
    the OBB half-packing stage consumes.
    """

    function_table_offset = UNITY_ICALL_FUNCTION_TABLE_OFFSET
    name_table_offset = UNITY_ICALL_NAME_TABLE_OFFSET
    index = MATRIX4X4_INVERSE_ICALL_INDEX
    actual_name_pointer = struct.unpack_from(
        "<Q", data, name_table_offset + index * 8
    )[0]
    actual_function_pointer = struct.unpack_from(
        "<Q", data, function_table_offset + index * 8
    )[0]
    require(
        "matrix4x4_inverse_icall_name_pointer",
        actual_name_pointer,
        MATRIX4X4_INVERSE_NAME_POINTER,
        UNITY_PLAYER,
    )
    require(
        "matrix4x4_inverse_icall_function_pointer",
        actual_function_pointer,
        MATRIX4X4_INVERSE_FUNCTION_POINTER,
        UNITY_PLAYER,
    )
    actual_name = data[
        MATRIX4X4_INVERSE_NAME_FILE_OFFSET : MATRIX4X4_INVERSE_NAME_FILE_OFFSET
        + len(MATRIX4X4_INVERSE_NAME)
    ].decode("ascii")
    require(
        "matrix4x4_inverse_icall_name",
        actual_name,
        MATRIX4X4_INVERSE_NAME,
        UNITY_PLAYER,
    )
    require(
        "matrix4x4_inverse_icall_name_terminator",
        data[MATRIX4X4_INVERSE_NAME_FILE_OFFSET + len(MATRIX4X4_INVERSE_NAME)],
        0,
        UNITY_PLAYER,
    )

    stub = data[
        MATRIX4X4_INVERSE_STUB_FILE_OFFSET : MATRIX4X4_INVERSE_STUB_FILE_OFFSET + 5
    ]
    require(
        "matrix4x4_inverse_stub_target",
        relative_branch_target(
            stub,
            MATRIX4X4_INVERSE_STUB_VA,
            0,
            0xE9,
            UNITY_PLAYER,
            "matrix4x4_inverse_stub_jump",
        ),
        MATRIX4X4_INVERSE_NATIVE_VA,
        UNITY_PLAYER,
    )
    body = data[
        MATRIX4X4_INVERSE_NATIVE_FILE_OFFSET : MATRIX4X4_INVERSE_NATIVE_FILE_OFFSET
        + MATRIX4X4_INVERSE_NATIVE_SIZE
    ]
    require(
        "matrix4x4_inverse_native_body_size",
        len(body),
        MATRIX4X4_INVERSE_NATIVE_SIZE,
        UNITY_PLAYER,
    )
    body_hash = hashlib.sha256(body).hexdigest()
    require(
        "matrix4x4_inverse_native_body_sha256",
        body_hash,
        MATRIX4X4_INVERSE_NATIVE_BODY_SHA256,
        UNITY_PLAYER,
    )
    sign_mask_bits = struct.unpack_from(
        "<I", data, MATRIX4X4_INVERSE_SIGN_MASK_FILE_OFFSET
    )[0]
    require(
        "matrix4x4_inverse_sign_mask_bits",
        sign_mask_bits,
        MATRIX4X4_INVERSE_SIGN_MASK_BITS,
        UNITY_PLAYER,
    )
    determinant_threshold = struct.unpack_from(
        "<d", data, MATRIX4X4_INVERSE_DETERMINANT_THRESHOLD_FILE_OFFSET
    )[0]
    require(
        "matrix4x4_inverse_determinant_threshold",
        determinant_threshold,
        MATRIX4X4_INVERSE_DETERMINANT_THRESHOLD,
        UNITY_PLAYER,
    )
    return {
        "icallIndex": index,
        "name": MATRIX4X4_INVERSE_NAME,
        "namePointer": f"0x{MATRIX4X4_INVERSE_NAME_POINTER:X}",
        "functionPointer": f"0x{MATRIX4X4_INVERSE_FUNCTION_POINTER:X}",
        "stubVirtualAddress": f"0x{MATRIX4X4_INVERSE_STUB_VA:X}",
        "nativeVirtualAddress": f"0x{MATRIX4X4_INVERSE_NATIVE_VA:X}",
        "nativeFileOffset": f"0x{MATRIX4X4_INVERSE_NATIVE_FILE_OFFSET:X}",
        "nativeBodySizeBytes": MATRIX4X4_INVERSE_NATIVE_SIZE,
        "nativeBodySha256": body_hash,
        "determinantThreshold": determinant_threshold,
        "signMaskBits": f"0x{sign_mask_bits:08X}",
        "arithmetic": (
            "scalar SSE float32 determinant/cofactor/division sequence; affine "
            "translation uses cofactor rows and xorps sign flips"
        ),
    }


def validate_matrix4x4_trs_native(data: bytes) -> dict[str, Any]:
    """Pin the UnityPlayer TRS producer used by the authored OBB path."""

    index = MATRIX4X4_TRS_ICALL_INDEX
    actual_name_pointer = struct.unpack_from(
        "<Q", data, UNITY_ICALL_NAME_TABLE_OFFSET + index * 8
    )[0]
    actual_function_pointer = struct.unpack_from(
        "<Q", data, UNITY_ICALL_FUNCTION_TABLE_OFFSET + index * 8
    )[0]
    require(
        "matrix4x4_trs_icall_name_pointer",
        actual_name_pointer,
        MATRIX4X4_TRS_NAME_POINTER,
        UNITY_PLAYER,
    )
    require(
        "matrix4x4_trs_icall_function_pointer",
        actual_function_pointer,
        MATRIX4X4_TRS_FUNCTION_POINTER,
        UNITY_PLAYER,
    )
    actual_name = data[
        MATRIX4X4_TRS_NAME_FILE_OFFSET : MATRIX4X4_TRS_NAME_FILE_OFFSET
        + len(MATRIX4X4_TRS_NAME)
    ].decode("ascii")
    require("matrix4x4_trs_icall_name", actual_name, MATRIX4X4_TRS_NAME, UNITY_PLAYER)
    require(
        "matrix4x4_trs_icall_name_terminator",
        data[MATRIX4X4_TRS_NAME_FILE_OFFSET + len(MATRIX4X4_TRS_NAME)],
        0,
        UNITY_PLAYER,
    )

    wrapper = data[
        MATRIX4X4_TRS_WRAPPER_FILE_OFFSET : MATRIX4X4_TRS_WRAPPER_FILE_OFFSET
        + MATRIX4X4_TRS_WRAPPER_SIZE
    ]
    require(
        "matrix4x4_trs_wrapper_size",
        len(wrapper),
        MATRIX4X4_TRS_WRAPPER_SIZE,
        UNITY_PLAYER,
    )
    wrapper_hash = hashlib.sha256(wrapper).hexdigest()
    require(
        "matrix4x4_trs_wrapper_body_sha256",
        wrapper_hash,
        MATRIX4X4_TRS_WRAPPER_BODY_SHA256,
        UNITY_PLAYER,
    )
    require(
        "matrix4x4_trs_wrapper_call_opcode",
        wrapper[0x17],
        0xE8,
        UNITY_PLAYER,
    )
    wrapper_call_target = MATRIX4X4_TRS_WRAPPER_VA + 0x17 + 5 + struct.unpack_from(
        "<i", wrapper, 0x18
    )[0]
    require(
        "matrix4x4_trs_wrapper_native_target",
        wrapper_call_target,
        MATRIX4X4_TRS_NATIVE_VA,
        UNITY_PLAYER,
    )

    body = data[
        MATRIX4X4_TRS_NATIVE_FILE_OFFSET : MATRIX4X4_TRS_NATIVE_FILE_OFFSET
        + MATRIX4X4_TRS_NATIVE_SIZE
    ]
    require(
        "matrix4x4_trs_native_body_size",
        len(body),
        MATRIX4X4_TRS_NATIVE_SIZE,
        UNITY_PLAYER,
    )
    body_hash = hashlib.sha256(body).hexdigest()
    require(
        "matrix4x4_trs_native_body_sha256",
        body_hash,
        MATRIX4X4_TRS_NATIVE_BODY_SHA256,
        UNITY_PLAYER,
    )
    require(
        "matrix4x4_trs_quaternion_helper_target",
        relative_call_target(body, MATRIX4X4_TRS_NATIVE_VA, MATRIX4X4_TRS_HELPER_CALL_OFFSET),
        MATRIX4X4_TRS_QUATERNION_HELPER_VA,
        UNITY_PLAYER,
    )
    helper = data[
        MATRIX4X4_TRS_QUATERNION_HELPER_FILE_OFFSET : MATRIX4X4_TRS_QUATERNION_HELPER_FILE_OFFSET
        + MATRIX4X4_TRS_QUATERNION_HELPER_SIZE
    ]
    require(
        "matrix4x4_trs_quaternion_helper_size",
        len(helper),
        MATRIX4X4_TRS_QUATERNION_HELPER_SIZE,
        UNITY_PLAYER,
    )
    helper_hash = hashlib.sha256(helper).hexdigest()
    require(
        "matrix4x4_trs_quaternion_helper_body_sha256",
        helper_hash,
        MATRIX4X4_TRS_QUATERNION_HELPER_BODY_SHA256,
        UNITY_PLAYER,
    )
    return {
        "icallIndex": index,
        "name": MATRIX4X4_TRS_NAME,
        "namePointer": f"0x{MATRIX4X4_TRS_NAME_POINTER:X}",
        "functionPointer": f"0x{MATRIX4X4_TRS_FUNCTION_POINTER:X}",
        "wrapperVirtualAddress": f"0x{MATRIX4X4_TRS_WRAPPER_VA:X}",
        "wrapperBodySizeBytes": MATRIX4X4_TRS_WRAPPER_SIZE,
        "wrapperBodySha256": wrapper_hash,
        "nativeVirtualAddress": f"0x{MATRIX4X4_TRS_NATIVE_VA:X}",
        "nativeFileOffset": f"0x{MATRIX4X4_TRS_NATIVE_FILE_OFFSET:X}",
        "nativeBodySizeBytes": MATRIX4X4_TRS_NATIVE_SIZE,
        "nativeBodySha256": body_hash,
        "quaternionToMatrixHelperVirtualAddress": f"0x{MATRIX4X4_TRS_QUATERNION_HELPER_VA:X}",
        "quaternionToMatrixHelperFileOffset": f"0x{MATRIX4X4_TRS_QUATERNION_HELPER_FILE_OFFSET:X}",
        "quaternionToMatrixHelperBodySizeBytes": MATRIX4X4_TRS_QUATERNION_HELPER_SIZE,
        "quaternionToMatrixHelperBodySha256": helper_hash,
        "arithmetic": (
            "native quaternion-to-column-major-matrix helper, then scalar float32 "
            "column scaling and raw position copies"
        ),
    }


def _relative_call_target_from_source(
    body: bytes, base_va: int, offset: int, source: Path
) -> int:
    require(f"native_call_{offset:04x}_opcode", body[offset], 0xE8, source)
    displacement = struct.unpack_from("<i", body, offset + 1)[0]
    return base_va + offset + 5 + displacement


def validate_quaternion_euler_native(
    managed_body: bytes,
    scale_helper_body: bytes,
    degrees_to_radians_bytes: bytes,
    unity_player_data: bytes,
) -> dict[str, Any]:
    """Pin the managed degrees-to-radians and UnityPlayer Euler boundary.

    The managed wrapper's dynamic call target is intentionally not resolved:
    IFix may replace the ``Internal_FromEulerRad_Injected`` slot at runtime.
    The static wrapper, exact float32 scale helper, UnityPlayer icall binding,
    native half-angle constant, and six sin/cos call sites are all validated so
    a future runtime capture can be joined without silently substituting a
    different Euler order.
    """

    require(
        "quaternion_euler_managed_body_size",
        len(managed_body),
        QUATERNION_EULER_MANAGED_SIZE,
        GAME_ASSEMBLY,
    )
    managed_hash = hashlib.sha256(managed_body).hexdigest()
    require(
        "quaternion_euler_managed_body_sha256",
        managed_hash,
        QUATERNION_EULER_MANAGED_BODY_SHA256,
        GAME_ASSEMBLY,
    )
    require(
        "quaternion_euler_managed_scale_call_target",
        _relative_call_target_from_source(
            managed_body,
            QUATERNION_EULER_MANAGED_VA,
            QUATERNION_EULER_MANAGED_SCALE_CALL_OFFSET,
            GAME_ASSEMBLY,
        ),
        QUATERNION_EULER_SCALE_HELPER_VA,
        GAME_ASSEMBLY,
    )
    require(
        "quaternion_euler_degrees_to_radians_bits",
        struct.unpack("<I", degrees_to_radians_bytes)[0],
        DEGREES_TO_RADIANS_BITS,
        GAME_ASSEMBLY,
    )
    require(
        "quaternion_euler_scale_helper_size",
        len(scale_helper_body),
        QUATERNION_EULER_SCALE_HELPER_SIZE,
        GAME_ASSEMBLY,
    )
    scale_helper_hash = hashlib.sha256(scale_helper_body).hexdigest()
    require(
        "quaternion_euler_scale_helper_body_sha256",
        scale_helper_hash,
        QUATERNION_EULER_SCALE_HELPER_BODY_SHA256,
        GAME_ASSEMBLY,
    )

    index = QUATERNION_EULER_ICALL_INDEX
    actual_name_pointer = struct.unpack_from(
        "<Q", unity_player_data, UNITY_ICALL_NAME_TABLE_OFFSET + index * 8
    )[0]
    actual_function_pointer = struct.unpack_from(
        "<Q", unity_player_data, UNITY_ICALL_FUNCTION_TABLE_OFFSET + index * 8
    )[0]
    require(
        "quaternion_euler_icall_name_pointer",
        actual_name_pointer,
        QUATERNION_EULER_NAME_POINTER,
        UNITY_PLAYER,
    )
    require(
        "quaternion_euler_icall_function_pointer",
        actual_function_pointer,
        QUATERNION_EULER_FUNCTION_POINTER,
        UNITY_PLAYER,
    )
    actual_name = unity_player_data[
        QUATERNION_EULER_NAME_FILE_OFFSET : QUATERNION_EULER_NAME_FILE_OFFSET
        + len(QUATERNION_EULER_NAME)
    ].decode("ascii")
    require(
        "quaternion_euler_icall_name",
        actual_name,
        QUATERNION_EULER_NAME,
        UNITY_PLAYER,
    )
    require(
        "quaternion_euler_icall_name_terminator",
        unity_player_data[QUATERNION_EULER_NAME_FILE_OFFSET + len(QUATERNION_EULER_NAME)],
        0,
        UNITY_PLAYER,
    )

    wrapper = unity_player_data[
        QUATERNION_EULER_STUB_FILE_OFFSET : QUATERNION_EULER_STUB_FILE_OFFSET
        + QUATERNION_EULER_STUB_SIZE
    ]
    require(
        "quaternion_euler_wrapper_size",
        len(wrapper),
        QUATERNION_EULER_STUB_SIZE,
        UNITY_PLAYER,
    )
    wrapper_hash = hashlib.sha256(wrapper).hexdigest()
    require(
        "quaternion_euler_wrapper_body_sha256",
        wrapper_hash,
        QUATERNION_EULER_STUB_BODY_SHA256,
        UNITY_PLAYER,
    )
    require(
        "quaternion_euler_wrapper_native_call_target",
        _relative_call_target_from_source(
            wrapper,
            QUATERNION_EULER_STUB_VA,
            0x17,
            UNITY_PLAYER,
        ),
        QUATERNION_EULER_NATIVE_VA,
        UNITY_PLAYER,
    )

    native = unity_player_data[
        QUATERNION_EULER_NATIVE_FILE_OFFSET : QUATERNION_EULER_NATIVE_FILE_OFFSET
        + QUATERNION_EULER_NATIVE_SIZE
    ]
    require(
        "quaternion_euler_native_body_size",
        len(native),
        QUATERNION_EULER_NATIVE_SIZE,
        UNITY_PLAYER,
    )
    native_hash = hashlib.sha256(native).hexdigest()
    require(
        "quaternion_euler_native_body_sha256",
        native_hash,
        QUATERNION_EULER_NATIVE_BODY_SHA256,
        UNITY_PLAYER,
    )
    math_calls = []
    for offset, target, description in QUATERNION_EULER_MATH_CALLS:
        actual_target = _relative_call_target_from_source(
            native, QUATERNION_EULER_NATIVE_VA, offset, UNITY_PLAYER
        )
        require(
            f"quaternion_euler_math_call_{offset:04x}_target",
            actual_target,
            target,
            UNITY_PLAYER,
        )
        math_calls.append(
            {
                "offset": f"0x{offset:02X}",
                "target": f"0x{target:X}",
                "operation": description,
            }
        )
    half_angle_bits = struct.unpack_from(
        "<I", unity_player_data, QUATERNION_EULER_HALF_ANGLE_FILE_OFFSET
    )[0]
    require(
        "quaternion_euler_half_angle_constant_bits",
        half_angle_bits,
        QUATERNION_EULER_HALF_ANGLE_BITS,
        UNITY_PLAYER,
    )
    return {
        "managedVirtualAddress": f"0x{QUATERNION_EULER_MANAGED_VA:X}",
        "managedFileOffset": f"0x{QUATERNION_EULER_MANAGED_FILE_OFFSET:X}",
        "managedBodySizeBytes": QUATERNION_EULER_MANAGED_SIZE,
        "managedBodySha256": managed_hash,
        "degreesToRadiansBits": f"0x{DEGREES_TO_RADIANS_BITS:08X}",
        "scaleHelperVirtualAddress": f"0x{QUATERNION_EULER_SCALE_HELPER_VA:X}",
        "scaleHelperFileOffset": f"0x{QUATERNION_EULER_SCALE_HELPER_FILE_OFFSET:X}",
        "scaleHelperBodySizeBytes": QUATERNION_EULER_SCALE_HELPER_SIZE,
        "scaleHelperBodySha256": scale_helper_hash,
        "icallIndex": index,
        "name": QUATERNION_EULER_NAME,
        "namePointer": f"0x{QUATERNION_EULER_NAME_POINTER:X}",
        "functionPointer": f"0x{QUATERNION_EULER_FUNCTION_POINTER:X}",
        "wrapperVirtualAddress": f"0x{QUATERNION_EULER_STUB_VA:X}",
        "wrapperBodySizeBytes": QUATERNION_EULER_STUB_SIZE,
        "wrapperBodySha256": wrapper_hash,
        "nativeVirtualAddress": f"0x{QUATERNION_EULER_NATIVE_VA:X}",
        "nativeFileOffset": f"0x{QUATERNION_EULER_NATIVE_FILE_OFFSET:X}",
        "nativeBodySizeBytes": QUATERNION_EULER_NATIVE_SIZE,
        "nativeBodySha256": native_hash,
        "halfAngleConstantBits": f"0x{half_angle_bits:08X}",
        "mathCalls": math_calls,
        "order": "native body receives radians, multiplies each component by 0.5f, then dispatches sin/cos pairs; enum/order result remains runtime-capture dependent",
        "runtimeBoundary": "managed wrapper's IFix Internal_FromEulerRad_Injected slot is not inferred from static bytes",
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


def validate_record0_discriminator_native(body: bytes) -> dict[str, Any]:
    spot = bytes.fromhex(
        "e8360f6b010fb6c003c00fafde660f6ec0498b85c80000000f5bc04863cb"
        "4883c1064803c9f30f1185dc000000"
    )
    point = bytes.fromhex(
        "e8c8096b010fb6c00fafde8d044501000000660f6ec0498b85c80000000f5bc0"
        "4863cb4883c1064803c9f30f11850c010000"
    )
    require(
        "record0_spot_discriminator_sequence",
        body[0x0DD9 : 0x0DD9 + len(spot)],
        spot,
        GAME_ASSEMBLY,
    )
    require(
        "record0_point_discriminator_sequence",
        body[0x1347 : 0x1347 + len(point)],
        point,
        GAME_ASSEMBLY,
    )
    return {
        "formula": "float(lightKind + 2 * shadowOnly)",
        "lightKind": {"Spot": 0, "PointOrLinearExtension": 1},
        "encodedValues": {
            "Spot": {"normal": 0.0, "shadowOnly": 2.0},
            "PointOrLinearExtension": {"normal": 1.0, "shadowOnly": 3.0},
        },
        "spotSequenceOffset": "0x0DD9",
        "pointSequenceOffset": "0x1347",
        "destination": "record0.w",
    }


def validate_point_shadow_face_pack_native(body: bytes) -> dict[str, Any]:
    """Pin the native Point/linear record2.w face-index packing contract.

    This deliberately reports the cache values as runtime inputs rather than
    manufacturing a byte-exact record.  The installed body proves the face
    order, cache lookup order, unavailable-slot sentinel, and byte packing.
    """

    face_calls = []
    for call_offset, face_index in POINT_SHADOW_FACE_CONSTRUCTOR_CALLS:
        require(
            f"point_shadow_face_{face_index}_constructor_target",
            call_target(body, call_offset),
            LIGHT_CASTER_CONSTRUCTOR_VA,
            GAME_ASSEMBLY,
        )
        face_calls.append(
            {
                "face": face_index,
                "constructorInstructionOffset": f"0x{call_offset:04X}",
                "target": f"0x{LIGHT_CASTER_CONSTRUCTOR_VA:X}",
            }
        )

    cache_calls = []
    for call_offset, face_index in POINT_SHADOW_CACHE_INDEX_CALLS:
        require(
            f"point_shadow_face_{face_index}_cache_index_target",
            call_target(body, call_offset),
            PUNCTUAL_SHADOW_CACHE_INDEX_VA,
            GAME_ASSEMBLY,
        )
        cache_calls.append(
            {
                "face": face_index,
                "cacheIndexInstructionOffset": f"0x{call_offset:04X}",
                "target": f"0x{PUNCTUAL_SHADOW_CACHE_INDEX_VA:X}",
            }
        )

    require(
        "point_shadow_unavailable_slot_fallback_sequence",
        body[0x124A : 0x124A + len(POINT_SHADOW_FALLBACK_SEQUENCE)],
        POINT_SHADOW_FALLBACK_SEQUENCE,
        GAME_ASSEMBLY,
    )
    require(
        "point_shadow_face_pack_sequence",
        body[0x1274 : 0x1274 + len(POINT_SHADOW_PACK_SEQUENCE)],
        POINT_SHADOW_PACK_SEQUENCE,
        GAME_ASSEMBLY,
    )
    return {
        "faceOrder": [row["face"] for row in face_calls],
        "faceConstructors": face_calls,
        "cacheIndexLookups": cache_calls,
        "unavailableCacheIndex": -1,
        "unavailableSentinelByte": 255,
        "packing": {
            "source": "six uint8 face indices",
            "byteOrder": "face0, face1, face2, face3, face4, face5",
            "record2W": "(face0 << 24) | (face1 << 16) | (face2 << 8) | face3",
            "record3X": "(face4 << 8) | face5",
            "nativeFallbackAndPackClosed": True,
        },
        "liveValues": {
            "closed": False,
            "requiredCapture": "six target-frame GetShadowCacheIndexForCaster return values",
        },
    }


def validate_point_shadow_cache_index_native(body: bytes) -> dict[str, Any]:
    """Pin the cache resolver that supplies each Point face index.

    The face pack audit proves how ``PrepareCPUData`` consumes the six return
    values.  This companion audit keeps the resolver's three native outcomes
    explicit: a dynamic caster returns ``40 + ordinal``, a static descriptor
    returns its cached slot field, and an unmatched caster returns ``-1``.
    The latter is the only value that the producer maps to the shader's 255
    unavailable sentinel.
    """

    require(
        "point_shadow_cache_index_body_sha256",
        hashlib.sha256(body).hexdigest(),
        "569216d2b51545da1b7867902e78ff36f9cbcf7f893db66c581481facd9ac622",
        GAME_ASSEMBLY,
    )
    for offset, target, name in (
        (0x26, 0x1831068E0, "patched_gate"),
        (0x3A, 0x189B4F6CC, "dynamic_count_initial"),
        (0x87, 0x189B52B7C, "light_caster_equality"),
        (0x97, 0x189B4F6CC, "dynamic_count_loop"),
        (0xBC, 0x187C86250, "static_caster_lookup"),
        (0xE8, 0x1808AE754, "static_cache_descriptor_lookup"),
        (0xF4, 0x189CDC2C0, "patched_wrapper_lookup"),
        (0xFE, 0x1800D8260, "null_state_fail_fast"),
    ):
        require(
            f"point_shadow_cache_index_{name}_target",
            cache_index_call_target(body, offset),
            target,
            GAME_ASSEMBLY,
        )
    require(
        "point_shadow_cache_index_dynamic_list_field",
        body[0x43 : 0x43 + 7],
        bytes.fromhex("488b8b80000000"),
        GAME_ASSEMBLY,
    )
    require(
        "point_shadow_cache_index_dynamic_return",
        body[0xCA : 0xCA + 3],
        bytes.fromhex("8d4728"),
        GAME_ASSEMBLY,
    )
    require(
        "point_shadow_cache_index_static_list_field",
        body[0xA0 : 0xA0 + 4],
        bytes.fromhex("488b4b38"),
        GAME_ASSEMBLY,
    )
    require(
        "point_shadow_cache_index_unmatched_return",
        body[0xC5 : 0xC5 + 3],
        bytes.fromhex("83c8ff"),
        GAME_ASSEMBLY,
    )
    require(
        "point_shadow_cache_index_static_slot_field",
        body[0xED : 0xED + 3],
        bytes.fromhex("8b400c"),
        GAME_ASSEMBLY,
    )
    return {
        "nativeVirtualAddress": f"0x{PUNCTUAL_SHADOW_CACHE_INDEX_VA:X}",
        "fileOffset": f"0x{PUNCTUAL_SHADOW_CACHE_INDEX_FILE_OFFSET:X}",
        "bodySize": len(body),
        "bodySha256": hashlib.sha256(body).hexdigest(),
        "dynamicCasterListField": "this + 0x80",
        "staticCasterListField": "this + 0x38",
        "dynamicMatchResult": "dynamicOrdinal + 40 (0x28)",
        "staticMatchResult": "PunctualLightCachedShadowDesc.shadowCacheSlotIndex (+0x0C)",
        "unmatchedResult": -1,
        "nullManagerOrCasterList": "fail-fast via 0x1800D8260",
        "resolverOutcomeClosed": True,
    }


def validate_point_record_transform_native(body: bytes) -> dict[str, Any]:
    """Pin native world-position and octahedral-forward producer calls."""

    calls = []
    for call_offset, target, method in POINT_RECORD_TRANSFORM_CALLS:
        require(
            f"point_record_transform_{method.rsplit('.', 1)[-1]}_target",
            call_target(body, call_offset),
            target,
            GAME_ASSEMBLY,
        )
        calls.append(
            {
                "instructionOffset": f"0x{call_offset:04X}",
                "target": f"0x{target:X}",
                "method": method,
            }
        )
    return {
        "calls": calls,
        "record1XYZ": {
            "producer": "VisibleLightExtensionMethods.GetPosition(VisibleLight)",
            "nativeSpace": "world-space",
            "deferredConsumerSpace": "camera-relative via worldPosition - cameraPosition",
            "targetFrameValues": "capture-only",
        },
        "record2XY": {
            "producer": "HGUtils.PackNormalOctRectEncode(VisibleLightExtensionMethods.GetForward(VisibleLight))",
            "encoding": "octahedral rectangle",
            "targetFrameValues": "capture-only",
        },
    }


def validate_visible_light_transform_helpers(
    forward: bytes,
    position: bytes,
    pack: bytes,
    one_constant: bytes,
    half_constant: bytes,
) -> dict[str, Any]:
    """Pin the helper bodies behind PrepareCPUData's transform producers."""
    for check, body, size, expected_hash in (
        (
            "visible_light_get_forward",
            forward,
            VISIBLE_LIGHT_GET_FORWARD_SIZE,
            EXPECTED_HASHES["visibleLightGetForwardBody"],
        ),
        (
            "visible_light_get_position",
            position,
            VISIBLE_LIGHT_GET_POSITION_SIZE,
            EXPECTED_HASHES["visibleLightGetPositionBody"],
        ),
        (
            "pack_normal_oct_rect_encode",
            pack,
            HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_SIZE,
            EXPECTED_HASHES["packNormalOctRectEncodeBody"],
        ),
    ):
        require(f"{check}_size", len(body), size, GAME_ASSEMBLY)
        require(
            f"{check}_body_sha256",
            hashlib.sha256(body).hexdigest(),
            expected_hash,
            GAME_ASSEMBLY,
        )

    require(
        "visible_light_get_forward_ifix_method_id",
        forward[0x1D:0x24],
        bytes.fromhex("33d2b97a070000"),
        GAME_ASSEMBLY,
    )
    require(
        "visible_light_get_position_ifix_method_id",
        position[0x1D:0x24],
        bytes.fromhex("33d2b97d070000"),
        GAME_ASSEMBLY,
    )
    require(
        "pack_normal_oct_rect_encode_ifix_method_id",
        pack[0x15:0x1A],
        bytes.fromhex("b97b070000"),
        GAME_ASSEMBLY,
    )
    require(
        "pack_normal_oct_rect_encode_one_constant_bits",
        struct.unpack("<I", one_constant)[0],
        0x3F800000,
        GAME_ASSEMBLY,
    )
    require(
        "pack_normal_oct_rect_encode_half_constant_bits",
        struct.unpack("<I", half_constant)[0],
        0x3F000000,
        GAME_ASSEMBLY,
    )
    for check, offset, target in (
        ("abs", PACK_NORMAL_ABS_CALL_OFFSET, PACK_NORMAL_ABS_VA),
        ("dot", PACK_NORMAL_DOT_CALL_OFFSET, PACK_NORMAL_DOT_VA),
        (
            "float3_multiply",
            PACK_NORMAL_FLOAT3_MULTIPLY_CALL_OFFSET,
            PACK_NORMAL_FLOAT3_MULTIPLY_VA,
        ),
        ("clamp", PACK_NORMAL_CLAMP_CALL_OFFSET, PACK_NORMAL_CLAMP_VA),
        ("copy_sign", PACK_NORMAL_COPY_SIGN_CALL_OFFSET, PACK_NORMAL_COPY_SIGN_VA),
    ):
        require(
            f"pack_normal_oct_rect_encode_{check}_target",
            relative_call_target(pack, HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_VA, offset),
            target,
            GAME_ASSEMBLY,
        )
    for name, body in (("forward", forward), ("position", position)):
        for offset, expected in (
            (0x2D, bytes.fromhex("0f104324")),
            (0x39, bytes.fromhex("0f104b34")),
            (0x47, bytes.fromhex("0f104344")),
            (0x54, bytes.fromhex("0f104b54")),
        ):
            require(
                f"visible_light_get_{name}_matrix_load_{offset:02x}",
                body[offset : offset + len(expected)],
                expected,
                GAME_ASSEMBLY,
            )
        require(
            f"visible_light_get_{name}_matrix_column",
            body[0x4B:0x4F],
            bytes.fromhex("458d4102" if name == "forward" else "458d4103"),
            GAME_ASSEMBLY,
        )
        require(
            f"visible_light_get_{name}_matrix_get_column_target",
            relative_call_target(
                body,
                VISIBLE_LIGHT_GET_FORWARD_VA
                if name == "forward"
                else VISIBLE_LIGHT_GET_POSITION_VA,
                0x62,
            ),
            MATRIX4X4_GET_COLUMN_VA,
            GAME_ASSEMBLY,
        )
        require(
            f"visible_light_get_{name}_vector4_implicit_target",
            relative_call_target(
                body,
                VISIBLE_LIGHT_GET_FORWARD_VA
                if name == "forward"
                else VISIBLE_LIGHT_GET_POSITION_VA,
                0x7A,
            ),
            VECTOR4_IMPLICIT_VECTOR3_VA,
            GAME_ASSEMBLY,
        )

    return {
        "getForward": {
            "method": "VisibleLightExtensionMethods.GetForward",
            "virtualAddress": f"0x{VISIBLE_LIGHT_GET_FORWARD_VA:X}",
            "fileOffset": f"0x{VISIBLE_LIGHT_GET_FORWARD_FILE_OFFSET:X}",
            "sizeBytes": VISIBLE_LIGHT_GET_FORWARD_SIZE,
            "bodySha256": hashlib.sha256(forward).hexdigest(),
            "ifixMethodId": f"0x{VISIBLE_LIGHT_GET_FORWARD_IFIX_METHOD_ID:X}",
            "sourceField": "VisibleLight.LocalToWorldMatrix",
            "sourceFieldOffset": f"0x{VISIBLE_LIGHT_LOCAL_TO_WORLD_MATRIX_FIELD_OFFSET:X}",
            "matrixColumn": 2,
            "extraction": "Matrix4x4.GetColumn(2) then Vector4.op_Implicit(Vector3), xyz; no normalization call in this body",
        },
        "getPosition": {
            "method": "VisibleLightExtensionMethods.GetPosition",
            "virtualAddress": f"0x{VISIBLE_LIGHT_GET_POSITION_VA:X}",
            "fileOffset": f"0x{VISIBLE_LIGHT_GET_POSITION_FILE_OFFSET:X}",
            "sizeBytes": VISIBLE_LIGHT_GET_POSITION_SIZE,
            "bodySha256": hashlib.sha256(position).hexdigest(),
            "ifixMethodId": f"0x{VISIBLE_LIGHT_GET_POSITION_IFIX_METHOD_ID:X}",
            "sourceField": "VisibleLight.LocalToWorldMatrix",
            "sourceFieldOffset": f"0x{VISIBLE_LIGHT_LOCAL_TO_WORLD_MATRIX_FIELD_OFFSET:X}",
            "matrixColumn": 3,
            "extraction": "Matrix4x4.GetColumn(3) then Vector4.op_Implicit(Vector3), xyz",
        },
        "packNormalOctRectEncode": {
            "method": "HGUtils.PackNormalOctRectEncode",
            "virtualAddress": f"0x{HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_VA:X}",
            "fileOffset": f"0x{HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_FILE_OFFSET:X}",
            "sizeBytes": HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_SIZE,
            "bodySha256": hashlib.sha256(pack).hexdigest(),
            "ifixMethodId": f"0x{HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_IFIX_METHOD_ID:X}",
            "input": "float3 direction",
            "output": "float2 octahedral rectangle encoding",
            "methodIndex": 288324,
            "token": "0x060014C0",
            "formula": "n1=n/(abs(n.x)+abs(n.y)+abs(n.z)); u=CopySign(clamp(0.5+0.5*(n1.y-n1.x),0,1),n1.z,true); v=n1.x+n1.y",
            "consumerDecodeFormula": "a=(0.5+0.5*v)-abs(u); b=v-a; c=abs(max((1-abs(a))-abs(b),0.00048828125)); normalize(float3(a,b,sign(u)*c))",
            "constants": {
                "oneBits": "0x3F800000",
                "halfBits": "0x3F000000",
            },
            "callTargets": {
                "abs": f"0x{PACK_NORMAL_ABS_VA:X}",
                "dot": f"0x{PACK_NORMAL_DOT_VA:X}",
                "float3Multiply": f"0x{PACK_NORMAL_FLOAT3_MULTIPLY_VA:X}",
                "clamp": f"0x{PACK_NORMAL_CLAMP_VA:X}",
                "copySign": f"0x{PACK_NORMAL_COPY_SIGN_VA:X}",
            },
        },
    }


def validate_shadow_caster_property_getters(
    is_dynamic_body: bytes,
    cast_static_body: bytes,
    cast_dynamic_body: bytes,
) -> dict[str, Any]:
    """Pin the native HGSharedLightData caster-property bit masks.

    These getters are the input consumed by GetShadowRenderType.  They read
    the packed caster-properties word through the Unity native bridge and
    expose bits 0, 1, and 2 as dynamic-caster, static-object, and
    dynamic-object flags respectively.  The selected room's serialized word
    is kept separate from the runtime cache result; it does not by itself
    establish six unavailable cache slots.
    """

    expected = {
        "isDynamicShadowCaster": (
            is_dynamic_body,
            HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_SIZE,
            "90ea0aae2d7409a8dc4fdc07cffdd57af60069b9e34fdbec0506ff946f615bfc",
            bytes.fromhex("4883ec2833d2e87d03000024014883c428c3"),
            0x01,
        ),
        "castStaticObjects": (
            cast_static_body,
            HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_SIZE,
            "512c74973a1f42fb0bdfcc029266400d3867d6b91cfb8abaec5453e45e9233e1",
            bytes.fromhex("4883ec2833d2e89d080000a8020f97c04883c428c3"),
            0x02,
        ),
        "castDynamicObjects": (
            cast_dynamic_body,
            HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_SIZE,
            "f71bcbf11d32cb9ce1d32c2959397575b0f3883f2593d730223c8e6c0f723558",
            bytes.fromhex("4883ec2833d2e8b5080000a8040f97c04883c428c3"),
            0x04,
        ),
    }
    result = {}
    for name, (body, size, expected_hash, sequence, mask) in expected.items():
        require(f"{name}_body_size", len(body), size, GAME_ASSEMBLY)
        require(
            f"{name}_body_sha256",
            hashlib.sha256(body).hexdigest(),
            expected_hash,
            GAME_ASSEMBLY,
        )
        require(f"{name}_mask_sequence", body, sequence, GAME_ASSEMBLY)
        result[name] = {
            "mask": f"0x{mask:02X}",
            "packedWord": "HGSharedLightData.m_CasterProperties",
            "nativeBodySha256": hashlib.sha256(body).hexdigest(),
        }
    return {
        "packedWord": "HGSharedLightData.m_CasterProperties",
        "fields": result,
        "propertyMasksClosed": True,
        "runtimeCacheValuesStillOpen": True,
    }


def validate_shadow_render_type_native(body: bytes) -> dict[str, Any]:
    """Pin GetShadowRenderType's native patch gate and default branches.

    Method 0x886 first asks WrappersManagerImpl.IsPatched.  When that gate is
    clear, the static request is a native branch (static=true, dynamic=false)
    and the dynamic request follows the three HGSharedLightData caster bits.
    When the gate is set, the method obtains patch 0x886 and delegates to the
    generated ILFix wrapper; that runtime table entry and its returned flags
    are intentionally not inferred from serialized light data.
    """

    require("shadow_render_type_size", len(body), GET_SHADOW_RENDER_TYPE_SIZE, GAME_ASSEMBLY)
    body_hash = hashlib.sha256(body).hexdigest()
    require(
        "shadow_render_type_body_sha256",
        body_hash,
        EXPECTED_HASHES["getShadowRenderTypeBody"],
        GAME_ASSEMBLY,
    )
    require(
        "shadow_render_type_patch_id_sequence",
        body[0x19:0x1E],
        bytes.fromhex("b986080000"),
        GAME_ASSEMBLY,
    )
    call_offsets = {
        0x24: (WRAPPERS_MANAGER_IS_PATCHED_VA, "WrappersManagerImpl.IsPatched"),
        0x46: (HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_VA, "HGSharedLightData.get_isDynamicShadowCaster"),
        0x56: (HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_VA, "HGSharedLightData.get_castStaticObjects"),
        0x6A: (HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_VA, "HGSharedLightData.get_castStaticObjects"),
        0x7A: (HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_VA, "HGSharedLightData.get_castDynamicObjects"),
        0x8A: (HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_VA, "HGSharedLightData.get_castStaticObjects"),
        0x9A: (HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_VA, "HGSharedLightData.get_castDynamicObjects"),
        0xBA: (WRAPPERS_MANAGER_GET_PATCH_VA, "WrappersManagerImpl.GetPatch"),
        0xC7: (FAIL_FAST_VA, "fail-fast"),
        0xED: (ILFIX_DYNAMIC_METHOD_WRAPPER_874_VA, "ILFixDynamicMethodWrapper.__Gen_Wrap_874"),
    }
    calls = []
    for offset, (target, name) in call_offsets.items():
        actual = shadow_render_type_call_target(body, offset)
        require(f"shadow_render_type_call_{offset:02x}_target", actual, target, GAME_ASSEMBLY)
        calls.append({"offset": f"0x{offset:02X}", "target": f"0x{target:X}", "method": name})

    short_branches = {
        0x3D: (0x74, 0xAB, "static_request_default"),
        0x54: (0x75, 0x6A, "dynamic_static_bit_true"),
        0x5D: (0x74, 0xA3, "dynamic_static_bit_false"),
        0x71: (0x74, 0x83, "dynamic_static_fallback"),
        0x81: (0x74, 0xAB, "dynamic_dynamic_bit_false"),
        0x91: (0x75, 0x5F, "dynamic_static_only_return"),
        0xA1: (0x74, 0x5F, "dynamic_dynamic_only_return"),
        0xA9: (0xEB, 0xF2, "dynamic_only_return"),
        0xB1: (0xEB, 0xF2, "static_only_return"),
        0xC5: (0x75, 0xCD, "patched_wrapper_call"),
    }
    branch_rows = []
    for offset, (opcode, target_offset, name) in short_branches.items():
        target = relative_short_branch_target(
            body, GET_SHADOW_RENDER_TYPE_VA, offset, opcode, GAME_ASSEMBLY,
            f"shadow_render_type_{name}",
        )
        expected_target = GET_SHADOW_RENDER_TYPE_VA + target_offset
        require(
            f"shadow_render_type_{name}_target",
            target,
            expected_target,
            GAME_ASSEMBLY,
        )
        branch_rows.append(
            {
                "offset": f"0x{offset:02X}",
                "target": f"0x{target:X}",
                "name": name,
            }
        )
    near_branches = {
        0x2B: (bytes.fromhex("0f85"), 0xB3, "patched_gate"),
        0x65: (bytes.fromhex("e9"), 0xF2, "dynamic_both_true_return"),
    }
    for offset, (opcode, target_offset, name) in near_branches.items():
        target = relative_near_branch_target(
            body, GET_SHADOW_RENDER_TYPE_VA, offset, opcode, GAME_ASSEMBLY,
            f"shadow_render_type_{name}",
        )
        expected_target = GET_SHADOW_RENDER_TYPE_VA + target_offset
        require(
            f"shadow_render_type_{name}_target",
            target,
            expected_target,
            GAME_ASSEMBLY,
        )
        branch_rows.append(
            {
                "offset": f"0x{offset:02X}",
                "target": f"0x{target:X}",
                "name": name,
            }
        )

    return {
        "method": "HG.Rendering.Runtime.HGPunctualLightShadowManagerV2.GetShadowRenderType",
        "methodIndex": 285595,
        "virtualAddress": f"0x{GET_SHADOW_RENDER_TYPE_VA:X}",
        "fileOffset": f"0x{GET_SHADOW_RENDER_TYPE_FILE_OFFSET:X}",
        "sizeBytes": GET_SHADOW_RENDER_TYPE_SIZE,
        "bodySha256": body_hash,
        "patchMethodId": f"0x{GET_SHADOW_RENDER_TYPE_PATCH_ID:X}",
        "resolvedCalls": calls,
        "resolvedBranches": branch_rows,
        "nativeDefault": {
            "staticRequest": {
                "condition": "IsPatched(0x886) == false and isDynamicRequest == false",
                "castStaticObjects": True,
                "castDynamicObjects": False,
                "branchTarget": f"0x{GET_SHADOW_RENDER_TYPE_VA + 0xAB:X}",
            },
            "dynamicRequest": {
                "condition": "IsPatched(0x886) == false and isDynamicRequest == true",
                "inputs": [
                    "HGSharedLightData.get_isDynamicShadowCaster (mask 0x01)",
                    "HGSharedLightData.get_castStaticObjects (mask 0x02)",
                    "HGSharedLightData.get_castDynamicObjects (mask 0x04)",
                ],
                "branchLogicClosed": True,
            },
        },
        "runtimePatchedPath": {
            "condition": "IsPatched(0x886) == true",
            "patchLookup": f"0x{WRAPPERS_MANAGER_GET_PATCH_VA:X}",
            "wrapper": f"0x{ILFIX_DYNAMIC_METHOD_WRAPPER_874_VA:X}",
            "missingPatchFailFast": f"0x{FAIL_FAST_VA:X}",
            "runtimeWrapperTableEntryStillOpen": True,
            "returnedFlagsStillOpen": True,
        },
        "nativeDefaultStaticResultClosed": True,
        "runtimePatchedResultStillOpen": True,
    }


def validate_renderer_config_native(body: bytes) -> dict[str, Any]:
    """Pin GetRendererConfig's shadow-flag projection and patch gate."""

    require("renderer_config_size", len(body), GET_RENDERER_CONFIG_SIZE, GAME_ASSEMBLY)
    body_hash = hashlib.sha256(body).hexdigest()
    require(
        "renderer_config_body_sha256",
        body_hash,
        EXPECTED_HASHES["getRendererConfigBody"],
        GAME_ASSEMBLY,
    )
    require(
        "renderer_config_patch_id_sequence",
        body[0x20:0x25],
        bytes.fromhex("b987080000"),
        GAME_ASSEMBLY,
    )
    call_offsets = {
        0x28: (WRAPPERS_MANAGER_IS_PATCHED_VA, "WrappersManagerImpl.IsPatched"),
        0x4F: (GET_SHADOW_RENDER_TYPE_VA, "HGPunctualLightShadowManagerV2.GetShadowRenderType"),
        0x7F: (WRAPPERS_MANAGER_GET_PATCH_VA, "WrappersManagerImpl.GetPatch"),
        0x89: (FAIL_FAST_VA, "fail-fast"),
        0xA1: (ILFIX_DYNAMIC_METHOD_WRAPPER_875_VA, "ILFixDynamicMethodWrapper.__Gen_Wrap_875"),
    }
    calls = []
    for offset, (target, name) in call_offsets.items():
        actual = renderer_config_call_target(body, offset)
        require(f"renderer_config_call_{offset:02x}_target", actual, target, GAME_ASSEMBLY)
        calls.append({"offset": f"0x{offset:02X}", "target": f"0x{target:X}", "method": name})

    branches = []
    for offset, (opcode, target_offset, name) in {
        0x2F: (0x75, 0x78, "patched_gate"),
        0x87: (0x75, 0x8F, "patched_wrapper_call"),
    }.items():
        target = relative_short_branch_target(
            body,
            GET_RENDERER_CONFIG_VA,
            offset,
            opcode,
            GAME_ASSEMBLY,
            f"renderer_config_{name}",
        )
        expected_target = GET_RENDERER_CONFIG_VA + target_offset
        require(
            f"renderer_config_{name}_target",
            target,
            expected_target,
            GAME_ASSEMBLY,
        )
        branches.append(
            {"offset": f"0x{offset:02X}", "target": f"0x{target:X}", "name": name}
        )
    require(
        "renderer_config_native_formula_sequence",
        body[0x54:0x78],
        bytes.fromhex(
            "8a442430f6d81bc0250010000005004800008a4c2431"
            "f6d91bd281e2002000000bc2eb2e"
        ),
        GAME_ASSEMBLY,
    )
    require(
        "renderer_config_default_base_flags",
        int.from_bytes(body[0x62:0x66], "little"),
        0x4800,
        GAME_ASSEMBLY,
    )
    return {
        "method": "HG.Rendering.Runtime.HGPunctualLightShadowManagerV2.GetRendererConfig",
        "methodIndex": 285596,
        "virtualAddress": f"0x{GET_RENDERER_CONFIG_VA:X}",
        "fileOffset": f"0x{GET_RENDERER_CONFIG_FILE_OFFSET:X}",
        "sizeBytes": GET_RENDERER_CONFIG_SIZE,
        "bodySha256": body_hash,
        "patchMethodId": f"0x{GET_RENDERER_CONFIG_PATCH_ID:X}",
        "resolvedCalls": calls,
        "resolvedBranches": branches,
        "nativeDefault": {
            "condition": "IsPatched(0x887) == false",
            "baseFlags": "0x4800",
            "castStaticPointer": "rsp+0x30 (r9 argument to GetShadowRenderType)",
            "castDynamicPointer": "rsp+0x31 (fifth argument to GetShadowRenderType)",
            "formula": "0x4800 | (castStaticObjects ? 0x1000 : 0) | (castDynamicObjects ? 0x2000 : 0)",
            "sourceFlagsClosed": True,
        },
        "runtimePatchedPath": {
            "condition": "IsPatched(0x887) == true",
            "patchLookup": f"0x{WRAPPERS_MANAGER_GET_PATCH_VA:X}",
            "wrapper": f"0x{ILFIX_DYNAMIC_METHOD_WRAPPER_875_VA:X}",
            "missingPatchFailFast": f"0x{FAIL_FAST_VA:X}",
            "runtimeWrapperTableEntryStillOpen": True,
            "returnedFlagsStillOpen": True,
        },
        "nativeDefaultFlagsClosed": True,
        "runtimePatchedResultStillOpen": True,
    }


def validate_ecs_render_flags_native(body: bytes) -> dict[str, Any]:
    """Pin GetECSRenderFlags' default flag writes and HDPLS augmentation."""

    require("ecs_render_flags_size", len(body), GET_ECS_RENDER_FLAGS_SIZE, GAME_ASSEMBLY)
    body_hash = hashlib.sha256(body).hexdigest()
    require(
        "ecs_render_flags_body_sha256",
        body_hash,
        EXPECTED_HASHES["getEcsRenderFlagsBody"],
        GAME_ASSEMBLY,
    )
    require(
        "ecs_render_flags_patch_id_sequence",
        body[0x25:0x2A],
        bytes.fromhex("bb88080000"),
        GAME_ASSEMBLY,
    )
    call_offsets = {
        0x38: (WRAPPERS_MANAGER_IS_PATCHED_VA, "WrappersManagerImpl.IsPatched"),
        0x81: (GET_SHADOW_RENDER_TYPE_VA, "HGPunctualLightShadowManagerV2.GetShadowRenderType"),
        0xC1: (HG_SHARED_LIGHT_ENABLE_HD_CHARACTER_SHADOW_VA, "HGSharedLightData.get_enableHDCharacterShadow_Injected"),
        0xD5: (0x1800036A0, "helper"),
        0xDA: (HG_HDPLS_GET_ACTIVE_VA, "HGHDPLSCharacterShadowManager.get_isActive"),
        0xE9: (HG_SHARED_LIGHT_EXTENSION_GET_ENTITY_VA, "HGSharedLightDataExtension.GetEntity"),
        0xF8: (0x1800036A0, "helper"),
        0x102: (HG_HDPLS_IS_LIGHT_VA, "HGHDPLSCharacterShadowManager.IsHDPLSLight"),
        0x115: (WRAPPERS_MANAGER_GET_PATCH_VA, "WrappersManagerImpl.GetPatch"),
        0x122: (FAIL_FAST_VA, "fail-fast"),
        0x158: (ILFIX_DYNAMIC_METHOD_WRAPPER_876_VA, "ILFixDynamicMethodWrapper.__Gen_Wrap_876"),
    }
    calls = []
    for offset, (target, name) in call_offsets.items():
        actual = ecs_render_flags_call_target(body, offset)
        require(f"ecs_render_flags_call_{offset:02x}_target", actual, target, GAME_ASSEMBLY)
        calls.append({"offset": f"0x{offset:02X}", "target": f"0x{target:X}", "method": name})

    require(
        "ecs_render_flags_default_write_sequence",
        body[0x51:0x78],
        bytes.fromhex(
            "b802000008488b5d60458ac7488364242800498bcc488b5538"
            "89068907b8000008024189068903"
        ),
        GAME_ASSEMBLY,
    )
    require(
        "ecs_render_flags_shadow_call_setup",
        body[0x78:0x81],
        bytes.fromhex("488d45f04889442420"),
        GAME_ASSEMBLY,
    )
    require(
        "ecs_render_flags_caster_projection_sequence",
        body[0x98:0xBB],
        bytes.fromhex(
            "84d2741284c9750c44090644090745090e44090b84d20f94c084c8740644090744090b"
        ),
        GAME_ASSEMBLY,
    )
    require(
        "ecs_render_flags_hdpls_bit_sequence",
        body[0xF8:0x111],
        bytes.fromhex("e85fb24bf633d2488bcbe8ede7ffff84c074520fba2f1ceb4c"),
        GAME_ASSEMBLY,
    )
    branches = []
    for offset, (opcode, target_offset, name) in {
        0x9A: (0x74, 0xAE, "static_false"),
        0x9E: (0x75, 0xAC, "dynamic_true"),
        0xB3: (0x74, 0xBB, "caster_projection_done"),
        0xE1: (0x74, 0x15D, "hd_character_shadow_disabled"),
        0x109: (0x74, 0x15D, "hdpls_light_false"),
        0x120: (0x75, 0x128, "patched_wrapper_call"),
    }.items():
        target = relative_short_branch_target(
            body,
            GET_ECS_RENDER_FLAGS_VA,
            offset,
            opcode,
            GAME_ASSEMBLY,
            f"ecs_render_flags_{name}",
        )
        expected_target = GET_ECS_RENDER_FLAGS_VA + target_offset
        require(
            f"ecs_render_flags_{name}_target",
            target,
            expected_target,
            GAME_ASSEMBLY,
        )
        branches.append(
            {"offset": f"0x{offset:02X}", "target": f"0x{target:X}", "name": name}
        )
    for offset, (opcode, target_offset, name) in {
        0x3F: (bytes.fromhex("0f85"), 0x111, "patched_gate"),
        0xC8: (bytes.fromhex("0f84"), 0x15D, "hd_character_shadow_inactive"),
    }.items():
        target = relative_near_branch_target(
            body,
            GET_ECS_RENDER_FLAGS_VA,
            offset,
            opcode,
            GAME_ASSEMBLY,
            f"ecs_render_flags_{name}",
        )
        expected_target = GET_ECS_RENDER_FLAGS_VA + target_offset
        require(
            f"ecs_render_flags_{name}_target",
            target,
            expected_target,
            GAME_ASSEMBLY,
        )
        branches.append(
            {"offset": f"0x{offset:02X}", "target": f"0x{target:X}", "name": name}
        )
    return {
        "method": "HG.Rendering.Runtime.HGPunctualLightShadowManagerV2.GetECSRenderFlags",
        "methodIndex": 285597,
        "virtualAddress": f"0x{GET_ECS_RENDER_FLAGS_VA:X}",
        "fileOffset": f"0x{GET_ECS_RENDER_FLAGS_FILE_OFFSET:X}",
        "sizeBytes": GET_ECS_RENDER_FLAGS_SIZE,
        "bodySha256": body_hash,
        "patchMethodId": f"0x{GET_ECS_RENDER_FLAGS_PATCH_ID:X}",
        "resolvedCalls": calls,
        "resolvedBranches": branches,
        "nativeDefault": {
            "condition": "IsPatched(0x888) == false",
            "argumentPointers": {
                "objectFlags": "r9 -> [rsi]",
                "objectFlagsMask": "fifth argument -> [rdi]",
                "renderFlags": "sixth argument -> [r14]",
                "renderFlagsMask": "seventh argument -> [rbx]",
            },
            "baseValues": {
                "objectFlags": "0x08000002",
                "objectFlagsMask": "0x08000002",
                "renderFlags": "0x02080000",
                "renderFlagsMask": "0x02080000",
            },
            "shadowRenderTypeInputs": {
                "castStaticPointer": "rbp-0x0F (r9)",
                "castDynamicPointer": "rbp-0x10 (fifth argument)",
            },
            "exclusiveCasterProjection": {
                "condition": "castStaticObjects XOR castDynamicObjects",
                "objectFlagsAndMaskOr": "0x04000000",
                "renderFlagsAndMaskOr": "0x01000000",
            },
            "hdCharacterShadow": {
                "condition": "enableHDCharacterShadow && HGHDPLSCharacterShadowManager.isActive && IsHDPLSLight(entity)",
                "destination": "objectFlagsMask",
                "bit": 28,
                "orMask": "0x10000000",
            },
            "sourceFlagsClosed": True,
        },
        "runtimePatchedPath": {
            "condition": "IsPatched(0x888) == true",
            "patchLookup": f"0x{WRAPPERS_MANAGER_GET_PATCH_VA:X}",
            "wrapper": f"0x{ILFIX_DYNAMIC_METHOD_WRAPPER_876_VA:X}",
            "missingPatchFailFast": f"0x{FAIL_FAST_VA:X}",
            "runtimeWrapperTableEntryStillOpen": True,
            "returnedFlagsStillOpen": True,
        },
        "nativeDefaultFlagsClosed": True,
        "runtimePatchedResultStillOpen": True,
    }


def validate_authored_room_transform_candidates(
    cull_view: dict[str, Any],
    hierarchy: dict[str, Any],
    rotatehouse: dict[str, Any],
) -> dict[str, Any]:
    """Recompose the authored room transforms used by the cull-view audit."""

    parent = rotatehouse["m_Transform"]
    parent_position = [
        f32(float(parent["m_LocalPosition"][key])) for key in ("X", "Y", "Z")
    ]
    parent_rotation = [
        f32(float(parent["m_LocalRotation"][key]))
        for key in ("X", "Y", "Z", "W")
    ]
    parent_scale = [
        f32(float(parent["m_LocalScale"][key])) for key in ("X", "Y", "Z")
    ]
    require("rotatehouse_local_scale", parent_scale, [1.0, 1.0, 1.0], ROTATEHOUSE)
    hierarchy_rows = {
        row["name"]: row
        for row in hierarchy["lights"]
        if row["rarityGroup"] == "SceneLight6Rarity"
    }
    cull_rows = {
        row["name"]: row
        for row in cull_view["authoredRoomRowsInStrictNativeDistanceOrder"]
    }
    require(
        "authored_room_transform_candidate_membership",
        set(hierarchy_rows),
        set(cull_rows),
        GACHA_CULL_VIEW_AUDIT,
    )

    candidates = []
    candidate_order = [
        row["name"]
        for row in cull_view["authoredRoomRowsInStrictNativeDistanceOrder"]
    ]
    require("authored_room_transform_candidate_order_count", len(candidate_order), 12, GACHA_CULL_VIEW_AUDIT)
    for name in candidate_order:
        hierarchy_row = hierarchy_rows[name]
        cull_row = cull_rows[name]
        local_position = [
            f32(float(hierarchy_row["localPosition"][key]))
            for key in ("X", "Y", "Z")
        ]
        local_rotation = [
            f32(float(hierarchy_row["localRotation"][key]))
            for key in ("X", "Y", "Z", "W")
        ]
        rotated_position = quaternion_rotate(parent_rotation, local_position)
        world_position = [
            f32(parent_position[index] + rotated_position[index]) for index in range(3)
        ]
        expected_position = [
            float(item["value"]) for item in cull_row["worldPosition"]
        ]
        require(
            f"{name}_authored_world_position_bits",
            [float32_bits(value) for value in world_position],
            [float32_bits(value) for value in expected_position],
            GACHA_CULL_VIEW_AUDIT,
        )
        world_rotation = quaternion_multiply(parent_rotation, local_rotation)
        world_forward = quaternion_rotate(world_rotation, [0.0, 0.0, 1.0])
        packed_forward = pack_normal_oct_rect_encode_candidate(world_forward)
        candidates.append(
            {
                "name": name,
                "lightPathId": int(cull_row["lightPathId"]),
                "source": cull_row["source"],
                "localPosition": {
                    "values": local_position,
                    "bits": [f"0x{float32_bits(value):08X}" for value in local_position],
                },
                "localRotation": {
                    "values": local_rotation,
                    "bits": [f"0x{float32_bits(value):08X}" for value in local_rotation],
                },
                "worldPosition": {
                    "values": world_position,
                    "bits": [f"0x{float32_bits(value):08X}" for value in world_position],
                },
                "worldForward": {
                    "values": world_forward,
                    "bits": [f"0x{float32_bits(value):08X}" for value in world_forward],
                },
                "record2XYCandidate": {
                    "values": packed_forward,
                    "bits": [
                        f"0x{float32_bits(value):08X}" for value in packed_forward
                    ],
                },
            }
        )
    return {
        "scope": "authored SceneLight6Rarity room hierarchy at pinned rotatehouse transform",
        "sourceSpace": "world-space",
        "positionProducerInput": "VisibleLight.LocalToWorldMatrix column 3",
        "forwardProducerInput": "VisibleLight.LocalToWorldMatrix column 2",
        "record2XYFormula": "PackNormalOctRectEncode(worldForward) using the hash-pinned unpatched body",
        "record2XYCandidateClosed": True,
        "parentTransform": {
            "position": parent_position,
            "rotation": parent_rotation,
            "scale": parent_scale,
        },
        "count": len(candidates),
        "rows": candidates,
        "targetFrameValues": "capture-only; these are authored static candidates, not a retail LightCullResult capture",
    }


def validate_static_record_terms_native(
    body: bytes,
    range_getter_body: bytes,
    scalar_cos_body: bytes,
    one_bytes: bytes,
    angle_divisor_bytes: bytes,
    angle_pi_bytes: bytes,
) -> dict[str, Any]:
    require(
        "visible_light_get_range_size",
        len(range_getter_body),
        VISIBLE_LIGHT_GET_RANGE_SIZE,
        GAME_ASSEMBLY,
    )
    range_hash = hashlib.sha256(range_getter_body).hexdigest()
    require(
        "visible_light_get_range_body_sha256",
        range_hash,
        EXPECTED_HASHES["visibleLightGetRangeBody"],
        GAME_ASSEMBLY,
    )
    require(
        "visible_light_get_range_field_offset",
        range_getter_body,
        bytes.fromhex("6690f30f104168c3"),
        GAME_ASSEMBLY,
    )
    require(
        "prepare_cpu_data_one_constant_load",
        body[0x0E3:0x0EC],
        bytes.fromhex("f3440f103558c9c401"),
        GAME_ASSEMBLY,
    )
    require(
        "prepare_cpu_data_one_constant_bits",
        struct.unpack("<I", one_bytes)[0],
        0x3F800000,
        GAME_ASSEMBLY,
    )
    require(
        "record1_inverse_range_sequence",
        body[0x8A5:0x8CA],
        bytes.fromhex(
            "410f28ce89742420f30f5e8da80400004d8bcc4c8d8540040000498bd5"
            "f30f118d8c000000"
        ),
        GAME_ASSEMBLY,
    )

    require("scalar_cos_size", len(scalar_cos_body), SCALAR_COS_SIZE, GAME_ASSEMBLY)
    cos_hash = hashlib.sha256(scalar_cos_body).hexdigest()
    require(
        "scalar_cos_body_sha256",
        cos_hash,
        EXPECTED_HASHES["scalarCosBody"],
        GAME_ASSEMBLY,
    )
    require(
        "spot_angle_divisor_bits",
        struct.unpack("<I", angle_divisor_bytes)[0],
        SPOT_ANGLE_DIVISOR_BITS,
        GAME_ASSEMBLY,
    )
    require(
        "spot_angle_pi_bits",
        struct.unpack("<I", angle_pi_bytes)[0],
        SPOT_ANGLE_PI_BITS,
        GAME_ASSEMBLY,
    )
    require(
        "spot_inner_angle_scale_sequence",
        body[0xCFD:0xD0D],
        bytes.fromhex("f30f5e05ebbdc401f30f5905b7c3c401"),
        GAME_ASSEMBLY,
    )
    require(
        "spot_outer_angle_scale_sequence",
        body[0xD21:0xD31],
        bytes.fromhex("f30f5e05c7bdc401f30f590593c3c401"),
        GAME_ASSEMBLY,
    )
    require(
        "spot_record2_cosine_terms",
        (
            body[0xE25:0xE2A],
            body[0xE4F:0xE58],
            body[0xEA2:0xEAA],
            body[0xEB7:0xEBF],
        ),
        (
            bytes.fromhex("f3410f5cf0"),
            bytes.fromhex("f3440f1185e8000000"),
            bytes.fromhex("410f28c6f30f5ec6"),
            bytes.fromhex("f30f1185ec000000"),
        ),
        GAME_ASSEMBLY,
    )
    require(
        "point_record2_length_term",
        (
            body[0x140C:0x1414],
            body[0x141C:0x1423],
        ),
        (
            bytes.fromhex("f30f118518010000"),
            bytes.fromhex("0f108510010000"),
        ),
        GAME_ASSEMBLY,
    )
    return {
        "visibleLightRange": {
            "method": "UnityEngine.Rendering.VisibleLight.get_range",
            "methodIndex": 408154,
            "virtualAddress": f"0x{VISIBLE_LIGHT_GET_RANGE_VA:X}",
            "fileOffset": f"0x{VISIBLE_LIGHT_GET_RANGE_FILE_OFFSET:X}",
            "bodySha256": range_hash,
            "fieldOffset": "0x68",
            "record1WFormula": "1.0f / VisibleLight.range",
        },
        "spotRecord2": {
            "scalarCosVirtualAddress": f"0x{SCALAR_COS_VA:X}",
            "scalarCosBodySha256": cos_hash,
            "halfAngleRadiansFormula": "float32(degrees / 360.0f * piFloat32)",
            "record2ZFormula": "cos(outer half-angle)",
            "record2WFormula": "1.0f / (cos(inner half-angle) - cos(outer half-angle))",
            "selectedGoldenBits": {
                key: f"0x{bits:08X}" for key, bits in EXPECTED_SPOT_RECORD2_BITS.items()
            },
        },
        "pointRecord2": {
            "record2ZFormula": "HGSharedLightData.length",
            "record2WBoundary": "packed point-shadow face indices; not closed here",
        },
    }


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
        "record0Discriminator": validate_record0_discriminator_native(body),
        "pointShadowFacePack": validate_point_shadow_face_pack_native(body),
        "pointRecordTransform": validate_point_record_transform_native(body),
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


def f32_mul(left: float, right: float) -> float:
    return f32(left * right)


def f32_add(left: float, right: float) -> float:
    return f32(left + right)


def f32_sub(left: float, right: float) -> float:
    return f32(left - right)


def f32_div(left: float, right: float) -> float:
    return f32(left / right)


def unity_quaternion_euler_degrees_to_radians_candidate(
    degrees: list[float],
) -> list[float]:
    """Replay GameAssembly's exact float32 degree-to-radian helper."""

    scale = float32_from_bits(DEGREES_TO_RADIANS_BITS)
    return [f32_mul(f32(value), scale) for value in degrees]


def xor_sign_bit(value: float) -> float:
    """Mirror the native ``xorps`` against UnityPlayer's -0 sign mask."""

    return float32_from_bits(float32_bits(value) ^ MATRIX4X4_INVERSE_SIGN_MASK_BITS)


def unity_matrix4x4_inverse_affine_candidate(
    matrix_rows: list[list[float]],
) -> tuple[list[list[float]], bool, float]:
    """Replay UnityPlayer ``Matrix4x4::Inverse`` for an affine matrix.

    Unity's Matrix4x4 fields are laid out column-major (m00, m10, m20, ...),
    while the b31 packer later gathers those fields back into logical rows.
    The native body uses scalar ``mulss/addss/subss/divss`` and explicit sign
    xor operations; keeping each intermediate in float32 preserves the
    installed implementation's rounding and signed-zero behavior.
    """

    fields = [
        f32(matrix_rows[row][column])
        for column in range(4)
        for row in range(4)
    ]
    a = fields[0]   # m00
    b = fields[1]   # m10
    c = fields[2]   # m20
    d = fields[4]   # m01
    e = fields[5]   # m11
    f_value = fields[6]  # m21
    g = fields[8]   # m02
    h = fields[9]   # m12
    i = fields[10]  # m22
    tx = fields[12]  # m03
    ty = fields[13]  # m13
    tz = fields[14]  # m23

    determinant = f32_mul(f32_mul(e, a), i)
    determinant = f32_add(determinant, f32(0.0))
    determinant = f32_add(
        determinant,
        f32_mul(f32_mul(f_value, b), g),
    )
    determinant = f32_add(
        determinant,
        f32_mul(f32_mul(d, c), h),
    )
    determinant = f32_sub(
        determinant,
        f32_mul(f32_mul(e, c), g),
    )
    determinant = f32_sub(
        determinant,
        f32_mul(f32_mul(b, d), i),
    )
    determinant = f32_sub(
        determinant,
        f32_mul(f32_mul(f_value, a), h),
    )

    # Native code compares the float32 determinant square after promoting it
    # to double.  The selected authored TRS matrices are comfortably above
    # this fail-to-zero threshold, but model the failure path as well.
    determinant_square = f32_mul(determinant, determinant)
    if float(determinant_square) < MATRIX4X4_INVERSE_DETERMINANT_THRESHOLD:
        return (
            [[0.0, 0.0, 0.0, 0.0] for _ in range(3)]
            + [[0.0, 0.0, 0.0, 0.0]],
            False,
            determinant,
        )

    inverse_determinant = f32_div(f32(1.0), determinant)

    def cofactor(value: float, flip_sign: bool = False) -> float:
        if flip_sign:
            value = xor_sign_bit(value)
        return f32_mul(value, inverse_determinant)

    # These are the nine stores at native offsets 0x00..0x28.  The names are
    # cofactor positions; the resulting list is still Matrix4x4 field order.
    c00 = cofactor(f32_sub(f32_mul(i, e), f32_mul(h, f_value)))
    c01 = cofactor(
        f32_sub(f32_mul(i, b), f32_mul(h, c)),
        True,
    )
    c02 = cofactor(f32_sub(f32_mul(f_value, b), f32_mul(e, c)))
    c10 = cofactor(
        f32_sub(f32_mul(i, d), f32_mul(g, f_value)),
        True,
    )
    c11 = cofactor(f32_sub(f32_mul(i, a), f32_mul(g, c)))
    c12 = cofactor(
        f32_sub(f32_mul(f_value, a), f32_mul(d, c)),
        True,
    )
    c20 = cofactor(f32_sub(f32_mul(h, d), f32_mul(g, e)))
    c21 = cofactor(
        f32_sub(f32_mul(h, a), f32_mul(g, b)),
        True,
    )
    c22 = cofactor(f32_sub(f32_mul(e, a), f32_mul(d, b)))

    fields_out = [
        c00, c01, c02, 0.0,
        c10, c11, c12, 0.0,
        c20, c21, c22, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]

    def translated(first: float, second: float, third: float) -> float:
        value = f32_add(f32_mul(first, tx), f32_mul(second, ty))
        value = f32_add(value, f32_mul(third, tz))
        return xor_sign_bit(value)

    fields_out[12] = translated(c00, c10, c20)
    fields_out[13] = translated(c01, c11, c21)
    fields_out[14] = translated(c02, c12, c22)
    rows = [
        [fields_out[column * 4 + row] for column in range(4)]
        for row in range(4)
    ]
    return rows, True, determinant


def unity_quaternion_to_matrix_candidate(
    quaternion: list[float],
) -> list[list[float]]:
    """Replay UnityPlayer's scalar quaternion-to-Matrix4x4 helper.

    The helper at ``0x18056B8A0`` receives quaternion ``(x, y, z, w)`` and
    writes Unity's column-major fields.  Each intermediate is rounded to
    float32 in the same order as the native ``addss/mulss/subss`` sequence.
    """

    x, y, z, w = (f32(value) for value in quaternion)
    one = f32(1.0)
    doubled_z = f32_add(z, z)
    doubled_y = f32_add(y, y)
    doubled_x = f32_add(x, x)
    doubled_z_z = f32_mul(doubled_z, z)
    doubled_z_w = f32_mul(doubled_z, w)
    doubled_y_y = f32_mul(doubled_y, y)
    doubled_y_w = f32_mul(doubled_y, w)
    doubled_x_x = f32_mul(doubled_x, x)
    doubled_x_w = f32_mul(doubled_x, w)
    doubled_xy = f32_mul(doubled_y, x)
    doubled_xz = f32_mul(doubled_z, x)
    doubled_yz = f32_mul(doubled_z, y)

    # Keep the native column-major field order (m00, m10, m20, ...).
    fields = [
        f32_sub(one, f32_add(doubled_z_z, doubled_y_y)),
        f32_add(doubled_z_w, doubled_xy),
        f32_sub(doubled_xz, doubled_y_w),
        f32(0.0),
        f32_sub(doubled_xy, doubled_z_w),
        f32_sub(one, f32_add(doubled_z_z, doubled_x_x)),
        f32_add(doubled_yz, doubled_x_w),
        f32(0.0),
        f32_add(doubled_xz, doubled_y_w),
        f32_sub(doubled_yz, doubled_x_w),
        f32_sub(one, f32_add(doubled_y_y, doubled_x_x)),
        f32(0.0),
        f32(0.0),
        f32(0.0),
        f32(0.0),
        one,
    ]
    return [
        [fields[column * 4 + row] for column in range(4)]
        for row in range(4)
    ]


def unity_matrix4x4_trs_candidate(
    quaternion: list[float],
    position: list[float],
    scale: list[float],
) -> list[list[float]]:
    """Replay UnityPlayer ``Matrix4x4.TRS`` after its quaternion helper."""

    fields = [
        f32(value)
        for column in zip(*unity_quaternion_to_matrix_candidate(quaternion))
        for value in column
    ]
    # Native TRS multiplies each Matrix4x4 column by one scale component.
    for column, scale_value in enumerate(scale):
        scale_f32 = f32(scale_value)
        base = column * 4
        for row in range(3):
            fields[base + row] = f32_mul(fields[base + row], scale_f32)
    fields[12:15] = [f32(value) for value in position]
    return [
        [fields[column * 4 + row] for column in range(4)]
        for row in range(4)
    ]


def recovered_y_rotation_inverse_rows(
    row: dict[str, Any],
) -> tuple[list[list[float]], list[list[float]], float]:
    """Model selected rows' Y-only TRS and replay UnityPlayer inverse."""
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

    radians = unity_quaternion_euler_degrees_to_radians_candidate(
        [float(orientation["x"]), float(orientation["y"]), float(orientation["z"])]
    )[1]
    half_angle = f32_mul(radians, f32(0.5))
    quaternion_y = f32(math.sin(half_angle))
    quaternion_w = f32(math.cos(half_angle))
    quaternion = [f32(0.0), quaternion_y, f32(0.0), quaternion_w]
    rotation4 = unity_quaternion_to_matrix_candidate(quaternion)
    rotation = [row[:3] for row in rotation4[:3]]
    trs = unity_matrix4x4_trs_candidate(quaternion, position, scale)
    inverse, success, determinant = unity_matrix4x4_inverse_affine_candidate(trs)
    require(
        f"room_{row['lightPathId']}_obb_native_inverse_success",
        success,
        True,
        REPO_ROOT / row["sourcePath"],
    )
    return rotation, inverse, determinant


def recover_obb_pack(row: dict[str, Any]) -> dict[str, Any]:
    rotation, inverse, determinant = recovered_y_rotation_inverse_rows(row)
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
        "nativeInverseCandidateWordHex": [f"0x{word:08X}" for word in words],
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
        "nativeInverseDeterminantBits": f"0x{float32_bits(determinant):08X}",
        "precisionBoundary": (
            "the pinned UnityPlayer Matrix4x4::Inverse body now closes the scalar "
            "float32 cofactor/division and signed-zero candidate bits; the "
            "native Matrix4x4::TRS body and quaternion-to-matrix helper now close "
            "the TRS arithmetic, and the managed Euler wrapper now closes the "
            "float32 degree-to-radian/half-angle input; native sin/cos output, "
            "runtime IFix order, and retail capture remain separate boundaries"
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
        require(
            f"{name}_shadow_caster_properties",
            int(data["m_Shadows"]["m_CasterProperties"]),
            6,
            path,
        )
        require(
            f"{name}_light_shadow_caster_mode",
            int(data["m_LightShadowCasterMode"]),
            0,
            path,
        )
        require(
            f"{name}_point_shadow_caster_faces",
            int(data["m_Shadows"]["m_PointLightShadowCasterFaces"]),
            -1,
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
                "shadowCasterProperties": 6,
                "lightShadowCasterMode": 0,
                "pointShadowCasterFaces": -1,
            }
        )

    require("selected_room_type_counts", Counter(row["unityLightType"] for row in result), Counter({2: 10, 0: 1}), ROOM_LIGHT_ROOT)
    require(
        "selected_linear_extension_count",
        sum(row["unityLightType"] == 2 and row["linearLightLength"] > 0 for row in result),
        4,
        ROOM_LIGHT_ROOT,
    )
    require(
        "selected_shadow_caster_properties",
        Counter(row["shadowCasterProperties"] for row in result),
        Counter({6: len(result)}),
        ROOM_LIGHT_ROOT,
    )
    require(
        "selected_point_shadow_caster_faces",
        Counter(row["pointShadowCasterFaces"] for row in result),
        Counter({-1: len(result)}),
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


def recover_record0_discriminator(row: dict[str, Any]) -> dict[str, Any]:
    source = REPO_ROOT / row["sourcePath"]
    light_type = int(row["unityLightType"])
    require(
        f"room_{row['lightPathId']}_record0_supported_light_type",
        light_type in (0, 2),
        True,
        source,
    )
    light_kind = 0 if light_type == 0 else 1
    shadow_only = bool(row["shadowOnly"])
    encoded_integer = light_kind + 2 * int(shadow_only)
    encoded_value = f32(float(encoded_integer))
    return {
        "producerFormula": "float(lightKind + 2 * shadowOnly)",
        "nativeBranch": "Spot" if light_kind == 0 else "PointOrLinearExtension",
        "lightKind": light_kind,
        "shadowOnly": shadow_only,
        "encodedInteger": encoded_integer,
        "record0W": encoded_value,
        "record0WBits": f"0x{float32_bits(encoded_value):08X}",
    }


def recover_record1_inverse_range(row: dict[str, Any]) -> dict[str, Any]:
    source = REPO_ROOT / row["sourcePath"]
    range_bits = float32_bits(row["range"])
    require(
        f"room_{row['lightPathId']}_record1_range_known",
        range_bits in EXPECTED_INVERSE_RANGE_BITS,
        True,
        source,
    )
    expected_bits = EXPECTED_INVERSE_RANGE_BITS[range_bits]
    calculated_bits = float32_bits(f32(1.0 / float32_from_bits(range_bits)))
    require(
        f"room_{row['lightPathId']}_record1_inverse_range_bits",
        calculated_bits,
        expected_bits,
        source,
    )
    return {
        "producerFormula": "1.0f / VisibleLight.range",
        "range": float32_from_bits(range_bits),
        "rangeBits": f"0x{range_bits:08X}",
        "record1W": float32_from_bits(expected_bits),
        "record1WBits": f"0x{expected_bits:08X}",
    }


def recover_record2_static_terms(row: dict[str, Any]) -> dict[str, Any]:
    source = REPO_ROOT / row["sourcePath"]
    if row["unityLightType"] == 0:
        inner_bits = float32_bits(row["innerSpotAngleDegrees"])
        outer_bits = float32_bits(row["outerSpotAngleDegrees"])
        require(
            f"room_{row['lightPathId']}_record2_spot_angles",
            (inner_bits, outer_bits),
            (
                EXPECTED_SPOT_RECORD2_BITS["innerAngleDegrees"],
                EXPECTED_SPOT_RECORD2_BITS["outerAngleDegrees"],
            ),
            source,
        )
        z_bits = EXPECTED_SPOT_RECORD2_BITS["outerCos"]
        w_bits = EXPECTED_SPOT_RECORD2_BITS["inverseCosDifference"]
        return {
            "nativeBranch": "Spot",
            "record2ZSemantic": "cos(outer half-angle)",
            "record2Z": float32_from_bits(z_bits),
            "record2ZBits": f"0x{z_bits:08X}",
            "record2WSemantic": "inverse inner-minus-outer half-angle cosine difference",
            "record2W": float32_from_bits(w_bits),
            "record2WBits": f"0x{w_bits:08X}",
            "record2WClosed": True,
            "record2WContractClosed": True,
        }

    require(
        f"room_{row['lightPathId']}_record2_point_branch",
        row["unityLightType"],
        2,
        source,
    )
    length_bits = float32_bits(row["linearLightLength"])
    require(
        f"room_{row['lightPathId']}_record2_point_length",
        length_bits in (0xBF800000, 0x41900000),
        True,
        source,
    )
    return {
        "nativeBranch": "PointOrLinearExtension",
        "record2ZSemantic": "HGSharedLightData.length",
        "record2Z": float32_from_bits(length_bits),
        "record2ZBits": f"0x{length_bits:08X}",
        "record2WSemantic": "packed point-shadow face indices",
        "record2W": None,
        "record2WBits": None,
        "record2WClosed": False,
        "record2WContractClosed": True,
        "record3XSemantic": "packed point-shadow face indices 4 and 5",
        "record3X": None,
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
        "gachaCullViewAuditSha256": verified_hash(
            "gachaCullViewAudit", GACHA_CULL_VIEW_AUDIT
        ),
        "rotatehouseSha256": verified_hash("rotatehouse", ROTATEHOUSE),
    }
    with GAME_ASSEMBLY.open("rb") as stream:
        stream.seek(WRAPPERS_MANAGER_IS_PATCHED_FILE_OFFSET)
        wrappers_manager_is_patched_body = stream.read(WRAPPERS_MANAGER_IS_PATCHED_SIZE)
        stream.seek(WRAPPERS_MANAGER_IS_PATCHED_COLD_FILE_OFFSET)
        wrappers_manager_is_patched_cold_body = stream.read(
            WRAPPERS_MANAGER_IS_PATCHED_COLD_SIZE
        )
        stream.seek(WRAPPERS_MANAGER_GET_PATCH_FILE_OFFSET)
        wrappers_manager_get_patch_body = stream.read(WRAPPERS_MANAGER_GET_PATCH_SIZE)
        stream.seek(PREPARE_CPU_DATA_FILE_OFFSET)
        body = stream.read(PREPARE_CPU_DATA_SIZE)
        stream.seek(QUATERNION_EULER_MANAGED_FILE_OFFSET)
        quaternion_euler_managed_body = stream.read(QUATERNION_EULER_MANAGED_SIZE)
        stream.seek(QUATERNION_EULER_SCALE_HELPER_FILE_OFFSET)
        quaternion_euler_scale_helper_body = stream.read(
            QUATERNION_EULER_SCALE_HELPER_SIZE
        )
        stream.seek(PUNCTUAL_SHADOW_CACHE_INDEX_FILE_OFFSET)
        point_shadow_cache_index_body = stream.read(PUNCTUAL_SHADOW_CACHE_INDEX_SIZE)
        stream.seek(GET_SHADOW_RENDER_TYPE_FILE_OFFSET)
        shadow_render_type_body = stream.read(GET_SHADOW_RENDER_TYPE_SIZE)
        stream.seek(GET_RENDERER_CONFIG_FILE_OFFSET)
        renderer_config_body = stream.read(GET_RENDERER_CONFIG_SIZE)
        stream.seek(GET_ECS_RENDER_FLAGS_FILE_OFFSET)
        ecs_render_flags_body = stream.read(GET_ECS_RENDER_FLAGS_SIZE)
        stream.seek(HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_FILE_OFFSET)
        is_dynamic_shadow_caster_body = stream.read(
            HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_SIZE
        )
        stream.seek(HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_FILE_OFFSET)
        cast_static_objects_body = stream.read(HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_SIZE)
        stream.seek(HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_FILE_OFFSET)
        cast_dynamic_objects_body = stream.read(HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_SIZE)
        stream.seek(GET_LIGHT_NPR_DATA_FILE_OFFSET)
        npr_body = stream.read(GET_LIGHT_NPR_DATA_SIZE)
        stream.seek(GET_LIGHT_ADDITIONAL_DATA_FILE_OFFSET)
        additional_body = stream.read(GET_LIGHT_ADDITIONAL_DATA_SIZE)
        stream.seek(GET_LIGHT_FALLOFF_FILE_OFFSET)
        falloff_body = stream.read(GET_LIGHT_FALLOFF_SIZE)
        stream.seek(GET_LIGHT_FALLOFF_DEFAULT_FILE_OFFSET)
        falloff_default = stream.read(4)
        stream.seek(VISIBLE_LIGHT_GET_RANGE_FILE_OFFSET)
        range_getter_body = stream.read(VISIBLE_LIGHT_GET_RANGE_SIZE)
        stream.seek(SCALAR_COS_FILE_OFFSET)
        scalar_cos_body = stream.read(SCALAR_COS_SIZE)
        stream.seek(SPOT_ANGLE_DIVISOR_FILE_OFFSET)
        angle_divisor_bytes = stream.read(4)
        stream.seek(SPOT_ANGLE_PI_FILE_OFFSET)
        angle_pi_bytes = stream.read(4)
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
        stream.seek(VISIBLE_LIGHT_GET_FORWARD_FILE_OFFSET)
        visible_light_get_forward_body = stream.read(VISIBLE_LIGHT_GET_FORWARD_SIZE)
        stream.seek(VISIBLE_LIGHT_GET_POSITION_FILE_OFFSET)
        visible_light_get_position_body = stream.read(VISIBLE_LIGHT_GET_POSITION_SIZE)
        stream.seek(HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_FILE_OFFSET)
        pack_normal_oct_rect_encode_body = stream.read(
            HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_SIZE
        )
        stream.seek(PACK_NORMAL_ONE_CONSTANT_FILE_OFFSET)
        pack_normal_one_constant = stream.read(4)
        stream.seek(PACK_NORMAL_HALF_CONSTANT_FILE_OFFSET)
        pack_normal_half_constant = stream.read(4)
    global_game_managers_data = GLOBAL_GAME_MANAGERS.read_bytes()
    unity_player_data = UNITY_PLAYER.read_bytes()
    population = json.loads(GACHA_POPULATION.read_text(encoding="utf-8"))
    hierarchy = json.loads(ROOM_HIERARCHY.read_text(encoding="utf-8"))
    cull_view = json.loads(GACHA_CULL_VIEW_AUDIT.read_text(encoding="utf-8"))
    rotatehouse = json.loads(ROTATEHOUSE.read_text(encoding="utf-8"))
    rows = attach_room_additional_data(room_light_rows(population, hierarchy))
    for row in rows:
        row["record0Color"] = recover_record0_color(row)
        row["record0Discriminator"] = recover_record0_discriminator(row)
        row["record1InverseRange"] = recover_record1_inverse_range(row)
        row["record2StaticTerms"] = recover_record2_static_terms(row)
        row["obbPackedTransform"] = recover_obb_pack(row)
    consumer = validate_consumer(SELECTED_FRAGMENT.read_text(encoding="utf-8"))
    native = validate_native_body(body)
    native["pointShadowCacheIndex"] = validate_point_shadow_cache_index_native(
        point_shadow_cache_index_body
    )
    native["ifixWrapperTable"] = validate_ifix_wrapper_table_native(
        wrappers_manager_is_patched_body,
        wrappers_manager_is_patched_cold_body,
        wrappers_manager_get_patch_body,
    )
    native["shadowRenderType"] = validate_shadow_render_type_native(
        shadow_render_type_body
    )
    native["rendererConfig"] = validate_renderer_config_native(renderer_config_body)
    native["ecsRenderFlags"] = validate_ecs_render_flags_native(ecs_render_flags_body)
    native["shadowCasterPropertyGetters"] = validate_shadow_caster_property_getters(
        is_dynamic_shadow_caster_body,
        cast_static_objects_body,
        cast_dynamic_objects_body,
    )
    native["pointRecordTransform"]["helperBodies"] = (
        validate_visible_light_transform_helpers(
            visible_light_get_forward_body,
            visible_light_get_position_body,
            pack_normal_oct_rect_encode_body,
            pack_normal_one_constant,
            pack_normal_half_constant,
        )
    )
    native["pointRecordTransform"]["authoredRoomCandidates"] = (
        validate_authored_room_transform_candidates(cull_view, hierarchy, rotatehouse)
    )
    native["additionalLightData"] = validate_additional_data_native(
        npr_body, additional_body
    )
    native["lightFalloff"] = validate_light_falloff_native(
        falloff_body, falloff_default
    )
    native["staticRecordTerms"] = validate_static_record_terms_native(
        body,
        range_getter_body,
        scalar_cos_body,
        falloff_default,
        angle_divisor_bytes,
        angle_pi_bytes,
    )
    native["unityPlayerLightColor"] = validate_unity_light_color_native(
        unity_player_data
    )
    native["matrix4x4Inverse"] = validate_matrix4x4_inverse_native(
        unity_player_data
    )
    native["matrix4x4Trs"] = validate_matrix4x4_trs_native(unity_player_data)
    native["quaternionEuler"] = validate_quaternion_euler_native(
        quaternion_euler_managed_body,
        quaternion_euler_scale_helper_body,
        degrees_to_radians_bytes,
        unity_player_data,
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
    record0_discriminator_counts = Counter(
        row["record0Discriminator"]["encodedInteger"] for row in rows
    )
    require(
        "selected_room_record0_discriminator_counts",
        record0_discriminator_counts,
        Counter({1: 10, 0: 1}),
        ROOM_LIGHT_ROOT,
    )
    record1_closed_count = sum("record1WBits" in row["record1InverseRange"] for row in rows)
    record2_z_closed_count = sum("record2ZBits" in row["record2StaticTerms"] for row in rows)
    record2_w_closed_count = sum(row["record2StaticTerms"]["record2WClosed"] for row in rows)
    record2_w_contract_closed_count = sum(
        row["record2StaticTerms"]["record2WContractClosed"] for row in rows
    )
    point_length_counts = Counter(
        row["record2StaticTerms"]["record2Z"]
        for row in rows
        if row["record2StaticTerms"]["nativeBranch"] == "PointOrLinearExtension"
    )
    require("selected_room_record1_w_closed_count", record1_closed_count, 11, ROOM_LIGHT_ROOT)
    require("selected_room_record2_z_closed_count", record2_z_closed_count, 11, ROOM_LIGHT_ROOT)
    require("selected_room_record2_w_closed_count", record2_w_closed_count, 1, ROOM_LIGHT_ROOT)
    require(
        "selected_room_record2_w_contract_closed_count",
        record2_w_contract_closed_count,
        11,
        ROOM_LIGHT_ROOT,
    )
    require(
        "point_shadow_face_pack_face_order",
        native["pointShadowFacePack"]["faceOrder"],
        list(range(6)),
        GAME_ASSEMBLY,
    )
    require(
        "point_record_transform_call_order",
        [row["method"] for row in native["pointRecordTransform"]["calls"]],
        [
            "VisibleLightExtensionMethods.GetForward",
            "HGUtils.PackNormalOctRectEncode",
            "VisibleLightExtensionMethods.GetPosition",
        ],
        GAME_ASSEMBLY,
    )
    require(
        "selected_room_point_length_counts",
        point_length_counts,
        Counter({-1.0: 6, 18.0: 4}),
        ROOM_LIGHT_ROOT,
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
        "schema": "endfield.gacha-deferred-light-data-recovery.v20",
        "status": "room_record0_record1w_record2z_transform_point_shadow_cache_shadow_render_type_renderer_config_ecs_flags_ifix_table_lookup_and_unityplayer_obb_euler_input_trs_inverse_contract_closed",
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
            "allShadowCasterProperties": 6,
            "allPointShadowCasterFaces": -1,
            "allLightShadowCasterMode": 0,
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
            "record0DiscriminatorSummary": {
                "producerFormula": "float(lightKind + 2 * shadowOnly)",
                "spotCount": 1,
                "pointOrLinearExtensionCount": 10,
                "shadowOnlyCount": 0,
                "valueCounts": {
                    "0": record0_discriminator_counts[0],
                    "1": record0_discriminator_counts[1],
                },
                "exactCandidateCount": len(rows),
                "closedLanes": ["record0.w"],
            },
            "record1InverseRangeSummary": {
                "producerFormula": "1.0f / VisibleLight.range",
                "exactCandidateCount": record1_closed_count,
                "closedLanes": ["record1.w"],
            },
            "record2StaticTermsSummary": {
                "spotRecord2ZFormula": "cos(outer half-angle)",
                "spotRecord2WFormula": "1.0f / (cos(inner half-angle) - cos(outer half-angle))",
                "pointRecord2ZFormula": "HGSharedLightData.length",
                "pointLengthCounts": {
                    "-1": point_length_counts[-1.0],
                    "18": point_length_counts[18.0],
                },
                "record2ZExactCandidateCount": record2_z_closed_count,
                "record2WExactCandidateCount": record2_w_closed_count,
                "record2WContractExactCandidateCount": record2_w_contract_closed_count,
                "pointShadowFacePack": native["pointShadowFacePack"],
                "pointShadowCacheIndex": native["pointShadowCacheIndex"],
                "ifixWrapperTable": native["ifixWrapperTable"],
                "shadowRenderType": native["shadowRenderType"],
                "rendererConfig": native["rendererConfig"],
                "ecsRenderFlags": native["ecsRenderFlags"],
                "shadowCasterPropertyGetters": native["shadowCasterPropertyGetters"],
                "pointRecordTransform": native["pointRecordTransform"],
                "closedLanes": [
                    "record2.z for all rows",
                    "record2.w for the Spot row",
                    "Point record2.w/record3.x face-index packing contract",
                ],
                "openLanes": [
                    "target-frame Point record2.w/record3.x cache-index values",
                ],
            },
            "obbHalfPackingSummary": {
                "producerFormula": "inverse TRS of authored relative position, ZXY Euler orientation, and half extents",
                "wordPlacement": "six row-major half2 words in record5.xyz then record6.xyz",
                "installedPackingMethodClosed": True,
                "installedMatrix4x4TrsBodyClosed": True,
                "nativeTrsCandidateUsesQuaternionHelperAndScalarFloat32Scale": True,
                "installedMatrix4x4InverseBodyClosed": True,
                "nativeInverseCandidateUsesScalarFloat32Cofactors": True,
                "nativeInverseCandidateCount": len(rows),
                "oneFloat32UlpSensitiveLocations": obb_boundaries,
                "nativeInverseSignedZeroCandidateBits": True,
                "retailSignedZeroBitsCaptured": False,
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
                "the UnityPlayer icall-table entry 2471 (Matrix4x4::Inverse3DAffine_Injected), its 0x1800A2020 stub, and hash-pinned 0x180569BD0 scalar affine-inverse body",
                "the UnityPlayer icall-table entry 2470 (Matrix4x4::TRS_Injected), its hash-pinned 0x1800A1BB0 wrapper, 0x18056CB40 scale/translation body, and 0x18056B8A0 quaternion-to-column-major-matrix helper",
                "the managed Quaternion.Euler wrapper/helper, degree-to-radian constant 0x3C8EFA35, UnityPlayer icall 2489 (Internal_FromEulerRad_Injected), its 0x1800A5010 wrapper, hash-pinned 0x180567590 half-angle body, and all six native sin/cos call targets",
                "the native inverse determinant threshold, -0 sign mask, cofactor/division order, translation cofactor rows, and exact float32 candidate half words for all eleven authored rows",
                "the native TRS helper's quaternion matrix arithmetic, scalar column scaling order, and raw position-field copies; the managed Euler degree-to-radian and native half-angle input arithmetic is source-closed",
                "six-word native-inverse OBB candidates for all eleven rows and every non-boundary half payload; decoded candidates return every authored corner to the unit-box boundary within 0.003",
                "the installed PlayerSettings Linear color space and GraphicsSettings linear-light-intensity/color-temperature flags from pinned globalgamemanagers objects",
                "the UnityPlayer finalColor producer, Color.linear body, light-animation disable path, and flickerScale inactive fallback of exactly 1.0",
                "all eleven rows disable per-light color temperature, culling-distance/far-show falloff, animation, multistate, and flicker; their state tables and flicker references are empty",
                "exact UnityPlayer-derived record0.xyz IEEE-754 candidates for all eleven rows: linearized serialized RGB times intensity, with falloff and flickerScale both 1",
                "the native record0.w discriminator formula float(lightKind + 2*shadowOnly), yielding exact 0.0 for the one Spot row and 1.0 for all ten Point/linear-extension rows",
                "VisibleLight.get_range reads field +0x68 and PrepareCPUData divides exact 1.0f by it, closing record1.w for all eleven rows",
                "the pinned original scalar-cosine body and exact half-angle scaling close record2.z and record2.w for the one Spot row",
                "HGSharedLightData.length closes record2.z as -1 for six ordinary Point rows and 18 for four linear-extension rows",
                "the Point/linear native branch constructs LightCaster face requests in order 0..5, queries GetShadowCacheIndexForCaster for each, maps -1 to 255, and packs faces 0..3 into record2.w plus faces 4..5 into record3.x",
                "GetShadowCacheIndexForCaster is source-closed: dynamic matches return ordinal + 40, static matches return shadowCacheSlotIndex, unmatched casters return -1, and null manager/list state fail-fast",
                "the native HGSharedLightData caster-property getters are hash-pinned masks 0x01/0x02/0x04; all selected room rows serialize m_CasterProperties=6, point-shadow faces=-1, and LightShadowCasterMode=0",
                "GetShadowRenderType method 0x886 is hash-pinned: IsPatched gates a native default path whose static request returns castStatic=true/castDynamic=false and whose dynamic path consumes the three caster-property getters",
                "the patched GetShadowRenderType path is explicitly bounded to WrappersManagerImpl.GetPatch(0x886) and ILFixDynamicMethodWrapper.__Gen_Wrap_874, with missing-patch fail-fast; no runtime wrapper result is inferred",
                "GetRendererConfig method 0x887 is hash-pinned: its unpatched projection is 0x4800 | (castStaticObjects ? 0x1000 : 0) | (castDynamicObjects ? 0x2000 : 0), and its patched path is bounded to __Gen_Wrap_875",
                "GetECSRenderFlags method 0x888 is hash-pinned: it initializes object/render flags, projects exclusive caster results into 0x04000000/0x01000000, and adds objectFlagsMask bit 28 only for the enableHDCharacterShadow + active HDPLS-light path",
                "WrappersManagerImpl.IsPatched/GetPatch are hash-pinned: the live manager table uses +0xB8 -> active table, +0x18 entry count, and +0x20 + 8*methodId entries, with exact signed/unsigned bounds and null-entry behavior closed",
                "the Point/linear native branch calls VisibleLightExtensionMethods.GetForward, HGUtils.PackNormalOctRectEncode, and VisibleLightExtensionMethods.GetPosition for record2.xy and record1.xyz",
                "the pinned GetForward/GetPosition helper bodies read LocalToWorldMatrix columns 2/3 through Matrix4x4.GetColumn and Vector4.op_Implicit; the PackNormalOctRectEncode body, sizes, hashes, and IFix method IDs are closed",
                "the authored SceneLight6Rarity hierarchy recomposes all 12 world positions and directions from the pinned rotatehouse transform, bit-matching the independent cull-view audit",
                "PackNormalOctRectEncode's unpatched abs/dot/float3-multiply/clamp/CopySign call chain and 1.0/0.5 constants close the exact float32 formula; all 12 authored record2.xy candidates are generated from it",
            ],
            "open": [
                "target-frame record1.xyz world positions, camera-relative subtraction input, and record2.xy encoded directions",
                "the authored candidates do not replace a retail LightCullResult capture; runtime transform mutation and the final packed record2.xy values remain open",
                "the IFix patched helper branches and their target-frame return values remain version/runtime-boundary evidence, even though the retail unpatched helper bodies are hash-pinned",
                "native sin/cos result payloads, runtime IFix Euler-order/output selection, and retail buffer capture of the packed OBB signed-zero bits; target-frame Point record2.w/record3.x shadow-face cache indices and other shadow/cookie cache indices",
                "GetShadowRenderType's runtime IsPatched(0x886) gate, any patched return flags, and the runtime caster-list membership/culling state; serialized shadowType=0 is not treated as proof that all six Point cache lookups return -1",
                "the active IFix table membership/pointers for 0x886/0x887/0x888 and any patched return values remain runtime-boundary evidence; static GameAssembly does not contain the live table entries",
                "the complete retail survivor array, runtime/custom carry-in, and final lightCount",
            ],
            "decision": (
                "Treat the eight-record native schema and the eleven serialized room inputs as source-closed, "
                "including all record0 lanes, the record1/record2 transform producer contract, record1.w, record2.z, the Spot record2.w, the Point face-index packing contract, additional-light lanes, and the native UnityPlayer OBB Euler-input/TRS/inverse arithmetic up to the runtime sin/cos/IFix boundary. Do not publish "
                "a byte-exact Gacha b31 fixture or enable deferred pass 0 until the remaining UnityPlayer/boundary "
                "bits, target-frame record1.xyz/record2.xy values, live Point record2.w/record3.x cache indices, and runtime list boundary are closed."
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
        "all 11 record0 float4 values, record1/record2 transform producer contract, "
        "record1.w/record2.z static terms, the Spot record2.w, Point face-index packing and cache-resolver contracts, "
        "shadow render-type/renderer-config/ECS-flag gates, IFix wrapper-table lookup contract, additional-light components, and the UnityPlayer OBB Euler-input/TRS/inverse half candidates closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
