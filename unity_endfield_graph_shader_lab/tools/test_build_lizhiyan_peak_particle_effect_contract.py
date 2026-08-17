#!/usr/bin/env python3
"""Focused ABI pins for Li Zhiyan OverviewPeakParticles M23."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PATH = Path(__file__).with_name("build_lizhiyan_peak_particle_effect_contract.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_peak", PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


CONTRACT = (
    PATH.parents[1]
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "lizhiyan_overview_peak_particle_effects.json"
)


def test_m23_abi_constants_and_generated_contract() -> None:
    assert M.M23_PATH_ID == -430604955415889784
    assert M.M23_VARIANT_PASS == "ForwardOnly"
    assert M.M23_VARIANT_KEYWORDS == [
        "HG_ENABLE_MV", "_SAMPLE_TEX0", "_SAMPLE_TEX1",
        "_SAMPLE_TEX2", "_SAMPLE_TEX3", "_USE_FRESNEL",
    ]
    assert M.M23_VARIANT_FILES["vertex"]["bytes"] == 10720
    assert M.M23_VARIANT_FILES["fragment"]["bytes"] == 8100
    assert M.M23_LOW_CBUFFER_MAPPINGS["cb4[1].x"] == "_InParticle"
    assert M.M23_LOW_CBUFFER_MAPPINGS["cb4[6]"] == "_MainTexUVSpeed"
    assert M.M23_TEXCOORD_PACKING["vertexOutputs"] == {
        "o1.xy": "mainUV", "o2.xy": "sample0UV", "o2.zw": "sample1UV",
        "o3.xy": "sample2UV", "o3.zw": "sample3UV",
    }
    assert "cb4[11..12]" in M.M23_UNRESOLVED_CBUFFER_SLOTS
    assert M.M23_FRAGMENT_CONTAINER["hasRdef"] is False
    assert M.M23_FRAGMENT_CONTAINER["b4Float4Registers"] == 44
    assert M.M23_FRAGMENT_CONTAINER["highestDirectlyAccessedB4Index"] == 43
    assert M.M23_FRAGMENT_CONTAINER["unresolvedNameBoundary"] == "cb4[10..43]"

    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    abi = data["m23ShaderAbi"]
    assert abi["shader"]["pass"] == "ForwardOnly"
    assert abi["shader"]["keywords"] == M.M23_VARIANT_KEYWORDS
    assert abi["material"]["pathID"] == M.M23_PATH_ID
    assert abi["selectionBoundary"] == {
        "serializedNonInstancedPair": "blob1277 / sidecars 0138+0139",
        "srpInstancedAlternative": "blob1956 / sidecars 4212+4213; adds SRP_INSTANCING_ON",
        "retailDrawVariantCaptured": False,
        "interpretation": "material valid keywords plus HG_ENABLE_MV uniquely select blob1277 only when SRP_INSTANCING_ON is absent; serialized GPU-instancing flags do not prove that runtime fork/HG decision",
    }
    assert abi["variants"]["vertex"]["blob"]["bytes"] == 10720
    assert abi["variants"]["fragment"]["blob"]["bytes"] == 8100
    assert abi["texcoordPacking"] == M.M23_TEXCOORD_PACKING
    assert abi["lowCbufferMappings"] == M.M23_LOW_CBUFFER_MAPPINGS
    assert abi["unresolvedCbufferSlots"] == M.M23_UNRESOLVED_CBUFFER_SLOTS
    assert abi["fragmentContainer"] == M.M23_FRAGMENT_CONTAINER
    shader_json = abi["shaderJsonEvidence"]
    assert shader_json["source"] == {
        "path": "scratch/animestudio/m23_shader_json_probe/out/Shader/"
        "HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.json",
        "bytes": 17166809,
        "sha256": "B77939FDD44FF3684C61F4CF4464514535F43530DF6BCDC68E08DC20F1BB160E",
        "objectType": "ShaderSerializedJSON",
        "pathID": M.SHADER_PATH_ID,
    }
    assert shader_json["propertyCount"] == 296
    assert shader_json["unityPerMaterial"] == {
        "size": 432,
        "isPartial": True,
        "namedVectorCount": 20,
        "maxNamedIndex": 144,
    }
    assert shader_json["packingCandidates"] == [
        {
            "name": "activeSerializedProperties",
            "propertyCount": 19,
            "totalBytes": 144,
            "firstDivergence": {
                "property": "_VertCameraOffset", "candidateOffset": 8, "knownOffset": 52,
            },
            "matchesKnownLowLayout": False,
            "matchesUnityPerMaterialSize": False,
            "matchesShexB4Bytes": False,
            "passesGates": False,
            "mainTexSTOffset": None,
        },
        {
            "name": "activeSerializedPropertiesPlusMainTexST",
            "propertyCount": 20,
            "totalBytes": 160,
            "firstDivergence": {
                "property": "_VertCameraOffset", "candidateOffset": 8, "knownOffset": 52,
            },
            "matchesKnownLowLayout": False,
            "matchesUnityPerMaterialSize": False,
            "matchesShexB4Bytes": False,
            "passesGates": False,
            "mainTexSTOffset": 48,
        },
        {
            "name": "allNonTextureSerializedProperties",
            "propertyCount": 277,
            "totalBytes": 1840,
            "firstDivergence": {
                "property": "_SurfaceType", "candidateOffset": 4, "knownOffset": 0,
            },
            "matchesKnownLowLayout": False,
            "matchesUnityPerMaterialSize": False,
            "matchesShexB4Bytes": False,
            "passesGates": False,
            "mainTexSTOffset": None,
        },
    ]
    assert M.m23_shader_json_evidence() == shader_json
    assert "Runtime selection between that pair and the blob1956" in data["executionBoundary"]


if __name__ == "__main__":
    test_m23_abi_constants_and_generated_contract()
    print("Li Zhiyan peak M23 ABI contract tests passed: 1")
