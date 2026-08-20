#!/usr/bin/env python3
"""stdlib unittest coverage for settled phase sweep wrapping and planning."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from run_settled_phase_sweeps import (
        build_plan,
        expected_render_paths,
        phase_times,
        SweepError,
        validate_render_paths,
        wrap_phase,
    )
except ModuleNotFoundError:  # ``python -m unittest tools.test_...``
    from tools.run_settled_phase_sweeps import (
        build_plan,
        expected_render_paths,
        phase_times,
        SweepError,
        validate_render_paths,
        wrap_phase,
    )


class SettledPhaseSweepTests(unittest.TestCase):
    def test_wrap_handles_negative_and_overflow(self) -> None:
        self.assertAlmostEqual(wrap_phase(-0.2, 2.0), 1.8)
        self.assertAlmostEqual(wrap_phase(2.2, 2.0), 0.2)
        self.assertEqual(wrap_phase(2.0, 2.0), 0.0)

    def test_phase_times_are_seven_wrapped_samples(self) -> None:
        self.assertEqual(
            phase_times(1.9, 2.0),
            [1.3, 1.5, 1.7, 1.9, 0.1, 0.3, 0.5],
        )

    def test_expected_paths_match_unity_three_decimal_stem_contract(self) -> None:
        paths = expected_render_paths({"actor": "chen", "times": [1.1334, 0.1334]})
        self.assertEqual(
            [path.name for path in paths],
            ["chen_t1p133.png", "chen_t0p133.png"],
        )

    def test_validate_render_paths_accepts_exact_seven_planned_files(self) -> None:
        row = {"actor": "chen", "times": [index / 5 for index in range(7)]}
        with tempfile.TemporaryDirectory() as directory:
            sweep_root = Path(directory)
            expected = expected_render_paths(row, sweep_root=sweep_root)
            for path in expected:
                path.touch()
            self.assertEqual(validate_render_paths(row, sweep_root=sweep_root), expected)

    def test_validate_render_paths_rejects_missing_file(self) -> None:
        row = {"actor": "chen", "times": [index / 5 for index in range(7)]}
        with tempfile.TemporaryDirectory() as directory:
            sweep_root = Path(directory)
            expected = expected_render_paths(row, sweep_root=sweep_root)
            for path in expected[:-1]:
                path.touch()
            with self.assertRaisesRegex(SweepError, "missing=.*chen_t1p200.png"):
                validate_render_paths(row, sweep_root=sweep_root)

    def test_validate_render_paths_rejects_unexpected_stale_glob(self) -> None:
        row = {"actor": "chen", "times": [index / 5 for index in range(7)]}
        with tempfile.TemporaryDirectory() as directory:
            sweep_root = Path(directory)
            for path in expected_render_paths(row, sweep_root=sweep_root):
                path.touch()
            stale = sweep_root / "chen_t9p999.png"
            stale.touch()
            with self.assertRaisesRegex(SweepError, "unexpected=.*chen_t9p999.png"):
                validate_render_paths(row, sweep_root=sweep_root)

    def test_plan_selects_repeated_actor_order_and_clip_duration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settled.json"
            path.write_text(
                json.dumps(
                    {
                        "frames": [
                            {
                                "actor": "endmin",
                                "actorDirectory": "Endminf",
                                "loopClip": "endmin_loop",
                                "loopClipSeconds": 2.0833,
                                "loopPhaseSeconds": 1.8167,
                            },
                            {
                                "actor": "chen",
                                "actorDirectory": "Chen",
                                "loopClip": "chen_loop",
                                "loopClipSeconds": 2.0,
                                "loopPhaseSeconds": 1.7334,
                            },
                            {
                                "actor": "pelica",
                                "actorDirectory": "Pelica",
                                "loopClip": "pelica_loop",
                                "loopClipSeconds": 3.0833,
                                "loopPhaseSeconds": 2.3333,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            plan = build_plan(path, ("pelica", "chen", "pelica"))
            self.assertEqual(
                [row["actor"] for row in plan["actors"]], ["pelica", "chen"]
            )
            self.assertEqual(len(plan["actors"][0]["times"]), 7)
            self.assertTrue(
                all(0.0 <= value < 3.0833 for value in plan["actors"][0]["times"])
            )


if __name__ == "__main__":
    unittest.main()
