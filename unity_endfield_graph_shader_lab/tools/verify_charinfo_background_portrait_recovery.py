#!/usr/bin/env python3
"""Verify the source-authored CharInfo background portrait recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
ORIGINAL_DATA = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoBackgroundPortrait"
)
MANIFEST = ORIGINAL_DATA / "source_manifest.json"
RUNTIME = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Rendering"
    / "EndfieldRecoveredCharInfoBackgroundPortrait.cs"
)
BUILDER = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldRecoveredCharInfoBackgroundPortraitBuilder.cs"
)
SHADER = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Shaders"
    / "Recovered"
    / "EndfieldCharInfoBackgroundPortraitRecovered.shader"
)
PIPELINE = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Rendering"
    / "HGCompatRenderPipeline.cs"
)
SETUP = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldManifestCharacterSetup.cs"
)
SCENES = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Scenes"
)
CANONICAL_SCENES = (
    SCENES / "CharacterRecoveryViewer.unity",
    SCENES / "CharacterRenderStyleFast.unity",
)
PORTRAIT_SCRIPT_GUID = "b18bbd5bbbaefe247a740f1c07e01135"
WRAPPERS = {
    "wulfa": PROJECT / "render_charinfo_background_portrait_wulfa.bat",
    "zhuangfy": PROJECT / "render_charinfo_background_portrait_zhuangfy.bat",
}
SOURCE_TEXTURES = {
    "wulfa": (
        REPO
        / "export_full"
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "convert_by_type"
        / "Texture2D"
        / "bg_charinfo_chr_0028_wulfa_p98B763E6C1636E1F.png",
        "426f6391011a58f88f2c51cbf1809f6068b07f10a17a08336528bdc3c20d9225",
    ),
    "zhuangfy": (
        REPO
        / "export_full"
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "convert_by_type"
        / "Texture2D"
        / "bg_charinfo_chr_0030_zhuangfy_p854C77D240F142E7.png",
        "2b214668ca5b48ef6d9ecbee6e3dffa50c9e7536d47c65d5272da673cf472a77",
    ),
}
GENERATED_TEXTURES = {
    "wulfa": (
        PROJECT
        / "Assets"
        / "EndfieldGraphShaderLab"
        / "Generated"
        / "CharInfoBackgroundPortrait"
        / "Textures"
        / "bg_charinfo_chr_0028_wulfa.png"
    ),
    "zhuangfy": (
        PROJECT
        / "Assets"
        / "EndfieldGraphShaderLab"
        / "Generated"
        / "CharInfoBackgroundPortrait"
        / "Textures"
        / "bg_charinfo_chr_0030_zhuangfy.png"
    ),
}
SOURCE_TEXTURE_RECTS = {
    "wulfa": (211.07613, 55.051315, 605.87256, 904.87256),
    "zhuangfy": (209.01112, 98.051315, 675.9128, 923.94867),
}
GENERATED_MESHES = {
    "wulfa": (
        PROJECT
        / "Assets"
        / "EndfieldGraphShaderLab"
        / "Generated"
        / "CharInfoBackgroundPortrait"
        / "Meshes"
        / "RecoveredCharInfoBackgroundPortraitWulfaTightQuad.asset"
    ),
    "zhuangfy": (
        PROJECT
        / "Assets"
        / "EndfieldGraphShaderLab"
        / "Generated"
        / "CharInfoBackgroundPortrait"
        / "Meshes"
        / "RecoveredCharInfoBackgroundPortraitZhuangfyTightQuad.asset"
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    require(header[:8] == b"\x89PNG\r\n\x1a\n", f"not a PNG: {path}")
    require(header[12:16] == b"IHDR", f"missing PNG IHDR: {path}")
    return struct.unpack(">II", header[16:24])


def verify_generated_mesh(actor: str) -> str:
    path = GENERATED_MESHES[actor]
    require(path.is_file(), f"missing generated {actor} tight quad: {path}")
    asset = path.read_text(encoding="utf-8")
    expected_name = (
        "RecoveredCharInfoBackgroundPortraitWulfaTightQuad"
        if actor == "wulfa"
        else "RecoveredCharInfoBackgroundPortraitZhuangfyTightQuad"
    )
    require(f"m_Name: {expected_name}" in asset, f"{actor} tight-quad name drifted")
    require("m_VertexCount: 4" in asset, f"{actor} tight quad is not four vertices")
    require(
        "m_IndexBuffer: 000002000100000003000200" in asset,
        f"{actor} tight-quad winding drifted",
    )
    packed = re.search(r"_typelessdata: ([0-9a-fA-F]+)", asset)
    require(packed is not None, f"{actor} tight-quad vertex bytes are missing")
    vertex_bytes = bytes.fromhex(packed.group(1))
    require(len(vertex_bytes) == 80, f"{actor} tight-quad vertex bytes are not 80 bytes")
    actual = struct.unpack("<20f", vertex_bytes)

    x, y, width, height = SOURCE_TEXTURE_RECTS[actor]
    left = -0.5 + x / 1022.0
    bottom = -0.5 + y / 1022.0
    right = -0.5 + (x + width) / 1022.0
    top = -0.5 + (y + height) / 1022.0
    u_min = x / 1024.0
    v_min = y / 1024.0
    u_max = (x + width) / 1024.0
    v_max = (y + height) / 1024.0
    expected = (
        left, bottom, 0.0, u_min, v_min,
        right, bottom, 0.0, u_max, v_min,
        right, top, 0.0, u_max, v_max,
        left, top, 0.0, u_min, v_max,
    )
    for index, (actual_value, expected_value) in enumerate(zip(actual, expected)):
        require(
            math.isclose(actual_value, expected_value, rel_tol=0.0, abs_tol=1e-6),
            f"{actor} tight-quad float {index} drifted: "
            f"{actual_value} != {expected_value}",
        )
    return sha256(path)


def verify_scene_binding(path: Path) -> None:
    require(path.is_file(), f"missing canonical scene: {path}")
    scene = path.read_text(encoding="utf-8")
    game_object = re.search(
        r"--- !u!1 &(\d+)\nGameObject:\n(?:(?!\n--- !u!).)*?"
        r"  m_Layer: 16\n  m_Name: RecoveredCharInfoBackgroundPortrait\n"
        r"(?:(?!\n--- !u!).)*",
        scene,
        flags=re.DOTALL,
    )
    require(game_object is not None, f"{path.name}: portrait GameObject/layer binding missing")
    require(
        scene.count(f"guid: {PORTRAIT_SCRIPT_GUID}") == 1,
        f"{path.name}: expected exactly one portrait component",
    )
    component = re.search(
        rf"m_Script: \{{fileID: 11500000, guid: {PORTRAIT_SCRIPT_GUID}, type: 3\}}"
        r"(?:(?!\n--- !u!).)*",
        scene,
        flags=re.DOTALL,
    )
    require(component is not None, f"{path.name}: portrait component block missing")
    component_text = component.group(0)
    for field in (
        "portraitRenderer",
        "portraitMeshFilter",
        "wulfaMesh",
        "zhuangfyMesh",
        "wulfaTexture",
        "zhuangfyTexture",
        "sourceManifest",
        "actorRoot",
    ):
        match = re.search(rf"  {field}: \{{fileID: (-?\d+)", component_text)
        require(
            match is not None and int(match.group(1)) != 0,
            f"{path.name}: portrait field {field} is unbound",
        )


def verify_static(actor: str, *, verify_wrapper: bool = True) -> dict:
    required_paths = [MANIFEST, RUNTIME, BUILDER, SHADER, PIPELINE, SETUP]
    if verify_wrapper:
        required_paths.append(WRAPPERS[actor])
    for path in required_paths:
        require(path.is_file(), f"missing recovery file: {path}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(
        manifest.get("schema")
        == "endfield.charinfo.background-portrait.original-data.v1",
        "wrong portrait source-manifest schema",
    )
    require(
        manifest["prefab"]["settled_animation_alpha"] == 90 / 255,
        "settled source alpha is not 90/255",
    )
    require(
        manifest["material"]["specialized_ui_raw_depth_equation"]
        == "saturate(z_over_w - 0.011)",
        "selected original UI depth equation drifted",
    )
    require(manifest["prefab"]["canvas_game_object_layer"] == 16, "source UI layer drifted")
    require(
        manifest["prefab"]["canvas_override_sorting"] is False
        and manifest["prefab"]["canvas_sorting_layer_id"] == 0
        and manifest["prefab"]["canvas_sorting_order"] == 0,
        "source Canvas sorting contract drifted",
    )
    for actor_name, manifest_name in (("wulfa", "Wulfa"), ("zhuangfy", "Zhuangfy")):
        actor_manifest = manifest["actors"][manifest_name]
        require(
            actor_manifest["sprite_rect"] == [0.0, 0.0, 1022.0, 1022.0],
            f"{manifest_name} logical Sprite rect drifted",
        )
        require(
            actor_manifest["sprite_texture_rect"]
            == list(SOURCE_TEXTURE_RECTS[actor_name]),
            f"{manifest_name} tight textureRect drifted",
        )
        require(
            actor_manifest["sprite_mesh_type"] == "Tight",
            f"{manifest_name} Sprite mesh type drifted",
        )

    source_hashes: dict[str, str] = {}
    for name, (path, expected_hash) in SOURCE_TEXTURES.items():
        require(path.is_file(), f"missing original {name} portrait: {path}")
        actual_hash = sha256(path)
        require(actual_hash == expected_hash, f"original {name} hash drifted")
        source_hashes[name] = actual_hash
        generated = GENERATED_TEXTURES[name]
        require(generated.is_file(), f"missing generated {name} portrait: {generated}")
        require(sha256(generated) == expected_hash, f"generated {name} pixels drifted")

    generated_mesh_hashes = {
        name: verify_generated_mesh(name) for name in GENERATED_MESHES
    }

    runtime = RUNTIME.read_text(encoding="utf-8")
    for token in (
        '"ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT"',
        "SourceUiLayer = 16",
        "SettledAnimationAlpha = 90.0f / 255.0f",
        "SourceCanvasScale = 0.0016f",
        "SourceCardSize = 900.0f",
        "SourceDepthOffset = 0.011f",
        "new Vector3(-300.0f, 50.0f, 0.0f)",
        "public MeshFilter portraitMeshFilter",
        "public Mesh wulfaMesh",
        "public Mesh zhuangfyMesh",
        "portraitMeshFilter.sharedMesh = mesh",
        "presentationProfile.overviewImageOffset",
        '$"overviewImgOffset=({overviewImageOffset.x:R},'
        '{overviewImageOffset.y:R},{overviewImageOffset.z:R}), "',
    ):
        require(token in runtime, f"runtime source contract missing {token!r}")

    shader = SHADER.read_text(encoding="utf-8")
    for token in (
        'Name "Default"',
        '"LightMode" = "SRPDefaultUnlit"',
        "ZWrite Off",
        "ZTest Always",
        "Blend One OneMinusSrcAlpha",
        "clip(_EndfieldRecoveredPostUberWorldUiReady - 0.5)",
        "Texture2D<float> _SceneDepth",
        "SamplerState sampler_LinearRepeat",
        "_SceneDepth.Sample(",
        "saturate(input.positionCS.z - _DepthOffset)",
        "clip(sceneLinearDepth - uiLinearDepth)",
        "sampleValue.rgb * _TintColor.rgb * alpha",
    ):
        require(token in shader, f"selected UI shader mapping missing {token!r}")

    pipeline = PIPELINE.read_text(encoding="utf-8")
    for token in (
        "TryPrepareRecoveredPostUberWorldUi(",
        "GraphicsFormat.D32_SFloat_S8_UInt",
        "GraphicsFormat.D24_UNorm_S8_UInt",
        "camera.cullingMask & ~(1 << EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer)",
        "DrawRecoveredPostUberWorldUi(",
        "new RenderTargetIdentifier(primarySceneDepth)",
        "commandBuffer.SetGlobalTexture(SceneDepthId, portraitSceneDepth)",
        "commandBuffer.SetRenderTarget(postColorTarget)",
        "commandBuffer.SetGlobalFloat(HGFlipYId, 0.0f)",
    ):
        require(token in pipeline, f"post-Uber portrait pipeline contract missing {token!r}")

    builder = BUILDER.read_text(encoding="utf-8")
    for token in (
        "SourceLogicalSpriteSize = 1022.0f",
        "SourceTextureSize = 1024.0f",
        "new Rect(211.07613f, 55.051315f, 605.87256f, 904.87256f)",
        "new Rect(209.01112f, 98.051315f, 675.9128f, 923.94867f)",
        "textureRect.xMin / SourceLogicalSpriteSize",
        "textureRect.xMin / SourceTextureSize",
        "textureRect.yMax / SourceTextureSize",
        "TextureImporterCompression.Uncompressed",
        "TextureImporterAlphaSource.FromInput",
        "importer.sRGBTexture = true",
        "importer.alphaIsTransparency = false",
        "portraitObject.layer = EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer",
        "renderer.sortingLayerID = 0",
        "renderer.sortingOrder = 0",
        source_hashes["wulfa"].upper(),
        source_hashes["zhuangfy"].upper(),
    ):
        require(token in builder, f"builder source contract missing {token!r}")

    setup = SETUP.read_text(encoding="utf-8")
    require(
        setup.count("EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(") >= 5,
        "normal/full/fast/capture/runtime scene paths do not all retain the portrait binding",
    )
    require(
        "Fast scene source-authored CharInfo portrait binding is missing or malformed."
        in setup,
        "fast-scene portrait assertion is missing",
    )
    for scene_path in CANONICAL_SCENES:
        verify_scene_binding(scene_path)

    if verify_wrapper:
        wrapper_path = WRAPPERS[actor]
        require(
            wrapper_path.is_file(),
            f"missing runtime wrapper: {wrapper_path}",
        )
        wrapper = wrapper_path.read_text(encoding="utf-8")
        for token in (
            'set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=1"',
            'set "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC=1"',
            'set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE=off"',
            'set "ENDFIELD_RECOVERED_CHARINFO_PRESENTATION=0"',
            'set "ENDFIELD_RECOVERED_PREGBUFFER_DIAGNOSTIC=0"',
            'set "ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_DIAGNOSTIC=0"',
            "verify_charinfo_background_portrait_recovery.py",
            "-force-d3d12",
        ):
            require(token in wrapper, f"{wrapper_path.name}: missing {token!r}")

    return {
        "manifest": str(MANIFEST),
        "manifestSha256": sha256(MANIFEST),
        "sourceTextureSha256": source_hashes,
        "generatedMeshSha256": generated_mesh_hashes,
        "runtimeWrapperChecked": verify_wrapper,
        "staticContractValid": True,
    }


def verify_runtime(actor: str, log_path: Path, png_path: Path) -> dict:
    require(log_path.is_file() and log_path.stat().st_size, f"missing log: {log_path}")
    require(png_path.is_file() and png_path.stat().st_size, f"missing PNG: {png_path}")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    expected_actor = "Wulfa" if actor == "wulfa" else "Zhuangfy"
    for token in (
        f"Recovered CharInfo background portrait active: actor={expected_actor}",
        "Recovered CharInfo ready-subset diagnostic active: partial/non-original",
        "settledAlpha=90/255",
        "simpleSpriteTightQuad=actor-specific",
        "depthOffset=0.011",
        "Recovered post-Uber CharInfo world UI active:",
    ):
        require(token in log, f"runtime log missing {token!r}")
    for forbidden in (
        "Recovered CharInfo background portrait failed closed",
        "Shader error in 'Endfield/Recovered/CharInfo/BackgroundPortrait'",
        "Compilation failed",
    ):
        require(forbidden not in log, f"runtime log contains {forbidden!r}")

    width, height = png_dimensions(png_path)
    require((width, height) == (3840, 2160), f"portrait PNG is {width}x{height}")
    return {
        "actor": actor,
        "runtimeValid": True,
        "png": {
            "path": str(png_path),
            "width": width,
            "height": height,
            "bytes": png_path.stat().st_size,
            "sha256": sha256(png_path),
        },
        "log": {"path": str(log_path), "sha256": sha256(log_path)},
        "boundary": (
            "The asset/controller/layout, actor-specific settled GenerateSimpleSprite "
            "geometry, selected UI shader equation, primary full-scene _SceneDepth producer, "
            "and post-Uber layer-16 schedule are original-data closed. The retail pass's "
            "distinct paired output-depth descriptor and frame-specific constants remain "
            "outside this tranche."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--actor", choices=tuple(WRAPPERS))
    parser.add_argument("--log", type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.static_only:
        # Runtime wrappers are local/ignored operator conveniences and are not
        # part of a clean checkout. Static-only mode validates the maintained
        # source, generated assets, scenes, shader, and render-pipeline contract
        # without pretending those absent wrappers were checked.
        results = {
            actor: verify_static(actor, verify_wrapper=False)
            for actor in WRAPPERS
        }
        print(json.dumps({"staticValid": True, "actors": results}, indent=2, sort_keys=True))
        return 0
    require(args.actor is not None, "--actor is required unless --static-only is used")
    require(args.log is not None, "--log is required unless --static-only is used")
    require(args.png is not None, "--png is required unless --static-only is used")
    require(args.report is not None, "--report is required unless --static-only is used")
    result = verify_static(args.actor)
    result.update(verify_runtime(args.actor, args.log.resolve(), args.png.resolve()))
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
