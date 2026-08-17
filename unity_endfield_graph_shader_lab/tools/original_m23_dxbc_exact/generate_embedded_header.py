#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED = {
    "vertex": (10720, "7d0a508f7b1e5c9aef0b89489feae97f8669a8cddaba1de0ccc0e26fd0eb2ca0"),
    "pixel": (8100, "0ff508aa08112122c14a3ece17d12f15778eaf39ad0c639c946512dc996b6f83"),
}

def checked(path: Path, stage: str) -> bytes:
    value = path.read_bytes()
    expected_size, expected_hash = EXPECTED[stage]
    actual = hashlib.sha256(value).hexdigest()
    if (len(value), actual) != (expected_size, expected_hash):
        raise SystemExit(f"{stage} M23 DXBC drift: size={len(value)} sha256={actual}")
    return value

def render(name: str, value: bytes) -> str:
    rows = ["    " + ", ".join(f"0x{x:02x}" for x in value[i:i+16]) + "," for i in range(0, len(value), 16)]
    return f"inline constexpr unsigned char {name}[] = {{\n" + "\n".join(rows) + f"\n}};\ninline constexpr std::size_t {name}Size = sizeof({name});\n"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertex", type=Path, required=True)
    parser.add_argument("--pixel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    vertex = checked(args.vertex, "vertex")
    pixel = checked(args.pixel, "pixel")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("#pragma once\n#include <cstddef>\n\n" + render("g_EndfieldM23VertexDxbc", vertex) + "\n" + render("g_EndfieldM23PixelDxbc", pixel), encoding="utf-8", newline="\n")
    print(args.output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
