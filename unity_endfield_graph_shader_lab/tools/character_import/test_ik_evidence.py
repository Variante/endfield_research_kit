from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.ik_evidence import (  # noqa: E402
    DEFAULT_CATALOG,
    EVIDENCE_NAMES,
    build_playable_ik_evidence_catalog,
)


class PlayableIkEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = build_playable_ik_evidence_catalog(DEFAULT_CATALOG)

    def test_catalog_accounts_for_the_declared_roster_without_fixed_clip_counts(self) -> None:
        self.assertEqual(
            self.payload["roster_count"],
            len(self.payload["characters"]),
        )
        self.assertEqual(
            self.payload["totals"]["actor_count"],
            len(self.payload["characters"]),
        )
        self.assertEqual(
            self.payload["totals"]["clip_count"],
            sum(
                actor["clip_binding_summary"]["clip_count"]
                for actor in self.payload["characters"]
            ),
        )

    def test_exact_clip_lists_match_every_dynamic_summary_count(self) -> None:
        for actor in self.payload["characters"]:
            summary = actor["clip_binding_summary"]
            for evidence_name in EVIDENCE_NAMES:
                self.assertEqual(
                    summary[f"bilateral_{evidence_name}_clip_count"],
                    len(summary[f"clips_with_bilateral_{evidence_name}"]),
                    (actor["character_id"], evidence_name, "bilateral"),
                )
                self.assertEqual(
                    summary[f"partial_{evidence_name}_clip_count"],
                    len(summary[f"clips_with_partial_{evidence_name}"]),
                    (actor["character_id"], evidence_name, "partial"),
                )

    def test_every_current_actor_remains_fail_closed_without_runtime_proof(self) -> None:
        for actor in self.payload["characters"]:
            runtime = actor["runtime_solver"]
            self.assertFalse(runtime["default_enabled"], actor["character_id"])
            self.assertFalse(runtime["consumer_proven"], actor["character_id"])
            self.assertFalse(runtime["weights_proven"], actor["character_id"])
            self.assertTrue(runtime["foot_binding_proven"], actor["character_id"])
            self.assertTrue(runtime["foot_weight_flow_proven"], actor["character_id"])
            self.assertTrue(runtime["foot_weight_source_proven"], actor["character_id"])
            requested = runtime["foot_weight_source"]["requested_values"]
            self.assertEqual(
                [item["runtime_name"] for item in requested],
                ["FootIKWeight", "FootIKFootWeight", "FootIKAdsorbWeight"],
                actor["character_id"],
            )
            self.assertEqual(
                [item["ui_clip_binding_count"] for item in requested],
                [24, 0, 0],
                actor["character_id"],
            )
            self.assertTrue(
                runtime["foot_weight_source"]["do_not_synthesize_absent_values"]
            )
            self.assertTrue(
                runtime["foot_weight_source"]["absent_key_fallback_recovered"]
            )
            self.assertFalse(
                runtime["foot_weight_source"]["complete_grounder_weight_outputs_recovered"]
            )
            self.assertTrue(
                runtime["foot_weight_source"][
                    "final_pelvis_weight_recurrence_recovered"
                ]
            )
            self.assertEqual(
                runtime["foot_weight_source"]["final_pelvis_weight_runtime"][
                    "air"
                ]["rate"],
                360.0,
            )
            self.assertNotIn(
                "serialized_grounder_defaults", runtime["foot_weight_source"]
            )
            profile_binding = runtime["foot_weight_source"][
                "serialized_profile_binding"
            ]
            self.assertTrue(profile_binding["do_not_substitute_global_defaults"])
            self.assertEqual(
                profile_binding["status"],
                "exact_per_actor_grounder_component_bound_to_manifest",
            )
            self.assertFalse(profile_binding["animation_scalar_curves_bound"])
            original_profile = runtime["original_grounder_profile"]
            self.assertEqual(original_profile["character_id"], actor["character_id"])
            self.assertFalse(original_profile["runtime"]["default_enabled"])
            self.assertEqual(
                original_profile["runtime"][
                    "active_movement_setting_ik_layers_decimal"
                ],
                0x00300000,
            )
            queries = runtime["ordinary_grounding"]["queries"]
            self.assertTrue(queries["active_movement_setting_ik_layers_recovered"])
            self.assertEqual(
                queries["active_movement_setting_ik_layers_decimal"], 0x00300000
            )
            self.assertFalse(
                queries["source_compatible_terrain_query_provider_recovered"]
            )
            foot_binding = runtime["per_target_binding"]["foot"]
            self.assertEqual(
                foot_binding["source_roster_audit_count"],
                len(self.payload["characters"]),
            )
            self.assertIn("source_postmodel_examples", foot_binding)
            self.assertNotIn("source_postmodels", foot_binding)
            self.assertEqual(
                runtime["ordinary_grounding"]["status"],
                "source_closed_quality3_ordinary_and_rotated_root_aligned_base_paths_"
                "shared_prediction_and_capsule_redirects_open_not_implemented",
                actor["character_id"],
            )
            self.assertEqual(
                runtime["ordinary_grounding"]["position_request_formula"],
                "lerp(authoredIKFootBone.position,leg.IKPosition,"
                "clamp(weight*maintianPelvisFootWeight,0,1))",
                actor["character_id"],
            )
        self.assertEqual(
            self.payload["totals"]["runtime_consumers_unproven_count"],
            len(self.payload["characters"]),
        )
        self.assertEqual(
            self.payload["totals"]["runtime_weights_unproven_count"],
            len(self.payload["characters"]),
        )


if __name__ == "__main__":
    unittest.main()
