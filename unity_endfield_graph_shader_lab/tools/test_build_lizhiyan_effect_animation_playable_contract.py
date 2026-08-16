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
    assert [row["pathID"] for row in topology["clipSlots"]] == [
        7360398354216100382, 0, 0
    ]
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
