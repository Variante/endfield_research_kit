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

    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    abi = data["m23ShaderAbi"]
    assert abi["shader"]["pass"] == "ForwardOnly"
    assert abi["shader"]["keywords"] == M.M23_VARIANT_KEYWORDS
    assert abi["material"]["pathID"] == M.M23_PATH_ID
    assert abi["variants"]["vertex"]["blob"]["bytes"] == 10720
    assert abi["variants"]["fragment"]["blob"]["bytes"] == 8100
    assert abi["texcoordPacking"] == M.M23_TEXCOORD_PACKING
    assert abi["lowCbufferMappings"] == M.M23_LOW_CBUFFER_MAPPINGS
    assert abi["unresolvedCbufferSlots"] == M.M23_UNRESOLVED_CBUFFER_SLOTS


if __name__ == "__main__":
    test_m23_abi_constants_and_generated_contract()
    print("Li Zhiyan peak M23 ABI contract tests passed: 1")
