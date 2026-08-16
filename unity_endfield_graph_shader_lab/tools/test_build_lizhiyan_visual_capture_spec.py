#!/usr/bin/env python3
"""Focused tests for the Li Zhiyan visual capture-spec builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_lizhiyan_visual_capture_spec.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_visual_capture_spec", MODULE_PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_capture_pts_are_sorted_and_map_to_exact_local_milliseconds() -> None:
    assert list(M.MINIMAL_CAPTURE_PTS) == sorted(M.MINIMAL_CAPTURE_PTS)
    assert M.MINIMAL_CAPTURE_PTS[0] == M.RESTART_PTS
    assert (40834 - M.RESTART_PTS) / 1000.0 == 2.867
    assert (39367 - M.RESTART_PTS) / 1000.0 == 1.4
    assert (41434 - M.RESTART_PTS) / 1000.0 == 3.467
    assert (43867 - M.RESTART_PTS) / 1000.0 == 5.9
    assert (44967 - M.RESTART_PTS) / 1000.0 == 7.0


def test_source_contracts_and_statuses_are_current() -> None:
    contract = M.build()
    assert contract["schema"].endswith(".v1")
    assert contract["status"] == "diagnostic_only"
    assert contract["eventOriginProven"] is False
    assert contract["visibleAdmission"] is False
    assert contract["clock"]["restartCandidatePts"] == 37967
    assert contract["minimalCapturePts"] == list(M.MINIMAL_CAPTURE_PTS)
    assert len(contract["minimalCapturePts"]) == 24
    assert [row["endRetailPts"] for row in contract["effectLifetimes"]] == [40167, 42967, 44967]
    assert contract["sharedMaterialClip"]["nearestCapturePts"] == 44334
    assert contract["sources"]["timingAlignment"]["status"] == "source_timing_closed_retail_request_epoch_pending"
    assert contract["sources"]["timingAlignment"]["visibleAdmission"] is False


if __name__ == "__main__":
    test_capture_pts_are_sorted_and_map_to_exact_local_milliseconds()
    test_source_contracts_and_statuses_are_current()
    print("Li Zhiyan visual capture-spec tests passed: 2")
