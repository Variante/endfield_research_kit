#!/usr/bin/env python3
"""Focused tests for the Endminf secondary-dynamics trajectory comparison."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parent
    / "build_endminf_secondary_dynamics_trajectory_comparison.py"
)
SPEC = importlib.util.spec_from_file_location("trajectory_comparison", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TrajectoryComparisonTests(unittest.TestCase):
    def test_current_capture_schema_is_admitted_explicitly(self) -> None:
        self.assertIn(
            "endfield.endminf-viewer-playmode-sequence.v18",
            MODULE.SUPPORTED_UNITY_SCHEMAS,
        )
        self.assertNotIn(
            "endfield.endminf-viewer-playmode-sequence.v17",
            MODULE.SUPPORTED_UNITY_SCHEMAS,
        )

    def test_translation_error_uses_matrix_translation_column(self) -> None:
        identity = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
        translated = [
            [1.0, 0.0, 0.0, 3.0],
            [0.0, 1.0, 0.0, 4.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
        self.assertEqual(MODULE.translation_error(identity, translated), 5.0)

    def test_rotation_error_reports_quarter_turn(self) -> None:
        identity = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
        quarter_turn = [
            [0.0, -1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
        self.assertTrue(
            math.isclose(
                MODULE.rotation_error_degrees(identity, quarter_turn),
                90.0,
                abs_tol=1e-9,
            )
        )

    def test_solver_writeback_accepts_v5_uniform_enabled_state(self) -> None:
        frames = [
            {"secondaryDynamicsSolverWriteback": True},
            {"secondaryDynamicsSolverWriteback": True},
        ]
        self.assertTrue(MODULE.solver_writeback_enabled(frames))

    def test_solver_writeback_rejects_mixed_state(self) -> None:
        frames = [
            {"secondaryDynamicsSolverWriteback": False},
            {"secondaryDynamicsSolverWriteback": True},
        ]
        with self.assertRaisesRegex(
            MODULE.ComparisonError,
            "state changes within the sequence",
        ):
            MODULE.solver_writeback_enabled(frames)


if __name__ == "__main__":
    unittest.main()
