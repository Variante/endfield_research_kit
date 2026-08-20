#!/usr/bin/env python3
"""stdlib-only checks for the serialized CharInfo camera-track contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from build_charinfo_camera_track_contract import (
        DEFAULT_OUTPUT,
        DEFAULT_WORK_ROOT,
        TrackContractError,
        build_contract,
        main,
        pptr,
    )
except ModuleNotFoundError:  # ``python -m unittest tools.test_...``
    from tools.build_charinfo_camera_track_contract import (
        DEFAULT_OUTPUT,
        DEFAULT_WORK_ROOT,
        TrackContractError,
        build_contract,
        main,
        pptr,
    )


class CameraTrackContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = build_contract(DEFAULT_WORK_ROOT)
        cls.by_actor = {row["actor"]: row for row in cls.contract["characters"]}

    def test_live_extract_has_required_roster_and_pptr_edges(self) -> None:
        self.assertEqual(self.contract["character_count"], 31)
        for actor in ("endminf", "pelica", "chen"):
            row = self.by_actor[actor]
            dolly = row["tracked_dolly"]
            pointer = dolly["m_Path"]
            self.assertEqual(dolly["component_type"], "CinemachineTrackedDolly")
            self.assertNotEqual(pointer["path_id"], 0)
            self.assertEqual(pointer["path_id"], row["path"]["path_id"])
            self.assertEqual(pointer["source"]["path_id"], row["path"]["path_id"])
            self.assertNotEqual(pointer["target_name"], "vcam_overview")

    def test_external_pptr_is_rejected(self) -> None:
        with self.assertRaisesRegex(TrackContractError, "external PPtr"):
            pptr({"m_FileID": 1, "m_PathID": 42})

    def test_contract_paths_are_portable(self) -> None:
        source = self.contract["source"]
        self.assertEqual(source["work_root"], "scratch/charinfo_playable_profiles")
        self.assertNotIn(":", source["source_plan"])
        serialized = json.dumps(self.contract)
        self.assertNotIn("source_original_path", serialized)
        self.assertNotIn("Endfield_Data", serialized)

    def test_priority_tracks_capture_path_controls_and_lookat_type(self) -> None:
        expected_names = {
            "endminf": "weapon_overview",
            "pelica": "equip_overview",
            "chen": "skill_overview",
        }
        for actor, path_name in expected_names.items():
            row = self.by_actor[actor]
            dolly = row["tracked_dolly"]
            self.assertEqual(row["path"]["name"], path_name)
            self.assertEqual(dolly["m_PathPosition"], 1.0)
            self.assertEqual(dolly["m_PositionUnits"], 2)
            self.assertEqual(dolly["m_PathOffset"], [0.0, 0.0, 0.0])
            self.assertIn("m_ZDamping", dolly["m_PositionDamping"])
            self.assertIn("m_Enabled", dolly["m_AutoDolly"])
            self.assertEqual(row["lookat_overview_ani"]["component_types"], ["Transform"])

    def test_path_endpoint_is_the_static_camera_position(self) -> None:
        for row in self.contract["characters"]:
            check = row["endpoint_validation"]
            self.assertTrue(check["ok"], row["actor"])
            self.assertEqual(check["max_abs_delta"], 0.0, row["actor"])
            self.assertEqual(check["path_endpoint"], check["static_camera_position"])
            self.assertEqual(row["path"]["waypoints"][-1]["position"], check["path_endpoint"])

    def test_check_detects_modified_output(self) -> None:
        payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        payload["characters"][0]["path"]["resolution"] += 1
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contract.json"
            output.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        "--check",
                        "--work-root",
                        str(DEFAULT_WORK_ROOT),
                        "--output",
                        str(output),
                    ]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
