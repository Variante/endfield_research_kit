#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "extract_original_render_parameters.py"
SPEC = importlib.util.spec_from_file_location("extract_original_render_parameters", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class UseDataOnVolumeSnapshotTests(unittest.TestCase):
    def test_checked_in_payload_preserves_all_raw_modifier_pairs(self) -> None:
        payload_path = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters"
            / "character_render_parameters.json"
        )
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        expected = set(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS)
        self.assertGreater(len(payload["characters"]), 0)
        for actor, record in payload["characters"].items():
            modifier = record["modifier_serialized_parameters"]
            self.assertEqual(set(modifier), expected, actor)
            for name, parameter in modifier.items():
                self.assertIn("value", parameter, (actor, name))
                self.assertIn("override_state", parameter, (actor, name))

    def test_exact_30_fields_replace_value_and_override_state(self) -> None:
        base = {
            name: {"value": index + 100, "override_state": True}
            for index, name in enumerate(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS)
        }
        base["charGlobalAmbientParam1"] = {
            "value": {"x": 1, "y": 2, "z": 3, "w": 4},
            "override_state": True,
        }
        modifier = {
            name: {"value": index, "override_state": index % 2 == 0}
            for index, name in enumerate(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS)
        }

        snapshot = MODULE.apply_use_data_on_volume_snapshot(base, modifier)
        for index, name in enumerate(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS):
            self.assertEqual(snapshot[name]["value"], index)
            self.assertEqual(snapshot[name]["override_state"], index % 2 == 0)
            self.assertEqual(snapshot[name]["source"], "actor_overview_modifier")
        self.assertEqual(snapshot["charGlobalAmbientParam1"]["value"]["z"], 3)
        self.assertEqual(
            snapshot["charGlobalAmbientParam1"]["source"],
            "char_override_profile_initial",
        )

        active = MODULE.active_overrides(snapshot)
        self.assertIn(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS[0], active)
        self.assertNotIn(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS[1], active)
        self.assertIn("charGlobalAmbientParam1", active)

        lower = {
            MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS[1]: {
                "value": 77,
                "override_state": True,
            }
        }
        composed = MODULE.compose_volume_layers(
            ("gacha_room_priority_30000", lower),
            ("actor_override_priority_30001", snapshot),
        )
        self.assertEqual(
            composed[MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS[1]]["value"], 77
        )
        self.assertEqual(
            composed[MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS[0]]["value"], 0
        )

    def test_contract_rejects_missing_or_extra_fields(self) -> None:
        modifier = {
            name: {"value": 0, "override_state": False}
            for name in MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS
        }
        modifier.pop(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS[-1])
        with self.assertRaisesRegex(MODULE.RecoveryError, "field contract mismatch"):
            MODULE.apply_use_data_on_volume_snapshot({}, modifier)
        modifier[MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS[-1]] = {
            "value": 0,
            "override_state": False,
        }
        modifier["inventedField"] = {"value": 0, "override_state": False}
        with self.assertRaisesRegex(MODULE.RecoveryError, "field contract mismatch"):
            MODULE.apply_use_data_on_volume_snapshot({}, modifier)


if __name__ == "__main__":
    unittest.main()
