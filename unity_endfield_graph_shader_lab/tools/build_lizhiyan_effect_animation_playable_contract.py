#!/usr/bin/env python3
"""Build the fail-closed retail EffectAnimation playable-topology contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
BODY_TARGETS = REPO / "scratch/character_recovery/overview_effect_owner/effect_native_body_targets.json"
EFFECT_INSTANCE_TARGETS = (
    REPO / "scratch/reverse_engineering/zhuangfy_lizi_lodfade_20260724/"
    "effect_instance_native.json"
)
EFFECT_LIFECYCLE_TARGETS = (
    REPO / "scratch/reverse_engineering/zhuangfy_lizi_lodfade_20260724/"
    "effect_lifecycle_native.json"
)
OWNER_REPORT = REPO / "reports/assets/character_recovery/overview_effect_owner_animator_negative_20260815.md"
STATIC_CONTRACT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_01_effect.json"
SIBLING_CONTRACT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_02_03_effects.json"
INSTALLED_IFIX_STATE = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "installed_ifix_patch_state.json"
)
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


def external_artifact(path: Path, kind: str) -> dict[str, Any]:
    return {
        "pathAtRecovery": path.resolve().as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "objectType": kind,
    }


def pe_file_offset(data: bytes, virtual_address: int) -> int:
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional = pe + 24
    image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    section = optional + struct.unpack_from("<H", data, pe + 20)[0]
    rva = virtual_address - image_base
    for index in range(section_count):
        offset = section + index * 40
        virtual_size, section_rva, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        if section_rva <= rva < section_rva + max(virtual_size, raw_size):
            return raw_offset + rva - section_rva
    raise RuntimeError(f"VA 0x{virtual_address:X} is outside the PE image")


def validate_unityplayer_native_contract(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    require(
        len(data) == 38194232
        and hashlib.sha256(data).hexdigest().upper()
        == "B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2",
        "installed UnityPlayer build drifted",
    )

    def validate_icall(
        index: int, name_slot: int, function_slot: int, expected_name: str,
        expected_target: int, body_size: int, body_sha256: str,
    ) -> dict[str, Any]:
        name_pointer = struct.unpack_from("<Q", data, name_slot)[0]
        target = struct.unpack_from("<Q", data, function_slot)[0]
        name_offset = pe_file_offset(data, name_pointer)
        end = data.index(b"\0", name_offset)
        name = data[name_offset:end].decode("ascii")
        require(name == expected_name and target == expected_target,
                f"UnityPlayer internal call {expected_name} drifted")
        body_offset = pe_file_offset(data, target)
        body = data[body_offset:body_offset + body_size]
        require(hashlib.sha256(body).hexdigest() == body_sha256,
                f"UnityPlayer body {expected_name} drifted")
        return {
            "tableIndex": index,
            "name": name,
            "namePointerSlotFileOffset": f"0x{name_slot:X}",
            "functionPointerSlotFileOffset": f"0x{function_slot:X}",
            "nativeTargetVA": f"0x{target:X}",
            "nativeBodyBytes": body_size,
            "nativeBodySha256": body_sha256,
        }

    def validate_body(va: int, size: int, expected_sha256: str) -> dict[str, Any]:
        offset = pe_file_offset(data, va)
        body = data[offset:offset + size]
        require(hashlib.sha256(body).hexdigest() == expected_sha256,
                f"UnityPlayer body 0x{va:X} drifted")
        return {
            "va": f"0x{va:X}",
            "bytes": size,
            "sha256": expected_sha256,
        }

    return {
        "source": external_artifact(path, "PinnedRetailUnityPlayer"),
        "advancedMixerCreate": validate_icall(
            501, 0x20DD608, 0x20DF118,
            "UnityEngine.Animations.AdvancedAnimationMixerPlayable::CreateHandleInternal_Injected",
            0x180158B30, 66,
            "a1344805c7af26cc4c405b18c770e862a7a3c3108d06d9efaa170ce57e71be25",
        ),
        "rendererEntityId": validate_icall(
            1278, 0x20D4FA0, 0x20CD1F0, "UnityEngine.Renderer::get_entityID",
            0x1800E6C40, 324,
            "b9b416829ec0528693a48ec4116a2e71ed7d4d26893866fc807aa59c86045e79",
        ),
        "advancedMixerInputCount": validate_body(
            0x18074EAA0, 121,
            "0cd93353cb9280e457b88630ff0332c2c831dc666c8fdba57bb1bc889c98e2fb",
        ),
        "advancedMixerInputWeight": validate_body(
            0x18074EB20, 38,
            "8d84b5f59d398bbb9b7345b78bccba930f60930c27403fb9d54ca79363a90e99",
        ),
        "setInputCountDispatch": validate_body(
            0x18075E9D0, 205,
            "6b6ff53abbb2469c4a65b8cd1d9f0225f055582e3594371a4882020c2ef9e8bd",
        ),
        "advancedMixerInitializer": validate_body(
            0x180AC6330, 42,
            "0c83d36fb5450ae8fbc9930f7e56e23d1da17788bb6f80c37083eac60c525f72",
        ),
        "stockMixerInitializer": validate_body(
            0x180AA5950, 137,
            "c6cb43e0ea30297f92540a1c0705977a304087a0acc7254d28ff62e4fa932214",
        ),
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


def lod_method(body_targets: dict[str, Any], name: str, token: str, va: str) -> dict[str, str]:
    rows = [
        row for row in body_targets["bodyTargets"]
        if row.get("type") == "Beyond.Gameplay.EffectLodCfg" and row.get("method") == name
    ]
    require(len(rows) == 1, f"EffectLodCfg.{name} body target missing or ambiguous")
    row = rows[0]
    require(row["token"].upper() == token.upper() and row["methodPointerVa"].upper() == va.upper(),
            f"EffectLodCfg.{name} ABI drifted")
    return {"token": token, "va": va}


def renderer_ids(effect: dict[str, Any]) -> list[int]:
    return [
        int(row["renderer"]["m_PathID"])
        for row in effect["effectSetting"]["fields"]["lodSetting"]
        if int(row["renderer"]["m_PathID"]) != 0
    ]


def build() -> dict[str, Any]:
    for path in (
        BODY_TARGETS, EFFECT_INSTANCE_TARGETS, EFFECT_LIFECYCLE_TARGETS, OWNER_REPORT, STATIC_CONTRACT,
        SIBLING_CONTRACT, INSTALLED_IFIX_STATE,
    ):
        require(path.is_file(), f"playable topology source missing: {path}")
    body_targets = json.loads(BODY_TARGETS.read_text(encoding="utf-8"))
    effect_instance_targets = json.loads(EFFECT_INSTANCE_TARGETS.read_text(encoding="utf-8"))
    effect_lifecycle_targets = json.loads(EFFECT_LIFECYCLE_TARGETS.read_text(encoding="utf-8"))
    start01 = json.loads(STATIC_CONTRACT.read_text(encoding="utf-8"))
    siblings = json.loads(SIBLING_CONTRACT.read_text(encoding="utf-8"))
    ifix_state = json.loads(INSTALLED_IFIX_STATE.read_text(encoding="utf-8"))
    unityplayer_path = Path(ifix_state["source_build"]["game_assembly"]["path_at_recovery"]).parent / "UnityPlayer.dll"
    require(unityplayer_path.is_file(), f"installed UnityPlayer missing: {unityplayer_path}")
    unityplayer = validate_unityplayer_native_contract(unityplayer_path)
    require(start01["animation"]["startAnimationClip"]["pathID"] == 7360398354216100382,
            "start_01 shared clip identity drifted")
    require(siblings["sharedAnimation"]["pathID"] == 7360398354216100382,
            "sibling shared clip identity drifted")
    patch_file = ifix_state["vfs_state"]["persistent_overlay"]["file"]
    protected_types = {
        "Beyond.Gameplay.EffectAnimation",
        "Beyond.Gameplay.EffectInstance",
        "Beyond.Gameplay.EffectLodCfg",
    }
    targets = ifix_state["targets"]
    require(
        patch_file["size"] == 86926
        and patch_file["sha256"].upper()
        == "BAA28AE497E64D94E152886622BBE5FB391199BCBF8366E2DF91591C9A9F172C"
        and len(targets) == 32,
        "installed Persistent IFix snapshot drifted",
    )
    protected_targets = [row for row in targets if row["type"] in protected_types]
    require(not protected_targets, "installed IFix patch now targets EffectAnimation ownership")
    return {
        "schema": "endfield.lizhiyan-effect-animation-playable-topology.v1",
        "status": "retail_topology_and_installed_fallback_closed_editor_advanced_mixer_unavailable_visible_fail_closed",
        "visibleAdmission": False,
        "sources": {
            "nativeBodyTargets": artifact(BODY_TARGETS, "PinnedNativeBodyTargets"),
            "effectInstanceBodyTargets": artifact(EFFECT_INSTANCE_TARGETS, "PinnedEffectInstanceBodyTargets"),
            "effectLifecycleBodyTargets": artifact(EFFECT_LIFECYCLE_TARGETS, "PinnedEffectLifecycleBodyTargets"),
            "ownerReport": artifact(OWNER_REPORT, "NativeOwnerReport"),
            "start01Contract": artifact(STATIC_CONTRACT, "Start01EffectContract"),
            "siblingContract": artifact(SIBLING_CONTRACT, "SiblingEffectContract"),
            "installedIfixState": artifact(INSTALLED_IFIX_STATE, "InstalledIfixPatchState"),
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
                "setSourcePlayableCallOffset": "0x15F",
                "setSourcePlayableVA": "0x1834380EF",
            },
            "addClip": {
                "token": "0x060059CD",
                "va": "0x183437D60",
                "animationClipPlayableCreateVA": "0x183437E02",
                "connectCallOffset": "0x129",
                "connectCallVA": "0x183437E89",
                "operation": "graph.Connect(clipPlayable,0,mixer,animationState-1)",
                "nullClipBehavior": "return_before_create_and_connect",
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
                    "CreateHandleInternal_Injected is bound to UnityPlayer 0x180158B30 and creates the "
                    "retail 0x178 native node; input count and weights are handled later"
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
                    "advanced-only vtable slots outside shared input count and weight operations",
                    "null-playable type-specific transitions and equality behavior",
                    "extreme allocation-failure behavior",
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
            "playAnimationStateMachine": {
                "methodToken": "0x060059D1",
                "methodVA": "0x183436AD0",
                "targetInput": "animationState-1",
                "loopInputs": [0, 1, 2],
                "operations": [
                    {
                        "callOffset": "0x447",
                        "callVA": "0x183436F17",
                        "identity": "PlayableExtensions.SetInputWeight<AdvancedAnimationMixerPlayable>",
                        "arguments": "mixer,inputIndex,(inputIndex==targetInput?1.0:0.0)",
                    },
                    {
                        "callOffset": "0x482",
                        "callVA": "0x183436F52",
                        "identity": "PlayableExtensions.IsValid<AnimationClipPlayable>",
                        "arguments": "clipPlayable[inputIndex]",
                    },
                    {
                        "callOffset": "0x4A0",
                        "callVA": "0x183436F70",
                        "identity": "PlayableExtensions.Pause<AnimationClipPlayable>",
                        "condition": "inputIndex!=targetInput_and_valid",
                    },
                    {
                        "callOffset": "0x4AE",
                        "callVA": "0x183436F7E",
                        "identity": "PlayableExtensions.Play<AnimationClipPlayable>",
                        "condition": "inputIndex==targetInput_and_valid",
                    },
                    {
                        "callOffset": "0x4C6",
                        "callVA": "0x183436F96",
                        "identity": "PlayableExtensions.SetTime<AnimationClipPlayable>",
                        "arguments": "clipPlayable[inputIndex],0.0",
                        "condition": "valid_after_Play_or_Pause",
                    },
                ],
                "weightMode": "one_hot_no_cross_fade",
                "validClipTimeResetSeconds": 0.0,
                "currentPlayableFieldOffset": "0xC8",
            },
            "liZhiyanStartOnlyEffectiveRoute": {
                "connectedInputs": [0],
                "unconnectedInputs": [1, 2],
                "weightsOnStart": [1.0, 0.0, 0.0],
                "slot0Operations": ["Play", "SetTime(0.0)"],
                "slot1And2Behavior": "weights_written_zero_no_clip_operation",
                "crossFade": False,
                "classification": "retail_start_only_graph_control_closed",
            },
            "liZhiyanAdvancedApplicability": {
                "advancedMixerCreation": "proven_applicable",
                "threeInputGraph": "proven_applicable",
                "startOnlyConnectAndOneHotControl": "proven_applicable",
                "customStageTimelineRuntimeExists": True,
                "customStageTimelineLiActivation": "not_proven_fail_closed",
                "serializedStageProducer": "not_found_in_start01_start02_start03_effect_roots",
                "serializedFacts": {
                    "rootAnimator": True,
                    "effectAnimationHelper": True,
                    "controller": None,
                    "avatar": None,
                    "effectSettingLifetimesSeconds": [2.2, 5.0, 7.0],
                    "sharedClipLengthSeconds": 6.366667,
                },
                "lifetimeInterpretation": (
                    "EffectSetting destruction boundaries do not prove mixer stage count, clip retiming, "
                    "or native custom-timeline population"
                ),
                "backendDecision": (
                    "do not inject custom stage behavior into Li; stock mixer may host an explicitly "
                    "labeled proven-external-behavior simulation but is not retail ABI equivalent"
                ),
                "visibleAdmission": False,
            },
        },
        "retailAdvancedMixerNative": {
            **unityplayer["advancedMixerCreate"],
            "managedWrappers": {
                "Create": "0x183E0F350",
                "CreateHandle": "0x183E0F450",
                "CreateHandleInternal": "0x183E0F5C0",
                "CreateHandleInternal_Injected": "0x183E0FA30",
                "SetInputCount": "0x183E0F8D0",
                "SetInputCount_Injected": "0x183E0F910",
            },
            "nativeCreateHelperVA": "0x180B3E5C0",
            "invalidGraphDiagnosticVA": "0x1807791C0",
            "advancedNodeTypeId": "0x178",
            "stockNodeTypeId": "0x170",
            "handleLayout": {
                "nativePointerOffset": 0,
                "versionOffset": 8,
                "meaningfulBytes": 12,
                "storageBytes": 16,
            },
            "sharedInputOperations": {
                "setInputCount": unityplayer["advancedMixerInputCount"],
                "setInputWeight": unityplayer["advancedMixerInputWeight"],
                "dispatch": unityplayer["setInputCountDispatch"],
                "advancedAndStockShareVirtualTargets": True,
                "slotStrideBytes": 16,
                "slotPlayablePointerOffset": 0,
                "slotWeightOffset": 8,
                "newAndReactivatedSlotsAreZeroed": True,
                "defaultPlayable": "null",
                "defaultWeight": 0.0,
                "automaticNormalization": False,
                "acceptedInputCount": "all_nonnegative_counts_subject_to_allocation",
                "negativeInputCount": "diagnostic_Playable_input_count_cannot_be_negative",
                "setWeightBounds": "writes_only_when_0_le_index_lt_current_count_and_weight_not_negative",
                "nanWeightBehavior": "written_because_nan_does_not_satisfy_negative_test",
            },
            "initializers": {
                "advanced": unityplayer["advancedMixerInitializer"],
                "stock": unityplayer["stockMixerInitializer"],
                "advancedCallsStockInitializer": True,
                "advancedRootVtableVA": "0x181DDBD08",
                "stockRootVtableVA": "0x181DDAC48",
                "advancedExtraWordOffset": "0x170",
                "advancedExtraWordValue": "0x0101",
            },
            "advancedOnlyStateSlots": {
                "stateFields": {
                    "state170": {"offset": "0x170", "initialValue": 1},
                    "state171": {"offset": "0x171", "initialValue": 1},
                    "word174": {"offset": "0x174", "initialValue": "initializer_dependent"},
                },
                "slot3": {
                    "va": "0x180AD5230",
                    "stockVA": "0x180076890",
                    "stockBehavior": "no_op",
                    "behavior": (
                        "validates input/runtime context; computes double evaluation time from source "
                        "float+0x40 times double+0x08; invalid context sets state170=1; first valid call "
                        "with state171=1 clears state171 and calls 0x180A5A680; later calls "
                        "0x180A634D0(context,time,source,&state170)"
                    ),
                    "firstHandshakeVA": "0x180A5A680",
                    "subsequentRuntimeVA": "0x180A634D0",
                },
                "slot4": {
                    "va": "0x180AD87C0",
                    "stockVA": "0x18074F180",
                    "behavior": "sets word174=0 and state170=1 then tail-calls stock time/speed propagation",
                },
                "slot13": {
                    "va": "0x180AD43E0",
                    "stockVA": "0x180076890",
                    "stockBehavior": "no_op",
                    "commands": {
                        "0": "word174=0",
                        "1": "state170=1_and_state171=1",
                        "other": "no_op",
                    },
                },
                "slot18": {
                    "va": "0x180AD59F0",
                    "stockVA": "0x180AA8230",
                    "behavior": "tail_call_stock_only_when_state170_or_state171_nonzero",
                },
                "slot19": {
                    "va": "0x180AD5460",
                    "stockVA": "0x180AA7B10",
                    "behavior": "tail_call_stock_only_when_state170_or_state171_nonzero",
                },
                "stockImplementationsDiffer": True,
                "restrictedStartOnlyStockEquivalenceProven": False,
                "classification": "advanced_runtime_state_gate_not_reproducible_with_stock_mixer",
                "nativeSchedulerBoundary": (
                    "managed EffectAnimation does not call these slots directly; PlayableGraph native "
                    "evaluation dispatches them indirectly, and exact named scheduler callsites remain open"
                ),
                "unity2022EmulationDecision": (
                    "stock AnimationMixerPlayable reproduces topology/weights/clip control only; a "
                    "ScriptPlayable cannot be retail-faithful until the 0x180A5A680 and 0x180A634D0 "
                    "runtime callbacks and scheduler contract are reproduced"
                ),
                "runtimeCallbacks": {
                    "reset": {
                        "va": "0x180A5A680",
                        "bytes": 45,
                        "writes": {
                            "context+0x9E8..0x9FF": "zero",
                            "context+0xA04": 0,
                            "context+0xA08": "0x00010101",
                            "context+0xA0C": 0,
                        },
                        "classification": "advanced_animation_state_record_reset",
                    },
                    "update": {
                        "va": "0x180A634D0",
                        "stageProcessorVA": "0x180AC4A90",
                        "stageRecordStrideBytes": 28,
                        "stageTableOffset": "0x748",
                        "stageIndexOffset": "0x768",
                        "stageCountOffset": "0x758",
                        "stateRecordOffset": "0x9E8",
                        "requiresContextEnabledOffset": "0x744",
                        "classification": "gated_per_stage_custom_animation_timeline_update",
                    },
                    "stageProcessor": {
                        "va": "0x180AC4A90",
                        "modes": [0, 1, 2, 3],
                        "provenEffects": [
                            "advances double time and float accumulator",
                            "increments stage count and selects 28-byte stage records",
                            "writes time back to the caller at stage boundaries",
                            "sets node state170 and packed state flags",
                            "handles mode-specific jump_loop_transition_or_end flags",
                        ],
                        "semanticNames": "not_uniquely_recovered_do_not_label_modes",
                    },
                    "additionalDirectUpdateCallers": ["0x180AD52C0", "0x180ADA2D0"],
                    "publicPlayableApiEquivalent": False,
                    "exactBackendRequirement": (
                        "native custom playable node/shim, or a complete managed rewrite explicitly "
                        "classified as behavioral simulation rather than retail ABI equivalence"
                    ),
                },
            },
            "classification": "native_create_and_shared_input_semantics_closed_advanced_slots_pending",
            "provenBehavior": [
                "validates a non-null graph handle and masked version",
                "allocates and attaches a distinct native 0x178 playable node",
                "materializes a native-pointer plus version PlayableHandle",
                "CreateHandle applies inputCount only after injected creation through SetInputCount",
                "new input slots are null and zero-weight with no automatic normalization",
            ],
            "failureBoundary": (
                "invalid graphs and negative input counts reach diagnostics; extreme allocation failure "
                "and advanced-only virtual slots remain unresolved"
            ),
        },
        "effectAnimationControlAbi": {
            "installedPatchState": {
                "patchSha256": patch_file["sha256"].upper(),
                "patchBytes": patch_file["size"],
                "targetCount": len(targets),
                "protectedTypes": sorted(protected_types),
                "matchingTargets": protected_targets,
                "classification": "current_installed_persistent_patch_does_not_replace_effect_animation_chain",
                "evidenceBoundary": (
                    "proves the currently installed local Persistent VFS snapshot only; a later "
                    "downloaded patch or live manager mutation remains outside offline evidence"
                ),
            },
            "effectiveBodyForInstalledSnapshot": "decoded_il2cpp_fallback_body",
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
        "effectLodRendererOwnership": {
            "managedField": {
                "declaringType": "Beyond.Gameplay.EffectLodCfg",
                "declaringTypeToken": "0x02000DB9",
                "name": "renderer",
                "fieldToken": "0x04004F24",
                "fieldType": "UnityEngine.Renderer",
            },
            "lifecycle": {
                "Play": lod_method(effect_lifecycle_targets, "Play", "0x06005C9E", "0x1834FC5E0"),
                "Stop": lod_method(effect_lifecycle_targets, "Stop", "0x06005C9F", "0x18339BE80"),
            },
            "serializedBindings": [
                {
                    "effect": "P_fxui_lizhiyan_overview_start_01",
                    "effectSettingPathID": start01["effectSetting"]["pathID"],
                    "rendererPathIDs": renderer_ids(start01),
                },
                *[
                    {
                        "effect": effect["effectName"],
                        "effectSettingPathID": effect["effectSetting"]["pathID"],
                        "rendererPathIDs": renderer_ids(effect),
                    }
                    for effect in siblings["effects"]
                ],
            ],
            "provenBehavior": (
                "EffectLodCfg.Play enables its configured Renderer and EffectLodCfg.Stop disables "
                "or resets the same managed lifecycle; each non-null lodSetting renderer is an exact "
                "serialized Li Zhiyan MeshRenderer PathID"
            ),
            "nativeJoinStatus": "managed_renderer_to_hgtree_survivor_record_unresolved_fail_closed",
            "ordinaryRendererNativeIdentity": {
                **unityplayer["rendererEntityId"],
                "managedBackingPointerHelperVA": "0x180769270",
                "nativeEntityIdOffset": "0x268",
                "classification": "ordinary_renderer_native_entity_id_field_closed_semantic_join_pending",
                "managedWrapperVA": "0x18302D0E0",
                "directManagedCallersInGameAssemblyText": 0,
                "nativeBodyEntityLoads": ["0x1800E6D16", "0x1800E6D38"],
                "consumerClassification": "no_static_managed_consumer_or_hgtree_join",
            },
            "hgMeshRendererComparison": {
                "getEntityManagedVA": "0x18B3FA3B0",
                "getEntityInjectedUnityPlayerVA": "0x1801E04E0",
                "hasEntityUnityPlayerVA": "0x1801E0340",
                "nativeEntityOffset": "0x50",
                "requiresNonzeroOffsets": ["0x50", "0x54"],
                "ordinaryRendererEquivalent": False,
            },
            "remainingIdentityEdge": (
                "a concrete UnityEngine.MeshRenderer pointer or instance id must be joined to the "
                "native entity/renderer index and one accepted 64-byte HGTree record"
            ),
            "nonClaims": [
                "native ECS component slot 67 is not EffectLodCfg.renderer",
                "ordinary Renderer native+0x268 is not proven equal to HGMeshRenderer native+0x50",
                "generic HGTree renderer-list creation does not assign a Li Zhiyan PathID to a draw",
                "HGTree vtable +0x268 calls are context methods, not Renderer native+0x268 field reads",
            ],
        },
        "labBoundary": {
            "projectEditorVersion": "2022.3.62f3",
            "retailAdvancedMixerTypeExpectedInEditor": False,
            "standardAnimationMixerPlayableIsExactSubstitute": False,
            "driverStatus": "exact_retail_mixer_type_unavailable_do_not_start_graph",
            "requiredBehavior": (
                "validate admitted source marker; create GameTime graph; target the null-controller/null-avatar "
                "Animator; use the exact three-input advanced mixer; connect only start clip; write weights "
                "one-hot as 1/0/0; Play and reset start to time zero at speed one; "
                "destroy graph at each EffectSetting lifetime"
            ),
            "blockedBy": [
                "retail AdvancedAnimationMixerPlayable is absent from stock Unity 2021/2022 editor AnimationModule assemblies",
                "standard AnimationMixerPlayable equivalence is not proven",
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
