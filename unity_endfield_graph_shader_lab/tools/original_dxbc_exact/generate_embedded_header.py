#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED = {
    "deferred_vertex": (
        496,
        "a6afe2c96caa3fd940004ce9ee725886d0f8df683d5f73403278743e32563155",
    ),
    "deferred_pixel": (
        48_984,
        "b21a1e35eda1c5bcb60198c6af313799ddcc94d0cee0be9025938f3ba8c56b6f",
    ),
    "m27_vertex": (
        8_148,
        "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c",
    ),
    "m27_pixel": (
        8_200,
        "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e",
    ),
    "m14_vertex": (
        6_148,
        "62a5ce6c09171de949ade143b0520cef5b6f899137c1d0190d4014b053eee698",
    ),
    "m14_pixel": (
        5_072,
        "5558deddb1ee6188dfb530e5be89d86d67352362384fababc585e778b78b99e7",
    ),
    "m13_vertex": (
        5_672,
        "96a93dcb3965cbedd03699822fac90d431a43353b56088035f44014d2c273030",
    ),
    "m13_pixel": (
        11_652,
        "0265c7a6806a095fef85fe2f14360cf0874e521d2510c4740db4e2ae341a3c5c",
    ),
    "uber_vertex": (
        608,
        "a8c084c37eba0ecc78f26d984a2b8c658f8d743002048c84431807d9dee0ce4e",
    ),
    "uber_normal_pixel": (
        3_416,
        "de96a55f118305ea6145db7aae1789640b1f5b3355cfae87b342e05adaee80dd",
    ),
    "uber_pixel": (
        4_216,
        "86a732cef7eedb150cbcafb35a994c1e3f7b1ef837dc618131a95e9dfe030c97",
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


def render_digest(name: str, digest: bytes) -> str:
    values = ", ".join(f"0x{value:02x}" for value in digest)
    return f"inline constexpr unsigned char {name}[32] = {{{values}}};\n"


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
    parser.add_argument("--deferred-vertex", type=Path, required=True)
    parser.add_argument("--deferred-pixel", type=Path, required=True)
    parser.add_argument("--m27-vertex", type=Path, required=True)
    parser.add_argument("--m27-pixel", type=Path, required=True)
    parser.add_argument("--m14-vertex", type=Path, required=True)
    parser.add_argument("--m14-pixel", type=Path, required=True)
    parser.add_argument("--m13-vertex", type=Path, required=True)
    parser.add_argument("--m13-pixel", type=Path, required=True)
    parser.add_argument("--uber-vertex", type=Path, required=True)
    parser.add_argument("--uber-normal-pixel", type=Path, required=True)
    parser.add_argument("--uber-pixel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    deferred_vertex = checked(args.deferred_vertex, "deferred_vertex")
    deferred_pixel = checked(args.deferred_pixel, "deferred_pixel")
    m27_vertex = checked(args.m27_vertex, "m27_vertex")
    m27_pixel = checked(args.m27_pixel, "m27_pixel")
    m14_vertex = checked(args.m14_vertex, "m14_vertex")
    m14_pixel = checked(args.m14_pixel, "m14_pixel")
    m13_vertex = checked(args.m13_vertex, "m13_vertex")
    m13_pixel = checked(args.m13_pixel, "m13_pixel")
    uber_vertex = checked(args.uber_vertex, "uber_vertex")
    uber_normal_pixel = checked(
        args.uber_normal_pixel, "uber_normal_pixel")
    uber_pixel = checked(args.uber_pixel, "uber_pixel")
    text = (
        "#pragma once\n"
        "#include <cstddef>\n\n"
        + render_array("g_EndfieldSelectedVertexDxbc", deferred_vertex)
        + "\n"
        + render_array("g_EndfieldSelectedPixelDxbc", deferred_pixel)
        + "\n"
        + render_array("g_EndfieldM27VertexDxbc", m27_vertex)
        + "\n"
        + render_array("g_EndfieldM27PixelDxbc", m27_pixel)
        + "\n"
        + render_digest(
            "g_EndfieldM27VertexDxbcSha256", hashlib.sha256(m27_vertex).digest()
        )
        + render_digest(
            "g_EndfieldM27PixelDxbcSha256", hashlib.sha256(m27_pixel).digest()
        )
        + "\n"
        + render_array("g_EndfieldM14VertexDxbc", m14_vertex)
        + "\n"
        + render_array("g_EndfieldM14PixelDxbc", m14_pixel)
        + "\n"
        + render_digest(
            "g_EndfieldM14VertexDxbcSha256", hashlib.sha256(m14_vertex).digest()
        )
        + render_digest(
            "g_EndfieldM14PixelDxbcSha256", hashlib.sha256(m14_pixel).digest()
        )
        + "\n"
        + render_array("g_EndfieldM13VertexDxbc", m13_vertex)
        + "\n"
        + render_array("g_EndfieldM13PixelDxbc", m13_pixel)
        + "\n"
        + render_digest(
            "g_EndfieldM13VertexDxbcSha256", hashlib.sha256(m13_vertex).digest()
        )
        + render_digest(
            "g_EndfieldM13PixelDxbcSha256", hashlib.sha256(m13_pixel).digest()
        )
        + "\n"
        + render_array("g_EndfieldUberVertexDxbc", uber_vertex)
        + "\n"
        + render_array("g_EndfieldUberNormalPixelDxbc", uber_normal_pixel)
        + "\n"
        + render_array("g_EndfieldUberPixelDxbc", uber_pixel)
        + "\n"
        + render_digest(
            "g_EndfieldUberVertexDxbcSha256", hashlib.sha256(uber_vertex).digest()
        )
        + render_digest(
            "g_EndfieldUberNormalPixelDxbcSha256",
            hashlib.sha256(uber_normal_pixel).digest(),
        )
        + render_digest(
            "g_EndfieldUberPixelDxbcSha256", hashlib.sha256(uber_pixel).digest()
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
