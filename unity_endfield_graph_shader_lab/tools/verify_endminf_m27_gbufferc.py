#!/usr/bin/env python3
"""Verify the frame-7439 M27 GBufferC source-port contract."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SHADER = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/"
    "EndfieldEndminfM27HGBuffer.shader"
)
FRAGMENT = (
    REPO_ROOT
    / "scratch/animestudio/endminf_liteffect_shader/"
    "live_subprogram113/fragment.hlsl"
)
FRAME = (
    REPO_ROOT
    / "scratch/reverse_engineering/endfield_capture/"
    "20260826T042005Z/graphics/frames/7439/metadata.json"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("FAIL: " + message)


def captured_ps_b3() -> tuple[tuple[float, ...], tuple[float, ...]]:
    metadata = json.loads(FRAME.read_text(encoding="utf-8"))
    draws = [
        draw
        for draw in metadata["drawRecords"]
        if draw.get("priorityM27Geometry")
        and draw.get("count") == 1080
        and draw.get("instanceCount") == 1
    ]
    require(len(draws) == 1, "frame 7439 must contain one exact M27 draw")
    ranges = [
        cb
        for cb in draws[0]["constantBuffers"]
        if cb["stage"] == 4 and cb["slot"] == 3
    ]
    require(len(ranges) == 1, "M27 PS b3 range must be unique")
    values = struct.unpack(
        "<" + "f" * (len(ranges[0]["dataHex"]) // 8),
        bytes.fromhex(ranges[0]["dataHex"]),
    )
    require(len(values) >= 36, "captured PS b3 must include c4 and c8")
    return tuple(values[16:20]), tuple(values[32:36])


def main() -> None:
    c4, c8 = captured_ps_b3()
    require(c4 == (0.0, 0.0, 1.0, 0.0), f"unexpected captured b3 c4: {c4}")
    require(c8 == (1.0, 1.0, 1.0, 1.0), f"unexpected captured b3 c8: {c8}")

    fragment = FRAGMENT.read_text(encoding="utf-8")
    for exact in (
        "float _284 = asfloat(asuint(_45_m0[4u].z));",
        "float _298 = asfloat(asuint(_45_m0[4u].x));",
        "SV_Target_4.x = mad(_298, _274 - _288, _288);",
        "SV_Target_4.y = mad(_298, _275 - _289, _289);",
        "SV_Target_4.z = mad(_298, _276 - _290, _290);",
        "SV_Target_4.w = 0.0f;",
    ):
        require(exact in fragment, "decompiled equation drifted: " + exact)

    shader = SHADER.read_text(encoding="utf-8")
    require(
        re.search(
            r"float3\s+tintedBase\s*=\s*saturate\s*\(\s*"
            r"baseSample\.rgb\s*\*\s*_BaseColor\.rgb\s*\*\s*"
            r"_BaseColorBrighterScale\s*\)\s*;",
            shader,
        ) is not None,
        "source port must map b3 c4.z to _BaseColorBrighterScale",
    )
    require(
        re.search(
            r"output\.gBufferC\s*=\s*float4\s*\(\s*lerp\s*\(\s*"
            r"tintedBase\s*,\s*_BaseColor\.rgb\s*,\s*"
            r"_BaseColorTintCover\s*\)\s*,\s*0\.0\s*\)\s*;",
            shader,
        ) is not None,
        "source port must map b3 c4.x to _BaseColorTintCover and Target4.w=0",
    )
    require(
        re.search(
            r"_BaseColorBrighterScale\s*\([^\n]*\)\s*=\s*1(?:\.0)?\s*$",
            shader,
            re.MULTILINE,
        ) is not None,
        "material property default must preserve captured b3 c4.z=1",
    )

    print(json.dumps({
        "status": "pass",
        "frame": 7439,
        "draw_indices": 1080,
        "ps_b3_c4": c4,
        "ps_b3_c8": c8,
        "mapping": {
            "b3_c4_x": "_BaseColorTintCover",
            "b3_c4_z": "_BaseColorBrighterScale",
            "b3_c8_xyz": "_BaseColor.rgb",
            "ps_t0": "_BaseColorMap",
            "sv_target4_w": 0.0,
        },
    }, indent=2))


if __name__ == "__main__":
    main()
