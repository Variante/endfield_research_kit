from __future__ import annotations

import unittest

from character_import.grounder_profiles import (
    GROUNDER_SCRIPT_PATH_ID,
    build_catalog,
)


class GrounderProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = build_catalog()
        cls.by_id = {
            profile["character_id"]: profile
            for profile in cls.catalog["profiles"]
        }

    def test_exact_original_profile_coverage(self) -> None:
        self.assertEqual(self.catalog["profile_count"], 31)
        self.assertEqual(self.catalog["summary"]["quality3_count"], 31)
        self.assertEqual(self.catalog["summary"]["nonrotated_count"], 28)
        self.assertEqual(self.catalog["summary"]["rotated_count"], 3)
        self.assertEqual(self.catalog["summary"]["zero_layer_mask_count"], 2)
        self.assertEqual(
            self.catalog["summary"]["resolved_bilateral_foot_count"], 31
        )
        self.assertEqual(self.catalog["summary"]["runtime_enabled_count"], 0)
        self.assertEqual(
            self.catalog["summary"]["active_movement_setting_ik_layers_decimal"],
            0x00300000,
        )

    def test_every_profile_keeps_exact_provenance_and_foot_binding(self) -> None:
        for profile in self.catalog["profiles"]:
            source = profile["source"]
            self.assertEqual(source["script_path_id"], GROUNDER_SCRIPT_PATH_ID)
            self.assertEqual(len(source["component_json_sha256"]), 64)
            self.assertEqual(len(source["component_raw_data_sha256"]), 64)
            self.assertTrue(profile["bindings"]["left_foot"]["exact_expected_name"])
            self.assertTrue(profile["bindings"]["right_foot"]["exact_expected_name"])
            self.assertNotIn(None, profile["solver"].values())
            self.assertIsNotNone(profile["component"]["weight"])
            self.assertIsNotNone(profile["component"]["maintianPelvisFootWeight"])
            self.assertIsNotNone(profile["component"]["footAdsorbWeight"])
            self.assertFalse(profile["runtime"]["default_enabled"])
            self.assertFalse(profile["runtime"]["profile_bound_to_lab_runtime"])
            self.assertFalse(
                profile["runtime"]["serialized_layer_mask_runtime_authoritative"]
            )
            self.assertTrue(
                profile["runtime"]["active_movement_setting_ik_layers_recovered"]
            )
            self.assertEqual(
                profile["runtime"]["active_movement_setting_ik_layers_decimal"],
                0x00300000,
            )
            self.assertEqual(
                profile["runtime"]["active_movement_setting_layers"],
                ["Terrain", "IK"],
            )
            self.assertFalse(
                profile["runtime"]["source_compatible_terrain_query_provider_recovered"]
            )

    def test_actor_specific_exceptions_are_not_normalized(self) -> None:
        chen = self.by_id["chr_0005_chen"]
        whiten = self.by_id["chr_0021_whiten"]
        lizhiyan = self.by_id["chr_0032_lizhiyan"]
        camille = self.by_id["chr_0033_camille"]
        liino = self.by_id["chr_0035_liino"]

        self.assertEqual(whiten["component"]["weight"], 0.348)
        self.assertEqual(chen["component"]["maintianPelvisFootWeight"], 0.9999998)
        self.assertEqual(lizhiyan["component"]["maintianPelvisFootWeight"], 0.9999998)
        self.assertEqual(
            chen["runtime"]["mode_status"],
            "rotated_root_aligned_base_recovered_runtime_not_implemented",
        )
        self.assertEqual(
            lizhiyan["runtime"]["mode_status"],
            "rotated_root_aligned_base_recovered_runtime_not_implemented",
        )
        self.assertTrue(
            chen["runtime"]["rotated_root_aligned_base_path_native_evidence"]
        )
        self.assertTrue(
            lizhiyan["runtime"]["rotated_root_aligned_base_path_native_evidence"]
        )
        self.assertEqual(
            camille["runtime"]["mode_status"],
            "ordinary_nonrotated_base_recovered_runtime_not_implemented",
        )
        self.assertEqual(
            liino["runtime"]["mode_status"],
            "rotated_root_aligned_base_recovered_runtime_not_implemented",
        )


if __name__ == "__main__":
    unittest.main()
