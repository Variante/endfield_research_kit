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


class OriginalRenderParameterExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = MODULE.find_repo_root(HERE)
        cls.payload = MODULE.extract(cls.repo_root)

    def test_exact_source_identity(self) -> None:
        expected_count = len(MODULE.discover_actor_manifests(self.repo_root))
        self.assertEqual(len(self.payload["characters"]), expected_count)
        self.assertEqual(len(self.payload["validation"]["actors"]), expected_count)
        base = self.payload["base_character_volume"]["source"]
        self.assertEqual(base["path_id"], -1513979593761442464)
        self.assertEqual(
            base["raw_data_sha256"],
            "5133a5977d6cf4321e9f61795c55ba9218bfc1cbce83738d2da91f94001370b0",
        )
        expected = {
            "wulfa": (
                5250125279948022002,
                "3a5c681ae974ad0c53a831b88dfbe8e902662a70401a67947c7d14e8fd903d33",
                "track_chr_0028_wulfa",
            ),
            "zhuangfy": (
                7598368292888403912,
                "8518128249611e61a455e28e493f6b7b97e66b6d18c67f17d9d1db1912e69e3e",
                "track_chr_0030_zhuangfy",
            ),
        }
        for actor, (path_id, digest, ancestor) in expected.items():
            record = self.payload["characters"][actor]
            self.assertEqual(record["modifier_source"]["path_id"], path_id)
            self.assertEqual(record["modifier_source"]["raw_data_sha256"], digest)
            self.assertEqual(
                record["modifier_ancestry"],
                ["volume_overview", "VolumeModifiers", ancestor],
            )

    def test_exact_post_use_data_on_volume_snapshot(self) -> None:
        expected = {
            "wulfa": (1.05, 0.55, 0.9, -0.1, 0),
            "zhuangfy": (1.0, 0.55, 1.0, 0.0, 0),
        }
        for actor, values in expected.items():
            record = self.payload["characters"][actor]
            snapshot = record["post_use_data_on_volume"]
            actual = (
                snapshot["charMainLightMultiplier"]["value"],
                snapshot["charEnvLightMultiplier"]["value"],
                snapshot["charEnvShadowMultiplier"]["value"],
                snapshot["charMainLightRangeBias"]["value"],
                snapshot["charIgnoreMainLightShadow"]["value"],
            )
            self.assertEqual(actual, values)
            self.assertEqual(
                snapshot["charCameraFollowMainLightBias"]["value"],
                {"x": 32.0, "y": 12.0},
            )
            self.assertEqual(snapshot["charMainLightMode"]["value"], 1)
            self.assertEqual(snapshot["charGlobalAmbientParam1"]["value"], {
                "x": 0.15,
                "y": 1.5,
                "z": 0.5,
                "w": 0.0,
            })

    def test_native_snapshot_copies_all_30_value_and_state_pairs(self) -> None:
        copied = set(MODULE.CHAR_LIGHT_VOLUME_DATA_FIELDS)
        self.assertEqual(len(copied), 30)
        for actor, record in self.payload["characters"].items():
            modifier = record["modifier_serialized_parameters"]
            snapshot = record["post_use_data_on_volume"]
            self.assertEqual(set(modifier), copied, actor)
            for name in copied:
                self.assertEqual(snapshot[name]["value"], modifier[name]["value"], (actor, name))
                self.assertEqual(
                    snapshot[name]["override_state"],
                    modifier[name]["override_state"],
                    (actor, name),
                )
                self.assertEqual(snapshot[name]["source"], "actor_overview_modifier")

        zhuangfy = self.payload["characters"]["zhuangfy"]
        snapshot = zhuangfy["post_use_data_on_volume"]
        active = zhuangfy["resolved_active_overrides"]
        for name in (
            "charIgnoreMainLightShadow",
            "charShadowTintControl",
            "charShadowTintColor",
        ):
            self.assertFalse(snapshot[name]["override_state"])
            self.assertNotIn(name, active)
        self.assertEqual(snapshot["charGlobalAmbientParam1"]["source"], "charinfo_volume")

    def test_material_payload_is_deliberately_manifest_owned(self) -> None:
        self.assertEqual(
            set(self.payload["validation"]["material_count"].values()),
            {0},
        )
        self.assertTrue(
            self.payload["validation"]["all_material_sources_selected_by_exact_identity"]
        )
        self.assertEqual(
            self.payload["validation"]["material_manifest_payload_mismatch_count"],
            0,
        )
        self.assertEqual(
            self.payload["validation"]["material_manifest_conflicting_value_count"],
            0,
        )
        for actor in self.payload["characters"].values():
            self.assertEqual(actor["materials"], [])

    def test_live_only_state_is_not_invented(self) -> None:
        unknown = self.payload["live_only_unknowns"]
        self.assertIn("_ExposureParams.x", unknown)
        self.assertIn("_CharacterParams11.xyz", unknown)
        encoded = MODULE.encoded_json(self.payload).lower()
        self.assertIn('"visual_fitting_allowed": false', encoded)
        self.assertNotIn('"adapted_exposure_value"', encoded)

    def test_environment_static_vector(self) -> None:
        self.assertEqual(
            self.payload["environment"]["environment_global_params0"],
            [0.28772247, 0.28772247, 1.0, 0.0],
        )
        serialized = self.payload["environment"]["serialized"]
        self.assertEqual(serialized["direct_pitch_yaw"], {"x": 40.0, "y": -181.6})
        self.assertEqual(serialized["direct_color_temperature"], 7000.0)
        self.assertEqual(serialized["direct_ev100"], 13.5)

    def test_json_encoding_is_deterministic(self) -> None:
        first = MODULE.encoded_json(self.payload)
        second = MODULE.encoded_json(json.loads(first))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
