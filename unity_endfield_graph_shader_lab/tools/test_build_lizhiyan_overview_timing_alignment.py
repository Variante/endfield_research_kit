#!/usr/bin/env python3
"""Focused checks for Li Zhiyan source/video timing alignment."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PATH = Path(__file__).with_name("build_lizhiyan_overview_timing_alignment.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_timing", PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_current_sources_and_alignment() -> None:
    contract = M.build()
    controller = contract["sourceClosedControllerTiming"]
    compatibility = contract["labCompatibilityChronology"]
    samples = contract["retailVisualAlignment"]["mappedSamples"]
    static = contract["sourceClosedStaticEffectMaterialChronology"]
    assert controller["entryClipLocalSeconds"] == 0.062452073
    assert controller["exitClipLocalSeconds"] == 10.68547903
    assert controller["transitionDurationSeconds"] == 0.014519697
    assert compatibility["effectCreateClipLocalSeconds"] == 0.895782073
    assert compatibility["effectDestroyClipLocalSeconds"] == 3.229112073
    assert [row["compatibilityFingerEffectWindow"] for row in samples] == [
        "inactive", "active", "inactive", "inactive", "inactive", "inactive"
    ]
    assert contract["visibleAdmission"] is False
    assert static["curveCount"] == 53
    assert len(static["targetWindows"]) == 10
    assert {row["effectRoot"] for row in static["targetWindows"]} == {
        "P_fxui_lizhiyan_overview_start_01",
        "P_fxui_lizhiyan_overview_start_02",
        "P_fxui_lizhiyan_overview_start_03",
    }


if __name__ == "__main__":
    test_current_sources_and_alignment()
    print("Li Zhiyan overview timing alignment tests passed: 1")
