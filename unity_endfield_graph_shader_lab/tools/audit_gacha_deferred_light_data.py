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
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_deferred_light_data_recovery.json"
)

VALIDATOR = "gacha_deferred_light_data"
PREPARE_CPU_DATA_VA = 0x189D0C7BC
PREPARE_CPU_DATA_FILE_OFFSET = 0x9D0ADBC
PREPARE_CPU_DATA_SIZE = 0x1838

EXPECTED_HASHES = {
    "gameAssembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "globalMetadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "selectedFragment": "44dc5090af87a8f65ffca870f9e02b8525c4cfe14f84cf8feaa3ea6c49e4b9db",
    "gachaPopulation": "02e15c70197bcd96f804007fe042fcb46577c0014d956d78a28f2d96162e189a",
    "roomHierarchy": "bf26b44919a7563bd6c7ee137346d7f8880bb1a32911a8972c586b2bb0c87db9",
    "prepareCpuDataBody": "c55bd6dc86c971123c433a5dd29b446b557f8713f73b132da25c257369e9bd0b",
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


def call_target(body: bytes, offset: int) -> int:
    require(f"native_call_{offset:04x}_opcode", body[offset], 0xE8, GAME_ASSEMBLY)
    displacement = struct.unpack_from("<i", body, offset + 1)[0]
    return PREPARE_CPU_DATA_VA + offset + 5 + displacement


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
            "3": "shadow/cookie addressing and additional-light flags; CharacterOnly is z",
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
    population = json.loads(GACHA_POPULATION.read_text(encoding="utf-8"))
    hierarchy = json.loads(ROOM_HIERARCHY.read_text(encoding="utf-8"))
    rows = room_light_rows(population, hierarchy)
    consumer = validate_consumer(SELECTED_FRAGMENT.read_text(encoding="utf-8"))
    native = validate_native_body(body)
    return {
        "schema": "endfield.gacha-deferred-light-data-recovery.v1",
        "status": "native_point_spot_row_schema_closed_room_inputs_censused",
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
            "rows": rows,
        },
        "evidenceBoundary": {
            "closed": [
                "PrepareCPUData owns all eight float4 writes for both native Spot and Point/linear-extension branches",
                "the selected deferred consumer's record offsets and observed lane semantics",
                "the exact selected-aspect 11-row authored room membership and raw Unity Light inputs",
                "one Spot, six ordinary Point, and four positive-length linear-extension Point rows",
                "all eleven selected room rows enable OBB culling and have no cookie, shadow, shadow-only, or override-shadow state",
            ],
            "open": [
                "room HGAdditionalLightData component/default resolution, including NPR data, CharacterOnly, volumetric, and falloff lanes",
                "exact float32 color/intensity helper results and camera-relative position/direction values at the target frame",
                "exact packed OBB half words and shadow/cookie cache indices for the eleven rows",
                "the complete retail survivor array, runtime/custom carry-in, and final lightCount",
            ],
            "decision": (
                "Treat the eight-record native schema and the eleven serialized room inputs as source-closed, "
                "but do not publish a byte-exact Gacha b31 fixture or enable deferred pass 0 until the "
                "additional-light defaults, target-frame transforms, and runtime list boundary are closed."
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
        "closed; 11 selected room inputs censused."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
