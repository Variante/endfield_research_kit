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
    assert topology["updateMode"] == "GameTime"
    assert [row["pathID"] for row in topology["clipSlots"]] == [
        7360398354216100382, 0, 0
    ]
    assert contract["labBoundary"]["standardAnimationMixerPlayableIsExactSubstitute"] is False
    assert contract["visibleAdmission"] is False


if __name__ == "__main__":
    test_topology()
    print("Li Zhiyan playable topology tests passed: 1")
