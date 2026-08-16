#!/usr/bin/env python3
"""Focused test for the Li Zhiyan start_01 static-mesh contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PATH = Path(__file__).with_name("build_lizhiyan_overview_start01_contract.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_start01", PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_current_source_contract() -> None:
    # The builder's public check is exercised separately; constants here pin
    # the non-particle identity that the Unity importer must preserve.
    assert M.EFFECT_NAME == "P_fxui_lizhiyan_overview_start_01"
    assert M.MESH_PATH_ID == -6840663686705882004
    assert M.ANIMATION_CLIP_PATH_ID == 7360398354216100382
    clip = M.animation_clip_contract(M.ANIMATION_CLIP)
    assert clip["name"] == "A_fxui__lizhiyan_overview_start_01"
    assert clip["sampleRate"] == 30.0
    assert clip["stopTime"] == 6.366667
    assert clip["events"] == []
    assert set(M.MATERIAL_PATHS) == {
        -6912999194325832649, 2993445828574428557, 3282333668994552481
    }


if __name__ == "__main__":
    test_current_source_contract()
    print("Li Zhiyan start_01 contract tests passed: 1")
