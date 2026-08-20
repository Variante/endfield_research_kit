"""Focused tests for the composite overview phase contract builder."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from build_overview_phase_contract import PhaseContractError, build_contract
except ModuleNotFoundError:  # ``python -m unittest tools.test_...``
    from tools.build_overview_phase_contract import PhaseContractError, build_contract


class OverviewPhaseContractTests(unittest.TestCase):
    def _fixture(self, *, include_endmin_alias: bool = True):
        root = Path(tempfile.mkdtemp())
        animation_root = root / "Playable"
        runtime_rows = []
        boundaries = []
        for index, actor, template, start, loop, start_duration, transition in (
            (10, "endmin", "chr_9000_endmin", 10.0, "A_actor_endminf_ui_overview_loop", 5.866667, 1.466667),
            (11, "chen", "chr_0005_chen", 20.0, "A_actor_chen_ui_overview_loop", 5.25, 0.7875),
            (12, "pelica", "chr_0004_pelica", 30.0, "A_actor_pelica_ui_overview_loop", 6.4166665, 0.575),
            (13, "whiten", "chr_0021_whiten", 45.0, "unused", 1.0, 0.1),
        ):
            boundaries.append(
                {
                    "index": index,
                    "actor": actor,
                    "templateId": template,
                    "modelSwapFrame": int(start * 60),
                    "modelSwapSeconds": start,
                    "bandPeakRatio": 5.0,
                }
            )
            if actor not in {"chen", "pelica"}:
                continue
            token = actor
            runtime_rows.append(
                {
                    "character_id": f"chr_{5 if actor == 'chen' else 4:04d}_{actor}",
                    "actor_token": token,
                    "main_overview": {
                        "controller_name": f"chr_{token}_controller",
                        "source_json": f"export/{token}.json",
                        "start_clip": f"A_actor_{token}_ui_overview_start",
                        "loop_clip": loop,
                        "entry_normalized_offset": 0.0,
                        "destination_normalized_offset": 0.0,
                        "exit_normalized_time": (0.85 if actor == "chen" else 0.91),
                        "transition_duration": (0.15 if actor == "chen" else 0.575),
                        "transition_duration_fixed": actor == "pelica",
                    },
                }
            )
            actor_dir = animation_root / actor.title() / "Animations"
            actor_dir.mkdir(parents=True, exist_ok=True)
            (actor_dir / f"A_actor_{token}_ui_overview_start.anim").write_text(
                f"m_StopTime: {start_duration}\n", encoding="utf-8"
            )
            (actor_dir / f"{loop}.anim").write_text("m_StopTime: 2.0\n", encoding="utf-8")
        if not include_endmin_alias:
            boundaries = [row for row in boundaries if row["actor"] != "endmin"]
        boundaries_path = root / "boundaries.json"
        boundaries_path.write_text(
            json.dumps(
                {
                    "video": {"path": "videos/reference.mkv", "bytes": 1, "sha256": "pinned"},
                    "boundaries": boundaries,
                }
            ),
            encoding="utf-8",
        )
        runtime_path = root / "runtime.json"
        runtime_path.write_text(json.dumps({"actors": runtime_rows}), encoding="utf-8")
        return root, boundaries_path, runtime_path, animation_root

    def test_pelica_and_chen_use_runtime_timing_as_composite_boundary(self) -> None:
        _, boundaries, runtime, animations = self._fixture()
        contract = build_contract(
            boundaries,
            runtime,
            animations,
            ("pelica", "chen"),
        )
        self.assertTrue(contract["admission"]["ready"])
        self.assertEqual(contract["evidencePolicy"]["videoOnlyLoopMeasurement"], "not_claimed")
        pelica = next(row for row in contract["entries"] if row["actor"] == "pelica")
        loop = pelica["phases"][-1]
        self.assertAlmostEqual(loop["startSeconds"], 36.4141665, places=5)
        self.assertEqual(loop["timingSource"], "composite; runtime loop period plus video segment end")

    def test_entry_offset_and_runtime_identity_are_fail_closed(self) -> None:
        _, boundaries, runtime, animations = self._fixture()
        value = json.loads(runtime.read_text(encoding="utf-8"))
        chen = next(row for row in value["actors"] if row["actor_token"] == "chen")
        chen["main_overview"]["entry_normalized_offset"] = 0.1
        runtime.write_text(json.dumps(value), encoding="utf-8")
        contract = build_contract(boundaries, runtime, animations, ("chen",))
        start = contract["entries"][0]["phases"][0]
        self.assertAlmostEqual(start["durationSeconds"], (0.85 - 0.1) * 5.25)

        chen["character_id"] = "chr_0004_pelica"
        runtime.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(PhaseContractError, "character_id"):
            build_contract(boundaries, runtime, animations, ("chen",))

    def test_endmin_alias_fails_closed(self) -> None:
        _, boundaries, runtime, animations = self._fixture()
        with self.assertRaisesRegex(PhaseContractError, "endminf.*unambiguous"):
            build_contract(boundaries, runtime, animations, ("endminf",))

    def test_allow_unresolved_writes_inadmissible_diagnostic_shape(self) -> None:
        _, boundaries, runtime, animations = self._fixture()
        contract = build_contract(
            boundaries,
            runtime,
            animations,
            ("endminf", "pelica"),
            allow_unresolved=True,
        )
        self.assertFalse(contract["admission"]["ready"])
        self.assertEqual([row["actor"] for row in contract["unresolved"]], ["endminf"])
        self.assertEqual([row["actor"] for row in contract["entries"]], ["pelica"])

    def test_missing_following_video_boundary_is_not_loop_end(self) -> None:
        _, boundaries, runtime, animations = self._fixture()
        value = json.loads(boundaries.read_text(encoding="utf-8"))
        value["boundaries"] = [row for row in value["boundaries"] if row["actor"] != "whiten"]
        boundaries.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(PhaseContractError, "following model-swap"):
            build_contract(boundaries, runtime, animations, ("pelica",))


if __name__ == "__main__":
    unittest.main()
