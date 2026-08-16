#!/usr/bin/env python3
"""Build the fail-closed retail EffectAnimation playable-topology contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
BODY_TARGETS = REPO / "scratch/character_recovery/overview_effect_owner/effect_native_body_targets.json"
EFFECT_INSTANCE_TARGETS = (
    REPO / "scratch/reverse_engineering/zhuangfy_lizi_lodfade_20260724/"
    "effect_instance_native.json"
)
OWNER_REPORT = REPO / "reports/assets/character_recovery/overview_effect_owner_animator_negative_20260815.md"
STATIC_CONTRACT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_01_effect.json"
SIBLING_CONTRACT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_02_03_effects.json"
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger/lizhiyan_effect_animation_playable_topology.json"
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def artifact(path: Path, kind: str) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(REPO.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "objectType": kind,
    }


def body_method(
    body_targets: dict[str, Any],
    name: str,
    token: str,
    va: str,
    parameters: list[str],
) -> dict[str, Any]:
    rows = [
        row for row in body_targets["bodyTargets"]
        if row.get("type") == "Beyond.Gameplay.EffectAnimation"
        and row.get("method") == name
    ]
    require(len(rows) == 1, f"EffectAnimation.{name} body target missing or ambiguous")
    row = rows[0]
    require(
        row["token"].upper() == token.upper()
        and row["methodPointerVa"].upper() == va.upper()
        and row["parameters"] == parameters,
        f"EffectAnimation.{name} ABI drifted",
    )
    patch_ids = []
    direct_callees = []
    for call in row["methodBodySummary"]["calls"]:
        resolved = call.get("resolved", [])
        names = [f'{item["type"]}.{item["method"]}' for item in resolved]
        direct_callees.extend(names)
        if "IFix.WrappersManagerImpl.IsPatched" in names:
            patch_ids.append(call.get("argumentOrigins", {}).get("rcx"))
    return {
        "token": token,
        "va": va,
        "parameters": parameters,
        "ifFixDispatchIds": sorted(value for value in set(patch_ids) if value),
        "directCallees": sorted(set(direct_callees)),
    }


def effect_instance_route(
    body_targets: dict[str, Any],
    name: str,
    token: str,
    va: str,
    parameters: list[str],
    expected_calls: dict[str, list[str]],
) -> dict[str, Any]:
    rows = [
        row for row in body_targets["bodyTargets"]
        if row.get("type") == "Beyond.Gameplay.EffectInstance"
        and row.get("method") == name
    ]
    require(len(rows) == 1, f"EffectInstance.{name} body target missing or ambiguous")
    row = rows[0]
    require(
        row["token"].upper() == token.upper()
        and row["methodPointerVa"].upper() == va.upper()
        and row["parameters"] == parameters,
        f"EffectInstance.{name} ABI drifted",
    )
    calls: dict[str, list[str]] = {}
    for call in row["directCalls"]:
        for resolved in call.get("resolved", []):
            callee = resolved["method"]
            if callee in expected_calls:
                calls.setdefault(callee, []).append(f'0x{call["offset"]:X}')
    require(calls == expected_calls, f"EffectInstance.{name} caller route drifted")
    return {
        "token": token,
        "va": va,
        "parameters": parameters,
        "calls": calls,
    }


def build() -> dict[str, Any]:
    for path in (BODY_TARGETS, EFFECT_INSTANCE_TARGETS, OWNER_REPORT, STATIC_CONTRACT, SIBLING_CONTRACT):
        require(path.is_file(), f"playable topology source missing: {path}")
    body_targets = json.loads(BODY_TARGETS.read_text(encoding="utf-8"))
    effect_instance_targets = json.loads(EFFECT_INSTANCE_TARGETS.read_text(encoding="utf-8"))
    start01 = json.loads(STATIC_CONTRACT.read_text(encoding="utf-8"))
    siblings = json.loads(SIBLING_CONTRACT.read_text(encoding="utf-8"))
    require(start01["animation"]["startAnimationClip"]["pathID"] == 7360398354216100382,
            "start_01 shared clip identity drifted")
    require(siblings["sharedAnimation"]["pathID"] == 7360398354216100382,
            "sibling shared clip identity drifted")
    return {
        "schema": "endfield.lizhiyan-effect-animation-playable-topology.v1",
        "status": "retail_topology_closed_editor_advanced_mixer_unavailable_visible_fail_closed",
        "visibleAdmission": False,
        "sources": {
            "nativeBodyTargets": artifact(BODY_TARGETS, "PinnedNativeBodyTargets"),
            "effectInstanceBodyTargets": artifact(EFFECT_INSTANCE_TARGETS, "PinnedEffectInstanceBodyTargets"),
            "ownerReport": artifact(OWNER_REPORT, "NativeOwnerReport"),
            "start01Contract": artifact(STATIC_CONTRACT, "Start01EffectContract"),
            "siblingContract": artifact(SIBLING_CONTRACT, "SiblingEffectContract"),
        },
        "retailEffectAnimationTopology": {
            "updateMode": "GameTime",
            "timeScale": 1.0,
            "manualEvaluation": False,
            "clipRetiming": "not_proven_do_not_apply",
            "createPlayableGraph": {
                "token": "0x060059D0",
                "va": "0x183437F90",
                "graphCreateCallOffset": "0x74",
                "animationPlayableOutputCreateVA": "0x183438077",
                "advancedMixerCreateVA": "0x1834380BA",
            },
            "addClip": {
                "token": "0x060059CD",
                "va": "0x183437D60",
                "animationClipPlayableCreateVA": "0x183437E02",
            },
            "playAnimation": {"token": "0x060059D1", "va": "0x183436AD0"},
            "manualEvaluate": {"token": "0x060059D2", "va": "0x187431CB0"},
            "stop": {"token": "0x060059DB", "va": "0x1831DC580"},
            "mixer": {
                "type": "UnityEngine.Animations.AdvancedAnimationMixerPlayable",
                "image": "UnityEngine.AnimationModule.dll",
                "typeToken": "0x02000053",
                "inputCount": 3,
                "fields": ["m_Handle", "m_NullPlayable"],
                "fieldTokens": {
                    "m_Handle": "0x04000151",
                    "m_NullPlayable": "0x04000152",
                },
                "createSignature": "Create(PlayableGraph graph, inputCount)",
                "injectedBoundary": (
                    "CreateHandleInternal_Injected carries internal-call metadata, but its native body and "
                    "exact by-reference/value lowering are not recovered"
                ),
                "methodTokens": {
                    "Create": "0x06000339",
                    "CreateHandle": "0x0600033A",
                    "constructor": "0x0600033B",
                    "GetHandle": "0x0600033C",
                    "Equals": "0x0600033D",
                    "CreateHandleInternal": "0x0600033E",
                    "staticConstructor": "0x0600033F",
                    "CreateHandleInternal_Injected": "0x06000340",
                },
                "stockAnimationMixerComparison": {
                    "stockTypeToken": "0x02000057",
                    "stockCreateToken": "0x06000371",
                    "stockCreateHasNormalizeWeightsParameter": True,
                    "advancedCreateHasNormalizeWeightsParameter": False,
                    "stockHasImplicitPlayableConversion": True,
                    "advancedHasImplicitPlayableConversion": False,
                    "behavioralEquivalenceProven": False,
                },
                "unresolvedSemantics": [
                    "default and normalized input weights",
                    "null-playable state transitions and equality behavior",
                    "accepted input-count range and failure behavior",
                    "native CreateHandleInternal_Injected implementation",
                ],
            },
            "clipSlots": [
                {"index": 0, "semantic": "start", "pathID": 7360398354216100382},
                {"index": 1, "semantic": "loop", "pathID": 0},
                {"index": 2, "semantic": "end", "pathID": 0},
            ],
            "effectLifetimesSeconds": {
                "P_fxui_lizhiyan_overview_start_01": 2.2,
                "P_fxui_lizhiyan_overview_start_02": 5.0,
                "P_fxui_lizhiyan_overview_start_03": 7.0,
            },
            "clipStopTimeSeconds": 6.366667,
        },
        "effectAnimationControlAbi": {
            "runtimePatchBoundary": (
                "each listed method checks an IFix dispatch ID; the decoded IL2CPP fallback body "
                "does not prove the effective retail body when a patch is active"
            ),
            "methods": {
                "SetManual": body_method(body_targets, "SetManual", "0x060059C7", "0x187431E24", ["useManual"]),
                "ManualEvaluate": body_method(body_targets, "ManualEvaluate", "0x060059D2", "0x187431CB0", ["evaluateTime"]),
                "SyncProgress": body_method(body_targets, "SyncProgress", "0x060059D3", "0x187431FF4", ["progress"]),
                "SetTimeScale": body_method(body_targets, "SetTimeScale", "0x060059D5", "0x1831DD6B0", ["curTimeScale"]),
                "SetIgnoreGlobalTimeScale": body_method(body_targets, "SetIgnoreGlobalTimeScale", "0x060059D6", "0x1834FBFE0", ["ignoreGlobalTimeScale"]),
                "SetStartAnimationDuration": body_method(body_targets, "SetStartAnimationDuration", "0x060059D7", "0x187431E80", ["duration"]),
                "SetStartAnimationScale": body_method(body_targets, "SetStartAnimationScale", "0x060059D8", "0x187431F60", ["scale"]),
                "RefreshRootPlayableTimeScale": body_method(body_targets, "_RefreshRootPlayableTimeScale", "0x060059D9", "0x183434F90", ["force"]),
                "Stop": body_method(body_targets, "Stop", "0x060059DB", "0x1831DC580", []),
                "OnDisable": body_method(body_targets, "OnDisable", "0x060059C9", "0x18450FE60", []),
                "OnRelease": body_method(body_targets, "OnRelease", "0x060059CA", "0x1846107B0", []),
            },
            "fallbackBodyFacts": [
                "SetManual(bool) sets manual-active true in the fallback body; honoring false is visible only through the IFix path",
                "ManualEvaluate(float evaluateTime) requires positive current clip length and calls PlayableGraph.Evaluate_Injected",
                "SyncProgress(float progress) derives an evaluate time from progress/current clip state and delegates to ManualEvaluate",
                "SetStartAnimationDuration and SetStartAnimationScale require positive inputs and force root playable time-scale refresh",
                "SetIgnoreGlobalTimeScale forwards the Boolean to the owning entity when present",
                "OnDisable calls Stop and clears manual-active state",
                "OnRelease destroys the PlayableGraph only when PlayableGraph.IsValid_Injected succeeds",
            ],
            "effectInstanceCallerRoutes": {
                "ManualSyncTime": effect_instance_route(effect_instance_targets, "ManualSyncTime", "0x06005ADD", "0x18743E6E0", ["deltaTime"], {"ManualUpdateAnimation": ["0x49", "0x57", "0x103"]}),
                "ManualUpdateAnimation": effect_instance_route(effect_instance_targets, "ManualUpdateAnimation", "0x06005ADC", "0x18743E838", ["deltaTime"], {"ManualEvaluate": ["0x5C"]}),
                "SyncAnimationProgress": effect_instance_route(effect_instance_targets, "SyncAnimationProgress", "0x06005ADE", "0x18743F1D0", ["progress"], {"SyncProgress": ["0x3B"]}),
                "SetAnimationIgnoreGlobalTimeScale": effect_instance_route(effect_instance_targets, "SetAnimationIgnoreGlobalTimeScale", "0x06005A8E", "0x1834FAA30", ["ignoreGlobalTimeScale"], {"SetIgnoreGlobalTimeScale": ["0x84"]}),
                "SetActive": effect_instance_route(effect_instance_targets, "SetActive", "0x06005AA1", "0x18302A920", ["active"], {"Play": ["0x19B"], "Stop": ["0x1DA"]}),
                "SetEffectPlayState": effect_instance_route(effect_instance_targets, "SetEffectPlayState", "0x06005AA2", "0x18743EBA0", ["play"], {"Stop": ["0x107"], "Play": ["0x131"]}),
            },
            "liZhiyanCallerStatus": "no_asset_specific_caller_proven_for_optional_time_controls",
        },
        "labBoundary": {
            "projectEditorVersion": "2022.3.62f3",
            "retailAdvancedMixerTypeExpectedInEditor": False,
            "standardAnimationMixerPlayableIsExactSubstitute": False,
            "driverStatus": "exact_retail_mixer_type_unavailable_do_not_start_graph",
            "requiredBehavior": (
                "validate admitted source marker; create GameTime graph; target the null-controller/null-avatar "
                "Animator; use the exact three-input advanced mixer; connect only start clip at speed one; "
                "destroy graph at each EffectSetting lifetime"
            ),
            "blockedBy": [
                "retail AdvancedAnimationMixerPlayable is absent from stock Unity 2021/2022 editor AnimationModule assemblies",
                "standard AnimationMixerPlayable equivalence is not proven",
                "active IFix payload state is not closed for EffectAnimation control methods",
                "asset-specific callers of optional time controls are not proven for these Li Zhiyan roots",
                "static renderer identity is not joined to a final draw",
            ],
        },
        "nonClaims": [
            "the standard Unity AnimationMixerPlayable is not treated as the retail advanced mixer",
            "the shared clip is not stretched to an EffectSetting lifetime",
            "a closed managed playable topology does not admit the static renderers or shaders",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file() and args.output.read_text(encoding="utf-8") == rendered,
                "Li Zhiyan playable topology contract drifted")
        print("Li Zhiyan EffectAnimation playable topology verified: exact mixer unavailable")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: visibleAdmission=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
