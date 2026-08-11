#!/usr/bin/env python3
"""Audit the source-backed TAAU history/resource contract.

The local FractalMiner source is a decompilation of the installed retail
GameAssembly.  This audit deliberately proves only the static contract: the
history-validity gate, constant-buffer lanes, render-graph resource lifetime,
and pass ordering.  It does not invent live TextureHandle values, settled
history weights, or the result of an IFix replacement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent

_CONFIGURED_GAME_ROOT = Path(
    os.environ.get("ENDFIELD_GAME_ROOT", r"D:\Program Files\Endfield Game")
)


def resolve_game_root(configured: Path) -> Path:
    """Accept either the install root or its ``Endfield_Data`` child."""

    if (configured / "GameAssembly.dll").is_file():
        return configured
    if (
        configured.name.casefold() == "endfield_data"
        and (configured.parent / "GameAssembly.dll").is_file()
    ):
        return configured.parent
    return configured


GAME_ROOT = resolve_game_root(_CONFIGURED_GAME_ROOT)
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
GLOBAL_METADATA = (
    GAME_ROOT
    / "Endfield_Data"
    / "il2cpp_data"
    / "Metadata"
    / "global-metadata.dat"
)

DECOMPILED_SOURCE = (
    REPO_ROOT
    / "tools"
    / "FractalMiner"
    / "Assets"
    / "Project"
    / "EndField"
    / "HGRP"
    / "packages"
    / "com.hg.render-pipelines"
    / "runtime"
    / "HG"
    / "Rendering"
    / "Runtime"
    / "TAAUPassConstructor.cs"
)
SCENE_SOURCE = (
    REPO_ROOT
    / "tools"
    / "FractalMiner"
    / "Assets"
    / "Project"
    / "EndField"
    / "HGRP"
    / "packages"
    / "com.hg.render-pipelines"
    / "runtime"
    / "HG"
    / "Rendering"
    / "Runtime"
    / "HGRenderPathScene.cs"
)
CAMERA_METADATA = LAB_ROOT / "scratch" / "overlay_taa_volume" / "camera_taa_metadata.json"
OUTPUT = LAB_ROOT / "scratch" / "overlay_taa_volume" / "taau_history_contract.json"

EXPECTED_HASHES = {
    "GameAssembly.dll": (
        GAME_ASSEMBLY,
        "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    ),
    "global-metadata.dat": (
        GLOBAL_METADATA,
        "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    ),
    "TAAUPassConstructor.cs": (
        DECOMPILED_SOURCE,
        "6a9771638697179d51930330b9f44db6904b4df340466e616e37bc9c83f9f7fc",
    ),
    "HGRenderPathScene.cs": (
        SCENE_SOURCE,
        "dd4f118d9e3d58f5dac757a934a2897928c5333f4a062a7473f341cbaaa1235f",
    ),
    "camera_taa_metadata.json": (
        CAMERA_METADATA,
        "e1b2c67024b4d571384f86ef405639857a12f23929a5c65af6e6a654e8b572c4",
    ),
}

EXPECTED_TAAU_FIELDS = [
    "m_gaussianKernel",
    "m_gaussianKernelStdDev",
    "m_taauPassMaterials",
    "<prevTAAUState>k__BackingField",
    "m_constants",
    "m_historyDilatedSceneDepth",
    "m_historyDilatedSceneMV",
    "m_rtNames",
    "s_dilationRenderFunc",
    "s_maskDilationRenderFunc",
    "s_resolveRenderFunc",
]
EXPECTED_TAAU_METHODS = {
    "HG.Rendering.Runtime.IPassConstructor.PrepareShaderVariablesGlobal": (
        287693,
        "0x06001249",
    ),
    "HG.Rendering.Runtime.IPassConstructor.OnPreRendering": (287694, "0x0600124a"),
    "HG.Rendering.Runtime.IPassConstructor.OnPostRendering": (287695, "0x0600124b"),
    "ConstructPass": (287696, "0x0600124c"),
    "PrepareParameters": (287698, "0x0600124e"),
    "ConstructTAAUPasses": (287699, "0x0600124f"),
    "ConstructDilationPass": (287700, "0x06001250"),
    "ConstructMaskDilationPass": (287701, "0x06001251"),
    "ConstructResolvePass": (287702, "0x06001252"),
}
EXPECTED_SCENE_METHODS = {
    "OnPostRendering": (288032, "0x0600139c"),
    "RenderInternal": (288033, "0x0600139d"),
    "RenderPostProcessPhase2": (288039, "0x060013a3"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise AssertionError(
            f"TAAU history audit failed: check={check}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def require_tokens(source: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        if token not in source:
            raise AssertionError(f"TAAU history audit failed: {label}: missing {token!r}")


def require_order(source: str, tokens: tuple[str, ...], label: str) -> None:
    cursor = -1
    for token in tokens:
        found = source.find(token, cursor + 1)
        if found < 0:
            raise AssertionError(
                f"TAAU history audit failed: {label}: missing ordered {token!r}"
            )
        cursor = found


def verify_hashes() -> dict[str, str]:
    actual: dict[str, str] = {}
    for label, (path, expected) in EXPECTED_HASHES.items():
        if not path.is_file():
            raise AssertionError(f"TAAU history audit failed: missing {label}: {path}")
        found = sha256(path)
        actual[label] = found
        require(f"{label}.sha256", found, expected)
    return actual


def verify_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    matched = metadata.get("matchedTypes", [])
    taau = next(
        (row for row in matched if row.get("fullName") == "HG.Rendering.Runtime.TAAUPassConstructor"),
        None,
    )
    scene = next(
        (row for row in matched if row.get("fullName") == "HG.Rendering.Runtime.HGRenderPathScene"),
        None,
    )
    require("TAAUPassConstructor metadata row", taau is not None, True)
    require("HGRenderPathScene metadata row", scene is not None, True)
    assert taau is not None and scene is not None
    require("TAAUPassConstructor field count", taau["fieldCount"], 11)
    require("TAAUPassConstructor fields", [x["name"] for x in taau["fields"]], EXPECTED_TAAU_FIELDS)
    methods = {row["name"]: row for row in taau["methods"]}
    for name, (index, token) in EXPECTED_TAAU_METHODS.items():
        row = methods.get(name)
        require(f"method {name} present", row is not None, True)
        assert row is not None
        require(f"method {name}.index", row["index"], index)
        require(f"method {name}.token", row["token"].lower(), token.lower())
    scene_fields = {x["name"]: x for x in scene["fields"]}
    for field in ("<sceneColor>k__BackingField", "<sceneDepth>k__BackingField", "<sceneMV>k__BackingField", "<historySceneColor>k__BackingField"):
        require(f"HGRenderPathScene field {field}", field in scene_fields, True)
    require(
        "historySceneColor field index/token",
        (scene_fields["<historySceneColor>k__BackingField"]["index"], scene_fields["<historySceneColor>k__BackingField"]["token"].lower()),
        (176842, "0x040024f9"),
    )
    scene_methods = {row["name"]: row for row in scene["methods"]}
    for name, (index, token) in EXPECTED_SCENE_METHODS.items():
        row = scene_methods.get(name)
        require(f"scene method {name} present", row is not None, True)
        assert row is not None
        require(f"scene method {name}.index", row["index"], index)
        require(f"scene method {name}.token", row["token"].lower(), token.lower())
    return {
        "taauType": {
            "index": taau["index"],
            "fieldCount": taau["fieldCount"],
            "methodStart": taau["methodStart"],
            "methodCount": taau["methodCount"],
            "fields": EXPECTED_TAAU_FIELDS,
            "methods": {
                name: {"index": index, "token": token}
                for name, (index, token) in EXPECTED_TAAU_METHODS.items()
            },
        },
        "sceneType": {
            "index": scene["index"],
            "fieldCount": scene["fieldCount"],
            "historyField": "<historySceneColor>k__BackingField",
            "historyFieldIndex": 176842,
            "methods": {
                name: {"index": index, "token": token}
                for name, (index, token) in EXPECTED_SCENE_METHODS.items()
            },
        },
    }


def verify_source(source: str) -> dict[str, Any]:
    require_tokens(
        source,
        (
            "!HG::Rendering::RenderGraphModule::TextureHandle::IsValid(&input.historySceneColor",
            "|| !this.fields._prevTAAUState_k__BackingField",
            "!HG::Rendering::RenderGraphModule::TextureHandle::IsValid(&this.fields.m_historyDilatedSceneDepth",
            "!HG::Rendering::RenderGraphModule::TextureHandle::IsValid(&this.fields.m_historyDilatedSceneMV",
        ),
        "history validity gate",
    )
    require_tokens(
        source,
        (
            "this.fields.m_constants.taauParameters0.z = historyWeight",
            "this.fields.m_constants.taauParameters0.w = input.historyWeightInMotion",
            "this.fields.m_constants.taauParameters4.x = input.fastConvergeHistoryWeight",
            "this.fields.m_constants.taauParameters2.z = input.responsiveAAHistoryWeight",
            "this.fields.m_constants.taauParameters3.y = input.minMVConsideredDynamic",
            "this.fields.m_constants.taauParameters3.z = input.maxMVConsideredDynamic",
            "this.fields.m_constants.taauParameters3.w = input.characterMotionSensitivity",
            "this.fields.m_constants.taauParameters1.y = input.occlusionDepthDiff",
            "this.fields.m_constants.taauParameters4.w = input.inputSampleLumaWeight",
            "this.fields.m_constants.taauParameters2.w = (float)input.fastConvergeState",
            "this.fields.m_constants.taauParameters5.x = input.enableResponsiveTransparency",
            "this.fields.m_constants.taauParameters1.w = (float)v7",
            "this.fields.m_constants.taauParameters1.z = HG::Rendering::Runtime::TAAUPassConstructor::ComputeSharpenStrength",
            "this.fields.m_constants.taauParameters7 = *(Vector4 *)&v20.bufferId",
            "this.fields.m_constants.taauParameters6 = *(Vector4 *)&v20.bufferId",
            "UnityEngine::Rendering::ScriptableRenderContext::AllocateConstantBuffer",
            "System::Buffer::MemoryCopy((Void *)&this.fields.m_constants, (Void *)v20.ptr, 192LL, 192LL, 0LL)",
        ),
        "constant-buffer lane mapping",
    )
    require_tokens(
        source,
        (
            "this.fields.m_historyDilatedSceneDepth = *HG::Rendering::RenderGraphModule::HGRenderGraph::PreserveTexture(",
            "this.fields.m_historyDilatedSceneMV = *HG::Rendering::RenderGraphModule::HGRenderGraph::PreserveTexture(",
            "this.fields.m_historyDilatedSceneDepth = *HG::Rendering::RenderGraphModule::HGRenderGraph::CreateTexture(",
            "this.fields.m_historyDilatedSceneMV = *HG::Rendering::RenderGraphModule::HGRenderGraph::CreateTexture(",
            "HG::Rendering::RenderGraphModule::HGRenderGraphBuilder::ReadWriteTexture(",
            "HG::Rendering::RenderGraphModule::HGRenderGraphBuilder::ReadTexture(",
        ),
        "history resource lifecycle",
    )
    require_order(
        source,
        (
            "TAAUPassConstructor::ConstructDilationPass(this, input, renderGraph",
            "TAAUPassConstructor::ConstructMaskDilationPass(this, input, renderGraph",
            "TAAUPassConstructor::ConstructResolvePass(this, input, output, renderGraph",
        ),
        "TAAU pass order",
    )
    require_tokens(
        source,
        (
            "if ( !input.quality )",
            "*output = (TAAUPassConstructor_PassOutput)input.sceneColor",
            "this.fields.m_historyDilatedSceneDepth = *(TextureHandle *)sub_182E7CCD0(v12)",
            "this.fields.m_historyDilatedSceneMV = *(TextureHandle *)sub_182E7CCD0(v12)",
            "this.fields._prevTAAUState_k__BackingField = input.enableTAAU",
            "v45[4] = (Object)input.historySceneColor",
            "HG::Rendering::RenderGraphModule::HGRenderGraphBuilder::ReadTexture(",
            "&input.historySceneColor",
            "output.currentSceneColor = v47",
        ),
        "enable/resolve contract",
    )
    return {
        "historyGate": [
            "input.historySceneColor is valid",
            "previous frame had TAAU enabled",
            "quality 0 additionally requires persistent dilated scene depth and motion-vector handles",
        ],
        "constantLanes": {
            "taauParameters0.z": "historyWeight (forced to 0 when the gate fails)",
            "taauParameters0.w": "historyWeightInMotion",
            "taauParameters1.y": "occlusionDepthDiff",
            "taauParameters1.z": "ComputeSharpenStrength(screenSize, sharpenStrength1K/2K/4K)",
            "taauParameters1.w": "history gate flag",
            "taauParameters2.w": "fastConvergeState",
            "taauParameters2.z": "responsiveAAHistoryWeight",
            "taauParameters3.yzw": "min/max MV dynamic thresholds and characterMotionSensitivity",
            "taauParameters4.x": "fastConvergeHistoryWeight",
            "taauParameters4.w": "inputSampleLumaWeight",
            "taauParameters5.x": "enableResponsiveTransparency",
            "taauParameters6": "renderSize.xy and inverse render size",
            "taauParameters7": "screenSize.xy and inverse screen size",
        },
        "historyResources": {
            "sceneColor": "input.historySceneColor is read when valid; resolve writes a new screen-size currentSceneColor",
            "dilatedSceneDepth": "render-size R32-style colorFormat 45; created once and preserved across frames",
            "dilatedSceneMV": "render-size texture inheriting input.sceneMV colorFormat; created once and preserved across frames",
            "dilationInputs": ["input.sceneDepth", "input.sceneMV"],
            "dilationOutputs": ["m_historyDilatedSceneDepth", "m_historyDilatedSceneMV"],
        },
        "passOrder": ["Dilation", "MaskDilation", "Resolve"],
        "qualityBehavior": {
            "quality0": "runs Dilation and MaskDilation before Resolve; Resolve uses output format 48",
            "quality1": "skips the two dilation passes; Resolve reads sceneDepth and sceneMV and uses sceneColor format",
        },
        "boundary": (
            "Static TAAU history/resource ABI is source-closed. Live TextureHandle identities, "
            "settled history weights/internal extent, runtime frame resets, and any IFix replacement "
            "of the wrapped methods remain open."
        ),
    }


def verify_scene_source(source: str) -> dict[str, Any]:
    require_tokens(
        source,
        (
            "if ( renderPathParams.skipRender )",
            "v9 = *(TextureHandle *)&this[1].fields._.m_shaderVariablesGlobal._PrevNonJitteredViewNoTransProjMatrix.m23",
            "v9 = *(TextureHandle *)&this[1].fields._.m_shaderVariablesGlobal._PrevNonJitteredViewProjMatrix.m03",
            "HG::Rendering::RenderGraphModule::HGRenderGraph::PreserveTexture(&v12, m_RenderGraph, &v11, 1, (String *)\"historySceneColor\", 0LL)",
            "HG::Rendering::Runtime::HGRenderPathBase::OnPostRendering((HGRenderPathBase *)this, renderPathParams, 0LL)",
            "IFix::WrappersManagerImpl::IsPatched(3037, 0LL)",
        ),
        "scene history writeback",
    )
    require_tokens(
        source,
        (
            "v161.sceneColor = *(TextureHandle *)&v4[1].fields._.m_shaderVariablesGlobal._PrevNonJitteredViewProjMatrix.m03",
            "v161.sceneDepth = *(TextureHandle *)&v4[1].fields._.m_shaderVariablesGlobal._PrevNonJitteredViewNoTransProjMatrix.m00",
            "v161.sceneMV = *(TextureHandle *)&v4[1].fields._.m_shaderVariablesGlobal._PrevNonJitteredViewNoTransProjMatrix.m01",
            "v161.historySceneColor = *(TextureHandle *)&v4[1].fields._.m_shaderVariablesGlobal._PrevNonJitteredViewNoTransProjMatrix.m23",
            "v161.screenSize = v23[3]",
            "v161.renderSize = v24[6]",
            "HG::Rendering::Runtime::TAAUPassConstructor::ConstructPass(",
            "*(TAAUPassConstructor_PassOutput *)&v4[1].fields._.m_shaderVariablesGlobal._PrevNonJitteredViewProjMatrix.m03 = output",
            "hgrp.fields._fastConvergeState_k__BackingField = 0",
        ),
        "scene history input handoff",
    )
    return {
        "inputHandoff": {
            "currentSceneColor": "HGRenderPathScene sceneColor",
            "sceneDepth": "HGRenderPathScene sceneDepth",
            "sceneMV": "HGRenderPathScene sceneMV",
            "historySceneColor": "HGRenderPathScene persistent historySceneColor",
            "screenSize": "HGCamera view-size entry v23[3]",
            "renderSize": "HGCamera render-size entry v24[6]",
        },
        "writeback": {
            "normalFrame": "TAAU/PostProcess output currentSceneColor",
            "skipRender": "previous historySceneColor",
            "preserveName": "historySceneColor",
            "fastConvergeState": "reset to 0 after ConstructPass",
        },
        "boundary": (
            "The scene-level history handoff and PreserveTexture writeback are source-closed. "
            "The runtime TextureHandle identities and the IFix 3037 replacement result remain open."
        ),
    }


def build_audit() -> dict[str, Any]:
    hashes = verify_hashes()
    metadata = json.loads(CAMERA_METADATA.read_text(encoding="utf-8"))
    source = DECOMPILED_SOURCE.read_text(encoding="utf-8")
    scene_source = SCENE_SOURCE.read_text(encoding="utf-8")
    return {
        "schema": "endfield.taau-history-contract.v1",
        "status": "source_closed_live_handles_open",
        "evidence": {
            "hashes": hashes,
            "metadata": verify_metadata(metadata),
            "source": "FractalMiner decompilation comments from the hash-pinned retail GameAssembly",
        },
        "contract": verify_source(source),
        "sceneHistory": verify_scene_source(scene_source),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="compare the generated scratch report")
    args = parser.parse_args()
    audit = build_audit()
    rendered = json.dumps(audit, indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file():
            raise AssertionError(f"TAAU history audit failed: missing generated audit: {OUTPUT}")
        require("generated_audit", OUTPUT.read_text(encoding="utf-8"), rendered)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "TAAU history audit passed: validity gate, 192-byte constants, "
        "persistent depth/MV resources, scene history handoff, and "
        "Dilation->MaskDilation->Resolve are source-closed; live handles remain open."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
