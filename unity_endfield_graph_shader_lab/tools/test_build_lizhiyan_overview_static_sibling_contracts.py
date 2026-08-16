#!/usr/bin/env python3
"""Focused tests for Li Zhiyan start_02/_03 static source contracts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PATH = Path(__file__).with_name("build_lizhiyan_overview_static_sibling_contracts.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_static_siblings", PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_specs() -> None:
    assert M.ANIMATION_CLIP_PATH_ID == 7360398354216100382
    assert [(row.name, row.duration) for row in M.SPECS] == [
        ("P_fxui_lizhiyan_overview_start_02", 5.0),
        ("P_fxui_lizhiyan_overview_start_03", 7.0),
    ]
    assert [len(row.mesh_paths) for row in M.SPECS] == [1, 2]
    assert [len(row.material_paths) for row in M.SPECS] == [3, 3]


if __name__ == "__main__":
    test_specs()
    print("Li Zhiyan start_02/_03 contract tests passed: 1")
