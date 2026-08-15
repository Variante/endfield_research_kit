#!/usr/bin/env python3
"""Verify the shared Character Info CharEffect source and Unity shader gate."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
LAB_ROOT = TOOLS_ROOT.parent
sys.path.insert(0, str(TOOLS_ROOT))

import build_charinfo_overview_effect_contract as builder


CONTRACT_PATH = builder.OUTPUT
SHADER_PATH = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Shaders/Recovered"
    / "EndfieldZhuangfyVFXRefractMRT.shader"
)


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> int:
    published = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    rebuilt = builder.build()
    assert canonical(published) == canonical(rebuilt), "published contract is stale"
    assert published["schema"] == builder.SCHEMA
    assert len(published["nodes"]) == 2
    assert [row["hierarchy"] for row in published["nodes"]] == [
        "CharEffect",
        "CharEffect/trail",
    ]
    assert published["material"]["pathID"] == 4388811075012960551
    assert published["texture"]["pathID"] == -7046954404783675798
    assert published["execution_gate"] == {
        "queue": 3000,
        "lightMode": "Distortion",
        "keywords": ["HG_ENABLE_MV", "_USE_RBOFFSET"],
        "fragmentDxbcHash": "f905de094d0261d5",
        "sceneMvFormat": "A2B10G10R10_UNormPack32",
        "selectedTarget1": [0.0, 0.0, 1.0, 0.0],
    }

    shader = SHADER_PATH.read_text(encoding="utf-8")
    for token in (
        '#pragma shader_feature_local_fragment _USE_RBOFFSET',
        '_RBOffset.xy * 0.01',
        'scene.rgb * _RBMainColorMask.rgb',
        'rbScene.rgb * _RBOffsetColorMask.rgb',
        'saturate(_RBIntensity)',
        'output.sceneMV = float4(0.0, 0.0, 1.0, 0.0)',
        'Tags { "LightMode"="Distortion" }',
        '"EndfieldSceneMVMRT"="ExactSelectedFiftyThree"',
    ):
        assert token in shader, token

    digest = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest().upper()
    print(
        "verified CharInfo CharEffect contract: "
        f"nodes=2 material=4388811075012960551 texture=-7046954404783675798 "
        f"shaderVariant=HG_ENABLE_MV+_USE_RBOFFSET contractSha256={digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
