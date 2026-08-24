#!/usr/bin/env python3
"""Verify the exact Endminf overview burst-stripe texture binding."""

from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
SOURCE = (
    REPO
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D"
    / "T_fx_star_07_D_pEE1B76A5C2D86411.png"
)
IMPORTER = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldEndminfOverviewEffectImporter.cs"
)
GENERATED = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf"
    / "Effects/Overview"
)
TEXTURE = GENERATED / "Textures/T_fx_star_07_D_pEE1B76A5C2D86411.png"
TEXTURE_META = TEXTURE.with_suffix(TEXTURE.suffix + ".meta")
MATERIAL = GENERATED / "Materials/M_fx_endminm_gfx_09_p632B1622242536EC.mat"
EXPECTED_SHA256 = "f4d1623d32b3144b10bcfc1ff9e1fb6a0eca8bee5cc182a5502a6c82fd8b13ea"


def main() -> int:
    source = SOURCE.read_bytes()
    assert hashlib.sha256(source).hexdigest() == EXPECTED_SHA256
    assert source[:8] == b"\x89PNG\r\n\x1a\n"
    ihdr_length = struct.unpack(">I", source[8:12])[0]
    assert source[12:16] == b"IHDR" and ihdr_length == 13
    width, height, bit_depth, color_type = struct.unpack(">IIBB", source[16:26])
    assert (width, height, bit_depth, color_type) == (512, 512, 8, 6)

    importer = IMPORTER.read_text(encoding="utf-8")
    for token in (
        "0xEE1B76A5C2D86411UL",
        EXPECTED_SHA256,
        "BuildExactEndminfDecodedTexture",
        "DoesSourceTextureHaveAlpha()",
        "Recovered Endminf material retained a missing texture binding",
    ):
        assert token in importer, token

    assert TEXTURE.read_bytes() == source
    meta = TEXTURE_META.read_text(encoding="utf-8")
    match = re.search(r"(?m)^guid: ([0-9a-f]{32})$", meta)
    assert match is not None
    material = MATERIAL.read_text(encoding="utf-8")
    assert "- _MainTex:" in material
    assert f"guid: {match.group(1)}" in material

    print(
        "verified Endminf overview stripe texture: "
        f"sha256={EXPECTED_SHA256} rgba={width}x{height} "
        "binding=M_fx_endminm_gfx_09._MainTex"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
