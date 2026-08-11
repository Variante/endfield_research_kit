#!/usr/bin/env python3
"""Verify the source-pinned CharacterNPR PreG/canonical-depth owner recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
ASSET_ROOT = PROJECT / "Assets/EndfieldGraphShaderLab"
CONTRACT = (
    ASSET_ROOT
    / "Generated/OriginalData/RenderParameters"
    / "character_preg_depth_owner_contract.json"
)
SCRATCH_CONTRACT = (
    PROJECT
    / "scratch/character_recovery/preg_depth_owner"
    / "character_preg_depth_owner_contract.json"
)
PIPELINE = ASSET_ROOT / "Runtime/Rendering/HGCompatRenderPipeline.cs"
OWNER = ASSET_ROOT / "Runtime/Rendering/EndfieldRecoveredPreGBufferDepthOwner.cs"
GPU_VERIFIER = (
    ASSET_ROOT
    / "Editor/CharacterRecovery"
    / "EndfieldRecoveredPreGBufferDepthOwnerBatchVerifier.cs"
)
SETUP = (
    ASSET_ROOT
    / "Editor/CharacterRecovery/EndfieldManifestCharacterSetup.cs"
)
SHADER_ROOT = ASSET_ROOT / "Shaders/Recovered"
RECOVERED_SHADERS = (
    SHADER_ROOT / "EndfieldCharacterSkinRecovered.shader",
    SHADER_ROOT / "EndfieldCharacterClothRecovered.shader",
    SHADER_ROOT / "EndfieldCharacterEyeRecovered.shader",
    SHADER_ROOT / "EndfieldCharacterHairRecovered.shader",
)
LAST_RITE_MATERIAL = (
    ASSET_ROOT
    / "Generated/Characters/Playable/Lastrite/Materials"
    / "actor_lastrite_pathid_-1435421870657246405.mat"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = REPO / path
    if candidate.exists():
        return candidate
    return PROJECT / path


def require_pinned(entry: dict, path_key: str = "path") -> Path:
    path = resolve(entry[path_key])
    require(path.is_file(), f"missing pinned source: {path}")
    require(path.stat().st_size == entry["size"], f"size drift: {path}")
    require(sha256(path) == entry["sha256"], f"SHA-256 drift: {path}")
    return path


def require_in_order(text: str, tokens: list[str], label: str) -> None:
    offset = 0
    for token in tokens:
        index = text.find(token, offset)
        require(index >= 0, f"{label}: missing or out-of-order token {token!r}")
        offset = index + len(token)


def yaml_float(text: str, name: str, value: float) -> None:
    require(f"- {name}: {value:g}" in text, f"generated material lost {name}={value:g}")


def verify_sources(contract: dict) -> None:
    installed = contract["installed_inputs"]
    for key in ("game_assembly", "global_metadata"):
        require_pinned(installed[key])
    shader_path = require_pinned(
        installed["character_npr_shader"],
        "converted_path",
    )
    material_path = require_pinned(
        installed["last_rite_cloth_03"],
        "type_tree_path",
    )
    for value in contract["focused_evidence"].values():
        require_pinned(value)

    shader = shader_path.read_text(encoding="utf-8")
    require_in_order(
        shader,
        [
            'Name "PreGBuffer"',
            '"LIGHTMODE" = "DepthCharacterOnly"',
            "Cull Off",
            "Stencil {",
            "Comp Always",
            "Pass Replace",
            "Fail Keep",
            "ZFail Keep",
        ],
        "installed CharacterNPR PreGBuffer state",
    )
    preg_start = shader.find('Name "PreGBuffer"')
    preg_program = shader.find('Program "vp"', preg_start)
    preg_state = shader[preg_start:preg_program]
    require("ZTest" not in preg_state, "installed PreG gained an explicit ZTest override")
    require("ZWrite" not in preg_state, "installed PreG gained an explicit ZWrite override")

    material = material_path.read_text(encoding="utf-8")
    for token in (
        "int m_CustomRenderQueue = 2000",
        'string first = "_SurfaceType"',
        "float second = 0",
        'string first = "_ZTest"',
        "float second = 3",
        'string first = "_ZWrite"',
        "float second = 1",
        'string first = "_PreZStencilRefOption"',
        "float second = 36",
        'string data = "GBuffer"',
        'string data = "ReflectionForwardOnly"',
        'string data = "DepthOnly"',
    ):
        require(token in material, f"Last Rite cloth-03 source drift: {token}")
    require(
        'string data = "PreGBuffer"' not in material,
        "Last Rite cloth-03 now disables its CharacterNPR PreGBuffer pass",
    )


def verify_native_contract(contract: dict) -> None:
    selected = require_pinned(contract["focused_evidence"]["selected_instructions"])
    native = selected.read_text(encoding="utf-8")
    for method, expected in contract["method_map"].items():
        if "va" in expected:
            require(
                f"VA={expected['va']}" in native,
                f"selected native evidence lost {method} at {expected['va']}",
            )

    require_in_order(
        native,
        [
            "## HG.Rendering.Runtime.HGRenderPathDeferred.OnPreRendering",
            "+0x0441 ba 00 05 00 00",
            "+0x044b 41 b9 00 10 00 00",
            "+0x0456 41 b8 00 01 00 00",
            "+0x0478",
            "+0x0484 89 87 d4 13 00 00",
            "+0x0d50 ba 00 05 00 00",
            "+0x0d5a 41 b9 80 00 00 00",
            "+0x0d65 41 b8 00 01 00 00",
            "+0x0d8c",
            "+0x0d93 89 b7 fc 13 00 00",
        ],
        "DepthCharacterOnly/ForwardCharacterOnly list preparation",
    )
    require_in_order(
        native,
        [
            "## HG.Rendering.Runtime.HGRenderPathDefaultDeferred.RenderScene",
            "+0x21e8",
            "call 0x189b9bc3c",
            "+0x27e4",
            "call 0x189badf00",
        ],
        "DefaultDeferred depth-before-GBuffer chronology",
    )
    require_in_order(
        native,
        [
            "## HG.Rendering.Runtime.GBufferPassConstructor+<>c.<.cctor>b__10_0",
            "mov esi, [rdx+0x5c]",
            "call 0x189c096f4",
            "mov esi, [rdi+0x60]",
            "call 0x189c096f4",
            "mov rdx, [rdi+0x40]",
            "call 0x189c0989c",
            "mov rdx, [rdi+0x38]",
            "call 0x189c0989c",
            "mov edx, [rdi+0x48]",
            "call 0x189c096f4",
            "mov edx, [rdi+0x4c]",
            "call 0x189c096f4",
        ],
        "CharacterPrePass-before-ordinary-GBuffer draw order",
    )
    for ifix_id in ("0xc12", "0xc75", "0xdf6"):
        require(f"mov ebx, {ifix_id}" in native or f"mov esi, {ifix_id}" in native, f"IFix id drift: {ifix_id}")


def verify_implementation() -> None:
    owner = OWNER.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")
    setup = SETUP.read_text(encoding="utf-8")
    gpu_verifier = GPU_VERIFIER.read_text(encoding="utf-8")

    for token in (
        "ENDFIELD_RECOVERED_PREGBUFFER_DEPTH_OWNER",
        "-endfield-recovered-pregbuffer-depth-owner",
        'CharacterPassName = "RECOVERED_PREGBUFFER_DIAGNOSTIC"',
        'SourceZTestPropertyName = "_RecoveredSourceZTest"',
        "material.renderQueue <= (int)RenderQueue.GeometryLast",
        "SystemInfo.supportedRenderTargetCount < 2",
        "GraphicsFormat.A2B10G10R10_UNormPack32",
        "commandBuffer.SetRenderTarget(mrt, canonicalDepthTarget)",
        "genericDepthDraws",
        "characterDraws",
        "commandBuffer.DrawRenderer(",
        "material.SetFloat(ZTestId, (float)CompareFunction.LessEqual)",
        "material.SetFloat(ZTestId, state.sourceZTest)",
        "context.ExecuteCommandBuffer(commandBuffer)",
        "commandBuffer.ReleaseTemporaryRT(GBufferAId)",
        "commandBuffer.ReleaseTemporaryRT(GBufferBId)",
        "source Equal remains disabled",
    ):
        require(token in owner, f"depth-owner implementation lost token: {token}")
    require_in_order(
        owner,
        [
            "ResetCandidateZTestsToCompatibility",
            "TryCollectDraws",
            "commandBuffer.SetRenderTarget(mrt, canonicalDepthTarget)",
            "foreach (GenericDepthDraw draw in genericDepthDraws)",
            "foreach (CharacterDraw draw in characterDraws)",
            "RestoreCanonicalTarget",
            "context.ExecuteCommandBuffer(commandBuffer)",
            "ActivateSourceZTests",
        ],
        "fail-closed canonical owner sequence",
    )

    for token in (
        "recoveredPreGBufferDepthOwner",
        "new EndfieldRecoveredPreGBufferDepthOwner()",
        "RenderCanonicalOwner(",
        "canonicalDepthTarget",
        "useRecoveredPostUberWorldUi",
        "recoveredPreGBufferDepthOwner?.Dispose()",
    ):
        require(token in pipeline, f"pipeline depth-owner wiring lost token: {token}")
    owner_call = pipeline.find("recoveredPreGBufferDepthOwner.RenderCanonicalOwner(")
    # Keep this chronology check resilient to ordinary C# formatting changes:
    # the production call is intentionally multiline, so matching the old
    # single-line spelling falsely reported a lost owner boundary.
    forward_call = pipeline.find("DrawRenderers(", owner_call)
    forward = pipeline.find("RenderQueueRange.opaque", forward_call)
    require(
        owner_call >= 0 and forward_call > owner_call and forward > forward_call,
        "canonical owner chronology missing: "
        f"ownerCall={owner_call}, forwardCall={forward_call}, "
        f"opaqueRange={forward}",
    )

    require(
        '"_RecoveredSourceZTest"' in setup,
        "material setup no longer preserves source ZTest",
    )
    require_in_order(
        setup,
        [
            'floats.TryGetValue("_ZTest"',
            'SetMaterialFloat(material, "_RecoveredSourceZTest"',
            'material.SetFloat("_ZTest", (float)CompareFunction.LessEqual)',
        ],
        "source-ZTest preservation before fail-closed compatibility ZTest",
    )
    for shader_path in RECOVERED_SHADERS:
        text = shader_path.read_text(encoding="utf-8")
        require(
            '[HideInInspector] _RecoveredSourceZTest' in text,
            f"{shader_path.name}: missing hidden source ZTest carrier",
        )
        require(
            'Name "RECOVERED_PREGBUFFER_DIAGNOSTIC"' in text,
            f"{shader_path.name}: missing recovered PreG pass",
        )

    for token in (
        'ExpectedUnityVersion = "2022.3.62f3"',
        "GraphicsDeviceType.Direct3D12",
        "ENDFIELD_RECOVERED_PREGBUFFER_DEPTH_OWNER",
        "ENDFIELD_RECOVERED_PREGBUFFER_DIAGNOSTIC",
        "actor_lastrite_pathid_-1435421870657246405.mat",
        'material.SetFloat("_ZTest", (float)CompareFunction.LessEqual)',
        "camera.Render()",
        "CompareFunction.Equal",
        "EndfieldRecoveredPreGBufferDiagnosticBatchVerifier.Verify()",
        "endfield-recovered-canonical-pregbuffer-depth-owner-v1",
    ):
        require(token in gpu_verifier, f"GPU depth-owner verifier lost token: {token}")


def verify_generated_last_rite() -> None:
    require(LAST_RITE_MATERIAL.is_file(), f"missing refreshed material: {LAST_RITE_MATERIAL}")
    material = LAST_RITE_MATERIAL.read_text(encoding="utf-8")
    require("m_Name: M_actor_lastrite_cloth_03" in material, "wrong Last Rite material")
    require("m_CustomRenderQueue: -1" in material, "Last Rite queue is not effective shader queue 2000")
    yaml_float(material, "_ZTest", 4.0)
    yaml_float(material, "_ZWrite", 1.0)
    yaml_float(material, "_RecoveredSourceZTest", 3.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scratch-contract",
        action="store_true",
        help="validate the pre-promotion scratch contract",
    )
    parser.add_argument(
        "--require-generated",
        action="store_true",
        help="also require the refreshed Last Rite material source-ZTest carrier",
    )
    args = parser.parse_args()
    contract_path = SCRATCH_CONTRACT if args.scratch_contract else CONTRACT
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    require(
        contract["schema"] == "endfield.character-preg-depth-owner-contract.v1",
        "contract schema drift",
    )
    verify_sources(contract)
    verify_native_contract(contract)
    verify_implementation()
    if args.require_generated:
        verify_generated_last_rite()
    print("character PreG/canonical-depth owner recovery: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
