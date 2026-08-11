from __future__ import annotations

import unittest

from character_import.foot_ik_scalar_curves import load_catalog, runtime_metadata


class FootIkScalarCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        if cls.catalog is None:
            raise RuntimeError("generated foot IK scalar catalog is missing")

    def test_exact_original_ui_clip_scope_and_binding_counts(self) -> None:
        self.assertEqual(
            self.catalog["scope"]["unique_current_all_ui_clip_count"], 779
        )
        self.assertEqual(
            self.catalog["scope"]["nonempty_float_buffer_clip_count"], 754
        )
        self.assertEqual(self.catalog["authored_curve_count"], 24)
        self.assertEqual(self.catalog["authored_actor_count"], 9)
        self.assertEqual(
            [
                item["ui_clip_binding_count"]
                for item in self.catalog["requested_values"]
            ],
            [24, 0, 0],
        )

    def test_only_proven_curve_is_track_15_constant_one(self) -> None:
        for row in self.catalog["authored_curves"]:
            self.assertEqual(row["float_curve_count"], row["animator_binding_count"])
            self.assertEqual(len(row["curves"]), 1)
            curve = row["curves"][0]
            self.assertEqual(curve["runtime_name"], "FootIKWeight")
            self.assertEqual(curve["scalar_track_index"], 15)
            self.assertEqual(curve["minimum"], 1.0)
            self.assertEqual(curve["maximum"], 1.0)
            self.assertEqual(len(curve["samples"]), curve["sample_count"])

    def test_absent_key_semantics_are_recovered_but_final_outputs_stay_disabled(self) -> None:
        metadata = runtime_metadata("chr_0032_lizhiyan", self.catalog)
        self.assertFalse(metadata["complete_three_value_source_recovered"])
        self.assertTrue(metadata["three_requested_key_lookup_semantics_recovered"])
        self.assertTrue(metadata["absent_key_fallback_recovered"])
        self.assertFalse(metadata["complete_grounder_weight_outputs_recovered"])
        self.assertTrue(metadata["final_pelvis_weight_recurrence_recovered"])
        recurrence = metadata["final_pelvis_weight_runtime"]
        self.assertEqual(recurrence["air"]["rate"], 360.0)
        self.assertIn("min(abs(floorPredictTheta)-10,0)", recurrence["grounded"]["acceleration_target"])
        self.assertEqual(
            recurrence["grounded"]["desired_gait_values"],
            {"Walk": 0, "Run": 1, "Sprint": 2},
        )
        self.assertFalse(
            recurrence["downstream_grounder_update"]["callback_order_recovered"]
        )
        self.assertEqual(
            recurrence["live_state_producers"]["m_isInUltSkill"],
            "current_skill_skillType_equals_UltimateSkill_7",
        )
        self.assertTrue(metadata["do_not_synthesize_absent_values"])
        self.assertEqual(metadata["current_actor_exact_foot_ik_weight_curve_count"], 2)
        self.assertEqual(
            metadata["foot_ik_adsorb_weight_absent_key_result"],
            "raw_zero_to_immediate_one",
        )


if __name__ == "__main__":
    unittest.main()
