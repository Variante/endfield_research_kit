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
    assert [row["pathID"] for row in topology["clipSlots"]] == [
        7360398354216100382, 0, 0
    ]
    assert contract["labBoundary"]["standardAnimationMixerPlayableIsExactSubstitute"] is False
    abi = contract["effectAnimationControlAbi"]
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
    assert contract["visibleAdmission"] is False


if __name__ == "__main__":
    test_topology()
    print("Li Zhiyan playable topology tests passed: 1")
