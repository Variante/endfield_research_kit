#!/usr/bin/env python3
"""Focused tests for the Li Zhiyan retail visual oracle builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_lizhiyan_retail_visual_oracle.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_visual_oracle", MODULE_PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_select_expression_uses_exact_integer_pts() -> None:
    expression = M._select_expression(((38000, "a"), (40000, "b")))
    assert expression == "eq(pts,38000)+eq(pts,40000)"


def test_measure_roi_has_fixed_quarter_scale_and_teal_predicate() -> None:
    frame = bytearray(M.WIDTH * M.HEIGHT * 3)
    bounds = (0, 0, 8, 8)
    # Scaled ROI is 2x2. Two pixels satisfy the fixed teal predicate.
    pixels = [(10, 100, 90), (60, 70, 90), (0, 80, 80), (90, 100, 100)]
    for pixel_index, rgb in enumerate(pixels):
        x = pixel_index % 2
        y = pixel_index // 2
        offset = (y * M.WIDTH + x) * 3
        frame[offset:offset + 3] = bytes(rgb)
    measured = M.measure_roi(bytes(frame), bounds)
    assert measured["scaledBoundsXyxy"] == [0, 0, 2, 2]
    assert measured["pixelCount"] == 4
    assert measured["tealPixelCount"] == 2
    assert measured["tealCoverage"] == 0.5


def test_all_samples_stay_non_admitting() -> None:
    assert [row[0] for row in M.SAMPLES] == [38000, 40000, 42000, 43000, 44000, 46000]
    assert M.SCHEMA.endswith(".v1")


if __name__ == "__main__":
    test_select_expression_uses_exact_integer_pts()
    test_measure_roi_has_fixed_quarter_scale_and_teal_predicate()
    test_all_samples_stay_non_admitting()
    print("Li Zhiyan retail visual oracle tests passed: 3")
