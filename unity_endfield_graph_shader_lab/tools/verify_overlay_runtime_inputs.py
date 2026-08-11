#!/usr/bin/env python3
"""Verify retail OverlayShadow jitter and clustered-visibility inputs.

This verifier is intentionally pinned to the currently installed Endfield
binary and the exact selected OverlayShadow DXBC sidecar.  It proves only the
normal, non-forced jitter path and the resource ABI consumed by that shader;
the IFix-wrapped TAA history setup and retail draw scheduling remain outside
the closed boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab"

GAME_ROOT = Path(
    os.environ.get("ENDFIELD_GAME_ROOT", r"D:\Program Files\Endfield Game")
)
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
GLOBAL_METADATA = (
    GAME_ROOT
    / "Endfield_Data"
    / "il2cpp_data"
    / "Metadata"
    / "global-metadata.dat"
)

BYTECODE_ROOT = (
    PROJECT_ROOT
    / "scratch"
    / "overlay_taa_volume"
    / "shader_export"
    / "Shader"
    / "HGRP_CharacterNPR_OverlayShadow_p1B3C2C084B83F71F.shader.bytecode"
)
SELECTED_DXBC = BYTECODE_ROOT / "0031_endfield_dxbc_1.dxbc"
SELECTED_METADATA = Path(str(SELECTED_DXBC) + ".metadata.json")
CONVERTED_SHADER = (
    PROJECT_ROOT
    / "scratch"
    / "overlay_runtime_recovery"
    / "animestudio_convert"
    / "Shader"
    / "HGRP_CharacterNPR_OverlayShadow_p1B3C2C084B83F71F.shader"
)

RECOVERED_SHADER = (
    ASSET_ROOT
    / "Shaders"
    / "Recovered"
    / "EndfieldCharacterOverlayShadowRecovered.shader"
)
PIPELINE = ASSET_ROOT / "Runtime" / "Rendering" / "HGCompatRenderPipeline.cs"
LIGHTING_INCLUDE = (
    ASSET_ROOT
    / "Shaders"
    / "HGRPCompat"
    / "EndfieldHGRPCharacterLighting.cginc"
)
LIGHT_BINNING = (
    ASSET_ROOT
    / "Runtime"
    / "Rendering"
    / "EndfieldRecoveredLightBinning.cs"
)

EXPECTED_HASHES = {
    GAME_ASSEMBLY: "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    GLOBAL_METADATA: "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    SELECTED_DXBC: "6997620071f0b1082abc4193cb173f410ff64cb8856ab81f2a8d1a9abb7d21d2",
    SELECTED_METADATA: "076e3d89382febcf01b643d7e1b4d6db320e1f462d7ddcb4bbdeae5153acf391",
}

# File offsets and lengths are valid only under the hash-pinned GameAssembly.
METHOD_SLICES = {
    "HGCamera.GetJitteredProjectionMatrix": (
        0x3269EB0,
        0x500,
        "e588eaee2d1c9b6b3283ce9179e078844777316e39a67bc4158b2cab6d3127d0",
    ),
    "HGCamera.UpdateShaderVariablesGlobalCB.head": (
        0x32DE620,
        0x500,
        "be394bd59d37eca9a14917221c31b1f5f25254ae7ab4e27b0629676b490af361",
    ),
    "TAAUPassConstructor.ConstructTAAUPasses": (
        0x9BD16C4,
        0xBC,
        "5010ae51506da74af990a051019dedc4895eaf681843c1f6b0909cb5de594db9",
    ),
    "TAAUPassConstructor.PrepareShaderVariablesGlobal": (
        0x9BD18EC,
        0x54,
        "df239954285c0f372665a12b9d18e585b5e55b8ee0eb1e81bd5fe1f0b5c261e2",
    ),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{label}: missing {token!r}")


def verify_hashes() -> None:
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            raise AssertionError(f"missing exact retail evidence: {path}")
        actual = sha256(path)
        if actual != expected:
            raise AssertionError(
                f"{path}: expected SHA-256 {expected}, found {actual}"
            )


def named_constant_buffer(metadata: dict, name: str) -> dict:
    matches = [
        value
        for value in metadata["ConstantBufferParameters"]
        if value["Name"] == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one {name} constant buffer, found {len(matches)}")
    return matches[0]


def vector_layout(buffer: dict) -> dict[str, tuple[int, int]]:
    return {
        value["Name"]: (value["Index"], value["ArraySize"])
        for value in buffer["VectorParameters"]
    }


def verify_selected_shader_abi() -> None:
    metadata = json.loads(SELECTED_METADATA.read_text(encoding="utf-8-sig"))
    assert metadata["SourcePassIndex"] == 1
    assert metadata["SourcePassName"] == "OverlayShadow"
    assert metadata["SourceCompilerPlatform"] == "d3d11"
    assert metadata["SourceCompiledKeywords"] == [
        "DISABLE_DRAW_UNDER_HAIR",
        "SRP_INSTANCING_ON",
    ]
    # AnimeStudio currently labels the combined serialized program as vertex;
    # the _1 filename and DXBC execution signature select its fragment member.
    assert metadata["SourceSerializedProgramStage"] == "vertex"

    buffers = {value["Name"]: value for value in metadata["BufferParameters"]}
    assert buffers["_GlobalBinningBuffer"]["Index"] == 50

    globals_layout = vector_layout(named_constant_buffer(metadata, "ShaderVariablesGlobal"))
    assert globals_layout["_TaaJitterStrength"] == (0x130, 0)
    assert globals_layout["_BinningBufferOffsets"] == (0x1C0, 0)

    binning_layout = vector_layout(
        named_constant_buffer(metadata, "_LightBinningConstants")
    )
    assert binning_layout["_NumTilesX"] == (20, 0)
    assert binning_layout["_NumZBinSlice"] == (28, 0)
    assert binning_layout["_InvZBinSlice"] == (44, 0)

    light_layout = vector_layout(named_constant_buffer(metadata, "_LightDataBuffer"))
    assert light_layout["_DirectionalLightDirection"] == (0, 0)
    assert light_layout["_PunctualLightData"] == (96, 2048)

    converted = CONVERTED_SHADER.read_text(encoding="utf-8-sig")
    require_tokens(
        converted,
        (
            "r1.xy = cb1[19].zw * r0.ww;",
            "o3.xy = r1.xy * float2(2,-2) + r3.xy;",
            "r3.w = r5.w;",
            "r0.w = 1 + -r3.w;",
            "r4.w = r1.w * r0.w;",
        ),
        "hash-pinned selected OverlayShadow conversion",
    )


def find_all(source: bytes, needle: bytes) -> list[int]:
    result: list[int] = []
    cursor = 0
    while True:
        found = source.find(needle, cursor)
        if found < 0:
            return result
        result.append(found)
        cursor = found + 1


def call_target(method_va: int, body: bytes, call_offset: int) -> int:
    if body[call_offset] != 0xE8:
        raise AssertionError(f"expected rel32 call at +0x{call_offset:x}")
    displacement = struct.unpack_from("<i", body, call_offset + 1)[0]
    return method_va + call_offset + 5 + displacement


def verify_native_producer() -> None:
    game_assembly = GAME_ASSEMBLY.read_bytes()
    for name, (offset, size, expected_hash) in METHOD_SLICES.items():
        body = game_assembly[offset : offset + size]
        if len(body) != size:
            raise AssertionError(f"{name}: truncated method slice")
        assert sha256_bytes(body) == expected_hash, name

    # Normal path: taaFrameIndex at HGCamera+0x758 is masked to 1024 phases;
    # base-2/base-3 radical inverses are stored as raw and normalized XY at
    # HGCamera+0x68.  The whole method slice is hash-pinned above, while these
    # unique anchors prevent a misleading offset-only match.
    anchors = {
        "Halton normal-path start": bytes.fromhex(
            "8b 87 58 07 00 00 0f 57 f6 f3 44 0f 10 05"
        ),
        "taaJitter store": bytes.fromhex(
            "0f 11 44 24 40 0f 11 47 68"
        ),
        # movups xmm0,[rbx+68h]; movups [rdi+130h],xmm0
        "taaJitter to ShaderVariablesGlobal": bytes.fromhex(
            "0f 10 43 68 0f 11 87 30 01 00 00"
        ),
    }
    for label, anchor in anchors.items():
        hits = find_all(game_assembly, anchor)
        if len(hits) != 1:
            raise AssertionError(f"{label}: expected one anchor, found {hits}")

    construct = game_assembly[0x9BD16C4 : 0x9BD16C4 + 0xBC]
    assert call_target(0x189BD30C4, construct, 0x45) == 0x189BD1948
    assert call_target(0x189BD30C4, construct, 0x56) == 0x189BD25A0
    assert call_target(0x189BD30C4, construct, 0x6D) == 0x189BD2AF0


def radical_inverse(value: int, base: int) -> float:
    result = 0.0
    weight = 1.0 / base
    while value > 0:
        value, digit = divmod(value, base)
        result += digit * weight
        weight /= base
    return result


def retail_jitter(frame_index: int, width: int, height: int, scale: float) -> tuple[float, ...]:
    phase = (frame_index & 0x3FF) + 1
    raw_x = radical_inverse(phase, 2) - 0.5
    raw_y = radical_inverse(phase, 3) - 0.5
    return (
        raw_x,
        raw_y,
        raw_x / (width * scale),
        raw_y / (height * scale),
    )


def verify_jitter_reference() -> None:
    expected_raw = (
        (0.0, -1.0 / 6.0),
        (-0.25, 1.0 / 6.0),
        (0.25, -7.0 / 18.0),
    )
    for frame, expected in enumerate(expected_raw):
        actual = retail_jitter(frame, 1920, 1080, 1.0)
        assert math.isclose(actual[0], expected[0], abs_tol=1e-12)
        assert math.isclose(actual[1], expected[1], abs_tol=1e-12)
        assert math.isclose(actual[2], expected[0] / 1920, abs_tol=1e-12)
        assert math.isclose(actual[3], expected[1] / 1080, abs_tol=1e-12)


def verify_exact_lab_neutral_state() -> None:
    shader = RECOVERED_SHADER.read_text(encoding="utf-8-sig")
    pipeline = PIPELINE.read_text(encoding="utf-8-sig")
    lighting = LIGHTING_INCLUDE.read_text(encoding="utf-8-sig")
    binning = LIGHT_BINNING.read_text(encoding="utf-8-sig")
    require_tokens(
        shader,
        (
            "_EndfieldRecoveredOverlayTaaJitterStrength.zw *",
            "o.pos.w * float2(2.0, -2.0);",
            "clustered punctual-light records",
            "EndfieldHGRecoveredOverlayLocalVolumeOcclusion(",
            "1.0h - aggregateLocalVolumeOcclusion;",
        ),
        "recovered OverlayShadow runtime inputs",
    )
    require_tokens(
        pipeline,
        (
            "does not run the retail TAA",
            "sample/history/resolve lifecycle",
            "OverlayTaaJitterStrengthId, Vector4.zero",
            "recoveredLightBinning.PrepareCamera(",
            "new Vector4(0.0f, 1.0f, 1.0f, 1.0f)",
        ),
        "exact compatibility neutral state",
    )
    require_tokens(
        lighting,
        (
            "EndfieldHGRecoveredOverlayLocalVolumeOcclusion(",
            "nprType == 16",
            "additionalData.x + _CharacterParams12.z < 0.5",
            "nprType != 4",
            "surfaceToLight = coneAxis * dot(surfaceToLight, coneAxis);",
            "falloffExponent = max(2.0 * lightNprData.y, 0.1);",
            "attenuation * lightNprData.x + aggregateOcclusion",
        ),
        "source-backed isolated local-volume consumer",
    )
    require_tokens(
        binning,
        (
            "private const int TileSize = EndfieldRecoveredLightBinningConstantsContract.TileSize;",
            "private const int SliceCount = EndfieldRecoveredLightBinningConstantsContract.SliceCount;",
            "private const int WordsPerBin = 8;",
            "commandBuffer.SetGlobalFloat(GlobalAvailableId, 1.0f);",
            "commandBuffer.SetGlobalFloat(GlobalAvailableId, 0.0f);",
        ),
        "source-backed isolated light-bin producer",
    )


def main() -> int:
    verify_hashes()
    verify_selected_shader_abi()
    verify_native_producer()
    verify_jitter_reference()
    verify_exact_lab_neutral_state()
    print(
        "Overlay runtime-input verification passed: the selected retail DXBC "
        "consumes ShaderVariablesGlobal._TaaJitterStrength at 0x130 and "
        "clustered _GlobalBinningBuffer/_PunctualLightData records; the "
        "hash-pinned HGCamera normal path produces packed Halton raw/normalized "
        "jitter and uploads HGCamera+0x68 to CB+0x130; TAA pass construction is "
        "Dilation -> MaskDilation -> Resolve. The lab's non-jittered projection "
        "keeps jitter neutral; the isolated CharInfo rig now supplies the exact "
        "32-pixel/2048-slice membership and type-4 Fog visibility subset, while "
        "missing producer state still binds neutral zero occlusion. IFix-wrapped "
        "history constants remain unresolved; shared-depth "
        "overlay scheduling is verified separately by "
        "verify_face_eye_overlay_chronology.py."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
