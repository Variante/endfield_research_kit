#!/usr/bin/env python3
"""Verify the source-closed post-Uber CharInfo portrait compositor tranche."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CONTRACT = (
    ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters"
    / "charinfo_portrait_post_uber_contract.json"
)
PIPELINE = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
SHADER = ROOT / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldCharInfoBackgroundPortraitRecovered.shader"
COMPONENT = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredCharInfoBackgroundPortrait.cs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def png_info(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height, len(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    pipeline = PIPELINE.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")
    component = COMPONENT.read_text(encoding="utf-8")

    require(
        contract.get("schema") == "endfield.charinfo.portrait-post-uber-compositor-contract.v1",
        "unexpected contract schema",
        failures,
    )
    for key in ("audit_json", "audit_markdown"):
        relative = Path(contract["evidence"][key])
        source = REPO / relative
        require(source.is_file(), f"missing evidence {relative}", failures)
        if source.is_file():
            require(
                sha256(source) == contract["evidence"][f"{key}_sha256"],
                f"evidence hash mismatch: {relative}",
                failures,
            )

    pipeline_markers = [
        "TryPrepareRecoveredPostUberWorldUi(",
        "GraphicsFormat.D32_SFloat_S8_UInt",
        "GraphicsFormat.D24_UNorm_S8_UInt",
        "FormatUsage.Render",
        "ShadowSamplingMode.RawDepth",
        "primarySceneDepth.depthStencilFormat != selectedFormat",
        "camera.cullingMask & ~(1 << EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer)",
        "DrawRecoveredPostUberWorldUi(",
        "new RenderTargetIdentifier(primarySceneDepth)",
        "commandBuffer.SetGlobalTexture(SceneDepthId, portraitSceneDepth)",
        "SortingCriteria.CommonTransparent",
        "1 << EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer",
        "commandBuffer.SetGlobalFloat(RecoveredPostUberWorldUiReadyId, 0.0f)",
        "commandBuffer.SetGlobalFloat(RecoveredPostUberWorldUiReadyId, 1.0f)",
        "GL.GetGPUProjectionMatrix(",
        "camera.nonJitteredProjectionMatrix",
        "projection * viewNoTranslation",
        "commandBuffer.SetGlobalFloat(RenderPathInjectedId, 1.0f)",
        "ReleaseRecoveredPrimarySceneDepth(recoveredPrimarySceneDepth)",
    ]
    for marker in pipeline_markers:
        require(marker in pipeline, f"pipeline marker missing: {marker}", failures)

    d32 = pipeline.find("GraphicsFormat.D32_SFloat_S8_UInt")
    d24 = pipeline.find("GraphicsFormat.D24_UNorm_S8_UInt")
    require(0 <= d32 < d24, "D32S8 intent must precede the D24S8 fallback", failures)

    ordinary = pipeline.find("int ordinaryTransparentLayerMask")
    post_call = pipeline.find("ApplyCharacterPostProcess(", ordinary)
    post_draw = pipeline.find("DrawRecoveredPostUberWorldUi(", post_call)
    require(
        0 <= ordinary < post_call < post_draw,
        "chronology markers do not prove ordinary transparent -> fullscreen post -> layer-16 UI",
        failures,
    )
    require(
        "commandBuffer.SetRenderTarget(postColorTarget);" in pipeline,
        "post-Uber UI does not target the post color",
        failures,
    )
    portrait_draw = pipeline[
        pipeline.find("private void DrawRecoveredPostUberWorldUi"):pipeline.find(
            "private int BuildRecoveredSceneBloomPyramid"
        )
    ]
    post_ui_render_targets = re.findall(
        r"commandBuffer\.SetRenderTarget\((.*?)\);",
        portrait_draw,
        flags=re.DOTALL,
    )
    require(
        all("primarySceneDepth" not in arguments
            for arguments in post_ui_render_targets),
        "primary depth must not be rebound as a simultaneous post-UI DSV",
        failures,
    )
    require(
        "commandBuffer.SetGlobalFloat(HGFlipYId, 0.0f);" in portrait_draw,
        "post-Uber portrait draw does not retain the offscreen target orientation",
        failures,
    )
    require(
        "camera.targetTexture == null ? 1.0f : 0.0f" not in portrait_draw,
        "post-Uber portrait still applies a portrait-only backbuffer Y flip",
        failures,
    )

    shader_markers = [
        "Texture2D<float> _SceneDepth;",
        "SamplerState sampler_LinearRepeat;",
        "clip(_EndfieldRecoveredPostUberWorldUiReady - 0.5);",
        "_SceneDepth.Sample(",
        "sampler_LinearRepeat",
        "LinearEyeDepth(sceneRawDepth)",
        "LinearEyeDepth(uiRawDepth)",
        "Blend One OneMinusSrcAlpha",
        "ZTest Always",
        "ZWrite Off",
        "float4x4 _NonJitteredViewNoTransProjMatrix;",
        "float4 _WorldSpaceCameraPos_Internal;",
        "_WorldSpaceCameraPos_Internal.xyz * _RenderPathInjected",
        "_NonJitteredViewNoTransProjMatrix",
        "output.positionCS.x *= 1.0 - 2.0 * _HGFlipX;",
        "output.positionCS.y *= 1.0 - 2.0 * _HGFlipY;",
    ]
    for marker in shader_markers:
        require(marker in shader, f"shader marker missing: {marker}", failures)
    require(
        "_EndfieldRecoveredCameraDepthTexture" not in shader,
        "portrait shader still references the character-only RFloat substitute",
        failures,
    )
    require(
        '"ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT"' in component,
        "default-off portrait selector is missing",
        failures,
    )
    for marker in (
        "BuildCardAnchoredXCurve()",
        "BuildCardAlphaCurve()",
        "2.2694368f",
        "0.04842146f",
        "WeightedMode.Both",
        "new Keyframe(1.0f, SettledAnimationAlpha, 0.0f, 0.0f)",
        "TryGetAutomaticOverviewStartSeconds(",
        "overviewPlayback.PlaybackGeneration",
    ):
        require(marker in component, f"portrait animation marker missing: {marker}", failures)

    runtime: dict[str, object] = {}
    if not args.static_only and args.log:
        log = args.log.read_text(encoding="utf-8", errors="replace")
        activation = "Recovered post-Uber CharInfo world UI active:" in log
        runtime["activation_log"] = activation
        require(activation, "runtime activation marker missing", failures)
        format_match = re.search(
            r"full-scene primary (D32_SFloat_S8_UInt|D24_UNorm_S8_UInt) depth/stencil",
            log,
        )
        runtime["primary_depth_format"] = (
            format_match.group(1) if format_match else None
        )
        require(format_match is not None, "runtime primary depth format marker missing", failures)
        forbidden = (
            "Shader error in 'Endfield/Recovered/CharInfo/BackgroundPortrait'",
            "Scripts have compiler errors",
            "Compilation failed",
            "NullReferenceException",
        )
        for marker in forbidden:
            require(marker not in log, f"runtime log contains: {marker}", failures)
    if not args.static_only and args.png:
        width, height, size = png_info(args.png)
        runtime["png"] = {
            "path": str(args.png),
            "width": width,
            "height": height,
            "bytes": size,
            "sha256": sha256(args.png),
        }
        require(width == 3840 and height == 2160, "unexpected render dimensions", failures)

    result = {
        "schema": contract["schema"],
        "ok": not failures,
        "failures": failures,
        "static": {
            "audit_json_sha256": contract["evidence"]["audit_json_sha256"],
            "depth_intent": "D32_SFloat_S8_UInt RawDepth depth-plane SRV",
            "depth_fallback": "D24_UNorm_S8_UInt",
            "primary_depth_is_full_scene": True,
            "layer16_is_post_uber": True,
            "unrelated_non_world_ui_transparents_moved": False,
            "paired_output_depth_implemented": False,
        },
        "runtime": runtime,
    }
    output = json.dumps(result, indent=2)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
