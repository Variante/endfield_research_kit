#!/usr/bin/env python3
"""Audit the native b31 punctual-row schema and selected Gacha room inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
GLOBAL_METADATA = GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
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
HG_ADDITIONAL_LIGHT_DATA_SCRIPT_PATH_ID = 4098216658219718577

EXPECTED_HASHES = {
    "gameAssembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "globalMetadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "selectedFragment": "44dc5090af87a8f65ffca870f9e02b8525c4cfe14f84cf8feaa3ea6c49e4b9db",
    "gachaPopulation": "02e15c70197bcd96f804007fe042fcb46577c0014d956d78a28f2d96162e189a",
    "roomHierarchy": "bf26b44919a7563bd6c7ee137346d7f8880bb1a32911a8972c586b2bb0c87db9",
    "prepareCpuDataBody": "c55bd6dc86c971123c433a5dd29b446b557f8713f73b132da25c257369e9bd0b",
    "getLightNprDataBody": "49eeca70b72791b2ad58f8b77cf3fbc3f27149766dcc0510a00b9d129e6698c8",
    "getLightAdditionalDataBody": "071061feb7f3c76044273efe703f9bdf78288703516b863c10c592b263f73e00",
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
    0x08DB: (0x1832040F0, "LightExtensions.GetLightAdditionalData"),
    0x0A68: (0x18B3BDD4C, "HGSharedLightData.get_enableOBBCullingBox_Injected"),
    0x0A77: (0x18B3BDD88, "HGSharedLightData.get_enableOverrideShadowLight_Injected"),
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


def validate_consumer(text: str) -> dict[str, Any]:
    checks = {
        "recordStride": "int((32u * _747) + _758) * 8",
        "record0Type": "_LightDataBuffer_f_96[_764].w < 1.5f",
        "record1Position": "_LightDataBuffer_f_96[_767].xyz - _448",
        "record1InverseRange": "_LightDataBuffer_f_96[_767].w * _LightDataBuffer_f_96[_767].w",
        "record2Direction": "_LightDataBuffer_f_96[_770].y",
        "record3CharacterOnly": "_LightDataBuffer_f_96[_773].z > 0.5f",
        "record5ObbFlags": "uint(_LightDataBuffer_f_96[_776].w)",
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
        "globalMetadataSha256": verified_hash("globalMetadata", GLOBAL_METADATA),
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
    population = json.loads(GACHA_POPULATION.read_text(encoding="utf-8"))
    hierarchy = json.loads(ROOM_HIERARCHY.read_text(encoding="utf-8"))
    rows = attach_room_additional_data(room_light_rows(population, hierarchy))
    consumer = validate_consumer(SELECTED_FRAGMENT.read_text(encoding="utf-8"))
    native = validate_native_body(body)
    native["additionalLightData"] = validate_additional_data_native(
        npr_body, additional_body
    )
    volumetric_counts = Counter(
        row["additionalLightData"]["volumetricScatteringIntensity"] for row in rows
    )
    return {
        "schema": "endfield.gacha-deferred-light-data-recovery.v2",
        "status": "native_point_spot_row_schema_and_room_additional_data_closed",
        "installedInputs": hashes,
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
            ],
            "open": [
                "exact float32 color/intensity helper results and camera-relative position/direction values at the target frame",
                "exact packed OBB half words and shadow/cookie cache indices for the eleven rows",
                "the complete retail survivor array, runtime/custom carry-in, and final lightCount",
            ],
            "decision": (
                "Treat the eight-record native schema and the eleven serialized room inputs as source-closed, "
                "including their additional-light lanes, but do not publish a byte-exact Gacha b31 fixture "
                "or enable deferred pass 0 until target-frame transforms, color/intensity helpers, packed OBB "
                "words, and the runtime list boundary are closed."
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
        "Gacha deferred LightData audit passed: native Spot/Point 8-float4 schema "
        "and all 11 room additional-light components closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
