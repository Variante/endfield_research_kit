#!/usr/bin/env python3
"""Focused test for Li Zhiyan retail EffectAnimation playable topology."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PATH = Path(__file__).with_name("build_lizhiyan_effect_animation_playable_contract.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_playable_topology", PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_topology() -> None:
    contract = M.build()
    topology = contract["retailEffectAnimationTopology"]
    assert topology["mixer"]["inputCount"] == 3
    assert topology["mixer"]["fieldTokens"]["m_NullPlayable"] == "0x04000152"
    assert topology["mixer"]["stockAnimationMixerComparison"]["behavioralEquivalenceProven"] is False
    assert topology["updateMode"] == "GameTime"
    native_mixer = contract["retailAdvancedMixerNative"]
    assert native_mixer["tableIndex"] == 501
    assert native_mixer["nativeTargetVA"] == "0x180158B30"
    assert native_mixer["advancedNodeTypeId"] == "0x178"
    assert native_mixer["stockNodeTypeId"] == "0x170"
    assert native_mixer["handleLayout"]["meaningfulBytes"] == 12
    inputs = native_mixer["sharedInputOperations"]
    assert inputs["advancedAndStockShareVirtualTargets"] is True
    assert inputs["slotStrideBytes"] == 16
    assert inputs["defaultPlayable"] == "null"
    assert inputs["defaultWeight"] == 0.0
    assert inputs["automaticNormalization"] is False
    assert native_mixer["initializers"]["advancedExtraWordValue"] == "0x0101"
    advanced_slots = native_mixer["advancedOnlyStateSlots"]
    assert advanced_slots["slot3"]["va"] == "0x180AD5230"
    assert advanced_slots["slot3"]["firstHandshakeVA"] == "0x180A5A680"
    assert advanced_slots["slot3"]["subsequentRuntimeVA"] == "0x180A634D0"
    assert advanced_slots["stateFields"]["state170"]["initialValue"] == 1
    assert advanced_slots["stateFields"]["state171"]["initialValue"] == 1
    assert advanced_slots["slot13"]["commands"]["1"] == "state170=1_and_state171=1"
    assert advanced_slots["stockImplementationsDiffer"] is True
    assert advanced_slots["restrictedStartOnlyStockEquivalenceProven"] is False
    assert [row["pathID"] for row in topology["clipSlots"]] == [
        7360398354216100382, 0, 0
    ]
    state_machine = topology["playAnimationStateMachine"]
    assert [row["callOffset"] for row in state_machine["operations"]] == [
        "0x447", "0x482", "0x4A0", "0x4AE", "0x4C6"
    ]
    assert state_machine["weightMode"] == "one_hot_no_cross_fade"
    start_only = topology["liZhiyanStartOnlyEffectiveRoute"]
    assert start_only["weightsOnStart"] == [1.0, 0.0, 0.0]
    assert start_only["slot0Operations"] == ["Play", "SetTime(0.0)"]
    assert start_only["crossFade"] is False
    assert contract["labBoundary"]["standardAnimationMixerPlayableIsExactSubstitute"] is False
    abi = contract["effectAnimationControlAbi"]
    patch = abi["installedPatchState"]
    assert patch["patchBytes"] == 86926
    assert patch["targetCount"] == 32
    assert patch["matchingTargets"] == []
    assert abi["effectiveBodyForInstalledSnapshot"] == "decoded_il2cpp_fallback_body"
    assert abi["methods"]["ManualEvaluate"]["parameters"] == ["evaluateTime"]
    assert abi["methods"]["SyncProgress"]["parameters"] == ["progress"]
    assert abi["methods"]["SetManual"]["ifFixDispatchIds"] == ["0x64ca"]
    assert abi["methods"]["SetStartAnimationDuration"]["ifFixDispatchIds"] == ["0x64d3"]
    assert abi["effectInstanceCallerRoutes"]["ManualUpdateAnimation"]["calls"] == {
        "ManualEvaluate": ["0x5C"]
    }
    assert abi["effectInstanceCallerRoutes"]["SetActive"]["calls"] == {
        "Play": ["0x19B"], "Stop": ["0x1DA"]
    }
    assert abi["liZhiyanCallerStatus"] == "no_asset_specific_caller_proven_for_optional_time_controls"
    ownership = contract["effectLodRendererOwnership"]
    assert ownership["managedField"]["fieldToken"] == "0x04004F24"
    assert ownership["ordinaryRendererNativeIdentity"]["tableIndex"] == 1278
    assert ownership["ordinaryRendererNativeIdentity"]["nativeEntityIdOffset"] == "0x268"
    assert ownership["ordinaryRendererNativeIdentity"]["directManagedCallersInGameAssemblyText"] == 0
    assert ownership["hgMeshRendererComparison"]["nativeEntityOffset"] == "0x50"
    assert ownership["hgMeshRendererComparison"]["ordinaryRendererEquivalent"] is False
    assert [row["rendererPathIDs"] for row in ownership["serializedBindings"]] == [
        [-1741348596941359387, 4708942470875150053, 8270785745755535077,
         -6436609233402104091],
        [-6295135500902477663, 761294555274727585, 8727063177047822497],
        [5803225578291246396, 2656199819621283132, -7969026351845493444],
    ]
    assert ownership["nativeJoinStatus"].endswith("unresolved_fail_closed")
    assert contract["visibleAdmission"] is False


if __name__ == "__main__":
    test_topology()
    print("Li Zhiyan playable topology tests passed: 1")
