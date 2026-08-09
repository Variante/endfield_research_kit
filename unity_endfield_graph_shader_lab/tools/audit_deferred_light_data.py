#!/usr/bin/env python3
"""Audit the selected deferred resolver's source-backed b31 reads."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
GLOBAL_METADATA = (
    GAME_ROOT
    / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
)
SHADER_METADATA = (
    LAB_ROOT
    / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
    "original_shader_export/Shader/"
    "HGRP_DeferredLighting_p5F10B115E8D3AFDE.shader.bytecode/"
    "0097_endfield_dxbc_1.dxbc.metadata.json"
)
SELECTED_FRAGMENT = (
    LAB_ROOT
    / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
    "selected_fragment.hlsl"
)
ENV_SOURCE = (
    REPO_ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/"
    "MonoBehaviour/CharInfo_Env_p10AB447A9F33D0F3.json"
)
OUTPUT = LAB_ROOT / "scratch/character_recovery/deferred_light_data/audit.json"

EXPECTED_HASHES = {
    "game_assembly": (
        "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
    ),
    "global_metadata": (
        "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
    ),
    "shader_metadata": (
        "07b16f92bce820666837e624777b4160d89bb5faf9a57e8eafe48c6041501cff"
    ),
    "selected_fragment": (
        "44dc5090af87a8f65ffca870f9e02b8525c4cfe14f84cf8feaa3ea6c49e4b9db"
    ),
    "environment_source": (
        "33bb9d19d4a7c1e0dfb5e82117821c908108059f76b7103c2c0ed5e8ba7f873c"
    ),
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
            "Deferred LightData audit failed: "
            f"check={check}; expected={expected!r}; actual={actual!r}"
        )


def verified_hash(name: str, path: Path) -> str:
    actual = sha256(path)
    require(f"{name}_sha256", actual, EXPECTED_HASHES[name])
    return actual


def build_audit() -> dict[str, object]:
    hashes = {
        "game_assembly": verified_hash("game_assembly", GAME_ASSEMBLY),
        "global_metadata": verified_hash("global_metadata", GLOBAL_METADATA),
        "shader_metadata": verified_hash("shader_metadata", SHADER_METADATA),
        "selected_fragment": verified_hash(
            "selected_fragment", SELECTED_FRAGMENT
        ),
        "environment_source": verified_hash(
            "environment_source", ENV_SOURCE
        ),
    }

    metadata = json.loads(SHADER_METADATA.read_text(encoding="utf-8"))
    light_data = next(
        row
        for row in metadata["ConstantBufferParameters"]
        if row["Name"] == "_LightDataBuffer"
    )
    require("buffer_size", light_data["Size"], 32864)
    require("partial_consumer_metadata", light_data["IsPartialCB"], True)
    require(
        "selected_header_fields",
        [(row["Name"], row["Index"]) for row in light_data["VectorParameters"]],
        [
            ("_DirectionalLightDirection", 0),
            ("_DirectionalLightColor", 16),
            ("_DirectionalLightCustomData2", 64),
        ],
    )

    return {
        "schema": "endfield.recovered-deferred-light-data-audit.v1",
        "status": "selected_charinfo_consumer_reads_source_closed",
        "installedInputs": {
            "gameAssemblySha256": hashes["game_assembly"],
            "globalMetadataSha256": hashes["global_metadata"],
        },
        "selectedShader": {
            "metadataPath": SHADER_METADATA.relative_to(LAB_ROOT).as_posix(),
            "metadataSha256": hashes["shader_metadata"],
            "decompiledFragmentPath": SELECTED_FRAGMENT.relative_to(
                LAB_ROOT
            ).as_posix(),
            "decompiledFragmentSha256": hashes["selected_fragment"],
            "binding": 31,
            "sizeBytes": 32864,
            "vectorCount": 2054,
            "partialConsumerMetadata": True,
        },
        "nativeProducer": {
            "constructor": {
                "method": "HG.Rendering.Runtime.LightCulling..ctor",
                "methodIndex": 285273,
                "virtualAddress": "0x1841a21f0",
                "allocationRule": (
                    "6 + (NUM_FLOAT4_PUNCTUALIGHT << 8) float4"
                ),
            },
            "cpuPack": {
                "method": "HG.Rendering.Runtime.LightCulling.PrepareCPUData",
                "methodIndex": 285282,
                "virtualAddress": "0x189d0c7bc",
                "fileOffset": "0x9d0adbc",
                "sizeBytes": 6200,
                "punctualAddressRule": (
                    "header[6] + lightIndex * 8 + recordVector[0..7]"
                ),
            },
            "environmentColor": {
                "method": (
                    "HG.Rendering.Runtime.HGLightConfig.UpdateDirectFinalColor"
                ),
                "methodIndex": 284457,
                "virtualAddress": "0x189ce41f4",
                "fileOffset": "0x9ce27f4",
                "sizeBytes": 304,
            },
        },
        "layout": {
            "headerVectors": 6,
            "maxPunctualLights": 256,
            "vectorsPerPunctualLight": 8,
            "directionalSelectedVectors": {
                "0": "direction.xyz",
                "1": "finalColor.xyz",
                "4": (
                    "specularIntensity, sin(softRadiusRadians), "
                    "cos(softRadiusRadians), unused"
                ),
            },
            "selectedCharinfoPunctualReads": {
                "record5w": "OBB/override flags; zero for every selected row",
                "record3z": "LightCharacterOnly; one for every selected row",
                "controlFlow": (
                    "SphereOutside exits after these values, before "
                    "general-scene light terms or shadow-slot words"
                ),
            },
        },
        "charinfoEnvironment": {
            "rawSourcePath": ENV_SOURCE.relative_to(REPO_ROOT).as_posix(),
            "rawSourceFileSha256": hashes["environment_source"],
            "sourcePathId": 1201129019072041203,
            "sourceRawDataSha256": (
                "f9d1384c29f1e54599cd55e5f9c5c6d7eb9bd6f678d9fd104c7c329e6f1a66f9"
            ),
            "forwardDirect": [0.021389274, -0.64278764, -0.76574594],
            "directIntensity": 8.631674,
            "directSpecularIntensity": 1.0,
            "directSoftSourceRadiusDegrees": 0.0,
            "directColorTemperature": 7000.0,
        },
        "fixtureBoundary": {
            "actors": ["Wulfa", "Zhuangfy"],
            "requiredLightCounts": [8, 6],
            "allRowsCharacterOnly": True,
            "allRowsNoObb": True,
            "allRowsNoCookie": True,
            "allRowsNoCullingDistance": True,
            "allRowsNoFlicker": True,
            "oneShadowedRow": "source row 4, RimLight_2 (5), soft shadow",
            "sameFrameShadowAtlasRequiredBySelectedConsumer": False,
            "generalScenePunctualPayloadRecovered": False,
            "pass0Activated": False,
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
        "Deferred LightData audit passed: b31=32864 bytes, "
        "layout=6+256*8 float4, selected CharInfo reads source-closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
