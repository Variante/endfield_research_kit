from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_manifest_common import (  # noqa: E402
    GROUNDING_RUNTIME_POLICY,
    _ENDFIELD_HUMANOID_NATIVE_EVIDENCE,
    attach_ik_clip_evidence,
    classify_clip,
)
import unity_muscleclip_sampler as muscle_sampler  # noqa: E402


class ManifestCommonTests(unittest.TestCase):
    def test_native_twist_and_normal_update_contract_is_source_closed(self) -> None:
        evidence = _ENDFIELD_HUMANOID_NATIVE_EVIDENCE

        self.assertEqual(evidence["twist_solve_rva"], "0xB323F0")
        public = evidence["public_2021_3_34f1_baseline"]
        self.assertEqual(public["human_trait_muscle_count"], 95)
        self.assertEqual(public["human_trait_bone_count"], 55)
        self.assertEqual(public["extension_names_present"], 0)
        self.assertEqual(public["direct_muscle_to_bone_table_rva"], "0x17E70C0")
        self.assertEqual(public["body_bone_axis_to_muscle_table_rva"], "0x17E6D90")
        self.assertFalse(public["physical_transform_output_oracle"])
        fixture = public["synthetic_numeric_fixture"]
        self.assertEqual(fixture["mapped_direct_muscles"], 49)
        self.assertEqual(fixture["ruri_compared_body_bones"], 21)
        self.assertLess(fixture["ruri_max_angular_error_degrees"], 1e-4)
        self.assertEqual(
            fixture["scope"],
            "public_stock_numeric_validation_not_endfield_f5_output",
        )
        converter = evidence["production_axes_converter"]
        self.assertEqual(
            converter["status"],
            "instruction_level_semantic_counterpart_proven_no_f5_equation_delta",
        )
        self.assertEqual(converter["endfield_inner_range"], "0xB34260..0xB34908")
        self.assertEqual(converter["public_inner_range"], "0x95B8B0..0x95C12C")
        self.assertEqual(converter["dispatch_cases"], [1, 2, 4, "default"])
        self.assertEqual(converter["humanoid_zyroll_case"], 1)
        self.assertEqual(converter["endfield_tangent_helper_rva"], "0xA7B990")
        self.assertEqual(converter["public_avatar_sandwich"], "leaf_0x908540")
        self.assertEqual(evidence["human_fix_twist_rva"], "0xB27930")
        self.assertEqual(len(evidence["twist_solve_pairs"]), 8)
        self.assertEqual(
            evidence["post_apply_0xB17DB0_status"],
            "per_side_foot_goal_ik_rebuild_not_twist_solve_"
            "wulfa_SprintSP_controller_and_optimized_job_path_skip",
        )
        self.assertIn(
            "0xB323F0_twist_solve", evidence["normal_animator_update_chain"]
        )
        self.assertEqual(
            evidence["muscle_production_chain"]["extension_table_rows"][
                "RightToes"
            ],
            [40, 41, 42],
        )
        mapping = evidence["twist_solve_physical_mapping"]
        self.assertEqual(mapping["status"], "closed_for_current_playable_avatars")
        self.assertEqual(mapping["pair_observations"], 272)
        self.assertEqual(mapping["compact_intermediate_nodes"], 0)
        self.assertEqual(mapping["physical_intermediate_nodes"], 0)
        self.assertIn("named_twist_side_branch_local_tracks_untouched", evidence["twist_solve_write_boundary"])
        fixture = evidence["extension_muscle_numeric_fixture"]
        self.assertEqual(fixture["current_all_ui_clips_mapping_extensions"], 0)
        self.assertEqual(fixture["broader_clips_animating_all_six"], 76)
        self.assertEqual(fixture["clip_name"], "A_actor_loli_sprint_loop_sp_01")
        self.assertEqual(fixture["animated_extension_slots"], [28, 30, 31, 39, 41, 42])
        controller = fixture["controller_state"]
        self.assertEqual(
            controller["state"],
            "Base Layer.Locomotion.Grounded.Move.SprintSP",
        )
        self.assertTrue(controller["write_default_values"])
        self.assertFalse(controller["state_ik_on_feet"])
        self.assertFalse(controller["layer_ik_pass"])
        self.assertTrue(controller["all_layers_ik_pass_false"])
        self.assertTrue(controller["all_states_ik_on_feet_false"])
        self.assertTrue(
            fixture["physical_output_oracle"][
                "do_not_substitute_unity_2022_lab_output"
            ]
        )
        oracle = fixture["physical_output_oracle"]
        self.assertEqual(
            oracle["status"],
            "original_2021_3_34f5_native_QTS_fixture_recovered",
        )
        self.assertEqual(oracle["frame_count"], 33)
        self.assertEqual(oracle["physical_node_count"], 486)
        self.assertEqual(
            oracle["raw_sha256"],
            "3276498D97C516E83D1C0F7094754C9D7E2F3A5B448EBD8DBAFE01E1615FA115",
        )
        native_pose = evidence["post_conversion_pose_bake"][
            "original_native_full_pose_oracle"
        ]
        self.assertEqual(native_pose["isolated_humanoid_rotations_exact"], [693, 693])
        self.assertEqual(native_pose["generic_overlay_records_exact"], [1914, 1914])
        self.assertEqual(native_pose["untouched_rest_records_exact"], [13332, 13332])
        self.assertTrue(native_pose["repeat_runs_identical"])
        self.assertEqual(native_pose["guard_failures"], 0)

    def test_sampler_and_manifest_native_evidence_schema_do_not_drift(self) -> None:
        self.assertEqual(
            _ENDFIELD_HUMANOID_NATIVE_EVIDENCE,
            muscle_sampler.ENDFIELD_HUMANOID_NATIVE_EVIDENCE,
        )

    def test_grounding_component_audit_records_recovered_rotated_root_frame(self) -> None:
        audit = GROUNDING_RUNTIME_POLICY["original_component_audit"]

        self.assertEqual(audit["actor_count"], 31)
        self.assertEqual(audit["nonrotated_ordinary_count"], 28)
        self.assertEqual(audit["rotated_root_aligned_count"], 3)
        self.assertEqual(
            audit["rotated_root_aligned_actors"],
            ["chr_0005_chen", "chr_0032_lizhiyan", "chr_0035_liino"],
        )
        self.assertEqual(
            GROUNDING_RUNTIME_POLICY["field_offsets"]["rotateSolver"],
            "Grounding+0x9C",
        )
        self.assertEqual(
            GROUNDING_RUNTIME_POLICY["field_offsets"]["isAccelerating"],
            "Grounding+0x3D",
        )
        self.assertNotIn("rotateSolver_true", GROUNDING_RUNTIME_POLICY["unsupported_modes"])
        self.assertEqual(
            GROUNDING_RUNTIME_POLICY["rotated_root_aligned_path"]["common_final_stages"],
            ["FinalSetIKPosition", "SetLegIK"],
        )
        queries = GROUNDING_RUNTIME_POLICY["queries"]
        self.assertEqual(queries["delegate_installer"], "Grounding_ctor_0x4407F80")
        self.assertEqual(queries["trigger_interaction"], "Ignore_1")
        self.assertFalse(queries["serialized_grounder_layer_mask_runtime_authoritative"])
        self.assertTrue(queries["active_movement_setting_ik_layers_recovered"])
        self.assertEqual(
            queries["active_movement_setting_ik_layers_decimal"], 0x00300000
        )
        self.assertEqual(queries["active_movement_setting_layers"], ["Terrain", "IK"])
        self.assertFalse(queries["source_compatible_terrain_query_provider_recovered"])
        self.assertEqual(
            queries["collider_acceptance"]["root"],
            "valid_ECSColliderResultProxy_required",
        )
        self.assertEqual(
            audit["late_recovered_grounders"],
            ["chr_0032_lizhiyan", "chr_0033_camille", "chr_0035_liino"],
        )
        self.assertEqual(
            audit["serialized_zero_layer_mask_actors"],
            ["chr_0018_dapan", "chr_0024_deepfin"],
        )
        self.assertEqual(
            audit["runtime_layer_source"],
            "MovementSetting._ikLayers_via_OnAnimationSetup",
        )

    def test_actor_token_beginning_with_ik_is_not_an_ik_helper(self) -> None:
        classification = classify_clip("A_actor_ikut_ui_overview_loop")
        self.assertEqual(classification["clip_class"], "ui")
        self.assertTrue(classification["standalone_candidate"])

    def test_explicit_ik_segment_remains_a_helper(self) -> None:
        classification = classify_clip("A_actor_test_ik_hand")
        self.assertEqual(classification["clip_class"], "helper")
        self.assertFalse(classification["standalone_candidate"])

    def test_actor_token_ending_with_ik_is_not_an_ik_helper(self) -> None:
        classification = classify_clip("A_actor_nik_ui_overview_loop")
        self.assertEqual(classification["clip_class"], "ui")

    def test_hand_ik_evidence_does_not_infer_runtime_solver(self) -> None:
        ik = {"source_evidence": {}, "runtime_solver": {"default_enabled": False}}
        hand_root = "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2"
        clips = [
            {
                "name": "A_actor_test_ui_overview_loop",
                "bones": [
                    {"path": "Root/IK_Root/IK_Hand_L_001", "pos_animated": True},
                    {"path": "Root/IK_Root/IK_Hand_R_001", "rot_animated": True},
                    {"path": "Root/IK_Foot_L_001", "pos_animated": True},
                    {"path": "Root/IK_Foot_R_001", "rot_animated": True},
                    {"path": "Root/IK_Knee_L_001", "pos_animated": True},
                    {"path": "Root/IK_Knee_R_001", "rot_animated": True},
                    {"path": "Root/IK_Root/IK_Weapon_L_001", "pos_animated": True},
                    {"path": "Root/IK_Root/IK_Weapon_R_001", "rot_animated": True},
                    {"path": hand_root + "/Bip001_L_Clavicle/Bip001_L_UpperArm/Bip001_L_Forearm/Bip001_L_Hand", "rot_animated": True},
                    {"path": hand_root + "/Bip001_R_Clavicle/Bip001_R_UpperArm/Bip001_R_Forearm/Bip001_R_Hand", "rot_animated": True},
                ],
            }
        ]

        attach_ik_clip_evidence(ik, clips)

        record = ik["clip_binding_evidence"][0]
        self.assertTrue(record["has_bilateral_hand_targets"])
        self.assertTrue(record["has_bilateral_deforming_hands"])
        self.assertTrue(record["has_bilateral_foot_targets"])
        self.assertTrue(record["has_bilateral_knee_targets"])
        self.assertTrue(record["has_bilateral_weapon_targets"])
        summary = ik["clip_binding_summary"]
        self.assertEqual(summary["bilateral_hand_targets_clip_count"], 1)
        self.assertEqual(summary["bilateral_deforming_hands_clip_count"], 1)
        self.assertEqual(summary["bilateral_foot_targets_clip_count"], 1)
        self.assertEqual(summary["bilateral_knee_targets_clip_count"], 1)
        self.assertEqual(summary["bilateral_weapon_targets_clip_count"], 1)
        self.assertEqual(summary["partial_weapon_targets_clip_count"], 0)
        self.assertFalse(ik["runtime_solver"]["default_enabled"])
        self.assertIn("no runtime solver", record["evidence_boundary"])


if __name__ == "__main__":
    unittest.main()
