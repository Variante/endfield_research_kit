#!/usr/bin/env python3
"""Normalize Ruri's frame-proven Endminf deferred retail HLSL aliases."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BUFFER_HEADER_RE = re.compile(
    r"ByteAddressBuffer _9 : register\(t0, space0\);.*?"
    r"(?=Texture2D<float4> _13 : register\(t1, space0\);)",
    re.DOTALL,
)
BUFFER_HEADER = """ByteAddressBuffer _EndfieldBufferT0 : register(t0);
cbuffer EndfieldCB0 : register(b0) { float4 EndfieldCB0_f_0[45] : packoffset(c0); };
cbuffer EndfieldCB1 : register(b1) { float4 EndfieldCB1_f_0[157] : packoffset(c0); };
cbuffer EndfieldCB2 : register(b2) { float4 EndfieldCB2_f_0[259] : packoffset(c0); };
cbuffer EndfieldCB3 : register(b3) { float4 EndfieldCB3_f_0[3] : packoffset(c0); };
cbuffer EndfieldCB4 : register(b4) { float4 EndfieldCB4_f_0[2054] : packoffset(c0); };
cbuffer EndfieldCB5 : register(b5) { float4 EndfieldCB5_f_0[401] : packoffset(c0); };
cbuffer EndfieldCB6 : register(b6) { float4 EndfieldCB6_f_0[216] : packoffset(c0); };
cbuffer EndfieldCB7 : register(b7) { float4 EndfieldCB7_f_0[15] : packoffset(c0); };
cbuffer EndfieldCB8 : register(b8) { float4 EndfieldCB8_f_0[160] : packoffset(c0); };
cbuffer EndfieldCB9 : register(b9) { float4 EndfieldCB9_f_0[4] : packoffset(c0); };

"""
CB_ALIASES = {
    "_48_m0": "EndfieldCB0_f_0",
    "_54_m0": "EndfieldCB0_f_0",
    "_59_m0": "EndfieldCB1_f_0",
    "_64_m0": "EndfieldCB1_f_0",
    "_69_m0": "EndfieldCB2_f_0",
    "_74_m0": "EndfieldCB2_f_0",
    "_79_m0": "EndfieldCB3_f_0",
    "_83_m0": "EndfieldCB4_f_0",
    "_87_m0": "EndfieldCB4_f_0",
    "_91_m0": "EndfieldCB5_f_0",
    "_95_m0": "EndfieldCB5_f_0",
    "_99_m0": "EndfieldCB6_f_0",
    "_103_m0": "EndfieldCB7_f_0",
    "_107_m0": "EndfieldCB8_f_0",
    "_111_m0": "EndfieldCB8_f_0",
    "_116_m0": "EndfieldCB9_f_0",
    "_121_m0": "EndfieldCB9_f_0",
}
TEXTURE_IDS = {
    13: 1, 14: 2, 15: 3, 16: 4, 19: 5, 20: 6, 21: 7,
    22: 8, 23: 9, 24: 10, 25: 11, 26: 12, 27: 13, 28: 14,
    31: 15, 32: 16, 33: 17, 34: 18, 35: 19, 36: 20,
    37: 21, 38: 22, 39: 23, 40: 24, 41: 25, 42: 26, 43: 27,
}


def normalize(source: str) -> str:
    normalized, replacements = BUFFER_HEADER_RE.subn(BUFFER_HEADER, source, count=1)
    if replacements != 1:
        raise ValueError("Ruri constant-buffer alias header did not match")
    normalized = re.sub(r"\b_9\b", "_EndfieldBufferT0", normalized)
    normalized = normalized.replace("_EndfieldBufferT0.Load<uint>(", "_EndfieldBufferT0.Load(")
    for old, new in CB_ALIASES.items():
        normalized = re.sub(rf"\b{re.escape(old)}\b", new, normalized)
    for old, slot in sorted(TEXTURE_IDS.items(), reverse=True):
        normalized = re.sub(
            rf"\b_{old}\b", f"_EndfieldTextureT{slot}", normalized
        )
    normalized = normalized.replace(", space0)", ")")
    for slot in range(10):
        count = len(re.findall(rf"register\(b{slot}\)", normalized))
        if count != 1:
            raise ValueError(f"normalized b{slot} declaration count is {count}, expected 1")
    for slot in range(1, 28):
        token = f"_EndfieldTextureT{slot} : register(t{slot})"
        if token not in normalized:
            raise ValueError(f"normalized texture declaration missing: {token}")
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = normalize(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
