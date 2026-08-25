#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED = {
    "vertex": (
        496,
        "a6afe2c96caa3fd940004ce9ee725886d0f8df683d5f73403278743e32563155",
    ),
    "pixel": (
        50_296,
        "ca09544336a4d56e78c28a080da2df320c11cd21a896dacfdcdcac2b400752e5",
    ),
}


def render_array(name: str, data: bytes) -> str:
    rows = []
    for start in range(0, len(data), 16):
        chunk = data[start : start + 16]
        rows.append("    " + ", ".join(f"0x{value:02x}" for value in chunk) + ",")
    return (
        f"inline constexpr unsigned char {name}[] = {{\n"
        + "\n".join(rows)
        + "\n};\n"
        + f"inline constexpr std::size_t {name}Size = sizeof({name});\n"
    )


def checked(path: Path, stage: str) -> bytes:
    data = path.read_bytes()
    expected_size, expected_hash = EXPECTED[stage]
    actual_hash = hashlib.sha256(data).hexdigest()
    if len(data) != expected_size or actual_hash != expected_hash:
        raise SystemExit(
            f"{stage} DXBC drift: size={len(data)} sha256={actual_hash}; "
            f"expected size={expected_size} sha256={expected_hash}"
        )
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertex", type=Path, required=True)
    parser.add_argument("--pixel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    vertex = checked(args.vertex, "vertex")
    pixel = checked(args.pixel, "pixel")
    text = (
        "#pragma once\n"
        "#include <cstddef>\n\n"
        + render_array("g_EndfieldSelectedVertexDxbc", vertex)
        + "\n"
        + render_array("g_EndfieldSelectedPixelDxbc", pixel)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
