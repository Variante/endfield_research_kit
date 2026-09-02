#!/usr/bin/env python3

from __future__ import annotations

import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_secondary_dynamics_owner_recovery as builder


class OverviewControllerPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actor = {"character_id": "chr_0003_endminf"}
        self.manifest = {
            "original_usage": {
                "selected_ui_clip_assets": [{"Name": "ui_overview_start"}],
                "selected_ui_item_widget_clip_assets": [{"Name": "ui_widget"}],
            }
        }

    def test_recovers_source_from_maintained_manifest_inputs(self) -> None:
        source = r"D:\\source\\AnimatorController#1.json"
        with patch.object(
            builder,
            "recover_main_overview_controller",
            return_value={"source_json": source},
        ) as recover:
            actual = builder.overview_controller_path("endminf", self.actor, self.manifest)

        self.assertEqual(actual, Path(source))
        recover.assert_called_once_with(
            {
                "character_id": "chr_0003_endminf",
                "ui_animation": {
                    "selected_entries": [{"Name": "ui_overview_start"}],
                    "selected_companion_widget_entries": [{"Name": "ui_widget"}],
                },
            }
        )

    def test_missing_controller_fails_with_actor_diagnostic(self) -> None:
        with patch.object(builder, "recover_main_overview_controller", return_value={}):
            with self.assertRaisesRegex(
                ValueError,
                "endminf: maintained controller recovery did not resolve",
            ):
                builder.overview_controller_path("endminf", self.actor, self.manifest)


class IfixBoundaryRefreshTests(unittest.TestCase):
    def test_current_state_projects_exact_target_count_and_hash(self) -> None:
        boundary = builder.ifix_boundary_contract()
        state = json.loads(builder.IFIX_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(boundary["persistent_target_count"], 32)
        self.assertEqual(
            boundary["persistent_target_count"],
            state["patch_format"]["target_count"],
        )
        self.assertFalse(boundary["beyond_dynamic_bone_patch_present"])

    def test_projection_refresh_preserves_unrelated_owner_payload(self) -> None:
        payload = {
            "schema": "endfield.charinfo.secondary-dynamics-owner.v1",
            "actors": {"endminf": {"sentinel": 7}},
            "ifix_boundary": {"sha256": "stale"},
        }
        refreshed = builder.refresh_ifix_boundary_payload(payload)
        self.assertEqual(refreshed["actors"], payload["actors"])
        self.assertNotEqual(refreshed["ifix_boundary"], payload["ifix_boundary"])
        self.assertEqual(refreshed["ifix_boundary"]["persistent_target_count"], 32)

    def test_projection_refresh_rejects_wrong_owner_schema(self) -> None:
        with self.assertRaisesRegex(ValueError, "owner report schema drifted"):
            builder.refresh_ifix_boundary_payload({"schema": "wrong"})


if __name__ == "__main__":
    unittest.main()
